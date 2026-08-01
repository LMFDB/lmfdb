# -*- coding: utf-8 -*-
"""
The connection object at the center of psycodict.

:class:`PostgresDatabase` connects using a
:class:`~psycodict.config.Configuration` and exposes each table in the
database as an attribute (``db.nf_fields``), a
:class:`~psycodict.searchtable.PostgresSearchTable`.  It also provides the
database-wide operations: creating, dropping and renaming tables,
reloading or cleaning up every table at once, schema-change notifications
(:meth:`~PostgresDatabase.listener`), refreshing table metadata without a
restart (:meth:`~PostgresDatabase.refresh_tables`), and the metadata
format stamp and its migrations.
"""
import csv
import logging
from pathlib import Path
import time
import traceback
from collections import defaultdict, Counter

from psycopg import connect, DatabaseError
from psycopg.errors import UndefinedTable
from psycopg.sql import SQL, Identifier, Placeholder
from psycopg.adapt import Loader
from psycopg.types.json import set_json_loads

from .encoding import (
    Json,
    numeric_converter,
    Array,
    ArrayDumper,
    JsonWrapperDumper,
    DictJsonDumper,
)
from .base import (
    PostgresBase,
    META_FORMAT,
    _meta_tables_cols,
    _meta_tables_defaults,
    _meta_cols_types_jsonb_idx,
)
from .searchtable import PostgresSearchTable
from .utils import DelayCommit

# The registry of metadata-format migrations.  Entry N describes the step
# from format N-1 to format N; MetadataFormats.md has the checklist a new
# format must follow.
#
#   description -- one line, shown when the step is applied
#   compatible  -- whether a psycodict expecting format >= N still operates
#                  against a database at format < N (features introduced by
#                  the new format degrade gracefully, nothing else changes).
#                  Decides warn-and-proceed versus refuse at connect time.
#   min_compat  -- stamped into meta_format alongside the version: the oldest
#                  META_FORMAT a psycodict may have and still safely use a
#                  database at this format.  Raised to N whenever a client that
#                  predates format N would *mishandle* the new metadata rather
#                  than merely miss it -- which includes a purely additive
#                  column when older write paths would silently drop it (as an
#                  older restore_index/reload would drop a whereclause), not
#                  only outright breaking changes.
#   upgrade     -- name of the PostgresDatabase method performing the DDL
#                  (just the DDL, idempotently: stamping is done by
#                  upgrade_metadata itself).
META_MIGRATIONS = {
    1: {
        "description": "meta_indexes/meta_indexes_hist gain a whereclause column (partial indexes)",
        "compatible": True,
        # A format-0 client reads a format-1 database fine, but its
        # restore_index/reload would silently rebuild a partial index as a
        # full one and drop the predicate, so it must not *write* one: the
        # oldest format that can safely use a format-1 database is 1 itself.
        "min_compat": 1,
        "upgrade": "_upgrade_meta_0_to_1",
    },
}


def _stamped_min_compat(version):
    """
    The min_compat that stamping ``version`` should record (format 0 predates
    both the stamp and the registry, hence the default).
    """
    return META_MIGRATIONS[version]["min_compat"] if version in META_MIGRATIONS else 0


class NumericLoader(Loader):
    """
    Loads Postgres numeric values through :func:`numeric_converter`
    (Sage Integer/RealLiteral when Sage is available, int/float otherwise).
    """
    def load(self, data):
        """
        Convert the numeric's text representation to a Python/Sage number.
        """
        return numeric_converter(bytes(data).decode())


def setup_connection(conn):
    """
    Prepare a fresh psycopg connection for psycodict: set the client
    encoding and register the loaders and dumpers that implement
    psycodict's value conversion (numerics, json, arrays, and -- when Sage
    is available -- Sage integers and reals).  Called for every connection
    the database opens.
    """
    # psycopg3 uses unicode (str) everywhere by default, so the psycopg2-era
    # UNICODE/UNICODEARRAY registrations are no longer needed.
    conn.execute("SET client_encoding TO 'UTF8'")
    conn.commit()
    # All registrations below are per-connection (psycopg3 improvement over
    # psycopg2's process-global register_adapter).
    conn.adapters.register_loader("numeric", NumericLoader)
    conn.adapters.register_dumper(dict, DictJsonDumper)
    conn.adapters.register_dumper(Json, JsonWrapperDumper)
    conn.adapters.register_dumper(Array, ArrayDumper)
    set_json_loads(Json.loads, conn)
    try:
        # RealNumber must come from real_mpfr: sage.all.RealNumber is the
        # create_RealNumber factory function (not a class), and dumpers can
        # only be registered on classes
        from sage.rings.integer import Integer
        from sage.rings.real_mpfr import RealNumber
        from .encoding import RealLiteralDumper, SageIntegerDumper, LmfdbRealLiteral
    except ImportError:
        pass
    else:
        conn.adapters.register_dumper(Integer, SageIntegerDumper)
        conn.adapters.register_dumper(RealNumber, RealLiteralDumper)
        conn.adapters.register_dumper(LmfdbRealLiteral, RealLiteralDumper)


