
import re
import time

from flask import abort, render_template, request, url_for, redirect, make_response
from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, round

from lmfdb.utils import (
    web_latex_split_on_pm, flash_error, to_dict,
    SearchArray, TextBox, CountBox, prop_int_pretty,
    parse_ints, parse_posints, parse_list, parse_count,
    parse_bracketed_posints, parse_start, clean_input,
    parse_rational_to_list,
    search_wrap, redirect_no_cache, Downloader, ParityBox)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.lattice import lattice_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.lattice_stats import Lattice_stats

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
    n = ZZ(round((-1+sqrt(1+8*len(v)))/2))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(i, n):
            M[i, j] = v[k]
            M[j, i] = v[k]
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
    base = [("Lattices", url_for(".lattice_render_webpage"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Labels for integral lattices', url_for(".labels_page")),
            ('History of lattices', url_for(".history_page"))]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


#############################################
# Webpages: main, random and search results #
#############################################

@lattice_page.route("/")
def lattice_render_webpage():
    info = to_dict(request.args, search_array=LatSearchArray())

    # Prepare list of signatures to browse (display as round brackets, internally use square brackets)
    sig_list = sum([[[n-nm, nm] for nm in range(1 + (n//2))] for n in range(1, 10)], [])
    signature_list = [[str(s).replace(' ',''), str(tuple(s)).replace(' ','')] for s in sig_list[:16]]

    if not request.args:
        stats = Lattice_stats()
        dim_list = list(range(1, 13))
        class_number_list = list(range(1, 31))
        det_list_endpoints = [-1000, -100, -10, 1, 10, 100, 1000]
        det_list = ["%s..%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        #name_list = ["A2", "Z2", "D3", "D3*", "3.1942.3884.56.1", "A5", "E8", "A14", "Leech"]
        info.update({'dim_list': dim_list, 'signature_list': signature_list,
                     'class_number_list': class_number_list, 'det_list': det_list})
        t = 'Integral lattices'
        bread = get_bread()
        info['stats'] = stats
        info['max_cn'] = stats.max_cn
        info['max_rank'] = stats.max_rank
        info['max_det'] = stats.max_det
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

def lattice_by_label_or_name(lab):
    clean_lab = str(lab).replace(" ", "")
    clean_and_cap = str(clean_lab).capitalize()
    for l in [lab, clean_lab, clean_and_cap]:
        label = db.lat_lattices_new.lucky(
            {'$or':
             [{'label': l},
              {'name': {'$contains': [l]}}]},
            'label')
        if label is not None:
            return redirect(url_for(".render_lattice_webpage", label=label))
    if lattice_label_regex.match(lab):
        flash_error("The integral lattice %s is not recorded in the database or the label is invalid", lab)
    else:
        flash_error("No integral lattice in the database has label or name %s", lab)
    return redirect(url_for(".lattice_render_webpage"))



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
        for gram in db.lat_lattices_new.search({'dim': n, 'det': int(d)}, 'gram'):
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


lattice_columns = SearchColumns([
    LinkCol("label", "lattice.label", "Label", url_for_label),
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
    MathCol("minimum", "lattice.minimal_vector", "Minimal vector"),
    MathCol("aut_size", "lattice.group_order", "Aut. group order"),
    MathCol("density", "lattice.density", "Density", default=False),
    MathCol("hermite", "lattice.hermite", "Hermite", default=False),
    MathCol("kissing", "lattice.kissing", "Kissing", default=False),
    ProcessedCol("discriminant_group_invs", "lattice.discriminant_group", "Disc. Inv.", short_title="Disc. Inv.",  default=False),
    MathCol("festi_veniani_index", "lattice.festi_veniani_index", "Festi-Veniani index", default=False)
])


@search_wrap(table=db.lat_lattices_new,
             title='Integral lattices search results',
             err_title='Integral lattices search error',
             columns=lattice_columns,
             shortcuts={'download': Downloader(db.lat_lattices_new),
                        'label': lambda info: lattice_by_label_or_name(info.get('label'))},
             postprocess=lattice_search_isometric,
             url_for_label=url_for_label,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def lattice_search(info, query):
    for field, name in [('rank', 'Rank'), ('level', 'Level'),  ('class_number', 'Class number'),
                        ('minimum', 'Minimal vector length'), ('aut_size', 'Group order'),
                        ('kissing', 'Kissing number'), ('dual_kissing', 'Dual kissing number'),
                         ]: 
        parse_posints(info, query, field, name)
    for field, name in [('det', 'Determinant'),  ('disc', 'Discriminant'),
                        ('dual_det', 'Dual determinant'), ('festi_veniani_index', "Festi-Veniani Index")]:
        parse_ints(info, query, field, name)
    parse_bracketed_posints(info, query, 'signature', qfield=('rank','signature'),exactlength=2, allow0=True, extractor=lambda L: (L[0]+L[1],L[0]))

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
    if gram and not (9 + 8*ZZ(gram.count(','))).is_square():
        flash_error("%s is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3].", gram)
        raise ValueError
    parse_list(info, query, 'gram', process=vect_to_sym)
    parse_list(info, query, 'discriminant_group_invs', process=lambda x: x)


@lattice_page.route('/<label>')
def render_lattice_webpage(**args):
    f = None
    if 'label' in args:
        lab = clean_input(args.get('label'))
        if lab != args.get('label'):
            return redirect(url_for('.render_lattice_webpage', label=lab), 301)
        f = db.lat_lattices_new.lucky({'$or': [{'label': lab}]})
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

    # Get invariants from the genus home page (must query db)
    genus_label = info['genus_label']
    f_genus = db.lat_genera.lucky({'$or': [{'label': genus_label}]})
    
    friends = []
    friends.append(("Genus of this lattice", "/Lattice/Genus/%s" % genus_label))

    # Get signature and whether lattice is positive definite
    nplus = int(f['signature'])
    nminus = info['rank'] - nplus
    info['signature'] = (nplus, nminus)
    info['is_positive_definite'] = (nminus==0)

    info['det'] = int(f['det'])
    info['level'] = int(f['level'])
    info['disc'] = int(f['disc'])
    info['conway_symbol'] = format_conway_symbol(f.get('conway_symbol', ''))
    info['gram'] = vect_to_matrix(vect_to_sym2(f['gram']))
    info['density'] = str(f['density']) if 'density' in info else "?"
    info['hermite'] = str(f['hermite']) if 'hermite' in info else "?"
    info['minimum'] = int(f['minimum'])  if 'minimum' in info else "?"
    info['kissing'] = int(f['kissing'])  if 'kissing' in info else "?"
    info['even_odd'] = 'Even' if f['is_even'] else 'Odd'
    info['mass'] = str(f_genus['mass'][0])+"/"+str(f_genus['mass'][1]) if 'mass' in f_genus else "?"
    info['festi_veniani'] = int(f['festi_veniani_index'])  if 'festi_veniani_index' in info else "?"

    # Gram matrix (with download link)
    info['gram'] = vect_to_matrix(vect_to_sym2(f['gram']))
    info['download_gram'] = [
        (i, url_for(".render_lattice_webpage_download", label=info['label'], lang=i, obj='genus_reps')) for i in ['gp', 'magma', 'sage']]

    # Data about automorphism group
    info['aut_group'] = f.get('aut_group', "not computed")
    info['aut_label'] = f.get('aut_label', "not computed")
    info['aut_size']  = f.get('aut_size', "not computed")

    # Display Theta series
    ncoeff = 20
    if 'theta_series' in f:
        coeff = [f['theta_series'][i] for i in range(ncoeff + 1)]
        info['theta_series'] = my_latex(print_q_expansion(coeff))
        info['theta_display'] = url_for(".theta_display", label=f['label'], number="")

    info['class_number'] = f.get('class_number', "?")
    info['shortest'] = f.get('shortest', '')

    # Discriminant form data
    discriminant_group_invs = f.get('discriminant_group_invs', [])
    info['discriminant_group_invs'] = ', '.join(str(inv) for inv in discriminant_group_invs)
    discriminant_form = f_genus.get('discriminant_form', [])
    info['discriminant_gram'] = vect_to_matrix(vect_to_sym2(discriminant_form))

    # Data about the dual lattice
    info['dual_conway_symbol'] = format_conway_symbol(f_genus.get('dual_conway_symbol', ''))
    info['dual_label'] = f.get('dual_label', "not in database")
    if 'dual_theta_series' in f:
        coeff = [f['dual_theta_series'][i] for i in range(ncoeff + 1)]
        info['dual_theta_series'] = my_latex(print_q_expansion(coeff))
        info['dual_theta_display'] = url_for(".dual_theta_display", label=f['label'], number="")    


    # Properties box
    info['properties'] = [
        ('Label', '%s' % info['label']),
        ('Rank', prop_int_pretty(info['rank'])),
        ('Signature', '$%s$' % str(info['signature'])),
        ('Determinant', prop_int_pretty(info['det'])),
        ('Discriminant', prop_int_pretty(info['disc'])),
        ('Level', prop_int_pretty(info['level'])), 
        ('Class Number', str(info['class_number'])),
        ('Even/Odd', info['even_odd'])]
    downloads = [("Underlying data", url_for(".lattice_data", label=lab))]

    t = "Integral lattice "+info['label']
    return render_template(
        "lattice-single.html",
        info=info,
        title=t,
        bread=bread,
        properties=info['properties'],
        friends=friends,
        downloads=downloads,
        learnmore=learnmore_list(),
        KNOWL_ID="lattice.%s" % info['label'])


@lattice_page.route('/data/<label>')
def lattice_data(label):
    if not lattice_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Lattice data - {label}"
    return datapage(label, "lat_lattices_new", title=title, bread=bread)


# auxiliary function for displaying more coefficients of the theta series
@lattice_page.route('/theta_display/<label>/<number>')
def theta_display(label, number):
    try:
        number = int(number)
    except Exception:
        number = 20
    if number < 20:
        number = 30
    number = min(number, 150)
    data = db.lat_lattices_new.lookup(label, projection=['theta_series'])
    coeff = [data['theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)

# auxiliary function for displaying more coefficients of the dual theta series
# (todo: merge this with the above theta_display function)
@lattice_page.route('/dual_theta_display/<label>/<number>')
def dual_theta_display(label, number):
    try:
        number = int(number)
    except Exception:
        number = 20
    if number < 20:
        number = 30
    number = min(number, 150)
    data = db.lat_lattices_new.lookup(label, projection=['dual_theta_series'])
    coeff = [data['dual_theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)



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
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="lattice.dimension",
            example="3",
            example_span="3 or 2-5")
        signature = TextBox(
            name="signature",
            label="Signature",
            knowl="lattice.signature",
            example="[1,1]")
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
            example="10",
            example_span="1 or 10-100")
        even_odd = ParityBox(
            name="is_even",
            label="Even/Odd",
            knowl="lattice.even_odd")
        minimum = TextBox(
            name="minimum",
            label="Minimal vector length",
            knowl="lattice.minimal_vector",
            example="1")
        class_number = TextBox(
            name="class_number",
            label="Class number",
            knowl="lattice.class_number",
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
        disc_invs = TextBox(
            name="discriminant_group_invs",
            label="Disc. group invariants",
            knowl="lattice.discriminant_group",
            example="2,4",
            example_span="2,4 or 2,2,8")
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
