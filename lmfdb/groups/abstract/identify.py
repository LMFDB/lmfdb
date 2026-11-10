# -*- coding: utf-8 -*-
r"""
Identify a finite group from a user-supplied description (permutation
generators, a PC group code, or matrix generators) by computing the
LMFDB isomorphism-invariant hash in-process with Sage's ``libgap`` and
looking it up against the database.

The hash is a faithful port of the Magma implementation in the
FiniteGroups repository (``Code/Hash.m``, ``github.com/roed314/FiniteGroups``)
which produced every value stored in ``gps_groups.hash`` and
``gps_smallhash.hash``.  See :func:`group_hash` for the algorithm and
:func:`magma_identifiable` for the pipeline-era ``IdentifyGroup``
availability predicate that the stored hashes depend on.

SECURITY: user input is *never* passed to ``libgap.eval``.  Descriptions
are validated with strict regular expressions and (for matrices)
``ast.literal_eval`` on a literals-only body; the group objects are then
constructed programmatically.  Parsing, group construction and the order
computation all run inside a single ``cysignals`` ``alarm``; the order cap
is then enforced before any further work (in particular before factoring
the order), and the hash computation runs under a second alarm.  No
unbounded Sage or GAP computation is reachable from user input.  GAP's own
start-up is deliberately outside the guard, see :func:`prepare_gap`.
"""

import ast
import re
from collections import defaultdict

from sage.all import (
    ZZ,
    GF,
    Zmod,
    matrix,
    latex,
    PermutationGroup,
    alarm,
    cancel_alarm,
)
from sage.libs.gap.libgap import libgap
from sage.libs.gap.util import GAPError
from cysignals.alarm import AlarmInterrupt

from lmfdb import db
from .web_groups import primary_to_smith
from .hash_lookup import live_pages_available, resolve_order_hash

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REDP = 9223372036854775783  # largest prime below 2^63 (Postgres signed bigint)

ORDER_CAP = 10 ** 6      # the magma_identifiable predicate is only verified this far
MAX_INPUT = 2000         # characters
MAX_GENS = 20
MAX_PERM_DEGREE = 512
MAX_MATRIX_DIM = 12
MAX_MATRIX_Q = 1024
MAX_MATRIX_ENTRY = 10 ** 6

ORDER_TIMEOUT = 5        # seconds to compute the group order
HASH_TIMEOUT = 10        # seconds to compute the hash / identification


class HashUncomputable(Exception):
    """The stored hash embeds a pipeline-era small-group index that cannot be
    reproduced server-side.

    This happens at orders ``m`` of signature ``p^2 q r`` or ``p^2 q^2`` above
    2000 whose ``IdentifyGroup`` numbering drifted between the pipeline-era
    Magma and today's GAP, when ``m`` has no rows in ``gps_groups`` to recover
    the index from (e.g. the order-5050 Borel subgroup arising in
    ``hash(PSL(2,101))``), and at magma-identifiable orders that GAP cannot
    identify.  The single argument is the obstructing order.
    """


class DescriptionError(ValueError):
    """The user description could not be parsed or is out of bounds."""


# ---------------------------------------------------------------------------
# The hash algorithm (faithful port of FiniteGroups/Code/Hash.m)
# ---------------------------------------------------------------------------

def collapse_int_list(x):
    """Combine (nested) integers into a single integer, matching Magma's
    ``CollapseIntList``.  Scalars reduce mod :data:`REDP`; a list folds
    ``res = 997*len(L)`` then ``res = x XOR (1000003*res mod REDP)``."""
    if isinstance(x, (list, tuple)):
        L = [collapse_int_list(e) for e in x]
        res = 997 * len(L)
        for y in L:
            res = y ^ ((1000003 * res) % REDP)
        return res
    return int(x) % REDP


