
# -*- coding: utf-8 -*-
import ast
import re
from io import BytesIO
import time

from flask import abort, render_template, request, url_for, redirect, make_response, send_file
from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, round

from lmfdb.utils import (
    web_latex_split_on_pm, flash_error, to_dict,
    SearchArray, TextBox, CountBox, prop_int_pretty,
    parse_ints, parse_list, parse_count, parse_start, clean_input,
    search_wrap, redirect_no_cache)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, LinkCol, MathCol
from lmfdb.api import datapage
from lmfdb.lattice import lattice_page
from lmfdb.lattice.isom import isom
from lmfdb.lattice.lattice_stats import Lattice_stats

# Database connection

from lmfdb import db

# utilitary functions for displays


def vect_to_matrix(v):
    return str(latex(matrix(v)))


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

#breadcrumbs and links for data quality entries

def get_bread(tail=[]):
    base = [("Lattice", url_for(".lattice_render_webpage"))]
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


# webpages: main, random and search results

@lattice_page.route("/")
def lattice_render_webpage():
    info = to_dict(request.args, search_array=LatSearchArray())
    if not request.args:
        stats = Lattice_stats()
        dim_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 24]
        class_number_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 50, 51, 52, 54, 55, 56]
        det_list_endpoints = [1, 1000, 10000, 100000, 1000000, 10000000, 100000000]
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        name_list = ["A2","Z2", "D3", "D3*", "3.1942.3884.56.1", "A5", "E8", "A14", "Leech"]
        info.update({'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list, 'name_list': name_list})
        t = 'Integral lattices'
        bread = get_bread()
        info['stats'] = stats
        info['max_cn'] = stats.max_cn
        info['max_dim'] = stats.max_dim
        info['max_det'] = stats.max_det
        return render_template("lattice-index.html", info=info, title=t, learnmore=learnmore_list(), bread=bread)
    else:
        return lattice_search(info)

# Random Lattice
@lattice_page.route("/random")
@redirect_no_cache
def random_lattice():
    return url_for(".render_lattice_webpage", label=db.lat_lattices.random())

@lattice_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "lattice",
        db.lat_lattices,
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

lattice_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_lattice_label(lab):
    return lattice_label_regex.match(lab).groups()

def lattice_by_label_or_name(lab):
    clean_lab=str(lab).replace(" ","")
    clean_and_cap=str(clean_lab).capitalize()
    for l in [lab, clean_lab, clean_and_cap]:
        label = db.lat_lattices.lucky(
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

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}

def download_search(info):
    lang = info["Submit"]
    filename = 'integral_lattices' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    res = list(db.lat_lattices.search(ast.literal_eval(info["query"]), 'gram'))

    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Integral lattices downloaded from the LMFDB on %s. Found %s lattices.\n\n'%(mydate, len(res))
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\\\n'
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])
    # loop through all search results and grab the gram matrix
    s += ",\\\n".join(entry(gram) for gram in res)
    s += list_end
    s += download_assignment_end[lang]
    s += '\n'
    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

lattice_search_projection = ['label','dim','det','level','class_number','aut','minimum']
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
        for gram in db.lat_lattices.search({'dim': n, 'det': int(d)}, 'gram'):
            if isom(A, gram):
                query['gram'] = gram
                proj = lattice_search_projection
                count = parse_count(info)
                start = parse_start(info)
                res = db.lat_lattices.search(query, proj, limit=count, offset=start, info=info)
                break

    return res

def url_for_label(label):
    return url_for(".render_lattice_webpage", label=label)

lattice_columns = SearchColumns([
    LinkCol("label", "lattice.label", "Label", url_for_label, default=True),
    MathCol("dim", "lattice.dimension", "Dimension", default=True),
    MathCol("det", "lattice.determinant", "Determinant", default=True),
    MathCol("level", "lattice.level", "Level", default=True),
    MathCol("class_number", "lattice.class_number", "Class number", default=True),
    MathCol("minimum", "lattice.minimal_vector", "Minimal vector", default=True),
    MathCol("aut", "lattice.group_order", "Aut. group order", default=True)])

