# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones

import re
import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb import base
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, make_logger
from sage.all import ZZ, var, PolynomialRing, QQ, latex

from lmfdb.motives import motive_page, motive_logger

HGM_credit = 'D. Roberts and J. Jones'


def get_bread(breads=[]):
    bc = [("Motives", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

LIST_RE = re.compile(r'^(\d+|(\d+-\d+))(,(\d+|(\d+-\d+)))*$')


@motive_page.route("/")
def index():
    bread = get_bread([])
    #if len(request.args) != 0:
    #    return hgm_search(**request.args)
    info = {}
    friends=[('Hypergeometric', url_for(".index2"))]
    return render_template("motive-index.html", title="Motives", bread=bread, credit=HGM_credit, info=info, friends=friends)

@motive_page.route("/Hypergeometric")
@motive_page.route("/Hypergeometric/")
def index2():
    bread = get_bread([('Hypergeometric', url_for('.index2'))])
    info = {}
    friends=[('Hypergeometric over $\Q$', url_for("hypergm.index"))]
    return render_template("hypergeometric-index.html", title="Hypergeometric Motives", bread=bread, credit=HGM_credit, info=info, friends=friends)

