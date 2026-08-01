# -*- coding: utf-8 -*-
"""
The write and schema half of a table.

:class:`PostgresTable` manages a single search table: row-level writes
(``insert_many``, ``update``, ``upsert``, ``delete``), the bulk file-based
import and export that psycodict is built around (``copy_from``,
``copy_to``, ``reload`` and its staged ``_tmp``-table machinery), and the
table's schema -- columns, indexes, constraints and the corresponding
``meta_*`` bookkeeping with its versioned history.  The read interface
lives in the subclass :class:`~psycodict.searchtable.PostgresSearchTable`,
which is what ``db.<tablename>`` actually returns.
"""
import csv
import os
import tempfile
import time
import re
from bisect import bisect
from functools import partial

from psycopg.sql import SQL, Identifier, Placeholder, Literal

from .encoding import Json, check_copy_sep, copy_dumps
from .base import PostgresBase, _meta_table_name
from .utils import DelayCommit, IdentifierWrapper, LockError
from .base import (
    _meta_cols_types_jsonb_idx,
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
    "gin": ["jsonb_path_ops", "array_ops"],
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
    on which searches are performed.

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
    - ``stats_valid`` -- whether the statistics tables are currently up to date
    - ``total`` -- the total number of rows in the table; cached as a performance optimization
    - ``data_types`` -- a dictionary holding the data types of the columns; see the ``_column_types`` method for more details

    ATTRIBUTES:

    The following public attributes are available on instances of this class

    - ``search_table`` -- a string, the name of the associated postgres search table
    - ``search_cols`` -- a list of column names in the search table.  Does not include the id column.
    - ``col_type`` -- a dictionary with keys the column names and values the postgres type of that column.
    - ``stats`` -- the attached ``PostgresStatsTable`` instance

    The following private attributes are sometimes also useful

    - ``_label_col`` -- the column used by default in the ``lookup`` method
    - ``_sort_org`` -- either None or a list of columns or pairs ``(col, direction)``
    - ``_sort_keys`` -- a set of column names included in the sort order
    - ``_primary_sort`` -- either None, a column name or a pair ``(col, direction)``, the most significant column when sorting
    - ``_sort`` -- the psycopg.sql.Composable object containing the default sort clause
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
        stats_valid=True,
        total=None,
        include_nones=True,
        data_types=None,
    ):
        self.search_table = search_table
        self._label_col = label_col
        self._count_cutoff = count_cutoff
        self._id_ordered = id_ordered
        self._out_of_order = out_of_order
        self._stats_valid = stats_valid
        # None (a meta_tables row from before the column existed) means the
        # default, which is to include None values in search results
        self._include_nones = True if include_nones is None else include_nones
        PostgresBase.__init__(self, search_table, db)
        self.col_type = {}
        self._has_id = False
        self.search_cols, self.col_type, self._has_id = self._column_types(search_table, data_types=data_types)
        self._set_sort(sort)
        self.stats = self._stats_table_class_(self, total)

    def _set_sort(self, sort):
        """
        Initialize the sorting attributes from a list of columns or pairs (col, direction)
        """
        self._sort_orig = sort
        self._sort_keys = set()
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

    def _refresh(self, meta=None, data_types=None):
        """
        Update this object to match the current schema of the underlying table.

        The columns and their types, together with this table's metadata in
        ``meta_tables`` (sort order, label column, etc.), are read from the
        database when this object is created.  A long-running process (such as
        a website) does not see schema changes made by other processes, and
        once its snapshot is stale its queries can fail.  This method re-reads
        this table's row in ``meta_tables`` together with the current columns,
        updating the object in place.  It is normally invoked through
        ``db.refresh_tables()``, which refreshes every table at once; see its
        documentation for more details.

        INPUT:

        - ``meta`` -- (optional) this table's row in ``meta_tables``, as a tuple
          ``(label_col, sort, count_cutoff, id_ordered, out_of_order,
          stats_valid, total, include_nones)``.  If not provided, the row will
          be looked up from the database.
        - ``data_types`` -- (optional) a dictionary providing a list of column
          names and types for each table name, as in ``_column_types``.  If not
          provided, the columns will be looked up from the database.
        """
        if meta is None:
            cur = self._execute(
                SQL(
                    "SELECT label_col, sort, count_cutoff, id_ordered, out_of_order, "
                    "stats_valid, total, include_nones FROM meta_tables WHERE name = %s"
                ),
                [self.search_table],
            )
            if cur.rowcount == 0:
                raise ValueError("%s is not in meta_tables" % (self.search_table,))
            meta = cur.fetchone()
        (label_col, sort, count_cutoff, id_ordered,
         out_of_order, stats_valid, total, include_nones) = meta
        self._label_col = label_col
        self._count_cutoff = count_cutoff
        self._id_ordered = id_ordered
        self._out_of_order = out_of_order
        self._stats_valid = stats_valid
        # A legacy meta_tables row predating the include_nones column reads as
        # SQL NULL; treat it as True, matching the constructor, so that a later
        # refresh_tables() does not silently flip such a table back to the old
        # omit-Nones behavior.  (The coalescing in the constructor arrives with
        # PR #103; keeping the two in step is the point of doing it here too.)
        self._include_nones = True if include_nones is None else include_nones
        self.search_cols, self.col_type, self.has_id = self._column_types(self.search_table, data_types=data_types)
        self._set_sort(sort)
        self.stats._init_total(total)

    def __repr__(self):
        return "Interface to Postgres table %s" % (self.search_table)

    ##################################################################
    # Indexes and performance analysis                               #
    ##################################################################

    def analyze(self, query, projection=1, limit=1000, offset=0, sort=None, explain_only=False, join=None):
        """
        Prints an analysis of how a given query is being executed, for use in optimizing searches.

        INPUT:

        - ``query`` -- a query dictionary
        - ``projection`` -- outputs, as in the ``search`` method
        - ``limit`` -- a maximum on the number of rows to return
        - ``offset`` -- an offset starting point for results
        - ``sort`` -- a string or list specifying a sort order
        - ``explain_only`` -- whether to execute the query (if ``True`` then will only use Postgres' query planner rather than actually carrying out the query)
        - ``join`` -- a list of tuples describing other search tables to join
          to this one, as for ``search``; the query, projection and sort may
          then use qualified columns.  Slow joined searches log a replication
          command that includes this argument.

        EXAMPLES::

            >>> nf = db.test_fields
            >>> nf.analyze({'degree': 2}, limit=4)
            SELECT "class_group", "class_number", "degree", "disc_abs", "disc_sign", "label", "r2", "ramps" FROM "test_fields" WHERE "degree" = 2 ORDER BY "degree", "disc_abs", "label" LIMIT 4
            Limit  (cost=... rows=4... loops=1)
            ...
            Execution Time: ... ms
        """
        if join is not None:
            _, selecter, values = self._join_selecter(query, projection, join, limit=limit, offset=offset, sort=sort)
        else:
            search_cols = self._parse_projection(projection)
            cols = SQL(", ").join(self._column_composable(c) for c in search_cols)
            if limit is None:
                qstr, values = self._build_query(query, sort=sort)
            else:
                qstr, values = self._build_query(query, limit, offset, sort)
            selecter = SQL("SELECT {0} FROM {1}{2}").format(cols, Identifier(self.search_table), qstr)
        if explain_only:
            analyzer = SQL("EXPLAIN {0}").format(selecter)
        else:
            analyzer = SQL("EXPLAIN ANALYZE {0}").format(selecter)
        print(self._mogrify(selecter, values))
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
        - not necessarily a superset of all the built indexes

        For the current built indexes on the search table, see ``_list_built_indexes``
        """
        if self._db._meta_format >= 1:
            selecter = SQL("SELECT index_name, type, columns, modifiers, whereclause FROM meta_indexes WHERE table_name = %s")
        else:
            # A format-0 database has no whereclause column (and so no
            # partial indexes); selecting NULL keeps the row shape uniform.
            selecter = SQL("SELECT index_name, type, columns, modifiers, NULL FROM meta_indexes WHERE table_name = %s")
        cur = self._execute(selecter, [self.search_table], silent=True)
        output = {}
        for name, typ, columns, modifiers, whereclause in cur:
            output[name] = {"type": typ, "columns": columns, "modifiers": modifiers}
            # Only partial indexes carry a predicate; including the key
            # unconditionally would change every caller's output and let a plain
            # index be recreated with where=None, so add it only when present.
            # As a bonus, create_index(**entry) then rebuilds a partial index
            # correctly (used by create_table_like).
            if whereclause is not None:
                output[name]["where"] = whereclause
            if verbose:
                colspec = [" ".join([col] + mods) for col, mods in zip(columns, modifiers)]
                line = "{0} ({1}): {2}".format(name, typ, ", ".join(colspec))
                if whereclause is not None:
                    line += " WHERE {0}".format(whereclause)
                print(line)
        if not verbose:
            return output

    def _get_tablespace(self):
        """
        Determine the tablespace hosting this table (which is then used for indexes and constraints)
        """
        cur = self._execute(SQL("SELECT tablespace FROM pg_tables WHERE tablename=%s"), [self.search_table])
        return cur.fetchone()[0]

    def _create_index_statement(self, name, table, type, columns, modifiers, storage_params, whereclause=None):
        """
        Utility function for making the create index SQL statement.
        """
        # We whitelisted the type, modifiers and storage parameters
        # when creating the index so the following is safe from SQL injection
        if storage_params:
            # The keys of storage_params have been whitelisted; the values are
            # inlined as literals because DDL statements cannot take bound
            # parameters under psycopg3's server-side binding.
            storage_params = SQL(" WITH ({0})").format(
                SQL(", ").join(
                    SQL("{0} = {{0}}".format(param)).format(Literal(val))
                    for param, val in storage_params.items()
                )
            )
        else:
            storage_params = SQL("")
        tablespace = self._tablespace_clause()
        # A partial index restricts the rows it covers to those matching a
        # predicate.  The clause is raw SQL supplied by an administrator (see
        # create_index), so it is inlined directly, like the whitelisted type
        # and modifiers above; it must come last, after WITH and TABLESPACE.
        if whereclause:
            where = SQL(" WHERE " + whereclause)
        else:
            where = SQL("")
        modifiers = [" " + " ".join(mods) if mods else "" for mods in modifiers]
        # The inner % operator is on strings prior to being wrapped by SQL: modifiers have been whitelisted.
        columns = SQL(", ").join(
            SQL("{0}%s" % mods).format(Identifier(col))
            for col, mods in zip(columns, modifiers)
        )
        # The inner % operator is on strings prior to being wrapped by SQL: type has been whitelisted.
        creator = SQL("CREATE INDEX {0} ON {1} USING %s ({2}){3}{4}{5}" % (type))
        return creator.format(Identifier(name), Identifier(table), columns, storage_params, tablespace, where)

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
                self._execute(creator)
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

    def create_index(self, columns, type="btree", modifiers=None, name=None, storage_params=None, where=None):
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
        - ``where`` -- if given, a string with the predicate of a partial index, emitted
            verbatim as the ``WHERE`` clause of ``CREATE INDEX`` (e.g. ``"disc > 0"``).
            Unlike a search query, this is **raw SQL**: it is not parsed, escaped or
            translated, and is inlined into the DDL like ``storage_params``.  It is
            administrative input (you are already trusted to run DDL), never website
            input, and must be trusted accordingly.  The predicate is recorded in
            meta_indexes so the partial index survives a drop/restore or reload.  A
            partial index needs a name distinct from any plain index on the same
            columns: pass an explicit ``name``, or rely on the automatic numeric
            suffix appended below when the generated name collides with an existing
            relation.
        """
        now = time.time()
        if type not in _operator_classes:
            raise ValueError("Unrecognized index type")
        if where is not None and self._db._meta_format < 1:
            raise ValueError(
                "Partial indexes need metadata format 1, but this database "
                "uses format %s: migrate it with db.upgrade_metadata() (or "
                "reconnect with PostgresDatabase(upgrade=True)); see "
                "MetadataFormats.md." % self._db._meta_format
            )
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
            if len(name) >= 64:
                name = name[:63]
            if self._relation_exists(name):
                disamb = 0
                while self._relation_exists(name + str(disamb)):
                    disamb += 1
                name += str(disamb)

        with DelayCommit(self, silence=True):
            self._check_index_name(name, "Index")
            creator = self._create_index_statement(
                name, self.search_table, type, columns, modifiers, storage_params, where
            )
            self._execute(creator)
            values = [
                name,
                self.search_table,
                type,
                Json(columns),
                Json(modifiers),
                storage_params,
            ]
            if self._db._meta_format >= 1:
                inserter = SQL("INSERT INTO meta_indexes (index_name, table_name, type, columns, modifiers, storage_params, whereclause) VALUES (%s, %s, %s, %s, %s, %s, %s)")
                values.append(where)
            else:
                # A format-0 database has no whereclause column; ``where`` is
                # necessarily None here (checked above).
                inserter = SQL("INSERT INTO meta_indexes (index_name, table_name, type, columns, modifiers, storage_params) VALUES (%s, %s, %s, %s, %s, %s)")
            self._execute(inserter, values)
        print("Index %s created in %.3f secs" % (name, time.time() - now))

    def drop_index(self, name, suffix="", permanent=True):
        """
        Drop a specified index.

        INPUT:

        - ``name`` -- the name of the index
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the DROP INDEX statement.
        - ``permanent`` -- whether to remove the index from the meta_indexes table
        """
        now = time.time()
        # We don't want to wrap these in a DelayCommit since we want them to succeed independently
        if permanent:
            deleter = SQL("DELETE FROM meta_indexes WHERE table_name = %s AND index_name = %s")
            self._execute(deleter, [self.search_table, name])
        dropper = SQL("DROP INDEX IF EXISTS {0}").format(Identifier(name + suffix))
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
            if self._db._meta_format >= 1:
                selecter = SQL(
                    "SELECT type, columns, modifiers, storage_params, whereclause FROM meta_indexes "
                    "WHERE table_name = %s AND index_name = %s"
                )
            else:
                # A format-0 database has no whereclause column (and so no
                # partial indexes); selecting NULL keeps the row shape uniform.
                selecter = SQL(
                    "SELECT type, columns, modifiers, storage_params, NULL FROM meta_indexes "
                    "WHERE table_name = %s AND index_name = %s"
                )
            cur = self._execute(selecter, [self.search_table, name])
            if cur.rowcount > 1:
                raise RuntimeError("Duplicated rows in meta_indexes")
            elif cur.rowcount == 0:
                raise ValueError("Index %s does not exist in meta_indexes" % (name,))
            type, columns, modifiers, storage_params, whereclause = cur.fetchone()
            creator = self._create_index_statement(
                name + suffix,
                self.search_table + suffix,
                type,
                columns,
                modifiers,
                storage_params,
                whereclause,
            )
            # this avoids clashes with deprecated indexes/constraints
            self._rename_if_exists(name, suffix)
            self._execute(creator)
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

    def drop_indexes(self, columns=[], suffix="", permanent=True):
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
        with DelayCommit(self):
            for res in self._indexes_touching(columns):
                self.drop_index(res[0], suffix, permanent=permanent)
            for res in self._constraints_touching(columns):
                # These are constraints, so dropping them as indexes fails:
                # Postgres refuses to drop an index that implements a
                # constraint.  Compare restore_indexes, which restores the
                # two kinds separately.
                self.drop_constraint(res[0], suffix, permanent=permanent)

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

    def _pkey_common(self, command, suffix, action):
        """
        Common code for ``drop_pkeys`` and ``restore_pkeys``.

        INPUT:

        - ``command`` -- an sql.Composable object giving the command to execute.
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the command.
        - ``action`` -- either "Dropped" or "Built", for printing.
        """
        now = time.time()
        with DelayCommit(self, silence=True):
            # Note that the primary keys don't follow the same convention as the other
            # indexes, since they end in _pkey rather than the suffix.
            self._execute(command.format(
                Identifier(self.search_table + suffix),
                Identifier(self.search_table + suffix + "_pkey"),
            ))
        print("%s primary key on %s in %.3f secs" % (action, self.search_table, time.time() - now))

    def drop_pkeys(self, suffix=""):
        """
        Drop the primary key on the id columns.

        INPUT:

        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the ALTER TABLE statements.
        """
        command = SQL("ALTER TABLE {0} DROP CONSTRAINT {1}")
        self._pkey_common(command, suffix, "Dropped")

    def restore_pkeys(self, suffix=""):
        """
        Restore the primary key on the id columns.

        INPUT:

        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the ALTER TABLE statements.
        """
        command = SQL("ALTER TABLE {0} ADD CONSTRAINT {1} PRIMARY KEY (id)")
        self._pkey_common(command, suffix, "Built")

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
        - not necessarily a superset of all the built constraints

        For the current built constraints on the search table, see ``_list_built_constraints``
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
        if type == "NOT NULL":
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
        if type == "NOT NULL":
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
        if type == "NOT NULL" and len(columns) != 1:
            raise ValueError("NOT NULL only supports one column")
        if all(col == "id" for col in columns):
            raise ValueError("Must specify non-id columns")
        for col in columns:
            if col != "id" and col not in self.search_cols:
                raise ValueError("%s not a column" % (col))
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
            table = self.search_table
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
        table = self.search_table + suffix
        return type, columns, check_func, table

    def drop_constraint(self, name, suffix="", permanent=False):
        """
        Drop a specified constraint.

        INPUT:

        - ``name`` -- the name of the constraint
        - ``suffix`` -- a string such as "_tmp" or "_old1" to be appended to the names in the statement.
        - ``permanent`` -- whether to remove the index from the meta_constraint table
        """
        now = time.time()
        with DelayCommit(self, silence=True):
            type, columns, _, table = self._get_constraint_data(name, suffix)
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
        """
        Export this table's row of ``meta_tables`` to a file, in the format
        accepted by :meth:`reload_meta`.
        """
        self._copy_to_meta("meta_tables", filename, self.search_table, sep=sep)

    def copy_to_indexes(self, filename, sep="|"):
        """
        Export this table's index definitions (its rows of ``meta_indexes``)
        to a file, in the format accepted by :meth:`reload_indexes`.
        """
        self._copy_to_meta("meta_indexes", filename, self.search_table, sep=sep)

    def copy_to_constraints(self, filename, sep="|"):
        """
        Export this table's constraint definitions (its rows of
        ``meta_constraints``) to a file, in the format accepted by
        :meth:`reload_constraints`.
        """
        self._copy_to_meta("meta_constraints", filename, self.search_table, sep=sep)

    def _get_current_index_version(self):
        return self._get_current_meta_version("meta_indexes", self.search_table)

    def _get_current_constraint_version(self):
        return self._get_current_meta_version("meta_constraints", self.search_table)

    def reload_indexes(self, filename, sep="|"):
        """
        Replace this table's index definitions in ``meta_indexes`` with the
        contents of the file (as written by :meth:`copy_to_indexes`).  The
        definitions being replaced are archived in ``meta_indexes_hist``, so
        :meth:`revert_indexes` can undo this.
        """
        return self._reload_meta("meta_indexes", filename, self.search_table, sep=sep)

    def reload_meta(self, filename, sep="|"):
        """
        Replace this table's row of ``meta_tables`` with the contents of the
        file (as written by :meth:`copy_to_meta`).  The row being replaced
        is archived in ``meta_tables_hist``, so :meth:`revert_meta` can undo
        this.
        """
        return self._reload_meta("meta_tables", filename, self.search_table, sep=sep)

    def reload_constraints(self, filename, sep="|"):
        """
        Replace this table's constraint definitions in ``meta_constraints``
        with the contents of the file (as written by
        :meth:`copy_to_constraints`).  The definitions being replaced are
        archived in ``meta_constraints_hist``, so :meth:`revert_constraints`
        can undo this.
        """
        return self._reload_meta("meta_constraints", filename, self.search_table, sep=sep)

    def revert_indexes(self, version=None):
        """
        Restore an earlier version of this table's index definitions from
        ``meta_indexes_hist``.

        INPUT:

        - ``version`` -- the version to restore (default: the one before the
          current version)
        """
        return self._revert_meta("meta_indexes", self.search_table, version)

    def revert_constraints(self, version=None):
        """
        Restore an earlier version of this table's constraint definitions
        from ``meta_constraints_hist``.

        INPUT:

        - ``version`` -- the version to restore (default: the one before the
          current version)
        """
        return self._revert_meta("meta_constraints", self.search_table, version)

    def revert_meta(self, version=None):
        """
        Restore an earlier version of this table's ``meta_tables`` row from
        ``meta_tables_hist``.

        INPUT:

        - ``version`` -- the version to restore (default: the one before the
          current version)
        """
        return self._revert_meta("meta_tables", self.search_table, version)

    ##################################################################
    # Insertion and updating data                                    #
    ##################################################################

    def _check_locks(self, changetype, datafile=None, suffix=""):
        """
        This function can be overridden to support additional checks before changing data.
        To this end, it has a return value (defaulting to None) that is passed into the eventual
        _log_db_change in the functions that call this, and it takes a datafile as input to
        support checking the size on disk (nothing is done with this datafile by default).

        While a staged copy of the table exists (see ``staged``), changes to
        the live table are refused: the copy was taken when the context was
        entered, so anything written to the live table afterward would be
        silently discarded when the copy is swapped into place.  This covers
        writes made through psycodict's API only; raw SQL from another
        connection bypasses it, with the count check at the end of ``staged``
        as a partial backstop.
        """
        # Skip the staged guard when a suffix is given (the operation targets
        # the suffixed scratch table, not the live one) and for
        # create_table_like, which only reads this table.  Note that the
        # staged handle itself is unaffected: its search_table already ends
        # in _tmp, so it checks for a doubly suffixed table here.  reload is
        # deliberately not exempted, since it would collide with the staged
        # copy partway through; failing here gives it a clear message.
        if not suffix and changetype != "create_table_like" and self._table_exists(self.search_table + "_tmp"):
            raise LockError(
                "A staged copy of %s exists (%s_tmp): a staged() context or a "
                "reload is in progress, and writes to the live table would be "
                "lost when the copy is swapped into place.  Exit the staged "
                "context first, or if the copy is left over from an "
                "interrupted operation, discard it with db.%s.drop_tmp() and "
                "try again."
                % (self.search_table, self.search_table, self.search_table)
            )
        if changetype in ["upsert", "update"]:
            locktypes = "update"
        elif changetype in ["insert_many", "copy_from"]:
            locktypes = "insert"
        elif changetype == "delete":
            locktypes = "delete"
        elif changetype == "create_table_like":
            locktypes = "select"
        elif changetype == "reload":
            # A reload builds new tables on the side and swaps them in at the
            # end, so it can proceed while other sessions use the table -- but
            # the swap takes an ACCESS EXCLUSIVE lock, so it will wait for any
            # lock held at that point (blocking everyone else while it queues).
            # Warn rather than raise, since these locks may well be gone by
            # the time the swap happens.
            locks = self._table_locked(self.search_table + suffix, "all")
            if locks:
                print(
                    "Warning: %s is locked by other processes; the swap at "
                    "the end of the reload will block until these locks are "
                    "released:" % (self.search_table + suffix,)
                )
                for locktype, pid in locks:
                    print("    %s held by pid %s" % (locktype, pid))
                print("Use db.show_queries() and db.show_blocked() to monitor them.")
            return
        else:
            locktypes = "all"
        locks = self._table_locked(self.search_table + suffix, locktypes)
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
        """
        Intended to finish off a batch of data changes by updating the
        cached total, refreshing statistics targets, and re-sorting by id.
        Currently a placeholder that does nothing.
        """
        # TODO
        # Update stats.total
        # Refresh stats targets
        # Sort and set self._out_of_order
        pass

    def _forbid_reindex_false(self, reindex, inplace):
        """
        Raise an error on a request to skip index rebuilding during an update
        that swaps in a new table, which cannot be honored; see the docstrings
        of ``rewrite`` and ``update_from_file``.
        """
        if reindex is False and not inplace:
            raise ValueError(
                "reindex=False is impossible when updating by swapping in a new "
                "table (the default): the replacement table is built from scratch "
                "(so that reload_revert is available) and its indexes must be "
                "recreated.  Pass inplace=True (which cannot be undone with "
                "reload_revert) to update rows without rebuilding indexes."
            )

    def rewrite(
        self,
        func,
        query={},
        # Keyword-only so that old positional calls (which had reindex fifth,
        # before restat) fail loudly instead of silently binding to restat.
        *,
        resort=True,
        restat=True,
        tostr_func=None,
        datafile=None,
        progress_count=10000,
        **kwds
    ):
        """
        This function can be used to edit some or all records in the table.

        Note that if you want to add new columns, you must explicitly call add_column() first.

        The modified records are written to a file and loaded into a brand-new
        table, which is then swapped in for the current one, so that the change
        can be undone with ``reload_revert`` and no locks are taken on a table
        that is being actively used.  Since the replacement table is built from
        scratch, all of its indexes are always recreated; there is thus no
        ``reindex`` option, and asking for ``reindex=False`` raises an error
        (unless ``inplace=True`` is passed through to ``update_from_file``,
        which edits rows on the live table instead).  All arguments other than
        ``func`` and ``query`` must be passed by keyword.

        INPUT:

        - ``func`` -- a function that takes a record (dictionary) as input and returns the modified record
        - ``query`` -- a query dictionary; only rows satisfying this query will be changed
        - ``resort`` -- whether to resort the table after running the rewrite
        - ``restat`` -- whether to recompute statistics after running the rewrite
        - ``tostr_func`` -- a function to be used when writing data to the temp file
            defaults to copy_dumps from encoding
        - ``datafile`` -- a filename to use for the temp file holding the data
        - ``progress_count`` -- (default 10000) how frequently to print out status reports as the rewrite proceeds
        - ``**kwds`` -- any other keyword arguments (such as ``inplace`` or ``sep``) are passed on to the ``update_from_file`` method

        EXAMPLES:

        For example, to add a new column to test_fields holding the signed
        discriminant, you would do the following::

            >>> nf = db.test_fields
            >>> nf.add_column('disc', 'integer')  # doctest: +SKIP
            >>> def add_disc(rec):
            ...     rec['disc'] = rec['disc_sign'] * rec['disc_abs']
            ...     return rec
            >>> nf.rewrite(add_disc)  # doctest: +SKIP
        """
        # Fail before the expensive dump below rather than deep inside update_from_file
        self._forbid_reindex_false(kwds.get("reindex"), kwds.get("inplace"))
        sep = kwds.get("sep", "|")
        # An unusable separator would otherwise be rejected only by COPY itself,
        # after func has already been run over every row of the table.
        check_copy_sep(sep)
        if not kwds.get("inplace"):
            # A non-inplace rewrite ends in update_from_file, which repeats
            # this check; running it here as well means that a leftover from
            # an unfinished reload is reported before ``func`` is run on
            # every row of the table.
            self._check_tmp_leftovers([self.search_table])
        data_cols = projection = ["id"] + self.search_cols
        # It would be nice to just use Postgres' COPY TO here, but it would then be hard
        # to give func access to the data to process.
        # An alternative approach would be to use COPY TO and have func and filter both
        # operate on the results, but then func would have to process the strings
        if tostr_func is None:
            # Curry the separator in so that every formatted field gets it escaped the
            # way COPY FROM expects.  A user-supplied tostr_func keeps its (value, type)
            # signature, so it is responsible for its own separator handling.
            tostr_func = partial(copy_dumps, sep=sep)
        if datafile is None:
            datafile = tempfile.NamedTemporaryFile("w", delete=False)
        elif os.path.exists(datafile):
            raise ValueError("Data file %s already exists" % datafile)
        else:
            datafile = open(datafile, "w")
        start = time.time()
        count = 0
        tot = self.count(query)
        try:
            with datafile:
                # write headers
                datafile.write(sep.join(data_cols) + "\n")
                datafile.write(
                    sep.join(self.col_type.get(col) for col in data_cols)
                    + "\n\n"
                )

                for rec in self.search(query, projection=projection, sort=[]):
                    processed = func(rec)
                    datafile.write(
                        sep.join(
                            tostr_func(processed.get(col), self.col_type[col])
                            for col in data_cols
                        )
                        + "\n"
                    )
                    count += 1
                    if (count % progress_count) == 0:
                        print(
                            "%d of %d records (%.1f percent) dumped in %.3f secs"
                            % (count, tot, 100.0 * count / tot, time.time() - start)
                        )
            print("All records dumped in %.3f secs" % (time.time() - start))
            self.update_from_file(
                datafile.name,
                label_col="id",
                resort=resort,
                restat=restat,
                logging=dict(operation="rewrite", query=query, projection=projection),
                **kwds
            )
        finally:
            os.unlink(datafile.name)

    def update_from_file(
        self,
        datafile,
        label_col=None,
        # Keyword-only so that callers must name reindex (whose default and
        # meaning changed) rather than reaching it positionally.
        *,
        inplace=False,
        resort=None,
        reindex=None,
        restat=True,
        logging={"operation":"file_update"},
        **kwds
    ):
        """
        Updates this table from data stored in a file.

        By default the updated rows are merged into a brand-new table, which is
        then swapped in for the current one, so that the change can be undone
        with ``reload_revert`` and no locks are taken on a table that is being
        actively used.  Since the replacement table is built from scratch, all
        of its indexes are always recreated, whatever ``reindex`` says; with
        ``inplace=True`` the rows are instead edited on the live table and
        ``reindex`` controls how the indexes are handled.  Arguments after
        ``label_col`` must be passed by keyword.

        INPUT:

        - ``datafile`` -- a file with header lines (unlike ``reload``, does not need to include all columns) and rows containing data to be updated.
        - ``label_col`` -- a column specifying which row(s) of the table should be updated corresponding to each row of the input file.  This will usually be the label for the table, in which case it can be omitted.
        - ``inplace`` -- whether to do the update in place.  If set, the operation cannot be undone with ``reload_revert``.
        - ``resort`` -- whether this table should be resorted after updating (default is to resort when the sort columns intersect the updated columns)
        - ``reindex`` -- only meaningful when ``inplace`` is set: whether to drop the indexes touching the updated columns before the update and recreate them afterward, which is faster when many rows change (by default this is done when more than 1000 rows are updated).  Without ``inplace``, all indexes are necessarily recreated on the replacement table, so ``reindex=True`` is redundant and ``reindex=False`` raises an error.
        - ``restat`` -- whether to recompute stats for the table
        - ``logging`` -- a dictionary of keyword arguments for _log_db_change
        - ``kwds`` -- passed on to the ``COPY`` command.  Cannot include "columns".
        """
        self._forbid_reindex_false(reindex, inplace)
        if not inplace:
            # The non-inplace update clones the search table to a _tmp copy
            # and rebuilds its indexes with _tmp names, just like reload, so
            # leftovers from an unfinished reload would make it fail midway.
            # The counts and stats tables are not checked: this method
            # deliberately reuses their _tmp versions when they exist.
            self._check_tmp_leftovers([self.search_table])
        logid = self._check_locks(logging["operation"], datafile=datafile)
        logging["aborted"] = True
        try:
            sep = kwds.get("sep", "|")
            print("Updating %s from %s..." % (self.search_table, datafile))
            now = time.time()
            if label_col is None:
                label_col = self._label_col
                if label_col is None:
                    raise ValueError("You must specify a column that is contained in the datafile and uniquely specifies each row")
            elif label_col != "id" and label_col not in self.search_cols or self.count_distinct(label_col) != self.count():
                raise ValueError("You must specify a column that uniquely specifies each row")
            with open(datafile) as F:
                tables = [self.search_table]
                columns = list(self.search_cols)
                columns = self._check_header_lines(F, tables, set(columns), sep=sep, prohibit_missing=False)
                if columns[0] != label_col:
                    raise ValueError("%s must be the first column in the data file" % label_col)
                if "id" in columns[1:]:
                    raise ValueError("Cannot update id using update_from_file")
                if inplace and reindex is None:
                    rowcount = 0
                    for line in F:
                        rowcount += 1
                    reindex = rowcount > 1000
            if resort is None:
                resort = bool(set(columns[1:]).intersection(self._sort_keys))
            # Create a temp table to hold the data
            tmp_table = "tmp_update_from_file"

            def drop_tmp():
                dropper = SQL("DROP TABLE {0}").format(Identifier(tmp_table))
                self._execute(dropper)

            with DelayCommit(self, silence=True):
                if self._table_exists(tmp_table):
                    drop_tmp()
                self._create_table(tmp_table,
                                   [(col, self.col_type[col]) for col in columns],
                                   addid=(label_col != "id" and self.col_type["id"]))
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
                suffix = "" if inplace else "_tmp"
                stable = self.search_table + suffix
                if inplace:
                    if reindex:
                        self.drop_indexes(columns[1:], permanent=False)
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
                else:
                    self._clone(self.search_table, stable)
                    inserter = SQL("INSERT INTO {0} ({1}) SELECT {2} FROM {3} tdisk RIGHT JOIN {4} tcur ON tdisk.{5} = tcur.{5}")
                    self._execute(inserter.format(
                        Identifier(stable),
                        SQL(", ").join(Identifier(col) for col in ["id"] + self.search_cols),
                        SQL(", ").join((SQL("COALESCE(tdisk.{0}, tcur.{0})") if col in scols else
                                        SQL("tcur.{0}")).format(Identifier(col))
                                       for col in ["id"] + self.search_cols),
                        Identifier(tmp_table),
                        Identifier(self.search_table),
                        Identifier(label_col)))
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
                if restat and self.stats.saving:
                    if not inplace:
                        for table in [self.stats.counts, self.stats.stats]:
                            if not self._table_exists(table + "_tmp"):
                                self._clone(table, table + "_tmp")
                    self.stats.refresh_stats(suffix=suffix)
                if not inplace:
                    # Swap in the refreshed counts/stats alongside the search
                    # table.  refresh_stats above populated the _tmp counts and
                    # stats tables, but they only reach the live names if they
                    # are in this list; otherwise the recomputed statistics are
                    # silently dropped (the live stats keep their stale values)
                    # and the _tmp tables are left orphaned.  reload builds its
                    # swap list the same way.
                    tables = [self.search_table]
                    if restat and self.stats.saving:
                        tables += [self.stats.counts, self.stats.stats]
                    if self.stats.counts in tables:
                        # _clone built the _tmp counts table with a bare LIKE,
                        # which copies no indexes; build the standard counts
                        # indexes on it before the swap so the live counts
                        # table keeps them (otherwise cached-count lookups
                        # degrade to sequential scans).  reload does the same.
                        self._create_counts_indexes(suffix=suffix)
                    self._swap_in_tmp(tables)
                    if ordered:
                        self._set_ordered()
                # Delete the temporary table used to load the data
                drop_tmp()
                logging["logid"] = logid
                logging["aborted"] = False
                print("Updated %s in %.3f secs" % (self.search_table, time.time() - now))
        finally:
            self._log_db_change(**logging)

    def delete(self, query, restat=True):
        """
        Delete all rows matching the query.

        INPUT:

        - ``query`` -- a query dictionary; rows matching the query will be deleted
        - ``restat`` -- whether to recreate statistics afterward
        """
        logid = self._check_locks("delete")
        aborted = True
        nrows = -1
        try:
            with DelayCommit(self, silence=True):
                qstr, values = self._parse_dict(query)
                if qstr is None:
                    qstr = SQL("")
                else:
                    qstr = SQL(" WHERE {0}").format(qstr)
                deleter = SQL("DELETE FROM {0}{1}").format(Identifier(self.search_table), qstr)
                cur = self._execute(deleter, values)
                #self._break_order()
                self._break_stats()
                nrows = cur.rowcount
                self.stats._update_total(-nrows)
                if self.stats.saving and restat:
                    self.stats.refresh_stats(total=False)
            aborted = False
        finally:
            self._log_db_change("delete", aborted=aborted, logid=logid, query=query, nrows=nrows)

    def update(self, query, changes, resort=False, restat=True):
        """
        Update a table using Postgres' update command

        INPUT:

        - ``query`` -- a query dictionary.  Only rows matching the query will be updated
        - ``changes`` -- a dictionary.  The keys should be column names, the values should be constants.
        - ``resort`` -- whether to resort the table afterward
        - ``restat`` -- whether to recompute statistics afterward
        """
        logid = self._check_locks("update")
        aborted = True
        try:
            with DelayCommit(self):
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
            aborted = False
        finally:
            self._log_db_change("update", aborted=aborted, logid=logid, query=query, changes=changes)

    def upsert(self, query, data):
        """
        Update the unique row satisfying the given query, or insert a new row if no such row exists.
        If more than one row exists, raises an error.

        Upserting will often break the order constraint if the table is id_ordered,
        so you will probably want to call ``resort`` after all upserts are complete.

        INPUT:

        - ``query`` -- a dictionary with key/value pairs specifying at most one row of the table.
          The most common case is that there is one key, which is either an id or a label.
        - ``data`` -- a dictionary containing key/value pairs to be set on this row.

        The keys of both inputs must be columns of the table.

        OUTPUT:

        - ``new_row`` -- whether a new row was inserted
        - ``row_id`` -- the id of the found/new row
        """
        logid = self._check_locks("upsert")
        aborted = True
        try:
            if not query or not data:
                raise ValueError("Both query and data must be nonempty")
            if "id" in data:
                raise ValueError("Cannot set id")
            for col in query:
                if col != "id" and col not in self.search_cols:
                    raise ValueError("%s is not a column of %s" % (col, self.search_table))
            search_data = dict(data)
            for col in data:
                if col not in self.search_cols:
                    raise ValueError("%s is not a column of %s" % (col, self.search_table))
            cases = [(self.search_table, search_data)]
            with DelayCommit(self, silence=True):
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
                    for table, dat in cases:
                        inserter = SQL("INSERT INTO {0} ({1}) VALUES ({2})").format(
                            Identifier(table),
                            SQL(", ").join(map(Identifier, list(dat))),
                            SQL(", ").join(Placeholder() * len(dat)),
                        )
                        self._execute(inserter, self._parse_values(dat))
                    self._break_order()
                    self.stats._update_total(1)
                self._break_stats()
            aborted = False
            return new_row, row_id
        finally:
            self._log_db_change("upsert", aborted=aborted, logid=logid, query=query, data=data)

    def insert_many(self, data, resort=False, reindex=None, restat=True):
        """
        Insert multiple rows.

        This function will be faster than repeated ``upsert`` calls, but slower than ``copy_from``

        INPUT:

        - ``data`` -- a list of dictionaries, whose keys are columns and values the values to be set.
          All dictionaries must have the same set of keys.
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- boolean (default True iff data has more than 1000 entries). Whether to drop the indexes
          before insertion and restore afterward.  Note that if there is an exception during insertion
          the indexes will need to be restored manually using ``restore_indexes``.
        - ``restat`` -- whether to refresh statistics after insertion

        If the search table has an id, the dictionaries will be updated with the ids of the inserted records,
        though note that those ids will change if the ids are resorted.
        """
        logid = self._check_locks("insert_many")
        aborted = True
        search_data = []
        try:
            if not data:
                raise ValueError("No data provided")
            if reindex is None:
                reindex = len(data) > 1000
            invalid = [x for x in data[0] if x not in self.search_cols]
            if invalid:
                raise ValueError(f"Input has invalid columns: {', '.join(invalid)}")
            # The INSERT payload is a copy of each row: the documented API
            # stamps the assigned id onto the caller's dictionaries (see the
            # docstring), but the Json wrapping below is an implementation
            # detail that must not leak into them.
            search_data = [dict(D) for D in data]
            search_cols = set(data[0])
            with DelayCommit(self):
                jsonb_cols = [col for col, typ in self.col_type.items() if typ == "jsonb"]
                for i, SD in enumerate(search_data):
                    if set(SD) != search_cols:
                        raise ValueError("All dictionaries must have the same set of keys")
                    # Stamped on the caller's dictionary too -- the docstring
                    # promises the input is updated with the assigned ids.
                    SD["id"] = data[i]["id"] = self.max_id() + i + 1
                    for col in jsonb_cols:
                        # None must stay None: wrapping it in Json would store
                        # the jsonb value 'null' rather than SQL NULL, and the
                        # documented {col: None} query could never match it.
                        if col in SD and SD[col] is not None:
                            SD[col] = Json(SD[col])
                cases = [(self.search_table, search_data)]
                now = time.time()
                if reindex:
                    self.drop_pkeys()
                    self.drop_indexes(search_cols, permanent=False)
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
                    self.restore_indexes(search_cols)
                self.stats._update_total(len(search_data))
                if self.stats.saving and restat:
                    self.stats.refresh_stats(total=False)
            aborted = False
        finally:
            self._log_db_change("insert_many", aborted=aborted, logid=logid, nrows=len(search_data))

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
        tmp_table = Identifier(self.search_table + suffix + "_sorter")
        tmp_seq = Identifier(self.search_table + suffix + "_sorter" + '_newid_seq')
        sort_order = self._sort if sort is None else self._sort_str(sort)
        if sort_order is None:
            print("resort failed, no sort order given")
            return False
        logid = self._check_locks("resort", suffix=suffix)
        aborted = True
        try:
            with DelayCommit(self, silence=True):
                if (self._id_ordered and self._out_of_order) or suffix:
                    now = time.time()
                    # we will use a temporary table to avoid ACCESS EXCLUSIVE lock
                    self._execute(SQL(
                        "CREATE TEMP SEQUENCE {0} MINVALUE 0 START 0 CACHE 10000"
                    ).format(tmp_seq))

                    id_type = self.col_type["id"]
                    self._execute(SQL(
                        "CREATE TEMP TABLE {0} (oldid %s, newid %s NOT NULL DEFAULT nextval('{1}')) ON COMMIT DROP" % (id_type, id_type)
                    ).format(tmp_table, tmp_seq))

                    self._execute(SQL(
                        "ALTER SEQUENCE {0} OWNED BY {1}.newid"
                    ).format(tmp_seq, tmp_table))

                    self._execute(SQL(
                        "INSERT INTO {0} "
                        "SELECT id as oldid FROM {1} ORDER BY {2}"
                    ).format(tmp_table, search_table, sort_order))
                    self.drop_pkeys(suffix=suffix)
                    self._execute(SQL(
                        "UPDATE {0} SET id = {1}.newid "
                        "FROM {1} WHERE {0}.id = {1}.oldid"
                    ).format(search_table, tmp_table))
                    self.restore_pkeys(suffix=suffix)
                    if not suffix:
                        self._set_ordered()
                    print("Resorted %s in %.3f secs" % (self.search_table, time.time() - now))
                elif self._id_ordered and not self._out_of_order:
                    print(f"Table {self.search_table} already sorted")
                else:  # not self._id_ordered
                    print("Data does not have an id column to be sorted")
            aborted = False
            return True
        finally:
            self._log_db_change("resort", logid=logid, aborted=aborted, sort_order=sort_order)

    def _set_ordered(self):
        """
        Marks this table as sorted in meta_tables
        """
        with DelayCommit(self, silence=True):
            updater = SQL("UPDATE meta_tables SET (id_ordered, out_of_order) = (%s, %s) WHERE name = %s")
            self._execute(updater, [True, False, self.search_table])
            self._id_ordered = True
            self._out_of_order = False

    def _write_header_lines(self, F, cols, sep="|", include_id=True):
        """
        Writes the header lines to a file
        (row of column names, row of column types, blank line).

        INPUT:

        - ``F`` -- a writable open file handle, at the beginning of the file.
        - ``cols`` -- a list of columns to write (e.g. self.search_cols)
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
        for ext in ["", "_counts", "_stats"]:
            while self._table_exists("{0}{1}_old{2}".format(self.search_table, ext, backup_number)):
                backup_number += 1
        return backup_number

    def _swap_in_tmp(self, tables):
        """
        Helper function for ``reload``: appends _old{n} to the names of tables/indexes/pkeys
        and renames the _tmp versions to the live versions.

        INPUT:

        - ``tables`` -- a list of tables to rename (e.g. self.search_table, self.stats.counts, self.stats.stats)
        """
        now = time.time()
        backup_number = self._next_backup_number()
        with DelayCommit(self, silence=True):
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

    def _check_file_input(self, searchfile, kwds):
        """
        Utility function for validating the inputs to ``rewrite``, ``reload`` and ``copy_from``.
        """
        if searchfile is None:
            raise ValueError("Must specify search file")
        if "columns" in kwds:
            raise ValueError("Cannot specify column order using the columns parameter")

    def _check_tmp_leftovers(self, clone_tables=None):
        """
        Check for indexes, constraints and tables left over from an earlier
        unfinished reload, whose names collide with the temporary names that
        the next reload will use.

        A crashed or interrupted reload can leave objects whose names end in
        ``_tmp`` (or ``_tmp_pkey`` for primary keys) attached to the live
        search, counts and stats tables.  The next reload then fails partway
        through, after the expensive data loading.  This is called at the
        start of ``reload`` and of a non-inplace ``rewrite`` or
        ``update_from_file`` so that the failure happens before any work is
        done, with a ValueError whose message lists each offending object
        together with SQL commands that rename or drop it.

        INPUT:

        - ``clone_tables`` -- a list of table names (optional).  The caller
            will create a fresh ``<name>_tmp`` table for each, so an existing
            table of that name is reported as a leftover.  Tables for which
            the caller reuses an existing ``_tmp`` table (the counts and
            stats tables when no data file is given) must not be included.
        """
        if self.search_table.endswith("_tmp"):
            # This object is itself a scratch copy (e.g. a staged() handle):
            # its own objects legitimately carry _tmp names, and no live
            # table can end in _tmp (_check_restricted_suffix forbids it),
            # so there is nothing to protect here.
            return
        tables = [self.search_table]
        if self.stats.saving:
            tables.extend([self.stats.counts, self.stats.stats])
        # The two shapes of temporary names used by reload: indexes and
        # constraints get <name>_tmp, primary keys get <table>_tmp_pkey.
        pattern = "_tmp(_pkey)?$"
        leftovers = [
            ("constraint", tbl, name)
            for tbl, name in self._execute(
                SQL(
                    "SELECT rel.relname, con.conname FROM pg_constraint con "
                    "JOIN pg_class rel ON rel.oid = con.conrelid "
                    "WHERE rel.relname = ANY(%s) AND con.conname ~ %s"
                ),
                [tables, pattern],
                silent=True,
            )
        ]
        # A unique or primary key constraint is backed by an index of the same
        # name; it can only be renamed or dropped as a constraint, so report
        # it once, as a constraint.
        found = {(tbl, name) for (kind, tbl, name) in leftovers}
        leftovers.extend(
            ("index", tbl, name)
            for tbl, name in self._execute(
                SQL(
                    "SELECT tablename, indexname FROM pg_indexes "
                    "WHERE tablename = ANY(%s) AND indexname ~ %s"
                ),
                [tables, pattern],
                silent=True,
            )
            if (tbl, name) not in found
        )
        leftovers.sort(key=lambda trip: (trip[1], trip[2]))
        if clone_tables is None:
            clone_tables = []
        tmp_tables = [t + "_tmp" for t in clone_tables if self._table_exists(t + "_tmp")]
        if not (leftovers or tmp_tables):
            return
        lines = [
            "Found leftover objects from an earlier unfinished reload of %s; "
            "they would collide with this operation." % (self.search_table,),
            "If an object holds live data (e.g. the final swap of a reload "
            "was interrupted), rename it; if it is junk, drop it:",
        ]
        for name in tmp_tables:
            lines.append("- table %s:\n    %s;" % (
                name,
                SQL("DROP TABLE {0}").format(Identifier(name)).as_string(self.conn),
            ))
        for kind, tbl, name in leftovers:
            if name.endswith("_tmp"):
                newname = name[:-len("_tmp")]
            else:
                newname = name[:-len("_tmp_pkey")] + "_pkey"
            if kind == "constraint":
                rename = SQL("ALTER TABLE {0} RENAME CONSTRAINT {1} TO {2}").format(
                    Identifier(tbl), Identifier(name), Identifier(newname)
                )
                drop = SQL("ALTER TABLE {0} DROP CONSTRAINT {1}").format(
                    Identifier(tbl), Identifier(name)
                )
            else:
                rename = SQL("ALTER INDEX {0} RENAME TO {1}").format(
                    Identifier(name), Identifier(newname)
                )
                drop = SQL("DROP INDEX {0}").format(Identifier(name))
            lines.append("- %s %s on table %s:\n    %s;\n    %s;" % (
                kind, name, tbl,
                rename.as_string(self.conn), drop.as_string(self.conn),
            ))
        if tmp_tables:
            lines.append(
                "Leftover _tmp tables can also be removed with "
                "db.%s.drop_tmp(); if they come from a reload with "
                "final_swap=False, finish that reload with "
                "db.%s.reload_final_swap() instead."
                % (self.search_table, self.search_table)
            )
        raise ValueError("\n".join(lines))

    def reload(
        self,
        searchfile,
        countsfile=None,
        statsfile=None,
        indexesfile=None,
        constraintsfile=None,
        metafile=None,
        resort=None,
        restat=None,
        final_swap=True,
        silence_meta=False,
        adjust_schema=False,
        **kwds
    ):
        """
        Safely and efficiently replaces this table with the contents of one or more files.

        The data is loaded into a brand-new table, which is then swapped in for
        the current one, so that the change can be undone with ``reload_revert``
        and no locks are taken on a table that is being actively used.  The
        primary key, indexes and constraints are always recreated on the new
        table, after the data is loaded (building them afterward is faster than
        maintaining them during the load).  There is deliberately no ``reindex``
        option: the replacement table starts without indexes, so they can only
        be rebuilt, never preserved.

        INPUT:

        - ``searchfile`` -- a string, the file with data for the search table
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
            when the searchfile does not contain ids.
        - ``restat`` -- whether to refresh statistics afterward.  Default behavior
            is to refresh stats if either countsfile or statsfile is missing.
        - ``final_swap`` -- whether to perform the final swap exchanging the
            temporary table with the live one.
        - ``silence_meta`` -- suppress the warning message when using a metafile
        - ``adjust_schema`` -- If True, it will create the new tables using the
            header columns, otherwise expects the schema specified by the files
            to match the current one
        - ``kwds`` -- passed on to the ``COPY`` command.  Cannot include "columns".

        .. NOTE:

            If the search file contains ids, they should be contiguous,
            starting at 1.
        """
        sep = kwds.get("sep", "|")
        suffix = "_tmp"
        if restat is None:
            restat = countsfile is None or statsfile is None
        self._check_file_input(searchfile, kwds)
        # Fail now, rather than partway through, if an earlier unfinished
        # reload left _tmp objects behind.  Only the tables with a data file
        # get a fresh clone below; the other tables reuse an existing _tmp.
        clone_tables = [self.search_table]
        if self.stats.saving:
            clone_tables.extend(
                tbl
                for tbl, datafile in [(self.stats.counts, countsfile), (self.stats.stats, statsfile)]
                if datafile is not None
            )
        self._check_tmp_leftovers(clone_tables)
        print("Reloading %s..." % (self.search_table))
        logid = self._check_locks("reload", datafile=searchfile)
        aborted = True
        try:
            now_overall = time.time()

            tables = []
            counts = {}
            tabledata = [
                (self.search_table, self.search_cols, True, searchfile),
            ]
            if self.stats.saving:
                tabledata.extend([
                    (self.stats.counts, _counts_cols, False, countsfile),
                    (self.stats.stats, _stats_cols, False, statsfile),
                ])
            addedid = None
            with DelayCommit(self, silence=True):
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
                    if header:
                        if addedid is None:
                            addedid = addid
                    if resort is None and addid:
                        resort = True
                    print(
                        "\tLoaded data into %s in %.3f secs from %s"
                        % (table, time.time() - now, filename)
                    )

                self.restore_pkeys(suffix=suffix)

                # update the indexes
                # these are needed before restoring indexes
                if indexesfile is not None:
                    # we do the swap at the end
                    self.reload_indexes(indexesfile, sep=sep)
                if constraintsfile is not None:
                    self.reload_constraints(constraintsfile, sep=sep)
                # Also restores constraints
                self.restore_indexes(suffix=suffix)

                if resort:
                    if metafile:
                        # read the metafile
                        # using code from _reload_meta
                        meta_name = 'meta_tables'
                        meta_cols, _, _ = _meta_cols_types_jsonb_idx(meta_name)
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
                                idx = meta_cols.index(col)
                                if line[idx] not in ['t', 'f']:
                                    raise RuntimeError(
                                        f"column {idx} (= {line[idx]}) "
                                        f"in the file {metafile} is different from 't' or 'f'"
                                    )
                            resort = (
                                line[meta_cols.index("id_ordered")] == 't'
                                and line[meta_cols.index("out_of_order")] == 'f'
                            )
                    else:
                        if not self._id_ordered: # this table doesn't need to be sorted
                            resort = False
                    # tracks the success of resort
                    ordered = self.resort(suffix=suffix)
                else:
                    ordered = False

                # Ensure stats/counts tables are backed up and new empty ones created
                if self.stats.saving:
                    for table in [self.stats.counts, self.stats.stats]:
                        if table not in tables:
                            # Create _tmp version if it doesn't exist
                            if not self._table_exists(table + suffix):
                                self._clone(table, table + suffix)
                            # Add to tables list so it gets backed up in the swap
                            tables.append(table)

                    # Only refresh stats if restat is True
                    if restat and (countsfile is None or statsfile is None):
                        self.stats.refresh_stats(suffix=suffix)

                if self.stats.counts in tables:
                    # create index on counts table
                    self._create_counts_indexes(suffix=suffix)

                if final_swap:
                    self.reload_final_swap(tables=tables,
                                           metafile=metafile,
                                           ordered=ordered)
                elif metafile is not None and not silence_meta:
                    print("Warning: since the final swap was not requested, we have not updated meta_tables")
                    print("when performing the final swap with reload_final_swap, pass the metafile as an argument to update the meta_tables")
                print("Reloaded %s in %.3f secs" % (self.search_table, time.time() - now_overall))
            aborted = False
        finally:
            self._log_db_change(
                "reload",
                logid=logid,
                aborted=aborted,
                counts=(countsfile is not None),
                stats=(statsfile is not None),
            )

    def reload_final_swap(self, tables=None, metafile=None, ordered=False, sep="|"):
        """
        Renames the ``_tmp`` versions of ``tables`` to the live versions,
        and updates the corresponding meta_tables row if ``metafile`` is provided.

        INPUT:

        - ``tables`` -- list of strings (optional), of the tables to be renamed.  If None is provided, renames all the tables ending in ``_tmp``
        - ``metafile`` -- a string (optional), giving a file containing the meta information for the table.
        - ``sep`` -- a character (default ``|``) to separate columns
        """
        with DelayCommit(self, silence=True):
            if tables is None:
                # _swap_in_tmp takes the base names and appends the _tmp
                # itself, so record the base name (not the _tmp one) of each
                # companion that actually has a staged _tmp copy.
                tables = []
                for suffix in ["", "_stats", "_counts"]:
                    tablename = "{0}{1}".format(self.search_table, suffix)
                    if self._table_exists(tablename + "_tmp"):
                        tables.append(tablename)

            self._swap_in_tmp(tables)
            if metafile is not None:
                self.reload_meta(metafile, sep=sep)
            if ordered:
                self._set_ordered()
            # The swapped-in table's row count bears no relation to the old
            # total, so recount and store it before the reinitialization
            # below reads meta_tables.
            self.stats._set_total(self.stats._slow_count({}, record=False))
            self._db._notify_schema_change(self.search_table)  # rides this transaction

        # Reinitialize object
        tabledata = self._execute(
            SQL(
                "SELECT name, label_col, sort, count_cutoff, id_ordered, out_of_order, "
                "stats_valid, total, include_nones "
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
            for suffix in ["", "_stats", "_counts"]:
                tablename = "{0}{1}_tmp".format(self.search_table, suffix)
                if self._table_exists(tablename):
                    self._execute(SQL("DROP TABLE {0}").format(Identifier(tablename)))
                    print("Dropped {0}".format(tablename))

    def reload_revert(self, backup_number=None):
        """
        Use this method to revert to an older version of a table.

        Note that calling this method twice with the same input
        should return you to the original state.

        INPUT:

        - ``backup_number`` -- the backup version to restore,
            or ``None`` for the most recent.
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
        with DelayCommit(self, silence=True):
            old = "_old" + str(backup_number)
            tables = []
            for suffix in ["", "_stats", "_counts"]:
                tablename = "{0}{1}".format(self.search_table, suffix)
                if self._table_exists(tablename + old):
                    tables.append(tablename)
            self._swap(tables, "", "_tmp")
            self._swap(tables, old, "")
            self._swap(tables, "_tmp", old)
            self._log_db_change("reload_revert")
        print(
            "Swapped backup %s with %s"
            % (self.search_table, "{0}_old{1}".format(self.search_table, backup_number))
        )

    def cleanup_from_reload(self, keep_old=0):
        """
        Drop the ``_tmp`` and ``_old*`` tables that are created during ``reload``.

        Note that doing so will prevent ``reload_revert`` from working.

        INPUT:

        - ``keep_old`` -- the number of old tables to keep (they will be renamed so that they start at 1)
        """
        to_remove = []
        to_swap = []
        tablenames = [name for name in self._all_tablenames() if name.startswith(self.search_table)]
        for suffix in ["", "_stats", "_counts"]:
            head = self.search_table + suffix
            tablename = head + "_tmp"
            if tablename in tablenames:
                to_remove.append(tablename)
            olds = []
            for name in tablenames:
                m = re.fullmatch(head + r"_old(\d+)", name)
                if m:
                    olds.append(int(m.group(1)))
            olds.sort()
            if keep_old > 0:
                for new_number, n in enumerate(olds[-keep_old:], 1):
                    if n != new_number:
                        to_swap.append((head, n, new_number))
                olds = olds[:-keep_old]
            to_remove.extend([head + f"_old{n}" for n in olds])
        with DelayCommit(self, silence=True):
            for table in to_remove:
                self._execute(SQL("DROP TABLE {0}").format(Identifier(table)))
                print("Dropped {0}".format(table))
            for head, cur_tail, new_tail in to_swap:
                self._swap([head], f"_old{cur_tail}", f"_old{new_tail}")
                print(f"Swapped {head}{cur_tail} to {head}{new_tail}")

    ##################################################################
    # Staged writes                                                  #
    ##################################################################

    # Methods disabled on the staged handle yielded by ``staged``: changing
    # the schema of the staged copy would desynchronize it from the meta_*
    # rows describing the live table (which the swap does not touch), the
    # reload machinery does not compose with an active staged context, and
    # an unpaired drop_pkeys would strip the primary key from the table that
    # the swap installs (the commit only rebuilds what meta_indexes and
    # meta_constraints record, which does not include the primary key).
    # drop_indexes and restore_indexes are deliberately not here: they only
    # act on what meta_indexes and meta_constraints record for the handle's
    # (suffixed) name, which is nothing, and the write methods call them
    # internally when reindex is set, so they must stay working no-ops.
    _staged_unsupported = (
        "add_column",
        "drop_column",
        "create_index",
        "drop_index",
        "restore_index",
        "create_constraint",
        "drop_constraint",
        "restore_constraint",
        "drop_pkeys",
        "restore_pkeys",
        "set_sort",
        "set_label",
        "set_importance",
        "reload",
        "reload_final_swap",
        "reload_revert",
        "cleanup_from_reload",
        "reload_indexes",
        "reload_meta",
        "reload_constraints",
        "revert_indexes",
        "revert_meta",
        "revert_constraints",
        "drop_tmp",
        "staged",
        "staged_force_swap",
    )

    def staged(self):
        """
        Returns a context manager for editing this table without ever
        modifying the live table in place.

        On entering the context, the search table is copied (data, ids and
        primary key, but no other indexes) to a table with a ``_tmp`` suffix,
        and empty copies of the counts and stats tables are created alongside
        it.  The object yielded is a genuine table object pointed at the
        copy, so the usual write methods (``insert_many``, ``update``,
        ``upsert``, ``delete``, ``rewrite``, ...) and the search methods work
        on it, while reads on the live table proceed as if nothing had
        happened.

        On exiting normally, the indexes and constraints recorded in
        meta_indexes and meta_constraints are built on the copy and it is
        swapped into place using the same renaming choreography as
        ``reload``: the previous version is kept with an ``_old<n>`` suffix,
        so ``reload_revert`` undoes the swap and ``cleanup_from_reload``
        drops the backups.  The statistics are invalidated rather than
        recomputed: the swapped-in counts and stats tables are empty and
        stats_valid is set to false in meta_tables.

        On exiting with an exception, the copies are dropped and the live
        table is left exactly as it was.

        As with ``reload``, a successful swap replaces the table object held
        by the database, so get a fresh reference afterward (``db[name]``)
        rather than continuing to use an old one; the staged handle is also
        dead once the context exits.  Only one staged context (or reload) at
        a time can be active on a table; a second one raises on entry.
        Schema changes through the staged handle are disabled.  If the swap
        itself fails, the staged tables are left in place so that no work is
        lost; ``drop_tmp`` discards them and ``staged_force_swap`` adopts
        them, discarding whatever concurrent changes made the swap refuse.

        While the context is open, writes to the live table through
        psycodict's API (``insert_many``, ``update``, ``delete``, ..., from
        this or any other connection) raise ``LockError``, since the swap
        would silently discard them.  Raw SQL bypasses that guard; as a
        backstop, the commit refuses to swap if the live table's row count
        or maximum id changed while the context was open.  In-place updates
        change neither number and escape the backstop, so raw-SQL writers
        must simply stay away from a table while it is being staged.

        EXAMPLES:

        Stage a batch of changes -- here inserting a (real) totally real
        quartic field, touching it up, and then deleting it again, so the
        table ends up back where it started::

            >>> nf = db.test_fields
            >>> row = {'label': '4.4.725.1', 'degree': 4, 'r2': 0,
            ...        'disc_abs': 725, 'disc_sign': 1, 'ramps': [5, 29],
            ...        'class_number': 1, 'class_group': []}
            >>> with nf.staged() as staged:
            ...     staged.insert_many([row])
            ...     staged.update({'label': '4.4.725.1'}, {'class_number': 1})
            ...     staged.delete({'degree': 4})
            Built primary key on test_fields in ... secs
            Staged copy of test_fields created in ... secs
            Inserted 1 records into test_fields_tmp in ... secs
            ...
            Swapped temporary tables for test_fields into place in ... secs
            New backup at test_fields_old1
            >>> nf.count()
            22
        """
        return StagedWriteContext(self)

    def _staged_tables(self):
        """
        The tables taking part in a staged swap: the search table together
        with its counts and stats companions.
        """
        return [self.search_table, self.stats.counts, self.stats.stats]

    def _staged_blocked(self, methodname):
        """
        Utility function producing the stub that disables ``methodname`` on
        staged handles.
        """
        def blocked(*args, **kwds):
            raise ValueError(
                "%s is not supported on a staged table; "
                "exit the staged context and call it on %s itself"
                % (methodname, self.search_table)
            )
        return blocked

    def _staged_enter(self):
        """
        Create the staged copy of this table; the first half of ``staged``.

        OUTPUT:

        A pair ``(staged, logid)`` where ``staged`` is a table object
        pointed at the copy and ``logid`` comes from ``_check_locks``.
        """
        suffix = "_tmp"
        for table in self._staged_tables():
            if self._table_exists(table + suffix):
                raise ValueError(
                    "Temporary table %s already exists: another staged context "
                    "or reload may be in progress on %s.  If it is left over "
                    "from an interrupted one, run db.%s.drop_tmp() and try again."
                    % (table + suffix, self.search_table, self.search_table)
                )
        # Creating the copy only reads the live table, so it conflicts with
        # the same locks as the copy in create_table_like
        logid = self._check_locks("create_table_like")
        aborted = True
        try:
            now = time.time()
            # A single transaction, so that a failure part way through leaves
            # nothing behind; the copy becomes visible to other connections
            # (making their staged() fail fast above) when it commits.
            with DelayCommit(self, silence=True):
                for table in self._staged_tables():
                    self._clone(table, table + suffix)
                cols = SQL(", ").join(map(Identifier, ["id"] + self.search_cols))
                inserter = SQL("INSERT INTO {0} ({1}) SELECT {1} FROM {2}").format(
                    Identifier(self.search_table + suffix),
                    cols,
                    Identifier(self.search_table),
                )
                total = self._execute(inserter).rowcount
                # Reading the copy rather than the live table pins down
                # exactly what was copied, even if the live table moves
                # between the statements; the commit-time drift check
                # compares the live table against this.
                source_max_id = self.max_id(self.search_table + suffix)
                # The primary key keeps id lookups (max_id, upserts, updates
                # by id) fast during staging and catches id collisions as
                # they happen; the other indexes are built at commit time as
                # in reload, so that they are built once on the final data
                # rather than maintained through every staged write.
                self.restore_pkeys(suffix=suffix)
                # Staged writes are usually keyed by the label column (update,
                # upsert and update_from_file all look rows up by it), so give
                # the copy a plain index on it as well, turning those per-write
                # lookups from sequential scans into index scans.  Like the
                # other non-pkey indexes it is not part of meta_indexes; it is
                # dropped at commit before the real indexes are rebuilt (see
                # _staged_commit), so it never reaches the live table.
                if self._label_col is not None and self._label_col != "id":
                    self._execute(SQL("CREATE INDEX {0} ON {1} ({2})").format(
                        Identifier(self.search_table + suffix + "_staged_label"),
                        Identifier(self.search_table + suffix),
                        Identifier(self._label_col),
                    ))
            print(
                "Staged copy of %s created in %.3f secs"
                % (self.search_table, time.time() - now)
            )
            # A real table object pointed at the copy: the copy has no row in
            # meta_tables, so it is built from the live table's metadata and
            # the row count of the copy.  Writes through it update its cached
            # total and flags in memory; their meta_tables updates are keyed
            # on the suffixed name and so touch nothing.
            staged = type(self)(
                self._db,
                self.search_table + suffix,
                self._label_col,
                sort=self._sort_orig,
                count_cutoff=self._count_cutoff,
                id_ordered=self._id_ordered,
                out_of_order=self._out_of_order,
                stats_valid=self._stats_valid,
                total=total,
                include_nones=self._include_nones,
            )
            # The stats object derives its table names from the handle's name
            # (name_tmp_counts), but the clones follow the reload convention
            # of suffixing the companion names (name_counts_tmp), since that
            # is what the swap and cleanup machinery renames; repoint it.
            staged.stats.counts = self.stats.counts + suffix
            staged.stats.stats = self.stats.stats + suffix
            # What the live table held when the copy was taken, for the
            # commit-time check that it did not change during staging
            staged._staged_source_count = total
            staged._staged_source_max_id = source_max_id
            for methodname in self._staged_unsupported:
                setattr(staged, methodname, self._staged_blocked(methodname))
            # The staged table is already a scratch copy, so updating it from
            # a file edits it directly rather than cloning it again (rewrite
            # goes through this path); a nested non-inplace update would also
            # collide with the _tmp naming machinery.
            unstaged_update_from_file = staged.update_from_file

            def update_from_file(datafile, label_col=None, inplace=True, **kwds):
                if not inplace:
                    raise ValueError("update_from_file on a staged table is always performed in place")
                return unstaged_update_from_file(datafile, label_col=label_col, inplace=True, **kwds)

            staged.update_from_file = update_from_file
            # With reindex set, insert_many drops the primary key around the
            # insert and rebuilds it afterward; on the staged handle that
            # pair is blocked (an unpaired drop would survive the swap, see
            # _staged_unsupported), and the copy carries no other indexes to
            # drop, so force it off rather than letting the automatic
            # reindex=None default trip over the block on large inserts.
            unstaged_insert_many = staged.insert_many

            def insert_many(data, resort=False, reindex=None, restat=True):
                return unstaged_insert_many(data, resort=resort, reindex=False, restat=restat)

            staged.insert_many = insert_many
            aborted = False
            return staged, logid
        finally:
            if aborted:
                self._log_db_change("staged", logid=logid, aborted=True)

    def _staged_commit(self, staged, logid):
        """
        Swap the staged copy into place; the second half of ``staged``.

        INPUT:

        - ``staged`` -- the staged table object returned by ``_staged_enter``
        - ``logid`` -- passed on to ``_log_db_change``
        """
        suffix = "_tmp"
        # Drop the staging-only label index before rebuilding the real
        # indexes.  Committed on its own, ahead of the swap transaction below,
        # so that even if the drift check refuses the swap (rolling that
        # transaction back), the staged copy is left without this artifact:
        # _swap renames indexes but does not drop them, so a leftover here
        # would otherwise ride into the live table when the caller forces the
        # swap with the staged_force_swap recovery named in the error (which
        # drops it again itself, but only staged tables adopted from a session
        # that never reached this point still carry it).
        if self._label_col is not None and self._label_col != "id":
            with DelayCommit(self, silence=True):
                self._execute(SQL("DROP INDEX IF EXISTS {0}").format(
                    Identifier(self.search_table + suffix + "_staged_label")))
        aborted = True
        try:
            with DelayCommit(self, silence=True):
                # Build the indexes and constraints recorded in meta_indexes
                # and meta_constraints, as reload does just before its swap
                self.restore_indexes(suffix=suffix)
                self._create_counts_indexes(suffix=suffix)
                # Backstop against writes that reached the live table anyway
                # (raw SQL bypasses the guard in _check_locks): if the row
                # count or the maximum id moved since the copy was taken,
                # the swap would silently discard those rows into the _old
                # backup.  Checked after the index builds to keep the window
                # between check and swap small.  In-place updates change
                # neither number and are not caught here; the _check_locks
                # guard is the primary defense.
                live_count = self.stats._slow_count({}, record=False)
                live_max_id = self.max_id()
                if (live_count != staged._staged_source_count
                        or live_max_id != staged._staged_source_max_id):
                    name = self.search_table
                    raise RuntimeError(
                        "The live table %s changed during staging: it held "
                        "%s rows with max id %s when the staged copy was taken, "
                        "but now holds %s rows with max id %s.  Refusing to "
                        "swap, since the swap would discard those changes.  The "
                        "staged tables are kept: run db.%s.drop_tmp() to discard "
                        "the staged writes, or -- if instead you want the staged "
                        "copy to win, discarding those concurrent changes -- "
                        "swap it in with db.%s.staged_force_swap()."
                        % (
                            name,
                            staged._staged_source_count,
                            staged._staged_source_max_id,
                            live_count,
                            live_max_id,
                            name,
                            name,
                        )
                    )
                self._staged_swap_in(staged._out_of_order)
            aborted = False
        finally:
            self._log_db_change("staged", logid=logid, aborted=aborted)

    def _staged_swap_in(self, out_of_order):
        """
        The shared tail of ``_staged_commit`` and ``staged_force_swap``:
        transfer the flags to the live meta_tables row and swap the staged
        tables into place.

        INPUT:

        - ``out_of_order`` -- whether the live table must be marked out of
          order, because the staged writes broke (or, in the forced case,
          may have broken) the id ordering.
        """
        # The staged writes could not update the meta_tables row (it is
        # keyed on the live name), so transfer the order flag and invalidate
        # the statistics: the swapped-in counts and stats tables are empty,
        # not refreshed
        if out_of_order:
            self._break_order()
        self._break_stats()
        # reload_final_swap backs the live tables up under _old<n>, renames
        # the _tmp ones into place, recounts the total and replaces the
        # table object held by the database
        self.reload_final_swap(tables=self._staged_tables(), ordered=False)

    def staged_force_swap(self):
        """
        Adopt a staged copy whose commit never happened: build its indexes
        and swap it into place, finalized exactly as a clean ``staged`` exit
        would have.

        This is the recovery named in the error raised when a staged commit
        refuses to swap because the live table changed during staging; it
        also adopts staged tables left behind by a session that died before
        its commit ran.  Unlike the commit it performs **no** drift check:
        the staged copy wins, and whatever the live table holds is backed up
        under ``_old<n>`` (so ``reload_revert`` still undoes this).

        The staged handle that knew whether the staged writes preserved the
        id ordering is gone, so the table is conservatively marked out of
        order -- always safe, it merely disables a sort optimization; run
        ``resort`` afterward to restore id order.  As with a normal staged
        commit the statistics are invalidated, and the table object held by
        the database is replaced, so get a fresh reference (``db[name]``)
        afterward.
        """
        suffix = "_tmp"
        missing = [
            table + suffix
            for table in self._staged_tables()
            if not self._table_exists(table + suffix)
        ]
        if missing:
            raise ValueError(
                "Cannot force a staged swap on %s: %s missing"
                % (self.search_table, ", ".join(missing))
            )
        with DelayCommit(self, silence=True):
            # The staging-only label index: a commit that got as far as its
            # drift check has already dropped it, but staged tables left by
            # a session that died before commit still carry it, and _swap
            # renames indexes rather than dropping them
            if self._label_col is not None and self._label_col != "id":
                self._execute(SQL("DROP INDEX IF EXISTS {0}").format(
                    Identifier(self.search_table + suffix + "_staged_label")))
            # The index builds from a refused commit were rolled back along
            # with its transaction, so build them all here, as the commit
            # itself would have
            self.restore_indexes(suffix=suffix)
            self._create_counts_indexes(suffix=suffix)
            self._staged_swap_in(out_of_order=True)

    def _staged_abort(self, logid):
        """
        Discard the staged copy; the exception half of ``staged``.
        """
        # A failed write can leave the connection in an aborted transaction;
        # clear it so that the drops below can run
        self.conn.rollback()
        self.drop_tmp()
        self._log_db_change("staged", logid=logid, aborted=True)

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
        resort=False,
        reindex=None,
        restat=True,
        **kwds
    ):
        """
        Efficiently copy data from files into this table.

        INPUT:

        - ``searchfile`` -- a string, the file with data for the search table
        - ``resort`` -- whether to sort the ids after copying in the data.  Only relevant for tables that are id_ordered.
        - ``reindex`` -- whether to drop the indexes before importing data and rebuild them afterward.
            If the number of rows is a substantial fraction of the size of the table, this will be faster.
            Defaults to true when the number of rows added is more than 1000
        - ``restat`` -- whether to recreate statistics after reloading.
        - ``kwds`` -- passed on to the ``COPY`` command.  Cannot include "columns".

        .. NOTE:

            If the search file contains ids, they should be contiguous,
            starting immediately after the current max id (or at 1 if empty).
        """
        self._check_file_input(searchfile, kwds)
        logid = self._check_locks("copy_from", datafile=searchfile)
        aborted = True
        search_count = -1
        try:
            with DelayCommit(self, silence=True):
                if reindex is None:
                    rowcount = 0
                    with open(searchfile) as F:
                        for line in F:
                            rowcount += 1
                    reindex = rowcount > 1003 # 3 header lines
                if reindex:
                    self.drop_indexes(permanent=False)
                now = time.time()
                search_addid, search_count = self._copy_from(
                    searchfile, self.search_table, self.search_cols, True, kwds
                )
                print("Loaded data into %s in %.3f secs" % (self.search_table, time.time() - now))
                self._break_order()
                if self._id_ordered and resort:
                    self.resort()
                if reindex:
                    self.restore_indexes()
                self._break_stats()
                if self.stats.saving and restat:
                    self.stats.refresh_stats(total=False)
                self.stats._update_total(search_count)
            aborted = False
        finally:
            self._log_db_change("copy_from", logid=logid, aborted=aborted, nrows=search_count)

    def copy_to(
        self,
        searchfile,
        countsfile=None,
        statsfile=None,
        indexesfile=None,
        constraintsfile=None,
        metafile=None,
        columns=None,
        query=None,
        include_id=True,
        **kwds
    ):
        """
        Efficiently copy data from the database to a file.

        The result will have one line per row of the table, separated by | characters and in order
        given by self.search_cols.

        INPUT:

        - ``searchfile`` -- a string, the filename to write data into for the search table
        - ``countsfile`` -- a string (optional), the filename to write the data into for the counts table.
        - ``statsfile`` -- a string (optional), the filename to write the data into for the stats table.
        - ``indexesfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_indexes table.
        - ``constraintsfile`` -- a string (optional), the filename to write the data into for the corresponding rows of the meta_constraints table.
        - ``metafile`` -- a string (optional), the filename to write the data into for the corresponding row of the meta_tables table.
        - ``columns`` -- a list of column names to export
        - ``query`` -- a query dictionary
        - ``include_id`` -- whether to include the id column in the output file
        - ``kwds`` -- may contain ``sep`` and ``null`` options for the COPY.
            Cannot include "columns".
        """
        self._check_file_input(searchfile, kwds)
        sep = kwds.pop("sep", "|")
        null = kwds.pop("null", r"\N")

        search_cols = [col for col in self.search_cols if columns is None or col in columns]
        if columns is not None and len(columns) != len(search_cols):
            raise ValueError("Invalid columns %s" % (", ".join([col for col in columns if col not in search_cols])))
        tabledata = [
            # tablename, cols, addid, write_header, filename
            (self.search_table, search_cols, include_id, True, searchfile),
        ]
        if self.stats.saving:
            tabledata.extend([
                (self.stats.counts, _counts_cols, False, False, countsfile),
                (self.stats.stats, _stats_cols, False, False, statsfile),
            ])

        # The columns this database actually has (an older-format database
        # lacks the columns added by newer formats; see MetadataFormats.md)
        metadata = [
            ("meta_indexes", "table_name",
             _meta_cols_types_jsonb_idx("meta_indexes", self._db._meta_format)[0], indexesfile),
            ("meta_constraints", "table_name",
             _meta_cols_types_jsonb_idx("meta_constraints", self._db._meta_format)[0], constraintsfile),
            ("meta_tables", "name",
             _meta_cols_types_jsonb_idx("meta_tables", self._db._meta_format)[0], metafile),
        ]
        print("Exporting %s..." % (self.search_table))
        now_overall = time.time()
        with DelayCommit(self):
            for table, cols, addid, write_header, filename in tabledata:
                if filename is None:
                    continue
                now = time.time()
                if addid:
                    cols = ["id"] + cols
                if kwds:
                    raise TypeError("Unsupported copy_to options: %s" % ", ".join(kwds))
                cur = self._db._cursor()
                with open(filename, "w") as F:
                    try:
                        if write_header:
                            self._write_header_lines(F, cols, include_id=include_id, sep=sep)
                        options = []
                        if sep != "\t":
                            options.append(SQL("DELIMITER {0}").format(Literal(sep)))
                        if null != r"\N":
                            options.append(SQL("NULL {0}").format(Literal(null)))
                        if options:
                            sep_clause = SQL(" ({0})").format(SQL(", ").join(options))
                        else:
                            sep_clause = SQL("")
                        if query is None:
                            copyto = SQL("COPY {0} ({1}) TO STDOUT{2}").format(
                                Identifier(table),
                                SQL(", ").join(map(Identifier, cols)),
                                sep_clause,
                            )
                        else:
                            qstr, values = self._build_query(query, sort=[])
                            scols = SQL(", ").join(map(IdentifierWrapper, cols))
                            selecter = SQL("SELECT {0} FROM {1}{2}").format(scols, IdentifierWrapper(table), qstr)
                            copyto = SQL("COPY ({0}) TO STDOUT{1}").format(selecter, sep_clause)
                            # COPY doesn't support parameters, so interpolate client-side
                            copyto = SQL(self._mogrify(copyto, values))
                        with cur.copy(copyto) as copy:
                            for data in copy:
                                F.write(bytes(data).decode())
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

    def set_sort(self, sort, id_ordered=True, resort=True):
        """
        Change the default sort order for this table

        INPUT:

        - ``sort`` -- a list of columns or pairs (col, direction) where direction is 1 or -1.
        - ``id_ordered`` -- the value ``id_ordered`` to set when changing the sort to a non ``None`` value.
          If ``sort`` is ``None``, then ``id_ordered`` will be set to ``False``.
        - ``resort`` -- whether to resort the table ids when changing the sort to a non None value
          and if id_ordered=True
        """
        self._set_sort(sort)
        with DelayCommit(self, silence=True):
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
            self._log_db_change("set_sort", sort=sort)

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
        This stub defines the API for getting and setting the table description.
        In the LMFDB, this is implemented using the knowl table, but we do nothing by default.

        INPUT:

        - ``table_description`` -- if provided, set the description to this value.
          If not, return the current description.
        """
        pass

    def column_description(self, col=None, description=None, drop=False):
        """
        This stub defines the API for getting, setting and deleting column descriptions.
        In the LMFDB, this is implemented using the knowl table, but we do nothing by default.

        INPUT:

        - ``col`` -- the name of the column.  If None, ``description`` should be a dictionary
          with keys equal to the column names.

        - ``description`` -- if provided, set the column description to this value.
          If not, return the current description.

        - ``drop`` -- if ``True``, delete the column from the description dictionary in
          preparation for dropping the column.
        """
        pass

    def add_column(self, name, datatype, description=None, label=False, force_description=False):
        """
        Adds a column to this table.

        INPUT:

        - ``name`` -- a string giving the column name.  Must not be a current column name.
        - ``datatype`` -- a valid Postgres data type (e.g. 'numeric' or 'text')
        - ``description`` -- a string giving the description of the column
        - ``label`` -- whether this column should be set as the label column for this table
          (used in the ``lookup`` method for example).
        """
        if name in self.search_cols:
            raise ValueError("%s already has column %s" % (self.search_table, name))
        if force_description and description is None:
            raise ValueError("You must provide a description of this column")
        elif description is None:
            description = ""
        logid = self._check_locks("add_column")
        aborted = True
        try:
            self._check_col_datatype(datatype)
            self.col_type[name] = datatype
            table = self.search_table
            with DelayCommit(self, silence=True):
                # Since we have run the datatype through the whitelist,
                # the following string substitution is safe
                modifier = SQL("ALTER TABLE {0} ADD COLUMN {1} %s" % datatype).format(
                    Identifier(table), Identifier(name)
                )
                self._execute(modifier)
                if name != "id":
                    self.search_cols.insert(bisect(self.search_cols, name), name)
                if label:
                    self.set_label(name)
                self.column_description(name, description)
                self._db._notify_schema_change(self.search_table)  # rides this transaction
            aborted = False
        finally:
            self._log_db_change("add_column", logid=logid, aborted=aborted, name=name, datatype=datatype)

    def drop_column(self, name, force=False):
        """
        Drop a column and any data stored in it.

        INPUT:

        - ``name`` -- the name of the column
        - ``force`` -- if False, will ask for confirmation
        """
        logid = self._check_locks("drop_column")
        aborted = True

        try:
            if not force:
                ok = input("Are you sure you want to drop %s? (y/N) " % name)
                if not (ok and ok[0] in ["y", "Y"]):
                    return
            if name in self._sort_keys:
                raise ValueError(
                    "Sorting for %s depends on %s; change default sort order with set_sort() before dropping column"
                    % (self.search_table, name)
                )
            with DelayCommit(self, silence=True):
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
                else:
                    raise ValueError("%s is not a column of %s" % (name, self.search_table))
                modifier = SQL("ALTER TABLE {0} DROP COLUMN {1}").format(Identifier(table), Identifier(name))
                self._execute(modifier)
                self.col_type.pop(name, None)
                self._db._notify_schema_change(self.search_table)  # rides this transaction
            print("Column %s dropped" % (name))
            aborted = False
        finally:
            self._log_db_change("drop_column", logid=logid, aborted=aborted, name=name)

    def _log_db_change(self, operation, logid=None, aborted=False, **data):
        """
        Log changes to search tables.

        INPUT:

        - ``operation`` -- a string, explaining what operation was performed
        - ``**data`` -- any additional information to install in the logging table (will be stored as a json dictionary)
        """
        self._db._log_db_change(operation, tablename=self.search_table, logid=logid, aborted=aborted, **data)

    def set_importance(self, importance):
        """
        Production tables are marked as important so that they can't be accidentally dropped.

        Use this method to mark a table important or not important.
        """
        updater = SQL("UPDATE meta_tables SET important = %s WHERE name = %s")
        self._execute(updater, [importance, self.search_table])


class StagedWriteContext():
    """
    Context manager for staging writes to a copy of a search table, swapping
    the copy into place on a clean exit and dropping it on an exception.

    Returned by the ``staged`` method on ``PostgresTable``; see its
    documentation for details.
    """

    def __init__(self, table):
        self.table = table

    def __enter__(self):
        self.staged, self.logid = self.table._staged_enter()
        return self.staged

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.table._staged_commit(self.staged, self.logid)
        else:
            self.table._staged_abort(self.logid)
        return False
