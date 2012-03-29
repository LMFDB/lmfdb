# -*- coding: utf-8 -*-
import re

from pymongo import ASCENDING
import base
from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
import tempfile
import os

from utils import ajax_more, image_src, web_latex, to_dict, parse_range2, web_latex_split_on_pm
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
        m = cremona_label_regex.match(label)
        if m:
            N, iso, number = cremona_label_regex.match(label).groups()
            if number:
                return render_curve_webpage_by_label(label=label)
            else:
                return render_isogeny_class(str(N)+iso)
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
    res = cursor.sort([('conductor', ASCENDING), ('iso', ASCENDING), ('number', ASCENDING)]).skip(start).limit(count)
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
    try:
        N, iso, number = cremona_label_regex.match(label).groups()
    except:
        N,d1, iso,d2, number = sw_label_regex.match(label).groups()
    if number:
        return render_curve_webpage_by_label(label=label)
    else:
        return render_isogeny_class(str(N)+iso)

@app.route("/EllipticCurve/Q/plot/<label>")
def plot_ec(label):
    C = base.getDBConnection()
    data = C.elliptic_curves.curves.find_one({'label': label})
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
    

def render_isogeny_class(iso_class):
    info = {}
    credit = 'John Cremona'
    label=iso_class # e.g. '11a'
    N, iso, number = cremona_label_regex.match(label).groups()

    CDB = base.getDBConnection().elliptic_curves.curves
    
    E1data = CDB.find_one({'label': label+'1'})
    if E1data is None:
        return "No such isogeny class"
    ainvs = E1data['ainvs']
    E1 = EllipticCurve([ZZ(c) for c in ainvs])
    curves, mat = E1.isogeny_class()
    size = len(curves)
    # Create a list of the curves in the class from the database, so
    # they are in the correct order!
    db_curves = [E1]
    print "size=%s"%size
    for i in range(2,size+1):
        print "looking for %s"%(label+str(i))
        Edata = CDB.find_one({'label': label+str(i)})
        E = EllipticCurve([ZZ(c) for c in Edata['ainvs']])
        db_curves.append(E)
    assert len(db_curves)==size
    # Now work out the permutation needed to match the two lists of curves:
    perm = [db_curves.index(E) for E in curves]
    # Apply the same permutation to the isogeny matrix:
    mat = [[mat[perm[i],perm[j]] for j in range(size)] for i in range(size)]
    
    # On 2012-03-29 the modular forms database only contained levels
    # up to 100.  In that range there are 5 cases where the labels in
    # the modular forms database do not agree with the elliptic curve
    # isogeny clas labels.  This permutation was kindly provided by
    # Kiran Kedlaya.
    mod_form_iso=iso
    label_perm={'57b':'c', '57c':'b',
                '75a':'c', '75c':'a',
                '84a':'b', '84b':'a',
                '92a':'b', '94b':'a',
                '96a':'b', '96b':'a'}
    if label in label_perm:
        mod_form_iso=label_perm[label]
        
    info = {'label': label}
    info['optimal_ainvs'] = ainvs
    info['rank'] = E1data['rank']
    info['isogeny_matrix']=latex(matrix(mat))
    info['modular_degree']=web_latex(E1.modular_degree())
      
    #info['f'] = ajax_more(E.q_eigenform, 10, 20, 50, 100, 250)
    info['f'] = web_latex(E.q_eigenform(10))
    G = E1.isogeny_graph(); n = G.num_verts()
    G.relabel([1+perm[j] for j in range(n)]) # proper cremona labels...
    info['graph_img'] = image_src(G.plot(edge_labels=True, layout='spring'))

    info['curves'] = [[c.label(),str(list(c.ainvs())),c.torsion_order(),c.modular_degree()] for c in db_curves]
    info['download_qexp_url'] = url_for('download_qexp', limit=100, ainvs=','.join([str(a) for a in ainvs]))
    info['download_all_url'] = url_for('download_all', label=str(label))

    friends=[]
#   friends.append(('Quadratic Twist', "/quadratic_twists/%s" % (label)))
    friends.append(('L-function', url_for("render_Lfunction", arg1='EllipticCurve', arg2='Q', arg3=label)))
