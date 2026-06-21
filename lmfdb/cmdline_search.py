r"""
Command-line search interface for the LMFDB.

The logic lives here (rather than in the ``lmfdb_search`` executable) so that it
can be imported and unit tested.  The executable is a thin wrapper that calls
:func:`main`.

You can provide a query in three ways:

* A url query string, matching the query-string part of an LMFDB url (only for
  sections, e.g. ``NumberField``).  For example ``degree=4`` matches
  https://www.lmfdb.org/NumberField/?degree=4
* A json dictionary giving a psycodict query, e.g. ``{"degree":4}`` (works for
  both sections and raw tables).
* Raw SQL with the ``--sql`` flag.
"""

import os
import sys
import csv
import json
from argparse import ArgumentParser
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse

from lmfdb import db
from lmfdb.utils.completeness import results_complete
from psycodict.encoding import copy_dumps, Json

# CLI format names that are only producible through a section's download object.
LANGUAGE_FORMATS = ["text", "sage", "gap", "pari", "magma", "oscar"]

# Map a CLI format name to the key used in a Downloader's ``languages`` dict.
# The LMFDB download machinery uses ``gp`` for the pari/gp language.
DOWNLOAD_LANG = {"pari": "gp"}

# Reverse map, used when reading a download language out of a pasted url (the
# website's "Submit" value uses "gp" where the CLI uses "pari").
URL_FORMAT = {v: k for k, v in DOWNLOAD_LANG.items()}

# The LMFDB sections understood by section_lookup, as they appear in an LMFDB
# url path.  Kept in sync with section_lookup by a test.
SECTIONS = (
    "L", "L/rational",
    "ModularForm/GL2/Q/holomorphic", "ModularForm/GL2/Q/Maass",
    "ModularForm/GL2/TotallyReal", "ModularForm/GL2/ImaginaryQuadratic",
    "EllipticCurve/Q", "EllipticCurve", "Genus2Curve/Q", "ModularCurve/Q",
    "HigherGenus/C/Aut", "Variety/Abelian/Fq", "Belyi", "NumberField",
    "padicField", "Character/Dirichlet/", "ArtinRepresentation",
    "Motive/Hypergeometric/Q", "GaloisGroup", "SatoTateGroup",
    "Groups/Abstract", "Lattice",
)

# url query-string keys that are not search-form fields but commonly appear in a
# search-results url (pagination, sorting, column control, download triggers).
META_PARAMS = frozenset({
    "search_type", "hst", "start", "count", "sort_order", "sort_dir",
    "columns", "showcol", "hidecol", "search_array", "jump", "label", "labels",
    "download", "Submit", "query", "download_row_count", "result_count",
})


def download_lang_key(fmt):
    return DOWNLOAD_LANG.get(fmt, fmt)


def section_param_names(search_array):
    """The set of url query-string keys recognized for a section: the names of
    the search-form input boxes, plus the common meta parameters."""
    names = set(META_PARAMS)
    for arr in (getattr(search_array, "refine_array", []),
                getattr(search_array, "browse_array", [])):
        for row in arr:
            for box in row:
                name = getattr(box, "name", None)
                if name:
                    names.add(name)
    return names


def check_query_columns(query, valid, parser):
    """Raise a parser error if a dict query uses a key that is not a column.

    Recurses into the lists of the ``$and``/``$or``/``$nor`` logical operators;
    other ``$``-prefixed keys are psycodict value-operators and are left alone.
    """
    if not isinstance(query, dict):
        return
    bad = []
    for key, val in query.items():
        if key in ("$and", "$or", "$nor"):
            if isinstance(val, list):
                for sub in val:
                    check_query_columns(sub, valid, parser)
        elif key.startswith("$"):
            continue
        elif key not in valid:
            bad.append(key)
    if bad:
        parser.error("not a column of the search table: " + ", ".join(bad))


