# -*- coding: utf-8 -*-
import re
import pymongo
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
import tempfile
import os

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range2, web_latex_split_on_pm, comma, clean_input, parse_range
from lmfdb.number_fields.number_field import parse_list, parse_discs, make_disc_key
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.isog_class import G2Cisog_class, url_for_label, isog_url_for_label
from lmfdb.genus2_curves.web_g2c import WebG2C, list_to_min_eqn, isog_label

import sage.all
from sage.all import ZZ, QQ, latex, matrix, srange
q = ZZ['x'].gen()
# credit_string = "KNOWL('g2c.credit', title='The Genus 2 Team')" 
credit_string = "Andrew Booker, Andrew Sutherland, John Voight, and Dan Yasaki"

#########################
#   Database connection
#########################
g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves
    return g2cdb


#########################
#    Top level
#########################

@app.route("/G2C")
def G2C_redirect():
    return redirect(url_for(".index", **request.args))

#########################
#  Search/navigate
#########################

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
        db_g2c().curves.find_one({"label":"12500.a.12500.1"})
    ]
    info["conductor_list"] = ['1-499', '500-999', '1000-99999','100000-1000000'   ]
    info["discriminant_list"] = ['1-499', '500-999', '1000-99999','100000-1000000'   ]
    st_temp = ['J(C_2)','J(C_4)','J(C_6)','J(D_2)', 'J(D_3)','J(D_4)','J(D_6)', 'J(T)', 'J(O)','C{2,1}','C_{6,1}','D_{2,1}','D_{3,2}','D_{4,1}','D_{4,2}','D_{6,1}','D_{6,2}','O_1','E_1','E_2','E_3','E_4','E_6','J(E_1)','J(E_2)','J(E_3)','J(E_4)','J(E_6)','F_{a,b}','F_{ac}','N(G_{1,3})','G_{3,3}','N(G_{3,3})','USp(4)']
    info["st_group_list"] = [[a,a] for a in st_temp]
    info["real_geom_end_alg_list"] = [
        ['M_2(C)','U(1)'],
        ['M_2(R)','SU(2)'],
        ['C x C','G_{1,1}'],
        ['C x R','G_{1,3}'],
        ['R x R','G_{3,3}'],
        ['R','USp(4)']
        ]
    info["aut_grp_list"] = [
        ['[2, 1]','C_2'],
        ['[4, 1]','C_4'],                   
        ['[4, 2]','V_4'],
        ['[6, 2]','C_6'],                   
        ['[8, 3]','D_8'],                   
        ['[12, 4]','D_{12}']
        ]
    info["geom_aut_grp_list"] = [
        ['[2, 1]','C_2'],
        ['[4, 2]','V_4'],
        ['[8, 3]','D_8'],
        ['[10, 2]','C_{10}'],
        ['[12, 4]','D_{12}'],
        ['[24, 8]','2D_{12}'],
        ['[48, 29]','tilde{S}_4']]
    credit =  credit_string
    title = 'Genus 2 curves over $\Q$'
    bread = [('Genus 2 Curves', url_for(".index")), ('$\Q$', ' ')]
    return render_template("browse_search_g2.html", info=info, credit=credit, title=title, bread=bread)

@g2c_page.route("/Q/<int:conductor>/")
def by_conductor(conductor):
    return genus2_curve_search(cond=conductor, **request.args)

@g2c_page.route("/random")
def random_curve():
    from sage.misc.prandom import randint
    n = get_stats().counts()['ncurves']
    n = randint(0,n-1)
    return render_curve_webpage_by_label(db_g2c().curves.find()[n]['label'])

def split_label(label_string):
    L = label_string.split(".")
    return L

