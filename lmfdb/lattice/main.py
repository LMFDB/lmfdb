import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ, latex

from lmfdb.lattice import lattice_page, lattice_logger

lattice_credit = 'Samuele Anni, Anna Haensch, Gabriele Nebe and Neil Sloane'


def get_bread(breads=[]):
    bc = [("Lattices", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')


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
    for field in ['dim','det','level', 'gram', 'minimum', 'class_number', 'aut', 'theta_weight', 'name']:
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
	v_clean['gram']=v['gram']
	v_clean['density']=v['density']
	v_clean['hermite']=v['hermite']
	v_clean['minimum']=v['minimum']
	v_clean['kissing']=v['kissing']
	v_clean['shortest']=v['shortest']
	v_clean['aut']=v['aut']
	v_clean['theta_series']=v['theta_series']
	v_clean['class_number']=v['class_number']
	v_clean['genus_reps']=v['genus_reps']
	v_clean['name']=v['name']
	v_clean['comments']=v['comments']
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
        label = str(args['label'])
        data = C.Lattices.lat.find_one({'label': label})
    if data is None:
        return "No such field"
    info = {}
    info.update(data)

    info['friends'] = []

    bread = [('Lattice', url_for(".lattice_render_webpage")), ('%s' % data['label'], ' ')]
    t = "Integral Lattice %s" % info['label']
    credit = lattice_credit
    f = C.halfintegralmf.forms.find_one({'dim': data['dim'],'det': data['det'],'level': data['level'],'gram': data['gram'],'minimum': data['minimum'],'class_number': data['class_number'],'aut': data[ 'aut'],'name': data['name']})
 
    dim = f['dim']
    dimtheta = f['dimtheta']
    dimnew=dim-dimtheta	
    info['dimension'] = dim
    info['dimtheta']= dimtheta
    info['dimnew'] = dimnew
    chi = f['character']
    info['ch_lab']= chi.replace('.','/')
    chi1=chi.split(".")	
    chi2="\chi_{"+chi1[0]+"}("+chi1[1]+",\cdot)"	
    info['char']= chi2
    new=[]
    for n in f['newpart']:
	v= {}	
        v['dim'] = n['dim_image']
	s=[]
	for h in n['half_forms']:
		s.append(my_latex_from_qexp(print_q_expansion(h)))		
        v['lattice'] = s
        v['mf'] = n['mf_label']
	v['nf'] = n['nf_label']
	new.append(v)
    info['new']= new
    if dimtheta !=0:
	theta=[]
	for m in f['thetas']:
		for n in m:
			n_lab= n.replace('.','/')
			n_l=n.split(".")	
		    	n_lat="\chi_{"+n_l[0]+"}("+n_l[1]+",\cdot)"	
			v=[n_lab, n_lat]
			theta.append(v)
	info['theta']= theta
    else:
	info['theta']= f['thetas']
    return render_template("lattice-single.html", info=info, credit=credit, title=t, bread=bread)



