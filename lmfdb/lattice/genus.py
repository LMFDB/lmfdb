
import re
import time

from flask import abort, render_template, request, url_for, redirect, make_response
from cypari2.handle_error import PariError
from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, round, pari

#from lmfdb.local_fields.main import formatbracketcol
from lmfdb.utils import (
    web_latex_split_on_pm, flash_error, to_dict,
    SearchArray, EmbeddedSearchArray, TextBox, CountBox, prop_int_pretty,
    parse_ints, parse_posints, parse_list, parse_count,
    parse_bracketed_posints, parse_start, clean_input, parse_noop,
    parse_rational_to_list, raw_typeset_qexp,
    search_wrap, embed_wrap, redirect_no_cache, Downloader, ParityBox)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.lattice import lattice_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.genera_stats import Genus_stats

# Database connection

from lmfdb import db

#####################################
# Utilitary functions for displays  #
#####################################

def vect_to_matrix(v):
    """
    Converts a list of vectors of ints into a latex-formatted string which renders a latex pmatrix, ready for display
    """
    return str(latex(matrix(v)))

def vect_to_sym(v):
    """
    Converts an upper triangular vector of ints, to a full 2d list of ints
    """
    n = ZZ(round(sqrt(len(v))))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(n):
            M[i, j] = v[k]
            k += 1
    return [[int(M[i, j]) for i in range(n)] for j in range(n)]

def vect_to_sym2(v):
    """
    Converts a list of n^2 ints, to a 2D n x n array
    """
    n = ZZ(round(sqrt(len(v))))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(n):
            M[i, j] = v[k]
            k += 1
    return [[int(M[i, j]) for i in range(n)] for j in range(n)]

def format_conway_symbol(s):
    # Format Conway symbol so Roman numerals appear as text (upright) in LaTeX
    return s.replace('II_', r'\text{II}_').replace('I_', r'\text{I}_')

def make_neighbors_graph(M):
    """
    Given the adjacemency matrix data, we construct a graph object to plot on the genus page
    """
    from sage.graphs.graph import Graph
    G = Graph(unfill_isogeny_matrix(M), format='weighted_adjacency_matrix')
    return G


# breadcrumbs and links for data quality entries

