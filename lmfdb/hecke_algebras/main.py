# -*- coding: utf-8 -*-

import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

from flask import render_template, request, url_for, redirect, make_response, flash,  send_file

from lmfdb.base import getDBConnection
from lmfdb.utils import to_dict, web_latex_split_on_pm, random_object_from_collection

from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt

from lmfdb.hecke_algebras import hecke_algebras_page
from lmfdb.hecke_algebras.hecke_algebras_stats import get_stats
from lmfdb.search_parsing import parse_ints, parse_list, parse_count, parse_start, clean_input

from markupsafe import Markup

import time
import ast
import StringIO

hecke_algebras_credit = 'Samuele Anni, Panagiotis Tsaknias and Gabor Wiese'


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
        weight_list= range(1, 20, 2)
        lvl_list_endpoints = [1, 100, 200, 300, 400, 500]
        lvl_list = ["%s-%s" % (start, end - 1) for start, end in zip(lvl_list_endpoints[:-1], lvl_list_endpoints[1:])]
        favourite_list = ["1.12.1","139.2.1","9.16.1"]
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

def split_hecke_algebras_label(lab):
    return hecke_algebras_label_regex.match(lab).groups()

def hecke_algebras_by_label(lab, C):
    clean_lab=str(lab).replace(" ","")
    clean_and_cap=str(clean_lab).capitalize()
    for l in [lab, clean_lab, clean_and_cap]:
        result= C.hecke_algebrass.lat.find({'$or':[{'label': l}]})
        if result.count()>0:
            lab=result[0]['label']
            return redirect(url_for(".render_hecke_algebras_webpage", label=lab))
    if hecke_algebras_label_regex.match(lab):
        flash(Markup("The Hecke Algebra <span style='color:black'>%s</span> is not recorded in the database or the label is invalid" % lab), "error")
    else:
        flash(Markup("No Hecke Algebras in the database has label <span style='color:black'>%s</span>" % lab), "error")
    return redirect(url_for(".hecke_algebras_render_webpage"))



def hecke_algebras_search(**args):
    C = getDBConnection()
    info = to_dict(args)  # what has been entered in the search boxes

    if 'download' in info:
        return download_search(info)

    if 'label' in info and info.get('label'):
        return hecke_algebras_by_label(info.get('label'), C)

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
    res = C.hecke_algebrass.lat.find(query).sort([('dim', ASC), ('det', ASC), ('level', ASC), ('class_number', ASC), ('label', ASC)]).skip(start).limit(count)
    nres = res.count()

    # here we are checking for isometric hecke_algebrass if the user enters a valid gram matrix but not one stored in the database_names, this may become slow in the future: at the moment we compare against list of stored matrices with same dimension and determinant (just compare with respect to dimension is slow)

    if nres==0 and info.get('gram'):
        A=query['gram'];
        n=len(A[0])
        d=matrix(A).determinant()
        result=[B for B in C.hecke_algebrass.lat.find({'dim': int(n), 'det' : int(d)}) if isom(A, B['gram'])]
        if len(result)>0:
            result=result[0]['gram']
            query_gram={ 'gram' : result }
            query.update(query_gram)
            res = C.hecke_algebrass.lat.find(query)
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

    info['hecke_algebrass'] = res_clean

    t = 'Integral hecke_algebrass Search Results'
    bread = [('HeckeAlgebras', url_for(".hecke_algebras_render_webpage")),('Search Results', ' ')]
    properties = []
    return render_template("hecke_algebras-search.html", info=info, title=t, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info, bread=None):
    t = 'Integral hecke_algebrass Search Error'
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

    info['friends'] = []

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % data['label'], ' ')]
    credit = hecke_algebras_credit
    f = C.mod_l_eigenvalues.hecke_algebras.find_one({'level': data['level'],'weight': data['weight'],'num_orbits': data['num_orbits']})
    info['level']=int(f['level'])
    info['weight']= int(f['weight'])
    info['num_orbits']= int(f['num_orbits'])
    t = "Hecke Algebra %s" % info['label']
    info['properties'] = [
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight']),
        ('Label', '%s' %info['label'])]
    info['friends'] = [('Modular form ' + info['label'], url_for("emf.render_elliptic_modular_forms", level=info['level'], weight=info['weight'], character=1))]
    return render_template("hecke_algebras-single.html", info=info, credit=credit, title=t, bread=bread, properties2=info['properties'], learnmore=learnmore_list(), friends=info['friends'])



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

def download_search(info):
    lang = info["submit"]
    filename = 'integral_hecke_algebrass' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here

    res = getDBConnection().hecke_algebrass.lat.find(ast.literal_eval(info["query"]))

    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Integral hecke_algebrass downloaded from the LMFDB on %s. Found %s hecke_algebrass.\n\n'%(mydate, res.count())
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
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)


@hecke_algebras_page.route('/<label>/download/<lang>/<obj>')
def render_hecke_algebras_webpage_download(**args):
    if args['obj'] == 'shortest_vectors':
        response = make_response(download_hecke_algebras_full_lists_v(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['obj'] == 'genus_reps':
        response = make_response(download_hecke_algebras_full_lists_g(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_hecke_algebras_full_lists_v(**args):
    C = getDBConnection()
    label = str(args['label'])
    res = C.hecke_algebrass.lat.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such hecke_algebras"
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


def download_hecke_algebras_full_lists_g(**args):
    C = getDBConnection()
    label = str(args['label'])
    res = C.hecke_algebrass.lat.find_one({'label': label})
    mydate = time.strftime("%d %B %Y")
    if res is None:
        return "No such hecke_algebras"
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

