"""
Zenodo deposit metadata and generated documentation (README, HTML
description) for LMFDB records.

Table and column descriptions are pulled from the knowl-backed
``description()`` / ``column_description()`` methods of
``LMFDBSearchTable`` when a database object is available; all lookups
degrade gracefully so packaging also works without database access
(placeholders are used).  Knowls are written in Markdown with the LMFDB's
template macros; ``render_knowl`` turns them into plain Markdown for the
READMEs, and the record pages get them as HTML.
"""

import ast
import html
import re
from datetime import datetime, timezone

# Decided by the managing editors (2026-07-18)
LICENSE_ID = "cc-by-sa-4.0"  # listed at zenodo.org/api/vocabularies/licenses
CREATORS = [{"name": "The LMFDB Collaboration"}]
DEFAULT_COMMUNITY = "lmfdb"
LMFDB_URL = "https://www.lmfdb.org"
KNOWL_URL = LMFDB_URL + "/knowledge/show/%s"

MISSING = "(description not available)"


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def deposit_metadata(title, description_html, version, keywords=None,
                     community=DEFAULT_COMMUNITY, related=(), notes=None):
    """
    The ``{"metadata": ...}`` payload for the Zenodo deposit API.

    - ``version`` -- the record version being published, e.g. ``"1.4"``
    - ``related`` -- ``(identifier, relation)`` pairs, e.g.
      ``("https://www.lmfdb.org/api/nf_fields", "isSupplementTo")``
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
    if related:
        md["related_identifiers"] = [
            {"identifier": ident, "relation": relation}
            for ident, relation in related]
    if notes:
        md["notes"] = notes
    return {"metadata": md}


######################################################################
# Knowl text                                                         #
######################################################################

_MACRO = re.compile(r"\{\{\s*(\w+)\s*\((.*?)\)\s*\}\}", re.S)


def _macro_args(src):
    """The literal arguments of a template macro call, or None."""
    try:
        call = ast.parse("f(%s)" % src, mode="eval").body
        return ([ast.literal_eval(a) for a in call.args],
                {k.arg: ast.literal_eval(k.value) for k in call.keywords})
    except (SyntaxError, ValueError):
        return None


def render_knowl(text):
    """
    Knowl source as plain Markdown: the macros of the LMFDB's knowl
    templates become links to the knowls on www.lmfdb.org (``KNOWL``,
    ``KNOWL_LINK``, ``KNOWL_INC``), external links (``LINK_EXT``) or bold
    terms (``DEFINES``); other templates are left as they are.
    """
    def sub(m):
        name, parsed = m.group(1), _macro_args(m.group(2))
        if parsed is None:
            return m.group(0)
        args, kwds = parsed
        if name in ("KNOWL", "KNOWL_LINK", "KNOWL_INC") and args:
            title = kwds.get("title") or (args[1] if len(args) > 1 else None)
            return "[%s](%s)" % (title or args[0], KNOWL_URL % args[0])
        if name == "LINK_EXT" and len(args) >= 2:
            return "[%s](%s)" % (args[0], args[1])
        if name == "DEFINES" and args:
            return "**%s**" % args[0]
        return m.group(0)
    return _MACRO.sub(sub, text or "")


def _plain(text):
    """Knowl source as one line of plain text (for titles and keywords)."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", render_knowl(text))
    return " ".join(text.replace("*", "").split())


def _html(text, inline=False):
    """
    Knowl source as HTML for a record page; TeX between dollar signs is
    kept as it is, out of reach of the Markdown converter.
    """
    text = render_knowl(text)
    try:
        import markdown
    except ImportError:
        return html.escape(text)
    tex = []

    def hide(m):
        tex.append(m.group(0))
        return "TEXPLACEHOLDER%dX" % (len(tex) - 1)

    out = markdown.markdown(re.sub(r"\$\$.+?\$\$|\$.+?\$", hide, text, flags=re.S))
    out = re.sub(r"TEXPLACEHOLDER(\d+)X",
                 lambda m: html.escape(tex[int(m.group(1))]), out)
    if inline and out.startswith("<p>") and out.endswith("</p>") \
            and out.count("<p>") == 1:
        out = out[3:-4]
    return out


######################################################################
# Search table records                                               #
######################################################################

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
        for col in ["id"] + list(table.search_cols):
            typ = table.col_type.get(col, "")
            cols.append((col, typ, coldesc.get(col, "")))
    except Exception:
        pass
    try:
        nrows = table.stats.quick_count({})
    except Exception:
        pass
    return desc, cols, nrows


def _subject(desc):
    """The table description as a short phrase, or None if it is not one."""
    plain = _plain(desc).rstrip(".")
    if desc == MISSING or not plain or len(plain) > 100 or ". " in plain:
        return None
    return plain


