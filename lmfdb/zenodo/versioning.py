"""
Version strings: LMFDB versions ``{major}.{data}-{code}`` and the
``{major}.{minor}`` versions of individual Zenodo records.

- An LMFDB version such as ``2.3-5`` has a major version (bumped manually), a
  data counter (one per push of tables to production) and a code counter (one
  per push to the web branch); the two counters reset when the major version
  changes.  The data-only prefix ``2.3`` names a data version.
- Each archived table has its own record version such as ``1.4``, starting at
  ``1.0`` and bumped (major or minor) by the editor pushing the change, as
  requested by the contributor of the data.

This module deliberately has no dependencies beyond the standard library, so
that it can be used by the deploy watcher on machines without sage and by the
web frontend alike.
"""

import re
from datetime import timedelta

__all__ = [
    "BUMPS",
    "FIRST_RECORD_VERSION",
    "format_time",
    "format_version",
    "history_events",
    "next_record_version",
    "parse_record_version",
    "parse_version",
    "VERSION_RE",
]


# A full version like 2.3-5; we also accept the data-only prefix 2.3
VERSION_RE = re.compile(r"^(\d+)\.(\d+)(?:-(\d+))?$")
RECORD_VERSION_RE = re.compile(r"^(\d+)\.(\d+)$")

BUMPS = ("major", "minor")
FIRST_RECORD_VERSION = "1.0"


def format_version(major, data_seq, code_seq=None):
    """
    Format an LMFDB version string.

    INPUT:

    - ``major`` -- non-negative integer, the major version
    - ``data_seq`` -- non-negative integer, the data push counter
    - ``code_seq`` -- non-negative integer, the frontend release counter,
      or None to produce the data-only form ``{major}.{data}``

    EXAMPLES: ``format_version(2, 3, 5) == "2.3-5"``,
    ``format_version(2, 3) == "2.3"``.
    """
    major, data_seq = int(major), int(data_seq)
    if major < 0 or data_seq < 0:
        raise ValueError("version components must be non-negative")
    if code_seq is None:
        return "%s.%s" % (major, data_seq)
    code_seq = int(code_seq)
    if code_seq < 0:
        raise ValueError("version components must be non-negative")
    return "%s.%s-%s" % (major, data_seq, code_seq)


def parse_version(v):
    """
    Parse an LMFDB version string.

    INPUT:

    - ``v`` -- a string like ``"2.3-5"`` or ``"2.3"``

    OUTPUT:

    A tuple ``(major, data_seq, code_seq)`` of integers; ``code_seq`` is None
    for the data-only form.

    EXAMPLES: ``parse_version("2.3-5") == (2, 3, 5)``.
    """
    m = VERSION_RE.fullmatch(v.strip())
    if not m:
        raise ValueError(
            "invalid LMFDB version %r (expected e.g. '2.3-5' or '2.3')" % (v,)
        )
    major, data_seq, code_seq = m.groups()
    return int(major), int(data_seq), None if code_seq is None else int(code_seq)


def parse_record_version(v):
    """
    Parse a record version such as ``"1.4"`` into ``(major, minor)``.
    """
    m = RECORD_VERSION_RE.fullmatch(str(v).strip())
    if not m:
        raise ValueError("invalid record version %r (expected e.g. '1.4')" % (v,))
    return int(m.group(1)), int(m.group(2))


def next_record_version(previous, bump):
    """
    The version of the next Zenodo version of a record.

    INPUT:

    - ``previous`` -- the record's latest published version, or None if the
      record has never been published (then the result is ``"1.0"`` and
      ``bump`` is ignored)
    - ``bump`` -- ``"major"`` or ``"minor"``

    EXAMPLES: ``next_record_version("1.4", "minor") == "1.5"``,
    ``next_record_version("1.4", "major") == "2.0"``.
    """
    if previous is None:
        return FIRST_RECORD_VERSION
    major, minor = parse_record_version(previous)
    if bump == "major":
        return "%s.0" % (major + 1)
    if bump == "minor":
        return "%s.%s" % (major, minor + 1)
    raise ValueError("bump must be one of %s, not %r" % (", ".join(BUMPS), bump))


def format_time(t):
    """
    A naive UTC datetime as ``"YYYY-MM-DD HH:MM:SS UTC"``, rounded to the
    nearest second; ``""`` for None.
    """
    if t is None:
        return ""
    return (t + timedelta(microseconds=500000)).strftime("%Y-%m-%d %H:%M:%S UTC")


HISTORY_KINDS = {"data": "data push", "code": "frontend release",
                 "major": "major version bump"}


def history_events(rows):
    """
    The version history for display, most recent first.

    INPUT:

    - ``rows`` -- ``version_history`` rows as dicts, in any order

    OUTPUT:

    A list of copies of the rows, each with ``version``, the LMFDB version
    current right after it, and ``kind_label``.  A major row and the code
    row recorded with it (see ``state.major_rows``) become a single event.
    """
    events = []
    major = data_seq = code_seq = None
    for row in sorted(rows, key=lambda r: (r["time"], r["id"])):
        if row["kind"] == "major" or row["major"] != major:
            major, data_seq, code_seq = row["major"], 0, None
        if row["kind"] == "data":
            data_seq = row["seq"]
        elif row["kind"] == "code":
            code_seq = row["seq"]
        version = format_version(major, data_seq, code_seq)
        if row["kind"] == "code" and events and events[-1]["kind"] == "major":
            events[-1]["version"] = version
            events[-1]["git_hash"] = events[-1]["git_hash"] or row["git_hash"]
            continue
        events.append(dict(row, version=version,
                           kind_label=HISTORY_KINDS[row["kind"]]))
    events.reverse()
    return events
