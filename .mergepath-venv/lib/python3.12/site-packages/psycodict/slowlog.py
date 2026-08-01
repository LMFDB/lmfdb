# -*- coding: utf-8 -*-
"""
Tools for analyzing the slow-query logs that psycodict writes.

When a query takes longer than the ``slowcutoff`` configured in the
``[logging]`` section, ``PostgresBase._execute`` appends lines like the
following to the file configured as ``slowlogfile``::

    2026-07-20 20:19:14,940 - SELECT "label" FROM "curves" WHERE "n" = 5 ORDER BY "n" ran in \\x1b[91m 0.35s \\x1b[0m
    2026-07-20 20:19:14,940 - Replicate with db.curves.analyze({'n': 5}, ['label'], None, 0)

The timing is wrapped in ANSI color escapes, the ``Replicate with`` hint
line follows the query it describes, and versions of this code from before
2019 wrote ``... ran in 0.35s`` without the color escapes.  A query whose
inlined values contain newlines spans several physical lines.  Search
iterators log a third shape (normally only to the console, but captured
console output is worth parsing too)::

    Search iterator for curves {'n': 5} required a total of \\x1b[91m0.35s\\x1b[0m

The functions here parse such files, group the queries by *shape* (the
query with all constants removed), and produce a report aimed at two
questions: would raising ``slowcutoff`` shrink the log substantially, and
which queries might benefit from an index?

Typical usage::

    from psycodict.slowlog import show_slow_report
    show_slow_report("slow_queries.log", db=db)  # db optional

or equivalently ``db.show_slow_report("slow_queries.log")``.  Nothing here
writes to the database: when ``db`` is provided, the report reads the
indexes recorded in ``meta_indexes`` (through ``table.list_indexes()``) to
check whether the columns constrained by slow queries are covered.
"""

import re
from collections import defaultdict
from datetime import datetime
from heapq import heapify, heappop, heappush
from math import ceil, floor, log10

_TIMESTAMP_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - ")
_ANSI_RE = re.compile("\x1b\\[[0-9;]*m")
_NUMBER = r"(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
_RAN_IN_RE = re.compile(r"\s+ran in\s+(" + _NUMBER + r")s\s*$")
_ITERATOR_RE = re.compile(
    r"^Search iterator for (\S+)\s+(.*?)\s*required a total of\s*(" + _NUMBER + r")s\s*$",
    re.DOTALL,
)
_REPLICATE_RE = re.compile(r"^Replicate with (db\.([A-Za-z0-9_]+)\.[A-Za-z0-9_]+\(.*\))\s*$", re.DOTALL)


def _classify(message):
    """
    Match a logical log message (timestamp prefix removed) against the known
    line shapes.

    OUTPUT:

    - ``None`` if the message matches no known shape (possibly because it is
      the first part of a multi-line message);
    - ``("hint", table, call)`` for a ``Replicate with db.<table>...`` line;
    - ``("query", duration, sql)`` for a ``... ran in <t>s`` line;
    - ``("iterator", duration, querydict, table)`` for a search iterator line.
    """
    message = _ANSI_RE.sub("", message)
    m = _REPLICATE_RE.match(message)
    if m:
        return ("hint", m.group(2), m.group(1))
    m = _RAN_IN_RE.search(message)
    if m:
        return ("query", float(m.group(1)), message[:m.start()])
    m = _ITERATOR_RE.match(message)
    if m:
        return ("iterator", float(m.group(3)), m.group(2), m.group(1))
    return None


def _make_record(timestamp, nlines, kind):
    """
    Build a parsed-record dictionary from a buffered message.
    """
    if timestamp is not None:
        try:
            timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            timestamp = None
    rec = {
        "timestamp": timestamp,
        "duration": kind[1],
        "query": kind[2],
        "kind": kind[0],
        "table": kind[3] if kind[0] == "iterator" else None,
        "replicate": None,
        "lines": nlines,
    }
    return rec


def parse_slow_log(logfile, stats=None):
    """
    Iterate over the records in a slow-query log file.

    INPUT:

    - ``logfile`` -- the filename of a slow-query log (as configured by the
      ``slowlogfile`` logging option), or an open file object
    - ``stats`` -- an optional dictionary, updated in place with the keys
      ``lines`` (physical lines read) and ``unparsed`` (lines that were not
      part of any recognized record)

    OUTPUT:

    An iterator of dictionaries, one per logged query, with keys:

    - ``timestamp`` -- a datetime from the logging prefix (None if absent)
    - ``duration`` -- the logged runtime in seconds, as a float
    - ``query`` -- the SQL that was logged; for search iterator records,
      the query dictionary as a string
    - ``kind`` -- ``"query"`` for ordinary statements, ``"iterator"`` for
      ``Search iterator`` records
    - ``table`` -- the table the query was issued against, when the log
      provides it (from the adjacent ``Replicate with`` hint line, or from
      the search iterator line); otherwise None.  A hint is attached only
      when its table appears in the query, since several processes
      appending to one log can interleave their lines.
    - ``replicate`` -- the ``db.<table>.analyze(...)`` call from the hint
      line when present, for replaying the query
    - ``lines`` -- the number of physical log lines this record occupies,
      including its hint line and any continuation lines

    Multi-line SQL (inlined values containing newlines) is reassembled.
    Unrecognized lines are skipped and counted in ``stats``, since a log
    that has accumulated for years contains lines in formats no longer in
    use.
    """
    if stats is None:
        stats = {}
    stats["lines"] = 0
    stats["unparsed"] = 0
    if hasattr(logfile, "read"):
        for rec in _parse_stream(logfile, stats):
            yield rec
    else:
        with open(logfile, "r", errors="replace") as F:
            for rec in _parse_stream(F, stats):
                yield rec


