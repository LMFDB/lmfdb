"""
This module provides an interface to Postgres supporting
the kinds of queries needed by the LMFDB.

EXAMPLES::

    sage: from lmfdb import db
    sage: db
    Interface to Postgres database
    sage: len(db.tablenames)
    53
    sage: db.tablenames[0]
    'artin_field_data'
    sage: db.artin_field_data
    Interface to Postgres table artin_field_data

You can search using the methods ``search``, ``lucky`` and ``lookup``::

    sage: G = db.gps_small.lookup('8.2')
    sage: G['Exponent']
    4

- ``extra_table`` -- a string or None.  If provided, gives the name of a table that is linked to the search table by an ``id`` column and provides more data that cannot be searched on.  The reason to separate the data into two tables is to reduce the size of the search table.  For large tables this speeds up some queries.
- ``count_table`` -- a string or None.  If provided, gives the name of a table that caches counts for searches on the search table.  These counts are relevant when many results are returned, allowing the search pages to report the number of records even when it would take Postgres a long time to compute this count.

"""

import datetime, inspect, logging, os, random, re, shutil, signal, subprocess, tempfile, time, traceback
from collections import defaultdict, Counter
from glob import glob
import csv
import sys

from psycopg2 import connect, DatabaseError, InterfaceError, OperationalError, ProgrammingError, NotSupportedError, DataError
from psycopg2.sql import SQL, Identifier, Placeholder, Literal, Composable
from psycopg2.extras import execute_values
from psycopg2.extensions import cursor as pg_cursor
from sage.all import cartesian_product_iterator, binomial

from lmfdb.backend.encoding import setup_connection, Json, copy_dumps, numeric_converter
from lmfdb.utils import KeyedDefaultDict, make_tuple, reraise
from lmfdb.logger import make_logger
from lmfdb.typed_data.artin_types import Dokchitser_ArtinRepresentation, Dokchitser_NumberFieldGaloisGroup

# This list is used when creating new tables
types_whitelist = [
    "int2", "smallint", "smallserial", "serial2",
    "int4", "int", "integer", "serial", "serial4",
    "int8", "bigint", "bigserial", "serial8",
    "numeric", "decimal",
    "float4", "real",
    "float8", "double precision",
    "boolean", "bool",
    "text", "char", "character", "character varying", "varchar",
    "json", "jsonb", "xml",
    "date", "interval", "time", "time without time zone", "time with time zone", "timetz",
    "timestamp", "timestamp without time zone", "timestamp with time zone", "timestamptz",
    "bytea", "bit", "bit varying", "varbit",
    "point", "line", "lseg", "path", "box", "polygon", "circle",
    "tsquery", "tsvector",
    "txid_snapshot", "uuid",
    "cidr", "inet", "macaddr",
    "money", "pg_lsn",
]
# add arrays
types_whitelist += [ elt + '[]' for elt in types_whitelist]
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

# The following is used in bucketing for statistics
pg_to_py = {}
for typ in ["int2", "smallint", "smallserial", "serial2",
    "int4", "int", "integer", "serial", "serial4",
    "int8", "bigint", "bigserial", "serial8"]:
    pg_to_py[typ] = int
for typ in ["numeric", "decimal"]:
    pg_to_py[typ] = numeric_converter
for typ in ["float4", "real", "float8", "double precision"]:
    pg_to_py[typ] = float
for typ in ["text", "char", "character", "character varying", "varchar"]:
    pg_to_py[typ] = str

# the non-default operator classes, used in creating indexes
_operator_classes = {'brin':   ['inet_minmax_ops'],
                     'btree':  ['bpchar_pattern_ops', 'cidr_ops', 'record_image_ops',
                                'text_pattern_ops', 'varchar_ops', 'varchar_pattern_ops'],
                     'gin':    ['jsonb_path_ops'],
                     'gist':   ['inet_ops'],
                     'hash':   ['bpchar_pattern_ops', 'cidr_ops', 'text_pattern_ops',
                                'varchar_ops', 'varchar_pattern_ops'],
                     'spgist': ['kd_point_ops']}
# Valid storage parameters by type, used in creating indexes
_valid_storage_params = {'brin':   ['pages_per_range', 'autosummarize'],
                         'btree':  ['fillfactor'],
                         'gin':    ['fastupdate', 'gin_pending_list_limit'],
                         'gist':   ['fillfactor', 'buffering'],
                         'hash':   ['fillfactor'],
                         'spgist': ['fillfactor']}



##################################################################
# meta_* infrastructure                                          #
##################################################################

def jsonb_idx(cols, cols_type):
    return tuple(i for i, elt in enumerate(cols) if cols_type[elt] == "jsonb")

_meta_tables_cols = ("name", "sort", "count_cutoff", "id_ordered",
                     "out_of_order", "has_extras", "stats_valid", "label_col", "total", "important")
_meta_tables_cols_notrequired = ("count_cutoff", "stats_valid", "total", "important") # 1000, true, 0, false
_meta_tables_types = dict(zip(_meta_tables_cols,
    ("text", "jsonb", "smallint", "boolean",
        "boolean", "boolean", "boolean", "text", "bigint", "boolean")))
_meta_tables_jsonb_idx = jsonb_idx(_meta_tables_cols, _meta_tables_types)

_meta_indexes_cols = ("index_name", "table_name", "type", "columns", "modifiers", "storage_params")
_meta_indexes_types = dict(zip(_meta_indexes_cols,
    ("text", "text", "text", "jsonb", "jsonb", "jsonb")))
_meta_indexes_jsonb_idx = jsonb_idx(_meta_indexes_cols, _meta_indexes_types)

_meta_constraints_cols = ("constraint_name", "table_name", "type", "columns", "check_func")
_meta_constraints_types = dict(zip(_meta_constraints_cols,
    ("text", "text", "text", "jsonb", "text")))
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

##################################################################
# counts and stats columns and their types                       #
##################################################################

_counts_cols = ("cols", "values", "count", "extra", "split")
_counts_types =  dict(zip(_counts_cols,
    ("jsonb", "jsonb", "bigint", "boolean", "boolean")))
_counts_jsonb_idx = jsonb_idx(_counts_cols, _counts_types)
_counts_indexes = [{"name": "{}_cols_vals_split",
                   "columns": ('cols', 'values', 'split'),
                   "type": "btree"},
                   {"name": "{}_cols_split",
                    "columns": ('cols', 'split'),
                    "type": "btree"}]


_stats_cols = ("cols", "stat", "value", "constraint_cols", "constraint_values", "threshold")
_stats_types =  dict(zip(_stats_cols,
    ("jsonb", "text", "numeric", "jsonb", "jsonb", "integer")))
_stats_jsonb_idx = jsonb_idx(_stats_cols, _stats_types)

def IdentifierWrapper(name, convert = True):
    """
    Returns a composable representing an SQL identifer.
    This is  wrapper for psycopg2.sql.Identifier that supports ARRAY slicers
    and coverts them (if desired) from the Python format to SQL,
    as SQL starts at 1, and it is inclusive at the end

    Example:

        >>> IdentifierWrapper('name')
        Identifier('name')
        >>> print IdentifierWrapper('name[:10]').as_string(db.conn)
        "name"[:10]
        >>> print IdentifierWrapper('name[1:10]').as_string(db.conn)
        "name"[2:10]
        >>> print IdentifierWrapper('name[1:10]', convert = False).as_string(db.conn)
        "name"[1:10]
        >>> print IdentifierWrapper('name[1:10:3]').as_string(db.conn)
        "name"[2:10:3]
        >>> print IdentifierWrapper('name[1:10:3][0:2]').as_string(db.conn)
        "name"[2:10:3][1:2]
        >>> print IdentifierWrapper('name[1:10:3][0::1]').as_string(db.conn)
        "name"[2:10:3][1::1]
        >>> print IdentifierWrapper('name[1:10:3][0]').as_string(db.conn)
        "name"[2:10:3][1]
    """
    if '[' not in name:
        return Identifier(name)
    else:
        i = name.index('[')
        knife = name[i:]
        name = name[:i]
        # convert python slicer to postgres slicer
        # SQL starts at 1, and it is inclusive at the end
        # so we just need to convert a:b:c -> a+1:b:c

        # first we remove spaces
        knife = knife.replace(' ','')


        # assert that the knife is of the shape [*]
        if knife[0] != '[' or knife[-1] != ']':
            raise ValueError("%s is not in the proper format" % knife)
        chunks = knife[1:-1].split('][')
        # Prevent SQL injection
        if not all(all(x.isdigit() for x in chunk.split(':')) for chunk in chunks):
            raise ValueError("% is must be numeric, brackets and colons"%knife)
        if convert:
            for i, s in enumerate(chunks):
                # each cut is of the format a:b:c
                # where a, b, c are either integers or empty strings
                split = s.split(':',1)
                # nothing to adjust
                if split[0] == '':
                    continue
                else:
                    # we should increment it by 1
                    split[0] = str(int(split[0]) + 1)
                chunks[i] = ':'.join(split)
            sql_slicer = '[' + ']['.join(chunks) + ']'
        else:
            sql_slicer = knife

        return SQL('{0}{1}').format(Identifier(name), SQL(sql_slicer))


class QueryLogFilter(object):
    """
    A filter used when logging slow queries.
    """
    def filter(self, record):
        if record.pathname.startswith('db_backend.py'):
            return 1
        else:
            return 0

class EmptyContext(object):
    """
    Used to simplify code in cases where we may or may not want to open an extras file.
    """
    name = None
    def __enter__(self):
        pass
    def __exit__(self, exc_type, exc_value, traceback):
        pass

class DelayCommit(object):
    """
    Used to set default behavior for whether to commit changes to the database connection.

    Entering this context in a with statement will cause `_execute` calls to not commit by
    default.  When the final DelayCommit is exited, the connection will commit.
    """
    def __init__(self, obj, final_commit=True, silence=None):
        self.obj = obj._db
        self.final_commit = final_commit
        self._orig_silenced = obj._db._silenced
        if silence is not None:
            obj._silenced = silence
    def __enter__(self):
        self.obj._nocommit_stack += 1
    def __exit__(self, exc_type, exc_value, traceback):
        self.obj._nocommit_stack -= 1
        self.obj._silenced = self._orig_silenced
        if exc_type is None and self.obj._nocommit_stack == 0 and self.final_commit:
            self.obj.conn.commit()
        if exc_type is not None:
            self.obj.conn.rollback()

class PostgresBase(object):
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
        from lmfdb.utils.config import Configuration
        logging_options = Configuration().get_logging()
        self.slow_cutoff = logging_options['slowcutoff']
        handler = logging.FileHandler(logging_options['slowlogfile'])
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        filt = QueryLogFilter()
        handler.setFormatter(formatter)
        handler.addFilter(filt)
        self.logger = make_logger(loggername, hl = False, extraHandlers = [handler])


    def _execute(self, query, values=None, silent=None, values_list=False,
                 template=None, commit=None, slow_note=None, reissued=False,
                 buffered=False):
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
        - ``buffered`` -- whether to create a server side cursor that must be
            manually closed after using it, this implies ``commit=False``.

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
                except (OperationalError, ProgrammingError, NotSupportedError, DataError) as e:
                    try:
                        context = ' happens while executing {}'.format(cur.mogrify(query, values))
                    except Exception:
                        context = ' happens while executing {} with values {}'.format(query, values)
                    reraise(type(e), type(e)(str(e) + context), sys.exc_info()[2])
            if silent is False or (silent is None and not self._db._silenced):
                t = time.time() - t
                if t > self.slow_cutoff:
                    if values_list:
                        query = query.as_string(self.conn).replace('%s','VALUES_LIST')
                    elif values:
                        try:
                            query = cur.mogrify(query, values)
                        except Exception:
                            # This shouldn't happen since the execution above was successful
                            query = query + str(values)
                    else:
                        query = query.as_string(self.conn)
                    self.logger.info(query + ' ran in \033[91m {0!s}s \033[0m'.format(t))
                    if slow_note is not None:
                        self.logger.info(
                                "Replicate with db.%s.%s(%s)",
                                slow_note[0], slow_note[1],
                                ", ".join(str(c) for c in slow_note[2:])
                                )
        except (DatabaseError, InterfaceError):
            if self.conn.closed != 0:
                # If reissued, we need to raise since we're recursing.
                if reissued:
                    raise
                # Attempt to reset the connection
                self._db.reset_connection()
                if commit or (commit is None and self._db._nocommit_stack == 0):
                    return self._execute(query,
                                         values=values,
                                         silent=silent,
                                         values_list=values_list,
                                         template=template,
                                         commit=commit,
                                         slow_note=slow_note,
                                         buffered=buffered,
                                         reissued=True)
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
        cur = self._execute(SQL("SELECT 1 from pg_tables where tablename=%s"),
                            [tablename], silent=True)
        return cur.fetchone() is not None

    def _index_exists(self, indexname, tablename=None):
        if tablename:
            cur = self._execute(
                    SQL("SELECT 1 FROM pg_indexes WHERE indexname = %s AND tablename = %s"),
                    [indexname, tablename],  silent=True)
            return cur.fetchone() is not None
        else:
            cur = self._execute(SQL("SELECT tablename FROM pg_indexes WHERE indexname=%s"),
                    [indexname],  silent=True)
            table = cur.fetchone()
            if table is None:
                return False
            else:
                return table[0]

    def _relation_exists(self, name):
        cur = self._execute(SQL('SELECT 1 FROM pg_class where relname = %s'), [name])
        return cur.fetchone() is not None

    def _constraint_exists(self, constraintname, tablename=None):
        if tablename:
            cur = self._execute(SQL("SELECT 1 from information_schema.table_constraints where table_name=%s and constraint_name=%s"), [tablename, constraintname],  silent=True)
            return cur.fetchone() is not None
        else:
            cur = self._execute(SQL("SELECT table_name from information_schema.table_constraints where constraint_name=%s"), [constraintname],  silent=True)
            table = cur.fetchone()
            if table is None:
                return False
            else:
                return table[0]

    def _list_indexes(self, tablename):
        """
        Lists built indexes names on the search table `tablename`
        """
        cur = self._execute(SQL("SELECT indexname FROM pg_indexes WHERE tablename = %s"), [tablename],  silent=True)
        return [elt[0] for elt in cur]

    def _list_constraints(self, tablename):
        """
        Lists constraints names on the search table `tablename`
        """
        # if we look into information_schema.table_constraints
        # we also get internal constraints, I'm not sure why
        # Alternatively, we do a triple join to get the right answer
        cur = self._execute(SQL("SELECT con.conname "
                               "FROM pg_catalog.pg_constraint con "
                               "INNER JOIN pg_catalog.pg_class rel "
                               "           ON rel.oid = con.conrelid "
                               "INNER JOIN pg_catalog.pg_namespace nsp "
                               "           ON nsp.oid = connamespace "
                               "WHERE rel.relname = %s"),
                               [tablename],  silent=True)
        return [elt[0] for elt in cur]



    def _rename_if_exists(self, name, suffix=""):
        """
        Given:
            -- `name` of an index or constraint,
            -- `suffix` a suffix to append to `name`
        if an index or constraint `name` + `suffix` already exists,
        renames so it ends in _depN
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
                raise ValueError("Relation with " +
                                 "name {} ".format(name + suffix) +
                                 "already exists. " +
                                 "And it is not an index " +
                                 "or a constraint")

            # Find a new name for the existing index
            depsuffix = "_dep0" + suffix
            i = 0
            deprecated_name = name[:64 - len(depsuffix)] + depsuffix
            while self._relation_exists(deprecated_name):
                i += 1
                depsuffix = "_dep" + str(i) + suffix
                deprecated_name = name[:64 - len(depsuffix)] + depsuffix

            self._execute(begin_renamer + end_renamer.format(
                Identifier(name + suffix), Identifier(deprecated_name)))

            command = begin_command + end_command.format(Identifier(deprecated_name))

            logging.warning("{} with name {} ".format(kind, name + suffix) +
                            "already exists. " +
                            "It has been renamed to {} ".format(deprecated_name) +
                            "and it can be deleted " +
                            "with the following SQL command:\n" +
                            self._db.cursor().mogrify(command))

    def _check_restricted_suffix(self, name, kind="Index", skip_dep=False):
        """
        Given:
            -- `name` of an index/constraint, and
            -- `kind` in ["Index", "Constraint"] (only used for error msg)
        checks that `name` doesn't end with:
            - _tmp
            _ _pkey
            _ _oldN
            - _depN
        """
        tests = [(r"_old[\d]+$", "_oldN"),
                 (r"_tmp$", "_tmp"),
                 ("_pkey$", "_pkey")]
        if not skip_dep:
            tests.append((r"_dep[\d]+_$", "_depN"))
        for match, message in tests:
            if re.match(match, name):
                raise ValueError("{} name {} is invalid, ".format(kind, name) +
                                 "cannot end in {}, ".format(message) +
                                 "try specifying a different name")

    @staticmethod
    def _sort_str(sort_list):
        """
        Constructs a psycopg2.sql.Composable object describing a sort order for Postgres from a list of columns.

        INPUT:

        - ``sort_list`` -- a list, either of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).

        OUTPUT:

        - a Composable to be used by psycopg2 in the ORDER BY clause.
        """
        L = []
        for col in sort_list:
            if isinstance(col, basestring):
                L.append(Identifier(col))
            elif col[1] == 1:
                L.append(Identifier(col[0]))
            else:
                L.append(SQL("{0} DESC").format(Identifier(col[0])))
        return SQL(", ").join(L)

    def _column_types(self, table_name, data_types=None):
        """
        Returns the column list, column types (as a dict), and has_id for a given table_name
        """
        has_id = False
        col_list = []
        col_type = {}
        if data_types is None or table_name not in data_types:
            # in case of an array data type, data_type only gives 'ARRAY', while 'udt_name::regtype' gives us 'base_type[]'
            cur = self._execute(SQL("SELECT column_name, udt_name::regtype FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position"), [table_name])
        else:
            cur = data_types[table_name]
        for rec in cur:
            col = rec[0]
            col_type[col] = rec[1]
            if col != 'id':
                col_list.append(col)
            else:
                has_id = True
        return col_list, col_type, has_id

    def _copy_to_select(self, select, filename, header="", sep=None, silent=False):
        """
        Using the copy_expert from psycopg2 exports the data from a select statement.
        """
        if sep:
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
                    print "Created file %s" % filename

    def _check_header_lines(self, F, table_name, columns_set, sep=u"\t"):
        """
        Reads the header lines from a file (row of column names, row of column
        types, blank line), checking if these names match the columns set and
        the types match the expected types in the table.
        Returns a list of column names present in the header.

        INPUT:

        - ``F`` -- an open file handle, at the beginning of the file.
        - ``table_name`` -- the table to compare types against
        - ``columns_set`` -- a set of the columns expected in the table.
        - ``sep`` -- a string giving the column separator.

        OUTPUT:

        The ordered list of columns.  The first entry may be ``"id"`` if the data
        contains an id column.
        """

        col_list, col_type, _ = self._column_types(table_name)
        columns_set.discard("id")
        if not (columns_set <= set(col_list)):
            raise ValueError("{} is not a subset of {}".format(columns_set, col_type.keys()))
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
        wrong_type = [(name, typ) for name, typ in header_cols
                if name in columns_set and col_type[name] != typ]

        if missing or extra or wrong_type:
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
                        for name, typ in wrong_type)
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
        - ``cur_count`` -- the current number of rows in the table
        - ``header`` -- whether the file has header rows ordering the columns.
            This should be True for search and extra tables, False for counts and stats.
        - ``kwds`` -- passed on to psycopg2's copy_from
        """
        sep = kwds.get("sep", u"\t")

        with DelayCommit(self, silence=True):
            with open(filename) as F:
                if header:
                    # This consumes the first three lines
                    columns = self._check_header_lines(F, table, set(columns), sep=sep)
                    addid = ('id' not in columns)
                else:
                    addid = False

                # We have to add quotes manually since copy_from doesn't accept
                # psycopg2.sql.Identifiers
                # None of our column names have double quotes in them. :-D
                assert all('"' not in col for col in columns)
                columns = ['"' + col + '"' for col in columns]
                if addid:
                    # create sequence
                    cur_count = self.max_id(table)
                    seq_name = table + '_seq'
                    create_seq = SQL("CREATE SEQUENCE {0} START WITH %s MINVALUE %s CACHE 10000").format(Identifier(seq_name))
                    self._execute(create_seq, [cur_count+1]*2);
                    # edit default value
                    alter_table = SQL("ALTER TABLE {0} ALTER COLUMN {1} SET DEFAULT nextval(%s)").format(Identifier(table), Identifier('id'))
                    self._execute(alter_table, [seq_name])

                cur = self._db.cursor()
                cur.copy_from(F, table, columns=columns, **kwds)

                if addid:
                    alter_table = SQL("ALTER TABLE {0} ALTER COLUMN {1} DROP DEFAULT").format(Identifier(table), Identifier('id'))
                    self._execute(alter_table)
                    drop_seq = SQL("DROP SEQUENCE {0}").format(Identifier(seq_name))
                    self._execute(drop_seq)

                return addid, cur.rowcount

    def _clone(self, table, tmp_table):
        """
        Utility function: creates a table with the same schema as the given one.
        """
        if self._table_exists(tmp_table):
            raise ValueError("Temporary table %s already exists.  Run db.%s.cleanup_from_reload() if you want to delete it and proceed."%(tmp_table, table))
        creator = SQL("CREATE TABLE {0} (LIKE {1})").format(Identifier(tmp_table), Identifier(table))
        self._execute(creator)

    def _create_table(self, name, columns):
        """
        Utility function: creates a table with the schema specified by `columns`

        INPUT:

        - ``name`` -- the desired name
        - ``columns`` -- list of pairs, where the first entry is the column name
        and the second one is the corresponding type
        """
        #FIXME make the code use this
        for col, typ in columns:
            if typ not in types_whitelist:
                if not any(regexp.match(typ.lower()) for regexp in param_types_whitelist):
                    raise RuntimeError("%s is not a valid type"%(typ))

        table_col = SQL(", ").join(SQL("{0} %s"%typ).format(Identifier(col)) for col, typ in columns)
        creator = SQL("CREATE TABLE {0} ({1})").format(Identifier(name), table_col)
        self._execute(creator)

    def _create_table_from_header(self, filename, name, addid=True):
        """
        Utility function: creates a table with the schema specified in the header of the file.
        Returns column names found in the header
        """
        if self._table_exists(name):
            error_msg = "Table %s already exists." % name
            if name.endswith("_tmp"):
                error_msg += "Run db.%s.cleanup_from_reload() if you want to delete it and proceed." % (name[:-4])
            raise ValueError(error_msg)
        with open(filename, "r") as F:
            columns = self._read_header_lines(F)
        col_list = [elt[0] for elt in columns]
        if addid:
            if ('id','bigint') not in columns:
                columns = [('id','bigint')] + columns

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
                        "{} of {} with name {}".format(kind, tablename, name) +
                        " does not end with the suffix {}".format(source))

            elif source != '':
                # drop the suffix
                original_name = original_name[:-len(source)]

            assert original_name + source == name

            target_name = original_name + target
            try:
                self._check_restricted_suffix(original_name, kind, skip_dep=True)
            except ValueError:
                logging.warning(
                        "{} of {} with name {}".format(kind, tablename, name) +
                        " uses a restricted suffix. ".format(source) +
                        "The name will be extended with a _ in the swap")
                target_name = original_name + '_' + target
            # assure that the rename will be successful
            self._rename_if_exists(target_name)
            return target_name



        with DelayCommit(self, silence=True):
            for table in tables:
                tablename_old = table + source
                tablename_new = table + target
                self._execute(rename_table.format(Identifier(tablename_old), Identifier(tablename_new)))

                done = set({}) # done constraints/indexes
                # We threat pkey separately
                pkey_old = table + source + "_pkey"
                pkey_new = table + target + "_pkey"
                if self._constraint_exists(pkey_old, tablename_new):
                    self._execute(rename_constraint.format(Identifier(tablename_new),
                                                           Identifier(pkey_old),
                                                           Identifier(pkey_new)))
                    done.add(pkey_new)


                for constraint in self._list_constraints(tablename_new):
                    if constraint in done:
                        continue
                    c_target = target_name(constraint,
                                           tablename_new,
                                           "Constraint")
                    self._execute(
                            rename_constraint.format(Identifier(tablename_new),
                                                     Identifier(constraint),
                                                     Identifier(c_target)))
                    done.add(c_target)

                for index in self._list_indexes(tablename_new):
                    if index in done:
                        continue
                    i_target = target_name(index, tablename_new, "Index")
                    self._execute(rename_index.format(Identifier(index),
                                                      Identifier(i_target)))
                    done.add(i_target) # not really needed




    def _read_header_lines(self, F, sep=u"\t"):
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
            raise ValueError("The first line specifies %s columns, while the second specifies %s"%(len(names), len(types)))
        return zip(names, types)


    ##################################################################
    # Exporting, importing, reloading and reverting meta_*           #
    ##################################################################


    def _copy_to_meta(self, meta_name, filename, search_table):
        meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
        table_name = _meta_table_name(meta_name)
        table_name_sql = Identifier(table_name)
        meta_name_sql = Identifier(meta_name)
        cols_sql = SQL(", ").join(map(Identifier, meta_cols))
        select = SQL("SELECT {} FROM {} WHERE {} = {}").format(
                cols_sql, meta_name_sql, table_name_sql, Literal(search_table))
        now = time.time()
        with DelayCommit(self):
            self._copy_to_select(select, filename, silent=True)
        print "Exported %s for %s in %.3f secs" % (meta_name,
                search_table, time.time() - now)

    def _copy_from_meta(self, meta_name, filename):
        meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
        try:
            cur = self._db.cursor()
            cur.copy_from(filename, meta_name, columns=meta_cols)
        except Exception:
            self.conn.rollback()
            raise

    def _get_current_meta_version(self, meta_name, search_table):
        # the column which will match search_table
        table_name = _meta_table_name(meta_name)
        table_name_sql = Identifier(table_name)
        meta_name_hist_sql = Identifier(meta_name + "_hist")
        res = self._execute(SQL(
            "SELECT MAX(version) FROM {} WHERE {} = %s"
            ).format(meta_name_hist_sql, table_name_sql),
            [search_table]
            ).fetchone()[0]
        if res is None:
            res = -1
        return res

    def _reload_meta(self, meta_name, filename, search_table):

        meta_cols, _, jsonb_idx = _meta_cols_types_jsonb_idx(meta_name)
        # the column which will match search_table
        table_name = _meta_table_name(meta_name)

        table_name_idx = meta_cols.index(table_name)
        table_name_sql = Identifier(table_name)
        meta_name_sql = Identifier(meta_name)
        meta_name_hist_sql = Identifier(meta_name + "_hist")


        with open(filename, "r") as F:
            lines = [line for line in csv.reader(F, delimiter = "\t")]
            if len(lines) == 0:
                return
            for line in lines:
                if line[table_name_idx] != search_table:
                    raise RuntimeError("column %d in the file doesn't match the search table name" % table_name_idx)


        with DelayCommit(self, silence=True):
            # delete the current columns
            self._execute(SQL(
                "DELETE FROM {} WHERE {} = %s"
                ).format(meta_name_sql, table_name_sql),
                [search_table])

            # insert new columns
            with open(filename, "r") as F:
                try:
                    cur = self._db.cursor()
                    cur.copy_from(F, meta_name, columns=meta_cols)
                except Exception:
                    self.conn.rollback()
                    raise

            version = self._get_current_meta_version(meta_name, search_table) + 1

            # copy the new rows to history
            cols_sql = SQL(", ").join(map(Identifier, meta_cols))
            rows = self._execute(SQL(
                "SELECT {} FROM {} WHERE {} = %s"
                ).format(cols_sql, meta_name_sql, table_name_sql),
                [search_table])

            cols = meta_cols + ('version',)
            cols_sql = SQL(", ").join(map(Identifier, cols))
            place_holder = SQL(", ").join(Placeholder() * len(cols))
            query = SQL(
                    "INSERT INTO {} ({}) VALUES ({})"
                    ).format(meta_name_hist_sql, cols_sql, place_holder)

            for row in rows:
                row = [Json(elt) if i in jsonb_idx else elt
                        for i, elt in enumerate(row)]
                self._execute(query, row + [version])


    def _revert_meta(self, meta_name, search_table, version = None):
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
            self._execute(SQL(
                "DELETE FROM {} WHERE {} = %s"
                ).format(meta_name_sql, table_name_sql),
                [search_table])

            # copy data from history
            cols_sql = SQL(", ").join(map(Identifier, meta_cols))
            rows = self._execute(SQL(
                "SELECT {} FROM {} WHERE {} = %s AND version = %s"
                ).format(meta_name_hist_sql, cols_sql, table_name_sql),
                [search_table, version])


            place_holder = SQL(", ").join(Placeholder() * len(meta_cols))
            query =  SQL(
                    "INSERT INTO {} ({}) VALUES ({})"
                    ).format(meta_name_sql, cols_sql, place_holder)

            cols = meta_cols + ('version',)
            cols_sql = SQL(", ").join(map(Identifier, cols))
            place_holder = SQL(", ").join(Placeholder() * len(cols))
            query_hist = SQL(
                    "INSERT INTO {} ({}) VALUES ({})"
                    ).format(meta_name_hist_sql, cols_sql, place_holder)
            for row in rows:
                row = [Json(elt) if i in jsonb_idx else elt
                        for i, elt in enumerate(row)]
                self._execute(query, row)
                self._execute(query_hist, row + [currentversion + 1,])