def table_title(db, tablename):
    """E.g. ``Genus 2 curves over Q (LMFDB table g2c_curves)``."""
    subject = _subject(_table_info(db, tablename)[0])
    if subject is None:
        return "LMFDB table %s" % tablename
    return "%s (LMFDB table %s)" % (subject, tablename)


def table_keywords(db, tablename):
    subject = _subject(_table_info(db, tablename)[0])
    return [tablename] + ([subject] if subject else [])


def versions_note(registry_url=None):
    """
    Records are published before the LMFDB data version that includes them
    is assigned, so they point to the version history rather than name it.
    """
    registry = "the LMFDB version registry on Zenodo"
    if registry_url:
        registry = "the [LMFDB version registry](%s)" % registry_url
    return ("The LMFDB versions that include this record version are listed "
            "at %s/version and in %s." % (LMFDB_URL, registry))


def table_description_html(db, tablename, version, nrows=None, notes=None,
                           registry_url=None):
    """
    HTML description for a table's Zenodo record (shown on the record page):
    the mathematics first, then the archive.

    - ``version`` -- the record version, e.g. ``"1.4"``
    - ``notes`` -- description of the changes in this version
    - ``registry_url`` -- link to the version registry, if it exists
    """
    desc, cols, dbrows = _table_info(db, tablename)
    nrows = nrows if nrows is not None else dbrows
    e = html.escape
    parts = [_html(desc)]
    parts.append(
        "<p>Version %s of the search table <code>%s</code> of the L-functions "
        "and modular forms database (<a href=\"%s\">LMFDB</a>), archived from "
        "the production database%s.  %s</p>"
        % (e(str(version)), e(tablename), LMFDB_URL,
           "" if nrows is None else ", with %s rows" % nrows,
           _html(versions_note(registry_url), inline=True)))
    if notes:
        parts.append("<p><b>Changes in this version:</b> %s</p>" % e(notes))
    parts.append(
        "<p>The data is in <code>%s.txt.zst</code>; the other files hold the "
        "statistics, indexes, constraints and metadata that "
        "<a href=\"https://github.com/roed314/psycodict\">psycodict</a> "
        "needs to restore a fully functional copy of the table.  README.md "
        "describes every file, the data format and how to restore it, and "
        "<code>%s_sample.md</code> shows the first rows.</p>"
        % (e(tablename), e(tablename)))
    if cols:
        rows = "".join(
            "<tr><td><code>%s</code></td><td><code>%s</code></td><td>%s</td></tr>"
            % (e(c), e(t), _html(d, inline=True)) for c, t, d in cols)
        parts.append(
            "<p>Columns:</p><table><tr><th>column</th><th>type</th>"
            "<th>description</th></tr>%s</table>" % rows)
    return "\n".join(parts)


def _size(n):
    for unit, scale in [("GB", 10**9), ("MB", 10**6), ("kB", 10**3)]:
        if n >= scale:
            return "%.1f %s" % (n / scale, unit)
    return "%d B" % n


# What each file of a table record is for, by the end of its name
FILE_ROLES = [
    ("_counts.txt", "cached counts of search results"),
    ("_stats.txt", "cached statistics shown on the LMFDB's statistics pages"),
    ("_indexes.txt", "the table's indexes, for restoring"),
    ("_constraints.txt", "the table's constraints, for restoring"),
    ("_meta.txt", "the table's metadata (sort order, label column, ...), "
                  "for restoring"),
    ("_schema.sql", "a CREATE TABLE statement"),
    (".txt", "**the data**"),
]


def file_guide(manifest):
    """Markdown table of the files of a packaged record, from its manifest."""
    lines = ["| file | download | uncompressed | rows | contents |",
             "|---|---|---|---|---|"]
    for art in manifest["artifacts"]:
        src = manifest["source_files"][art["source"]]
        role = next(r for end, r in FILE_ROLES if art["source"].endswith(end))
        names = ([p["name"] for p in art["parts"]] if "parts" in art
                 else [art["name"]])
        rows = src["rows"] if src.get("rows") is not None else ""
        lines.append("| %s | %s | %s | %s | %s |" % (
            "<br>".join("`%s`" % n for n in names), _size(art["size"]),
            _size(src["size"]), rows, role))
    if manifest.get("sample"):
        lines.append("| `%s` | | | | a readable preview of the first rows |"
                     % manifest["sample"])
    lines += ["| `MANIFEST.json` | | | | sizes, row counts and md5/sha256 "
              "checksums of every file, compressed and uncompressed |",
              "| `README.md` | | | | this file |"]
    if any("parts" in art for art in manifest["artifacts"]):
        lines += ["", "Files larger than %s are split into parts: join them "
                  "with `cat NAME.zst.part* > NAME.zst` before decompressing."
                  % _size(max(p["size"] for art in manifest["artifacts"]
                              for p in art.get("parts", [{"size": 0}])))]
    return "\n".join(lines)


