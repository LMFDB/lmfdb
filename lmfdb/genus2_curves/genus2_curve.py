# -*- coding: utf-8 -*-
import StringIO
import ast
import re
import time
import pymongo
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from flask import Flask, flash, session, g, render_template, url_for, request, redirect, make_response, send_file
from markupsafe import Markup
import tempfile
import os

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict
from lmfdb.search_parsing import parse_bool, parse_ints, parse_signed_ints, parse_bracketed_posints, parse_count, parse_start
from lmfdb.number_fields.number_field import make_disc_key
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.isog_class import G2Cisog_class, url_for_label, isog_url_for_label
from lmfdb.genus2_curves.web_g2c import WebG2C, list_to_min_eqn, isog_label, st_group_name

import sage.all
from sage.all import ZZ, QQ, latex, matrix, srange
#q = ZZ['x'].gen()
credit_string = "Andrew Booker, Jeroen Sijsling, Andrew Sutherland, John Voight, and Dan Yasaki"

###############################################################################
# Database connection
###############################################################################

g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves
    return g2cdb

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
# Routing for top level, random curves and by conductor:
###############################################################################

@app.route("/G2C")
def G2C_redirect():
    return redirect(url_for(".index", **request.args))

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
    curve_count = db_g2c().curves.count()
    if len(request.args) != 0:
        return genus2_curve_search(**request.args)
    info = {'count' : curve_count}
    info["curve_url"] =  lambda dbc: url_for_label(dbc['label'])
    info["browse_curves"] = [
        db_g2c().curves.find_one({"label":"169.a.169.1"}),
        db_g2c().curves.find_one({"label":"1152.a.147456.1"}),
        db_g2c().curves.find_one({"label":"12500.a.12500.1"}),
        db_g2c().curves.find_one({"label":"23552.a.23552.1"})
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
    credit =  credit_string
    title = 'Genus 2 curves over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' ')]
    return render_template("browse_search_g2.html", info=info, credit=credit, title=title, learnmore=learnmore_list(), bread=bread)

@g2c_page.route("/Q/<int:conductor>/")
def by_conductor(conductor):
    return genus2_curve_search(cond=conductor, **request.args)

@g2c_page.route("/Q/random")
def random_curve():
    from sage.misc.prandom import randint
    n = db_g2c().curves.count()
    n = randint(0,n-1)
    label = db_g2c().curves.find()[n]['label']
    # This version leaves the word 'random' in the URL:
    #return render_curve_webpage_by_label(label)
    # This version uses the curve's own URL:
    return redirect(url_for(".by_g2c_label", label=label), 301)

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
    if data == "Invalid label":
        return data
    if data == "Data for curve not found":
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
        label_regex = re.compile(r'\d+\.[a-z]+.\d+.\d+')
        if label_regex.match(info["jump"].strip()):
            data = render_curve_webpage_by_label(info["jump"].strip())
        else:
            data = "Invalid label"
        if data == "Invalid label":
            flash(Markup("The label <span style='color:black'>%s</span> is invalid."%(info["jump"])),"error")
            return redirect(url_for(".index"))
        if data == "Data for curve not found":
            flash(Markup("No genus 2 curve with label <span style='color:black'>%s</span> was found in the database."%(info["jump"])),"error")
            return redirect(url_for(".index"))
        return data
    try:
        parse_ints(info,query,'abs_disc','absolute discriminant')
        parse_bool(info,query,'is_gl2_type')
        parse_bool(info,query,'has_square_sha')
        parse_bool(info,query,'locally_solvable')
        for fld in ('st_group', 'real_geom_end_alg'):
            if info.get(fld): query[fld] = info[fld]
        for fld in ('aut_grp', 'geom_aut_grp'):
            parse_bracketed_posints(info,query,fld,exactlength=2) #Encoded into a GAP ID.
        # igusa and igusa_clebsch invariants not currently searchable
        parse_bracketed_posints(info, query, 'torsion', 'torsion structure', maxlength=4,check_divisibility="increasing")
        parse_ints(info,query,'cond','conductor')
        parse_ints(info,query,'num_rat_wpts','Weierstrass points')
        parse_ints(info,query,'torsion_order')
        parse_ints(info,query,'two_selmer_rank','2-Selmer rank')
        parse_ints(info,query,'analytic_rank','analytic rank')
    except ValueError as err:
        info['err'] = str(err)
        return render_template("search_results_g2.html", info=info, title='Genus 2 Curves Search Input Error', bread=bread, credit=credit_string)

    info["query"] = dict(query)
    count = parse_count(info, 50)
    start = parse_start(info)
    cursor = db_g2c().curves.find(query)
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
        isogeny_class = db_g2c().isogeny_classes.find_one({'label' :
            isog_label(v["label"])})
        v_clean["is_gl2_type"] = isogeny_class["is_gl2_type"]
        if isogeny_class["is_gl2_type"] == True:
            v_clean["is_gl2_type_display"] = '&#10004;' #checkmark
        else:
            v_clean["is_gl2_type_display"] = ''
        v_clean["equation_formatted"] = list_to_min_eqn(v["min_eqn"])
        v_clean["st_group_name"] = st_group_name(isogeny_class['st_group'])
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

def download_search(info):
    dltype = info["submit"]
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'genus2_curves.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'genus2_curves.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'genus2_curves.m'
    s = com1 + "\n"
    # reissue saved query here
    res = db_g2c().curves.find(ast.literal_eval(info["query"]))
    s += com + ' Genus 2 curves downloaded from the LMFDB downloaded on %s. Found %s curves.\n'%(mydate, res.count())
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [Weierstrass Coefficients]\n'
    s += '\n' + com2
    s += '\n'
    if dltype == 'magma':
        s += 'data := ['
    else:
        s += 'data = ['
    s += '\\\n'
    # loop through all search results and grab the curve equations
    for r in res:
        entry = str(r['min_eqn'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        s += entry + ',\\\n'
    s = s[:-3]
    s += ']\n'
    if delim == 'brace':
        s = s.replace('[', '{')
        s = s.replace(']', '}')
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
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


