
import re
import time

from flask import abort, render_template, request, url_for, redirect, make_response
from sage.all import matrix, ZZ, IntegralLattice

from lmfdb.utils import (
    flash_error, flash_info, to_dict, #web_latex_split_on_pm,
    SearchArray, CountBox, #TextBox, prop_int_pretty,
    parse_ints, parse_posints, parse_count, parse_noop, #parse_list,
    parse_start, #clean_input,
    search_wrap, redirect_no_cache, Downloader, CodeSnippet)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol #MathCol, ProcessedCol, MultiProcessedCol
#from lmfdb.groups.abstract.web_groups import abstract_group_display_knowl
from lmfdb.api import datapage
from lmfdb.lattice import lattice_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.genus import common_parse, set_index_info, common_columns,  common_boxes, lat_only_columns, learnmore_list
from lmfdb.lattice.lattice_stats import Lattice_stats
from lmfdb.lattice.web_lattice import WebLattice, WebGenus, flat_to_matrix #vect_to_sym, vect_to_sym2, format_conway_symbol

# Database connection

from lmfdb import db

# breadcrumbs and links for data quality entries

def get_bread(tail=[]):
    base = [("Lattices", url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


#############################################
# Webpages: main, random and search results #
#############################################

@lattice_page.route("/")
def index():
    info = to_dict(request.args, search_array=LatSearchArray())

    if not request.args:
        set_index_info(info, Lattice_stats())
        t = 'Integral lattices'
        bread = get_bread()
        return render_template("lattice-index.html", info=info, title=t, learnmore=learnmore_list(), bread=bread)
    else:
        return lattice_search(info)


# Random Lattice
@lattice_page.route("/random")
@redirect_no_cache
def random_lattice():
    return url_for(".render_lattice_webpage", label=db.lat_lattices_new.random())

@lattice_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "lattice",
        db.lat_lattices_new,
        url_for_label=url_for_label,
        title=r"Some interesting Lattices",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@lattice_page.route("/stats")
def statistics():
    title = 'Lattices: Statistics'
    bread = get_bread('Statistics')
    return render_template("display_stats.html", info=Lattice_stats(), title=title, bread=bread, learnmore=learnmore_list())


# Regex for lattice label format
lattice_label_regex = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:((?:\.[0-9a-zA-Z]+)*))\.([0-9a-fA-F]+)\.(\d+)')


def split_lattice_label(lab):
    return lattice_label_regex.match(lab).groups()

def lattice_jump(info):
    jump = info["jump"]
    # by label
    if lattice_label_regex.fullmatch(jump):
        return redirect(url_for_label(jump))
    # by name - could improve this by reordering
    label = db.lat_lattices_new.lucky({"name": jump}, "label")
    if label is not None:
        return redirect(url_for_label(label))
    flash_error("No integral lattice in the database has label or name %s", jump)
    return redirect(url_for(".index"))



lattice_search_projection = ['label', 'rank', 'det_abs', 'level',
                             'class_number', 'aut', 'minimum']


def _show_genus(query, info, genus_label):
    """Show all lattices in the given genus with an informational flash message."""
    genus_url = url_for(".render_genus_webpage", label=genus_label)
    flash_info("The exact Gram matrix was not found in the database, "
               "but the lattice belongs to genus <a href='%s'>%s</a>. "
               "Showing all lattices in that genus." % (genus_url, genus_label))
    query.pop('gram', None)
    query['genus_label'] = genus_label
    count = parse_count(info)
    start = parse_start(info)
    return db.lat_lattices_new.search(query, limit=count, offset=start, info=info)


def lattice_search_isometric(res, info, query):
    """
    We check for isometric lattices if the user enters a valid gram matrix
    but not one stored in the database.

    Strategy:
    1. Compute the genus of the input matrix and find the matching genus in the DB.
    2. Use the user's other search constraints to narrow candidates within the genus.
    3. If only one candidate matches, it must be the lattice — return it directly.
    4. Otherwise try isometry against each candidate, with a time budget.
    5. If no match is found (or the time budget is exceeded), show all lattices
       in the genus with an informational message.
    """
    ISOM_TIME_LIMIT = 20.0  # seconds

    if info['number'] == 0 and info.get('gram_matrix'):
        A = info['gram_matrix']
        query.pop('gram', None)
        M = matrix(ZZ, A)
        count = parse_count(info)
        start = parse_start(info)
        t0 = time.time()

        try:
            L = IntegralLattice(M)
            input_genus = L.genus()
        except Exception:
            return res

        # Use genus invariants to narrow the DB search
        genus_query = {
            'rank': int(input_genus.rank()),
            'det': int(input_genus.det()),
            'level': int(input_genus.level()),
            'nplus': int(input_genus.signature()),
            'is_even': bool(input_genus.is_even()),
        }

        for rep in db.lat_genera.search(genus_query, ['rep', 'label']):
            if time.time() - t0 > ISOM_TIME_LIMIT:
                break
            rep_2d = flat_to_matrix(rep['rep'])
            L2 = IntegralLattice(matrix(ZZ, rep_2d))
            if input_genus == L2.genus():
                genus_label = rep['label']
                query['genus_label'] = genus_label

                # Count candidates matching all user constraints within this genus
                n_candidates = db.lat_lattices_new.count(query)

                if n_candidates == 1:
                    # Unique match — must be this lattice
                    res = db.lat_lattices_new.search(query, limit=count, offset=start, info=info)
                    return res

                if n_candidates > 1:
                    # Try isometry against each candidate, with time limit
                    for gram_val in db.lat_lattices_new.search(query, 'gram'):
                        if time.time() - t0 > ISOM_TIME_LIMIT:
                            break
                        if gram_val and isinstance(gram_val[0], list):
                            flat = gram_val[0]
                        else:
                            flat = gram_val
                        gram_2d = flat_to_matrix(flat)
                        if isom(A, gram_2d):
                            query['gram'] = gram_val
                            res = db.lat_lattices_new.search(query, limit=count, offset=start, info=info)
                            return res

                # No isometric match, time exceeded, or no candidates — show genus
                return _show_genus(query, info, genus_label)

    return res


def url_for_label(label):
    return url_for(".render_lattice_webpage", label=label)


lattice_columns = [
    LinkCol("label", "lattice.label", "Label", url_for_label)
] + common_columns + lat_only_columns


# Class to download lattice search results
class LatticeDownloader(Downloader):
    table = db.lat_lattices_new
    title = "Integral lattices"

    inclusions = {
        "lattice": (
            ["rank", "gram"],
            {
                "sage": 'lattice = IntegralLattice(Matrix(ZZ, out["rank"], out["rank"], out["gram"]))',
                "magma": 'lattice := LatticeWithGram(out["rank"], out["gram"]);',
                "oscar": 'lattice = integer_lattice(gram = matrix(ZZ, out["rank"], out["rank"], out["gram"]))'
            }
        ),
    }

@search_wrap(table=db.lat_lattices_new,
             title='Integral lattices search results',
             err_title='Integral lattices search error',
             columns=SearchColumns(lattice_columns),
             shortcuts={'download': LatticeDownloader(),
                        'jump': lattice_jump},
             postprocess=lattice_search_isometric,
             url_for_label=url_for_label,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def lattice_search(info, query):
    common_parse(info, query)
    # Store flat gram in query for direct DB matching (lat_lattices_new has a gram column)
    if 'gram_matrix' in info:
        mat = info['gram_matrix']
        n = len(mat)
        query['gram'] = [mat[i][j] for i in range(n) for j in range(n)]
    for field, name in [('minimum', 'Minimal vector length'), ('aut_size', 'Group order'),
                        ('kissing', 'Kissing number'), ('dual_kissing', 'Dual kissing number'),
                         ]:
        parse_posints(info, query, field, name)
    for field, name in [('dual_det', 'Dual determinant'), ('festi_veniani_index', "Festi-Veniani Index")]:
        parse_ints(info, query, field, name)
    parse_noop(info, query, "aut_label")


@lattice_page.route('/<label>')
def render_lattice_webpage(label):
    data = db.lat_lattices_new.lookup(label)
    if data is None:
        flash_error("%s is not the label of a lattice in the database.", label)
        return redirect(url_for(".index"))

    lattice = WebLattice(label, data)

    return render_template(
        "lattice-single.html",
        lattice=lattice,
        title=f"Integral lattice {label}",
        bread=get_bread(label),
        properties=lattice.properties,
        friends=lattice.friends,
        code=lattice.code,
        downloads=lattice.downloads,
        learnmore=learnmore_list(),
        KNOWL_ID=f"lattice.{lattice.label}")


@lattice_page.route('/data/<label>')
def lattice_data(label):
    if not lattice_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    genus_label = ".".join(label.split(".")[:-1])
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Lattice data - {label}"
    return datapage([label, genus_label], ["lat_lattices_new", "lat_genera"], title=title, bread=bread)


#################################
# Downloads for particular data #
#################################

# Download variables
download_comment_prefix = {'magma': '//', 'sage': '#', 'gp': '\\\\'}
download_assignment_start = {'magma': 'data := ', 'sage': 'data = ', 'gp': 'data = '}
download_assignment_end = {'magma': ';', 'sage': '', 'gp': ''}
download_file_suffix = {'magma': '.m', 'sage': '.sage', 'gp': '.gp'}

# Code snippet names to export for lattice pages
sorted_code_names = [
    'lattice_definition', 'rank', 'signature', 'determinant', 'discriminant', 'level',
    'class_number', 'conway_symbol', 'parity', 'automorphism_group', 'automorphism_group_order',
    'density', 'hermite', 'minimum', 'kissing', 'discriminant_group', 'successive_minima',
    'festi_veniani', 'gram', 'quadratic_form', 'theta_series',  
    # Dual lattice code snippets
    'dual', 'dual_conway', 'dual_det', 'dual_density', 'dual_hermite', 'dual_kissing', 'dual_theta',
    'orthogonal_decomposition', 'even_sublattice', 'minimal_vectors', 'pneighbors'
]

# Code snippet names to export for genus pages
genus_sorted_code_names = [
    'genus_definition', 'rank', 'signature', 'determinant', 'discriminant', 'level',
    'class_number', 'conway_symbol', 'dual_conway', 'parity', 'mass'
]

@lattice_page.route('/<label>/download/<lang>/<obj>')
def render_lattice_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_lattice_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_lattice_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_lattice_full_lists_v(**args):
    label = str(args['label'])
    res = db.lat_lattices_new.lookup(label)
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    outstr = c + ' Full list of normalized minimal vectors downloaded from the LMFDB on %s. \n\n' % (mydate)
    outstr += download_assignment_start[lang] + '\\\n'
    if res['name'] == ['Leech']:
        outstr += str(res['shortest']).replace("'", "").replace("u", "")
    else:
        outstr += str(res['shortest'])
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


def download_lattice_full_lists_g(**args):
    label = str(args['label'])
    res = db.lat_lattices_new.lookup(label, projection=['gram'])
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"

    def entry(r):
        return "".join([mat_start, str(r), mat_end])

    outstr = c + ' Full list of genus representatives downloaded from the LMFDB on %s. \n\n' % (mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join(entry(r) for r in res['gram'])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


@lattice_page.route('/<label>/download/<download_type>')
def lattice_code_download(**args):
    label = args['label']
    lang = args['download_type']
    try:
        lat = WebLattice(label)
        code = CodeSnippet(lat.code)
        response_code = code.export_code(label, lang, sorted_code_names)
    except Exception as err:
        return abort(404, str(err))
    response = make_response(response_code)
    response.headers['Content-type'] = 'text/plain'
    return response

@lattice_page.route('/Genus/<label>/download/<download_type>')
def genus_code_download(**args):
    label = args['label']
    lang = args['download_type']
    try:
        genus = WebGenus(label)
        code = CodeSnippet(genus.code)
        response_code = code.export_code(label, lang, genus_sorted_code_names)
    except Exception as err:
        return abort(404, str(err))
    response = make_response(response_code)
    response.headers['Content-type'] = 'text/plain'
    return response


class LatSearchArray(SearchArray):
    noun = "lattice"
    sorts = [("", "rank", ['rank', 'det_abs', 'level', 'class_number', 'label']),
             ("det_abs", "determinant", ['det_abs', 'rank', 'level', 'class_number', 'label']),
             ("level", "level", ['level', 'rank', 'det_abs', 'class_number', 'label']),
             ("class_number", "class number", ['class_number', 'rank', 'det_abs', 'level', 'label']),
             ("minimum", "minimum", ['minimum', 'rank', 'det_abs', 'level', 'class_number', 'label']),
             ("aut_size", "aut. group order", ['aut_size', 'rank', 'det_abs', 'level', 'class_number', 'label'])]

    def __init__(self):
        rank, signature, det_abs, level, gram, discriminant, parity, class_number, disc_invs, minimum, aut_label, aut_size, kissing, dual_det, dual_kissing, festi_veniani = common_boxes()
        count = CountBox()

        self.browse_array = [
            [rank, signature],
            [det_abs, discriminant],
            [level, class_number],
            [minimum, parity],
            [aut_size, aut_label],
            [dual_det, dual_kissing],
            [disc_invs, gram],
            [kissing, festi_veniani],
            [count]
        ]

        self.refine_array = [
            [rank, signature, det_abs, discriminant, level],
            [aut_size, aut_label, class_number, minimum, parity],
            [dual_det, dual_kissing, disc_invs, kissing, festi_veniani],
            [gram]
        ]
