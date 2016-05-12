# -*- coding: utf-8 -*-
import re
from pymongo import ASCENDING, DESCENDING
from lmfdb.base import app
from lmfdb.abvar.fq import abvarfq_page
from flask import render_template, url_for, request, redirect, make_response, send_file
from sage.misc.cachefunc import cached_function

#########################
#   Database connection
#########################

@cached_function
def db_ec():
    return lmfdb.base.getDBConnection().abvar.fq_isog

#########################
#    Top level
#########################

def get_bread(*breads):
    bc = [('Abelian Varieties', url_for("abvar.index")),
          ('Fq', url_for("abvarfq.index"))]
    map(bc.append, breads)
    return bc

def get_credit():
    return 'Kiran Kedlaya'

@app.route("/EllipticCurves/Fq")
def ECFq_redirect():
    return redirect(url_for("abvarfq.abelian_varieties"), **request.args)

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for isogeny classes of abelian varieties', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) < 0, learnmore_list())

#########################
#  Search/navigate
#########################

@abvarfq_page.route("/")
def abelian_varieties():
    args = request.args
    if args:
        return abelian_variety_search(**args)
    else:
        info = {}
        # table[q][g] = number of polys
        # col_heads = list of qs
        # row_heads = list of gs
        return render_template("abvarfq-index.html", title="Abelian Varieties over Finite Fields",
                               info=info, credit=credit, bread=get_bread(), learnmore=learnmore_list())

@abvarfq_page.route("/<int:g>/")
def abelian_varieties_by_g(g):
    return abelian_variety_search(g=g, **request.args)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    return abelian_variety_search(g=g, q=q, **request.args)

def abelian_variety_search(**args):
    pass

def search_input_error(info, bread):
    return render_template("abvarfq-search-results.html", info=info, title='Abelian Variety Search Input Error', bread=get_bread(bread))

@abvarfq_page.route("/<label>")
def by_label(label):
    pass

def by_poly(poly):
    pass

def download_search(info):
    pass

@abvarfq_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Weil polynomial data'
    bread = _common_bread + [('Completeness', '')]
    credit = 'Kiran Kedlaya'
    return render_template("single.html", kid='dq.abvar.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@abvarfq_page.route("/Source")
def how_computed_page():
    pass

@abvarfq_page.route("/Labels")
def labels_page():
                                pass
