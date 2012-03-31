# -*- coding: utf-8 -*-
import re

from pymongo import ASCENDING
import base
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
import tempfile
import os

from utils import ajax_more, image_src, web_latex, to_dict, parse_range2, web_latex_split_on_pm, make_logger
logger = make_logger("EllipticCurve")
from number_fields.number_field import parse_list
import sage.all 
from sage.all import ZZ, EllipticCurve, latex, matrix,srange
q = ZZ['x'].gen()

#########################
#   Utility functions
#########################

ncurves = max_N = max_rank = None
init_ecdb_flag = False

def init_ecdb_count():
    global ncurves, max_N, max_rank, init_ecdb_flag
    if not init_ecdb_flag:
        ecdb = base.getDBConnection().elliptic_curves.curves
        ncurves = ecdb.count()
        max_N = max(ecdb.distinct('conductor'))
        max_rank = max(ecdb.distinct('rank'))
        init_ecdb_flag = True

cremona_label_regex = re.compile(r'(\d+)([a-z]+)(\d*)')
lmfdb_label_regex = re.compile(r'(\d+)\.([a-z]+)(\d*)')
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
        x,y,z = [ZZ(str(c)) for c in g1]
        fulllist.append((x/z,y/z))
    return fulllist

def cmp_label(lab1,lab2):
    from sage.databases.cremona import parse_cremona_label, class_to_int
    a,b,c = parse_cremona_label(lab1)
    id1 = int(a),class_to_int(b),int(c)
    a,b,c = parse_cremona_label(lab2)
    id2 = int(a),class_to_int(b),int(c)
    return cmp(id1,id2)
    
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
    init_ecdb_count()
    info = {
        'rank_list': range(max_rank+1),
        'torsion_list': [1,2,3,4,5,6,7,8,9,10,12,16], 
        'conductor_list': conductor_list,
        'ncurves': ncurves,
        'max_N': max_N,
        'max_rank': max_rank
    }
    credit = 'John Cremona'
    t = 'Elliptic curves/$\mathbb{Q}$'
    bread = [('Elliptic Curves', url_for("rational_elliptic_curves")),('Elliptic curves/$\mathbb{Q}$',' ')]
    return render_template("elliptic_curve/elliptic_curve_Q.html", info = info, credit=credit, title = t,bread=bread)

@app.route("/EllipticCurve/Q/<int:conductor>")
def by_conductor(conductor):
    return elliptic_curve_search(conductor=conductor, **request.args)


def elliptic_curve_search(**args):
    info = to_dict(args)
    query = {}
    if 'jump' in args:
        label = info.get('label', '')
        m = lmfdb_label_regex.match(label)
        if m:
            N, iso, number = m.groups()
            if number:
                return render_curve_webpage_by_label(label=label)
            else:
                return render_isogeny_class(str(N)+'.'+iso)
        else:
            query['label'] = label

    for field in ['conductor', 'torsion', 'rank', 'sha_an']:
        if info.get(field):
            ran = info[field]
            ran = ran.replace('..','-')
            tmp = parse_range2(ran, field)
            # work around syntax for $or
            # we have to foil out multiple or conditions
            if tmp[0]=='$or' and query.has_key('$or'):
                newors = []
                for y in tmp[1]:
                    oldors = [dict.copy(x) for x in query['$or']]
                    for x in oldors: x.update(y) 
                    newors.extend(oldors)
                tmp[1] = newors
            query[tmp[0]] = tmp[1]
#            query[field] = parse_range2(info[field])

    if 'optimal' in info and info['optimal']=='on':
        query['number'] = 1

    if 'torsion_structure' in info and info['torsion_structure']:
        query['torsion_structure'] = [str(a) for a in parse_list(info['torsion_structure'])]

    info['query'] = query

    count_default=100
    if info.get('count'):        
        try:
            count = int(info['count'])
        except:
            count = count_default
    else:
        info['count'] = count_default
        count = count_default
    
    start_default=0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0): start += (1-(start+1)/count)*count
        except:
            start = start_default
    else:
        start = start_default

    print query
    cursor = base.getDBConnection().elliptic_curves.curves.find(query)
    nres = cursor.count()
    if(start>=nres): start-=(1+(start-nres)/count)*count
    if(start<0): start=0
    res = cursor.sort([('conductor', ASCENDING), ('lmfdb_iso', ASCENDING), ('lmfdb_number', ASCENDING)]).skip(start).limit(count)
    info['curves'] = res
    info['format_ainvs'] = format_ainvs
    info['number'] = nres
    info['start'] = start
    if nres==1:
        info['report'] = 'unique match'
    else:
        if nres>count or start!=0:
            info['report'] = 'displaying matches %s-%s of %s'%(start+1,min(nres,start+count),nres)
        else:
            info['report'] = 'displaying all %s matches'%nres
    credit = 'John Cremona'
    t = 'Elliptic Curves'
    bread = [('Elliptic Curves', url_for("rational_elliptic_curves")),
             ('Search Results', '.')]
    return render_template("elliptic_curve/elliptic_curve_search.html",  info = info, credit=credit,bread=bread, title = t)
    

