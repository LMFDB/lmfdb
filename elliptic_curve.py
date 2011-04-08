 # -*- coding: utf-8 -*-
import re

from pymongo import ASCENDING
import base
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response


from utilities import ajax_more, image_src, web_latex, to_dict, parse_range
import sage.all 
from sage.all import ZZ, EllipticCurve, latex, matrix,srange
q = ZZ['x'].gen()

#########################
#   Utility functions
#########################

cremona_label_regex = re.compile(r'(\d+)([a-z])+(\d*)')
sw_label_regex=re.compile(r'sw(\d+)(\.)(\d+)(\.*)(\d*)')

def format_ainvs(ainvs):
    """
    The a-invariants are stored as a list of strings because mongodb doesn't
    have big-ints, and all strings are stored as unicode. However, printing 
    a list of unicodes looks like [u'0', u'1', ...]
    """
    return [int(a) for a in ainvs]

def xintegral_point(s):
    """
    parses integral points
    """
    return [int(a) for a in eval(s) if a not in ['[',',',']']] 

def proj_to_aff(s):
    r"""
    This is used to convert projective coordinates to affine for integral points
    """

    fulllist=[]
    for x in s:
        L=[]
        for y in x:
            if y !=':'and len(L)<2 :
                L.append(y)
        fulllist.append(tuple(L))
    return fulllist
    
def parse_gens(s):
    r"""
    Converts projective coordinates to affine coordinates for generator
    """    
    fulllist=[]
    for g in s:
        g1=g.replace('(', ' ').replace(')',' ').split(':')
        fulllist.append((eval(g1[0]),eval(g1[1])))
    return fulllist
    
#########################
#    Top level
#########################

@app.route("/EC")
def EC_redirect():
    return redirect(url_for("rational_elliptic_curves", **request.args))

@app.route("/EllipticCurve")
def EC_toplevel():
    return redirect(url_for("rational_elliptic_curves", **request.args))

#########################
#  Search/navigate
#########################

@app.route("/EllipticCurve/Q")
def rational_elliptic_curves():
    if len(request.args) != 0:
        return elliptic_curve_search(**request.args)
    conductor_list_endpoints = [1,100,1000,5000] + range(10000,130001,10000)
    conductor_list = ["%s-%s" % (start,end-1) for start, end in zip(conductor_list_endpoints[:-1], conductor_list_endpoints[1:])]
    info = {
        'rank_list': range(6),
        'torsion_list': [1,2,3,4,5,6,7,8,9,10,12,16], 
        'conductor_list': conductor_list,
    }
    credit = 'John Cremona'
    t = 'Elliptic curves over \(\mathbb{Q}\)'
    bread = [('Elliptic Curves', url_for("rational_elliptic_curves")),('Elliptic curves over \(\mathbb{Q}\)',' ')]
    return render_template("elliptic_curve/elliptic_curve_Q.html", info = info, credit=credit, title = t,bread=bread)

@app.route("/EllipticCurve/Q/<int:conductor>")
def by_conductor(conductor):
    return elliptic_curve_search(conductor=conductor, **request.args)


def elliptic_curve_search(**args):
    info = to_dict(args)
    query = {}
    if 'jump' in args:
        label = info.get('label', '')
        m = cremona_label_regex.match(label)
        if m:
            N, iso, number = cremona_label_regex.match(label).groups()
            if number:
                return render_curve_webpage_by_label(label=label)
            else:
                return render_isogeny_class(str(N)+iso)
        else:
            query['label'] = label
    for field in ['conductor', 'torsion', 'rank']:
        if info.get(field):
            query[field] = parse_range(info[field])
    #if info.get('iso'):
        #query['isogeny'] = parse_range(info['isogeny'], str)
    if 'optimal' in info:
        query['number'] = 1
    info['query'] = query
    res = (base.getDBConnection().ellcurves.curves.find(query)
        .sort([('conductor', ASCENDING), ('iso', ASCENDING), ('number', ASCENDING)])
        .limit(500)) # TOOD: pages
    info['curves'] = res
    info['format_ainvs'] = format_ainvs
    credit = 'John Cremona'
    t = 'Elliptic curves over \(\mathbb{Q}\)'
    bread = [('Elliptic Curves', url_for("rational_elliptic_curves")),('Elliptic Curves over \(\mathbb{Q}\)', url_for("rational_elliptic_curves")),('search results',' ')]
    return render_template("elliptic_curve/elliptic_curve_search.html",  info = info, credit=credit,bread=bread, title = t)
    

##########################
#  Specific curve pages
##########################

@app.route("/EllipticCurve/Q/<label>")
def by_ec_label(label):
    try:
        N, iso, number = cremona_label_regex.match(label).groups()
    except:
        N,d1, iso,d2, number = sw_label_regex.match(label).groups()
    if number:
        return render_curve_webpage_by_label(label=label)
    else:
        return render_isogeny_class(label)
    
