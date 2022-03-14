# -*- coding: utf-8 -*-
import random
import time
from itertools import islice

from psycopg2.extensions import cursor as pg_cursor

from psycopg2.sql import SQL, Identifier, Literal

from .base import number_types
from .table import PostgresTable
from .encoding import Json
from .utils import IdentifierWrapper, DelayCommit, filter_sql_injection, postgres_infix_ops


class PostgresSearchTable(PostgresTable):
    ##################################################################
    # Helper functions for querying                                  #
    ##################################################################

    def _parse_projection(self, projection):
        """
        Parses various ways of specifying which columns are desired.

        INPUT:

        - ``projection`` -- either 0, 1, 2, 3, a dictionary or list of column names.

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
                raise RuntimeError("No label column for %s" % (self.search_table))
            return (self._label_col,), ()
        elif not projection:
            raise ValueError("You must specify at least one key.")
        if projection == 1:
            return tuple(self.search_cols), ()
        elif projection == 2:
            return tuple(self.search_cols), tuple(self.extra_cols)
        elif projection == 3:
            return tuple(["id"] + self.search_cols), tuple(self.extra_cols)
        elif isinstance(projection, dict):
            projvals = set(bool(val) for val in projection.values())
            if len(projvals) > 1:
                raise ValueError("You cannot both include and exclude.")
            including = projvals.pop()
            include_id = projection.pop("id", False)
            for col in self.search_cols:
                if (col in projection) == including:
                    search_cols.append(col)
                projection.pop(col, None)
            for col in self.extra_cols:
                if (col in projection) == including:
                    extra_cols.append(col)
                projection.pop(col, None)
            if projection:  # there were more columns requested
                raise ValueError("%s not column of %s" % (", ".join(projection), self.search_table))
        else:  # iterable or str
            if isinstance(projection, str):
                projection = [projection]
            include_id = False
            for col in projection:
                colname = col.split("[", 1)[0]
                if colname in self.search_cols:
                    search_cols.append(col)
                elif colname in self.extra_cols:
                    extra_cols.append(col)
                elif col == "id":
                    include_id = True
                else:
                    raise ValueError("%s not column of %s" % (col, self.search_table))
        if include_id:
            search_cols.insert(0, "id")
        return tuple(search_cols), tuple(extra_cols)

    def _create_typecast(self, key, value, col, col_type):
        """
        This method is used to add typecasts to queries when necessary.
        It is called from `_parse_special` and `_parse_dict`; see the documentation
        of those functions for inputs.
        """
        if col_type == "smallint[]" and key in ["$contains", "$containedin"]:
            # smallint[] requires a typecast to test containment
            return "::int[]"
        if col_type.endswith("[]") and key in ["$eq", "$ne", "$contains", "$containedin"]:
            if isinstance(col, Identifier):
                return "::" + col_type
            else:
                # Selected a path
                return "::" + col_type[:-2]
        return ""

    def _parse_special(self, key, value, col, col_type):
        """
        Implements more complicated query conditions than just testing for equality:
        inequalities, containment and disjunctions.

        INPUT:
        - ``key`` -- a code starting with $ from the following list:
            - ``$and`` -- and
            - ``$or`` -- or
            - ``$not`` -- not
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
            - ``$overlaps`` -- the column should overlap the given array
            - ``$exists`` -- if True, require not null; if False, require null.
            - ``$startswith`` -- for text columns, matches strings that start with the given string.
            - ``$like`` -- for text columns, matches strings according to the LIKE operand in SQL.
            - ``$ilike`` -- for text columns, matches strings according to the ILIKE, the case-insensitive version of LIKE in PostgreSQL.
            - ``$regex`` -- for text columns, matches the given regex expression supported by PostgresSQL
            - ``$raw`` -- a string to be inserted as SQL after filtering against SQL injection
        - ``value`` -- The value to compare to.  The meaning depends on the key.
        - ``col`` -- The name of the column, wrapped in SQL
        - ``col_type`` -- the SQL type of the column

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
        if key in ["$or", "$and"]:
            pairs = [
                self._parse_dict(clause, outer=col, outer_type=col_type)
                for clause in value
            ]
            if key == "$or" and any(pair[0] is None for pair in pairs):
                # If any of the pairs is None, then we should not filter anything
                return None, None
            pairs = [pair for pair in pairs if pair[0] is not None]
            if pairs:
                strings, values = zip(*pairs)
                # flatten values
                values = [item for sublist in values for item in sublist]
                joiner = " OR " if key == "$or" else " AND "
                return SQL("({0})").format(SQL(joiner).join(strings)), values
            else:
                return None, None
        elif key == "$not":
            negated, values = self._parse_dict(value, outer=col, outer_type=col_type)
            if negated is None:
                return SQL("%s"), [False]
            else:
                return SQL("NOT ({0})").format(negated), values

        # First handle the cases that have unusual values
        if key == "$exists":
            if value:
                cmd = SQL("{0} IS NOT NULL").format(col)
            else:
                cmd = SQL("{0} IS NULL").format(col)
            value = []
        elif key == "$notcontains":
            if col_type == "jsonb":
                cmd = SQL(" AND ").join(SQL("NOT {0} @> %s").format(col) * len(value))
                value = [Json(v) for v in value]
            else:
                cmd = SQL(" AND ").join(SQL("NOT (%s = ANY({0}))").format(col) * len(value))
        elif key == "$mod":
            if not (isinstance(value, (list, tuple)) and len(value) == 2):
                raise ValueError("Error building modulus operation: %s" % value)
            # have to take modulus twice since MOD(-1,5) = -1 in postgres
            cmd = SQL("MOD(%s + MOD({0}, %s), %s) = %s").format(col)
            value = [value[1], value[1], value[1], value[0] % value[1]]
        elif key == "$raw":
            cmd, value = filter_sql_injection(value, col, col_type, "=", self)
        elif isinstance(value, dict) and len(value) == 1 and "$raw" in value:
            # We support queries like {'abvar_count':{'$lte':{'$raw':'q^g'}}}
            if key in postgres_infix_ops:
                cmd, value = filter_sql_injection(value, col, col_type, postgres_infix_ops[key], self)
            else:
                raise ValueError("Error building query: {0} (in $raw)".format(key))
        else:
            if key in postgres_infix_ops:
                cmd = SQL("{0} " + postgres_infix_ops[key] + " %s")
            # FIXME, we should do recursion with _parse_special
            elif key == "$maxgte":
                cmd = SQL("array_max({0}) >= %s")
            elif key == "$anylte":
                cmd = SQL("%s >= ANY({0})")
            elif key == "$in":
                if col_type == "jsonb":
                    # jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("{0} <@ %s")
                else:
                    cmd = SQL("{0} = ANY(%s)")
            elif key == "$nin":
                if col_type == "jsonb":
                    # jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("NOT ({0} <@ %s)")
                else:
                    cmd = SQL("NOT ({0} = ANY(%s)")
            elif key == "$contains":
                cmd = SQL("{0} @> %s")
                if col_type != "jsonb":
                    value = [value]
            elif key == "$containedin":
                # jsonb_path_ops modifiers for the GIN index doesn't support this query
                cmd = SQL("{0} <@ %s")
            elif key == "$overlaps":
                if col_type == "jsonb":
                    # jsonb doesn't support &&
                    # We could convert it to a giant conjunction, but that leads to very bad performance
                    raise ValueError("Jsonb columns do not support $overlaps")
                cmd = SQL("{0} && %s")
            elif key == "$startswith":
                cmd = SQL("{0} LIKE %s")
                value = value.replace("_", r"\_").replace("%", r"\%") + "%"
            else:
                raise ValueError("Error building query: {0}".format(key))
            if col_type == "jsonb":
                value = Json(value)
            cmd = cmd.format(col)
            # For some array types (e.g. numeric), operators such as = and @> can't automatically typecast so we have to do it manually.
            typecast = self._create_typecast(key, value, col, col_type)
            if typecast:
                cmd += SQL(typecast)
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
            sage: db.nf_fields._parse_dict({})
            []
            sage: db.lfunc_lfunctions._parse_values({'bad_lfactors':[1,2]})[1][0]
            '[1, 2]'
            sage: db.char_dir_values._parse_values({'values':[1,2]})
            [1, 2]
        """

        return [Json(val) if self.col_type[key] == "jsonb" else val for key, val in D.items()]

    def _parse_dict(self, D, outer=None, outer_type=None):
        """
        Parses a dictionary that specifies a query in something close to Mongo syntax into an SQL query.

        INPUT:

        - ``D`` -- a dictionary, or a scalar if outer is set
        - ``outer`` -- the column that we are parsing (None if not yet parsing any column).  Used in recursion.  Should be wrapped in SQL.
        - ``outer_type`` -- the SQL type for the outer column

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
            if outer_type == "jsonb":
                D = Json(D)
            return SQL("{0} = %s").format(outer), [D]
        if len(D) == 0:
            return None, None
        else:
            strings = []
            values = []
            for key, value in D.items():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == "$":
                    sub, vals = self._parse_special(key, value, outer, col_type=outer_type)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                    continue
                if "." in key:
                    path = [int(p) if p.isdigit() else p for p in key.split(".")]
                    key = path[0]
                    if self.col_type.get(key) == "jsonb":
                        path = [SQL("->{0}").format(Literal(p)) for p in path[1:]]
                    else:
                        path = [SQL("[{0}]").format(Literal(p)) for p in path[1:]]
                else:
                    path = None
                if key != "id" and key not in self.search_cols:
                    raise ValueError("%s is not a column of %s" % (key, self.search_table))
                # Have to determine whether key is jsonb before wrapping it in Identifier
                col_type = self.col_type[key]
                if path:
                    key = SQL("{0}{1}").format(Identifier(key), SQL("").join(path))
                else:
                    key = Identifier(key)
                if isinstance(value, dict) and all(k.startswith("$") for k in value):
                    sub, vals = self._parse_dict(value, key, outer_type=col_type)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                    continue
                if value is None:
                    strings.append(SQL("{0} IS NULL").format(key))
                else:
                    if col_type == "jsonb":
                        value = Json(value)
                    cmd = "{0} = %s" + self._create_typecast("$eq", value, key, col_type)
                    strings.append(SQL(cmd).format(key))
                    values.append(value)
            if strings:
                return SQL(" AND ").join(strings), values
            else:
                return None, None

    def _columns_searched(self, D):
        """
        The list of columns included in a search query
        """
        if isinstance(D, list): # can happen recursively in $or queries
            return sum((self._columns_searched(part) for part in D), [])
        L = []
        for key, value in D.items():
            if key in ["$not", "$and", "$or"]:
                L.extend(self._columns_searched(value))
            else:
                if "." in key:
                    key = key.split(".")[0]
                if key in self.search_cols:
                    L.append(key)
        return sorted(set(L))

    def _process_sort(self, query, limit, offset, sort):
        """
        OUTPUT:

        - a Composed object for use in a PostgreSQL query
        - a boolean indicating whether the results are being sorted
        - a list of columns or pairs, as input into the search method
        """
        if sort is None:
            has_sort = True
            if self._sort is None:
                if limit is not None and not (limit == 1 and offset == 0):
                    sort = Identifier("id")
                    raw = ["id"]
                else:
                    has_sort = False
                    raw = []
            elif self._primary_sort in query or self._out_of_order:
                # The first precedence is a hack to prevent sequential scans
                # Thus, we use the actual sort because the postgres query planner doesn't know that
                # the primary key is connected to the id.
                #
                # Also, if id_ordered = False, then out_of_order = False
                sort = self._sort
                raw = self._sort_orig
            else:
                sort = Identifier("id")
                raw = ["id"]
            return sort, has_sort, raw
        else:
            return self._sort_str(sort), bool(sort), sort

    def _build_query(self, query, limit=None, offset=0, sort=None, raw=None, one_per=None, raw_values=[]):
        """
        Build an SQL query from a dictionary, including limit, offset and sorting.

        INPUT:

        - ``query`` -- a dictionary query, in the mongo style (but only supporting certain special operators, as in ``_parse_special``)
        - ``limit`` -- a limit on the number of records returned
        - ``offset`` -- an offset on how many records to skip
        - ``sort`` -- a sort order (to be passed into the ``_sort_str`` method, or None.
        - ``one_per`` -- a list of columns.  If provided, only one result will be included with each given set of values for those columns (the first according to the provided sort order).
        - ``raw`` -- a string to be used as the WHERE clause.  DO NOT USE WITH INPUT FROM THE WEBSITE

        OUTPUT:

        If ``one_per`` is provided,

        - an SQL Composable giving the WHERE component for the inner portion of a nested SQL query, possibly including %s
        - an SQL Composable giving the ORDER BY, LIMIT and OFFSET components for the outer portion of a nested SQL query
        - a list of values to substitute for the %s entries

        Otherwise,

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
        if raw is None:
            qstr, values = self._parse_dict(query)
        else:
            qstr, values = SQL(raw), raw_values
        if qstr is None:
            where = SQL("")
            values = []
        else:
            where = SQL(" WHERE {0}").format(qstr)
        sort, has_sort, raw_sort = self._process_sort(query, limit, offset, sort)
        if has_sort:
            olo = SQL(" ORDER BY {0}").format(sort)
        else:
            olo = SQL("")
        if one_per:
            inner_sort, _, _ = self._process_sort(query, limit, offset, one_per + raw_sort)
            where += SQL(" ORDER BY {0}").format(inner_sort)
        if limit is not None:
            olo = SQL("{0} LIMIT %s").format(olo)
            values.append(limit)
            if offset != 0:
                olo = SQL("{0} OFFSET %s").format(olo)
                values.append(offset)
        if one_per:
            return where, olo, values
        else:
            return where + olo, values

    def _search_iterator(self, cur, search_cols, extra_cols, projection, query=""):
        """
        Returns an iterator over the results in a cursor,
        filling in columns from the extras table if needed.

        INPUT:

        - ``cur`` -- a psycopg2 cursor
        - ``search_cols`` -- the columns in the search table in the results
        - ``extra_cols`` -- the columns in the extras table in the results
        - ``projection`` -- the projection requested.
        - ``query`` -- the dictionary specifying the query (optional, only used for slow query print statements)

        OUTPUT:

        If projection is 0 or a string, an iterator that yields the labels/column values of the query results.
        Otherwise, an iterator that yields dictionaries with keys
        from ``search_cols`` and ``extra_cols``.
        """
        # Eventually want to batch the queries on the extra_table so that we
        # make fewer SQL queries here.
        total = 0
        t = time.time()
        try:
            for rec in cur:
                total += time.time() -t
                if projection == 0 or isinstance(projection, str):
                    yield rec[0]
                else:
                    yield {
                        k: v
                        for k, v in zip(search_cols + extra_cols, rec)
                        if (self._include_nones or v is not None)
                    }
                t = time.time()
        finally:
            if total > self.slow_cutoff:
                self.logger.info("Search iterator for {0} {1} required a total of \033[91m{2!s}s\033[0m".format(self.search_table, query, total))
            if isinstance(cur, pg_cursor):
                cur.close()
                if (
                    cur.withhold # to assure that it is a buffered cursor
                    and self._db._nocommit_stack == 0 # and there is nothing to commit
                ):
                    cur.connection.commit()

    ##################################################################
    # Methods for querying                                           #
    ##################################################################

    def _split_ors(self, query, sort=None):
        """
        Splits a query into multiple queries by breaking up the outer
        $or clause and copying the rest of the query.

        If sort is provided, the resulting dictionaries will be sorted by the first entry of the given sort.
        """
        # make a copy of the query so we don't modify the original
        query = dict(query)
        ors = query.pop("$or", None)
        if ors is None:
            # no $or clause
            return [query]
        queries = []

        def is_special(v):
            return isinstance(v, dict) and all(
                isinstance(k, str) and k.startswith("$") for k in v
            )

        for orc in ors:
            Q = dict(query)
            for key, val in orc.items():
                if key in Q and val != Q[key]:
                    if not is_special(val) and not is_special(Q[key]):
                        # this branch of the or would assert that the value is equal to two different things
                        break
                    else:
                        # It would be possible to try to merge queries, but we stick to a simple approach and just throw them in an $and
                        Q[key] = {"$and": [val, Q[key]]}
                else:
                    Q[key] = val
            else:
                # There were no incompatibilities, so we add Q to the list of queries
                queries.append(Q)
        if sort:
            col = sort[0]
            if isinstance(col, str):
                asc = 1
            else:
                col, asc = col
            queries.sort(key=lambda Q: Q[col], reverse=(asc != 1))
        return queries

    def _get_table_clause(self, extra_cols):
        """
        Return a clause for use in the FROM section of a SELECT query.

        INPUT:

        - ``extra_cols`` -- a list of extra columns (only evaluated as a boolean)
        """
        if extra_cols:
            return SQL("{0} JOIN {1} USING (id)").format(
                Identifier(self.search_table), Identifier(self.extra_table)
            )
        else:
            return Identifier(self.search_table)

    def lucky(self, query={}, projection=2, offset=0, sort=[], raw=None, raw_values=[]):
        # FIXME Nulls aka Nones are being erased, we should perhaps just leave them there
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
            - a list of strings (which are interpreted as column names in the
                ascending direction) or of pairs (column name, 1 or -1).
                If not specified, will use the default sort order on the table.
            - [] (default), unsorted, thus if there is more than one match to
                the query then the choice of the result is arbitrary.
        - ``raw`` -- a string, to be used as the WHERE part of the query.  DO NOT USE THIS DIRECTLY FOR INPUT FROM WEBSITE.
        - ``raw_values`` -- a list of values to be substituted for %s entries in the raw string.  Useful when strings might include quotes.

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
        cols = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        qstr, values = self._build_query(query, 1, offset, sort=sort, raw=raw, raw_values=raw_values)
        tbl = self._get_table_clause(extra_cols)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(cols, tbl, qstr)
        cur = self._execute(selecter, values)
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if projection == 0 or isinstance(projection, str):
                return rec[0]
            else:
                return {
                    k: v
                    for k, v in zip(search_cols + extra_cols, rec)
                    if (self._include_nones or v is not None)
                }

    def search(
        self,
        query={},
        projection=1,
        limit=None,
        offset=0,
        sort=None,
        info=None,
        split_ors=False,
        one_per=None,
        silent=False,
        raw=None,
        raw_values=[],
    ):
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
        - ``offset`` -- a nonnegative integer (default 0), where to start in the list of results.
        - ``sort`` -- a sort order.  Either None or a list of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).  If not specified, will use the default sort order on the table.  If you want the result unsorted, use [].
        - ``info`` -- a dictionary, which is updated with values of 'query', 'count', 'start', 'exact_count' and 'number'.  Optional.
        - ``split_ors`` -- a boolean.  If true, executes one query per clause in the `$or` list, combining the results.  Only used when a limit is provided.
        - ``one_per`` -- a list of columns.  If provided, only one result will be included with each given set of values for those columns (the first according to the provided sort order).
        - ``silent`` -- a boolean.  If True, slow query warnings will be suppressed.
        - ``raw`` -- a string, to be used as the WHERE part of the query.  DO NOT USE THIS DIRECTLY FOR INPUT FROM WEBSITE.
        - ``raw_values`` -- a list of values to be substituted for %s entries in the raw string.  Useful when strings might include quotes.

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
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        search_cols, extra_cols = self._parse_projection(projection)
        if limit is None and split_ors:
            raise ValueError("split_ors only supported when a limit is provided")
        if raw is not None:
            split_ors = False
        if split_ors or one_per:
            # We need to be able to extract the sort columns, so they need to be added
            _, _, raw_sort = self._process_sort(query, limit, offset, sort)
            raw_sort = [((col, 1) if isinstance(col, str) else col) for col in raw_sort]
            sort_cols = [col[0] for col in raw_sort]
            sort_only = tuple(col for col in sort_cols if col not in search_cols)
            search_cols = search_cols + sort_only
        cols = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        tbl = self._get_table_clause(extra_cols)
        nres = None if (one_per or limit is None) else self.stats.quick_count(query)

        def run_one_query(Q, lim, off):
            if lim is None:
                built = self._build_query(Q, sort=sort, raw=raw, one_per=one_per, raw_values=raw_values)
            else:
                built = self._build_query(Q, lim, off, sort, raw=raw, one_per=one_per, raw_values=raw_values)
            if one_per:
#SELECT lmfdb_label FROM (SELECT lmfdb_label, conductor, iso_nlabel, lmfdb_number, row_number() OVER (PARTITION BY lmfdb_iso ORDER BY conductor, iso_nlabel, lmfdb_number) as row_number FROM ec_curvedata WHERE jinv = '{-4096, 11}') temp WHERE row_number = 1 ORDER BY conductor, iso_nlabel, lmfdb_number
                where, olo, values = built
                inner_cols = SQL(", ").join(map(IdentifierWrapper, set(search_cols + extra_cols + tuple(sort_cols))))
                op = SQL(", ").join(map(IdentifierWrapper, one_per))
                selecter = SQL("SELECT {0} FROM (SELECT DISTINCT ON ({1}) {2} FROM {3}{4}) temp {5}").format(cols, op, inner_cols, tbl, where, olo)
            else:
                qstr, values = built
                selecter = SQL("SELECT {0} FROM {1}{2}").format(cols, tbl, qstr)
            return self._execute(
                selecter,
                values,
                silent=silent,
                buffered=(lim is None),
                slow_note=(self.search_table, "analyze", Q, repr(projection), lim, off),
            )

        def trim_results(it, lim, off, projection):
            for rec in islice(it, off, lim + off):
                if projection == 0:
                    yield rec[self._label_col]
                elif isinstance(projection, str):
                    yield rec[projection]
                else:
                    for col in sort_only:
                        rec.pop(col, None)
                    yield rec

        if split_ors:
            queries = self._split_ors(query, raw_sort)
            if len(queries) <= 1:
                # no ors to split
                split_ors = False
            else:
                if one_per:
                    raise ValueError("split_ors and one_per not compatible")
                results = []
                total = 0
                prelimit = (
                    max(limit + offset, self._count_cutoff)
                    if nres is None
                    else limit + offset
                )
                exact_count = True # updated below if we have a subquery hitting the prelimit
                for Q in queries:
                    cur = run_one_query(Q, prelimit, 0)
                    if cur.rowcount == prelimit and nres is None:
                        exact_count = False
                    total += cur.rowcount
                    # theoretically it's faster to use a heap to merge these sorted lists,
                    # but the sorting runtime is small compared to getting the records from
                    # postgres in the first place, so we use a simpler option.
                    # We override the projection on the iterator since we need to sort
                    results.extend(self._search_iterator(cur, search_cols, extra_cols, projection=1, query=Q))
                if all(
                    (asc == 1 or self.col_type[col] in number_types)
                    for col, asc in raw_sort
                ):
                    # every key is in increasing order or numeric so we can just use a tuple as a sort key
                    if raw_sort:
                        results.sort(
                            key=lambda x: tuple(
                                (x[col] if asc == 1 else -x[col])
                                for col, asc in raw_sort
                            )
                        )
                else:
                    for col, asc in reversed(raw_sort):
                        results.sort(key=lambda x: x[col], reverse=(asc != 1))
                results = list(trim_results(results, limit, offset, projection))
                if nres is None:
                    if exact_count:
                        nres = total
                    else:
                        # We could use total, since it's a valid lower bound, but we want consistency
                        # with the results that don't use split_ors
                        nres = min(total, self._count_cutoff)

        if not split_ors:  # also handle the case len(queries) == 1
            if nres is not None or limit is None:
                prelimit = limit
            else:
                prelimit = max(limit, self._count_cutoff - offset)
            cur = run_one_query(query, prelimit, offset)
            if limit is None:
                if info is not None:
                    # caller is requesting count data
                    info["number"] = self.count(query)
                return self._search_iterator(cur, search_cols, extra_cols, projection, query=query)
            if nres is None:
                exact_count = cur.rowcount < prelimit
                nres = offset + cur.rowcount
            else:
                exact_count = True
            results = cur.fetchmany(limit)
            results = list(self._search_iterator(results, search_cols, extra_cols, projection, query=query))
        if info is not None:
            if offset >= nres > 0:
                # We're passing in an info dictionary, so this is a front end query,
                # and the user has requested a start location larger than the number
                # of results.  We adjust the results to be the last page instead.
                offset -= (1 + (offset - nres) / limit) * limit
                if offset < 0:
                    offset = 0
                return self.search(
                    query,
                    projection,
                    limit=limit,
                    offset=offset,
                    sort=sort,
                    info=info,
                    silent=silent,
                )
            info["query"] = dict(query)
            info["number"] = nres
            info["count"] = limit
            info["start"] = offset
            info["exact_count"] = exact_count
        return results

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

        Note, the example below uses loc_algebras which is no longer a column
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
        return self.lucky({label_col: label}, projection=projection, sort=[])

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
        return self.lucky(query, projection="id") is not None

    def label_exists(self, label, label_col=None):
        """
        Determines whether these exists a record with the given label.

        INPUT:

        - ``label`` -- a string, the label
        - ``label_col`` -- the column holding the label (most tables have a default setting)
        """
        if label_col is None:
            label_col = self._label_col
            if label_col is None:
                raise ValueError("Lookup method not supported for tables with no label column")
        return self.exists({label_col: label})

    def random(self, query={}, projection=0, pick_first=None):
        """
        Return a random label or record from this table.

        INPUT:

        - ``query`` -- a query dictionary from which a result
          will be selected, uniformly at random
        - ``projection`` -- which columns are requested
          (default 0, meaning just the label).
          See ``_parse_projection`` for more details.
        - ``pick_first`` -- a column name.  If provided, a value is chosen uniformly
          from the distinct values (subject to the given query), then a random
          element is chosen with that value.  Note that the set of distinct values
          is computed and stored, so be careful not to choose a column that takes
          on too many values.

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
        if pick_first:
            colvals = self.distinct(pick_first, query)
            query = dict(query)
            query[pick_first] = random.choice(colvals)
            return self.random(query, projection)
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
                    # An arbitrary projection might be large, so we get ids
                    L = list(self.search(query, "id", sort=[]))
                self.stats._record_count(query, len(L))
                if len(L) == 0:
                    return None
                res = random.choice(L)
                if projection != 0:
                    res = self.lucky({"id": res}, projection=projection)
                return res
            elif cnt == 0:
                return None
            else:
                offset = random.randrange(cnt)
                return self.lucky(query, projection=projection, offset=offset, sort=[])
        else:
            maxtries = 100
            # a temporary hack FIXME
            # maxid = self.max('id')
            maxid = self.max_id()
            if maxid == 0:
                return None
            # a temporary hack FIXME
            minid = self.min_id()
            for _ in range(maxtries):
                # The id may not exist if rows have been deleted
                # a temporary hack FIXME
                # rid = random.randint(1, maxid)
                rid = random.randint(minid, maxid)
                res = self.lucky({"id": rid}, projection=projection)
                if res:
                    return res
            raise RuntimeError("Random selection failed!")
        ### This code was used when not every table had an id.
        ## Get the number of pages occupied by the search_table
        # cur = self._execute(SQL("SELECT relpages FROM pg_class WHERE relname = %s"), [self.search_table])
        # num_pages = cur.fetchone()[0]
        ## extra_cols will be () since there is no id
        # search_cols, extra_cols = self._parse_projection(projection)
        # vars = SQL(", ").join(map(Identifier, search_cols + extra_cols))
        # selecter = SQL("SELECT {0} FROM {1} TABLESAMPLE SYSTEM(%s)").format(vars, Identifier(self.search_table))
        ## We select 3 pages in an attempt to not accidentally get nothing.
        # percentage = min(float(300) / num_pages, 100)
        # for _ in range(maxtries):
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
                mode = "bernoulli"
            else:
                mode = "choice"
        mode = mode.upper()
        search_cols, extra_cols = self._parse_projection(projection)
        if ratio > 1 or ratio <= 0:
            raise ValueError("Ratio must be a positive number between 0 and 1")
        if ratio == 1:
            return self.search(query, projection, sort=[])
        elif mode == "CHOICE":
            results = list(self.search(query, projection, sort=[]))
            count = int(len(results) * ratio)
            if repeatable is not None:
                random.seed(repeatable)
            return random.sample(results, count)
        elif mode in ["SYSTEM", "BERNOULLI"]:
            if extra_cols:
                raise ValueError("You cannot use the system or bernoulli modes with extra columns")
            cols = SQL(", ").join(map(Identifier, search_cols))
            if repeatable is None:
                repeatable = SQL("")
                values = [100 * ratio]
            else:
                repeatable = SQL(" REPEATABLE %s")
                values = [100 * ratio, int(repeatable)]
            qstr, qvalues = self._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
            else:
                qstr = SQL(" WHERE {0}").format(qstr)
                values.extend(qvalues)
            selecter = SQL(
                "SELECT {0} FROM {1} TABLESAMPLE " + mode + "(%s){2}{3}"
            ).format(cols, Identifier(self.search_table), repeatable, qstr)
            cur = self._execute(selecter, values, buffered=True)
            return self._search_iterator(cur, search_cols, extra_cols, projection, query=query)

    def copy_to_example(self, searchfile, extrafile=None, id=None, sep=u"|", commit=True):
        """
        This function writes files in the format used for copy_from and reload.
        It writes the header and a single random row.

        INPUT:

        - ``searchfile`` -- a string, the filename to write data into for the search table
        - ``extrafile`` -- a string,the filename to write data into for the extra table.
            If there is an extra table, this argument is required.
        - ``id`` -- an id to use for the example row (random if unspecified)
        - ``sep`` -- a character to use as a separator between columns
        """
        self._check_file_input(searchfile, extrafile, {})
        if id is None:
            id = self.random({}, "id")
            if id is None:
                return self.copy_to(searchfile, extrafile, commit=commit, sep=sep)
        tabledata = [
            # tablename, cols, addid, write_header, filename
            (self.search_table, ["id"] + self.search_cols, searchfile),
            (self.extra_table, ["id"] + self.extra_cols, extrafile),
        ]
        with DelayCommit(self, commit):
            for table, cols, filename in tabledata:
                if filename is None:
                    continue
                types = [self.col_type[col] for col in cols]
                header = "%s\n%s\n\n" % (sep.join(cols), sep.join(types))
                select = SQL("SELECT {0} FROM {1} WHERE id = {2}").format(
                    SQL(", ").join(map(Identifier, cols)),
                    Identifier(table),
                    Literal(id))
                self._copy_to_select(select, filename, header=header, silent=True, sep=sep)
                print("Wrote example to %s" % filename)

    ##################################################################
    # Convenience methods for accessing statistics                   #
    ##################################################################

    def max(self, col, constraint={}):
        """
        The maximum value attained by the given column.

        INPUT:

        - ``col`` -- the name of the column
        - ``constraint`` -- a query dictionary constraining which rows are considered

        EXAMPLES::

            sage: from lmfdb import db
            sage: db.nf_fields.max('class_number')
            1892503075117056
        """
        return self.stats.max(col, constraint)

    def min(self, col, constraint={}):
        """
        The minimum value attained by the given column.

        INPUT:

        - ``col`` -- the name of the column
        - ``constraint`` -- a query dictionary constraining which rows are considered

        EXAMPLES::

            sage: from lmfdb import db
            sage: db.ec_mwbsd.min('area')
            0.00000013296713869846309987200099760
        """
        return self.stats.min(col, constraint)

    def distinct(self, col, query={}):
        """
        Returns a list of the distinct values taken on by a given column.

        INPUT:

        - ``col`` -- the name of the column
        - ``query`` -- a query dictionary constraining which rows are considered
        """
        selecter = SQL("SELECT DISTINCT {0} FROM {1}").format(Identifier(col), Identifier(self.search_table))
        qstr, values = self._parse_dict(query)
        if qstr is not None:
            selecter = SQL("{0} WHERE {1}").format(selecter, qstr)
        selecter = SQL("{0} ORDER BY {1}").format(selecter, Identifier(col))
        cur = self._execute(selecter, values)
        return [res[0] for res in cur]

    def count(self, query={}, groupby=None, record=True):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``groupby`` -- (default None) a list of columns
        - ``record`` -- (default True) whether to record the number of results in the counts table.

        OUTPUT:

        If ``groupby`` is None, the number of records satisfying the query.
        Otherwise, a dictionary with keys the distinct tuples of values taken on by the columns
        in ``groupby``, and values the number of rows with those values.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.count({'degree':int(6),'galt':int(7)})
            244006
        """
        return self.stats.count(query, groupby=groupby, record=record)

    def count_distinct(self, col, query={}, record=True):
        """
        Count the number of distinct values taken on by a given column.

        The result will be the same as taking the length of the distinct values, but a bit faster and caches the answer

        INPUT:

        - ``col`` -- the name of the column, or a list of such names
        - ``query`` -- a query dictionary constraining which rows are considered
        - ``record`` -- (default True) whether to record the number of results in the stats table.
        """
        return self.stats.count_distinct(col, query, record=record)