def magma_identifiable(n):
    r"""Whether pipeline-era Magma ``CanIdentifyGroup(n)`` (equivalently, the
    order at which the stored hashes used the small-group index rather than
    conjugacy-class statistics).

    Closed form, exact on ``2..10**6`` (0 mismatches vs. a Magma V2.28 sweep).
    GAP's availability differs (GAP can id 1152, 1920 and cubefree orders below
    50000, but not ``q*p^3`` for ``p >= 11``); this predicate tracks *Magma*,
    which is what the stored hashes were built with.
    """
    n = ZZ(n)
    if n <= 2000:
        return n not in (512, 1024, 1152, 1536, 1920)
    F = n.factor()
    es = sorted((e for p, e in F), reverse=True)
    if es[0] == 1:
        return True                              # squarefree
    if len(F) == 1:
        p, e = F[0]
        return e <= 4 or (e == 5 and p <= 5)     # p^2..p^4 all p; p^5 only p<=5
    if len(F) == 2 and es[1] == 1:               # p^k * q
        k = es[0]
        p = [p for p, e in F if e == k][0]
        if k == 2:
            return True                          # p^2 q, all p
        return (p == 2 and k <= 8) or (p == 3 and k <= 6) or (p == 5 and k <= 5) \
            or (p == 7 and k <= 4) or k == 3     # p^k q with p^k | 2^8,3^6,5^5,7^4; p^3 q all p
    return tuple(es) in ((2, 2), (2, 1, 1))      # p^2 q^2, p^2 q r (cubefree databases)


def _small_index(G, m):
    """The small-group index that the stored hashes use for a group ``G`` of
    order ``m``, or ``None`` when the conjugacy-class statistics branch applies.

    Raises :class:`HashUncomputable` when the index cannot be reproduced.
    """
    m = ZZ(m)
    if m <= 2000:
        if m in (512, 1024, 1152, 1536, 1920):
            return None                          # conjugacy-class statistics
        return int(libgap.IdGroup(G)[1])         # GAP == Magma numbering here
    if not magma_identifiable(m):
        return None                              # conjugacy-class statistics
    sig = tuple(sorted((e for p, e in m.factor()), reverse=True))
    if sig in ((2, 1, 1), (2, 2)):
        # Numbering drift: labels follow GAP, but stored hashes embed the
        # pipeline-era index.  Recover it from the (order, counter) row.
        if not libgap.IdGroupsAvailable(m):
            raise HashUncomputable(int(m))
        j = int(libgap.IdGroup(G)[1])
        stored = db.gps_groups.lucky({"order": int(m), "counter": j}, "hash")
        if stored is None:
            raise HashUncomputable(int(m))
        return int(stored)
    # Other magma-identifiable signatures: GAP index agrees class-wide.
    if not libgap.IdGroupsAvailable(m):
        raise HashUncomputable(int(m))
    return int(libgap.IdGroup(G)[1])


def easy_hash(G):
    """Port of Magma ``EasyHash``: the small-group index when available, else
    ``CollapseIntList`` of the sorted ``[order, class size, multiplicity]``
    conjugacy-class statistics."""
    m = ZZ(G.Order())
    idx = _small_index(G, m)
    if idx is not None:
        return idx
    data = defaultdict(int)
    for C in G.ConjugacyClasses():
        data[(int(C.Representative().Order()), int(C.Size()))] += 1
    triples = sorted([o, s, mult] for (o, s), mult in data.items())
    return collapse_int_list(triples)


def group_hash(G):
    """Port of Magma ``hash``: isomorphism-invariant hash of a finite group.

    * small-group index when the order is identifiable;
    * ``CollapseIntList`` of the ascending invariant factors when abelian;
    * otherwise ``CollapseIntList`` of the sorted ``[order, EasyHash]`` pairs
      over ``G`` and its maximal-subgroup class representatives.
    """
    m = ZZ(G.Order())
    idx = _small_index(G, m)
    if idx is not None:
        return idx
    if G.IsAbelian():
        smith = primary_to_smith(sorted(ZZ(q) for q in G.AbelianInvariants()))
        return collapse_int_list([int(x) for x in smith])
    pairs = [[int(m), easy_hash(G)]]
    for H in G.MaximalSubgroupClassReps():
        pairs.append([int(H.Order()), easy_hash(H)])
    pairs.sort()
    return collapse_int_list(pairs)


