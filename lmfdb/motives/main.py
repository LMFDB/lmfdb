# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones

import re
from flask import render_template, url_for, redirect, request

from lmfdb.motives import motive_page

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
    return redirect(url_for("hypergm.index", **request.args))

    # For later when we have other hypergeometric motives
    #bread = get_bread([('Hypergeometric', url_for('.index2'))])
    #info = {}
    #friends=[('Hypergeometric over $\Q$', url_for("hypergm.index"))]
    #return render_template("hypergeometric-index.html", title="Hypergeometric Motives", bread=bread, credit=HGM_credit, info=info, friends=friends)

