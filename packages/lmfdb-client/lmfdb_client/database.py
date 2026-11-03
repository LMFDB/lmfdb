"""
The LMFDB's database classes, extending psycodict's.

On top of psycodict, these classes apply the LMFDB's conventions: the
privileges granted on new tables, table names that start with their section,
and, for editors making data changes, the record of who changed what and a
check that the servers have enough disk space.

The LMFDB website subclasses them in ``lmfdb/lmfdb_database.py`` to add what
needs the rest of the LMFDB: editing table and column descriptions (which
are knowls), and the verification framework.
"""

import datetime
import inspect
import os
import socket
from collections import Counter

from psycodict import SQL
from psycodict.database import PostgresDatabase
from psycodict.searchtable import PostgresSearchTable
from psycodict.statstable import PostgresStatsTable

from .config import ConfigWrapper

try:
    from psycodict.grants import LMFDBGrantPolicy
except ImportError:
    # psycodict before roed314/psycodict#137, which granted these privileges
    # unconditionally and so has nothing to be told about them.  Delete this
    # fallback once the psycodict requirement is pinned past that PR.
    LMFDBGrantPolicy = None


def utc_now_naive():
    """
    The current UTC time as a naive datetime, as stored in the database's
    'timestamp without time zone' columns.
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def overrides(super_class):
    def overrider(method):
        super_method = getattr(super_class, method.__name__)
        assert super_method
        if not method.__doc__:
            method.__doc__ = super_method.__doc__
        method.__signature__ = inspect.signature(super_method)
        return method
    return overrider


class LMFDBStatsTable(PostgresStatsTable):
    saving = True


# These are the operations where we don't insert records into the ongoing_operations table since they don't take noticeable space.
_nolog_changetypes = ["delete", "resort", "add_column", "drop_column", "create_table"]

_NO_DESCRIPTION = "(description not yet updated on this server)"


class LMFDBSearchTable(PostgresSearchTable):
    _stats_table_class_ = LMFDBStatsTable

    # Table and column descriptions are stored as knowls.  The queries below
    # match KnowlBackend.get_table_description and get_column_descriptions in
    # lmfdb/knowledge/knowl.py, which the website uses (and which edit them).
    def description(self, table_description=None):
        """
        The description of this table.

        Descriptions can only be read here; edit them from an LMFDB checkout.
        """
        if table_description is not None:
            raise NotImplementedError("Descriptions are knowls and can only be edited from an LMFDB checkout")
        cur = self._execute(
            SQL("SELECT content FROM (SELECT DISTINCT ON (id) id, content FROM kwl_knowls WHERE id = %s AND type = %s AND status >= %s ORDER BY id, timestamp) knowls LIMIT 1"),
            [f"tables.{self.search_table}", 2, 0],
        )
        rec = cur.fetchone()
        return _NO_DESCRIPTION if rec is None else rec[0]

    def column_description(self, col=None, description=None, drop=False):
        """
        The description of the column ``col``, or a dictionary giving the
        descriptions of all columns if ``col`` is None.

        Descriptions can only be read here; edit them from an LMFDB checkout.
        """
        if drop or description is not None:
            raise NotImplementedError("Descriptions are knowls and can only be edited from an LMFDB checkout")
        cur = self._execute(
            SQL("SELECT id, content FROM (SELECT DISTINCT ON (id) id, content FROM kwl_knowls WHERE id LIKE %s AND type = %s AND status >= %s ORDER BY id, timestamp) knowls ORDER BY id"),
            [f"columns.{self.search_table}.%", 2, 0],
        )
        current = {kid.split(".")[-1]: content for kid, content in cur}
        # We want to allow the set of columns to be out of date temporarily, on prod for example
        if col is None:
            for c in self.search_cols:
                current.setdefault(c, _NO_DESCRIPTION)
            return current
        return current.get(col, _NO_DESCRIPTION)

    @overrides(PostgresSearchTable)
    def add_column(self, *args, **kwds):
        if "force_description" not in kwds:
            kwds["force_description"] = True
        return super().add_column(*args, **kwds)

    @overrides(PostgresSearchTable)
    def _check_locks(self, changetype, datafile=None, suffix=""):
        super()._check_locks(changetype, datafile=datafile, suffix=suffix)
        if self._db.config.postgresql_options["user"] != "editor":
            raise RuntimeError("You must be logged in as editor to make data changes")
        if changetype in _nolog_changetypes or socket.gethostname() == "proddb":
            return

        # The following is the definition of run_diskfree used below to find the available space on grace
        # CREATE ROLE diskfree_exec NOLOGIN;
        # GRANT pg_execute_server_program TO diskfree_exec;
        # SET ROLE diskfree_exec;
        # CREATE OR REPLACE FUNCTION run_diskfree(path text)
        # RETURNS text
        # LANGUAGE plpgsql
        # SECURITY DEFINER AS $$
        # DECLARE
        #     sys_cmd   text;
        #     df_result text;
        # BEGIN
        #     -- Validate path to prevent injection
        #     IF path !~ '^[/a-z0-9._-]+$' THEN
        #         RAISE EXCEPTION 'Invalid path: "%"', path;
        #     END IF;
        #     sys_cmd := 'df ' || path || ' | tail -n 1';
        #     -- Use a temp table to capture result safely
        #     CREATE TEMP TABLE tmp_diskfree(output_text text) ON COMMIT DROP;
        #     EXECUTE 'COPY tmp_diskfree (output_text) FROM PROGRAM ' || quote_literal(sys_cmd);
        #     SELECT output_text INTO df_result FROM tmp_diskfree;
        #     RETURN df_result;
        # END;
        # $$;

        def extract_space(line, path=None):
            """Extract the space available from a line of output from df, in bytes"""
            pieces = line.split()
            if path is not None and not pieces[-1].startswith(path):
                return -1
            # df returns its amounts in 1K blocks
            return 1024 * int(pieces[3])

        def devmirror_space_available():
            """Return the amount of space available on the devmirror postgres filesystem"""
            editor_password = self._db.config.postgresql_options["password"]
            import pexpect
            child = pexpect.spawn('ssh -o "StrictHostKeyChecking no" -o PreferredAuthentications=password dfuser_ssh@devmirror.lmfdb.xyz')
            _ = child.expect("password:")
            _ = child.sendline(editor_password)
            _ = child.expect(pexpect.EOF)
            payload = child.before.decode().strip().replace("\r", "").split("\n")
            for line in payload:
                # Devmirror puts everything into this filesystem
                free = extract_space(line, "/var/lib/postgresql")
                if free >= 0:
                    return free

        def grace_space_available():
            """Return the amount of space on postgres and scratch on grace.mit.edu"""
            line = self._execute(SQL("SELECT run_diskfree(%s)"), ["/var/lib/postgresql"]).fetchone()[0]
            default = extract_space(line)
            line = self._execute(SQL("SELECT run_diskfree(%s)"), ["/scratch"]).fetchone()[0]
            scratch = extract_space(line)
            return default, scratch

        # Estimate the size needed by this operation
        tablespace = self._get_tablespace()
        cur_size = self._db.table_sizes()[self.search_table]
        size_guess = cur_size["total_bytes"]
        if datafile is None:
            if changetype != "create_table_like":
                size_guess = 0 # insert_many, update, upsert.  We rely on the 100GB offset to provide enough space since there is no datafile to use
        else:
            size_guess = max(size_guess, os.path.getsize(datafile))

        def get_space_needed(ops):
            """Space needed by operations that have started but not finished"""
            finished = set(logid for logid, finishing, space_impact, ts, time, table, op, user in ops if finishing)
            space_claimed = Counter()
            for logid, finishing, space_impact, ts, time, table, op, user in ops:
                if not finishing and logid not in finished:
                    space_claimed[ts] += space_impact
            return finished, space_claimed

        def ts_filter(ops, ts):
            return [op for op in ops if op[3] == ts]

        def check_space(needed, available, location, ops):
            """Raise an informative error if there is not enough space"""
            if needed > 0 and (needed * 2 + 10**11) > available:
                needGB = float(needed) / 10**9
                avGB = float(available) / 10**9
                guessGB = float(size_guess) / 10**9
                if ops:
                    op_summary = ", prior commitments from " + ", ".join(f"{table}:{op} by {user} at {time:%a %H:%M} for {float(space_impact)/10**9:.2f}GB" for (logid, finishing, space_impact, ts, time, table, op, user) in ops if not finishing)
                else:
                    op_summary = ""
                raise OSError(f"Not enough space on {location}: {needGB:.2f}GB (+100%+100GB) needed, {avGB:.2f}GB available.  This table estimated at {guessGB:.2f}GB{op_summary}.")

        # Find the operations that have been logged on grace.
        op_cmd = SQL("SELECT logid, finishing, space_impact, tablespace, time, tablename, operation, username FROM userdb.ongoing_operations ORDER BY time")
        grace_ops = list(self._execute(op_cmd))
        # grace_finished is a set with logids that have finished on grace; grace_space_claimed is a dictionary (by tablespace) of how much space the in-progress operations might need
        grace_finished, grace_space_claimed = get_space_needed(grace_ops)
        # Add the amount of space this operation requires
        grace_space_claimed[tablespace] += size_guess
        # Determine how much space is available
        grace_default, grace_scratch = grace_space_available()
        # Check that there is sufficient space on both the postgres and scratch filesystems
        check_space(grace_space_claimed[None], grace_default, "grace.mit.edu /var/lib/postgresql", ts_filter(grace_ops, None))
        check_space(grace_space_claimed["scratch"], grace_scratch, "grace.mit.edu /scratch", ts_filter(grace_ops, "scratch"))

        # Get a connection to devmirror so that we can see which operations have been mirrored there.
        # Every connection parameter is given explicitly, but we still pass along our own
        # configuration: without it psycodict builds a default Configuration, which reads (and
        # creates) a config.ini in the current directory, and in some versions parses sys.argv,
        # so that an unrelated argument to the calling script aborts the upload.
        devmirror = PostgresDatabase(
            config=self._db.config,
            host="devmirror.lmfdb.xyz",
            user="lmfdb",
            password="lmfdb",
            port="5432",
            dbname="lmfdb",
        )
        dm_ops = list(devmirror._execute(op_cmd))
        # dm_finished is a set with logids that have finished mirroring; dm_space_claimed is a dictionary (by tablespace) of how much space the in-progress operations might need
        dm_finished, dm_space_claimed = get_space_needed(dm_ops)
        # Devmirror stores everything in one place
        dm_space_claimed = sum(dm_space_claimed.values()) + size_guess
        # Determine how much space is available
        dm_available = devmirror_space_available()
        # Check that there is sufficient space in all tablespaces
        check_space(dm_space_claimed, dm_available, "devmirror.lmfdb.xyz", dm_ops)

        # Delete entries from userdb.ongoing_operations that have finished on both grace and devmirror
        for deleted_id in grace_finished.intersection(dm_finished):
            self._execute(SQL("DELETE FROM userdb.ongoing_operations WHERE logid = %s"), [deleted_id])

        # Insert this operation
        logid = self._execute(SQL("INSERT INTO userdb.ongoing_operations (finishing, space_impact, tablespace, time, tablename, operation, username) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING logid"), [False, size_guess, tablespace, utc_now_naive(), self.search_table, changetype, self._db.login()]).fetchone()[0]

        return logid


class LMFDBDatabase(PostgresDatabase):
    """
    PARAMETERS:

    - ``config`` -- optional configuration. Can be:
        * None (default): uses the process-wide configuration (see
          :func:`lmfdb_client.config.current_configuration`)
        * dict: a dictionary with keys 'postgresql_options', 'flask_options', 'logging_options'
        * Configuration object: used directly
    """
    _search_table_class_ = LMFDBSearchTable

    def __init__(self, config=None, **kwargs):
        if config is None:
            config = self.default_configuration()
        elif isinstance(config, dict):
            # If config is a dict, create a wrapper object with the required attributes
            config = ConfigWrapper(config)
        # else: config is already a Configuration object, use it as-is

        if LMFDBGrantPolicy is not None:
            # psycodict's default policy grants nothing, so a table it creates
            # -- or swaps in during a reload -- would be readable only by its
            # owner.  This policy is what psycodict used to do: SELECT to lmfdb
            # and webserver, INSERT to webserver on counts and stats.  It warns
            # rather than raises when a role is missing, since a development
            # database usually has neither; a deployment that must have both
            # can pass LMFDBGrantPolicy(missing_role="error") instead.
            kwargs.setdefault("grant_policy", LMFDBGrantPolicy())
        PostgresDatabase.__init__(self, config, **kwargs)
        self.__editor = config.logging_options.get("editor", "")

    @classmethod
    def default_configuration(cls):
        """
        The configuration used when none is given: the process-wide one.
        """
        from .config import current_configuration
        return current_configuration()

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

    def _log_db_change(self, operation, tablename=None, logid=None, aborted=False, **data):
        """
        Log a change to the database.

        INPUT:

        - ``operation`` -- a string, explaining what operation was performed
        - ``tablename`` -- the name of the table that the change is affecting
        - ``**data`` -- any additional information to install in the logging table (will be stored as a json dictionary)
        """
        if aborted:
            if socket.gethostname() != "proddb":
                deleter = SQL("DELETE FROM userdb.ongoing_operations WHERE logid = %s")
                self._execute(deleter, [logid])
        else:
            uid = self.login()
            # This table is used for long-term recording of database operations
            inserter = SQL(
                "INSERT INTO userdb.dbrecord (username, time, tablename, logid, operation, data) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            )
            self._execute(inserter, [uid, utc_now_naive(), tablename, logid, operation, data])
            if operation not in _nolog_changetypes and socket.gethostname() != "proddb":
                # This table is used by _check_locks to determine if there is enough space to execute an upload
                inserter = SQL(
                    "INSERT INTO userdb.ongoing_operations (logid, finishing, time, tablename, operation, username) "
                    "VALUES (%s, %s, %s, %s, %s, %s)"
                )
                self._execute(inserter, [logid, True, utc_now_naive(), tablename, operation, uid])

    # psycodict renamed this hook to _log_db_change (roed314/psycodict#92);
    # keep the old name bound too so the override works whichever psycodict is
    # installed.  Delete this alias once psycodict is pinned past that PR.
    log_db_change = _log_db_change

    @overrides(PostgresDatabase)
    def create_table(self, name, *args, **kwargs):
        if "_" not in name:
            raise ValueError("Table name '%s' must contain an underscore; first part gives the LMFDB section" % name,)
        if "force_description" not in kwargs:
            kwargs["force_description"] = True
        return PostgresDatabase.create_table(self, name, *args, **kwargs)
