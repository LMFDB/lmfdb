"""
Database state for the Zenodo backup system and the LMFDB version history.

Two tables are used:

- ``version_history`` (public schema) -- one row per version event.  This
  table lives on proddb (for www) and on grace (from where it is mirrored to
  devmirror, so that beta can display it); rows are inserted by the backup
  pipeline and the deploy watcher.  It is in the public schema so that the
  read-only web connection can display the /version page.

  Row kinds:

  * ``major`` -- a major version bump (seq is the new major, for convenience)
  * ``data`` -- a data push: ``seq`` is the data counter within ``major`` and
    ``tables`` records ``{tablename: {version, recid, doi, concept_doi}}`` for
    the tables published in this batch
  * ``code`` -- a frontend release: ``seq`` is the code counter within
    ``major`` (displayed via the letter code) and ``git_hash`` records the
    commit deployed to the web branch

- ``userdb.zenodo_backups`` (proddb only) -- operational state of the upload
  pipeline, one row per (table, version) upload attempt, driving idempotent
  resume after failures.

All functions take the database object as first argument; nothing here opens
connections of its own.
"""

import json
from datetime import datetime, timezone

from psycopg2.sql import SQL

from .versioning import format_version

# Status values for userdb.zenodo_backups, in normal order of progression.
STATUSES = [
    "pending",        # decided to upload, not yet packaged
    "packaging",      # compressing / hashing / generating metadata
    "uploading",      # draft created on Zenodo, files going up
    "awaiting_quota", # draft exceeds 50GB; owner must raise quota in the UI
    "published",      # publish action succeeded
    "verified",       # checksums on Zenodo confirmed against local values
    "failed",         # gave up; error column has details
]