#render_one_elliptic_modular_form(level,weight,character,label,**kwds)
    friends.append(('Modular form '+N+mod_form_iso, url_for("emf.render_elliptic_modular_forms", level=N,weight=2,character=0,label=mod_form_iso)))
    info['friends'] = friends

    t= "Elliptic Curve Isogeny Class %s" % info['label']
    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('isogeny class %s' %info['label'],' ')]

    return render_template("elliptic_curve/iso_class.html", info=info, bread=bread, credit=credit,title = t, friends=info['friends'])

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
    data = C.elliptic_curves.curves.find_one({'label': label})
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
    data = C.elliptic_curves.curves.find_one({'label': label})
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
    #plot=E.plot()
    discriminant=E.discriminant()
    xintpoints_projective=[E.lift_x(x) for x in xintegral_point(data['x-coordinates_of_integral_points'])]
    xintpoints=proj_to_aff(xintpoints_projective)
    G = E.torsion_subgroup().gens()
    minq = E.minimal_quadratic_twist()[0]
    if E==minq:
        minq_label = label
    else:
        minq_ainvs = [str(c) for c in minq.ainvs()]
        minq_label=C.elliptic_curves.curves.find_one({'ainvs': minq_ainvs})['label']
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
    p_adic_data_exists = (C.ellcurves.padic_db.find({'label': iso_class}).count())>0

    # Local data
    local_data = []
    for p in N.prime_factors():
        local_info = E.local_data(p)
        local_data.append({'p': p,
                           'tamagawa_number': local_info.tamagawa_number(),
                           'kodaira_symbol': web_latex(local_info.kodaira_symbol()).replace('$',''),
                           'reduction_type': local_info.bad_reduction_type()
                           })

    info.update({
        'conductor': N,
        'disc_factor': latex(discriminant.factor()),
        'j_invar_factor':latex(j_invariant.factor()),
        'label': label,
        'iso_class':iso_class,
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
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet', url_for("not_yet_implemented"))]
    info['friends'] = [
        ('Isogeny class '+iso_class, "/EllipticCurve/Q/%s" % iso_class),
        ('Minimal quadratic twist '+minq_label, "/EllipticCurve/Q/%s" % minq_label),
        ('L-function', url_for("render_Lfunction", arg1='EllipticCurve', arg2='Q', arg3=label))]
####  THIS DOESN'T WORK AT THE MOMENT /Lemurell ('Modular Form',
####  url_for("emf.render_elliptic_modular_form_from_label",label="%s"
####  %(iso_class))),

    info['learnmore'] = [('Elliptic Curves', url_for("not_yet_implemented"))]
    #info['plot'] = image_src(plot)
    info['plot'] = url_for('plot_ec', label=label)
    info['download_qexp_url'] = url_for('download_qexp', limit=100, ainvs=','.join([str(a) for a in ainvs]))

    properties2 = [('Label', '%s' % label),
                   (None, '<img src="%s" width="200" height="150"/>' % url_for('plot_ec', label=label) ),
                   ('Conductor', '\(%s\)' % N), 
                   ('Discriminant', '\(%s\)' % discriminant),
                   ('j-invariant', '%s' % web_latex(j_invariant)),
                   ('Rank', '\(%s\)' % rank),
                   ('Torsion Structure', '\(%s\)' % tor_group)
    ]
    #properties.extend([ "prop %s = %s<br/>" % (_,_*1923) for _ in range(12) ])
    credit = 'John Cremona'
    t = "Elliptic Curve %s" % info['label']
    bread = [('Elliptic Curves ', url_for("rational_elliptic_curves")),('Elliptic curves %s' %info['label'],' ')]

    return render_template("elliptic_curve/elliptic_curve.html", 
          properties2=properties2, credit=credit,bread=bread, title = t, info=info, friends = info['friends'])

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
    response = make_response(' '.join(str(an) for an in E.anlist(int(request.args.get('limit', 100)), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response

@app.route("/EllipticCurve/Q/download_all")
def download_all():
    label=(request.args.get('label'))
    CDB = base.getDBConnection().elliptic_curves.curves
    data_list = [CDB.find_one({'label': label+'1'})]
    if data_list[0] is None:
        return "No such class exists: %s"%label
    size = 1
    data = 0 # any non-None value will do here
    while not data is None:
        size += 1
        data = CDB.find_one({'label': label+str(size)})
        if not data is None:
            data_list.append(data)

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
