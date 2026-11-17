"""
Zenodo deposit metadata and generated documentation (README, HTML
description) for LMFDB records.

Table and column descriptions are pulled from the knowl-backed
``description()`` / ``column_description()`` methods of
``LMFDBSearchTable`` when a database object is available; all lookups
degrade gracefully so packaging also works without database access
(placeholders are used).
"""

import html
from datetime import datetime, timezone

# Decided by the managing editors (2026-07-18)
LICENSE_ID = "cc-by-sa-4.0"  # listed at zenodo.org/api/vocabularies/licenses
CREATORS = [{"name": "The LMFDB Collaboration"}]
DEFAULT_COMMUNITY = "lmfdb"
LMFDB_URL = "https://www.lmfdb.org"

MISSING = "(description not available)"


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def deposit_metadata(title, description_html, version, keywords=None,
                     community=DEFAULT_COMMUNITY, related_url=None,
                     notes=None):
    """
    The ``{"metadata": ...}`` payload for the Zenodo deposit API.

    - ``version`` -- the record version being published, e.g. ``"1.4"``
    - ``related_url`` -- e.g. ``https://www.lmfdb.org/api/nf_fields``
    - ``notes`` -- description of the changes in this version
    """
    md = {
        "upload_type": "dataset",
        "publication_date": _today(),
        "title": title,
        "creators": list(CREATORS),
        "description": description_html,
        "license": LICENSE_ID,
        "access_right": "open",
        "version": version,
        "keywords": ["LMFDB", "L-functions and modular forms database",
                     "number theory"] + list(keywords or []),
    }
    if community:
        md["communities"] = [{"identifier": community}]
    if related_url:
        md["related_identifiers"] = [
            {"identifier": related_url, "relation": "isSupplementTo"}]
    if notes:
        md["notes"] = notes
    return {"metadata": md}


def _table_info(db, tablename):
    """
    Best-effort collection of (description, [(col, type, description)], nrows)
    for a table; every piece may come back as a placeholder.
    """
    desc, cols, nrows = MISSING, [], None
    if db is None:
        return desc, cols, nrows
    try:
        table = db[tablename]
    except Exception:
        return desc, cols, nrows
    try:
        desc = table.description() or MISSING
    except Exception:
        pass
    try:
        coldesc = table.column_description()
    except Exception:
        coldesc = {}
    try:
        # extra_cols only exists before psycodict 1.0
        for col in (["id"] + list(table.search_cols)
                    + list(getattr(table, "extra_cols", []))):
            typ = table.col_type.get(col, "")
            cols.append((col, typ, coldesc.get(col, "")))
    except Exception:
        pass
    try:
        nrows = table.stats.quick_count({})
    except Exception:
        pass
    return desc, cols, nrows


def table_title(tablename):
    return "LMFDB table %s" % tablename


# Records are published before the LMFDB data version that includes them is
# assigned, so they point to the version history rather than naming it.
VERSIONS_NOTE = ("The LMFDB versions that include this record version are "
                 "listed at %s/version and in the LMFDB version registry "
                 "record on Zenodo." % LMFDB_URL)


def table_description_html(db, tablename, version, nrows=None, notes=None):
    """
    HTML description for a table's Zenodo record (shown on the record page).

    - ``version`` -- the record version, e.g. ``"1.4"``
    - ``notes`` -- description of the changes in this version
    """
    desc, cols, dbrows = _table_info(db, tablename)
    nrows = nrows if nrows is not None else dbrows
    e = html.escape
    parts = [
        "<p>Version %s of the search table <code>%s</code> of the L-functions "
        "and modular forms database (<a href=\"%s\">LMFDB</a>), archived from "
        "the production database.  %s</p>"
        % (e(str(version)), e(tablename), LMFDB_URL, e(VERSIONS_NOTE)),
    ]
    if notes:
        parts.append("<p><b>Changes in this version:</b> %s</p>" % e(notes))
    parts.append("<p>%s</p>" % e(desc))
    if nrows is not None:
        parts.append("<p>Number of rows: %s.</p>" % nrows)
    parts.append(
        "<p>The record contains the table's data (and, where present, its "
        "extra table, statistics and counts) as compressed "
        "<code>|</code>-separated files, together with the index, constraint "
        "and schema information needed to reconstruct a fully functional "
        "copy with <a href=\"https://github.com/roed314/psycodict\">"
        "psycodict</a>'s <code>reload_all</code>.  See README.md and "
        "MANIFEST.json inside the record for details, and "
        "<code>%s_sample.md</code> for a preview of the first rows.</p>"
        % e(tablename))
    if cols:
        rows = "".join(
            "<tr><td><code>%s</code></td><td><code>%s</code></td><td>%s</td></tr>"
            % (e(c), e(t), e(d)) for c, t, d in cols)
        parts.append(
            "<p>Columns:</p><table><tr><th>column</th><th>type</th>"
            "<th>description</th></tr>%s</table>" % rows)
    return "\n".join(parts)