def _parse_stream(F, stats):
    """
    The implementation of ``parse_slow_log`` on an open file object.

    Physical lines are grouped into logical messages: a line with a
    timestamp prefix starts a new message, and a line without one continues
    the previous message when that message is not yet complete.  A parsed
    query record is held back until the next message so that a following
    ``Replicate with`` hint can be attached to it.
    """
    pending = None  # a query record awaiting a possible hint line
    buf = None  # [timestamp, message, nlines, classification]
    lines = iter(F)
    while True:
        raw = next(lines, None)
        if raw is None:
            new = None
        else:
            stats["lines"] += 1
            line = raw.rstrip("\r\n")
            tm = _TIMESTAMP_RE.match(line)
            if tm is None and buf is not None and buf[3] is None:
                # continuation of a multi-line message
                buf[1] += "\n" + line
                buf[2] += 1
                buf[3] = _classify(buf[1])
                continue
            if tm is None:
                new = [None, line, 1, _classify(line)]
            else:
                message = line[tm.end():]
                new = [tm.group(1), message, 1, _classify(message)]
        if buf is not None:
            kind = buf[3]
            if kind is None:
                stats["unparsed"] += buf[2]
            elif kind[0] == "hint":
                # Attach the hint to the preceding query, but only if its
                # table appears there: several processes appending to one log
                # can interleave a hint with another process' query.
                if (
                    pending is not None
                    and pending["kind"] == "query"
                    and re.search(r"\b%s\b" % re.escape(kind[1]), pending["query"])
                ):
                    pending["table"] = kind[1]
                    pending["replicate"] = kind[2]
                    pending["lines"] += buf[2]
                    yield pending
                    pending = None
                else:
                    # a hint with no query to attach to
                    stats["unparsed"] += buf[2]
            else:
                if pending is not None:
                    yield pending
                pending = _make_record(buf[0], buf[2], kind)
        if raw is None:
            break
        buf = new
    if pending is not None:
        yield pending


##################################################################
# Query normalization                                            #
##################################################################

_NUMBER_RE = re.compile(_NUMBER)
_ARRAY_RE = re.compile(r"\bARRAY\[")
_ARRAY_CONTENT_RE = re.compile(r"^[?,\s\[\]]*$")
_PLACEHOLDER_LIST_RE = re.compile(r"\(\s*\?\s*(?:,\s*\?\s*)+\)")
_PLACEHOLDER_BRACKET_RE = re.compile(r"\[\s*\?\s*(?:,\s*\?\s*)+\]")
_DUP_CLAUSE_RE = re.compile(r"(?<![\w\"'?])((?:NOT )?[^()]{1,400}?) (OR|AND) \1(?![\w\"'?])")
_JSONB_PATH_OPS = ("->", "->>", "#>", "#>>")


