"""
The LMFDB website's database classes.

The connection, the LMFDB's conventions and the checks on data changes come
from lmfdb-client (``packages/lmfdb-client/lmfdb_client/database.py``),
which is also what ``pip install lmfdb-client`` provides.  The subclasses
here add what needs the rest of the LMFDB: editing table and column
descriptions (which are knowls), the verification framework, and resetting
the statistics displayed on the website.
"""

import inspect
import os
import shutil
import signal
import subprocess
# SQL comes from psycodict itself (which re-exports its driver's sql
# classes) rather than lmfdb.utils.psycopg_compat: importing anything from
# lmfdb.utils executes its heavyweight __init__, and this module must stay
# importable without sage or flask.  The verify modules import it from here.
from psycodict import SQL
from psycodict.utils import DelayCommit
from lmfdb_client.database import (
    LMFDBDatabase as _ClientDatabase,
    LMFDBSearchTable as _ClientSearchTable,
    LMFDBStatsTable,
    overrides,
)
from lmfdb.config import lmfdb_log_dir, lmfdb_package_dir

assert SQL and LMFDBStatsTable  # re-exported


class LMFDBSearchTable(_ClientSearchTable):
    # descriptions are edited through the knowl backend (see below), so the
    # schema changes that set them are possible here
    _can_edit_descriptions = True

    def __init__(self, *args, **kwds):
        _ClientSearchTable.__init__(self, *args, **kwds)
        self._verifier = None  # set when importing lmfdb.verify

    def description(self, table_description=None):
        """
        We use knowls to implement the table description API.
        """
        from lmfdb.knowledge.knowl import knowldb
        if table_description is None:
            current = knowldb.get_table_description(self.search_table)
            if current:
                return current.content
            else:
                return "(description not yet updated on this server)"
        else:
            knowldb.set_table_description(self.search_table, table_description)

    def column_description(self, col=None, description=None, drop=False):
        """
        We use knowls to implement the column description API.
        """
        from lmfdb.knowledge.knowl import knowldb
        allcols = self.search_cols
        current = knowldb.get_column_descriptions(self.search_table)
        current = {col: kwl.content for col, kwl in current.items()}
        if not drop and description is None:
            # We want to allow the set of columns to be out of date temporarily, on prod for example
            if col is None:
                for col in allcols:
                    if col not in current:
                        current[col] = "(description not yet updated on this server)"
                return current
            return current.get(col, "(description not yet updated on this server)")
        else:
            if not (drop or col is None or col in allcols):
                raise ValueError(f"{col} is not a column of this table")
            if drop:
                if col is None:
                    raise ValueError("Must specify column name to drop")
                knowldb.drop_column(self.search_table, col)
            elif col is None:
                assert isinstance(description, dict)
                for col in description:
                    if col not in allcols:
                        raise ValueError(f"{col} is not a column of this table")
                    assert isinstance(description[col], str)
                    knowldb.set_column_description(self.search_table, col, description[col])
            else:
                assert isinstance(description, str)
                knowldb.set_column_description(self.search_table, col, description)

    def port_column_knowls(self, other_table, keep_old=True):
        """
        This function either copies column knowls from another table or change the ids to this table's.

        INPUT:

        - ``other_table`` -- a string, the name of the other table.
        - ``keep_old`` -- if true, new knowls for this table will be created from the column knowls for the old table.  Otherwise, the old knowls will be renamed, or deleted if they are not columns of this table.
        """
        from lmfdb.knowledge.knowl import knowldb
        from lmfdb.utils.datetime_utils import utc_now_naive
        knowls = knowldb.get_column_description(other_table)
        with DelayCommit(self):
            for col, knowl in knowls.items():
                if col in self.col_type:
                    if keep_old:
                        new_knowl = knowl.copy(ID=f'columns.{self.search_table}.{col}', timestamp=utc_now_naive())
                        who = self._db.login()
                        new_knowl.save(who, most_recent=knowl, minor=True)
                    else:
                        knowldb.actually_rename(knowl, new_name=f'columns.{self.search_table}.{col}')
                elif not keep_old:
                    knowldb.delete(knowl)

    def _check_verifications_enabled(self):
        """
        Check whether verifications have been enabled in this session (by importing db from lmfdb.verify and implementing an appropriate file).
        """
        if not self._db.is_verifying:
            raise ValueError("Verification not enabled by default; import db from lmfdb.verify to enable")
        if self._verifier is None:
            raise ValueError("No verifications defined for this table; add a class {0} in lmfdb/verify/{0}.py to enable".format(self.search_table))

    def verify(
        self,
        speedtype="all",
        check=None,
        label=None,
        ratio=None,
        logdir=None,
        parallel=4,
        follow=["errors", "log", "progress"],
        poll_interval=0.1,
        debug=False,
    ):
        """
        Run the tests on this table defined in the lmfdb/verify folder.

        If parallel is True, sage should be in your path or aliased appropriately.

        Note that if check is not provided and parallel is False, no output will be printed, files
        will still be written to the log directory.

        INPUT:

        - ``speedtype`` -- a string: "overall", "overall_long", "fast", "slow" or "all".
        - ``check`` -- a string, giving the function name for a particular test.
            If provided, ``speedtype`` will be ignored.
        - ``label`` -- a string, giving the label for a particular object on which to run tests
            (as in the label_col attribute of the verifier).
        - ``ratio`` -- for slow and fast tests, override the ratio of rows to be tested. Only valid
            if ``check`` is provided.
        - ``logdir`` -- a directory to output log files.  Defaults to LMFDB_ROOT/logs/verification.
        - ``parallel`` -- A cap on the number of threads to use in parallel (if 0, doesn't use parallel).
            If ``check`` or ``label`` is set, parallel is ignored and tests are run directly.
        - ``follow`` -- Which output logs to print to stdout.  'log' contains failed tests,
            'errors' details on errors in tests, and 'progress' shows progress in running tests.
            If False or empty, a subprocess.Popen object to the subprocess will be returned.
        - ``poll_interval`` -- The polling interval to follow the output if executed in parallel.
        - ``debug`` -- if False, will redirect stdout and stderr for the spawned process to /dev/null.
        """
        self._check_verifications_enabled()
        if ratio is not None and check is None:
            raise ValueError("You can only provide a ratio if you specify a check")
        if logdir is None:
            logdir = os.path.join(lmfdb_log_dir(), "verification")
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        if label is not None:
            parallel = 0
        verifier = self._verifier
        if check is None:
            olddir = os.path.join(logdir, "old")
            if not os.path.exists(olddir):
                os.makedirs(olddir)

            def move_to_old(tname):
                for suffix in [".log", ".errors", ".progress", ".started", ".done"]:
                    filename = os.path.join(logdir, tname + suffix)
                    if os.path.exists(filename):
                        n = 0
                        oldfile = os.path.join(olddir, tname + str(n) + suffix)
                        while os.path.exists(oldfile):
                            n += 1
                            oldfile = os.path.join(olddir, tname + str(n) + suffix)
                        shutil.move(filename, oldfile)

            if speedtype == "all":
                types = verifier.all_types()
            else:
                types = [verifier.speedtype(speedtype)]
            tabletypes = [
                "%s.%s" % (self.search_table, typ.shortname)
                for typ in types
                if verifier.get_checks_count(typ) > 0
            ]
            if len(tabletypes) == 0:
                raise ValueError(
                    "No checks of type %s defined for %s"
                    % (", ".join(typ.__name__ for typ in types), self.search_table)
                )
            for tname in tabletypes:
                move_to_old(tname)
            if parallel:
                parallel = min(parallel, len(tabletypes))
                for tabletype in tabletypes:
                    print("Starting %s" % tabletype)
                cmd = os.path.abspath(os.path.join(
                    os.path.dirname(os.path.realpath(__file__)),
                    "verify",
                    "verify_tables.py",
                ))
                cmd = [
                    "sage",
                    "-python",
                    cmd,
                    "-j%s" % int(parallel),
                    logdir,
                    str(self.search_table),
                    speedtype,
                ]
                if debug:
                    pipe = subprocess.Popen(cmd)
                else:
                    DEVNULL = open(os.devnull, "wb")
                    pipe = subprocess.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
                if follow:
                    from lmfdb.verify.follower import Follower

                    try:
                        Follower(logdir, tabletypes, follow, poll_interval).follow()
                    finally:
                        # kill the subprocess
                        # From the man page, the following will terminate child processes
                        if pipe.poll() is None:
                            pipe.send_signal(signal.SIGTERM)
                            pipe.send_signal(signal.SIGTERM)
                else:
                    return pipe
            else:
                for typ in types:
                    if verifier.get_checks_count(typ) == 0:
                        print("No %s checks defined for %s" % (typ.__name__, self.search_table))
                    else:
                        print("Starting %s checks for %s" % (typ.__name__, self.search_table))
                        verifier.run(typ, logdir, label)
        else:
            msg = "Starting check %s" % check
            if label is not None:
                msg += " for label %s" % label
            print(msg)
            verifier.run_check(check, label=label, ratio=ratio)

    def list_verifications(self, details=True):
        """
        Lists all verification functions available for this table.

        INPUT:

        - ``details`` -- if True, details such as the docstring, ratio of rows on which the test
            is run by default and the constraint on rows for which this test is run are shown.
        """
        self._check_verifications_enabled()
        green = "\033[92m"
        red = "\033[91m"
        stop = "\033[0m"

        def show_check(name, check, typ):
            if typ.__name__ in ["overall", "fast"]:
                color = green
            else:
                color = red
            print("* " + color + name + stop)
            if details:
                if check.ratio < 1:
                    ratio_fmt = "Ratio of rows: {val:.2%}"
                else:
                    ratio_fmt = "Ratio of rows: {val:.0%}"
                for line in inspect.getdoc(check).split("\n"):
                    print(" " * 4 + line)
                for attr, fmt in [
                    ("disabled", "Disabled"),
                    ("ratio", ratio_fmt),
                    ("max_failures", "Max failures: {val}"),
                    ("timeout", "Timeout after: {val}s"),
                    ("constraint", "Constraint: {val}"),
                    ("projection", "Projection: {val}"),
                    ("report_slow", "Report slow test after: {val}s"),
                    ("max_slow", "Maximum number of slow tests: {val}"),
                ]:
                    cattr = getattr(check, attr, None)
                    tattr = getattr(typ, attr, None)
                    if cattr is not None and cattr != tattr:
                        print(" " * 6 + fmt.format(val=cattr))

        verifier = self._verifier
        for typ in ["over", "fast", "long", "slow"]:
            color = green if typ in ["over", "fast"] else red
            typ = verifier.speedtype(typ)
            if verifier.get_checks_count(typ) > 0:
                name = color + typ.__name__ + stop
                print("\n{0} checks (default {1:.0%} of rows, {2}s timeout)".format(
                        name, float(typ.ratio), typ.timeout
                ))
                for checkname, check in inspect.getmembers(verifier.__class__):
                    if isinstance(check, typ):
                        show_check(checkname, check, typ)


