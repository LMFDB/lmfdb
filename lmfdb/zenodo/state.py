"""
Database state for the Zenodo backup system and the LMFDB version history.

Two tables are used:

- ``version_history`` (public schema, proddb only) -- one row per version
  event, inserted by the backup pipeline and the deploy watcher.  It is in
  the public schema so that the read-only web connection can display the
  /version page.  Beta has no version: its data and code are both ahead of
  any release.

  Row kinds:

  * ``major`` -- a major version bump (seq is the new major, for convenience)
  * ``data`` -- a data push: ``seq`` is the data counter within ``major`` and
    ``tables`` records ``{tablename: {version, recid, doi, concept_doi,
    notes}}`` for the tables published in this batch, where ``version`` is
    the table's own record version (e.g. ``1.4``)
  * ``code`` -- a frontend release: ``seq`` is the code counter within
    ``major`` and ``git_hash`` records the commit deployed to the web branch

- ``userdb.zenodo_backups`` (proddb only) -- operational state of the upload
  pipeline, one row per (table, record version) upload attempt, driving
  idempotent resume after failures.  ``version`` is the record version,
  ``lmfdb_version`` the data version (e.g. ``2.3``) that first included it.

All functions take the database object as first argument; nothing here opens
connections of its own.  Passing ``Sandbox(db)`` instead points them at
separate tables (``userdb.version_history_sandbox`` and
``userdb.zenodo_backups_sandbox``), so that a rehearsal against
sandbox.zenodo.org never shares record ids, drafts or version history with
the production archive.
"""

import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from psycodict import SQL

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
    "superseded",     # replaced by a later attempt (e.g. for newer content)
]
UNFINISHED = ("pending", "packaging", "uploading", "awaiting_quota")