def normalize_query(query):
    """
    Normalize an SQL query (or a query dictionary rendered as a string) to
    its *shape*: literal values are replaced by ``?`` so that queries
    differing only in their constants compare equal.

    - numbers, quoted strings and boolean literals become ``?`` (string
      literals and numbers directly after the jsonb path operators ``->``,
      ``->>``, ``#>``, ``#>>`` are kept, since they select which field or
      array position is queried rather than which value)
    - the contents of ``ARRAY[...]`` literals collapse to ``ARRAY[?]``
    - comma-separated lists of replaced values, as in ``IN (1, 2, 3)``,
      collapse to ``(?)``
    - a clause repeated with ``OR`` (or ``AND``), as produced for example
      by ``$in`` on a jsonb column, collapses to a single copy
    - runs of whitespace (including newlines) become a single space

    Identifiers are left alone, even when they contain digits.

    EXAMPLES::

        >>> from psycodict.slowlog import normalize_query
        >>> normalize_query("SELECT \\"a\\" FROM \\"t\\" WHERE \\"n\\" = 5 AND \\"s\\" = 'x1' LIMIT 4")
        'SELECT "a" FROM "t" WHERE "n" = ? AND "s" = ? LIMIT ?'
    """
    out = []
    tail = ""  # the last few non-space characters emitted
    i = 0
    n = len(query)
    while i < n:
        c = query[i]
        if c == "'":
            # a string literal, with '' escapes
            j = i + 1
            while j < n:
                if query[j] == "'":
                    if j + 1 < n and query[j + 1] == "'":
                        j += 2
                        continue
                    break
                j += 1
            if tail.endswith(_JSONB_PATH_OPS):
                # part of the query shape, not a value
                out.append(query[i:j + 1])
                tail = (tail + query[i:j + 1])[-4:]
            else:
                out.append("?")
                tail = (tail + "?")[-4:]
            i = j + 1
        elif c == '"':
            # a quoted identifier, with "" escapes
            j = i + 1
            while j < n:
                if query[j] == '"':
                    if j + 1 < n and query[j + 1] == '"':
                        j += 2
                        continue
                    break
                j += 1
            out.append(query[i:j + 1])
            tail = (tail + query[i:j + 1])[-4:]
            i = j + 1
        elif c.isalpha() or c == "_":
            j = i + 1
            while j < n and (query[j].isalnum() or query[j] == "_"):
                j += 1
            word = query[i:j]
            if word in ("E", "e") and j < n and query[j] == "'":
                # an E'...' escaped string: skip the prefix, the literal
                # itself is handled (and replaced) on the next pass
                i = j
                continue
            if word in ("true", "false", "TRUE", "FALSE"):
                out.append("?")
                tail = (tail + "?")[-4:]
            else:
                out.append(word)
                tail = (tail + word)[-4:]
            i = j
        elif c.isdigit() or (c in ".-" and i + 1 < n and query[i + 1].isdigit()):
            if c == "-" and (tail[-1:].isalnum() or tail[-1:] in ")?\"'"):
                # binary minus, not a sign
                out.append(c)
                tail = (tail + c)[-4:]
                i += 1
                continue
            j = i + (1 if c == "-" else 0)
            m = _NUMBER_RE.match(query, j)
            if m is None:
                # "." or "-" not actually starting a number
                out.append(c)
                tail = (tail + c)[-4:]
                i += 1
                continue
            if tail.endswith(_JSONB_PATH_OPS):
                # an array position in a jsonb path: part of the query
                # shape, not a value
                number = query[i:m.end()]
                out.append(number)
                tail = (tail + number)[-4:]
            else:
                out.append("?")
                tail = (tail + "?")[-4:]
            i = m.end()
        elif c.isspace():
            if out and not out[-1].endswith(" "):
                out.append(" ")
            i += 1
        else:
            out.append(c)
            tail = (tail + c)[-4:]
            i += 1
    s = "".join(out).strip()
    s = _collapse_arrays(s)
    s = _PLACEHOLDER_LIST_RE.sub("(?)", s)
    s = _collapse_repeats(s)
    return s


def _collapse_arrays(s):
    """
    Replace the contents of ``ARRAY[...]`` literals (whose values have
    already been replaced by ``?``) with a single ``?``.
    """
    out = []
    pos = 0
    for m in _ARRAY_RE.finditer(s):
        if m.start() < pos:
            continue
        # find the matching closing bracket
        depth = 0
        for j in range(m.end() - 1, len(s)):
            if s[j] == "[":
                depth += 1
            elif s[j] == "]":
                depth -= 1
                if depth == 0:
                    break
        else:
            break  # unbalanced; leave the rest alone
        content = s[m.end():j]
        if _ARRAY_CONTENT_RE.match(content):
            out.append(s[pos:m.end()])
            out.append("?")
            pos = j
    out.append(s[pos:])
    return "".join(out)


def _collapse_repeats(s):
    """
    Collapse a clause repeated with ``OR`` or ``AND`` (with identical text
    after normalization) into a single copy, so that e.g. the expansion of
    ``$in`` on a jsonb column groups independently of the list length.
    """
    for _ in range(30):
        new = _DUP_CLAUSE_RE.sub(r"\1", s)
        if new == s:
            break
        s = new
    return s


def normalize_dict_query(query):
    """
    Normalize a query dictionary rendered as a string (the Python repr that
    ``Search iterator`` log lines carry) to its shape.

    In a query dictionary the keys -- column names and ``$``-operators like
    ``$gte`` -- describe the structure of the query, and only the values
    are data, so :func:`normalize_query` (which treats every quoted string
    as a literal value) would collapse structurally different queries such
    as ``{'n': {'$gte': 5}}`` and ``{'label': {'$lte': 'z'}}`` to the same
    shape.  Here a quoted string or a number is kept exactly when it is
    followed by ``:``, i.e. when it is a dictionary key:

    - values (numbers, quoted strings, ``True``/``False``/``None``) become
      ``?``
    - lists and tuples of replaced values collapse: ``[1, 2, 3]`` becomes
      ``[?]``, so ``$in`` queries group independently of the list length
    - runs of whitespace (including newlines) become a single space

    EXAMPLES::

        >>> from psycodict.slowlog import normalize_dict_query
        >>> normalize_dict_query("{'n': {'$gte': 5}, 'label': 'a'}")
        "{'n': {'$gte': ?}, 'label': ?}"
    """
    out = []
    i = 0
    n = len(query)

    def is_key(j):
        # whether the literal ending just before position j is a dict key,
        # i.e. is followed by a colon
        while j < n and query[j].isspace():
            j += 1
        return j < n and query[j] == ":"

    while i < n:
        c = query[i]
        if c in "'\"":
            # a Python string literal, with backslash escapes
            j = i + 1
            while j < n:
                if query[j] == "\\":
                    j += 2
                    continue
                if query[j] == c:
                    break
                j += 1
            if is_key(j + 1):
                out.append(query[i:j + 1])
            else:
                out.append("?")
            i = j + 1
        elif c.isalpha() or c == "_":
            j = i + 1
            while j < n and (query[j].isalnum() or query[j] == "_"):
                j += 1
            word = query[i:j]
            if word in ("True", "False", "None") and not is_key(j):
                out.append("?")
            else:
                out.append(word)
            i = j
        elif c.isdigit() or (c in ".-" and i + 1 < n and query[i + 1].isdigit()):
            m = _NUMBER_RE.match(query, i + (1 if c == "-" else 0))
            if m is None:
                out.append(c)
                i += 1
                continue
            if is_key(m.end()):
                out.append(query[i:m.end()])
            else:
                out.append("?")
            i = m.end()
        elif c.isspace():
            if out and not out[-1].endswith(" "):
                out.append(" ")
            i += 1
        else:
            out.append(c)
            i += 1
    s = "".join(out).strip()
    s = _PLACEHOLDER_BRACKET_RE.sub("[?]", s)
    s = _PLACEHOLDER_LIST_RE.sub("(?)", s)
    return s


