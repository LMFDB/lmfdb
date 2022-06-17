# -*- coding: utf-8 -*-
import logging
import time
from collections import defaultdict

from psycopg2 import DatabaseError
from psycopg2.sql import SQL, Identifier, Literal

from .base import PostgresBase
from .encoding import Json, numeric_converter
from .utils import DelayCommit, KeyedDefaultDict, make_tuple

# The following is used in bucketing for statistics
pg_to_py = {}
for typ in [
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
]:
    pg_to_py[typ] = int
for typ in ["numeric", "decimal"]:
    pg_to_py[typ] = numeric_converter
for typ in ["float4", "real", "float8", "double precision"]:
    pg_to_py[typ] = float
for typ in ["text", "char", "character", "character varying", "varchar"]:
    pg_to_py[typ] = str


class PostgresStatsTable(PostgresBase):
    """
    This object is used for storing statistics and counts for a search table.

    For each search table (e.g. ec_curvedata), there are two auxiliary tables supporting
    statistics functionality.  The counts table (e.g. ec_curvedata_counts) records
    the number of rows in the search table that satisfy a particular query.
    These counts are used by the website to display the number of matches on a
    search results page, and is also used on statistics pages and some browse pages.
    The stats table (e.g. ec_curvedata_stats) is used to record minimum, maximum and
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

        sage: list(db.mf_newforms.stats.extra_counts())[0]
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
    # By default we don't save counts.  You can inherit from this class and change
    # the following value to True, then set _stats_table_class_ to your new stats class on your table class
    saving = False

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

    def _has_stats(self, jcols, ccols, cvals, threshold, split_list=False, threshold_inequality=False, suffix=""):
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
        selecter = selecter.format(Identifier(self.stats + suffix), SQL(ccols), SQL(cvals), SQL(threshold))
        cur = self._execute(selecter, values)
        return cur.rowcount > 0

    def quick_count(self, query, split_list=False, suffix=""):
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
        if not query:
            return self.total
        cols, vals = self._split_dict(query)
        selecter = SQL(
            "SELECT count FROM {0} WHERE cols = %s AND values = %s AND split = %s"
        ).format(Identifier(self.counts + suffix))
        cur = self._execute(selecter, [cols, vals, split_list])
        if cur.rowcount:
            return int(cur.fetchone()[0])

    def null_counts(self, suffix=""):
        """
        Returns the columns with null values, together with the count of the number of null rows for each
        """
        selecter = SQL(
            "SELECT cols, count FROM {0} WHERE values = %s AND split = %s"
        ).format(Identifier(self.counts + suffix))
        cur = self._execute(selecter, [Json([None]), False])
        allcounts = {rec[0][0]: rec[1] for rec in cur}
        for col in self.table.search_cols:
            if col not in allcounts:
                allcounts[col] = self._slow_count({col: None}, suffix=suffix, extra=False)
        return {col: cnt for col, cnt in allcounts.items() if cnt > 0}

    def refresh_null_counts(self, suffix=""):
        """
        Recomputes the counts of null values for all search columns
        """
        for col in self.table.search_cols:
            self._slow_count({col: None}, suffix=suffix, extra=False)

    def _slow_count(self, query, split_list=False, record=True, suffix="", extra=True):
        """
        No shortcuts: actually count the rows in the search table.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``split_list`` -- see the ``add_stats`` method.
        - ``record`` -- boolean (default True).  Whether to store the result in the count table.
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
        if record and self.saving:
            self._record_count(query, nres, split_list, suffix, extra)
        return nres

    def _record_count(self, query, count, split_list=False, suffix="", extra=True):
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
        # We only want to record 0 counts for value [NULL], since other cases can break stats
        nullrec = (list(query.values()) == [None])
        cols, vals = self._split_dict(query)
        data = [count, cols, vals, split_list]
        if self.quick_count(query, suffix=suffix) is None:
            if count == 0 and not nullrec:
                return # we don't want to store 0 counts since it can break stats
            updater = SQL("INSERT INTO {0} (count, cols, values, split, extra) VALUES (%s, %s, %s, %s, %s)")
            data.append(extra)
        else:
            if count == 0 and not nullrec:
                updater = SQL("DELETE FROM {0} WHERE cols = %s AND values = %s AND split = %s")
                data = [cols, vals, split_list]
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

    def count(self, query={}, groupby=None, record=True):
        """
        Count the number of results for a given query.

        INPUT:

        - ``query`` -- a mongo-style dictionary, as in the ``search`` method.
        - ``record`` -- (default True) whether to record the number of results in the counts table.
        - ``groupby`` -- (default None) a list of columns

        OUTPUT:

        If ``grouby`` is None, the number of records satisfying the query.
        Otherwise, a dictionary with keys the distinct tuples of values taken on by the columns
        in ``groupby``, and values the number of rows with those values.

        EXAMPLES::

            sage: from lmfdb import db
            sage: nf = db.nf_fields
            sage: nf.stats.count({'degree':int(6),'galt':int(7)})
            244006
        """
        if groupby is None:
            nres = self.quick_count(query)
            if nres is None:
                nres = self._slow_count(query, record=record)
            return int(nres)
        else:
            # We don't currently support caching groupby counts
            qstr, values = self.table._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
            else:
                qstr = SQL(" WHERE ") + qstr
            selecter = SQL("SELECT COUNT(*), {0} FROM {1}{2} GROUP BY {0}").format(
                SQL(", ").join(map(Identifier, groupby)),
                Identifier(self.search_table),
                qstr,
            )
            print(selecter)
            cur = self._execute(selecter, values)
            return {tuple(rec[1:]): int(rec[0]) for rec in cur}

    def quick_count_distinct(self, cols, query={}, suffix=""):
        """
        Tries to quickly determine the number of distinct values of a column
        using the stats table.

        INPUT:

        - ``cols`` -- a list of column names
        - ``query`` -- a search query, as a dictionary
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to perform the count

        OUTPUT:

        Either an integer giving the number of distinct values, or None if not cached.
        """
        ccols, cvals = self._split_dict(query)
        selecter = SQL("SELECT value FROM {0} WHERE stat = %s AND cols = %s AND constraint_cols = %s AND constraint_values = %s").format(Identifier(self.stats + suffix))
        cur = self._execute(selecter, ["distinct", Json(cols), ccols, cvals])
        if cur.rowcount:
            return int(cur.fetchone()[0])

    def _slow_count_distinct(self, cols, query={}, record=True, suffix=""):
        """
        No shortcuts: actually count the number of distinct values in the search table.

        INPUT:

        - ``cols`` -- a list of column names
        - ``query`` -- a search query, as a dictionary
        - ``record`` -- boolean (default True).  Whether to store the result in the stats table.
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to perform the count

        OUTPUT:

        The number of distinct values taken on by the specified columns among rows satisfying the constraint.
        """
        qstr, values = self.table._parse_dict(query)
        selecter = SQL("SELECT COUNT(*) FROM (SELECT DISTINCT {0} FROM {1}{2}) AS temp").format(
            SQL(", ").join(map(Identifier, cols)),
            Identifier(self.search_table + suffix),
            SQL("") if qstr is None else SQL(" WHERE {0}").format(qstr))
        cur = self._execute(selecter, values)
        nres = cur.fetchone()[0]
        if record and self.saving:
            self._record_count_distinct(cols, query, nres, suffix)
        return nres

    def _record_count_distinct(self, cols, query, count, suffix=""):
        """
        Add the count to the stats table.

        INPUT:

        - ``cols`` -- a list of column names
        - ``query`` -- a search query, as a dictionary
        - ``count`` -- the number of distinct values taken on by the column
        - ``suffix`` -- if provided, the table with that suffix added will be
            used to perform the count
        """
        ccols, cvals = self._split_dict(query)
        data = [count, Json(cols), "distinct", ccols, cvals]
        if self.quick_count_distinct(cols, query, suffix=suffix) is None:
            updater = SQL("INSERT INTO {0} (value, cols, stat, constraint_cols, constraint_values) VALUES (%s, %s, %s, %s, %s)")
        else:
            updater = SQL("UPDATE {0} SET value = %s WHERE cols = %s AND stats = %s AND constraint_cols = %s AND constraint_values = %s")
        try:
            # This will fail if we don't have write permission,
            # for example, if we're running as the lmfdb user
            self._execute(updater.format(Identifier(self.stats + suffix)), data)
        except DatabaseError:
            raise

    def count_distinct(self, col, query={}, record=True):
        """
        Count the number of distinct values taken on by given column(s).

        The result will be the same as taking the length of the distinct values, but a bit faster and caches the answer

        INPUT:

        - ``col`` -- the name of the column, or a list of such names
        - ``query`` -- a query dictionary constraining which rows are considered
        - ``record`` -- (default True) whether to record the number of results in the stats table.
        """
        if isinstance(col, str):
            col = [col]
        nres = self.quick_count_distinct(col, query)
        if nres is None:
            nres = self._slow_count_distinct(col, query, record=record)
        return int(nres)

    def column_counts(self, cols, constraint=None, threshold=1, split_list=False):
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

        If the value taken on by a column is a dictionary D, then the key will be tuple(D.items()).  However, we omit entries where D contains only keys starting with ``$``, since these are used to encode queries.
        """
        if isinstance(cols, str):
            cols = [cols]
            one_col = True
        else:
            one_col = False
            cols = sorted(cols)
        if constraint is None:
            ccols, cvals, allcols = Json([]), Json([]), cols
        else:
            ccols, cvals = self._split_dict(constraint)
            allcols = sorted(list(set(cols + list(constraint))))
            # Ideally we would include the constraint in the query, but it's not easy to do that
            # So we check the results in Python
        jcols = Json(cols)
        if not self._has_stats(
            jcols,
            ccols,
            cvals,
            threshold=threshold,
            split_list=split_list,
            threshold_inequality=True,
        ):
            self.add_stats(cols, constraint, threshold, split_list)
        jallcols = Json(allcols)
        if threshold is None:
            thresh = SQL("")
        else:
            thresh = SQL(" AND count >= {0}").format(Literal(threshold))
        selecter = SQL(
            "SELECT values, count FROM {0} WHERE cols = %s AND split = %s{1}"
        ).format(Identifier(self.counts), thresh)
        cur = self._execute(selecter, [jallcols, split_list])
        if one_col:
            _make_tuple = lambda x: make_tuple(x)[0]
        else:
            _make_tuple = make_tuple
        if constraint is None:
            # We need to remove counts that aren't the actual value,
            # but instead part of a query
            return {
                _make_tuple(rec[0]): rec[1]
                for rec in cur
                if not any(
                    isinstance(val, dict) and all(
                        isinstance(k, str) and k.startswith("$") for k in val
                    )
                    for val in rec[0]
                )
            }
        else:
            constraint_list = [
                (i, constraint[col])
                for (i, col) in enumerate(allcols)
                if col in constraint
            ]
            column_indexes = [i for (i, col) in enumerate(allcols) if col not in constraint]

            def satisfies_constraint(val):
                return all(val[i] == c for i, c in constraint_list) and not any(
                    isinstance(val[i], dict)
                    and all(
                        isinstance(k, str) and k.startswith("$")
                        for k in val[i]
                    )
                    for i in column_indexes
                )

            def remove_constraint(val):
                return [val[i] for i in column_indexes]

            return {
                _make_tuple(remove_constraint(rec[0])): rec[1]
                for rec in cur
                if satisfies_constraint(rec[0])
            }

    def _quick_extreme(self, col, ccols, cvals, kind="max"):
        """
        Return the min or max value achieved by the column, or None if not cached.

        INPUT::

        - ``col`` -- the column
        - ``ccols`` -- constraint columns
        - ``cvals`` -- constraint values.  The max will be taken over rows where
            the constraint columns take on these values.
        - ``kind`` -- either "min" or "max"
        """
        constraint = SQL("constraint_cols = %s AND constraint_values = %s")
        values = [kind, Json([col]), ccols, cvals]
        selecter = SQL(
            "SELECT value FROM {0} WHERE stat = %s AND cols = %s AND threshold IS NULL AND {1}"
        ).format(Identifier(self.stats), constraint)
        cur = self._execute(selecter, values)
        if cur.rowcount:
            return cur.fetchone()[0]

    def _slow_extreme(self, col, constraint, kind="max"):
        """
        Compute the minimum/maximum value achieved by the column.

        INPUT::

        - ``col`` -- the column
        - ``constraint`` -- a dictionary giving a constraint.  The min/max will be taken
            over rows satisfying this constraint.
        """
        qstr, values = self.table._parse_dict(constraint)
        if qstr is None:
            where = SQL("")
            values = []
        else:
            where = SQL(" WHERE {0}").format(qstr)
        if kind == "min":
            base_selecter = SQL("SELECT {0} FROM {1}{2} ORDER BY {0}")
        elif kind == "max":
            base_selecter = SQL("SELECT {0} FROM {1}{2} ORDER BY {0} DESC ")
        else:
            raise ValueError("Invalid kind")
        base_selecter = base_selecter.format(
            Identifier(col), Identifier(self.search_table), where
        )
        selecter = base_selecter + SQL("LIMIT 1")
        cur = self._execute(selecter, values)
        m = cur.fetchone()[0]
        if m is None and kind == "max":
            # the default order ends with NULLs, so we now have to use NULLS LAST,
            # preventing the use of indexes.
            selecter = base_selecter + SQL("NULLS LAST LIMIT 1")
            cur = self._execute(selecter, values)
            m = cur.fetchone()[0]
        return m

    def _record_extreme(self, col, ccols, cvals, m, kind="max"):
        """
        Store a computed maximum value in the stats table.

        INPUT:

        - ``col`` -- the column on which the max is taken
        - ``ccols`` -- the constraint columns
        - ``cvals`` -- the constraint values
        - ``m`` -- the maximum value to be stored
        """
        try:
            inserter = SQL(
                "INSERT INTO {0} "
                "(cols, stat, value, constraint_cols, constraint_values) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
            self._execute(
                inserter.format(Identifier(self.stats)),
                [Json([col]), kind, m, ccols, cvals],
            )
        except Exception:
            pass

    def max(self, col, constraint={}, record=True):
        """
        The maximum value attained by the given column, which must be in the search table.

        Will raise an error if there are no non-null values of the column.

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
        if col not in self.table.search_cols:
            raise ValueError("%s not a column of %s" % (col, self.search_table))
        ccols, cvals = self._split_dict(constraint)
        m = self._quick_extreme(col, ccols, cvals, kind="max")
        if m is None:
            m = self._slow_extreme(col, constraint, kind="max")
            if record and self.saving:
                self._record_extreme(col, ccols, cvals, m, kind="max")
        return m

    def min(self, col, constraint={}, record=True):
        """
        The minimum value attained by the given column, which must be in the search table.

        Will raise an error if there are no non-null values of the column.

        INPUT:

        - ``col`` -- the column on which the min is taken.
        - ``constraint`` -- a dictionary giving a constraint.  The min will be taken
            over rows satisfying this constraint.
        - ``record`` -- whether to store the result in the stats table.

        EXAMPLES::

            sage: from lmfdb import db
            sage: db.ec_mwbsd.stats.min('area')
            0.00000013296713869846309987200099760
        """
        if col not in self.table.search_cols:
            raise ValueError("%s not a column of %s" % (col, self.search_table))
        ccols, cvals = self._split_dict(constraint)
        m = self._quick_extreme(col, ccols, cvals, kind="min")
        if m is None:
            m = self._slow_extreme(col, constraint, kind="min")
            if record and self.saving:
                self._record_extreme(col, ccols, cvals, m, kind="min")
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
        from sage.all import cartesian_product_iterator
        expanded_buckets = []
        for col, divisions in buckets.items():
            parse_singleton = pg_to_py[self.table.col_type[col]]
            cur_list = []
            for bucket in divisions:
                if not bucket:
                    continue
                if bucket[-1] == "-":
                    a = parse_singleton(bucket[:-1])
                    cur_list.append({col: {"$gte": a}})
                elif "-" not in bucket[1:]:
                    cur_list.append({col: parse_singleton(bucket)})
                else:
                    if bucket[0] == "-":
                        L = bucket[1:].split("-")
                        L[0] = "-" + L[0]
                    else:
                        L = bucket.split("-")
                    a, b = map(parse_singleton, L)
                    cur_list.append({col: {"$gte": a, "$lte": b}})
            expanded_buckets.append(cur_list)
        for X in cartesian_product_iterator(expanded_buckets):
            if constraint is None:
                bucketed_constraint = {}
            else:
                bucketed_constraint = dict(constraint)  # copy
            for D in X:
                bucketed_constraint.update(D)
            yield bucketed_constraint

    def add_bucketed_counts(self, cols, buckets, constraint={}, commit=True):
        """
        A convenience function for adding statistics on a given set of columns,
        where rows are grouped into intervals by a bucketing dictionary.

        See the ``add_stats`` method for the actual statistics computed.

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
            return [Json(t) for t in zip(*sorted(D.items()))]
        else:
            return [Json([]), Json([])]

    def _join_dict(self, ccols, cvals):
        """
        A utility function for joining a list of keys and of values into a dictionary.
        """
        assert len(ccols) == len(cvals)
        return dict(zip(ccols, cvals))

    def _print_statmsg(
        self, cols, constraint, threshold, grouping=None, split_list=False, tense="now"
    ):
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
            msg = "numerical statistics for %s, grouped by %s," % (
                cols[0],
                "+".join(grouping),
            )
        if tense == "now":
            msg = "Adding %s to %s " % (msg, self.search_table)
        else:
            msg = "%s " % msg.capitalize()
        if grouping is None and cols:
            msg += "for " + ", ".join(cols)
        if constraint:
            from .utils import range_formatter

            msg += ": " + ", ".join(
                "{col} = {disp}".format(col=col, disp=range_formatter(val))
                for col, val in constraint.items()
            )
        if threshold:
            msg += " (threshold=%s)" % threshold
        if tense == "now":
            self.logger.info(msg)
        else:
            print(msg)

    def _compute_numstats(
        self,
        col,
        grouping,
        where,
        values,
        constraint=None,
        threshold=None,
        suffix="",
        silent=False,
    ):
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
        cols = SQL("COUNT(*), AVG({0}), MIN({0}), MAX({0})").format(Identifier(col))
        if grouping:
            groups = SQL(", ").join(map(Identifier, grouping))
            groupby = SQL(" GROUP BY {0}").format(groups)
            cols = SQL("{0}, {1}").format(cols, groups)
        else:
            groupby = SQL("")
        selecter = SQL("SELECT {cols} FROM {table}{where}{groupby}{having}").format(
            cols=cols,
            table=Identifier(self.search_table + suffix),
            groupby=groupby,
            where=where,
            having=having,
        )
        return self._execute(selecter, values)

    def add_numstats(
        self, col, grouping, constraint=None, threshold=None, suffix="", commit=True
    ):
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
        if isinstance(grouping, str):
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
        if self._has_numstats(jcol, jcgcols, cvals, threshold, suffix=suffix):
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
            stats_to_add.append((
                jcol,
                "ntotal",
                total,
                Json(ccols.adapted + grouping),
                cvals,
                threshold,
            ))
            # It's possible that stats/counts have been added by an add_stats call
            # The right solution is a unique index and an ON CONFLICT DO NOTHING clause,
            # but for now we just live with the possibility of a few duplicate rows.
            inserter = SQL("INSERT INTO {0} (cols, stat, value, constraint_cols, constraint_values, threshold) VALUES %s")
            self._execute(
                inserter.format(Identifier(self.stats + suffix)),
                stats_to_add,
                values_list=True,
            )
            inserter = SQL("INSERT INTO {0} (cols, values, count, split, extra) VALUES %s")
            self._execute(
                inserter.format(Identifier(self.counts + suffix)),
                counts_to_add,
                values_list=True,
            )
        self.logger.info("Added numstats in %.3f secs" % (time.time() - now))

    def _has_numstats(self, jcol, cgcols, cvals, threshold, suffix=""):
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
        selecter = selecter.format(Identifier(self.stats + suffix), SQL(threshold))
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
        if isinstance(grouping, str):
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
        for rec in self._execute(selecter, values):
            stat, val, cgvals = rec
            if stat == "ntotal":
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
            allcols = sorted(list(set(cols + list(constraint))))
            if any(key.startswith("$") for key in constraint):
                raise ValueError("Top level special keys not allowed")
            qstr, values = self.table._parse_dict(constraint)
            if qstr is not None:
                where.append(qstr)
        if allcols:
            where = SQL(" WHERE {0}").format(SQL(" AND ").join(where))
        else:
            where = SQL("")
        return where, values, constraint, ccols, cvals, allcols

    def _compute_stats(
        self,
        cols,
        where,
        values,
        constraint=None,
        threshold=None,
        split_list=False,
        suffix="",
        silent=False,
    ):
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
            cols_vars = SQL(", ").join(map(Identifier, cols))
            groupby = SQL(" GROUP BY {0}").format(cols_vars)
            cols_vars = SQL("{0}, COUNT(*)").format(cols_vars)
        else:
            cols_vars = SQL("COUNT(*)")
            groupby = SQL("")
        selecter = SQL(
            "SELECT {cols_vars} FROM {table}{where}{groupby}{having}"
        ).format(
            cols_vars=cols_vars,
            table=Identifier(self.search_table + suffix),
            groupby=groupby,
            where=where,
            having=having,
        )
        return self._execute(selecter, values)

    def add_stats(
        self,
        cols,
        constraint=None,
        threshold=None,
        split_list=False,
        suffix="",
        commit=True,
    ):
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
        if self._db._read_only:
            self.logger.info("Read only mode, not recording stats")
            return
        from sage.all import cartesian_product_iterator
        if split_list and threshold is not None:
            raise ValueError("split_list and threshold not simultaneously supported")
        cols = sorted(cols)
        where, values, constraint, ccols, cvals, allcols = self._process_constraint(cols, constraint)
        if self._has_stats(Json(cols), ccols, cvals, threshold, split_list, suffix=suffix):
            self.logger.info("Statistics already exist")
            return
        now = time.time()
        seen_one = False
        if split_list:
            to_add = defaultdict(int)
            allcols = tuple(allcols)
        else:
            to_add = []
            jallcols = Json(allcols)
        total = 0
        onenumeric = False  # whether we're grouping by a single numeric column
        if len(cols) == 1 and self.table.col_type.get(cols[0]) in [
            "numeric",
            "bigint",
            "integer",
            "smallint",
            "double precision",
        ]:
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
                self.logger.info(
                    "No rows exceeded the threshold; returning after %.3f secs"
                    % (time.time() - now)
                )
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
            self._execute(
                inserter.format(Identifier(self.stats + suffix)),
                stats,
                values_list=True,
            )
            inserter = SQL("INSERT INTO {0} (cols, values, count, split, extra) VALUES %s")
            if split_list:
                to_add = [
                    (Json(c), Json(v), ct, True, False)
                    for ((c, v), ct) in to_add.items()
                ]
            self._execute(
                inserter.format(Identifier(self.counts + suffix)),
                to_add,
                values_list=True,
            )
            if len(to_add) > 10000:
                logging.warning(
                    "{:d} rows were just inserted to".format(len(to_add))
                    + " into {}, ".format(self.counts + suffix)
                    + "all with with cols = {}. ".format(jallcols)
                    + "This might decrease the counts table performance "
                    + "significantly! Consider clearing all the stats "
                    + "db.{}.stats._clear_stats_counts()".format(self.search_table)
                    + " and rebuilding the stats more carefully."
                )
        self.logger.info("Added stats in %.3f secs" % (time.time() - now))
        return True

    def _approx_most_common(self, col, n):
        """
        Returns the n most common values for ``col``.  Counts are only approximate,
        but this functions should be quite fast.  Note that the returned list
        may have length less than ``n`` if there are not many common values.

        Returns a list of pairs ``(value, count)`` where ``count`` is
        the number of rows where ``col`` takes on the value ``value``.

        INPUT:

        - ``col`` -- a column name
        - ``n`` -- an integer
        """
        if col not in self.table.search_cols:
            raise ValueError("Column %s not a search column for %s" % (col, self.search_table))
        selecter = SQL(
            """SELECT v.{0}, (c.reltuples * freq)::int as estimate_ct
