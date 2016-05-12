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

from lmfdb.modlmf import modlmf_page, modlmf_logger
from lmfdb.modlmf.modlmf_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list, parse_count, parse_start


from markupsafe import Markup

import time
import os
import ast
import StringIO

modlmf_credit = 'Samuele Anni, Anna Medvedovsky, Bartosz Naskrecki, David Roberts'


# utilitary functions for displays 

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
    bc = [("mod &#x2113; Modular Forms", url_for(".index"))]
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
@modlmf_page.route("/")
def modlmf_render_webpage():
    args = request.args
    if len(args) == 0:
        counts = get_stats().counts()
        characteristic_list= [2,3,5,7,11]
        level_list_endpoints = [1, 10, 20, 30, 40, 50]
        level_list = ["%s-%s" % (start, end - 1) for start, end in zip(level_list_endpoints[:-1], level_list_endpoints[1:])]
        weight_list= [1, 2, 3, 4, 5]
        label_list = ["2.1.1.0.1.1","2.1.3.0.1.1"]
        info = {'characteristic_list': characteristic_list, 'level_list': level_list,'weight_list': weight_list, 'label_list': label_list}
        credit = modlmf_credit
        t = 'mod &#x2113; Modular Forms'
        bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage"))]
        info['counts'] = get_stats().counts()
        return render_template("modlmf-index.html", info=info, credit=credit, title=t, learnmore=learnmore_list_remove('Completeness'), bread=bread)
    else:
        return modlmf_search(**args)


# Random modlmf
@modlmf_page.route("/random")
def random_modlmf():
    res = random_object_from_collection( getDBConnection().mod_l_eigenvalues.modlmf )
    return redirect(url_for(".render_modlmf_webpage", label=res['label']))

modlmf_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d+)\.(\d*)')

def split_modlmf_label(lab):
    return modlmf_label_regex.match(lab).groups()