def genus2_curve_search(**args):
    info = to_dict(args)
    query = {}  # database callable
    bread = [('Genus 2 Curves', url_for(".index")),
             ('$\Q$', url_for(".index_Q")),
             ('Search Results', '.')]
    #if 'SearchAgain' in args:
    #    return rational_genus2_curves()

    if 'jump' in args:
        return render_curve_webpage_by_label(info["jump"])

    if info.get("disc"):
        field = "abs_disc"
        ran = info["disc"]
        ran = ran.replace('..', '-').replace(' ','')
        # Past input check
        dlist = parse_discs(ran)
        tmp = g2_list_to_query(dlist)

        if len(tmp) == 1:
            tmp = tmp[0]
        else:
            query[tmp[0][0]] = tmp[0][1]
            tmp = tmp[1]

        print tmp

        # work around syntax for $or
        # we have to foil out multiple or conditions
        if tmp[0] == '$or' and '$or' in query:
            newors = []
            for y in tmp[1]:
                oldors = [dict.copy(x) for x in query['$or']]
                for x in oldors:
                    x.update(y)
                newors.extend(oldors)
            tmp[1] = newors
        query[tmp[0]] = tmp[1]
        
    if info.get("is_gl2_type"):
       query['is_gl2_type']=bool(info['is_gl2_type'])    

    for fld in ['aut_grp', 'geom_aut_grp','st_group','real_geom_end_alg']:
        if info.get(fld):
            query[fld] = info[fld]
    for fld in ['aut_grp', 'geom_aut_grp']:
        if info.get(fld):
            query[fld] = eval(info[fld])

    if info.get("cond"):
        field = "cond"
        ran = str(info[field])
        ran = ran.replace('..', '-').replace(' ','')
        # Past input check
        tmp = parse_range2(ran, field)

        print tmp

        # work around syntax for $or
        # we have to foil out multiple or conditions
        if tmp[0] == '$or' and '$or' in query:
            newors = []
            for y in tmp[1]:
                oldors = [dict.copy(x) for x in query['$or']]
                for x in oldors:
                    x.update(y)
                newors.extend(oldors)
            tmp[1] = newors
        query[tmp[0]] = tmp[1]

    info["query"] = dict(query)

    count_default = 50
    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = count_default
    else:
        count = count_default
    info['count'] = count

    start_default = 0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default

    cursor = db_g2c().curves.find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    #res = db_g2c().curves.find(query).sort([("cond", pymongo.ASCENDING),
    #("label", pymongo.ASCENDING)]).limit(count)
    res = cursor.sort([("cond", pymongo.ASCENDING),
                                            ("class", pymongo.ASCENDING),
                                            ("disc_key", pymongo.ASCENDING),
                                            ("label", pymongo.ASCENDING)]).skip(start).limit(count)
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
        isogeny_class = db_g2c().isogeny_classes.find_one({'label' : isog_label(v["label"])})
        v_clean["is_gl2_type"] = isogeny_class["is_gl2_type"]
        v_clean["equation_formatted"] = list_to_min_eqn(v["min_eqn"])
        res_clean.append(v_clean)

    info["curves"] = res_clean

    info["curve_url"] = lambda dbc: url_for_label(dbc['label'])
    info["isog_url"] = lambda dbc: isog_url_for_label(dbc['label'])
    info["start"] = start
    info["count"] = count
    credit = credit_string
    title = 'Genus 2 Curves search results'
    return render_template("search_results_g2.html", info=info, credit=credit, bread=bread, title=title)

def g2_list_to_query(dlist):
    # if there is only one part, we don't need an $or
    if len(dlist) == 1:
        dlist = dlist[0]
        if type(dlist) == list:
            s0, d0 = make_disc_key(dlist[0])
            s1, d1 = make_disc_key(dlist[1])
            if s0 < 0:
                return [['disc_key', {'$gte': d1, '$lte': d0}]]
            else:
                return [['disc_key', {'$lte': d1, '$gte': d0}]]
        else:
            s0, d0 = make_disc_key(dlist)
            return [['disc_key', d0]]
    # Now dlist has length >1
    ans = []
    for x in dlist:
        if type(x) == list:
            s0, d0 = make_disc_key(x[0])
            s1, d1 = make_disc_key(x[1])
            if s0 < 0:
                ans.append({ 'disc_key': {'$gte': d1, '$lte': d0}})
            else:
                ans.append({ 'disc_key': {'$lte': d1, '$gte': d0}})
        else:
            s0, d0 = make_disc_key(x)
            ans.append({'disc_key': d0})
    return [['$or', ans]]

##########################
#  Specific curve pages
##########################

@g2c_page.route("/Q/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor,iso_label):
    full_iso_label = str(conductor)+"."+iso_label
    return render_isogeny_class(full_iso_label)

@g2c_page.route("/Q/<int:conductor>/<iso_label>/<int:disc>/<int:number>")
def by_full_label(conductor,iso_label,disc,number):
    full_label = str(conductor)+"."+iso_label+"."+str(disc)+"."+str(number)
    g2c_logger.debug(full_label)
    return render_curve_webpage_by_label(full_label)


@g2c_page.route("/Q/<label>")
def by_g2c_label(label):
    g2c_logger.debug(label)
    return render_curve_webpage_by_label(label)

def render_isogeny_class(iso_class):
    credit = credit_string
    class_data = G2Cisog_class.by_label(iso_class)

    return render_template("isogeny_class_g2.html",
                           properties2=class_data.properties,
                           bread=class_data.bread,
                           credit=credit,
                           info=class_data,
                           title=class_data.title,
                           friends=class_data.friends,
                           downloads=class_data.downloads)


def render_curve_webpage_by_label(label):
    credit = credit_string
    data = WebG2C.by_label(label)
    
    return render_template("curve_g2.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           bread=data.bread, title=data.title,
                           friends=data.friends,
                           downloads=data.downloads)
