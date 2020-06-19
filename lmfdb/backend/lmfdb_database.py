
import os
from lmfdb.utils.config import Configuration
from .database import PostgresDatabase
from .searchtable import PostgresSearchTable
from .lmfdb_statstable import PostgresStatsTable
from six.moves.configparser import ConfigParser

class LMFDBStatsTable(PostgresStatsTable):
    saving = True

class LMFDBSearchTable(PostgresSearchTable):
    _stats_table_class_ = LMFDBStatsTable
    def __init__(self, *args, **kwds):
        PostgresSearchTable.__init__(self, *args, **kwds)
        self._verifier = None  # set when importing lmfdb.verify

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
        lmfdb_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
        if logdir is None:
            logdir = os.path.join(lmfdb_root, "logs", "verification")
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
                    "..",
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

class LMFDBDatabase(PostgresDatabase):
    """
    ATTRIBUTES:

    In addition to the attributes on PostgresDatabase:

    - ``is_verifying`` -- whether this database has been configured with verifications (import from lmfdb.verify if you want this to be True)
    """
    _search_table_class_ = LMFDBSearchTable

    def __init__(self, **kwargs):
        # This will write the default configuration file if needed
        config = Configuration()
        #configfile = abs_path_lmfdb("config.ini")
        #secretsfile = abs_path_lmfdb("password.ini")
        #if not os.path.exists(secretsfile):
        #    oldpass = abs_path_lmfdb("password")
        #    if os.path.exists(oldpass):
        #        cfgp = ConfigParser()
        #        with open(oldpass) as Fold:
        #            passwd = Fold.readlines()[0].strip()
        #        cfgp.add_section("postgresql")
        #        cfgp.set("postgresql", "user", "webserver")
        #        cfgp.set("postgresql", "password", passwd)
        #        cfgp.write(secretsfile)
        #    else:
        #        secretsfile = None
        PostgresDatabase.__init__(self, config, **kwargs)
        self.is_verifying = False  # set to true when importing lmfdb.verify

    def login(self):
        """
        Identify an editor by their lmfdb username.

        The goal is to associate changes with people and keep a record of changes made.
        There is no real security against malicious use.

        Note that you can permanently log in by setting the editor
        field in the logging section of your config.ini file.
        """
        if not self.__editor:
            print("Please provide your knowl username,")
            print("so that we can associate database changes with individuals.")
            print(
                "Note that you can also do this by setting the editor field "
                "in the logging section of your config.ini file."
            )
            uid = input("Username: ")
            selecter = SQL("SELECT username FROM userdb.users WHERE username = %s")
            cur = self._execute(selecter, [uid])
            if cur.rowcount == 0:
                raise ValueError("That username not present in database!")
            self.__editor = uid
        return self.__editor

    def log_db_change(self, operation, tablename=None, **data):
        """
        Log a change to the database.

        INPUT:

        - ``operation`` -- a string, explaining what operation was performed
        - ``tablename`` -- the name of the table that the change is affecting
        - ``**data`` -- any additional information to install in the logging table (will be stored as a json dictionary)
        """
        uid = self.login()
        inserter = SQL(
            "INSERT INTO userdb.dbrecord (username, time, tablename, operation, data) "
            "VALUES (%s, %s, %s, %s, %s)"
        )
        self._execute(inserter, [uid, datetime.datetime.utcnow(), tablename, operation, data])

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
        lmfdb_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
        if logdir is None:
            logdir = os.path.join(lmfdb_root, "logs", "verification")
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
        cmd = os.path.abspath(os.path.join(os.path.abspath(__file__), "..", "verify", "verify_tables.py"))
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
