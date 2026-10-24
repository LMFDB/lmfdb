r"""
Read-only checks before and after loading belyi_galmap_dessins.

Usage, from the LMFDB root:

    sage -python scripts/belyi/check_dessins.py --before [--dump PATH]
    sage -python scripts/belyi/check_dessins.py --after

--before checks that the account, the database and this machine are ready for
upload_dessins.py to create the table, and that the dump (by default
scripts/belyi/belyi_images.txt.gz) is the reviewed one.  --after checks the
loaded rows themselves, not cached counts, against belyi_galmaps, along with
the table's metadata, grants and knowls.  The default --dump path is where
the dump lived on the upload branch, and --before is only needed for a new load.

The script never writes: it sets default_transaction_read_only, a 30s
statement timeout and a 3s lock timeout through PGOPTIONS before connecting,
and stops unless postgres reports the session read-only.  Each check prints a
PASS or FAIL line; a check whose query errors fails without stopping the rest.
NOTE lines are information only and do not count as checks.
The exit status is 0 if every check passed, 1 if any failed or the session
was not read-only, and 2 on a usage error.
"""

import argparse
import hashlib
import os
import shutil
import sys
from importlib.metadata import version
from importlib.util import find_spec

os.environ["PGOPTIONS"] = " ".join(filter(None, [
    os.environ.get("PGOPTIONS"),
    "-c default_transaction_read_only=on -c statement_timeout=30000 -c lock_timeout=3000"]))
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../.."))

import psycodict
from lmfdb import db
from lmfdb.utils.psycopg_compat import SQL

TABLE = "belyi_galmap_dessins"
DUMP = "scripts/belyi/belyi_images.txt.gz"
DUMP_SHA256 = "481de914064f56988e9dcc72fc88ec71e8648716b46461b32c2db8a3f0306235"
ROWS, SVGS, MAX_SVGS = 1110, 4733, 28
ROLES = ["lmfdb", "webserver"]
RELATIONS = [TABLE, TABLE + "_counts", TABLE + "_stats"]
GRANTS = [(role, "SELECT", rel) for role in ROLES for rel in RELATIONS]
GRANTS += [("webserver", "INSERT", rel) for rel in RELATIONS[1:]]
KNOWLS = ["tables." + TABLE, "columns.%s.label" % TABLE, "columns.%s.dessins" % TABLE]
TWINS = ["9T23-6.2.1_6.2.1_6.2.1-a", "9T23-6.2.1_6.2.1_6.2.1-b"]
# Unfinished operations, restricted by OWN + [True] to this table and its companions, OWN + [False] to the rest.
OWN = [TABLE, TABLE.replace("_", "\\_") + "\\_%"]
UNFINISHED = ("FROM userdb.ongoing_operations s WHERE s.finishing IS NOT TRUE AND NOT EXISTS "
              "(SELECT 1 FROM userdb.ongoing_operations f WHERE f.logid = s.logid AND f.finishing IS TRUE) "
              "AND coalesce(s.tablename = %s OR s.tablename LIKE %s, false) = %s ")

results = []


def query(sql, values=None):
    return db._execute(SQL(sql), values, silent=True).fetchall()


def check(name, test):
    """Run test(), which returns (ok, observed, expected), and print its line."""
    try:
        ok, observed, expected = test()
    except Exception as err:
        ok, observed, expected = False, "error: %s" % str(err).strip().split("\n")[0], "no error"
    print("PASS %s: %s" % (name, observed) if ok else "FAIL %s: %s (expected %s)" % (name, observed, expected))
    results.append(ok)


def note(name, describe):
    """Print an informational line, which is not a check and does not affect the exit status."""
    try:
        print("NOTE %s: %s" % (name, describe()))
    except Exception as err:
        print("NOTE %s: error: %s" % (name, str(err).strip().split("\n")[0]))


def equal(sql, expected, values=None):
    """A test that the first row of a query, unwrapped if it has one column, is expected."""
    def test():
        rows = query(sql, values)
        observed = (rows[0][0] if len(rows[0]) == 1 else tuple(rows[0])) if rows else "no row"
        return observed == expected, observed, expected
    return test


def none_found(sql, values=None, show=10, found="found"):
    """A test that a query returns no rows, showing the first few it returns."""
    def test():
        rows = [row[0] if len(row) == 1 else tuple(row) for row in query(sql, values)]
        return not rows, "%d %s: %s" % (len(rows), found, rows[:show]) if rows else "none", "none"
    return test


def all_found(wanted, sql, values=None):
    """A test that every element of wanted is in the first column of a query."""
    def test():
        missing = sorted(set(wanted) - {row[0] for row in query(sql, values)})
        return not missing, "missing %s" % missing if missing else "all present", "all of %s" % wanted
    return test