# ---------------------------------------------------------------------------
# Input parsers (strict; never eval user text)
# ---------------------------------------------------------------------------

# One or more cycles, cycles optionally comma-separated (as in web_groups.perm_re).
PERM_RE = re.compile(r"^\(\d+(,\d+)*\)(,?\(\d+(,\d+)*\))*$")
# Generator boundary: a comma sitting between a close paren and an open paren.
_GEN_SPLIT_RE = re.compile(r"(?<=\)),(?=\()")
_CYCLE_RE = re.compile(r"\((\d+(?:,\d+)*)\)")

PC_RE = re.compile(r"^(\d+)PC(\d+)$")
MAT_RE = re.compile(r"^Mat\((\d+),(\d+)\):(.*)$", re.DOTALL)


def looks_like_permutation(s):
    """Cheap check used by the jump box: does ``s`` look like permutation input?"""
    return s.startswith("(") and PERM_RE.fullmatch(s.replace(" ", "")) is not None


def parse_permutation_group(s):
    """Parse comma-separated permutation generators in cycle notation, e.g.
    ``(1,2,3)(4,5),(1,2)``, into a GAP permutation group."""
    s = s.replace(" ", "")
    if not PERM_RE.fullmatch(s):
        raise DescriptionError(
            "Not a valid list of permutations; use disjoint cycle notation, "
            "e.g. (1,2,3)(4,5),(1,2)")
    gen_strs = _GEN_SPLIT_RE.split(s)
    if len(gen_strs) > MAX_GENS:
        raise DescriptionError(f"At most {MAX_GENS} generators are allowed.")
    gens = []
    maxpt = 0
    for gs in gen_strs:
        cycles = []
        for cyc in _CYCLE_RE.findall(gs):
            pts = [int(x) for x in cyc.split(",")]
            if any(p < 1 for p in pts):
                raise DescriptionError("Permutation points must be positive integers.")
            if len(set(pts)) != len(pts):
                raise DescriptionError("A cycle may not repeat a point.")
            if pts:
                maxpt = max(maxpt, max(pts))
            cycles.append(tuple(pts))
        gens.append(cycles)
    if maxpt > MAX_PERM_DEGREE:
        raise DescriptionError(
            f"Permutation degree must be at most {MAX_PERM_DEGREE}.")
    try:
        G = PermutationGroup(gens)
    except (ValueError, TypeError) as err:
        raise DescriptionError(f"Invalid permutations: {err}")
    return G._libgap_()


def parse_pc_group(s):
    """Parse ``<order>PC<code>`` (the FiniteGroups ``StringToGroup`` convention)
    into a GAP PC group.

    Like the other parsers this is called from :func:`identify_group` inside
    the alarm that also bounds the order computation, so the ``Order()`` check
    below (a PC group knows its order) is guarded."""
    m = PC_RE.fullmatch(s.replace(" ", ""))
    if not m:
        raise DescriptionError(
            "Not a valid PC code; use <order>PC<code>, e.g. 8PC4.")
    order = ZZ(m.group(1))
    code = ZZ(m.group(2))          # sage Integer -> safe big-integer coercion
    if order < 1:
        raise DescriptionError("Order must be a positive integer.")
    if order > ORDER_CAP:
        raise DescriptionError(
            f"Order {order} exceeds the supported bound of {ORDER_CAP}.")
    try:
        G = libgap.PcGroupCode(code, order)
    except (GAPError, ValueError, RuntimeError):
        raise DescriptionError(f"Invalid PC code for order {order}.")
    if ZZ(G.Order()) != order:
        raise DescriptionError(
            f"PC code does not encode a group of order {order}.")
    return G


