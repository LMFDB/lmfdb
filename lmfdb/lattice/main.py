import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input

import sage.all

from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi, latex, matrix, srange, PowerSeriesRing

from lmfdb.lattice import lattice_page, lattice_logger

lattice_credit = 'Samuele Anni, Anna Haensch, Gabriele Nebe and Neil Sloane'


def get_bread(breads=[]):
    bc = [("Lattices", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')



def vect_to_matrix(v):
	return latex(matrix(v))	


@lattice_page.route("/")
def index():
    bread = get_bread([])
    info = {}
    friends=[]
    return render_template("lattice-index.html", title="Integral Lattices", bread=bread, credit=lattice_credit, info=info, friends=friends)


@lattice_page.route("/")
def lattice_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = lattice_credit
        t = 'Integral Lattices'
        bread = [('Integral Lattices', url_for(".lattice_render_webpage"))]
        info['learnmore'] = []
        return render_template("lattice-index.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return lattice_search(**args)


def lattice_search(**args):
    C = getDBConnection()
    C.Lattices.lat.ensure_index([('dim', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])

    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        args = {'label': info['label']}
        return render_lattice_webpage(**args)
    query = {}
    for field in ['dim','det','level', 'gram', 'minimum', 'class_number', 'aut', 'name']:
        if info.get(field):
		if field == 'dim':
			query[field] = int(info[field])
		elif field == 'det':
			query[field] = int(info[field])
		elif field == 'level':
			query[field] = int(info[field])
		elif field == 'gram':
			query[field] = parse_field_string(info[field])
		elif field == 'minimum':
			query[field] = int(info[field])
		elif field == 'class_number':
			query[field] = int(info[field])
		elif field == 'aut':
			query[field] = int(info[field])
		elif field == 'name':
			query[field] = parse_field_string(info[field])
    info['query'] = dict(query)
    res = C.Lattices.lat.find(query).sort([('level', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])
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
	v_clean['dim']=v['dim']
	v_clean['det']=v['det']
	v_clean['level']=v['level']
	v_clean['gram']=vect_to_matrix(v['gram'])
        res_clean.append(v_clean)

    info['lattices'] = res_clean

    t = 'Integral Lattices search results'
    bread = [('Lattices', url_for(".lattice_render_webpage")),('Search results', ' ')]
    properties = []
    return render_template("lattice_search.html", info=info, title=t, properties=properties, bread=bread)



@lattice_page.route('/<label>')
def render_lattice_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        label = str(args['label'])
        data = C.Lattices.lat.find_one({'label': label})
    if data is None:
        return "No such field"
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
    info['shortest']=str(f['shortest'])
    info['aut']=int(f['aut'])
    info['theta_series']=str(f['theta_series'])
    info['class_number']=int(f['class_number'])
    info['genus_reps']=vect_to_matrix(f['genus_reps'])
    info['name']=str(f['name'])
    info['comments']=str(f['comments'])

    if info['name'] == "":
	t = "Integral Lattice %s" % info['label']
    else:
	t = "Integral Lattice %s" % info['label'] % info['name']

    return render_template("lattice-single.html", info=info, credit=credit, title=t, bread=bread)