class LMFDBDatabase(_ClientDatabase):
    """
    ATTRIBUTES:

    In addition to the attributes on PostgresDatabase:

    - ``is_verifying`` -- whether this database has been configured with verifications (import from lmfdb.verify if you want this to be True)

    PARAMETERS:

    - ``config`` -- optional configuration. Can be:
        * None (default): uses the process-wide configuration (see
          lmfdb.config.current_configuration)
        * dict: a dictionary with keys 'postgresql_options', 'flask_options', 'logging_options'
        * Configuration object: used directly
    """
    _search_table_class_ = LMFDBSearchTable

    def __init__(self, config=None, **kwargs):
        _ClientDatabase.__init__(self, config, **kwargs)
        self.is_verifying = False  # set to true when importing lmfdb.verify

    @classmethod
    def default_configuration(cls):
        # the website's configuration rather than lmfdb-client's
        from lmfdb.config import current_configuration
        return current_configuration()

    def verify(
        self,
        speedtype="all",
        logdir=None,
        parallel=8,
        follow=["errors", "log", "progress"],
        poll_interval=0.1,
        debug=False,
    ):
        """
        Run verification tests on all tables (if defined in the lmfdb/verify folder).
        For more granular control, see the ``verify`` function on a particular table.

        sage should be in your path or aliased appropriately.

        INPUT:

        - ``speedtype`` -- a string: "overall", "overall_long", "fast", "slow" or "all".
        - ``logdir`` -- a directory to output log files.  Defaults to LMFDB_ROOT/logs/verification.
        - ``parallel`` -- A cap on the number of threads to use in parallel
        - ``follow`` -- The polling interval to follow the output.
            If 0, a parallel subprocess will be started and a subprocess.Popen object to it will be returned.
        - ``debug`` -- if False, will redirect stdout and stderr for the spawned process to /dev/null.
        """
        if not self.is_verifying:
            raise ValueError("Verification not enabled by default; import db from lmfdb.verify to enable")
        if parallel <= 0:
            raise ValueError("Non-parallel runs not supported for whole database")
        if logdir is None:
            logdir = os.path.join(lmfdb_log_dir(), "verification")
        if not os.path.exists(logdir):
            os.makedirs(logdir)
        types = None
        tabletypes = []
        for tablename in self.tablenames:
            table = self[tablename]
            verifier = table._verifier
            if verifier is not None:
                if types is None:
                    if speedtype == "all":
                        types = verifier.all_types()
                    else:
                        types = [verifier.speedtype(speedtype)]
                for typ in types:
                    if verifier.get_checks_count(typ) != 0:
                        tabletypes.append("%s.%s" % (tablename, typ.shortname))
        if len(tabletypes) == 0:
            # Shouldn't occur....
            raise ValueError("No verification tests defined!")
        parallel = min(parallel, len(tabletypes))
        cmd = str(lmfdb_package_dir / "verify" / "verify_tables.py")
        cmd = ["sage", "-python", cmd, "-j%s" % int(parallel), logdir, "all", speedtype]
        if debug:
            pipe = subprocess.Popen(cmd)
        else:
            DEVNULL = open(os.devnull, "wb")
            pipe = subprocess.Popen(cmd, stdout=DEVNULL, stderr=DEVNULL)
        if follow:
            from lmfdb.verify.follower import Follower

            try:
                Follower(logdir, tabletypes, follow, poll_interval).follow()
            finally:
                # kill the subprocess
                # From the man page, the following will terminate child processes
                pipe.send_signal(signal.SIGTERM)
                pipe.send_signal(signal.SIGTERM)
        else:
            return pipe

    def reset_all_stats(self):
        """
        This function clears all stats and counts (extra=False) from tables where statistics have been added, then adds all relevant statistics.
        """
        from . import website # loads all the modules
        assert website
        from lmfdb.utils.display_stats import StatsDisplay

        def find_subs(L):
            # Assume no multiple inheritance
            new_subs = sum([C.__subclasses__() for C in L], [])
            if new_subs:
                new_subs = find_subs(new_subs)
            return L + new_subs
        all_subs = find_subs([StatsDisplay])[1:]
        with DelayCommit(self):
            cleared_tables = set()
            for disp in all_subs:
                print("Resetting statistics for %s" % (disp.table.search_table))
                tbls = set()
                if disp.table not in cleared_tables:
                    tbls.add(disp.table)
                for attr in disp.stat_list:
                    if "table" in attr and attr["table"] not in cleared_tables:
                        tbls.add(attr["table"])
                for tbl in tbls:
                    tbl.stats._clear_stats_counts(extra=False)
                cleared_tables.update(tbls)
                disp().setup(delete=False)

    @overrides(_ClientDatabase)
    def drop_table(self, name, *args, **kwargs):
        cols = self[name].search_cols
        super().drop_table(name, *args, **kwargs)
        from lmfdb.knowledge.knowl import knowldb
        knowldb.drop_table(name)
        for col in cols:
            knowldb.drop_column(name, col)
        print("Deleted table and column descriptions from knowl database")

# The public lazy proxy, importable from here for backwards compatibility
# (the verify modules and older scripts do `from lmfdb.lmfdb_database import
# db`).  This is the same object as lmfdb.db, not a second database.
from lmfdb import db
assert db
