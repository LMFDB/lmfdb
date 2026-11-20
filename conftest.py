# Author: David Roe
"""
Record and replay the database queries made by the test suite.

CI pulls every query result from devmirror, whose bandwidth is limited.  This
plugin saves those results in a SQLite "tape", keyed by the exact SQL sent,
so that test runs can be served from the tape instead.

- DBTAPE_MODE=replay: answer queries from the tape DBTAPE_FILE.  Queries it
  lacks, and queries reading a table edited since they were recorded, go to
  the database in config.ini as usual.
- DBTAPE_MODE=record: the same, except the results fetched from the database
  are recorded, and every entry used is written to a new tape in the
  directory DBTAPE_OUT, one per pytest process; `python3 conftest.py merge`
  combines them.  Without DBTAPE_FILE this records the whole run.  Only
  results read to the end are recorded, so a search stopped early always
  runs live.
- Without DBTAPE_MODE this file does nothing.

A table counts as edited when userdb.dbrecord, where LMFDB's _log_db_change
logs every psycodict editing operation, has an entry for it later than the
recording.  Knowls and user accounts are saved without that log, so for them
a fingerprint of the table (FINGERPRINTS) is compared with the one recorded.
DBTAPE_STALE lists further tables to treat as edited ("all" for every table),
which is the way to refresh after editing data with raw SQL.  The results of
catalog queries, which psycodict reads its registry of tables from, go stale
together after any logged edit.  When recording, age stands in for checks
that could not be made: if the edit log cannot be read, every result is
fetched again once it is older than its limit, and if a fingerprint cannot
be read, so are that table's results.  Each result's limit lies between half
and one and a half times DBTAPE_MAX_AGE_DAYS (14 by default); the catalog's
is DBTAPE_MAX_AGE_DAYS itself.  Replays never refresh by age.  See the
"Query tape" section of Development.md.

This is a root conftest.py so that pytest loads it before any test module
imports lmfdb, which connects and reads the table metadata at import time.
It does not import pytest, so that `python3 conftest.py merge` runs anywhere.
"""

import base64
import datetime
import decimal
import hashlib
import itertools
import json
import math
import os
import random
import re
import sqlite3
import sys
import time
import zlib

MODE = os.environ.get("DBTAPE_MODE", "")
# Edit-log times come from the editors' clocks.
CLOCK_SKEW = datetime.timedelta(hours=1)
# Bump when the encoding changes; a tape of another format is ignored.
FORMAT = "2"
# Tables edited without psycodict's logging (knowls by lmfdb.knowledge,
# accounts by lmfdb.users), each with a query whose result changes whenever
# what the tests can read of the table does.
FINGERPRINTS = {
    "kwl_knowls": "SELECT count(*), sum(xmin::text::bigint) FROM kwl_knowls",
    # The lmfdb role may read only these columns, and not xmin.
    "userdb.users": "SELECT count(username), md5(json_agg(json_build_array(username, full_name) "
                    "ORDER BY username)::text) FROM userdb.users",
}

_tape = None


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class Unrecordable(Exception):
    pass


# Results are stored as JSON.  Values JSON cannot represent exactly are tagged
# as one-key dicts whose key starts with "~"; dicts that could be mistaken for
# a tag are stored as key/value pairs.

