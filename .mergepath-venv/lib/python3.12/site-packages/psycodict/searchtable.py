# -*- coding: utf-8 -*-
"""
The read half of a table: dictionary queries.

:class:`PostgresSearchTable` extends
:class:`~psycodict.table.PostgresTable` with the query API -- ``search``,
``lucky``, ``lookup``, ``count``, ``random`` and friends -- translating
query dictionaries into SQL SELECT statements, with projections, sorting,
joins and the ``info`` contract used by search pages.  The query language
is specified in QueryLanguage.md and the read API in Searching.md.
"""
import random
import time
from itertools import islice

from psycopg import Cursor, ServerCursor
from psycopg.sql import SQL, Identifier, Literal, Composed

from .base import number_types
from .table import PostgresTable
from .encoding import Json
from .utils import IdentifierWrapper, DelayCommit, filter_sql_injection, postgres_infix_ops

# psycopg3 splits plain and server-side cursors into two classes
# (psycopg2 had a single cursor class, which this name used to alias)
pg_cursor = (Cursor, ServerCursor)


def _qualify(frag, tablename):
    """
    Rewrites the bare column Identifiers in an SQL fragment produced by
    ``_parse_dict``, ``_sort_str`` or ``IdentifierWrapper`` into
    table-qualified form ("table"."column"), for use in a query that joins
    several tables.  Literals, placeholders and plain SQL are left alone.
    """
    if isinstance(frag, Composed):
        return Composed([_qualify(part, tablename) for part in frag])
    elif isinstance(frag, Identifier):
        # _obj holds the tuple of name parts; psycopg3 has no public accessor
        return Identifier(tablename, frag._obj[-1])
    else:
        return frag


