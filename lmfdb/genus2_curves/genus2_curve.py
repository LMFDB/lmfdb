# -*- coding: utf-8 -*-
import StringIO
import ast
import re
import time
import pymongo
from pymongo import ASCENDING, DESCENDING
from operator import mul
import lmfdb.base
from lmfdb.base import app
from flask import Flask, flash, session, g, render_template, url_for, request, redirect, make_response, send_file
from markupsafe import Markup
import tempfile
import os

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, comma, random_object_from_collection
from lmfdb.search_parsing import parse_bool, parse_ints, parse_signed_ints, parse_bracketed_posints, parse_count, parse_start
from lmfdb.number_fields.number_field import make_disc_key
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.isog_class import G2Cisog_class, url_for_label, isog_url_for_label, st_group_name, st_group_href
from lmfdb.genus2_curves.web_g2c import WebG2C, g2cdb, list_to_min_eqn, isog_label, st0_group_name, aut_group_name, boolean_name, globally_solvable_name

import sage.all
from sage.all import ZZ, QQ, latex, matrix, srange
credit_string = "Andrew Booker, Jeroen Sijsling, Andrew Sutherland, John Voight, and Dan Yasaki"

###############################################################################
# global database connection and stats objects
###############################################################################

the_g2cstats = None
def g2cstats():
    global the_g2cstats
    if the_g2cstats is None:
        the_g2cstats = G2C_stats()
    return the_g2cstats

###############################################################################
# List and dictionaries needed routing and searching
###############################################################################

# lists determine display order in drop down lists, dictionary key is the
# database entry, dictionary value is the display value
st_group_list = ['J(C_2)', 'J(C_4)', 'J(C_6)', 'J(D_2)', 'J(D_3)', 'J(D_4)',
        'J(D_6)', 'J(T)', 'J(O)', 'C_{2,1}', 'C_{6,1}', 'D_{2,1}', 'D_{3,2}',
        'D_{4,1}', 'D_{4,2}', 'D_{6,1}', 'D_{6,2}', 'O_1', 'E_1', 'E_2', 'E_3',
        'E_4', 'E_6', 'J(E_1)', 'J(E_2)', 'J(E_3)', 'J(E_4)', 'J(E_6)',
        'F_{a,b}', 'F_{ac}', 'N(G_{1,3})', 'G_{3,3}', 'N(G_{3,3})', 'USp(4)']
st_group_dict = {a:a for a in st_group_list}

# End_QQbar tensored with RR determines ST0 (which is the search parameter):
real_geom_end_alg_list = ['M_2(C)', 'M_2(R)', 'C x C', 'C x R', 'R x R', 'R']
real_geom_end_alg_to_ST0_dict = {
        'M_2(C)':'U(1)',
        'M_2(R)':'SU(2)',
        'C x C':'U(1) x U(1)',
        'C x R':'U(1) x SU(2)',
        'R x R':'SU(2) x SU(2)',
        'R':'USp(4)'
        }

aut_grp_list = ['[2,1]', '[4,1]', '[4,2]', '[6,2]', '[8,3]', '[12,4]']
aut_grp_dict = {
        '[2,1]':'C_2',
        '[4,1]':'C_4',
        '[4,2]':'V_4',
        '[6,2]':'C_6',
        '[8,3]':'D_8',
        '[12,4]':'D_{12}'
        }

geom_aut_grp_list = ['[2,1]', '[4,2]', '[8,3]', '[10,2]', '[12,4]', '[24,8]', '[48,29]']
geom_aut_grp_dict = {
        '[2,1]':'C_2',
        '[4,2]':'V_4',
        '[8,3]':'D_8',
        '[10,2]':'C_{10}',
        '[12,4]':'D_{12}',
        '[24,8]':'2D_{12}',
        '[48,29]':'tilde{S}_4'}

###############################################################################
# Routing for top level, random_curve, by_conductor, and stats
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Genus 2 curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