def _encode(v):
    if v is None or v is True or v is False:
        return v
    t = type(v)
    if t is str or t is int:
        return v
    if t is float:
        return v if math.isfinite(v) else {"~f": repr(v)}
    if t is list:
        return [_encode(x) for x in v]
    if t is tuple:
        return {"~t": [_encode(x) for x in v]}
    if t is dict:
        if all(type(k) is str and not k.startswith("~") for k in v):
            return {k: _encode(x) for k, x in v.items()}
        return {"~d": [[_encode(k), _encode(x)] for k, x in v.items()]}
    if t is decimal.Decimal:
        return {"~D": str(v)}
    if t is datetime.datetime:
        return {"~dt": v.isoformat()}
    if t is datetime.date:
        return {"~da": v.isoformat()}
    if t is datetime.time:
        return {"~ti": v.isoformat()}
    if t is datetime.timedelta:
        return {"~td": [v.days, v.seconds, v.microseconds]}
    if t is bytes or t is memoryview:
        return {"~b": base64.b64encode(bytes(v)).decode()}
    name = t.__name__
    if name == "Integer":
        return {"~Z": str(v)}
    if name == "LmfdbRealLiteral":
        return {"~R": [int(v.prec()), v.literal]}
    if name == "LmfdbDecimalZero":
        return {"~0": v.literal}
    # Anything else must survive psycodict's own JSON encoding, which is how
    # Sage values inside jsonb columns were decoded in the first place.
    from psycodict.encoding import Json
    try:
        return {"~J": Json.dumps(v)}
    except Exception:
        raise Unrecordable(name)


def _decode(v):
    if type(v) is list:
        return [_decode(x) for x in v]
    if type(v) is not dict:
        return v
    if len(v) == 1:
        (k, x), = v.items()
        if k.startswith("~"):
            return _DECODERS[k](x)
    return {k: _decode(x) for k, x in v.items()}


def _sage_integer(s):
    from sage.rings.integer import Integer
    return Integer(s)


def _real_literal(x):
    from sage.rings.real_mpfr import RealField
    from psycodict.encoding import LmfdbRealLiteral
    return LmfdbRealLiteral(RealField(x[0]), x[1])


def _decimal_zero(s):
    from psycodict.encoding import LmfdbDecimalZero
    return LmfdbDecimalZero(s)


def _psycodict_json(s):
    from psycodict.encoding import Json
    return Json.loads(s)


_DECODERS = {
    "~f": float,
    "~t": lambda x: tuple(_decode(y) for y in x),
    "~d": lambda x: {_decode(k): _decode(y) for k, y in x},
    "~D": decimal.Decimal,
    "~dt": datetime.datetime.fromisoformat,
    "~da": datetime.date.fromisoformat,
    "~ti": datetime.time.fromisoformat,
    "~td": lambda x: datetime.timedelta(*x),
    "~b": base64.b64decode,
    "~Z": _sage_integer,
    "~R": _real_literal,
    "~0": _decimal_zero,
    "~J": _psycodict_json,
}


def _same(a, b):
    """
    Whether ``b`` would behave like ``a`` in the tests: same types throughout,
    equal values, and the same printed form and precision for Sage reals.
    """
    if type(a) is not type(b):
        return False
    if type(a) in (list, tuple):
        return len(a) == len(b) and all(map(_same, a, b))
    if type(a) is dict:
        return len(a) == len(b) and all(k in b and _same(x, b[k]) for k, x in a.items())
    if type(a) is float and math.isnan(a):
        return math.isnan(b)
    if getattr(a, "literal", None) != getattr(b, "literal", None):
        return False
    parent = getattr(a, "parent", None)
    if callable(parent):
        try:
            if parent() != b.parent():
                return False
        except Exception:
            return False
    try:
        return bool(a == b)
    except Exception:
        return False


def _row_json(row):
    """
    The stored form of one row.  Raises Unrecordable unless decoding it gives
    back the same row.
    """
    row = tuple(row)
    try:
        text = json.dumps(_encode(list(row)), separators=(",", ":"))
        same = _same(row, tuple(_decode(json.loads(text))))
    except Unrecordable:
        raise
    except Exception as err:
        raise Unrecordable("%s: %s" % (type(err).__name__, err))
    if not same:
        raise Unrecordable("round trip")
    return text


def _pack(rowcount, rows):
    """
    The stored form of a result, from its rows or (as str) their stored forms.
    """
    rows = [r if type(r) is str else _row_json(r) for r in rows]
    return zlib.compress(("[%d,[%s]]" % (rowcount, ",".join(rows))).encode(), 6)