##################################################################
# Aggregation and reporting                                      #
##################################################################

# Candidate values for raising slowcutoff, in seconds
_LADDER = (0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

_TABLES_RE = re.compile(r'\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:"([A-Za-z_][A-Za-z0-9_]*)"|([A-Za-z_][A-Za-z0-9_]*))')
_NONTABLE_WORDS = frozenset(["SELECT", "STDIN", "STDOUT", "UNNEST"])


def _tables_in_sql(sql):
    """
    The table names appearing after FROM/JOIN/INTO/UPDATE in an SQL string.
    This is a heuristic (it does not parse SQL), but psycodict's generated
    queries quote their table names, making them easy to find.
    """
    found = set()
    for m in _TABLES_RE.finditer(sql):
        name = m.group(1) or m.group(2)
        if name.upper() not in _NONTABLE_WORDS:
            found.add(name)
    return found


def _bucket(duration):
    """
    Round a duration down to 3 significant digits, for the histogram used
    to compute percentiles and threshold counts with bounded memory.
    """
    if duration <= 0:
        return 0.0
    scale = 10.0 ** (floor(log10(duration)) - 2)
    return floor(duration / scale) * scale


def _percentile(buckets, total, p):
    """
    The ``p``-th percentile (nearest-rank) of a duration histogram given as
    a sorted list of ``(bucket, count)`` pairs with ``total`` entries.
    """
    if total == 0:
        return None
    rank = max(1, int(ceil(p / 100.0 * total)))
    cumulative = 0
    for value, count in buckets:
        cumulative += count
        if cumulative >= rank:
            return value
    return buckets[-1][0]


class _LeaderPool:
    """
    Tracks the (up to) ``cap`` shapes with the largest key seen so far, where
    each shape's key only ever increases (total time or max duration here).
    ``members`` is the current set; ``cap=None`` keeps every shape.

    Implemented as a lazy-deletion min-heap by key: a member's key growing
    pushes a fresh entry, and stale entries (superseded, or for an evicted
    shape) are discarded when they surface at the top or during ``compact``.
    """

    def __init__(self, cap):
        self.cap = cap
        self.members = set()
        self._heap = []       # (key, seq, shape); may hold stale entries
        self._live = {}       # shape -> seq of its current (live) heap entry
        self._seq = 0

    def _push(self, shape, key):
        self._seq += 1
        self._live[shape] = self._seq
        heappush(self._heap, (key, self._seq, shape))

    def _purge_stale(self):
        while self._heap:
            _, seq, shape = self._heap[0]
            if shape in self.members and self._live.get(shape) == seq:
                break
            heappop(self._heap)

    def offer(self, shape, key):
        """
        Record that ``shape`` now has this key; return the shape evicted to
        make room, or None.  ``members`` is updated in place.
        """
        if self.cap is None:
            self.members.add(shape)
            return None
        if shape in self.members:
            self._push(shape, key)
            return None
        if len(self.members) < self.cap:
            self.members.add(shape)
            self._push(shape, key)
            return None
        self._purge_stale()
        if self._heap and key >= self._heap[0][0]:
            evicted = heappop(self._heap)[2]
            self.members.discard(evicted)
            self._live.pop(evicted, None)
            self.members.add(shape)
            self._push(shape, key)
            return evicted
        return None

    def compact(self):
        # Keep the heap O(cap) by dropping accumulated stale entries.
        if self.cap is not None and len(self._heap) > 4 * self.cap + 64:
            self._heap = [
                (key, seq, shape) for (key, seq, shape) in self._heap
                if shape in self.members and self._live.get(shape) == seq
            ]
            heapify(self._heap)


def slow_query_report(logfile, top=20, cutoff=None, db=None):
    """
    Analyze a slow-query log file, grouping queries by shape.

    INPUT:

    - ``logfile`` -- the filename of a slow-query log (as configured by the
      ``slowlogfile`` logging option), or an open file object
    - ``top`` -- the number of query shapes to include in each ranking (there
      are two: by total time and by mean time)
    - ``cutoff`` -- only consider queries at least this slow (in seconds).
      This simulates raising ``slowcutoff``: the report shows what the log
      would have contained with that threshold.
    - ``db`` -- an optional ``PostgresDatabase``.  When provided, the
      suggestions check the columns constrained by each query shape against
      the indexes recorded in ``meta_indexes`` (via ``list_indexes``) for
      the search tables involved, and suggest ``create_index`` calls for
      constrained columns that no existing index leads with.

    OUTPUT:

    A dictionary with keys:

    - ``logfile``, ``cutoff`` -- the corresponding inputs
    - ``lines`` -- the number of physical lines in the file
    - ``unparsed`` -- lines that were not part of any recognized record
    - ``records`` -- the number of parsed query records
    - ``skipped`` -- records below ``cutoff`` (0 when no cutoff is given);
      the rest of the report describes the ``records - skipped`` others
    - ``total_time`` -- their summed duration in seconds
    - ``percentiles`` -- a dictionary with keys ``p50``, ``p90``, ``p99``
      and ``max``.  The percentiles are computed from a histogram with 3
      significant digits, so they are lower bounds accurate to about 1%;
      the max is exact.
    - ``thresholds`` -- a list of dictionaries with keys ``cutoff``,
      ``records``, ``lines`` and ``percent``: raising ``slowcutoff`` to
      that value would have logged that many records, occupying that many
      physical lines, i.e. that percentage of the current line volume.
      The candidate cutoffs mix a fixed ladder with the observed
      percentiles.
    - ``shapes`` -- a list of dictionaries, one per query shape, sorted by
      total time, with keys ``shape``, ``kind``, ``count``, ``total``,
      ``mean``, ``max``, ``tables``, ``example`` (the slowest query
      retained for this shape; see below), ``replicate`` (the hint-line
      call of that same example record, if it had one) and ``suggestions``
      (a list of strings; see the module documentation).
    - ``shapes_by_mean`` -- the same kind of list, the top shapes ordered by
      mean time instead of total time (the two lists overlap and share their
      dictionaries).

    Memory use: the per-shape numeric aggregates (``count``, ``total``,
    ``max``, ``tables`` and the shape string itself) are exact and are kept
    for every distinct shape, so that ``total_time``, ``percentiles``,
    ``thresholds`` and the reported aggregates do not depend on ``top``.
    This dictionary grows with the number of DISTINCT shapes -- bounded in
    practice by the variety of queries the application issues, not by the
    length of the log.  The large per-shape strings (``example`` and
    ``replicate``), by contrast, are retained only for a bounded candidate
    set: the current leaders by total time (up to ``4 * top`` shapes)
    together with the current leaders by max duration (up to another
    ``4 * top``), so that both the by-total and the by-mean rankings have
    reproducible examples.  When a shape drops out of both pools its example
    is discarded, and if it later climbs back the next record of that shape
    refills it.  The example of a reported shape is therefore the slowest of
    the records that arrived while the shape was retained -- normally, but
    not always, its globally slowest record.  Every reported shape has an
    example, and
    with ``top=None`` all shapes retain theirs.
    """
    stats = {}
    shapes = {}
    histogram = defaultdict(lambda: [0, 0])  # bucket -> [records, lines]
    records = skipped = considered_lines = 0
    total_time = 0.0
    max_duration = None
    # Example retention (see the docstring): full example/replicate strings
    # are kept only for a bounded candidate set -- the ``cap`` current leaders
    # by total time (for the by-total ranking) UNION the ``cap`` leaders by
    # max duration (so the rare, very slow shapes that top the by-mean ranking
    # are reproducible too).  A shape keeps its example while it is in either
    # pool.
    cap = None if top is None else 4 * top
    pool_total = _LeaderPool(cap)
    pool_max = _LeaderPool(cap)
    for rec in parse_slow_log(logfile, stats=stats):
        records += 1
        duration = rec["duration"]
        if cutoff is not None and duration < cutoff:
            skipped += 1
            continue
        total_time += duration
        considered_lines += rec["lines"]
        if max_duration is None or duration > max_duration:
            max_duration = duration
        entry = histogram[_bucket(duration)]
        entry[0] += 1
        entry[1] += rec["lines"]
        if rec["kind"] == "iterator":
            shape = "Search iterator for %s %s" % (rec["table"], normalize_dict_query(rec["query"]))
        else:
            shape = normalize_query(rec["query"])
        data = shapes.get(shape)
        if data is None:
            tables = _tables_in_sql(shape) if rec["kind"] == "query" else set()
            data = shapes[shape] = {
                "shape": shape,
                "kind": rec["kind"],
                "count": 0,
                "total": 0.0,
                "max": 0.0,
                "tables": tables,
                "example": None,
                "replicate": None,
            }
        data["count"] += 1
        data["total"] += duration
        if rec["table"]:
            data["tables"].add(rec["table"])
        if duration > data["max"]:
            data["max"] = duration
        # Offer the shape to both retention pools (by total, by max); a shape
        # keeps its example while it is a member of either.  A shape evicted
        # from one pool loses its example only if it is not in the other.
        evicted_total = pool_total.offer(shape, data["total"])
        evicted_max = pool_max.offer(shape, data["max"])
        for evicted in (evicted_total, evicted_max):
            if (evicted is not None
                    and evicted not in pool_total.members
                    and evicted not in pool_max.members):
                ev = shapes[evicted]
                ev["example"] = ev["replicate"] = None
                ev.pop("_exdur", None)
        if shape in pool_total.members or shape in pool_max.members:
            # Fill on first admission, and thereafter keep the slowest record
            # (its example and replicate hint always come from one record).
            if "_exdur" not in data or duration >= data["_exdur"]:
                data["example"] = rec["query"]
                data["replicate"] = rec["replicate"]
                data["_exdur"] = duration
        pool_total.compact()
        pool_max.compact()

    considered = records - skipped
    buckets = sorted((value, counts[0]) for value, counts in histogram.items())
    percentiles = {
        "p50": _percentile(buckets, considered, 50),
        "p90": _percentile(buckets, considered, 90),
        "p99": _percentile(buckets, considered, 99),
        "max": max_duration,
    }
    thresholds = []
    if considered:
        candidates = {percentiles["p50"], percentiles["p90"], percentiles["p99"]}
        candidates.update(c for c in _LADDER if c <= max_duration)
        if cutoff is not None:
            candidates = {c for c in candidates if c >= cutoff}
        for c in sorted(candidates):
            kept_records = kept_lines = 0
            for value, counts in histogram.items():
                if value >= c:
                    kept_records += counts[0]
                    kept_lines += counts[1]
            thresholds.append({
                "cutoff": c,
                "records": kept_records,
                "lines": kept_lines,
                "percent": 100.0 * kept_lines / considered_lines,
            })

    # Two rankings of the same per-shape aggregates: by total time (the biggest
    # cumulative cost) and by mean time (the slowest per call, regardless of how
    # often it ran).  Among shapes tied on the sort key, prefer those retaining
    # an example.  Examples are retained for the leaders by total AND by max
    # duration (see the docstring), so the by-mean leaders -- the rare, very
    # slow shapes -- are reproducible too.
    top_shapes = sorted(
        shapes.values(), key=lambda data: (-data["total"], data["example"] is None)
    )[:top]
    top_by_mean = sorted(
        shapes.values(),
        key=lambda data: (-data["total"] / data["count"], data["example"] is None),
    )[:top]
    # Finalize each shape once, even if it appears in both rankings (they share
    # the same underlying dicts, and _suggestions may hit the database).
    finalized = set()
    for data in (*top_shapes, *top_by_mean):
        if data["shape"] in finalized:
            continue
        finalized.add(data["shape"])
        data.pop("_exdur", None)
        data.pop("_seq", None)
        data["mean"] = data["total"] / data["count"]
        data["tables"] = sorted(data["tables"])
        data["suggestions"] = _suggestions(data, db)

    return {
        "logfile": getattr(logfile, "name", logfile),
        "cutoff": cutoff,
        "lines": stats["lines"],
        "unparsed": stats["unparsed"],
        "records": records,
        "skipped": skipped,
        "total_time": total_time,
        "percentiles": percentiles,
        "thresholds": thresholds,
        "shapes": top_shapes,
        "shapes_by_mean": top_by_mean,
    }


##################################################################
# Suggestions                                                    #
##################################################################

# A column reference as it appears in psycodict-generated SQL: a quoted
# identifier, optionally qualified by a quoted table name (as in joined
# queries), optionally followed by jsonb path accesses or array slices
_COLREF = (
    r'(?:"(?P<tbl>[A-Za-z_][A-Za-z0-9_]*)"\.)?'
    r'"(?P<col>[A-Za-z_][A-Za-z0-9_]*)"'
    r'(?P<path>(?:(?:->>?|#>>?)(?:\'(?:[^\']|\'\')*\'|\?|-?[0-9]+)|\[[^\]]*\])*)'
)
_CONSTRAINT_RE = re.compile(_COLREF + r"\s*(?P<op>=\s*ANY\s*\(|@>|<@|&&|<=|>=|!=|<>|=|<|>)")
_LIKE_RE = re.compile(_COLREF + r"\s+(?:NOT\s+)?(?:LIKE|ILIKE)\s+(?P<pat>'(?:[^']|'')*')", re.IGNORECASE)
_ORDER_BY_RE = re.compile(r"\bORDER\s+BY\s+(?P<cols>[^()]*?)(?:\s+LIMIT\b|\s+OFFSET\b|\)|$)", re.IGNORECASE | re.DOTALL)
_SORT_COL_RE = re.compile(r'^(?:"(?P<tbl>[A-Za-z_][A-Za-z0-9_]*)"\.)?"(?P<col>[A-Za-z_][A-Za-z0-9_]*)"')
_WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)