@g2c_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@g2c_page.route("/Q/")
def index_Q():
    if len(request.args) != 0:
        return genus2_curve_search(**request.args)
    info = {'counts' : g2cstats().counts()}
    info["stats_url"] = url_for(".statistics")
    info["curve_url"] =  lambda dbc: url_for_label(dbc['label'])
    info["browse_curves"] = [
        g2cdb().curves.find_one({"label":"169.a.169.1"}),
        g2cdb().curves.find_one({"label":"1116.a.214272.1"}),
        g2cdb().curves.find_one({"label":"1152.a.147456.1"}),
        g2cdb().curves.find_one({"label":"1369.a.50653.1"}),
        g2cdb().curves.find_one({"label":"12500.a.12500.1"}),
    ]
    info["conductor_list"] = ['1-499', '500-999', '1000-99999','100000-1000000'   ]
    info["discriminant_list"] = ['1-499', '500-999', '1000-99999','100000-1000000'   ]
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    title = 'Genus 2 curves over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' ')]
    return render_template("browse_search_g2.html", info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread)

@g2c_page.route("/Q/<int:conductor>/")
def by_conductor(conductor):
    return genus2_curve_search(cond=conductor, **request.args)

@g2c_page.route("/Q/random")
def random_curve():
    label = random_object_from_collection(g2cdb().curves)['label']
    # This version leaves the word 'random' in the URL:
    #return render_curve_webpage_by_label(label)
    # This version uses the curve's own URL:
    return redirect(url_for(".by_g2c_label", label=label), 301)

@g2c_page.route("/Q/stats")
def statistics():
    info = {
        'counts': g2cstats().counts(),
        'stats': g2cstats().stats(),
    }
    title = 'Genus 2 curves over $\Q$: statistics'
    bread = [('Genus 2 Curves', url_for(".index")),
        ('$\Q$', url_for(".index_Q")),
        ('statistics', ' ')]
    return render_template("statistics_g2.html", info=info, credit=credit_string, title=title, bread=bread, learnmore=learnmore_list())

###############################################################################
# Curve pages
###############################################################################

@g2c_page.route("/Q/<int:conductor>/<iso_label>/<int:disc>/<int:number>")
def by_full_label(conductor,iso_label, disc,number):
    full_label = str(conductor)+"."+iso_label+"."+str(disc)+"."+str(number)
    g2c_logger.debug(full_label)
    return render_curve_webpage_by_label(full_label)

@g2c_page.route("/Q/<label>")
def by_g2c_label(label):
    g2c_logger.debug(label)
    return render_curve_webpage_by_label(label)

def render_curve_webpage_by_label(label):
    credit = credit_string
    data = WebG2C.by_label(label)
    if isinstance(data,str):
        return data
    return render_template("curve_g2.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           bread=data.bread,
                           learnmore=learnmore_list(),
                           title=data.title,
                           friends=data.friends)
                           #downloads=data.downloads)

###############################################################################
# Isogeny class pages
###############################################################################