DATA_FORMAT = """\
## Reading the data

Each `.txt` file is a PostgreSQL `COPY` dump with `|` as the separator.  The
data file starts with three header lines: the column names, the PostgreSQL
column types, and a blank line; each following line is one row.  In the rows:

- `\\N` is NULL; a backslash escapes a literal `|`, backslash or newline
  (`\\|`, `\\\\`, `\\n`);
- arrays are written `{1,2,3}` (nested `{{1,2},{3,4}}`, strings in double
  quotes when needed), and `jsonb` columns hold JSON;
- `text` columns may contain structured values (lists, polynomials, labels
  of other LMFDB objects): the column descriptions below and the linked
  knowls on www.lmfdb.org explain them.

The files decompress with `zstd -d` (or `gzip -d` for `.gz` files).
"""


# Both routes below restored the sandbox copy of g2c_curves on 2026-11-17
TESTED_WITH = "psycodict 1.0.0rc1 and PostgreSQL 18"


def restore_instructions(tablename, psycodict_version=None):
    """The README's restoring section."""
    return """\
## Restoring

These files are exactly what [psycodict](https://github.com/roed314/psycodict)
(the LMFDB's database layer) writes and reads, so it can rebuild a fully
functional copy of the table, with its indexes, constraints, statistics and
metadata.  You need PostgreSQL and Python%s.

1. Install psycodict: `pip install psycodict`.
2. Create a database: `createdb lmfdb_archive`.
3. Download the files of this record into an otherwise empty folder and
   decompress them there: `zstd -d *.zst`.  The folder must contain no other
   `.txt` files, since every one of them is loaded as a table.
4. In Python:

       from psycodict.database import PostgresDatabase
       from psycodict.statstable import PostgresStatsTable
       PostgresStatsTable.saving = True
       db = PostgresDatabase(dbname="lmfdb_archive", user="YOUR_USER",
                             host="localhost", create=True)
       db.reload_all("/path/to/folder", adjust_schema=True)
       db.%s.count()

   `saving = True` makes psycodict load the counts and statistics files too
   (without it, `reload_all` stops with an error about a missing
   `_counts_tmp` table), `create=True` sets up psycodict's metadata tables
   in a new database, and `adjust_schema=True` creates the table from the
   record's `_meta.txt` and column types.  Use the same connection arguments as `psql` (add
   `password=...` and `port=...` if needed).  psycodict writes a default
   configuration file to `~/.psycodict/config.ini` on first use, and
   `reload_all` keeps the empty table it replaced as `%s_old1`, which can be
   dropped.

Without psycodict, the data file alone loads into plain PostgreSQL: create a
table whose columns are the names on the file's first line, in that order,
with the types on its second line; remove the three header lines; and run
`\\copy TABLE FROM 'FILE' (DELIMITER '|')`.

Both ways were tested with %s.
""" % ("" if not psycodict_version else
       " (the files were written by psycodict %s; use that version or later)"
       % psycodict_version, tablename, tablename, TESTED_WITH)


def table_readme(db, tablename, version, manifest, date=None, notes=None,
                 registry_url=None, psycodict_version=None):
    """
    Markdown README.md content for a table record; ``manifest`` is the
    package's MANIFEST.json, the other arguments are as for
    ``table_description_html``.
    """
    desc, cols, nrows = _table_info(db, tablename)
    nrows = manifest["source_files"].get(tablename + ".txt", {}).get("rows", nrows)
    lines = [
        "# %s, version %s" % (table_title(db, tablename), version),
        "",
        render_knowl(desc),
        "",
        "Version %s of the search table `%s` of the [LMFDB](%s), archived from "
        "its production database on %s%s.  %s"
        % (version, tablename, LMFDB_URL, date or _today(),
           "" if nrows is None else ", with %s rows" % nrows,
           versions_note(registry_url)),
        "",
    ]
    if notes:
        lines += ["Changes in this version: %s" % notes, ""]
    lines += [
        "Browse or search the current data at %s/api/%s." % (LMFDB_URL, tablename),
        "",
        "License: CC BY-SA 4.0.  Please cite this record (see the Zenodo "
        "citation box) and the LMFDB (https://www.lmfdb.org/citation) when "
        "using this data.",
        "",
        "## Files",
        "",
        file_guide(manifest),
        "",
        DATA_FORMAT,
        restore_instructions(tablename, psycodict_version),
    ]
    if cols:
        lines += [
            "## Columns",
            "",
            "| column | type | description |",
            "|---|---|---|",
        ]
        for c, t, d in cols:
            lines.append("| `%s` | `%s` | %s |" % (
                c, t, render_knowl(d).replace("|", "\\|").replace("\n", " ")))
        lines.append("")
    return "\n".join(lines)


######################################################################
# Knowls record                                                      #
######################################################################