class PostgresDatabase(PostgresBase):
    """
    The interface to the postgres database.

    It creates and stores the global connection object,
    and collects the table interfaces.

    A single psycopg connection is shared by this database object and every
    table interface registered on it (see ``register_object`` and
    ``reset_connection``).  The psycopg connection itself is thread-safe --
    it serializes concurrent cursor use with an internal lock -- but sharing
    one connection means sharing one transaction and session state, and
    psycodict layers unsynchronized mutable bookkeeping on top (the
    commit-deferral stack behind ``DelayCommit``, the server-side cursor
    counter, the per-object connection references reset together).  So a
    ``PostgresDatabase`` instance is not thread-safe; use one instance per
    process or thread (this is how LMFDB deploys it).

    INPUT:

    - ``create`` -- if True, create psycodict's metadata tables (meta_tables,
      meta_indexes, meta_constraints and their _hist counterparts) when they
      are missing, allowing use of a fresh database
    - ``upgrade`` -- if True, migrate the metadata tables to the format this
      psycodict implements before connecting (see upgrade_metadata and
      MetadataFormats.md).  Without it, a database using an older but
      compatible metadata format connects with a warning and operates at the
      older format.
    - ``**kwargs`` -- passed on to psycopg's connect method

    ATTRIBUTES:

    The following public attributes are stored on the db object.

    - ``server_side_counter`` -- an integer tracking how many buffered connections have been created
    - ``conn`` -- the psycopg connection object
    - ``tablenames`` -- a list of tablenames in the database, as strings
    - ``meta_format`` -- the metadata format this connection operates at (see
      MetadataFormats.md)

    Also, each tablename will be stored as an attribute, so that db.ec_curvedata works for example.

    These table objects are snapshots: if another process later changes the schema
    (adding or dropping columns or tables), call ``refresh_tables`` to update them
    in place instead of restarting the process.

    EXAMPLES::

        >>> db
        Interface to Postgres database
        >>> db.conn
        <psycopg.Connection [IDLE] (host=... database=...) at 0x...>
        >>> 'test_fields' in db.tablenames
        True
        >>> db.test_fields
        Interface to Postgres table test_fields
    """
    # Override the following to use a different class for search tables
    _search_table_class_ = PostgresSearchTable

    def _new_connection(self, **kwargs):
        """
        Create a new connection to the postgres database.
        """
        options = dict(self.config.options["postgresql"])
        # overrides the options passed as keyword arguments
        for key, value in kwargs.items():
            options[key] = value
        self._user = options["user"]
        logging.info(
            "Connecting to PostgresSQL server as: user=%s host=%s port=%s dbname=%s..."
            % (options["user"], options["host"], options["port"], options["dbname"])
        )
        connection = connect(**options)
        logging.info("Done!\n connection = %s" % connection)
        # The following function controls how Python classes are converted to
        # strings for passing to Postgres, and how the results are decoded upon
        # extraction from the database.
        # Note that it has some global effects, since register_adapter
        # is not limited to just one connection
        setup_connection(connection)
        return connection

    def reset_connection(self):
        """
        Resets the connection
        """
        logging.info("Connection broken (status %s); resetting...", self.conn.closed)
        conn = self._new_connection()
        # Note that self is the first entry in self._objects
        for obj in self._objects:
            obj.conn = conn

    def _register_object(self, obj):
        """
        The database holds references to tables, etc so that connections can be refreshed if they fail.
        """
        obj.conn = self.conn
        self._objects.append(obj)

    def __init__(self, config=None, secretsfile=None, create=False, upgrade=False, **kwargs):
        if config is None:
            from .config import Configuration
            config = Configuration()
        self.config = config
        self.server_side_counter = 0
        self._nocommit_stack = 0
        self._silenced = False
        self._objects = []
        # The connection overrides passed here take precedence over config for
        # every connection this database opens, including the separate one a
        # listener() opens (otherwise it could subscribe on a different server
        # or database than the sender writes to).
        self._connect_kwargs = dict(kwargs)
        self.conn = self._new_connection(**kwargs)
        PostgresBase.__init__(self, "db_all", self)
        if self._user == "webserver":
            self._execute(SQL("SET SESSION statement_timeout = '25s'"))

        if create:
            # Create any missing metadata tables before the read-only detection
            # below, which concludes read-only when no tables are visible
            self._bootstrap_meta()

        if upgrade:
            # Migrate the metadata tables up to the format this psycodict
            # expects.  This runs before the format check below, so that
            # ``PostgresDatabase(..., upgrade=True)`` connects at the current
            # format (and without the older-format warning) in one call.
            self.upgrade_metadata()

        if self._execute(SQL("SELECT pg_is_in_recovery()")).fetchone()[0]:
            self._read_only = True
        else:
            # Check if there is a table where we can insert/update
            privileges = ["INSERT", "UPDATE"]
            cur = self._execute(
                SQL(
                    "SELECT count(*) FROM information_schema.role_table_grants "
                    + "WHERE grantee = %s AND table_schema = %s "
                    + "AND privilege_type IN ("
                    + ",".join(["%s"] * len(privileges))
                    + ")"
                ),
                [self._user, "public"] + privileges,
            )
            self._read_only = cur.fetchone()[0] == 0

        self._super_user = (self._execute(SQL("SELECT current_setting('is_superuser')")).fetchone()[0] == "on")

        if self._read_only:
            self._read_and_write_knowls = False
            self._read_and_write_userdb = False
        elif self._super_user and not self._read_only:
            self._read_and_write_knowls = True
            self._read_and_write_userdb = True
        else:
            privileges = ["INSERT", "SELECT", "UPDATE"]
            knowls_tables = ["kwl_knowls"]
            cur = sorted(self._execute(
                SQL(
                    "SELECT table_name, privilege_type "
                    + "FROM information_schema.role_table_grants "
                    + "WHERE grantee = %s AND table_name IN ("
                    + ",".join(["%s"] * len(knowls_tables))
                    + ") AND privilege_type IN ("
                    + ",".join(["%s"] * len(privileges))
                    + ")"
                ),
                [self._user] + knowls_tables + privileges,
            ))
            #            print cur
            #            print sorted([(table, priv) for table in knowls_tables for priv in privileges])
            self._read_and_write_knowls = cur == sorted(
                [(table, priv) for table in knowls_tables for priv in privileges]
            )

            cur = sorted(self._execute(
                SQL(
                    "SELECT privilege_type FROM information_schema.role_table_grants "
                    + "WHERE grantee = %s AND table_schema = %s "
                    + "AND table_name=%s AND privilege_type IN ("
                    + ",".join(["%s"] * len(privileges))
                    + ")"
                ),
                [self._user, "userdb", "users"] + privileges,
            ))
            self._read_and_write_userdb = cur == sorted([(priv,) for priv in privileges])

        logging.info("User: %s", self._user)
        logging.info("Read only: %s", self._read_only)
        logging.info("Super user: %s", self._super_user)
        logging.info("Read/write to userdb: %s", self._read_and_write_userdb)
        logging.info("Read/write to knowls: %s", self._read_and_write_knowls)

        # Refuse to run against a database that still uses the removed
        # search/extras table split
        legacy = self._execute(SQL(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'meta_tables' AND column_name = 'has_extras'"
        ))
        if legacy.rowcount:
            cur = self._execute(SQL("SELECT name FROM meta_tables WHERE has_extras"))
            if cur.rowcount:
                raise RuntimeError(
                    "The following tables still use an extras table, which is no "
                    "longer supported by psycodict: %s.  Merge each extras table "
                    "into its search table before upgrading psycodict."
                    % (", ".join(rec[0] for rec in cur))
                )

        # Check the database's metadata format (see MetadataFormats.md): an
        # older-but-compatible or acceptably-newer format connects with a
        # warning and this connection operates at the shared format,
        # self._meta_format; a layout this psycodict cannot safely use is
        # refused.  _stored_meta_format explains how the format of an
        # unstamped database is inferred.
        stored, min_compat = self._stored_meta_format()
        action, message = self._meta_format_action(stored, min_compat, self._read_only)
        if action == "error":
            raise RuntimeError(message)
        if action == "warn":
            logging.warning(message)
        # The metadata format this connection operates at: everything that
        # reads or writes meta_* columns consults this, so that a psycodict
        # ahead of the database (or behind it) only touches the columns both
        # sides have.
        self._meta_format = min(stored, META_FORMAT)

        self.tablenames = []
        self.refresh_tables()

    def refresh_tables(self):
        """
        Update the table objects to match the current state of the database.

        The set of tables, and each table's columns, types, sort order and
        other metadata, are read from the database when this object is
        created.  A long-running process (such as a website) therefore does
        not see schema changes made from other processes: after a column is
        dropped, for example, its queries still mention the column and fail,
        while a newly added column is silently invisible.  Rather than
        restarting every such process, call this method to bring the process
        up to date -- on a schedule, say, or upon catching an
        ``errors.UndefinedColumn``.

        Existing table objects are updated in place, so table references held
        by application code (``nf = db.nf_fields``) remain valid.  Tables
        created since the last refresh become accessible as attributes and are
        added to ``tablenames``; tables that have been dropped are removed.  A
        reference held to a dropped table's object will raise an error on its
        next query, as it must, since the underlying table no longer exists.
        """
        cur = self._execute(SQL(
            "SELECT table_name, column_name, udt_name::regtype "
            "FROM information_schema.columns ORDER BY table_name, ordinal_position"
        ))
        data_types = {}
        for table_name, column_name, regtype in cur:
            if table_name not in data_types:
                data_types[table_name] = []
            data_types[table_name].append((column_name, regtype))

        try:
            cur = self._execute(SQL(
                "SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, "
                "stats_valid, total, include_nones FROM meta_tables"
            ))
        except UndefinedTable:
            raise ValueError(
                "This database does not contain psycodict's metadata tables. "
                "If this is a fresh database, connect with PostgresDatabase(create=True) "
                "to create them."
            )
        current = set()
        for tabledata in cur:
            tablename = tabledata[0]
            current.add(tablename)
            if tablename in self.tablenames:
                self.__dict__[tablename]._refresh(tabledata[1:], data_types)
            else:
                tabledata += (data_types,)
                table = self._search_table_class_(self, *tabledata)
                self.__dict__[tablename] = table
                self.tablenames.append(tablename)
        for tablename in [name for name in self.tablenames if name not in current]:
            delattr(self, tablename)
            self.tablenames.remove(tablename)
        self.tablenames.sort()

    def __repr__(self):
        return "Interface to Postgres database"

    def _cursor(self, buffered=False):
        """
        Returns a new cursor.

        If buffered, then it creates a server side cursor that must be manually
        closed after done using it.
        """
        if buffered:
            self.server_side_counter += 1
            cur = self.conn.cursor(str(self.server_side_counter), withhold=True)
            # psycopg3's ServerCursor defaults to itersize=100 (psycopg2's
            # named cursors used 2000), which multiplies round trips when
            # iterating over large result sets.
            cur.itersize = 2000
            return cur
        else:
            return self.conn.cursor()

    def _log_db_change(self, operation, tablename=None, logid=None, aborted=False, **data):
        """
        By default we don't log changes (from updates, etc), but you can
        override this method if you want to do some logging.
        """
        pass

    def _existing_roles(self, users):
        """
        Filters a list of role names down to those that exist in the cluster.

        Missing roles produce a warning rather than an error, so that table
        creation works on clusters without the LMFDB roles (lmfdb, webserver).
        """
        existing = {rec[0] for rec in self._execute(SQL("SELECT rolname FROM pg_roles"))}
        missing = [user for user in users if user not in existing]
        if missing:
            logging.warning(
                "Postgres role(s) %s do not exist; skipping grants",
                ", ".join(missing),
            )
        return [user for user in users if user in existing]

    def _grant(self, action, table_name, users):
        """
        Utility function for granting permissions on tables.
        """
        action = action.upper()
        if action not in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
            raise ValueError("%s is not a valid action" % action)
        grantor = SQL("GRANT %s ON TABLE {0} TO {1}" % action)
        for user in self._existing_roles(users):
            self._execute(grantor.format(Identifier(table_name), Identifier(user)), silent=True)

    def grant_select(self, table_name, users=["lmfdb", "webserver"]):
        """
        Grant users the ability to run SELECT statements on a given table

        INPUT:

        - ``table_name`` -- a string, the name of the table
        - ``users`` -- a list of users to grant this permission
        """
        self._grant("SELECT", table_name, users)

    def grant_insert(self, table_name, users=["webserver"]):
        """
        Grant users the ability to run INSERT statements on a given table

        INPUT:

        - ``table_name`` -- a string, the name of the table
        - ``users`` -- a list of users to grant this permission
        """
        self._grant("INSERT", table_name, users)

    def grant_update(self, table_name, users=["webserver"]):
        """
        Grant users the ability to run UPDATE statements on a given table

        INPUT:

        - ``table_name`` -- a string, the name of the table
        - ``users`` -- a list of users to grant this permission
        """
        self._grant("UPDATE", table_name, users)

    def grant_delete(self, table_name, users=["webserver"]):
        """
        Grant users the ability to run DELETE statements on a given table

        INPUT:

        - ``table_name`` -- a string, the name of the table
        - ``users`` -- a list of users to grant this permission
        """
        self._grant("DELETE", table_name, users)

    def _is_read_only(self):
        """
        Whether this instance of the database is read only.
        """
        return self._read_only

    def _can_read_write_knowls(self):
        """
        Whether this instance of the database has permission to read and write to the knowl tables
        """
        return self._read_and_write_knowls

    def _can_read_write_userdb(self):
        """
        Whether this instance of the database has permission to read and write to the user info tables.
        """
        return self._read_and_write_userdb

    def _is_alive(self):
        """
        Check that the connection to the database is active.
        """
        try:
            cur = self._execute(SQL("SELECT 1"))
            if cur.rowcount == 1:
                return True
        except Exception:
            pass
        return False

    def __getitem__(self, name):
        """
        Accesses a PostgresSearchTable object by name.
        """
        if name in self.tablenames:
            return getattr(self, name)
        else:
            raise ValueError("%s is not a search table" % name)

    def table_sizes(self):
        """
        Returns a dictionary containing information on the sizes of the search tables.

        OUTPUT:

        A dictionary with a row for each search table
        (as well as a few others such as kwl_knowls), with entries

        - ``nrows`` -- an estimate for the number of rows in the table
        - ``nstats`` -- an estimate for the number of rows in the stats table
        - ``ncounts`` -- an estimate for the number of rows in the counts table
        - ``total_bytes`` -- the total number of bytes used by the main table, as well as stats, counts, indexes, ancillary storage....
        - ``index_bytes`` -- the number of bytes used for indexes on the main table
        - ``toast_bytes`` -- the number of bytes used for storage of variable length data types, such as strings and jsonb
        - ``table_bytes`` -- the number of bytes used for fixed length storage on the main table
        - ``counts_bytes`` -- the number of bytes used by the counts table
        - ``stats_bytes`` -- the number of bytes used by the stats table
        """
        query = """
SELECT table_name, row_estimate, total_bytes, index_bytes, toast_bytes,
       total_bytes-index_bytes-COALESCE(toast_bytes,0) AS table_bytes FROM (
  SELECT relname as table_name,
         c.reltuples AS row_estimate,
         pg_total_relation_size(c.oid) AS total_bytes,
         pg_indexes_size(c.oid) AS index_bytes,
         pg_total_relation_size(reltoastrelid) AS toast_bytes
  FROM pg_class c
  LEFT JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND relkind = 'r'
) a"""
        sizes = defaultdict(lambda: defaultdict(int))
        cur = self._execute(SQL(query))
        for (
            table_name,
            row_estimate,
            total_bytes,
            index_bytes,
            toast_bytes,
            table_bytes,
        ) in cur:
            if table_name.endswith("_stats"):
                name = table_name[:-6]
                sizes[name]["nstats"] = int(row_estimate)
                sizes[name]["stats_bytes"] = total_bytes
            elif table_name.endswith("_counts"):
                name = table_name[:-7]
                sizes[name]["ncounts"] = int(row_estimate)
                sizes[name]["counts_bytes"] = total_bytes
            else:
                name = table_name
                sizes[name]["nrows"] = int(row_estimate)
                # use the cached account for an accurate count
                if name in self.tablenames:
                    row_cached = self[name].stats.quick_count({})
                    if row_cached is not None:
                        sizes[name]["nrows"] = row_cached
                sizes[name]["index_bytes"] = index_bytes
                sizes[name]["toast_bytes"] = toast_bytes
                sizes[name]["table_bytes"] = table_bytes
            sizes[name]["total_bytes"] += total_bytes
        return sizes

    def _meta_creator(self, meta_name, hist=False, fmt=None):
        """
        Create one of the six metadata tables, with columns generated from
        the shared definitions in base.py (_meta_*_cols and _meta_*_types),
        so that the DDL cannot drift from the code that reads and writes
        these tables.  ``fmt`` gives the metadata format to create the table
        at (default: the current one), so that filling in a table missing
        from an older-format database does not smuggle in a partial upgrade.
        """
        meta_cols, meta_types, _ = _meta_cols_types_jsonb_idx(meta_name, fmt)
        cols = list(meta_cols)
        types = dict(meta_types)
        if hist:
            cols.append("version")
            types["version"] = "integer"
        defaults = _meta_tables_defaults if meta_name == "meta_tables" else {}
        parts = []
        for col in cols:
            # The types and defaults are module constants, not user input
            part = SQL("{0} " + types[col]).format(Identifier(col))
            if col in defaults:
                part = part + SQL(" DEFAULT " + defaults[col])
            parts.append(part)
        tbl = meta_name + ("_hist" if hist else "")
        self._execute(SQL("CREATE TABLE {0} ({1})").format(Identifier(tbl), SQL(", ").join(parts)))
        self.grant_select(tbl)

    @property
    def meta_format(self):
        """
        The metadata format this connection operates at.

        This is the format stamped in the database, capped at the format this
        psycodict implements (``META_FORMAT``).  When it is lower than
        ``META_FORMAT``, features introduced by newer formats are unavailable
        (their methods raise with instructions) until the database is
        migrated with :meth:`upgrade_metadata`; see MetadataFormats.md.
        """
        return self._meta_format

    def _stored_meta_format(self):
        """
        The (version, min_compat) pair recorded in this database's single-row
        ``meta_format`` table.

        A database that has meta tables but no ``meta_format`` is a format-0
        database: psycodict 0.x never stamped.  A database with no meta
        tables at all is fresh, so it reports the current format (the missing
        ``meta_tables`` is diagnosed elsewhere).  ``(None, None)`` means the
        stamp exists but is empty; its format is unknowable, which the caller
        reports rather than guessing.
        """
        if self._table_exists("meta_format"):
            row = self._execute(SQL("SELECT version, min_compat FROM meta_format")).fetchone()
            return (None, None) if row is None else (row[0], row[1])
        elif self._table_exists("meta_tables"):
            return (0, 0)
        return (META_FORMAT, _stamped_min_compat(META_FORMAT))

    @staticmethod
    def _meta_format_action(stored, min_compat, read_only):
        """
        How to treat a database whose stamped metadata format is ``stored``
        (with ``min_compat``, the oldest format allowed to use it) when this
        psycodict implements ``META_FORMAT``: one of ``("ok", None)``,
        ``("warn", message)`` or ``("error", message)``.

        A pure function of its inputs, so the whole compatibility matrix can
        be tested without manufacturing a database in each state.  The policy
        (MetadataFormats.md):

        - the same format connects silently;
        - an older format connects with a warning when every intervening
          migration is marked compatible (the connection then operates at the
          older format, newer features unavailable), and is refused otherwise;
        - a newer format connects with a warning when its stamped
          ``min_compat`` admits this psycodict, and is refused otherwise.
        """
        if stored is None:
            return ("error",
                    "This database's meta_format table is empty, so its "
                    "metadata format is unknown; insert the correct "
                    "(version, min_compat) row to assert compatibility.")
        if stored == META_FORMAT:
            return ("ok", None)
        if stored > META_FORMAT:
            if min_compat is not None and min_compat <= META_FORMAT:
                return ("warn",
                        "This database uses metadata format %s, newer than this "
                        "psycodict (format %s) but marked compatible with it.  "
                        "Metadata added by the newer format is preserved but "
                        "invisible here; upgrade psycodict to use it."
                        % (stored, META_FORMAT))
            return ("error",
                    "This database uses metadata format %s and requires a "
                    "psycodict with format at least %s (this one implements "
                    "format %s): upgrade psycodict."
                    % (stored, min_compat, META_FORMAT))
        # stored < META_FORMAT: possible only when every step up to the
        # current format is registered and marked compatible
        if all(META_MIGRATIONS.get(fmt, {}).get("compatible", False)
               for fmt in range(stored + 1, META_FORMAT + 1)):
            if read_only:
                remedy = ("The warning will go away once the primary "
                          "database is migrated (upgrade_metadata, run by an "
                          "administrator on a read-write connection).")
            else:
                remedy = ("Migrate it with upgrade_metadata() -- or connect "
                          "with PostgresDatabase(upgrade=True) -- at your "
                          "convenience.")
            return ("warn",
                    "This database uses metadata format %s, older than this "
                    "psycodict (format %s).  Everything present in format %s "
                    "keeps working, but features introduced by newer formats "
                    "(see MetadataFormats.md) are unavailable.  %s"
                    % (stored, META_FORMAT, stored, remedy))
        return ("error",
                "This database uses metadata format %s, which this psycodict "
                "(format %s) cannot operate against.  Migrate the database "
                "with upgrade_metadata() (or connect with upgrade=True)%s, or "
                "use the psycodict release matching its format."
                % (stored, META_FORMAT,
                   " on a read-write connection" if read_only else ""))

    def upgrade_metadata(self):
        """
        Migrate this database's metadata tables up to the format that this
        version of psycodict implements (``META_FORMAT``), applying each
        registered migration in order and stamping the format as it goes.

        Connecting to an older-format database only warns (when the formats
        are compatible; see MetadataFormats.md), so migrating is a deliberate
        act -- this method, or ``PostgresDatabase(config=..., upgrade=True)``,
        which bootstraps (when ``create=True``), migrates, and then connects,
        all in one call.

        Migrations only move forward.  A database already at the current
        format is left untouched, so calling this is idempotent; a database
        whose format is *newer* than this psycodict is an error (upgrade
        psycodict instead), as is a ``meta_format`` table that exists but is
        empty (its format is unknown, so it cannot be migrated blindly).
        """
        stored, _ = self._stored_meta_format()
        if stored is None:
            raise RuntimeError(
                "Cannot upgrade the metadata: the meta_format table is empty, "
                "so the current format is unknown.  Insert the correct "
                "(version, min_compat) row into meta_format first."
            )
        if stored > META_FORMAT:
            raise RuntimeError(
                "Cannot upgrade the metadata: this database uses format %s, "
                "which is newer than this psycodict understands (%s); upgrade "
                "psycodict instead." % (stored, META_FORMAT)
            )
        while stored < META_FORMAT:
            target = stored + 1
            step = META_MIGRATIONS.get(target)
            if step is None:
                raise RuntimeError(
                    "No metadata migration from format %s to %s is known"
                    % (stored, target)
                )
            # The DDL and the stamp commit together, so an interrupted
            # migration leaves the database cleanly at the old format.
            with DelayCommit(self, silence=True):
                getattr(self, step["upgrade"])()
                self._stamp_meta_format(target)
            print("Upgraded metadata format %s -> %s (%s)"
                  % (stored, target, step["description"]))
            stored = target
        # A post-construction upgrade lifts the format this connection
        # operates at; during __init__ (upgrade=True) this is recomputed by
        # the format check that follows.
        self._meta_format = META_FORMAT

    def _upgrade_meta_0_to_1(self):
        """
        The DDL migrating metadata format 0 to 1: meta_indexes and its history
        table gain a nullable ``whereclause`` column, holding the predicate of
        a partial index (NULL for an ordinary index).

        The column is added with ``IF NOT EXISTS`` so that re-running the
        migration -- or running it on a database that already grew the column
        out of band -- is a harmless no-op.
        """
        for tbl in ("meta_indexes", "meta_indexes_hist"):
            self._execute(SQL(
                "ALTER TABLE {0} ADD COLUMN IF NOT EXISTS whereclause text"
            ).format(Identifier(tbl)))

    def _stamp_meta_format(self, version):
        """
        Record ``(version, min_compat)`` in the single-row ``meta_format``
        table, creating the table when the database predates it.  Also drops
        the transient ``meta_version`` table that briefly played this role
        during development (it never appeared in a release, and its numbering
        was off by one from the meta_format one).
        """
        min_compat = _stamped_min_compat(version)
        with DelayCommit(self, silence=True):
            if self._table_exists("meta_format"):
                self._execute(SQL("UPDATE meta_format SET version = %s, min_compat = %s"),
                              [version, min_compat])
            else:
                self._execute(SQL(
                    "CREATE TABLE meta_format (version integer NOT NULL, "
                    "min_compat integer NOT NULL)"
                ))
                self._execute(SQL("INSERT INTO meta_format (version, min_compat) VALUES (%s, %s)"),
                              [version, min_compat])
                self.grant_select("meta_format")
            self._execute(SQL("DROP TABLE IF EXISTS meta_version"))
        print("Stamped metadata format %s (min_compat %s)" % (version, min_compat))

    def _create_meta_tables(self, fmt=None):
        with DelayCommit(self, silence=True):
            self._meta_creator("meta_tables", fmt=fmt)
        print("Table meta_tables created")

    def _create_meta_indexes(self, fmt=None):
        with DelayCommit(self, silence=True):
            self._meta_creator("meta_indexes", fmt=fmt)
        print("Table meta_indexes created")

    def _create_meta_constraints(self, fmt=None):
        with DelayCommit(self, silence=True):
            self._meta_creator("meta_constraints", fmt=fmt)
        print("Table meta_constraints created")

    def _create_meta_hist(self, meta_name, fmt=None):
        """
        Create the _hist counterpart of a metadata table, copying any rows
        already present in the base table at version 0.
        """
        meta_cols, _, jsonb_idx = _meta_cols_types_jsonb_idx(meta_name, fmt)
        with DelayCommit(self, silence=True):
            self._meta_creator(meta_name, hist=True, fmt=fmt)
            cols = meta_cols + ("version",)
            rows = self._execute(SQL("SELECT {0} FROM {1}").format(
                SQL(", ").join(map(Identifier, meta_cols)),
                Identifier(meta_name),
            ))
            inserter = SQL("INSERT INTO {0} ({1}) VALUES ({2})").format(
                Identifier(meta_name + "_hist"),
                SQL(", ").join(map(Identifier, cols)),
                SQL(", ").join(Placeholder() * len(cols)),
            )
            for row in rows:
                row = [
                    Json(elt) if i in jsonb_idx else elt for i, elt in enumerate(row)
                ]
                self._execute(inserter, row + [0])
        print("Table %s_hist created" % meta_name)

    def _bootstrap_meta(self):
        """
        Create any missing psycodict metadata tables (meta_tables, meta_indexes,
        meta_constraints, their _hist counterparts, and the meta_format stamp),
        for use on a fresh database.  Called from the constructor when
        ``create=True`` is passed.

        Missing tables are created at the format the database is already at:
        a fresh database comes up at the current format, while filling in the
        gaps of an older-format database must not silently migrate it -- that
        is upgrade_metadata's job, deliberately invoked.
        """
        existing = {
            rec[0] for rec in self._execute(SQL(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            ))
        }
        stored, _ = self._stored_meta_format()
        fmt = META_FORMAT if stored is None else min(stored, META_FORMAT)
        # The base tables must be created before the _hist creators, which copy from them
        for name, creator in [
            ("meta_tables", self._create_meta_tables),
            ("meta_indexes", self._create_meta_indexes),
            ("meta_constraints", self._create_meta_constraints),
            ("meta_tables_hist", self._create_meta_tables_hist),
            ("meta_indexes_hist", self._create_meta_indexes_hist),
            ("meta_constraints_hist", self._create_meta_constraints_hist),
        ]:
            if name not in existing:
                creator(fmt=fmt)
        if "meta_format" not in existing:
            # A database that already had meta tables predates the stamp, so
            # it is stamped with the format it actually has (0); moving it to
            # the current format is a deliberate migration, not a side effect
            # of connecting.  A fresh database is created at the current
            # format.
            self._stamp_meta_format(META_FORMAT if "meta_tables" not in existing else 0)

    def _create_meta_indexes_hist(self, fmt=None):
        self._create_meta_hist("meta_indexes", fmt=fmt)

    def _create_meta_constraints_hist(self, fmt=None):
        self._create_meta_hist("meta_constraints", fmt=fmt)

    def _create_meta_tables_hist(self, fmt=None):
        self._create_meta_hist("meta_tables", fmt=fmt)

    def _clone_storage_settings(self, new_name, table):
        """
        Copy per-column storage settings (the state set by ``ALTER COLUMN ...
        SET STORAGE`` and ``SET COMPRESSION``) from the search table of
        ``table`` to the newly created table ``new_name``.

        Creating a table from column types alone silently resets these to the
        type defaults, so a copy of a source with customized column storage
        would store its rows differently from the source (compressing values
        the source keeps external, or vice versa) and the two tables would
        differ in size even though they hold the same data.  This is the one
        way ``create_table_like`` could produce a copy whose on-disk size
        disagrees with its source (see LMFDB/lmfdb#6775): the row copy itself
        preserves toast compression byte for byte.

        INPUT:

        - ``new_name`` -- the name of the new table, already created
        - ``table`` -- a PostgresSearchTable object giving the source table
        """
        server_version = self._execute(
            SQL("SELECT current_setting('server_version_num')::int")
        ).fetchone()[0]
        # Column level compression settings (attcompression) appeared in
        # postgres 14; on older servers there is only attstorage to copy.
        if server_version >= 140000:
            selecter = SQL(
                "SELECT attname, attstorage, attcompression FROM pg_attribute "
                "WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped"
            )
        else:
            selecter = SQL(
                "SELECT attname, attstorage, '' FROM pg_attribute "
                "WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped"
            )

        def settings(tname):
            return {rec[0]: (rec[1], rec[2]) for rec in self._execute(selecter, [tname])}

        source = settings(table.search_table)
        target = settings(new_name)
        # The keywords are whitelisted here, so it's okay to use string
        # formatting to insert them into the SQL commands below.
        storage_keywords = {"p": "PLAIN", "e": "EXTERNAL", "m": "MAIN", "x": "EXTENDED"}
        compression_keywords = {"p": "pglz", "l": "lz4"}
        with DelayCommit(self, silence=True):
            for col, (storage, compression) in source.items():
                if col not in target:
                    continue
                target_storage, target_compression = target[col]
                if storage != target_storage and storage in storage_keywords:
                    self._execute(
                        SQL(
                            "ALTER TABLE {0} ALTER COLUMN {1} SET STORAGE "
                            + storage_keywords[storage]
                        ).format(Identifier(new_name), Identifier(col))
                    )
                if compression != target_compression and compression in compression_keywords:
                    self._execute(
                        SQL(
                            "ALTER TABLE {0} ALTER COLUMN {1} SET COMPRESSION "
                            + compression_keywords[compression]
                        ).format(Identifier(new_name), Identifier(col))
                    )

    def create_table_like(self, new_name, table, tablespace=None, data=False, indexes=False):
        """
        Creates a new table with the same schema as an existing one, including
        each column's storage and compression settings.  By default neither
        data, indexes nor stats are copied.

        INPUT:

        - ``new_name`` -- a string giving the desired table name.
        - ``table`` -- a string or PostgresSearchTable object giving an existing table.
        - ``tablespace`` -- the tablespace for the new table
        - ``data`` -- whether to copy over data from the source table
        - ``indexes`` -- whether to copy over indexes from the source table
        """
        if isinstance(table, str):
            table = self[table]
        search_columns = {
            typ: [col for col in table.search_cols if table.col_type[col] == typ]
            for typ in set(table.col_type.values())
        }
        # Remove empty lists
        for typ, cols in list(search_columns.items()):
            if not cols:
                search_columns.pop(typ)
        label_col = table._label_col
        table_description = table.description()
        col_description = table.column_description()
        sort = table._sort_orig
        id_ordered = table._id_ordered
        self.create_table(
            new_name,
            search_columns,
            label_col,
            table_description,
            col_description,
            sort,
            id_ordered,
            tablespace=tablespace,
            # Without this an integer id would silently widen to the
            # default bigint in the copy.
            id_type=table.col_type["id"],
            # keep the source's behavior rather than the current default
            include_nones=table._include_nones,
        )
        # Copy the column storage settings before any data, so that rows are
        # stored (kept external, compressed, ...) the same way as the source's.
        self._clone_storage_settings(new_name, table)
        if data:
            logid = table._check_locks("create_table_like")
            aborted = True
            try:
                cols = SQL(", ").join(map(Identifier, ["id"] + table.search_cols))
                self._execute(
                    SQL("INSERT INTO {0} ( {1} ) SELECT {1} FROM {2}").format(
                        Identifier(new_name), cols, Identifier(table.search_table)
                    ),
                )
                aborted = False
            finally:
                table._log_db_change("create_table_like", logid=logid, aborted=aborted, new_name=new_name)
        if indexes:
            for idata in table.list_indexes(verbose=False).values():
                self[new_name].create_index(**idata)
        if data:
            # The bulk insert leaves the new table without planner statistics
            # until autovacuum notices it; analyze right away so that queries
            # against the copy (including the stats refresh below) plan sanely.
            self._execute(SQL("ANALYZE {0}").format(Identifier(new_name)))
            self[new_name].stats.refresh_stats()

    def create_table(
        self,
        name,
        search_columns,
        label_col,
        table_description=None,
        col_description=None,
        sort=None,
        id_ordered=None,
        tablespace=None,
        force_description=False,
        id_type="bigint",
        include_nones=True,
    ):
        """
        Add a new search table to the database.  See also :meth:`create_table_like`.

        INPUT:

        - ``name`` -- the name of the table, which must include an underscore.  See existing names for consistency.
        - ``search_columns`` -- either a dictionary whose keys are valid postgres types and whose values
            are lists of column names (or just a string if only one column has the specified type);
            or a list of pairs (col, type).
            An id column of type ``id_type`` will be added as a primary key if not present.
        - ``label_col`` -- the column holding the LMFDB label.  This will be used in the ``lookup`` method
            and in the display of results on the API.  Use None if there is no appropriate column.
        - ``table_description`` -- a text description of this table
        - ``col_description`` -- a dictionary giving descriptions for the columns
        - ``sort`` -- If not None, provides a default sort order for the table, in formats accepted by
            the ``_sort_str`` method.
        - ``id_ordered`` -- boolean (default None).  If set, the table will be sorted by id when
            pushed to production, speeding up some kinds of search queries.  Defaults to True
            when sort is not None.
        - ``tablespace`` -- (optional) a postgres tablespace to use for the new table
        - ``force_description`` -- whether to require descriptions
        - ``id_type`` -- what postgres type to use for the id column
        - ``include_nones`` -- whether search results should include columns
          whose value is None (default True).  Pass False to omit None values
          from result dictionaries, as was the default before psycodict 1.0.
          The value is stored explicitly in meta_tables, so the flipped
          default reaches databases created before it without any migration.

        COMMON TYPES:

        The postgres types most commonly used are:

        - smallint -- a 2-byte signed integer.
        - integer -- a 4-byte signed integer.
        - bigint -- an 8-byte signed integer.
        - numeric -- exact, high precision integer or decimal.
        - real -- a 4-byte float.
        - double precision -- an 8-byte float.
        - text -- string (see collation note above).
        - boolean -- true or false.
        - jsonb -- data iteratively built from numerics, strings, booleans, nulls, lists and dictionaries.
        - timestamp -- 8-byte date and time with no timezone.
        """
        if name in self.tablenames:
            raise ValueError("%s already exists" % name)
        now = time.time()
        if id_ordered is None:
            id_ordered = sort is not None

        if not isinstance(search_columns, dict):
            search_columns = self._pairs_to_dict(search_columns)
        for typ, L in list(search_columns.items()):
            if isinstance(L, str):
                search_columns[typ] = [L]
        valid_list = sum(search_columns.values(), [])
        valid_set = set(valid_list)
        # Check that columns aren't listed twice
        if len(valid_list) != len(valid_set):
            C = Counter(valid_list)
            raise ValueError("Column %s repeated" % (C.most_common(1)[0][0]))
        # Check that label_col is valid
        if label_col is not None and label_col not in valid_set:
            raise ValueError("label_col must be a search column")

        # Check that sort is valid
        if sort is not None:
            for col in sort:
                if isinstance(col, tuple):
                    if len(col) != 2:
                        raise ValueError("Sort terms must be either strings or pairs")
                    if col[1] not in [1, -1]:
                        raise ValueError("Sort terms must be of the form (col, 1) or (col, -1)")
                    col = col[0]
                if col not in valid_set:
                    raise ValueError("Column %s does not exist" % (col))

        # Check that descriptions are provided if required
        description_columns = []
        for col in search_columns.values():
            if col == 'id':
                continue
            if isinstance(col, str):
                description_columns.append(col)
            else:
                description_columns.extend([c for c in col if c != "id"])
        if force_description:
            if table_description is None or col_description is None:
                raise ValueError("You must provide table and column descriptions")
            if set(col_description) != set(description_columns):
                raise ValueError("Must provide descriptions for all columns")
        else:
            if table_description is None:
                table_description = ""
            if col_description is None:
                col_description = {col: "" for col in description_columns}

        with DelayCommit(self, silence=True):
            self._create_table(name, search_columns, addid=id_type, tablespace=tablespace)
            self.grant_select(name)
            tablespace = self._tablespace_clause(tablespace)
            creator = SQL(
                "CREATE TABLE {0} "
                "(cols jsonb, values jsonb, count bigint, "
                "extra boolean, split boolean DEFAULT FALSE){1}"
            )
            creator = creator.format(Identifier(name + "_counts"), tablespace)
            self._execute(creator)
            self.grant_select(name + "_counts")
            self.grant_insert(name + "_counts")
            creator = SQL(
                "CREATE TABLE {0} "
                '(cols jsonb, stat text COLLATE "C", value numeric, '
                "constraint_cols jsonb, constraint_values jsonb, threshold integer){1}"
            )
            creator = creator.format(Identifier(name + "_stats"), tablespace)
            self._execute(creator)
            self.grant_select(name + "_stats")
            self.grant_insert(name + "_stats")
            # FIXME use global constants ?
            # include_nones is written explicitly rather than left to the
            # column default: existing databases keep the DDL default their
            # meta_tables was created with, so relying on it would give new
            # tables different behavior in old and new databases.
            inserter = SQL(
                "INSERT INTO meta_tables "
                "(name, sort, id_ordered, out_of_order, label_col, include_nones) "
                "VALUES (%s, %s, %s, %s, %s, %s)"
            )
            self._execute(
                inserter,
                [
                    name,
                    Json(sort),
                    id_ordered,
                    not id_ordered,
                    label_col,
                    include_nones,
                ],
            )
            self._notify_schema_change(name)  # rides this transaction
        new_table = self._search_table_class_(
            self,
            name,
            label_col,
            sort=sort,
            id_ordered=id_ordered,
            out_of_order=(not id_ordered),
            total=0,
            include_nones=include_nones,
        )
        # Add the primary key on id, so that methods like drop_pkeys (used by
        # insert_many and reload) find the constraint they expect
        new_table.restore_pkeys()
        new_table.description(table_description)
        new_table.column_description(description=col_description)
        self.__dict__[name] = new_table
        self.tablenames.append(name)
        self.tablenames.sort()
        self._log_db_change(
            "create_table",
            tablename=name,
            name=name,
            search_columns=search_columns,
            label_col=label_col,
            sort=sort,
            id_ordered=id_ordered,
        )
        print("Table %s created in %.3f secs" % (name, time.time() - now))

    def drop_table(self, name, force=False):
        """
        Drop a table.

        INPUT:

        - ``name`` -- the name of the table
        - ``force`` -- refrain from asking for confirmation

        NOTE:

        You cannot drop a table that has been marked important.  You must first set it as not important if you want to drop it.
        """
        table = self[name]
        selecter = SQL("SELECT important FROM meta_tables WHERE name=%s")
        if self._execute(selecter, [name]).fetchone()[0]:
            raise ValueError("You cannot drop an important table.  Use the set_importance method on the table if you actually want to drop it.")
        if not force:
            ok = input("Are you sure you want to drop %s? (y/N) " % (name))
            if not (ok and ok[0] in ["y", "Y"]):
                return
        with DelayCommit(self, silence=True):
            table.cleanup_from_reload()
            indexes = list(self._execute(
                SQL("SELECT index_name FROM meta_indexes WHERE table_name = %s"),
                [name],
            ))
            if indexes:
                self._execute(SQL("DELETE FROM meta_indexes WHERE table_name = %s"), [name])
                print("Deleted indexes {0}".format(", ".join(index[0] for index in indexes)))
            constraints = list(self._execute(
                SQL("SELECT constraint_name FROM meta_constraints WHERE table_name = %s"),
                [name],
            ))
            if constraints:
                self._execute(SQL("DELETE FROM meta_constraints WHERE table_name = %s"), [name])
                print("Deleted constraints {0}".format(", ".join(constraint[0] for constraint in constraints)))
            self._execute(SQL("DELETE FROM meta_tables WHERE name = %s"), [name])
            for tbl in [name, name + "_counts", name + "_stats"]:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(tbl)))
                print("Dropped {0}".format(tbl))
            self.tablenames.remove(name)
            delattr(self, name)
            self._notify_schema_change(name)  # rides this transaction

    def rename_table(self, old_name, new_name):
        """
        Rename a table.

        INPUT:

        - ``old_name`` -- the current name of the table, as a string
        - ``new_name`` -- the new name of the table, as a string
        """
        assert old_name != new_name
        assert new_name not in self.tablenames
        with DelayCommit(self, silence=True):
            table = self[old_name]
            # first rename indexes and constraints
            icols = [Identifier(s) for s in ["index_name", "table_name"]]
            ccols = [Identifier(s) for s in ["constraint_name", "table_name"]]
            rename_index = SQL("ALTER INDEX IF EXISTS {0} RENAME TO {1}")
            rename_constraint = SQL("ALTER TABLE {0} RENAME CONSTRAINT {1} TO {2}")
            for meta, mname, cols in [
                ("meta_indexes", "index_name", icols),
                ("meta_indexes_hist", "index_name", icols),
                ("meta_constraints", "constraint_name", ccols),
                ("meta_constraints_hist", "constraint_name", ccols),
            ]:
                indexes = list(self._execute(
                    SQL("SELECT {0} FROM {1} WHERE table_name = %s").format(
                        Identifier(mname), Identifier(meta)
                    ),
                    [old_name],
                ))
                if indexes:
                    rename_index_in_meta = SQL("UPDATE {0} SET ({1}) = ({2}) WHERE {3} = {4}")
                    rename_index_in_meta = rename_index_in_meta.format(
                        Identifier(meta),
                        SQL(", ").join(cols),
                        SQL(", ").join(Placeholder() * len(cols)),
                        cols[0],
                        Placeholder(),
                    )
                    for old_index_name in indexes:
                        old_index_name = old_index_name[0]
                        new_index_name = old_index_name.replace(old_name, new_name)
                        self._execute(rename_index_in_meta, [new_index_name, new_name, old_index_name])
                        if meta == "meta_indexes":
                            self._execute(rename_index.format(
                                Identifier(old_index_name),
                                Identifier(new_index_name),
                            ))
                        elif meta == "meta_constraints":
                            self._execute(rename_constraint.format(
                                Identifier(old_name),
                                Identifier(old_index_name),
                                Identifier(new_index_name),
                            ))
            else:
                print("Renamed all indexes, constraints and the corresponding metadata")

            # rename meta_tables and meta_tables_hist
            rename_table_in_meta = SQL("UPDATE {0} SET name = %s WHERE name = %s")
            for meta in ["meta_tables", "meta_tables_hist"]:
                self._execute(rename_table_in_meta.format(Identifier(meta)), [new_name, old_name])
            else:
                print("Renamed all entries meta_tables(_hist)")

            rename = SQL("ALTER TABLE {0} RENAME TO {1}")
            for suffix in ["", "_counts", "_stats"]:
                self._execute(rename.format(Identifier(old_name + suffix), Identifier(new_name + suffix)))
                print("Renamed {0} to {1}".format(old_name + suffix, new_name + suffix))

            # rename oldN tables
            for backup_number in range(table._next_backup_number()):
                for ext in ["", "_counts", "_stats"]:
                    old_name_old = "{0}{1}_old{2}".format(old_name, ext, backup_number)
                    new_name_old = "{0}{1}_old{2}".format(new_name, ext, backup_number)
                    if self._table_exists(old_name_old):
                        self._execute(rename.format(Identifier(old_name_old), Identifier(new_name_old)))
                        print("Renamed {0} to {1}".format(old_name_old, new_name_old))
            for ext in ["", "_counts", "_stats"]:
                old_name_tmp = "{0}{1}_tmp".format(old_name, ext)
                new_name_tmp = "{0}{1}_tmp".format(new_name, ext)
                if self._table_exists(old_name_tmp):
                    self._execute(rename.format(Identifier(old_name_tmp), Identifier(new_name_tmp)))
                    print("Renamed {0} to {1}".format(old_name_tmp, new_name_old))

            # initialized table
            tabledata = self._execute(
                SQL(
                    "SELECT name, label_col, sort, count_cutoff, id_ordered, "
                    "out_of_order, stats_valid, total, include_nones "
                    "FROM meta_tables WHERE name = %s"
                ),
                [new_name],
            ).fetchone()
            table = self._search_table_class_(self, *tabledata)
            self.__dict__[new_name] = table
            # Also drop the old attribute (as drop_table does), so that
            # db.<old_name> does not keep handing out a table object whose
            # postgres table no longer exists.
            self.__dict__.pop(old_name, None)
            self.tablenames.append(new_name)
            self.tablenames.remove(old_name)
            self.tablenames.sort()
            # A rename touches both names: the old one is gone, the new one
            # appeared.  Announce both so a listener can drop the stale
            # metadata and pick up the new table (rides this transaction).
            self._notify_schema_change(old_name)
            self._notify_schema_change(new_name)

    def copy_to(self, search_tables, data_folder, fail_on_error=True, **kwds):
        """
        Copy a set of search tables to a folder on the disk.

        INPUT:

        - ``search_tables`` -- a list of strings giving names of tables to copy
        - ``data_folder`` -- a path to a folder to save the data.  The folder must not currently exist.
        - ``**kwds`` -- other arguments are passed on to the ``copy_to`` method of each table.
        """
        if fail_on_error:
            for tablename in search_tables:
                if tablename not in self.tablenames:
                    raise ValueError(f"{tablename} is not in tablenames")

        data_folder = Path(data_folder)

        if data_folder.exists():
            raise ValueError("The path {} already exists".format(data_folder))
        data_folder.mkdir(parents=True)
        failures = []
        for tablename in search_tables:
            if tablename in self.tablenames:
                table = self[tablename]
                searchfile = data_folder / (tablename + ".txt")
                statsfile = data_folder / (tablename + "_stats.txt")
                countsfile = data_folder / (tablename + "_counts.txt")
                indexesfile = data_folder / (tablename + "_indexes.txt")
                constraintsfile = data_folder / (tablename + "_constraints.txt")
                metafile = data_folder / (tablename + "_meta.txt")
                table.copy_to(
                    searchfile=searchfile,
                    countsfile=countsfile,
                    statsfile=statsfile,
                    indexesfile=indexesfile,
                    constraintsfile=constraintsfile,
                    metafile=metafile,
                    **kwds
                )
            else:
                print("%s is not in tablenames " % (tablename,))
                failures.append(tablename)
        if failures:
            print("Failed to copy %s (not in tablenames)" % (", ".join(failures)))

    def copy_to_from_remote(self, search_tables, data_folder, remote_opts=None, fail_on_error=True, **kwds):
        """
        Copy data to a folder from a postgres instance on another server.

        INPUT:

        - ``search_tables`` -- a list of strings giving names of tables to copy
        - ``data_folder`` -- a path to a folder to save the data.  The folder must not currently exist.
        - ``remote_opts`` -- options for the remote connection (passed on to psycopg's connect method)
        - ``**kwds`` -- other arguments are passed on to the ``copy_to`` method of each table.
        """
        if remote_opts is None:
            remote_opts = self.config.get_postgresql_default()

        source = PostgresDatabase(**remote_opts)

        # copy all the data
        source.copy_to(search_tables, data_folder, fail_on_error=fail_on_error, **kwds)

    def reload_all(
        self,
        data_folder,
        halt_on_errors=True,
        resort=None,
        restat=None,
        adjust_schema=False,
        sequential_swap=False,
        **kwds
    ):
        """
        Reloads all tables from files in a given folder.  The filenames must match
        the names of the tables, with ``_counts`` and ``_stats`` appended as appropriate.

        INPUT:

        - ``data_folder`` -- the folder that contains files to be reloaded
        - ``halt_on_errors`` -- whether to stop if a DatabaseError is
          encountered while trying to reload one of the tables
        - ``sequential_swap`` -- if True, then the whole transaction will not
          be wrapped in a DelayCommit, which can sometimes prevent deadlocks
        - ``resort``, ``restat``, ``adjust_schema``, and any extra keywords
          are passed on to the ``reload`` method of each
          :class:`~psycodict.table.PostgresTable`

        Note that this function currently does not reload data that is not in a
        search table, such as knowls or user data.
        """
        data_folder = Path(data_folder)

        if not data_folder.is_dir():
            raise ValueError("The path {} is not a directory".format(data_folder))
        sep = kwds.get("sep", "|")
        with DelayCommit(self, silence=True, active=not sequential_swap):
            file_list = []
            tablenames = []
            non_existent_tables = []
            possible_endings = [
                "_counts.txt",
                "_stats.txt",
                "_indexes.txt",
                "_constraints.txt",
                "_meta.txt",
            ]
            for path in data_folder.glob("*.txt"):
                filename = path.name
                if any(filename.endswith(elt) for elt in possible_endings):
                    continue
                tablename = path.stem
                if tablename not in self.tablenames:
                    non_existent_tables.append(tablename)
            if non_existent_tables:
                if not adjust_schema:
                    raise ValueError(
                        "non existent tables: {0}; use adjust_schema=True to create them".format(
                            ", ".join(non_existent_tables)
                        )
                    )
                print("Creating tables: {0}".format(", ".join(non_existent_tables)))
                for tablename in non_existent_tables:
                    search_table_file = data_folder / (tablename + ".txt")
                    metafile = data_folder / (tablename + "_meta.txt")
                    if not metafile.exists():
                        raise ValueError("meta file missing for {0}".format(tablename))
                    # read metafile
                    with metafile.open("r") as F:
                        rows = list(csv.reader(F, delimiter=str(sep)))
                    if len(rows) != 1:
                        raise RuntimeError("Expected only one row in {0}")
                    meta = dict(zip(_meta_tables_cols, rows[0]))
                    assert meta["name"] == tablename

                    with search_table_file.open("r") as F:
                        search_columns_pairs = self._read_header_lines(F, sep=sep)

                    search_columns = defaultdict(list)
                    for name, typ in search_columns_pairs:
                        if name != "id":
                            search_columns[typ].append(name)

                    # the rest of the meta arguments will be replaced on the reload_all
                    # We use force_description=False so that beta and prod can be out-of-sync with respect to columns and/or descriptions
                    self.create_table(tablename, search_columns, None, force_description=False)

            for tablename in self.tablenames:
                included = []

                searchfile = data_folder / (tablename + ".txt")
                if not searchfile.exists():
                    continue
                included.append(tablename)

                table = self[tablename]

                extrafile = data_folder / (tablename + "_extras.txt")
                if extrafile.exists():
                    raise ValueError(
                        "Unexpected file %s: extras tables are no longer supported; "
                        "merge the extras columns into the search table file" % extrafile
                    )

                countsfile = data_folder / (tablename + "_counts.txt")
                if countsfile.exists():
                    included.append(tablename + "_counts")
                else:
                    countsfile = None

                statsfile = data_folder / (tablename + "_stats.txt")
                if statsfile.exists():
                    included.append(tablename + "_stats")
                else:
                    statsfile = None

                indexesfile = data_folder / (tablename + "_indexes.txt")
                if not indexesfile.exists():
                    indexesfile = None

                constraintsfile = data_folder / (tablename + "_constraints.txt")
                if not constraintsfile.exists():
                    constraintsfile = None

                metafile = data_folder / (tablename + "_meta.txt")
                if not metafile.exists():
                    metafile = None

                file_list.append(
                    (
                        table,
                        (
                            searchfile,
                            countsfile,
                            statsfile,
                            indexesfile,
                            constraintsfile,
                            metafile,
                        ),
                        included,
                    )
                )
                tablenames.append(tablename)
            print("Reloading {0}".format(", ".join(tablenames)))
            failures = []
            for table, filedata, included in file_list:
                try:
                    table.reload(
                        *filedata,
                        resort=resort,
                        restat=restat,
                        final_swap=False,
                        silence_meta=True,
                        adjust_schema=adjust_schema,
                        **kwds
                    )
                except DatabaseError:
                    if halt_on_errors or non_existent_tables:
                        raise
                    else:
                        traceback.print_exc()
                        failures.append(table)
            for table, filedata, included in file_list:
                if table in failures:
                    continue
                table.reload_final_swap(tables=included, metafile=filedata[-1], sep=sep)

        if failures:
            print("Reloaded %s" % (", ".join(tablenames)))
            print(
                "Failures in reloading %s"
                % (", ".join(table.search_table for table in failures))
            )
        else:
            print("Successfully reloaded %s" % (", ".join(tablenames)))

    def reload_all_revert(self, data_folder):
        """
        Reverts the most recent ``reload_all`` by swapping with the backup table
        for each search table modified.

        INPUT:

        - ``data_folder`` -- the folder used in ``reload_all``;
            determines which tables
            were modified.
        """
        data_folder = Path(data_folder)

        if not data_folder.is_dir():
            raise ValueError("The path {} is not a directory".format(data_folder))

        with DelayCommit(self, silence=True):
            for tablename in self.tablenames:
                searchfile = data_folder / (tablename + ".txt")
                if not searchfile.exists():
                    continue
                self[tablename].reload_revert()

    def cleanup_all(self):
        """
        Drops all ``_tmp`` and ``_old`` tables created by the reload() method.
        """
        with DelayCommit(self, silence=True):
            for tablename in self.tablenames:
                table = self[tablename]
                table.cleanup_from_reload()

    def _get_queries(self):
        """
        The queries currently running in this database, excluding this
        connection's own, as (pid, duration, username, query) tuples in
        starting order (oldest first).
        """
        return list(self._execute(SQL(
            "SELECT pid, age(clock_timestamp(), query_start), usename, query "
            "FROM pg_stat_activity "
            "WHERE state = 'active' AND datname = current_database() "
            "AND pid != pg_backend_pid() ORDER BY query_start"
        ), silent=True))

    def show_queries(self):
        """
        Prints the queries currently running in this database (which may be
        holding the locks shown by ``show_locks``; see ``show_blocked`` for
        statements that are stuck behind them).
        """
        queries = self._get_queries()
        if not queries:
            print("No queries currently running")
            return
        # Collapse each query's whitespace once, up front, so the pid, duration
        # and user columns are measured (and aligned) against what prints; the
        # query itself is last, so it needs no padding.
        rows = [("pid %s" % pid, str(duration), user, " ".join(query.split()))
                for pid, duration, user, query in queries]
        pidlen = max(len(pidstr) for pidstr, _, _, _ in rows) + 2
        durlen = max(len(duration) for _, duration, _, _ in rows) + 2
        userlen = max(len(user) for _, _, user, _ in rows) + 2
        for pidstr, duration, user, query in rows:
            print(
                pidstr
                + " " * (pidlen - len(pidstr))
                + duration
                + " " * (durlen - len(duration))
                + user
                + " " * (userlen - len(user))
                + query
            )

    def _get_blocked(self):
        """
        Statements waiting on locks, each paired with a session that actually
        blocks them, as tuples (blocked_pid, blocked_user, blocking_pid,
        blocking_user, blocked_statement, blocking_statement).

        Blockers are determined by pg_blocking_pids, which accounts for lock
        modes, grant status and the wait queue; the well-known pg_locks
        self-join matches on resource identity alone and reports bystanders
        (e.g. an unrelated ACCESS SHARE holder) as blockers.
        """
        return list(self._execute(SQL(
            "SELECT blocked.pid, blocked.usename, "
            "blocking.pid, blocking.usename, "
            "blocked.query, blocking.query "
            "FROM pg_stat_activity blocked "
            "JOIN LATERAL unnest(pg_blocking_pids(blocked.pid)) AS b(bpid) ON true "
            "JOIN pg_stat_activity blocking ON blocking.pid = b.bpid "
            "WHERE blocked.datname = current_database() "
            "ORDER BY blocked.pid, blocking.pid"
        ), silent=True))

    def show_blocked(self):
        """
        Prints the statements that are waiting on locks held by other
        sessions, together with the sessions holding them.
        """
        for bpid, buser, gpid, guser, bquery, gquery in self._get_blocked():
            print("pid %s (%s) blocked on pid %s (%s)" % (bpid, buser, gpid, guser))
            print("  waiting: %s" % " ".join(bquery.split()))
            print("  blocker: %s" % " ".join(gquery.split()))

    def show_locks(self):
        """
        Prints information on all locks currently held on any table.
        """
        locks = sorted(self._get_locks())
        if locks:
            namelen = max(len(name) for (name, locktype, pid, t) in locks) + 3
            typelen = max(len(locktype) for (name, locktype, pid, t) in locks) + 3
            pidlen = max(len(str(pid)) for (name, locktype, pid, t) in locks) + 3
            for name, locktype, pid, t in locks:
                print(
                    name
                    + " " * (namelen - len(name))
                    + locktype
                    + " " * (typelen - len(locktype))
                    + "pid %s" % pid
                    + " " * (pidlen - len(str(pid)))
                    + "age %s" % t
                )
        else:
            print("No locks currently held")

    def tablespaces(self):
        """
        Returns a dictionary giving giving the tablespace for all tables
        """
        D = {rec[0]: rec[1] for rec in self._execute(SQL("SELECT tablename, tablespace FROM pg_tables"))}
        return {name: space if space else "" for (name, space) in D.items()}

    def compare(self, other, tables=None, row_counts=True, null_counts=False, exact=False):
        """
        Returns the differences between the search tables of this database
        and those of another one, such as a beta and a production server.

        The comparison is read-only on both sides: only SELECT statements are
        issued, and (unlike the ``count`` method of a table, which may cache
        its results when count saving is enabled) nothing is recorded in the
        counts tables or meta_tables of either database, so ``other`` may
        safely be a production server.

        INPUT:

        - ``other`` -- another ``PostgresDatabase`` instance; you connect to
          the second server yourself (see the examples below)
        - ``tables`` -- a table name or list of table names (default None,
          meaning every search table of either database); restricts every
          part of the comparison to those tables
        - ``row_counts`` -- boolean (default True).  Whether to compare the
          number of rows in tables present in both databases
        - ``null_counts`` -- boolean (default False).  Whether to compare the
          number of NULL entries in each column shared by both sides.  This
          requires a full scan of each compared table in each database, which
          can take minutes for the largest LMFDB tables, so consider
          restricting ``tables``
        - ``exact`` -- boolean (default False).  By default row counts are
          read from the total cached in meta_tables, which psycodict's write
          paths maintain and ``count()`` reports; that is a single cheap
          query per database, but it can be stale if a table was modified
          from outside psycodict or its statistics were never refreshed.  Set
          to True to run SELECT COUNT(*) on each compared table instead,
          which is exact but slow on big tables (the counting scans run with
          whatever statement timeout each connection has)

        OUTPUT:

        A dictionary with keys

        - ``only_in_self``, ``only_in_other`` -- sorted lists of the names of
          search tables present in only one of the databases
        - ``schema`` -- a dictionary indexed by the tables present in both
          databases whose schemas differ, with values dictionaries containing
          whichever of the following differences occur: ``only_in_self`` and
          ``only_in_other`` (lists of pairs ``(col, type)`` of columns
          present on one side only), ``type_changed`` (a list of triples
          ``(col, type_self, type_other)``, with types rendered in full so
          that e.g. ``numeric(10,2)`` vs ``numeric(20,4)`` is reported) and
          ``meta_changed`` (a list of
          triples ``(item, value_self, value_other)`` recording disagreements
          in the label_col, sort, id_ordered, include_nones or count_cutoff
          settings from meta_tables)
        - ``row_counts`` (if requested) -- ``{table: (rows_self,
          rows_other)}``, only for the tables where the counts differ
        - ``null_counts`` (if requested) -- ``{table: {col: (nulls_self,
          nulls_other)}}``, only for the columns where the counts differ

        EXAMPLES:

        Comparing with a server described by a second configuration file::

            >>> from psycodict.config import Configuration
            >>> from psycodict.database import PostgresDatabase
            >>> prod_config = Configuration(defaults={"config_file": "prod-config.ini"}, readargs=False)  # doctest: +SKIP
            >>> prod = PostgresDatabase(config=prod_config)  # doctest: +SKIP
            >>> db.compare(prod)["only_in_self"]  # doctest: +SKIP
            ['mf_newspaces_test']

        Keyword arguments override the configuration, so a server that
        differs only in its host can reuse this database's configuration::

            >>> prod = PostgresDatabase(config=db.config, host="proddb.lmfdb.xyz")  # doctest: +SKIP
            >>> db.compare(prod, tables="mf_newspaces", null_counts=True)  # doctest: +SKIP
            {'only_in_self': [], 'only_in_other': [], 'schema': {}, 'row_counts': {}, 'null_counts': {}}
        """
        from .dbdiff import compare_databases
        return compare_databases(
            self, other,
            tables=tables,
            row_counts=row_counts,
            null_counts=null_counts,
            exact=exact,
        )

    def show_differences(self, other, tables=None, row_counts=True, null_counts=False, exact=False):
        """
        Prints a readable report of the differences between the search tables
        of this database and those of another one.

        Sections without differences are omitted; if the databases agree,
        prints "No differences found".  See ``compare`` for the meaning of
        the arguments, the cost of the optional comparisons, and the
        guarantee that both databases are only read from.
        """
        from .dbdiff import compare_databases, format_differences
        diff = compare_databases(
            self, other,
            tables=tables,
            row_counts=row_counts,
            null_counts=null_counts,
            exact=exact,
        )
        print(format_differences(diff, self, other))

    def show_slow_report(self, logfile, top=20, cutoff=None):
        """
        Prints an analysis of a slow-query log file: which query shapes take
        the most time, how much smaller the log would be with a higher
        ``slowcutoff``, and which constrained columns lack a supporting index
        (checked against the indexes recorded in ``meta_indexes``).

        See :mod:`psycodict.slowlog` for the underlying functions, which can
        also be used without a database connection.

        INPUT:

        - ``logfile`` -- the filename of a log written via the ``slowlogfile``
          logging option
        - ``top`` -- the number of query shapes to show
        - ``cutoff`` -- only consider queries at least this slow, in seconds
        """
        from .slowlog import show_slow_report
        show_slow_report(logfile, top=top, cutoff=cutoff, db=self)

    # ---------------------------------------------------------------------
    # LISTEN/NOTIFY support (see psycodict/notifications.py for the design).
    # ---------------------------------------------------------------------

    def notify(self, channel, payload=""):
        """
        Send a PostgreSQL notification on ``channel`` with the given payload.

        The notification is sent with ``pg_notify`` on the main connection,
        through ``_execute``, so it is *transactional*: PostgreSQL delivers it
        when the surrounding transaction commits and drops it on rollback.
        Called on its own (outside a ``DelayCommit``) it commits immediately and
        so is delivered at once; called inside a ``DelayCommit`` it rides that
        transaction and is delivered (or dropped) with it.

        INPUT:

        - ``channel`` -- the channel name; must be a plain identifier (letters,
          digits and underscores, not starting with a digit)
        - ``payload`` -- a string payload (default ``""``); received verbatim by
          listeners

        Subscribe with :meth:`listener` (or the standalone
        :class:`~psycodict.notifications.NotificationListener`).
        """
        from .notifications import validate_channel_name
        validate_channel_name(channel)
        self._execute(SQL("SELECT pg_notify(%s, %s)"), [channel, payload])

    def _notify_schema_change(self, tablename):
        """
        Announce that ``tablename``'s schema changed, on the schema channel.

        Used by the schema-changing operations (create/drop/rename table,
        add/drop column, reload swap).  Because it goes through :meth:`notify`
        on the main connection, the announcement is part of the same
        transaction as the change itself.
        """
        from .notifications import SCHEMA_CHANNEL
        self.notify(SCHEMA_CHANNEL, tablename)

    def listener(self, channels=None):
        """
        Return a :class:`~psycodict.notifications.NotificationListener`.

        The listener opens its *own* ``autocommit`` connection from this
        database's configuration and ``LISTEN``s on ``channels`` (default: the
        schema channel ``"psycodict_schema"`` alone).  It is pull-based: call
        ``poll(timeout)`` for a bounded batch, or iterate ``listen()``; use it
        as a context manager to close the connection when done.

        The intended follow-up use is a long-running website process that keeps
        a listener on ``"psycodict_schema"`` and, whenever a table name arrives,
        refreshes that table's cached metadata so newly created columns and
        reloaded tables become visible without a restart.  That refresh
        mechanism is proposed in a separate PR; psycodict ships the notification
        plumbing here without depending on it, so the two can land in either
        order.

        Under a pre-forking web server each worker must build its own listener
        after the fork, and a server in recovery (a hot standby) refuses
        ``LISTEN`` outright; see the *Forking* and *Hot standbys* sections of
        :mod:`psycodict.notifications`.

        INPUT:

        - ``channels`` -- a channel name or iterable of them; ``None`` (default)
          means the schema channel only
        """
        from .notifications import NotificationListener, SCHEMA_CHANNEL
        if channels is None:
            channels = (SCHEMA_CHANNEL,)
        # Pass the same connection overrides the database itself was opened
        # with, so the listener's dedicated connection reaches the same server
        # and database as the sender.
        return NotificationListener(self.config, channels, **self._connect_kwargs)
