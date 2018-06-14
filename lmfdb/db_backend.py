"""
This module provides an interface to Postgres supporting
the kinds of queries needed by the LMFDB.

EXAMPLES::

    sage: from lmfdb.db_backend import db
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

- ``extras_table`` -- a string or None.  If provided, gives the name of a table that is linked to the search table by an ``id`` column and provides more data that cannot be searched on.  The reason to separate the data into two tables is to reduce the size of the search table.  For large tables this speeds up some queries.
- ``count_table`` -- a string or None.  If provided, gives the name of a table that caches counts for searches on the search table.  These counts are relevant when many results are returned, allowing the search pages to report the number of records even when it would take Postgres a long time to compute this count.

"""


import logging
import pymongo
import re, os
from psycopg2 import connect, DatabaseError
import psycopg2.extras, psycopg2.extensions
from psycopg2.extras import Json, execute_values
from psycopg2.extensions import register_type, register_adapter, new_type, UNICODE, UNICODEARRAY, AsIs
import json, random, time
from lmfdb.utils import random_object_from_collection
from sage.rings.integer import Integer
from sage.misc.cachefunc import cached_method
from sage.rings.real_mpfr import RealLiteral, RealField
from sage.functions.other import ceil
from sage.misc.mrange import cartesian_product_iterator
from lmfdb.utils import make_logger, format_percentage

SLOW_QUERY_LOGFILE = "slow_queries.log"
SLOW_CUTOFF = 1

def numeric_converter(value, cur):
    """
    Used for converting numeric values from Postgres to Python.

    INPUT:

    - ``value`` -- a string representing a decimal number.
    - ``cur`` -- a cursor, unused

    OUTPUT:

    - either a sage integer (if there is no decimal point) or a real number whose precision depends on the number of digits in value.
    """
    if value is None:
        return None
    if '.' in value:
        prec = max(ceil(len(value)*3.322), 53)
        return RealLiteral(RealField(prec), value)
    else:
        return Integer(value)

def prep_json(value):
    """
    Make json compliant.  Namely, it iteratively changes Integers to ints and RealLiterals to floats.
    """
    if isinstance(value, list):
        return [prep_json(x) for x in value]
    elif isinstance(value, tuple):
        return tuple(prep_json(x) for x in value)
    elif isinstance(value, dict):
        return {k:prep_json(v) for k,v in value.iteritems()}
    elif isinstance(value, Integer):
        return int(value)
    elif isinstance(value, RealLiteral):
        return float(value)
    else:
        return value

class QueryLogFilter(object):
    """
    A filter used when logging slow queries.
    """
    def filter(self, record):
        if record.pathname.startswith('db_backend.py'):
            return 1
        else:
            return 0

class PostgresBase(object):
    """
    A base class for various objects that interact with Postgres.

    Any class inheriting from this one must provide a connection
    to the postgres database, as well as a name used when creating a logger.
    """
    def __init__(self, loggername, conn):
        self.conn = conn
        self.logger = make_logger(loggername)
        handler = logging.FileHandler(SLOW_QUERY_LOGFILE)
        formatter = logging.Formatter("%(asctime)s - %(message)s")
        filt = QueryLogFilter()
        handler.setFormatter(formatter)
        handler.addFilter(filt)
        self.logger.addHandler(handler)

    def _execute(self, query, values=None, silent=False, values_list=False, template=None, commit=True):
        """
        Execute an SQL command, properly catching errors and returning the resulting cursor.

        INPUT:

        - ``query`` -- string, the SQL command to execute.
        - ``values`` -- values to substitute for %s in the query.  Quoting from the documentation for psycopg2 (http://initd.org/psycopg/docs/usage.html#passing-parameters-to-sql-queries):

        Never, never, NEVER use Python string concatenation (+) or string parameters interpolation (%) to pass variables to a SQL query string. Not even at gunpoint.
        - ``silent`` -- boolean (default False).  If True, don't log a warning for a slow query.
        - ``values_list`` -- boolean (default False).  If True, use the ``execute_values`` method, designed for inserting multiple values.
        - ``template`` -- string, for use with ``values_list`` to insert constant values: for example ``"(%s, %s, 42)"``. See the documentation of ``execute_values`` for more details.
        - ``commit`` -- boolean (default True).  Whether to commit changes on success.

        OUTPUT:

        - a cursor object from which the resulting records can be obtained via iteration.

        This function will also log slow queries.
        """
        cur = self.conn.cursor()
        try:
            t = time.time()
            if values_list:
                execute_values(cur, query, values, template)
            else:
                cur.execute(query, values)
            if not silent:
                t = time.time() - t
                if t > SLOW_CUTOFF:
                    if values:
                        query = query%(tuple(values))
                    self.logger.info(query + " ran in %ss"%(t))
        except DatabaseError:
            self.conn.rollback()
            raise
        else:
            if commit:
                self.conn.commit()
        return cur

    @cached_method
    def _table_exists(self, tablename):
        cur = self._execute("SELECT to_regclass(%s);", [tablename], silent=True)
        return cur.fetchone()[0] is not None

    @staticmethod
    def _sort_str(sort_list):
        """
        Constructs a string describing a sort order for Postgres from a list of columns.

        INPUT:

        - ``sort_list`` -- a list, either of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).

        OUTPUT:

        - a string to be used in postgres in the ORDER BY clause.
        """
        L = []
        for col in sort_list:
            if isinstance(col, basestring):
                L.append(col)
            else:
                L.append(col[0] if col[1] == 1 else col[0] + " DESC")
        return ", ".join(L)