def _abbreviate(text, length=40):
    if len(text) > length:
        return text[:length] + "..."
    return text


def _constrained_columns(example):
    """
    Extract the constrained columns of a query, from its text.

    INPUT:

    - ``example`` -- an SQL query as logged (with its literal values)

    OUTPUT:

    A dictionary with keys ``equality``, ``range``, ``containment`` (the
    array/jsonb operators ``@>``, ``<@``, ``&&``) and ``order`` (the
    columns of the outermost ORDER BY), each a list of ``(table, column)``
    pairs in order of first appearance, where ``table`` is the explicit
    qualifier of a ``"tbl"."col"`` reference (as in joined queries) or
    None; and keys ``path`` (equality on a path inside a jsonb column, a
    list of column names) and ``like`` (a list of (column, pattern)
    pairs).  Only quoted column names are recognized, which is how
    psycodict renders columns; the parsing is heuristic and makes no
    attempt to understand subqueries.
    """
    found = {"equality": [], "range": [], "containment": [], "path": [], "like": [], "order": []}

    def add(kind, item):
        if item not in found[kind]:
            found[kind].append(item)

    m = _WHERE_RE.search(example)
    if m:
        where = example[m.end():]
        tail = _ORDER_BY_RE.search(where)
        if tail:
            where = where[:tail.start()]
        for m in _CONSTRAINT_RE.finditer(where):
            tbl, col, path, op = m.group("tbl"), m.group("col"), m.group("path"), m.group("op")
            op = op.rstrip()
            if op.startswith("=") and op.endswith("("):
                op = "ANY"
            if op in ("!=", "<>"):
                continue  # inequality does not benefit from an index
            if path:
                # a jsonb path or an array slice: a plain index on the
                # column does not support these directly
                if ("->" in path or "#>" in path) and op in ("=", "ANY"):
                    add("path", col)
                continue
            if op in ("=", "ANY"):
                add("equality", (tbl, col))
            elif op in ("<", "<=", ">", ">="):
                add("range", (tbl, col))
            else:  # @>, <@, &&
                add("containment", (tbl, col))
        for m in _LIKE_RE.finditer(where):
            found["like"].append((m.group("col"), m.group("pat").strip("'")))
    m = _ORDER_BY_RE.search(example)
    if m:
        for piece in m.group("cols").split(","):
            cm = _SORT_COL_RE.match(piece.strip())
            if cm:
                add("order", (cm.group("tbl"), cm.group("col")))
    return found