def utcnow():
    """Naive UTC timestamp, matching the convention of userdb.dbrecord."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def table_exists(db, name):
    """Whether a table (optionally schema-qualified) exists."""
    cur = db._execute(SQL("SELECT to_regclass(%s)"), [name])
    return cur.fetchone()[0] is not None


class Sandbox:
    """
    The database, with the state tables of a sandbox rehearsal in place of
    the production ones.  Everything else is delegated to the wrapped object.
    """
    history_table = "userdb.version_history_sandbox"
    backups_table = "userdb.zenodo_backups_sandbox"

    def __init__(self, db):
        self.wrapped = db

    def __getattr__(self, name):
        return getattr(self.wrapped, name)

    def __getitem__(self, name):
        return self.wrapped[name]


def unwrap(db):
    """The database object itself, without any ``Sandbox`` around it."""
    return db.wrapped if isinstance(db, Sandbox) else db


def _history_name(db):
    return db.history_table if isinstance(db, Sandbox) else "version_history"


def _backups_name(db):
    return db.backups_table if isinstance(db, Sandbox) else "userdb.zenodo_backups"


def _history(db):
    return SQL(_history_name(db))


def _backups(db):
    return SQL(_backups_name(db))


def ensure_tables(db, grant_select_to=("lmfdb",)):
    """
    Create the state tables if they do not exist.  Run once (per database) by
    an editor; harmless to re-run.

    ``grant_select_to`` -- roles given read access to version_history so the
    web frontend can render the /version page; grant failures (e.g. a missing
    role on a private installation) are ignored.
    """
    history, backups = _history_name(db), _backups_name(db)
    db._execute(SQL("""
        CREATE TABLE IF NOT EXISTS {0} (
            id bigserial PRIMARY KEY,
            major smallint NOT NULL,
            kind text NOT NULL CHECK (kind IN ('major', 'data', 'code')),
            seq integer NOT NULL,
            time timestamp without time zone NOT NULL,
            editor text,
            git_hash text,
            tables jsonb,
            comment text
        )""").format(SQL(history)))
    base = history.split(".")[-1]
    db._execute(SQL("CREATE INDEX IF NOT EXISTS {0} ON {1} (time)").format(
        SQL(base + "_time"), SQL(history)))
    # rejects a second row for the same version if two writers race
    db._execute(SQL(
        "CREATE UNIQUE INDEX IF NOT EXISTS {0} ON {1} (major, kind, seq)"
    ).format(SQL(base + "_seq"), SQL(history)))
    for role in grant_select_to:
        try:
            db._execute(SQL("GRANT SELECT ON {0} TO {1}").format(
                SQL(history), SQL(role)))
        except Exception:
            pass
    db._execute(SQL("""
        CREATE TABLE IF NOT EXISTS {0} (
            id bigserial PRIMARY KEY,
            tablename text NOT NULL,
            owner text NOT NULL,
            concept_recid text,
            concept_doi text,
            recid text,
            doi text,
            version text,
            bump text,
            notes text,
            lmfdb_version text,
            source_time timestamp without time zone,
            status text NOT NULL,
            draft_id text,
            source_md5s jsonb,
            uploaded_files jsonb,
            total_size bigint,
            started timestamp without time zone,
            finished timestamp without time zone,
            error text
        )""").format(SQL(backups)))
    db._execute(SQL("CREATE INDEX IF NOT EXISTS {0} ON {1} (tablename, id)").format(
        SQL(backups.split(".")[-1] + "_tablename"), SQL(backups)))


######################################################################
# version_history                                                    #
######################################################################

def version_row(major, kind, seq, time=None, editor=None, git_hash=None,
                tables=None, comment=None):
    """
    A version_history row as a dict (see ``insert_version_rows``); ``time``
    defaults to the database server's clock at insertion.
    """
    return {"major": major, "kind": kind, "seq": seq, "time": time,
            "editor": editor, "git_hash": git_hash, "tables": tables,
            "comment": comment}


def insert_version_rows(db, rows):
    """
    Insert version_history rows in one statement, so all or none land.
    Rows without a time get the server's, so that the order of events does
    not depend on the clocks of the machines recording them.
    """
    _write(
        db,
        SQL("INSERT INTO {0} "
            "(major, kind, seq, time, editor, git_hash, tables, comment) "
            "VALUES ").format(_history(db))
        + SQL(", ").join([SQL("(%s, %s, %s, COALESCE(%s::timestamp, "
                              "timezone('UTC', now())), %s, %s, %s::jsonb, %s)")]
                         * len(rows)),
        [val for r in rows for val in
         (r["major"], r["kind"], r["seq"], r["time"], r["editor"],
          r["git_hash"], None if r["tables"] is None else json.dumps(r["tables"]),
          r["comment"])],
    )


def _insert_version_row(db, major, kind, seq, **kwds):
    insert_version_rows(db, [version_row(major, kind, seq, **kwds)])


def major_rows(major, git_hash=None, editor=None, comment=None, time=None):
    """
    The rows recording a major version bump: the bump itself and a code row
    with seq 0 (the frontend at the moment of the bump), so that
    ``{major}.0-0`` is resolvable.
    """
    return [version_row(major, "major", major, time=time, editor=editor,
                        git_hash=git_hash, comment=comment),
            version_row(major, "code", 0, time=time, editor=editor,
                        git_hash=git_hash, comment="code counter reset")]


def insert_major(db, major, git_hash=None, editor=None, comment=None, time=None):
    """Record a major version bump (see ``major_rows``)."""
    insert_version_rows(db, major_rows(major, git_hash=git_hash, editor=editor,
                                       comment=comment, time=time))


_HISTORY_COLS = "id, major, kind, seq, time, editor, git_hash, tables, comment"


def _history_rows(db, where=SQL(""), values=None, order="time, id", limit=None):
    query = SQL("SELECT {0} FROM {1}").format(SQL(_HISTORY_COLS), _history(db))
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


def next_data_version(db):
    """
    The ``(major, seq)`` of the next data push.  The major is the active one
    in the history (a major bump becomes active when its deploy is recorded),
    not ``lmfdb.version.MAJOR`` of the process doing the push, which may be
    stale.
    """
    cur = latest_versions(db)
    if cur is None:
        raise ValueError("version_history is empty: activate versioning with "
                         "db.zenodo_setup() first")
    return cur["major"], cur["data_seq"] + 1


def recorded_records(db):
    """
    The ``(tablename, recid)`` pairs listed in some data version, i.e. the
    published records that are part of the version history.
    """
    return {(name, entry.get("recid"))
            for r in _history_rows(db, SQL(" WHERE kind = 'data'"))
            for name, entry in (r["tables"] or {}).items()}


def latest_data_row(db):
    """The most recent data version row, or None."""
    rows = _history_rows(db, SQL(" WHERE kind = 'data'"),
                         order="time DESC, id DESC", limit=1)
    return rows[0] if rows else None


def insert_data_version(db, tables, editor=None, comment=None):
    """
    Record a data push as the next data version of the active major, and
    return its ``(major, seq)``.  The number is chosen under ``history_lock``,
    which the deploy watcher also takes, so a major bump recorded meanwhile
    is never skipped.
    """
    with history_lock(db):
        major, seq = next_data_version(db)
        insert_version_rows(db, [version_row(major, "data", seq, editor=editor,
                                             tables=tables, comment=comment)])
    return major, seq


@contextmanager
def history_lock(db):
    """
    Serialize reading the current version and inserting the next one
    (briefly; separate from the archive lock, which is held for hours).
    """
    name = _history_name(db) + ":insert"
    db._execute(SQL("SELECT pg_advisory_lock(hashtext(%s))"), [name])
    try:
        yield
    finally:
        db._execute(SQL("SELECT pg_advisory_unlock(hashtext(%s))"), [name])


def add_to_data_row(db, major, seq, name, entry):
    """Add ``{name: entry}`` to the ``tables`` of data version major.seq."""
    _write(
        db,
        SQL("UPDATE {0} SET tables = COALESCE(tables, '{{}}'::jsonb) "
            "|| jsonb_build_object(%s::text, %s::jsonb) "
            "WHERE kind = 'data' AND major = %s AND seq = %s").format(_history(db)),
        [name, json.dumps(entry), major, seq])


LOCK_POLL = 30


class LockLost(RuntimeError):
    """The session holding the archive lock was replaced by a reconnect."""


# id of the database object -> the session (pid, start) holding the lock
_held = {}


def _session(db):
    return tuple(db._execute(SQL(
        "SELECT pid, backend_start FROM pg_stat_activity "
        "WHERE pid = pg_backend_pid()")).fetchone())


@contextmanager
def lock(db):
    """
    Hold the archive lock (a PostgreSQL advisory lock, separate for sandbox
    state) for the duration: archive runs are serialized, so that two of
    them never edit the same draft or archive state at once.  Re-entrant;
    released if the connection dies, after which every state write of the
    run raises ``LockLost``.
    """
    key = id(unwrap(db))
    if key in _held:
        yield
        return
    name = _history_name(db)
    waiting = False
    while not db._execute(SQL("SELECT pg_try_advisory_lock(hashtext(%s))"),
                          [name]).fetchone()[0]:
        if not waiting:
            print("Another archive run is in progress; waiting for it to "
                  "finish (interrupt to give up, then re-run later).")
            waiting = True
        time.sleep(LOCK_POLL)
    _held[key] = _session(db)
    try:
        yield
    finally:
        del _held[key]
        db._execute(SQL("SELECT pg_advisory_unlock(hashtext(%s))"), [name])


def _write(db, query, values=None):
    """
    Execute a statement changing archive state, returning its rows if any.
    Within ``lock``, it runs in one transaction with a check that the session
    is still the one holding the lock: on a dropped connection psycodict
    would otherwise replay it on a new session, outside the lock.
    """
    held = _held.get(id(unwrap(db)))
    if held is None:
        cur = db._execute(query, values)
        return cur.fetchall() if cur.description else None
    from psycodict.utils import DelayCommit
    with DelayCommit(unwrap(db)):
        if _session(db) != held:
            raise LockLost("the database connection was reset during an "
                           "archive run, so another run may hold the lock "
                           "now; re-run to resume")
        cur = db._execute(query, values)
        return cur.fetchall() if cur.description else None


def current_version_string(db):
    """
    The full current version, e.g. ``"2.3-5"``, or None if the version
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
    - ``tables`` -- dict ``{tablename: {version, recid, doi, concept_doi,
      notes}}`` giving the record version of every table at this LMFDB
      version
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
            raise ValueError("unknown code version %s.*-%s" % (major, code_seq))
        git_hash, git_time = code[0]["git_hash"], code[0]["time"]
    return {
        "version": format_version(major, data_seq, code_seq),
        "git_hash": git_hash,
        "git_time": git_time,
        "tables": tables,
        "time": anchor["time"],
    }