def render_isogeny_class(iso_class):
    info = {}
    credit = 'John Cremona'
    label=iso_class

    C = base.getDBConnection()
    data = C.ellcurves.isogeny.find_one({'label': label})
    if data is None:
        return "No such isogeny class"
    ainvs = [int(a) for a in data['ainvs_for_optimal_curve']]
    E = EllipticCurve(ainvs)
    info = {'label': label}
    info['optimal_ainvs'] = ainvs
    if 'imag' in data:
        info['imag']=data['imag']
    if 'real' in data:
        info['real']=data['real']
    info['rank'] = data['rank'] 
    info['isogeny_matrix']=latex(matrix(eval(data['isogeny_matrix'])))
    info['modular_degree']=data['degree']
    info['f'] = ajax_more(E.q_eigenform, 10, 20, 50, 100, 250)
    G = E.isogeny_graph(); n = G.num_verts()
    G.relabel(range(1,n+1)) # proper cremona labels...
    info['graph_img'] = image_src(G.plot(edge_labels=True))
    curves = data['label_of_curves_in_the_class']
    info['curves'] = list(curves)
    info['download_qexp_url'] = url_for('download_qexp', limit=100, ainvs=','.join([str(a) for a in ainvs]))
    info['download_all_url'] = url_for('download_all', label=str(label))
    friends=[('Elliptic Curve %s' % l , "/EllipticCurve/Q/%s" % l) for l in data['label_of_curves_in_the_class']]
    friends.append(('Quadratic Twist', "/quadratic_twists/%s" % (label)))
    friends.append(('Modular Form', url_for("cmf.render_classical_modular_form_from_label",label="%s" %(label))))
    info['friends'] = friends

    t= "Elliptic Curve Isogeny Class %s" % info['label']
    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('Elliptic Curves over \(\mathbb{Q}\)',url_for("rational_elliptic_curves")),('isogeny class %s' %info['label'],' ')]

    return render_template("elliptic_curve/iso_class.html", info = info,bread=bread, credit=credit,title = t)


#@app.route("/EllipticCurve/Q/<label>")
#def by_cremona_label(label):
#    try:
#        N, iso, number = cremona_label_regex.match(label).groups()
#    except:
#        N, iso, number = sw_label_regex.match(label).groups()
#    if number:
#        return render_curve_webpage_by_label(str(label))
#    else:
#        return render_isogeny_class(str(N)+iso)

#@app.route("/EllipticCurve/Q/<int:conductor>/<iso_class>/<int:number>")
#def by_curve(conductor, iso_class, number):
#    if conductor <140000:
#        return render_curve_webpage_by_label(label="%s%s%s" % (conductor, iso_class, number))
#    else:
#        return render_curve_webpage_by_label(label="sw%s.%s.%s" % (conductor, iso_class, number))
        
