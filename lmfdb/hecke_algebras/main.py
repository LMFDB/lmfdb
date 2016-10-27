# -*- coding: utf-8 -*-

import re
import pymongo
ASC = pymongo.ASCENDING
LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')

from flask import render_template, request, url_for, redirect, make_response, flash,  send_file

from lmfdb.base import getDBConnection
from lmfdb.utils import to_dict, web_latex_split_on_pm, random_object_from_collection

from sage.all import ZZ, QQ, PolynomialRing, latex, matrix, PowerSeriesRing, sqrt, sage_eval

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
    if C.mod_l_eigenvalues.hecke_algebras.find({'label': lab}).limit(1).count() > 0:
        return render_hecke_algebras_webpage(label=lab)
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
        for field, name in (('level','Level'),('weight','Weight'),('num_orbits', 'Number of Hecke orbits')):
            parse_ints(info, query, field, name)
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info)

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

    info['friends'] = []

    bread = [('HeckeAlgebra', url_for(".hecke_algebras_render_webpage")), ('%s' % data['label'], ' ')]
    credit = hecke_algebras_credit
    f = C.mod_l_eigenvalues.hecke_algebras.find_one({'level': data['level'],'weight': data['weight'],'num_orbits': data['num_orbits']})
    info['level']=int(f['level'])
    info['weight']= int(f['weight'])
    info['num_orbits']= int(f['num_orbits'])

    try:
        orb = C.mod_l_eigenvalues.hecke_algebras_orbits.find({'parent_label': f['label']})
        #consistency check
        if orb.count()!= int(f['num_orbits']):
            return search_input_error(info)
        info['orbits']=[o for o in orb]
        info['orbits_label']=[o['orbit_label'] for o in orb]
    except ValueError as err:
        info['err'] = str(err)
        return search_input_error(info)


    info['properties'] = [
        ('Level', '%s' %info['level']),
        ('Weight', '%s' %info['weight']),
        ('Label', '%s' %info['label'])]
    info['friends'] = [('Modular form ' + info['label'], url_for("emf.render_elliptic_modular_forms", level=info['level'], weight=info['weight'], character=1))]
    t = "Hecke Algebra %s" % info['label']
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
    filename = 'hecke_algebras' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here
    res = getDBConnection().mod_l_eigenvalues.hecke_algebras.find(ast.literal_eval(info["query"])).sort([('level', ASC), ('weight', ASC)])
    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Hecke Algebras downloaded from the LMFDB on %s. Found %s hecke_algebrass.\n\n'%(mydate, res.count())
    # The list entries are matrices of different sizes.  Sage and gp
    # do not mind this but Magma requires a different sort of list.
    list_start = '[*' if lang=='magma' else '['
    list_end = '*]' if lang=='magma' else ']'
    s += download_assignment_start[lang] + list_start + '\n'
    s += str(',\n'.join([str([r['level'],r['weight'],r['num_orbits']]) for r in res])) 
    s += list_end + download_assignment_end[lang]
    s += '\n\n'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