@g2c_page.route("/Q/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor, iso_label):
    full_iso_label = str(conductor)+"."+iso_label
    return render_isogeny_class(full_iso_label)

def render_isogeny_class(iso_class):
    credit = credit_string
    class_data = G2Cisog_class.by_label(iso_class)
    if isinstance(class_data,str):
        return class_data
    return render_template("isogeny_class_g2.html",
                           properties2=class_data.properties,
                           bread=class_data.bread,
                           learnmore=learnmore_list(),
                           credit=credit,
                           info=class_data,
                           title=class_data.title,
                           friends=class_data.friends)
                           #downloads=class_data.downloads)

################################################################################
# Searching
################################################################################

def genus2_curve_search(**args):
    info = to_dict(args)
    
    if 'download' in info and info['download'] == '1':
        return download_search(info)
    
    info["st_group_list"] = st_group_list
    info["st_group_dict"] = st_group_dict
    info["real_geom_end_alg_list"] = real_geom_end_alg_list
    info["real_geom_end_alg_to_ST0_dict"] = real_geom_end_alg_to_ST0_dict
    info["aut_grp_list"] = aut_grp_list
    info["aut_grp_dict"] = aut_grp_dict
    info["geom_aut_grp_list"] = geom_aut_grp_list
    info["geom_aut_grp_dict"] = geom_aut_grp_dict
    query = {}  # database callable
    bread = [('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('Search Results', '.')]
    #if 'SearchAgain' in args:
    #    return rational_genus2_curves()

    if 'jump' in args:
        curve_label_regex = re.compile(r'\d+\.[a-z]+.\d+.\d+$')
        if curve_label_regex.match(info["jump"].strip()):
            data = render_curve_webpage_by_label(info["jump"].strip())
        else:
            class_label_regex = re.compile(r'\d+\.[a-z]+$')
            if class_label_regex.match(info["jump"].strip()):
                data = render_isogeny_class(info["jump"].strip())
            else:
                class_label_regex = re.compile(r'#\d+$')
                if class_label_regex.match(info["jump"].strip()) and ZZ(info["jump"][1:]) < 2**61:
                    c = g2cdb().isogeny_classes.find_one({'hash':int(info["jump"][1:])})
                    if c:
                        data = render_isogeny_class(c["label"])
                    else:
                        data = "Hash not found"
                else:
                    data = "Invalid label"
        if isinstance(data,str):
            flash(Markup(data + " <span style='color:black'>%s</span>"%(info["jump"])),"error")
            return redirect(url_for(".index"))
        return data
    try:
        parse_ints(info,query,'abs_disc','absolute discriminant')
        parse_bool(info,query,'is_gl2_type')
        parse_bool(info,query,'has_square_sha')
        parse_bool(info,query,'locally_solvable')
        parse_bracketed_posints(info, query, 'torsion', 'torsion structure', maxlength=4,check_divisibility="increasing")
        parse_ints(info,query,'cond','conductor')
        parse_ints(info,query,'num_rat_wpts','Weierstrass points')
        parse_ints(info,query,'torsion_order')
        if 'torsion' in query and not 'torsion_order' in query:
            query['torsion_order'] = reduce(mul,[int(n) for n in query['torsion']],1)
        parse_ints(info,query,'two_selmer_rank','2-Selmer rank')
        parse_ints(info,query,'analytic_rank','analytic rank')
        # G2 invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
        if info.get('g20') and info.get('g21') and info.get('g22'):
            query['g2inv'] = [ info['g20'], info['g21'], info['g22'] ]
        for fld in ('st_group', 'real_geom_end_alg', 'aut_grp_id', 'geom_aut_grp_id'):
            if info.get(fld): query[fld] = info[fld]
    except ValueError as err:
        info['err'] = str(err)
        return render_template("search_results_g2.html", info=info, title='Genus 2 Curves Search Input Error', bread=bread, credit=credit_string)
    info["query"] = dict(query)
    count = parse_count(info, 50)
    start = parse_start(info)
    cursor = g2cdb().curves.find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    res = cursor.sort([("cond", pymongo.ASCENDING), ("class", pymongo.ASCENDING),  ("disc_key", pymongo.ASCENDING),  ("label", pymongo.ASCENDING)]).skip(start).limit(count)
    nres = res.count()

    if nres == 1:
        info["report"] = "unique match"
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    res_clean = []

    for v in res:
        v_clean = {}
        v_clean["label"] = v["label"]
        v_clean["isog_label"] = v["class"]
        isogeny_class = g2cdb().isogeny_classes.find_one({'label' :
            isog_label(v["label"])})
        v_clean["is_gl2_type"] = isogeny_class["is_gl2_type"]
        if isogeny_class["is_gl2_type"] == True:
            v_clean["is_gl2_type_display"] = '&#10004;' #checkmark
        else:
            v_clean["is_gl2_type_display"] = ''
        v_clean["equation_formatted"] = list_to_min_eqn(v["min_eqn"])
        v_clean["st_group_name"] = st_group_name(isogeny_class['st_group'])
        v_clean["st_group_href"] = st_group_href(isogeny_class['st_group'])
        v_clean["analytic_rank"] = v["analytic_rank"]
        res_clean.append(v_clean)

    info["curves"] = res_clean
    info["curve_url"] = lambda dbc: url_for_label(dbc['label'])
    info["isog_url"] = lambda dbc: isog_url_for_label(dbc['label'])
    info["start"] = start
    info["count"] = count
    info["more"] = int(start+count<nres)
    
    credit = credit_string
    title = 'Genus 2 Curves search results'
    return render_template("search_results_g2.html", info=info, credit=credit,learnmore=learnmore_list(), bread=bread, title=title)

################################################################################
# Statistics
################################################################################

stats_attribute_list = [
    {'name':'num_rat_wpts','top_title':'rational Weierstrass points','row_title':'Weierstrass points','knowl':'g2c.num_rat_wpts','avg':True},
    {'name':'aut_grp_id','top_title':'$\mathrm{Aut}(X)$','row_title':'automorphism group','knowl':'g2c.aut_grp','format':aut_group_name},
    {'name':'geom_aut_grp_id','top_title':'$\mathrm{Aut}(X_{\mathbb{Q}})$','row_title':'automorphism group','knowl':'g2c.geom_aut_grp','format':aut_group_name},
    {'name':'analytic_rank','top_title':'analytic ranks','row_title':'analytic rank','knowl':'g2c.analytic_rank','avg':True},
    {'name':'two_selmer_rank','top_title':'2-Selmer ranks','row_title':'2-Selmer rank','knowl':'g2c.two_selmer_rank','avg':True},
    {'name':'has_square_sha','top_title':'squareness of &#1064;','row_title':'has square Sha','knowl':'g2c.has_square_sha', 'format':boolean_name},
    {'name':'locally_solvable','top_title':'local solvability','row_title':'locally solvable','knowl':'g2c.locally_solvable', 'format':boolean_name},
    {'name':'is_gl2_type','top_title':'$\mathrm{GL}_2$-type','row_title':'is of GL2-type','knowl':'g2c.gl2type', 'format':boolean_name},
    {'name':'real_geom_end_alg','top_title':'Sato-Tate group identity components','row_title':'identity component','knowl':'g2c.st_group_identity_component', 'format':st0_group_name},
    {'name':'st_group','top_title':'Sato-Tate groups','row_title':'Sato-Tate groups','knowl':'g2c.st_group', 'format':st_group_name},
    {'name':'torsion_order','top_title':'torsion subgroup orders','row_title':'torsion order','knowl':'g2c.torsion_order','avg':True},
]

def format_percentage(num, denom):
    return "%10.2f"%((100.0*num)/denom)

class G2C_stats(object):
    """
    Class for creating and displaying statistics for genus 2 curves over Q
    """

    def __init__(self):
        self._counts = {}
        self._stats = {}

    def counts(self):
        self.init_g2c_count()
        return self._counts

    def stats(self):
        self.init_g2c_count()
        self.init_g2c_stats()
        return self._stats

    def init_g2c_count(self):
        if self._counts:
            return
        counts = {}
        ncurves = g2cdb().curves.count()
        counts['ncurves']  = ncurves
        counts['ncurves_c'] = comma(ncurves)
        nclasses = g2cdb().isogeny_classes.count()
        counts['nclasses'] = nclasses
        counts['nclasses_c'] = comma(nclasses)
        max_D = g2cdb().curves.find().sort('abs_disc', DESCENDING).limit(1)[0]['abs_disc']
        counts['max_D'] = max_D
        counts['max_D_c'] = comma(max_D)
        self._counts  = counts

    def init_g2c_stats(self):
        if self._stats:
            return
        g2c_logger.debug("Computing genus 2 curve stats...")
        counts = self._counts
        total = counts["ncurves"]
        stats = {}
        dists = []
        for attr in stats_attribute_list:
            values = g2cdb().curves.distinct(attr['name'])
            values.sort()
            vcounts = []
            rows = []
            colcount = 0
            avg = 0
            for value in values:
                n = g2cdb().curves.find({attr['name']:value}).count()
                prop = format_percentage(n,total)
                if 'avg' in attr and attr['avg']:
                    avg += n*value
                value_string = attr['format'](value) if 'format' in attr else value
                vcounts.append({'value': value_string, 'curves': n, 'query':url_for(".index_Q")+'?'+attr['name']+'='+str(value),'proportion': prop})
                if len(vcounts) == 10:
                    rows.append(vcounts)
                    vcounts = []
            if len(vcounts):
                rows.append(vcounts)
            if 'avg' in attr and attr['avg']:
                vcounts.append({'value':'\\mathrm{avg}\\ %.2f'%(float(avg)/total), 'curves':total, 'query':url_for(".index_Q") +'?'+attr['name'],'proportion':format_percentage(1,1)})
            dists.append({'attribute':attr,'rows':rows})
        stats["distributions"] = dists
        self._stats = stats
        g2c_logger.debug("... finished computing genus 2 curve stats.")

download_comment_prefix = {'magma':'//','sage':'#','gp':'\\\\'}
download_assignment_start = {'magma':'data :=[','sage':'data =[','gp':'data =['}
download_assignment_end = {'magma':'];','sage':']','gp':']'}
download_file_suffix = {'magma':'.m','sage':'.sage','gp':'.gp'}
download_make_data = {
'magma':'function make_data()\n  R<x>:=PolynomialRing(Rationals());\n  return [HyperellipticCurve(R!r[1],R!r[2]):r in data];\nend function;\n',
'sage':'def make_data():\n\tR.<x>=PolynomialRing(QQ)\n\treturn [HyperellipticCurve(R(r[0]),R(r[1])) for r in data]\n\n',
'gp':''
}
download_make_data_comment = {'magma': 'To create a list of curves, type "curves:= make_data();"','sage':'To create a list of curves, type "curves = make_data()"', 'gp':''}

def download_search(info):
    lang = info["submit"]
    filename = 'genus2_curves' + download_file_suffix[lang]
    mydate = time.strftime("%d %B %Y")
    # reissue saved query here
    res = g2cdb().curves.find(ast.literal_eval(info["query"]))
    c = download_comment_prefix[lang]
    s =  '\n'
    s += c + ' Genus 2 curves downloaded from the LMFDB downloaded on %s. Found %s curves.\n'%(mydate, res.count())
    s += c + ' Below is a list called data. Each entry has the form:\n'
    s += c + '   [[f coeffs],[h coeffs]]\n'
    s += c + ' defining the hyperelliptic curve y^2+h(x)y=f(x)\n'
    s += c + '\n'
    s += c + ' ' + download_make_data_comment[lang] + '\n'
    s += '\n'
    s += download_assignment_start[lang] + '\\\n'
    # loop through all search results and grab the curve equations
    for r in res:
        entry = str(r['min_eqn'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        s += entry + ',\\\n'
    s = s[:-3]
    s += download_assignment_end[lang]
    s += '\n\n'
    s += download_make_data[lang]
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True)


@g2c_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of genus 2 curve data over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Completeness','')]
    return render_template("single.html", kid='dq.g2c.extent',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@g2c_page.route("/Source")
def how_computed_page():
    t = 'Source of genus 2 curve data over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Source','')]
    return render_template("single.html", kid='dq.g2c.source',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@g2c_page.route("/Labels")
def labels_page():
    t = 'Labels for genus 2 curves over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' '),('Labels','')]
    return render_template("single.html", kid='g2c.label',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