##########################
#  Specific curve pages
##########################

@app.route("/EllipticCurve/Q/<label>")
def by_ec_label(label):
    logger.debug(label)
    try:
        N, iso, number = lmfdb_label_regex.match(label).groups()
    except:
        print label
        N, iso, number = cremona_label_regex.match(label).groups()
        print N, iso, number
        C = base.getDBConnection()
        # We permanently redirect to the lmfdb label
        if number:
            data = C.elliptic_curves.curves.find_one({'label': label})
            logger.debug(url_for("by_ec_label",label=data['lmfdb_label']))
            return redirect(url_for("by_ec_label",label=data['lmfdb_label']),301)
        else:
            data = C.elliptic_curves.curves.find_one({'iso': label})
            logger.debug(url_for("by_ec_label",label=data['lmfdb_label']))
            return redirect(url_for("by_ec_label",label=data['lmfdb_iso']),301)
        #N,d1, iso,d2, number = sw_label_regex.match(label).groups()
    if number:
        return render_curve_webpage_by_label(label=label)
    else:
        return render_isogeny_class(str(N)+'.'+iso)

@app.route("/EllipticCurve/Q/plot/<label>")
def plot_ec(label):
    C = base.getDBConnection()
    data = C.elliptic_curves.curves.find_one({'lmfdb_label': label})
    if data is None:
        return "No such curve"    
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    P = E.plot()
    _, filename = tempfile.mkstemp('.png')
    P.save(filename)
    data = open(filename).read()
    os.unlink(filename)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

@app.route("/EllipticCurve/Q/iso_graph/<label>")
def plot_iso_graph(label):
    C = base.getDBConnection()
    data = C.elliptic_curves.curves.find_one({'lmfdb_iso': label})
    if data is None:
        return "No such curve"
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    G = E.isogeny_graph(); n = G.num_verts()
    G.relabel(range(1,n+1)) # proper lmfdb labels...
    P = G.plot(edge_labels=True, layout='spring')
    _, filename = tempfile.mkstemp('.png')
    P.save(filename)
    data = open(filename).read()
    os.unlink(filename)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

def render_isogeny_class(iso_class):
    info = {}
    credit = 'John Cremona'
    lmfdb_iso=iso_class # e.g. '11.a'
    N, iso, number = lmfdb_label_regex.match(lmfdb_iso).groups()

    CDB = base.getDBConnection().elliptic_curves.curves

    E1data = CDB.find_one({'lmfdb_label': lmfdb_iso+'1'})
    if E1data is None:
        return "No such isogeny class"

    cremona_iso = E1data['iso']
    ainvs = E1data['ainvs']
    E1 = EllipticCurve([ZZ(c) for c in ainvs])
    curves, mat = E1.isogeny_class()
    size = len(curves)
    # Create a list of the curves in the class from the database, so
    # they are in the correct order!
    db_curves = [E1]
    optimal_flags = [False]*size
    cremona_labels = [E1data['label']]+[0]*(size-1)
    if E1data['number']==1:
        optimal_flags[0]=True
    for i in range(2,size+1):
        Edata = CDB.find_one({'lmfdb_label': lmfdb_iso+str(i)})
        E = EllipticCurve([ZZ(c) for c in Edata['ainvs']])
        cremona_labels[i-1]=Edata['label']
        if Edata['number']==1:
            optimal_flags[i-1]=True
        db_curves.append(E)
    # Now work out the permutation needed to match the two lists of curves:
    perm = [db_curves.index(E) for E in curves]
    # Apply the same permutation to the isogeny matrix:
    mat = [[mat[perm[i],perm[j]] for j in range(size)] for i in range(size)]
    
        
    info = {'label': lmfdb_iso}
    info['optimal_ainvs'] = ainvs
    info['rank'] = E1data['rank']
    info['isogeny_matrix']=latex(matrix(mat))
      
    #info['f'] = ajax_more(E.q_eigenform, 10, 20, 50, 100, 250)
    info['f'] = web_latex(E.q_eigenform(10))
    info['graph_img'] = url_for('plot_iso_graph', label=lmfdb_iso)
   
    info['curves'] = [[lmfdb_iso+str(i+1),cremona_labels[i],str(list(c.ainvs())),c.torsion_order(),c.modular_degree(),optimal_flags[i]] for i,c in enumerate(db_curves)]

    friends=[]