def modlmf_by_label(lab, C):
    if C.modlmfs.lat.find({'label': lab}).limit(1).count() > 0:
        return render_modlmf_webpage(label=lab)
    if modlmf_label_regex.match(lab):
        flash(Markup("The mod &#x2113; modular form <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No mod &#x2113; modular form in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".modlmf_render_webpage"))





def modlmf_search(**args):
    C = getDBConnection()
    info = to_dict(args)  # what has been entered in the search boxes

    if 'download' in info:
        return download_search(info)

    if 'label' in info and info.get('label'):
        return modlmf_by_label(info.get('label'), C)
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

#    count_default = 50
#    if info.get('count'):
#        try:
#            count = int(info['count'])
#        except:
#            err = "Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a positive integer." % info['count']
#            flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a positive integer." % info['count']), "error")
#            info['err'] = str(err)
#            return search_input_error(info)
#    else:
#        info['count'] = count_default
#        count = count_default

#    start_default = 0
#    if info.get('start'):
#        try:
#            start = int(info['start'])
#            if(start < 0):
#                start += (1 - (start + 1) / count) * count
#        except:
#            start = start_default
#    else:
#        start = start_default

    info['query'] = dict(query)
    res = C.modlmfs.lat.find(query).sort([('dim', ASC), ('det', ASC), ('level', ASC), ('class_number', ASC), ('label', ASC)]).skip(start).limit(count)
    nres = res.count()

    # here we are checking for isometric modlmfs if the user enters a valid gram matrix but not one stored in the database_names, this may become slow in the future: at the moment we compare against list of stored matrices with same dimension and determinant (just compare with respect to dimension is slow)

    if nres==0 and info.get('gram'):
        A=query['gram'];
        n=len(A[0])
        d=matrix(A).determinant()
        result=[B for B in C.modlmfs.lat.find({'dim': int(n), 'det' : int(d)}) if isom(A, B['gram'])]
        if len(result)>0:
            result=result[0]['gram']
            query_gram={ 'gram' : result }
            query.update(query_gram)
            res = C.modlmfs.lat.find(query)
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

    info['modlmfs'] = res_clean

    t = 'Integral modlmfs Search Results'
    bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")),('Search Results', ' ')]
    properties = []
    return render_template("modlmf-search.html", info=info, title=t, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info, bread=None):
    t = 'Integral modlmfs Search Error'
    if bread is None:
        bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")),('Search Results', ' ')]
    return render_template("modlmf-search.html", info=info, title=t, properties=[], bread=bread, learnmore=learnmore_list())










@modlmf_page.route('/<label>')
def render_modlmf_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        lab = args.get('label')
        data = C.mod_l_eigenvalues.modlmf.find_one({'label': lab })
    if data is None:
        t = "mod &#x2113; modular form search error"
        bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage"))]
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label for a mod &#x2113; modular form in the database." % (lab)),"error")
        return render_template("modlmf-error.html", title=t, properties=[], bread=bread, learnmore=learnmore_list())
    info = {}
    info.update(data)

    info['friends'] = []

    bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")), ('%s' % data['label'], ' ')]
    credit = modlmf_credit
    f = C.mod_l_eigenvalues.modlmf.find_one({'characteristic':data['characteristic'], 'deg' : data['deg'], 'level' : data['level'],'conductor' : data['conductor'],'min_weight': data['min_weight'], 'dirchar' : data['dirchar'], 'atkinlehner': data['atkinlehner'],'n_coeffs': data['n_coeffs'],'coeffs': data['coeffs']})
    for m in ['characteristic','deg','level','conductor','min_weight', 'n_coeffs']:
        info[m]=int(f[m])
    for m in ['coeffs', 'atkinlehner']:
        info[m]=f[m]
    info['dirchar']=str('dirchar')

    ncoeff=20
    p_range=[2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]
    if f['coeffs'] != "":
        coeff=[f['coeffs'][i] for i in range(ncoeff+1)]
        info['q_exp']=my_latex(print_q_expansion(coeff))
        info['q_exp'] = url_for(".q_exp_display", label=f['label'], number="")
        info['table_list']=[[p_range[i], f['coeffs'][p_range[i]]] for i in range(len(p_range)-1)]
        info['download_q_exp'] = [
            (i, url_for(".render_modlmf_webpage_download", label=info['label'], lang=i, obj='coeffs')) for i in ['gp', 'magma','sage']]

        t = "mod &#x2113; Modular Form "+info['label']
    info['properties'] = [
        ('Field characteristic', '%s' %info['characteristic'])
        ('Field degree', '%s' %info['deg'])
        ('Level', '%s' %info['level']),
        ('Conductor', '%s' %info['conductor']),
        ('Minimal weight', '%s' %info['min_weight']),
        ('Label', '%s' %info['label'])]
    return render_template("modlmf-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list())



#auxiliary function for displaying more coefficients of the theta series
@modlmf_page.route('/theta_display/<label>/<number>')
def q_exp_display(label, number):
    try:
        number = int(number)
    except:
        number = 20
    if number < 20:
        number = 30
    if number > 150:
        number = 150
    C = getDBConnection()
    data = C.mod_l_eigenvalues.modlmf.find_one({'label': label})
    coeff=[data['coeffs'][i] for i in range(number+1)]
    return print_q_expansion(coeff)


#data quality pages
@modlmf_page.route("Completeness")
def completeness_page():
    t = 'Completeness of the mod &#8467; modular form data'
    bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")),
             ('Completeness', '')]
    credit = modlmf_credit
    return render_template("single.html", kid='dq.modlmf.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@modlmf_page.route("Source")
def how_computed_page():
    t = 'Source of the mod &#8467; modular form data'
    bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")),
             ('Source', '')]
    credit = modlmf_credit
    return render_template("single.html", kid='dq.modlmf.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@modlmf_page.route("Labels")
def labels_page():
    t = 'Label of a mod &#x2113; modular forms'
    bread = [('mod &#x2113; Modular Forms', url_for(".modlmf_render_webpage")),
             ('Labels', '')]
    credit = modlmf_credit
    return render_template("single.html", kid='modlmf.label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

#download
download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data := ','sage':'data = ','gp':'data = '}
download_assignment_end = {'magma':';','sage':'','gp':''}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}

def download_search(info):
    lang = info["submit"]
    filename = 'integral_modlmfs' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    res = getDBConnection().modlmfs.lat.find(ast.literal_eval(info["query"]))

    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Integral modlmfs downloaded from the LMFDB on %s. Found %s modlmfs.\n\n'%(mydate, res.count())
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


@modlmf_page.route('/<label>/download/<lang>/<obj>')
def render_modlmf_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_modlmf_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_modlmf_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_modlmf_full_lists_v(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    res = C.modlmfs.lat.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such modlmf"
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


def download_modlmf_full_lists_g(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    res = C.modlmfs.lat.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such modlmf"
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