RESTORE_INSTRUCTIONS = """\
## Restoring

The files in this record are exactly what the LMFDB's own reload machinery
consumes.  To rebuild the table in a PostgreSQL database:

1. Install PostgreSQL and [psycodict](https://github.com/roed314/psycodict)
   (`pip install psycodict`), or a full [LMFDB](https://github.com/LMFDB/lmfdb)
   installation.
2. Download the files of this record into a folder and decompress them
   (`zstd -d *.zst`; for split files first `cat NAME.zst.part* > NAME.zst`,
   see MANIFEST.json).  The folder must not contain other `.txt` files:
   `reload_all` loads every one of them as a table.
3. From an LMFDB installation, run

       from lmfdb import db
       db.reload_all("/path/to/folder", adjust_schema=True)

   which will create the table (using the `_meta.txt` schema information) if
   it does not already exist, load the data, and rebuild indexes and
   constraints.

MANIFEST.json records sizes, md5 and sha256 checksums of every file, both
compressed and uncompressed, plus row counts.
"""


def table_readme(db, tablename, version, date=None, notes=None):
    """
    Markdown README.md content for a table record; the arguments are as for
    ``table_description_html``.
    """
    desc, cols, nrows = _table_info(db, tablename)
    date = date or _today()
    lines = [
        "# LMFDB table `%s`, version %s" % (tablename, version),
        "",
        "Archived from the production database of the [LMFDB](%s) on %s.  %s"
        % (LMFDB_URL, date, VERSIONS_NOTE),
        "",
    ]
    if notes:
        lines += ["Changes in this version: %s" % notes, ""]
    lines += [
        desc,
        "",
    ]
    if nrows is not None:
        lines += ["Number of rows: %s." % nrows, ""]
    lines += [
        "Live version of this data: %s/api/%s" % (LMFDB_URL, tablename),
        "",
        "License: CC BY-SA 4.0.  Please cite this record (see the Zenodo "
        "citation box) and the LMFDB (https://www.lmfdb.org/citation) when "
        "using this data.",
        "",
        RESTORE_INSTRUCTIONS,
    ]
    if cols:
        lines += [
            "## Columns",
            "",
            "| column | type | description |",
            "|---|---|---|",
        ]
        for c, t, d in cols:
            lines.append("| `%s` | `%s` | %s |"
                         % (c, t, d.replace("|", "\\|").replace("\n", " ")))
        lines.append("")
    return "\n".join(lines)


def knowls_description_html():
    return (
        "<p>The knowledge database (knowls) of the L-functions and modular "
        "forms database (<a href=\"%s\">LMFDB</a>): the mathematical "
        "background, definitions and descriptions displayed throughout the "
        "site, including the table and column descriptions of the archived "
        "search tables.</p>"
        "<p>Unlike the search tables, knowls are edited live on the website, "
        "so this record is refreshed on every LMFDB data push.  %s</p>"
        % (LMFDB_URL, html.escape(VERSIONS_NOTE)))


def knowls_readme(date=None):
    return "\n".join([
        "# LMFDB knowledge database (knowls)",
        "",
        "Archived from the production database of the [LMFDB](%s) on %s.  %s"
        % (LMFDB_URL, date or _today(), VERSIONS_NOTE),
        "",
        "Contains the tables `kwl_knowls` (current knowls, including table "
        "and column descriptions) and `kwl_deleted` (deleted knowls), each "
        "as a compressed `|`-separated dump with a header (column names, "
        "column types, blank line) followed by PostgreSQL COPY rows, plus "
        "`*_schema.sql` files with CREATE TABLE statements.",
        "",
        "License: CC BY-SA 4.0.",
        "",
        "## Restoring",
        "",
        "Create the tables using the `*_schema.sql` files, strip the three "
        "header lines, and load with `COPY ... FROM ... (DELIMITER '|')`.",
        "",
    ])


def registry_description_html():
    return (
        "<p>The version registry of the L-functions and modular forms "
        "database (<a href=\"%s\">LMFDB</a>).  Each version of this record "
        "corresponds to an LMFDB version and contains a JSON file mapping "
        "every archived search table to the Zenodo record and version "
        "holding its data at that LMFDB version, together with the version "
        "history (including the git commits of the website frontend).  See "
        "<a href=\"%s/version\">%s/version</a> for the human-readable "
        "version history.</p>" % (LMFDB_URL, LMFDB_URL, LMFDB_URL))