def parse_lmfdb_url(url, parser):
    """Split a full LMFDB search-results url into ``(section, query_string,
    download_format)``.

    ``download_format`` is a CLI format name if the url triggers a download
    (``download=1``/``Submit=...``), otherwise ``None``.  Errors out on urls
    that are not LMFDB search-results urls.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not (
            parsed.netloc == "lmfdb.org" or parsed.netloc.endswith(".lmfdb.org")):
        parser.error(f"not an LMFDB url: {url}")
    path = parsed.path.strip("/")
    # Sections may end in a slash in the url (e.g. Character/Dirichlet/).
    if path in SECTIONS:
        section = path
    elif path + "/" in SECTIONS:
        section = path + "/"
    else:
        parser.error(f"{url} is not an LMFDB search-results url (could not identify a search section)")
    fmt = None
    is_download = False
    kept = []
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "Submit":
            is_download = True
            fmt = URL_FORMAT.get(val, val)
        elif key in ("download", "download_row_count", "query"):
            # download triggers / duplicated query; not part of the search
            is_download = is_download or key == "download"
        else:
            kept.append((key, val))
    if is_download and fmt is None:
        # download with no explicit language defaults to text (as on the website)
        fmt = "text"
    return section, urlencode(kept), fmt


def build_parser():
    parser = ArgumentParser(
        prog="LMFDBSearch",
        description="""Command-line search interface for the L-functions and modular forms database (LMFDB)

You can provide input in several formats:
* A url string, matching the query-string part of an LMFDB url.  For example, searching for number fields with degree 4 would be done with degree=4, matching the LMFDB url https://www.lmfdb.org/NumberField/?degree=4.
* A json dictionary such as {"degree":4}.