def code_rows_for_commit(db, git_hash):
    """The code rows recording ``git_hash`` (empty if it has no version yet)."""
    return _history_rows(db, SQL(" WHERE kind = 'code' AND git_hash = %s"),
                         [git_hash])


######################################################################
# userdb.zenodo_backups                                              #
######################################################################

_BACKUP_COLS = ("id, tablename, owner, concept_recid, concept_doi, recid, doi, "
                "version, bump, notes, lmfdb_version, source_time, status, draft_id, "
                "source_md5s, uploaded_files, total_size, started, finished, "
                "error")


def _backup_rows(db, where, values):
    query = SQL("SELECT {0} FROM {1}").format(SQL(_BACKUP_COLS), _backups(db))
    query += where
    cur = db._execute(query, values)
    cols = [c.strip() for c in _BACKUP_COLS.split(",")]
    return [dict(zip(cols, row)) for row in cur]


def start_attempt(db, tablename, owner, version, source_md5s, bump=None,
                  notes=None, source_time=None):
    """
    Insert a new upload attempt (status ``pending``); returns its id.

    ``version`` is the record version being uploaded, ``bump`` the requested
    increment (None for a first version), ``notes`` the change description
    and ``source_time`` when the archived data was taken from production.
    """
    return _write(
        db,
        SQL("INSERT INTO {0} "
            "(tablename, owner, version, bump, notes, source_time, status, "
            "source_md5s, started) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) "
            "RETURNING id").format(_backups(db)),
        [tablename, owner, version, bump, notes, source_time, "pending",
         json.dumps(source_md5s), utcnow()],
    )[0][0]