FROM pg_stats s
CROSS JOIN LATERAL
   unnest(s.most_common_vals::text::"""
            + self.table.col_type[col]
            + """[]
        , s.most_common_freqs) WITH ORDINALITY v ({0}, freq, ord)
CROSS  JOIN (
   SELECT reltuples FROM pg_class
   WHERE oid = regclass 'public.nf_fields') c
WHERE schemaname = 'public' AND tablename = %s AND attname = %s
ORDER BY v.ord LIMIT %s"""
        ).format(Identifier(col))
        cur = self._execute(selecter, [self.search_table, col, n])
        return [tuple(x) for x in cur]

    def _common_cols(self, threshold=700):
        """
        Returns a list of columns where the most common value has a count of at least the given threshold.
        """
        common_cols = []
        for col in self.table.search_cols:
            most_common = self._approx_most_common(col, 1)
            if most_common and most_common[0][1] >= threshold:
                common_cols.append(col)
        return common_cols

    def _clear_stats_counts(self, extra=True, suffix=""):
        """
        Deletes all stats and counts.  This cannot be undone.

        INPUT:

        - ``extra`` -- if false, only delete the rows of the counts table not marked as extra.
        """
        deleter = SQL("DELETE FROM {0}")
        self._execute(deleter.format(Identifier(self.stats + suffix)))
        if not extra:
            deleter = SQL("DELETE FROM {0} WHERE extra IS NOT TRUE")  # false and null
        self._execute(deleter.format(Identifier(self.counts + suffix)))

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
        from sage.all import binomial
        with DelayCommit(self, silence=True):
            if cols is None:
                cols = self._common_cols()
            for constraint in constraints:
                ccols, cvals = self._split_dict(constraint)
                level = 0
                curlevel = [([], None)]
                while curlevel:
                    i = 0
                    logging.info(
                        "Starting level %s/%s (%s/%s colvecs)"
                        % (level, len(cols), len(curlevel), binomial(len(cols), level))
                    )
                    while i < len(curlevel):
                        colvec, _ = curlevel[i]
                        if self._has_stats(
                            Json(cols),
                            ccols,
                            cvals,
                            threshold=threshold,
                            threshold_inequality=True,
                        ):
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
                            for j in range(m + 1, len(cols)):
                                col = cols[j]
                                if not isinstance(col, list):
                                    col = [col]
                                curlevel.append((colvec + col, j))
                    level += 1

    def _status(self, reset_None_to_1=False):
        """
        Returns information that can be used to recreate the statistics table.

        INPUT:

        - ``reset_None_to_1`` -- change threshold None to 1 in the stored statistics

        OUTPUT:

        - ``stats_cmds`` -- a list of quadruples (cols, ccols, cvals, threshold) for input into add_stats
        - ``split_cmds`` -- a list of quadruples (cols, ccols, cvals, threshold) for input into add_stats with split_list=True
        - ``nstat_cmds`` -- a list of quintuples (col, grouping, ccols, cvals, threshold) for input into add_numstats
        """
        selecter = SQL(
            "SELECT cols, constraint_cols, constraint_values, threshold FROM {0} WHERE stat = %s"
        ).format(Identifier(self.stats))
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
                ccols = cgcols[: len(cvals)]
            nstat_cmds.append((cols[0], grouping, ccols, cvals, threshold))
        if reset_None_to_1:
            for L in [stat_cmds, split_cmds, nstat_cmds]:
                for i in range(len(L)):
                    newval = list(L[i])
                    if newval[-1] is None:
                        newval[-1] = 1
                        L[i] = tuple(newval)
        return stat_cmds, split_cmds, nstat_cmds

    def refresh_stats(self, total=True, reset_None_to_1=False, suffix=""):
        """
        Regenerate stats and counts, using rows with ``stat = "total"`` in the stats
        table to determine which stats to recompute, and the rows with ``extra = True``
        in the counts table which have been added by user searches.

        INPUT:

        - ``total`` -- if False, doesn't update the total count (since we can often
            update the total cheaply)
        - ``reset_None_to_1`` -- change threshold None to 1 in stored statistics
        - ``suffix`` -- appended to the table name when computing and storing stats.
            Used when reloading a table.
        """
        self.logger.info("Refreshing statistics on %s" % self.search_table)
        t0 = time.time()
        with DelayCommit(self, silence=True):
            # Determine the stats and counts currently recorded
            stat_cmds, split_cmds, nstat_cmds = self._status(reset_None_to_1)
            col_value_dict = self.extra_counts(include_counts=False, suffix=suffix)

            # Delete all stats and counts
            deleter = SQL("DELETE FROM {0}")
            self._execute(deleter.format(Identifier(self.stats + suffix)))
            self._execute(deleter.format(Identifier(self.counts + suffix)))

            # Regenerate stats and counts
            for cols, ccols, cvals, threshold in stat_cmds:
                self.add_stats(cols, (ccols, cvals), threshold, suffix=suffix)
            for cols, ccols, cvals, threshold in split_cmds:
                self.add_stats(cols, (ccols, cvals), threshold, split_list=True, suffix=suffix)
            for col, grouping, ccols, cvals, threshold in nstat_cmds:
                self.add_numstats(col, grouping, (ccols, cvals), threshold, suffix=suffix)
            self._add_extra_counts(col_value_dict, suffix=suffix)

            if total:
                # Refresh total in meta_tables
                self.total = self._slow_count({}, suffix=suffix, extra=False)
            self.logger.info("Refreshed statistics in %.3f secs" % (time.time() - t0))

    def status(self, reset_None_to_1=False):
        """
        Prints a status report on the statistics for this table.
        """
        stat_cmds, split_cmds, nstat_cmds = self._status(reset_None_to_1)
        col_value_dict = self.extra_counts(include_counts=False)
        have_stats = stat_cmds or split_cmds or nstat_cmds
        if have_stats:
            for cols, ccols, cvals, threshold in stat_cmds:
                print("  ", end=" ")
                self._print_statmsg(cols, (ccols, cvals), threshold, tense="past")
            for cols, ccols, cvals, threshold in split_cmds:
                print("  ", end=" ")
                self._print_statmsg(cols, (ccols, cvals), threshold, split_list=True, tense="past")
            for col, grouping, ccols, cvals, threshold in nstat_cmds:
                print("  ", end=" ")
                self._print_statmsg([col], (ccols, cvals), threshold, grouping=grouping, tense="past")
            selecter = SQL("SELECT COUNT(*) FROM {0} WHERE extra = %s").format(Identifier(self.counts))
            count_nrows = self._execute(selecter, [False]).fetchone()[0]
            selecter = SQL("SELECT COUNT(*) FROM {0}").format(Identifier(self.stats))
            stats_nrows = self._execute(selecter).fetchone()[0]
            msg = (
                "hese statistics take up %s rows in the stats table and %s rows in the counts table."
                % (stats_nrows, count_nrows)
            )
            if len(stat_cmds) + len(split_cmds) + len(nstat_cmds) == 1:
                print("T" + msg)
            else:
                print("Altogether, t" + msg)
        else:
            print("No statistics have been computed for this table.")
        if col_value_dict:
            if have_stats:
                print(
                    "In addition to the statistics described above, "
                    "additional counts are recorded",
                    end=" ",
                )
            else:
                print("The following counts are being stored", end=" ")
            print(" (we collect all counts referring to the same columns):")
            for cols, values in col_value_dict.items():
                print(
                    "  (%s): %s row%s in counts table"
                    % (", ".join(cols), len(values), "" if len(values) == 1 else "s")
                )
        else:
            if have_stats:
                print("No additional counts are stored.")
            else:
                print("No counts are stored for this table.")

    def _copy_extra_counts_to_tmp(self):
        """
        Generates the extra counts in the ``_tmp`` table using the
        extra counts that currently exist in the main table.
        """
        col_value_dict = self.extra_counts(include_counts=False)
        self._add_extra_counts(col_value_dict, suffix="_tmp")

    def _add_extra_counts(self, col_value_dict, suffix=""):
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

    def extra_counts(self, include_counts=True, suffix=""):
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
        selecter = SQL("SELECT cols, values, count FROM {0} WHERE extra ='t'").format(
            Identifier(self.counts + suffix)
        )
        cur = self._execute(selecter)
        ans = defaultdict(list)
        for cols, values, count in cur:
            if include_counts:
                ans[tuple(cols)].append((tuple(values), count))
            else:
                ans[tuple(cols)].append(tuple(values))

        return ans

    def _get_values_counts(
        self,
        cols,
        constraint,
        split_list,
        formatter,
        query_formatter,
        base_url,
        buckets=None,
        recursing=False,
    ):
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
        selecter_constraints = [SQL("split = %s"), SQL("cols = %s"), SQL("count > 0")]
        if constraint:
            allcols = sorted(set(cols + list(constraint)))
            selecter_values = [split_list, Json(allcols)]
            for i, x in enumerate(allcols):
                if x in constraint:
                    cx = constraint[x]
                    if isinstance(cx, dict) and all(isinstance(k, str) and k and k[0] == "$" for k in cx):
                        # Have to handle some constraint parsing here
                        typ = self.table.col_type[x]
                        for k, v in cx.items():
                            if k in ['$gte', '$gt']:
                                oe = '>='
                                ko = '$gte' if k == '$gt' else '$gt'
                                op = '>' if k == '$gt' else '>='
                            elif k in ['$lte', '$lt']:
                                oe = '<='
                                ko = '$lte' if k == '$lt' else '$lt'
                                op = '<' if k == '$lt' else '<='
                            else:
                                raise ValueError("Unsupported constraint key: %s" % k)
                            selecter_constraints.append(SQL(
                                "((values->{0}?%s AND (values->{0}->>%s)::{1} {3} %s) OR "
                                "(values->{0}?%s AND (values->{0}->>%s)::{1} {2} %s) OR "
                                "(jsonb_typeof(values->{0}) = %s AND (values->>{0})::{1} {2} %s))".format(
                                    i, typ, op, oe)))
                            selecter_values.extend([k, k, v, ko, ko, v, "number", v])
                    else:
                        selecter_constraints.append(SQL("values->{0} = %s".format(i)))
                        selecter_values.append(Json(cx))
        else:
            allcols = sorted(cols)
            selecter_values = [split_list, Json(allcols)]
        positions = [allcols.index(x) for x in cols]
        selecter = SQL("SELECT values, count FROM {0} WHERE {1}").format(
            Identifier(self.counts), SQL(" AND ").join(selecter_constraints)
        )
        headers = [[] for _ in cols]
        default_proportion = "      0.00%" if len(cols) == 1 else ""

        def make_count_dict(values, cnt):
            if isinstance(values, (list, tuple)):
                query = base_url + "&".join(query_formatter[col](val) for col, val in zip(cols, values))
            else:
                query = base_url + query_formatter[cols[0]](values)
            return {
                "count": cnt,
                "query": query,
                "proportion": default_proportion,  # will be overridden for nonzero cnts.
            }

        data = KeyedDefaultDict(lambda key: make_count_dict(key, 0))
        if buckets:
            buckets_seen = set()
            bucket_positions = [i for (i, col) in enumerate(cols) if col in buckets]
        for values, count in self._execute(selecter, values=selecter_values):
            values = [values[i] for i in positions]
            if any(
                isinstance(val, dict)
                and any(relkey in val for relkey in ["$lt", "$lte", "$gt", "$gte", "$exists"])
                and cols[i] not in buckets
                for (i, val) in enumerate(values)
            ):
                # For non-bucketed statistics, we don't want to include counts for range queries
                continue
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
        if not buckets:
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
                    logging.info(
                        "Adding statistics for %s with constraints %s"
                        % (
                            ", ".join(cols),
                            ", ".join(
                                "%s:%s" % (cc, cv)
                                for cc, cv in bucketed_constraint.items()
                            ),
                        )
                    )
                    self.add_stats(ucols, bucketed_constraint)
                    ok = False
        if not recursing and not ok:
            return self._get_values_counts(
                cols,
                constraint,
                split_list,
                formatter,
                query_formatter,
                base_url,
                buckets,
                recursing=True
            )
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
        totaler = SQL(
            "SELECT value FROM {0} WHERE cols = %s AND stat = %s AND threshold IS NULL"
        ).format(Identifier(self.stats))
        ccols, cvals = self._split_dict(constraint)
        totaler = SQL("{0} AND constraint_cols = %s AND constraint_values = %s").format(totaler)
        totaler_values = [jcols, total_str, ccols, cvals]
        cur_total = self._execute(totaler, values=totaler_values)
        if cur_total.rowcount == 0:
            raise ValueError("Database does not contain stats for %s" % (cols[0],))
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
        print("Oldstats created successfully")

    def get_oldstat(self, name):
        """
        Temporary support for statistics created in Mongo.
        """
        selecter = SQL("SELECT data FROM {0} WHERE _id = %s").format(Identifier(self.search_table + "_oldstats"))
        cur = self._execute(selecter, [name])
        if cur.rowcount != 1:
            raise ValueError("Not a unique oldstat identifier")
        return cur.fetchone()[0]
