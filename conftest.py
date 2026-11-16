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
  combines them.  Without DBTAPE_FILE this records the whole run.
- Without DBTAPE_MODE this file does nothing.

A table counts as edited when userdb.dbrecord, where LMFDB's _log_db_change
logs every psycodict editing operation, has an entry for it later than the
recording.  DBTAPE_STALE lists further tables to treat as edited ("all" for
every table).  When recording, results older than DBTAPE_MAX_AGE_DAYS (7 to
21 days by default) are fetched again too, which catches edits made outside
psycodict.  See the "Query tape" section of Development.md.

This is a root conftest.py so that pytest loads it before any test module
imports lmfdb, which connects and reads the table metadata at import time.
It does not import pytest, so that `python3 conftest.py merge` runs anywhere.
"""

import base64
import datetime
import decimal
import hashlib
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
FORMAT = "1"

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


def _pack(rowcount, rows):
    """
    The stored form of a result.  Raises Unrecordable unless unpacking it
    gives back the same rows.
    """
    try:
        stored = [rowcount, [_encode(list(r)) for r in rows]]
        blob = json.dumps(stored, separators=(",", ":")).encode()
        same = _same(list(rows), _unpack(blob)[1])
    except Unrecordable:
        raise
    except Exception as err:
        raise Unrecordable("%s: %s" % (type(err).__name__, err))
    if not same:
        raise Unrecordable("round trip")
    return zlib.compress(blob, 6)


def _unpack(blob):
    if blob[:1] != b"[":
        blob = zlib.decompress(blob)
    rowcount, rows = json.loads(blob)
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


def _family(table):
    # psycodict rebuilds a table's _counts and _stats along with it.
    for suffix in ("_counts", "_stats"):
        if table.endswith(suffix):
            return table[:-len(suffix)]
    return table


def create_tables(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    # k: hash of the SQL q; c: whether all n rows of the result are stored;
    # r: when it was recorded (UTC); t: the tables q reads; v: the result
    conn.execute("CREATE TABLE IF NOT EXISTS tape "
                 "(k TEXT PRIMARY KEY, c INTEGER, n INTEGER, r TEXT, t TEXT, q TEXT, v BLOB)")


def upsert(conn, row):
    # Keep whichever recording of a query covers more of its result, then the newer.
    conn.execute(
        "INSERT INTO tape VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(k) DO UPDATE "
        "SET c = excluded.c, n = excluded.n, r = excluded.r, t = excluded.t, v = excluded.v "
        "WHERE excluded.c > tape.c OR (excluded.c = tape.c AND (excluded.n > tape.n "
        "OR (excluded.n = tape.n AND excluded.r >= tape.r)))",
        row)


class _Entry:
    """
    A result being recorded.  Rows from a server-side cursor are recorded as
    the caller reads them, so a long result read only in part is stored in part.
    """

    def __init__(self, key, sql, rowcount, rows, complete):
        self.key = key
        self.sql = sql
        self.rowcount = rowcount
        self.rows = rows
        self.complete = complete
        self.recorded = _utcnow().isoformat(timespec="seconds")


class Tape:
    """
    A tape being replayed (``src``, if it exists) and, in record mode, the
    tape being written (``out``, a file only this process writes to).
    """

    def __init__(self, mode, src=None, out=None, stale=(), max_age=datetime.timedelta(days=14),
                 misslog=None, seed=None):
        self.mode = mode
        self.forced = set(stale)
        self.max_age = max_age
        self.misslog = misslog
        self.where = "collection"
        self.stats = dict.fromkeys(["hit", "miss", "stale", "partial", "recorded", "unrecordable"], 0)
        self.pending = set()
        self.copied = set()
        self.changes = None
        self.edit_log = "not read"
        self.since = None
        self.now = _utcnow()
        self.src = None
        self.out = None
        meta = {}
        if src is not None and os.path.exists(src):
            self.src = sqlite3.connect("file:%s?mode=ro&immutable=1" % src, uri=True)
            meta = dict(self.src.execute("SELECT k, v FROM meta"))
            if meta.get("format") != FORMAT:
                sys.stderr.write("dbtape: ignoring %s, which has format %s rather than %s\n"
                                 % (src, meta.get("format"), FORMAT))
                self.src, meta = None, {}
        self.seed = meta.get("seed")
        if self.seed is None or (mode == "record" and "all" in self.forced):
            # A full recording is free to pick new random objects.
            self.seed = seed or str(int(time.time()))
        if self.src is not None:
            oldest = self.src.execute("SELECT min(r) FROM tape").fetchone()[0]
            if oldest is not None:
                self.since = datetime.datetime.fromisoformat(oldest) - CLOCK_SKEW
        if mode == "record":
            self.out = sqlite3.connect(out, isolation_level=None)
            self.out.execute("PRAGMA synchronous=OFF")
            create_tables(self.out)
            self.out.execute("INSERT OR IGNORE INTO meta VALUES ('format', ?), ('seed', ?)", (FORMAT, self.seed))

    @property
    def recording(self):
        return self.mode == "record" and self.out is not None

    def close(self):
        if self.recording:
            self.flush()
            self.out.close()
            self.out = None

    def read_edit_log(self, conn):
        """
        Find which tables were edited since the oldest result on the tape was
        recorded.  This runs once, on psycodict's connection, before its first
        query.  The log has no index unless one is added for this, and is far
        too large to scan from every test process, so without one it is skipped.
        """
        if self.since is None:
            self.edit_log = "not needed"
            return
        indexed = ("SELECT 1 FROM pg_index i JOIN pg_attribute a "
                   "ON a.attrelid = i.indrelid AND a.attnum = i.indkey[0] "
                   "WHERE i.indrelid = 'userdb.dbrecord'::regclass AND a.attname = 'time'")
        changed = ("SELECT tablename, max(time) FROM userdb.dbrecord "
                   "WHERE time > %s GROUP BY tablename")
        try:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(indexed)
                    if cur.fetchone() is None:
                        self.edit_log = "skipped (userdb.dbrecord has no index on time)"
                        return
                    cur.execute(changed, [self.since])
                    rows = cur.fetchall()
        except Exception as err:
            self.edit_log = "unreadable (%s)" % type(err).__name__
            return
        self.edit_log = "read (%s tables edited)" % len(rows)
        self.changes = {}
        for table, when in rows:
            if table and when:
                family = _family(table)
                self.changes[family] = max(self.changes.get(family, when), when)

    def is_stale(self, key, tables, recorded):
        if "all" in self.forced:
            return True
        families = {_family(t) for t in tables}
        catalog = any(is_catalog(t) for t in tables)
        if families & self.forced or (catalog and self.forced):
            return True
        recorded = datetime.datetime.fromisoformat(recorded)
        if self.recording:
            # Spread expiry over 0.5 to 1.5 times max_age so a tape recorded
            # all at once is refreshed a little at a time.
            spread = 0.5 + int(key[:8], 16) / 2**32
            if self.now - recorded > self.max_age * spread:
                return True
        if not self.changes:
            return False
        cutoff = recorded - CLOCK_SKEW
        if catalog:
            return max(self.changes.values()) > cutoff
        return any(f in self.changes and self.changes[f] > cutoff for f in families)

    def lookup(self, key):
        """
        The stored result for ``key`` as (rowcount, rows, complete), or why
        there is none to use: "miss" or "stale".
        """
        if self.src is None:
            return "miss"
        row = self.src.execute("SELECT c, r, t, v FROM tape WHERE k = ?", (key,)).fetchone()
        if row is None:
            return "miss"
        complete, recorded, tables, blob = row
        if self.is_stale(key, tables.split(), recorded):
            return "stale"
        if self.recording and key not in self.copied:
            self.copied.add(key)
            upsert(self.out, self.src.execute("SELECT * FROM tape WHERE k = ?", (key,)).fetchone())
        rowcount, rows = _unpack(blob)
        return rowcount, rows, bool(complete)

    def track(self, entry):
        self.pending.add(entry)
        if entry.complete:
            self.write(entry)

    def write(self, entry):
        self.pending.discard(entry)
        try:
            blob = _pack(entry.rowcount, entry.rows)
        except Unrecordable as err:
            self.stats["unrecordable"] += 1
            self.log("unrecordable (%s)" % err, entry.sql)
            return
        upsert(self.out, (entry.key, int(entry.complete), len(entry.rows), entry.recorded,
                          " ".join(tables_read(entry.sql)), entry.sql, blob))
        self.stats["recorded"] += 1

    def flush(self):
        for entry in list(self.pending):
            self.write(entry)

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
        self._complete = True
        self._live = None
        self._replayed = None
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
        self._finish_entry()
        self._pos = 0
        self._live = None
        self._replayed = None
        found = tape.lookup(key)
        if type(found) is tuple:
            tape.stats["hit"] += 1
            self.rowcount, self._rows, self._complete = found
            self._replayed = (query, params, kwargs, key, sql)
            return self
        real = self._get_real()
        real.execute(query, params, **kwargs)
        self.rowcount = real.rowcount
        if real.description is None:
            # SET, BEGIN and the like: always run, never recorded
            self._rows, self._complete = None, True
            return self
        tape.stats[found] += 1
        tape.log(found, sql)
        if self.withhold:
            self._rows, self._complete, self._live = [], False, iter(real)
        else:
            self._rows, self._complete = real.fetchall(), True
        self._record(key, sql)
        return self

    def _record(self, key, sql):
        if self._tape.recording:
            self._entry = _Entry(key, sql, self.rowcount, self._rows, self._complete)
            self._tape.track(self._entry)

    def _finish_entry(self):
        if self._entry is not None and self._entry in self._tape.pending:
            self._tape.write(self._entry)
        self._entry = None

    def _next(self):
        rows = self._rows
        if rows is None:
            return None
        if self._pos < len(rows):
            self._pos += 1
            return rows[self._pos - 1]
        if self._complete:
            return None
        if self._live is None:
            # Read past the stored part of a result: rerun it live and skip
            # the rows already served.
            self._tape.stats["partial"] += 1
            query, params, kwargs, key, sql = self._replayed
            self._tape.log("partial", sql)
            real = self._get_real()
            real.execute(query, params, **kwargs)
            self._live = iter(real)
            for _ in range(len(rows)):
                next(self._live, None)
            self._record(key, sql)
        try:
            row = next(self._live)
        except StopIteration:
            self._complete = True
            if self._entry is not None:
                self._entry.complete = True
                self._finish_entry()
            return None
        rows.append(row)
        self._pos += 1
        return row

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
        self._finish_entry()
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
    if _tape.recording:
        _tape.flush()
    s = _tape.stats
    line = "%s hits, %s misses, %s stale, %s partial" % (s["hit"], s["miss"], s["stale"], s["partial"])
    if _tape.recording:
        line += ", %s recorded, %s unrecordable" % (s["recorded"], s["unrecordable"])
    line = "dbtape %s (%s): %s; edit log %s" % (MODE, " ".join(config.args), line, _tape.edit_log)
    terminalreporter.write_line(line)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as F:
            F.write("- %s\n" % line)


def pytest_unconfigure(config):
    if _tape is not None:
        _tape.close()


def merge(out, inputs):
    """
    Combine the tapes written by several test processes into one.
    """
    if os.path.exists(out):
        os.remove(out)
    conn = sqlite3.connect(out, isolation_level=None)
    create_tables(conn)
    seeds = set()
    for path in inputs:
        src = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
        meta = dict(src.execute("SELECT k, v FROM meta"))
        if meta.get("format") != FORMAT:
            raise ValueError("%s has tape format %s, not %s" % (path, meta.get("format"), FORMAT))
        seeds.add(meta["seed"])
        conn.execute("BEGIN")
        for row in src.execute("SELECT * FROM tape"):
            upsert(conn, row)
        conn.execute("COMMIT")
        src.close()
    if len(seeds) != 1:
        raise ValueError("tapes recorded with different seeds: %s" % sorted(seeds))
    conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', ?), ('created', ?)",
                 (FORMAT, seeds.pop(), datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")))
    conn.execute("VACUUM")
    conn.close()


def describe(path):
    conn = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    for k, v in conn.execute("SELECT k, v FROM meta ORDER BY k"):
        print("%s: %s" % (k, v))
    n, size, partial, oldest, newest = conn.execute(
        "SELECT count(*), sum(length(v)), sum(1 - c), min(r), max(r) FROM tape").fetchone()
    print("%s results, %.1f MB compressed, %s partial, recorded %s to %s"
          % (n, (size or 0) / 1e6, partial or 0, oldest, newest))
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
