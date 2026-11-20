# Author: David Roe
# Tests for the query tape: conftest.py at the top of the repository, which
# lets CI replay database results instead of fetching them from devmirror.

import datetime
import decimal
import hashlib
import itertools
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from itertools import islice

import psycopg
from psycopg.pq import TransactionStatus

import conftest as dbtape
from lmfdb import db

HOUR = datetime.timedelta(hours=1)
DAY = datetime.timedelta(days=1)


def key(name):
    return hashlib.sha256(name.encode()).hexdigest()


@contextmanager
def using(tape):
    """
    Route psycodict's queries through ``tape``, whatever the plugin is doing
    for the rest of the run.
    """
    dbtape.install()
    old, dbtape._tape = dbtape._tape, tape
    try:
        yield tape
    finally:
        tape.close()
        dbtape._tape = old


def replaying(path):
    """
    A replay of the tape ``path`` that does not read the edit log, by which
    an edit made in the hour before a test would make what it just recorded
    stale.
    """
    tape = dbtape.Tape("replay", src=path)
    tape.edit_log = "not read in this test"
    return tape


def session_state():
    """
    Whether psycodict left a transaction open, and how many cursors.  The
    status has to be read first: counting cursors runs a transaction itself.
    """
    return db.conn.info.transaction_status, open_cursors()


def open_cursors():
    with db.conn.transaction():
        with db.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM pg_cursors")
            return cur.fetchone()[0]


class FakeConnection:
    """
    Answers the queries Tape.read_edit_log makes.  A table missing from
    ``fingerprints`` cannot be fingerprinted.
    """

    def __init__(self, rows=(), error=None, fingerprints={}, privileged=False):
        self.rows = list(rows)
        self.error = error
        self.fingerprints = fingerprints
        self.privileged = privileged
        self.result = []

    @contextmanager
    def transaction(self):
        yield

    @contextmanager
    def cursor(self):
        yield self

    def execute(self, query, params=None):
        if self.error is not None:
            raise self.error
        tables = [t for t, q in dbtape.FINGERPRINTS.items() if q == query]
        if "has_column_privilege" in query:
            self.result = [("tester", self.privileged)]
        elif tables:
            if tables[0] not in self.fingerprints:
                raise psycopg.errors.InsufficientPrivilege("denied")
            self.result = [self.fingerprints[tables[0]]]
        else:
            self.result = self.rows

    def fetchone(self):
        return self.result[0] if self.result else None

    def fetchall(self):
        return self.result


class DbTapeTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def path(self, name):
        return os.path.join(self.dir, name)

    def make_tape(self, entries, meta={}):
        """
        A tape holding a dummy result for each (name, tables, recorded).
        """
        path = self.path("made.sqlite")
        conn = sqlite3.connect(path)
        dbtape.create_tables(conn)
        conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', '5')", (dbtape.FORMAT,))
        conn.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
        for name, tables, recorded in entries:
            conn.execute("INSERT INTO tape VALUES (?, ?, ?, 'q', ?)",
                         (key(name), recorded.isoformat(timespec="seconds"), tables, dbtape._pack(1, [(1,)])))
        conn.commit()
        conn.close()
        return path

    def record(self, action):
        """
        Record ``action()`` into a fresh tape; return its result and the tape's path.
        """
        rec = dbtape.Tape("record", out=self.path("rec.sqlite"), seed="1")
        with using(rec):
            result = action()
        self.assertEqual(rec.stats["unrecordable"], 0)
        self.recorded_stats = rec.stats
        dbtape.merge(self.path("tape.sqlite"), [self.path("rec.sqlite")])
        return result, self.path("tape.sqlite")

    def test_values_round_trip(self):
        from sage.all import Integer, QQ, NumberField, polygen
        from psycodict.encoding import numeric_converter
        x = polygen(QQ)
        K = NumberField(x**2 + 1, "i")
        values = [None, True, 0, 2**100, 1.5, float("inf"), "~t", [1, [2, "x"]], (1, 2),
                  {"a": 1, "~t": 2}, {1: "a"}, decimal.Decimal("1.50"),
                  datetime.datetime(2026, 1, 2, 3, 4, 5, 6), datetime.date(2026, 1, 2), b"\x00\xff",
                  Integer(12), numeric_converter("3.14159265358979323846"), numeric_converter("0.000"),
                  QQ(3) / 7, x**2 - 2, K.gen() + 1]
        for v in values:
            back = dbtape._unpack(dbtape._pack(1, [(v,)]))[1][0][0]
            self.assertTrue(dbtape._same(v, back), (v, back))
        self.assertFalse(dbtape._same(numeric_converter("1.50"), numeric_converter("1.5")))
        self.assertFalse(dbtape._same(1, Integer(1)))

    def test_record_then_replay(self):
        def queries():
            return (db.nf_fields.lookup("2.0.3.1", ["label", "disc_abs", "coeffs"]),
                    list(db.nf_fields.search({"degree": 2, "disc_abs": {"$lte": 20}}, ["label", "class_number"])),
                    db.nf_fields.count({"degree": 2, "disc_abs": {"$lte": 20}}),
                    list(db.nf_fields.search({"degree": 2, "disc_abs": {"$lte": 20}}, "label", limit=None)),
                    list(islice(db.nf_fields.search({"degree": 2}, "label", limit=None), 3)))
        recorded, path = self.record(queries)
        self.assertEqual(self.recorded_stats["unfinished"], 1)
        replay = replaying(path)
        with using(replay):
            replayed = queries()
            longer = list(islice(db.nf_fields.search({"degree": 2}, "label", limit=None), 5))
        self.assertEqual(replayed, recorded)
        self.assertEqual(longer[:3], recorded[4])
        self.assertEqual(len(longer), 5)
        self.assertGreater(replay.stats["hit"], 0)
        # The search read only in part was not recorded, so it ran live both times.
        self.assertEqual(replay.stats["miss"], 2)

    def test_rows_are_recorded_as_fetched(self):
        def search(limit):
            out = []
            for rec in db.nf_fields.search({"degree": 2, "disc_abs": {"$lte": 20}}, ["label", "coeffs"], limit=limit):
                out.append(str(rec))
                # As lmfdb/utils/uploader.py does with a jsonb column
                rec["coeffs"].append(99)
            return out
        for limit in [None, 100]:
            recorded, path = self.record(lambda: search(limit))
            with using(replaying(path)):
                self.assertEqual(search(limit), recorded)

    def test_server_side_cursors_are_closed(self):
        def search():
            it = db.nf_fields.search({"degree": 2}, "label", limit=None)
            next(it)
            it.close()
            stopped = session_state()
            list(db.nf_fields.search({"degree": 2, "disc_abs": {"$lte": 20}}, "label", limit=None))
            return stopped, session_state()
        idle = (TransactionStatus.IDLE, 0)
        live, path = self.record(search)
        self.assertEqual(live, (idle, idle))
        with using(replaying(path)):
            self.assertEqual(search(), (idle, idle))
        tape = dbtape.Tape("replay", src=path)
        self.assertIsInstance(dbtape.TapeCursor(tape, db, True, None), psycopg.ServerCursor)
        self.assertIsInstance(dbtape.TapeCursor(tape, db, False, None), psycopg.Cursor)

    def test_catalog_queries_follow_any_edit(self):
        _, path = self.record(db.refresh_tables)
        tape = dbtape.Tape("replay", src=path)
        rows = tape.src.execute("SELECT t, r FROM tape").fetchall()
        self.assertTrue(rows)
        for tables, recorded in rows:
            self.assertTrue(any(dbtape.is_catalog(t) for t in tables.split()), tables)
            self.assertFalse(tape.is_stale(tables.split(), recorded))
        # A table created later shows up only in what these queries return.
        tape.changes = {"a_new_table": dbtape._utcnow() + HOUR}
        for tables, recorded in rows:
            self.assertTrue(tape.is_stale(tables.split(), recorded), tables)
        tape = dbtape.Tape("replay", src=path, stale=["a_new_table"])
        for tables, recorded in rows:
            self.assertTrue(tape.is_stale(tables.split(), recorded), tables)

    def test_staleness(self):
        now = dbtape._utcnow()
        entries = [("edited", "ec_curvedata", now - DAY),
                   ("same family", "ec_curvedata_counts", now - DAY),
                   ("edited before", "nf_fields", now - DAY),
                   ("within clock skew", "g2c_curves", now - 2 * DAY + HOUR / 2),
                   ("catalog", "pg_class pg_namespace", now - DAY),
                   ("older catalog", "meta_tables", now - 3 * DAY),
                   ("untouched", "lfunc_lfunctions", now - 3 * DAY),
                   # a search table whose own name ends in _stats
                   ("stats-named", "hgcwa_per_group_stats", now - DAY),
                   ("its stats", "hgcwa_per_group_stats_stats", now - DAY)]
        path = self.make_tape(entries)

        def stale(tape):
            return {name for name, _, _ in entries if tape.lookup(key(name)) == "stale"}
        tape = dbtape.Tape("replay", src=path)
        self.assertEqual(stale(tape), set())
        tape.read_edit_log(FakeConnection(rows=[("ec_curvedata", now - 5 * HOUR), ("nf_fields", now - 2 * DAY),
                                                ("g2c_curves", now - 2 * DAY)]))
        self.assertEqual(stale(tape), {"edited", "same family", "within clock skew", "catalog", "older catalog"})
        tape.read_edit_log(FakeConnection(rows=[("hgcwa_per_group_stats", now - 5 * HOUR)]))
        self.assertEqual(stale(tape), {"stats-named", "its stats", "catalog", "older catalog"})
        # The catalog results go stale together, even when only the older
        # ones were recorded before the edit.
        tape.read_edit_log(FakeConnection(rows=[("mf_newforms", now - 2 * DAY)]))
        self.assertEqual(stale(tape), {"catalog", "older catalog"})
        tape = dbtape.Tape("replay", src=path, stale=["lfunc_lfunctions"])
        self.assertEqual(stale(tape), {"untouched", "catalog", "older catalog"})
        tape = dbtape.Tape("replay", src=path, stale=["hgcwa_per_group_stats"])
        self.assertEqual(stale(tape), {"stats-named", "its stats", "catalog", "older catalog"})
        # Age alone makes nothing stale, recording or not.
        tape = dbtape.Tape("record", src=path, out=self.path("out.sqlite"))
        tape.now += 1000 * DAY
        tape.read_edit_log(FakeConnection(fingerprints={"kwl_knowls": (0, 0)}))
        self.assertEqual(stale(tape), set())
        self.assertEqual(tape.problems, [])
        tape.close()

    def test_fingerprints(self):
        # Knowls are edited without the edit log.
        now = dbtape._utcnow()
        entries = [("knowl", "kwl_knowls", now - DAY), ("field", "nf_fields", now - DAY),
                   ("catalog", "meta_tables", now - DAY)]
        path = self.make_tape(entries, {"fingerprint kwl_knowls": "1 10"})

        def stale(tape):
            return {name for name, _, _ in entries if tape.lookup(key(name)) == "stale"}
        tape = dbtape.Tape("replay", src=path)
        tape.read_edit_log(FakeConnection(fingerprints={"kwl_knowls": (1, 10)}))
        self.assertEqual(stale(tape), set())
        tape = dbtape.Tape("replay", src=path)
        tape.read_edit_log(FakeConnection(fingerprints={"kwl_knowls": (1, 11)}))
        # The catalog only follows logged edits.
        self.assertEqual(stale(tape), {"knowl"})
        self.assertEqual(tape.fingerprint_status, "kwl_knowls changed")
        # A recording keeps the fingerprint it read,
        out = self.path("out.sqlite")
        tape = dbtape.Tape("record", src=path, out=out)
        tape.read_edit_log(FakeConnection(fingerprints={"kwl_knowls": (1, 11)}))
        tape.close()
        meta = dict(sqlite3.connect(out).execute("SELECT k, v FROM meta"))
        self.assertEqual(meta["fingerprint kwl_knowls"], "1 11")
        # and one that cannot read it is not kept.
        tape = dbtape.Tape("record", src=path, out=self.path("out2.sqlite"))
        tape.read_edit_log(FakeConnection())
        self.assertEqual(stale(tape), set())
        self.assertEqual(tape.problems, ["the kwl_knowls fingerprint is unreadable (InsufficientPrivilege)"])
        tape.close()

    def test_private_queries(self):
        # Accounts and the edit log are never put on a tape, which is published.
        for sql in ["SELECT username FROM userdb.users", 'SELECT 1 FROM "userdb"."users"',
                    "SELECT 1 FROM nf_fields JOIN userdb.dbrecord ON true"]:
            self.assertTrue(dbtape.is_private(sql), sql)
        for sql in ["SELECT 'userdb' FROM nf_fields", "SELECT x FROM my_userdb.t"]:
            self.assertFalse(dbtape.is_private(sql), sql)
        from lmfdb.utils.psycopg_compat import SQL

        def lookup():
            return list(db._execute(SQL("SELECT username, full_name FROM userdb.users WHERE username = %s"),
                                    ["cremona"]))
        live, path = self.record(lookup)
        self.assertEqual(self.recorded_stats["recorded"], 0)
        self.assertEqual(sqlite3.connect(path).execute("SELECT count(*) FROM tape").fetchone()[0], 0)
        with using(replaying(path)) as tape:
            self.assertEqual(lookup(), live)
        self.assertEqual((tape.stats["hit"], tape.stats["miss"]), (0, 0))
        # Merging drops any such entry a process tape holds.
        proc = self.write_recordings("private.sqlite", [([("x",)], "08:00")])
        conn = sqlite3.connect(proc)
        conn.execute("UPDATE tape SET q = 'SELECT password FROM userdb.users'")
        conn.commit()
        conn.close()
        dbtape.merge(self.path("merged.sqlite"), [proc])
        self.assertEqual(sqlite3.connect(self.path("merged.sqlite")).execute("SELECT count(*) FROM tape").fetchone()[0], 0)

    def test_recording_role(self):
        # Recording as a role that can read passwords is refused; replaying is not.
        tape = dbtape.Tape("record", out=self.path("out.sqlite"))
        with self.assertRaises(RuntimeError):
            tape.read_edit_log(FakeConnection(privileged=True, fingerprints={"kwl_knowls": (1, 10)}))
        tape.close(complete=False)
        tape = dbtape.Tape("record", out=self.path("out.sqlite"))
        tape.read_edit_log(FakeConnection(fingerprints={"kwl_knowls": (1, 10)}))
        tape.close()
        tape = dbtape.Tape("replay", src=self.path("out.sqlite"))
        tape.read_edit_log(FakeConnection(privileged=True, fingerprints={"kwl_knowls": (1, 10)}))

    def test_edit_log(self):
        now = dbtape._utcnow()
        path = self.make_tape([("x", "ec_curvedata", now - DAY)])
        tape = dbtape.Tape("replay", src=path)
        tape.read_edit_log(FakeConnection(error=psycopg.errors.InsufficientPrivilege("denied")))
        self.assertEqual(tape.edit_log, "unreadable (InsufficientPrivilege)")
        self.assertIsNone(tape.changes)
        self.assertIn("the edit log is unreadable (InsufficientPrivilege)", tape.problems)
        tape.read_edit_log(FakeConnection(rows=[("ec_curvedata", now - HOUR), ("ec_curvedata_counts", now)]))
        self.assertEqual(tape.changes, {"ec_curvedata": now - HOUR, "ec_curvedata_stats": now - HOUR,
                                        "ec_curvedata_counts": now, "ec_curvedata_counts_counts": now,
                                        "ec_curvedata_counts_stats": now})
        # Whatever the real database allows, reading the log leaves the connection usable.
        tape.read_edit_log(db.conn)
        self.assertTrue(db.nf_fields.exists({"label": "2.0.3.1"}))

    def test_processes_record_to_their_own_files(self):
        outdir = self.path("out")
        code = ("import sys; sys.path.insert(0, %r); import conftest as d; "
                "d.Tape('record', out=d.out_path(%r, [sys.argv[1]]), seed='1').close()"
                % (os.path.dirname(dbtape.__file__), outdir))
        for i in range(3):
            procs = [subprocess.Popen([sys.executable, "-c", code, "round%s.py" % i]) for _ in range(4)]
            self.assertEqual([p.wait() for p in procs], [0] * 4)
        tapes = [os.path.join(outdir, f) for f in os.listdir(outdir)]
        self.assertEqual(len(tapes), 12)
        dbtape.merge(self.path("merged.sqlite"), tapes)

    def test_unfinished_runs_leave_no_tape(self):
        outdir = self.path("out")
        env = {k: v for k, v in os.environ.items() if not k.startswith("DBTAPE_") and k != "GITHUB_STEP_SUMMARY"}
        env.update(DBTAPE_MODE="record", DBTAPE_OUT=outdir, DBTAPE_SEED="1",
                   PYTHONPATH=os.pathsep.join(filter(None, [os.path.dirname(dbtape.__file__), env.get("PYTHONPATH")])))
        # A test that runs into a database it cannot check staleness on
        unchecked = ("import conftest\n"
                     "class Unreadable:\n"
                     "    def transaction(self):\n"
                     "        raise RuntimeError('permission denied')\n"
                     "def test_x():\n"
                     "    conftest._tape.read_edit_log(Unreadable())\n")
        for name, body, finished, status in [("test_pass.py", "def test_x():\n    pass\n", True, 0),
                                             ("test_fail.py", "def test_x():\n    assert False\n", True, 1),
                                             ("test_broken.py", "raise RuntimeError('database unreachable')\n", False, 2),
                                             ("test_unchecked.py", unchecked, False, 1)]:
            with open(self.path(name), "w") as F:
                F.write(body)
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "conftest", "-p", "no:cacheprovider", name],
                                 cwd=self.dir, env=env, capture_output=True, text=True)
            made = [f for f in os.listdir(outdir) if f.startswith(name)]
            self.assertEqual([f.endswith(".sqlite") for f in made], [finished], made)
            self.assertEqual(run.returncode, status, run.stdout)
        self.assertIn("fingerprint is unreadable", run.stdout)

    def write_recordings(self, name, recordings, seed="5", meta={}):
        """
        A process's tape holding ``recordings`` (rows, recorded) of one query.
        """
        path = self.path(name)
        if os.path.exists(path):
            os.remove(path)
        conn = sqlite3.connect(path)
        dbtape.create_tables(conn, recordings=True)
        conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', ?)", (dbtape.FORMAT, seed))
        conn.executemany("INSERT INTO meta VALUES (?, ?)", meta.items())
        for rows, recorded in recordings:
            conn.execute("INSERT INTO tape VALUES ('k', ?, 'nf_fields', 'q', ?)",
                         (recorded, dbtape._pack(len(rows), rows)))
        conn.commit()
        conn.close()
        return path

    def test_merge(self):
        def merged(*recordings, one_file=False):
            groups = [recordings] if one_file else [[rec] for rec in recordings]
            tapes = [self.write_recordings("in%s.sqlite" % i, group) for i, group in enumerate(groups)]
            out = self.path("merged.sqlite")
            dbtape.merge(out, tapes)
            recorded, blob = sqlite3.connect(out).execute("SELECT r, v FROM tape").fetchone()
            return recorded, dbtape._unpack(blob)[1]

        a, b, c = [("a",)], [("a",), ("b",)], [("b",), ("a",)]
        cases = [
            # The newest recording wins: a row may have been added or deleted.
            ([(b, "08:00"), (a, "09:00")], ("09:00", a)),
            ([(a, "08:00"), (b, "09:00")], ("09:00", b)),
            # Recordings made in the same second (an unordered search, say)
            # merge to the same result whatever their order.
            ([(b, "08:00"), (c, "08:00"), (a, "07:00")], ("08:00", max(b, c, key=lambda rows: dbtape._pack(2, rows)))),
        ]
        for recordings, expected in cases:
            for order in itertools.permutations(recordings):
                self.assertEqual(merged(*order), expected, order)
                self.assertEqual(merged(*order, one_file=True), expected, order)
        with self.assertRaises(ValueError):
            dbtape.merge(self.path("merged.sqlite"), [self.write_recordings("x.sqlite", [(a, "08:00")], seed="5"),
                                                      self.write_recordings("y.sqlite", [(a, "08:00")], seed="6")])
        # Fingerprints are kept where every process recorded the same one.
        fp = {"fingerprint kwl_knowls": "1 10", "fingerprint other": "2 ab"}
        dbtape.merge(self.path("merged.sqlite"), [
            self.write_recordings("x.sqlite", [(a, "08:00")], meta=fp),
            self.write_recordings("y.sqlite", [(a, "08:00")], meta={"fingerprint kwl_knowls": "1 11"})])
        meta = dict(sqlite3.connect(self.path("merged.sqlite")).execute("SELECT k, v FROM meta"))
        self.assertEqual((meta["fingerprint kwl_knowls"], meta["fingerprint other"]), ("mixed", "mixed"))
        dbtape.merge(self.path("merged.sqlite"), [self.write_recordings("x.sqlite", [(a, "08:00")], meta=fp),
                                                  self.write_recordings("y.sqlite", [(a, "08:00")], meta=fp)])
        meta = dict(sqlite3.connect(self.path("merged.sqlite")).execute("SELECT k, v FROM meta"))
        self.assertEqual(meta["fingerprint kwl_knowls"], "1 10")

    def test_base(self):
        # Publishing compares a recording's base with the published tape's
        # creation time, to keep a tape published while it was recording.
        def meta(path):
            return dict(sqlite3.connect(path).execute("SELECT k, v FROM meta"))
        first = self.path("first.sqlite")
        dbtape.Tape("record", out=first, seed="1").close()
        self.assertEqual(meta(first)["base"], "")
        dbtape.merge(self.path("published.sqlite"), [first])
        published = meta(self.path("published.sqlite"))
        self.assertEqual(published["base"], "")
        second = self.path("second.sqlite")
        dbtape.Tape("record", src=self.path("published.sqlite"), out=second).close()
        self.assertEqual(meta(second)["base"], published["created"])
        dbtape.merge(self.path("next.sqlite"), [second])
        self.assertEqual(meta(self.path("next.sqlite"))["base"], published["created"])
        dbtape.merge(self.path("next.sqlite"), [first, second])
        self.assertEqual(meta(self.path("next.sqlite"))["base"], "mixed")

    def test_command_line(self):
        tapes = [self.write_recordings("in%s.sqlite" % i, [([("a",)], "2026-01-01T0%s:00:00" % i)]) for i in range(2)]
        out = self.path("merged.sqlite")

        def run(*args):
            return subprocess.run([sys.executable, dbtape.__file__] + list(args), capture_output=True, text=True)
        self.assertEqual(run("merge", out, *tapes).returncode, 0)
        described = run("describe", out)
        self.assertEqual(described.returncode, 0, described.stderr)
        self.assertIn("seed: 5", described.stdout)
        self.assertIn("1 results, 0.0 MB compressed, recorded 2026-01-01T01:00:00 to 2026-01-01T01:00:00",
                      described.stdout)
        self.assertIn("nf_fields", described.stdout)
        self.assertIn("usage", run("describe").stderr)