def _unpack(blob):
    rowcount, rows = json.loads(zlib.decompress(blob))
    return rowcount, [tuple(_decode(r)) for r in rows]


_TABLE_RE = re.compile(r'\b(?:FROM|JOIN)\s+((?:"[^"]+"|\w+)(?:\.(?:"[^"]+"|\w+))?)', re.IGNORECASE)


def tables_read(sql):
    """
    The tables a query reads, as far as its text shows.  Extra names (from
    EXTRACT(... FROM col), say) only make an entry go stale more often.
    """
    return sorted({m.replace('"', "") for m in _TABLE_RE.findall(sql)})


def is_catalog(table):
    """
    Whether ``table`` is one psycodict reads its registry of tables and
    columns from, which any edit can change.
    """
    return table.startswith(("pg_", "information_schema.", "meta_"))


def edited_relations(table):
    """
    The relations an edit logged for ``table`` can change.  psycodict logs
    edits under the search table's name, and names its counts and stats
    tables by appending these suffixes to it.
    """
    return (table, table + "_counts", table + "_stats")


def create_tables(conn, recordings=False):
    """
    The tables of a tape: one result per query, or with ``recordings`` (a
    process's own tape) every recording made, for merge() to choose from.
    """
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    # k: hash of the SQL q; r: when it was recorded (UTC); t: the tables q
    # reads; v: the result
    conn.execute("CREATE TABLE IF NOT EXISTS tape (k TEXT%s, r TEXT, t TEXT, q TEXT, v BLOB)"
                 % ("" if recordings else " PRIMARY KEY"))


def choose(recordings):
    """
    Which of all the recordings (tape rows) of one query to keep: the newest,
    and of those made in the same second, the same one whatever their order.
    """
    return max(recordings, key=lambda rec: (rec[1], rec[4]))


class _Entry:
    """
    A result being recorded.  Each row is stored as it is fetched, before the
    caller can change it.
    """

    def __init__(self, key, sql, rowcount):
        self.key = key
        self.sql = sql
        self.rowcount = rowcount
        self.rows = []
        self.error = None
        self.recorded = _utcnow().isoformat(timespec="seconds")

    def add(self, rows):
        if self.error is None:
            try:
                self.rows.extend(_row_json(r) for r in rows)
            except Unrecordable as err:
                self.error = str(err)