#   friends.append(('Quadratic Twist', "/quadratic_twists/%s" % (lmfdb_iso)))
    friends.append(('L-function', url_for("render_Lfunction", arg1='EllipticCurve', arg2='Q', arg3=lmfdb_iso)))
    friends.append(('Symmetric square L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='2',arg3='EllipticCurve', arg4='Q', arg5=lmfdb_iso)))
    friends.append(('Symmetric 4th power L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='4',arg3='EllipticCurve', arg4='Q', arg5=lmfdb_iso)))
#render_one_elliptic_modular_form(level,weight,character,label,**kwds)

    if int(N)<100:
        friends.append(('Modular form '+lmfdb_iso, url_for("emf.render_elliptic_modular_forms", level=N,weight=2,character=0,label=iso)))
    else:
        friends.append(('Modular form '+lmfdb_iso+' not available', 0))

    info['friends'] = friends

    info['downloads'] = [('Download coeffients of q-expansion', url_for("download_EC_qexp", label=lmfdb_iso, limit=100)), \
                         ('Download stored data for curves in this class', url_for("download_EC_all", label=lmfdb_iso))]

    if lmfdb_iso==cremona_iso:
        t = "Elliptic Curve Isogeny Class %s" % lmfdb_iso
    else:
        t = "Elliptic Curve Isogeny Class %s (Cremona label %s)" % (lmfdb_iso,cremona_iso)
    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('isogeny class %s' %lmfdb_iso,' ')]

    return render_template("elliptic_curve/iso_class.html", info=info, bread=bread, credit=credit,title = t, friends=info['friends'], downloads=info['downloads'])

@app.route("/EllipticCurve/Q/modular_form_display/<label>/<number>")
def modular_form_display(label, number):
    try:
        number = int(number)
    except:
        number = 10
    if number < 10:
        number = 10
    if number > 100000:
        number = 20
    if number > 50000:
        return "OK, I give up."
    if number > 20000:
        return "This incident will be reported to the appropriate authorities."
    if number > 9600:
        return "You have been banned from this website."
    if number > 4800:
        return "Seriously."
    if number > 2400:
        return "I mean it."
    if number > 1200:
        return "Please stop poking me."
    if number > 1000:
        number = 1000
    C = base.getDBConnection()
    data = C.elliptic_curves.curves.find_one({'lmfdb_label': label})
    if data is None:
        return "No such curve"
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    modform = E.q_eigenform(number)
    modform_string = web_latex_split_on_pm(modform)
    return modform_string
    #url_for_more = url_for('modular_form_coefficients_more', label = label, number = number * 2)
    #return """
    #    <span id='modular_form_more'> %(modform_string)s 
    #    <a onclick="$('modular_form_more').load(
    #            '%(url_for_more)s', function() { 
    #                MathJax.Hub.Queue(['Typeset',MathJax.Hub,'modular_form_more']);
    #            });
    #            return false;" href="#">more</a></span>
    #""" % { 'modform_string' : modform_string, 'url_for_more' : url_for_more }

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
    data = C.elliptic_curves.curves.find_one({'lmfdb_label': label})
    if data is None:
        return "No such curve"    
    info = {}
    ainvs = [int(a) for a in data['ainvs']]
    E = EllipticCurve(ainvs)
    cremona_label=data['label']
    lmfdb_label=data['lmfdb_label']
    N = ZZ(data['conductor'])
    cremona_iso_class = data['iso'] # eg '37a'
    lmfdb_iso_class = data['lmfdb_iso'] # eg '37.a'
    rank = data['rank']
    j_invariant=E.j_invariant()
    #plot=E.plot()
    discriminant=E.discriminant()
    xintpoints_projective=[E.lift_x(x) for x in xintegral_point(data['x-coordinates_of_integral_points'])]
    xintpoints=proj_to_aff(xintpoints_projective)
    G = E.torsion_subgroup().gens()
    minq = E.minimal_quadratic_twist()[0]
    if E==minq:
        minq_label = lmfdb_label
    else:
        minq_ainvs = [str(c) for c in minq.ainvs()]
        minq_label=C.elliptic_curves.curves.find_one({'ainvs': minq_ainvs})['lmfdb_label']
# We do not just do the following, as Sage's installed database
# might not have all the curves in the LMFDB database.
# minq_label = E.minimal_quadratic_twist()[0].label()
    
    if 'gens' in data:
        generator=parse_gens(data['gens'])
    if len(G) == 0:
        tor_struct = '\mathrm{Trivial}'
        tor_group='\mathrm{Trivial}'
    else:
        tor_group=' \\times '.join(['\mathbb{Z}/{%s}\mathbb{Z}'%a.order() for a in G])
    if 'torsion_structure' in data:
        info['tor_structure']= ' \\times '.join(['\mathbb{Z}/{%s}\mathbb{Z}'% int(a) for a in data['torsion_structure']])
    else:
        info['tor_structure'] = tor_group
        
    info.update(data)
    if rank >=2:
        lder_tex = "L%s(E,1)" % ("^{("+str(rank)+")}")
    elif rank ==1:
        lder_tex = "L%s(E,1)" % ("'"*rank)
    else:
        assert rank == 0
        lder_tex = "L(E,1)"
    p_adic_data_exists = (C.ellcurves.padic_db.find({'label': cremona_iso_class}).count())>0

    # Local data
    local_data = []
    for p in N.prime_factors():
        local_info = E.local_data(p)
        local_data.append({'p': p,
                           'tamagawa_number': local_info.tamagawa_number(),
                           'kodaira_symbol': web_latex(local_info.kodaira_symbol()).replace('$',''),
                           'reduction_type': local_info.bad_reduction_type()
                           })

    mod_form_iso=lmfdb_label_regex.match(lmfdb_iso_class).groups()[1]

    info.update({
        'conductor': N,
        'disc_factor': latex(discriminant.factor()),
        'j_invar_factor':latex(j_invariant.factor()),
        'label': lmfdb_label,
        'cremona_label': cremona_label,
        'iso_class':lmfdb_iso_class,
        'cremona_iso_class': cremona_iso_class,
        'equation': web_latex(E),
        #'f': ajax_more(E.q_eigenform, 10, 20, 50, 100, 250),
        'f' : web_latex(E.q_eigenform(10)),
        'generators':','.join(web_latex(g) for g in generator) if 'gens' in data else ' ',
        'lder'  : lder_tex,
        'p_adic_primes': [p for p in sage.all.prime_range(5,100) if E.is_ordinary(p) and not p.divides(N)],
        'p_adic_data_exists': p_adic_data_exists,
        'ainvs': format_ainvs(data['ainvs']),
        'tamagawa_numbers': r' \cdot '.join(str(sage.all.factor(c)) for c in E.tamagawa_numbers()),
        'local_data': local_data,
        'cond_factor':latex(N.factor()),
        'xintegral_points':','.join(web_latex(i_p) for i_p in xintpoints),
        'tor_gens':','.join(web_latex(eval(g)) for g in data['torsion_generators']) if False else ','.join(web_latex(P.element().xy()) for P in list(G))
        # Database has errors when torsion generators not integral
        # 'tor_gens':','.join(web_latex(eval(g)) for g in data['torsion_generators']) if 'torsion_generators' in data else [P.element().xy() for P in list(G)]
                        })
    info['friends'] = [
        ('Isogeny class '+lmfdb_iso_class, "/EllipticCurve/Q/%s" % lmfdb_iso_class),
        ('Minimal quadratic twist '+minq_label, "/EllipticCurve/Q/%s" % minq_label),
        ('L-function', url_for("render_Lfunction", arg1='EllipticCurve', arg2='Q', arg3=lmfdb_label)),
        ('Symmetric square L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='2',arg3='EllipticCurve', arg4='Q', arg5=lmfdb_iso_class)),
        ('Symmetric 4th power L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='4',arg3='EllipticCurve', arg4='Q', arg5=lmfdb_iso_class))]

    if int(N)<100:
        info['friends'].append(('Modular form '+lmfdb_iso_class.replace('.','.2'), url_for("emf.render_elliptic_modular_forms", level=int(N),weight=2,character=0,label=mod_form_iso)))
    else:
        info['friends'].append(('Modular form '+lmfdb_iso_class.replace('.','.2')+" not available",0))

    info['downloads'] = [('Download coeffients of q-expansion', url_for("download_EC_qexp", label=lmfdb_label, limit=100)), \
                         ('Download all stored data', url_for("download_EC_all", label=lmfdb_label))]


    #info['learnmore'] = [('Elliptic Curves', url_for("not_yet_implemented"))]
    #info['plot'] = image_src(plot)
    info['plot'] = url_for('plot_ec', label=lmfdb_label)

    properties2 = [('Label', '%s' % lmfdb_label),
                   (None, '<img src="%s" width="200" height="150"/>' % url_for('plot_ec', label=lmfdb_label) ),
                   ('Conductor', '\(%s\)' % N),
                   ('Discriminant', '\(%s\)' % discriminant),
                   ('j-invariant', '%s' % web_latex(j_invariant)),
                   ('Rank', '\(%s\)' % rank),
                   ('Torsion Structure', '\(%s\)' % tor_group)
    ]
    #properties.extend([ "prop %s = %s<br/>" % (_,_*1923) for _ in range(12) ])
    credit = 'John Cremona'
    if info['label']==info['cremona_label']:
        t = "Elliptic Curve %s" % info['label']
    else:
        t = "Elliptic Curve %s (Cremona label %s)" % (info['label'],info['cremona_label'])

    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('Elliptic curves %s' %lmfdb_label,' ')]

    return render_template("elliptic_curve/elliptic_curve.html",
          properties2=properties2, credit=credit,bread=bread, title = t, info=info, friends = info['friends'], downloads = info['downloads'])

@app.route("/EllipticCurve/Q/padic_data")
def padic_data():
    info = {}
    label = request.args['label']
    p = int(request.args['p'])
    info['p'] = p
    N, iso, number = lmfdb_label_regex.match(label).groups()
    #print N, iso, number
    if request.args['rank'] == '0':
        info['reg'] = 1
    elif number == '1':
        C = base.getDBConnection()
        data = C.elliptic_curves.curves.find_one({'lmfdb_iso': N+'.'+iso})      
        data = C.ellcurves.padic_db.find_one({'label': data['label'], 'p': p})
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

@app.route("/EllipticCurve/Q/download_qexp/<label>/<limit>")
def download_EC_qexp(label, limit):
    logger.debug(label)
    CDB = base.getDBConnection().elliptic_curves.curves
    N, iso, number = lmfdb_label_regex.match(label).groups()
    if number:
        data = CDB.find_one({'lmfdb_label':label})
    else:
        data = CDB.find_one({'lmfdb_iso':label})
    ainvs = data['ainvs']
    logger.debug(ainvs)
    E = EllipticCurve([int(a) for a in ainvs])
    response = make_response(' '.join(str(an) for an in E.anlist(int(limit), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response

@app.route("/EllipticCurve/Q/download_all/<label>")
def download_EC_all(label):
    CDB = base.getDBConnection().elliptic_curves.curves
    N, iso, number = lmfdb_label_regex.match(label).groups()
    if number:
        data = CDB.find_one({'lmfdb_label':label})
        if data is None:
            raise ValueError("No such curve known in database")
        data_list = [data]
    else:
        data_list = sorted(list(CDB.find({'lmfdb_iso':label})), key = lambda E: E['number'])
        if len(data_list) == 0:
            raise ValueError("No such class known in database")

    #titles of all entries of curves
    dump_data=[]
    titles = [str(c) for c in data_list[0]]
    titles.sort()
    dump_data.append(titles)
    for data in data_list:
        dump_data.append([data[t] for t in titles])
    response=make_response('\n'.join(str(an) for an in dump_data))
    response.headers['Content-type'] = 'text/plain'
    return response

@app.route('/ModularForm/GL2/<field_label>/holomorphic/<label>/download/<download_type>')
def render_hmf_webpage_download(**args):
    if args['download_type'] == 'magma':
        response = make_response(download_hmf_magma(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['download_type'] == 'sage':
        response = make_response(download_hmf_sage(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    
#@app.route("/EllipticCurve/Q/download_Rub_data")
#def download_Rub_data():
#    import gridfs
#    label=(request.args.get('label'))
#    type=(request.args.get('type'))
#    C = base.getDBConnection()
#    fs = gridfs.GridFS(C.elliptic_curves,'isogeny' )
#    isogeny=C.ellcurves.isogeny.files
#    filename=isogeny.find_one({'label':str(label),'type':str(type)})['filename']
#    d= fs.get_last_version(filename)
#    response = make_response(d.readline())
#    response.headers['Content-type'] = 'text/plain'
#    return response
