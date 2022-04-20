# -*- coding: utf-8 -*-
import csv
import logging
import re
import sys
import time

from psycopg2 import (
    DatabaseError,
    InterfaceError,
    OperationalError,
    ProgrammingError,
    NotSupportedError,
    DataError,
)
from psycopg2.sql import SQL, Identifier, Placeholder, Literal, Composable
from psycopg2.extras import execute_values

from .encoding import Json
from .utils import reraise, DelayCommit, QueryLogFilter, psycopg2_version


# This list is used when creating new tables
number_types = [
    "int2",
    "smallint",
    "smallserial",
    "serial2",
    "int4",
    "int",
    "integer",
    "serial",
    "serial4",
    "int8",
    "bigint",
    "bigserial",
    "serial8",
    "numeric",
    "decimal",
    "float4",
    "real",
    "float8",
    "double precision",
]
types_whitelist = number_types + [
    "boolean",
    "bool",
    "text",
    "char",
    "character",
    "character varying",
    "varchar",
    "json",
    "jsonb",
    "xml",
    "date",
    "interval",
    "time",
    "time without time zone",
    "time with time zone",
    "timetz",
    "timestamp",
    "timestamp without time zone",
    "timestamp with time zone",
    "timestamptz",
    "bytea",
    "bit",
    "bit varying",
    "varbit",
    "point",
    "line",
    "lseg",
    "path",
    "box",
    "polygon",
    "circle",
    "tsquery",
    "tsvector",
    "txid_snapshot",
    "uuid",
    "cidr",
    "inet",
    "macaddr",
    "money",
    "pg_lsn",
]
# add arrays
types_whitelist += [elt + "[]" for elt in types_whitelist]

# make it a set
types_whitelist = set(types_whitelist)


param_types_whitelist = [
    r"^(bit( varying)?|varbit)\s*\([1-9][0-9]*\)$",
    r'(text|(char(acter)?|character varying|varchar(\s*\(1-9][0-9]*\))?))(\s+collate "(c|posix|[a-z][a-z]_[a-z][a-z](\.[a-z0-9-]+)?)")?',
    r"^interval(\s+year|month|day|hour|minute|second|year to month|day to hour|day to minute|day to second|hour to minute|hour to second|minute to second)?(\s*\([0-6]\))?$",
    r"^timestamp\s*\([0-6]\)(\s+with(out)? time zone)?$",
    r"^time\s*\(([0-9]|10)\)(\s+with(out)? time zone)?$",
    r"^(numeric|decimal)\s*\([1-9][0-9]*(,\s*(0|[1-9][0-9]*))?\)$",
]
param_types_whitelist = [re.compile(s) for s in param_types_whitelist]

##################################################################
# meta_* infrastructure                                          #
##################################################################


def jsonb_idx(cols, cols_type):
    return tuple(i for i, elt in enumerate(cols) if cols_type[elt] == "jsonb")


_meta_tables_cols = (
    "name",
    "sort",
    "count_cutoff",
    "id_ordered",
    "out_of_order",
    "has_extras",
    "stats_valid",
    "label_col",
    "total",
    "important",
    "include_nones",
    "table_description",
    "col_description",
)
_meta_tables_cols_notrequired = (
    "count_cutoff",
    "stats_valid",
    "total",
    "important",
    "include_nones",
    "table_description",
    "col_description",
)  # defaults: 1000, true, 0, false, false, "", {}
_meta_tables_types = dict(zip(_meta_tables_cols, (
    "text",
    "jsonb",
    "smallint",
    "boolean",
    "boolean",
    "boolean",
    "boolean",
    "text",
    "bigint",
    "boolean",
    "boolean",
    "text",
    "jsonb",
)))
_meta_tables_jsonb_idx = jsonb_idx(_meta_tables_cols, _meta_tables_types)

_meta_indexes_cols = (
    "index_name",
    "table_name",
    "type",
    "columns",
    "modifiers",
    "storage_params",
)
_meta_indexes_types = dict(
    zip(_meta_indexes_cols, ("text", "text", "text", "jsonb", "jsonb", "jsonb"))
)
_meta_indexes_jsonb_idx = jsonb_idx(_meta_indexes_cols, _meta_indexes_types)

_meta_constraints_cols = (
    "constraint_name",
    "table_name",
    "type",
    "columns",
    "check_func",
)
_meta_constraints_types = dict(
    zip(_meta_constraints_cols, ("text", "text", "text", "jsonb", "text"))
)
_meta_constraints_jsonb_idx = jsonb_idx(_meta_constraints_cols, _meta_constraints_types)


def _meta_cols_types_jsonb_idx(meta_name):
    assert meta_name in ["meta_tables", "meta_indexes", "meta_constraints"]
    if meta_name == "meta_tables":
        meta_cols = _meta_tables_cols
        meta_types = _meta_tables_types
        meta_jsonb_idx = _meta_tables_jsonb_idx
    elif meta_name == "meta_indexes":
        meta_cols = _meta_indexes_cols
        meta_types = _meta_indexes_types
        meta_jsonb_idx = _meta_indexes_jsonb_idx
    elif meta_name == "meta_constraints":
        meta_cols = _meta_constraints_cols
        meta_types = _meta_constraints_types
        meta_jsonb_idx = _meta_constraints_jsonb_idx

    return meta_cols, meta_types, meta_jsonb_idx


