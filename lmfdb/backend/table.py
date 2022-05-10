# -*- coding: utf-8 -*-
import csv
import os
import tempfile
import time

from psycopg2.sql import SQL, Identifier, Placeholder, Literal

from .encoding import Json, copy_dumps
from .base import PostgresBase, _meta_table_name
from .utils import DelayCommit, EmptyContext, IdentifierWrapper, LockError, psycopg2_version
from .base import (
    _meta_indexes_cols,
    _meta_constraints_cols,
    _meta_tables_cols,
    jsonb_idx,
)
from .statstable import PostgresStatsTable


# the non-default operator classes, used in creating indexes
_operator_classes = {
    "brin": ["inet_minmax_ops"],
    "btree": [
        "bpchar_pattern_ops",
        "cidr_ops",
        "record_image_ops",
        "text_pattern_ops",
        "varchar_ops",
        "varchar_pattern_ops",
    ],
    "gin": ["jsonb_path_ops"],
    "gist": ["inet_ops"],
    "hash": [
        "bpchar_pattern_ops",
        "cidr_ops",
        "text_pattern_ops",
        "varchar_ops",
        "varchar_pattern_ops",
    ],
    "spgist": ["kd_point_ops"],
}

# Valid storage parameters by type, used in creating indexes
_valid_storage_params = {
    "brin": ["pages_per_range", "autosummarize"],
    "btree": ["fillfactor"],
    "gin": ["fastupdate", "gin_pending_list_limit"],
    "gist": ["fillfactor", "buffering"],
    "hash": ["fillfactor"],
    "spgist": ["fillfactor"],
}


##################################################################
# counts and stats columns and their types                       #
##################################################################

_counts_cols = ("cols", "values", "count", "extra", "split")
_counts_types = dict(zip(_counts_cols, ("jsonb", "jsonb", "bigint", "boolean", "boolean")))
_counts_jsonb_idx = jsonb_idx(_counts_cols, _counts_types)
_counts_indexes = [
    {
        "name": "{}_cols_vals_split",
        "columns": ("cols", "values", "split"),
        "type": "btree",
    },
    {"name": "{}_cols_split", "columns": ("cols", "split"), "type": "btree"},
]


_stats_cols = (
    "cols",
    "stat",
    "value",
    "constraint_cols",
    "constraint_values",
    "threshold",
)
_stats_types = dict(zip(_stats_cols, ("jsonb", "text", "numeric", "jsonb", "jsonb", "integer")))
_stats_jsonb_idx = jsonb_idx(_stats_cols, _stats_types)


