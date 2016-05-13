import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

import flask
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, Flask, session, g, redirect, make_response, flash,  send_file

from lmfdb import base
from lmfdb.base import app, getDBConnection
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, make_logger, web_latex_split_on_pm, comma, random_object_from_collection

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi, latex, matrix, srange, PowerSeriesRing, sqrt, QuadraticForm

from lmfdb.rep_galois_modl import rep_galois_modl_page, rep_galois_modl_logger
from lmfdb.rep_galois_modl.rep_galois_modl_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list, parse_count, parse_start


from markupsafe import Markup

import time
import os
import ast
import StringIO

rep_galois_modl_credit = 'Samuele Anni, Anna Medvedovsky, Bartosz Naskrecki, David Roberts'



# utilitary functions for displays 

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
    bc = [('Representations', "/Representation"),("mod &#x2113;", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())


# webpages: main, random and search results

@rep_galois_modl_page.route("/")
def rep_galois_modl_render_webpage():
    args = request.args
    if len(args) == 0:
        counts = get_stats().counts()
        dim_list= range(1, 11, 1)
        max_class_number=20
        class_number_list=range(1, max_class_number+1, 1)
        det_list_endpoints = [1, 5000, 10000, 20000, 25000, 30000]
#        if counts['max_det']>3000:
#            det_list_endpoints=det_list_endpoints+range(3000, max(int(round(counts['max_det']/1000)+2)*1000, 10000), 1000)
        det_list = ["%s-%s" % (start, end - 1) for start, end in zip(det_list_endpoints[:-1], det_list_endpoints[1:])]
        name_list = ["A2","Z2", "D3", "D3*", "3.1942.3884.56.1", "A5", "E8", "A14", "Leech"]
        info = {'dim_list': dim_list,'class_number_list': class_number_list,'det_list': det_list, 'name_list': name_list}
        credit = rep_galois_modl_credit
        t = 'Mod &#x2113; Galois representations'
        bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage"))]
        info['counts'] = get_stats().counts()
        return render_template("rep_galois_modl-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
    else:
        return rep_galois_modl_search(**args)

# Random rep_galois_modl
@rep_galois_modl_page.route("/random")
def random_rep_galois_modl():
    res = random_object_from_collection( getDBConnection().mod_l_galois.reps )
    return redirect(url_for(".render_rep_galois_modl_webpage", label=res['label']))


rep_galois_modl_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_rep_galois_modl_label(lab):
    return rep_galois_modl_label_regex.match(lab).groups()

def rep_galois_modl_by_label_or_name(lab, C):
    if C.mod_l_galois.reps.find({'$or':[{'label': lab}, {'name': lab}]}).limit(1).count() > 0:
        return render_rep_galois_modl_webpage(label=lab)
    if rep_galois_modl_label_regex.match(lab):
        flash(Markup("The integral rep_galois_modl <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No integral rep_galois_modl in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".rep_galois_modl_render_webpage"))

def rep_galois_modl_search(**args):
    C = getDBConnection()
    info = to_dict(args)  # what has been entered in the search boxes

    if 'download' in info:
        return download_search(info)

    if 'label' in info and info.get('label'):
        return rep_galois_modl_by_label_or_name(info.get('label'), C)
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

    count = parse_count(info,50)
    start = parse_start(info)

    info['query'] = dict(query)
    res = C.mod_l_galois.reps.find(query).sort([('dim', ASC), ('det', ASC), ('level', ASC), ('class_number', ASC), ('label', ASC)]).skip(start).limit(count)
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

    info['rep_galois_modls'] = res_clean

    t = 'Mod &#x2113; Galois representations Search Results'

    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".index")), ('Search Results', ' ')]
    properties = []
    return render_template("rep_galois_modl-search.html", info=info, title=t, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info, bread=None):
    t = 'Mod &#x2113; Galois representations Search Results Error'
    if bread is None:
        bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".index")),('Search Results', ' ')]
    return render_template("rep_galois_modl-search.html", info=info, title=t, properties=[], bread=bread, learnmore=learnmore_list())