def entry_ring(q):
    """The coefficient ring for ``Mat(d,q)`` together with the decoder turning
    an integer code from the input into a ring element.

    * ``q = p`` prime: ``GF(p)``, codes are integers reduced modulo ``p``;
    * ``q = p^e`` with ``e > 1``: ``GF(q)``, codes are integers ``0 <= x < q``
      whose base-``p`` digits, least significant first, are the coefficients of
      the entry in the basis ``1, a, ..., a^(e-1)``, where ``a`` is the Conway
      generator of ``GF(q)``, the element GAP writes as ``Z(q)``.  This is
      the convention of ``DecodeMat`` in the FiniteGroups repository, whose
      ``Basis(GF(q))`` is that same power basis;
    * ``q`` not a prime power: ``Z/q``, codes are integers reduced modulo ``q``.
    """
    q = ZZ(q)
    if not q.is_prime_power():
        R = Zmod(q)
        return R, R
    R = GF(q, "a")
    e = q.factor()[0][1]
    if e == 1:
        return R, R

    def decode(x):
        if not (0 <= x < q):
            raise DescriptionError(
                f"Over GF({q}) each matrix entry must be an integer code x with "
                f"0 <= x < {q}, whose base-{q.factor()[0][0]} digits are its "
                "coordinates in the power basis of the field generator.")
        return R.from_integer(int(x))

    return R, decode


def parse_matrix_group(s):
    """Parse ``Mat(d,q):[[...]],[[...]]`` into a GAP matrix group over ``GF(q)``
    (prime power) or ``Z/q`` (otherwise).  See :func:`entry_ring` for how the
    integer entries are interpreted."""
    m = MAT_RE.fullmatch(s.strip())
    if not m:
        raise DescriptionError(
            "Not a valid matrix description; use "
            "Mat(d,q):[[..],[..]],[[..],[..]].")
    d = int(m.group(1))
    q = int(m.group(2))
    body = m.group(3).strip()
    if not (1 <= d <= MAX_MATRIX_DIM):
        raise DescriptionError(f"Matrix dimension must be between 1 and {MAX_MATRIX_DIM}.")
    if not (2 <= q <= MAX_MATRIX_Q):
        raise DescriptionError(f"Modulus q must be between 2 and {MAX_MATRIX_Q}.")
    R, decode = entry_ring(q)
    try:
        data = ast.literal_eval(body)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        raise DescriptionError(
            "Matrix generators must be a comma-separated list of integer matrices.")
    if isinstance(data, tuple):
        data = list(data)
    if not isinstance(data, list) or not data:
        raise DescriptionError("Provide at least one matrix generator.")
    # Allow a single matrix given without an enclosing list.
    if data and all(isinstance(row, (list, tuple)) and row
                    and all(isinstance(x, int) for x in row) for row in data):
        data = [data]
    if len(data) > MAX_GENS:
        raise DescriptionError(f"At most {MAX_GENS} generators are allowed.")
    mats = []
    for M in data:
        if (not isinstance(M, (list, tuple)) or len(M) != d
                or any(not isinstance(row, (list, tuple)) or len(row) != d for row in M)):
            raise DescriptionError(f"Each generator must be a {d} x {d} matrix.")
        flat = [x for row in M for x in row]
        if any(not isinstance(x, int) or abs(x) > MAX_MATRIX_ENTRY for x in flat):
            raise DescriptionError(
                f"Matrix entries must be integers with absolute value at most {MAX_MATRIX_ENTRY}.")
        MM = matrix(R, d, [decode(x) for x in flat])
        if not MM.is_invertible():
            raise DescriptionError("Matrix generators must be invertible.")
        mats.append(MM)
    try:
        return libgap.Group([libgap(M) for M in mats])
    except (GAPError, ValueError, RuntimeError) as err:
        raise DescriptionError(f"Could not build a matrix group: {err}")


def _parse(desc):
    """Dispatch on the shape of ``desc`` and return ``(GAP group, kind)``."""
    if desc.startswith("Mat("):
        return parse_matrix_group(desc), "matrix"
    if PC_RE.fullmatch(desc.replace(" ", "")):
        return parse_pc_group(desc), "pc"
    if desc.startswith("("):
        return parse_permutation_group(desc), "permutation"
    raise DescriptionError(
        "Unrecognized description.  Enter permutation generators like "
        "(1,2,3)(4,5),(1,2), a PC code like 8PC4, or matrices like "
        "Mat(2,3):[[1,1],[0,1]],[[0,1],[1,0]].")


# ---------------------------------------------------------------------------
# Top-level identification
# ---------------------------------------------------------------------------

def describe_formats():
    """Short human-readable list of accepted input formats (for the templates)."""
    return [
        ("Permutations", "comma-separated generators in cycle notation",
         "(1,2,3)(4,5),(1,2)"),
        ("PC code", "the order and small-group PC code, as order PC code",
         "8PC4"),
        ("Matrices", "generators over GF(q) for q a prime power, or over Z/q "
         "otherwise, as Mat(dimension,q) followed by the matrices",
         "Mat(2,3):[[1,1],[0,1]],[[0,1],[1,0]]"),
        ("Matrices over GF(p^e)", "an entry over a field with q = p^e elements is "
         "an integer code 0 ≤ x < q whose base-p digits, least significant "
         "first, are its coordinates in the basis 1, a, ..., a^(e-1) of the "
         "Conway generator a (so over GF(4) the code 2 is a itself)",
         "Mat(1,4):[[2]]"),
    ]


def _candidate(label, present, live=False):
    """One group sharing the computed hash: ``present`` says it has a row in
    ``gps_groups``, ``live`` that GAP can build a page for it anyway."""
    return {"label": label, "present": present, "live": live}


def _lookup(G, N):
    """Given a parsed GAP group ``G`` of order ``N``, return a result dict."""
    N = ZZ(N)
    # (a) GAP can identify the group AND Magma agrees on the numbering: a proof.
    if libgap.IdGroupsAvailable(N) and (N <= 2000 or magma_identifiable(N)):
        n, i = libgap.IdGroup(G)
        return {
            "status": "redirect",
            "label": f"{int(n)}.{int(i)}",
            "proof": True,
            "proof_reason": "GAP identified this group up to isomorphism.",
        }
    h = group_hash(G)
    res = resolve_order_hash(N, h)
    # (b) A complete-table order: gps_smallhash lists every group of this order
    # with this hash, so a unique match is a proof of isomorphism and a
    # multiple match pins the group to an explicit hash-collision cluster.
    if res.complete:
        present = set(res.in_lmfdb())
        # Groups of most of these orders have a homepage computed by GAP even
        # when they are not in the database; those of order 6561 do not.
        live = live_pages_available(N)
        if len(res.labels) == 1 and (res.labels[0] in present or live):
            return {
                "status": "redirect",
                "label": res.labels[0],
                "hash": h,
                "proof": True,
                "proof_reason": ("The hash tables are complete for order "
                                 f"{int(N)} and exactly one group has this hash."),
            }
        if not res.labels:
            # The hash was computed from an actual group of this order, so the
            # complete table has to contain it: this is a data problem, not a
            # statement about the input.
            return {
                "status": "list",
                "hash": h,
                "complete": True,
                "candidates": [],
                "data_error": True,
                "note": (f"The complete hash table for order {int(N)} did not contain "
                         "the computed hash.  The table may be unavailable or "
                         "inconsistent; please report this."),
            }
        return {
            "status": "list",
            "hash": h,
            "complete": True,
            "candidates": [_candidate(lab, lab in present, live) for lab in res.labels],
            "caveat": (f"The hash tables are complete for order {int(N)}, so this "
                       "group is isomorphic to exactly one of the following "
                       f"{len(res.labels)} groups (they share a hash collision)."),
        }
    # (c) Any other order: the hash matches in gps_groups.  A hash match does
    # NOT prove isomorphism (e.g. 6561.23 and 6561.25 collide).
    if res.labels:
        return {
            "status": "list",
            "hash": h,
            "complete": False,
            "candidates": [_candidate(lab, True) for lab in res.labels],
            "caveat": ("Equal order and hash does not prove isomorphism, so your "
                       "group is isomorphic to one of the following, or to a group "
                       "not in the database with the same hash."),
        }
    # No match: distinguish "no such order" from "no hash match".
    total = db.gps_groups.count({"order": int(N)})
    if total == 0:
        return {
            "status": "list",
            "hash": h,
            "complete": False,
            "candidates": [],
            "note": f"The LMFDB contains no groups of order {int(N)}.",
        }
    note = (f"No group of order {int(N)} in the LMFDB has this hash "
            f"(there are {total} such groups).")
    # Some orders (e.g. 2028) have rows whose hash was never computed.
    if db.gps_groups.lucky({"order": int(N), "hash": None}) is not None:
        note += " Some groups of this order have no computed hash yet."
    return {
        "status": "list",
        "hash": h,
        "complete": False,
        "candidates": [],
        "note": note,
    }


