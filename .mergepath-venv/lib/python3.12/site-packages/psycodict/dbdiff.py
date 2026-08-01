# -*- coding: utf-8 -*-
"""
Compare the search tables of two psycodict databases.

The LMFDB runs the same schema in several places (beta, production, private
development copies), and the copies drift: a table is created in one place
and not the other, a column is added or retyped on beta only, data is pushed
to one server and not the other.  The functions here detect that drift; see
LMFDB/lmfdb#5900 for the motivating incident, where ``mf_newspaces`` ended up
with different schemas on beta and production.

The entry points are the ``compare`` and ``show_differences`` methods of
``PostgresDatabase``, which delegate to :func:`compare_databases` and
:func:`format_differences` here.  Everything runs read-only on both sides:
only SELECT statements are issued, and unlike ``table.count()`` (which may
cache the counts it computes when count saving is enabled), nothing is ever
recorded in the counts tables or in meta_tables of either database, so it is
safe to point at a production server.

Comparisons are based on fresh queries rather than on the schema cached on
the ``PostgresDatabase`` objects at connection time, so long-lived
connections do not report stale differences.
"""

from psycopg.sql import SQL, Identifier

# The columns of meta_tables that are compared for tables present in both
# databases (in this order).  The remaining columns are deliberately left
# out: total is reported through row_counts instead, out_of_order and
# stats_valid describe transient operational state rather than schema, and
# important is administrative.
_meta_compared = ("label_col", "sort", "id_ordered", "include_nones", "count_cutoff")


def _meta_rows(db):
    """
    The comparable part of meta_tables, as a dictionary of dictionaries.

    INPUT:

    - ``db`` -- a ``PostgresDatabase`` instance

    OUTPUT:

    A dictionary indexed by search table name whose values are dictionaries
    with the keys in ``_meta_compared`` together with ``total`` (the cached
    row count that psycodict's write paths maintain).
    """
    selecter = SQL("SELECT {0}, total FROM meta_tables").format(
        SQL(", ").join(Identifier(col) for col in ("name",) + _meta_compared)
    )
    return {
        rec[0]: dict(zip(_meta_compared + ("total",), rec[1:]))
        for rec in db._execute(selecter)
    }


def _column_types(db, names):
    """
    The column names and types of the given tables, freshly queried.

    INPUT:

    - ``db`` -- a ``PostgresDatabase`` instance
    - ``names`` -- a container of table names to report on

    OUTPUT:

    A dictionary indexed by table name whose values are dictionaries mapping
    column name to the full rendered postgres type (as a string, e.g.
    ``"numeric[]"`` or ``"character varying(16)"``).  Tables that no longer
    exist in pg_class (dropped out from under meta_tables) are absent.

    Types are rendered with ``format_type`` from the catalog rather than read
    off information_schema's ``udt_name``, because ``udt_name`` drops type
    modifiers: ``numeric(10,2)`` and ``numeric(20,4)`` would both come back
    as ``numeric`` and precision or scale drift between the two databases
    would go unreported.  information_schema's separate modifier columns
    (character_maximum_length and friends) would need per-type reassembly and
    are NULL for arrays, while ``format_type`` on ``pg_attribute`` is exactly
    the canonical human-readable rendering psql's ``\\d`` shows, and for
    modifier-less columns it matches the ``udt_name::regtype`` strings this
    function used to return.
    """
    names = set(names)
    cur = db._execute(SQL(
        "SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod) "
        "FROM pg_attribute a "
        "JOIN pg_class c ON a.attrelid = c.oid "
        "JOIN pg_namespace n ON c.relnamespace = n.oid "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' "
        "AND a.attnum > 0 AND NOT a.attisdropped"
    ))
    columns = {}
    for table_name, column_name, typ in cur:
        if table_name in names:
            columns.setdefault(table_name, {})[column_name] = typ
    return columns


def _exact_count(db, name):
    """
    The exact number of rows in a table, via SELECT COUNT(*).
    """
    selecter = SQL("SELECT COUNT(*) FROM {0}").format(Identifier(name))
    return db._execute(selecter).fetchone()[0]


def _null_counts(db, name, cols):
    """
    The number of NULL entries in each of the given columns of a table.

    All columns are counted in a single scan of the table, using
    ``COUNT(*) FILTER (WHERE col IS NULL)``.

    OUTPUT:

    A dictionary mapping each column in ``cols`` to its number of NULLs.
    """
    selecter = SQL("SELECT {0} FROM {1}").format(
        SQL(", ").join(
            SQL("COUNT(*) FILTER (WHERE {0} IS NULL)").format(Identifier(col))
            for col in cols
        ),
        Identifier(name),
    )
    return dict(zip(cols, db._execute(selecter).fetchone()))


