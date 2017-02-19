# -*- coding: utf-8 -*-

import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

from flask import render_template, request, url_for, redirect, make_response, flash,  send_file

from lmfdb.base import getDBConnection
from lmfdb.utils import to_dict, web_latex_split_on_pm, random_object_from_collection

from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, sage_eval, prime_range

from lmfdb.hecke_algebras import hecke_algebras_page
from lmfdb.hecke_algebras.hecke_algebras_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list, parse_count, parse_start, clean_input

from markupsafe import Markup

import time
import ast
import StringIO

hecke_algebras_credit = 'Samuele Anni, Panagiotis Tsaknias and Gabor Wiese'
l_range=[ell for ell in prime_range(14)]

#breadcrumbs and links for data quality entries

def get_bread(breads=[]):
    bc = [("HeckeAlgebra", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for Hecke Algebras', url_for(".labels_page")),
            ('History of Hecke Algebras', url_for(".history_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@hecke_algebras_page.route("/")
def hecke_algebras_render_webpage():
    args = request.args
    if len(args) == 0:
#        counts = get_stats().counts()
        weight_list= range(2, 20, 2)
        lvl_list_endpoints = [1, 100, 200, 300, 400, 500]
        lvl_list = ["%s-%s" % (start, end - 1) for start, end in zip(lvl_list_endpoints[:-1], lvl_list_endpoints[1:])]
        favourite_list = ["1.12.1","139.2.1","239.2.1","9.16.1"]
        info = {'lvl_list': lvl_list,'wt_list': weight_list, 'favourite_list': favourite_list}
        credit = hecke_algebras_credit
        t = 'Hecke Algebras'
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        info['counts'] = get_stats().counts()
        return render_template("hecke_algebras-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
    else:
        return hecke_algebras_search(**args)

# Random hecke_algebras
@hecke_algebras_page.route("/random")
def random_hecke_algebra():
    res = random_object_from_collection( getDBConnection().mod_l_eigenvalues.hecke_algebras)
    return redirect(url_for(".render_hecke_algebras_webpage", label=res['label']))



hecke_algebras_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d*)')
hecke_algebras_orbit_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_hecke_algebras_label(lab):
    return hecke_algebras_label_regex.match(lab).groups()

def split_hecke_algebras_orbit_label(lab):
    return hecke_algebras_orbit_label_regex.match(lab).groups()

def hecke_algebras_by_label(lab, C):
    if C.mod_l_eigenvalues.hecke_algebras.find({'label': lab}).limit(1).count() > 0:
        return render_hecke_algebras_webpage(label=lab)
    if hecke_algebras_label_regex.match(lab):
        flash(Markup("The Hecke Algebra <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No Hecke Algebras in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".hecke_algebras_render_webpage"))

def hecke_algebras_by_orbit_label(lab, C):
    if C.mod_l_eigenvalues.hecke_algebras_orbits.find({'orbit_label': lab}).limit(1).count() > 0:
        sp=split_hecke_algebras_orbit_label(lab)
        ol=sp[0]+'.'+sp[1]+'.'+sp[2]
        return render_hecke_algebras_webpage(label=ol)
    if hecke_algebras_orbit_label_regex.match(lab):
        flash(Markup("The Hecke Algebra orbit <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No Hecke Algebras orbit in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".hecke_algebras_render_webpage"))


def hecke_algebras_search(**args):
    C = getDBConnection()
    info = to_dict(args)  # what has been entered in the search boxes

    if 'download' in info:
        return download_search(info)

    if 'label' in info and info.get('label'):
        return hecke_algebras_by_label(info.get('label'), C)

    if 'orbit_label' in info and info.get('orbit_label'):
        return hecke_algebras_by_orbit_label(info.get('orbit_label'), C)

    query = {}
    try:
        for field, name in (('level','Level'),('weight','Weight'),('num_orbits', 'Number of Hecke orbits')):
            parse_ints(info, query, field, name)
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info)
    # here need a check for ell as input, if the orbit is given should go to the right page otherwise list all base labels for which mod l info is available
    count = parse_count(info,50)
    start = parse_start(info)

    info['query'] = dict(query)
    res = C.mod_l_eigenvalues.hecke_algebras.find(query).sort([('level', ASC), ('weight', ASC), ('num_orbits', ASC)]).skip(start).limit(count)
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
        v_clean['level']=v['level']
        v_clean['weight']=v['weight']
        v_clean['num_orbits']=v['num_orbits']
        res_clean.append(v_clean)

    info['hecke_algebras'] = res_clean

    t = 'Hecke Algebras Search Results'
    bread = [('HeckeAlgebras', url_for(".hecke_algebras_render_webpage")),('Search Results', ' ')]
    properties = []
    return render_template("hecke_algebras-search.html", info=info, title=t, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info, bread=None):
    t = 'Hecke Algebras Search Error'
    if bread is None:
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),('Search Results', ' ')]
    return render_template("hecke_algebras-search.html", info=info, title=t, properties=[], bread=bread, learnmore=learnmore_list())


@hecke_algebras_page.route('/<label>')
def render_hecke_algebras_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        lab = clean_input(args.get('label'))
        if lab != args.get('label'):
            return redirect(url_for('.render_hecke_algebras_webpage', label=lab), 301)
        data = C.mod_l_eigenvalues.hecke_algebras.find_one({'label': lab })
    if data is None:
        t = "Hecke Agebras Search Error"
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for a Hecke Algebras in the database." % (lab)),"error")
        return render_template("hecke_algebras-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % data['label'], ' ')]
    credit = hecke_algebras_credit
    f = C.mod_l_eigenvalues.hecke_algebras.find_one({'level': data['level'],'weight': data['weight'],'num_orbits': data['num_orbits']})
    info['level']=int(f['level'])
    info['weight']= int(f['weight'])
    info['num_orbits']= int(f['num_orbits'])

    orb = C.mod_l_eigenvalues.hecke_algebras_orbits.find({'parent_label': f['label']}).sort([('orbit', ASC)])
    if orb.count()!=0:
        #consistency check
        if orb.count()!= int(f['num_orbits']):
            return search_input_error(info)

        res_clean = []
        for v in orb:
            v_clean = {}
            v_clean['orbit_label']=v['orbit_label']
            v_clean['hecke_op']=v['hecke_op']
            v_clean['gen']=v['gen']
            v_clean['dim']=int(matrix(sage_eval(v_clean['hecke_op'])[0]).dimensions()[0])
            if v_clean['dim']>4:
                v_clean['hecke_op_display']=[]
            elif v_clean['dim']==1:
                v_clean['hecke_op_display']=[[i+1, (sage_eval(v_clean['hecke_op'])[i])[0][0]] for i in range(0,10)]
            else:
                v_clean['hecke_op_display']=[[i+1, latex(matrix(sage_eval(v_clean['hecke_op'])[i]))] for i in range(0,5)]
            v_clean['num_hecke_op']=v['num_hecke_op']
            v_clean['download_op'] = [(i, url_for(".render_hecke_algebras_webpage_download", orbit_label=v_clean['orbit_label'], lang=i, obj='operators')) for i in ['gp', 'magma','sage']]
            if 'Zbasis' in v.keys():
                v_clean['Zbasis']=[[int(i) for i in j] for j in v['Zbasis']]
                if v_clean['dim']>4:
                    v_clean['gen_display']=[]
                elif v_clean['dim']==1:
                    v_clean['gen_display']=[v_clean['Zbasis'][0][0]]
                else:
                    v_clean['gen_display']=[latex(matrix(v_clean['dim'],v_clean['dim'], v_clean['Zbasis'][i])) for i in range(0,v_clean['dim'])]
                v_clean['discriminant']= int(v['discriminant'])
                v_clean['disc_fac']= [[int(i) for i in j] for j in v['disc_fac']]
                v_clean['Qbasis']=[int(i) for i in v['Qbasis']]
                v_clean['Qalg_gen']=[int(i) for i in v['Qalg_gen']]
                if 'inner_twists' in v.keys():
                    v_clean['inner_twists']= [str(i) for i in v['inner_twists']]
                else:
                    v_clean['inner_twists']="not available"
                v_clean['download_gen'] = [(i, url_for(".render_hecke_algebras_webpage_download", orbit_label=v_clean['orbit_label'], lang=i, obj='gen')) for i in ['gp', 'magma','sage']]
            res_clean.append(v_clean)

        info['orbits']=res_clean

    info['l_adic']=l_range
    info['properties'] = [
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight']),
        ('Label', '%s' %info['label'])]
    info['friends'] = [('Modular form ' + info['label'], url_for("emf.render_elliptic_modular_forms", level=info['level'], weight=info['weight'], character=1))]
    t = "Hecke Algebra %s" % info['label']
    return render_template("hecke_algebras-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list(), friends=info['friends'])




hecke_algebras_orbit_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split(lab):
    return hecke_algebras_orbit_label_regex.match(lab).groups()

@hecke_algebras_page.route('/<orbit_label>/<prime>')
def render_hecke_algebras_webpage_l_adic(**args):
    C = getDBConnection()
    data = None
    if 'orbit_label' in args and 'prime' in args:
        lab = clean_input(args.get('orbit_label'))
        if lab != args.get('orbit_label'):
            base_lab=".".join([split(lab)[i] for i in [0,1,2]])
            return redirect(url_for('.render_hecke_algebras_webpage', label=base_lab), 301)
        try:
            ell = int(args.get('prime'))
        except ValueError as err:
            base_lab=".".join([split(lab)[i] for i in [0,1,2]])
            return redirect(url_for('.render_hecke_algebras_webpage', label=base_lab), 301)
        data = C.mod_l_eigenvalues.hecke_algebras_l_adic.find_one({'orbit_label': lab , 'ell': ell})
    if data is None:
        t = "Hecke Agebras Search Error"
        bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for the &#x2113;-adic information for an Hecke Algebra orbit in the database." % (lab)),"error")
        return render_template("hecke_algebras-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)
    res = C.mod_l_eigenvalues.hecke_algebras_l_adic.find({'level': data['level'],'weight': data['weight'],'orbit_label': data['orbit_label'], 'ell': data['ell']})

    info['num_l_adic_orbits']=res.count()
    res_clean = []
    for f in res:
        f_clean = {}#add f['deg'], f['field_poly']
        if f['idempotent'] != "":
            f['dim']=len(sage_eval(f['idempotent']))
            l_max= sage_eval(f['idempotent'])[0][0].ndigits()
            if f['dim']>4 or l_max>5:
                f_clean['idempotent_display']=[]
            elif f['dim']==1:
                f_clean['idempotent_display']=sage_eval(f['idempotent'])[0][0]
            else:
                f_clean['idempotent_display']=latex(matrix(sage_eval(f['idempotent'])))
        else:
            f_clean['idempotent_display']=latex(matrix([[1]]))
        f_clean['gen_l']=str(f['gen_l'])
        f_clean['num_gen_l']=str(f['num_gen_l'])  #is empty for now, so made into a string
        f_clean['rel_l']=str(f['rel_l'])
        f_clean['num_charpoly_ql']=int(f['num_charpoly_ql'])
        f_clean['charpoly_ql']=str(f['charpoly_ql'])
        f_clean['hecke_mod_op_display']=[] #to be changed
        f_clean['num_hecke_mod_op']=[] #to be added
        res_clean.append(f_clean)

    info['l_adic_orbits']=res_clean

    info['level']=int(data['level'])
    info['weight']= int(data['weight'])
    info['base_lab']=".".join([split(data['orbit_label'])[i] for i in [0,1,2]])
    info['orbit_label']= str(data['orbit_label'])
    info['ell']=int(data['ell'])

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % info['base_lab'], url_for('.render_hecke_algebras_webpage', label=info['base_lab'])), ('%s' % info['ell'], ' ')]
    credit = hecke_algebras_credit
    info['properties'] = [
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight']),
        ('Characteristic', '%s' %info['ell']),
        ('Orbit label', '%s' %info['orbit_label'])]    
    info['friends'] = [('Modular form ' + info['base_lab'], url_for("emf.render_elliptic_modular_forms", level=info['level'], weight=info['weight'], character=1))]

    t = "%s-adic and mod %s data for the Hecke Algebra orbit %s" % (info['ell'], info['ell'], info['orbit_label'])
    return render_template("hecke_algebras_l_adic-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list(), friends=info['friends'])



#data quality pages
@hecke_algebras_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Hecke Algebra data'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Completeness', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='dq.hecke_algebras.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@hecke_algebras_page.route("/Source")
def how_computed_page():
    t = 'Source of the Hecke Algebra data'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Source', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='dq.hecke_algebras.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@hecke_algebras_page.route("/Labels")
def labels_page():
    t = 'Label of Hecke Algebras'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Labels', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='hecke_algebras.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@hecke_algebras_page.route("/History")
def history_page():
    t = 'A brief history of Hecke Algebras'
    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")),
             ('Histoy', '')]
    credit = hecke_algebras_credit
    return render_template("single.html", kid='hecke_algebras.history',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('History'))

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}


@hecke_algebras_page.route('/<orbit_label>/download/<lang>/<obj>')
def render_hecke_algebras_webpage_download(**args):
    if args['obj'] == 'operators':
        response = make_response(download_hecke_algebras_full_lists_op(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'gen': 
        response = make_response(download_hecke_algebras_full_lists_gen(**args))
        response.headers['Content-type'] = 'text/plain'
        return response

def download_hecke_algebras_full_lists_op(**args):
    C = getDBConnection()
    label = str(args['orbit_label'])
    res = C.mod_l_eigenvalues.hecke_algebras_orbits.find_one({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + 'Hecke algebra for Gamma0(%s) and weight %s, orbit label %s. List of Hecke operators T_1, ..., T_%s. Downloaded from the LMFDB on %s. \n\n'%(res['level'], res['weight'], res['orbit_label'],res['num_hecke_op'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry(r) for r in [sage_eval(res['hecke_op'])[i] for i in range(0,res['num_hecke_op'])]])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

def download_hecke_algebras_full_lists_gen(**args):
    C = getDBConnection()
    label = str(args['orbit_label'])
    res = C.mod_l_eigenvalues.hecke_algebras_orbits.find_one({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + 'Hecke algebra for Gamma0(%s) and weight %s, orbit label %s. List of generators for the algebra. Downloaded from the LMFDB on %s. \n\n'%(res['level'], res['weight'], res['orbit_label'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry([list(k) for k in matrix(sqrt(len(r)), sqrt(len(r)), r).rows()]) for r in [[int(i) for i in j] for j in res['Zbasis']] ])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr


@hecke_algebras_page.route('/<orbit_label>/<prime>/download/<lang>/<obj>')
def render_hecke_algebras_webpage_ell_download(**args):
    if args['obj'] == 'operators':
        response = make_response(download_hecke_algebras_full_lists_mod_op(**args)) 
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'idempotents': 
        response = make_response(download_hecke_algebras_full_lists_id(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_hecke_algebras_full_lists_mod_op(**args):#write this
    C = getDBConnection()
    label = str(args['orbit_label'])
    res = C.mod_l_eigenvalues.hecke_algebras_orbits.find_one({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + ' List of Hecke operators T_1, ..., T_%s downloaded from the LMFDB on %s. \n\n'%(res['num_hecke_op'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry(r) for r in [sage_eval(res['hecke_op'])[i] for i in range(0,res['num_hecke_op'])]])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

def download_hecke_algebras_full_lists_id(**args):#write this
    C = getDBConnection()
    label = str(args['orbit_label'])
    res = C.mod_l_eigenvalues.hecke_algebras_orbits.find_one({'orbit_label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such lattice"
    lang = args['lang']
    c = download_comment_prefix[lang]
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])

    outstr = c + ' List of Hecke operators T_1, ..., T_%s downloaded from the LMFDB on %s. \n\n'%(res['num_hecke_op'], mydate)
    outstr += download_assignment_start[lang] + '[\\\n'
    outstr += ",\\\n".join([entry(r) for r in [sage_eval(res['hecke_op'])[i] for i in range(0,res['num_hecke_op'])]])
    outstr += ']'
    outstr += download_assignment_end[lang]
    outstr += '\n'
    return outstr

