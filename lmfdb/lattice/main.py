import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

import flask
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, Flask, session, g, redirect, make_response, flash

from lmfdb import base
from lmfdb.base import app, getDBConnection
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input, web_latex_split_on_pm

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi, latex, matrix, srange, PowerSeriesRing, sqrt

from lmfdb.lattice import lattice_page, lattice_logger
from lmfdb.lattice.lattice_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list

from markupsafe import Markup

lattice_credit = 'Samuele Anni, Anna Haensch, Gabriele Nebe and Neil Sloane'


def get_bread(breads=[]):
    bc = [("Lattices", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def vect_to_matrix(v):
    return str(latex(matrix(v)))

def print_q_expansion(list):
     list=[str(c) for c in list]
     Qa=PolynomialRing(QQ,'a')
     a = QQ['a'].gen()
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


@lattice_page.route("/")
def lattice_render_webpage():
    args = request.args
    if len(args) == 0:
        counts = get_stats().counts()
        dim_list= range(2, counts['max_dim']+1, 1)
        class_number_list=range(1, counts['max_class_number']+1, 1)
        det_list_endpoints = [1, 400, 800, 1200]
        if counts['max_det']>1200:
            det_list_endpoints=det_list_endpoints+range(1200, int(round(counts['max_det']/400)+2)*400, 400)
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        info = {'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list}
        credit = lattice_credit
        t = 'Integral Lattices'
        bread = [('Integral Lattices', url_for(".lattice_render_webpage"))]
        info['learnmore'] = []
        info['counts'] = get_stats().counts()
        return render_template("lattice-index.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return lattice_search(**args)


@lattice_page.route("/random")
def random_lattice():    # Random Lattice
    from sage.misc.prandom import randint
    n = get_stats().counts()['nlattice']
    n = randint(0,n-1)
    C = getDBConnection()
    res = C.Lattices.lat.find()[n]
    return redirect(url_for(".render_lattice_webpage", label=res['label']))



def lattice_search(**args):
    C = getDBConnection()
    C.Lattices.lat.ensure_index([('dim', ASC), ('label', ASC)])
    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        lab = info.get('label')
        control= by_label_or_name(lab, C)
        if control == "ok":
            args = {'label': lab }
            return render_lattice_webpage(**args)
        else:
            check=lattice_label_error(control, lab , url_for(".lattice_render_webpage"))
            if check is not None:
                return check

    query = {}
    for field in ['dim','det','level', 'gram', 'minimum', 'class_number', 'aut']:
        if info.get(field):
            if field in ['dim', 'det', 'level', 'minimum', 'class_number', 'aut']:
                try:
                    info['start']
                    check= parse_ints(info.get(field), query, field)
                except:
                    check= parse_ints(info.get(field), query, field, url_for(".lattice_render_webpage"))
                if check is not None:
                    return check
            elif field == 'gram':
                try:
                    info['start']
                    check= parse_list(info.get(field), query, field, vect_to_sym)
                except:
                    check= parse_list(info.get(field), query, field, vect_to_sym, url_for(".lattice_render_webpage"))
                if check is not None:
                    return check
    info['query'] = dict(query)
    res = C.Lattices.lat.find(query).sort([('level', ASC), ('label', ASC)])
    nres = res.count()
    count = 100

    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count:
            info['report'] = 'displaying first %s of %s matches' % (count, nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    res_clean = []
    for v in res:
        v_clean = {}
        v_clean['label']=v['label']
        v_clean['dim']=v['dim']
        v_clean['det']=v['det']
        v_clean['level']=v['level']
        v_clean['gram']=vect_to_matrix(v['gram'])
        res_clean.append(v_clean)

    info['lattices'] = res_clean

    t = 'Integral Lattices search results'
    bread = [('Lattices', url_for(".lattice_render_webpage")),('Search results', ' ')]
    properties = []
    return render_template("lattice-search.html", info=info, title=t, properties=properties, bread=bread)


@lattice_page.route('/<label>')
def render_lattice_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        lab = args.get('label')
        data = C.Lattices.lat.find_one({'$or':[{'label': lab }, {'name': lab }]})
    if data is None:
        return "No such field %s" %args
    info = {}
    info.update(data)

    info['friends'] = []

    bread = [('Lattice', url_for(".lattice_render_webpage")), ('%s' % data['label'], ' ')]
    credit = lattice_credit
    f = C.Lattices.lat.find_one({'dim': data['dim'],'det': data['det'],'level': data['level'],'gram': data['gram'],'minimum': data['minimum'],'class_number': data['class_number'],'aut': data[ 'aut'],'name': data['name']})
    info['dim']= int(f['dim'])
    info['det']= int(f['det'])
    info['level']=int(f['level'])
    info['gram']=vect_to_matrix(f['gram'])
    info['density']=str(f['density'])
    info['hermite']=str(f['hermite'])
    info['minimum']=int(f['minimum'])
    info['kissing']=int(f['kissing'])
    info['shortest']=str([tuple(v) for v in f['shortest']]).strip('[').strip(']').replace('),', '), ')
    info['aut']=int(f['aut'])

    ncoeff=20
    coeff=[f['theta_series'][i] for i in range(ncoeff+1)]
    info['theta_series']=my_latex(print_q_expansion(coeff))
    info['theta_display'] = url_for(".theta_display", label=f['label'], number="")

    info['class_number']=int(f['class_number'])
    info['genus_reps']=[vect_to_matrix(n) for n in f['genus_reps']]
    info['name']=str(f['name'])
    info['comments']=str(f['comments'])
    if info['name'] == "":
        t = "Integral Lattice %s" % info['label']
    else:
        t = "Integral Lattice "+info['label']+" ("+info['name']+")"
    if info['name'] != "" or info['comments'] !="":
        info['knowl_args']= "name=%s&report=%s" %(info['name'], info['comments'].replace(' ', '-space-'))
    info['properties'] = [
        ('Label', '$%s$' % info['label']),
        ('Dimension', '$%s$' % info['dim']),
        ('Gram matrix', '$%s$' % info['gram'])
        ]
    if info['name'] != "" :
        info['properties'].append(('Name','%s' % info['name'] ))
    friends = [('L-series (not available)', ' ' ),('Half integral weight modular forms (not available)', ' ')]
    return render_template("lattice-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], friends=friends)



lmfdb_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_lmfdb_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def by_label_or_name(lab, C):
    try:
        dim, det, level, class_number, number = split_lmfdb_label(lab)
    except:
        try:
            data = C.Lattices.lat.find_one({'name' : lab })
        except:
            return "missing_lattice_name"
    data = C.Lattices.lat.find_one({'$or':[{'label': lab }, {'name': lab }]})
    if data:
        return "ok"
    return "missing_lattice" 


def lattice_label_error(err_msg, lab, url):
    if err_msg=="missing_lattice_name":
        flash(Markup("No integral lattice in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
    elif err_msg=="missing_lattice":
        flash(Markup("The integral lattice <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    if url is not None:
        return redirect(url)


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





@lattice_page.route('/theta_display/<label>/<number>')
def theta_display(label, number):
    try:
        number = int(number)
    except:
        number = 30
    if number < 30:
        number = 30
    if number > 150:
        number = 150
    C = getDBConnection()
    data = C.Lattices.lat.find_one({'label': label})
    coeff=[data['theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)