_gap_ready = False


def prepare_gap():
    """Force GAP's one-time start-up before any alarm is set.

    Starting GAP and loading the libraries behind Sage's conversions takes
    about twenty seconds in a fresh worker, and an alarm that fires during that
    start-up leaves ``libgap`` unusable for the rest of the process (every
    later GAP call returns ``Aborted``).  The work is the same whatever the
    user typed, so it belongs outside the guard; interrupting GAP once it is
    running is safe, as the timeouts below rely on.
    """
    global _gap_ready
    if not _gap_ready:
        PermutationGroup([[(1, 2)]])._libgap_().Order()
        _gap_ready = True


def identify_group(desc):
    """Identify the group described by ``desc``.

    Returns a result dict with a ``status`` key, one of:

    * ``"empty"``    -- no input; render the form only;
    * ``"error"``    -- bad input, timeout, or an uncomputable hash;
    * ``"redirect"`` -- ``label`` identifies the group (``proof`` says whether
      up to isomorphism);
    * ``"list"``     -- ``candidates`` (possibly empty) share the group's
      (order, hash); ``complete`` says whether the set is a proven cluster.
    """
    base = {"input": desc or "", "kind": None, "order": None, "order_factored": None}
    if desc is None or not desc.strip():
        return {**base, "status": "empty"}
    desc = desc.strip()
    base["input"] = desc
    if len(desc) > MAX_INPUT:
        return {**base, "status": "error",
                "error": f"Input too long (at most {MAX_INPUT} characters)."}

    # Parsing already builds Sage and GAP objects (a permutation group, a PC
    # group from its code, matrices over a finite ring), so it runs under the
    # same alarm as the order computation rather than ahead of it.
    prepare_gap()
    try:
        alarm(ORDER_TIMEOUT)
        G, kind = _parse(desc)
        N = ZZ(G.Order())
    except DescriptionError as err:
        return {**base, "status": "error", "error": str(err)}
    except AlarmInterrupt:
        return {**base, "status": "error",
                "error": ("Timed out constructing the group and computing its order; "
                          "try a smaller group.")}
    except (GAPError, ValueError, RuntimeError, TypeError) as err:
        return {**base, "status": "error",
                "error": f"Could not construct the group or compute its order: {err}"}
    finally:
        cancel_alarm()

    base["kind"] = kind
    base["order"] = int(N)
    # Nothing that scales with the order (factoring included) before the cap.
    if N > ORDER_CAP:
        return {**base, "status": "error",
                "error": (f"Order {int(N)} exceeds the supported bound of "
                          f"{ORDER_CAP}; only smaller groups can be identified."),
                "show_order_link": False}
    base["order_factored"] = latex(N.factor())

    # Hash / identification under a longer timeout.
    try:
        alarm(HASH_TIMEOUT)
        result = _lookup(G, N)
    except AlarmInterrupt:
        return {**base, "status": "error",
                "error": "Timed out computing the group hash; try a smaller group.",
                "show_order_link": True}
    except HashUncomputable as err:
        return {**base, "status": "error",
                "error": (f"This group's hash requires identification data for order "
                          f"{err} that is not available server-side, so it cannot be "
                          "computed here."),
                "show_order_link": True}
    except (GAPError, ValueError, RuntimeError) as err:
        return {**base, "status": "error",
                "error": f"Could not compute with this group: {err}",
                "show_order_link": True}
    finally:
        cancel_alarm()

    result.update(base)
    return result
