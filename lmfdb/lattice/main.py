import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

import flask
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, Flask, session, g, redirect, make_response, flash

from lmfdb import base
from lmfdb.base import app, getDBConnection
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, make_logger, web_latex_split_on_pm, comma

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi, latex, matrix, srange, PowerSeriesRing, sqrt, QuadraticForm

from lmfdb.lattice import lattice_page, lattice_logger
from lmfdb.lattice.lattice_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list

from markupsafe import Markup

lattice_credit = 'Samuele Anni, Anna Haensch, Gabriele Nebe and Neil Sloane'



# usiliary functions for displays 

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

#breadcrumbs and links for data quality entries

def get_bread(breads=[]):
    bc = [("Lattice", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for integral lattices', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@lattice_page.route("/")
def lattice_render_webpage():
    args = request.args
    if len(args) == 0:
        counts = get_stats().counts()
        dim_list= range(2, counts['max_dim']+1, 1)
        class_number_list=range(1, counts['max_class_number']+1, 1)
        det_list_endpoints = [1, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
#        if counts['max_det']>3000:
#            det_list_endpoints=det_list_endpoints+range(3000, max(int(round(counts['max_det']/1000)+2)*1000, 10000), 1000)
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        info = {'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list}
        credit = lattice_credit
        t = 'Integral Lattices'
        bread = [('Lattice', url_for(".lattice_render_webpage"))]
        info['counts'] = get_stats().counts()
        return render_template("lattice-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
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


lattice_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_lattice_label(lab):
    return lattice_label_regex.match(lab).groups()

def lattice_by_label_or_name(lab, C):
    if C.Lattices.lat.find({'$or':[{'label': lab}, {'name': lab}]}).limit(1).count() > 0:
        return render_lattice_webpage(label=lab)
    if lattice_label_regex.match(lab):
        flash(Markup("The integral lattice <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No integral lattice in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".lattice_render_webpage"))

def lattice_search(**args):
    C = getDBConnection()
#    C.Lattices.lat.ensure_index([('dim', ASC), ('label', ASC)])
    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info and info.get('label'):
        return lattice_by_label_or_name(info.get('label'), C)
    query = {}
    try:
        for field, name in (('dim','Dimension'),('det','Determinant'),('level',None),
                            ('minimum','Minimal vector length'), ('class_number',None), ('aut','Group order')):
            parse_ints(info, query, field, name)
        # Check if length of gram is triangular
        gram = info.get('gram')
        if gram and not (9 + 8*ZZ(gram.count(','))).is_square():
            flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for Gram matrix.  It must be a list of integer vectors of triangular length, such as [1,2,3]." % (gram)),"error")
            raise ValueError
        parse_list(info, query, 'gram', process=vect_to_sym)
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info)

    count_default = 50
    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            err = "Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a positive integer." % info['count']
            flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a positive integer." % info['count']), "error")
            info['err'] = str(err)
            return search_input_error(info)
    else:
        info['count'] = count_default
        count = count_default

    start_default = 0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default

    info['query'] = dict(query)
    res = C.Lattices.lat.find(query).sort([('dim', ASC), ('det', ASC), ('label', ASC)]).skip(start).limit(count)
    nres = res.count()

    # here we are checking for isometric lattices if the user enters a valid gram matrix but not one stored in the database_names, this may become slow in the future: at the moment we compare against list of stored matrices with same dimension and determinant (just compare with respect to dimension is slow)

    if nres==0 and info.get('gram'):
        A=query['gram'];
        n=len(A[0])
        d=matrix(A).determinant()
        result=[B for B in C.Lattices.lat.find({'dim': int(n), 'det' : int(d)}) if isom(A, B['gram'])==True]
        if len(result)>0:
            result=result[0]['gram']
            query_gram={ 'gram' : result }
            query.update(query_gram)
            res = C.Lattices.lat.find(query)
            nres = res.count()

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['number'] = nres
    info['start'] = int(start)
    info['more'] = int(start + count < nres)
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres == 0:
            info['report'] = 'no matches'
        else:
            if nres > count or start != 0:
                info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
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

    t = 'Integral Lattices Search Results'
    bread = [('Lattices', url_for(".lattice_render_webpage")),('Search Results', ' ')]
    properties = []
    return render_template("lattice-search.html", info=info, title=t, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info, bread=None):
    t = 'Integral Lattices Search Error'
    if bread is None:
        bread = [('Lattices', url_for(".lattice_render_webpage")),('Search Results', ' ')]
    return render_template("lattice-search.html", info=info, title=t, properties=[], bread=bread, learnmore=learnmore_list())

@lattice_page.route('/<label>')
def render_lattice_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        lab = args.get('label')
        data = C.Lattices.lat.find_one({'$or':[{'label': lab }, {'name': lab }]})
    if data is None:
        t = "Integral Lattices Search Error"
        bread = [('Lattice', url_for(".lattice_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label or name for an integral lattice in the database." % (lab)),"error")
        return render_template("lattice-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
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
    info['shortest']=[str([tuple(v)]).strip('[').strip(']').replace('),', '), ') for v in f['shortest']]
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
    return render_template("lattice-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], friends=friends, learnmore=learnmore_list())

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


# function for checking isometries
def isom(A,B):
    # First check that A is a symmetric matrix.
    if not matrix(A).is_symmetric():
        return False
    # Then check A against the viable database candidates.
    else:
        n=len(A[0])
        m=len(B[0])
        Avec=[]
        Bvec=[]
        for i in range(n):
            for j in range(i,n):
                if i==j:
                    Avec+=[A[i][j]]
                else:
                    Avec+=[2*A[i][j]]
        for i in range(m):
            for j in range(i,m):
                if i==j:
                    Bvec+=[B[i][j]]
                else:
                    Bvec+=[2*B[i][j]]
        Aquad=QuadraticForm(ZZ,len(A[0]),Avec)
    # check positive definite
        if Aquad.is_positive_definite():
            Bquad=QuadraticForm(ZZ,len(B[0]),Bvec)
            return Aquad.is_globally_equivalent_to(Bquad)
        else:
            return False


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
    C = getDBConnection()
    data = C.Lattices.lat.find_one({'label': label})
    coeff=[data['theta_series'][i] for i in range(number+1)]
    return print_q_expansion(coeff)


#data quality pages
@lattice_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the integral lattice data'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Completeness', '')]
    credit = lattice_credit
    return render_template("single.html", kid='dq.lattice.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@lattice_page.route("/Source")
def how_computed_page():
    t = 'Source of integral lattice data'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Source', '')]
    credit = lattice_credit
    return render_template("single.html", kid='dq.lattice.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@lattice_page.route("/Labels")
def labels_page():
    t = 'Label of an integral lattice'
    bread = [('Lattice', url_for(".lattice_render_webpage")),
             ('Labels', '')]
    credit = lattice_credit
    return render_template("single.html", kid='lattice.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