def utcnow():
    """Naive UTC timestamp, matching the convention of userdb.dbrecord."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def table_exists(db, name):
    """Whether a table (optionally schema-qualified) exists."""
    cur = db._execute(SQL("SELECT to_regclass(%s)"), [name])
    return cur.fetchone()[0] is not None


def ensure_tables(db, grant_select_to=("lmfdb",)):
    """
    Create the state tables if they do not exist.  Run once (per database) by
    an editor; harmless to re-run.

    ``grant_select_to`` -- roles given read access to version_history so the
    web frontend can render the /version page; grant failures (e.g. a missing
    role on a private installation) are ignored.
    """
    db._execute(SQL("""
        CREATE TABLE IF NOT EXISTS version_history (
            id bigserial PRIMARY KEY,
            major smallint NOT NULL,
            kind text NOT NULL CHECK (kind IN ('major', 'data', 'code')),
            seq integer NOT NULL,
            time timestamp without time zone NOT NULL,
            editor text,
            git_hash text,
            tables jsonb,
            comment text
        )"""))
    db._execute(SQL(
        "CREATE INDEX IF NOT EXISTS version_history_time ON version_history (time)"
    ))
    for role in grant_select_to:
        try:
            db._execute(SQL("GRANT SELECT ON version_history TO {0}").format(
                SQL(role)))
        except Exception:
            pass
    db._execute(SQL("""
        CREATE TABLE IF NOT EXISTS userdb.zenodo_backups (
            id bigserial PRIMARY KEY,
            tablename text NOT NULL,
            owner text NOT NULL,
            concept_recid text,
            concept_doi text,
            recid text,
            doi text,
            version text,
            status text NOT NULL,
            draft_id text,
            source_md5s jsonb,
            uploaded_files jsonb,
            total_size bigint,
            started timestamp without time zone,
            finished timestamp without time zone,
            error text
        )"""))
    db._execute(SQL(
        "CREATE INDEX IF NOT EXISTS zenodo_backups_tablename "
        "ON userdb.zenodo_backups (tablename, id)"
    ))


######################################################################
# version_history                                                    #
######################################################################

def _insert_version_row(db, major, kind, seq, time=None, editor=None,
                        git_hash=None, tables=None, comment=None):
    db._execute(
        SQL("INSERT INTO version_history "
            "(major, kind, seq, time, editor, git_hash, tables, comment) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)"),
        [major, kind, seq, time or utcnow(), editor, git_hash,
         None if tables is None else json.dumps(tables), comment],
    )


def insert_major(db, major, git_hash=None, editor=None, comment=None, time=None):
    """
    Record a major version bump.  Also records a code row with seq 0 (the
    frontend state at the moment of the bump), so that ``{major}.0.a`` is
    resolvable.
    """
    time = time or utcnow()
    _insert_version_row(db, major, "major", major, time=time, editor=editor,
                        git_hash=git_hash, comment=comment)
    _insert_version_row(db, major, "code", 0, time=time, editor=editor,
                        git_hash=git_hash, comment="code counter reset")


def insert_code(db, major, seq, git_hash, editor=None, comment=None, time=None):
    """Record a frontend release (deploy of the web branch)."""
    _insert_version_row(db, major, "code", seq, time=time, editor=editor,
                        git_hash=git_hash, comment=comment)


def insert_data(db, major, seq, tables, editor=None, comment=None, time=None):
    """
    Record a data push.

    - ``tables`` -- dict ``{tablename: {"version": ..., "recid": ...,
      "doi": ..., "concept_doi": ...}}`` for the tables published in this batch
    """
    _insert_version_row(db, major, "data", seq, time=time, editor=editor,
                        tables=tables, comment=comment)


_HISTORY_COLS = "id, major, kind, seq, time, editor, git_hash, tables, comment"


def _history_rows(db, where=SQL(""), values=None, order="time, id", limit=None):
    query = SQL("SELECT {0} FROM version_history").format(SQL(_HISTORY_COLS))
    query += where
    query += SQL(" ORDER BY %s" % order)
    if limit is not None:
        query += SQL(" LIMIT %d" % int(limit))
    cur = db._execute(query, values)
    cols = [c.strip() for c in _HISTORY_COLS.split(",")]
    return [dict(zip(cols, row)) for row in cur]


def history(db, limit=None):
    """Version events, most recent first (for the /version page)."""
    return _history_rows(db, order="time DESC, id DESC", limit=limit)


def latest_versions(db):
    """
    The current version state, as a dict with keys ``major``, ``data_seq``,
    ``code_seq`` and ``time`` (of the most recent event), or None if the
    version history is empty (versioning not yet activated).
    """
    rows = _history_rows(db)
    if not rows:
        return None
    major = max(r["major"] for r in rows if r["kind"] == "major") \
        if any(r["kind"] == "major" for r in rows) else min(r["major"] for r in rows)
    data_seq = max((r["seq"] for r in rows
                    if r["kind"] == "data" and r["major"] == major), default=0)
    code_seq = max((r["seq"] for r in rows
                    if r["kind"] == "code" and r["major"] == major), default=0)
    return {
        "major": major,
        "data_seq": data_seq,
        "code_seq": code_seq,
        "time": max(r["time"] for r in rows),
    }


def next_data_seq(db, major):
    """The data counter to use for the next push within ``major``."""
    cur = latest_versions(db)
    if cur is None or cur["major"] != major:
        return 1
    return cur["data_seq"] + 1


def current_version_string(db):
    """
    The full current version, e.g. ``"2.3.ba"``, or None if the version
    history table is missing or empty (callers should then fall back to
    ``lmfdb.version.LEGACY_VERSION``).  Never raises: intended for the footer.
    """
    try:
        cur = latest_versions(db)
    except Exception:
        return None
    if cur is None:
        return None
    return format_version(cur["major"], cur["data_seq"], cur["code_seq"])


def resolve_version(db, major, data_seq, code_seq=None):
    """
    Resolve an LMFDB version to its constituents.

    OUTPUT:

    A dict with keys:

    - ``version`` -- the normalized version string
    - ``git_hash``, ``git_time`` -- the frontend commit (None if ``code_seq``
      is None or unknown)
    - ``tables`` -- dict ``{tablename: {version, recid, doi, concept_doi}}``
      giving the version of every table at this LMFDB version
    - ``time`` -- the timestamp at which this data version was created

    Raises ValueError if the version does not appear in the history.
    """
    rows = _history_rows(db)
    # Anchor time for the data component
    if data_seq == 0:
        anchors = [r for r in rows if r["kind"] == "major" and r["major"] == major]
    else:
        anchors = [r for r in rows
                   if r["kind"] == "data" and r["major"] == major
                   and r["seq"] == data_seq]
    if not anchors:
        raise ValueError("unknown data version %s.%s" % (major, data_seq))
    anchor = anchors[0]
    tables = {}
    for r in rows:
        if r["kind"] != "data" or r["tables"] is None:
            continue
        if (r["time"], r["id"]) <= (anchor["time"], anchor["id"]):
            tables.update(r["tables"])
    git_hash = git_time = None
    if code_seq is not None:
        code = [r for r in rows
                if r["kind"] == "code" and r["major"] == major
                and r["seq"] == code_seq]
        if not code:
            raise ValueError("unknown code version %s.*.%s" % (major, code_seq))
        git_hash, git_time = code[0]["git_hash"], code[0]["time"]
    return {
        "version": format_version(major, data_seq, code_seq),
        "git_hash": git_hash,
        "git_time": git_time,
        "tables": tables,
        "time": anchor["time"],
    }


def latest_code_deploy(db):
    """The most recent code row (any major), or None -- used by the watcher."""
    rows = _history_rows(db)
    code = [r for r in rows if r["kind"] == "code"]
    return code[-1] if code else None


######################################################################
# userdb.zenodo_backups                                              #
######################################################################

_BACKUP_COLS = ("id, tablename, owner, concept_recid, concept_doi, recid, doi, "
                "version, status, draft_id, source_md5s, uploaded_files, "
                "total_size, started, finished, error")


def _backup_rows(db, where, values):
    query = SQL("SELECT {0} FROM userdb.zenodo_backups").format(SQL(_BACKUP_COLS))
    query += where
    cur = db._execute(query, values)
    cols = [c.strip() for c in _BACKUP_COLS.split(",")]
    return [dict(zip(cols, row)) for row in cur]


def start_attempt(db, tablename, owner, version, source_md5s):
    """Insert a new upload attempt (status ``pending``); returns its id."""
    cur = db._execute(
        SQL("INSERT INTO userdb.zenodo_backups "
            "(tablename, owner, version, status, source_md5s, started) "
            "VALUES (%s, %s, %s, %s, %s::jsonb, %s) RETURNING id"),
        [tablename, owner, version, "pending", json.dumps(source_md5s), utcnow()],
    )
    return cur.fetchone()[0]


def update_attempt(db, attempt_id, **fields):
    """Update columns of an upload attempt (e.g. status, recid, error)."""
    allowed = {"owner", "concept_recid", "concept_doi", "recid", "doi",
               "version", "status", "draft_id", "source_md5s",
               "uploaded_files", "total_size", "finished", "error"}
    bad = set(fields) - allowed
    if bad:
        raise ValueError("cannot update %s" % ", ".join(sorted(bad)))
    if fields.get("status") is not None and fields["status"] not in STATUSES:
        raise ValueError("invalid status %r" % (fields["status"],))
    sets, values = [], []
    for col, val in fields.items():
        if col in ("source_md5s", "uploaded_files") and val is not None:
            sets.append("%s = %%s::jsonb" % col)
            values.append(json.dumps(val))
        else:
            sets.append("%s = %%s" % col)
            values.append(val)
    values.append(attempt_id)
    db._execute(
        SQL("UPDATE userdb.zenodo_backups SET " + ", ".join(sets)
            + " WHERE id = %s"),
        values,
    )


def latest_attempt(db, tablename, statuses=None):
    """
    The most recent attempt row for a table (optionally restricted to given
    statuses), or None.
    """
    where = SQL(" WHERE tablename = %s")
    values = [tablename]
    if statuses:
        where += SQL(" AND status IN (" + ", ".join(["%s"] * len(statuses)) + ")")
        values.extend(statuses)
    rows = _backup_rows(db, where + SQL(" ORDER BY id DESC LIMIT 1"), values)
    return rows[0] if rows else None


def latest_published(db, tablename):
    """The most recent published/verified attempt for a table, or None."""
    return latest_attempt(db, tablename, statuses=["published", "verified"])


def unfinished(db):
    """All attempts in a non-terminal status (for resume and status display)."""
    return _backup_rows(
        db,
        SQL(" WHERE status IN ('pending', 'packaging', 'uploading', "
            "'awaiting_quota') ORDER BY id"),
        None,
    )


def all_latest_published(db):
    """
    Dict ``{tablename: row}`` of the most recent published/verified attempt
    for every table (for status display and the registry record).
    """
    rows = _backup_rows(
        db,
        SQL(" WHERE status IN ('published', 'verified') ORDER BY id"),
        None,
    )
    return {r["tablename"]: r for r in rows}