class PostgresTable(PostgresBase):
    """
    This class is used to abstract a table in the LMFDB database
    on which searches are performed.  Technically, it may represent
    more than one table, since some tables are split in two for performance
    reasons (into a search table, with columns that can be used for searching,
    and an extra table, with columns that cannot)

    INPUT:

    - ``db`` -- an instance of ``PostgresDatabase``
    - ``search_table`` -- a string, the name of the table in postgres.
    - ``label_col`` -- the column holding the LMFDB label, or None if no such column exists.
    - ``sort`` -- a list giving the default sort order on the table, or None.  If None, sorts that can return more than one result must explicitly specify a sort order.  Note that the id column is sometimes used for sorting; see the ``search`` method for more details.
    - ``count_cutoff`` -- an integer parameter (default 1000) which determines the threshold at which searches will no longer report the exact number of results.
    - ``id_ordered`` -- a boolean, whether the ids of the rows are in sort order.
        Used for improving search performance
    - ``out_of_order`` -- if the rows are supposed to be ordered by ID, this boolean value records
        that they are currently out of order due to insertions or updates.
    - ``has_extras`` -- boolean, whether this table is split into a search and extra table
    - ``stats_valid`` -- whether the statistics tables are currently up to date
    - ``total`` -- the total number of rows in the table; cached as a performance optimization
    - ``data_types`` -- a dictionary holding the data types of the columns; see the ``_column_types`` method for more details

    ATTRIBUTES:

    The following public attributes are available on instances of this class

    - ``search_table`` -- a string, the name of the associated postgres search table
    - ``extra_table`` -- either None, or a string giving the name of the extra table in postgres (generally it will be the search table with "_extras" appended
    - ``search_cols`` -- a list of column names in the search table.  Does not include the id column.
    - ``extra_cols`` -- a list of column names in the extra table.  Does not include the id column.  Will be the empty list if no extra table.
    - ``col_type`` -- a dictionary with keys the column names and values the postgres type of that column.
    - ``stats`` -- the attached ``PostgresStatsTable`` instance

    The following private attributes are sometimes also useful

    - ``_label_col`` -- the column used by default in the ``lookup`` method
    - ``_sort_org`` -- either None or a list of columns or pairs ``(col, direction)``
    - ``_sort_keys`` -- a set of column names included in the sort order
    - ``_primary_sort`` -- either None, a column name or a pair ``(col, direction)``, the most significant column when sorting
    - ``_sort`` -- the psycopg2.sql.Composable object containing the default sort clause
    """
    _stats_table_class_ = PostgresStatsTable

    def __init__(
        self,
        db,
        search_table,
        label_col,
        sort=None,
        count_cutoff=1000,
        id_ordered=False,
        out_of_order=False,
        has_extras=False,
        stats_valid=True,
        total=None,
        include_nones=False,
        data_types=None,
    ):
        self.search_table = search_table
        self._label_col = label_col
        self._count_cutoff = count_cutoff
        self._id_ordered = id_ordered
        self._out_of_order = out_of_order
        self._stats_valid = stats_valid
        self._include_nones = include_nones
        PostgresBase.__init__(self, search_table, db)
        self.col_type = {}
        self.has_id = False
        self.search_cols = []
        if has_extras:
            self.extra_table = search_table + "_extras"
            self.extra_cols, self.col_type, _ = self._column_types(self.extra_table, data_types=data_types)
        else:
            self.extra_table = None
            self.extra_cols = []

        self.search_cols, extend_coltype, self.has_id = self._column_types(search_table, data_types=data_types)
        self.col_type.update(extend_coltype)
        self._set_sort(sort)
        self.stats = self._stats_table_class_(self, total)

    def _set_sort(self, sort):
        """
        Initialize the sorting attributes from a list of columns or pairs (col, direction)
        """
        self._sort_orig = sort
        self._sort_keys = set([])
        if sort:
            for col in sort:
                if isinstance(col, str):
                    self._sort_keys.add(col)
                else:
                    self._sort_keys.add(col[0])
            self._primary_sort = sort[0]
            if not isinstance(self._primary_sort, str):
                self._primary_sort = self._primary_sort[0]
            self._sort = self._sort_str(sort)
        else:
            self._sort = self._primary_sort = None

    def __repr__(self):
        return "Interface to Postgres table %s" % (self.search_table)

    ##################################################################
    # Indexes and performance analysis                               #
    ##################################################################

    def analyze(self, query, projection=1, limit=1000, offset=0, sort=None, explain_only=False):
        """
        Prints an analysis of how a given query is being executed, for use in optimizing searches.

        INPUT:

        - ``query`` -- a query dictionary
        - ``projection`` -- outputs, as in the ``search`` method
        - ``limit`` -- a maximum on the number of rows to return
        - ``offset`` -- an offset starting point for results
        - ``sort`` -- a string or list specifying a sort order
        - ``explain_only`` -- whether to execute the query (if ``True`` then will only use Postgres' query planner rather than actually carrying out the query)

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
        cols = SQL(", ").join(map(IdentifierWrapper, search_cols + extra_cols))
        if limit is None:
            qstr, values = self._build_query(query, sort=sort)
        else:
            qstr, values = self._build_query(query, limit, offset, sort)
        tbl = self._get_table_clause(extra_cols)
        selecter = SQL("SELECT {0} FROM {1}{2}").format(cols, tbl, qstr)
        if explain_only:
            analyzer = SQL("EXPLAIN {0}").format(selecter)
        else:
            analyzer = SQL("EXPLAIN ANALYZE {0}").format(selecter)
        cur = self._db.cursor()
        print(cur.mogrify(selecter, values))
        cur = self._execute(analyzer, values, silent=True)
        for line in cur:
            print(line[0])

    def _list_built_indexes(self):
        """
        Lists built indexes names on the search table
        """
        return self._list_indexes(self.search_table)

    def list_indexes(self, verbose=False):
        """
        Lists the indexes on the search table present in meta_indexes

        INPUT:

        - ``verbose`` -- if True, prints the indexes; if False, returns a dictionary

        OUTPUT:

        - If not verbose, returns a dictionary with keys the index names and values a dictionary containing the type, columns and modifiers.

        NOTE:

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
                print("{0} ({1}): {2}".format(name, typ, ", ".join(colspec)))
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
            storage_params = SQL(" WITH ({0})").format(
                SQL(", ").join(SQL("{0} = %s".format(param)) for param in storage_params)
            )
        else:
            storage_params = SQL("")
        modifiers = [" " + " ".join(mods) if mods else "" for mods in modifiers]
        # The inner % operator is on strings prior to being wrapped by SQL: modifiers have been whitelisted.
        columns = SQL(", ").join(
            SQL("{0}%s" % mods).format(Identifier(col))
            for col, mods in zip(columns, modifiers)
        )
        # The inner % operator is on strings prior to being wrapped by SQL: type has been whitelisted.
        creator = SQL("CREATE INDEX {0} ON {1} USING %s ({2}){3}" % (type))
        return creator.format(Identifier(name), Identifier(table), columns, storage_params)

    def _create_counts_indexes(self, suffix="", warning_only=False):
        """
        A utility function for creating the default indexes on the counts tables
        """
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
                creator = self._create_index_statement(
                    name,
                    tablename + suffix,
                    index["type"],
                    index["columns"],
                    [[]] * len(index["columns"]),
                    storage_params,
                )
                self._execute(creator, list(storage_params.values()))
                print("Index {} created in {:.3f} secs".format(
                    index["name"].format(self.search_table), time.time() - now
                ))

    def _check_index_name(self, name, kind="Index"):
        """
        Checks to ensure that the given name doesn't end with one
        of the following restricted suffixes, and that it doesn't already exist

        - ``_tmp``
        - ``_pkey``
        - ``_oldN``
        - ``_depN``

        INPUT:

        - ``name`` -- string, the name of an index or constraint
        - ``kind`` -- either ``"Index"`` or ``"Constraint"``
        """
        self._check_restricted_suffix(name, kind)

        if self._relation_exists(name):  # this also works for constraints
            raise ValueError(
                "{} name {} is invalid, ".format(kind, name)
                + "a relation with that name already exists, "
                + "e.g, index, constraint or table; "
                + "try specifying a different name"
            )

        if kind == "Index":
            meta = "meta_indexes"
            meta_name = "index_name"
        elif kind == "Constraint":
            meta = "meta_constraints"
            meta_name = "constraint_name"
        else:
            raise ValueError("""kind={} is not "Index" or "Constraint" """)

        selecter = SQL("SELECT 1 FROM {} WHERE {} = %s AND table_name = %s")
        cur = self._execute(
            selecter.format(*tuple(map(Identifier, [meta, meta_name]))),
            [name, self.search_table],
        )
        if cur.rowcount > 0:
            raise ValueError(
                "{} name {} is invalid, ".format(kind, name)
                + "an {} with that name".format(kind.lower())
                + "already exists in {}; ".format(meta)
                + "try specifying a different name"
            )

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
                    if self.col_type[col] == "jsonb":
                        return ["jsonb_path_ops"]
                    elif self.col_type[col].endswith("[]"):
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
                    if (
                        mod.lower()
                        not in ["asc", "desc", "nulls first", "nulls last"]
                        + _operator_classes[type]
                    ):
                        raise ValueError("Invalid modifier %s" % (mod,))
        if storage_params is None:
            if type in ["btree", "hash", "gist", "spgist"]:
                storage_params = {"fillfactor": 100}
            else:
                storage_params = {}
        else:
            for key in storage_params:
                if key not in _valid_storage_params[type]:
                    raise ValueError("Invalid storage parameter %s" % key)
        for col in columns:
            if col != "id" and col not in self.search_cols:
                raise ValueError("%s not a column" % (col))
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
            creator = self._create_index_statement(
                name, self.search_table, type, columns, modifiers, storage_params
            )
            self._execute(creator, list(storage_params.values()))
            inserter = SQL("INSERT INTO meta_indexes (index_name, table_name, type, columns, modifiers, storage_params) VALUES (%s, %s, %s, %s, %s, %s)")
            self._execute(
                inserter,
                [
                    name,
                    self.search_table,
                    type,
                    Json(columns),
                    Json(modifiers),
                    storage_params,
                ],
            )
        print("Index %s created in %.3f secs" % (name, time.time() - now))

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
        print("Dropped index %s in %.3f secs" % (name, time.time() - now))

    def restore_index(self, name, suffix=""):
        """
        Restore a specified index using the meta_indexes table.

        INPUT:

        - ``name`` -- the name of the index
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the CREATE INDEX statement.
        """
        now = time.time()
        with DelayCommit(self, silence=True):
            selecter = SQL(
                "SELECT type, columns, modifiers, storage_params FROM meta_indexes "
                "WHERE table_name = %s AND index_name = %s"
            )
            cur = self._execute(selecter, [self.search_table, name])
            if cur.rowcount > 1:
                raise RuntimeError("Duplicated rows in meta_indexes")
            elif cur.rowcount == 0:
                raise ValueError("Index %s does not exist in meta_indexes" % (name,))
            type, columns, modifiers, storage_params = cur.fetchone()
            creator = self._create_index_statement(
                name + suffix,
                self.search_table + suffix,
                type,
                columns,
                modifiers,
                storage_params,
            )
            # this avoids clashes with deprecated indexes/constraints
            self._rename_if_exists(name, suffix)
            self._execute(creator, list(storage_params.values()))
        print("Created index %s in %.3f secs" % (name, time.time() - now))

    def _indexes_touching(self, columns):
        """
        Utility function for determining which indexes reference any of the given columns.
        """
        selecter = SQL("SELECT index_name FROM meta_indexes WHERE table_name = %s")
        if columns:
            selecter = SQL("{0} AND ({1})").format(
                selecter, SQL(" OR ").join(SQL("columns @> %s") * len(columns))
            )
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
            self._execute(command.format(
                Identifier(self.search_table + suffix),
                Identifier(self.search_table + suffix + "_pkey"),
            ))
            if self.extra_table is not None:
                self._execute(command.format(
                    Identifier(self.extra_table + suffix),
                    Identifier(self.extra_table + suffix + "_pkey"),
                ))
        print("%s primary key on %s in %.3f secs" % (action, self.search_table, time.time() - now))

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

        INPUT:

        - ``verbose`` -- if True, prints the constraints; if False, returns a dictionary

        OUTPUT:

        - If not verbose, returns a dictionary with keys the index names and values a dictionary containing the type, columns and the check_func

        NOTE:

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
                show = (name if check_func is None else "{0} {1}".format(name, check_func))
                print("{0} ({1}): {2}".format(show, typ, ", ".join(columns)))
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
            return SQL(
                "ALTER TABLE {0} ADD CONSTRAINT {1} UNIQUE ({2}) WITH (fillfactor=100)"
            ).format(Identifier(table), Identifier(name), cols)
        elif type == "CHECK":
            return SQL(
                "ALTER TABLE {0} ADD CONSTRAINT {1} CHECK (%s({2}))" % check_func
            ).format(Identifier(table), Identifier(name), cols)

    @staticmethod
    def _drop_constraint_statement(name, table, type, columns):
        """
        Utility function for making the drop constraint SQL statement.
        """
        if type == "NON NULL":
            return SQL("ALTER TABLE {0} ALTER COLUMN {1} DROP NOT NULL").format(
                Identifier(table), Identifier(columns[0])
            )
        else:
            return SQL("ALTER TABLE {0} DROP CONSTRAINT {1}").format(
                Identifier(table), Identifier(name)
            )

    _valid_constraint_types = ["UNIQUE", "CHECK", "NOT NULL"]
    _valid_check_functions = []  # defined in utils.psql

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
        if isinstance(columns, str):
            columns = [columns]
        if type not in self._valid_constraint_types:
            raise ValueError("Unrecognized constraint type")
        if check_func is not None and check_func not in self._valid_check_functions:
            # If the following line fails, add the desired function to the list defined above
            raise ValueError("%s not in list of approved check functions (edit db_backend to add)")
        if (check_func is None) == (type == "CHECK"):
            raise ValueError("check_func should specified just for CHECK constraints")
        if type == "NON NULL" and len(columns) != 1:
            raise ValueError("NON NULL only supports one column")
        search = None
        for col in columns:
            if col == "id":
                continue
            if col in self.search_cols:
                if search is False:
                    raise ValueError("Cannot mix search and extra columns")
                search = True
            elif col in self.extra_cols:
                if search is True:
                    raise ValueError("Cannot mix search and extra columns")
                search = False
            else:
                raise ValueError("%s not a column" % (col))
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
            self._check_index_name(name, "Constraint")  # also works for constraints
            table = self.search_table if search else self.extra_table
            creator = self._create_constraint_statement(name, table, type, columns, check_func)
            self._execute(creator)
            inserter = SQL(
                "INSERT INTO meta_constraints "
                "(constraint_name, table_name, type, columns, check_func) "
                "VALUES (%s, %s, %s, %s, %s)"
            )
            self._execute(inserter, [name, self.search_table, type, Json(columns), check_func])
        print("Constraint %s created in %.3f secs" % (name, time.time() - now))

    def _get_constraint_data(self, name, suffix):
        """
        Utility function for getting data on an existing constraint

        INPUT:

        - ``name`` -- the name of the constraint
        - ``suffix`` -- a suffix to be added to the returned table name

        OUTPUT:

        - ``type`` -- the type of the constraint
        - ``columns`` -- the columns of the constraint
        - ``check_func`` -- the function implementing the constraint
        - ``table`` -- the postgres table on which the constraint operates (with suffix appended)
        """
        selecter = SQL("SELECT type, columns, check_func FROM meta_constraints WHERE table_name = %s AND constraint_name = %s")
        cur = self._execute(selecter, [self.search_table, name])
        if cur.rowcount > 1:
            raise RuntimeError("Duplicated rows in meta_constraints")
        elif cur.rowcount == 0:
            raise ValueError("Constraint %s does not exist in meta_constraints" % (name,))
        type, columns, check_func = cur.fetchone()
        search = columns[0] in self.search_cols
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
        print("Dropped constraint %s in %.3f secs" % (name, time.time() - now))

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
        print("Created constraint %s in %.3f secs" % (name, time.time() - now))

    def _constraints_touching(self, columns):
        """
        Utility function for determining which constraints reference any of the given columns.
        """
        selecter = SQL("SELECT constraint_name FROM meta_constraints WHERE table_name = %s")
        if columns:
            selecter = SQL("{0} AND ({1})").format(
                selecter, SQL(" OR ").join(SQL("columns @> %s") * len(columns))
            )
            columns = [Json(col) for col in columns]
        return self._execute(selecter, [self.search_table] + columns, silent=True)

    ##################################################################
    # Exporting, reloading and reverting meta_tables, meta_indexes and meta_constraints     #
    ##################################################################

    def copy_to_meta(self, filename, sep="|"):
        self._copy_to_meta("meta_tables", filename, self.search_table, sep=sep)

    def copy_to_indexes(self, filename, sep="|"):
        self._copy_to_meta("meta_indexes", filename, self.search_table, sep=sep)

    def copy_to_constraints(self, filename, sep="|"):
        self._copy_to_meta("meta_constraints", filename, self.search_table, sep=sep)

    def _get_current_index_version(self):
        return self._get_current_meta_version("meta_indexes", self.search_table)

    def _get_current_constraint_version(self):
        return self._get_current_meta_version("meta_constraints", self.search_table)

    def reload_indexes(self, filename, sep="|"):
        return self._reload_meta("meta_indexes", filename, self.search_table, sep=sep)

    def reload_meta(self, filename, sep="|"):
        return self._reload_meta("meta_tables", filename, self.search_table, sep=sep)

    def reload_constraints(self, filename, sep="|"):
        return self._reload_meta("meta_constraints", filename, self.search_table, sep=sep)

    def revert_indexes(self, version=None):
        return self._revert_meta("meta_indexes", self.search_table, version)

    def revert_constraints(self, version=None):
        return self._revert_meta("meta_constraints", self.search_table, version)

    def revert_meta(self, version=None):
        return self._revert_meta("meta_tables", self.search_table, version)

    ##################################################################
    # Insertion and updating data                                    #
    ##################################################################

    def _check_locks(self, suffix="", types="all"):
        locks = self._table_locked(self.search_table + suffix, types)
        if self.extra_table:
            locks += self._table_locked(self.extra_table + suffix, types)
        if locks:
            typelen = max(len(locktype) for (locktype, pid) in locks) + 3
            for locktype, pid in locks:
                print(locktype + " " * (typelen - len(locktype)) + str(pid))
            raise LockError("Table is locked.  Please resolve the lock by killing the above processes and try again")

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

    def rewrite(
        self,
        func,
        query={},
        resort=True,
        reindex=True,
        restat=True,
        tostr_func=None,
        commit=True,
        searchfile=None,
        extrafile=None,
        progress_count=10000,
        **kwds
    ):
        """
        This function can be used to edit some or all records in the table.

        Note that if you want to add new columns, you must explicitly call add_column() first.

        INPUT:

        - ``func`` -- a function that takes a record (dictionary) as input and returns the modified record
        - ``query`` -- a query dictionary; only rows satisfying this query will be changed
        - ``resort`` -- whether to resort the table after running the rewrite
        - ``reindex`` -- whether to reindex the table after running the rewrite
        - ``restat`` -- whether to recompute statistics after running the rewrite
        - ``tostr_func`` -- a function to be used when writing data to the temp file
            defaults to copy_dumps from encoding
        - ``commit`` -- whether to actually execute the rewrite
        - ``searchfile`` -- a filename to use for the temp file holding the search table
        - ``extrafile`` -- a filename to use for the temp file holding the extra table
        - ``progress_count`` -- (default 10000) how frequently to print out status reports as the rewrite proceeds
        - ``**kwds`` -- any other keyword arguments are passed on to the ``reload`` method

        EXAMPLES:

        For example, to add a new column to artin_reps that tracks the
        signs of the galois conjugates, you would do the following::

            sage: from lmfdb import db
            sage: db.artin_reps.add_column('GalConjSigns','jsonb')
            sage: def add_signs(rec):
            ....:     rec['GalConjSigns'] = sorted(list(set([conj['Sign'] for conj in rec['GaloisConjugates']])))
            ....:     return rec
            sage: db.artin_reps.rewrite(add_signs)
        """
        search_cols = ["id"] + self.search_cols
        if self.extra_table is None:
            projection = search_cols
        else:
            projection = search_cols + self.extra_cols
            extra_cols = ["id"] + self.extra_cols
        # It would be nice to just use Postgres' COPY TO here, but it would then be hard
        # to give func access to the data to process.
        # An alternative approach would be to use COPY TO and have func and filter both
        # operate on the results, but then func would have to process the strings
        if tostr_func is None:
            tostr_func = copy_dumps
        if searchfile is None:
            searchfile = tempfile.NamedTemporaryFile("w", delete=False)
        elif os.path.exists(searchfile):
            raise ValueError("Search file %s already exists" % searchfile)
        else:
            searchfile = open(searchfile, "w")
        if self.extra_table is None:
            extrafile = EmptyContext()
        elif extrafile is None:
            extrafile = tempfile.NamedTemporaryFile("w", delete=False)
        elif os.path.exists(extrafile):
            raise ValueError("Extra file %s already exists" % extrafile)
        else:
            extrafile = open(extrafile, "w")
        start = time.time()
        count = 0
        tot = self.count(query)
        sep = kwds.get("sep", u"|")
        try:
            with searchfile:
                with extrafile:
                    # write headers
                    searchfile.write(sep.join(search_cols) + u"\n")
                    searchfile.write(
                        sep.join(self.col_type.get(col) for col in search_cols)
                        + u"\n\n"
                    )
                    if self.extra_table is not None:
                        extrafile.write(sep.join(extra_cols) + u"\n")
                        extrafile.write(
                            sep.join(self.col_type.get(col) for col in extra_cols)
                            + u"\n\n"
                        )

                    for rec in self.search(query, projection=projection, sort=[]):
                        processed = func(rec)
                        searchfile.write(
                            sep.join(
                                tostr_func(processed.get(col), self.col_type[col])
                                for col in search_cols
                            )
                            + u"\n"
                        )
                        if self.extra_table is not None:
                            extrafile.write(
                                sep.join(
                                    tostr_func(processed.get(col), self.col_type[col])
                                    for col in extra_cols
                                )
                                + u"\n"
                            )
                        count += 1
                        if (count % progress_count) == 0:
                            print(
                                "%d of %d records (%.1f percent) dumped in %.3f secs"
                                % (count, tot, 100.0 * count / tot, time.time() - start)
                            )
            print("All records dumped in %.3f secs" % (time.time() - start))
            self.reload(
                searchfile.name,
                extrafile.name,
                resort=resort,
                reindex=reindex,
                restat=restat,
                commit=commit,
                log_change=False,
                **kwds
            )
            self.log_db_change("rewrite", query=query, projection=projection)
        finally:
            os.unlink(searchfile.name)
            if self.extra_table is not None:
                os.unlink(extrafile.name)

    def update_from_file(
        self,
        datafile,
        label_col=None,
        inplace=False,
        resort=None,
        reindex=True,
        restat=True,
        commit=True,
        log_change=True,
        **kwds
    ):
        """
        Updates this table from data stored in a file.

        INPUT:

        - ``datafile`` -- a file with header lines (unlike ``reload``, does not need to include all columns) and rows containing data to be updated.
        - ``label_col`` -- a column specifying which row(s) of the table should be updated corresponding to each row of the input file.  This will usually be the label for the table, in which case it can be omitted.
        - ``inplace`` -- whether to do the update in place.  If set, the operation cannot be undone with ``reload_revert``.
        - ``resort`` -- whether this table should be resorted after updating (default is to resort when the sort columns intersect the updated columns)
        - ``reindex`` -- whether the indexes on this table should be dropped and recreated during update (default is to recreate only the indexes that touch the updated columns)
        - ``restat`` -- whether to recompute stats for the table
        - ``commit`` -- whether to actually commit the changes
        - ``log_change`` -- whether to log the update to the log table
        - ``kwds`` -- passed on to psycopg2's ``copy_from``.  Cannot include "columns".
        """
        self._check_locks()
        sep = kwds.get("sep", u"|")
        print("Updating %s from %s..." % (self.search_table, datafile))
        now = time.time()
        if label_col is None:
            label_col = self._label_col
            if label_col is None:
                raise ValueError("You must specify a column that is contained in the datafile and uniquely specifies each row")
        with open(datafile) as F:
            tables = [self.search_table]
            columns = self.search_cols
            if self.extra_table is not None:
                tables.append(self.extra_table)
                columns.extend(self.extra_cols)
            columns = self._check_header_lines(F, tables, set(columns), sep=sep, prohibit_missing=False)
            if columns[0] != label_col:
                raise ValueError("%s must be the first column in the data file" % label_col)
            # We don't allow updating id using this interface (it gets in the way of the tie-in with extras tables)
            if "id" in columns[1:]:
                raise ValueError("Cannot update id using update_from_file")
        if resort is None:
            resort = bool(set(columns[1:]).intersection(self._sort_keys))
        # Create a temp table to hold the data
        tmp_table = "tmp_update_from_file"

        def drop_tmp():
            dropper = SQL("DROP TABLE {0}").format(Identifier(tmp_table))
            self._execute(dropper)

        with DelayCommit(self, commit, silence=True):
            if self._table_exists(tmp_table):
                drop_tmp()
            processed_columns = SQL(", ").join([
                SQL("{0} " + self.col_type[col]).format(Identifier(col))
                for col in columns
            ])
            creator = SQL("CREATE TABLE {0} ({1})").format(Identifier(tmp_table), processed_columns)
            self._execute(creator)
            # We need to add an id column and populate it correctly
            if label_col != "id":
                coladd = SQL("ALTER TABLE {0} ADD COLUMN id bigint").format(Identifier(tmp_table))
                self._execute(coladd)
            self._copy_from(datafile, tmp_table, columns, True, kwds)
            if label_col != "id":
                # When using _copy_from, the id column was just added consecutively
                # We reset it to match the id from the search table
                idadder = SQL("UPDATE {0} SET id = {1}.id FROM {1} WHERE {0}.{2} = {1}.{2}").format(
                    Identifier(tmp_table),
                    Identifier(self.search_table),
                    Identifier(label_col),
                )
                self._execute(idadder)
            # don't include the label col
            scols = [col for col in columns[1:] if col in self.search_cols]
            if self.extra_table is not None:
                ecols = [col for col in columns[1:] if col in self.extra_cols]
            suffix = "" if inplace else "_tmp"
            stable = self.search_table + suffix
            etable = None if self.extra_table is None else self.extra_table + suffix
            if inplace:
                if reindex:
                    self.drop_indexes(columns[1:], commit=commit)
                if self.extra_table is not None and not ecols:
                    etable = None
            else:
                self._clone(self.search_table, stable)
                inserter = SQL("INSERT INTO {0} SELECT * FROM {1}")
                self._execute(inserter.format(Identifier(stable), Identifier(self.search_table)))
                if self.extra_table is None or not ecols:
                    etable = None
                else:
                    self._clone(self.extra_table, etable)
                    self._execute(inserter.format(Identifier(etable), Identifier(self.extra_table)))
            scols = SQL(", ").join([
                SQL("{0} = {1}.{0}").format(Identifier(col), Identifier(tmp_table))
                for col in scols
            ])
            updater = SQL("UPDATE {0} SET {1} FROM {2} WHERE {0}.{3} = {2}.{3}")
            self._execute(updater.format(
                Identifier(stable),
                scols,
                Identifier(tmp_table),
                Identifier(label_col),
            ))
            if reindex and inplace:
                # also restores constraints
                self.restore_indexes(columns[1:])
            elif not inplace:
                # restore all indexes since we're working with a fresh table; also restores constraints
                self.restore_indexes(suffix=suffix)
                # We also need to recreate the primary key
                self.restore_pkeys(suffix=suffix)
            if self._id_ordered and resort:
                ordered = self.resort(suffix=suffix)
            else:
                ordered = False
            if etable is not None:
                ecols = SQL(", ").join([
                    SQL("{0} = {1}.{0}").format(col, Identifier(tmp_table))
                    for col in ecols
                ])
                self._execute(updater.format(
                    Identifier(etable),
                    ecols,
                    Identifier(tmp_table),
                    Identifier(label_col),
                ))
            if restat and self.stats.saving:
                if not inplace:
                    for table in [self.stats.counts, self.stats.stats]:
                        if not self._table_exists(table + "_tmp"):
                            self._clone(table, table + "_tmp")
                self.stats.refresh_stats(suffix=suffix)
            if not inplace:
                swapped_tables = (
                    [self.search_table]
                    if etable is None
                    else [self.search_table, self.extra_table]
                )
                self._swap_in_tmp(swapped_tables, commit=commit)
                if ordered:
                    self._set_ordered()
            # Delete the temporary table used to load the data
            drop_tmp()
            if log_change:
                self.log_db_change("file_update")
            print("Updated %s in %.3f secs" % (self.search_table, time.time() - now))

    def delete(self, query, restat=True, commit=True):
        """
        Delete all rows matching the query.

        INPUT:

        - ``query`` -- a query dictionary; rows matching the query will be deleted
        - ``restat`` -- whether to recreate statistics afterward
        """
        self._check_locks("delete")
        with DelayCommit(self, commit, silence=True):
            qstr, values = self._parse_dict(query)
            if qstr is None:
                qstr = SQL("")
            else:
                qstr = SQL(" WHERE {0}").format(qstr)
            deleter = SQL("DELETE FROM {0}{1}").format(Identifier(self.search_table), qstr)
            if self.extra_table is not None:
                deleter = SQL(
                    "WITH deleted_ids AS ({0} RETURNING id) DELETE FROM {1} WHERE id IN (SELECT id FROM deleted_ids)"
                ).format(deleter, Identifier(self.extra_table))
            cur = self._execute(deleter, values)
            #self._break_order()
            self._break_stats()
            nrows = cur.rowcount
            if self.stats.saving:
                self.stats.total -= nrows
                self.stats._record_count({}, self.stats.total)
                if restat:
                    self.stats.refresh_stats(total=False)
            self.log_db_change("delete", query=query, nrows=nrows)

    def update(self, query, changes, resort=True, restat=True, commit=True):
        """
        Update a table using Postgres' update command

        INPUT:

        - ``query`` -- a query dictionary.  Only rows matching the query will be updated
        - ``changes`` -- a dictionary.  The keys should be column names, the values should be constants.
        - ``resort`` -- whether to resort the table afterward
        - ``restat`` -- whether to recompute statistics afterward
        """
        for col in changes:
            if col in self.extra_cols:
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
            updater = updater.format(
                Identifier(self.search_table),
                SQL(", ").join(map(Identifier, changes)),
                SQL(", ").join(Placeholder() * len(changes)),
                qstr,
            )
            change_values = self._parse_values(changes)
            self._execute(updater, change_values + values)
            self._break_order()
            self._break_stats()
            if resort:
                self.resort()
            if restat and self.stats.saving:
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
        - ``commit`` -- whether to actually execute the upsert.

        The keys of both inputs must be columns in either the search or extras table.

        OUTPUT:

        - ``new_row`` -- whether a new row was inserted
        - ``row_id`` -- the id of the found/new row
        """
        self._check_locks("update")
        if not query or not data:
            raise ValueError("Both query and data must be nonempty")
        if "id" in data:
            raise ValueError("Cannot set id")
        for col in query:
            if col != "id" and col not in self.search_cols:
                raise ValueError("%s is not a column of %s" % (col, self.search_table))
        if self.extra_table is None:
            search_data = dict(data)
            for col in data:
                if col not in self.search_cols:
                    raise ValueError("%s is not a column of %s" % (col, self.search_table))
        else:
            search_data = {}
            extras_data = {}
            for col, val in data.items():
                if col in self.search_cols:
                    search_data[col] = val
                elif col in self.extra_cols:
                    extras_data[col] = val
                else:
                    raise ValueError("%s is not a column of %s" % (col, self.search_table))
        cases = [(self.search_table, search_data)]
        if self.extra_table is not None:
            cases.append((self.extra_table, extras_data))
        with DelayCommit(self, commit, silence=True):
            # We have to split this command into a SELECT and an INSERT statement
            # rather than using postgres' INSERT INTO ... ON CONFLICT statement
            # because we have to take different additional steps depending on whether
            # an insertion actually occurred
            qstr, values = self._parse_dict(query)
            selecter = SQL("SELECT {0} FROM {1} WHERE {2} LIMIT 2").format(
                Identifier("id"), Identifier(self.search_table), qstr
            )
            cur = self._execute(selecter, values)
            val = {"operation": None}
            if cur.rowcount > 1:
                raise ValueError("Query %s does not specify a unique row" % (query))
            elif cur.rowcount == 1:  # update
                new_row = False
                row_id = cur.fetchone()[0]
                for table, dat in cases:
                    # we are not updating any column in the extras table
                    if len(dat) == 0:
                        continue
                    # the syntax for updating only one columns differs from multiple columns
                    elif len(dat) == 1:
                        updater = SQL("UPDATE {0} SET {1} = {2} WHERE {3}")
                    else:
                        updater = SQL("UPDATE {0} SET ({1}) = ({2}) WHERE {3}")
                    updater = updater.format(
                        Identifier(table),
                        SQL(", ").join(map(Identifier, list(dat))),
                        SQL(", ").join(Placeholder() * len(dat)),
                        SQL("id = %s"),
                    )
                    dvalues = self._parse_values(dat)
                    dvalues.append(row_id)
                    val["operation"] = "UPDATE"
                    val["record"] = self._execute(updater, dvalues)
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
                        SQL(", ").join(map(Identifier, list(dat))),
                        SQL(", ").join(Placeholder() * len(dat)),
                    )
                    self._execute(inserter, self._parse_values(dat))
                self._break_order()
                if self.stats.saving:
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
          All dictionaries must have the same set of keys.
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- boolean (default False). Whether to drop the indexes
          before insertion and restore afterward.  Note that if there is an exception during insertion
          the indexes will need to be restored manually using ``restore_indexes``.
        - ``restat`` -- whether to refresh statistics after insertion

        If the search table has an id, the dictionaries will be updated with the ids of the inserted records,
        though note that those ids will change if the ids are resorted.
        """
        self._check_locks("insert")
        if not data:
            raise ValueError("No data provided")
        if self.extra_table is not None:
            search_cols = [col for col in self.search_cols if col in data[0]]
            extra_cols = [col for col in self.extra_cols if col in data[0]]
            all_cols = set(search_cols + extra_cols)
            if len(all_cols) != len(data[0]):
                raise ValueError(f"Input has invalid columns: {', '.join(x for x in data[0] if x not in all_cols)}")
            if not all(set(D) == all_cols for D in data):
                raise ValueError("All dictionaries must have the same set of keys")
            search_data = [{col: D[col] for col in search_cols} for D in data]
            extra_data = [{col: D[col] for col in extra_cols} for D in data]
            search_cols = set(search_cols)
            extra_cols = set(extra_cols)
        else:
            # we don't want to alter the input
            search_data = data[:]
            search_cols = set(data[0])
        with DelayCommit(self, commit):
            jsonb_cols = [col for col, typ in self.col_type.items() if typ == "jsonb"]
            for i, SD in enumerate(search_data):
                if set(SD) != search_cols:
                    raise ValueError("All dictionaries must have the same set of keys")
                SD["id"] = self.max_id() + i + 1
                for col in jsonb_cols:
                    if col in SD:
                        SD[col] = Json(SD[col])
            cases = [(self.search_table, search_data)]
            if self.extra_table is not None:
                for i, ED in enumerate(extra_data):
                    if set(ED) != extra_cols:
                        raise ValueError("All dictionaries must have the same set of keys")
                    ED["id"] = self.max_id() + i + 1
                    for col in jsonb_cols:
                        if col in ED:
                            ED[col] = Json(ED[col])
                cases.append((self.extra_table, extra_data))
            now = time.time()
            if reindex:
                self.drop_pkeys()
                self.drop_indexes()
            for table, L in cases:
                template = SQL("({0})").format(SQL(", ").join(map(Placeholder, L[0])))
                inserter = SQL("INSERT INTO {0} ({1}) VALUES %s")
                inserter = inserter.format(Identifier(table), SQL(", ").join(map(Identifier, L[0])))
                self._execute(inserter, L, values_list=True, template=template)
            print(
                "Inserted %s records into %s in %.3f secs"
                % (len(search_data), self.search_table, time.time() - now)
            )
            self._break_order()
            self._break_stats()
            if resort:
                self.resort()
            if reindex:
                self.restore_pkeys()
                self.restore_indexes()
            if self.stats.saving:
                self.stats.total += len(search_data)
                self.stats._record_count({}, self.stats.total)
                if restat:
                    self.stats.refresh_stats(total=False)
            self.log_db_change("insert_many", nrows=len(search_data))


    def resort(self, suffix="", sort=None):
        """
        Restores the sort order on the id column.
        The id sequence might have gaps after resorting.
        See: https://www.postgresql.org/docs/current/functions-sequence.html

        INPUT:

        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the command.
        - ``sort`` -- -- a list, either of strings (which are interpreted as column names
            in the ascending direction) or of pairs (column name, 1 or -1).
            If None, will use ``self._sort_orig``.
        """

        print("resorting disabled")
        # resorting without a reload makes replication stall
        # and doesn't store data correctly on disk
        # Given that our tables are readonly, we should just dump sorted and reload
        return None
        search_table = Identifier(self.search_table + suffix)
        if self.extra_table:
            extra_table = Identifier(self.extra_table + suffix)
        else:
            extra_table = None

        tmp_table = Identifier(self.search_table + suffix + "_sorter")
        tmp_seq = Identifier(self.search_table + suffix + "_sorter" + '_newid_seq')
        sort_order = self._sort if sort is None else self._sort_str(sort)
        if sort_order is None:
            print("resort failed, no sort order given")
            return False
        self._check_locks(suffix=suffix)
        with DelayCommit(self, silence=True):
            if (self._id_ordered and self._out_of_order) or suffix:
                now = time.time()
                # we will use a temporary table to avoid ACCESS EXCLUSIVE lock
                self._execute(SQL(
                    "CREATE TEMP SEQUENCE {0} MINVALUE 0 START 0 CACHE 10000"
                ).format(tmp_seq))

                self._execute(SQL(
                    "CREATE TEMP TABLE {0} "
                    "(oldid bigint, newid bigint NOT NULL DEFAULT nextval('{1}')) "
                    "ON COMMIT DROP"
                ).format(tmp_table, tmp_seq))

                self._execute(SQL(
                    "ALTER SEQUENCE {0} OWNED BY {1}.newid"
                ).format(tmp_seq, tmp_table))

                self._execute(SQL(
                    "INSERT INTO {0} "
                    "SELECT id as oldid FROM {1} ORDER BY {2}"

                ).format(tmp_table, search_table, sort_order))
                self.drop_pkeys(suffix=suffix)
                for table in [search_table, extra_table]:
                    if table is not None:
                        self._execute(SQL(
                            "UPDATE {0} SET id = {1}.newid "
                            "FROM {1} WHERE {0}.id = {1}.oldid"
                        ).format(table, tmp_table))
                self.restore_pkeys(suffix=suffix)
                if not suffix:
                    self._set_ordered()
                print("Resorted %s in %.3f secs" % (self.search_table, time.time() - now))
            elif self._id_ordered and not self._out_of_order:
                print(f"Table {self.search_table} already sorted")
            else:  # not self._id_ordered
                print("Data does not have an id column to be sorted")
        return True

    def _set_ordered(self):
        """
        Marks this table as sorted in meta_tables
        """
        with DelayCommit(self, silence=True):
            updater = SQL("UPDATE meta_tables SET (id_ordered, out_of_order) = (%s, %s) WHERE name = %s")
            self._execute(updater, [True, False, self.search_table])
            self._id_ordered = True
            self._out_of_order = False

    def _write_header_lines(self, F, cols, sep=u"|", include_id=True):
        """
        Writes the header lines to a file
        (row of column names, row of column types, blank line).

        INPUT:

        - ``F`` -- a writable open file handle, at the beginning of the file.
        - ``cols`` -- a list of columns to write (either self.search_cols or self.extra_cols)
        - ``sep`` -- a string giving the column separator.  You should not use comma.
        """
        if include_id and cols and cols[0] != "id":
            cols = ["id"] + cols
        types = [self.col_type[col] for col in cols]
        F.write("%s\n%s\n\n" % (sep.join(cols), sep.join(types)))

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
            self._swap(tables, "", "_old" + str(backup_number))
            self._swap(tables, "_tmp", "")
            for table in tables:
                self._db.grant_select(table)
                if table.endswith("_counts") or table.endswith("_stats"):
                    self._db.grant_insert(table)
        print(
            "Swapped temporary tables for %s into place in %s secs\nNew backup at %s"
            % (
                self.search_table,
                time.time() - now,
                "{0}_old{1}".format(self.search_table, backup_number),
            )
        )
        if backup_number > 1:  # There are multiple backup tables
            print((
                "WARNING: there are now {1} backup tables for {0}\n"
                "You should probably run `db.{0}.cleanup_from_reload()` "
                "to save disc space"
            ).format(self.search_table, backup_number))

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

    def reload(
        self,
        searchfile,
        extrafile=None,
        countsfile=None,
        statsfile=None,
        indexesfile=None,
        constraintsfile=None,
        metafile=None,
        resort=None,
        reindex=True,
        restat=None,
        final_swap=True,
        silence_meta=False,
        adjust_schema=False,
        commit=True,
        log_change=True,
        **kwds
    ):
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
        - ``silence_meta`` -- suppress the warning message when using a metafile
        - ``adjust_schema`` -- If True, it will create the new tables using the
            header columns, otherwise expects the schema specified by the files
            to match the current one
        - ``log_change`` -- whether to log the reload to the log table
        - ``kwds`` -- passed on to psycopg2's ``copy_from``.  Cannot include "columns".

        .. NOTE:

            If the search and extra files contain ids, they should be contiguous,
            starting at 1.
        """
        sep = kwds.get("sep", u"|")
        suffix = "_tmp"
        if restat is None:
            restat = countsfile is None or statsfile is None
        self._check_file_input(searchfile, extrafile, kwds)
        print("Reloading %s..." % (self.search_table))
        now_overall = time.time()

        tables = []
        counts = {}
        tabledata = [
            (self.search_table, self.search_cols, True, searchfile),
            (self.extra_table, self.extra_cols, True, extrafile),
        ]
        if self.stats.saving:
            tabledata.extend([
                (self.stats.counts, _counts_cols, False, countsfile),
                (self.stats.stats, _stats_cols, False, statsfile),
            ])
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
                    cols = self._create_table_from_header(filename, tmp_table, sep)
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
                print(
                    "\tLoaded data into %s in %.3f secs from %s"
                    % (table, time.time() - now, filename)
                )

            if (extrafile is not None and counts[self.search_table] != counts[self.extra_table]):
                self.conn.rollback()
                raise RuntimeError("Different number of rows in searchfile and extrafile")

            self.restore_pkeys(suffix=suffix)

            # update the indexes
            # these are needed before reindexing
            if indexesfile is not None:
                # we do the swap at the end
                self.reload_indexes(indexesfile, sep=sep)
            if constraintsfile is not None:
                self.reload_constraints(constraintsfile, sep=sep)
            if reindex:
                # Also restores constraints
                self.restore_indexes(suffix=suffix)


            if resort:
                if metafile:
                    # read the metafile
                    from .base import _meta_cols_types_jsonb_idx
                    # using code from _reload_meta
                    meta_name = 'meta_tables'
                    meta_cols, _, jsonb_idx = _meta_cols_types_jsonb_idx(meta_name)
                    # the column which will match search_table
                    table_name = _meta_table_name(meta_name)
                    table_name_idx = meta_cols.index(table_name)
                    with open(metafile, "r") as F:
                        lines = list(csv.reader(F, delimiter=str(sep)))
                        if len(lines) != 1:
                            raise RuntimeError(
                                "%s has more than one line" % (metafile,)
                            )
                        line = lines[0]
                        if line[table_name_idx] != self.search_table:
                            raise RuntimeError(
                                f"column {table_name_idx} (= {line[table_name_idx]}) "
                                f"in the file {metafile} doesn't match "
                                f"the search table name {self.search_table}"
                            )
                        for col in ["id_ordered", "out_of_order"]:
                            idx = jsonb_idx[col]
                            if line[idx] not in ['t', 'f']:
                                raise RuntimeError(
                                    f"columns {idx} (= {line[idx]}) "
                                    f"in the file {metafile} is different from 't' or 'f'"
                                )
                        resort = line["id_ordered"] == 't' and line["out_of_order"] == 'f'
                else:
                    if not self._id_ordered: # this table doesn't need to be sorted
                        resort = False
                # tracks the success of resort
                ordered = self.resort(suffix=suffix)
            else:
                ordered = False


            if restat and self.stats.saving:
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
                self.reload_final_swap(tables=tables,
                                       metafile=metafile,
                                       ordered=ordered,
                                       commit=False)
            elif metafile is not None and not silence_meta:
                print(
                    "Warning: since the final swap was not requested, "
                    "we have not updated meta_tables"
                )
                print(
                    "when performing the final swap with reload_final_swap, "
                    "pass the metafile as an argument to update the meta_tables"
                )

            if log_change:
                self.log_db_change(
                    "reload",
                    counts=(countsfile is not None),
                    stats=(statsfile is not None),
                )
            print(
                "Reloaded %s in %.3f secs"
                % (self.search_table, time.time() - now_overall)
            )

    def reload_final_swap(self, tables=None, metafile=None, ordered=False, sep="|", commit=True):
        """
        Renames the _tmp versions of `tables` to the live versions.
        and updates the corresponding meta_tables row if `metafile` is provided

        INPUT:

        - ``tables`` -- list of strings (optional), of the tables to renamed. If None is provided, renames all the tables ending in `_tmp`
        - ``metafile`` -- a string (optional), giving a file containing the meta information for the table.
        - ``sep`` -- a character (default ``|``) to separate columns
        """
        with DelayCommit(self, commit, silence=True):
            if tables is None:
                tables = []
                for suffix in ["", "_extras", "_stats", "_counts"]:
                    tablename = "{0}{1}_tmp".format(self.search_table, suffix)
                    if self._table_exists(tablename):
                        tables.append(tablename)

            self._swap_in_tmp(tables, commit=False)
            if metafile is not None:
                self.reload_meta(metafile, sep=sep)
            if ordered:
                self._set_ordered()

        # Reinitialize object
        tabledata = self._execute(
            SQL(
                "SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, "
                "has_extras, stats_valid, total, include_nones "
                "FROM meta_tables WHERE name = %s"
            ),
            [self.search_table],
        ).fetchone()
        table = self._db._search_table_class_(self._db, *tabledata)
        self._db.__dict__[self.search_table] = table

    def drop_tmp(self):
        """
        Drop the temporary tables used in reloading.

        See the method ``cleanup_from_reload`` if you also want to drop
        the old backup tables.
        """
        with DelayCommit(self, silence=True):
            for suffix in ["", "_extras", "_stats", "_counts"]:
                tablename = "{0}{1}_tmp".format(self.search_table, suffix)
                if self._table_exists(tablename):
                    self._execute(SQL("DROP TABLE {0}").format(Identifier(tablename)))
                    print("Dropped {0}".format(tablename))

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
        if self._table_exists(self.search_table + "_tmp"):
            print(
                "Reload did not successfully complete. "
                "You must first call drop_tmp to delete the temporary tables created."
            )
            return
        if backup_number is None:
            backup_number = self._next_backup_number() - 1
            if backup_number == 0:
                raise ValueError("No old tables available to revert from.")
        elif not self._table_exists("%s_old%s" % (self.search_table, backup_number)):
            raise ValueError("Backup %s does not exist" % backup_number)
        with DelayCommit(self, commit, silence=True):
            old = "_old" + str(backup_number)
            tables = []
            for suffix in ["", "_extras", "_stats", "_counts"]:
                tablename = "{0}{1}".format(self.search_table, suffix)
                if self._table_exists(tablename + old):
                    tables.append(tablename)
            self._swap(tables, "", "_tmp")
            self._swap(tables, old, "")
            self._swap(tables, "_tmp", old)
            self.log_db_change("reload_revert")
        print(
            "Swapped backup %s with %s"
            % (self.search_table, "{0}_old{1}".format(self.search_table, backup_number))
        )

        # OLD VERSION that did something else
        # with DelayCommit(self, commit, silence=True):
        #    # drops the `_tmp` tables
        #    self.cleanup_from_reload(old = False)
        #    # reverts `meta_indexes` to previous state
        #    self.revert_indexes()
        #    print "Reverted %s to its previous state" % (self.search_table,)

    def cleanup_from_reload(self, keep_old=0):
        """
        Drop the ``_tmp`` and ``_old*`` tables that are created during ``reload``.

        Note that doing so will prevent ``reload_revert`` from working.

        INPUT:

        - ``keep_old`` -- the number of old tables to keep (they will be renamed so that they start at 1)
        """
        to_remove = []
        to_swap = []
        for suffix in ["", "_extras", "_stats", "_counts"]:
            head = self.search_table + suffix
            tablename = head + "_tmp"
            if self._table_exists(tablename):
                to_remove.append(tablename)
            backup_number = 1
            tails = []
            while True:
                tail = "_old{0}".format(backup_number)
                tablename = head + tail
                if self._table_exists(tablename):
                    tails.append(tail)
                else:
                    break
                backup_number += 1
            if keep_old > 0:
                for new_number, tail in enumerate(tails[-keep_old:], 1):
                    newtail = "_old{0}".format(new_number)
                    if newtail != tail:  # we might be keeping everything
                        to_swap.append((head, tail, newtail))
                tails = tails[:-keep_old]
            to_remove.extend([head + tail for tail in tails])
        with DelayCommit(self, silence=True):
            for table in to_remove:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(table)))
                print("Dropped {0}".format(table))
            for head, cur_tail, new_tail in to_swap:
                self._swap([head], cur_tail, new_tail)
                print("Swapped {0} to {1}".format(head + cur_tail, head + new_tail))

    def max_id(self, table=None):
        """
        The largest id occurring in the given table.  Used in the random method.
        """
        if table is None:
            table = self.search_table
        res = self._execute(SQL("SELECT MAX(id) FROM {}".format(table))).fetchone()[0]
        if res is None:
            res = -1
        return res

    # A temporary hack for RANDOM FIXME
    def min_id(self, table=None):
        """
        The smallest id occurring in the given table.  Used in the random method.
        """
        if table is None:
            table = self.search_table
        res = self._execute(SQL("SELECT MIN(id) FROM {}".format(table))).fetchone()[0]
        if res is None:
            res = 0
        return res

    def copy_from(
        self,
        searchfile,
        extrafile=None,
        resort=True,
        reindex=False,
        restat=True,
        commit=True,
        **kwds
    ):
        """
        Efficiently copy data from files into this table.

        INPUT:

        - ``searchfile`` -- a string, the file with data for the search table
        - ``extrafile`` -- a string, the file with data for the extra table.
            If there is an extra table, this argument is required.
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- whether to drop the indexes before importing data and rebuild them afterward.
            If the number of rows is a substantial fraction of the size of the table, this will be faster.
        - ``restat`` -- whether to recreate statistics after reloading.
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
            search_addid, search_count = self._copy_from(
                searchfile, self.search_table, self.search_cols, True, kwds
            )
            if extrafile is not None:
                extra_addid, extra_count = self._copy_from(
                    extrafile, self.extra_table, self.extra_cols, True, kwds
                )
                if search_count != extra_count:
                    self.conn.rollback()
                    raise ValueError("Different number of rows in searchfile and extrafile")
                if search_addid != extra_addid:
                    self.conn.rollback()
                    raise ValueError("Mismatch on search and extra containing id")
            print("Loaded data into %s in %.3f secs" % (self.search_table, time.time() - now))
            self._break_order()
            if self._id_ordered and resort:
                self.resort()
            if reindex:
                self.restore_indexes()
            self._break_stats()
            if self.stats.saving:
                if restat:
                    self.stats.refresh_stats(total=False)
                self.stats.total += search_count
                self.stats._record_count({}, self.stats.total)
            self.log_db_change("copy_from", nrows=search_count)

    def copy_to(
        self,
        searchfile,
        extrafile=None,
        countsfile=None,
        statsfile=None,
        indexesfile=None,
        constraintsfile=None,
        metafile=None,
        commit=True,
        columns=None,
        query=None,
        include_id=True,
        **kwds
    ):
        """
        Efficiently copy data from the database to a file.

        The result will have one line per row of the table, separated by | characters and in order
        given by self.search_cols and self.extra_cols.

        INPUT:

        - ``searchfile`` -- a string, the filename to write data into for the search table
        - ``extrafile`` -- a string,the filename to write data into for the extra table.
            If there is an extra table, this argument is required.
        - ``countsfile`` -- a string (optional), the filename to write the data into for the counts table.
        - ``statsfile`` -- a string (optional), the filename to write the data into for the stats table.
        - ``indexesfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_indexes table.
        - ``constraintsfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_constraints table.
        - ``metafile`` -- a string (optional), the filename to write the data into for the corresponding row of the meta_tables table.
        - ``columns`` -- a list of column names to export
        - ``query`` -- a query dictionary
        - ``include_id`` -- whether to include the id column in the output file
        - ``kwds`` -- passed on to psycopg2's ``copy_to``.  Cannot include "columns".
        """
        self._check_file_input(searchfile, extrafile, kwds)
        sep = kwds.pop("sep", u"|")

        search_cols = [col for col in self.search_cols if columns is None or col in columns]
        extra_cols = [col for col in self.extra_cols if columns is None or col in columns]
        if columns is not None and len(columns) != len(search_cols) + len(extra_cols):
            raise ValueError("Invalid columns %s" % (", ".join([col for col in columns if col not in search_cols and col not in extra_cols])))
        tabledata = [
            # tablename, cols, addid, write_header, filename
            (self.search_table, search_cols, include_id, True, searchfile),
            (self.extra_table, extra_cols, include_id, True, extrafile),
        ]
        if self.stats.saving:
            tabledata.extend([
                (self.stats.counts, _counts_cols, False, False, countsfile),
                (self.stats.stats, _stats_cols, False, False, statsfile),
            ])

        metadata = [
            ("meta_indexes", "table_name", _meta_indexes_cols, indexesfile),
            ("meta_constraints", "table_name", _meta_constraints_cols, constraintsfile),
            ("meta_tables", "name", _meta_tables_cols, metafile),
        ]
        print("Exporting %s..." % (self.search_table))
        now_overall = time.time()
        with DelayCommit(self, commit):
            for table, cols, addid, write_header, filename in tabledata:
                if filename is None:
                    continue
                now = time.time()
                if addid:
                    cols = ["id"] + cols
                if psycopg2_version < (2, 9, 0):
                    cols_wquotes = ['"' + col + '"' for col in cols]
                else:
                    cols_wquotes = cols
                cur = self._db.cursor()
                with open(filename, "w") as F:
                    try:
                        if write_header:
                            self._write_header_lines(F, cols, include_id=include_id, sep=sep)
                        if query is None:
                            cur.copy_to(F, table, columns=cols_wquotes, sep=sep, **kwds)
                        else:
                            if sep == "\t":
                                sep_clause = SQL("")
                            else:
                                sep_clause = SQL(" (DELIMITER {0})").format(Literal(sep))
                            qstr, values = self._build_query(query, sort=[])
                            scols = SQL(", ").join(map(IdentifierWrapper, cols))
                            selecter = SQL("SELECT {0} FROM {1}{2}").format(scols, IdentifierWrapper(table), qstr)
                            copyto = SQL("COPY ({0}) TO STDOUT{1}").format(selecter, sep_clause)
                            # copy_expert doesn't support values
                            cur.copy_expert(cur.mogrify(copyto, values), F, **kwds)
                    except Exception:
                        self.conn.rollback()
                        raise
                print(
                    "\tExported %s in %.3f secs to %s"
                    % (table, time.time() - now, filename)
                )

            for table, wherecol, cols, filename in metadata:
                if filename is None:
                    continue
                now = time.time()
                cols = SQL(", ").join(map(Identifier, cols))
                select = SQL("SELECT {0} FROM {1} WHERE {2} = {3}").format(
                    cols,
                    Identifier(table),
                    Identifier(wherecol),
                    Literal(self.search_table),
                )
                self._copy_to_select(select, filename, silent=True, sep=sep)
                print(
                    "\tExported data from %s in %.3f secs to %s"
                    % (table, time.time() - now, filename)
                )

            print(
                "Exported %s in %.3f secs"
                % (self.search_table, time.time() - now_overall)
            )

    ##################################################################
    # Updating the schema                                            #
    ##################################################################

    # Note that create_table and drop_table are methods on PostgresDatabase

    def set_sort(self, sort, id_ordered=True, resort=True, commit=True):
        """
        Change the default sort order for this table

        INPUT:

        - ``sort`` -- a list of columns or pairs (col, direction) where direction is 1 or -1.
        - ``id_ordered`` -- the value id_ordered to set when changing the sort to a non None value.
            If ``sort is None, then id_ordered will be set to False.
        - ``resort`` -- whether to resort the table ids when changing the sort to a non None value
            and if id_ordered=True
        """
        self._set_sort(sort)
        with DelayCommit(self, commit, silence=True):
            sort_json = Json(sort) if sort else None
            self._id_ordered = id_ordered if sort else False
            self._execute(SQL(
                "UPDATE meta_tables SET (sort, id_ordered) = (%s, %s) WHERE name = %s"),
                          [sort_json, self._id_ordered, self.search_table])
            self._break_order() # set out_order = False

            if sort:
                # add an index for the default sort
                sort_index = [x if isinstance(x, str) else x[0] for x in sort]
                if not any(index["columns"] == sort_index for index_name, index in self.list_indexes().items()):
                    self.create_index(sort_index)
                if self._id_ordered and resort:
                    self.resort()
            self.log_db_change("set_sort", sort=sort)

    def set_label(self, label_col=None):
        """
        Sets (or clears) the label column for this table.

        INPUT:

        - ``label_col`` -- a search column of this table, or ``None``.
          If ``None``, the current label column will be cleared without a replacement.
        """
        if not (label_col is None or label_col in self.search_cols):
            raise ValueError("%s is not a search column" % label_col)
        modifier = SQL("UPDATE meta_tables SET label_col = %s WHERE name = %s")
        self._execute(modifier, [label_col, self.search_table])
        self._label_col = label_col

    def get_label(self):
        """
        Returns the current label column as a string.
        """
        return self._label_col

    def description(self, table_description=None):
        """
        Return or set the description string for this table in meta_tables

        INPUT:

        - ``table_description`` -- if provided, set the description to this value.  If not, return the current description.
        """
        if table_description is None:
            selecter = SQL("SELECT table_description FROM meta_tables WHERE name = %s")
            desc = list(self._execute(selecter, [self.search_table]))
            if desc and desc[0]:
                return desc[0]
            else:
                return "(table description not yet updated on this server)"
        else:
            assert isinstance(table_description, str)
            modifier = SQL("UPDATE meta_tables SET table_description = %s WHERE name = %s")
            self._execute(modifier, [table_description, self.search_table])

    def column_description(self, col=None, description=None, drop=False):
        """
        Set the description for a column in meta_tables.

        INPUT:

        - ``col`` -- the name of the column.  If None, ``description`` should be a dictionary with keys equal to the column names.

        - ``description`` -- if provided, set the column description to this value.  If not, return the current description.

        - ``drop`` -- if ``True``, delete the column from the description dictionary in preparation for dropping the column.
        """
        allcols = self.search_cols + self.extra_cols
        # Get the current column description
        selecter = SQL("SELECT col_description FROM meta_tables WHERE name = %s")
        cur = self._execute(selecter, [self.search_table])
        current = cur.fetchone()[0]

        if not drop and description is None:
            # We want to allow the set of columns to be out of date temporarily, on prod for example
            if col is None:
                for col in allcols:
                    if col not in current:
                        current[col] = "(description not yet updated on this server)"
                return current
            return current.get(col, "(description not yet updated on this server)")
        else:
            if not (drop or col is None or col in allcols):
                raise ValueError("%s is not a column of this table" % col)
            if drop:
                if col is None:
                    raise ValueError("Must specify column name to drop")
                try:
                    del current[col]
                except KeyError:
                    # column was already not present for some reason
                    return
            elif col is None:
                assert isinstance(description, dict)
                for col in description:
                    if col not in allcols:
                        raise ValueError("%s is not a column of this table" % col)
                    assert isinstance(description[col], str)
                    current[col] = description[col]
            else:
                assert isinstance(description, str)
                current[col] = description
            modifier = SQL("UPDATE meta_tables SET col_description = %s WHERE name = %s")
            self._execute(modifier, [Json(current), self.search_table])

    def add_column(self, name, datatype, description=None, extra=False, label=False, force_description=False):
        """
        Adds a column to this table.

        INPUT:

        - ``name`` -- a string giving the column name.  Must not be a current column name.
        - ``datatype`` -- a valid Postgres data type (e.g. 'numeric' or 'text')
        - ``description`` -- a string giving the description of the column
        - ``extra`` -- whether this column should be added to the extras table.
          If no extras table has been created, you must call ``create_extra_table`` first.
        - ``label`` -- whether this column should be set as the label column for this table
          (used in the ``lookup`` method for example).
        """
        if name in self.search_cols:
            raise ValueError("%s already has column %s" % (self.search_table, name))
        if name in self.extra_cols:
            raise ValueError("%s already has column %s" % (self.extra_table, name))
        if label and extra:
            raise ValueError("label must be a search column")
        if force_description and description is None:
            raise ValueError("You must provide a description of this column")
        elif description is None:
            description = ""
        self._check_locks()
        self._check_col_datatype(datatype)
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
            modifier = SQL("ALTER TABLE {0} ADD COLUMN {1} %s" % datatype).format(
                Identifier(table), Identifier(name)
            )
            self._execute(modifier)
            if extra and name != "id":
                self.extra_cols.append(name)
            elif not extra and name != "id":
                self.search_cols.append(name)
            if label:
                self.set_label(name)
            self.column_description(name, description)
            self.log_db_change("add_column", name=name, datatype=datatype)

    def drop_column(self, name, commit=True, force=False):
        """
        Drop a column and any data stored in it.

        INPUT:

        - ``name`` -- the name of the column
        - ``commit`` -- whether to actually execute the change
        - ``force`` -- if False, will ask for confirmation
        """
        self._check_locks()

        if not force:
            ok = input("Are you sure you want to drop %s? (y/N) " % name)
            if not (ok and ok[0] in ["y", "Y"]):
                return
        if name in self._sort_keys:
            raise ValueError(
                "Sorting for %s depends on %s; change default sort order with set_sort() before dropping column"
                % (self.search_table, name)
            )
        with DelayCommit(self, commit, silence=True):
            self.column_description(name, drop=True)
            if name in self.search_cols:
                table = self.search_table
                counts_table = table + "_counts"
                stats_table = table + "_stats"
                jname = Json(name)
                deleter = SQL("DELETE FROM {0} WHERE table_name = %s AND columns @> %s")
                self._execute(deleter.format(Identifier("meta_indexes")), [table, jname])
                self._execute(deleter.format(Identifier("meta_constraints")), [table, jname])
                deleter = SQL("DELETE FROM {0} WHERE cols @> %s").format(Identifier(counts_table))
                self._execute(deleter, [jname])
                deleter = SQL(
                    "DELETE FROM {0} WHERE cols @> %s OR constraint_cols @> %s"
                ).format(Identifier(stats_table))
                self._execute(deleter, [jname, jname])
                self.search_cols.remove(name)
            elif name in self.extra_cols:
                table = self.extra_table
                self.extra_cols.remove(name)
            else:
                raise ValueError("%s is not a column of %s" % (name, self.search_table))
            modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(Identifier(table), Identifier(name))
            self._execute(modifier)
            self.col_type.pop(name, None)
            self.log_db_change("drop_column", name=name)
        print("Column %s dropped" % (name))

    def create_extra_table(self, columns, ordered=False, sep="|", commit=True):
        """
        Splits this search table into two, linked by an id column.

        INPUT:

        - ``columns`` -- columns that are currently in the search table
            that should be moved to the new extra table. Can be empty.
        - ``ordered`` -- whether the id column should be kept in sorted
            order based on the default sort order stored in meta_tables.
        - ``sep`` -- a character (default ``|``) to separate columns in
            the temp file used to move data
        """
        self._check_locks()
        if self.extra_table is not None:
            raise ValueError("Extra table already exists")
        with DelayCommit(self, commit, silence=True):
            if ordered and not self._id_ordered:
                updater = SQL("UPDATE meta_tables SET (id_ordered, out_of_order, has_extras) = (%s, %s, %s) WHERE name = %s")
                self._execute(updater, [True, True, True, self.search_table])
                self._id_ordered = True
                self._out_of_order = True
                self.resort()
            else:
                updater = SQL("UPDATE meta_tables SET (has_extras) = (%s) WHERE name = %s")
                self._execute(updater, [True,  self.search_table])
            self.extra_table = self.search_table + "_extras"
            col_type = [("id", "bigint")]
            cur = self._indexes_touching(columns)
            if cur.rowcount > 0:
                raise ValueError(
                    "Indexes (%s) depend on extra columns"
                    % (", ".join(rec[0] for rec in cur))
                )
            if columns:
                selecter = SQL(
                    "SELECT columns, constraint_name "
                    "FROM meta_constraints WHERE table_name = %s AND ({0})"
                ).format(SQL(" OR ").join(SQL("columns @> %s") * len(columns)))
                cur = self._execute(
                    selecter,
                    [self.search_table] + [Json(col) for col in columns],
                    silent=True,
                )
                for rec in cur:
                    if not all(col in columns for col in rec[0]):
                        raise ValueError(
                            "Constraint %s (columns %s) split between search and extra table"
                            % (rec[1], ", ".join(rec[0]))
                        )
            for col in columns:
                if col not in self.col_type:
                    raise ValueError("%s is not a column of %s" % (col, self.search_table))
                if col in self._sort_keys:
                    raise ValueError(
                        "Sorting for %s depends on %s; change default sort order "
                        "with set_sort() before moving column to extra table"
                        % (self.search_table, col)
                    )
                typ = self.col_type[col]
                self._check_col_datatype(typ)
                col_type.append((col, typ))
            self.extra_cols = []
            col_type_SQL = SQL(", ").join(
                SQL("{0} %s" % typ).format(Identifier(col)) for col, typ in col_type
            )
            creator = SQL("CREATE TABLE {0} ({1})").format(Identifier(self.extra_table), col_type_SQL)
            self._execute(creator)
            if columns:
                self.drop_constraints(columns)
                try:
                    try:
                        transfer_file = tempfile.NamedTemporaryFile("w", delete=False)
                        cur = self._db.cursor()
                        with transfer_file:
                            cur.copy_to(
                                transfer_file,
                                self.search_table,
                                columns=["id"] + columns,
                                sep=sep,
                            )
                        with open(transfer_file.name) as F:
                            cur.copy_from(F, self.extra_table, columns=["id"] + columns, sep=sep)
                    finally:
                        transfer_file.unlink(transfer_file.name)
                except Exception:
                    self.conn.rollback()
                    raise
                self.restore_constraints(columns)
                for col in columns:
                    modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(
                        Identifier(self.search_table), Identifier(col)
                    )
                    self._execute(modifier)
            else:
                sequencer = SQL("CREATE TEMPORARY SEQUENCE tmp_id")
                self._execute(sequencer)
                updater = SQL("UPDATE {0} SET id = nextval('tmp_id')").format(Identifier(self.extra_table))
                self._execute(updater)
            self.restore_pkeys()
            self.log_db_change("create_extra_table", columns=columns)

    def _move_column(self, column, src, target, commit):
        """
        This function moves a column between two tables, copying the data accordingly.

        The two tables must have corresponding id columns, so this is most useful for moving
        columns between search and extra tables.
        """
        self._check_locks()
        with DelayCommit(self, commit, silence=True):
            datatype = self.col_type[column]
            self._check_col_datatype(datatype)
            modifier = SQL("ALTER TABLE {0} ADD COLUMN {1} %s" % datatype).format(
                Identifier(target), Identifier(column)
            )
            self._execute(modifier)
            print("%s column created in %s; moving data" % (column, target))
            datamove = SQL(
                "UPDATE {0} SET {1} = {2}.{1} FROM {2} WHERE {0}.id = {2}.id"
            ).format(Identifier(target), Identifier(column), Identifier(src))
            self._execute(datamove)
            modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(Identifier(src), Identifier(column))
            self._execute(modifier)
            print("%s column successfully moved from %s to %s" % (column, src, target))
            self.log_db_change("move_column", name=column, dest=target)

    def move_column_to_extra(self, column, commit=True):
        """
        Move a column from a search table to an extra table.

        INPUT:

        - ``column`` -- the name of the column to move
        - ``commit`` -- whether to commit the change
        """
        if column not in self.search_cols:
            raise ValueError("%s not a search column" % (column))
        if self.extra_table is None:
            raise ValueError("Extras table does not exist.  Use create_extra_table")
        if column == self._label_col:
            raise ValueError("Cannot move the label column to extra")
        self._move_column(column, self.search_table, self.extra_table, commit)
        self.extra_cols.append(column)
        self.search_cols.remove(column)

    def move_column_to_search(self, column, commit=True):
        """
        Move a column from an extra table to a search table.

        INPUT:

        - ``column`` -- the name of the column to move
        - ``commit`` -- whether to commit the change
        """
        if column not in self.extra_cols:
            raise ValueError("%s not an extra column" % (column))
        self._move_column(column, self.extra_table, self.search_table, commit)
        self.search_cols.append(column)
        self.extra_cols.remove(column)

    def log_db_change(self, operation, **data):
        """
        Log changes to search tables.

        INPUT:

        - ``operation`` -- a string, explaining what operation was performed
        - ``**data`` -- any additional information to install in the logging table (will be stored as a json dictionary)
        """
        self._db.log_db_change(operation, tablename=self.search_table, **data)

    def set_importance(self, importance):
        """
        Production tables are marked as important so that they can't be accidentally dropped.

        Use this method to mark a table important or not important.
        """
        updater = SQL("UPDATE meta_tables SET important = %s WHERE name = %s")
        self._execute(updater, [importance, self.search_table])
