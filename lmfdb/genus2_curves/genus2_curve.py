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
from lmfdb.number_fields.number_field import parse_list
from lmfdb.genus2_curves import g2c_page, g2c_logger
from lmfdb.genus2_curves.isog_class import G2Cisog_class
from lmfdb.genus2_curves.web_g2c import WebG2C, list_to_min_eqn

import sage.all
from sage.all import ZZ, QQ, EllipticCurve, latex, matrix, srange
q = ZZ['x'].gen()

#########################
#   Database connection
#########################
g2cdb = None

def db_g2c():
    global g2cdb
    if g2cdb is None:
        g2cdb = lmfdb.base.getDBConnection().genus2_curves.curves
    return g2cdb


#########################
#    Top level
#########################

@app.route("/G2C")
def G2C_redirect():
    return redirect(url_for("g2c.rational_genus2_curves", **request.args))

#########################
#  Search/navigate
#########################

@g2c_page.route("/")
def rational_genus2_curves(err_args=None):
    if err_args is None:
        if len(request.args) != 0:
            return genus2_curve_search(**request.args)
        else:
            err_args = {}
            for field in ['conductor', 'jinv', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure', 'msg']:
                err_args[field] = ''
            err_args['count'] = '100'
    info = {
    }
    credit = 'Genus 2 Team'
    t = 'Genus 2 curves over $\Q$'
    bread = []
#    bread = [('Genus 2 Curves', url_for("ecnf.index")), ('$\Q$', ' ')]
    return render_template("browse_search_g2.html", info=info, credit=credit, title=t, bread=bread, **err_args)



@g2c_page.route("/<int:conductor>/")
def by_conductor(conductor):
    return genus2_curve_search(conductor=conductor, **request.args)

def split_label(label_string):
    L = label_string.split(".")
    return L


def genus2_curve_search(**args):
    info = to_dict(args)
    query = {}  # database callable
    bread = [
# ('Genus 2 Curves', url_for("ecnf.index")),
             ('$\Q$', url_for(".rational_genus2_curves")),
             ('Search Results', '.')]
    #if 'SearchAgain' in args:
    #    return rational_genus2_curves()

    if 'jump' in args:
        return render_curve_webpage_by_label(info["jump"])

    for field in ["cond", "disc"]:
        if info.get(field):
            query[field] = parse_range(info[field])
    if info.get("count"):
        try:
            count = int(info["count"])
        except:
            count = 100
    else:
        count = 100

    info["query"] = dict(query)
    res = db_g2c().find(query).sort([("cond", pymongo.ASCENDING),
                                     ("label", pymongo.ASCENDING)
                                 ]).limit(count)
    nres = res.count()
    if nres == 1:
        info["report"] = "unique match"
    else:
        if nres > count:
            info["report"] = "displaying first %s of %s matches" % (count, nres)
        else:
            info["report"] = "displaying all %s matches" % nres
    res_clean = []
    for v in res:
        v_clean = {}
        v_clean["label"] = v["label"]
        v_clean["equation_formatted"] = list_to_min_eqn(v["min_eqn"])
        res_clean.append(v_clean)

    info["curves"] = res_clean

    #conductor,iso_label,disc,number
    info["curve_url"] = lambda dbc: url_for(".by_full_label",
                                            conductor=split_label(dbc['label'])[0],
                                            iso_label=split_label(dbc['label'])[1],
                                            disc=split_label(dbc['label'])[2],
                                            number=split_label(dbc['label'])[3]   )
    credit = 'Genus 2 Team'
    t = 'Genus 2 Curves search results'
    return render_template("search_results_g2.html", info=info, credit=credit, bread=bread, title=t)


def search_input_error(info, bread):
    return render_template("search_results.html", info=info, title='Genus 2 Search Input Error', bread=bread)

##########################
#  Specific curve pages
##########################

@g2c_page.route("/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor,iso_label):
    full_iso_label = str(conductor)+"."+iso_label
    return render_isogeny_class(full_iso_label)

@g2c_page.route("/<int:conductor>/<iso_label>/<int:disc>/<int:number>")
def by_full_label(conductor,iso_label,disc,number):
    full_label = str(conductor)+"."+iso_label+"."+str(disc)+"."+str(number)
    g2c_logger.debug(full_label)
    return render_curve_webpage_by_label(full_label)


# The following function determines whether the given label is in
# LMFDB or Cremona format, and also whether it is a curve label or an
# isogeny class label, and calls the appropriate function

@g2c_page.route("/<label>")
def by_g2c_label(label):
    g2c_logger.debug(label)
    try:
        N, iso, number = split_lmfdb_label(label)
    except AttributeError:
        ec_logger.debug("%s not a valid lmfdb label, trying cremona")
        try:
            N, iso, number = split_cremona_label(label)
        except AttributeError:
            ec_logger.debug("%s not a valid cremona label either, trying Weierstrass")
            eqn = label.replace(" ","")
            if weierstrass_eqn_regex.match(eqn) or short_weierstrass_eqn_regex.match(eqn):
                return by_weierstrass(eqn)
            else:
                return elliptic_curve_jump_error(label, {})

        # We permanently redirect to the lmfdb label
        if number:
            data = db_ec().find_one({'label': label})
            if data is None:
                return elliptic_curve_jump_error(label, {})
            ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
            return redirect(url_for(".by_ec_label", label=data['lmfdb_label']), 301)
        else:
            data = db_ec().find_one({'iso': label})
            if data is None:
                return elliptic_curve_jump_error(label, {})
            ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
            return redirect(url_for(".by_ec_label", label=data['lmfdb_iso']), 301)
    if number:
        return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=number))
    else:
        return redirect(url_for(".by_double_iso_label", conductor=N, iso_label=iso))

def render_isogeny_class(iso_class):
    credit = 'Genus 2 Team'
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
    credit = 'Genus 2 Team'
    data = WebG2C.by_label(label)
    
    
    return render_template("curve_g2.html",
                           properties2=data.properties,
                           credit=credit,
                           data=data,
                           bread=data.bread, title=data.title,
                           friends=data.friends,
                           downloads=data.downloads)