You can also paste a full LMFDB search-results url (from the production or beta
site) as the only argument, and it will be split into the section and search
terms; a download format in the url (e.g. Submit=sage) sets the output format.
""")

    parser.add_argument("table", help="Which table or section of the lmfdb to search, or a full LMFDB search-results url")
    parser.add_argument("query", nargs="*", help="A query constraining which results are returned.  If not present, all results will be included")
    parser.add_argument("-i", "--input", help="Input file with search query", )
    parser.add_argument("-s", "--sql", action="store_true", help="Use SQL for input")
    parser.add_argument("-o", "--output", help="Output file for search results")
    parser.add_argument("-f", "--force", action="store_true", help="Overwrite output file even if it exists")
    parser.add_argument("-t", "--format", help="Output format (default: raw, or the download format from a pasted url)", choices=["raw", "text", "json", "csv", "tsv", "sage", "gap", "pari", "magma", "oscar"], default=None)
    parser.add_argument("-p", "--completeness", action="store_true", help="Whether to include completeness information at the begining of the output")
    parser.add_argument("-c", "--cols", help="Which columns to include in the output")
    parser.add_argument("-l", "--limit", type=int, help="The number of matching results to return (-1 for no limit)", default=50)
    parser.add_argument("--offset", type=int, help="Where to start in the list of results", default=0)
    parser.add_argument("--sort", help="columns by which to sort the search results; prepend a minus sign to a column to reverse it")
    parser.add_argument("--oneper", help="a list of columns, separated by commas.  If provided, only one result will be included with each given set of values for those columns (the first according to the provided sort order).")
    parser.add_argument("-r", "--random", action="store_true", help="Return a single object chosen uniformly at random from those matching the query")
    parser.add_argument("-d", "--debug", action="store_true", help="whether to raise errors")
    parser.add_argument("--host", help="PostgreSQL server host or socket directory [default: %(default)s]", default="devmirror.lmfdb.xyz")
    parser.add_argument("--port", type=int, help="PostreSQL server port [default: %(default)d]", default=5432)
    parser.add_argument("--user", help="PostgreSQL username [default: %(default)s]", default="lmfdb")
    parser.add_argument("--password", help="PostgreSQL password [default: %(default)s]", default="lmfdb")
    parser.add_argument("--dbname", help="PostgreSQL database name [default: %(default)s]", default="lmfdb")

    return parser


def section_lookup(section, parser):
    if section == "L":
        from lmfdb.lfunctions.main import l_function_search, LFunctionSearchArray
        return l_function_search, LFunctionSearchArray()
    if section == "L/rational":
        from lmfdb.lfunctions.main import l_function_search, LFunctionSearchArray
        return l_function_search, LFunctionSearchArray(force_rational=True)
    if section == "ModularForm/GL2/Q/holomorphic":
        from lmfdb.classical_modular_forms.main import newform_search, CMFSearchArray
        return newform_search, CMFSearchArray()
    if section == "ModularForm/GL2/Q/Maass":
        from lmfdb.maass.main import search, MaassSearchArray
        return search, MaassSearchArray()
    if section == "ModularForm/GL2/TotallyReal":
        from lmfdb.hilbert_modular_forms.hilbert_modular_form import hilbert_modular_form_search, HMFSearchArray
        return hilbert_modular_form_search, HMFSearchArray()
    if section == "ModularForm/GL2/ImaginaryQuadratic":
        from lmfdb.bianchi_modular_forms.bianchi_modular_form import bianchi_modular_form_search, BMFSearchArray
        return bianchi_modular_form_search, BMFSearchArray()
    if section == "EllipticCurve/Q":
        from lmfdb.elliptic_curves.elliptic_curve import elliptic_curve_search, ECSearchArray
        return elliptic_curve_search, ECSearchArray()
    if section == "EllipticCurve":
        from lmfdb.ecnf.main import elliptic_curve_search, ECNFSearchArray
        return elliptic_curve_search, ECNFSearchArray()
    if section == "Genus2Curve/Q":
        from lmfdb.genus2_curves.main import genus2_curve_search, G2CSearchArray
        return genus2_curve_search, G2CSearchArray()
    if section == "ModularCurve/Q":
        from lmfdb.modular_curves.main import modcurve_search, ModCurveSearchArray
        return modcurve_search, ModCurveSearchArray()
    if section == "HigherGenus/C/Aut":
        from lmfdb.higher_genus_w_automorphisms.main import higher_genus_w_automorphisms_search, HGCWASearchArray
        return higher_genus_w_automorphisms_search, HGCWASearchArray()
    if section == "Variety/Abelian/Fq":
        from lmfdb.abvar.fq.main import abelian_variety_search, AbvarSearchArray
        return abelian_variety_search, AbvarSearchArray()
    if section == "Belyi":
        from lmfdb.belyi.main import belyi_search, BelyiSearchArray
        return belyi_search, BelyiSearchArray()
    if section == "NumberField":
        from lmfdb.number_fields.number_field import number_field_search, NFSearchArray
        return number_field_search, NFSearchArray()
    if section == "padicField":
        from lmfdb.local_fields.main import local_field_search, LFSearchArray
        return local_field_search, LFSearchArray()
    if section == "Character/Dirichlet/":
        from lmfdb.characters.main import dirichlet_character_search, DirichSearchArray
        return dirichlet_character_search, DirichSearchArray()
    if section == "ArtinRepresentation":
        from lmfdb.artin_representations.main import artin_representation_search, ArtinSearchArray
        return artin_representation_search, ArtinSearchArray()
    if section == "Motive/Hypergeometric/Q":
        from lmfdb.hypergm.main import hgm_search, HGMSearchArray
        return hgm_search, HGMSearchArray()
    if section == "GaloisGroup":
        from lmfdb.galois_groups.main import galois_group_search, GalSearchArray
        return galois_group_search, GalSearchArray()
    if section == "SatoTateGroup":
        from lmfdb.sato_tate_groups import sato_tate_search, STSearchArray
        return sato_tate_search, STSearchArray()
    if section == "Groups/Abstract":
        from lmfdb.groups.abstract.main import group_search, GroupsSearchArray
        return group_search, GroupsSearchArray()
    if section == "Lattice":
        from lmfdb.lattice.main import lattice_search, LatSearchArray
        return lattice_search, LatSearchArray()
    # TODO: include tabs (e.g. families for p-adic fields, newspaces

    parser.error("Must provide an LMFDB table or section as the first argument")


def resolve_table(name, parser):
    """Return the psycodict table object for a raw table name or a section."""
    if name in db.tablenames:
        return db[name]
    wrapper, _ = section_lookup(name, parser)
    return wrapper.table


def print_help(parser, table=None, col=None):
    """Describe a table or a single column.

    Invoked as ``lmfdb_search help TABLE [COL]``.  With only a table, prints the
    table's description followed by the description of every column.  With a
    table and a column, prints the description of that one column.
    """
    if table is None:
        parser.print_help()
        return
    tbl = resolve_table(table, parser)
    descriptions = tbl.column_description()
    if col is not None:
        if col not in tbl.col_type:
            parser.error(f"{col} is not a column of {tbl.search_table}")
        print(f"{tbl.search_table}.{col}: {descriptions.get(col, '')}")
        return
    table_description = tbl.description()
    print(f"{tbl.search_table}: {table_description}" if table_description else tbl.search_table)
    cols = sorted(descriptions)
    if cols:
        width = max(len(c) for c in cols)
        print("\nColumns:")
        for c in cols:
            print(f"  {c.ljust(width)}  {descriptions[c] or ''}")


def write(s, F):
    if F is None:
        if s and s[-1] == "\n":
            s = s[:-1]
        print(s)
    else:
        _ = F.write(s)


def allowed_formats(section_search, wrapper):
    """The set of ``--format`` values supported for the given table/section."""
    formats = {"raw", "json", "csv", "tsv"}
    if section_search and "download" in wrapper.shortcuts:
        languages = wrapper.shortcuts["download"].languages
        for fmt in LANGUAGE_FORMATS:
            if download_lang_key(fmt) in languages:
                formats.add(fmt)
    return formats


def run(args, parser):
    cols = args.cols.split(",") if args.cols is not None else None

    if args.table == "help":
        if not args.query:
            parser.print_help()
        elif len(args.query) <= 2:
            print_help(parser, *args.query)
        else:
            parser.error("Too many positional arguments")
        return

    # A full LMFDB search-results url can be pasted as the only argument; split
    # it into the section, the search terms and (if present) a download format.
    if args.table.startswith(("http://", "https://")):
        if args.query:
            parser.error("when pasting a full LMFDB url, do not also provide a separate query")
        if args.input is not None:
            parser.error("when pasting a full LMFDB url, do not also use --input")
        section, url_query, url_format = parse_lmfdb_url(args.table, parser)
        args.table = section
        args.query = [url_query] if url_query else []
        if url_format is not None and args.format is None:
            args.format = url_format
    if args.format is None:
        args.format = "raw"

    if len(args.query) > 1:
        parser.error("Too many positional arguments")

    if args.table in db.tablenames:
        section_search = False
        wrapper = None
        table, search_array = db[args.table], None
    else:
        section_search = True
        wrapper, search_array = section_lookup(args.table, parser)
        table = wrapper.table

    # Validate the requested output format now that we know the table/section.
    if args.format not in allowed_formats(section_search, wrapper):
        parser.error(f"{args.format} output format not supported for {args.table}")

    # Validate columns now that the table is known.
    if cols is not None:
        bad = [col for col in cols if col not in table.search_cols]
        if bad:
            parser.error("Invalid columns in output: " + ",".join(bad))
        projection = cols
    elif section_search:
        projection = [col for col in wrapper.projection if col in table.search_cols]
    else:
        projection = 1

    if args.query and args.input is not None:
        parser.error("may only provide input from one source: input file or positional argument")
    elif args.input is not None:
        try:
            with open(args.input) as F:
                args.query = [F.read()]
        except IOError as err:
            if args.debug:
                raise
            parser.error(str(err))

    # Autodetect input format based on query.  Must be compatible with the
    # table specification.
    info = {"search_array": search_array}
    sort = one_per = raw = None
    if args.debug:
        print("QUERY", args.query)
    if not args.query:
        query = {}
    elif args.sql:
        query = {}
        raw = args.query[0]
    elif args.query[0][0] == "{":
        try:
            query = json.loads(args.query[0])
        except Exception as err:
            if args.debug:
                raise
            parser.error(str(err))
        # Catch typo'd column names up front rather than letting them through
        # (psycodict would otherwise raise a less friendly error).
        check_query_columns(query, set(table.search_cols) | {"id"}, parser)
    elif section_search:
        info = parse_qs(args.query[0])
        for key, val in info.items():
            if len(val) > 1:
                parser.error(f"Multiple values found for {key} in query string")
            info[key] = val[0]
        # Reject unrecognized search parameters rather than silently ignoring
        # them (a common and confusing mistake).
        valid = section_param_names(search_array)
        unknown = [key for key in info if key not in valid]
        if unknown:
            parser.error("unknown search parameter(s): " + ", ".join(unknown))
        info["search_array"] = search_array
        try:
            result = wrapper.make_query(info)
        except Exception as err:
            if args.debug:
                raise
            parser.error(str(err))
        if not isinstance(result, tuple):
            # make_query returned a rendered error page rather than a query
            parser.error(info.get("err", "Error parsing query"))
        query, sort, table, title, err_title, template, one_per = result
    else:
        parser.error("url-style queries are only supported for sections; use a json query (e.g. '{\"degree\":4}') for a raw table")

    if args.oneper:
        # one_per might also have been set by url, but we allow the user to override with this setting
        one_per = args.oneper.split(",")
        if any(col not in table.search_cols for col in one_per):
            parser.error(",".join(col for col in one_per if col not in table.search_cols) + " not columns of " + table.search_table)

    if args.sort:
        # sort might also have been set by url, but we allow the user to override with this setting
        sort = args.sort.split(",")
        sort = [(col[1:], -1) if col and col[0] == "-" else (col, 1) for col in sort]
        if any(col not in table.search_cols for col, asc in sort):
            parser.error(",".join(col for col, asc in sort if col not in table.search_cols) + " not columns of " + table.search_table)

    if args.limit == -1:
        args.limit = None

    if args.random:
        # A single object chosen uniformly at random; limit/offset/sort/oneper
        # do not apply, and raw SQL queries are not supported by table.random.
        if raw is not None:
            parser.error("--random is not supported together with --sql")
        rec = table.random(query, projection=projection)
        res = [] if rec is None else [rec]
    else:
        # Pass a fresh raw_values list: psycodict's search() has a mutable
        # default raw_values=[] that _build_query appends the limit/offset to,
        # so a second raw= search in the same process would otherwise inherit
        # stale values and fail with "not all arguments converted".
        res = table.search(query,
                           projection=projection,
                           limit=args.limit,
                           offset=args.offset,
                           sort=sort,
                           one_per=one_per,
                           raw=raw,
                           raw_values=[])
    if projection == 1:
        projection = table.search_cols

    # Whether the download machinery will be used to produce the output.
    use_download = (section_search
                    and "download" in wrapper.shortcuts
                    and args.format not in ["raw", "json"]
                    and download_lang_key(args.format) in wrapper.shortcuts["download"].languages)

    if use_download:
        try:
            if wrapper.cleaners:
                if args.limit is None:
                    res = list(res)
                for v in res:
                    for name, func in wrapper.cleaners.items():
                        v[name] = func(v)
            if wrapper.postprocess is not None:
                # This could be expensive, since postprocess functions assume that res usually has at most 50 items
                res = wrapper.postprocess(res, info, query)
        except Exception as err:
            if args.debug:
                raise
            parser.error(str(err))

    if args.format == "json":
        res = list(res)

    if args.output:
        if os.path.exists(args.output) and not args.force:
            parser.error("Output file already exists")
        try:
            fkwds = {}
            if args.format in ["csv", "tsv"]:
                fkwds["newline"] = ""
            F = open(args.output, "w", **fkwds)
        except Exception as err:
            if args.debug:
                raise
            parser.error(str(err))
    elif args.format in ["csv", "tsv"] and not use_download:
        F = sys.stdout
    else:
        F = None
    try:
        if args.completeness:
            complete, msg, caveat = results_complete(table.search_table, query, table._db, search_array)
            if args.format == "json":
                res = {
                    "complete": complete,
                    "completeness_msg": msg,
                    "completeness_caveat": caveat,
                    "results": res
                }
            elif complete:
                write("Complete, since the LMFDB contains all " + msg + "\n", F)
                if caveat is None:
                    write("No reliance on unproven conjectures\n", F)
                else:
                    write("The completeness " + caveat + "\n", F)
            else:
                write("Not guaranteed complete\n\n", F)
        if args.format == "raw":
            write("|".join(projection) + "\n", F)
            write("|".join([table.col_type[col] for col in projection]) + "\n\n", F)
            for rec in res:
                line = "|".join(copy_dumps(rec.get(col, None), table.col_type[col]) for col in projection)
                write(line + "\n", F)
        elif args.format == "json":
            # json and tsv are produced here (and in the csv.DictWriter branch
            # below) rather than through the section download machinery, because
            # lmfdb/utils/downloader.py has no JSON or TSV DownloadLanguage yet.
            # If those are added to Downloader.languages, these formats could be
            # routed through use_download like sage/magma/csv/etc.
            write(json.dumps(Json.prep(res)), F)
        elif use_download:
            dl = wrapper.shortcuts["download"]
            lang = dl.languages[download_lang_key(args.format)]
            columns = wrapper.columns
            if cols is None:
                outcols = [col for col in columns.columns_shown(info, rank=-1) if col.default(info)]
            else:
                outcols = [col for col in columns.columns if col.name in cols]
            for s in lang.assign_iter("data", lang.to_lang_iter(
                    map(
                        lambda rec: [col.download(dl.postprocess(rec, info, query)) for col in outcols],
                        res))):
                write(s, F)
        else:
            if args.format == "csv":
                delimiter = ","
            elif args.format == "tsv":
                delimiter = "\t"
            else:
                raise ValueError(f"Format {args.format} not valid")
            # one_per (and some queries) can include extra grouping/sort
            # columns in each record; restrict the output to the projection.
            writer = csv.DictWriter(F, projection, delimiter=delimiter, extrasaction="ignore")
            writer.writeheader()
            for rec in res:
                writer.writerow(rec)
    except Exception as err:
        if args.debug:
            raise
        parser.error(str(err))
    finally:
        if F is not None and F is not sys.stdout:
            F.close()


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    run(args, parser)


if __name__ == "__main__":
    main()