def before(dump):
    def tools():
        pexpect, ssh = find_spec("pexpect") is not None, shutil.which("ssh")
        return (pexpect and bool(ssh), "pexpect %s, ssh %s" % ("importable" if pexpect else "missing", ssh),
                "pexpect importable and ssh on PATH")

    def dump_hash():
        with open(dump, "rb") as F:
            digest = hashlib.sha256(F.read()).hexdigest()
        return digest == DUMP_SHA256, "%s has sha256 %s" % (dump, digest), DUMP_SHA256

    def other_operations():
        count, space, oldest = query(
            "SELECT count(*), coalesce(sum(s.space_impact), 0), min(s.time)::date::text " + UNFINISHED,
            OWN + [False])[0]
        return ("%d, claiming %.1f GB, oldest %s (upload_dessins.py's disk check counts their space)"
                % (count, float(space) / 10**9, oldest) if count else "none")

    check("current user", equal("SELECT current_user", "editor"))
    check("primary server", equal("SELECT pg_is_in_recovery()", False))
    check("table absent", equal("SELECT to_regclass(%s)::text", None, ["public." + TABLE]))
    check("no leftover relations", none_found(
        "SELECT oid::regclass::text FROM pg_class WHERE relname LIKE %s ORDER BY 1",
        [TABLE.replace("_", "\\_") + "%"]))
    check("no metadata row", equal("SELECT count(*) FROM meta_tables WHERE name = %s", 0, [TABLE]))
    check("reader roles", all_found(ROLES, "SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", [ROLES]))
    check("create on schema public",
          equal("SELECT has_schema_privilege(current_user, 'public', 'CREATE')", True))
    check("shared-table privileges", none_found(
        "SELECT t.rel || ' ' || t.priv FROM (VALUES ('meta_tables', 'INSERT'), ('meta_tables', 'UPDATE'), "
        "('kwl_knowls', 'INSERT'), ('userdb.dbrecord', 'INSERT'), ('userdb.ongoing_operations', 'INSERT'), "
        "('userdb.ongoing_operations', 'DELETE')) AS t(rel, priv) WHERE NOT has_table_privilege(t.rel, t.priv)",
        found="missing"))
    check("disk-check tools", tools)
    check("run_diskfree execute", equal(
        "SELECT CASE WHEN f.p IS NULL THEN 'function missing' ELSE has_function_privilege(f.p, 'EXECUTE')::text END "
        "FROM to_regprocedure('run_diskfree(text)') AS f(p)", "true"))
    check("no unfinished operations on " + TABLE, none_found(
        "SELECT s.logid, s.time::text, s.tablename, s.operation, s.username " + UNFINISHED + "ORDER BY s.time",
        OWN + [True], show=None))
    note("other unfinished operations", other_operations)
    check("dump", dump_hash)


def after():
    def id_range():
        lo, hi, labels = query("SELECT min(id), max(id), count(DISTINCT label) FROM " + TABLE)[0]
        ok = lo is not None and hi - lo + 1 == ROWS and labels == ROWS
        return (ok, "ids %s to %s, %d distinct labels" % (lo, hi, labels),
                "%d consecutive ids and %d distinct labels" % (ROWS, ROWS))

    check("physical rows, svgs, max svgs", equal(
        "SELECT count(*), sum(cardinality(dessins)), max(cardinality(dessins)) FROM " + TABLE,
        (ROWS, SVGS, MAX_SVGS)))
    check("ids and labels", id_range)
    check("metadata total", equal("SELECT total FROM meta_tables WHERE name = %s", ROWS, [TABLE]))
    check("labels in belyi_galmaps", none_found(
        "SELECT d.label FROM " + TABLE + " d WHERE NOT EXISTS "
        "(SELECT 1 FROM belyi_galmaps g WHERE g.label = d.label) ORDER BY 1"))
    check("one svg per embedding", none_found(
        "SELECT d.label, cardinality(d.dessins), jsonb_array_length(g.triples_cyc) FROM " + TABLE + " d "
        "JOIN belyi_galmaps g ON g.label = d.label "
        "WHERE cardinality(d.dessins) IS DISTINCT FROM jsonb_array_length(g.triples_cyc) ORDER BY 1"))
    check("reader grants", none_found(
        "SELECT w.role, w.priv, w.rel FROM unnest(%s::text[], %s::text[], %s::text[]) AS w(role, priv, rel) "
        "WHERE NOT coalesce(has_table_privilege((SELECT oid FROM pg_roles WHERE rolname = w.role), "
        "to_regclass(w.rel), w.priv), false)", [list(col) for col in zip(*GRANTS)], show=None, found="missing"))
    check("knowls", all_found(KNOWLS, "SELECT id FROM kwl_knowls WHERE id = ANY(%s) AND status >= 0", [KNOWLS]))
    check("9T23 twins present and different", equal(
        "SELECT count(*), count(DISTINCT dessins) FROM " + TABLE + " WHERE label = ANY(%s)", (2, 2), [TWINS]))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--before", action="store_true", help="check that the upload can run")
    mode.add_argument("--after", action="store_true", help="check the uploaded table")
    parser.add_argument("--dump", default=DUMP, help="the dump --before checks [default: %(default)s]")
    args = parser.parse_args()

    driver = psycodict.SQL.__module__.split(".")[0]
    print("psycodict %s, %s %s" % (version("psycodict"), driver, sys.modules[driver].__version__))
    if query("SHOW transaction_read_only")[0][0] != "on":
        sys.exit("the session is not read-only, so no checks were run")
    if args.before:
        before(args.dump)
    else:
        after()
    print("%d of %d checks passed" % (results.count(True), len(results)))
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
