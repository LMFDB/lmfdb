# -*- coding: utf-8 -*-
import csv
import logging
import os
import time
import traceback
import itertools
from collections import defaultdict, Counter
from glob import glob

from psycopg2 import connect, DatabaseError
from psycopg2.sql import SQL, Identifier, Placeholder
from psycopg2.extensions import (
    register_type,
    register_adapter,
    new_type,
    new_array_type,
    UNICODE,
    UNICODEARRAY,
    AsIs,
)
from psycopg2.extras import register_json

from .encoding import Json, numeric_converter
from .base import PostgresBase, _meta_tables_cols
from .searchtable import PostgresSearchTable
from .utils import DelayCommit


def setup_connection(conn):
    # We want to use unicode everywhere
    register_type(UNICODE, conn)
    register_type(UNICODEARRAY, conn)
    conn.set_client_encoding("UTF8")
    cur = conn.cursor()
    cur.execute("SELECT NULL::numeric")
    oid = cur.description[0][1]
    NUMERIC = new_type((oid,), "NUMERIC", numeric_converter)
    cur.execute("SELECT NULL::numeric[]")
    oid = cur.description[0][1]
    NUMERICL = new_array_type((oid,), "NUMERIC[]", NUMERIC)
    register_type(NUMERIC, conn)
    register_type(NUMERICL, conn)
    register_adapter(dict, Json)
    register_json(conn, loads=Json.loads)
    try:
        from sage.all import Integer, RealNumber
    except ImportError:
        pass
    else:
        register_adapter(Integer, AsIs)
        from .encoding import RealEncoder, LmfdbRealLiteral
        register_adapter(RealNumber, RealEncoder)
        register_adapter(LmfdbRealLiteral, RealEncoder)