class Tape:
    """
    A tape being replayed (``src``, if it exists) and, in record mode, the
    tape being written (``out``, a file only this process writes to).  It is
    written as ``out``.part and only renamed to ``out`` when closed as
    complete, so a run that crashed or never got to its tests leaves no tape.
    """

    def __init__(self, mode, src=None, out=None, stale=(), max_age=datetime.timedelta(days=14),
                 misslog=None, seed=None):
        self.mode = mode
        self.all_stale = "all" in stale
        self.forced = {rel for table in stale for rel in edited_relations(table)}
        self.max_age = max_age
        self.misslog = misslog
        self.where = "collection"
        self.stats = dict.fromkeys(["hit", "miss", "stale", "recorded", "unrecordable", "unfinished"], 0)
        self.copied = set()
        self.changes = None
        self.unlogged = {}
        self.unverified = set()
        self.edit_log = "not read"
        self.fingerprint_status = ""
        self.since = None
        self.catalog_recorded = None
        self.now = _utcnow()
        self.src = None
        self.out = None
        self.out_file = out
        self.finished = False
        meta = {}
        if src is not None and os.path.exists(src):
            self.src = sqlite3.connect("file:%s?mode=ro&immutable=1" % src, uri=True)
            meta = dict(self.src.execute("SELECT k, v FROM meta"))
            if meta.get("format") != FORMAT:
                sys.stderr.write("dbtape: ignoring %s, which has format %s rather than %s\n"
                                 % (src, meta.get("format"), FORMAT))
                self.src, meta = None, {}
        self.seed = meta.get("seed")
        self.fingerprints = {k[len("fingerprint "):]: v for k, v in meta.items() if k.startswith("fingerprint ")}
        # Which published tape this recording builds on, so that publishing
        # can refuse to replace a newer one.
        self.base = meta.get("created", "")
        if self.seed is None or (mode == "record" and self.all_stale):
            # A full recording is free to pick new random objects.
            self.seed = seed or str(int(time.time()))
        if self.src is not None:
            oldest = self.src.execute("SELECT min(r) FROM tape").fetchone()[0]
            if oldest is not None:
                self.since = datetime.datetime.fromisoformat(oldest) - CLOCK_SKEW
            catalog = [r for t, r in self.src.execute("SELECT t, r FROM tape")
                       if any(is_catalog(x) for x in t.split())]
            if catalog:
                self.catalog_recorded = min(catalog)
        if mode == "record":
            self.out = sqlite3.connect(out + ".part", isolation_level=None)
            self.out.execute("PRAGMA synchronous=OFF")
            create_tables(self.out, recordings=True)
            self.out.execute("INSERT OR IGNORE INTO meta VALUES ('format', ?), ('seed', ?), ('base', ?)",
                             (FORMAT, self.seed, self.base))

    @property
    def recording(self):
        return self.mode == "record" and self.out is not None

    def close(self, complete=True):
        if self.recording:
            self.out.close()
            self.out = None
            if complete:
                os.replace(self.out_file + ".part", self.out_file)

    def read_fingerprints(self, conn):
        """
        Compare the fingerprints of the tables edited without the edit log
        with the ones recorded, and record the current ones.
        """
        current = {}
        for table, query in FINGERPRINTS.items():
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(query)
                        current[table] = "%s %s" % tuple(cur.fetchone())
            except Exception:
                self.unverified.add(table)
        status = []
        for table in FINGERPRINTS:
            if table in self.unverified:
                status.append("%s unreadable" % table)
            elif self.src is not None and current[table] != self.fingerprints.get(table):
                status.append("%s changed" % table)
                for rel in edited_relations(table):
                    self.unlogged[rel] = self.now
        self.fingerprint_status = ", ".join(status) or ("no unlogged changes" if self.src else "fingerprints read")
        if self.recording:
            self.out.executemany("INSERT OR REPLACE INTO meta VALUES (?, ?)",
                                 [("fingerprint " + t, f) for t, f in current.items()])

    def read_edit_log(self, conn):
        """
        Find which tables were edited since the oldest result on the tape was
        recorded, after comparing the fingerprints.  This runs once, on
        psycodict's connection, before its first query.
        """
        self.read_fingerprints(conn)
        if self.since is None:
            self.edit_log = "not needed"
            return
        changed = ("SELECT tablename, max(time) FROM userdb.dbrecord "
                   "WHERE time > %s GROUP BY tablename")
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(changed, [self.since])
                    rows = cur.fetchall()
        except Exception as err:
            self.edit_log = "unreadable (%s)" % type(err).__name__
            return
        self.edit_log = "read (%s tables edited)" % len(rows)
        self.changes = {}
        for table, when in rows:
            if table and when:
                for rel in edited_relations(table):
                    self.changes[rel] = max(self.changes.get(rel, when), when)

    def is_stale(self, key, tables, recorded):
        if self.all_stale:
            return True
        catalog = any(is_catalog(t) for t in tables)
        if catalog:
            # psycodict checks the catalog results against each other, so
            # they must all describe the database at the same time.
            if self.forced:
                return True
            recorded, spread = self.catalog_recorded or recorded, 1
        else:
            if self.forced.intersection(tables):
                return True
            # Spread expiry over 0.5 to 1.5 times max_age so a tape recorded
            # all at once is refreshed a little at a time.
            spread = 0.5 + int(key[:8], 16) / 2**32
        recorded = datetime.datetime.fromisoformat(recorded)
        if self.recording and self.now - recorded > self.max_age * spread:
            # Age stands in for the checks that could not be made: the edit
            # log for every result, or the fingerprint for its tables.
            if self.changes is None or self.unverified.intersection(tables):
                return True
        cutoff = recorded - CLOCK_SKEW
        if catalog:
            return bool(self.changes) and max(self.changes.values()) > cutoff
        return any(changes.get(t, cutoff) > cutoff for changes in (self.changes or {}, self.unlogged) for t in tables)

    def lookup(self, key):
        """
        The stored result for ``key`` as (rowcount, rows), or why there is
        none to use: "miss" or "stale".
        """
        if self.src is None:
            return "miss"
        row = self.src.execute("SELECT r, t, v FROM tape WHERE k = ?", (key,)).fetchone()
        if row is None:
            return "miss"
        recorded, tables, blob = row
        if self.is_stale(key, tables.split(), recorded):
            return "stale"
        if self.recording and key not in self.copied:
            self.copied.add(key)
            self.out.execute("INSERT INTO tape VALUES (?, ?, ?, ?, ?)",
                             self.src.execute("SELECT * FROM tape WHERE k = ?", (key,)).fetchone())
        return _unpack(blob)

    def write(self, entry):
        if entry.error is not None:
            self.stats["unrecordable"] += 1
            self.log("unrecordable (%s)" % entry.error, entry.sql)
            return
        self.out.execute("INSERT INTO tape VALUES (?, ?, ?, ?, ?)",
                         (entry.key, entry.recorded, " ".join(tables_read(entry.sql)), entry.sql,
                          _pack(entry.rowcount, entry.rows)))
        self.stats["recorded"] += 1

    def drop(self, entry):
        self.stats["unfinished"] += 1
        self.log("unfinished", entry.sql)

    def log(self, kind, sql):
        if self.misslog:
            with open(self.misslog, "a") as F:
                F.write("%s\t%s\t%s\n" % (kind, self.where, " ".join(sql.split())[:1000]))