@search_wrap(table=db.lat_lattices,
             title='Integral lattices search results',
             err_title='Integral lattices search error',
             columns=lattice_columns,
             shortcuts={'download':download_search,
                        'label':lambda info:lattice_by_label_or_name(info.get('label'))},
             postprocess=lattice_search_isometric,
             url_for_label=url_for_label,
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             properties=lambda: [])
def lattice_search(info, query):
    for field, name in [('dim','Dimension'),('det','Determinant'),('level',None),
                        ('minimum','Minimal vector length'), ('class_number',None),
                        ('aut','Group order')]:
        parse_ints(info, query, field, name)
    # Check if length of gram is triangular
    gram = info.get('gram')
    if gram and not (9 + 8*ZZ(gram.count(','))).is_square():
        flash_error("%s is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3].", gram)
        raise ValueError
    parse_list(info, query, 'gram', process=vect_to_sym)

@lattice_page.route('/<label>')
def render_lattice_webpage(**args):
    f = None
    if 'label' in args:
        lab = clean_input(args.get('label'))
        if lab != args.get('label'):
            return redirect(url_for('.render_lattice_webpage', label=lab), 301)
        f = db.lat_lattices.lucky({'$or':[{'label': lab }, {'name': {'$contains': [lab]}}]})
    if f is None:
        t = "Integral lattice search error"
        bread = get_bread()
        flash_error("%s is not a valid label or name for an integral lattice in the database.", lab)
        return render_template("lattice-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(f)

    info['friends'] = []

    bread = get_bread(f['label'])
    info['dim']= int(f['dim'])
    info['det']= int(f['det'])
    info['level']=int(f['level'])
    info['gram']=vect_to_matrix(f['gram'])
    info['density']=str(f['density'])
    info['hermite']=str(f['hermite'])
    info['minimum']=int(f['minimum'])
    info['kissing']=int(f['kissing'])
    info['aut']=int(f['aut'])

    if f['shortest']=="":
        info['shortest']==f['shortest']
    else:
        if f['dim']==1:
            info['shortest']=str(f['shortest']).strip('[').strip(']')
        else:
            if info['dim']*info['kissing']<100:
                info['shortest']=[str([tuple(v)]).strip('[').strip(']').replace('),', '), ') for v in f['shortest']]
            else:
                max_vect_num=min(int(round(100/(info['dim']))), int(round(info['kissing']/2))-1)
                info['shortest']=[str([tuple(f['shortest'][i])]).strip('[').strip(']').replace('),', '), ') for i in range(max_vect_num+1)]
                info['all_shortest']="no"
        info['download_shortest'] = [
            (i, url_for(".render_lattice_webpage_download", label=info['label'], lang=i, obj='shortest_vectors')) for i in ['gp', 'magma','sage']]

    if f['name']==['Leech']:
        info['shortest']=[str([1,-2,-2,-2,2,-1,-1,3,3,0,0,2,2,-1,-1,-2,2,-2,-1,-1,0,0,-1,2]),
str([1,-2,-2,-2,2,-1,0,2,3,0,0,2,2,-1,-1,-2,2,-1,-1,-2,1,-1,-1,3]), str([1,-2,-2,-1,1,-1,-1,2,2,0,0,2,2,0,0,-2,2,-1,-1,-1,0,-1,-1,2])]
        info['all_shortest']="no"
        info['download_shortest'] = [
            (i, url_for(".render_lattice_webpage_download", label=info['label'], lang=i, obj='shortest_vectors')) for i in ['gp', 'magma','sage']]

    ncoeff=20
    if f['theta_series'] != "":
        coeff=[f['theta_series'][i] for i in range(ncoeff+1)]
        info['theta_series']=my_latex(print_q_expansion(coeff))
        info['theta_display'] = url_for(".theta_display", label=f['label'], number="")

    info['class_number']=int(f['class_number'])

    if f['dim']==1:
        info['genus_reps']=str(f['genus_reps']).strip('[').strip(']')
    else:
        if info['dim']*info['class_number']<50:
            info['genus_reps']=[vect_to_matrix(n) for n in f['genus_reps']]
        else:
            max_matrix_num=min(int(round(25/(info['dim']))), info['class_number'])
            info['all_genus_rep']="no"
            info['genus_reps']=[vect_to_matrix(f['genus_reps'][i]) for i in range(max_matrix_num+1)]
    info['download_genus_reps'] = [
        (i, url_for(".render_lattice_webpage_download", label=info['label'], lang=i, obj='genus_reps')) for i in ['gp', 'magma','sage']]

    if f['name'] != "":
        if f['name']==str(f['name']):
            info['name']= str(f['name'])
        else:
            info['name']=str(", ".join(str(i) for i in f['name']))
    else:
        info['name'] == ""
    info['comments']=str(f['comments'])
    if 'Leech' in info['comments']: # no need to duplicate as it is in the name
        info['comments'] = ''
    if info['name'] == "":
        t = "Integral lattice %s" % info['label']
    else:
        t = "Integral lattice "+info['label']+" ("+info['name']+")"
#This part code was for the dynamic knowl with comments, since the test is displayed this is redundant
#    if info['name'] != "" or info['comments'] !="":
#        info['knowl_args']= "name=%s&report=%s" %(info['name'], info['comments'].replace(' ', '-space-'))
    info['properties'] = [
        ('Dimension', prop_int_pretty(info['dim'])),
        ('Determinant', prop_int_pretty(info['det'])),
        ('Level', prop_int_pretty(info['level']))]
    if info['class_number'] == 0:
        info['properties']=[('Class number', 'not available')]+info['properties']
    else:
        info['properties']=[('Class number', prop_int_pretty(info['class_number']))]+info['properties']
    info['properties']=[('Label', '%s' % info['label'])]+info['properties']
    downloads = [("Underlying data", url_for(".lattice_data", label=lab))]

    if info['name'] != "":
        info['properties']=[('Name','%s' % info['name'] )]+info['properties']
#    friends = [('L-series (not available)', ' ' ),('Half integral weight modular forms (not available)', ' ')]
    return render_template(
        "lattice-single.html",
        info=info,
        title=t,
        bread=bread,
        properties=info['properties'],
        downloads=downloads,
        learnmore=learnmore_list(),
        KNOWL_ID="lattice.%s"%info['label'])
#friends=friends

def vect_to_sym(v):
    n = ZZ(round((-1+sqrt(1+8*len(v)))/2))
    M = matrix(n)
    k = 0
    for i in range(n):
        for j in range(i, n):
            M[i,j] = v[k]
            M[j,i] = v[k]
            k=k+1
    return [[int(M[i,j]) for i in range(n)] for j in range(n)]

@lattice_page.route('/data/<label>')
def lattice_data(label):
    if not lattice_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    title = f"Lattice data - {label}"
    return datapage(label, "lat_lattices", title=title, bread=bread)

#auxiliary function for displaying more coefficients of the theta series
@lattice_page.route('/theta_display/<label>/<number>')
def theta_display(label, number):
    try:
        number = int(number)
    except Exception:
        number = 20
    if number < 20:
        number = 30
    if number > 150:
        number = 150
    data = db.lat_lattices.lookup(label, projection=['theta_series'])
    coeff=[data['theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)


#data quality pages
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
    res = db.lat_lattices.lookup(label)
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    outstr = c + ' Full list of normalized minimal vectors downloaded from the LMFDB on %s. \n\n'%(mydate)
    outstr += download_assignment_start[lang] + '\\\n'
    if res['name']==['Leech']:
        outstr += str(res['shortest']).replace("'", "").replace("u", "")
    else:
        outstr += str(res['shortest'])
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


def download_lattice_full_lists_g(**args):
    label = str(args['label'])
    res = db.lat_lattices.lookup(label, projection=['genus_reps'])
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + ' Full list of genus representatives downloaded from the LMFDB on %s. \n\n'%(mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join(entry(r) for r in res['genus_reps'])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

class LatSearchArray(SearchArray):
    noun = "lattice"
    plural_noun = "lattices"
    sorts = [("", "dimension", ['dim', 'det', 'level', 'class_number', 'label']),
             ("det", "determinant", ['det', 'dim', 'level', 'class_number', 'label']),
             ("level", "level", ['level', 'dim', 'det', 'class_number', 'label']),
             ("class_number", "class number", ['class_number', 'dim', 'det', 'level', 'label']),
             ("minimum", "minimal vector length", ['minimum', 'dim', 'det', 'level', 'class_number', 'label']),
             ("aut", "automorphism group", ['aut', 'dim', 'det', 'level', 'class_number', 'label'])]
    def __init__(self):
        dim = TextBox(
            name="dim",
            label="Dimension",
            knowl="lattice.dimension",
            example="3",
            example_span="3 or 2-5")
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
        aut = TextBox(
            name="aut",
            label="Automorphism group order",
            short_label="Aut. group order",
            knowl="lattice.group_order",
            example="2",
            example_span="696729600")
        count = CountBox()

        self.browse_array = [[dim], [det], [level], [gram], [minimum], [class_number], [aut], [count]]

        self.refine_array = [[dim, det, level, gram], [minimum, class_number, aut]]