class PostgresDatabase(PostgresBase):
    """
    The interface to the postgres database.

    It creates and stores the global connection object,
    and collects the table interfaces.

    INPUT:

    - ``**kwargs`` -- passed on to psycopg's connect method

    ATTRIBUTES:

    The following public attributes are stored on the db object.

    - ``server_side_counter`` -- an integer tracking how many buffered connections have been created
    - ``conn`` -- the psycopg2 connection object
    - ``tablenames`` -- a list of tablenames in the database, as strings

    Also, each tablename will be stored as an attribute, so that db.ec_curvedata works for example.

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

    def register_object(self, obj):
        """
        The database holds references to tables, etc so that connections can be refreshed if they fail.
        """
        obj.conn = self.conn
        self._objects.append(obj)

    def __init__(self, config=None, secretsfile=None, **kwargs):
        if config is None:
            from .config import Configuration
            config = Configuration()
        self.config = config
        self.server_side_counter = 0
        self._nocommit_stack = 0
        self._silenced = False
        self._objects = []
        self.conn = self._new_connection(**kwargs)
        PostgresBase.__init__(self, "db_all", self)
        if self._user == "webserver":
            self._execute(SQL("SET SESSION statement_timeout = '25s'"))


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
            self._read_only = cur.fetchone()[0] ==0

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

        cur = self._execute(SQL(
            "SELECT table_name, column_name, udt_name::regtype "
            "FROM information_schema.columns ORDER BY table_name, ordinal_position"
        ))
        data_types = {}
        for table_name, column_name, regtype in cur:
            if table_name not in data_types:
                data_types[table_name] = []
            data_types[table_name].append((column_name, regtype))

        cur = self._execute(SQL(
            "SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, "
            "has_extras, stats_valid, total, include_nones FROM meta_tables"
        ))
        self.tablenames = []
        for tabledata in cur:
            tablename = tabledata[0]
            tabledata += (data_types,)
            table = self._search_table_class_(self, *tabledata)
            self.__dict__[tablename] = table
            self.tablenames.append(tablename)
        self.tablenames.sort()

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

    def log_db_change(self, operation, tablename=None, **data):
        """
        By default we don't log changes (from updates, etc), but you can
        override this method if you want to do some logging.
        """
        pass

    def _grant(self, action, table_name, users):
        """
        Utility function for granting permissions on tables.
        """
        action = action.upper()
        if action not in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
            raise ValueError("%s is not a valid action" % action)
        grantor = SQL("GRANT %s ON TABLE {0} TO {1}" % action)
        for user in users:
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

    def is_read_only(self):
        """
        Whether this instance of the database is read only.
        """
        return self._read_only

    def can_read_write_knowls(self):
        """
        Whether this instance of the database has permission to read and write to the knowl tables
        """
        return self._read_and_write_knowls

    def can_read_write_userdb(self):
        """
        Whether this instance of the database has permission to read and write to the user info tables.
        """
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
            elif table_name.endswith("_extras"):
                name = table_name[:-7]
                sizes[name]["extras_bytes"] = total_bytes
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

    def _create_meta_indexes_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL(
                "CREATE TABLE meta_indexes_hist "
                "(index_name text, table_name text, type text, columns jsonb, "
                "modifiers jsonb, storage_params jsonb, version integer)"
            ))
            version = 0

            # copy data from meta_indexes
            rows = self._execute(SQL(
                "SELECT index_name, table_name, type, columns, modifiers, "
                "storage_params FROM meta_indexes"
            ))

            for row in rows:
                self._execute(
                    SQL(
                        "INSERT INTO meta_indexes_hist (index_name, table_name, "
                        "type, columns, modifiers, storage_params, version) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    ),
                    row + (version,),
                )

            self.grant_select("meta_indexes_hist")

        print("Table meta_indexes_hist created")

    def _create_meta_constraints(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL(
                "CREATE TABLE meta_constraints "
                "(constraint_name text, table_name text, "
                "type text, columns jsonb, check_func jsonb)"
            ))
            self.grant_select("meta_constraints")
        print("Table meta_constraints created")

    def _create_meta_constraints_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL(
                "CREATE TABLE meta_constraints_hist "
                "(constraint_name text, table_name text, "
                "type text, columns jsonb, check_func jsonb, version integer)"
            ))
            version = 0

            # copy data from meta_constraints
            rows = self._execute(SQL(
                "SELECT constraint_name, table_name, type, columns, check_func "
                "FROM meta_constraints"
            ))

            for row in rows:
                self._execute(
                    SQL(
                        "INSERT INTO meta_constraints_hist "
                        "(constraint_name, table_name, type, columns, check_func, version) "
                        "VALUES (%s, %s, %s, %s, %s, %s)"
                    ),
                    row + (version,),
                )

            self.grant_select("meta_constraints_hist")

        print("Table meta_constraints_hist created")

    def _create_meta_tables_hist(self):
        with DelayCommit(self, silence=True):
            self._execute(SQL(
                "CREATE TABLE meta_tables_hist "
                "(name text, sort jsonb, count_cutoff smallint DEFAULT 1000, "
                "id_ordered boolean, out_of_order boolean, has_extras boolean, "
                "stats_valid boolean DEFAULT true, label_col text, total bigint, "
                "include_nones boolean, table_description text, col_description jsonb, version integer)"
            ))
            version = 0

            # copy data from meta_tables
            rows = self._execute(SQL(
                "SELECT name, sort, id_ordered, out_of_order, has_extras, label_col, total, include_nones, table_description, col_description FROM meta_tables "
            ))

            for row in rows:
                self._execute(
                    SQL(
                        "INSERT INTO meta_tables_hist "
                        "(name, sort, id_ordered, out_of_order, has_extras, label_col, "
                        "total, include_nones, table_description, col_description, version) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    ),
                    row + (version,),
                )

            self.grant_select("meta_tables_hist")

        print("Table meta_tables_hist created")

    def create_table_like(self, new_name, table, data=False, commit=True):
        """
        Copies the schema from an existing table, but none of the data, indexes or stats.

        INPUT:

        - ``new_name`` -- a string giving the desired table name.
        - ``table`` -- a string or PostgresSearchTable object giving an existing table.
        """
        if isinstance(table, str):
            table = self[table]
        search_columns = {
            typ: [col for col in table.search_cols if table.col_type[col] == typ]
            for typ in set(table.col_type.values())
        }
        extra_columns = {
            typ: [col for col in table.extra_cols if table.col_type[col] == typ]
            for typ in set(table.col_type.values())
        }
        # Remove empty lists
        for D in [search_columns, extra_columns]:
            for typ, cols in list(D.items()):
                if not cols:
                    D.pop(typ)
        if not extra_columns:
            extra_columns = extra_order = None
        else:
            extra_order = table.extra_cols
        label_col = table._label_col
        table_description = table.description()
        col_description = table.column_description()
        sort = table._sort_orig
        id_ordered = table._id_ordered
        search_order = table.search_cols
        self.create_table(
            new_name,
            search_columns,
            label_col,
            table_description,
            col_description,
            sort,
            id_ordered,
            extra_columns,
            search_order,
            extra_order,
            commit=commit,
        )
        if data:
            cols = SQL(", ").join(map(Identifier, ["id"] + table.search_cols))
            self._execute(
                SQL("INSERT INTO {0} ( {1} ) SELECT {1} FROM {2}").format(
                    Identifier(new_name), cols, Identifier(table.search_table)
                ),
                commit=commit,
            )
            if extra_columns:
                extra_cols = SQL(", ").join(map(Identifier, ["id"] + table.extra_cols))
                self._execute(
                    SQL("INSERT INTO {0} ( {1} ) SELECT {1} FROM {2}").format(
                        Identifier(new_name + "_extras"), extra_cols,
                        Identifier(table.extra_table)
                    ),
                    commit=commit,
                )
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
        extra_columns=None,
        search_order=None,
        extra_order=None,
        force_description=False,
        commit=True,
    ):
        """
        Add a new search table to the database.  See also `create_table_like`.

        INPUT:

        - ``name`` -- the name of the table, which must include an underscore.  See existing names for consistency.
        - ``search_columns`` -- a dictionary whose keys are valid postgres types and whose values
            are lists of column names (or just a string if only one column has the specified type).
            An id column of type bigint will be added as a primary key (do not include it).
        - ``label_col`` -- the column holding the LMFDB label.  This will be used in the ``lookup`` method
            and in the display of results on the API.  Use None if there is no appropriate column.
        - ``table_description`` -- a text description of this table
        - ``col_description`` -- a dictionary giving descriptions for the columns (both search and extra)
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
        - ``force_description`` -- whether to require descriptions

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
            raise ValueError("%s already exists" % name)
        now = time.time()
        if id_ordered is None:
            id_ordered = sort is not None
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
        # Check that search order is valid
        if search_order is not None:
            for col in search_order:
                if col not in valid_set:
                    raise ValueError("Column %s does not exist" % (col))
            if len(search_order) != len(valid_set):
                raise ValueError("Must include all columns")

        def process_columns(coldict, colorder):
            allcols = {}
            hasid = False
            dictorder = []
            for typ, cols in coldict.items():
                self._check_col_datatype(typ)
                if isinstance(cols, str):
                    cols = [cols]
                for col in cols:
                    if col == "id":
                        hasid = True
                    # We have whitelisted the types, so it's okay to use string formatting
                    # to insert them into the SQL command.
                    # This is useful so that we can specify the collation in the type
                    allcols[col] = SQL("{0} " + typ).format(Identifier(col))
                    dictorder.append(col)
            allcols = [allcols[col] for col in (dictorder if colorder is None else colorder)]
            if not hasid:
                allcols.insert(0, SQL("id bigint"))
            return allcols

        processed_search_columns = process_columns(search_columns, search_order)
        # Check that descriptions are provided if required
        if extra_columns is not None:
            valid_extra_list = sum(extra_columns.values(), [])
            valid_extra_set = set(valid_extra_list)
            # Check that columns aren't listed twice
            if len(valid_extra_list) != len(valid_extra_set):
                C = Counter(valid_extra_list)
                raise ValueError("Column %s repeated" % (C.most_common(1)[0][0]))
            if extra_order is not None:
                for col in extra_order:
                    if col not in valid_extra_set:
                        raise ValueError("Column %s does not exist" % (col))
                if len(extra_order) != len(valid_extra_set):
                    raise ValueError("Must include all columns")
            processed_extra_columns = process_columns(extra_columns, extra_order)
        else:
            processed_extra_columns = []
        description_columns = []
        for col in itertools.chain(search_columns.values(), [] if extra_columns is None else extra_columns.values()):
            if col == 'id':
                continue
            if isinstance(col, str):
                description_columns.append(col)
            else:
                description_columns.extend(col)
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

        with DelayCommit(self, commit, silence=True):
            creator = SQL("CREATE TABLE {0} ({1})").format(
                Identifier(name), SQL(", ").join(processed_search_columns)
            )
            self._execute(creator)
            self.grant_select(name)
            if extra_columns is not None:
                creator = SQL("CREATE TABLE {0} ({1})")
                creator = creator.format(
                    Identifier(name + "_extras"),
                    SQL(", ").join(processed_extra_columns),
                )
                self._execute(creator)
                self.grant_select(name + "_extras")
            creator = SQL(
                "CREATE TABLE {0} "
                "(cols jsonb, values jsonb, count bigint, "
                "extra boolean, split boolean DEFAULT FALSE)"
            )
            creator = creator.format(Identifier(name + "_counts"))
            self._execute(creator)
            self.grant_select(name + "_counts")
            self.grant_insert(name + "_counts")
            creator = SQL(
                "CREATE TABLE {0} "
                '(cols jsonb, stat text COLLATE "C", value numeric, '
                "constraint_cols jsonb, constraint_values jsonb, threshold integer)"
            )
            creator = creator.format(Identifier(name + "_stats"))
            self._execute(creator)
            self.grant_select(name + "_stats")
            self.grant_insert(name + "_stats")
            # FIXME use global constants ?
            inserter = SQL(
                "INSERT INTO meta_tables "
                "(name, sort, id_ordered, out_of_order, has_extras, label_col, table_description, col_description) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            )
            self._execute(
                inserter,
                [
                    name,
                    Json(sort),
                    id_ordered,
                    not id_ordered,
                    extra_columns is not None,
                    label_col,
                    table_description,
                    Json(col_description),
                ],
            )
        self.__dict__[name] = self._search_table_class_(
            self,
            name,
            label_col,
            sort=sort,
            id_ordered=id_ordered,
            out_of_order=(not id_ordered),
            has_extras=(extra_columns is not None),
            total=0,
        )
        self.tablenames.append(name)
        self.tablenames.sort()
        self.log_db_change(
            "create_table",
            tablename=name,
            name=name,
            search_columns=search_columns,
            label_col=label_col,
            sort=sort,
            id_ordered=id_ordered,
            extra_columns=extra_columns,
            search_order=search_order,
            extra_order=extra_order,
        )
        print("Table %s created in %.3f secs" % (name, time.time() - now))

    def drop_table(self, name, commit=True, force=False):
        """
        Drop a table.

        INPUT:

        - ``name`` -- the name of the table
        - ``commit`` -- whether to actually execute the drop command
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
        with DelayCommit(self, commit, silence=True):
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
            if table.extra_table is not None:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(table.extra_table)))
                print("Dropped {0}".format(table.extra_table))
            for tbl in [name, name + "_counts", name + "_stats"]:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(tbl)))
                print("Dropped {0}".format(tbl))
            self.tablenames.remove(name)
            delattr(self, name)

    def rename_table(self, old_name, new_name, commit=True):
        """
        Rename a table.

        INPUT:

        - ``old_name`` -- the current name of the table, as a string
        - ``new_name`` -- the new name of the table, as a string
        """
        assert old_name != new_name
        assert new_name not in self.tablenames
        with DelayCommit(self, commit, silence=True):
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
            # rename extra table
            if table.extra_table is not None:
                old_extra = table.extra_table
                assert old_extra == old_name + "_extras"
                new_extra = new_name + "_extras"
                self._execute(rename.format(Identifier(old_extra), Identifier(new_extra)))
                print("Renamed {0} to {1}".format(old_extra, new_extra))
            for suffix in ["", "_counts", "_stats"]:
                self._execute(rename.format(Identifier(old_name + suffix), Identifier(new_name + suffix)))
                print("Renamed {0} to {1}".format(old_name + suffix, new_name + suffix))

            # rename oldN tables
            for backup_number in range(table._next_backup_number()):
                for ext in ["", "_extras", "_counts", "_stats"]:
                    old_name_old = "{0}{1}_old{2}".format(old_name, ext, backup_number)
                    new_name_old = "{0}{1}_old{2}".format(new_name, ext, backup_number)
                    if self._table_exists(old_name_old):
                        self._execute(rename.format(Identifier(old_name_old), Identifier(new_name_old)))
                        print("Renamed {0} to {1}".format(old_name_old, new_name_old))
            for ext in ["", "_extras", "_counts", "_stats"]:
                old_name_tmp = "{0}{1}_tmp".format(old_name, ext)
                new_name_tmp = "{0}{1}_tmp".format(new_name, ext)
                if self._table_exists(old_name_tmp):
                    self._execute(rename.format(Identifier(old_name_tmp), Identifier(new_name_tmp)))
                    print("Renamed {0} to {1}".format(old_name_tmp, new_name_old))

            # initialized table
            tabledata = self._execute(
                SQL(
                    "SELECT name, label_col, sort, count_cutoff, id_ordered, "
                    "out_of_order, has_extras, stats_valid, total, include_nones "
                    "FROM meta_tables WHERE name = %s"
                ),
                [new_name],
            ).fetchone()
            table = self._search_table_class_(self, *tabledata)
            self.__dict__[new_name] = table
            self.tablenames.append(new_name)
            self.tablenames.remove(old_name)
            self.tablenames.sort()

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

        if os.path.exists(data_folder):
            raise ValueError("The path {} already exists".format(data_folder))
        os.makedirs(data_folder)
        failures = []
        for tablename in search_tables:
            if tablename in self.tablenames:
                table = self[tablename]
                searchfile = os.path.join(data_folder, tablename + ".txt")
                statsfile = os.path.join(data_folder, tablename + "_stats.txt")
                countsfile = os.path.join(data_folder, tablename + "_counts.txt")
                extrafile = os.path.join(data_folder, tablename + "_extras.txt")
                if table.extra_table is None:
                    extrafile = None
                indexesfile = os.path.join(data_folder, tablename + "_indexes.txt")
                constraintsfile = os.path.join(data_folder, tablename + "_constraints.txt")
                metafile = os.path.join(data_folder, tablename + "_meta.txt")
                table.copy_to(
                    searchfile=searchfile,
                    extrafile=extrafile,
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
        - ``remote_opts`` -- options for the remote connection (passed on to psycopg2's connect method)
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
        reindex=True,
        restat=None,
        adjust_schema=False,
        commit=True,
        **kwds
    ):
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
            raise ValueError("The path {} is not a directory".format(data_folder))
        sep = kwds.get("sep", u"|")
        with DelayCommit(self, commit, silence=True):
            file_list = []
            tablenames = []
            non_existent_tables = []
            possible_endings = [
                "_extras.txt",
                "_counts.txt",
                "_stats.txt",
                "_indexes.txt",
                "_constraints.txt",
                "_meta.txt",
            ]
            for path in glob(os.path.join(data_folder, "*.txt")):
                filename = os.path.basename(path)
                if any(filename.endswith(elt) for elt in possible_endings):
                    continue
                tablename = filename[:-4]
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
                    search_table_file = os.path.join(data_folder, tablename + ".txt")
                    extras_file = os.path.join(data_folder, tablename + "_extras.txt")
                    metafile = os.path.join(data_folder, tablename + "_meta.txt")
                    if not os.path.exists(metafile):
                        raise ValueError("meta file missing for {0}".format(tablename))
                    # read metafile
                    with open(metafile, "r") as F:
                        rows = list(csv.reader(F, delimiter=str(sep)))
                    if len(rows) != 1:
                        raise RuntimeError("Expected only one row in {0}")
                    meta = dict(zip(_meta_tables_cols, rows[0]))
                    import ast
                    meta["col_description"] = ast.literal_eval(meta["col_description"])
                    assert meta["name"] == tablename

                    with open(search_table_file, "r") as F:
                        search_columns_pairs = self._read_header_lines(F, sep=sep)

                    search_columns = defaultdict(list)
                    for name, typ in search_columns_pairs:
                        if name != "id":
                            search_columns[typ].append(name)

                    extra_columns = None
                    if meta["has_extras"] == "t":
                        if not os.path.exists(extras_file):
                            raise ValueError("extras file missing for {0}".format(tablename))
                        with open(extras_file, "r") as F:
                            extras_columns_pairs = self._read_header_lines(F, sep=sep)
                        extra_columns = defaultdict(list)
                        for name, typ in extras_columns_pairs:
                            if name != "id":
                                extra_columns[typ].append(name)
                    # the rest of the meta arguments will be replaced on the reload_all
                    # We use force_description=False so that beta and prod can be out-of-sync with respect to columns and/or descriptions
                    self.create_table(tablename, search_columns, None, table_description=meta["table_description"], col_description=meta["col_description"], extra_columns=extra_columns, force_description=False)

            for tablename in self.tablenames:
                included = []

                searchfile = os.path.join(data_folder, tablename + ".txt")
                if not os.path.exists(searchfile):
                    continue
                included.append(tablename)

                table = self[tablename]

                extrafile = os.path.join(data_folder, tablename + "_extras.txt")
                if os.path.exists(extrafile):
                    if table.extra_table is None:
                        raise ValueError("Unexpected file %s" % extrafile)
                    included.append(tablename + "_extras")
                elif table.extra_table is None:
                    extrafile = None
                else:
                    raise ValueError("Missing file %s" % extrafile)

                countsfile = os.path.join(data_folder, tablename + "_counts.txt")
                if os.path.exists(countsfile):
                    included.append(tablename + "_counts")
                else:
                    countsfile = None

                statsfile = os.path.join(data_folder, tablename + "_stats.txt")
                if os.path.exists(statsfile):
                    included.append(tablename + "_stats")
                else:
                    statsfile = None

                indexesfile = os.path.join(data_folder, tablename + "_indexes.txt")
                if not os.path.exists(indexesfile):
                    indexesfile = None

                constraintsfile = os.path.join(data_folder, tablename + "_constraints.txt")
                if not os.path.exists(constraintsfile):
                    constraintsfile = None

                metafile = os.path.join(data_folder, tablename + "_meta.txt")
                if not os.path.exists(metafile):
                    metafile = None

                file_list.append(
                    (
                        table,
                        (
                            searchfile,
                            extrafile,
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
                        reindex=reindex,
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
            raise ValueError("The path {} is not a directory".format(data_folder))

        with DelayCommit(self, commit, silence=True):
            for tablename in self.tablenames:
                searchfile = os.path.join(data_folder, tablename + ".txt")
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