def render_curve_webpage_by_label(label):
    C = base.getDBConnection()
    data = C.ellcurves.curves.find_one({'label': label})
    if data is None:
        return "No such curve"    
    info = {}
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    label=data['label']
    N = ZZ(data['conductor'])
    iso_class = data['iso']
    rank = data['rank']
    j_invariant=E.j_invariant()
    plot=E.plot()
    discriminant=E.discriminant()
    xintpoints_projective=[E.lift_x(x) for x in xintegral_point(data['x-coordinates_of_integral_points'])]
    xintpoints=proj_to_aff(xintpoints_projective)
    G = E.torsion_subgroup().gens()
    
    if 'gens' in data:
        generator=parse_gens(data['gens'])
    if len(G) == 0:
        tor_struct = 'Trivial'
        tor_group='Trivial'
    else:
        tor_group=' \\times '.join(['\mathbb{Z}/{%s}\mathbb{Z}'%a.order() for a in G])
    if 'torsion_structure' in data:
        info['tor_structure']= ' \\times '.join(['\mathbb{Z}/{%s}\mathbb{Z}'% int(a) for a in data['torsion_structure']])
    else:
        info['tor_structure'] = tor_group
        
    info.update(data)
    info.update({
        'conductor': N,
        'disc_factor': latex(discriminant.factor()),
        'j_invar_factor':latex(j_invariant.factor()),
        'label': label,
        'isogeny':iso_class,
        'equation': web_latex(E),
        'f': ajax_more(E.q_eigenform, 10, 20, 50, 100, 250),
        'generators':','.join(web_latex(g) for g in generator) if 'gens' in data else ' ',
        'lder'  : "L%s(1)" % ("'"*rank),
        'p_adic_primes': [p for p in sage.all.prime_range(5,100) if E.is_ordinary(p) and not p.divides(N)],
        'ainvs': format_ainvs(data['ainvs']),
        'tamagawa_numbers': r' \cdot '.join(str(sage.all.factor(c)) for c in E.tamagawa_numbers()),
        'cond_factor':latex(N.factor()),
        'xintegral_points':','.join(web_latex(i_p) for i_p in xintpoints),
        'tor_gens':','.join(web_latex(eval(g)) for g in data['torsion_generators']) if 'torsion_generators' in data else list(G)
                        })
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet', url_for("not_yet_implemented"))]
    info['friends'] = [('Isogeny class', "/EllipticCurve/Q/%s/%s" % (N, iso_class)),
                       ('Modular Form', url_for("cmf.render_classical_modular_form_from_label",label="%s" %(iso_class))),
                       ('L-function', "/L/EllipticCurve/Q/%s" % label)]
    info['learnmore'] = [('Elliptic Curves', url_for("not_yet_implemented"))]
    info['plot'] = image_src(plot)
    info['iso_class'] = data['iso']
    info['download_qexp_url'] = url_for('download_qexp', limit=100, ainvs=','.join([str(a) for a in ainvs]))
    properties = ['<h2>%s</h2>' % label, ' <img src="%s" width="200" height="150"/><br/><br/>' % image_src(plot),'<h2>Conductor</h2>',
    '\(%s\)<br/><br/>' % N, '<h2> Discriminant</h2>','\(%s\)<br/><br/>' % discriminant, '<h2>j-invariant</h2>','\(%s\)<br/><br/>' % j_invariant,
     '<h2>Rank</h2>','\(%s\)<br/><br/>' % rank ,'<h2>Torsion Structure</h2>', '\(%s\)<br/><br/>' % tor_group
    ]
    #properties.extend([ "prop %s = %s<br/>" % (_,_*1923) for _ in range(12) ])
    credit = 'John Cremona'
    t = "Elliptic Curve %s" % info['label']
    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('Elliptic Curves over \(\mathbb{Q}\)', url_for("rational_elliptic_curves")),('Elliptic curves %s' %info['label'],' ')]

    return render_template("elliptic_curve/elliptic_curve.html", info=info, properties=properties, credit=credit,bread=bread, title = t)

@app.route("/EllipticCurve/Q/padic_data")
def padic_data():
    info = {}
    label = request.args['label']
    p = int(request.args['p'])
    info['p'] = p
    N, iso, number = cremona_label_regex.match(label).groups()
    #print N, iso, number
    if request.args['rank'] == '0':
        info['reg'] = 1
    elif number == '1':
        C = base.getDBConnection()
        data = C.ellcurves.padic_db.find_one({'label': N + iso, 'p': p})
        info['data'] = data
        if data is None:
            info['reg'] = 'no data'
        else:
            reg = sage.all.Qp(p, data['prec'])(int(data['unit'])) * sage.all.Integer(p)**int(data['val'])
            reg = reg.add_bigoh(min(data['prec'], data['prec'] + data['val']))
            info['reg'] = web_latex(reg)
    else:
        info['reg'] = "no data"
    return render_template("elliptic_curve/elliptic_curve_padic.html", info = info)

@app.route("/EllipticCurve/Q/download_qexp")
def download_qexp():
    ainvs = request.args.get('ainvs')
    E = EllipticCurve([int(a) for a in ainvs.split(',')])
    response = make_response('\n'.join(str(an) for an in E.anlist(int(request.args.get('limit', 100)), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response

@app.route("/EllipticCurve/Q/download_all")
def download_all():
    label=(request.args.get('label'))
    C = base.getDBConnection()
    data = C.ellcurves.isogeny.find_one({'label': label})
    #all data about this isogeny
    data1=[str(c)+'='+str(data[c]) for c in data]
    curves=data['label_of_curves_in_the_class']
    #titles of all entries of curves
    lab=curves[0]
    titles_curves=[str(c) for c in C.ellcurves.curves.find_one({'label': lab})]
    data1.append(titles_curves)
    for lab in curves:
        print lab
        data_curves=C.ellcurves.curves.find_one({'label': lab})
        data1.append([data_curves[t] for t in titles_curves])
    response=make_response('\n'.join(str(an) for an in  data1))
    response.headers['Content-type'] = 'text/plain'
    return response
    
#@app.route("/EllipticCurve/Q/download_Rub_data")
#def download_Rub_data():
#    import gridfs
#    label=(request.args.get('label'))
#    type=(request.args.get('type'))
#    C = base.getDBConnection()
#    fs = gridfs.GridFS(C.ellcurves,'isogeny' )
#    isogeny=C.ellcurves.isogeny.files
#    filename=isogeny.find_one({'label':str(label),'type':str(type)})['filename']
#    d= fs.get_last_version(filename)
#    response = make_response(d.readline())
#    response.headers['Content-type'] = 'text/plain'
#    return response
