
import re
import time

from flask import abort, render_template, request, url_for, redirect, make_response
from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, round

from lmfdb.utils import (
    web_latex_split_on_pm, flash_error, to_dict,
    SearchArray, TextBox, CountBox, prop_int_pretty,
    parse_ints, parse_posints, parse_list, parse_count, parse_start, clean_input,
    search_wrap, redirect_no_cache, Downloader, ParityBox)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.lattice import genus_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.genera_stats import Genus_stats

# Database connection

from lmfdb import db

#####################################
# Utilitary functions for displays  #
#####################################

def vect_to_matrix(v):
    return str(latex(matrix(v)))

def vect_to_sym(v):
    n = ZZ(round(sqrt(len(v))))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(n):
            M[i, j] = v[k]
            k += 1
    return [[int(M[i, j]) for i in range(n)] for j in range(n)]

def print_q_expansion(lst):
    lst = [str(c) for c in lst]
    Qa = PolynomialRing(QQ, 'a')
    Qq = PowerSeriesRing(Qa, 'q')
    return web_latex_split_on_pm(Qq(lst).add_bigoh(len(lst)))

def my_latex(s):
    ss = ""
    ss += re.sub(r'x\d', 'x', s)
    ss = re.sub(r"\^(\d+)", r"^{\1}", ss)
    ss = re.sub(r'\*', '', ss)
    ss = re.sub(r'zeta(\d+)', r'zeta_{\1}', ss)
    ss = re.sub('zeta', r'\\zeta', ss)
    ss += ""
    return ss


def format_conway_symbol(s):
    # Format Conway symbol so Roman numerals appear as text (upright) in LaTeX
    return s.replace('II_', r'\text{II}_').replace('I_', r'\text{I}_')


# breadcrumbs and links for data quality entries

def get_bread(tail=[]):
    base = [("Genus", url_for(".genus_render_webpage"))]
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