class PostgresTable(PostgresBase):
    """
    This class is used to abstract a table in the LMFDB database
    on which searches are performed.  Technically, it may represent
    more than one table, since some tables are split in two for performance
    reasons.

    INPUT:

    - ``db`` -- an instance of ``PostgresDatabase``, currently just used to store the common connection ``conn``.
    - ``search_table`` -- a string, the name of the table in postgres.
    - ``label_col`` -- the column holding the LMFDB label, or None if no such column exists.
    - ``sort`` -- a list giving the default sort order on the table, or None.  If None, sorts that can return more than one result must explicitly specify a sort order.  Note that the id column is sometimes used for sorting; see the ``search`` method for more details.
    - ``count_cutoff`` -- an integer parameter (default 1000) which determines the threshold at which searches will no longer report the exact number of results.
    """
    def __init__(self, db, search_table, label_col, sort=None, count_cutoff=1000, id_ordered=False, out_of_order=False, has_extras=False, stats_valid=True, total=None, data_types=None):
        self.search_table = search_table
        self._label_col = label_col
        self._count_cutoff = count_cutoff
        self._id_ordered = id_ordered
        self._out_of_order = out_of_order
        self._stats_valid = stats_valid
        PostgresBase.__init__(self, search_table, db)
        self.col_type = {}
        self.has_id = False
        self._search_cols = []
        if has_extras:
            self.extra_table = search_table + "_extras"
            self._extra_cols, self.col_type, _ = self._column_types(
                                                        self.extra_table,
                                                        data_types=data_types)
        else:
            self.extra_table = None
            self._extra_cols = []

        self._search_cols, extend_coltype, self.has_id = self._column_types(
                                                        search_table,
                                                        data_types=data_types)
        self.col_type.update(extend_coltype)
        self._set_sort(sort)
        self.stats = PostgresStatsTable(self, total)
        self._verifier = None # set when importing lmfdb.verify


    def _set_sort(self, sort):
        """
        Initialize the sorting attributes from a list of columns or pairs (col, direction)
        """
        self._sort_orig = sort
        self._sort_keys = set([])
        if sort:
            for col in sort:
                if isinstance(col, basestring):
                    self._sort_keys.add(col)
                else:
                    self._sort_keys.add(col[0])
            self._primary_sort = sort[0]
            if not isinstance(self._primary_sort, basestring):
                self._primary_sort = self._primary_sort[0]
            self._sort = self._sort_str(sort)
        else:
            self._sort = self._primary_sort = None

    def __repr__(self):
        return "Interface to Postgres table %s"%(self.search_table)

    ##################################################################
    # Helper functions for querying                                  #
    ##################################################################

    def _parse_projection(self, projection):
        """
        Parses various ways of specifying which columns are desired.

        INPUT:

        - ``projection`` -- either 0, 1, 2, 3 a dictionary or list of column names.

          - If 0, projects just to the ``label``.  If the search table does not have a label column, raises a RuntimeError.
          - If 1, projects to all columns in the search table.
          - If 2, projects to all columns in either the search or extras tables.
          - If 3, as 2 but with id included
          - If a dictionary, can specify columns to include by giving True values, or columns to exclude by giving False values.
          - If a list, specifies which columns to include.
          - If a string, projects onto just that column; searches will return the value rather than a dictionary.

        OUTPUT:

        - a tuple of columns to be selected that are in the search table
        - a tuple of columns to be selected that are in the extras table (empty if it doesn't exist)

        EXAMPLES::

            sage: from lmfdb import db
            sage: ec = db.ec_padic
            sage: nf = db.nf_fields
            sage: nf._parse_projection(0)
            ((u'label',), ())
            sage: ec._parse_projection(1)
            ((u'lmfdb_iso', u'p', u'prec', u'val', u'unit'), ())
            sage: ec._parse_projection({"val":True, "unit":True})
            ((u'val', u'unit'), ())

        When the data is split across two tables, some columns may be in the extras table::

            sage: nf._parse_projection(["label", "unitsGmodule"])
            (('label'), ('unitsGmodule',))

        If you want the "id" column, you can list it explicitly::

            sage: nf._parse_projection(["id", "label", "unitsGmodule"])
            (('id', 'label'), ('unitsGmodule',))

        You can specify a dictionary with columns to exclude:

            sage: ec._parse_projection({"prec":False})
            ((u'lmfdb_iso', u'p', u'val', u'unit'), ())
        """
        search_cols = []
        extra_cols = []
        if projection == 0:
            if self._label_col is None:
                raise RuntimeError("No label column for %s"%(self.search_table))
            return (self._label_col,), ()
        elif not projection:
            raise ValueError("You must specify at least one key.")
        if projection == 1:
            return tuple(self._search_cols), ()
        elif projection == 2:
            return tuple(self._search_cols), tuple(self._extra_cols)
        elif projection == 3:
            return tuple(["id"] + self._search_cols), tuple(self._extra_cols)
        elif isinstance(projection, dict):
            projvals = set(bool(val) for val in projection.values())
            if len(projvals) > 1:
                raise ValueError("You cannot both include and exclude.")
            including = projvals.pop()
            include_id = projection.pop("id", False)
            for col in self._search_cols:
                if (col in projection) == including:
                    search_cols.append(col)
                projection.pop(col, None)
            for col in self._extra_cols:
                if (col in projvals) == including:
                    extra_cols.append(col)
                projection.pop(col, None)
            if projection: # there were more columns requested
                raise ValueError("%s not column of %s"%(", ".join(projection), self.search_table))
        else: # iterable or basestring
            if isinstance(projection, basestring):
                projection = [projection]
            include_id = False
            for col in projection:
                colname = col.split('[',1)[0]
                if colname in self._search_cols:
                    search_cols.append(col)
                elif colname in self._extra_cols:
                    extra_cols.append(col)
                elif col == 'id':
                    include_id = True
                else:
                    raise ValueError("%s not column of %s"%(col, self.search_table))
        if include_id:
            search_cols.insert(0, "id")
        return tuple(search_cols), tuple(extra_cols)

    def _parse_special(self, key, value, col, force_json):
        """
        Implements more complicated query conditions than just testing for equality:
        inequalities, containment and disjunctions.

        INPUT:
        - ``key`` -- a code starting with $ from the following list:
            - ``$lte`` -- less than or equal to
            - ``$lt`` -- less than
            - ``$gte`` -- greater than or equal to
            - ``$gt`` -- greater than
            - ``$ne`` -- not equal to
            - ``$in`` -- the column must be one of the given set of values
            - ``$nin`` -- the column must not be any of the given set of values
            - ``$contains`` -- for json columns, the given value should be a subset of the column.
            - ``$notcontains`` -- for json columns, the column must not contain any entry of the given value (which should be iterable)
            - ``$containedin`` -- for json columns, the column should be a subset of the given list
            - ``$exists`` -- if True, require not null; if False, require null.
            - ``$startswith`` -- for text columns, matches strings that start with the given string.
            - ``$like`` -- for text columns, matches strings according to the LIKE operand in SQL.
            - ``$regex`` -- for text columns, matches the given regex expression supported by PostgresSQL
        - ``value`` -- The value to compare to.  The meaning depends on the key.
        - ``col`` -- The name of the column, wrapped in SQL
        - ``force_json`` -- whether the column is a jsonb column

        OUTPUT:

        - A string giving the SQL test corresponding to the requested query, with %s
        - values to fill in for the %s entries (see ``_execute`` for more discussion).

        EXAMPLES::

            sage: from lmfdb import db
            sage: statement, vals = db.nf_fields._parse_special("$lte", 5, "degree")
            ('"degree" <= %s', [5])
            sage: statement, vals = db.nf_fields._parse_special("$or", [{"degree":{"$lte":5}},{"class_number":{"$gte":3}}], None)
            sage: statement.as_string(db.conn), vals
            ('("degree" <= %s OR "class_number" >= %s)', [5, 3])
            sage: statement, vals = db.nf_fields._parse_special("$or", [{"$lte":5}, {"$gte":10}], "degree")
            sage: statement.as_string(db.conn), vals
            ('("degree" <= %s OR "degree" >= %s)', [5, 10])
            sage: statement, vals = db.nf_fields._parse_special("$and", [{"$gte":5}, {"$lte":10}], "degree")
            sage: statement.as_string(db.conn), vals
            ('("degree" >= %s AND "degree" <= %s)', [5, 10])
            sage: statement, vals = db.nf_fields._parse_special("$contains", [2,3,5], "ramps")
            sage: statement.as_string(db.conn), vals
            ('"ramps" @> %s', [[2, 3, 5]])
        """
        if key in ['$or', '$and']:
            pairs = [self._parse_dict(clause, outer=col, outer_json=force_json) for clause in value]
            pairs = [pair for pair in pairs if pair[0] is not None]
            if pairs:
                strings, values = zip(*pairs)
                # flatten values
                values = [item for sublist in values for item in sublist]
                joiner = " OR " if key == '$or' else " AND "
                return SQL("({0})").format(SQL(joiner).join(strings)), values
            else:
                return None, None

        # First handle the cases that have unusual values
        if key == '$exists':
            if value:
                cmd = SQL("{0} IS NOT NULL").format(col)
            else:
                cmd = SQL("{0} IS NULL").format(col)
            value = []
        elif key == '$notcontains':
            if force_json:
                cmd = SQL(" AND ").join(SQL("NOT {0} @> %s").format(col) * len(value))
                value = [Json(v) for v in value]
            else:
                cmd = SQL(" AND ").join(SQL("NOT (%s = ANY({0}))").format(col) * len(value))
        elif key == '$mod':
            if not (isinstance(value, (list, tuple)) and len(value) == 2):
                raise ValueError("Error building modulus operation: %s" % value)
            # have to take modulus twice since MOD(-1,5) = -1 in postgres
            cmd = SQL("MOD(%s + MOD({0}, %s), %s) = %s").format(col)
            value = [value[1], value[1], value[1], value[0] % value[1]]

        else:
            if key == '$lte':
                cmd = SQL("{0} <= %s")
            elif key == '$lt':
                cmd = SQL("{0} < %s")
            elif key == '$gte':
                cmd = SQL("{0} >= %s")
            elif key == '$gt':
                cmd = SQL("{0} > %s")
            elif key == '$ne':
                cmd = SQL("{0} != %s")
            # FIXME, we should do recursion with _parse_special
            elif key == '$maxgte':
                cmd = SQL("array_max({0}) >= %s")
            elif key == '$anylte':
                cmd = SQL("%s >= ANY({0})")
            elif key == '$in':
                if force_json:
                    #jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("{0} <@ %s")
                else:
                    cmd = SQL("{0} = ANY(%s)")
            elif key == '$nin':
                if force_json:
                    #jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("NOT ({0} <@ %s)")
                else:
                    cmd = SQL("NOT ({0} = ANY(%s)")
            elif key == '$contains':
                cmd = SQL("{0} @> %s")
                if not force_json:
                    value = [value]
            elif key == '$containedin':
                #jsonb_path_ops modifiers for the GIN index doesn't support this query
                cmd = SQL("{0} <@ %s")
            elif key == '$startswith':
                cmd = SQL("{0} LIKE %s")
                value = value.replace('_',r'\_').replace('%',r'\%') + '%'
            elif key == '$like':
                cmd = SQL("{0} LIKE %s")
            elif key == '$regex':
                cmd = SQL("{0} ~ '%s'")
            else:
                raise ValueError("Error building query: {0}".format(key))
            if force_json:
                value = Json(value)
            cmd = cmd.format(col)
            value = [value]
        return cmd, value

    def _parse_values(self, D):
        """
        Returns the values of dictionary parse accordingly to be used as values in ``_execute``

        INPUT:
        - ``D`` -- a dictionary, or a scalar if outer is set

        OUTPUT:

        - A list of values to fill in for the %s in the string.  See ``_execute`` for more details

        EXAMPLES::

            sage: from lmfdb import db
            sage: sage: db.nf_fields._parse_dict({})
            []
            sage: db.lfunc_lfunctions._parse_values({'bad_lfactors':[1,2]})[1][0]
            '[1, 2]'
            sage: db.char_dir_values._parse_values({'values':[1,2]})
            [1, 2]
        """

        return [Json(val) if self.col_type[key] == 'jsonb' else val for key, val in D.iteritems()]

    def _parse_dict(self, D, outer=None, outer_json=None):
        """
        Parses a dictionary that specifies a query in something close to Mongo syntax into an SQL query.

        INPUT:

        - ``D`` -- a dictionary, or a scalar if outer is set
        - ``outer`` -- the column that we are parsing (None if not yet parsing any column).  Used in recursion.  Should be wrapped in SQL.
        - ``outer_json`` -- whether the outer column is a jsonb column

        OUTPUT:

        - An SQL Composable giving the WHERE component of an SQL query (possibly containing %s), or None if D imposes no constraint
        - A list of values to fill in for the %s in the string.  See ``_execute`` for more details.

        EXAMPLES::

            sage: from lmfdb import db
            sage: statement, vals = db.nf_fields._parse_dict({"degree":2, "class_number":6})
            sage: statement.as_string(db.conn), vals
            ('"class_number" = %s AND "degree" = %s', [6, 2])
            sage: statement, vals = db.nf_fields._parse_dict({"degree":{"$gte":4,"$lte":8}, "r2":1})
            sage: statement.as_string(db.conn), vals
            ('"r2" = %s AND "degree" <= %s AND "degree" >= %s', [1, 8, 4])
            sage: statement, vals = db.nf_fields._parse_dict({"degree":2, "$or":[{"class_number":1,"r2":0},{"disc_sign":1,"disc_abs":{"$lte":10000},"class_number":{"$lte":8}}]})
            sage: statement.as_string(db.conn), vals
            ('("class_number" = %s AND "r2" = %s OR "disc_sign" = %s AND "class_number" <= %s AND "disc_abs" <= %s) AND "degree" = %s', [1, 0, 1, 8, 10000, 2])
            sage: db.nf_fields._parse_dict({})
            (None, None)
        """
        if outer is not None and not isinstance(D, dict):
            if outer_json:
                D = Json(D)
            return SQL("{0} = %s").format(outer), [D]
        if len(D) == 0:
            return None, None
        else:
            strings = []
            values = []
            for key, value in D.iteritems():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == '$':
                    sub, vals = self._parse_special(key, value, outer, force_json=outer_json)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                    continue
                if '.' in key:
                    path = [int(p) if p.isdigit() else p for p in key.split('.')]
                    key = path[0]
                    if self.col_type.get(key) == 'jsonb':
                        path = [SQL("->{0}").format(Literal(p)) for p in path[1:]]
                    else:
                        path = [SQL("[{0}]").format(Literal(p)) for p in path[1:]]
                else:
                    path = None
                if key != 'id' and key not in self._search_cols:
                    raise ValueError("%s is not a column of %s"%(key, self.search_table))
                # Have to determine whether key is jsonb before wrapping it in Identifier
                coltype = self.col_type[key]
                force_json = (coltype == 'jsonb')
                if path:
                    key = SQL("{0}{1}").format(Identifier(key), SQL("").join(path))
                else:
                    key = Identifier(key)
                if isinstance(value, dict) and all(k.startswith('$') for k in value.iterkeys()):
                    sub, vals = self._parse_dict(value, key, outer_json=force_json)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                    continue
                if value is None:
                    strings.append(SQL("{0} IS NULL").format(key))
                else:
                    if force_json:
                        value = Json(value)
                    cmd = "{0} = %s"
                    # For arrays, have to add an explicit typecast
                    if coltype.endswith('[]'):
                        if not path:
                            cmd += '::' + coltype
                        else:
                            cmd += '::' + coltype[:-2]

                    strings.append(SQL(cmd).format(key))
                    values.append(value)
            if strings:
                return SQL(" AND ").join(strings), values
            else:
                return None, None

    def _build_query(self, query, limit=None, offset=0, sort=None):
        """
        Build an SQL query from a dictionary, including limit, offset and sorting.

        INPUT:

        - ``query`` -- a dictionary query, in the mongo style (but only supporting certain special operators, as in ``_parse_special``)
        - ``limit`` -- a limit on the number of records returned
        - ``offset`` -- an offset on how many records to skip
        - ``sort`` -- a sort order (to be passed into the ``_sort_str`` method, or None.

        OUTPUT:

        - an SQL Composable giving the WHERE, ORDER BY, LIMIT and OFFSET components of an SQL query, possibly including %s
        - a list of values to substitute for the %s entries

        EXAMPLES::

            sage: from lmfdb import db
            sage: statement, vals = db.nf_fields._build_query({"degree":2, "class_number":6})
            sage: statement.as_string(db.conn), vals
            (' WHERE "class_number" = %s AND "degree" = %s ORDER BY "degree", "disc_abs", "disc_sign", "label"', [6, 2])
            sage: statement, vals = db.nf_fields._build_query({"class_number":1}, 20)
            sage: statement.as_string(db.conn), vals
            (' WHERE "class_number" = %s ORDER BY "id" LIMIT %s', [1, 20])
        """
        qstr, values = self._parse_dict(query)
        if qstr is None:
            s = SQL("")
            values = []
        else:
            s = SQL(" WHERE {0}").format(qstr)
        if sort is None:
            has_sort = True
            if self._sort is None:
                if limit is not None and not (limit == 1 and offset == 0):
                    sort = Identifier("id")
                else:
                    has_sort = False
            elif self._primary_sort in query or self._out_of_order:
                # We use the actual sort because the postgres query planner doesn't know that
                # the primary key is connected to the id.
                sort = self._sort
            else:
                sort = Identifier("id")
        else:
            has_sort = bool(sort)
            sort = self._sort_str(sort)
        if has_sort:
            s = SQL("{0} ORDER BY {1}").format(s, sort)
        if limit is not None:
            s = SQL("{0} LIMIT %s").format(s)
            values.append(limit)
            if offset != 0:
                s = SQL("{0} OFFSET %s").format(s)
                values.append(offset)
        return s, values

    def _search_iterator(self, cur, search_cols, extra_cols, projection):
        """
        Returns an iterator over the results in a cursor,
        filling in columns from the extras table if needed.

        INPUT:

        - ``cur`` -- a psycopg2 cursor
        - ``search_cols`` -- the columns in the search table in the results
        - ``extra_cols`` -- the columns in the extras table in the results
        - ``projection`` -- the projection requested.

        OUTPUT:

        If projection is 0 or a string, an iterator that yields the labels/column values of the query results.
        Otherwise, an iterator that yields dictionaries with keys
        from ``search_cols`` and ``extra_cols``.
        """
        # Eventually want to batch the queries on the extra_table so that we
        # make fewer SQL queries here.
        try:
            for rec in cur:
                if projection == 0 or isinstance(projection, basestring):
                    yield rec[0]
                else:
                    yield {k: v for k, v in zip(search_cols + extra_cols, rec)
                           if v is not None}
        finally:
            if isinstance(cur, pg_cursor):
                cur.close()

    ##################################################################
    # Methods for querying                                           #
    ##################################################################

    def _get_table_clause(self, extra_cols):
        """
        Return a clause for use in the FROM section of a SELECT query.

        INPUT:

        - ``extra_cols`` -- a list of extra columns (only evaluated as a boolean)
        """
        if extra_cols:
            return SQL("{0} JOIN {1} USING (id)").format(Identifier(self.search_table),
                                                        Identifier(self.extra_table))
        else:
            return Identifier(self.search_table)

    def lucky(self, query={}, projection=2, offset=0, sort=[]):
        #FIXME Nulls aka Nones are being erased, we should perhaps just leave them there
        """
        One of the two main public interfaces for performing SELECT queries,
        intended for situations where only a single result is desired.

        INPUT:

        - ``query`` -- a mongo-style dictionary specifying the query.
           Generally, the keys will correspond to columns,
           and values will either be specific numbers (specifying an equality test)
           or dictionaries giving more complicated constraints.
           The main exception is that "$or" can be a top level key,
           specifying a list of constraints of which at least one must be true.
        - ``projection`` -- which columns are desired.
          This can be specified either as a list of columns to include;
           a dictionary specifying columns to include (using all True values)
                                           or exclude (using all False values);
           a string giving a single column (only returns the value, not a dictionary);
           or an integer code (0 means only return the label,
                               1 means return all search columns,
                               2 means all columns (default)).
        - ``offset`` -- integer. allows retrieval of a later record rather than just first.
        - ``sort`` -- The sort order, from which the first result is returned.
            - None, Using the default sort order for the table
                the query then the choice of the result is arbitrary.
            - a list of strings (which are interpreted as column names in the
                ascending direction) or of pairs (column name, 1 or -1).
                If not specified, will use the default sort order on the table.
            - [] (default), unsorted, thus if there is more than one match to

        OUTPUT:

        If projection is 0 or a string, returns the label/column value of the first record satisfying the query.
        Otherwise, return a dictionary with keys the column names requested by the projection.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.lucky({'degree':int(2),'disc_sign':int(1),'disc_abs':int(5)},projection=0)
            u'2.2.5.1'
            sage: nf.lucky({'label':u'6.6.409587233.1'},projection=1)
            {u'class_group': [],
             u'class_number': 1,
             u'cm': False,
             u'coeffs': [2, -31, 30, 11, -13, -1, 1],
             u'degree': 6,
             u'disc_abs': 409587233,
             u'disc_rad': 409587233,
             u'disc_sign': 1,
             u'galt': 16,
             u'label': u'6.6.409587233.1',
             u'oldpolredabscoeffs': None,
             u'r2': 0,
             u'ramps': [11, 53, 702551],
             u'used_grh': False}
            sage: nf.lucky({'label':u'6.6.409587233.1'},projection=['regulator'])
            {'regulator':455.191694993}
        """
        search_cols, extra_cols = self._parse_projection(projection)
        vars = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        qstr, values = self._build_query(query, 1, offset, sort=sort)
        tbl = self._get_table_clause(extra_cols)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(vars, tbl, qstr)
        cur = self._execute(selecter, values)
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if projection == 0 or isinstance(projection, basestring):
                return rec[0]
            else:
                return {k:v for k,v in zip(search_cols + extra_cols, rec) if v is not None}

    def search(self, query={}, projection=1, limit=None, offset=0, sort=None, info=None, silent=False):
        """
        One of the two main public interfaces for performing SELECT queries,
        intended for usage from search pages where multiple results may be returned.

        INPUT:

        - ``query`` -- a mongo-style dictionary specifying the query.
           Generally, the keys will correspond to columns,
           and values will either be specific numbers (specifying an equality test)
           or dictionaries giving more complicated constraints.
           The main exception is that "$or" can be a top level key,
           specifying a list of constraints of which at least one must be true.
        - ``projection`` -- which columns are desired.
          This can be specified either as a list of columns to include;
           a dictionary specifying columns to include (using all True values)
                                           or exclude (using all False values);
           a string giving a single column (only returns the value, not a dictionary);
           or an integer code (0 means only return the label,
                               1 means return all search columns (default),
                               2 means all columns).
        - ``limit`` -- an integer or None (default), giving the maximum number of records to return.
        - ``offset`` -- an integer (default 0), where to start in the list of results.
        - ``sort`` -- a sort order.  Either None or a list of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).  If not specified, will use the default sort order on the table.  If you want the result unsorted, use [].
        - ``info`` -- a dictionary, which is updated with values of 'query', 'count', 'start', 'exact_count' and 'number'.  Optional.
        - ``silent`` -- a boolean.  If True, slow query warnings will be suppressed.

        WARNING:

        For tables that are split into a search table and an extras table,
        requesting columns in the extras table via this function will
        require a separate database query for EACH ROW of the result.
        This function is intended for use only on the columns in the search table.

        OUTPUT:

        If ``limit`` is None, returns an iterator over the results, yielding dictionaries with keys the columns requested by the projection (or labels/column values if the projection is 0 or a string)

        Otherwise, returns a list with the same data.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: info = {}
            sage: nf.search({'degree':int(2),'class_number':int(1),'disc_sign':int(-1)}, projection=0, limit=4, info=info)
            [u'2.0.3.1', u'2.0.4.1', u'2.0.7.1', u'2.0.8.1']
            sage: info['number'], info['exact_count']
            (9, True)
            sage: info = {}
            sage: nf.search({'degree':int(6)}, projection=['label','class_number','galt'], limit=4, info=info)
            [{'class_number': 1, 'galt': 5, 'label': u'6.0.9747.1'},
             {'class_number': 1, 'galt': 11, 'label': u'6.0.10051.1'},
             {'class_number': 1, 'galt': 11, 'label': u'6.0.10571.1'},
             {'class_number': 1, 'galt': 5, 'label': u'6.0.10816.1'}]
            sage: info['number'], info['exact_count']
            (5522600, True)
            sage: info = {}
            sage: nf.search({'ramps':{'$contains':[int(2),int(7)]}}, limit=4, info=info)
            [{'label': u'2.2.28.1', 'ramps': [2, 7]},
             {'label': u'2.0.56.1', 'ramps': [2, 7]},
             {'label': u'2.2.56.1', 'ramps': [2, 7]},
             {'label': u'2.0.84.1', 'ramps': [2, 3, 7]}]
            sage: info['number'], info['exact_count']
            (1000, False)
        """
        search_cols, extra_cols = self._parse_projection(projection)
        vars = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        if limit is None:
            qstr, values = self._build_query(query, sort=sort)
        else:
            nres = self.stats.quick_count(query)
            if nres is None:
                prelimit = max(limit, self._count_cutoff - offset)
                qstr, values = self._build_query(query, prelimit, offset, sort)
            else:
                qstr, values = self._build_query(query, limit, offset, sort)
        tbl = self._get_table_clause(extra_cols)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(vars, tbl, qstr)
        cur = self._execute(selecter, values, silent=silent,
                            buffered=(limit is None),
                            slow_note=(
                                self.search_table, "analyze", query,
                                repr(projection), limit, offset))
        if limit is None:
            if info is not None:
                # caller is requesting count data
                info['number'] = self.count(query)
            return self._search_iterator(cur, search_cols,
                                         extra_cols, projection)
        if nres is None:
            exact_count = (cur.rowcount < prelimit)
            nres = offset + cur.rowcount
        else:
            exact_count = True
        res = cur.fetchmany(limit)
        res = list(
                self._search_iterator(res, search_cols, extra_cols, projection)
                )
        if info is not None:
            if offset >= nres:
                offset -= (1 + (offset - nres) / limit) * limit
            if offset < 0:
                offset = 0
            info['query'] = dict(query)
            info['number'] = nres
            info['count'] = limit
            info['start'] = offset
            info['exact_count'] = exact_count
        return res

    def lookup(self, label, projection=2, label_col=None):
        """
        Look up a record by its label.

        INPUT:

        - ``label`` -- string, the label for the desired record.
        - ``projection`` -- which columns are requested (default 2, meaning all columns).
                            See ``_parse_projection`` for more details.
        - ``label_col`` -- which column holds the label.  Most tables store a default.

        OUTPUT:

        A dictionary with keys the column names requested by the projection.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: rec = nf.lookup('8.0.374187008.1')
            sage: rec['loc_algebras']['13']
            u'x^2-13,x^2-x+2,x^4+x^2-x+2'
        """
        if label_col is None:
            label_col = self._label_col
            if label_col is None:
                raise ValueError("Lookup method not supported for tables with no label column")
        return self.lucky({label_col:label}, projection=projection, sort=[])

    def exists(self, query):
        """
        Determines whether there exists at least one record satisfying the query.

        INPUT:

        - ``query`` -- a mongo style dictionary specifying the search.
          See ``search`` for more details.

        OUTPUT:

        Boolean, whether there exists a record.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.exists({'class_number':int(7)})
            True
        """
        return self.lucky(query, projection='id') is not None

    def label_exists(self, label, label_col=None):
        if label_col is None:
            label_col = self._label_col
            if label_col is None:
                raise ValueError("Lookup method not supported for tables with no label column")
        return self.exists({label_col:label})


    def random(self, query={}, projection=0):
        """
        Return a random label or record from this table.

        INPUT:

        - ``query`` -- a query dictionary from which a result
          will be selected, uniformly at random
        - ``projection`` -- which columns are requested
          (default 0, meaning just the label).
          See ``_parse_projection`` for more details.

        OUTPUT:

        If projection is 0, a random label from the table.
        Otherwise, a dictionary with keys specified by the projection.
        A RuntimeError is raised if the selection fails when there are
        rows in the table; this can occur if the ids are not consecutive
        due to deletions.
        If there are no results satisfying the query, None is returned
        (analogously to the ``lucky`` method).

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.random()
            u'2.0.294787.1'
        """
        if query:
            # See if we know how many results there are
            cnt = self.stats.quick_count(query)
            if cnt is None:
                # We need the list of results
                # (in order to get a uniform sample),
                # and get the count as a side effect
                if projection == 0:
                    # Labels won't be too large,
                    # so we just get an unsorted list of labels
                    L = list(self.search(query, 0, sort=[]))
                else:
                    # An arbitary projection might be large, so we get ids
                    L = list(self.search(query, 'id', sort=[]))
                self.stats._record_count(query, len(L))
                if len(L) == 0:
                    return None
                res = random.choice(L)
                if projection != 0:
                    res = self.lucky({'id':res}, projection=projection)
                return res
            elif cnt == 0:
                return None
            else:
                offset = random.randrange(cnt)
                return self.lucky(query, projection=projection, offset=offset, sort=[])
        else:
            maxtries = 100
            # a temporary hack FIXME
            #maxid = self.max('id')
            maxid = self.max_id()
            if maxid == 0:
                return None
            # a temporary hack FIXME
            minid = self.min_id()
            for _ in range(maxtries):
                # The id may not exist if rows have been deleted
                # a temporary hack FIXME
                #rid = random.randint(1, maxid)
                rid = random.randint(minid, maxid)
                res = self.lucky({'id':rid}, projection=projection)
                if res: return res
            raise RuntimeError("Random selection failed!")
        ### This code was used when not every table had an id.
        ## Get the number of pages occupied by the search_table
        #cur = self._execute(SQL("SELECT relpages FROM pg_class WHERE relname = %s"), [self.search_table])
        #num_pages = cur.fetchone()[0]
        ## extra_cols will be () since there is no id
        #search_cols, extra_cols = self._parse_projection(projection)
        #vars = SQL(", ").join(map(Identifier, search_cols + extra_cols))
        #selecter = SQL("SELECT {0} FROM {1} TABLESAMPLE SYSTEM(%s)").format(vars, Identifier(self.search_table))
        ## We select 3 pages in an attempt to not accidentally get nothing.
        #percentage = min(float(300) / num_pages, 100)
        #for _ in range(maxtries):
        #    cur = self._execute(selecter, [percentage])
        #    if cur.rowcount > 0:
        #        return {k:v for k,v in zip(search_cols, random.choice(list(cur)))}

    def random_sample(self, ratio, query={}, projection=1, mode=None, repeatable=None):
        """
        Returns a random sample of rows from this table.  Note that ratio is not guaranteed, and different modes will have different levels of randomness.

        INPUT:

        - ``ratio`` -- a float between 0 and 1, the approximate fraction of rows satisfying the query to be returned.
        - ``query`` -- a dictionary query, as for searching.  Note that the WHERE clause is applied after the random selection except when using 'choice' mode
        - ``projection`` -- a description of which columns to include in the search results
        - ``mode`` -- one of ``'system'``, ``'bernoulli'``, ``'choice'`` and ``None``:
          - ``system`` -- the fastest option, but will introduce clustering since random pages are selected rather than random rows.
          - ``bernoulli`` -- rows are selected independently with probability the given ratio, then the where clause is applied
          - ``choice`` -- all results satisfying the query are fetched, then a random subset is chosen.  This will be slow if a large number of rows satisfy the query, but performs much better when only a few rows satisfy the query.  This option matches ratio mostly accurately.
          - ``None`` -- Uses ``bernoulli`` if more than ``self._count_cutoff`` results satisfy the query, otherwise uses ``choice``.
        - ``repeatable`` -- an integer, giving a random seed for a repeatable result.
        """
        if mode is None:
            if self.count(query) > self._count_cutoff:
                mode = 'bernoulli'
            else:
                mode = 'choice'
        mode = mode.upper()
        search_cols, extra_cols = self._parse_projection(projection)
        if ratio > 1 or ratio <= 0:
            raise ValueError("Ratio must be a positive number between 0 and 1")
        if ratio == 1:
            return self.search(query, projection, sort=[])
        elif mode == 'CHOICE':
            results = list(self.search(query, projection, sort=[]))
            count = int(len(results) * ratio)
            if repeatable is not None:
                random.seed(repeatable)
            return self._search_iterator(random.sample(results, count), search_cols, extra_cols, projection)
        elif mode in ['SYSTEM', 'BERNOULLI']:
            if extra_cols:
                raise ValueError("You cannot use the system or bernoulli modes with extra columns")
            vars = SQL(", ").join(map(Identifier, search_cols))
            if repeatable is None:
                repeatable = SQL("")
                values = [100*ratio]
            else:
                repeatable = SQL(" REPEATABLE %s")
                values = [100*ratio, int(repeatable)]
            qstr, qvalues = self._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
            else:
                qstr = SQL(" WHERE {0}").format(qstr)
                values.extend(qvalues)
            selecter = SQL("SELECT {0} FROM {1} TABLESAMPLE " + mode + "(%s){2}{3}").format(vars, Identifier(self.search_table), repeatable, qstr)
            cur = self._execute(selecter, values, buffered=True)
            return self._search_iterator(cur, search_cols, extra_cols, projection)

    ##################################################################
    # Convenience methods for accessing statistics                   #
    ##################################################################

    def max(self, col, constraint={}):
        """
        The maximum value attained by the given column.

        EXAMPLES::

            sage: from lmfdb import db
            sage: db.nf_fields.max('class_number')
            1892503075117056
        """
        return self.stats.max(col, constraint)

    def distinct(self, col, query={}):
        """
        Returns a list of the distinct values taken on by a given column.
        """
        selecter = SQL("SELECT DISTINCT {0} FROM {1}").format(Identifier(col), Identifier(self.search_table))
        qstr, values = self._parse_dict(query)
        if qstr is not None:
            selecter = SQL("{0} WHERE {1}").format(selecter, qstr)
        selecter = SQL("{0} ORDER BY {1}").format(selecter, Identifier(col))
        cur = self._execute(selecter, values)
        return [res[0] for res in cur]

    def count(self, query={}, record=True):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``record`` -- (default True) whether to record the number of results in the counts table.

        OUTPUT:

        The number of records satisfying the query.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.count({'degree':int(6),'galt':int(7)})
            244006
        """
        return self.stats.count(query, record=record)

    ##################################################################
    # Indexes and performance analysis                               #
    ##################################################################

    def analyze(self, query, projection=1, limit=1000, offset=0, sort=None, explain_only=False):
        """
        EXAMPLES::

        sage: from lmfdb import db
        sage: nf = db.nf_fields
        sage: nf.analyze({'degree':int(5)},limit=20)
        SELECT label, coeffs, degree, r2, cm, disc_abs, disc_sign, disc_rad, ramps, galt, class_number, class_group, used_grh, oldpolredabscoeffs FROM nf_fields WHERE degree = 5 ORDER BY degree, disc_abs, disc_sign, label LIMIT 20
        Limit  (cost=671790.56..671790.61 rows=20 width=305) (actual time=1947.351..1947.358 rows=20 loops=1)
          ->  Sort  (cost=671790.56..674923.64 rows=1253232 width=305) (actual time=1947.348..1947.352 rows=20 loops=1)
                Sort Key: disc_abs, disc_sign, label COLLATE "C"
                Sort Method: top-N heapsort  Memory: 30kB
                ->  Bitmap Heap Scan on nf_fields  (cost=28589.11..638442.51 rows=1253232 width=305) (actual time=191.837..1115.096 rows=1262334 loops=1)
                      Recheck Cond: (degree = 5)
                      Heap Blocks: exact=35140
                      ->  Bitmap Index Scan on nfs_ddd  (cost=0.00..28275.80 rows=1253232 width=0) (actual time=181.789..181.789 rows=1262334 loops=1)
                            Index Cond: (degree = 5)
        Planning time: 2.880 ms
        Execution time: 1947.655 ms
        """
        search_cols, extra_cols = self._parse_projection(projection)
        vars = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        if limit is None:
            qstr, values = self._build_query(query, sort=sort)
        else:
            qstr, values = self._build_query(query, limit, offset, sort)
        tbl = self._get_table_clause(extra_cols)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(vars, tbl, qstr)
        if explain_only:
            analyzer = SQL("EXPLAIN {0}").format(selecter)
        else:
            analyzer = SQL("EXPLAIN ANALYZE {0}").format(selecter)
        cur = self._db.cursor()
        print cur.mogrify(selecter, values)
        cur = self._execute(analyzer, values, silent=True)
        for line in cur:
             print line[0]

    def _list_built_indexes(self):
        """
        Lists built indexes names on the search table
        """
        return self._list_indexes(self.search_table)

    def list_indexes(self, verbose=False):
        """
        Lists the indexes on the search table present in meta_indexes
        Note:
         - not necessarily all built
         - not necessarily a supset of all the built indexes.

        For the current built indexes on the search table, see _list_built_indexes
        """
        selecter = SQL("SELECT index_name, type, columns, modifiers FROM meta_indexes WHERE table_name = %s")
        cur = self._execute(selecter, [self.search_table], silent=True)
        output = {}
        for name, typ, columns, modifiers in cur:
            output[name] = {"type": typ, "columns": columns, "modifiers": modifiers}
            if verbose:
                colspec = [" ".join([col] + mods) for col, mods in zip(columns, modifiers)]
                print "{0} ({1}): {2}".format(name, typ, ", ".join(colspec))
        if not verbose:
            return output

    @staticmethod
    def _create_index_statement(name, table, type, columns, modifiers, storage_params):
        """
        Utility function for making the create index SQL statement.
        """
        # We whitelisted the type, modifiers and storage parameters
        # when creating the index so the following is safe from SQL injection
        if storage_params:
            # The inner format is on a string rather than a psycopg2.sql.Composable:
            # the keys of storage_params have been whitelisted.
            storage_params = SQL(" WITH ({0})").format(SQL(", ").join(SQL("{0} = %s".format(param)) for param in storage_params))
        else:
            storage_params = SQL("")
        modifiers = [" " + " ".join(mods) if mods else "" for mods in modifiers]
        # The inner % operator is on strings prior to being wrapped by SQL: modifiers have been whitelisted.
        columns = SQL(", ").join(SQL("{0}%s"%mods).format(Identifier(col)) for col, mods in zip(columns, modifiers))
        # The inner % operator is on strings prior to being wrapped by SQL: type has been whitelisted.
        creator = SQL("CREATE INDEX {0} ON {1} USING %s ({2}){3}"%(type))
        return creator.format(Identifier(name), Identifier(table), columns, storage_params)

    def _create_counts_indexes(self, suffix="", warning_only=False):
        tablename = self.search_table + "_counts"
        storage_params = {}
        with DelayCommit(self, silence=True):
            for index in _counts_indexes:
                now = time.time()
                name = index["name"].format(tablename) + suffix
                if self._relation_exists(name):
                    message = "Relation with name {} already exists".format(name)
                    if warning_only:
                        print(message)
                        continue
                    else:
                        raise ValueError(message)
                creator = self._create_index_statement(name,
                                                       tablename + suffix,
                                                       index["type"],
                                                       index["columns"],
                                                       [[]] * len(index["columns"]),
                                                       storage_params)
                self._execute(creator, storage_params.values())
                print "Index {} created in {:.3f} secs".format(index["name"].format(self.search_table), time.time() - now)



    def _check_index_name(self, name, kind="Index"):
        """
        Given:
            -- `name` of an index/constraint, and
            -- `kind` in ["Index", "Constraint"]
        checks that `name` doesn't end with:
            - _tmp
            _ _pkey
            _ _oldN
            - _depN
        and that doesn't clash with another relation.

        """


        self._check_restricted_suffix(name, kind)


        if self._relation_exists(name): # this also works for constraints
            raise ValueError("{} name {} is invalid, ".format(kind, name) +
                             "a relation with that name already exists, " +
                             "e.g, index, constraint or table; " +
                             "try specifying a different name")

        if kind == "Index":
            meta = "meta_indexes"
            meta_name = "index_name"
        elif kind == "Constraint":
            meta = "meta_constraints"
            meta_name = "constraint_name"
        else:
            raise ValueError("""kind={} is not "Index" or "Constraint" """)

        selecter = SQL("SELECT 1 FROM {} WHERE {} = %s AND table_name = %s")
        cur = self._execute(selecter.format(*map(Identifier, [meta, meta_name])),
                            [name, self.search_table])
        if cur.rowcount > 0:
            raise ValueError("{} name {} is invalid, ".format(kind, name) +
                             "an {} with that name".format(kind.lower()) +
                             "already exists in {}; ".format(meta) +
                             "try specifying a different name")


    def create_index(self, columns, type="btree", modifiers=None, name=None, storage_params=None):
        """
        Create an index.

        This function will also add the indexing data to the meta_indexes table
        so that indexes can be dropped and recreated when uploading data.

        INPUT:

        - ``columns`` -- a list of column names
        - ``type`` -- one of the postgres index types: btree, gin, gist, brin, hash, spgist.
        - ``modifiers`` -- a list of lists of strings.  The overall length should be
            the same as the length of ``columns``, and each internal list can only contain the
            following whitelisted column modifiers:
            - a non-default operator class
            - ``ASC``
            - ``DESC``
            - ``NULLS FIRST``
            - ``NULLS LAST``
            This interface doesn't currently support creating indexes with nonstandard collations.
        """
        now = time.time()
        if type not in _operator_classes:
            raise ValueError("Unrecognized index type")
        if modifiers is None:
            if type == "gin":
                def mod(col):
                    if self.col_type[col] == 'jsonb':
                        return ["jsonb_path_ops"]
                    elif self.col_type[col].endswith('[]'):
                        return ["array_ops"]
                    else:
                        return []
                modifiers = [mod(col) for col in columns]
            else:
                modifiers = [[]] * len(columns)
        else:
            if len(modifiers) != len(columns):
                raise ValueError("modifiers must have same length as columns")
            for mods in modifiers:
                for mod in mods:
                    if mod.lower() not in ["asc", "desc", "nulls first", "nulls last"] + _operator_classes[type]:
                        raise ValueError("Invalid modifier %s"%(mod,))
        if storage_params is None:
            if type in ["btree", "hash", "gist", "spgist"]:
                storage_params = {"fillfactor": 100}
            else:
                storage_params = {}
        else:
            for key in storage_params:
                if key not in _valid_storage_params[type]:
                    raise ValueError("Invalid storage parameter %s"%key)
        for col in columns:
            if col != "id" and col not in self._search_cols:
                raise ValueError("%s not a column"%(col))
        if name is None:
            # Postgres has a maximum name length of 64 bytes
            # It will truncate if longer, but that causes suffixes of _tmp to be indistinguishable.
            if len(columns) <= 2:
                name = "_".join([self.search_table] + columns + ([] if type == "btree" else [type]))
            elif len(columns) <= 8:
                name = "_".join([self.search_table] + [col[:2] for col in columns])
            else:
                name = "_".join([self.search_table] + ["".join(col[0] for col in columns)])



        with DelayCommit(self, silence=True):
            self._check_index_name(name, "Index")
            creator = self._create_index_statement(name, self.search_table, type, columns, modifiers, storage_params)
            self._execute(creator, storage_params.values())
            inserter = SQL("INSERT INTO meta_indexes (index_name, table_name, type, columns, modifiers, storage_params) VALUES (%s, %s, %s, %s, %s, %s)")
            self._execute(inserter, [name, self.search_table, type, Json(columns), Json(modifiers), storage_params])
        print "Index %s created in %.3f secs"%(name, time.time() - now)

    def drop_index(self, name, suffix="", permanent=False, commit=True):
        """
        Drop a specified index.

        INPUT:

        - ``name`` -- the name of the index
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the DROP INDEX statement.
        - ``permanent`` -- whether to remove the index from the meta_indexes table
        """
        now = time.time()
        with DelayCommit(self, commit, silence=True):
            if permanent:
                deleter = SQL("DELETE FROM meta_indexes WHERE table_name = %s AND index_name = %s")
                self._execute(deleter, [self.search_table, name])
            dropper = SQL("DROP INDEX {0}").format(Identifier(name + suffix))
            self._execute(dropper)
        print "Dropped index %s in %.3f secs"%(name, time.time() - now)




    def restore_index(self, name, suffix=""):
        """
        Restore a specified index using the meta_indexes table.

        INPUT:

        - ``name`` -- the name of the index
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the CREATE INDEX statement.
        """
        now = time.time()
        with DelayCommit(self, silence=True):
            selecter = SQL("SELECT type, columns, modifiers, storage_params FROM meta_indexes WHERE table_name = %s AND index_name = %s")
            cur = self._execute(selecter, [self.search_table, name])
            if cur.rowcount > 1:
                raise RuntimeError("Duplicated rows in meta_indexes")
            elif cur.rowcount == 0:
                raise ValueError("Index %s does not exist in meta_indexes"%(name,))
            type, columns, modifiers, storage_params = cur.fetchone()
            creator = self._create_index_statement(name + suffix, self.search_table + suffix, type, columns, modifiers, storage_params)
            # this avoids clashes with deprecated indexes/constraints
            self._rename_if_exists(name, suffix)
            self._execute(creator, storage_params.values())
        print "Created index %s in %.3f secs"%(name, time.time() - now)

    def _indexes_touching(self, columns):
        """
        Utility function for determining which indexes reference any of the given columns.
        """
        selecter = SQL("SELECT index_name FROM meta_indexes WHERE table_name = %s")
        if columns:
            selecter = SQL("{0} AND ({1})").format(selecter, SQL(" OR ").join(SQL("columns @> %s") * len(columns)))
            columns = [Json(col) for col in columns]
        return self._execute(selecter, [self.search_table] + columns, silent=True)

    def drop_indexes(self, columns=[], suffix="", commit=True):
        """
        Drop all indexes and constraints.

        If ``columns`` provided, will instead only drop indexes and constraints
        that refer to any of those columns.

        INPUT:

        - ``columns`` -- a list of column names.  If any are included,
            then only indexes referencing those columns will be included.
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended
            to the names in the drop statements.
        """
        with DelayCommit(self, commit):
            for res in self._indexes_touching(columns):
                self.drop_index(res[0], suffix)
            for res in self._constraints_touching(columns):
                self.drop_index(res[0], suffix)

    def restore_indexes(self, columns=[], suffix=""):
        """
        Restore all indexes and constraints using the meta_indexes
        and meta_constraints tables.

        If ``columns`` provided, will instead only restore indexes and constraints
        that refer to any of those columns.

        INPUT:

        - ``columns`` -- a list of column names.  If any are included,
            then only indexes/constraints referencing those columns will be included.
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended
            to the names in the creation statements.
        """
        with DelayCommit(self):
            for res in self._indexes_touching(columns):
                self.restore_index(res[0], suffix)
            for res in self._constraints_touching(columns):
                self.restore_constraint(res[0], suffix)

    def _pkey_common(self, command, suffix, action, commit):
        """
        Common code for ``drop_pkeys`` and ``restore_pkeys``.

        INPUT:

        - ``command`` -- an sql.Composable object giving the command to execute.
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the command.
        - ``action`` -- either "Dropped" or "Built", for printing.
        """
        now = time.time()
        with DelayCommit(self, commit, silence=True):
            # Note that the primary keys don't follow the same convention as the other
            # indexes, since they end in _pkey rather than the suffix.
            self._execute(command.format(Identifier(self.search_table + suffix),
                                         Identifier(self.search_table + suffix + "_pkey")))
            if self.extra_table is not None:
                self._execute(command.format(Identifier(self.extra_table + suffix),
                                             Identifier(self.extra_table + suffix + "_pkey")))
        print "%s primary key on %s in %.3f secs"%(action, self.search_table, time.time()-now)

    def drop_pkeys(self, suffix="", commit=True):
        """
        Drop the primary key on the id columns.

        INPUT:

        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the ALTER TABLE statements.
        """
        command = SQL("ALTER TABLE {0} DROP CONSTRAINT {1}")
        self._pkey_common(command, suffix, "Dropped", commit)

    def restore_pkeys(self, suffix=""):
        """
        Restore the primary key on the id columns.

        INPUT:

        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the ALTER TABLE statements.
        """
        command = SQL("ALTER TABLE {0} ADD CONSTRAINT {1} PRIMARY KEY (id)")
        self._pkey_common(command, suffix, "Built", True)

    def _list_built_constraints(self):
        """
        Lists constraints names on the search table
        """
        return self._db._list_constraints(self.search_table)

    def list_constraints(self, verbose=False):
        """
        Lists the constraints on the search table present in meta_constraints
        Note:
         - not necessarily all built
         - not necessarily a supset of all the built constraints.
        For the current built constraints on the search table, see _list_built_constraints
        """
        selecter = SQL("SELECT constraint_name, type, columns, check_func FROM meta_constraints WHERE table_name = %s")
        cur = self._execute(selecter, [self.search_table], silent=True)
        output = {}
        for name, typ, columns, check_func in cur:
            output[name] = {"type": typ, "columns": columns, "check_func": check_func}
            if verbose:
                show = name if check_func is None else "{0} {1}".format(name, check_func)
                print "{0} ({1}): {2}".format(show, typ, ", ".join(columns))
        if not verbose:
            return output

    @staticmethod
    def _create_constraint_statement(name, table, type, columns, check_func):
        """
        Utility function for making the create constraint SQL statement.
        """
        # We whitelisted the type and check function so the following is safe
        cols = SQL(", ").join(Identifier(col) for col in columns)
        # from SQL injection
        if type == "NON NULL":
            return SQL("ALTER TABLE {0} ALTER COLUMN {1} SET NOT NULL").format(Identifier(table), cols)
        elif type == "UNIQUE":
            return SQL("ALTER TABLE {0} ADD CONSTRAINT {1} UNIQUE ({2}) WITH (fillfactor=100)").format(Identifier(table), Identifier(name), cols)
        elif type == "CHECK":
            return SQL("ALTER TABLE {0} ADD CONSTRAINT {1} CHECK (%s({2}))"%check_func).format(Identifier(table), Identifier(name), cols)

    @staticmethod
    def _drop_constraint_statement(name, table, type, columns):
        """
        Utility function for making the drop constraint SQL statement.
        """
        if type == "NON NULL":
            return SQL("ALTER TABLE {0} ALTER COLUMN {1} DROP NOT NULL").format(Identifier(table), Identifier(columns[0]))
        else:
            return SQL("ALTER TABLE {0} DROP CONSTRAINT {1}").format(Identifier(table), Identifier(name))

    _valid_constraint_types = ["UNIQUE", "CHECK", "NOT NULL"]
    _valid_check_functions = [] # defined in utils.psql
    def create_constraint(self, columns, type, name=None, check_func=None):
        """
        Create a constraint.

        This function will also add the constraint data to the meta_constraints table
        so that constraints can be dropped and recreated when uploading data.

        INPUT:

        - ``columns`` -- a list of column names
        - ``type`` -- we currently support "unique", "check", "not null"
        - ``name`` -- the name of the constraint; generated if not provided
        - ``check_func``-- a string, giving the name of a function
            that can take the columns as input and return a boolean output.
            It must be in the _valid_check_functions list above, in order
            to prevent SQL injection attacks
        """
        now = time.time()
        type = type.upper()
        if isinstance(columns, basestring):
            columns = [columns]
        if type not in self._valid_constraint_types:
            raise ValueError("Unrecognized constraint type")
        if check_func is not None and check_func not in self._valid_check_functions:
            # If the following line fails, add the desired function to the list defined above
            raise ValueError("%s not in list of approved check functions (edit db_backend to add)")
        if (check_func is None) == (type == 'CHECK'):
            raise ValueError("check_func should specified just for CHECK constraints")
        if type == 'NON NULL' and len(columns) != 1:
            raise ValueError("NON NULL only supports one column")
        search = None
        for col in columns:
            if col == "id":
                continue
            if col in self._search_cols:
                if search is False:
                    raise ValueError("Cannot mix search and extra columns")
                search = True
            elif col in self._extra_cols:
                if search is True:
                    raise ValueError("Cannot mix search and extra columns")
                search = False
            else:
                raise ValueError("%s not a column"%(col))
        if search is None:
            raise ValueError("Must specify non-id columns")
        if name is None:
            # Postgres has a maximum name length of 64 bytes
            # It will truncate if longer, but that causes suffixes of _tmp to be indistinguishable.
            if len(columns) <= 2:
                name = "_".join([self.search_table] + ["c"] + columns)
            elif len(columns) <= 8:
                name = "_".join([self.search_table] + ["c"] + [col[:2] for col in columns])
            else:
                name = "_".join([self.search_table] + ["c"] + ["".join(col[0] for col in columns)])



        with DelayCommit(self, silence=True):
            self._check_index_name(name, "Constraint") # also works for constraints
            table = self.search_table if search else self.extra_table
            creator = self._create_constraint_statement(name, table, type, columns, check_func)
            self._execute(creator)
            inserter = SQL("INSERT INTO meta_constraints (constraint_name, table_name, type, columns, check_func) VALUES (%s, %s, %s, %s, %s)")
            self._execute(inserter, [name, self.search_table, type, Json(columns), check_func])
        print "Constraint %s created in %.3f secs"%(name, time.time() - now)

    def _get_constraint_data(self, name, suffix):
        selecter = SQL("SELECT type, columns, check_func FROM meta_constraints WHERE table_name = %s AND constraint_name = %s")
        cur = self._execute(selecter, [self.search_table, name])
        if cur.rowcount > 1:
            raise RuntimeError("Duplicated rows in meta_constraints")
        elif cur.rowcount == 0:
            raise ValueError("Constraint %s does not exist in meta_constraints"%(name,))
        type, columns, check_func = cur.fetchone()
        search = (columns[0] in self._search_cols)
        table = self.search_table + suffix if search else self.extra_table + suffix
        return type, columns, check_func, table

    def drop_constraint(self, name, suffix="", permanent=False, commit=True):
        """
        Drop a specified constraint.

        INPUT:

        - ``name`` -- the name of the constraint
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the statement.
        - ``permanent`` -- whether to remove the index from the meta_constraint table
        """
        now = time.time()
        with DelayCommit(self, commit, silence=True):
            type, columns, check_func, table = self._get_constraint_data(name, suffix)
            dropper = self._drop_constraint_statement(name + suffix, table, type, columns)
            if permanent:
                deleter = SQL("DELETE FROM meta_constraints WHERE table_name = %s AND constraint_name = %s")
                self._execute(deleter, [self.search_table, name])
            self._execute(dropper)
        print "Dropped constraint %s in %.3f secs"%(name, time.time() - now)

    def restore_constraint(self, name, suffix=""):
        """
        Restore a specified constraint using the meta_constraints table.

        INPUT:

        - ``name`` -- the name of the constraint
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the ALTER TABLE statement.
        """
        now = time.time()
        with DelayCommit(self, silence=True):
            type, columns, check_func, table = self._get_constraint_data(name, suffix)
            # this avoids clashes with deprecated indexes/constraints
            self._rename_if_exists(name, suffix)
            creator = self._create_constraint_statement(name + suffix, table, type, columns, check_func)
            self._execute(creator)
        print "Created constraint %s in %.3f secs"%(name, time.time() - now)

    def _constraints_touching(self, columns):
        """
        Utility function for determining which constraints reference any of the given columns.
        """
        selecter = SQL("SELECT constraint_name FROM meta_constraints WHERE table_name = %s")
        if columns:
            selecter = SQL("{0} AND ({1})").format(selecter, SQL(" OR ").join(SQL("columns @> %s") * len(columns)))
            columns = [Json(col) for col in columns]
        return self._execute(selecter, [self.search_table] + columns, silent=True)

    ##################################################################
    # Exporting, reloading and reverting meta_tables, meta_indexes and meta_constraints     #
    ##################################################################

    def copy_to_meta(self, filename):
        self._copy_to_meta("meta_tables", filename, self.search_table)

    def copy_to_indexes(self, filename):
        self._copy_to_meta("meta_indexes", filename, self.search_table)

    def copy_to_constraints(self, filename):
        self._copy_to_meta("meta_constraints", filename, self.search_table)

    def _get_current_index_version(self):
        return self._get_current_meta_version("meta_indexes", self.search_table)

    def _get_current_constraint_version(self):
        return self._get_current_meta_version("meta_constraints", self.search_table)

    def reload_indexes(self, filename):
        return self._reload_meta("meta_indexes", filename, self.search_table)

    def reload_meta(self, filename):
        return self._reload_meta("meta_tables", filename, self.search_table)

    def reload_constraints(self, filename):
        return self._reload_meta("meta_constraints", filename, self.search_table)

    def revert_indexes(self, version = None):
        return self._revert_meta("meta_indexes", self.search_table, version)

    def revert_constraints(self, version = None):
        return self._revert_meta("meta_constraints", self.search_table, version)

    def revert_meta(self, version = None):
        return self._revert_meta("meta_tables", self.search_table, version)


    ##################################################################
    # Insertion and updating data                                    #
    ##################################################################

    def _break_stats(self):
        """
        This function should be called when the statistics are invalidated by an insertion or update.
        """
        if self._stats_valid:
            # Only need to interact with database in this case.
            updater = SQL("UPDATE meta_tables SET stats_valid = false WHERE name = %s")
            self._execute(updater, [self.search_table], silent=True)
            self._stats_valid = False

    def _break_order(self):
        """
        This function should be called when the id ordering is invalidated by an insertion or update.
        """
        if not self._out_of_order:
            # Only need to interact with database in this case.
            updater = SQL("UPDATE meta_tables SET out_of_order = true WHERE name = %s")
            self._execute(updater, [self.search_table], silent=True)
            self._out_of_order = True

    def finalize_changes(self):
        # TODO
        # Update stats.total
        # Refresh stats targets
        # Sort and set self._out_of_order
        pass

    def rewrite(self, func, query={}, resort=True, reindex=True, restat=True, tostr_func=None, commit=True, searchfile=None, extrafile=None, **kwds):
        """
        This function can be used to edit some or all records in the table.

        Note that if you want to add new columns, you must explicitly call add_column() first.

        For example, to add a new column to artin_reps that tracks the
        signs of the galois conjugates, you would do the following::

            sage: from lmfdb import db
            sage: db.artin_reps.add_column('GalConjSigns','jsonb')
            sage: def add_signs(rec):
            ....:     rec['GalConjSigns'] = sorted(list(set([conj['Sign'] for conj in rec['GaloisConjugates']])))
            ....:     return rec
            sage: db.artin_reps.rewrite(add_signs)
        """
        search_cols = ["id"] + self._search_cols
        if self.extra_table is None:
            projection = search_cols
        else:
            projection = search_cols + self._extra_cols
            extra_cols = ["id"] + self._extra_cols
        # It would be nice to just use Postgres' COPY TO here, but it would then be hard
        # to give func access to the data to process.
        # An alternative approach would be to use COPY TO and have func and filter both
        # operate on the results, but then func would have to process the strings
        if tostr_func is None:
            tostr_func = copy_dumps
        if searchfile is None:
            searchfile = tempfile.NamedTemporaryFile('w', delete=False)
        elif os.path.exists(searchfile):
            raise ValueError("Search file %s already exists" % searchfile)
        else:
            searchfile = open(searchfile, 'w')
        if self.extra_table is None:
            extrafile = EmptyContext()
        elif extrafile is None:
            extrafile = tempfile.NamedTemporaryFile('w', delete=False)
        elif os.path.exists(extrafile):
            raise ValueError("Extra file %s already exists" % extrafile)
        else:
            extrafile = open(extrafile, 'w')
        try:
            with searchfile:
                with extrafile:
                    # write headers
                    searchfile.write(u'\t'.join(search_cols) + u'\n')
                    searchfile.write(u'\t'.join(self.col_type.get(col) for col in search_cols) + u'\n\n')
                    if self.extra_table is not None:
                        extrafile.write(u'\t'.join(extra_cols) + u'\n')
                        extrafile.write(u'\t'.join(self.col_type.get(col) for col in extra_cols) + u'\n\n')

                    for rec in self.search(query, projection=projection, sort=[]):
                        processed = func(rec)
                        searchfile.write(u'\t'.join(tostr_func(processed.get(col), self.col_type[col]) for col in search_cols) + u'\n')
                        if self.extra_table is not None:
                            extrafile.write(u'\t'.join(tostr_func(processed.get(col), self.col_type[col]) for col in extra_cols) + u'\n')
            self.reload(searchfile.name, extrafile.name, resort=resort, reindex=reindex, restat=restat, commit=commit, log_change=False, **kwds)
            self.log_db_change("rewrite", query=query, projection=projection)
        finally:
            os.unlink(searchfile.name)
            if self.extra_table is not None:
                os.unlink(extrafile.name)

    def delete(self, query, resort=True, restat=True, commit=True):
        """
        Delete all rows matching the query.
        """
        with DelayCommit(self, commit, silence=True):
            qstr, values = self._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
            else:
                qstr = SQL(" WHERE {0}").format(qstr)
            deleter = SQL("DELETE FROM {0}{1}").format(Identifier(self.search_table), qstr)
            if self.extra_table is not None:
                deleter = SQL("WITH deleted_ids AS ({0} RETURNING id) DELETE FROM {1} WHERE id IN (SELECT id FROM deleted_ids)").format(deleter, Identifier(self.extra_table))
            cur = self._execute(deleter, values)
            self._break_order()
            self._break_stats()
            nrows = cur.rowcount
            self.stats.total -= nrows
            self.stats._record_count({}, self.stats.total)
            if resort:
                self.resort()
            if restat:
                self.stats.refresh_stats(total = False)
            self.log_db_change("delete", query=query, nrows=nrows)

    def update(self, query, changes, resort=True, restat=True, commit=True):
        for col in changes:
            if col in self._extra_cols:
                # Have to find the ids using the query, then update....
                raise NotImplementedError
        with DelayCommit(self, commit):
            qstr, values = self._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
                values = []
            else:
                qstr = SQL(" WHERE {0}").format(qstr)
            if len(changes) == 1:
                updater = SQL("UPDATE {0} SET {1} = {2}{3}")
            else:
                updater = SQL("UPDATE {0} SET ({1}) = ({2}){3}")
            updater = updater.format(Identifier(self.search_table),
                                     SQL(", ").join(map(Identifier, changes.keys())),
                                     SQL(", ").join(Placeholder() * len(changes)),
                                     qstr)
            change_values = self._parse_values(changes)
            self._execute(updater, change_values + values)
            self._break_order()
            self._break_stats()
            if resort:
                self.resort()
            if restat:
                self.stats.refresh_stats(total=False)
            self.log_db_change("update", query=query, changes=changes)

    def upsert(self, query, data, commit=True):
        """
        Update the unique row satisfying the given query, or insert a new row if no such row exists.
        If more than one row exists, raises an error.

        Upserting will often break the order constraint if the table is id_ordered,
        so you will probably want to call ``resort`` after all upserts are complete.

        INPUT:

        - ``query`` -- a dictionary with key/value pairs specifying at most one row of the table.
          The most common case is that there is one key, which is either an id or a label.
        - ``data`` -- a dictionary containing key/value pairs to be set on this row.

        The keys of both inputs must be columns in either the search or extras table.

        OUTPUT:

        - ``new_row`` -- whether a new row was inserted
        - ``row_id`` -- the id of the found/new row
        """
        if not query or not data:
            raise ValueError("Both query and data must be nonempty")
        if "id" in data:
            raise ValueError("Cannot set id")
        for col in query:
            if col != "id" and col not in self._search_cols:
                raise ValueError("%s is not a column of %s"%(col, self.search_table))
        if self.extra_table is None:
            search_data = dict(data)
            for col in data:
                if col not in self._search_cols:
                    raise ValueError("%s is not a column of %s"%(col, self.search_table))
        else:
            search_data = {}
            extras_data = {}
            for col, val in data.items():
                if col in self._search_cols:
                    search_data[col] = val
                elif col in self._extra_cols:
                    extras_data[col] = val
                else:
                    raise ValueError("%s is not a column of %s"%(col, self.search_table))
        cases = [(self.search_table, search_data)]
        if self.extra_table is not None:
            cases.append((self.extra_table, extras_data))
        with DelayCommit(self, commit, silence=True):
            # We have to split this command into a SELECT and an INSERT statement
            # rather than using postgres' INSERT INTO ... ON CONFLICT statement
            # because we have to take different additional steps depending on whether
            # an insertion actually occurred
            qstr, values = self._parse_dict(query)
            selecter = SQL("SELECT {0} FROM {1} WHERE {2} LIMIT 2").format(Identifier("id"), Identifier(self.search_table), qstr)
            cur = self._execute(selecter, values)
            if cur.rowcount > 1:
                raise ValueError("Query %s does not specify a unique row"%(query))
            elif cur.rowcount == 1: # update
                new_row = False
                row_id = cur.fetchone()[0]
                for table, dat in cases:
                    if len(dat) == 1:
                        updater = SQL("UPDATE {0} SET {1} = {2} WHERE {3}")
                    else:
                        updater = SQL("UPDATE {0} SET ({1}) = ({2}) WHERE {3}")
                    updater = updater.format(Identifier(table),
                                             SQL(", ").join(map(Identifier, dat.keys())),
                                             SQL(", ").join(Placeholder() * len(dat)),
                                             SQL("id = %s"))
                    dvalues = self._parse_values(dat)
                    dvalues.append(row_id)
                    self._execute(updater, dvalues)
                if not self._out_of_order and any(key in self._sort_keys for key in data):
                    self._break_order()

            else:  # insertion
                if "id" in data or "id" in query:
                    raise ValueError("Cannot specify an id for insertion")
                new_row = True
                for col, val in query.items():
                    if col not in search_data:
                        search_data[col] = val
                # We use the total on the stats object for the new id.  If someone else
                # has inserted data this will be a problem,
                # but it will raise an error rather than leading to invalid database state,
                # so it should be okay.
                search_data["id"] = row_id = self.max_id() + 1
                if self.extra_table is not None:
                    extras_data["id"] = self.max_id() + 1
                for table, dat in cases:
                    inserter = SQL("INSERT INTO {0} ({1}) VALUES ({2})").format(
                                    Identifier(table),
                                    SQL(", ").join(map(Identifier, dat.keys())),
                                    SQL(", ").join(Placeholder() * len(dat)))
                    self._execute(inserter, self._parse_values(dat))
                self._break_order()
                self.stats.total += 1
            self._break_stats()
            self.log_db_change("upsert", query=query, data=data)
            return new_row, row_id

    def insert_many(self, data, resort=True, reindex=False, restat=True, commit=True):
        """
        Insert multiple rows.

        This function will be faster than repeated ``upsert`` calls, but slower than ``copy_from``

        INPUT:

        - ``data`` -- a list of dictionaries, whose keys are columns and values the values to be set.
          All dictionaries should have the same set of keys;
          if this assumption is broken, some values may be set to their default values
          instead of the desired value, or an error may be raised.
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- boolean (default False). Whether to drop the indexes
          before insertion and restore afterward.  Note that if there is an exception during insertion
          the indexes will need to be restored manually using ``restore_indexes``.
        - ``restat`` -- whether to refresh statistics after insertion

        If the search table has an id, the dictionaries will be updated with the ids of the inserted records,
        though note that those ids will change if the ids are resorted.
        """
        if not data:
            raise ValueError("No data provided")
        if self.extra_table is not None:
            search_cols = [col for col in self._search_cols if col in data[0]]
            extra_cols = [col for col in self._extra_cols if col in data[0]]
            search_data = [{col: D[col] for col in search_cols} for D in data]
            extra_data = [{col: D[col] for col in extra_cols} for D in data]
        else:
            # we don't want to alter the input
            search_data = data[:]
        with DelayCommit(self, commit):
            if reindex:
                self.drop_pkeys()
                self.drop_indexes()
            jsonb_cols = [col for col, typ in self.col_type.iteritems() if typ == 'jsonb']
            for i, SD in enumerate(search_data):
                SD["id"] = self.max_id() + i + 1
                for col in jsonb_cols:
                    if col in SD:
                        SD[col] = Json(SD[col])
            cases = [(self.search_table, search_data)]
            if self.extra_table is not None:
                for i, ED in enumerate(extra_data):
                    ED["id"] = self.max_id() + i + 1
                    for col in jsonb_cols:
                        if col in ED:
                            ED[col] = Json(ED[col])
                cases.append((self.extra_table, extra_data))
            now = time.time()
            for table, L in cases:
                template = SQL("({0})").format(SQL(", ").join(map(Placeholder, L[0].keys())))
                inserter = SQL("INSERT INTO {0} ({1}) VALUES %s")
                inserter = inserter.format(Identifier(table),
                                           SQL(", ").join(map(Identifier, L[0].keys())))
                self._execute(inserter, L, values_list=True, template=template)
            print "Inserted %s records into %s in %.3f secs"%(len(search_data), self.search_table, time.time()-now)
            self._break_order()
            self._break_stats()
            self.stats.total += len(search_data)
            self.stats._record_count({}, self.stats.total)
            if resort:
                self.resort()
            if reindex:
                self.restore_pkeys()
                self.restore_indexes()
            if restat:
                self.stats.refresh_stats(total=False)
            self.log_db_change("insert_many", nrows=len(search_data))

    def _identify_tables(self, search_table, extra_table):
        """
        Utility function for normalizing input on ``resort``.
        """
        if search_table is not None:
            search_table = Identifier(search_table)
        else:
            search_table = Identifier(self.search_table)
        if extra_table is not None:
            if self.extra_table is None:
                raise ValueError("No extra table")
            extra_table = Identifier(extra_table)
        elif self.extra_table is not None:
            extra_table = Identifier(self.extra_table)
        return search_table, extra_table

    def resort(self, search_table=None, extra_table=None):
        """
        Restores the sort order on the id column.

        INPUT:

        - ``search_table`` -- a string giving the name of the search_table to be sorted.
            If None, will use ``self.search_table``; another common input is ``self.search_table + "_tmp"``.
        - ``extra_table`` -- a string giving the name of the extra_table to be sorted.
            If None, will use ``self.extra_table``; another common input is ``self.extra_table + "_tmp"``.
        """
        print "resorting disabled"
        return
        with DelayCommit(self, silence=True):
            if self._id_ordered and (search_table is not None or self._out_of_order):
                now = time.time()
                search_table, extra_table = self._identify_tables(search_table, extra_table)
                newid = "newid"
                while newid in self._search_cols or newid in self._extra_cols:
                    newid += "_"
                newid = Identifier(newid)
                oldid = Identifier("id")
                addcol = SQL("ALTER TABLE {0} ADD COLUMN {1} bigint")
                dropcol = SQL("ALTER TABLE {0} DROP COLUMN {1}")
                movecol = SQL("ALTER TABLE {0} RENAME COLUMN {1} TO {2}")
                pkey = SQL("ALTER TABLE {0} ADD PRIMARY KEY ({1})")
                self._execute(addcol.format(search_table, newid))
                updater = SQL("UPDATE {0} SET {1} = newsort.newid FROM (SELECT id, ROW_NUMBER() OVER(ORDER BY {2}) AS newid FROM {0}) newsort WHERE {0}.id = newsort.id")
                updater = updater.format(search_table, newid, self._sort)
                self._execute(updater)
                if extra_table is not None:
                    self._execute(addcol.format(extra_table, newid))
                    updater = SQL("UPDATE {0} SET {1} = search_table.{1} FROM (SELECT id, {1} FROM {2}) search_table WHERE {0}.id = search_table.id")
                    updater = updater.format(extra_table, newid, search_table)
                    self._execute(updater)
                    self._execute(dropcol.format(extra_table, oldid))
                    self._execute(movecol.format(extra_table, newid, oldid))
                    self._execute(pkey.format(extra_table, oldid))
                self._execute(dropcol.format(search_table, oldid))
                self._execute(movecol.format(search_table, newid, oldid))
                self._execute(pkey.format(search_table, oldid))
                self._set_ordered()
                print "Resorted %s in %.3f secs"%(self.search_table, time.time() - now)
            elif self._id_ordered:
                print "Data already sorted"
            else:
                print "Data does not have an id column to be sorted"

    def _set_ordered(self):
        """
        Marks this table as sorted in meta_tables
        """
        updater = SQL("UPDATE meta_tables SET out_of_order = false WHERE name = %s")
        self._execute(updater, [self.search_table])
        self._out_of_order = False



    def _write_header_lines(self, F, cols, sep=u"\t"):
        """
        Writes the header lines to a file
        (row of column names, row of column types, blank line).

        INPUT:

        - ``F`` -- a writable open file handle, at the beginning of the file.
        - ``cols`` -- a list of columns to write (either self._search_cols or self._extra_cols)
        - ``sep`` -- a string giving the column separator.  You should not use comma.
        """
        if cols and cols[0] != "id":
            cols = ["id"] + cols
        types = [self.col_type[col] for col in cols]
        F.write("%s\n%s\n\n"%(sep.join(cols), sep.join(types)))




    def _next_backup_number(self):
        """
        Finds the next unused backup number, for use in reload.
        """
        backup_number = 1
        for ext in ["", "_extras", "_counts", "_stats"]:
            while self._table_exists("{0}{1}_old{2}".format(self.search_table, ext, backup_number)):
                backup_number += 1
        return backup_number



    def _swap_in_tmp(self, tables, commit=True):
        """
        Helper function for ``reload``: appends _old{n} to the names of tables/indexes/pkeys
        and renames the _tmp versions to the live versions.

        INPUT:

        - ``tables`` -- a list of tables to rename (e.g. self.search_table, self.extra_table, self.stats.counts, self.stats.stats)
        """
        now = time.time()
        backup_number = self._next_backup_number()
        with DelayCommit(self, commit, silence=True):
            self._swap(tables, '', '_old' + str(backup_number))
            self._swap(tables, '_tmp', '')
            for table in tables:
                self._db.grant_select(table)
                if table.endswith("_counts") or table.endswith("_stats"):
                    self._db.grant_insert(table)
        print "Swapped temporary tables for %s into place in %s secs\nNew backup at %s"%(self.search_table, time.time()-now, "{0}_old{1}".format(self.search_table, backup_number))

    def _check_file_input(self, searchfile, extrafile, kwds):
        """
        Utility function for validating the inputs to ``rewrite``, ``reload`` and ``copy_from``.
        """
        if searchfile is None:
            raise ValueError("Must specify search file")
        if extrafile is not None and self.extra_table is None:
            raise ValueError("No extra table available")
        if extrafile is None and self.extra_table is not None:
            raise ValueError("Must provide file for extra table")
        if "columns" in kwds:
            raise ValueError("Cannot specify column order using the columns parameter")

    def reload(self, searchfile, extrafile=None, countsfile=None, statsfile=None, indexesfile=None, constraintsfile=None, metafile=None, resort=None, reindex=True, restat=None, final_swap=True, silence_meta=False, adjust_schema=False, commit=True, log_change=True, **kwds):
        """
        Safely and efficiently replaces this table with the contents of one or more files.

        INPUT:

        - ``searchfile`` -- a string, the file with data for the search table
        - ``extrafile`` -- a string, the file with data for the extra table.
            If there is an extra table, this argument is required.
        - ``countsfile`` -- a string (optional), giving a file containing counts
            information for the table.
        - ``statsfile`` -- a string (optional), giving a file containing stats
            information for the table.
        - ``indexesfile`` -- a string (optional), giving a file containing index
            information for the table.
        - ``constraintsfile`` -- a string (optional), giving a file containing constraint
            information for the table.
        - ``metafile`` -- a string (optional), giving a file containing the meta
            information for the table.
        - ``resort`` -- whether to sort the ids after copying in the data.
            Only relevant for tables that are id_ordered.  Defaults to sorting
            when the searchfile and extrafile do not contain ids.
        - ``reindex`` -- whether to drop the indexes before importing data
            and rebuild them afterward.  If the number of rows is a substantial
            fraction of the size of the table, this will be faster.
        - ``restat`` -- whether to refresh statistics afterward.  Default behavior
            is to refresh stats if either countsfile or statsfile is missing.
        - ``final_swap`` -- whether to perform the final swap exchanging the
            temporary table with the live one.
        - ``adjust_schema`` -- If True, it will create the new tables using the
            header columns, otherwise expects the schema specified by the files
            to match the current one
        - ``kwds`` -- passed on to psycopg2's ``copy_from``.  Cannot include "columns".

        .. NOTE:

            If the search and extra files contain ids, they should be contiguous,
            starting at 1.
        """
        suffix = "_tmp"
        if restat is None:
            restat = (countsfile is None or statsfile is None)
        self._check_file_input(searchfile, extrafile, kwds)
        print "Reloading %s..."%(self.search_table)
        now_overall = time.time()

        tables = []
        counts = {}
        tabledata = [(self.search_table, self._search_cols, True, searchfile),
                     (self.extra_table, self._extra_cols, True, extrafile),
                     (self.stats.counts, _counts_cols, False, countsfile),
                     (self.stats.stats, _stats_cols, False, statsfile)]
        addedid = None
        with DelayCommit(self, commit, silence=True):
            for table, cols, header, filename in tabledata:
                if filename is None:
                    continue
                tables.append(table)
                now = time.time()
                tmp_table = table + suffix
                if adjust_schema and header:
                    # read the header and create the tmp_table accordingly
                    cols = self._create_table_from_header(filename, tmp_table)
                else:
                    self._clone(table, tmp_table)
                addid, counts[table] = self._copy_from(filename, tmp_table, cols, header, kwds)
                # Raise error if exactly one of search and extra contains ids
                if header:
                    if addedid is None:
                        addedid = addid
                    elif addedid != addid:
                        raise ValueError("Mismatch on search and extra files containing id")
                if resort is None and addid:
                    resort = True
                print "\tLoaded data into %s in %.3f secs from %s" % (table, time.time() - now, filename)

            if extrafile is not None and counts[self.search_table] != counts[self.extra_table]:
                self.conn.rollback()
                raise RuntimeError("Different number of rows in searchfile and extrafile")

            ## a workaround while resort is disabled
            self.restore_pkeys(suffix=suffix)
            #if self._id_ordered and resort:
            #    extra_table = None if self.extra_table is None else self.extra_table + suffix
            #    self.resort(self.search_table + suffix, extra_table)
            #else:
            #    # We still need to build primary keys
            #    self.restore_pkeys(suffix=suffix)
            # end of workaround

            # update the indexes
            # these are needed before reindexing

            if indexesfile is not None:
                # we do the swap at the end
                self.reload_indexes(indexesfile)
            if constraintsfile is not None:
                self.reload_constraints(constraintsfile)
            if reindex:
                # Also restores constraints
                self.restore_indexes(suffix=suffix)
            if restat:
                # create tables before restating
                for table in [self.stats.counts, self.stats.stats]:
                    if not self._table_exists(table + suffix):
                        self._clone(table, table + suffix)

                if countsfile is None or statsfile is None:
                    self.stats.refresh_stats(suffix=suffix)
                for table in [self.stats.counts, self.stats.stats]:
                    if table not in tables:
                        tables.append(table)

            if countsfile:
                # create index on counts table
                self._create_counts_indexes(suffix=suffix)

            if final_swap:
                self.reload_final_swap(tables=tables, metafile=metafile, commit = False)
            elif metafile is not None and not silence_meta:
                print "Warning: since the final swap was not requested, we have not updated meta_tables"
                print "when performing the final swap with reload_final_swap, pass the metafile as an argument to update the meta_tables"

            if log_change:
                self.log_db_change("reload", counts=(countsfile is not None), stats=(statsfile is not None))
            print "Reloaded %s in %.3f secs" % (self.search_table, time.time() - now_overall)

    def reload_final_swap(self, tables=None, metafile=None, commit=True):
        """
        Renames the _tmp versions of `tables` to the live versions.
        and updates the corresponding meta_tables row if `metafile` is provided

        INPUT:

        - ``tables`` -- list of strings (optional), of the tables to renamed. If None is provided, renames all the tables ending in `_tmp`
        - ``metafile`` -- a string (optional), giving a file containing the meta information for the table.
        """
        with DelayCommit(self, commit, silence=True):
            if tables is None:
                tables = []
                for suffix in ['', '_extras', '_stats', '_counts']:
                    tablename = "{0}{1}_tmp".format(self.search_table, suffix)
                    if self._table_exists(tablename):
                        tables.append(tablename)

            self._swap_in_tmp(tables, commit=False)
            if metafile is not None:
                self.reload_meta(metafile)

        # Reinitialize object
        tabledata = self._execute(SQL("SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, has_extras, stats_valid, total FROM meta_tables WHERE name = %s"), [self.search_table]).fetchone()
        table = PostgresTable(self._db, *tabledata)
        self._db.__dict__[self.search_table] = table

    def drop_tmp(self):
        """
        Drop the temporary tables used in reloading.

        See the method ``cleanup_from_reload`` if you also want to drop
        the old backup tables.
        """
        with DelayCommit(self, silence=True):
            for suffix in ['', '_extras', '_stats', '_counts']:
                tablename = "{0}{1}_tmp".format(self.search_table, suffix)
                if self._table_exists(tablename):
                    self._execute(SQL("DROP TABLE {0}").format(Identifier(tablename)))
                    print "Dropped {0}".format(tablename)

    def reload_revert(self, backup_number=None, commit=True):
        """
        Use this method to revert to an older version of a table.

        Note that calling this method twice with the same input
        should return you to the original state.

        INPUT:

        - ``backup_number`` -- the backup version to restore,
            or ``None`` for the most recent.
        - ``commit`` -- whether to commit the changes.
        """
        if self._table_exists(self.search_table + '_tmp'):
            print "Reload did not successfully complete.  You must first call drop_tmp to delete the temporary tables created."
            return
        if backup_number is None:
            backup_number = self._next_backup_number() - 1
            if backup_number == 0:
                raise ValueError("No old tables available to revert from.")
        elif not self._table_exists("%s_old%s"%(self.search_table, backup_number)):
            raise ValueError("Backup %s does not exist"%backup_number)
        with DelayCommit(self, commit, silence=True):
            old = '_old' + str(backup_number)
            tables = []
            for suffix in ['', '_extras', '_stats', '_counts']:
                tablename = "{0}{1}".format(self.search_table, suffix)
                if self._table_exists(tablename + old):
                    tables.append(tablename)
            self._swap(tables, '', '_tmp')
            self._swap(tables, old, '')
            self._swap(tables, '_tmp', old)
            self.log_db_change("reload_revert")
        print "Swapped backup %s with %s"%(self.search_table, "{0}_old{1}".format(self.search_table, backup_number))

        # OLD VERSION that did something else
        #with DelayCommit(self, commit, silence=True):
        #    # drops the `_tmp` tables
        #    self.cleanup_from_reload(old = False)
        #    # reverts `meta_indexes` to previous state
        #    self.revert_indexes()
        #    print "Reverted %s to its previous state" % (self.search_table,)

    def cleanup_from_reload(self, old = True):
        """
        Drop the ``_tmp`` and ``_old*`` tables that are created during ``reload``.

        Note that doing so will prevent ``reload_revert`` from working.

        INPUT:

        - ``commit`` -- a boolean, default `True`, if to commit the changes to the database
        - ``old`` -- a boolean, default `True`, if to drop `_old*` tables
        """
        to_remove = []
        for suffix in ['', '_extras', '_stats', '_counts']:
            tablename = "{0}{1}_tmp".format(self.search_table, suffix)
            if self._table_exists(tablename):
                to_remove.append(tablename)
            backup_number = 1
            while old and True:
                tablename = "{0}{1}_old{2}".format(self.search_table, suffix, backup_number)
                if self._table_exists(tablename):
                    to_remove.append(tablename)
                else:
                    break
                backup_number += 1
        with DelayCommit(self, silence=True):
            for table in to_remove:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(table)))
                print "Dropped {0}".format(table)

    def max_id(self, table = None):
        if table is None:
            table = self.search_table
        res = db._execute(SQL("SELECT MAX(id) FROM {}".format(table))).fetchone()[0]
        if res is None:
            res = -1
        return res
    #A temporary hack for RANDOM FIXME
    def min_id(self, table = None):
        if table is None:
            table = self.search_table
        res = db._execute(SQL("SELECT MIN(id) FROM {}".format(table))).fetchone()[0]
        if res is None:
            res = 0
        return res


    def copy_from(self, searchfile, extrafile=None, resort=True, reindex=False, restat=True, commit=True, **kwds):
        """
        Efficiently copy data from files into this table.

        INPUT:

        - ``searchfile`` -- a string, the file with data for the search table
        - ``extrafile`` -- a string, the file with data for the extra table.
            If there is an extra table, this argument is required.
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- whether to drop the indexes before importing data and rebuild them afterward.
            If the number of rows is a substantial fraction of the size of the table, this will be faster.
        - ``kwds`` -- passed on to psycopg2's ``copy_from``.  Cannot include "columns".

        .. NOTE:

            If the search and extra files contain ids, they should be contiguous,
            starting immediately after the current max id (or at 1 if empty).
        """
        self._check_file_input(searchfile, extrafile, kwds)
        with DelayCommit(self, commit, silence=True):
            if reindex:
                self.drop_indexes()
            now = time.time()
            search_addid, search_count = self._copy_from(searchfile, self.search_table, self._search_cols, True, kwds)
            if extrafile is not None:
                extra_addid, extra_count = self._copy_from(extrafile, self.extra_table, self._extra_cols, True, kwds)
                if search_count != extra_count:
                    self.conn.rollback()
                    raise ValueError("Different number of rows in searchfile and extrafile")
                if search_addid != extra_addid:
                    self.conn.rollback()
                    raise ValueError("Mismatch on search and extra containing id")
            print "Loaded data into %s in %.3f secs"%(self.search_table, time.time() - now)
            self._break_order()
            if self._id_ordered and resort:
                self.resort()
            if reindex:
                self.restore_indexes()
            self._break_stats()
            if restat:
                self.stats.refresh_stats(total=False)
            self.stats.total += search_count
            self.stats._record_count({}, self.stats.total)
            self.log_db_change("copy_from", nrows=search_count)

    def copy_to(self, searchfile, extrafile=None, countsfile=None, statsfile=None, indexesfile=None, constraintsfile=None, metafile=None, commit=True, **kwds):
        """
        Efficiently copy data from the database to a file.

        The result will have one line per row of the table, tab separated and in order
        given by self._search_cols and self._extra_cols.

        INPUT:

        - ``searchfile`` -- a string, the filename to write data into for the search table
        - ``extrafile`` -- a string,the filename to write data into for the extra table.
            If there is an extra table, this argument is required.
        - ``countsfile`` -- a string (optional), the filename to write the data into for the counts table.
        - ``statsfile`` -- a string (optional), the filename to write the data into for the stats table.
        - ``indexesfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_indexes table.
        - ``constraintsfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_constraints table.
        - ``metatablesfile`` -- a string (optional), the filename to write the data into for the corresponding row of the meta_tables table.
        - ``kwds`` -- passed on to psycopg2's ``copy_to``.  Cannot include "columns".
        """
        self._check_file_input(searchfile, extrafile, kwds)
        sep = kwds.get("sep", u"\t")

        tabledata = [
                # tablename, cols, addid, write_header, filename
                (self.search_table, self._search_cols, True, True, searchfile),
                (self.extra_table, self._extra_cols, True, True, extrafile),
                (self.stats.counts, _counts_cols, False, False, countsfile),
                (self.stats.stats, _stats_cols, False, False, statsfile)
                ]

        metadata = [
                ("meta_indexes", "table_name", _meta_indexes_cols, indexesfile),
                ("meta_constraints", "table_name", _meta_constraints_cols, constraintsfile),
                ("meta_tables", "name", _meta_tables_cols, metafile)
                ]
        print "Exporting %s..."%(self.search_table)
        now_overall = time.time()
        with DelayCommit(self, commit):
            for table, cols, addid, write_header, filename in tabledata:
                if filename is None:
                    continue
                now = time.time()
                if addid:
                    cols = ["id"] + cols
                cols_wquotes = ['"' + col + '"' for col in cols]
                cur = self._db.cursor()
                with open(filename, "w") as F:
                    try:
                        if write_header:
                            self._write_header_lines(F, cols, sep=sep)
                        cur.copy_to(F, table, columns=cols_wquotes, **kwds)
                    except Exception:
                        self.conn.rollback()
                        raise
                print "\tExported %s in %.3f secs to %s" % (table, time.time() - now, filename)

            for table, wherecol, cols, filename in metadata:
                if filename is None:
                    continue
                now = time.time()
                cols = SQL(", ").join(map(Identifier, cols))
                select = SQL("SELECT {0} FROM {1} WHERE {2} = {3}").format(cols, Identifier(table), Identifier(wherecol), Literal(self.search_table))
                self._copy_to_select(select, filename, silent=True)
                print "\tExported data from %s in %.3f secs to %s" % (table, time.time() - now, filename)

            print "Exported %s in %.3f secs" % (self.search_table, time.time() - now_overall)

    ##################################################################
    # Updating the schema                                            #
    ##################################################################

    # Note that create_table and drop_table are methods on PostgresDatabase

    def set_sort(self, sort, resort=True, commit=True):
        """
        Change the default sort order for this table
        """
        self._set_sort(sort)
        with DelayCommit(self, commit, silence=True):
            if sort:
                updater = SQL("UPDATE meta_tables SET sort = %s WHERE name = %s")
                values = [sort, self.search_table]
            else:
                updater = SQL("UPDATE meta_tables SET sort = NULL WHERE name = %s")
                values = [self.search_table]
            self._execute(updater, values)
            self._break_order()
            if resort:
                self.resort()

            # add an index for the default sort
            if not any([index["columns"] == sort for index_name, index in self.list_indexes().iteritems()]):
                self.create_index(sort)
            self.log_db_change("set_sort", sort=sort)

    def add_column(self, name, datatype, extra=False):
        if name in self._search_cols:
            raise ValueError("%s already has column %s"%(self.search_table, name))
        if name in self._extra_cols:
            raise ValueError("%s already has column %s"%(self.extra_table, name))
        if datatype.lower() not in types_whitelist:
            if not any(regexp.match(datatype.lower()) for regexp in param_types_whitelist):
                raise ValueError("%s is not a valid type"%(datatype))
        self.col_type[name] = datatype
        if extra:
            if self.extra_table is None:
                raise ValueError("No extra table")
            table = self.extra_table
        else:
            table = self.search_table
        with DelayCommit(self, silence=True):
            # Since we have run the datatype through the whitelist,
            # the following string substitution is safe
            modifier = SQL("ALTER TABLE {0} ADD COLUMN {1} %s"%datatype).format(Identifier(table), Identifier(name))
            self._execute(modifier)
            if extra and name != 'id':
                self._extra_cols.append(name)
            elif not extra and name != 'id':
                self._search_cols.append(name)
            self.log_db_change("add_column", name=name, datatype=datatype)

    def drop_column(self, name, commit=True, force=False):
        if not force:
            ok = raw_input("Are you sure you want to drop %s? (y/N) "%name)
            if not (ok and ok[0] in ['y','Y']):
                return
        if name in self._sort_keys:
            raise ValueError("Sorting for %s depends on %s; change default sort order with set_sort() before dropping column"%(self.search_table, name))
        with DelayCommit(self, commit, silence=True):
            if name in self._search_cols:
                table = self.search_table
                counts_table = table + "_counts"
                stats_table = table + "_stats"
                jname = Json(name)
                deleter = SQL("DELETE FROM {0} WHERE table_name = %s AND columns @> %s")
                self._execute(deleter.format(Identifier("meta_indexes")), [table, jname])
                self._execute(deleter.format(Identifier("meta_constraints")), [table, jname])
                deleter = SQL("DELETE FROM {0} WHERE cols @> %s").format(Identifier(counts_table))
                self._execute(deleter, [jname])
                deleter = SQL("DELETE FROM {0} WHERE cols @> %s OR constraint_cols @> %s").format(Identifier(stats_table))
                self._execute(deleter, [jname, jname])
                self._search_cols.remove(name)
            elif name in self._extra_cols:
                table = self.extra_table
                self._extra_cols.remove(name)
            else:
                raise ValueError("%s is not a column of %s"%(name, self.search_table))
            modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(Identifier(table), Identifier(name))
            self._execute(modifier)
            self.col_type.pop(name, None)
            self.log_db_change("drop_column", name=name)
        print "Column %s dropped"%(name)

    def create_extra_table(self, columns, ordered=False, commit=True):
        """
        Splits this search table into two, linked by an id column.

        INPUT:

        - ``columns`` -- columns that are currently in the search table
            that should be moved to the new extra table. Can be empty.
        - ``ordered`` -- whether the id column should be kept in sorted
            order based on the default sort order stored in meta_tables.
        """
        if self.extra_table is not None:
            raise ValueError("Extra table already exists")
        with DelayCommit(self, commit, silence=True):
            if ordered and not self._id_ordered:
                updater = SQL("UPDATE meta_tables SET (id_ordered, out_of_order, has_extras) = (%s, %s, %s)")
                self._execute(updater, [True, True, True])
                self._id_ordered = True
                self._out_of_order = True
                self.resort()
            else:
                updater = SQL("UPDATE meta_tables SET (has_extras) = (%s)")
                self._execute(updater, [True])
            self.extra_table = self.search_table + "_extras"
            vars = [('id', 'bigint')]
            cur = self._indexes_touching(columns)
            if cur.rowcount > 0:
                raise ValueError("Indexes (%s) depend on extra columns"%(", ".join(rec[0] for rec in cur)))
            if columns:
                selecter = SQL("SELECT columns, constraint_name FROM meta_constraints WHERE table_name = %s AND ({0})").format(SQL(" OR ").join(SQL("columns @> %s") * len(columns)))
                cur = self._execute(selecter, [self.search_table] + [Json(col) for col in columns], silent=True)
                for rec in cur:
                    if not all(col in columns for col in rec[0]):
                        raise ValueError("Constraint %s (columns %s) split between search and extra table"%(rec[1], ", ".join(rec[0])))
            for col in columns:
                if col not in self.col_type:
                    raise ValueError("%s is not a column of %s"%(col, self.search_table))
                if col in self._sort_keys:
                    raise ValueError("Sorting for %s depends on %s; change default sort order with set_sort() before moving column to extra table"%(self.search_table, col))
                typ = self.col_type[col]
                if typ not in types_whitelist:
                    if not any(regexp.match(typ.lower()) for regexp in param_types_whitelist):
                        raise RuntimeError("%s is not a valid type"%(typ))
                vars.append((col, typ))
            self._extra_cols = []
            vars = SQL(", ").join(SQL("{0} %s"%typ).format(Identifier(col)) for col, typ in vars)
            creator = SQL("CREATE TABLE {0} ({1})").format(Identifier(self.extra_table), vars)
            self._execute(creator)
            if columns:
                self.drop_constraints(columns)
                try:
                    try:
                        transfer_file = tempfile.NamedTemporaryFile('w', delete=False)
                        cur = self._db.cursor()
                        with transfer_file:
                            cur.copy_to(transfer_file, self.search_table, columns=['id'] + columns)
                        with open(transfer_file.name) as F:
                            cur.copy_from(F, self.extra_table, columns=['id'] + columns)
                    finally:
                        transfer_file.unlink(transfer_file.name)
                except Exception:
                    self.conn.rollback()
                    raise
                self.restore_constraints(columns)
                for col in columns:
                    modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(Identifier(self.search_table), Identifier(col))
                    self._execute(modifier)
            else:
                sequencer = SQL("CREATE TEMPORARY SEQUENCE tmp_id")
                self._execute(sequencer)
                updater = SQL("UPDATE {0} SET id = nextval('tmp_id')").format(Identifier(self.extra_table))
                self._execute(updater)
            self.restore_pkeys()
            self.log_db_change("create_extra_table", columns=columns)

    def log_db_change(self, operation, **data):
        """
        Log changes to search tables.
        """
        self._db.log_db_change(operation, tablename=self.search_table, **data)

    def _check_verifications_enabled(self):
        if not self._db.is_verifying:
            raise ValueError("Verification not enabled by default; import db from lmfdb.verify to enable")
        if self._verifier is None:
            raise ValueError("No verifications defined for this table; add a class {0} in lmfdb/verify/{0}.py to enable".format(self.search_table))


    def verify(self, speedtype="all", check=None, label=None, ratio=None, logdir=None, parallel=4, follow=['errors', 'log', 'progress'], poll_interval=0.1, debug=False):
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
        lmfdb_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
        if logdir is None:
            logdir = os.path.join(lmfdb_root, 'logs', 'verification')
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
                for suffix in ['.log', '.errors', '.progress', '.started', '.done']:
                    filename = os.path.join(logdir, tname + suffix)
                    if os.path.exists(filename):
                        n = 0
                        oldfile = os.path.join(olddir, tname + str(n) + suffix)
                        while os.path.exists(oldfile):
                            n += 1
                            oldfile = os.path.join(olddir, tname + str(n) + suffix)
                        shutil.move(filename, oldfile)
            if speedtype == 'all':
                types = verifier.all_types()
            else:
                types = [verifier.speedtype(speedtype)]
            tabletypes = ["%s.%s" % (self.search_table, typ.shortname) for typ in types if verifier.get_checks_count(typ) > 0]
            if len(tabletypes) == 0:
                raise ValueError("No checks of type %s defined for %s" % (", ".join(typ.__name__ for typ in types), self.search_table))
            for tname in tabletypes:
                move_to_old(tname)
            if parallel:
                parallel = min(parallel, len(tabletypes))
                for tabletype in tabletypes:
                    print "Starting %s" % tabletype
                cmd = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'verify', 'verify_tables.py'))
                cmd = ['sage', '-python', cmd, '-j%s'%int(parallel), logdir, str(self.search_table), speedtype]
                if debug:
                    pipe = subprocess.Popen(cmd)
                else:
                    DEVNULL = open(os.devnull, 'wb')
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
                        print "No %s checks defined for %s" % (typ.__name__, self.search_table)
                    else:
                        print "Starting %s checks for %s" % (typ.__name__, self.search_table)
                        verifier.run(typ, logdir, label)
        else:
            msg = "Starting check %s" % check
            if label is not None:
                msg += " for label %s" % label
            print msg
            verifier.run_check(check, label=label, ratio=ratio)

    def list_verifications(self, details=True):
        """
        Lists all verification functions available for this table.

        INPUT:

        - ``details`` -- if True, details such as the docstring, ratio of rows on which the test
            is run by default and the constraint on rows for which this test is run are shown.
        """
        self._check_verifications_enabled()
        green = '\033[92m'
        red = '\033[91m'
        stop = '\033[0m'
        def show_check(name, check, typ):
            if typ.__name__ in ['overall', 'fast']:
                color = green
            else:
                color = red
            print '* ' + color + name + stop
            if details:
                if check.ratio < 1:
                    ratio_fmt = 'Ratio of rows: {val:.2%}'
                else:
                    ratio_fmt = 'Ratio of rows: {val:.0%}'
                for line in inspect.getdoc(check).split('\n'):
                    print ' '*4 + line
                for attr, fmt in [
                        ('disabled', 'Disabled'),
                        ('ratio', ratio_fmt),
                        ('max_failures', 'Max failures: {val}'),
                        ('timeout', 'Timeout after: {val}s'),
                        ('constraint', 'Constraint: {val}'),
                        ('projection', 'Projection: {val}'),
                        ('report_slow', 'Report slow test after: {val}s'),
                        ('max_slow', 'Maximum number of slow tests: {val}')]:
                    cattr = getattr(check, attr, None)
                    tattr = getattr(typ, attr, None)
                    if cattr is not None and cattr != tattr:
                        print ' '*6 + fmt.format(val=cattr)
        verifier = self._verifier
        for typ in ['over', 'fast', 'long', 'slow']:
            color = green if typ in ['over', 'fast'] else red
            typ = verifier.speedtype(typ)
            if verifier.get_checks_count(typ) > 0:
                name = color + typ.__name__ + stop
                print "\n{0} checks (default {1:.0%} of rows, {2}s timeout)".format(name, float(typ.ratio), typ.timeout)
                for checkname, check in inspect.getmembers(verifier.__class__):
                    if isinstance(check, typ):
                        show_check(checkname, check, typ)

    def set_importance(self, importance):
        """
        Production tables are marked as important so that they can't be accidentally dropped.

        Use this method to mark a table important or not important.
        """
        updater = SQL("UPDATE meta_tables SET important = %s WHERE name = %s")
        self._execute(updater, [importance, self.search_table])

class PostgresStatsTable(PostgresBase):
    """
    This object is used for storing statistics and counts for a search table.

    For each search table (e.g. ec_curves), there are two auxiliary tables supporting
    statistics functionality.  The counts table (e.g. ec_curves_counts) records
    the number of rows in the search table that satisfy a particular query.
    These counts are used by the website to display the number of matches on a
    search results page, and is also used on statistics pages and some browse pages.
    The stats table (e.g. ec_curves_stats) is used to record minimum, maximum and
    average values taken on by a numerical column (possibly over rows subject to some
    constraint).

    The stats table also serves a second purpose.  When displaying statistics for a
    section of the website, we often want to compute counts over all possible
    values of a set of columns.  For example, we might compute the number of
    elliptic curves with each possible torsion structure, or statistics on the
    conductor norm for elliptic curves over each number field.  The ``add_stats``
    and ``add_numstats`` methods provide these features, and when they are called
    a row is added to the stats table recording that these statistics were computed.

    We are only able to store counts and statistics in this way because our tables
    rarely change.  When we do make a change, statistics need to be updated.  This
    is done using the ``refresh_statistics`` method, which is called by default
    by the data management methods of ``PostgresTable`` like ``reload`` or ``copy_from``.
    As a consequence, once statistics are added, they do not need to be manually
    updated.

    The backend functionality of this object supports the StatsDisplay object
    available in `lmfdb.utils.display_stats`.  See that module for more details
    on making a statistics page for a section of the LMFDB.  In particular,
    the interface there has the capacity to automatically call ``add_stats`` so that
    viewing an appropriate stats page (e.g. beta.lmfdb.org/ModularForm/GL2/Q/holomorphic/stats)
    is sufficient to add the necessary statistics to the stats and counts tables.
    The methods ``_get_values_counts`` and ``_get_total_avg`` exist to support
    the ``StatsDisplay`` object.

    Once statistics have been added, they are accessed using the following functions:

    - ``quick_count`` -- count the number of rows satisfying a query,
                         returning None if not already cached.
    - ``count`` -- count the number of rows satisfying a query, computing and storing
                   the result if not yet cached.
    - ``max`` -- returns the maximum value attained by a column, computing and storing
                 the result if not yet cached.
    - ``column_counts`` -- provides all counts stored for a given column or set of columns.
                           This will be much faster than calling ``count`` repeatedly.
                           If ``add_stats`` has not been called, it will do so.
    - ``numstats`` -- provides numerical statistics on a single column, grouped by
                      the values taken on by another set of columns.
    - ``extra_counts`` -- returns a dictionary giving counts that were added separately
                          from an ``add_stats`` call (for example, via user requests on the website)
    - ``status`` -- prints a summary of the statistics currently stored.

    EXAMPLES:

    We add some statistics.  These specific commands aren't required in order to access stats,
    but they hopefully provide an example of how to add statistics that can be generalized to
    other tables.

    Adding statistics on torsion structure::

        sage: db.ec_nfcurves.stats.add_stats(['torsion_structure'])

    This make counts available::

        sage: db.ec_nfcurves.stats.quick_count({'torsion_structure': [2,4]})
        5100
        sage: torsion_structures = db.ec_nfcurves.stats.column_counts('torsion_structure')
        sage: torsion_structures[4,4]
        14L

    Adding statistics on norm_conductor, grouped by signature::

        sage: db.ec_nfcurves.stats.add_numstats('norm_conductor', ['signature'])

    Once added, we can later retrieve the statistics::

        sage: normstats = db.ec_nfcurves.stats.numstats('conductor_norm', ['signature'])

    And find the maximum conductor norm for a curve in the LMFDB over a totally real cubic field::

        sage: normstats[3,0]['max']
        2059

    You can also find this directly, but if you need the same kind of statistic many times
    then the ``numstats`` method will be faster::

        sage: db.ec_nfcurves.stats.max('conductor_norm', {'signature': [3,0]})
        2059

    You can see what additional counts are stored using the ``extra_counts`` method::

        sage: db.mf_newforms.stats.extra_counts().keys()[0]
        (u'dim',)
        sage: db.mf_newforms.stats.extra_counts()[('dim',)]
        [(({u'$gte': 10, u'$lte': 20},), 39288L)]

    SCHEMA:

    The columns in a counts table are:

    - ``cols`` -- these are the columns specified in the query.  A list, stored as a jsonb.
    - ``values`` -- these could be numbers, or dictionaries giving a more complicated constraint.
        A list, of the same length as ``cols``, stored as a jsonb.
    - ``count`` -- the number of rows in the search table where the the columns take on the given values.
    - ``extra`` -- false if the count was added in an ``add_stats`` method,
        true if it was added separately (such as by a request on a search results page).
    - ``split`` -- used when column values are arrays.  If true, then the array is split
        up before counting.  For example, when counting ramified primes,
        if split werefalse then [2,3,5] and [2,3,7] would count as separate values
        (there are 888280 number fields in the LMFDB with ramps = [2,3,5]).
        If split were true, then both [2,3,5] and [2,3,7] would contribute toward the count for 2.

    For example,
    ["ramps"], [[2, 3, 5]], 888280, t, f
    would record the count of number fields with ramps=[2, 3, 5], and
    ["ramps"], [2], 11372999, f, t
    would record the count of number fields with ramps containing 2.

    The columns in a stats table are:

    - ``stat`` -- a text field giving the statistic type.  Currently, will be one of
        "max", "min", "avg", "total" (one such row for each add_stats call),
        "ntotal" (one such row for each add_numstats call), "split_total"
        (one such row for each add_stats call with split_list True).
    - ``cols`` -- the columns for which statistics are being computed.  Must have
        length 1 and be numerical in order to have "max", "min" or "avg"
    - ``constraint_cols`` -- columns in the constraint dictionary
    - ``constraint_values`` -- the values specified for the columns in ``ccols``
    - ``threshold`` -- NULL or an integer.  If specified, only value sets where the
        row count surpasses the threshold will be added to the counts table and
        counted toward min, max and avg statistics.

    BUCKETED STATS:

    Sometimes you want to add statistics on a column, but it takes on too many values.
    For example, you want to give an idea of the distribution of levels for classical
    modular forms, but there are thousands of possibilities.

    You can use the ``add_bucketed_counts`` in this circumstance.  You provide a
    dictionary whose keys are columns, and whose values are a list of strings giving intervals.
    Counts are computed with values grouped into intervals.

    EXAMPLE::

        sage: db.mf_newforms.stats.add_bucketed_counts(['level', 'weight'], {'level': ['1','2-10','11-100','101-1000','1001-2000', '2001-4000','4001-6000','6001-8000','8001-10000'], 'weight': ['1','2','3','4','5-8','9-16','17-32','33-64','65-316']})

    You can now count certain ranges:

        sage: db.mf_newforms.stats.quick_count({'level':{'$gte':101, '$lte':1000}, 'weight':4})
        12281

    But only those specified by the buckets:

        sage: db.mf_newforms.stats.quick_count({'level':{'$gte':201, '$lte':800}, 'weight':2}) is None
        True

    INPUT:

    - ``table`` -- a ``PostgresTable`` object.
    - ``total`` -- an integer, the number of rows in the search table.  If not provided,
        it will be looked up or computed.
    """
    def __init__(self, table, total=None):
        PostgresBase.__init__(self, table.search_table, table._db)
        self.table = table
        self.search_table = st = table.search_table
        self.stats = st + "_stats"
        self.counts = st + "_counts"
        if total is None:
            total = self.quick_count({})
            if total is None:
                total = self._slow_count({}, extra=False)
        self.total = total

    def _has_stats(self, jcols, ccols, cvals, threshold, split_list=False, threshold_inequality=False):
        """
        Checks whether statistics have been recorded for a given set of columns.
        It just checks whether the "total" stat has been computed.

        INPUT:

        - ``jcols`` -- a list of the columns to be accumulated (wrapped in Json).
        - ``ccols`` -- a list of the constraint columns (wrapped in Json).
        - ``cvals`` -- a list of the values required for the constraint columns (wrapped in Json).
        - ``threshold`` -- an integer: if the number of rows with a given tuple of
           values for the accumulated columns is less than this threshold, those
           rows are thrown away.
        - ``split_list`` -- whether entries of lists should be counted once for each entry.
        - ``threshold_inequality`` -- if true, then any lower threshold will still count for having stats.
        """
        if split_list:
            values = [jcols, "split_total"]
        else:
            values = [jcols, "total"]
        values.extend([ccols, cvals])
        ccols = "constraint_cols = %s"
        cvals = "constraint_values = %s"
        if threshold is None:
            threshold = "threshold IS NULL"
        else:
            values.append(threshold)
            if threshold_inequality:
                threshold = "(threshold IS NULL OR threshold <= %s)"
            else:
                threshold = "threshold = %s"
        selecter = SQL("SELECT 1 FROM {0} WHERE cols = %s AND stat = %s AND {1} AND {2} AND {3}")
        selecter = selecter.format(Identifier(self.stats), SQL(ccols), SQL(cvals), SQL(threshold))
        cur = self._execute(selecter, values)
        return cur.rowcount > 0

    def quick_count(self, query, split_list=False, suffix=''):
        """
        Tries to quickly determine the number of results for a given query
        using the count table.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``split_list`` -- see the ``add_stats`` method
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to perform the count

        OUTPUT:

        Either an integer giving the number of results, or None if not cached.
        """
        cols, vals = self._split_dict(query)
        selecter = SQL("SELECT count FROM {0} WHERE cols = %s AND values = %s AND split = %s").format(Identifier(self.counts + suffix))
        cur = self._execute(selecter, [cols, vals, split_list])
        if cur.rowcount:
            return int(cur.fetchone()[0])

    def _slow_count(self, query, split_list=False, record=True, suffix='', extra=True):
        """
        No shortcuts: actually count the rows in the search table.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``split_list`` -- see the ``add_stats`` method.
        - ``record`` -- boolean (default False).  Whether to store the result in the count table.
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to perform the count
        - ``extra`` -- used if the result is recorded (see discussion at the top of this class).

        OUTPUT:

        The number of rows in the search table satisfying the query.
        """
        if split_list:
            raise NotImplementedError
        selecter = SQL("SELECT COUNT(*) FROM {0}").format(Identifier(self.search_table + suffix))
        qstr, values = self.table._parse_dict(query)
        if qstr is not None:
            selecter = SQL("{0} WHERE {1}").format(selecter, qstr)
        cur = self._execute(selecter, values)
        nres = cur.fetchone()[0]
        if record:
            self._record_count(query, nres, split_list, suffix, extra)
        return nres

    def _record_count(self, query, count, split_list=False, suffix='', extra=True):
        """
        Add the count to the counts table.

        INPUT::

        - ``query`` -- a dictionary
        - ``count`` -- the count of rows in the search table satisfying the query
        - ``split_list`` -- see the ``add_stats`` method
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to store the count
        - ``extra`` -- see the discussion at the top of this class.
        """
        cols, vals = self._split_dict(query)
        data = [count, cols, vals, split_list]
        if self.quick_count(query) is None:
            updater = SQL("INSERT INTO {0} (count, cols, values, split, extra) VALUES (%s, %s, %s, %s, %s)")
            data.append(extra)
        else:
            updater = SQL("UPDATE {0} SET count = %s WHERE cols = %s AND values = %s AND split = %s")
        try:
            # This will fail if we don't have write permission,
            # for example, if we're running as the lmfdb user
            self._execute(updater.format(Identifier(self.counts + suffix)), data)
        except DatabaseError:
            pass
        # We also store the total count in meta_tables to improve startup speed
        if not query:
            updater = SQL("UPDATE meta_tables SET total = %s WHERE name = %s")
            # This should never be called from the webserver, since we only record
            # counts for {} when data is updated.
            self._execute(updater, [count, self.search_table])

    def count(self, query={}, record=True):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``record`` -- (default True) whether to record the number of results in the counts table.

        OUTPUT:

        The number of records satisfying the query.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.stats.count({'degree':int(6),'galt':int(7)})
            244006
        """
        if not query:
            return self.total
        nres = self.quick_count(query)
        if nres is None:
            nres = self._slow_count(query, record=record)
        return int(nres)

    def column_counts(self, cols, constraint=None, threshold=None, split_list=False):
        """
        Returns all of the counts for a given column or set of columns.

        INPUT:

        - ``cols`` -- a string or list of strings giving column names.
        - ``constraint`` -- only rows satisfying this constraint will be considered.
            It should take the form of a dictionary of the form used in search queries.
        - ``threshold`` -- an integer or None.  If specified, only values with
            counts above the threshold are returned.
        - ``split_list`` -- see the documentation for add_stats.

        OUTPUT:

        A dictionary with keys the values taken on by the columns in the database,
        and value the count of rows taking on those values.  If threshold is provided,
        only counts at least the threshold will be included.

        If cols is a string, then the keys of the dictionary will be just the values
        taken on by that column.  If cols is a list of strings, then the keys will
        be tuples of values taken on by the dictionary.

        If the value taken on by a column is a dictionary D, then the key will be tuple(D.items()).
        """
        if isinstance(cols, basestring):
            cols = [cols]
            one_col = True
        else:
            one_col = False
            cols = sorted(cols)
        if constraint is None:
            ccols, cvals, allcols = Json([]), Json([]), cols
        else:
            ccols, cvals = self._split_dict(constraint)
            allcols = sorted(list(set(cols + constraint.keys())))
            # Ideally we would include the constraint in the query, but it's not easy to do that
            # So we check the results in Python
        jcols = Json(cols)
        if not self._has_stats(jcols, ccols, cvals, threshold=threshold, split_list=split_list, threshold_inequality=True):
            self.add_stats(cols, constraint, threshold, split_list)
        jallcols = Json(allcols)
        if threshold is None:
            thresh = SQL("")
        else:
            thresh = SQL(" AND count >= {0}").format(Literal(threshold))
        selecter = SQL("SELECT values, count FROM {0} WHERE cols = %s AND split = %s{1}").format(Identifier(self.counts), thresh)
        cur = self._execute(selecter, [jallcols, split_list])
        if one_col:
            _make_tuple = lambda x: make_tuple(x)[0]
        else:
            _make_tuple = make_tuple
        if constraint is None:
            return {_make_tuple(rec[0]): rec[1] for rec in cur}
        else:
            constraint_list = [(i, constraint[col]) for (i, col) in enumerate(allcols) if col in constraint]
            column_indexes = [i for (i, col) in enumerate(allcols) if col not in constraint]
            def satisfies_constraint(val):
                return all(val[i] == c for i,c in constraint_list)
            def remove_constraint(val):
                return [val[i] for i in column_indexes]
            return {_make_tuple(remove_constraint(rec[0])): rec[1] for rec in cur if satisfies_constraint(rec[0])}

    def _quick_max(self, col, ccols, cvals):
        """
        Return the maximum value achieved by the column, or None if not cached.

        INPUT::

        - ``col`` -- the column
        - ``ccols`` -- constraint columns
        - ``cvals`` -- constraint values.  The max will be taken over rows where
            the constraint columns take on these values.
        """
        constraint = SQL("constraint_cols = %s AND constraint_values = %s")
        values = ["max", Json([col]), ccols, cvals]
        selecter = SQL("SELECT value FROM {0} WHERE stat = %s AND cols = %s AND threshold IS NULL AND {1}").format(Identifier(self.stats), constraint)
        cur = self._execute(selecter, values)
        if cur.rowcount:
            return cur.fetchone()[0]

    def _slow_max(self, col, constraint):
        """
        Compute the maximum value achieved by the column.

        INPUT::

        - ``col`` -- the column
        - ``constraint`` -- a dictionary giving a constraint.  The max will be taken
            over rows satisfying this constraint.
        """
        qstr, values = self.table._parse_dict(constraint)
        if qstr is None:
            where = SQL("")
            values = []
        else:
            where = SQL(" WHERE {0}").format(qstr)
        base_selecter = SQL("SELECT {0} FROM {1}{2} ORDER BY {0} DESC ").format(
            Identifier(col), Identifier(self.search_table), where)
        selecter = base_selecter + SQL("LIMIT 1")
        cur = self._execute(selecter, values)
        m = cur.fetchone()[0]
        if m is None:
            # the default order ends with NULLs, so we now have to use NULLS LAST,
            # preventing the use of indexes.
            selecter = base_selecter + SQL("NULLS LAST LIMIT 1")
            cur = self._execute(selecter, values)
            m = cur.fetchone()[0]
        return m

    def _record_max(self, col, ccols, cvals, m):
        """
        Store a computed maximum value in the stats table.

        INPUT:

        - ``col`` -- the column on which the max is taken
        - ``ccols`` -- the constraint columns
        - ``cvals`` -- the constraint values
        - ``m`` -- the maximum value to be stored
        """
        try:
            inserter = SQL("INSERT INTO {0} (cols, stat, value, constraint_cols, constraint_values) VALUES (%s, %s, %s, %s, %s)")
            self._execute(inserter.format(Identifier(self.stats)), [Json([col]), "max", m, ccols, cvals])
        except Exception:
            pass

    def max(self, col, constraint={}, record=True):
        """
        The maximum value attained by the given column, which must be in the search table.

        INPUT:

        - ``col`` -- the column on which the max is taken.
        - ``constraint`` -- a dictionary giving a constraint.  The max will be taken
            over rows satisfying this constraint.
        - ``record`` -- whether to store the result in the stats table.

        EXAMPLES::

            sage: from lmfdb import db
            sage: db.nf_fields.stats.max('class_number')
            1892503075117056
        """
        if col == "id":
            # We just use the count in this case
            return self.count()
        if col not in self.table._search_cols:
            raise ValueError("%s not a column of %s"%(col, self.search_table))
        ccols, cvals = self._split_dict(constraint)
        m = self._quick_max(col, ccols, cvals)
        if m is None:
            m = self._slow_max(col, constraint)
            self._record_max(col, ccols, cvals, m)
        return m

    def _bucket_iterator(self, buckets, constraint):
        """
        Utility function for adding buckets to a constraint

        INPUT:

        - ``buckets`` -- a dictionary whose keys are columns, and whose values are
            lists of strings giving either single integers or intervals.
        - ``constraint`` -- a dictionary giving additional constraints on other columns.

        OUTPUT:

        Iterates over the cartesian product of the buckets formed, yielding in each case
        a dictionary that can be used as a query.
        """
        expanded_buckets = []
        for col, divisions in buckets.items():
            parse_singleton = pg_to_py[self.table.col_type[col]]
            cur_list = []
            for bucket in divisions:
                if not bucket:
                    continue
                if bucket[-1] == '-':
                    a = parse_singleton(bucket[:-1])
                    cur_list.append({col:{'$gte':a}})
                elif '-' not in bucket[1:]:
                    cur_list.append({col:parse_singleton(bucket)})
                else:
                    if bucket[0] == '-':
                        L = bucket[1:].split('-')
                        L[0] = '-' + L[0]
                    else:
                        L = bucket.split('-')
                    a, b = map(parse_singleton, L)
                    cur_list.append({col:{'$gte':a, '$lte':b}})
            expanded_buckets.append(cur_list)
        for X in cartesian_product_iterator(expanded_buckets):
            if constraint is None:
                bucketed_constraint = {}
            else:
                bucketed_constraint = dict(constraint) # copy
            for D in X:
                bucketed_constraint.update(D)
            yield bucketed_constraint

    def add_bucketed_counts(self, cols, buckets, constraint={}, commit=True):
        """
        A convenience function for adding statistics on a given set of columns,
        where rows are grouped into intervals by a bucketing dictionary.

        See the ``add_stats`` mehtod for the actual statistics computed.

        INPUT:

        - ``cols`` -- the columns to be displayed.  This will usually be a list of strings of length 1 or 2.
        - ``buckets`` -- a dictionary whose keys are columns, and whose values are lists
            of strings giving either single integers or intervals.
        - ``constraint`` -- a dictionary giving additional constraints on other columns.
        """
        # Conceptually, it makes sense to have the bucket keys included in the columns,
        # but they should be removed in order to treat the bucketed_constraint properly
        # as a constraint.
        cols = [col for col in cols if col not in buckets]
        for bucketed_constraint in self._bucket_iterator(buckets, constraint):
            self.add_stats(cols, bucketed_constraint, commit=commit)

    def _split_dict(self, D):
        """
        A utility function for splitting a dictionary into parallel lists of keys and values.
        """
        if D:
            ans = zip(*sorted(D.items()))
        else:
            ans = [], []
        return map(Json, ans)

    def _join_dict(self, ccols, cvals):
        """
        A utility function for joining a list of keys and of values into a dictionary.
        """
        assert len(ccols) == len(cvals)
        return dict(zip(ccols, cvals))

    def _print_statmsg(self, cols, constraint, threshold, grouping=None, split_list=False, tense='now'):
        """
        Print a message describing the statistics being added.

        INPUT:

        - ``cols`` -- as for ``add_stats``
        - ``constraint`` -- as output by ``_process_constraint``
        - ``threshold`` -- as for ``add_stats``
        - ``grouping`` -- as for ``add_numstats``
        - ``split_list`` -- as for ``add_stats``
        - ``tense`` -- either "now" or "past".  Just affects the grammar.
        """
        if isinstance(constraint, tuple):
            if constraint == (None, None):
                constraint = {}
            else:
                constraint = self._join_dict(*constraint)
        if split_list:
            msg = "split statistics"
        elif grouping is None:
            msg = "statistics"
        else:
            msg = "numerical statistics for %s, grouped by %s," % (cols[0], "+".join(grouping))
        if tense == 'now':
            msg = "Adding %s to %s " % (msg, self.search_table)
        else:
            msg = "%s " % msg.capitalize()
        if grouping is None and cols:
            msg += "for " + ", ".join(cols)
        if constraint:
            from lmfdb.utils import range_formatter
            msg += ": " + ", ".join("{col} = {disp}".format(col=col, disp=range_formatter(val)) for col, val in constraint.items())
        if threshold:
            msg += " (threshold=%s)" % threshold
        if tense == 'now':
            self.logger.info(msg)
        else:
            print msg

    def _compute_numstats(self, col, grouping, where, values, constraint=None, threshold=None, suffix='', silent=False):
        """
        Computes statistics on a single numerical column, grouped by the values of another set of columns.

        This function is used by add_numstats to compute the statistics to add.

        INPUT:

        - ``col`` -- as for ``add_numstats``
        - ``grouping`` -- as for ``add_numstats``
        - ``where`` -- as output by ``_process_constraint``
        - ``values`` -- as output by ``_process_constraint``
        - ``constraint`` -- as output by ``_process_constraint``
        - ``threshold`` -- as for ``add_numstats``
        - ``suffix`` -- as for ``add_numstats``
        - ``silent`` -- whether to print an info message to the logger.
        """
        if not silent:
            self._print_statmsg([col], constraint, threshold, grouping=grouping)
        if threshold is None:
            having = SQL("")
        else:
            having = SQL(" HAVING COUNT(*) >= {0}").format(Literal(threshold))
        vars = SQL("COUNT(*), AVG({0}), MIN({0}), MAX({0})").format(Identifier(col))
        if grouping:
            groups = SQL(", ").join(map(Identifier, grouping))
            groupby = SQL(" GROUP BY {0}").format(groups)
            vars = SQL("{0}, {1}").format(vars, groups)
        else:
            groupby = SQL("")
        selecter = SQL("SELECT {vars} FROM {table}{where}{groupby}{having}").format(vars=vars, table=Identifier(self.search_table + suffix), groupby=groupby, where=where, having=having)
        return self._execute(selecter, values)

    def add_numstats(self, col, grouping, constraint=None, threshold=None, suffix='', commit=True):
        """
        For each value taken on by the columns in ``grouping``, numerical statistics on ``col`` (min, max, avg) will be added.

        This function does not add counts of each distinct value taken on by ``col``,
        and it uses SQL rather than Python to compute MIN, MAX and AVG.  This makes it more
        suitable than ``add_stats`` if a column takes on a large number of distinct values.

        INPUT:

        - ``col`` -- the column whose minimum, maximum and average values are to be computed.
            Should be an integer or real type in order for `AVG` to function.
        - ``grouping`` -- a list of columns.  Statistics will be computed within groups defined by
            the values taken on by these columns.  If no columns given, then the overall statistics
            will be computed.
        - ``constraint`` -- a dictionary or pair of lists, giving a query.  Only rows satisfying this
            constraint will be included in the statistics.
        - ``threshold`` -- if given, only sets of values for the grouping columns where the
            count surpasses this threshold will be included.
        - ``suffix`` -- if given, the counts will be performed on the table with the suffix appended.
        - ``commit`` -- if false, the results will not be committed to the database.
        """
        if isinstance(grouping, basestring):
            grouping = [grouping]
        else:
            grouping = sorted(grouping)
        if isinstance(col, (list, tuple)):
            if len(col) == 1:
                col = col[0]
            else:
                raise ValueError("Must provide exactly one column")
        where, values, constraint, ccols, cvals, _ = self._process_constraint([col], constraint)
        jcol = Json([col])
        jcgcols = Json(sorted(ccols.adapted + grouping))
        if self._has_numstats(jcol, jcgcols, cvals, threshold):
            self.logger.info("Numstats already exist")
            return
        now = time.time()
        with DelayCommit(self, commit, silence=True):
            counts_to_add = []
            stats_to_add = []
            total = 0
            cur = self._compute_numstats(col, grouping, where, values, constraint, threshold, suffix)
            for statvec in cur:
                cnt, colstats, gvals = statvec[0], statvec[1:4], statvec[4:]
                total += cnt
                if constraint is None:
                    jcgvals = gvals
                else:
                    jcgvals = []
                    i = 0
                    for col in jcgcols.adapted:
                        if col in grouping:
                            jcgvals.append(gvals[i])
                            i += 1
                        else:
                            jcgvals.append(constraint[col])
                jcgvals = Json(jcgvals)
                counts_to_add.append((jcgcols, jcgvals, cnt, False, False))
                for st, val in zip(["avg", "min", "max"], colstats):
                    stats_to_add.append((jcol, st, val, jcgcols, jcgvals, threshold))
            # We record the grouping in a record to be inserted in the stats table
            # Note that we don't sort ccols and grouping together, so that we can distinguish them
            stats_to_add.append((jcol, "ntotal", total, Json(ccols.adapted + grouping), cvals, threshold))
            # It's possible that stats/counts have been added by an add_stats call
            # The right solution is a unique index and an ON CONFLICT DO NOTHING clause,
            # but for now we just live with the possibility of a few duplicate rows.
            inserter = SQL("INSERT INTO {0} (cols, stat, value, constraint_cols, constraint_values, threshold) VALUES %s")
            self._execute(inserter.format(Identifier(self.stats + suffix)), stats_to_add, values_list=True)
            inserter = SQL("INSERT INTO {0} (cols, values, count, split, extra) VALUES %s")
            self._execute(inserter.format(Identifier(self.counts + suffix)), counts_to_add, values_list=True)
        self.logger.info("Added numstats in %.3f secs"%(time.time() - now))

    def _has_numstats(self, jcol, cgcols, cvals, threshold):
        """
        Checks whether statistics have been recorded for a given set of columns.
        It just checks whether the "ntotal" stat has been added.

        INPUT:

        - ``jcol`` -- a list containing the column name whose min/max/avg were computed (wrapped in Json)
        - ``cgcols`` -- the sorted constraint columns, followed by the sorted grouping columns (wrappe in Json)
        - ``cvals`` -- a list of the values required for the constraint columns (wrapped in Json).
        - ``threshold`` -- an integer: if the number of rows with a given tuple of
           values for the grouping columns is less than this threshold, those
           rows are thrown away.
        """
        values = [jcol, "ntotal", cgcols, cvals]
        if threshold is None:
            threshold = "threshold IS NULL"
        else:
            values.append(threshold)
            threshold = "threshold = %s"
        selecter = SQL("SELECT 1 FROM {0} WHERE cols = %s AND stat = %s AND constraint_cols = %s AND constraint_values = %s AND {1}")
        selecter = selecter.format(Identifier(self.stats), SQL(threshold))
        cur = self._execute(selecter, values)
        return cur.rowcount > 0

    def numstats(self, col, grouping, constraint=None, threshold=None):
        """
        Returns statistics on a column, grouped by a set of other columns.

        If the statistics are not already cached, the ``add_numstats`` method will be called.

        INPUT:

        - ``col`` -- the column whose minimum, maximum and average values are to be computed.
            Should be an integer or real type in order for `AVG` to function.
        - ``grouping`` -- a list of columns.  Statistics will be computed within groups defined by
            the values taken on by these columns.  If no columns given, then the overall statistics
            will be computed.
        - ``constraint`` -- a dictionary or pair of lists, giving a query.  Only rows satisfying this
            constraint will be included in the statistics.
        - ``threshold`` -- if given, only sets of values for the grouping columns where the
            count surpasses this threshold will be included.

        OUTPUT:

        A dictionary with keys the possible values taken on the the columns in grouping.
        Each value is a dictionary with keys 'min', 'max', 'avg'
        """
        if isinstance(grouping, basestring):
            onegroup = True
            grouping = [grouping]
        else:
            onegroup = False
        if isinstance(col, (list, tuple)):
            if len(col) == 1:
                col = col[0]
            else:
                raise ValueError("Only single columns supported")
        grouping = sorted(grouping)
        ccols, cvals = self._split_dict(constraint)
        jcgcols = Json(sorted(ccols.adapted + grouping))
        jcol = Json([col])
        if not self._has_numstats(jcol, jcgcols, cvals, threshold):
            self.logger.info("Missing numstats, adding them")
            self.add_numstats(col, grouping, constraint, threshold)
            # raise ValueError("Missing numstats")
        values = [jcol, jcgcols]
        if threshold is None:
            threshold = SQL("threshold IS NULL")
        else:
            values.append(threshold)
            threshold = SQL("threshold = %s")
        selecter = SQL("SELECT stat, value, constraint_values FROM {0} WHERE cols = %s AND constraint_cols = %s AND {1}")
        selecter = selecter.format(Identifier(self.stats), threshold)
        nstats = defaultdict(dict)
        if onegroup:
            _make_tuple = lambda x: make_tuple(x)[0]
        else:
            _make_tuple = make_tuple
        for rec in db._execute(selecter, values):
            stat, val, cgvals = rec
            if stat == 'ntotal':
                continue
            if constraint is None:
                gvals = _make_tuple(cgvals)
            else:
                gvals = []
                for c, v in zip(jcgcols.adapted, cgvals):
                    if c in constraint:
                        if constraint[c] != v:
                            gvals = None
                            break
                    else:
                        gvals.append(v)
                if gvals is None:
                    # Doesn't satisfy constraint, so skip to next row
                    continue
                gvals = _make_tuple(gvals)
            nstats[gvals][stat] = val
        return nstats

    def _process_constraint(self, cols, constraint):
        """
        INPUT:

        - ``cols`` -- a list of columns
        - ``constraint`` -- a dictionary or a pair of lists (the result of calling _split_dict on a dict)

        OUTPUT:

        - ``where`` -- the where clause for a query
        - ``values`` -- a list of values for input into the _execute statement.
        - ``constraint`` -- the constraint dictionary
        - ``ccols`` -- a Json object holding the constraint columns
        - ``cvals`` -- a Json object holding the constraint values
        - ``allcols`` -- a sorted list of all columns in cols or constraint
        """
        where = [SQL("{0} IS NOT NULL").format(Identifier(col)) for col in cols]
        values, ccols, cvals = [], Json([]), Json([])
        if constraint is None or constraint == (None, None):
            allcols = cols
            constraint = None
        else:
            if isinstance(constraint, tuple):
                # reconstruct constraint from ccols and cvals
                ccols, cvals = constraint
                constraint = self._join_dict(ccols, cvals)
                ccols, cvals = Json(ccols), Json(cvals)
            else:
                ccols, cvals = self._split_dict(constraint)
            # We need to include the constraints in the count table if we're not grouping by that column
            allcols = sorted(list(set(cols + constraint.keys())))
            if any(key.startswith('$') for key in constraint.keys()):
                raise ValueError("Top level special keys not allowed")
            qstr, values = self.table._parse_dict(constraint)
            if qstr is not None:
                where.append(qstr)
        if allcols:
            where = SQL(" WHERE {0}").format(SQL(" AND ").join(where))
        else:
            where = SQL("")
        return where, values, constraint, ccols, cvals, allcols

    def _compute_stats(self, cols, where, values, constraint=None, threshold=None, split_list=False, suffix='', silent=False):
        """
        Computes statistics on a set of columns, subject to a given constraint.

        This function is used by add_stats to compute the statistics to add.

        INPUT:

        - ``cols`` -- as for ``add_stats``, but must be sorted
        - ``where`` -- as output by ``_process_constraint``
        - ``values`` -- as output by ``_process_constraint``
        - ``constraint`` -- as output by ``_process_constraint``
        - ``threshold`` -- as for ``add_stats``
        - ``split_list`` -- as for ``add_stats``
        - ``suffix`` -- as for ``add_stats``
        - ``silent`` -- whether to print an info message to the logger.

        OUTPUT:

        A cursor yielding n+1 tuples, the first n being the values taken on by ``cols``,
        and the last the count of rows with those values.
        """
        if not silent:
            self._print_statmsg(cols, constraint, threshold, split_list=split_list)
        having = SQL("")
        if threshold is not None:
            having = SQL(" HAVING COUNT(*) >= {0}").format(Literal(threshold))
        if cols:
            vars = SQL(", ").join(map(Identifier, cols))
            groupby = SQL(" GROUP BY {0}").format(vars)
            vars = SQL("{0}, COUNT(*)").format(vars)
        else:
            vars = SQL("COUNT(*)")
            groupby = SQL("")
        selecter = SQL("SELECT {vars} FROM {table}{where}{groupby}{having}").format(vars=vars, table=Identifier(self.search_table + suffix), groupby=groupby, where=where, having=having)
        return self._execute(selecter, values)

    def add_stats(self, cols, constraint=None, threshold=None, split_list=False, suffix='', commit=True):
        """
        Add statistics on counts, average, min and max values for a given set of columns.

        INPUT:

        - ``cols`` -- a list of columns, usually of length 1 or 2.
        - ``constraint`` -- only rows satisfying this constraint will be considered.
            It should take the form of a dictionary of the form used in search queries.
            Alternatively, you can provide a pair ccols, cvals giving the items in the dictionary.
        - ``threshold`` -- an integer or None.
        - ``split_list`` -- if True, then counts each element of lists separately.  For example,
            if the list [2,4,8] occurred as the value for a certain column,
            the counts for 2, 4 and 8 would each be incremented.  Constraint columns are not split.
            This option is not supported for nontrivial thresholds.
        - ``suffix`` -- if given, the counts will be performed on the table with the suffix appended.
        - ``commit`` -- if false, the results will not be committed to the database.

        OUTPUT:

        Counts for each distinct tuple of values will be stored,
        as long as the number of rows sharing that tuple is above
        the given threshold.  If there is only one column and it is numeric,
        average, min, and max will be computed as well.

        Returns a boolean: whether any counts were stored.
        """
        if split_list and threshold is not None:
            raise ValueError("split_list and threshold not simultaneously supported")
        where, values, constraint, ccols, cvals, allcols = self._process_constraint(cols, constraint)
        if self._has_stats(Json(cols), ccols, cvals, threshold, split_list):
            self.logger.info("Statistics already exist")
            return
        cols = sorted(cols)
        now = time.time()
        seen_one = False
        if split_list:
            to_add = defaultdict(int)
            allcols = tuple(allcols)
        else:
            to_add = []
            jallcols = Json(allcols)
        total = 0
        onenumeric = False # whether we're grouping by a single numeric column
        if (len(cols) == 1 and self.table.col_type.get(cols[0]) in
            ["numeric", "bigint", "integer", "smallint", "double precision"]):
            onenumeric = True
            avg = 0
            mn = None
            mx = None
        with DelayCommit(self, commit, silence=True):
            cur = self._compute_stats(cols, where, values, constraint, threshold, split_list, suffix)
            for countvec in cur:
                seen_one = True
                colvals, count = countvec[:-1], countvec[-1]
                if constraint is None:
                    allcolvals = colvals
                else:
                    allcolvals = []
                    i = 0
                    for col in allcols:
                        if col in cols:
                            allcolvals.append(colvals[i])
                            i += 1
                        else:
                            allcolvals.append(constraint[col])
                if split_list:
                    listed = [(x if isinstance(x, list) else list(x)) for x in allcolvals]
                    for vals in cartesian_product_iterator(listed):
                        total += count
                        to_add[(allcols, vals)] += count
                else:
                    to_add.append((jallcols, Json(allcolvals), count, False, False))
                    total += count
                if onenumeric:
                    val = colvals[0]
                    avg += val * count
                    if mn is None or val < mn:
                        mn = val
                    if mx is None or val > mx:
                        mx = val


            if not seen_one:
                self.logger.info("No rows exceeded the threshold; returning after %.3f secs" % (time.time() - now))
                return False
            jcols = Json(cols)
            if split_list:
                stats = [(jcols, "split_total", total, ccols, cvals, threshold)]
            else:
                stats = [(jcols, "total", total, ccols, cvals, threshold)]
            if onenumeric and total != 0:
                avg = float(avg) / total
                stats.append((jcols, "avg", avg, ccols, cvals, threshold))
                stats.append((jcols, "min", mn, ccols, cvals, threshold))
                stats.append((jcols, "max", mx, ccols, cvals, threshold))


            # Note that the cols in the stats table does not add the constraint columns, while in the counts table it does.
            inserter = SQL("INSERT INTO {0} (cols, stat, value, constraint_cols, constraint_values, threshold) VALUES %s")
            self._execute(inserter.format(Identifier(self.stats + suffix)), stats, values_list=True)
            inserter = SQL("INSERT INTO {0} (cols, values, count, split, extra) VALUES %s")
            if split_list:
                to_add = [(Json(c), Json(v), ct, True, False) for ((c, v), ct) in to_add.items()]
            self._execute(inserter.format(Identifier(self.counts + suffix)), to_add, values_list=True)
            if len(to_add) > 10000:
                logging.warning(
                        "{:d} rows were just inserted to".format(len(to_add)) +
                        " into {}, ".format(self.counts + suffix) +
                        "all with with cols = {}. ".format(jallcols) +
                        "This might decrease the counts table performance " +
                        "significantly! Consider clearing all the stats " +
                        "db.{}.stats._clear_stats_counts()".format(self.search_table) +
                        " and rebuilding the stats more carefully."
                        )
        self.logger.info("Added stats in %.3f secs"%(time.time() - now))
        return True

    def _approx_most_common(self, col, n):
        """
        Returns the n most common values for ``col``.  Counts are only approximate,
        but this functions should be quite fast.  Note that the returned list
        may have length less than ``n`` if there are not many common values.

        Returns a list of pairs ``(value, count)`` where ``count`` is
        the number of rows where ``col`` takes on the value ``value``.

        INPUT:

        - ``col`` -- a
        """
        if col not in self.table._search_cols:
            raise ValueError("Column %s not a search column for %s"%(col, self.search_table))
        selecter = SQL("""SELECT v.{0}, (c.reltuples * freq)::int as estimate_ct
FROM pg_stats s
CROSS JOIN LATERAL
   unnest(s.most_common_vals::text::""" + self.table.col_type[col] + """[]
        , s.most_common_freqs) WITH ORDINALITY v ({0}, freq, ord)
CROSS  JOIN (
   SELECT reltuples FROM pg_class
   WHERE oid = regclass 'public.nf_fields') c
WHERE schemaname = 'public' AND tablename = %s AND attname = %s
ORDER BY v.ord LIMIT %s""").format(Identifier(col))
        cur = self._execute(selecter, [self.search_table, col, n])
        return [tuple(x) for x in cur]

    def _common_cols(self, threshold=700):
        """
        Returns a list of columns where the most common value has a count of at least the given threshold.
        """
        common_cols = []
        for col in self.table._search_cols:
            most_common = self._approx_most_common(col, 1)
            if most_common and most_common[0][1] >= threshold:
                common_cols.append(col)
        return common_cols

    def _clear_stats_counts(self, extra=True):
        """
        Deletes all stats and counts.  This cannot be undone.

        INPUT:

        - ``extra`` -- if false, only delete the rows of the counts table not marked as extra.
        """
        deleter = SQL("DELETE FROM {0}")
        self._execute(deleter.format(Identifier(self.stats)))
        if not extra:
            deleter = SQL("DELETE FROM {0} WHERE extra IS NOT TRUE") # false and null
        self._execute(deleter.format(Identifier(self.counts)))

    def add_stats_auto(self, cols=None, constraints=[None], max_depth=None, threshold=1000):
        """
        Searches for combinations of columns with many rows having the same set of values.

        The main application is determining which indexes might be useful to add.

        INPUT:

        - ``cols`` -- a set of columns.  If not provided, columns where the most common value has at least 700 rows will be used.
        - ``constraints`` -- a list of constraints.  Statistics will be added for each set of constraints.
        - ``max_depth`` -- the maximum number of columns to include
        - ``threshold`` -- only counts above this value will be included.
        """
        with DelayCommit(self, silence=True):
            if cols is None:
                cols = self._common_cols()
            for constraint in constraints:
                ccols, cvals = self._split_dict(constraint)
                level = 0
                curlevel = [([],None)]
                while curlevel:
                    i = 0
                    logging.info("Starting level %s/%s (%s/%s colvecs)"%(level, len(cols), len(curlevel), binomial(len(cols), level)))
                    while i < len(curlevel):
                        colvec, _ = curlevel[i]
                        if self._has_stats(Json(cols), ccols, cvals, threshold=threshold, threshold_inequality=True):
                            i += 1
                            continue
                        added_any = self.add_stats(colvec, constraint=constraint, threshold=threshold)
                        if added_any:
                            i += 1
                        else:
                            curlevel.pop(i)
                    if max_depth is not None and level >= max_depth:
                        break
                    prevlevel = curlevel
                    curlevel = []
                    for colvec, m in prevlevel:
                        if m is None:
                            for j, col in enumerate(cols):
                                if not isinstance(col, list):
                                    col = [col]
                                curlevel.append((col, j))
                        else:
                            for j in range(m+1,len(cols)):
                                col = cols[j]
                                if not isinstance(col, list):
                                    col = [col]
                                curlevel.append((colvec + col, j))
                    level += 1

    def _status(self):
        """
        Returns information that can be used to recreate the statistics table.

        OUTPUT:

        - ``stats_cmds`` -- a list of quadruples (cols, ccols, cvals, threshold) for input into add_stats
        - ``split_cmds`` -- a list of quadruples (cols, ccols, cvals, threshold) for input into add_stats with split_list=True
        - ``nstat_cmds`` -- a list of quintuples (col, grouping, ccols, cvals, threshold) for input into add_numstats
        """
        selecter = SQL("SELECT cols, constraint_cols, constraint_values, threshold FROM {0} WHERE stat = %s").format(Identifier(self.stats))
        stat_cmds = list(self._execute(selecter, ["total"]))
        split_cmds = list(self._execute(selecter, ["split_total"]))
        nstat_cmds = []
        for rec in self._execute(selecter, ["ntotal"]):
            cols, cgcols, cvals, threshold = rec
            if cvals is None:
                grouping = cgcols
                ccols = []
                cvals = []
            else:
                grouping = cgcols[len(cvals):]
                ccols = cgcols[:len(cvals)]
            nstat_cmds.append((cols[0], grouping, ccols, cvals, threshold))
        return stat_cmds, split_cmds, nstat_cmds

    def refresh_stats(self, total=True, suffix=''):
        """
        Regenerate stats and counts, using rows with ``stat = "total"`` in the stats
        table to determine which stats to recompute, and the rows with ``extra = True``
        in the counts table which have been added by user searches.

        INPUT:

        - ``total`` -- if False, doesn't update the total count (since we can often
            update the total cheaply)
        - ``suffix`` -- appended to the table name when computing and storing stats.
            Used when reloading a table.
        """
        with DelayCommit(self, silence=True):
            # Determine the stats and counts currently recorded
            stat_cmds, split_cmds, nstat_cmds = self._status()
            col_value_dict = self.extra_counts(include_counts=False, suffix=suffix)

            # Delete all stats and counts
            deleter = SQL("DELETE FROM {0}")
            self._execute(deleter.format(Identifier(self.stats + suffix)))
            self._execute(deleter.format(Identifier(self.counts + suffix)))

            # Regenerate stats and counts
            for cols, ccols, cvals, threshold in stat_cmds:
                self.add_stats(cols, (ccols, cvals), threshold)
            for cols, ccols, cvals, threshold in split_cmds:
                self.add_stats(cols, (ccols, cvals), threshold, split_list=True)
            for col, grouping, ccols, cvals, threshold in nstat_cmds:
                self.add_numstats(col, grouping, (ccols, cvals), threshold)
            self._add_extra_counts(col_value_dict, suffix=suffix)

            if total:
                # Refresh total in meta_tables
                self.total = self._slow_count({}, suffix=suffix, extra=False)

    def status(self):
        """
        Prints a status report on the statistics for this table.
        """
        stat_cmds, split_cmds, nstat_cmds = self._status()
        col_value_dict = self.extra_counts(include_counts=False)
        have_stats = stat_cmds or split_cmds or nstat_cmds
        if have_stats:
            for cols, ccols, cvals, threshold in stat_cmds:
                print "  ",
                self._print_statmsg(cols, (ccols, cvals), threshold, tense='past')
            for cols, ccols, cvals, threshold in split_cmds:
                print "  ",
                self._print_statmsg(cols, (ccols, cvals), threshold, split_list=True, tense='past')
            for col, grouping, ccols, cvals, threshold in nstat_cmds:
                print "  ",
                self._print_statmsg([col], (ccols, cvals), threshold, grouping=grouping, tense='past')
            selecter = SQL("SELECT COUNT(*) FROM {0} WHERE extra = %s").format(Identifier(self.counts))
            count_nrows = self._execute(selecter, [False]).fetchone()[0]
            selecter = SQL("SELECT COUNT(*) FROM {0}").format(Identifier(self.stats))
            stats_nrows = self._execute(selecter).fetchone()[0]
            msg = "hese statistics take up %s rows in the stats table and %s rows in the counts table." % (stats_nrows, count_nrows)
            if len(stat_cmds) + len(split_cmds) + len(nstat_cmds) == 1:
                print "T" + msg
            else:
                print "Altogether, t" + msg
        else:
            print "No statistics have been computed for this table."
        if col_value_dict:
            if have_stats:
                print "In addition to the statistics described above, additional counts are recorded",
            else:
                print "The following counts are being stored",
            print " (we collect all counts referring to the same columns):"
            for cols, values in col_value_dict.items():
                print "  (%s): %s row%s in counts table" % (", ".join(cols), len(values), '' if len(values) == 1 else 's')
        else:
            if have_stats:
                print "No additional counts are stored."
            else:
                print "No counts are stored for this table."

    def _copy_extra_counts_to_tmp(self):
        """
        Generates the extra counts in the ``_tmp`` table using the
        extra counts that currently exist in the main table.
        """
        col_value_dict = self.extra_counts(include_counts=False)
        self._add_extra_counts(col_value_dict, suffix='_tmp')

    def _add_extra_counts(self, col_value_dict, suffix=''):
        """
        Records the counts requested in the col_value_dict.

        INPUT:

        - ``col_value_dict`` -- a dictionary giving queries to be counted,
            as output by the ``extra_counts`` function.
        - ``suffix`` -- A suffix (e.g. ``_tmp``) specifying where to
            perform and record the counts
        """
        for cols, values_list in col_value_dict.items():
            for values in values_list:
                query = self._join_dict(cols, values)
                if self.quick_count(query, suffix=suffix) is None:
                    self._slow_count(query, record=True, suffix=suffix)

    def extra_counts(self, include_counts=True, suffix=''):
        """
        Returns a dictionary of the extra counts that have been added by explicit ``count`` calls
        that were not included in counts generated by ``add_stats``.

        The keys are tuples giving the columns being counted, the values are lists of pairs,
        where the first entry is the tuple of values and the second is the count of rows
        with those values.  Note that sometimes the values could be dictionaries
        giving more complicated search queries on the corresponding columns.

        INPUT:

        - ``include_counts`` -- if False, will omit the counts and just give lists of values.
        - ``suffix`` -- Used when dealing with `_tmp` or `_old*` tables.
        """
        selecter = SQL("SELECT cols, values, count FROM {0} WHERE extra ='t'").format(Identifier(self.counts + suffix))
        cur = self._execute(selecter)
        ans = defaultdict(list)
        for cols, values, count in cur:
            if include_counts:
                ans[tuple(cols)].append((tuple(values), count))
            else:
                ans[tuple(cols)].append(tuple(values))

        return ans

    def _get_values_counts(self, cols, constraint, split_list, formatter, query_formatter, base_url, buckets=None):
        """
        Utility function used in ``display_data``, used to generate data for stats tables.

        Returns a list of pairs (value, count), where value is a list of values taken on by the specified
        columns and count is an integer giving the number of rows with those values.

        If the relevant statistics are not available, it will compute and insert them.

        INPUT:

        - ``cols`` -- a list of column names that are stored in the counts table.
        - ``constraint`` -- a dictionary specifying a constraint on rows to consider.
        - ``split_list`` -- see ``add_stats``.
        - ``formatter`` -- a dictionary whose keys are column names and whose values are functions that take a value of that column as input and return a string for display
        - ``query_formatter`` -- a dictionary whose keys are column names and whose values are functions that take a value of that column as input and return a string for inclusion in a url argument list
        - ``base_url`` -- the initial part of the url, including the '?' (and possibly some universal arguments)
        - ``buckets`` -- a dictionary with column names and keys and lists of strings as values.  See ``_bucket_iterator`` for more details

        OUTPUT:

        - ``header`` -- a list of lists giving the values to print along the top or side of the table
        - ``data`` -- a dictionary with data on counts
        """
        selecter_constraints = [SQL("split = %s"), SQL("cols = %s")]
        if constraint:
            allcols = sorted(list(set(cols + constraint.keys())))
            selecter_values = [split_list, Json(allcols)]
            for i, x in enumerate(allcols):
                if x in constraint:
                    selecter_constraints.append(SQL("values->{0} = %s".format(i)))
                    selecter_values.append(Json(constraint[x]))
        else:
            allcols = sorted(cols)
            selecter_values = [split_list, Json(allcols)]
        positions = [allcols.index(x) for x in cols]
        selecter = SQL("SELECT values, count FROM {0} WHERE {1}").format(Identifier(self.counts), SQL(" AND ").join(selecter_constraints))
        headers = [[] for _ in cols]
        default_proportion = '      0.00%' if len(cols) == 1 else ''
        def make_count_dict(values, cnt):
            if isinstance(values, (list, tuple)):
                query = base_url + '&'.join(query_formatter[col](val) for col, val in zip(cols, values))
            else:
                query = base_url + query_formatter[cols[0]](values)
            return {'count': cnt,
                    'query': query,
                    'proportion': default_proportion, # will be overridden for nonzero cnts.
            }
        data = KeyedDefaultDict(lambda key: make_count_dict(key, 0))
        if buckets:
            buckets_seen = set()
            bucket_positions = [i for (i, col) in enumerate(cols) if col in buckets]
        for values, count in self._execute(selecter, values=selecter_values):
            values = [values[i] for i in positions]
            for val, header in zip(values, headers):
                header.append(val)
            D = make_count_dict(values, count)
            if len(cols) == 1:
                values = formatter[cols[0]](values[0])
                if buckets:
                    buckets_seen.add((values,))
            else:
                values = tuple(formatter[col](val) for col, val in zip(cols, values))
                if buckets:
                    buckets_seen.add(tuple(values[i] for i in bucket_positions))
            data[values] = D
        # Ensure that we have all the statistics necessary
        ok = True
        if buckets == {}:
            # Just check that the results are nonempty
            if not data:
                self.add_stats(cols, constraint, split_list=split_list)
                ok = False
        elif buckets:
            # Make sure that every bucket is hit in data
            bcols = [col for col in cols if col in buckets]
            ucols = [col for col in cols if col not in buckets]
            for bucketed_constraint in self._bucket_iterator(buckets, constraint):
                cseen = tuple(formatter[col](bucketed_constraint[col]) for col in bcols)
                if cseen not in buckets_seen:
                    logging.info("Adding statistics for %s with constraints %s" % (", ".join(cols), ", ".join("%s:%s" % (cc, cv) for cc, cv in bucketed_constraint.items())))
                    self.add_stats(ucols, bucketed_constraint)
                    ok = False
        if not ok:
            # Set buckets=False so we have no chance of infinite recursion
            return self._get_values_counts(cols, constraint, split_list, formatter, query_formatter, base_url, buckets=False)
        if len(cols) == 1:
            return headers[0], data
        else:
            return headers, data

    def _get_total_avg(self, cols, constraint, avg, split_list):
        """
        Utility function used in ``display_data``.

        Returns the total number of rows and average value for the column, subject to the given constraint.

        INPUT:

        - ``cols`` -- a list of columns
        - ``constraint`` -- a dictionary specifying a constraint on rows to consider
        - ``avg`` -- boolean, whether to compute the average
        - ``split_list`` -- see the ``add_stats`` method

        OUTPUT:

        - the total number of rows satisying the constraint
        - the average value of the given column (only possible if cols has length 1),
          or None if the average not requested
        """
        jcols = Json(cols)
        total_str = "split_total" if split_list else "total"
        totaler = SQL("SELECT value FROM {0} WHERE cols = %s AND stat = %s AND threshold IS NULL").format(Identifier(self.stats))
        ccols, cvals = self._split_dict(constraint)
        totaler = SQL("{0} AND constraint_cols = %s AND constraint_values = %s").format(totaler)
        totaler_values = [jcols, total_str, ccols, cvals]
        cur_total = self._execute(totaler, values=totaler_values)
        if cur_total.rowcount == 0:
            raise ValueError("Database does not contain stats for %s"%(cols[0],))
        total = cur_total.fetchone()[0]
        if avg:
            # Modify totaler_values in place since query for avg is very similar
            totaler_values[1] = "avg"
            cur_avg = self._execute(totaler, values=totaler_values)
            avg = cur_avg.fetchone()[0]
        else:
            avg = False
        return total, avg

    def create_oldstats(self, filename):
        """
        Temporary support for statistics created in Mongo.
        """
        name = self.search_table + "_oldstats"
        with DelayCommit(self, silence=True):
            creator = SQL('CREATE TABLE {0} (_id text COLLATE "C", data jsonb)').format(Identifier(name))
            self._execute(creator)
            self._db.grant_select(name)
            cur = self._db.cursor()
            with open(filename) as F:
                try:
                    cur.copy_from(F, self.search_table + "_oldstats")
                except Exception:
                    self.conn.rollback()
                    raise
        print "Oldstats created successfully"

    def get_oldstat(self, name):
        """
        Temporary suppport for statistics created in Mongo.
        """
        selecter = SQL("SELECT data FROM {0} WHERE _id = %s").format(Identifier(self.search_table + "_oldstats"))
        cur = self._execute(selecter, [name])
        if cur.rowcount != 1:
            raise ValueError("Not a unique oldstat identifier")
        return cur.fetchone()[0]

