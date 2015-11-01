# -*- coding: utf-8 -*-
# This Blueprint is about the Galois groups of number fields
# Author: Paul-Olivier Dehaye

import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb.base import app, getDBConnection, url_for
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.number_field_galois_groups import nfgg_page, nfgg_logger
from lmfdb.math_classes import *


def initialize_indices():
    try:
        NumberFieldGaloisGroup.collection().ensure_index([("label", ASC)])
        NumberFieldGaloisGroup.collection().ensure_index([("Size", ASC)])
        NumberFieldGaloisGroup.collection(
        ).ensure_index([("Transitive_degree", ASC), ("Size", ASC), ("DBIndex", ASC)])
    except pymongo.errors.OperationFailure:
        pass


def get_bread(breads=[]):
    bc = [("Number Field Galois Group", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


@nfgg_page.route("/")
def index():
    bread = get_bread()
    return render_template("nfgg-index.html", title="Galois groups of number fields", bread=bread)


@nfgg_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("nfgg-search.html", title="Search for Galois groups of number fields", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return flask.redirect(404)


@nfgg_page.route("/<degree>/<size>/<index>")
def by_data(degree, size, index):
    nfgg_logger.debug(
        "Asked for the Galois group of size %s on %s points, with index %s" % (size, degree, index))
    return render_nfgg_webpage(degree, size, index)


@nfgg_page.route("/<degree>/<size>")
def by_partial_data(degree, size):
    nfgg_logger.debug("Asked for the Galois groups of size %s on %s points" % (size, degree))
    return render_nfgg_set_webpage(degree, size)


tim_credit = "Tim Dokchitser"
support_credit = "Support by Paul-Olivier Dehaye"


def render_nfgg_webpage(degree, size, index):
    the_nfgg = NumberFieldGaloisGroup.find_one(
        {"Degree": int(degree), "Size": int(size), "DBIndex": int(index)})
    if the_nfgg._data is None:
    # I haven't found it
        raise NotImplementedError

    nfgg_logger.info("Found %s" % (the_nfgg._data))

    bread = get_bread([(
        str("Degree %s, size %s, index %s" % (the_nfgg.degree(), the_nfgg.size(), the_nfgg.index())), ' ')])
    properties2 = [('Degree', '%s' % the_nfgg.degree()),
                   ('Size', '\(%s\)' % the_nfgg.size()),
                   ('Polynomial', '\(%s\)' % the_nfgg.polynomial().latex())]
                     #('Residue characteristic', '\(%s\)' % the_nfgg.residue_characteristic()

    return render_template("nfgg-show.html", credit=tim_credit, support=support_credit, title=the_nfgg.display_title(), bread=bread, info=the_nfgg, properties2=properties2)


def render_nfgg_set_webpage(degree, size):
    the_nfggs = NumberFieldGaloisGroup.find({"Degree": int(degree), "Size": int(size)})

    # nfgg_logger.info("Found %s"%(the_nfggs._data))

    bread = get_bread([(str("Degree %s, size %s" % (degree, size)), ' ')])
    title = "Number field Galois groups of degree $%s$ and size $%s$" % (degree, size)

    return render_template("nfgg-set-show.html", credit=tim_credit, support=support_credit, title=title, bread=bread, info=the_nfggs)