def _leading_index_columns(db, tables):
    """
    For each of the given tables known to ``db``, the set of columns that
    some index leads with, grouped by index type.

    OUTPUT:

    A dictionary ``{table: {index_type: set of first columns}}``, with only
    the tables present in ``db.tablenames`` as keys.
    """
    leaders = {}
    for tname in tables:
        if tname in db.tablenames:
            per_type = defaultdict(set)
            for info in db[tname].list_indexes().values():
                columns = info.get("columns") or []
                if columns:
                    per_type[info.get("type") or "btree"].add(columns[0])
            leaders[tname] = per_type
    return leaders


def _render_col(tbl, col):
    """
    Render a possibly qualified column reference for a suggestion message.
    """
    if tbl:
        return '"%s"."%s"' % (tbl, col)
    return '"%s"' % col


def _suggestions(data, db):
    """
    Heuristic suggestions for one query shape; see ``slow_query_report``.

    Each suggestion states what was observed in the query text and what to
    try.  With ``db`` provided, equality/range/containment observations are
    checked against the indexes recorded in ``meta_indexes`` and reported
    only when no index leads with the constrained column.  A qualified
    reference (``"tbl"."col"``, as in joined queries) is resolved against
    exactly that table; an unqualified column is looked up in all the
    referenced tables, and when several of them have a column of that name
    the suggestion lists each candidate rather than silently picking one.
    """
    if data["kind"] != "query" or not data["example"]:
        return []
    example = data["example"]
    found = _constrained_columns(example)
    suggestions = []

    if db is not None:
        referenced = set(data["tables"])
        for kind in ("equality", "range", "containment", "order"):
            referenced.update(tbl for tbl, _ in found[kind] if tbl)
        checked = _leading_index_columns(db, sorted(referenced))

        def leaders(tname, types=None):
            per_type = checked.get(tname, {})
            cols = set()
            for typ, first in per_type.items():
                if types is None or typ in types:
                    cols |= first
            return cols

        def candidate_tables(tbl, col):
            # the tables the constrained column could belong to: exactly
            # the qualifier when there is one, otherwise every referenced
            # table having a search column of that name
            if tbl is not None:
                if tbl in checked and col in db[tbl].search_cols:
                    return [tbl]
                return []
            return [tname for tname in checked if col in db[tname].search_cols]

        for kind, types, description in [
            ("equality", None, "an equality constraint"),
            ("range", ("btree",), "a range constraint"),
        ]:
            for tbl, col in found[kind]:
                if col == "id":
                    continue  # id always has its primary key index
                candidates = candidate_tables(tbl, col)
                lacking = [t for t in candidates if col not in leaders(t, types)]
                if not lacking:
                    continue
                if len(candidates) == 1:
                    tname = candidates[0]
                    suggestions.append(
                        '"%s" appears in %s but no index on %s leads with it; '
                        "consider db.%s.create_index(['%s'])"
                        % (col, description, tname, tname, col)
                    )
                else:
                    suggestions.append(
                        '"%s" appears in %s and several of the referenced tables '
                        "have a column of that name (%s); no index leads with it "
                        "on %s; consider %s"
                        % (col, description, ", ".join(candidates), ", ".join(lacking),
                           " or ".join("db.%s.create_index(['%s'])" % (t, col) for t in lacking))
                    )
        for tbl, col in found["containment"]:
            candidates = candidate_tables(tbl, col)
            lacking = [t for t in candidates if col not in leaders(t, ("gin",))]
            if not lacking:
                continue
            if len(candidates) == 1:
                tname = candidates[0]
                suggestions.append(
                    '"%s" is filtered with a containment/overlap operator (@>, <@, &&) '
                    "but has no GIN index; consider db.%s.create_index(['%s'], type='gin')"
                    % (col, tname, col)
                )
            else:
                suggestions.append(
                    '"%s" is filtered with a containment/overlap operator (@>, <@, &&) '
                    "and several of the referenced tables have a column of that name "
                    "(%s); no GIN index covers it on %s; consider %s"
                    % (col, ", ".join(candidates), ", ".join(lacking),
                       " or ".join("db.%s.create_index(['%s'], type='gin')" % (t, col) for t in lacking))
                )
        if found["order"]:
            tbl, first = found["order"][0]
            order_str = ", ".join(_render_col(t, c) for t, c in found["order"])
            candidates = candidate_tables(tbl, first)
            lacking = [t for t in candidates if first not in leaders(t, ("btree",))]
            if lacking:
                if len(candidates) == 1:
                    tname = candidates[0]
                    # an index can only support the sort as far as the sort
                    # columns stay on the same table
                    idxcols = []
                    for q, c in found["order"]:
                        if (q is None or q == tname) and c in db[tname].search_cols:
                            idxcols.append(c)
                        else:
                            break
                    suggestions.append(
                        "the sort ORDER BY %s is not supported by an index leading "
                        "with \"%s\"; consider db.%s.create_index(%s)"
                        % (order_str, first, tname, idxcols)
                    )
                else:
                    suggestions.append(
                        'the sort ORDER BY %s leads with "%s", and several of the '
                        "referenced tables have a column of that name (%s); no btree "
                        "index leads with it on %s; consider %s"
                        % (order_str, first, ", ".join(candidates), ", ".join(lacking),
                           " or ".join("db.%s.create_index(['%s'])" % (t, first) for t in lacking))
                    )
    else:
        observed = [
            (kind, found[kind])
            for kind in ("equality", "range", "containment", "order")
            if found[kind]
        ]
        if observed:
            suggestions.append(
                "columns constrained in this shape -- %s -- pass db= to check "
                "them against existing indexes"
                % "; ".join(
                    "%s: %s" % (kind, ", ".join(_render_col(t, c) for t, c in cols))
                    for kind, cols in observed
                )
            )

    for col in found["path"]:
        suggestions.append(
            'the query compares a path inside the jsonb column "%s" with =, which no '
            "btree or GIN index supports directly; consider restructuring as a "
            "containment ($contains) query backed by a GIN index, or an expression index"
            % col
        )
    for col, pattern in found["like"]:
        if pattern.startswith("%") or pattern.startswith("_"):
            suggestions.append(
                'LIKE pattern with a leading wildcard (%s) on "%s" cannot use a btree '
                "index; consider a trigram (pg_trgm) GIN index or anchoring the pattern"
                % (_abbreviate(pattern), col)
            )

    # the same create_index call can be suggested through several routes
    seen = set()
    unique = []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique


##################################################################
# Printing                                                       #
##################################################################


def _fmt_duration(t):
    if t is None:
        return "-"
    return "%.3gs" % t


def show_slow_report(logfile, top=20, cutoff=None, db=None):
    """
    Print the report produced by ``slow_query_report``; see its
    documentation for the inputs.

    EXAMPLES::

        >>> from psycodict.slowlog import show_slow_report
        >>> show_slow_report("slow_queries.log", db=db)  # doctest: +SKIP
    """
    report = slow_query_report(logfile, top=top, cutoff=cutoff, db=db)
    print(
        "Slow query log %s: %s lines, %s parsed records (%s unparsed lines)"
        % (report["logfile"], report["lines"], report["records"], report["unparsed"])
    )
    if cutoff is not None:
        print(
            "Only queries taking at least %s are considered (%s records below the cutoff)"
            % (_fmt_duration(cutoff), report["skipped"])
        )
    if report["records"] == report["skipped"]:
        print("No slow queries to analyze")
        return
    p = report["percentiles"]
    print(
        "Total query time %.3fs; durations p50 %s, p90 %s, p99 %s, max %s"
        % (report["total_time"], _fmt_duration(p["p50"]), _fmt_duration(p["p90"]),
           _fmt_duration(p["p99"]), _fmt_duration(p["max"]))
    )
    if report["thresholds"]:
        print("With a higher slowcutoff, the log would have kept:")
        print("    %10s %12s %12s %12s" % ("cutoff", "records", "lines", "% of lines"))
        for row in report["thresholds"]:
            print(
                "    %10s %12s %12s %11.1f%%"
                % (_fmt_duration(row["cutoff"]), row["records"], row["lines"], row["percent"])
            )
    def print_shape(i, data):
        tables = ", ".join(data["tables"])
        print(
            "#%s: %s times, total %.3fs (mean %.3fs, max %.3fs)%s"
            % (i, data["count"], data["total"], data["mean"], data["max"],
               " on " + tables if tables else "")
        )
        print("    %s" % data["shape"])
        if data["example"] is not None and (data["count"] > 1 or data["example"] != data["shape"]):
            print("    example: %s" % _abbreviate(data["example"], 500))
        if data["replicate"]:
            print("    replicate: %s" % _abbreviate(data["replicate"], 500))
        for suggestion in data["suggestions"]:
            print("    * %s" % suggestion)

    print("Top %s query shapes by total time:" % len(report["shapes"]))
    for i, data in enumerate(report["shapes"], 1):
        print_shape(i, data)
    by_mean = report.get("shapes_by_mean", [])
    if by_mean:
        print("Top %s query shapes by mean time:" % len(by_mean))
        for i, data in enumerate(by_mean, 1):
            print_shape(i, data)