def get_bread(tail=[]):
    base = [("Genus", url_for(".genus_index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Labels for genera of lattices', url_for(".labels_page")),
            ('History of lattices', url_for(".history_page"))]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


#############################################
# Webpages: main, random and search results #
#############################################

def set_index_info(info, stats):
    # Prepare list of signatures to browse (display as round brackets, internally use square brackets)
    sig_list = sum([[[n-nm, nm] for nm in range(1 + (n//2))] for n in range(1, 10)], [])
    signature_list = [[str(s).replace(' ',''), str(tuple(s)).replace(' ','')] for s in sig_list[:16]]
    dim_list = list(range(1, 13))
    class_number_list = list(range(1, 31))
    det_list_endpoints = [-1000, -100, -10, 1, 10, 100, 1000]
    det_list = ["%s..%s" % (start, end - 1 if end != 1 else -1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
    info.update({'dim_list': dim_list, 'signature_list': signature_list,
                 'det_list': det_list, 'class_number_list': class_number_list,
                 })
    info['stats'] = stats
    info['max_cn'] = stats.max_cn
    info['max_rank'] = stats.max_rank
    info['max_det'] = stats.max_det

@lattice_page.route("/Genus")
def genus_index():
    info = to_dict(request.args, search_array=GenusSearchArray())

    if not request.args:
        set_index_info(info, Genus_stats())
        t = 'Genera of integral lattices'
        bread = get_bread()
        return render_template("genus-index.html", info=info, title=t, learnmore=learnmore_list(), bread=bread)
    else:
        return genus_search(info)


# Random Lattice
@lattice_page.route("/Genus/random")
@redirect_no_cache
def random_genus():
    return url_for(".render_genus_webpage", label=db.lat_genera.random())


@lattice_page.route("/Genus/interesting")
def genus_interesting():
    return interesting_knowls(
        "lattice.genus",
        db.lat_genera,
        url_for_label=url_for_genus,
        title=r"Some interesting genera of lattices",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )


@lattice_page.route("/Genus/stats")
def genus_statistics():
    title = 'Genera of lattices: Statistics'
    bread = get_bread('Statistics')
    return render_template("display_stats.html", info=Genus_stats(), title=title, bread=bread, learnmore=learnmore_list())


# Regex for genus lattice label format
genus_label_regex = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:((?:\.[0-9a-zA-Z]+)*))\.([0-9a-fA-F]+)')

def split_genus_label(lab):
    return genus_label_regex.match(lab).groups()

def genus_jump(info):
    jump = info["jump"]
    # by label
    if genus_label_regex.fullmatch(jump):
        return redirect(url_for_genus(jump))
    # by name - could improve this by reordering
    label = db.lat_lattices_new.lucky({"name": jump}, "genus_label")
    if label is not None:
        return redirect(url_for_genus(label))
    flash_error("No genus in the database has label or name %s", jump)
    return redirect(url_for(".genus_index"))


genus_search_projection = ['label', 'rank', 'det', 'level', 'class_number']

def genus_search_equivalence(res, info, query):
    """
    We check for equivalent genuses if the user enters a valid gram matrix
    but not one stored in the database

    This may become slow in the future: at the moment we compare against
    a list of stored matrices with same dimension, signature and determinant
    (just compare with respect to dimension is slow)
    """
    if info['number'] == 0 and info.get('gram'):
        A = query['gram']
        n = len(A[0])
        L = IntegralLattice(matrix(A))
        det = matrix(A).determinant()
        for gram in db.lat_genera.search({'dim': n, 'det': int(det)}, 'rep'):
            L2 = IntegralLattice(Matrix(ZZ, n, n, gram))
            if L.genus() == L2.genus():
                query['gram'] = gram
                proj = genus_search_projection
                count = parse_count(info)
                start = parse_start(info)
                res = db.lat_genera.search(query, proj, limit=count, offset=start, info=info)
                break
    return res


def url_for_genus(label):
    return url_for(".render_genus_webpage", label=label)

def common_parse(info, query):
    for field, name in [('rank', 'Rank'), ('level', 'Level'), ('class_number', 'Class number')]:
        parse_posints(info, query, field, name)
    # TODO: fix handling of sign here (e.g. -100..-11 currently fails)
    for field, name in [('det', 'Determinant'),  ('disc', 'Discriminant')]:
        parse_ints(info, query, field, name)
    parse_bracketed_posints(info, query, 'signature', qfield=('rank','signature'),exactlength=2, allow0=True, extractor=lambda L: (L[0]+L[1],L[0]))

    # Handle even/odd search
    parity = info.get('is_even')
    if parity:
        if parity == 'even':
            query['is_even'] = True
        elif parity == 'odd':
            query['is_even'] = False
    # Check if length of gram is triangular
    gram = info.get('gram')
    if gram and not (9 + 8*ZZ(gram.count(','))).is_square():
        flash_error("%s is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3].", gram)
        raise ValueError("Invalid Gram matrix size")
    parse_list(info, query, 'gram', process=vect_to_sym)
    parse_list(info, query, 'discriminant_group_invs', process=lambda x: x)

common_columns = [
    MathCol("rank", "lattice.dimension", "Rank"),
    MultiProcessedCol("signature", "lattice.signature", "Signature", ["signature", "rank"], lambda signature, rank: '$(%s,%s)$' % (signature, rank-signature ),  align="center"),
    MathCol("det", "lattice.determinant", "Determinant"),
    MathCol("dual_det", "lattice.determinant", "Dual Determinant", default=False),
    MathCol("disc", "lattice.discriminant", "Discriminant"),
    MathCol("level", "lattice.level", "Level"),
    MathCol("class_number", "lattice.class_number", "Class number"),
    ProcessedCol("conway_symbol", "lattice.conway_symbol", "Conway Symbol", lambda v : "$"+format_conway_symbol(v)+"$", default=False),
    ProcessedCol("dual_conway_symbol", "lattice.conway_symbol", "Dual Conway Symbol", lambda v : "$"+format_conway_symbol(v)+"$", default=False),
    ProcessedCol("is_even", "lattice.even_odd", "Even/Odd", lambda v: "Even" if v else "Odd"),
    ProcessedCol("discriminant_group_invs", "lattice.discriminant_group", "Disc. Inv.", short_title="Disc. Inv.",  default=False),
]

lat_only_columns = [
    MathCol("minimum", "lattice.minimal_vector", "Minimal vector"),
    MathCol("aut_size", "lattice.group_order", "Aut. group order"),
    ProcessedCol("theta_series", "lattice.theta", "Theta series", raw_typeset_qexp, default=False),
    ProcessedCol("gram", "lattice.gram", "Gram matrix", lambda v: vect_to_matrix(vect_to_sym2(v)), mathmode=True),
    MathCol("density", "lattice.density", "Density", default=False),
    MathCol("hermite", "lattice.hermite", "Hermite", default=False),
    MathCol("kissing", "lattice.kissing", "Kissing", default=False),
    MathCol("festi_veniani_index", "lattice.festi_veniani_index", "Festi-Veniani index", default=False)
]

genus_columns = [LinkCol("label", "lattice.label", "Label", url_for_genus)] + common_columns

in_genus_columns = [LinkCol("label", "lattice.label", "Label", lambda label: url_for(".render_lattice_webpage", label=label))] + lat_only_columns

@search_wrap(table=db.lat_genera,
             title='Genera of integral lattices search results',
             err_title='Genera of integral lattices search error',
             columns=SearchColumns(genus_columns),
             shortcuts={'download': Downloader(db.lat_genera),
                        'label': lambda info: genus_by_label_or_name(info.get('label'))},
             postprocess=genus_search_equivalence,
             url_for_label=url_for_genus,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def genus_search(info, query):
    common_parse(info, query)
    parse_rational_to_list(info, query, 'mass', 'mass')

def common_render(info):

    # Get signature and whether lattice is positive definite
    nplus = int(info['signature'])
    nminus = info['rank'] - nplus
    info['signature'] = (nplus, nminus)
    info['is_positive_definite'] = (nminus==0)

    # TEMP FIX: Get class number (if class number not in db, display "?" for now)
    info['class_number'] = info.get('class_number', '?')

    info['conway_symbol'] = format_conway_symbol(info.get('conway_symbol', ''))
    info['dual_conway_symbol'] = format_conway_symbol(info.get('dual_conway_symbol', ''))
    info['even_odd'] = 'Even' if info['is_even'] else 'Odd'

    # Gram matrix (with download link)
    if 'rep' in info:
        # A genus
        gram = info['rep']
    elif info.get("canonical_gram"):
        gram = info["canonical_gram"]
    elif info.get("gram"):
        gram = info["gram"][0]
    else:
        gram = None
    if gram:
        info['gram'] = vect_to_matrix(vect_to_sym(gram))
        # TODO: Switch this to using code snippets
        info['download_gram'] = [
            (i, url_for(".render_genus_webpage_download", label=info['label'], lang=i, obj='gram')) for i in ['gp', 'magma', 'sage']]

    # Get the mass (if positive definite)
    if info.get("mass"):
        info["mass"] = "/".join(str(a) for a in info["mass"])
    else:
        info["mass"] = "not applicable"

    # Discriminant form data
    discriminant_group_invs = info.get('discriminant_group_invs', [])
    info['discriminant_group_invs'] = ', '.join(str(inv) for inv in discriminant_group_invs)
    discriminant_form = info.get('discriminant_form', [])
    info['discriminant_gram'] = vect_to_matrix(vect_to_sym(discriminant_form))

@lattice_page.route('/Genus/<label>')
def render_genus_webpage(label):
    data = db.lat_genera.lookup(label)
    # TODO: might need an object here because of name conflicts between data in info and search inputs in info
    if data is None:
        flash_error("%s is not the label of a genus in the lattice database.", label)
        return redirect(url_for(".genus_index"))
    info = to_dict(request.args, search_array=InGenusSearchArray())
    info.update(data)
    common_render(info)

    # Adjaceny graph data
    adjacency_primes = info['adjaceny_matrix'].keys() if 'adjaceny_matrix' in info else []
    for p in adjacency_primes:
        info['adjacency'][p]['poly'] = info['adjaceny_polynomials'][p]

        adj_mat = info['adjaceny_graph'][p]
        graph = make_graph(adj_mat)
        P = graph.plot(edge_labels=True)
        #info[p]['graph'] = make_neighbors_graph
        graph_img = encode_plot(P, transparent=True)
        info['adjacency'][p]['graph_link'] = '<img src="%s" width="200" height="150"/>' % graph_img

    info["bread"] = get_bread(info['label'])

    # Properties box
    info['properties'] = [
        ('Label', info['label']),
        ('Rank', prop_int_pretty(info['rank'])),
        ('Signature', '$%s$' % str(info['signature'])),
        ('Determinant', prop_int_pretty(info['det'])),
        ('Discriminant', prop_int_pretty(info['disc'])),
        ('Level', prop_int_pretty(info['level'])),
        ('Class Number', str(info['class_number'])),
        ('Even/Odd', info['even_odd'])]
    info["downloads"] = [("Underlying data", url_for(".genus_data", label=label))]

    info["title"] = "Genus of integral lattices "+info['label']
    info["KNOWL_ID"] = "lattice.%s" % info['label']
    return render_genus(info)

@embed_wrap(
    table=db.lat_lattices_new,
    template="genus-single.html",
    err_title="Genus error",
    columns=SearchColumns(in_genus_columns),
    learnmore=learnmore_list,
    # Each of the following arguments is set here so that it is overridden when constructing template_kwds,
    # which prioritizes values found in info (which are set in render_genus_webpage() before calling render_genus)
    bread=lambda:None,
    properties=lambda:None,
    friends=lambda:None,
    downloads=lambda:None,
    KNOWL_ID=lambda:None,
)
def render_genus(info, query):
    query["genus_label"] = info["label"]
    for field, name in [('minimum', 'Minimal vector length'), ('aut_size', 'Group order'),
                        ('kissing', 'Kissing number'), ('dual_kissing', 'Dual kissing number'),
                         ]:
        parse_posints(info, query, field, name)
    for field, name in [('dual_det', 'Dual determinant'), ('festi_veniani_index', "Festi-Veniani Index")]:
        parse_ints(info, query, field, name)
    parse_noop(info, query, "aut_label")

@lattice_page.route('/Genus/data/<label>')
def genus_data(label):
    if not genus_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_genus(label)), ("Data", " ")])
    title = f"Genus data - {label}"
    return datapage(label, ["lat_genera", "lat_lattices_new"], title=title, bread=bread, label_cols=["label", "genus_label"])


#################################
# Downloads for particular data #
#################################

# Download variables
download_comment_prefix = {'magma': '//', 'sage': '#', 'gp': '\\\\'}
download_assignment_start = {'magma': 'data := ', 'sage': 'data = ', 'gp': 'data = '}
download_assignment_end = {'magma': ';', 'sage': '', 'gp': ''}
download_file_suffix = {'magma': '.m', 'sage': '.sage', 'gp': '.gp'}


@lattice_page.route('/Genus/<label>/download/<lang>/<obj>')
def render_genus_webpage_download(**args):
    if args['obj'] == 'gram':
        response = make_response(download_gram_matrix(**args))
        response.headers['Content-type'] = 'text/plain'
        return response

def download_gram_matrix(**args):
    label = str(args['label'])
    res = db.lat_genera.lookup(label, projection=['rep'])
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"

    def entry(r):
        return "".join([mat_start, str(r), mat_end])

    outstr = c + ' A representative Gram matrix for genus %s downloaded from the LMFDB on %s. \n\n' % (label, mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join(entry(vect_to_sym(r)) for r in [res['rep']])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

def common_boxes():
    rank = TextBox(
        name="rank",
        label="Rank",
        knowl="lattice.dimension",
        example="3",
        example_span="3 or 2-5")
    signature=TextBox(
        name="signature",
        label="Signature",
        knowl="lattice.signature",
        example="[1,1]")
    det = TextBox(
        name="det",
        label="Determinant",
        knowl="lattice.determinant",
        example="10",
        example_span="1 or 10-100")
    level = TextBox(
        name="level",
        label="Level",
        knowl="lattice.level",
        example="48",
        example_span="48 or 40-100")
    gram = TextBox(
        name="gram",
        label="Gram matrix",
        knowl="lattice.gram",
        example="[5,1,23]",
        example_span=r"$[5,1,23]$ for the matrix $\begin{pmatrix}5 & 1\\ 1& 23\end{pmatrix}$")
    discriminant = TextBox(
        name="disc",
        label="Discriminant",
        knowl="lattice.discriminant",
        example="10",
        example_span="1 or 10-100")
    even_odd = ParityBox(
        name="is_even",
        label="Even/Odd",
        knowl="lattice.even_odd")
    class_number = TextBox(
        name="class_number",
        label="Class number",
        knowl="lattice.class_number",
        example="5")
    disc_invs = TextBox(
        name="discriminant_group_invs",
        label="Disc. group invariants",
        knowl="lattice.discriminant_group",
        example="2,4",
        example_span="2,4 or 2,2,8")

    minimum = TextBox(
        name="minimum",
        label="Minimal vector length",
        knowl="lattice.minimal_vector",
        example="1")
    aut_label = TextBox(
        name="aut_label",
        label="Automorphism group",
        short_label="Aut. group",
        knowl="lattice.automorphism_group",
        example="8.1",
        example_span="8.1")
    aut_size = TextBox(
        name="aut_size",
        label="Automorphism group order",
        short_label="Aut. group order",
        knowl="lattice.group_order",
        example="2",
        example_span="696729600")
    kissing = TextBox(
        name="kissing",
        label="Kissing number",
        knowl="lattice.kissing",
        example="1")
    dual_det = TextBox(
        name="dual_det",
        label="Dual determinant",
        knowl="lattice.determinant",
        example="1",
        example_span="1 or 10-100")
    dual_kissing = TextBox(
        name="dual_kissing",
        label="Dual kissing number",
        knowl="lattice.kissing",
        example="1")
    festi_veniani = TextBox(
        name="festi_veniani_index",
        label="Festi-Veniani Index",
        knowl="lattice.festi_veniani_index",
        example="1")

    return rank, signature, det, level, gram, discriminant, even_odd, class_number, disc_invs, minimum, aut_label, aut_size, kissing, dual_det, dual_kissing, festi_veniani

class GenusSearchArray(SearchArray):
    noun = "genus"
    sorts = [("rank", "signature", ['rank', 'signature', 'det', 'level', 'disc', 'label']),
             ("det", "determinant", ['det', 'rank', 'signature', 'level', 'disc', 'label']),
             ("level", "level", ['level', 'rank', 'signature', 'det', 'disc', 'label']),
             ("disc", "discriminant", ['disc', 'rank', 'signature', 'det', 'level', 'label']),
             ("class_number", "class number", ['class_number', 'rank', 'signature', 'det', 'level', 'disc', 'label']),
            ]

    def __init__(self):
        rank, signature, det, level, gram, discriminant, even_odd, class_number, disc_invs, minimum, aut_label, aut_size, kissing, dual_det, dual_kissing, festi_veniani = common_boxes()

        mass = TextBox(
            name="mass",
            label="Mass",
            knowl="lattice.mass",
            example="1/2",
            example_span="1/2 or 1/2 or 1/2")
        count = CountBox()

        self.browse_array = [
            [rank, signature],
            [det, discriminant],
            [level, class_number],
            [disc_invs, even_odd],
            [mass, gram],
            [count]
        ]

        self.refine_array = [
            [rank, signature, det, discriminant, level],
            [class_number, disc_invs, even_odd, mass, gram]
        ]

class InGenusSearchArray(EmbeddedSearchArray):
    noun = "lattice"
    sorts = [("minimum", "minimal vector length", ['minimum', 'rank', 'det', 'level', 'class_number', 'label']),
             ("aut", "automorphism group", ['aut', 'rank', 'det', 'level', 'class_number', 'label'])]

    def __init__(self):
        rank, signature, det, level, gram, discriminant, even_odd, class_number, disc_invs, minimum, aut_label, aut_size, kissing, dual_det, dual_kissing, festi_veniani = common_boxes()
        count = CountBox()

        self.refine_array = [
            [minimum, aut_label, aut_size, kissing, dual_kissing],
            [dual_det, festi_veniani, count]
        ]

######################
# Data quality pages #
######################

@lattice_page.route("/Source")
def how_computed_page():
    t = 'Source and acknowledgments for integral lattices'
    bread = get_bread("Source")
    return render_template("double.html", kid='rcs.source.lattice', kid2='rcs.ack.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))


@lattice_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of integral lattice data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@lattice_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of integral lattice data'
    bread = get_bread("Reliability")
    return render_template("single.html", kid='rcs.rigor.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))


@lattice_page.route("/Labels")
def labels_page():
    t = 'Integral lattice labels'
    bread = get_bread("Labels")
    return render_template("single.html", kid='lattice.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))


@lattice_page.route("/History")
def history_page():
    t = 'A brief history of lattices'
    bread = get_bread("History")
    return render_template("single.html", kid='lattice.history',
                           title=t, bread=bread, learnmore=learnmore_list_remove('History'))