class TapeCursor:
    """
    Stands in for the cursor psycodict would have used.  The real cursor is
    only opened when the database is actually needed.
    """

    def __init__(self, tape, db, buffered, make_real):
        self._tape = tape
        self._db = db
        self._make_real = make_real
        self._real = None
        # psycodict's server-side cursors are the buffered ones, made WITH HOLD.
        self.withhold = buffered
        self.closed = False
        self.rowcount = -1
        self._rows = None
        self._pos = 0
        self._live = None
        self._entry = None

    @property
    def __class__(self):
        # psycodict closes a search's cursor, and commits after a server-side
        # one, only for instances of psycopg's cursor classes.
        from psycopg import Cursor, ServerCursor
        return ServerCursor if self.withhold else Cursor

    @property
    def connection(self):
        return self._db.conn if self._real is None else self._real.connection

    def _get_real(self):
        if self._real is None:
            self._real = self._make_real()
        return self._real

    def __getattr__(self, name):
        return getattr(self._get_real(), name)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def execute(self, query, params=None, **kwargs):
        from psycopg import ClientCursor
        tape = self._tape
        if tape.edit_log == "not read":
            tape.read_edit_log(self._db.conn)
        sql = ClientCursor(self._db.conn).mogrify(query, params)
        key = hashlib.sha256(sql.encode()).hexdigest()
        self._drop_entry()
        self._rows, self._pos, self._live = None, 0, None
        found = tape.lookup(key)
        if type(found) is tuple:
            tape.stats["hit"] += 1
            self.rowcount, self._rows = found
            return self
        real = self._get_real()
        real.execute(query, params, **kwargs)
        self.rowcount = real.rowcount
        if real.description is None:
            # SET, BEGIN and the like: always run, never recorded
            return self
        tape.stats[found] += 1
        tape.log(found, sql)
        if tape.recording:
            self._entry = _Entry(key, sql, self.rowcount)
        if self.withhold:
            self._live = iter(real)
        else:
            self._rows = real.fetchall()
            self._finish_entry(self._rows)
        return self

    def _finish_entry(self, rows):
        if self._entry is not None:
            self._entry.add(rows)
            self._tape.write(self._entry)
            self._entry = None

    def _drop_entry(self):
        if self._entry is not None:
            self._tape.drop(self._entry)
            self._entry = None

    def _next(self):
        if self._live is not None:
            row = next(self._live, None)
            if row is None:
                self._live = None
                self._finish_entry(())
            elif self._entry is not None:
                self._entry.add((row,))
            return row
        if self._rows is None or self._pos == len(self._rows):
            return None
        self._pos += 1
        return self._rows[self._pos - 1]

    def fetchone(self):
        return self._next()

    def fetchmany(self, size=None):
        out = []
        for _ in range(size or 1):
            row = self._next()
            if row is None:
                break
            out.append(row)
        return out

    def fetchall(self):
        return list(iter(self._next, None))

    def __iter__(self):
        return iter(self._next, None)

    def close(self):
        self._drop_entry()
        if self._real is not None:
            self._real.close()
        self.closed = True