def update_attempt(db, attempt_id, **fields):
    """Update columns of an upload attempt (e.g. status, recid, error)."""
    allowed = {"owner", "concept_recid", "concept_doi", "recid", "doi",
               "version", "bump", "notes", "lmfdb_version", "source_time",
               "status",
               "draft_id", "source_md5s", "uploaded_files", "total_size",
               "finished", "error"}
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
    _write(
        db,
        SQL("UPDATE {0} SET " + ", ".join(sets) + " WHERE id = %s").format(
            _backups(db)),
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


def max_published_size(db, tablename):
    """The largest total size of the published versions of a record."""
    return db._execute(
        SQL("SELECT MAX(total_size) FROM {0} WHERE tablename = %s "
            "AND status IN ('published', 'verified')").format(_backups(db)),
        [tablename]).fetchone()[0] or 0


def get_attempt(db, attempt_id):
    """The attempt row with the given id."""
    return _backup_rows(db, SQL(" WHERE id = %s"), [attempt_id])[0]


def latest_published(db, tablename):
    """The most recent published/verified attempt for a table, or None."""
    return latest_attempt(db, tablename, statuses=["published", "verified"])


def unfinished(db):
    """All attempts in a non-terminal status (for resume and status display)."""
    return _backup_rows(
        db,
        SQL(" WHERE status IN (" + ", ".join(["%s"] * len(UNFINISHED))
            + ") ORDER BY id"),
        list(UNFINISHED),
    )


def uploaded_bytes_since(db, since):
    """
    Bytes actually sent to Zenodo by attempts (in any status) finished, or
    if unfinished started, at or after ``since``; files an attempt found
    already on Zenodo (inherited, or sent by an attempt it replaced) are
    counted only for the attempt that sent them.
    """
    rows = _backup_rows(
        db, SQL(" WHERE COALESCE(finished, started) >= %s"), [since])
    return sum(info.get("size", 0)
               for r in rows for info in (r["uploaded_files"] or {}).values()
               if not info.get("reused"))


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