@genus_page.route("/")
def genus_render_webpage():
    info = to_dict(request.args, search_array=GenusSearchArray())
    sig_list = sum([[[n-nm, nm] for nm in range(1 + (n//2))] for n in range(1, 10)], [])
    signature_list = [str(s).replace(' ','') for s in sig_list[:16]]
    if not request.args:
        stats = Genus_stats()
        dim_list = list(range(1, 13))
        class_number_list = list(range(1, 31))
        det_list_endpoints = [-1000, -100, -10, 1, 10, 100, 1000]
        det_list = ["%s..%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        info.update({'dim_list': dim_list, 'signature_list': signature_list,
                     'det_list': det_list, 'class_number_list': class_number_list,
                     })
        t = 'Genera of integral lattices'
        bread = get_bread()
        info['stats'] = stats
        info['max_cn'] = stats.max_cn
        info['max_rank'] = stats.max_rank
        info['max_det'] = stats.max_det
        return render_template("genus-index.html", info=info, title=t, learnmore=learnmore_list(), bread=bread)
    else:
        return genus_search(info)


# Random Lattice
@genus_page.route("/random")
@redirect_no_cache
def random_lattice():
    return url_for(".render_genus_webpage", label=db.lat_genera.random())


@genus_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "genus",
        db.lat_genera,
        url_for_label=url_for_label,
        title=r"Some interesting genera of lattices",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )


@genus_page.route("/stats")
def statistics():
    title = 'Genera of lattices: Statistics'
    bread = get_bread('Statistics')
    return render_template("display_stats.html", info=Genus_stats(), title=title, bread=bread, learnmore=learnmore_list())


genus_label_regex = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:((?:\.[0-9a-zA-Z]+)*))\.([0-9a-fA-F]+)')

def split_genus_label(lab):
    return genus_label_regex.match(lab).groups()

def genus_by_label_or_name(lab):
    clean_lab = str(lab).replace(" ", "")
    clean_and_cap = str(clean_lab).capitalize()
    for l in [lab, clean_lab, clean_and_cap]:
        label = db.lat_genera.lucky(
            {'$or':
             [{'label': l}]},
            'label')
        if label is not None:
            return redirect(url_for(".render_genus_webpage", label=label))
    if genus_label_regex.match(lab):
        flash_error("The genus of integral lattices %s is not recorded in the database or the label is invalid", lab)
    else:
        flash_error("No integral lattice in the database has label or name %s", lab)
    return redirect(url_for(".genus_render_webpage"))


# download
download_comment_prefix = {'magma': '//', 'sage': '#', 'gp': '\\\\'}
download_assignment_start = {'magma': 'data := ', 'sage': 'data = ', 'gp': 'data = '}
download_assignment_end = {'magma': ';', 'sage': '', 'gp': ''}
download_file_suffix = {'magma': '.m', 'sage': '.sage', 'gp': '.gp'}

genus_search_projection = ['label', 'rank', 'det', 'level',
                             #'class_number', 'aut', 'minimum']
                           ]

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
                proj = lattice_search_projection
                count = parse_count(info)
                start = parse_start(info)
                res = db.lat_genera.search(query, proj, limit=count, offset=start, info=info)
                break
    return res


def url_for_label(label):
    return url_for(".render_genus_webpage", label=label)


genus_columns = SearchColumns([
    LinkCol("label", "lattice.label", "Label", url_for_label),
    MathCol("rank", "lattice.dimension", "Rank"),
    MultiProcessedCol("signature", "lattice.signature", "Signature", ["signature", "rank"], lambda signature, rank: '[%s,%s]' % (signature, rank-signature ),),
    MathCol("det", "lattice.determinant", "Determinant"),
    MathCol("disc", "lattice.discriminant", "Discriminant"),
    MathCol("level", "lattice.level", "Level"),
    MathCol("class_number", "lattice.class_number", "Class number"),
    ProcessedCol("conway_symbol", "lattice.conway_symbol", "Conway Symbol", lambda v : "$"+format_conway_symbol(v)+"$", default=False),
    ProcessedCol("is_even", "lattice.even_odd", "Even/Odd", lambda v: "Even" if v else "Odd"),
    ProcessedCol("mass", "lattice.mass", "Mass", lambda v: r"$%s/%s$" % (v[0],v[1]) if len(v) > 1 else "", default=False),
    ])

@search_wrap(table=db.lat_genera,
             title='Genera of integral lattices search results',
             err_title='Genera of integral lattices search error',
             columns=genus_columns,
             shortcuts={'download': Downloader(db.lat_genera),
                        'label': lambda info: genus_by_label_or_name(info.get('label'))},
             postprocess=genus_search_equivalence,
             url_for_label=url_for_label,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def genus_search(info, query):
    for field, name in [('rank', 'Rank'), ('level', 'Level'), ('class_number', 'Class number')]:
        parse_posints(info, query, field, name)
    for field, name in [('det', 'Determinant'),  ('disc', 'Discriminant')]:
        parse_ints(info, query, field, name)

    # Handle even/odd search
    parity = info.get('is_even')
    #assert(False)
    if parity:
        if parity == 'even':
            query['is_even'] = True
        elif parity == 'odd':
            query['is_even'] = False
    # Check if length of gram is triangular
    gram = info.get('gram')
    if gram:
        # Validate that the number of entries forms a triangular number
        entries = re.sub(r"[\[\]]", "", gram).split(",")
        num_entries = len(entries)
        # Check if num_entries = n(n+1)/2 for some integer n
        if not ZZ(1 + 8*num_entries).is_square():
            flash_error("%s is not a valid input for Gram matrix. It must be a list of integer vectors of triangular length, such as [1,2,3] for a 2x2 matrix.", gram)
            #raise ValueError("Invalid Gram matrix input")
    parse_list(info, query, 'gram', process=vect_to_sym)
    parse_list(info, query, 'discriminant_group_invs', process=lambda x: x)


@genus_page.route('/<label>')
def render_genus_webpage(**args):
    f = None
    if 'label' in args:
        lab = clean_input(args.get('label'))
        if lab != args.get('label'):
            return redirect(url_for('.render_genus_webpage', label=lab), 301)
        f = db.lat_genera.lucky({'$or': [{'label': lab}]})
    if f is None:
        t = "Integral lattice search error"
        bread = get_bread()
        flash_error("%s is not a valid label or name for an integral lattice in the database.", lab)
        return render_template("lattice-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(f)

    info['friends'] = []

    bread = get_bread(f['label'])
    info['rank'] = int(f['rank'])
    nplus = int(f['signature'])
    nminus = info['rank'] - nplus
    info['signature'] = (nplus, nminus)
    info['det'] = int(f['det'])
    info['level'] = int(f['level'])
    info['disc'] = int(f['disc'])
    info['conway_symbol'] = format_conway_symbol(f.get('conway_symbol', ''))
    info['is_even'] = f.get('is_even', '')
    info['gram'] = vect_to_matrix(vect_to_sym(f['rep']))
    info['mass'] = f.get('mass', "?")
    info['class_number'] = f.get('class_number', "?")
    
    # Discriminant form data
    discriminant_group_invs = f.get('discriminant_group_invs', [])
    info['discriminant_group_invs'] = ', '.join(str(inv) for inv in discriminant_group_invs)
    discriminant_form = f.get('discriminant_form', [])
    info['discriminant_gram'] = vect_to_matrix(vect_to_sym(discriminant_form))

# This part code was for the dynamic knowl with comments, since the test is displayed this is redundant
#    if info['name'] != "" or info['comments'] !="":
#        info['knowl_args']= "name=%s&report=%s" %(info['name'], info['comments'].replace(' ', '-space-'))
    info['properties'] = [
        ('Label', info['label']),
        ('Rank', prop_int_pretty(info['rank'])),
        ('Signature', '$%s$' % str(info['signature'])),
        ('Determinant', prop_int_pretty(info['det'])),
        ('Discriminant', prop_int_pretty(info['disc'])),
        ('Level', prop_int_pretty(info['level'])),
        ('Class Number', "?"),
        ('Even/Odd', 'Even' if info['is_even'] else 'Odd')]
    downloads = [("Underlying data", url_for(".genus_data", label=lab))]

    t = "Genus of integral lattices "+info['label']
#    friends = [('L-series (not available)', ' ' ),('Half integral weight modular forms (not available)', ' ')]
    return render_template(
        "genus-single.html",
        info=info,
        title=t,
        bread=bread,
        properties=info['properties'],
        downloads=downloads,
        learnmore=learnmore_list(),
        KNOWL_ID="lattice.%s" % info['label'])
# friends=friends

@genus_page.route('/data/<label>')
def genus_data(label):
    if not genus_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Genus data - {label}"
    return datapage(label, "lat_genera", title=title, bread=bread)


######################
# Data quality pages #
######################

@genus_page.route("/Source")
def how_computed_page():
    t = 'Source and acknowledgments for integral lattices'
    bread = get_bread("Source")
    return render_template("double.html", kid='rcs.source.lattice', kid2='rcs.ack.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))


@genus_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of integral lattice data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@genus_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of integral lattice data'
    bread = get_bread("Reliability")
    return render_template("single.html", kid='rcs.rigor.lattice',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))


@genus_page.route("/Labels")
def labels_page():
    t = 'Genera of integral lattice labels'
    bread = get_bread("Labels")
    return render_template("single.html", kid='lattice.genus_label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@genus_page.route("/History")
def history_page():
    t = 'A brief history of lattices'
    bread = get_bread("History")
    return render_template("single.html", kid='lattice.history',
                           title=t, bread=bread, learnmore=learnmore_list_remove('History'))

#################################
# Downloads for particular data #
#################################

@genus_page.route('/<label>/download/<lang>/<obj>')
def render_genus_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_genera_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_genera_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response

def download_genera_full_lists_v(**args):
    label = str(args['label'])
    res = db.lat_genera.lookup(label)
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such genus"
    lang = args['lang']
    c = download_comment_prefix[lang]
    outstr += download_assignment_start[lang] + '\\\n'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

def download_genera_full_lists_g(**args):
    label = str(args['label'])
    res = db.lat_genera.lookup(label, projection=['genus_reps'])
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"

    def entry(r):
        return "".join([mat_start, str(r), mat_end])

    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join(entry(r) for r in [res['rep']])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


class GenusSearchArray(SearchArray):
    noun = "genus"
    sorts = [("rank", "signature", ['rank', 'signature', 'det', 'level', 'disc', 'label']),
             ("det", "determinant", ['det', 'rank', 'signature', 'level', 'disc', 'label']),
             ("level", "level", ['level', 'rank', 'signature', 'det', 'disc', 'label']),
             ("disc", "discriminant", ['disc', 'rank', 'signature', 'det', 'level', 'label']),
            ]

    def __init__(self):
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
            example="3",
            example_span="3 or 2-5"
            )
        det = TextBox(
            name="det",
            label="Determinant",
            knowl="lattice.determinant",
            example="1",
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
            example="1",
            example_span="1 or 10-100")
        even_odd = ParityBox(
            name="is_even",
            label="Even/Odd",
            knowl="lattice.even_odd")
        class_number = TextBox(
            name="class_number",
            label="Class number",
            knowl="lattice.class_number",
            example="1")
        disc_invs = TextBox(
            name="discriminant_group_invs",
            label="Discriminant group invs",
            knowl="lattice.discriminant_group",
            example="2,4",
            example_span="2,4 or 2,2,8")
        
        count = CountBox()

        self.browse_array = [[rank], [signature], [det], [discriminant], [level], [class_number], [even_odd], [gram], [disc_invs], [count]]

        self.refine_array = [
            [rank, signature, det, discriminant, level], 
            [class_number, disc_invs, even_odd, gram]
        ]