def install():
    """
    Route psycodict's cursors through the active tape, if any.  Safe to call
    more than once.
    """
    from psycodict.database import PostgresDatabase
    if getattr(PostgresDatabase._cursor, "dbtape", False):
        return
    original = PostgresDatabase._cursor

    def _cursor(self, buffered=False):
        if _tape is None:
            return original(self, buffered=buffered)
        return TapeCursor(_tape, self, buffered, lambda: original(self, buffered=buffered))
    _cursor.dbtape = True
    PostgresDatabase._cursor = _cursor


def _seed(label):
    # Random tests must ask for the same objects when replayed as when recorded.
    n = int.from_bytes(hashlib.sha256(("%s %s" % (_tape.seed, label)).encode()).digest()[:8], "big")
    random.seed(n)
    try:
        from sage.misc.randstate import set_random_seed
    except ImportError:
        pass
    else:
        set_random_seed(n)


def out_path(outdir, args):
    """
    The tape this process records to: one per process, merged afterwards, so
    that processes starting together never contend for a SQLite file.
    """
    os.makedirs(outdir, exist_ok=True)
    name = re.sub(r"[^\w.-]+", "_", " ".join(args))[-100:]
    return os.path.join(outdir, "%s-%s.sqlite" % (name, os.getpid()))


def pytest_configure(config):
    global _tape
    if not MODE:
        return
    if MODE not in ("record", "replay"):
        raise ValueError("DBTAPE_MODE must be record or replay, not %r" % MODE)
    out = None
    if MODE == "record":
        out = out_path(os.environ.get("DBTAPE_OUT", "dbtape-out"), config.args)
    tape = Tape(MODE, src=os.environ.get("DBTAPE_FILE", "dbtape.sqlite"), out=out,
                stale=os.environ.get("DBTAPE_STALE", "").split(),
                max_age=datetime.timedelta(days=float(os.environ.get("DBTAPE_MAX_AGE_DAYS", "14"))),
                misslog=os.environ.get("DBTAPE_MISSLOG"), seed=os.environ.get("DBTAPE_SEED"))
    if tape.src is None and not tape.recording:
        sys.stderr.write("dbtape: no usable tape, so every query goes to the database\n")
        return
    _tape = tape
    install()
    _seed("collection")


def pytest_runtest_setup(item):
    if _tape is not None:
        _tape.where = item.nodeid
        _seed(item.nodeid)