def _meta_table_name(meta_name):
    meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
    # the column which will match search_table
    table_name = "table_name"
    if "name" in meta_cols:
        table_name = "name"
    return table_name


class PostgresBase():
    """
    A base class for various objects that interact with Postgres.

    Any class inheriting from this one must provide a connection
    to the postgres database, as well as a name used when creating a logger.
    """

    def __init__(self, loggername, db):
        # Have to record this object in the db so that we can reset the connection if necessary.
        # This function also sets self.conn
        db.register_object(self)
        self._db = db

        logging_options = db.config.options["logging"]
        self.slow_cutoff = logging_options["slowcutoff"]
        self.logger = l = logging.getLogger(loggername)
        l.propogate = False
        l.setLevel(logging.INFO)
        fhandler = logging.FileHandler(logging_options["slowlogfile"])
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        filt = QueryLogFilter()
        fhandler.setFormatter(formatter)
        fhandler.addFilter(filt)
        l.addHandler(fhandler)
        shandler = logging.StreamHandler()
        shandler.setFormatter(formatter)
        l.addHandler(shandler)

    def _execute(
            self,
            query,
            values=None,
            silent=None,
            values_list=False,
            template=None,
            commit=None,
            slow_note=None,
            reissued=False,
            buffered=False
    ):
        """
        Execute an SQL command, properly catching errors and returning the resulting cursor.

        INPUT:

        - ``query`` -- an SQL Composable object, the SQL command to execute.
        - ``values`` -- values to substitute for %s in the query.  Quoting from the documentation
            for psycopg2 (http://initd.org/psycopg/docs/usage.html#passing-parameters-to-sql-queries):

            Never, never, NEVER use Python string concatenation (+) or string parameters
            interpolation (%) to pass variables to a SQL query string. Not even at gunpoint.

        - ``silent`` -- boolean (default None).  If True, don't log a warning for a slow query.
            If None, allow DelayCommit contexts to control silencing.
        - ``values_list`` -- boolean (default False).  If True, use the ``execute_values`` method,
            designed for inserting multiple values.
        - ``template`` -- string, for use with ``values_list`` to insert constant values:
            for example ``"(%s, %s, 42)"``. See the documentation of ``execute_values``
            for more details.
        - ``commit`` -- boolean (default None).  Whether to commit changes on success.  The default
            is to commit unless we are currently in a DelayCommit context.
        - ``slow_note`` -- a tuple for generating more useful data for slow query logging.
        - ``reissued`` -- used internally to prevent infinite recursion when attempting to
            reset the connection.
        - ``buffered`` -- whether to create a server side cursor that must be manually
            closed and connection committed  (to closed the transaction) after using it,
            this implies ``commit=False``.

        .. NOTE:

            If the Postgres connection has been closed, the execute statement will fail.
            We try to recover gracefully by attempting to open a new connection
            and issuing the command again.  However, this approach is not prudent if this
            execute statement is one of a chain of statements, which we detect by checking
            whether ``commit == False``.  In this case, we will reset the connection but reraise
            the interface error.

            The upshot is that you should use ``commit=False`` even for the last of a chain of
            execute statements, then explicitly call ``self.conn.commit()`` afterward.

        OUTPUT:

        - a cursor object from which the resulting records can be obtained via iteration.

        This function will also log slow queries.
        """
        if not isinstance(query, Composable):
            raise TypeError("You must use the psycopg2.sql module to execute queries")

        if buffered:
            if commit is None:
                commit = False
            elif commit:
                raise ValueError("buffered and commit are incompatible")

        try:
            cur = self._db.cursor(buffered=buffered)

            t = time.time()
            if values_list:
                if template is not None:
                    template = template.as_string(self.conn)
                execute_values(cur, query.as_string(self.conn), values, template)
            else:
                try:
                    cur.execute(query, values)
                except (OperationalError, ProgrammingError, NotSupportedError, DataError, SyntaxError) as e:
                    try:
                        context = " happens while executing {}".format(cur.mogrify(query, values))
                    except Exception:
                        context = " happens while executing {} with values {}".format(query, values)
                    reraise(type(e), type(e)(str(e) + context), sys.exc_info()[2])
            if silent is False or (silent is None and not self._db._silenced):
                t = time.time() - t
                if t > self.slow_cutoff:
                    if values_list:
                        query = query.as_string(self.conn).replace("%s", "VALUES_LIST")
                    elif values:
                        try:
                            query = cur.mogrify(query, values)
                        except Exception:
                            # This shouldn't happen since the execution above was successful
                            query = query + str(values)
                    else:
                        query = query.as_string(self.conn)
                    if isinstance(query, bytes): # PY3 compatibility
                        query = query.decode("utf-8")
                    self.logger.info(query + " ran in \033[91m {0!s}s \033[0m".format(t))
                    if slow_note is not None:
                        self.logger.info(
                            "Replicate with db.%s.%s(%s)",
                            slow_note[0],
                            slow_note[1],
                            ", ".join(str(c) for c in slow_note[2:]),
                        )
        except (DatabaseError, InterfaceError):
            if self.conn.closed != 0:
                # If reissued, we need to raise since we're recursing.
                if reissued:
                    raise
                # Attempt to reset the connection
                self._db.reset_connection()
                if commit or (commit is None and self._db._nocommit_stack == 0):
                    return self._execute(
                        query,
                        values=values,
                        silent=silent,
                        values_list=values_list,
                        template=template,
                        commit=commit,
                        slow_note=slow_note,
                        buffered=buffered,
                        reissued=True,
                    )
                else:
                    raise
            else:
                self.conn.rollback()
                raise
        else:
            if commit or (commit is None and self._db._nocommit_stack == 0):
                self.conn.commit()
        return cur

    def _table_exists(self, tablename):
        """
        Check whether the specified table exists

        INPUT:

        - ``tablename`` -- a string, the name of the table
        """
        cur = self._execute(SQL("SELECT 1 from pg_tables where tablename=%s"), [tablename], silent=True)
        return cur.fetchone() is not None

    def _get_locks(self):
        return self._execute(SQL(
            "SELECT t.relname, l.mode, l.pid, age(clock_timestamp(), a.backend_start) "
            "FROM pg_locks l "
            "JOIN pg_stat_all_tables t ON l.relation = t.relid JOIN pg_stat_activity a ON l.pid = a.pid "
            "WHERE l.granted AND t.schemaname <> 'pg_toast'::name AND t.schemaname <> 'pg_catalog'::name"
        ))

    def _table_locked(self, tablename, types="all"):
        """
        Tests whether a table is locked.

        INPUT:

        - tablename -- a string, the name of the table
        - types -- either a string describing the operation being performed
          (which is translated to a list of lock types with which that operation conflicts)
          or a list of lock types.

        The valid strings are:

        - 'update'
        - 'delete'
        - 'insert'
        - 'index'
        - 'all' (includes all locks)

        The valid lock types to filter on are:

        - 'AccessShareLock'
        - 'RowShareLock'
        - 'RowExclusiveLock'
        - 'ShareUpdateExclusiveLock'
        - 'ShareLock'
        - 'ShareRowExclusiveLock'
        - 'ExclusiveLock'
        - 'AccessExclusiveLock'

        OUTPUT:

        A list of pairs (locktype, pid) where locktype is a string as above,
        and pid is the process id of the postgres transaction holding the lock.
        """
        if isinstance(types, str):
            if types in ["update", "delete", "insert"]:
                types = [
                    "ShareLock",
                    "ShareRowExclusiveLock",
                    "ExclusiveLock",
                    "AccessExclusiveLock",
                ]
            elif types == "index":
                types = [
                    "RowExclusiveLock",
                    "ShareUpdateExclusiveLock",
                    "ShareRowExclusiveLock",
                    "ExclusiveLock",
                    "AccessExclusiveLock",
                ]
            elif types != "all":
                raise ValueError("Invalid lock type")
        if types != "all":
            good_types = [
                "AccessShareLock",
                "RowShareLock",
                "RowExclusiveLock",
                "ShareUpdateExclusiveLock",
                "ShareLock",
                "ShareRowExclusiveLock",
                "ExclusiveLock",
                "AccessExclusiveLock",
            ]
            bad_types = [locktype for locktype in types if locktype not in good_types]
            if bad_types:
                raise ValueError("Invalid lock type(s): %s" % (", ".join(bad_types)))
        return [
            (locktype, pid)
            for (name, locktype, pid, t) in self._get_locks()
            if name == tablename and (types == "all" or locktype in types) and pid != self.conn.info.backend_pid
        ]

    def _index_exists(self, indexname, tablename=None):
        """
        Check whether the specified index exists

        INPUT:

        - ``indexname`` -- a string, the name of the index
        - ``tablename`` -- (optional) a string

        OUTPUT:

        If ``tablename`` specified, returns a boolean.  If not, returns
        ``False`` if there is no index with this name, or the corresponding tablename
        as a string if there is.
        """
        if tablename:
            cur = self._execute(
                SQL("SELECT 1 FROM pg_indexes WHERE indexname = %s AND tablename = %s"),
                [indexname, tablename],
                silent=True,
            )
            return cur.fetchone() is not None
        else:
            cur = self._execute(
                SQL("SELECT tablename FROM pg_indexes WHERE indexname=%s"),
                [indexname],
                silent=True,
            )
            table = cur.fetchone()
            if table is None:
                return False
            else:
                return table[0]

    def _relation_exists(self, name):
        """
        Check whether the specified relation exists.  Relations are indexes or constraints.

        INPUT:

        - ``name`` -- a string, the name of the relation
        """
        cur = self._execute(SQL("SELECT 1 FROM pg_class where relname = %s"), [name])
        return cur.fetchone() is not None

    def _constraint_exists(self, constraintname, tablename=None):
        """
        Check whether the specified constraint exists

        INPUT:

        - ``constraintname`` -- a string, the name of the index
        - ``tablename`` -- (optional) a string

        OUTPUT:

        If ``tablename`` specified, returns a boolean.  If not, returns
        ``False`` if there is no constraint with this name, or the corresponding tablename
        as a string if there is.
        """
        if tablename:
            cur = self._execute(
                SQL(
                    "SELECT 1 from information_schema.table_constraints "
                    "WHERE table_name=%s and constraint_name=%s"
                ),
                [tablename, constraintname],
                silent=True,
            )
            return cur.fetchone() is not None
        else:
            cur = self._execute(
                SQL(
                    "SELECT table_name from information_schema.table_constraints "
                    "WHERE constraint_name=%s"
                ),
                [constraintname],
                silent=True,
            )
            table = cur.fetchone()
            if table is None:
                return False
            else:
                return table[0]

    def _list_indexes(self, tablename):
        """
        Lists built index names on the search table `tablename`
        """
        cur = self._execute(
            SQL("SELECT indexname FROM pg_indexes WHERE tablename = %s"),
            [tablename],
            silent=True,
        )
        return [elt[0] for elt in cur]

    def _list_constraints(self, tablename):
        """
        Lists constraint names on the search table `tablename`
        """
        # if we look into information_schema.table_constraints
        # we also get internal constraints, I'm not sure why
        # Alternatively, we do a triple join to get the right answer
        cur = self._execute(
            SQL(
                "SELECT con.conname "
                "FROM pg_catalog.pg_constraint con "
                "INNER JOIN pg_catalog.pg_class rel "
                "           ON rel.oid = con.conrelid "
                "INNER JOIN pg_catalog.pg_namespace nsp "
                "           ON nsp.oid = connamespace "
                "WHERE rel.relname = %s"
            ),
            [tablename],
            silent=True,
        )
        return [elt[0] for elt in cur]

    def _rename_if_exists(self, name, suffix=""):
        """
        Rename an index or constraint if it exists, appending ``_depN`` if so.

        INPUT:

        - ``name`` -- a string, the name of an index or constraint
        - ``suffix`` -- a suffix to append to the name
        """
        if self._relation_exists(name + suffix):
            # First we determine its type
            kind = None
            tablename = self._constraint_exists(name + suffix)
            if tablename:
                kind = "Constraint"
                begin_renamer = SQL("ALTER TABLE {0} RENAME CONSTRAINT").format(Identifier(tablename))
                end_renamer = SQL("{0} TO {1}")
                begin_command = SQL("ALTER TABLE {0}").format(Identifier(tablename))
                end_command = SQL("DROP CONSTRAINT {0}")
            elif self._index_exists(name + suffix):
                kind = "Index"
                begin_renamer = SQL("")
                end_renamer = SQL("ALTER INDEX {0} RENAME TO {1}")
                begin_command = SQL("")
                end_command = SQL("DROP INDEX {0}")
            else:
                raise ValueError(
                    "Relation with name "
                    + name + suffix
                    + " already exists. And it is not an index or a constraint"
                )

            # Find a new name for the existing index
            depsuffix = "_dep0" + suffix
            i = 0
            deprecated_name = name[: 64 - len(depsuffix)] + depsuffix
            while self._relation_exists(deprecated_name):
                i += 1
                depsuffix = "_dep" + str(i) + suffix
                deprecated_name = name[: 64 - len(depsuffix)] + depsuffix

            self._execute(
                begin_renamer + end_renamer.format(Identifier(name + suffix), Identifier(deprecated_name))
            )

            command = begin_command + end_command.format(Identifier(deprecated_name))

            logging.warning(
                "{} with name {} ".format(kind, name + suffix)
                + "already exists. "
                + "It has been renamed to {} ".format(deprecated_name)
                + "and it can be deleted with the following SQL command:\n"
                + self._db.cursor().mogrify(command)
            )

    def _check_restricted_suffix(self, name, kind="Index", skip_dep=False):
        """
        Checks to ensure that the given name doesn't end with one
        of the following restricted suffixes:

        - ``_tmp``
        - ``_pkey``
        - ``_oldN``
        - ``_depN``

        INPUT:

        - ``name`` -- string, the name of an index or constraint
        - ``kind`` -- either ``"Index"`` or ``"Constraint"`` (only used for error msg)
        - ``skip_dep`` -- if true, allow ``_depN`` as a suffix
        """
        tests = [(r"_old[\d]+$", "_oldN"), (r"_tmp$", "_tmp"), ("_pkey$", "_pkey")]
        if not skip_dep:
            tests.append((r"_dep[\d]+_$", "_depN"))
        for match, message in tests:
            if re.match(match, name):
                raise ValueError(
                    "{} name {} is invalid, ".format(kind, name)
                    + "cannot end in {}, ".format(message)
                    + "try specifying a different name"
                )

    @staticmethod
    def _sort_str(sort_list):
        """
        Constructs a psycopg2.sql.Composable object describing a sort order
        for Postgres from a list of columns.

        INPUT:

        - ``sort_list`` -- a list, either of strings (which are interpreted as
        column names in the ascending direction) or of pairs (column name, 1 or -1).

        OUTPUT:

        - a Composable to be used by psycopg2 in the ORDER BY clause.
        """
        L = []
        for col in sort_list:
            if isinstance(col, str):
                L.append(Identifier(col))
            elif col[1] == 1:
                L.append(Identifier(col[0]))
            else:
                L.append(SQL("{0} DESC NULLS LAST").format(Identifier(col[0])))
        return SQL(", ").join(L)

    def _column_types(self, table_name, data_types=None):
        """
        Returns the
            -column list,
            - column types (as a dict), and
            - has_id for a given table_name or list of table names

        INPUT:

        - ``table_name`` -- a string or list of strings
        - ``data_types`` -- (optional) a dictionary providing a list of column names and
        types for each table name.  If not provided, will be looked up from the database.

        EXAMPLE:
        sage: db._column_types('non_existant')
        ([], {}, False)
        sage: db._column_types('test_table')
        ([u'dim',
          u'label',
          u'discriminant',
          u'bad_primes',
          u'new_column1',
          u'new_label',
          u'bar'],
         {u'bad_primes': 'jsonb',
          u'bar': 'text',
          u'dim': 'smallint',
          u'discriminant': 'numeric',
          u'id': 'bigint',
          u'label': 'text',
          u'new_column1': 'text',
          u'new_label': 'text'},
         True)

        """
        has_id = False
        col_list = []
        col_type = {}
        if isinstance(table_name, str):
            table_name = [table_name]
        for tname in table_name:
            if data_types is None or tname not in data_types:
                # in case of an array data type, data_type only gives 'ARRAY', while 'udt_name::regtype' gives us 'base_type[]'
                cur = self._execute(
                    SQL(
                        "SELECT column_name, udt_name::regtype FROM information_schema.columns "
                        "WHERE table_name = %s ORDER BY ordinal_position"
                    ),
                    [tname],
                )
            else:
                cur = data_types[tname]
            for rec in cur:
                col = rec[0]
                if col in col_type and col_type[col] != rec[1]:
                    raise ValueError("Type mismatch on %s: %s vs %s" % (col, col_type[col], rec[1]))
                col_type[col] = rec[1]
                if col != "id":
                    col_list.append(col)
                else:
                    has_id = True
        return col_list, col_type, has_id

    def _copy_to_select(self, select, filename, header="", sep="|", silent=False):
        """
        Using the copy_expert from psycopg2, exports the data from a select statement.

        INPUT:

        - ``select`` -- an SQL Composable object giving a select statement
        - ``header`` -- An initial header to write to the file
        - ``sep`` -- a separator, defaults to ``|``
        - ``silent`` -- suppress reporting success
        """
        if sep != "\t":
            sep_clause = SQL(" (DELIMITER {0})").format(Literal(sep))
        else:
            sep_clause = SQL("")
        copyto = SQL("COPY ({0}) TO STDOUT{1}").format(select, sep_clause)
        with open(filename, "w") as F:
            try:
                F.write(header)
                cur = self._db.cursor()
                cur.copy_expert(copyto, F)
            except Exception:
                self.conn.rollback()
                raise
            else:
                if not silent:
                    print("Created file %s" % filename)

    def _check_header_lines(
        self, F, table_name, columns_set, sep=u"|", prohibit_missing=True
    ):
        """
        Reads the header lines from a file (row of column names, row of column
        types, blank line), checking if these names match the columns set and
        the types match the expected types in the table.
        Returns a list of column names present in the header.

        INPUT:

        - ``F`` -- an open file handle, at the beginning of the file.
        - ``table_name`` -- the table to compare types against (or a list of tables)
        - ``columns_set`` -- a set of the columns expected in the table.
        - ``sep`` -- a string giving the column separator.
        - ``prohibit_missing`` -- raise an error if not all columns present.

        OUTPUT:

        The ordered list of columns.  The first entry may be ``"id"`` if the data
        contains an id column.
        """

        col_list, col_type, _ = self._column_types(table_name)
        columns_set.discard("id")
        if not (columns_set <= set(col_list)):
            raise ValueError("{} is not a subset of {}".format(columns_set, col_list))
        header_cols = self._read_header_lines(F, sep=sep)
        names = [elt[0] for elt in header_cols]
        names_set = set(names)
        if "id" in names_set:
            if names[0] != "id":
                raise ValueError("id must be the first column")
            if header_cols[0][1] != "bigint":
                raise ValueError("id must be of type bigint")
            names_set.discard("id")
            header_cols = header_cols[1:]

        missing = columns_set - names_set
        extra = names_set - columns_set
        wrong_type = [
            (name, typ)
            for name, typ in header_cols
            if name in columns_set and col_type[name] != typ
        ]

        if (missing and prohibit_missing) or extra or wrong_type:
            err = ""
            if missing or extra:
                err += "Invalid header: "
                if missing:
                    err += ", ".join(list(missing)) + " (missing)"
                if extra:
                    err += ", ".join(list(extra)) + " (extra)"
            if wrong_type:
                if len(wrong_type) > 1:
                    err += "Invalid types: "
                else:
                    err += "Invalid type: "
                err += ", ".join(
                    "%s should be %s instead of %s" % (name, col_type[name], typ)
                    for name, typ in wrong_type
                )
            raise ValueError(err)
        return names

    def _copy_from(self, filename, table, columns, header, kwds):
        """
        Helper function for ``copy_from`` and ``reload``.

        INPUT:

        - ``filename`` -- the filename to load
        - ``table`` -- the table into which the data should be added
        - ``columns`` -- a list of columns to load (the file may contain them in
            a different order, specified by a header row)
        - ``header`` -- whether the file has header rows ordering the columns.
            This should be True for search and extra tables, False for counts and stats.
        - ``kwds`` -- passed on to psycopg2's copy_from
        """
        kwds = dict(kwds)  # to not modify the dict kwds, with the pop
        sep = kwds.pop("sep", u"|")

        with DelayCommit(self, silence=True):
            with open(filename) as F:
                if header:
                    # This consumes the first three lines
                    columns = self._check_header_lines(F, table, set(columns), sep=sep)
                    addid = "id" not in columns
                else:
                    addid = False

                if psycopg2_version < (2, 9, 0):
                    # We have to add quotes manually since copy_from doesn't accept
                    # psycopg2.sql.Identifiers
                    # None of our column names have double quotes in them. :-D
                    assert all('"' not in col for col in columns)
                    columns = ['"' + col + '"' for col in columns]
                if addid:
                    # create sequence
                    cur_count = self.max_id(table)
                    seq_name = table + "_seq"
                    create_seq = SQL(
                        "CREATE SEQUENCE {0} START WITH %s MINVALUE %s CACHE 10000"
                    ).format(Identifier(seq_name))
                    self._execute(create_seq, [cur_count + 1] * 2)
                    # edit default value
                    alter_table = SQL(
                        "ALTER TABLE {0} ALTER COLUMN {1} SET DEFAULT nextval(%s)"
                    ).format(Identifier(table), Identifier("id"))
                    self._execute(alter_table, [seq_name])

                cur = self._db.cursor()
                cur.copy_from(F, table, columns=columns, sep=sep, **kwds)

                if addid:
                    alter_table = SQL(
                        "ALTER TABLE {0} ALTER COLUMN {1} DROP DEFAULT"
                    ).format(Identifier(table), Identifier("id"))
                    self._execute(alter_table)
                    drop_seq = SQL("DROP SEQUENCE {0}").format(Identifier(seq_name))
                    self._execute(drop_seq)

                return addid, cur.rowcount

    def _clone(self, table, tmp_table):
        """
        Utility function: creates a table with the same schema as the given one.

        INPUT:

        - ``table`` -- string, the name of an existing table
        - ``tmp_table`` -- string, the name of the new table to create
        """
        if self._table_exists(tmp_table):
            # remove suffix for display message
            for suffix in ['_counts', '_stats']:
                if table.endswith(suffix):
                    table = table[:-len(suffix)]
            raise ValueError(
                "Temporary table %s already exists. "
                "Run db.%s.cleanup_from_reload() if you want to delete it and proceed."
                % (tmp_table, table)
            )
        creator = SQL("CREATE TABLE {0} (LIKE {1})").format(Identifier(tmp_table), Identifier(table))
        self._execute(creator)

    def _check_col_datatype(self, typ):
        if typ.lower() not in types_whitelist:
            if not any(regexp.match(typ.lower()) for regexp in param_types_whitelist):
                raise RuntimeError("%s is not a valid type" % (typ))

    def _create_table(self, name, columns):
        """
        Utility function: creates a table with the schema specified by `columns`

        INPUT:

        - ``name`` -- the desired name
        - ``columns`` -- list of pairs, where the first entry is the column name
        and the second one is the corresponding type
        """
        # FIXME make the code use this
        for col, typ in columns:
            self._check_col_datatype(typ)
        table_col = SQL(", ").join(SQL("{0} %s" % typ).format(Identifier(col)) for col, typ in columns)
        creator = SQL("CREATE TABLE {0} ({1})").format(Identifier(name), table_col)
        self._execute(creator)

    def _create_table_from_header(self, filename, name, sep, addid=True):
        """
        Utility function: creates a table with the schema specified in the header of the file.
        Returns column names found in the header

        INPUT:

        - ``filename`` -- a string, the filename to load the table from
        - ``name`` -- the name of the table
        - ``sep`` -- the separator character, defaulting to tab
        - ``addid`` -- if true, also adds an id column to the created table

        OUTPUT:

        The list of column names and types found in the header
        """
        if self._table_exists(name):
            error_msg = "Table %s already exists." % name
            if name.endswith("_tmp"):
                error_msg += (
                    "Run db.%s.cleanup_from_reload() "
                    "if you want to delete it and proceed." % (name[:-4])
                )
            raise ValueError(error_msg)
        with open(filename, "r") as F:
            columns = self._read_header_lines(F, sep)
        col_list = [elt[0] for elt in columns]
        if addid:
            if ("id", "bigint") not in columns:
                columns = [("id", "bigint")] + columns

        self._create_table(name, columns)
        return col_list

    def _swap(self, tables, source, target):
        """
        Renames tables, indexes, constraints and primary keys, for use in reload.

        INPUT:

        - ``tables`` -- a list of table names to reload (including suffixes like
            ``_extra`` or ``_counts`` but not ``_tmp``).
        - ``source`` -- the source suffix for the swap.
        - ``target`` -- the target suffix for the swap.
        """
        rename_table = SQL("ALTER TABLE {0} RENAME TO {1}")
        rename_constraint = SQL("ALTER TABLE {0} RENAME CONSTRAINT {1} TO {2}")
        rename_index = SQL("ALTER INDEX {0} RENAME TO {1}")

        def target_name(name, tablename, kind):
            original_name = name[:]
            if not name.endswith(source):
                logging.warning(
                    "{} of {} with name {}".format(kind, tablename, name)
                    + " does not end with the suffix {}".format(source)
                )

            elif source != "":
                # drop the suffix
                original_name = original_name[: -len(source)]

            assert original_name + source == name

            target_name = original_name + target
            try:
                self._check_restricted_suffix(original_name, kind, skip_dep=True)
            except ValueError:
                logging.warning(
                    "{} of {} with name {}".format(kind, tablename, name)
                    + " uses a restricted suffix. "
                    + "The name will be extended with a _ in the swap"
                )
                target_name = original_name + "_" + target
            # assure that the rename will be successful
            self._rename_if_exists(target_name)
            return target_name

        with DelayCommit(self, silence=True):
            for table in tables:
                tablename_old = table + source
                tablename_new = table + target
                self._execute(rename_table.format(Identifier(tablename_old), Identifier(tablename_new)))

                done = set({})  # done constraints/indexes
                # We threat pkey separately
                pkey_old = table + source + "_pkey"
                pkey_new = table + target + "_pkey"
                if self._constraint_exists(pkey_old, tablename_new):
                    self._execute(
                        rename_constraint.format(
                            Identifier(tablename_new),
                            Identifier(pkey_old),
                            Identifier(pkey_new),
                        )
                    )
                    done.add(pkey_new)

                for constraint in self._list_constraints(tablename_new):
                    if constraint in done:
                        continue
                    c_target = target_name(constraint, tablename_new, "Constraint")
                    self._execute(
                        rename_constraint.format(
                            Identifier(tablename_new),
                            Identifier(constraint),
                            Identifier(c_target),
                        )
                    )
                    done.add(c_target)

                for index in self._list_indexes(tablename_new):
                    if index in done:
                        continue
                    i_target = target_name(index, tablename_new, "Index")
                    self._execute(
                        rename_index.format(Identifier(index), Identifier(i_target))
                    )
                    done.add(i_target)  # not really needed

    def _read_header_lines(self, F, sep=u"|"):
        """
        Reads the header lines from a file
        (row of column names, row of column types, blank line).
        Returning the dictionary of columns and their types.

        INPUT:

        - ``F`` -- an open file handle, at the beginning of the file.
        - ``sep`` -- a string giving the column separator.

        OUTPUT:

        A list of pairs where the first entry is the column and the second the
        corresponding type
        """
        names = [x.strip() for x in F.readline().strip().split(sep)]
        types = [x.strip() for x in F.readline().strip().split(sep)]
        blank = F.readline()
        if blank.strip():
            raise ValueError("The third line must be blank")
        if len(names) != len(types):
            raise ValueError(
                "The first line specifies %s columns, while the second specifies %s"
                % (len(names), len(types))
            )
        return list(zip(names, types))

    ##################################################################
    # Exporting, importing, reloading and reverting meta_*           #
    ##################################################################

    def _copy_to_meta(self, meta_name, filename, search_table, sep="|"):
        meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
        table_name = _meta_table_name(meta_name)
        table_name_sql = Identifier(table_name)
        meta_name_sql = Identifier(meta_name)
        cols_sql = SQL(", ").join(map(Identifier, meta_cols))
        select = SQL("SELECT {} FROM {} WHERE {} = {}").format(
            cols_sql, meta_name_sql, table_name_sql, Literal(search_table)
        )
        now = time.time()
        with DelayCommit(self):
            self._copy_to_select(select, filename, sep=sep, silent=True)
        print(
            "Exported %s for %s in %.3f secs"
            % (meta_name, search_table, time.time() - now)
        )

    def _copy_from_meta(self, meta_name, filename, sep="|"):
        meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
        try:
            cur = self._db.cursor()
            cur.copy_from(filename, meta_name, columns=meta_cols, sep=sep)
        except Exception:
            self.conn.rollback()
            raise

    def _get_current_meta_version(self, meta_name, search_table):
        # the column which will match search_table
        table_name = _meta_table_name(meta_name)
        table_name_sql = Identifier(table_name)
        meta_name_hist_sql = Identifier(meta_name + "_hist")
        res = self._execute(
            SQL("SELECT MAX(version) FROM {} WHERE {} = %s").format(
                meta_name_hist_sql, table_name_sql
            ),
            [search_table],
        ).fetchone()[0]
        if res is None:
            res = -1
        return res

    def _reload_meta(self, meta_name, filename, search_table, sep="|"):
        meta_cols, _, jsonb_idx = _meta_cols_types_jsonb_idx(meta_name)
        # the column which will match search_table
        table_name = _meta_table_name(meta_name)

        table_name_idx = meta_cols.index(table_name)
        table_name_sql = Identifier(table_name)
        meta_name_sql = Identifier(meta_name)
        meta_name_hist_sql = Identifier(meta_name + "_hist")

        with open(filename, "r") as F:
            lines = list(csv.reader(F, delimiter=str(sep)))
        if not lines:
            return
        for line in lines:
            if line[table_name_idx] != search_table:
                raise RuntimeError(
                    f"column {table_name_idx} (= {line[table_name_idx]}) "
                    f"in the file {filename} doesn't match "
                    f"the search table name {search_table}"
                )

        with DelayCommit(self, silence=True):
            # delete the current columns
            self._execute(
                SQL("DELETE FROM {} WHERE {} = %s").format(meta_name_sql, table_name_sql),
                [search_table],
            )

            # insert new columns
            with open(filename, "r") as F:
                try:
                    cur = self._db.cursor()
                    cur.copy_from(F, meta_name, columns=meta_cols, sep=sep)
                except Exception:
                    self.conn.rollback()
                    raise

            version = self._get_current_meta_version(meta_name, search_table) + 1

            # copy the new rows to history
            cols_sql = SQL(", ").join(map(Identifier, meta_cols))
            rows = self._execute(
                SQL("SELECT {} FROM {} WHERE {} = %s").format(cols_sql, meta_name_sql, table_name_sql),
                [search_table],
            )

            cols = meta_cols + ("version",)
            cols_sql = SQL(", ").join(map(Identifier, cols))
            place_holder = SQL(", ").join(Placeholder() * len(cols))
            query = SQL("INSERT INTO {} ({}) VALUES ({})").format(meta_name_hist_sql, cols_sql, place_holder)

            for row in rows:
                row = [
                    Json(elt) if i in jsonb_idx else elt for i, elt in enumerate(row)
                ]
                self._execute(query, row + [version])

    def _revert_meta(self, meta_name, search_table, version=None):
        meta_cols, _, jsonb_idx = _meta_cols_types_jsonb_idx(meta_name)
        # the column which will match search_table
        table_name = _meta_table_name(meta_name)

        table_name_sql = Identifier(table_name)
        meta_name_sql = Identifier(meta_name)
        meta_name_hist_sql = Identifier(meta_name + "_hist")

        # by the default goes back one step
        currentversion = self._get_current_meta_version(meta_name, search_table)
        if currentversion == -1:
            raise RuntimeError("No history to revert")
        if version is None:
            version = max(0, currentversion - 1)

        with DelayCommit(self, silence=True):
            # delete current rows
            self._execute(
                SQL("DELETE FROM {} WHERE {} = %s").format(meta_name_sql, table_name_sql),
                [search_table],
            )

            # copy data from history
            cols_sql = SQL(", ").join(map(Identifier, meta_cols))
            rows = self._execute(
                SQL("SELECT {} FROM {} WHERE {} = %s AND version = %s").format(
                    meta_name_hist_sql, cols_sql, table_name_sql
                ),
                [search_table, version],
            )

            place_holder = SQL(", ").join(Placeholder() * len(meta_cols))
            query = SQL("INSERT INTO {} ({}) VALUES ({})").format(meta_name_sql, cols_sql, place_holder)

            cols = meta_cols + ("version",)
            cols_sql = SQL(", ").join(map(Identifier, cols))
            place_holder = SQL(", ").join(Placeholder() * len(cols))
            query_hist = SQL("INSERT INTO {} ({}) VALUES ({})").format(
                meta_name_hist_sql, cols_sql, place_holder
            )
            for row in rows:
                row = [Json(elt) if i in jsonb_idx else elt for i, elt in enumerate(row)]
                self._execute(query, row)
                self._execute(query_hist, row + [currentversion + 1])