class PostgresSearchTable(PostgresTable):
    """
    A single search table, as returned by ``db.<tablename>``: the interface
    for reading data with dictionary queries.

    The read methods -- :meth:`search`, :meth:`lucky`, :meth:`lookup`,
    :meth:`exists`, :meth:`count`, :meth:`random`, :meth:`distinct` and
    friends -- accept a query dictionary such as
    ``{"degree": 2, "disc": {"$lt": 0}}``, translate it into SQL, and
    return rows as dictionaries (or bare values, under a string
    projection).  The query language is specified in QueryLanguage.md and
    the read API in Searching.md.  Writing and schema changes live on the
    base class :class:`~psycodict.table.PostgresTable`, and precomputed
    statistics on :class:`~psycodict.statstable.PostgresStatsTable`
    (available as ``self.stats``).

    Instances are constructed by
    :class:`~psycodict.database.PostgresDatabase` from each table's
    ``meta_tables`` row; they are not meant to be created directly.
    """
    ##################################################################
    # Helper functions for querying                                  #
    ##################################################################

    def _parse_projection(self, projection):
        """
        Parses various ways of specifying which columns are desired.

        INPUT:

        - ``projection`` -- either 0, 1, 2, 3, a dictionary or list of column names.

          - If 0, projects just to the ``label``.  If the search table does not have a label column, raises a RuntimeError.
          - If 1, projects to all columns.
          - If 2, projects to all columns (a historical alias for 1, from when tables
            could be split into a search table and an extras table).
          - If 3, as 1 but with id included
          - If a dictionary, can specify columns to include by giving True values, or columns to exclude by giving False values.  Entries must be plain columns; path specifiers are not accepted here (they raise the not-a-column error).
          - If a list, specifies which columns to include.  Entries may be plain columns, array slicers (``vec[2]``) or dotted path specifiers (``data.s``, ``vec.1``; see the *Column part specifiers* section of QueryLanguage.md), the same forms accepted by joined queries; only the base column is validated, and the entry string is used verbatim as the key of the returned result dictionaries.
          - If a string, projects onto just that column (which may itself be a slicer or path); searches will return the value rather than a dictionary.

        OUTPUT:

        - a tuple of columns to be selected

        EXAMPLES::

            >>> nf = db.test_fields
            >>> nf._parse_projection(0)
            ('label',)
            >>> nf._parse_projection(1)
            ('class_group', 'class_number', 'degree', 'disc_abs', 'disc_sign', 'label', 'r2', 'ramps')
            >>> nf._parse_projection({"degree": True, "class_number": True})
            ('class_number', 'degree')

        If you want the "id" column, you can list it explicitly::

            >>> nf._parse_projection(["id", "label", "ramps"])
            ('id', 'label', 'ramps')

        You can specify a dictionary with columns to exclude::

            >>> nf._parse_projection({"class_group": False})
            ('class_number', 'degree', 'disc_abs', 'disc_sign', 'label', 'r2', 'ramps')
        """
        search_cols = []
        if projection == 0:
            if self._label_col is None:
                raise RuntimeError("No label column for %s" % (self.search_table))
            return (self._label_col,)
        elif not projection:
            raise ValueError("You must specify at least one key.")
        if projection == 1 or projection == 2:
            return tuple(self.search_cols)
        elif projection == 3:
            return tuple(["id"] + self.search_cols)
        elif isinstance(projection, dict):
            # Work on a copy: the pops below would otherwise empty the
            # caller's dictionary, making it single-use.
            projection = dict(projection)
            projvals = {bool(val) for val in projection.values()}
            if len(projvals) > 1:
                raise ValueError("You cannot both include and exclude.")
            including = projvals.pop()
            include_id = projection.pop("id", False)
            for col in self.search_cols:
                if (col in projection) == including:
                    search_cols.append(col)
                projection.pop(col, None)
            if projection:  # there were more columns requested
                raise ValueError("%s not column of %s" % (", ".join(projection), self.search_table))
        else:  # iterable or str
            if isinstance(projection, str):
                projection = [projection]
            else:
                projection = list(projection)
                seen = set()
                dups = [c for c in projection if c in seen or seen.add(c)]
                if dups:
                    raise ValueError(
                        "Duplicate column(s) in projection: %s"
                        % ", ".join(sorted(set(dups)))
                    )
            include_id = False
            for col in projection:
                # Determine the base column, matching _column_composable's
                # validation: for a dotted path the base is the segment before
                # the first ".", otherwise the name before any array slicer.
                # The full entry is kept verbatim (as the SELECT expression and
                # the result-dictionary key); _column_composable revalidates and
                # builds the SQL at query time.
                if "." in col:
                    colname = col.split(".", 1)[0]
                else:
                    colname = col.split("[", 1)[0]
                if colname in self.search_cols:
                    search_cols.append(col)
                elif col == "id":
                    include_id = True
                else:
                    raise ValueError("%s not column of %s" % (col, self.search_table))
        if include_id:
            search_cols.insert(0, "id")
        return tuple(search_cols)

    def _create_typecast(self, key, value, col, col_type):
        """
        This method is used to add typecasts to queries when necessary.
        It is called from ``_parse_special`` and ``_parse_dict``; see the documentation
        of those functions for inputs.
        """
        if col_type == "smallint[]" and key in ["$contains", "$containedin"]:
            # smallint[] requires a typecast to test containment
            return "::int[]"
        if col_type.endswith("[]") and key in ["$eq", "$ne", "$contains", "$containedin", "$overlaps"]:
            if isinstance(col, Identifier):
                return "::" + col_type
            else:
                # Selected a path
                return "::" + col_type[:-2]
        return ""

    def _any_cast(self, col_type):
        """
        A placeholder for an array parameter in an ANY(...) clause, cast to
        the column's array type when the type name is known and safe to
        interpolate.  See the comment at the $in branch of _parse_special.
        """
        if col_type and col_type.replace(" ", "").isalnum():
            return "%s::" + col_type + "[]"
        return "%s"

    def _column_composable(self, colspec, tname=None):
        """
        Turns a column specifier -- a column name, optionally with an array
        slicer (``vec[2]``) or a dotted path (``data.nested.k``, ``ainvs.1``)
        -- into a Composable for use in a SELECT or ORDER BY, validated
        against this table's columns and qualified with the table name
        ``tname`` when given.
        """
        if "." in colspec:
            path = [int(p) if p.isdigit() else p for p in colspec.split(".")]
            base = path[0]
            if base != "id" and base not in self.search_cols:
                raise ValueError("%s is not a column of %s" % (base, self.search_table))
            if self.col_type.get(base) == "jsonb":
                parts = [SQL("->{0}").format(Literal(p)) for p in path[1:]]
            else:
                parts = [SQL("[{0}]").format(Literal(p)) for p in path[1:]]
            ident = Identifier(base) if tname is None else Identifier(tname, base)
            return SQL("{0}{1}").format(ident, SQL("").join(parts))
        if colspec != "id" and colspec.split("[", 1)[0] not in self.search_cols:
            raise ValueError("%s is not a column of %s" % (colspec, self.search_table))
        wrapped = IdentifierWrapper(colspec)
        if tname is not None:
            wrapped = _qualify(wrapped, tname)
        return wrapped

    def _col_identifier(self, name, join_context=None):
        """
        Wraps a column name given as the value of a ``$col`` special key,
        after checking that it exists.  The name resolves exactly like a
        query key: a bare name is a column of this table, while
        "table.column" names a column of a joined table when a join is in
        use.  An array slicer (as in ``vec[2]``) is allowed.
        """
        if not isinstance(name, str):
            raise ValueError("$col takes a column name, not %s" % (type(name).__name__,))
        table, tname, colspec = self, None, name
        if join_context is not None:
            tname = self.search_table
            prefix, dot, rest = name.partition(".")
            if dot and prefix in join_context:
                table, tname, colspec = join_context[prefix], prefix, rest
        if colspec != "id" and colspec.split("[", 1)[0] not in table.search_cols:
            raise ValueError("%s is not a column of %s" % (colspec, table.search_table))
        wrapped = IdentifierWrapper(colspec)
        if tname is not None:
            wrapped = _qualify(wrapped, tname)
        return wrapped

    def _parse_special(self, key, value, col, col_type, join_context=None):
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
            - ``$size`` -- constrains the number of elements of an array or jsonb column.
              For an array column it is the cardinality; for a jsonb column it is the
              array length or, for a jsonb object, the number of keys -- a jsonb scalar
              (or json/SQL null) has no size, so it never matches (and does not error).
              The value is either an integer (testing equality of the length) or an
              operator dictionary (e.g. ``{"$gte": 2}``, ``{"$in": [2, 3]}``) that
              constrains the length like any integer column.
            - ``$exists`` -- if True, require not null; if False, require null.
            - ``$startswith`` -- for text columns, matches strings that start with the given string.
            - ``$like`` -- for text columns, matches strings according to the LIKE operand in SQL.
            - ``$ilike`` -- for text columns, matches strings according to the ILIKE, the case-insensitive version of LIKE in PostgreSQL.
            - ``$regex`` -- for text columns, matches the given regex expression supported by PostgresSQL
            - ``$raw`` -- a string to be inserted as SQL after filtering against SQL injection
            - ``$col`` -- the name of another column: ``{"col1": {"$col": "col2"}}``
              imposes ``col1 = col2``, and ``{"$col": "col2"}`` can also be used as the value
              for any of the infix comparison operators above.  The name resolves like a
              query key, so it can name a joined table's column when a join is in use.
        - ``value`` -- The value to compare to.  The meaning depends on the key.
        - ``col`` -- The name of the column, wrapped in SQL
        - ``col_type`` -- the SQL type of the column
        - ``join_context`` -- when parsing a joined query, the dictionary of joined
          tables (as produced by ``_parse_join``); None otherwise

        OUTPUT:

        - A string giving the SQL test corresponding to the requested query, with %s
        - values to fill in for the %s entries (see ``_execute`` for more discussion).

        EXAMPLES::

            >>> from psycodict import Identifier
            >>> nf = db.test_fields
            >>> statement, vals = nf._parse_special("$lte", 3, Identifier("degree"), "smallint")
            >>> statement.as_string(db.conn), vals
            ('"degree" <= %s', [3])
            >>> statement, vals = nf._parse_special("$or", [{"degree": {"$lte": 2}}, {"class_number": {"$gte": 3}}], None, None)
            >>> statement.as_string(db.conn), vals
            ('("degree" <= %s OR "class_number" >= %s)', [2, 3])
            >>> statement, vals = nf._parse_special("$contains", [2, 3], Identifier("ramps"), "integer[]")
            >>> statement.as_string(db.conn), vals
            ('"ramps" @> %s::integer[]', [[2, 3]])
        """
        if col_type is not None and col_type.endswith("[]"):
            # SQL does not correctly parse the =ANY(...) construction with array types, so we convert to an equivalent OR construction
            if key == "$in":
                key = "$or"
            elif key == "$nin":
                key = "$not"
                value = {"$or": value}
        if key in ["$or", "$and"]:
            if not isinstance(value, (list, tuple)):
                raise ValueError("%s requires a list of dictionaries" % key)
            pairs = [
                self._parse_dict(clause, outer=col, outer_type=col_type,
                                 join_context=join_context)
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
                if key == "$or":
                    # the empty or clause should be False
                    return SQL("false"), []
                else:
                    return None, None
        elif key == "$not":
            negated, values = self._parse_dict(value, outer=col, outer_type=col_type,
                                               join_context=join_context)
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
        elif key == "$ne" and value is None:
            # SQL "col != NULL" is never true, so {col: {"$ne": None}} used to
            # match nothing -- the opposite of {col: None} (which renders "col
            # IS NULL").  Make $ne None its true complement, mirroring $eq/None.
            cmd = SQL("{0} IS NOT NULL").format(col)
            value = []
        elif key == "$notcontains":
            if not value:
                # excluding nothing is no constraint at all
                return None, None
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
        elif key == "$size":
            # Constrains the number of elements of an array or jsonb-array column.
            if col_type is not None and col_type.endswith("[]"):
                # cardinality, not array_length(col, 1): array_length of an
                # empty array is NULL (so {"$size": 0} could never match an
                # empty array), while cardinality returns 0.  For a
                # multidimensional array it counts the elements of every
                # dimension, not the length of the outermost one.
                length = SQL("cardinality({0})").format(col)
            elif col_type == "jsonb":
                # A jsonb value has a "size" only when it is a container:
                # jsonb_typeof dispatches to the array's element count or the
                # object's key count.  Every other type (a scalar, or a json
                # null), and a SQL NULL, falls through to the implicit ELSE
                # NULL, so $size neither matches nor errors on them -- unlike a
                # bare jsonb_array_length, which raises on any non-array.  The
                # CASE guard is evaluated per row, so each branch's function
                # only ever sees the jsonb type it expects.  (An empty array or
                # object gives 0; there is no jsonb_object_length, hence the
                # key count.)
                length = SQL(
                    "CASE jsonb_typeof({0}) "
                    "WHEN 'array' THEN jsonb_array_length({0}) "
                    "WHEN 'object' THEN (SELECT count(*)::int FROM jsonb_object_keys({0})) "
                    "END"
                ).format(col)
            else:
                raise ValueError("$size requires an array or jsonb column")
            if isinstance(value, dict):
                # An operator dictionary recurses with the length expression as
                # the outer column, exactly as $or/$and recurse with a column,
                # so every integer operator ($gte, $in, $ne, ...) works against
                # the length -- including on joined columns and dotted paths,
                # since ``col`` arrives as an already-built composable.
                return self._parse_dict(value, outer=length, outer_type="integer",
                                        join_context=join_context)
            # A bare integer is an equality test on the length.
            cmd = SQL("{0} = %s").format(length)
            value = [value]
        elif key == "$raw":
            # Names in the expression resolve like query keys: bare names are
            # this table's columns, and in a joined query table.column names
            # a joined table's column
            cmd, value = filter_sql_injection(value, col, col_type, "=", self, join_context=join_context)
        elif isinstance(value, dict) and len(value) == 1 and "$raw" in value:
            # We support queries like {'abvar_count':{'$lte':{'$raw':'q^g'}}}
            if key in postgres_infix_ops:
                cmd, value = filter_sql_injection(value["$raw"], col, col_type, postgres_infix_ops[key], self, join_context=join_context)
            else:
                raise ValueError("Error building query: {0} (in $raw)".format(key))
        elif key == "$col":
            # {'col1': {'$col': 'col2'}} imposes "col1" = "col2"
            cmd = SQL("{0} = {1}").format(col, self._col_identifier(value, join_context))
            value = []
        elif isinstance(value, dict) and len(value) == 1 and "$col" in value:
            # {'col1': {'$lte': {'$col': 'col2'}}} imposes "col1" <= "col2"
            if key in postgres_infix_ops:
                cmd = SQL("{0} " + postgres_infix_ops[key] + " {1}").format(
                    col, self._col_identifier(value["$col"], join_context)
                )
                value = []
            else:
                raise ValueError("Error building query: {0} (in $col)".format(key))
        elif key in ["$in", "$nin"] and col_type == "jsonb" and any(isinstance(v, (dict, list)) for v in value):
            # jsonb containment (<@), used below for scalar values, cannot match
            # composite values (objects/arrays), so we fall back to a disjunction
            # of equality tests for those
            eq = SQL(" OR ").join(SQL("{0} = %s").format(col) * len(value))
            if key == "$in":
                cmd = SQL("({0})").format(eq)
            else:
                cmd = SQL("NOT ({0})").format(eq)
            value = [v if isinstance(v, Json) else Json(v) for v in value]
        else:
            if key in postgres_infix_ops:
                cmd = SQL("{0} " + postgres_infix_ops[key] + " %s")
            # FIXME, we should do recursion with _parse_special
            elif key == "$maxgte":
                # Inline rather than array_max(): that function is a custom
                # definition that exists on the LMFDB's servers but not on a
                # stock PostgreSQL, and this subquery is exactly its body
                # (which the planner inlines identically).
                cmd = SQL("(SELECT max(unnested) FROM unnest({0}) AS unnested) >= %s")
            elif key == "$anylte":
                cmd = SQL("%s >= ANY({0})")
            elif key == "$in": # This now handles scalar $in or jsonb $in
                if col_type == "jsonb":
                    # jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("{0} <@ %s")
                else: # Note that array types are handled at the beginning of the function
                    # We cast the array parameter to the column's type: psycopg3
                    # picks the smallest integer type for the parameter array,
                    # and comparing e.g. an integer column against ANY(smallint[])
                    # is several times slower than the same-type comparison.
                    cmd = SQL("{0} = ANY(" + self._any_cast(col_type) + ")")
            elif key == "$nin":
                if col_type == "jsonb":
                    # jsonb_path_ops modifiers for the GIN index doesn't support this query
                    cmd = SQL("NOT ({0} <@ %s)")
                else:
                    cmd = SQL("NOT ({0} = ANY(" + self._any_cast(col_type) + "))")
            elif key == "$contains":
                cmd = SQL("{0} @> %s")
                if col_type != "jsonb":
                    # The parameter of @> is the array of required elements.  A
                    # list is already that array and is passed through (so the
                    # empty list emits '{}', not the '{{}}' that wrapping would
                    # produce and that PostgreSQL before 17 rejects as
                    # malformed); a tuple means the same, but psycopg would
                    # adapt it as a composite literal '(3,5)' rather than an
                    # array, so normalize it to a list; anything else is a
                    # single required element and is wrapped.  This mirrors how
                    # $containedin passes its list through.
                    if isinstance(value, tuple):
                        value = list(value)
                    elif not isinstance(value, list):
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
                value = Json(value) if not isinstance(value, Json) else value
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

            >>> nf = db.test_fields
            >>> nf._parse_values({'degree': 3})
            [3]
            >>> nf._parse_values({'class_group': [3]})
            [Json([3])]
        """

        # None stays None even for jsonb columns, so that it is stored as SQL
        # NULL rather than the jsonb value 'null' (matching insert_many and
        # copy_dumps, and making the documented {col: None} query work).
        return [
            Json(val) if self.col_type[key] == "jsonb" and val is not None else val
            for key, val in D.items()
        ]

    def _parse_dict(self, D, outer=None, outer_type=None, join_context=None):
        """
        Parses a dictionary that specifies a query in something close to Mongo syntax into an SQL query.

        INPUT:

        - ``D`` -- a dictionary, or a scalar if outer is set
        - ``outer`` -- the column that we are parsing (None if not yet parsing any column).  Used in recursion.  Should be wrapped in SQL.
        - ``outer_type`` -- the SQL type for the outer column
        - ``join_context`` -- when parsing a joined query, the dictionary of joined
          tables (as produced by ``_parse_join``).  Keys then resolve by splitting
          at the first period (a joined-table prefix means that table's column) and
          all identifiers are emitted table-qualified.  None otherwise, in which
          case behavior is exactly as without joins.

        OUTPUT:

        - An SQL Composable giving the WHERE component of an SQL query (possibly containing %s), or None if D imposes no constraint
        - A list of values to fill in for the %s in the string.  See ``_execute`` for more details.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> statement, vals = nf._parse_dict({"degree": 2, "class_number": 3})
            >>> statement.as_string(db.conn), vals
            ('"degree" = %s AND "class_number" = %s', [2, 3])
            >>> statement, vals = nf._parse_dict({"degree": {"$gte": 2, "$lte": 3}, "r2": 1})
            >>> statement.as_string(db.conn), vals
            ('"degree" >= %s AND "degree" <= %s AND "r2" = %s', [2, 3, 1])
            >>> statement, vals = nf._parse_dict({"degree": 2, "$or": [{"class_number": 1, "r2": 0}, {"disc_sign": 1, "disc_abs": {"$lte": 10}}]})
            >>> statement.as_string(db.conn), vals
            ('"degree" = %s AND ("class_number" = %s AND "r2" = %s OR "disc_sign" = %s AND "disc_abs" <= %s)', [2, 1, 0, 1, 10])
            >>> nf._parse_dict({})
            (None, None)
        """
        if outer is not None and not isinstance(D, dict):
            if outer_type == "jsonb":
                D = Json(D)
            # The typecast matters for array columns: psycopg3 picks its own
            # element type for a list parameter (e.g. smallint[]), and there
            # is no equality operator between arrays of different types.
            cmd = "{0} = %s" + self._create_typecast("$eq", D, outer, outer_type)
            return SQL(cmd).format(outer), [D]
        if len(D) == 0:
            return None, None
        else:
            strings = []
            values = []
            for key, value in D.items():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == "$":
                    sub, vals = self._parse_special(key, value, outer, col_type=outer_type,
                                                    join_context=join_context)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                    continue
                orig_key = key  # the column name as written, for error messages
                # In a joined query, a prefix naming a joined table sends the
                # key to that table; anything else is a column of this table,
                # with periods keeping their usual path meaning
                table, tname = self, None
                if join_context is not None:
                    tname = self.search_table
                    prefix, dot, rest = key.partition(".")
                    if dot and prefix in join_context:
                        table, tname, key = join_context[prefix], prefix, rest
                if "." in key:
                    path = [int(p) if p.isdigit() else p for p in key.split(".")]
                    key = path[0]
                    if table.col_type.get(key) == "jsonb":
                        path = [SQL("->{0}").format(Literal(p)) for p in path[1:]]
                    else:
                        path = [SQL("[{0}]").format(Literal(p)) for p in path[1:]]
                else:
                    path = None
                if key != "id" and key not in table.search_cols:
                    raise ValueError("%s is not a column of %s" % (key, table.search_table))
                # Have to determine whether key is jsonb before wrapping it in Identifier
                col_type = table.col_type[key]
                ident = Identifier(key) if tname is None else Identifier(tname, key)
                if path:
                    key = SQL("{0}{1}").format(ident, SQL("").join(path))
                else:
                    key = ident
                if isinstance(value, dict):
                    dollar = [k for k in value if k.startswith("$")]
                    if dollar and len(dollar) != len(value):
                        # A dict of operators must be *all* operator keys.  A
                        # mix of "$"-keys and plain keys is almost always a
                        # dropped "$" on one operator; treating it as a literal
                        # value (the old behavior) fails to cast on a typed
                        # column and silently matches nothing on jsonb, so
                        # refuse it explicitly.
                        plain = [k for k in value if not k.startswith("$")]
                        raise ValueError(
                            "Error building query for %r: an operator dict mixes "
                            "operators %s with non-operator keys %s.  Use only "
                            "keys beginning with '$' (did you drop a '$'?); a "
                            "dict with no '$' keys is matched as a literal value."
                            % (orig_key, sorted(dollar), sorted(plain))
                        )
                    if dollar or not value:
                        # an all-operator dict, or {} (which imposes nothing)
                        sub, vals = self._parse_dict(value, key, outer_type=col_type,
                                                     join_context=join_context)
                        if sub is not None:
                            strings.append(sub)
                            values.extend(vals)
                        continue
                    # otherwise a dict with no operators is a literal value
                    # (e.g. a jsonb object), handled by the equality path below
                if value is None:
                    strings.append(SQL("{0} IS NULL").format(key))
                else:
                    if col_type == "boolean" and isinstance(value, int) and not isinstance(value, bool):
                        # Postgres has no boolean = integer operator, so 0/1 on
                        # a boolean column raised a cryptic "operator does not
                        # exist" deep in the driver.  Refuse it clearly instead;
                        # pass a real bool (True/False).
                        raise ValueError(
                            "Column %r is boolean; compare it with True or "
                            "False, not the integer %r." % (orig_key, value)
                        )
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
            # An explicit, user-provided sort.  Unlike the table's default sort
            # (built once by _sort_str and requiring plain columns), entries here
            # may be array slicers or dotted paths, so we build each ordering
            # term with _column_composable.  For a plain column name this emits
            # the same bare Identifier as _sort_str, and DESC keeps the same
            # ``DESC NULLS LAST`` form.
            L = []
            for col in sort:
                if isinstance(col, str):
                    L.append(self._column_composable(col))
                elif col[1] == 1:
                    L.append(self._column_composable(col[0]))
                else:
                    L.append(SQL("{0} DESC NULLS LAST").format(self._column_composable(col[0])))
            return SQL(", ").join(L), bool(sort), sort

    def _build_query(self, query, limit=None, offset=0, sort=None, raw=None, one_per=None, raw_values=None):
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

            >>> nf = db.test_fields
            >>> statement, vals = nf._build_query({"degree": 2, "class_number": 3})
            >>> statement.as_string(db.conn), vals
            (' WHERE "degree" = %s AND "class_number" = %s ORDER BY "degree", "disc_abs", "label"', [2, 3])
            >>> statement, vals = nf._build_query({"class_number": 1}, 4)
            >>> statement.as_string(db.conn), vals
            (' WHERE "class_number" = %s ORDER BY "degree", "disc_abs", "label" LIMIT %s', [1, 4])

        A ``raw_values`` list passed in by the caller is not mutated, even
        though the limit and offset are appended to the returned values::

            >>> raw_values = []
            >>> statement, vals = nf._build_query({}, 4, raw="degree = 2", raw_values=raw_values)
            >>> statement.as_string(db.conn), vals
            (' WHERE degree = 2 ORDER BY "degree", "disc_abs", "label" LIMIT %s', [4])
            >>> raw_values
            []
        """
        if raw_values is None:
            raw_values = []
        if raw is None:
            qstr, values = self._parse_dict(query)
        else:
            # Copy raw_values: we append limit/offset to ``values`` below, and
            # must not mutate the list passed in by the caller (in particular
            # the shared default of search()/lucky()).
            qstr, values = SQL(raw), list(raw_values)
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

    def _search_iterator(self, cur, search_cols, projection, query="", silent=False):
        """
        Returns an iterator over the results in a cursor.

        INPUT:

        - ``cur`` -- a psycopg cursor
        - ``search_cols`` -- the columns in the results
        - ``projection`` -- the projection requested.
        - ``query`` -- the dictionary specifying the query (optional, only used for slow query print statements)
        - ``silent`` -- whether to suppress slow query warnings

        OUTPUT:

        If projection is 0 or a string, an iterator that yields the labels/column values of the query results.
        Otherwise, an iterator that yields dictionaries with keys
        from ``search_cols``.
        """
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
                        for k, v in zip(search_cols, rec)
                        if (self._include_nones or v is not None)
                    }
                t = time.time()
        finally:
            if not silent and total > self.slow_cutoff:
                self._logger.info("Search iterator for {0} {1} required a total of \033[91m{2!s}s\033[0m".format(self.search_table, query, total))
            if isinstance(cur, pg_cursor):
                cur.close()
                if (
                    getattr(cur, "withhold", False) # to assure that it is a buffered (server side) cursor
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
            try:
                queries.sort(key=lambda Q: Q[col], reverse=(asc != 1))
            except (KeyError, TypeError):
                # A branch whose value for the sort column is a range clause
                # (a dict) or absent has no natural position among the
                # scalars, so settle for a deterministic order instead.
                queries.sort(key=lambda Q: str(Q.get(col)), reverse=(asc != 1))
        return queries

    def lucky(self, query={}, projection=2, offset=0, sort=[], raw=None, raw_values=None, join=None):
        # None values are kept in result dictionaries by default; tables
        # created with include_nones=False omit them instead
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
          1 means return all search columns, 2 means all columns (default)).
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
        - ``join`` -- a list of tuples describing other search tables to join to this one,
          as for ``search``.  Not compatible with ``raw``.

        OUTPUT:

        If projection is 0 or a string, returns the label/column value of the first record satisfying the query.
        Otherwise, return a dictionary with keys the column names requested by the projection.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> nf.lucky({'degree': 2, 'disc_sign': 1, 'disc_abs': 5}, projection=0)
            '2.2.5.1'
            >>> nf.lucky({'label': '3.3.49.1'})
            {'class_group': [],
             'class_number': 1,
             'degree': 3,
             'disc_abs': 49,
             'disc_sign': 1,
             'label': '3.3.49.1',
             'r2': 0,
             'ramps': [7]}
            >>> nf.lucky({'label': '2.0.47.1'}, projection='class_group')
            [5]
        """
        if join is not None:
            if raw is not None or raw_values is not None:
                raise ValueError("raw is not supported with join")
            return self._join_lucky(query, projection, join, offset=offset, sort=sort)
        search_cols = self._parse_projection(projection)
        cols = SQL(", ").join(self._column_composable(c) for c in search_cols)
        qstr, values = self._build_query(query, 1, offset, sort=sort, raw=raw, raw_values=raw_values)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(cols, Identifier(self.search_table), qstr)
        cur = self._execute(selecter, values)
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if projection == 0 or isinstance(projection, str):
                return rec[0]
            else:
                return {
                    k: v
                    for k, v in zip(search_cols, rec)
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
        raw_values=None,
        join=None,
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
          1 means return all search columns (default), 2 means all columns).
        - ``limit`` -- an integer or None (default), giving the maximum number of records to return.
        - ``offset`` -- a nonnegative integer (default 0), where to start in the list of results.
        - ``sort`` -- a sort order.  Either None or a list of strings (which are interpreted as column names in the ascending direction) or of pairs (column name, 1 or -1).  If not specified, will use the default sort order on the table.  If you want the result unsorted, use [].
        - ``info`` -- a dictionary, which is updated with values of 'query', 'count', 'start', 'exact_count' and 'number'.  Optional.
        - ``split_ors`` -- a boolean.  If true, executes one query per clause in the ``$or`` list, combining the results.  Only used when a limit is provided.
        - ``one_per`` -- a list of columns.  If provided, only one result will be included with each given set of values for those columns (the first according to the provided sort order).
        - ``silent`` -- a boolean.  If True, slow query warnings will be suppressed.
        - ``raw`` -- a string, to be used as the WHERE part of the query.  DO NOT USE THIS DIRECTLY FOR INPUT FROM WEBSITE.
        - ``raw_values`` -- a list of values to be substituted for %s entries in the raw string.  Useful when strings might include quotes.
        - ``join`` -- a list of tuples ``(col1, col2)`` or ``(col1, col2, jointype)``
          describing other search tables to join to this one.  In each tuple, ``col2``
          must be qualified as ``"table.column"`` and names the table being joined;
          ``col1`` is a column of this table, or of a previously joined table if
          qualified.  ``jointype`` is ``"inner"`` (the default), ``"left"``,
          ``"right"`` or ``"full"``.  When ``join`` is given, query keys,
          projection entries, sort entries, ``$col`` names and names in
          ``$raw`` expressions may be qualified
          as ``"table.column"`` to refer to columns of the joined tables
          (unqualified names refer to this table, with periods keeping their
          usual path meaning), and the keys in the result dictionaries match
          the projection entries as given.  Counts are never cached, and
          ``split_ors``, ``one_per`` and ``raw`` are not supported.  See the
          Joined queries section of QueryLanguage.md for details.

        OUTPUT:

        If ``limit`` is None, returns an iterator over the results, yielding dictionaries with keys the columns requested by the projection (or labels/column values if the projection is 0 or a string)

        Otherwise, returns a list with the same data.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> info = {}
            >>> nf.search({'degree': 2, 'disc_sign': -1}, projection=0, limit=4, info=info)
            ['2.0.3.1', '2.0.4.1', '2.0.7.1', '2.0.8.1']
            >>> info['number'], info['exact_count']
            (8, True)

        Without a limit, an iterator is returned::

            >>> list(nf.search({'degree': 3, 'r2': 0}, projection=['label', 'disc_abs', 'ramps']))
            [{'label': '3.3.49.1', 'disc_abs': 49, 'ramps': [7]},
             {'label': '3.3.81.1', 'disc_abs': 81, 'ramps': [3]}]
            >>> list(nf.search({'ramps': {'$contains': [2]}}, projection=0))
            ['2.0.4.1', '2.0.8.1', '2.2.8.1', '2.2.12.1', '3.1.44.1', '3.1.76.1']

        Columns of other tables can be searched on and projected onto by
        joining the tables::

            >>> db.test_curves.search(
            ...     {"rank": 1, "test_fields.degree": 2},
            ...     ["label", "test_fields.disc_abs"],
            ...     join=[("field_label", "test_fields.label")],
            ...     limit=3)
            [{'label': '2.2.13.1-51.2-a1', 'test_fields.disc_abs': 13},
             {'label': '2.2.13.1-51.2-a2', 'test_fields.disc_abs': 13},
             {'label': '2.2.13.1-51.3-a1', 'test_fields.disc_abs': 13}]
        """
        if join is not None:
            if raw is not None or raw_values is not None:
                raise ValueError("raw is not supported with join")
            if split_ors:
                raise ValueError("split_ors is not supported with join")
            if one_per:
                raise ValueError("one_per is not supported with join")
            return self._join_search(query, projection, join, limit=limit, offset=offset, sort=sort, info=info, silent=silent)
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        if limit is not None and limit < 0:
            raise ValueError("Limit cannot be negative")
        if sort is not None:
            self._check_sort_duplicates(sort)
        search_cols = self._parse_projection(projection)
        if limit is None and split_ors:
            raise ValueError("split_ors only supported when a limit is provided")
        if raw is not None:
            split_ors = False
        if split_ors or one_per:
            # split_ors and one_per manipulate the fetched records in Python,
            # keyed by the sort and projection names (extracting sort columns,
            # DISTINCT ON, merging and re-sorting).  That machinery assumes the
            # names are plain columns: a dotted path or an array slicer would be
            # projected as a scalar by the inner query and then re-projected by
            # the same expression on the outer one (subscripting an already
            # scalar value), so neither is supported here.
            if any("." in c or "[" in c for c in search_cols):
                raise ValueError("path specifiers and array slicers in the projection are not supported with split_ors or one_per")
            # We need to be able to extract the sort columns, so they need to be added
            _, _, raw_sort = self._process_sort(query, limit, offset, sort)
            raw_sort = [((col, 1) if isinstance(col, str) else col) for col in raw_sort]
            sort_cols = [col[0] for col in raw_sort]
            if any("." in col or "[" in col for col in sort_cols):
                raise ValueError("path specifiers and array slicers in the sort are not supported with split_ors or one_per")
            sort_only = tuple(col for col in sort_cols if col not in search_cols)
            search_cols = search_cols + sort_only
        cols = SQL(", ").join(self._column_composable(c) for c in search_cols)
        tbl = Identifier(self.search_table)
        nres = None if (one_per or limit is None) else self.stats.quick_count(query)

        def run_one_query(Q, lim, off):
            if lim is None:
                built = self._build_query(Q, sort=sort, raw=raw, one_per=one_per, raw_values=raw_values)
            else:
                built = self._build_query(Q, lim, off, sort, raw=raw, one_per=one_per, raw_values=raw_values)
            if one_per:
#SELECT lmfdb_label FROM (SELECT lmfdb_label, conductor, iso_nlabel, lmfdb_number, row_number() OVER (PARTITION BY lmfdb_iso ORDER BY conductor, iso_nlabel, lmfdb_number) as row_number FROM ec_curvedata WHERE jinv = '{-4096, 11}') temp WHERE row_number = 1 ORDER BY conductor, iso_nlabel, lmfdb_number
                where, olo, values = built
                inner_cols = SQL(", ").join(map(IdentifierWrapper, set(search_cols + tuple(sort_cols))))
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
                    results.extend(self._search_iterator(cur, search_cols, projection=1, query=Q, silent=silent))
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
                    # caller is requesting count data; search-page counts are
                    # the ones worth caching, so record them
                    info["number"] = self.count(query, record=True)
                return self._search_iterator(cur, search_cols, projection, query=query, silent=silent)
            if nres is None:
                exact_count = cur.rowcount < prelimit and (offset == 0 or cur.rowcount > 0)
                nres = offset + cur.rowcount
            else:
                exact_count = True
            # fetchmany(0) would fall back to arraysize and return a row
            results = cur.fetchmany(limit) if limit else []
            results = list(self._search_iterator(results, search_cols, projection, query=query, silent=silent))
        if info is not None:
            # ``limit`` guards the recursion: the last-page retry sets
            # offset = nres - limit, so with limit == 0 (a count-only query)
            # the offset never shrinks and the call recurses on identical
            # arguments forever.  A zero-limit query wants only the count in
            # ``info``, so there is no last page to jump to.
            if limit and offset >= nres > 0:
                # We're passing in an info dictionary, so this is a front end query,
                # and the user has requested a start location larger than the number
                # of results.  We adjust the results to be the last page instead.

                # nres may not be accurate here, but we could get a recursion error
                # if offset is very large compared to the actual number of results
                # and we just reduce the offset by the limit each time.  So we count for real.
                if not exact_count:
                    nres = self.stats.count(query, record=True)
                offset = nres - limit
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
                    one_per=one_per,
                )
            info["query"] = dict(query)
            info["number"] = nres
            info["count"] = limit
            info["start"] = offset
            info["exact_count"] = exact_count
        return results

    ##################################################################
    # Joined queries: the join= option of search, count and lucky    #
    ##################################################################

    def _parse_join(self, join):
        """
        Validates a join specification and builds the FROM clause.

        INPUT:

        - ``join`` -- a list of tuples ``(col1, col2)`` or ``(col1, col2, jointype)``,
          as described in the ``search`` method.

        OUTPUT:

        - a dictionary mapping table names to ``PostgresSearchTable`` objects,
          one for each joined table (not including this one)
        - an SQL Composable giving the FROM clause, including all JOINs
        """
        if not join or not isinstance(join, (list, tuple)):
            raise ValueError("join must be a nonempty list of (col1, col2) or (col1, col2, jointype) tuples")
        joined = {}
        frm = Identifier(self.search_table)
        for entry in join:
            if not isinstance(entry, (list, tuple)) or len(entry) not in (2, 3):
                raise ValueError(
                    "each join entry must be (col1, col2) or (col1, col2, jointype) "
                    "with col2 qualified as 'table.column', not %r" % (entry,)
                )
            col1, col2 = entry[0], entry[1]
            jointype = entry[2] if len(entry) == 3 else "inner"
            if not (isinstance(jointype, str) and jointype.lower() in ("inner", "left", "right", "full")):
                raise ValueError("join type must be 'inner', 'left', 'right' or 'full', not %r" % (jointype,))
            if not isinstance(col2, str) or "." not in col2:
                raise ValueError(
                    "%r: the second column of a join entry names the table being "
                    "joined, so must be qualified as 'table.column'" % (col2,)
                )
            tname2, cname2 = col2.split(".", 1)
            if tname2 == self.search_table or tname2 in joined:
                raise ValueError("%s is already part of the join (each table can appear only once)" % (tname2,))
            table2 = self._db[tname2]
            if not isinstance(col1, str):
                raise ValueError("%r: join columns must be strings" % (col1,))
            tname1, dot, cname1 = col1.partition(".")
            if dot:
                if tname1 == self.search_table:
                    table1 = self
                elif tname1 in joined:
                    table1 = joined[tname1]
                else:
                    raise ValueError(
                        "%s: %s is not part of the join yet (join entries are "
                        "processed in order, and the first column of each must "
                        "belong to %s or to a previously joined table)"
                        % (col1, tname1, self.search_table)
                    )
            else:
                tname1, cname1, table1 = self.search_table, col1, self
            for table, cname in [(table1, cname1), (table2, cname2)]:
                if cname != "id" and cname not in table.search_cols:
                    raise ValueError("%s is not a column of %s" % (cname, table.search_table))
            joined[tname2] = table2
            # jointype was validated against a whitelist above, so this string
            # interpolation cannot inject SQL
            frm += SQL(" %s JOIN {0} ON {1} = {2}" % jointype.upper()).format(
                Identifier(tname2),
                Identifier(tname1, cname1),
                Identifier(tname2, cname2),
            )
        return joined, frm

    def _parse_join_projection(self, projection, joined):
        """
        The analogue of ``_parse_projection`` for joined queries: entries may
        be qualified as "table.column" to refer to columns of joined tables.
        Dictionary projections are not supported.

        OUTPUT:

        - a tuple of strings, the keys used in the result dictionaries (the
          projection entries as given; integer projections refer to this
          table's columns only)
        - a list of SQL Composables, the corresponding table-qualified columns
        """
        if isinstance(projection, dict):
            raise ValueError("dictionary projections are not supported with join")
        if projection == 0:
            if self._label_col is None:
                raise RuntimeError("No label column for %s" % (self.search_table,))
            keys = [self._label_col]
        elif not projection:
            raise ValueError("You must specify at least one key.")
        elif projection == 1 or projection == 2:
            keys = list(self.search_cols)
        elif projection == 3:
            keys = ["id"] + list(self.search_cols)
        elif isinstance(projection, str):
            keys = [projection]
        else:
            keys = list(projection)
        cols = []
        for key in keys:
            if not isinstance(key, str):
                raise ValueError(
                    "projection entries must be strings, with columns of "
                    "joined tables qualified as 'table.column', not %r" % (key,)
                )
            prefix, dot, rest = key.partition(".")
            if dot and prefix in joined:
                table, colspec = joined[prefix], rest
            else:
                table, colspec = self, key
            cols.append(table._column_composable(colspec, table.search_table))
        return tuple(keys), cols

    def _join_sort(self, query, limit, offset, sort, joined):
        """
        Processes the sort order for a joined query, returning the ORDER BY
        clause.  Sort entries resolve like query keys: a bare name is a
        column of this table, while "table.column" names a joined table's
        column.  The default sort (sort=None) is this table's.
        """
        if sort:
            L = []
            for s in sort:
                name, asc = (s, 1) if isinstance(s, str) else (s[0], s[1])
                prefix, dot, rest = name.partition(".")
                if dot and prefix in joined:
                    tname, colspec, table = prefix, rest, joined[prefix]
                else:
                    tname, colspec, table = self.search_table, name, self
                ident = table._column_composable(colspec, tname)
                L.append(ident if asc == 1 else SQL("{0} DESC NULLS LAST").format(ident))
            return SQL(" ORDER BY {0}").format(SQL(", ").join(L))
        sort_composed, has_sort, _ = self._process_sort(query, limit, offset, sort)
        if has_sort:
            return SQL(" ORDER BY {0}").format(_qualify(sort_composed, self.search_table))
        return SQL("")

    def _join_selecter(self, query, projection, join, limit=None, offset=0, sort=None, sort_limit=None):
        """
        Builds the SELECT statement for a joined query; shared by ``search``,
        ``lucky`` and ``analyze``.

        INPUT: as for ``search``, except that ``limit`` is applied verbatim
        (``_join_search`` passes its inflated count-estimation prelimit),
        while ``sort_limit`` is the caller's limit, used only by the
        default-sort heuristics (defaults to ``limit``).

        OUTPUT:

        - a tuple of strings, the keys for result dictionaries
        - the SELECT statement, as an SQL Composable
        - the list of values to substitute into it
        """
        joined, frm = self._parse_join(join)
        search_cols, cols = self._parse_join_projection(projection, joined)
        qstr, values = self._parse_dict(query, join_context=joined)
        if qstr is None:
            where, values = SQL(""), []
        else:
            where = SQL(" WHERE {0}").format(qstr)
        if sort_limit is None:
            sort_limit = limit
        olo = self._join_sort(query, sort_limit, offset, sort, joined)
        if limit is not None:
            olo = SQL("{0} LIMIT %s").format(olo)
            values.append(limit)
            if offset != 0:
                olo = SQL("{0} OFFSET %s").format(olo)
                values.append(offset)
        selecter = SQL("SELECT {0} FROM {1}{2}{3}").format(SQL(", ").join(cols), frm, where, olo)
        return search_cols, selecter, values

    def _join_search(self, query, projection, join, limit=None, offset=0, sort=None, info=None, silent=False):
        """
        The implementation of ``search`` when ``join`` is provided; see the
        documentation there.  Counts are never cached for joined queries.
        """
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        if limit is not None and limit < 0:
            raise ValueError("Limit cannot be negative")
        if sort is not None:
            self._check_sort_duplicates(sort)
        if limit is None:
            prelimit = None
        else:
            prelimit = max(limit, self._count_cutoff - offset)
        search_cols, selecter, values = self._join_selecter(
            query, projection, join, limit=prelimit, offset=offset, sort=sort, sort_limit=limit
        )
        cur = self._execute(
            selecter,
            values,
            silent=silent,
            buffered=(prelimit is None),
            slow_note=(self.search_table, "analyze", query, repr(projection), prelimit, offset, "join=%s" % (join,)),
        )
        if limit is None:
            if info is not None:
                info["number"] = self._join_count(query, join)
            return self._search_iterator(cur, search_cols, projection, query=query, silent=silent)
        exact_count = cur.rowcount < prelimit and (offset == 0 or cur.rowcount > 0)
        nres = offset + cur.rowcount
        # fetchmany(0) would fall back to arraysize and return a row
        results = cur.fetchmany(limit) if limit else []
        results = list(self._search_iterator(results, search_cols, projection, query=query, silent=silent))
        if info is not None:
            # limit guards the recursion just as in search (see that comment):
            # a zero-limit query has no last page and would otherwise recurse
            # forever on identical arguments.
            if limit and offset >= nres > 0:
                # The caller requested a start location past the last result;
                # adjust to the last page instead, as search does.
                if not exact_count:
                    nres = self._join_count(query, join)
                offset = max(nres - limit, 0)
                return self._join_search(
                    query, projection, join,
                    limit=limit, offset=offset, sort=sort, info=info, silent=silent,
                )
            info["query"] = dict(query)
            info["number"] = nres
            info["count"] = limit
            info["start"] = offset
            info["exact_count"] = exact_count
        return results

    def _join_lucky(self, query, projection, join, offset=0, sort=[]):
        """
        The implementation of ``lucky`` when ``join`` is provided; see the
        documentation there.
        """
        search_cols, selecter, values = self._join_selecter(
            query, projection, join, limit=1, offset=offset, sort=sort
        )
        cur = self._execute(selecter, values)
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if projection == 0 or isinstance(projection, str):
                return rec[0]
            else:
                return {
                    k: v
                    for k, v in zip(search_cols, rec)
                    if (self._include_nones or v is not None)
                }

    def _join_count(self, query, join):
        """
        The implementation of ``count`` when ``join`` is provided; see the
        documentation there.  The count is computed directly and never cached.
        """
        joined, frm = self._parse_join(join)
        qstr, values = self._parse_dict(query, join_context=joined)
        if qstr is None:
            where, values = SQL(""), []
        else:
            where = SQL(" WHERE {0}").format(qstr)
        selecter = SQL("SELECT COUNT(*) FROM {0}{1}").format(frm, where)
        cur = self._execute(selecter, values)
        return cur.fetchone()[0]

    def lookup(self, label, projection=2, label_col=None, join=None):
        """
        Look up a record by its label.

        INPUT:

        - ``label`` -- string, the label for the desired record.
        - ``projection`` -- which columns are requested (default 2, meaning all columns).
                            See ``_parse_projection`` for more details.
        - ``label_col`` -- which column holds the label.  Most tables store a default.
        - ``join`` -- a list of tuples describing other search tables to join
          to this one, as for ``search``.

        OUTPUT:

        A dictionary with keys the column names requested by the projection.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> rec = nf.lookup('2.0.23.1')
            >>> rec['class_number'], rec['class_group']
            (3, [3])
            >>> nf.lookup('2.0.47.1', 'class_number')
            5
            >>> nf.lookup('4.0.117.1') is None
            True
        """
        if label_col is None:
            label_col = self._label_col
            if label_col is None:
                raise ValueError("Lookup method not supported for tables with no label column")
        return self.lucky({label_col: label}, projection=projection, sort=[], join=join)

    def exists(self, query):
        """
        Determines whether there exists at least one record satisfying the query.

        INPUT:

        - ``query`` -- a mongo style dictionary specifying the search.
          See ``search`` for more details.

        OUTPUT:

        Boolean, whether there exists a record.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> nf.exists({'class_number': 5})
            True
            >>> nf.exists({'degree': 4})
            False
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

            >>> nf = db.test_fields
            >>> label = nf.random()
            >>> nf.label_exists(label)
            True
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
                # Cache the count we just computed, but only when count-saving
                # is enabled -- matching count()/count_distinct(), which never
                # write to the cache tables while ``saving`` is False.
                if self.stats.saving:
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
            # max_id returns -1 on an empty table (MAX(id) is NULL), so
            # testing for 0 sent an empty table into randint(0, -1);
            # anything below 1 means there are no rows.
            if maxid < 1:
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

    def random_sample(self, ratio, query={}, projection=1, mode=None, repeatable=None, silent=False):
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
        - ``silent`` -- whether to suppress slow query warnings
        """
        if mode is None:
            if self.count(query) > self._count_cutoff:
                mode = "bernoulli"
            else:
                mode = "choice"
        mode = mode.upper()
        search_cols = self._parse_projection(projection)
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
            cols = SQL(", ").join(self._column_composable(c) for c in search_cols)
            if repeatable is None:
                repeatable = SQL("")
                values = [100 * ratio]
            else:
                # The seed must be read before repeatable is rebound to the
                # SQL fragment (int() of an SQL object was a TypeError), and
                # the grammar requires parentheses: REPEATABLE (seed).
                values = [100 * ratio, int(repeatable)]
                repeatable = SQL(" REPEATABLE (%s)")
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
            return self._search_iterator(cur, search_cols, projection, query=query, silent=silent)

    def copy_to_example(self, searchfile, id=None, sep="|"):
        """
        This function writes files in the format used for copy_from and reload.
        It writes the header and a single random row.

        INPUT:

        - ``searchfile`` -- a string, the filename to write data into for the search table
        - ``id`` -- an id to use for the example row (random if unspecified)
        - ``sep`` -- a character to use as a separator between columns
        """
        self._check_file_input(searchfile, {})
        if id is None:
            id = self.random({}, "id")
            if id is None:
                return self.copy_to(searchfile, sep=sep)
        tabledata = [
            # tablename, cols, addid, write_header, filename
            (self.search_table, ["id"] + self.search_cols, searchfile),
        ]
        with DelayCommit(self):
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

            >>> db.test_fields.max('disc_abs')
            87
            >>> db.test_fields.max('disc_abs', {'degree': 2})
            47
        """
        return self.stats.max(col, constraint)

    def min(self, col, constraint={}):
        """
        The minimum value attained by the given column.

        INPUT:

        - ``col`` -- the name of the column
        - ``constraint`` -- a query dictionary constraining which rows are considered

        EXAMPLES::

            >>> db.test_fields.min('disc_abs')
            1
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

    def count(self, query={}, groupby=None, record=False, join=None):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``groupby`` -- (default None) a list of columns
        - ``record`` -- (default False) whether to record the number of results
          in the counts table.  Recording is useful for queries whose counts are
          displayed repeatedly (search pages record theirs), but every distinct
          recorded query adds a row to the counts table, so it is opt-in:
          scripts running many one-off counts no longer clutter the table (and
          slow down reloads) by accident.  Recording also requires ``saving``
          to be enabled on the stats table; with the psycodict default
          ``saving = False`` nothing is written.
        - ``join`` -- a list of tuples describing other search tables to join
          to this one, as for ``search``.  Counts of joined queries are
          computed directly and never cached, so ``record`` is ignored;
          ``groupby`` is not supported with ``join``.

        OUTPUT:

        If ``groupby`` is None, the number of records satisfying the query.
        Otherwise, a dictionary with keys the distinct tuples of values taken on by the columns
        in ``groupby``, and values the number of rows with those values.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> nf.count({'degree': 2})
            12
            >>> nf.count()
            22
            >>> sorted(nf.count({'disc_sign': -1}, groupby=['degree']).items())
            [((2,), 8), ((3,), 7)]
        """
        if join is not None:
            if groupby is not None:
                raise ValueError("groupby is not supported with join")
            return self._join_count(query, join)
        return self.stats.count(query, groupby=groupby, record=record)

    def count_distinct(self, col, query={}, record=False):
        """
        Count the number of distinct values taken on by a given column.

        The result will be the same as taking the length of the distinct values, but a bit faster and can cache the answer

        INPUT:

        - ``col`` -- the name of the column, or a list of such names
        - ``query`` -- a query dictionary constraining which rows are considered
        - ``record`` -- (default False) whether to record the number of results
          in the stats table; opt-in for the same reason as in ``count``.
        """
        return self.stats.count_distinct(col, query, record=record)

    def sum(self, col, constraint={}):
        """
        The sum of a given column.

        INPUT:

        - ``col`` -- the name of the column
        - ``constraint`` -- a query dictionary constraining which rows are considered
        """
        return self.stats.sum(col, constraint)