@rep_galois_modl_page.route('/<label>')
def render_rep_galois_modl_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        lab = args.get('label')
        data = C.mod_l_galois.reps.find_one({'label': lab })
    if data is None:
        t = "Mod &#x2113; Galois representations Search Error"
        bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for a mod &#x2113; Galois representation in the database." % (lab)),"error")
        return render_template("rep_galois_modl-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    info['friends'] = []


    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")), ('%s' % data['label'], ' ')]
    credit = rep_galois_modl_credit
    f = C.mod_l_galois.reps.find_one({'base_field':data['base_field'],'rep_type':data['rep_type'],'image_type':data['image_type'],'image_label':data['image_label'],'image_at':data['image_at'], 'projective_type':data['projective_type'],'projective_label':data['projective_label'],'poly_ker':data['poly_ker'],'poly_proj_ker':data['poly_proj_ker'], 'related_objects':data['related_objects'],'dim':data['dim'],'field_char':data['field_char'],'field_deg':data['field_deg'],'conductor':data['conductor'], 'weight': data['weight'],'abs_irr':data['abs_irr'],'image_order':data['image_order'],'degree_proj_field':data['degree_proj_field'], 'primes_conductor':data['primes_conductor'],'bad_prime_list':data['bad_prime_list'],'good_prime_list':data['good_prime_list']})
    for m in ['base_field','image_type','image_label','image_at','projective_type','projective_label','related_objects', 'label']:
        info[m]=str(f[m])
    for m in ['dim','field_char','field_deg','conductor','weight','abs_irr','image_order','degree_proj_field']:
        info[m]=int(f[m])
    info['primes_conductor']=[int(i) for i in f['primes_conductor']]

    for m in ['poly_ker','poly_proj_ker']:
        info[m]=str(f[m]).replace("*", "").strip('(').strip(')')

    if f['rep_type'] =="symp":
        info['rep_type']="Symplectic"
    elif f['rep_type'] =="orth":
        info['rep_type']="Orthogonal"
    else:
        info['rep_type']="Linear"


    if info['field_deg'] > int(1):
        try:
            pol=str(conway_polynomial(f['characteristic'], f['deg'])).replace("*", "")
            info['field_str']=str('$\mathbb{F}_%s \cong \mathbb{F}_%s[a]$ where $a$ satisfies: $%s=0$' %(str(f['field_char']), str(f['field_char']), pol))
        except:
            info['field_str']=""


    info['bad_prime_list']=[]
    info['good_prime_list']=[]
    for n in f['bad_prime_list']:
        try:
            n1=[int(n[0]), str(n[1]), str(n[2]), int(n[3]), int(n[4])]
        except:
            n1=[int(n[0]), str(n[1]), str(n[2]), str(n[3]), str(n[4])]
        info['bad_prime_list'].append(n1)
    info['len_good']=[int(i+1) for i in range(len(f['good_prime_list'][0][1]))]
    for n in f['good_prime_list']:
        try:
            n1=[int(n[0]), [str(m) for m in n[1]], str(n[2]), int(n[3]), int(n[4])]
        except:
            n1=[int(n[0]), [str(m) for m in n[1]], str(n[2]), str(n[3]), str(n[4])]
        info['good_prime_list'].append(n1)

        info['download_list'] = [
            (i, url_for(".render_rep_galois_modl_webpage_download", label=info['label'], lang=i)) for i in ['gp', 'magma','sage']]

    t = "Mod &#x2113; Galois representation "+info['label']
    info['properties'] = [
        ('Label', '%s' %info['label']),
        ('Dimension', '%s' %info['dim']),
        ('Field characteristic', '%s' %info['field_char']),
        ('Conductor', '%s' %info['conductor']),]
    return render_template("rep_galois_modl-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list())
#friends=friends


#data quality pages
@rep_galois_modl_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the integral rep_galois_modl data'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Completeness', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='dq.rep_galois_modl.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@rep_galois_modl_page.route("/Source")
def how_computed_page():
    t = 'Source of the integral rep_galois_modl data'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Source', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='dq.rep_galois_modl.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@rep_galois_modl_page.route("/Labels")
def labels_page():
    t = 'Label of an integral rep_galois_modl'
    bread = [('Representations', "/Representation"),("mod &#x2113;", url_for(".rep_galois_modl_render_webpage")),
             ('Labels', '')]
    credit = rep_galois_modl_credit
    return render_template("single.html", kid='rep_galois_modl.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}

def download_search(info):
    lang = info["submit"]
    filename = 'integral_rep_galois_modls' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    res = getDBConnection().rep_galois_modls.reps.find(ast.literal_eval(info["query"]))

    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Integral rep_galois_modls downloaded from the LMFDB on %s. Found %s rep_galois_modls.\n\n'%(mydate, res.count())
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\\\n'
    mat_start = "Mat(" if lang == 'gp' else "Matrix("
    mat_end = "~)" if lang == 'gp' else ")"
    entry = lambda r: "".join([mat_start,str(r),mat_end])
    # loop through all search results and grab the gram matrix
    s += ",\\\n".join([entry(r['gram']) for r in res])
    s += list_end
    s += download_assignment_end[lang]
    s += '\n'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True)


@rep_galois_modl_page.route('/<label>/download/<lang>/')
def render_rep_galois_modl_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_rep_galois_modl_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_rep_galois_modl_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_rep_galois_modl_full_lists_v(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    res = C.mod_l_galois.reps.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such rep_galois_modl"
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


def download_rep_galois_modl_full_lists_g(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    res = C.mod_l_galois.reps.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such rep_galois_modl"
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

