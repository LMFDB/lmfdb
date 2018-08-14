# -*- coding: utf-8 -*-
import re
import time
import ast
import StringIO

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

from flask import render_template, request, url_for, redirect, make_response, flash,  send_file
from markupsafe import Markup

from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt

from lmfdb.utils import web_latex_split_on_pm
from lmfdb.search_parsing import parse_ints, parse_list, parse_count, parse_start, clean_input
from lmfdb.search_wrapper import search_wrap

from lmfdb.lattice import lattice_page
from lmfdb.lattice.lattice_stats import lattice_summary, lattice_summary_data
from lmfdb.lattice.isom import isom

lattice_credit = 'Samuele Anni, Stephan Ehlen, Anna Haensch, Gabriele Nebe and Neil Sloane'

# Database connection

from lmfdb.db_backend import db

# utilitary functions for displays 

def vect_to_matrix(v):
    return str(latex(matrix(v)))

def print_q_expansion(list):
     list=[str(c) for c in list]
     Qa=PolynomialRing(QQ,'a')
     Qq=PowerSeriesRing(Qa,'q')
     return web_latex_split_on_pm(Qq([c for c in list]).add_bigoh(len(list)))

def my_latex(s):
    ss = ""
    ss += re.sub('x\d', 'x', s)
    ss = re.sub("\^(\d+)", "^{\\1}", ss)
    ss = re.sub('\*', '', ss)
    ss = re.sub('zeta(\d+)', 'zeta_{\\1}', ss)
    ss = re.sub('zeta', '\zeta', ss)
    ss += ""
    return ss

#breadcrumbs and links for data quality entries

def get_bread(breads=[]):
    bc = [("Lattice", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for integral lattices', url_for(".labels_page")),
            ('History of lattices', url_for(".history_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@lattice_page.route("/")
def lattice_render_webpage():
    args = request.args
    if len(args) == 0:
        maxs=lattice_summary_data()
        dim_list= range(1, 11, 1)
        max_class_number=20
        class_number_list=range(1, max_class_number+1, 1)
        det_list_endpoints = [1, 5000, 10000, 20000, 25000, 30000]
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        name_list = ["A2","Z2", "D3", "D3*", "3.1942.3884.56.1", "A5", "E8", "A14", "Leech"]
        info = {'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list, 'name_list': name_list}
        credit = lattice_credit
        t = 'Integral Lattices'
        bread = [('Lattice', url_for(".lattice_render_webpage"))]
        info['summary'] = lattice_summary()
        info['max_cn']=maxs[0]
        info['max_dim']=maxs[1]
        info['max_det']=maxs[2]
        return render_template("lattice-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list(), bread=bread)
    else:
        return lattice_search(args)

# Random Lattice
@lattice_page.route("/random")
def random_lattice():
    return redirect(url_for(".render_lattice_webpage", label=db.lat_lattices.random()), 307)


lattice_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_lattice_label(lab):
    return lattice_label_regex.match(lab).groups()

def lattice_by_label_or_name(lab):
    clean_lab=str(lab).replace(" ","")
    clean_and_cap=str(clean_lab).capitalize()
    for l in [lab, clean_lab, clean_and_cap]:
        label = db.lat_lattices.lucky({'$or':[{'label': l}, {'name': l}]}, 'label')
        if label is not None:
            return redirect(url_for(".render_lattice_webpage", label=label))
    if lattice_label_regex.match(lab):
        flash(Markup("The integral lattice <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No integral lattice in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
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
    s += c + ' Integral Lattices downloaded from the LMFDB on %s. Found %s lattices.\n\n'%(mydate, len(res))
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\\\n'
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])
    # loop through all search results and grab the gram matrix
    s += ",\\\n".join([entry(gram) for gram in res])
    s += list_end
    s += download_assignment_end[lang]
    s += '\n'
    strIO = StringIO.StringIO()
    strIO.write(s)
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

    for v in res:
        v['min'] = v.pop('minimum')
    return res

@search_wrap(template="lattice-search.html",
             table=db.lat_lattices,
             title='Integral Lattices Search Results',
             err_title='Integral Lattices Search Error',
             shortcuts={'download':download_search,
                        'label':lambda info:lattice_by_label_or_name(info.get('label'))},
             projection=lattice_search_projection,
             postprocess=lattice_search_isometric,
             bread=lambda:[('Lattices', url_for(".lattice_render_webpage")),('Search Results', ' ')],
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
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3]." % (gram)),"error")
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
        t = "Integral Lattices Search Error"
        bread = [('Lattices', url_for(".lattice_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label or name for an integral lattice in the database." % (lab)),"error")
        return render_template("lattice-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(f)

    info['friends'] = []

    bread = [('Lattice', url_for(".lattice_render_webpage")), ('%s' % f['label'], ' ')]
    credit = lattice_credit
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
                max_vect_num=min(int(round(100/(info['dim']))), int(round(info['kissing']/2))-1);
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
            max_matrix_num=min(int(round(25/(info['dim']))), info['class_number']);
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
        t = "Integral Lattice %s" % info['label']
    else:
        t = "Integral Lattice "+info['label']+" ("+info['name']+")"
#This part code was for the dinamic knowl with comments, since the test is displayed this is redundant
#    if info['name'] != "" or info['comments'] !="":
#        info['knowl_args']= "name=%s&report=%s" %(info['name'], info['comments'].replace(' ', '-space-'))
    info['properties'] = [
        ('Dimension', '%s' %info['dim']),
        ('Determinant', '%s' %info['det']),
        ('Level', '%s' %info['level'])]
    if info['class_number'] == 0:
        info['properties']=[('Class number', 'not available')]+info['properties']
    else:
        info['properties']=[('Class number', '%s' %info['class_number'])]+info['properties']
    info['properties']=[('Label', '%s' % info['label'])]+info['properties']

    if info['name'] != "" :
        info['properties']=[('Name','%s' % info['name'] )]+info['properties']
#    friends = [('L-series (not available)', ' ' ),('Half integral weight modular forms (not available)', ' ')]
    return render_template("lattice-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list())
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


#auxiliary function for displaying more coefficients of the theta series
@lattice_page.route('/theta_display/<label>/<number>')
def theta_display(label, number):
    try:
        number = int(number)
    except:
        number = 20
    if number < 20:
        number = 30
    if number > 150:
        number = 150
    data = db.lat_lattices.lookup(label, projection=['theta_series'])
    coeff=[data['theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)


#data quality pages
@lattice_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Integral Lattice Data'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Completeness', '')]
    credit = lattice_credit
    return render_template("single.html", kid='dq.lattice.completeness',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@lattice_page.route("/Source")
def how_computed_page():
    t = 'Source of the Integral Lattice Data'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Source', '')]
    credit = lattice_credit
    return render_template("single.html", kid='dq.lattice.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@lattice_page.route("/Labels")
def labels_page():
    t = 'Label of an Integral Lattice'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Labels', '')]
    credit = lattice_credit
    return render_template("single.html", kid='lattice.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@lattice_page.route("/History")
def history_page():
    t = 'A Brief History of Lattices'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('History', '')]
    credit = lattice_credit
    return render_template("single.html", kid='lattice.history',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('History'))

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
    outstr += ",\\\n".join([entry(r) for r in res['genus_reps']])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr
