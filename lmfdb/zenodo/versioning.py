"""
Parsing and formatting of LMFDB version strings ``{major}.{data}.{code}``.

The ``code`` component uses the letter encoding of ``sage.databases.cremona``
(``cremona_letter_code``/``class_to_int``: a=0, ..., z=25, ba=26, bb=27, ...).
When sage is available we use its implementations directly; otherwise the
pure-python fallbacks below are used (the test suite checks that the two
agree).

This module deliberately has no dependencies beyond the standard library (and
optionally sage), so that it can be used by the deploy watcher on machines
without sage and by the web frontend alike.
"""

import re

__all__ = [
    "cremona_letter_code",
    "class_to_int",
    "format_version",
    "parse_version",
    "VERSION_RE",
]


def _cremona_letter_code(n):
    """
    Pure-python version of ``sage.databases.cremona.cremona_letter_code``:
    0 -> 'a', 25 -> 'z', 26 -> 'ba', 27 -> 'bb', ...
    """
    n = int(n)
    if n < 0:
        raise ValueError("n (=%s) must be a non-negative integer" % n)
    if n == 0:
        return "a"
    s = ""
    while n:
        s = chr(ord("a") + n % 26) + s
        n //= 26
    return s


def _class_to_int(k):
    """
    Pure-python version of ``sage.databases.cremona.class_to_int``,
    restricted to lower-case letter codes: 'a' -> 0, 'z' -> 25, 'ba' -> 26.
    """
    if not k or not re.fullmatch(r"[a-z]+", k):
        raise ValueError("invalid letter code %r" % (k,))
    n = 0
    for c in k:
        n = 26 * n + (ord(c) - ord("a"))
    return n


try:  # pragma: no cover - exercised only when sage is installed
    # broad except: importing sage outside of sage.all can raise more than
    # ImportError (partially initialized modules); the fallbacks are
    # equivalent (see test_letter_code_matches_sage)
    from sage.databases.cremona import cremona_letter_code, class_to_int
except Exception:
    cremona_letter_code = _cremona_letter_code
    class_to_int = _class_to_int


# A full version like 2.3.ba; we also accept the data-only prefix 2.3
VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:\.([a-z]+))?$")


def format_version(major, data_seq, code_seq=None):
    """
    Format an LMFDB version string.

    INPUT:

    - ``major`` -- non-negative integer, the major version
    - ``data_seq`` -- non-negative integer, the data push counter
    - ``code_seq`` -- non-negative integer, the frontend release counter,
      or None to produce the data-only form ``{major}.{data}``

    EXAMPLES: ``format_version(2, 3, 26) == "2.3.ba"``,
    ``format_version(2, 3) == "2.3"``.
    """
    major, data_seq = int(major), int(data_seq)
    if major < 0 or data_seq < 0:
        raise ValueError("version components must be non-negative")
    if code_seq is None:
        return "%s.%s" % (major, data_seq)
    return "%s.%s.%s" % (major, data_seq, cremona_letter_code(int(code_seq)))


def parse_version(v):
    """
    Parse an LMFDB version string.

    INPUT:

    - ``v`` -- a string like ``"2.3.ba"`` or ``"2.3"``

    OUTPUT:

    A tuple ``(major, data_seq, code_seq)`` of integers; ``code_seq`` is None
    for the data-only form.

    EXAMPLES: ``parse_version("2.3.ba") == (2, 3, 26)``.
    """
    m = VERSION_RE.fullmatch(v.strip())
    if not m:
        raise ValueError(
            "invalid LMFDB version %r (expected e.g. '2.3.ba' or '2.3')" % (v,)
        )
    major, data_seq, letters = m.groups()
    code_seq = None if letters is None else class_to_int(letters)
    return int(major), int(data_seq), code_seq
