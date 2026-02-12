
import re
import time

from flask import abort, render_template, request, url_for, redirect, make_response
from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, round

from lmfdb.utils import (
    web_latex_split_on_pm, flash_error, to_dict,
    SearchArray, TextBox, CountBox, prop_int_pretty,
    parse_ints, parse_posints, parse_list, parse_count, parse_noop,
    parse_bracketed_posints, parse_start, clean_input,
    parse_rational_to_list,
    search_wrap, redirect_no_cache, Downloader, ParityBox)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.groups.abstract.web_groups import abstract_group_display_knowl
from lmfdb.api import datapage
from lmfdb.lattice import lattice_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.genus import common_parse, set_index_info, common_columns,  common_boxes, lat_only_columns, learnmore_list
from lmfdb.lattice.lattice_stats import Lattice_stats
from lmfdb.lattice.web_lattice import WebLattice, WebGenus, vect_to_sym, vect_to_sym2, format_conway_symbol

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



lattice_search_projection = ['label', 'rank', 'det', 'level',
                             'class_number', 'aut', 'minimum']


def lattice_search_isometric(res, info, query):
    """
    We check for isometric lattices if the user enters a valid gram matrix
    but not one stored in the database

    This may become slow in the future: at the moment we compare against
    a list of stored matrices with same dimension and determinant
    (just compare with respect to dimension is slow)
    """
    if info['number'] == 0 and info.get('gram'):
        A = query['gram']
        n = len(A[0])
        d = matrix(A).determinant()
        for rec in db.lat_lattices_new.search({'dim': n, 'det': int(d)}, ["canonical_gram", "gram"]):
            if rec.get("canonical_gram"):
                gram = rec["canonical_gram"]
            elif rec.get("gram"):
                gram = rec["gram"][0]
            else:
                continue
            # TODO: isom only works for positive definite gram matrices
            if isom(A, gram):
                query['gram'] = gram
                proj = lattice_search_projection
                count = parse_count(info)
                start = parse_start(info)
                res = db.lat_lattices_new.search(query, proj, limit=count, offset=start, info=info)
                break

    return res


def url_for_label(label):
    return url_for(".render_lattice_webpage", label=label)


lattice_columns = [
    LinkCol("label", "lattice.label", "Label", url_for_label)
] + common_columns + lat_only_columns

@search_wrap(table=db.lat_lattices_new,
             title='Integral lattices search results',
             err_title='Integral lattices search error',
             columns=SearchColumns(lattice_columns),
             shortcuts={'download': Downloader(db.lat_lattices_new),
                        'jump': lattice_jump},
             postprocess=lattice_search_isometric,
             url_for_label=url_for_label,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def lattice_search(info, query):
    common_parse(info, query)
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


class LatSearchArray(SearchArray):
    noun = "lattice"
    sorts = [("", "rank", ['rank', 'det', 'level', 'class_number', 'label']),
             ("det", "determinant", ['det', 'rank', 'level', 'class_number', 'label']),
             ("level", "level", ['level', 'rank', 'det', 'class_number', 'label']),
             ("class_number", "class number", ['class_number', 'rank', 'det', 'level', 'label']),
             ("minimum", "minimal vector length", ['minimum', 'rank', 'det', 'level', 'class_number', 'label']),
             ("aut", "automorphism group", ['aut', 'rank', 'det', 'level', 'class_number', 'label'])]

    def __init__(self):
        rank, signature, det, level, gram, discriminant, even_odd, class_number, disc_invs, minimum, aut_label, aut_size, kissing, dual_det, dual_kissing, festi_veniani = common_boxes()
        count = CountBox()

        self.browse_array = [
            [rank, signature],
            [det, discriminant],
            [level, class_number],
            [minimum, even_odd],
            [aut_size, aut_label],
            [dual_det, dual_kissing],
            [disc_invs, gram],
            [kissing, festi_veniani],
            [count]
        ]

        self.refine_array = [
            [rank, signature, det, discriminant, level],
            [aut_size, aut_label, class_number, minimum, even_odd],
            [dual_det, dual_kissing, disc_invs, kissing, festi_veniani],
            [gram]
        ]