def pytest_terminal_summary(terminalreporter, config):
    if _tape is None:
        return
    s = _tape.stats
    line = "%s hits, %s misses, %s stale" % (s["hit"], s["miss"], s["stale"])
    if _tape.recording:
        line += ", %s recorded, %s unrecordable, %s read in part" % (s["recorded"], s["unrecordable"], s["unfinished"])
    line = "dbtape %s (%s): %s; edit log %s; %s" % (MODE, " ".join(config.args), line, _tape.edit_log,
                                                     _tape.fingerprint_status)
    terminalreporter.write_line(line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as F:
            F.write("- %s\n" % line)


def pytest_sessionfinish(session, exitstatus):
    if _tape is not None:
        # Failing tests still leave a usable tape; errors in collection,
        # interruptions and internal errors do not.
        _tape.finished = int(exitstatus) in (0, 1)


def pytest_unconfigure(config):
    if _tape is not None:
        _tape.close(complete=_tape.finished)


def merge(out, inputs):
    """
    Combine the tapes written by several test processes into one, keeping
    the newest recording of each query whatever the order of ``inputs``.
    Its base is the published tape they started from, and its fingerprints
    the ones they all recorded; either is "mixed" where they differ.
    """
    if os.path.exists(out):
        os.remove(out)
    conn = sqlite3.connect(out, isolation_level=None)
    create_tables(conn)
    conn.execute("CREATE TEMP TABLE seen AS SELECT * FROM tape WHERE 0")
    seeds = set()
    bases = set()
    metas = []
    for path in inputs:
        src = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        meta = dict(src.execute("SELECT k, v FROM meta"))
        if meta.get("format") != FORMAT:
            raise ValueError("%s has tape format %s, not %s" % (path, meta.get("format"), FORMAT))
        seeds.add(meta["seed"])
        bases.add(meta.get("base", ""))
        metas.append(meta)
        conn.execute("BEGIN")
        conn.executemany("INSERT INTO seen VALUES (?, ?, ?, ?, ?)", src.execute("SELECT * FROM tape"))
        conn.execute("COMMIT")
        src.close()
    if len(seeds) != 1:
        raise ValueError("tapes recorded with different seeds: %s" % sorted(seeds))
    conn.execute("BEGIN")
    seen = conn.cursor().execute("SELECT * FROM seen ORDER BY k")
    for _, recordings in itertools.groupby(seen, key=lambda rec: rec[0]):
        conn.execute("INSERT INTO tape VALUES (?, ?, ?, ?, ?)", choose(recordings))
    conn.execute("COMMIT")
    conn.execute("DROP TABLE seen")
    conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', ?), ('created', ?), ('base', ?)",
                 (FORMAT, seeds.pop(), datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                  bases.pop() if len(bases) == 1 else "mixed"))
    for k in sorted({k for meta in metas for k in meta if k.startswith("fingerprint ")}):
        values = {meta.get(k) for meta in metas}
        conn.execute("INSERT INTO meta VALUES (?, ?)", (k, values.pop() if len(values) == 1 else "mixed"))
    conn.execute("VACUUM")
    conn.close()


def describe(path):
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    for k, v in conn.execute("SELECT k, v FROM meta ORDER BY k"):
        print("%s: %s" % (k, v))
    n, size, oldest, newest = conn.execute(
        "SELECT count(*), sum(length(v)), min(r), max(r) FROM tape").fetchone()
    print("%s results, %.1f MB compressed, recorded %s to %s" % (n, (size or 0) / 1e6, oldest, newest))
    print("largest tables:")
    sizes = {}
    for tables, size in conn.execute("SELECT t, length(v) FROM tape"):
        for table in tables.split():
            sizes[table] = sizes.get(table, 0) + size
    for table, size in sorted(sizes.items(), key=lambda x: -x[1])[:15]:
        print("  %-40s %8.2f MB" % (table, size / 1e6))


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "merge":
        merge(sys.argv[2], sys.argv[3:])
    elif len(sys.argv) == 3 and sys.argv[1] == "describe":
        describe(sys.argv[2])
    else:
        sys.exit("usage: python3 conftest.py merge OUT TAPE [TAPE ...] | describe TAPE")
