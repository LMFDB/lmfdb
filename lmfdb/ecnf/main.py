# -*- coding: utf-8 -*-
# This Blueprint is about Local Number Fields
# Author: John Jones

#import re
import pymongo
ASC = pymongo.ASCENDING
#import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect
from lmfdb.utils import image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ
from lmfdb.ecnf import ecnf_page, logger

credit = "ECNF Credits" # TODO fill this in

db_ecnf = lambda : getDBConnection().elliptic_curves.ecnf

class ECNF(object):
    """
    ECNF Wrapper
    """

    def __init__(self, dbdata):
        """
        Arguments:

            - dbdata: the data from the database
        """
        dbdata.pop("_id")
        self.__dict__.update(dbdata)

    @staticmethod
    def by_label(label):
        """
        searches for a specific elliptic curve in the ecnf collection by its label
        """
        data = db_ecnf().find_one({"ec.label" : label})
        return ECNF(data)


def get_bread(*breads):
    bc = [("ECNF", url_for(".index"))]
    map(bc.append, breads)
    return bc


@ecnf_page.route("/")
def index():
    bread = get_bread()
    return render_template("ecnf-index.html", 
        title="Elliptic Curve Number Field",
        bread=bread)


@ecnf_page.route("/<nf>/<label>")
def show_ecnf(nf, label):
    title = "Elliptic Curve %s over Number Field %s" % (label, nf)
    bread = get_bread((label, url_for(".show_ecnf", label = label, nf = nf)))
    info = {}
    info["data1"] = "abc %s" % label
    info["data2"] = "xyz %s" % nf
    return render_template("show-ecnf.html",
        credit=credit,
        title=title,
        bread=bread,
        **info)


@ecnf_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("lf-search.html", title="Local Number Field Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return redirect(404)