def compare_databases(self_db, other_db, tables=None, row_counts=True, null_counts=False, exact=False):
    """
    Compute the differences between the search tables of two databases.

    This is the implementation of ``PostgresDatabase.compare``; see the
    docstring there for the interface, options and cost caveats.

    OUTPUT:

    A dictionary with keys

    - ``only_in_self``, ``only_in_other`` -- sorted lists of the names of
      search tables (rows of meta_tables) present in only one database
    - ``schema`` -- a dictionary indexed by the names of tables present in
      both databases whose schemas differ.  Each value is a dictionary
      containing whichever of the following are nonempty:

      - ``only_in_self``, ``only_in_other`` -- sorted lists of pairs
        ``(col, type)`` for columns present on one side only
      - ``type_changed`` -- a sorted list of triples ``(col, type_self,
        type_other)`` for columns whose postgres types disagree.  Types are
        rendered in full, including any modifiers, so ``numeric(10,2)`` vs
        ``numeric(20,4)`` is a difference
      - ``meta_changed`` -- a list of triples ``(item, value_self,
        value_other)`` for the meta_tables settings in ``_meta_compared``
        (label_col, sort, id_ordered, include_nones, count_cutoff) that
        disagree

    - ``row_counts`` (if requested) -- a dictionary ``{table: (rows_self,
      rows_other)}``, restricted to the tables where the counts differ
    - ``null_counts`` (if requested) -- a dictionary ``{table: {col:
      (nulls_self, nulls_other)}}`` over the columns shared by both sides
      (id excluded), restricted to the columns where the counts differ
    """
    self_meta = _meta_rows(self_db)
    other_meta = _meta_rows(other_db)
    self_names = set(self_meta)
    other_names = set(other_meta)
    if tables is None:
        requested = self_names | other_names
    else:
        if isinstance(tables, str):
            tables = [tables]
        requested = set(tables)
        missing = requested - self_names - other_names
        if missing:
            raise ValueError(
                "%s not a search table in either database" % (", ".join(sorted(missing)))
            )
    shared = sorted(requested & self_names & other_names)
    diff = {
        "only_in_self": sorted(requested & self_names - other_names),
        "only_in_other": sorted(requested & other_names - self_names),
        "schema": {},
    }
    self_cols = _column_types(self_db, shared)
    other_cols = _column_types(other_db, shared)
    for name in shared:
        scols = self_cols.get(name, {})
        ocols = other_cols.get(name, {})
        entry = {}
        only_self = sorted(set(scols) - set(ocols))
        only_other = sorted(set(ocols) - set(scols))
        changed = sorted(col for col in set(scols) & set(ocols) if scols[col] != ocols[col])
        if only_self:
            entry["only_in_self"] = [(col, scols[col]) for col in only_self]
        if only_other:
            entry["only_in_other"] = [(col, ocols[col]) for col in only_other]
        if changed:
            entry["type_changed"] = [(col, scols[col], ocols[col]) for col in changed]
        meta_changed = [
            (item, self_meta[name][item], other_meta[name][item])
            for item in _meta_compared
            if self_meta[name][item] != other_meta[name][item]
        ]
        if meta_changed:
            entry["meta_changed"] = meta_changed
        if entry:
            diff["schema"][name] = entry
    if row_counts:
        diff["row_counts"] = {}
        for name in shared:
            if exact:
                counts = (_exact_count(self_db, name), _exact_count(other_db, name))
            else:
                counts = (self_meta[name]["total"], other_meta[name]["total"])
            if counts[0] != counts[1]:
                diff["row_counts"][name] = counts
    if null_counts:
        diff["null_counts"] = {}
        for name in shared:
            cols = sorted(
                col
                for col in set(self_cols.get(name, {})) & set(other_cols.get(name, {}))
                if col != "id"
            )
            if not cols:
                continue
            self_nulls = _null_counts(self_db, name, cols)
            other_nulls = _null_counts(other_db, name, cols)
            changed = {
                col: (self_nulls[col], other_nulls[col])
                for col in cols
                if self_nulls[col] != other_nulls[col]
            }
            if changed:
                diff["null_counts"][name] = changed
    return diff


def _describe(db, fallback):
    """
    A short human-readable label for one side of the comparison.
    """
    if db is None:
        return fallback
    info = db.conn.info
    return "%s (%s:%s/%s)" % (fallback, info.host, info.port, info.dbname)


def format_differences(diff, self_db=None, other_db=None):
    """
    Render the output of :func:`compare_databases` as a readable report.

    INPUT:

    - ``diff`` -- a dictionary as returned by :func:`compare_databases`
    - ``self_db``, ``other_db`` -- optionally, the compared
      ``PostgresDatabase`` instances, used to label the two sides with their
      connection details rather than just "self" and "other"

    OUTPUT:

    A string; ``"No differences found"`` when every section is empty.
    Sections without differences are omitted.
    """
    self_desc = _describe(self_db, "self")
    other_desc = _describe(other_db, "other")
    lines = []
    for side, desc in [("only_in_self", self_desc), ("only_in_other", other_desc)]:
        if diff[side]:
            lines.append("Tables only in %s:" % desc)
            lines.extend("    %s" % name for name in diff[side])
    if diff["schema"]:
        lines.append("Schema differences:")
        for name in sorted(diff["schema"]):
            entry = diff["schema"][name]
            lines.append("    %s:" % name)
            for side, desc in [("only_in_self", self_desc), ("only_in_other", other_desc)]:
                for col, typ in entry.get(side, []):
                    lines.append("        column only in %s: %s (%s)" % (desc, col, typ))
            for col, styp, otyp in entry.get("type_changed", []):
                lines.append("        type of %s changed: %s vs %s" % (col, styp, otyp))
            for item, sval, oval in entry.get("meta_changed", []):
                lines.append("        %s changed: %s vs %s" % (item, sval, oval))
    if diff.get("row_counts"):
        lines.append("Row count differences:")
        for name in sorted(diff["row_counts"]):
            lines.append("    %s: %s vs %s" % ((name,) + diff["row_counts"][name]))
    if diff.get("null_counts"):
        lines.append("Null count differences:")
        for name in sorted(diff["null_counts"]):
            for col in sorted(diff["null_counts"][name]):
                lines.append(
                    "    %s.%s: %s vs %s" % ((name, col) + diff["null_counts"][name][col])
                )
    if not lines:
        return "No differences found"
    return "\n".join(lines)