KNOWL_MODEL = """\
## What the tables contain

`kwl_knowls` holds every revision of every knowl, one row per saved edit,
not just the text currently shown: there are usually several rows per `id`,
distinguished by `timestamp`.  Its codes:

- `status`: 1 reviewed, 0 beta (written but not yet reviewed), -1 in
  progress, -2 deleted;
- `type`: 0 an ordinary knowl, 1 and -1 the annotations shown at the top and
  bottom of a page (ids ending in `.top` and `.bottom`), 2 a description of
  a search table or one of its columns (ids `tables.TABLE` and
  `columns.TABLE.COLUMN`), -2 a comment on another knowl (`source`; ids
  ending in `.N.comment`).

www.lmfdb.org shows, for each `id`, the latest revision with status 1, or if
there is none the latest with status 0 (beta.lmfdb.org shows the latest with
status at least 0):

    SELECT DISTINCT ON (id) * FROM kwl_knowls WHERE status >= 0
    ORDER BY id, status >= 1 DESC, timestamp DESC;

`kwl_deleted` holds knowls that were deleted, with their history.  The text
is Markdown with TeX between dollar signs, and uses the LMFDB's template
macros: `{{ KNOWL('id', 'text') }}` links to another knowl, which is at
%s.
""" % (KNOWL_URL % "ID")


def knowls_description_html(registry_url=None):
    return (
        "<p>The knowledge database (knowls) of the L-functions and modular "
        "forms database (<a href=\"%s\">LMFDB</a>): the mathematical "
        "background, definitions and descriptions displayed throughout the "
        "site, including the table and column descriptions of the archived "
        "search tables, with the full revision history.</p>"
        "<p>Unlike the search tables, knowls are edited live on the website, "
        "so this record is refreshed with each LMFDB data push.  %s</p>"
        % (LMFDB_URL, _html(versions_note(registry_url), inline=True)))


def knowls_readme(manifest=None, date=None, registry_url=None):
    lines = [
        "# LMFDB knowledge database (knowls)",
        "",
        "Archived from the production database of the [LMFDB](%s) on %s.  %s"
        % (LMFDB_URL, date or _today(), versions_note(registry_url)),
        "",
        "License: CC BY-SA 4.0.",
        "",
    ]
    if manifest is not None:
        lines += ["## Files", "", file_guide(manifest), ""]
    lines += [
        KNOWL_MODEL,
        "## Restoring",
        "",
        "Create the tables with the `*_schema.sql` files, remove the three "
        "header lines (column names, column types, blank line) of each data "
        "file, and load it with `\\copy TABLE FROM 'FILE' (DELIMITER '|')`.",
        "",
    ]
    return "\n".join(lines)


######################################################################
# Version registry record                                            #
######################################################################

def registry_description_html():
    return (
        "<p>The version registry of the L-functions and modular forms "
        "database (<a href=\"%s\">LMFDB</a>).  Each version of this record "
        "corresponds to an LMFDB data version and lists, in README.md and in "
        "a JSON file, the Zenodo record and version holding each archived "
        "search table and the knowls at that LMFDB version, together with "
        "the version history (including the git commits of the website "
        "frontend).  See <a href=\"%s/version\">%s/version</a> for the "
        "version history on the site.</p>" % (LMFDB_URL, LMFDB_URL, LMFDB_URL))


def doi_url(entry):
    return "https://doi.org/%s" % entry["doi"]


def registry_readme(registry, titles, coverage, record_url=doi_url):
    """
    Markdown README.md for a registry record: a catalog of the records in
    the data version.

    - ``registry`` -- the registry JSON (see ``backup.build_registry``)
    - ``titles`` -- ``{name: title}`` of the records
    - ``coverage`` -- a sentence on which tables the archive covers
    - ``record_url`` -- the link for a record's entry (its DOI by default)
    """
    lines = [
        "# LMFDB version registry, data version %s" % registry["lmfdb_version"],
        "",
        "The records of the [LMFDB](%s) archived on Zenodo that make up its "
        "data version %s; `lmfdb_version_registry.json` has the same "
        "information, and the version history, in machine-readable form.  "
        "%s" % (LMFDB_URL, registry["lmfdb_version"], coverage),
        "",
        "| record | version | DOI | rows | size | changes in this version |",
        "|---|---|---|---|---|---|",
    ]
    for name, entry in sorted(registry["tables"].items()):
        lines.append("| %s | %s | [%s](%s) | %s | %s | %s |" % (
            titles.get(name, name), entry["version"], entry["doi"],
            record_url(entry), entry.get("rows") or "",
            _size(entry["size"]) if entry.get("size") else "",
            (entry.get("notes") or "").replace("|", "\\|").replace("\n", " ")))
    if not registry["tables"]:
        lines.append("| (none yet) | | | | | |")
    lines.append("")
    return "\n".join(lines)