class ExtendedTable(PostgresTable):
    """
    This class supports type conversion when extracting data from the database.

    It's use is currently hardcoded for artin_reps and artin_field_data,
    but could eventually be specified by columns in meta_tables.
    """
    def __init__(self, type_conversion, *args, **kwds):
        self._type_conversion = type_conversion
        PostgresTable.__init__(self, *args, **kwds)
    def _search_and_convert_iterator(self, source):
        for x in source:
            yield self._type_conversion(x)
    def search_and_convert(self, query={}, projection=1, limit=None, offset=0, sort=None, info=None):
        results = self.search(query, projection, limit=limit, offset=offset, sort=sort, info=info)
        if limit is None:
            return self._search_and_convert_iterator(results)
        else:
            return [self._type_conversion(x) for x in results]
    def convert_lucky(self, *args, **kwds):
        result = self.lucky(*args, **kwds)
        if result:
            return self._type_conversion(result)

class PostgresDatabase(PostgresBase):
    """
    The interface to the postgres database.

    It creates and stores the global connection object,
    and collects the table interfaces.

    INPUT:

    - ``tables`` -- the information needed to construct the table interfaces.
      Namely, a list, each entry of which is either a string (the name of the search table)
      or a tuple which is passed on to the PostgresTable constructor.

    EXAMPLES::

        sage: from lmfdb import db
        sage: db
        Interface to Postgres database
        sage: db.conn
        <connection object at 0x...>
        sage: db.tablenames[:3]
        ['artin_field_data', 'artin_reps', 'av_fqisog']
        sage: db.av_fqisog
        Interface to Postgres table av_fqisog
    """
    def _new_connection(self, **kwargs):
        from lmfdb.utils.config import Configuration
        options = Configuration().get_postgresql()
        # overrides the options passed as keyword arguments
        for key, value in kwargs.iteritems():
            options[key] = value
        self.fetch_userpassword(options)
        self._user = options['user']
        logging.info("Connecting to PostgresSQL server as: user=%s host=%s port=%s dbname=%s..." % (options['user'],options['host'], options['port'], options['dbname'],))
        connection = connect( **options)
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
        logging.info("Connection broken (status %s); resetting...",
                     self.conn.closed)
        conn = self._new_connection()
        # Note that self is the first entry in self._objects
        for obj in self._objects:
            obj.conn = conn

    def register_object(self, obj):
        obj.conn = self.conn
        self._objects.append(obj)

    def __init__(self, **kwargs):
        self.server_side_counter = 0
        self._nocommit_stack = 0
        self._silenced = False
        self._objects = []
        self.conn = self._new_connection(**kwargs)
        PostgresBase.__init__(self, 'db_all', self)
        if self._user == "webserver":
            self._execute(SQL("SET SESSION statement_timeout = '25s'"))

        self._read_only = self._execute(SQL("SELECT pg_is_in_recovery()")).fetchone()[0]
        self._super_user = self._execute(SQL("SELECT current_setting('is_superuser')")).fetchone()[0] == 'on'

        if self._read_only:
            self._read_and_write_knowls = False
            self._read_and_write_userdb = False
        elif self._super_user and not self._read_only:
            self._read_and_write_knowls = True
            self._read_and_write_userdb = True
        else:
            privileges = ['INSERT', 'SELECT', 'UPDATE', 'DELETE']
            knowls_tables = ['kwl_deleted', 'kwl_history', 'kwl_knowls']
            cur = sorted(list(self._execute(SQL("SELECT table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee = %s AND table_name IN (" + ",".join(['%s']*len(knowls_tables)) + ") AND privilege_type IN (" + ",".join(['%s']*len(privileges)) + ")"), [self._user] +  knowls_tables + privileges)))
            self._read_and_write_knowls = cur == sorted([(table, priv) for table in knowls_tables for priv in privileges])

            cur = sorted(list(self._execute(SQL("SELECT privilege_type FROM information_schema.role_table_grants WHERE grantee = %s AND table_schema = %s AND table_name=%s AND privilege_type IN (" + ",".join(['%s']*len(privileges)) + ")"), [self._user,  'userdb', 'users'] + privileges)))
            self._read_and_write_userdb = cur == sorted([(priv,) for priv in privileges])

        logging.info("User: %s", self._user)
        logging.info("Read only: %s", self._read_only)
        logging.info("Super user: %s", self._super_user)
        logging.info("Read/write to userdb: %s", self._read_and_write_userdb)
        logging.info("Read/write to knowls: %s", self._read_and_write_knowls)
        # Stores the name of the person making changes to the database
        from lmfdb.utils.config import Configuration
        self.__editor = Configuration().get_logging().get('editor')


        cur = self._execute(SQL('SELECT table_name, column_name, udt_name::regtype FROM information_schema.columns'))
        data_types = {}
        for table_name, column_name, regtype in cur:
            if table_name not in data_types:
                 data_types[table_name] = []
            data_types[table_name].append((column_name, regtype))

        cur = self._execute(SQL("SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, has_extras, stats_valid, total FROM meta_tables"))
        self.tablenames = []
        for tabledata in cur:
            tablename = tabledata[0]
            tabledata += (data_types,)
            # it would be nice to include this in meta_tables
            if tablename == 'artin_reps':
                table = ExtendedTable(Dokchitser_ArtinRepresentation, self, *tabledata)
            elif tablename == 'artin_field_data':
                table = ExtendedTable(Dokchitser_NumberFieldGaloisGroup, self, *tabledata)
            else:
                table = PostgresTable(self, *tabledata)
            self.__dict__[tablename] = table
            self.tablenames.append(tablename)
        self.tablenames.sort()
        self.is_verifying = False # set to true when importing lmfdb.verify

    def __repr__(self):
        return "Interface to Postgres database"


    def cursor(self, buffered=False):
        """
        Returns a new cursor.
        If buffered, then it creates a server side cursor that must be manually
        closed after done using it.
        """
        if buffered:
            self.server_side_counter += 1
            return self.conn.cursor(str(self.server_side_counter), withhold=True)
        else:
            return self.conn.cursor()


    def login(self):
        """
        Identify an editor by their lmfdb username.

        The goal is to associate changes with people and keep a record of changes made.
        There is no real security against malicious use.

        Note that you can permanently log in by setting the editor
        field in the logging section of your config.ini file.
        """
        if self.__editor is None:
            print "Please provide your knowl username,"
            print "so that we can associate database changes with individuals."
            print "Note that you can also do this by setting the editor field in the logging section of your config.ini file."
            uid = raw_input("Username: ")
            selecter = SQL("SELECT username FROM userdb.users WHERE username = %s")
            cur = self._execute(selecter, [uid])
            if cur.rowcount == 0:
                raise ValueError("That username not present in database!")
            self.__editor = uid
        return self.__editor

    def log_db_change(self, operation, tablename=None, **data):
        """
        Log a change to the database.
        """
        uid = self.login()
        inserter = SQL("INSERT INTO userdb.dbrecord (username, time, tablename, operation, data) VALUES (%s, %s, %s, %s, %s)")
        self._execute(inserter, [uid, datetime.datetime.utcnow(), tablename, operation, data])

    def fetch_userpassword(self, options):
        if 'user' not in options:
            options['user'] = 'lmfdb'

        if options['user'] == 'webserver':
            logging.info("Fetching webserver password...")
            # tries to read the file "password" on root of the project
            pw_filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), "../password")
            try:
                options['password'] = open(pw_filename, "r").readlines()[0].strip()
                logging.info("Done!")
            except Exception:
                # file not found or any other problem
                # this is read-only everywhere
                logging.warning("PostgresSQL authentication: no webserver password on {0} -- fallback to read-only access".format(pw_filename))
                options['user'], options['password'] = 'lmfdb', 'lmfdb'

        elif 'password' not in options:
            options['user'], options['password'] = 'lmfdb', 'lmfdb'

    def _grant(self, action, table_name, users):
        action = action.upper()
        if action not in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            raise ValueError("%s is not a valid action"%action)
        grantor = SQL('GRANT %s ON TABLE {0} TO {1}'%action)
        for user in users:
            self._execute(grantor.format(Identifier(table_name), Identifier(user)), silent=True)

    def grant_select(self, table_name, users=['lmfdb', 'webserver']):
        self._grant("SELECT", table_name, users)

    def grant_insert(self, table_name, users=['webserver']):
        self._grant("INSERT", table_name, users)

    def grant_update(self, table_name, users=['webserver']):
        self._grant("UPDATE", table_name, users)

    def grant_delete(self, table_name, users=['webserver']):
        self._grant("DELETE", table_name, users)

    def is_read_only(self):
        return self._read_only

    def can_read_write_knowls(self):
        return self._read_and_write_knowls

    def can_read_write_userdb(self):
        return self._read_and_write_userdb

    def is_alive(self):
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
        if name in self.tablenames:
            return getattr(self, name)
        else:
            raise ValueError("%s is not a search table"%name)

    def table_sizes(self):
        """
        Returns a dictionary containing information on the sizes of the search tables.

        OUTPUT:

        A dictionary with a row for each search table
        (as well as a few others such as kwl_knowls), with entries

        - ``nrows`` -- an estimate for the number of rows in the table
        - ``nstats`` -- an estimate for the number of rows in the stats table
        - ``ncounts`` -- an estimate for the number of rows in the counts table
        - ``total_bytes`` -- the total number of bytes used by the main table, as well as stats, counts, extras, indexes, ancillary storage....
        - ``index_bytes`` -- the number of bytes used for indexes on the main table
        - ``toast_bytes`` -- the number of bytes used for storage of variable length data types, such as strings and jsonb
        - ``table_bytes`` -- the number of bytes used for fixed length storage on the main table
        - ``extra_bytes`` -- the number of bytes used by the extras table (including the index on id, toast, etc)
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
        cur = db._execute(SQL(query))
        for table_name, row_estimate, total_bytes, index_bytes, toast_bytes, table_bytes in cur:
            if table_name.endswith('_stats'):
                name = table_name[:-6]
                sizes[name]['nstats'] = int(row_estimate)
                sizes[name]['stats_bytes'] = total_bytes
            elif table_name.endswith('_counts'):
                name = table_name[:-7]
                sizes[name]['ncounts'] = int(row_estimate)
                sizes[name]['counts_bytes'] = total_bytes
            elif table_name.endswith('_extras'):
                name = table_name[:-7]
                sizes[name]['extras_bytes'] = total_bytes
            else:
                name = table_name
                sizes[name]['nrows'] = int(row_estimate)
                # use the cached account for an accurate count
                if name in self.tablenames:
                    row_cached = db[name].stats.quick_count({})
                    if row_cached is not None:
                        sizes[name]['nrows'] = row_cached
                sizes[name]['index_bytes'] = index_bytes
                sizes[name]['toast_bytes'] = toast_bytes
                sizes[name]['table_bytes'] = table_bytes
            sizes[name]['total_bytes'] += total_bytes
        return sizes

    def _create_meta_indexes_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL("CREATE TABLE meta_indexes_hist (index_name text, table_name text, type text, columns jsonb, modifiers jsonb, storage_params jsonb, version integer)"))
            version = 0

            # copy data from meta_indexes
            rows = self._execute(SQL("SELECT index_name, table_name, type, columns, modifiers, storage_params FROM meta_indexes"))

            for row in rows:
                self._execute(SQL("INSERT INTO meta_indexes_hist (index_name, table_name, type, columns, modifiers, storage_params, version) VALUES (%s, %s, %s, %s, %s, %s, %s)"), row + (version,))

            self.grant_select('meta_indexes_hist')

        print("Table meta_indexes_hist created")


    def _create_meta_constraints(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL("CREATE TABLE meta_constraints (constraint_name text, table_name text, type text, columns jsonb, check_func jsonb)"))
            self.grant_select('meta_constraints')
        print("Table meta_constraints created")

    def _create_meta_constraints_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL("CREATE TABLE meta_constraints_hist (constraint_name text, table_name text, type text, columns jsonb, check_func jsonb, version integer)"))
            version = 0

            # copy data from meta_constraints
            rows = self._execute(SQL("SELECT constraint_name, table_name, type, columns, check_func FROM meta_constraints"))

            for row in rows:
                self._execute(SQL("INSERT INTO meta_constraints_hist (constraint_name, table_name, type, columns, check_func, version) VALUES (%s, %s, %s, %s, %s, %s)"), row + (version,))

            self.grant_select('meta_constraints_hist')

        print("Table meta_constraints_hist created")

    def _create_meta_tables_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL("CREATE TABLE meta_tables_hist (name text, sort jsonb, count_cutoff smallint DEFAULT 1000, id_ordered boolean, out_of_order boolean, has_extras boolean, stats_valid boolean DEFAULT true, label_col text, total bigint, version integer)"))
            version = 0

            # copy data from meta_tables
            rows = self._execute(SQL("SELECT name, sort, id_ordered, out_of_order, has_extras, label_col, total FROM meta_tables "))

            for row in rows:
                self._execute(SQL("INSERT INTO meta_tables_hist (name, sort, id_ordered, out_of_order, has_extras, label_col, total, version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"), row + (version,))

            self.grant_select('meta_tables_hist')

        print("Table meta_tables_hist created")

    def create_table_like(self, new_name, table, commit=True):
        """
        Copies the schema from an existing table, but none of the data, indexes or stats.

        INPUT:

        - ``new_name`` -- a string giving the desired table name.
        - ``table`` -- a string or PostgresTable object giving an existing table.
        """
        if isinstance(table, basestring):
            table = self[table]
        search_columns = {typ: [col for col in table._search_cols if table.col_type[col] == typ] for typ in set(table.col_type.values())}
        extra_columns = {typ: [col for col in table._extra_cols if table.col_type[col] == typ] for typ in set(table.col_type.values())}
        # Remove empty lists
        for D in [search_columns, extra_columns]:
            for typ, cols in list(D.items()):
                if not cols:
                    D.pop(typ)
        if not extra_columns:
            extra_columns = extra_order = None
        else:
            extra_order = table._extra_cols
        label_col = table._label_col
        sort = table._sort_orig
        id_ordered = table._id_ordered
        search_order = table._search_cols
        self.create_table(new_name, search_columns, label_col, sort, id_ordered, extra_columns, search_order, extra_order, commit=commit)

    def create_table(self, name, search_columns, label_col, sort=None, id_ordered=None, extra_columns=None, search_order=None, extra_order=None, commit=True):
        """
        Add a new search table to the database.  See also `create_table_like`.

        INPUT:

        - ``name`` -- the name of the table, which must include an underscore.  See existing names for consistency.
        - ``search_columns`` -- a dictionary whose keys are valid postgres types and whose values
            are lists of column names (or just a string if only one column has the specified type).
            An id column of type bigint will be added as a primary key (do not include it).
        - ``label_col`` -- the column holding the LMFDB label.  This will be used in the ``lookup`` method
            and in the display of results on the API.  Use None if there is no appropriate column.
        - ``sort`` -- If not None, provides a default sort order for the table, in formats accepted by
            the ``_sort_str`` method.
        - ``id_ordered`` -- boolean (default None).  If set, the table will be sorted by id when
            pushed to production, speeding up some kinds of search queries.  Defaults to True
            when sort is not None.
        - ``extra_columns`` -- a dictionary in the same format as the search_columns dictionary.
            If present, will create a second table (the name with "_extras" appended), linked by
            an id column.  Data in this table cannot be searched on, but will also not appear
            in the search table, speeding up scans.
        - ``search_order`` -- (optional) list of column names, specifying the default order of columns
        - ``extra_order`` -- (optional) list of column names, specifying the default order of columns

        COMMON TYPES:

        The postgres types most commonly used in the lmfdb are:

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
            raise ValueError("%s already exists"%name)
        if '_' not in name:
            raise ValueError("Table name must contain an underscore; first part gives LMFDB section")
        now = time.time()
        if id_ordered is None:
            id_ordered = (sort is not None)
        for typ, L in search_columns.items():
            if isinstance(L, basestring):
                search_columns[typ] = [L]
        valid_list = sum(search_columns.values(),[])
        valid_set = set(valid_list)
        # Check that columns aren't listed twice
        if len(valid_list) != len(valid_set):
            C = Counter(valid_list)
            raise ValueError("Column %s repeated"%(C.most_common(1)[0][0]))
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
                    raise ValueError("Column %s does not exist"%(col))
        # Check that search order is valid
        if search_order is not None:
            for col in search_order:
                if col not in valid_set:
                    raise ValueError("Column %s does not exist"%(col))
            if len(search_order) != len(valid_set):
                raise ValueError("Must include all columns")
        def process_columns(coldict, colorder):
            allcols = {}
            hasid = False
            dictorder = []
            for typ, cols in coldict.items():
                if typ.lower() not in types_whitelist:
                    if not any(regexp.match(typ.lower()) for regexp in param_types_whitelist):
                        raise ValueError("%s is not a valid type"%(typ))
                if isinstance(cols, basestring):
                    cols = [cols]
                for col in cols:
                    if col == 'id':
                        hasid = True
                    # We have whitelisted the types, so it's okay to use string formatting
                    # to insert them into the SQL command.
                    # This is useful so that we can specify the collation in the type
                    allcols[col] = SQL("{0} " + typ).format(Identifier(col))
                    dictorder.append(col)
            allcols = [allcols[col] for col in (dictorder if colorder is None else colorder)]
            if (not hasid):
                allcols.insert(0, SQL("id bigint"))
            return allcols
        processed_search_columns = process_columns(search_columns, search_order)
        with DelayCommit(self, commit, silence=True):
            creator = SQL('CREATE TABLE {0} ({1})').format(Identifier(name), SQL(", ").join(processed_search_columns))
            self._execute(creator)
            self.grant_select(name)
            if extra_columns is not None:
                valid_extra_list = sum(extra_columns.values(),[])
                valid_extra_set = set(valid_extra_list)
                # Check that columns aren't listed twice
                if len(valid_extra_list) != len(valid_extra_set):
                    C = Counter(valid_extra_list)
                    raise ValueError("Column %s repeated"%(C.most_common(1)[0][0]))
                if extra_order is not None:
                    for col in extra_order:
                        if col not in valid_extra_set:
                            raise ValueError("Column %s does not exist"%(col))
                    if len(extra_order) != len(valid_extra_set):
                        raise ValueError("Must include all columns")
                processed_extra_columns = process_columns(extra_columns, extra_order)
                creator = SQL('CREATE TABLE {0} ({1})')
                creator = creator.format(Identifier(name+"_extras"),
                                         SQL(", ").join(processed_extra_columns))
                self._execute(creator)
                self.grant_select(name+"_extras")
            creator = SQL('CREATE TABLE {0} (cols jsonb, values jsonb, count bigint, extra boolean, split boolean DEFAULT FALSE)')
            creator = creator.format(Identifier(name+"_counts"))
            self._execute(creator)
            self.grant_select(name+"_counts")
            self.grant_insert(name+"_counts")
            creator = SQL('CREATE TABLE {0} (cols jsonb, stat text COLLATE "C", value numeric, constraint_cols jsonb, constraint_values jsonb, threshold integer)')
            creator = creator.format(Identifier(name + "_stats"))
            self._execute(creator)
            self.grant_select(name+"_stats")
            self.grant_insert(name+"_stats")
            # FIXME use global constants ?
            inserter = SQL('INSERT INTO meta_tables (name, sort, id_ordered, out_of_order, has_extras, label_col) VALUES (%s, %s, %s, %s, %s, %s)')
            self._execute(inserter, [name, Json(sort), id_ordered, not id_ordered, extra_columns is not None, label_col])
        self.__dict__[name] = PostgresTable(self, name, label_col, sort=sort, id_ordered=id_ordered, out_of_order=(not id_ordered), has_extras=(extra_columns is not None), total=0)
        self.tablenames.append(name)
        self.tablenames.sort()
        self.log_db_change('create_table', tablename=name, name=name, search_columns=search_columns, label_col=label_col, sort=sort, id_ordered=id_ordered, extra_columns=extra_columns, search_order=search_order, extra_order=extra_order)
        print "Table %s created in %.3f secs"%(name, time.time()-now)

    def drop_table(self, name, commit=True, force=False):
        table = self[name]
        selecter = SQL("SELECT important FROM meta_tables WHERE name=%s")
        if self._execute(selecter, [name]).fetchone()[0]:
            raise ValueError("You cannot drop an important table.  Use the set_importance method on the table if you actually want to drop it.")
        if not force:
            ok = raw_input("Are you sure you want to drop %s? (y/N) "%(name))
            if not (ok and ok[0] in ['y','Y']):
                return
        with DelayCommit(self, commit, silence=True):
            table.cleanup_from_reload()
            indexes = list(self._execute(SQL("SELECT index_name FROM meta_indexes WHERE table_name = %s"), [name]))
            if indexes:
                self._execute(SQL("DELETE FROM meta_indexes WHERE table_name = %s"), [name])
                print "Deleted indexes {0}".format(", ".join(index[0] for index in indexes))
            constraints = list(self._execute(SQL("SELECT constraint_name FROM meta_constraints WHERE table_name = %s"), [name]))
            if constraints:
                self._execute(SQL("DELETE FROM meta_constraints WHERE table_name = %s"), [name])
                print "Deleted constraints {0}".format(", ".join(constraint[0] for constraint in constraints))
            self._execute(SQL("DELETE FROM meta_tables WHERE name = %s"), [name])
            if table.extra_table is not None:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(table.extra_table)))
                print "Dropped {0}".format(table.extra_table)
            for tbl in [name, name + "_counts", name + "_stats"]:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(tbl)))
                print "Dropped {0}".format(tbl)
            self.tablenames.remove(name)
            delattr(self, name)

    def rename_table(self, old_name, new_name, commit=True):
        assert old_name != new_name
        assert new_name not in self.tablenames
        with DelayCommit(self, commit, silence=True):
            table = self[old_name]
            # first rename indexes and constraints
            icols = map(Identifier, ['index_name', 'table_name'])
            ccols = map(Identifier, ['constraint_name', 'table_name'])
            rename_index = SQL("ALTER INDEX IF EXISTS {0} RENAME TO {1}")
            rename_constraint = SQL("ALTER TABLE {0} RENAME CONSTRAINT {1} TO {2}")
            for meta, mname, cols in [
                    ('meta_indexes', 'index_name', icols),
                    ('meta_indexes_hist', 'index_name', icols),
                    ('meta_constraints', 'constraint_name', ccols),
                    ('meta_constraints_hist', 'constraint_name', ccols)]:
                indexes = list(self._execute(SQL("SELECT {0} FROM {1} WHERE table_name = %s").format(Identifier(mname), Identifier(meta)), [old_name]))
                if indexes:
                    rename_index_in_meta = SQL("UPDATE {0} SET ({1}) = ({2}) WHERE {3} = {4}")
                    rename_index_in_meta = rename_index_in_meta.format( Identifier(meta),
                                                                        SQL(", ").join(cols),
                                                                        SQL(", ").join(Placeholder() * len(cols)),
                                                                        cols[0],
                                                                        Placeholder())
                    for old_index_name in indexes:
                        old_index_name = old_index_name[0]
                        new_index_name = old_index_name.replace(old_name, new_name)
                        self._execute(rename_index_in_meta, [new_index_name, new_name, old_index_name])
                        if meta == 'meta_indexes':
                            self._execute(rename_index.format(Identifier(old_index_name), Identifier(new_index_name)))
                        elif meta == 'meta_constraints':
                            self._execute(rename_constraint.format(Identifier(old_name), Identifier(old_index_name), Identifier(new_index_name)))
            else:
                print "Renamed all indexes, constraints and the corresponding metadata"

            # rename meta_tables and meta_tables_hist
            rename_table_in_meta = SQL("UPDATE {0} SET name = %s WHERE name = %s")
            for meta in ['meta_tables','meta_tables_hist']:
                self._execute(rename_table_in_meta.format(Identifier(meta)), [new_name, old_name])
            else:
                print "Renamed all entries meta_tables(_hist)"

            rename = SQL('ALTER TABLE {0} RENAME TO {1}');
            # rename extra table
            if table.extra_table is not None:
                old_extra = table.extra_table
                assert old_extra == old_name + '_extras'
                new_extra = new_name + '_extras'
                self._execute(rename.format(Identifier(old_extra), Identifier(new_extra)))
                print "Renamed {0} to {1}".format(old_extra, new_extra)
            for suffix in ['', "_counts", "_stats"]:
                self._execute(rename.format(Identifier(old_name + suffix), Identifier(new_name + suffix)))
                print "Renamed {0} to {1}".format(old_name + suffix, new_name + suffix)

            # rename oldN tables
            for backup_number in range(table._next_backup_number()):
                for ext in ["", "_extras", "_counts", "_stats"]:
                    old_name_old = "{0}{1}_old{2}".format(old_name, ext, backup_number)
                    new_name_old = "{0}{1}_old{2}".format(new_name, ext, backup_number)
                    if self._table_exists(old_name_old):
                        self._execute(rename.format(Identifier(old_name_old), Identifier(new_name_old)))
                        print "Renamed {0} to {1}".format(old_name_old, new_name_old)
            for ext in ["", "_extras", "_counts", "_stats"]:
                old_name_tmp = "{0}{1}_tmp".format(old_name, ext)
                new_name_tmp = "{0}{1}_tmp".format(new_name, ext)
                if self._table_exists(old_name_tmp):
                    self._execute(rename.format(Identifier(old_name_tmp), Identifier(new_name_tmp)))
                    print "Renamed {0} to {1}".format(old_name_tmp, new_name_old)

            # initialized table
            tabledata = self._execute(SQL("SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, has_extras, stats_valid, total FROM meta_tables WHERE name = %s"), [new_name]).fetchone()
            table = PostgresTable(self, *tabledata)
            self.__dict__[new_name] = table
            self.tablenames.append(new_name)
            self.tablenames.remove(old_name)
            self.tablenames.sort()

    def copy_to(self, search_tables, data_folder, **kwds):
        if os.path.exists(data_folder):
            raise ValueError("The path {} already exists".format(data_folder))
        os.makedirs(data_folder)
        failures = []
        for tablename in search_tables:
            if tablename in self.tablenames:
                table = self[tablename]
                searchfile = os.path.join(data_folder, tablename + '.txt')
                statsfile = os.path.join(data_folder, tablename + '_stats.txt')
                countsfile = os.path.join(data_folder, tablename + '_counts.txt')
                extrafile = os.path.join(data_folder, tablename + '_extras.txt')
                if table.extra_table is None:
                    extrafile = None
                indexesfile = os.path.join(data_folder, tablename + '_indexes.txt')
                constraintsfile = os.path.join(data_folder, tablename + '_constraints.txt')
                metafile = os.path.join(data_folder, tablename + '_meta.txt')
                table.copy_to(searchfile=searchfile, extrafile=extrafile, countsfile=countsfile, statsfile=statsfile, indexesfile=indexesfile, constraintsfile=constraintsfile, metafile=metafile, **kwds)
            else:
                print "%s is not in tablenames " % (tablename,)
                failures.append(tablename)
        if failures:
            print "Failed to copy %s (not in tablenames)" % (", ".join(failures))

    def copy_to_from_remote(self, search_tables, data_folder, remote_opts=None, **kwds):
        if remote_opts is None:
            from lmfdb.utils.config import Configuration
            remote_opts = Configuration().get_postgresql_default()

        source = PostgresDatabase(**remote_opts)

        # copy all the data
        source.copy_to(search_tables, data_folder, **kwds)


    def reload_all(self, data_folder, halt_on_errors=True, resort=None, reindex=True, restat=None,
                   adjust_schema=False, commit=True,
                   **kwds):
        """
        Reloads all tables from files in a given folder.  The filenames must match
        the names of the tables, with `_extras`, `_counts` and `_stats` appended as appropriate.

        INPUT:

            - ``data_folder`` -- the folder that contains files to be reloaded
            - ``halt_on_errors`` -- whether to stop if a DatabaseError is
                encountered while trying to reload one of the tables

        INPUTS passed to `reload` function in `PostgresTable`:

                - ``resort``, ``reindex``, ``restat``, ``adjust_schema``, ``commit``, and any extra keywords



        Note that this function currently does not reload data that is not in a
        search table, such as knowls or user data.

        """
        if not os.path.isdir(data_folder):
            raise ValueError(
                    "The path {} is not a directory".format(data_folder))
        with DelayCommit(self, commit, silence=True):
            file_list = []
            tablenames = []
            non_existent_tables = []
            possible_endings = ['_extras.txt', '_counts.txt', '_stats.txt',
                    '_indexes.txt','_constraints.txt','_meta.txt']
            for path in glob(os.path.join(data_folder, "*.txt")):
                filename = os.path.basename(path)
                if any(filename.endswith(elt) for elt in possible_endings):
                    continue
                tablename = filename[:-4]
                if tablename not in self.tablenames:
                    non_existent_tables.append(tablename)
            if non_existent_tables:
                if not adjust_schema:
                    raise ValueError("non existent tables: {0}; use adjust_schema=True to create them".format(", ".join(non_existent_tables)))
                print "Creating tables: {0}".format(", ".join(non_existent_tables))
                for tablename in non_existent_tables:
                    search_table_file = os.path.join(data_folder, tablename + '.txt')
                    extras_file = os.path.join(data_folder, tablename + '_extras.txt')
                    metafile = os.path.join(data_folder, tablename + '_meta.txt')
                    if not os.path.exists(metafile):
                        raise ValueError("meta file missing for {0}".format(tablename))
                    # read metafile
                    rows = []
                    with open(metafile, "r") as F:
                        rows = [line for line in csv.reader(F, delimiter = "\t")]
                    if len(rows) != 1:
                        raise RuntimeError("Expected only one row in {0}")
                    meta = dict(zip(_meta_tables_cols, rows[0]))
                    assert meta["name"] == tablename

                    with open(search_table_file, "r") as F:
                        search_columns_pairs = self._read_header_lines(F)

                    search_columns = defaultdict(list)
                    for name, typ in search_columns_pairs:
                        if name != 'id':
                            search_columns[typ].append(name)

                    extra_columns = None
                    if meta["has_extras"] == "t":
                        if not os.path.exists(extras_file):
                            raise ValueError("extras file missing for {0}".format(tablename))
                        with open(extras_file, "r") as F:
                            extras_columns_pairs = self._read_header_lines(F)
                        extra_columns = defaultdict(list)
                        for name, typ in extras_columns_pairs:
                            if name != 'id':
                                extra_columns[typ].append(name)
                    # the rest of the meta arguments will be replaced on the reload_all
                    self.create_table(tablename, search_columns, None, extra_columns=extra_columns)

            for tablename in self.tablenames:
                included = []

                searchfile = os.path.join(data_folder, tablename + '.txt')
                if not os.path.exists(searchfile):
                    continue
                included.append(tablename)


                table = self[tablename]

                extrafile = os.path.join(data_folder, tablename + '_extras.txt')
                if os.path.exists(extrafile):
                    if table.extra_table is None:
                        raise ValueError("Unexpected file %s"%extrafile)
                    included.append(tablename + '_extras')
                elif table.extra_table is None:
                    extrafile = None
                else:
                    raise ValueError("Missing file %s"%extrafile)

                countsfile = os.path.join(data_folder, tablename + '_counts.txt')
                if os.path.exists(countsfile):
                    included.append(tablename + '_counts')
                else:
                    countsfile = None

                statsfile = os.path.join(data_folder, tablename + '_stats.txt')
                if os.path.exists(statsfile):
                    included.append(tablename + '_stats')
                else:
                    statsfile = None

                indexesfile = os.path.join(data_folder, tablename + '_indexes.txt')
                if not os.path.exists(indexesfile):
                    indexesfile = None

                constraintsfile = os.path.join(data_folder, tablename + '_constraints.txt')
                if not os.path.exists(constraintsfile):
                    constraintsfile = None

                metafile = os.path.join(data_folder, tablename + '_meta.txt')
                if not os.path.exists(metafile):
                    metafile = None

                file_list.append((table, (searchfile, extrafile, countsfile, statsfile, indexesfile, constraintsfile, metafile), included))
                tablenames.append(tablename)
            print "Reloading {0}".format(", ".join(tablenames))
            failures = []
            for table, filedata, included in file_list:
                try:
                    table.reload(*filedata, resort=resort, reindex=reindex, restat=restat, final_swap=False, silence_meta=True, adjust_schema=adjust_schema, **kwds)
                except DatabaseError:
                    if halt_on_errors or non_existent_tables:
                        raise
                    else:
                        traceback.print_exc()
                        failures.append(table)
            for table, filedata, included in file_list:
                if table in failures:
                    continue
                table.reload_final_swap(tables=included, metafile=filedata[-1])

        if failures:
            print "Reloaded %s"%(", ".join(tablenames))
            print "Failures in reloading %s"%(", ".join(table.search_table for table in failures))
        else:
            print "Successfully reloaded %s"%(", ".join(tablenames))

    def reload_all_revert(self, data_folder, commit=True):
        """
        Reverts the most recent ``reload_all`` by swapping with the backup table
        for each search table modified.

        INPUT:

        - ``data_folder`` -- the folder used in ``reload_all``;
            determines which tables
            were modified.
        """
        if not os.path.isdir(data_folder):
            raise ValueError(
                    "The path {} is not a directory".format(data_folder))

        with DelayCommit(self, commit, silence=True):
            for tablename in self.tablenames:
                searchfile = os.path.join(data_folder, tablename + '.txt')
                if not os.path.exists(searchfile):
                    continue
                self[tablename].reload_revert()

    def cleanup_all(self, commit=True):
        """
        Drops all `_tmp` and `_old` tables created by the reload() method.
        """
        with DelayCommit(self, commit, silence=True):
            for tablename in self.tablenames:
                table = self[tablename]
                table.cleanup_from_reload()

    def verify(self, speedtype="all", logdir=None, parallel=8, follow=['errors', 'log', 'progress'], poll_interval=0.1, debug=False):
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
        lmfdb_root = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
        if logdir is None:
            logdir = os.path.join(lmfdb_root, 'logs', 'verification')
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
        cmd = os.path.abspath(os.path.join(os.path.abspath(__file__), '..', 'verify', 'verify_tables.py'))
        cmd = ['sage', '-python', cmd, '-j%s'%int(parallel), logdir, 'all', speedtype]
        if debug:
            pipe = subprocess.Popen(cmd)
        else:
            DEVNULL = open(os.devnull, 'wb')
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

db = PostgresDatabase()
