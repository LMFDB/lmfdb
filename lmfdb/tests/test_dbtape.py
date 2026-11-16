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
    Answers the two queries Tape.read_edit_log makes.
    """

    def __init__(self, indexed=True, rows=(), error=None):
        self.indexed = indexed
        self.rows = list(rows)
        self.error = error
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
        if "pg_index" in query:
            self.result = [(1,)] if self.indexed else []
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

    def make_tape(self, entries):
        """
        A tape holding a dummy result for each (name, tables, recorded).
        """
        path = self.path("made.sqlite")
        conn = sqlite3.connect(path)
        dbtape.create_tables(conn)
        conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', '5')", (dbtape.FORMAT,))
        for name, tables, recorded in entries:
            conn.execute("INSERT INTO tape VALUES (?, 1, 1, ?, ?, 'q', ?)",
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
                    list(islice(db.nf_fields.search({"degree": 2}, "label", limit=None), 3)))
        recorded, path = self.record(queries)
        replay = dbtape.Tape("replay", src=path)
        with using(replay):
            replayed = queries()
            # Only three rows of this search were recorded.
            longer = list(islice(db.nf_fields.search({"degree": 2}, "label", limit=None), 5))
        self.assertEqual(replayed, recorded)
        self.assertEqual(longer[:3], recorded[3])
        self.assertEqual(len(longer), 5)
        self.assertGreater(replay.stats["hit"], 0)
        self.assertEqual(replay.stats["miss"], 0)
        self.assertEqual(replay.stats["partial"], 1)

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
        with using(dbtape.Tape("replay", src=path)):
            self.assertEqual(search(), (idle, idle))
        tape = dbtape.Tape("replay", src=path)
        self.assertIsInstance(dbtape.TapeCursor(tape, db, True, None), psycopg.ServerCursor)
        self.assertIsInstance(dbtape.TapeCursor(tape, db, False, None), psycopg.Cursor)

    def test_catalog_queries_follow_any_edit(self):
        _, path = self.record(db.refresh_tables)
        tape = dbtape.Tape("replay", src=path)
        rows = tape.src.execute("SELECT k, t, r FROM tape").fetchall()
        self.assertTrue(rows)
        for k, tables, recorded in rows:
            self.assertTrue(any(dbtape.is_catalog(t) for t in tables.split()), tables)
            self.assertFalse(tape.is_stale(k, tables.split(), recorded))
        # A table created later shows up only in what these queries return.
        tape.changes = {"a_new_table": dbtape._utcnow() + HOUR}
        for k, tables, recorded in rows:
            self.assertTrue(tape.is_stale(k, tables.split(), recorded), tables)
        tape = dbtape.Tape("replay", src=path, stale=["a_new_table"])
        for k, tables, recorded in rows:
            self.assertTrue(tape.is_stale(k, tables.split(), recorded), tables)

    def test_staleness(self):
        now = dbtape._utcnow()
        entries = [("edited", "ec_curvedata", now - DAY),
                   ("same family", "ec_curvedata_counts", now - DAY),
                   ("edited before", "nf_fields", now - DAY),
                   ("within clock skew", "g2c_curves", now - 2 * DAY + HOUR / 2),
                   ("catalog", "pg_class pg_namespace", now - DAY),
                   ("untouched", "lfunc_lfunctions", now - 3 * DAY)]
        path = self.make_tape(entries)

        def stale(tape):
            return {name for name, _, _ in entries if tape.lookup(key(name)) == "stale"}
        tape = dbtape.Tape("replay", src=path)
        self.assertEqual(stale(tape), set())
        tape.changes = {"ec_curvedata": now - 5 * HOUR, "nf_fields": now - 2 * DAY, "g2c_curves": now - 2 * DAY}
        self.assertEqual(stale(tape), {"edited", "same family", "within clock skew", "catalog"})
        tape = dbtape.Tape("replay", src=path, stale=["lfunc_lfunctions"])
        self.assertEqual(stale(tape), {"untouched", "catalog"})
        # Only recording refreshes results by age.
        tape = dbtape.Tape("replay", src=path, max_age=HOUR)
        self.assertEqual(stale(tape), set())
        tape = dbtape.Tape("record", src=path, out=self.path("out.sqlite"), max_age=HOUR)
        self.assertEqual(stale(tape), {name for name, _, _ in entries})
        tape.close()

    def test_edit_log(self):
        now = dbtape._utcnow()
        path = self.make_tape([("x", "ec_curvedata", now - DAY)])
        tape = dbtape.Tape("replay", src=path)
        tape.read_edit_log(FakeConnection(indexed=False))
        self.assertTrue(tape.edit_log.startswith("skipped"), tape.edit_log)
        self.assertIsNone(tape.changes)
        tape.read_edit_log(FakeConnection(error=psycopg.errors.InsufficientPrivilege("denied")))
        self.assertEqual(tape.edit_log, "unreadable (InsufficientPrivilege)")
        tape.read_edit_log(FakeConnection(rows=[("ec_curvedata_stats", now), ("ec_curvedata", now - HOUR)]))
        self.assertEqual(tape.changes, {"ec_curvedata": now})
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
        for name, body, finished in [("test_pass.py", "def test_x():\n    pass\n", True),
                                     ("test_fail.py", "def test_x():\n    assert False\n", True),
                                     ("test_broken.py", "raise RuntimeError('database unreachable')\n", False)]:
            with open(self.path(name), "w") as F:
                F.write(body)
            subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "conftest", "-p", "no:cacheprovider", name],
                           cwd=self.dir, env=env, capture_output=True)
            made = [f for f in os.listdir(outdir) if f.startswith(name)]
            self.assertEqual([f.endswith(".sqlite") for f in made], [finished], made)

    def test_merge(self):
        one, two = [("2.0.3.1",)], [("2.0.3.1",), ("2.0.4.1",)]
        early, late = "2026-01-01T08:00:00", "2026-01-01T09:00:00"

        def merged(*recordings, seeds=None, one_file=False):
            """
            Merge tapes holding ``recordings`` (complete, rows, recorded) of
            one query: a tape each, or all on one process's tape.
            """
            groups = [recordings] if one_file else [[rec] for rec in recordings]
            tapes = []
            for i, group in enumerate(groups):
                tapes.append(self.path("in%s.sqlite" % i))
                if os.path.exists(tapes[-1]):
                    os.remove(tapes[-1])
                conn = sqlite3.connect(tapes[-1])
                dbtape.create_tables(conn, recordings=True)
                conn.execute("INSERT INTO meta VALUES ('format', ?), ('seed', ?)",
                             (dbtape.FORMAT, seeds[i] if seeds else "5"))
                for complete, rows, recorded in group:
                    conn.execute("INSERT INTO tape VALUES ('k', ?, ?, ?, 't', 'q', ?)",
                                 (complete, len(rows), recorded, dbtape._pack(len(rows), rows)))
                conn.commit()
                conn.close()
            out = self.path("merged.sqlite")
            dbtape.merge(out, tapes)
            complete, recorded, blob = sqlite3.connect(out).execute("SELECT c, r, v FROM tape").fetchone()
            return complete, recorded, dbtape._unpack(blob)[1]

        # Of two complete results the newer wins, in either order: a row may
        # have been deleted in between.
        self.assertEqual(merged((1, two, early), (1, one, late)), (1, late, one))
        self.assertEqual(merged((1, one, late), (1, two, early)), (1, late, one))
        # A newer partial result gives way to an older one that agrees with it
        # and covers more,
        self.assertEqual(merged((1, two, early), (0, one, late)), (1, early, two))
        self.assertEqual(merged((0, one, late), (0, two, early)), (0, early, two))
        # but not to one that contradicts it,
        self.assertEqual(merged((1, [("2.0.7.1",)], early), (0, one, late)), (0, late, one))
        # nor to one that differs in type only (== would call these equal).
        flags = [({"flag": True},), ({"flag": False},)]
        for recs in [((1, flags, early), (0, [({"flag": 1},)], late)),
                     ((0, [({"flag": 1},)], late), (1, flags, early))]:
            self.assertEqual(merged(*recs)[:2], (0, late))
        # A recording is only kept if every later one agrees with it, however
        # the recordings are ordered or split between tapes.
        a = (1, [("a",), ("b",)], "08:00")
        cases = [
            # b was deleted by 09:00; a partial read at 10:00 cannot bring it back.
            ((a, (1, [("a",)], "09:00"), (0, [("a",)], "10:00")), (1, "09:00", [("a",)])),
            # The result changed at 09:00, so only the 10:00 read is current.
            ((a, (1, [("c",), ("d",)], "09:00"), (0, [("a",)], "10:00")), (0, "10:00", [("a",)])),
            # Nothing contradicts the 08:00 result, which covers the most.
            ((a, (0, [("a",), ("b",)], "09:00"), (0, [("a",)], "10:00")), (1, "08:00", [("a",), ("b",)])),
        ]
        for recordings, expected in cases:
            for order in itertools.permutations(recordings):
                self.assertEqual(merged(*order), expected, order)
                self.assertEqual(merged(*order, one_file=True), expected, order)
        with self.assertRaises(ValueError):
            merged((1, one, early), (1, one, late), seeds=("5", "6"))