class PostgresTable(PostgresBase):
    """
    This class is used to abstract a table in the LMFDB database
    on which searches are performed.  Technically, it may represent
    more than one table, since some tables are split in two for performance
    reasons.

    INPUT:

    - ``db`` -- an instance of ``PostgresDatabase``, currently just used to store the common connection ``conn``.
    - ``search_table`` -- a string, the name of the table in postgres.
    - ``sort`` -- a list giving the default sort order on the table, or None.  If None, sorts that can return more than one result must explicitly specify a sort order.  Note that the id column is sometimes used for sorting; see the ``search`` method for more details.
    - ``cap`` -- a list of strings giving the list of column names that are not lower case.  This is necessary since postgres is not case sensitive but Python is.
    - ``count_cutoff`` -- an integer parameter (default 1000) which determines the threshold at which searches will no longer report the exact number of results.
    """
    def __init__(self, db, search_table, sort=None, cap=[], count_cutoff=1000, id_ordered=False, out_of_order=False, has_extras=False, stats_valid=True):
        self._db = db
        self.search_table = search_table
        self._count_cutoff = count_cutoff
        self._id_ordered = id_ordered
        self._out_of_order = out_of_order
        self._stats_valid = stats_valid
        PostgresBase.__init__(self, search_table, db.conn)
        cap = {col.lower(): col for col in cap}
        def set_column_info(col_list, json_set, table_name):
            cur = self._execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", [table_name])
            has_id = False
            for rec in cur:
                col = cap.get(rec[0],rec[0])
                if col == 'id':
                    has_id = True
                else:
                    col_list.append(col)
                    if rec[1] == 'jsonb':
                        json_set.add(col)
            if (self._id_ordered or self.extras_table is not None) and not has_id:
                raise RuntimeError("Table %s must have id column!"%(table_name))
            self.has_id = has_id # used in determining how to sort
        self._search_cols = []
        self._json_override = set()
        if has_extras:
            self.extras_table = search_table + "_extras"
            self._extra_cols = []
            set_column_info(self._extra_cols, self._json_override, self.extras_table)
            self._extra_cols = tuple(self._extra_cols)
        else:
            self.extras_table = None
            self._extra_cols = None
        set_column_info(self._search_cols, self._json_override, search_table)
        self._search_cols = tuple(self._search_cols)
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
        self.stats = PostgresStatsTable(self)

    def __repr__(self):
        return "Interface to Postgres table %s"%(self.search_table)

    ##################################################################
    # Helper functions for querying                                  #
    ##################################################################

    def _json_wrap(self, col, val):
        """
        Helper function that wraps the value in psycopg2's Json if necessary.
        """
        if val is None or col not in self._json_override:
            return val
        else:
            return Json(val)

    @cached_method
    def _col_types(self):
        """
        Returns dictionaries with the postgres types of the columns
        in the search and extras tables.

        If there is no extras table, the second dictionary will be None.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: db.ec_padic._col_types()
            ({u'lmfdb_iso': u'text',
              u'p': u'smallint',
              u'prec': u'smallint',
              u'unit': u'numeric',
              u'val': u'smallint'},
             None)
        """
        selector = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = %s;"
        cur = self._execute(selector, [self.search_table])
        search_types = {k:v for k,v in cur}
        if self.extras_table is None:
            extras_types = None
        else:
            cur = self._execute(selector, [self.extras_table])
            extras_types = {k:v for k,v in cur}
        return search_types, extras_types

    def _parse_projection(self, projection):
        """
        Parses various ways of specifying which columns are desired.

        INPUT:

        - ``projection`` -- either 0, 1, 2, a dictionary or list of column names.

          - If 0, projects just to the ``label``.  If the search table does not have a lable column, raises a RuntimeError.
          - If 1, projects to all columns in the search table.
          - If 2, projects to all columns in either the search or extras tables.
          - If a dictionary, can specify columns to include by giving True values, or columns to exclude by giving False values.
          - If a list, specifies which columns to include.
          - If a string, projects onto just that column; searches will return the value rather than a dictionary.

        OUTPUT:

        - a tuple of columns to be selected that are in the search table
        - a tuple of columns to be selected that are in the extras table (empty if it doesn't exist)
        - a start position for the columns to be returned to the user (the id column may be needed internally to link the two tables.

        EXAMPLES:

            sage: from lmfdb.db_backend import db
            sage: ec = db.ec_padic
            sage: nf = db.nf_fields
            sage: nf._parse_projection(0)
            ((u'label',), (), 0)
            sage: ec._parse_projection(1)
            ((u'lmfdb_iso', u'p', u'prec', u'val', u'unit'), (), 0)
            sage: ec._parse_projection({"val":True, "unit":True})
            ((u'val', u'unit'), (), 0)

        When the data is split across two tables, some columns may be in the extras table:

            sage: nf._parse_projection(["label", "unitsGmodule"])
            (('id', 'label'), ('unitsGmodule',), 1)

        In the previous example, the id column is included to link the tables.
        If you want the "id" column, list it explicitly.  The start_position will then be 0:

            sage: nf._parse_projection(["id", "label", "unitsGmodule"])
            (('id', 'label'), ('unitsGmodule',), 0)

        You can specify a dictionary with columns to exclude:

            sage: ec._parse_projection({"prec":False})
            ((u'lmfdb_iso', u'p', u'val', u'unit'), (), 0)
        """
        search_cols = []
        extra_cols = []
        if projection == 0:
            if "label" not in self._search_cols:
                raise RuntimeError("label not column of %s"%(self.search_table))
            return (u"label",), (), 0
        elif not projection:
            raise ValueError("You must specify at least one key.")
        if projection == 1:
            return self._search_cols, (), 0
        elif projection == 2:
            if self.extras_table is None:
                return self._search_cols, (), 0
            else:
                return ("id",) + self._search_cols, self._extra_cols, 1
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
            if self._extra_cols is not None:
                for col in self._extra_cols:
                    if (col in projvals) == including:
                        extra_cols.append(col)
                    projection.pop(col, None)
            if projection: # there were extra columns requested
                raise ValueError("%s not column of %s"%(", ".join(projection), self.search_table))
        else: # iterable or basestring
            if isinstance(projection, basestring):
                projection = [projection]
            include_id = False
            for col in projection:
                if col in self._search_cols:
                    search_cols.append(col)
                elif self._extra_cols is not None and col in self._extra_cols:
                    extra_cols.append(col)
                elif col == 'id':
                    include_id = True
                else:
                    raise ValueError("%s not column of table"%col)
        if include_id or extra_cols:
            search_cols.insert(0, "id")
        return tuple(search_cols), tuple(extra_cols), 0 if (include_id or not extra_cols) else 1

    def _parse_special(self, key, value, col):
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
          - ``$contains`` -- for json columns, the given value should be a subset of the column.
          - ``$notcontains`` -- for json columns, the column must not contain any entry of the given value (which should be iterable)
          - ``$containedin`` -- for json columns, the column should be a subset of the given list
          - ``$exists`` -- if True, require not null; if False, require null.
        - ``value`` -- The value to compare to.  The meaning depends on the key.
        - ``col`` -- The name of the column.

        OUTPUT:

        - A string giving the SQL test corresponding to the requested query, with %s
        - values to fill in for the %s entries (see ``_execute`` for more discussion).

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf._parse_special("$lte", 5, "degree")
            ('degree <= %s', [5])
            sage: nf._parse_special("$or", [{"degree":{"$lte":5}},{"class_number":{"$gte":3}}], None)
            ('(degree <= %s OR class_number >= %s)', [5, 3])
            sage: nf._parse_special("$contains", [2,3,5], "ramps")
            ('ramps @> %s', [<psycopg2._json.Json object at 0x...>])
        """
        if key == '$or':
            pairs = [self._parse_dict(clause) for clause in value]
            pairs = [pair for pair in pairs if pair[0] is not None]
            if pairs:
                strings, values = zip(*pairs)
                # flatten values
                values = [item for sublist in values for item in sublist]
                return "(" + " OR ".join(strings) + ")", values
            else:
                return None, None
        elif key == '$lte':
            return "{0} <= %s".format(col), [value]
        elif key == '$lt':
            return "{0} < %s".format(col), [value]
        elif key == '$gte':
            return "{0} >= %s".format(col), [value]
        elif key == '$gt':
            return "{0} > %s".format(col), [value]
        elif key == '$ne':
            return "{0} != %s".format(col), [value]
        elif key == '$in':
            return "{0} = ANY(%s)".format(col), [value]
        elif key == '$contains':
            value = self._json_wrap(col, value)
            return "{0} @> %s".format(col), [value]
        elif key == '$notcontains':
            if col in self._json_override:
                value = [Json([v]) for v in value]
            return " AND ".join("NOT {0} @> %s".format(col) for v in value), value
        elif key == '$containedin':
            value = self._json_wrap(col, value)
            return "{0} <@ %s".format(col), [value]
        elif key == '$exists':
            if value:
                return "{0} IS NOT NULL".format(col), []
            else:
                return "{0} IS NULL".format(col), []
        else:
            raise ValueError("Error building query: {0}".format(key))

    def _parse_dict(self, D, outer=None):
        """
        Parses a dictionary that specifies a query in something close to Mongo syntax into an SQL query.

        INPUT:

        - ``D`` -- a dictionary
        - ``outer`` -- the column that we are parsing (None if not yet parsing any column).  Used in recursion.

        OUTPUT:

        - A string giving the WHERE component of an SQL query (possibly containing %s), or None if D imposes no constraint
        - A list of values to fill in for the %s in the string.  See ``_execute`` for more details.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf._parse_dict({"degree":2, "class_number":6})
            ('class_number = %s AND degree = %s', [6, 2])
            sage: nf._parse_dict({"degree":{"$gte":4,"$lte":8}, "r2":1})
            ('r2 = %s AND degree <= %s AND degree >= %s', [1, 8, 4])
            sage: nf._parse_dict({"degree":2, "$or":[{"class_number":1,"r2":0},{"disc_sign":1,"disc_abs":{"$lte":10000},"class_number":{"$lte":8}}]})
            ('(class_number = %s AND r2 = %s OR disc_sign = %s AND class_number <= %s AND disc_abs <= %s) AND degree = %s',
 [1, 0, 1, 8, 10000, 2])
            sage: nf._parse_dict({})
            (None, None)
        """
        if len(D) == 0:
            return None, None
        else:
            strings = []
            values = []
            for key, value in D.iteritems():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == '$':
                    sub, vals = self._parse_special(key, value, outer)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                elif isinstance(value, dict) and all(k.startswith('$') for k in value.iterkeys()):
                    sub, vals = self._parse_dict(value, key)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                elif '.' in key:
                    raise ValueError("Error building query: subdocuments not supported")
                else:
                    strings.append("{0} = %s".format(key))
                    values.append(self._json_wrap(key, value))
            if strings:
                return " AND ".join(strings), values
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

        - a string giving the WHERE, ORDER BY, LIMIT and OFFSET components of an SQL query, possibly including %s
        - a list of values to substitute for the %s entries

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf._build_query({"degree":2, "class_number":6})
            (' WHERE class_number = %s AND degree = %s ORDER BY degree, disc_abs, disc_sign, label', [6, 2])
            sage: nf._build_query({"class_number":1}, 20)
            (' WHERE class_number = %s ORDER BY id LIMIT 20', [1])
        """
        qstr, values = self._parse_dict(query)
        if qstr is None:
            s = ""
        else:
            s = " WHERE " + qstr
        if sort is None:
            if self._sort is None:
                if limit is not None and not (limit == 1 and offset == 0):
                    raise ValueError("You must specify a sort order")
            elif self._primary_sort in query or self._out_of_order:
                # We use the actual sort because the postgres query planner doesn't know that
                # the primary key is connected to the id.
                sort = self._sort
            else:
                sort = "id"
        else:
            sort = self._sort_str(sort)
        if sort:
            s += " ORDER BY " + sort
        if limit is not None:
            s += " LIMIT " + str(limit)
            if offset != 0:
                s += " OFFSET " + str(offset)
        return s, values

    def _search_iterator(self, cur, search_cols, extra_cols, id_offset, projection):
        """
        Returns an iterator over the results in a cursor,
        filling in columns from the extras table if needed.

        INPUT:

        - ``cur`` -- a psycopg2 cursor
        - ``search_cols`` -- the columns in the search table in the results
        - ``extra_cols`` -- the columns in the extras table in the results
        - ``id_offset`` -- 0 or 1.  Where to start in search_cols,
                           depending on whether ``id`` should be included.
        - ``projection`` -- the projection requested.

        OUTPUT:

        If projection is 0 or a string, an iterator that yields the labels/column values of the query results.
        Otherwise, an iterator that yields dictionaries with keys
        from ``search_cols`` and ``extra_cols``.
        """
        # Eventually want to batch the queries on the extras_table so that we make
        # fewer SQL queries here.
        for rec in cur:
            if projection == 0 or isinstance(projection, basestring) and not extra_cols:
                yield rec[0]
            else:
                D = {k:v for k,v in zip(search_cols[id_offset:], rec[id_offset:]) if v is not None}
                if extra_cols:
                    selector = "SELECT {0} FROM {1} WHERE id = %s".format(", ".join(extra_cols), self.extras_table)
                    extra_cur = self._execute(selector, [rec[0]])
                    extra_rec = extra_cur.fetchone()
                    for k,v in zip(extra_cols, extra_rec):
                        if v is not None:
                            D[k] = v
                if isinstance(projection, basestring):
                    yield D[projection]
                else:
                    yield D

    ##################################################################
    # Methods for querying                                           #
    ##################################################################

    def lucky(self, query, projection=2, offset=0):
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

        OUTPUT:

        If projection is 0 or a string, returns the label/column value of the first record satisfying the query.
        Otherwise, return a dictionary with keys the column names requested by the projection.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
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
            sage: nf.lucky({'label':u'6.6.409587233.1'},projection=['reg'])
            {'reg':455.191694993}
        """
        search_cols, extra_cols, id_offset = self._parse_projection(projection)
        vars = ", ".join(search_cols)
        qstr, values = self._build_query(query, 1, offset)
        selector = "SELECT {0} FROM {1}{2}".format(vars, self.search_table, qstr)
        cur = self._execute(selector, values)
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if projection == 0:
                return rec[0]
            elif extra_cols:
                id = rec[0]
                D = {k:v for k,v in zip(search_cols[id_offset:], rec[id_offset:]) if v is not None}
                vars = ", ".join(extra_cols)
                selector = "SELECT {0} FROM {1} WHERE id = %s".format(vars, self.extras_table)
                cur = self._execute(selector, [id])
                rec = cur.fetchone()
                for k,v in zip(extra_cols, rec):
                    if v is not None:
                        D[k] = v
                if isinstance(projection, basestring):
                    return D[projection]
                else:
                    return D
            elif isinstance(projection, basestring):
                return rec[0]
            else:
                return {k:v for k,v in zip(search_cols, rec) if v is not None}

    def search(self, query, projection=1, limit=None, offset=0, sort=None, info=None):
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
        - ``sort`` -- a sort order.  Either None or a list of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).  If not specified, will use the default sort order on the table.
        - ``info`` -- a dictionary, which is updated with values of 'query', 'count', 'start', 'exact_count' and 'number'.  Optional.

        WARNING:

        For tables that are split into a search table and an extras table,
        requesting columns in the extras table via this function will
        require a separate database query for EACH ROW of the result.
        This function is intended for use only on the columns in the search table.

        OUTPUT:

        If ``limit`` is None, returns an iterator over the results, yielding dictionaries with keys the columns requested by the projection (or labels/column values if the projection is 0 or a string)

        Otherwise, returns a list with the same data.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
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
        search_cols, extra_cols, id_offset = self._parse_projection(projection)
        vars = ", ".join(search_cols)
        if limit is None:
            qstr, values = self._build_query(query, sort=sort)
        else:
            nres = self.stats.quick_count(query)
            if nres is None:
                prelimit = max(limit, self._count_cutoff - offset)
                qstr, values = self._build_query(query, prelimit, offset, sort)
            else:
                qstr, values = self._build_query(query, limit, offset, sort)
        selector = "SELECT {0} FROM {1}{2}".format(vars, self.search_table, qstr)
        cur = self._execute(selector, values)
        if limit is None:
            if info is not None:
                # caller is requesting count data
                info['number'] = self.count(query)
            return self._search_iterator(cur, search_cols, extra_cols, id_offset, projection)
        if nres is None:
            exact_count = (cur.rowcount < prelimit)
            nres = offset + cur.rowcount
        else:
            exact_count = True
        res = cur.fetchmany(limit)
        res = list(self._search_iterator(res, search_cols, extra_cols, id_offset, projection))
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

    def lookup(self, label, projection=2):
        """
        Look up a record by its label.

        INPUT:

        - ``label`` -- string, the label for the desired record.
        - ``projection`` -- which columns are requested (default 2, meaning all columns).
                            See ``_parse_projection`` for more details.

        OUTPUT:

        A dictionary with keys the column names requested by the projection.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: rec = nf.lookup('8.0.374187008.1')
            sage: rec['loc_algebras']['13']
            u'x^2-13,x^2-x+2,x^4+x^2-x+2'
        """
        return self.lucky({'label':label}, projection=projection)

    def exists(self, query):
        """
        Determines whether there exists at least one record satisfying the query.

        INPUT:

        - ``query`` -- a mongo style dictionary specifying the search.
          See ``search`` for more details.

        OUTPUT:

        Boolean, whether there exists a record.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf.exists({'class_number':int(7)})
            True
        """
        return self.lucky(query, projection=1) is not None

    def random(self, projection=0):
        """
        Return a random label or record from this table.

        INPUT:

        - ``projection`` -- which columns are requested (default 0, meaning just the label).
                            See ``_parse_projection`` for more details.

        OUTPUT:

        If projection is 0, a random label from the table.
        Otherwise, a dictionary with keys specified by the projection.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf.random()
            u'2.0.294787.1'
        """
        if self.has_id:
            maxid = self.max('id')
            id = random.randint(0, maxid)
            return self.lucky({'id':id}, projection=projection)
        else:
            # We should use TABLESAMPLE in this case
            raise NotImplementedError

    ##################################################################
    # Convenience methods for accessing statistics                   #
    ##################################################################

    def max(self, col):
        """
        The maximum value attained by the given column.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: db.nf_fields.max('class_number')
            1892503075117056
        """
        return self.stats.max(col)

    def count(self, query={}):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.

        OUTPUT:

        The number of records satisfying the query.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf.count({'degree':int(6),'galt':int(7)})
            244006
        """
        return self.stats.count(query)

    ##################################################################
    # Indexes and performance analysis                               #
    ##################################################################

    def analyze(self, query, projection=1, limit=1000, offset=0, sort=None, explain_only=False):
        """
        EXAMPLES::

        sage: from lmfdb.db_backend import db
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
        search_cols, extra_cols, id_offset = self._parse_projection(projection)
        vars = ", ".join(search_cols)
        if limit is None:
            qstr, values = self._build_query(query, sort=sort)
        else:
            qstr, values = self._build_query(query, limit, offset, sort)
        selector = "SELECT {0} FROM {1}{2}".format(vars, self.search_table, qstr)
        if explain_only:
            analyzer = "EXPLAIN " + selector
        else:
            analyzer = "EXPLAIN ANALYZE " + selector
        print selector%tuple(values)
        cur = self._execute(analyzer, values, silent=True)
        for line in cur:
            print line[0]

    def _approx_cost(self, selector, values):
        """
        Determines an approximate cost for running a query using Postgres' EXPLAIN command.

        INPUT:

        - ``selector`` -- an SQL SELECT query, possibly with %s entries to be substituted.
        - ``values`` -- the values to substitute.  See the ``_execute`` method for more discussion.

        OUTPUT:

        - the query planner's approximation to the number of rows that will be returned.
        - the query planner's estimate on the amount of time the query will require, measured in disk page fetches.
        """
        explainer = "EXPLAIN (FORMAT JSON) " + selector
        cur = self._execute(explainer, values)
        try:
            plan = cur.fetchall()[0][0][0]['Plan']
        except IndexError, KeyError:
            # This doesn't happen for the queries I've tested,
            # But maybe some queries have a different format for explain?
            raise RuntimeError("Unexpected explanation")
        t = plan['Total Cost']
        if plan['Node Type'] == 'Limit' and plan.get('Plans',[]):
            nrows = plan['Plans'][0]['Plan Rows']
        else:
            nrows = plan['Plan Rows']
        return nrows, t

    def list_indexes(self):
        """
        Lists the indexes on the search table.
        """
        selector = "SELECT index_name, columns, type FROM meta_indexes WHERE table_name = %s;"
        cur = self._execute(selector, [self.search_table])
        for name, columns, typ in cur:
            print "{0} ({1}): {2}".format(name, typ, ", ".join(columns))

    def create_index(self, columns, type="btree", name=None, command=None):
        cols = [] # just column names
        colspec = [] # include DESC
        for col in columns:
            if isinstance(col, basestring):
                cols.append(col)
                colspec.append(col)
            elif command is not None:
                raise ValueError("Cannot specify both command and directions")
            else:
                if len(col) != 2:
                    raise ValueError
                if not isinstance(col[0], basestring):
                    raise ValueError("First entry must be a column")
                if col[1] == 1:
                    cols.append(col[0])
                    if type == "gin":
                        colspec.append(col[0] + " jsonb_path_ops")
                    else:
                        colspec.append(col[0])
                elif type == "gin":
                    raise ValueError("Cannot specify order using gin")
                elif col[1] == -1:
                    cols.append(col[0])
                    colspec.append(col[0] + " DESC")
                else:
                    raise ValueError("Invalid order specification %s"%(col[1]))
        for col in cols:
            if col != "id" and col not in self._search_cols:
                raise ValueError("%s not a column"%(col))
        colspec = ", ".join(colspec)
        if name is None:
            name = self.search_table + "_" + "_".join(cols)
            if type != "btree":
                name += "_" + type
        selector = "SELECT 1 FROM meta_indexes WHERE index_name = %s AND table_name = %s"
        cur = self._execute(selector, [name, self.search_table])
        if cur.rowcount > 0:
            raise ValueError("Index with that name already exists")
        if command is None:
            if type == "btree":
                command = "CREATE INDEX {0} ON {1} USING btree (%s) WITH (fillfactor='100');"
            elif type == "gin":
                command = "CREATE INDEX {0} ON {1} USING gin (%s)"
            command = command%(colspec)
        self._execute(command, commit=False)
        insertor = "INSERT INTO meta_indexes (index_name, table_name, columns, type, command) VALUES (%s, %s, %s, %s, %s);"
        self._execute(insertor, [name, self.search_table, Json(cols), type, command])

    def drop_index(self, name, permanent=False):
        if permanent:
            deleter = "DELETE FROM meta_indexes WHERE table_name = %s AND index_name = %s"
            self._execute(deleter, [self.search_table, name])
        dropper = "DROP INDEX {0}".format(name)
        self._execute(dropper)

    def drop_indexes(self, columns=[]):
        selector = "SELECT index_name FROM meta_indexes WHERE table_name = %s"
        if columns:
            selector += " AND (" + " OR ".join("columns @> %s" for _ in columns) + ")"
            columns = [Json([col]) for col in columns]
        cur = self._execute(selector, [self.search_table] + columns)
        for res in cur:
            try:
                self.drop_index(res[0])
            except Exception:
                pass

    def restore_index(self, name):
        selector = "SELECT command FROM meta_indexes WHERE table_name = %s AND index_name = %s"

    def restore_indexes(self, columns=None):
        pass

    ##################################################################
    # Insertion and updating data                                    #
    ##################################################################

    def _break_stats(self):
        """
        This function should be called when the statistics are invalidated by an insertion or update.

        Note that this function does not commit to the connection.
        """
        if self._stats_valid:
            # Only need to interact with database in this case.
            updator = "UPDATE meta_tables SET stats_valid = false WHERE name = %s"
            self._execute(updator, [self.search_table], commit=False)
            self._stats_valid = False

    def _break_order(self):
        """
        This function should be called when the id ordering is invalidated by an insertion or update.

        Note that this function does not commit to the connection.
        """
        if not self._out_of_order:
            # Only need to interact with database in this case.
            updator = "UPDATE meta_tables SET out_of_order = true WHERE name = %s"
            self._execute(updator, [self.search_table], commit=False)
            self._out_of_order = True

    def finalize_changes(self):
        # Update stats.total
        # Refresh stats targets
        # Sort and set self._out_of_order
        pass

    def upsert(self, query, data):
        """
        Update the unique row satisfying the given query, or insert a new row if no such row exists.
        If more than one row exists, raises an error.

        INPUT:

        - ``query`` -- a dictionary with key/value pairs specifying at most one row of the table.
          The most common case is that there is one key, which is either an id or a label.
        - ``data`` -- a dictionary containing key/value pairs to be set on this row.

        The keys of both inputs must be columns in either the search or extras table.
        """
        if not label or not data:
            raise ValueError("Both label and data must be nonempty")
        if "id" in data:
            raise ValueError("Cannot set id")
        for col in query:
            if col != "id" and col not in self._search_cols:
                raise ValueError("%s is not a column of %s"%(col, self.search_table))
        if self.extras_table is None:
            search_data = data
            for col in data:
                if col not in self._search_cols:
                    raise ValueError("%s is not a column of %s"%(col, self.search_table))
        else:
            search_data = {}
            extras_data = {}
            for col, val in data.items():
                if col in self._search_cols:
                    search_data[col] = self._json_wrap(col, val)
                elif col in self._extra_cols:
                    extras_data[col] = self._json_wrap(col, val)
                else:
                    raise ValueError("%s is not a column of %s"%(col, self.search_table))
        # We have to split this command into a SELECT and an INSERT statement
        # rather than using postgres' INSERT INTO ... ON CONFLICT statement
        # because we have to take different additional steps depending on whether
        # an insertion actually occurred
        qstr, values = self._parse_dict(query)
        selector = "SELECT {2} FROM {0} WHERE {1} LIMIT 2".format(self.search_table, qstr, "id" if self.has_id else "1")
        cur = self._execute(selector, values)
        cases = [(self.search_table, search_data)]
        if self.extras_table is not None:
            cases.append((self.extras_table, extras_data))
        if cur.rowcount > 1:
            raise ValueError("Query %s does not specify a unique row"%(query))
        elif cur.rowcount == 1:
            row_id = cur.fetchone()[0] # might be just 1 if has_id is False
            for table, dat in cases:
                updator = "UPDATE {0} SET ({1}) = ({2}) WHERE {3}"
                updator = updator.format(table,
                                         ", ".join(dat.keys()),
                                         ", ".join(["%s"] * len(dat)),
                                         "id = %s" if self.has_id else qstr)
                dvalues = dat.values()
                if self.has_id:
                    dvalues.append(row_id)
                else:
                    dvalues.extend(values)
                self._execute(updator, dvalues, commit=False)
            if not self._out_of_order and any(key in self._sort_keys for key in data):
                self._break_order()
        else:
            if self.has_id and ("id" in data or "id" in query):
                raise ValueError("Cannot specify an id for insertion")
            for col, val in query.items():
                if col not in search_data:
                    search_data[col] = val
            # We use the total on the stats object for the new id.  If someone else
            # has inserted data this will be a problem,
            # but it will raise an error rather than leading to invalid database state,
            # so it should be okay.
            if self.has_id:
                search_data["id"] = self.stats.total
                if self.extras_table is not None:
                    extras_data["id"] = self.stats.total
            for table, dat in cases:
                insertor = "INSERT INTO {0} ({1}) VALUES ({2})".format(table,
                                                                       ", ".join(dat.keys()),
                                                                       ", ".join(["%s"] * len(dat)))
                self._execute(insertor, dat.values(), commit=False)
            self._break_order()
            self.stats.total += 1
        self._break_stats()
        self.conn.commit()

    def insert_many(self, search_data, extras_data=None, drop_indexes=False):
        """
        Insert multiple rows.

        This function will be faster than repeated ``upsert`` calls, but slower than ``copy_from``

        INPUT:

        - ``search_data`` -- a list of dictionaries, whose keys are columns and values the values to be set
          in the search table.  All dictionaries should have the same set of keys;
          if this assumption is broken, some values may be set to their default values
          instead of the desired value, or an error may be raised.
        - ``extras_data`` -- a list of dictionaries with data to be inserted into the extras table.
          Must be present, and of the same length as search_data, if the extras table exists.
        - ``drop_indexes`` -- boolean (default False). Whether to drop the indexes
          before insertion and restore afterward.  Note that if there is an exception during insertion
          the indexes will need to be restored manually using ``restore_indexes``.

        If the search table has an id, the dictionaries will be updated with the ids of the inserted records,
        though note that those ids will change if the ids are resorted.
        """
        if not search_data:
            raise ValueError("No data provided")
        if (extras_data is None) != (self.extras_table is None):
            raise ValueError("extras_data must be present iff extras_table is")
        if extras_data is not None and len(search_data) != len(extras_data):
            raise ValueError("search_data and extras_data must have same length")
        if drop_indexes:
            self.drop_indexes()
        cases = [(self.search_table, search_data)]
        if self.has_id:
            for i, SD in enumerate(search_data):
                SD["id"] = self.stats.total + i
        if extras_data is not None:
            cases.append((self.extras_table, extras_data))
            for i, ED in enumerate(extras_data):
                ED["id"] = self.stats.total + i
        for table, L in cases:
            template = "(" + ", ".join("%({0})s".format(col) for col in L[0].keys()) + ")"
            insertor = "INSERT INTO {0} ({1}) VALUES %s".format(table, ", ".join(L[0].keys()))
            self._execute(insertor, L, silent=True, values_list=True, template=template, commit=False)
        self._break_order()
        self._break_stats()
        self.stats.total += len(search_data)
        self.conn.commit()
        if drop_indexes:
            self.restore_indexes()

    def copy_from(self, filename, appendix=None, tmp_table=False, includes_ids=None, drop_indexes=None, sort=False, **kwds):
        """
        Efficiently copy data from a file into the database.

        INPUT:

        - ``filename`` -- a string, the file to import
        - ``appendix`` -- a string ("extras", "counts", "stats"), used when copying into an auxiliary table.
        - ``tmp_table`` -- boolean (default False), whether to create a temporary table to load the data, before renaming the current and new tables to do the actual swap.
        - ``includes_ids`` -- whether the file includes ids as the first column.
            If so, the ids should be contiguous, starting immediately after the current max id.
            If ids are provided, if this table is id_ordered, and if this table
            currently contains no data, the ids should be in sorted order
            (since the metadata will reflect this assumption after the import).
            If the file does not include ids, and this table has ids, the user must have write permission
            to the file's directory: the filename with "_with_ids" will be used as a temporary file.
        - ``drop_indexes`` -- whether to drop the indexes before importing data and rebuild them afterward.
        - ``kwds`` -- passed on to psycopg2's ``copy_from``.  Notably, ``columns`` allows one
            to specify the order of columns in the file; the default is self._search_cols/self._extra_cols.
        """
        if appendix is None:
            table = self.search_table
            cols = list(self._search_cols)
            if self.has_id:
                cols.insert(0, "id")
        elif appendix == "extras":
            if self.extras_table is None:
                raise ValueError("No extras table")
            table = self.extras_table
            cols = ["id"] + self._extra_cols
        elif appendix == "counts":
            table = self.stats.counts
            cols = ["cols", "values", "count"]
        elif appendix == "stats":
            table = self.stats.stats
            cols = ["cols", "stat", "value", "constraint_cols", "constraint_values", "threshold"]
        else:
            raise ValueError("Unrecognized appendix")
        if not includes_ids:
            idfile = filename + "_with_ids"
            if os.path.exists(idfile):
                raise ValueError("Would overwrite existing file")
            sep = kwds.get("sep", u"\t")
            with open(filename) as F:
                with open(idfile, 'w') as Fid:
                    for i, line in enumerate(F):
                        Fid.write((unicode(i + self.stats.total) + sep + line).encode("utf-8"))
        else:
            idfile = filename
        kwds = dict(kwds)
        kwds["columns"] = kwds.get("columns", cols)
        cur = self.conn.cursor()
        with open(idfile) as Fid:
            try:
                cur.copy_from(Fid, table, **kwds)
            except Exception:
                self.conn.rollback()
                raise
        if not (includes_ids and self._id_ordered and self.stats.total == 0):
            self._break_order()
        self._break_stats()
        self.stats.total += cur.rowcount
        self.conn.commit()

    def copy_to(self, filename, appendix=None, include_ids=False, **kwds):
        """
        Efficiently copy data from the database to a file.

        INPUT:

        - ``filename`` -- a string, the file to export
        - ``appendix`` -- a string ("extras", "counts", "stats"), used when copying from an auxiliary table.
        - ``include_ids`` -- whether to include the id column.  Note that this keyword differs from that in ``copy_from`` (no "s")
        - ``kwds`` -- passed on to pscyopg2's ``copy_to``.  Notably, ``columns`` allows one
            to specify the order of columns in the file; the default is self._search_cols/self._extra_cols.
        """
        if appendix is None:
            table = self.search_table
            cols = list(self._search_cols)
            if self.has_id:
                cols.insert(0, "id")
        elif appendix == "extras":
            if self.extras_table is None:
                raise ValueError("No extras table")
            table = self.extras_table
            cols = list(self._extra_cols)
            if include_ids:
                cols.insert(0, "id")
        elif appendix == "counts":
            table = self.stats.counts
            cols = ["cols", "values", "count"]
        elif appendix == "stats":
            table = self.stats.stats
            cols = ["cols", "stat", "value", "constraint_cols", "constraint_values", "threshold"]
        else:
            raise ValueError("Unrecognized appendix")
        kwds = dict(kwds)
        kwds["columns"] = kwds.get("columns", cols)
        cur = self.conn.cursor()
        with open(filename, "w") as F:
            try:
                cur.copy_to(filename, table, **kwds)
            except Exception:
                self.conn.rollback()
                raise
        self.conn.commit()

class PostgresStatsTable(PostgresBase):
    # We cache this for quick counting
    empty_json_list = Json([])

    def __init__(self, table):
        PostgresBase.__init__(self, table.search_table, table.conn)
        self.table = table
        self.search_table = st = table.search_table
        self.stats = st + "_stats"
        self.counts = st + "_counts"
        self.total = self.quick_count({})
        if self.total is None:
            self.total = self._slow_count({}, record=True)

    def _has_stats(self, jcols, ccols, cvals, threshold):
        values = [jcols, "total"]
        if ccols is None:
            ccols = "constraint_cols IS NULL"
            cvals = "constraint_values IS NULL"
        else:
            values.extend([ccols, cvals])
            ccols = "constraint_cols = %s"
            cvals = "constraint_values = %s"
        if threshold is None:
            threshold = "threshold IS NULL"
        else:
            values.append(threshold)
            threshold = "threshold = %s"
        selector = "SELECT 1 FROM {0} WHERE cols = %s AND stat = %s AND {1} AND {2} AND {3}".format(self.stats, ccols, cvals, threshold)
        cur = self._execute(selector, values)
        return cur.rowcount > 0

    def quick_count(self, query):
        """
        Tries to quickly determine the number of results for a given query
        using the count table.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.

        OUTPUT:

        Either an integer giving the number of results, or None if not cached.
        """
        cols, vals = self._split_dict(query)
        selector = "SELECT count FROM {0} WHERE cols = %s AND values = %s;".format(self.counts)
        cur = self._execute(selector, [cols, vals])
        if cur.rowcount:
            return int(cur.fetchone()[0])

    def _slow_count(self, query, record=False):
        """
        No shortcuts: actually count the rows in the search table.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``record`` -- boolean (default False).  Whether to store the result in the count table.

        OUTPUT:

        The number of rows in the search table satisfying the query.
        """
        selector = "SELECT COUNT(*) FROM " + self.search_table
        qstr, values = self.table._parse_dict(query)
        if qstr is not None:
            selector += " WHERE " + qstr
        cur = self._execute(selector, values)
        nres = cur.fetchone()[0]
        if record:
            cols, vals = self._split_dict(query)
            if self.quick_count(query) is None:
                updator = "INSERT INTO {0} (count, cols, values) VALUES (%s, %s, %s);".format(self.counts)
            else:
                updator = "UPDATE {0} SET count = %s WHERE cols = %s AND values = %s;".format(self.counts)
            self._execute(updator, [nres, cols, vals])
        return nres

    def count(self, query={}):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.

        OUTPUT:

        The number of records satisfying the query.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: nf = db.nf_fields
            sage: nf.stats.count({'degree':int(6),'galt':int(7)})
            244006
        """
        if not query:
            return self.total
        nres = self.quick_count(query)
        if nres is None:
            nres = self._slow_count(query)
        return int(nres)

    def max(self, col):
        """
        The maximum value attained by the given column, which must be in the search table.

        EXAMPLES::

            sage: from lmfdb.db_backend import db
            sage: db.nf_fields.stats.max('class_number')
            1892503075117056
        """
        if col == "id":
            # We just use the count in this case
            return self.count() - 1
        if col not in self.table._search_cols:
            raise ValueError("%s not a column of %s"%(col, self.search_table))
        jcol = Json([col])
        cur = self._execute("SELECT value FROM {0} WHERE stat = %s AND cols = %s AND threshold IS NULL AND constraint_cols IS NULL".format(self.stats), ["max", jcol])
        if cur.rowcount:
            return cur.fetchone()[0]
        cur = self._execute("SELECT {0} FROM {1} ORDER BY {0} DESC LIMIT 1".format(col, self.search_table))
        m = cur.fetchone()[0]
        if m is None:
            # the default order ends with NULLs, so we now have to use NULLS LAST,
            # preventing the use of indexes.
            cur = self._execute("SELECT {0} FROM {1} ORDER BY {0} DESC NULLS LAST LIMIT 1".format(col, self.search_table))
            m = cur.fetchone()[0]
        try:
            self._execute("INSERT INTO {0} (cols, stat, value) VALUES (%s, %s, %s)", [jcol, "max", m])
        except Exception:
            pass
        return m

    def _split_buckets(self, buckets, constraint, include_upper=True):
        expanded_buckets = []
        for col, divisions in buckets.items():
            expanded_buckets.append([])
            if len(divisions) < 2:
                raise ValueError
            divisions = [None] + sorted(divisions) + [None]
            for a,b,c,d in zip(divisions[:-3],divisions[1:-2],divisions[2:-1],divisions[3:]):
                if b == c:
                    expanded_buckets[-1].append({col:b})
                else:
                    if include_upper:
                        gt = True
                        lt = (c == d)
                    else:
                        lt = True
                        gt = (a == b)
                    expanded_buckets[-1].append({col:{"$gt" if gt else "$gte": b,
                                                      "$lt" if lt else "$lte": c}})
        for X in cartesian_product_iterator(expanded_buckets):
            bucketed_constraint = dict(constraint) # copy
            for D in X:
                bucketed_constraint.update(D)
            yield bucketed_constraint

    def add_bucketed_counts(self, cols, buckets, constraint={}, include_upper=True):
        # Need to check that the buckets cover all cases.
        for bucketed_constraint in self._split_buckets(buckets, constraint, include_upper):
            self.add_stats(cols, bucketed_constraint)

    def _split_dict(self, D):
        if D:
            return map(Json, zip(*sorted(D.items())))
        else:
            return self.empty_json_list, self.empty_json_list

    def add_stats(self, cols, constraint=None, threshold=None):
        cols = sorted(cols)
        jcols = Json(cols)
        where, values, ccols, cvals = " WHERE " + " AND ".join("{0} IS NOT NULL".format(col) for col in cols), [], None, None
        if constraint is None:
            allcols = cols
        else:
            # We need to include the constraints in the count table if we're not grouping by that column
            allcols = sorted(list(set(cols + constraint.keys())))
            if any(key.startswith('$') for key in constraint.keys()):
                raise ValueError("Top level special keys not allowed")
            ccols, cvals = self._split_dict(constraint)
            qstr, values = self.table._parse_dict(constraint)
            if qstr is not None:
                where = where + " AND " + qstr
        if self._has_stats(jcols, ccols, cvals, threshold):
            return
        self.logger.info("Adding stats for {0} ({1})".format(", ".join(cols), "no threshold" if threshold is None else "threshold = %s"%threshold))
        having = ""
        if threshold is not None:
            having = " HAVING COUNT(*) >= {0}".format(threshold)
        if cols:
            vars = ", ".join(cols)
            groupby = " GROUP BY {0}".format(vars)
            vars += ", COUNT(*)"
        else:
            vars = "COUNT(*)"
            groupby = ""
            if not allcols:
                where = ""
        selector = "SELECT {vars} FROM {table}{where}{groupby}{having}".format(vars=vars, table=self.search_table, groupby=groupby, where=where, having=having)
        cur = self._execute(selector, values, silent=True)
        to_add = []
        total = 0
        onenumeric = False # whether we're grouping by a single numeric column
        if len(cols) == 1:
            col = cols[0]
            stypes, etypes = self.table._col_types()
            if stypes.get(col) in ["numeric", "bigint", "integer", "smallint", "double precision"]:
                onenumeric = True
                avg = 0
                mn = None
                mx = None
        jallcols = Json(allcols)
        for countvec in cur:
            colvals, count = countvec[:-1], countvec[-1]
            if constraint is None:
                allcolvals = map(prep_json, colvals)
            else:
                allcolvals = []
                i = 0
                for col in allcols:
                    if col in cols:
                        allcolvals.append(prep_json(colvals[i]))
                        i += 1
                    else:
                        allcolvals.append(prep_json(constraint[col]))
            to_add.append((jallcols, Json(allcolvals), count))
            total += count
            if onenumeric:
                val = colvals[0]
                avg += val * count
                if mn is None or val < mn:
                    mn = val
                if mx is None or val > mx:
                    mx = val
        stats = [(jcols, "total", total, ccols, cvals, threshold)]
        if onenumeric:
            avg = float(avg) / total
            stats.append((jcols, "avg", avg, ccols, cvals, threshold))
            stats.append((jcols, "min", mn, ccols, cvals, threshold))
            stats.append((jcols, "max", mx, ccols, cvals, threshold))
        # Note that the cols in the stats table does not add the constraint columns, while in the counts table it does.
        self._execute("INSERT INTO {0} (cols, stat, value, constraint_cols, constraint_values, threshold) VALUES %s;".format(self.stats), stats, values_list=True, silent=True)
        self._execute("INSERT INTO {0} (cols, values, count) VALUES %s;".format(self.counts), to_add, values_list=True, silent=True)

    def _get_values_counts(self, cols, constraint):
        selector_constraints = ["cols = %s"]
        if constraint:
            allcols = sorted(list(set(cols + constraint.keys())))
            positions = [allcols.index(x) for x in cols]
            selector_values = [Json(allcols)]
            for i, x in enumerate(allcols):
                if x in constraint:
                    selector_constraints.append("values->{0} = %s".format(i))
                    selector_values.append(Json(constraint[x]))
        else:
            selector_values = [Json(cols)]
            positions = range(len(cols))
        selector = "SELECT values, count FROM {0} WHERE {1}".format(self.counts, " AND ".join(selector_constraints))
        return [([values[i] for i in positions], int(count)) for values, count in self._execute(selector, values = selector_values)]

    def _get_total_avg(self, cols, constraint, include_avg):
        totaler = "SELECT value FROM {0} WHERE cols = %s AND stat = %s AND threshold IS NULL".format(self.stats)
        if constraint:
            ccols, cvals = self._split_dict(constraint)
            totaler += " AND constraint_cols = %s AND constraint_values = %s;"
            totaler_values = [Json(cols), "total", ccols, cvals]
        else:
            totaler += " AND constraint_cols IS NULL;"
            totaler_values = [Json(cols), "total"]
        cur_total = self._execute(totaler, values = totaler_values)
        if cur_total.rowcount == 0:
            raise ValueError("Database does not contain stats for %s"%(cols[0],))
        total = cur_total.fetchone()[0]
        if include_avg:
            # Modify totaler_values in place since query for avg is very similar
            totaler_values[1] = "avg"
            cur_avg = self._execute(totaler, values = totaler_values)
            avg = cur_avg.fetchone()[0]
        else:
            avg = None
        return total, avg

    def display_data(self, cols, base_url, constraint=None, include_avg=False, formatter=None, buckets = None, include_upper=True, query_formatter=None, count_key='count'):
        if formatter is None:
            formatter = lambda x: x
        if len(cols) == 1 and buckets is None:
            if query_formatter is None:
                query_formatter = lambda x: str(x)
            col = cols[0]
            total, avg = self._get_total_avg(cols, constraint, include_avg)
            data = [(values[0], count) for values, count in self._get_values_counts(cols, constraint)]
            data.sort()
        elif len(cols) == 0 and buckets is not None and len(buckets) == 1:
            if include_avg:
                raise ValueError
            if query_formatter is None:
                def query_formatter(x):
                    if isinstance(x, dict):
                        a = x.get('$gte',x['$gt']+1)
                        b = x.get('$lte',x['$lt']-1)
                        return "{0}-{1}".format(a,b)
                    return str(x)
            col = buckets.keys()[0]
            total = 0
            data = []
            for bucketed_constraint in self._split_buckets(buckets, constraint, include_upper):
                L = self._get_values_counts(cols, bucketed_constraint)
                if len(L) != 1:
                    raise RuntimeError
                count = L[0][1]
                data.append((bucketed_constraint[col], count))
                total += count
        data = [{'value':formatter(value),
                 count_key:count,
                 'query':"{0}?{1}={2}".format(base_url, col, query_formatter(value)),
                 'proportion':format_percentage(count, total)}
                for value, count in data]
        if include_avg:
            data.append({'value':'\(\\mathrm{avg}\\ %.2f\)'%avg,
                         count_key:total,
                         'query':"{0}?{1}".format(base_url, cols[0]),
                         'proportion':format_percentage(1,1)})
        return data

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

        sage: from lmfdb.db_backend import db
        sage: db
        Interface to Postgres database
        sage: db.conn
        <connection object at 0x...>
        sage: db.tablenames[:3]
        ['artin_field_data', 'artin_reps', 'av_fqisog']
        sage: db.av_fqisog
        Interface to Postgres table av_fqisog
    """
    def __init__(self):
        PostgresBase.__init__(self, 'db_all', connect(dbname="lmfdb", user="lmfdb", password="LMFDB5077simons"))
        # We want to use unicode everywhere
        register_type(UNICODE, self.conn)
        register_type(UNICODEARRAY, self.conn)
        cur = self._execute("SELECT NULL::numeric")
        oid = cur.description[0][1]
        NUMERIC = new_type((oid,), "NUMERIC", numeric_converter)
        register_type(NUMERIC, self.conn)
        register_adapter(Integer, AsIs)
        cur = self._execute("SELECT name, sort, capitalization, count_cutoff, id_ordered, out_of_order, has_extras, stats_valid FROM meta_tables")
        self.tablenames = []
        for tabledata in cur:
            tablename = tabledata[0]
            ## Skip until fixed
            if tablename in ('mwf_coeffs', 'mwf_forms', 'mwf_plots', 'smf_samples', 'sl2z_subgroups'):
                continue
            self.__dict__[tablename] = PostgresTable(self, *tabledata)
            self.tablenames.append(tablename)

    def __repr__(self):
        return "Interface to Postgres database"

    def create_new_table(self, name, columns, sort=None, id_ordered=False, extra_columns=None):
        """
        Add a new search table to the database.

        INPUT:

        - ``name`` -- the name of the table.  See existing names for consistency.
        - ``columns`` -- a dictionary whose keys are valid postgres types and whose values are lists
            of column names (or just a string if only one column has the specified type).
            An id column of type bigint will be added if either id_ordered is set or
            extra_columns are specified.
        - ``sort`` -- If not None, provides a default sort order for the table, in formats accepted by
            the ``_sort_str`` method.
        - ``id_ordered`` -- boolean (default False).  If set, the table will be sorted by id when
            pushed to production, speeding up some kinds of search queries.
        - ``extra_columns`` -- a dictionary in the same format as the columns dictionary.
            If present, will create a second table (the name with "_extras" appended), linked by
            an id column.  Data in this table cannot be searched on, but will also not appear
            in the search table, speeding up scans.

        NOTE:

        For collatable types (text, char and varchar) we add 'COLLATE "C"' to the postgres type for speed,
        since most text data in the LMFDB doesn't need locale-specific sorting.  If a different collation
        is desired, you can specify it in the type itself (e.g. 'text COLLATE "en_US.UTF-8"')

        Beware that some mathematical terms (e.g. group and order) are postgres keywords and must be avoided.

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
        valid_sort_list = sum(columns.values(),[])
        valid_sort_set = set(valid_sort_list)
        # Check that columns aren't listed twice
        if len(valid_sort_list) != len(valid_sort_set):
            from collections import Counter
            C = Counter(valid_sort_list)
            raise ValueError("Column %s repeated"%(C.most_common(1)[0][0]))
        # Check that sort is valid
        if sort is not None:
            for col in sort:
                if isinstance(col, tuple):
                    if len(col) != 2:
                        raise ValueError("Sort terms must be either strings or pairs")
                    if col[1] not in [1, -1]:
                        raise ValueError("Sort terms must be of the form (col, 1) or (col, -1)")
                    col = col[0]
                if col not in valid_sort_set:
                    raise ValueError("Column %s does not exist"%(col))
            sort = Json(sort)
        # caps will be updated by process_columns
        caps = []
        def process_columns(coldict):
            allcols = []
            hasid = False
            for typ, cols in coldict.items():
                if typ in ('text','char','varchar'):
                    typ = typ + ' COLLATE "C"'
                if isinstance(cols, basestring):
                    cols = [cols]
                for col in cols:
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                        raise ValueError("Invalid column name")
                    if col != col.lower():
                        caps.append(col)
                    if col == 'id':
                        hasid = True
                    allcols.append("{0} {1}".format(col, typ))
            if (not hasid) and (id_ordered or extra_columns is not None):
                allcols.insert(0,"id bigint")
            return allcols
        columns = process_columns(columns)
        creator = 'CREATE TABLE {0} ({1});'.format(name, ", ".join(columns))
        self._execute(creator)
        if extra_columns is not None:
            extra_columns = process_columns(extra_columns)
            creator = 'CREATE TABLE {0}_extras ({1});'.format(name, ", ".join(extra_columns))
        creator = 'CREATE TABLE {0}_counts (cols jsonb, values jsonb, count bigint);'.format(name)
        self._execute(creator)
        creator = 'CREATE TABLE {0}_stats (cols jsonb, stat text COLLATE "C", value numeric, constraint_cols jsonb, constraint_values jsonb, threshold integer);'.format(name)
        self._execute(creator)
        insertor = 'INSERT INTO meta_tables (name, sort, capitalization, id_ordered, out_of_order, has_extras) VALUES (%s, %s, %s, %s, %s, %s);'
        self._execute(insertor, [name, sort, Json(caps), id_ordered, not id_ordered, extra_columns is not None])

db = PostgresDatabase()
