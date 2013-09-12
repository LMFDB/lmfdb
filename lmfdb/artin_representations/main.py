# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: Paul-Olivier Dehaye

import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.artin_representations import artin_representations_page, artin_logger
from lmfdb.utils import to_dict

from lmfdb.math_classes import *
from lmfdb.WebNumberField import *


def initialize_indices():
    ArtinRepresentation.collection().ensure_index([("Dim", ASC), ("Conductor_plus", ASC)])
    ArtinRepresentation.collection().ensure_index([("Dim", ASC), ("Conductor", ASC)])
    ArtinRepresentation.collection().ensure_index([("Conductor", ASC), ("Dim", ASC)])
    ArtinRepresentation.collection().ensure_index([("Conductor_plus", ASC), ("Dim", ASC)])


def get_bread(breads=[]):
    bc = [("Artin Representations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc


@artin_representations_page.route("/")
def index():
    args = request.args
    bread = get_bread()
    if len(args) == 0:
        return render_template("artin-representation-index.html", title="Artin Representations", bread=bread)
    else:
        return artin_representation_search(**args)


def parse_range_simple(query, fn=lambda x: x):
    tmp = query.split("-")
    if len(tmp) == 1:
        return fn(tmp[0])
    try:
        assert len(tmp) == 2
    except AssertionError:
        raise AssertionError("Error while parsing request")
    return {"$lte": fn(tmp[1]), "$gte": fn(tmp[0])}


def parse_compound(query, fn=lambda x: x):
    tmp = query.split(",")
    return [parse_range_simple(y, fn=fn) for y in tmp]


def artin_representation_search(**args):
    req = to_dict(args)
    title = 'Artin representations search results'
    bread = [('Artin representations', url_for(".index")), ('Search results', ' ')]
    query = {}
    if req.get("ramified", "") != "":
        tmp = req["ramified"].split(",")
        query["BadPrimes"] = {"$all": [str(x) for x in tmp]}
    if req.get("unramified", "") != "":
        tmp = req["unramified"].split(",")
        a = query.get("BadPrimes", {})
        a.update({"$not": {"$in": [str(x) for x in tmp]}})
        query["BadPrimes"] = a

    if req.get("root_number", "") != "":
        try:
            assert req["root_number"] in ["1", "-1"]
        except:
            raise AssertionError("The root number can only be 1 or -1")
        query["Sign"] = int(req["root_number"])

    if req.get("frobenius_schur_indicator", "") != "":
        try:
            assert req["frobenius_schur_indicator"] in ["1", "-1", "0"]
        except:
            raise AssertionError("The Frobenius-Schur indicator can only be 0, 1 or -1")
        query["Indicator"] = int(req["frobenius_schur_indicator"])
    if req.get("group", "") != "":
        try:
            gcs = complete_group_codes(info[field])
            if len(gcs) == 1:
                query['galois'] = make_galois_pair(gcs[0][0], gcs[0][1])
# list(gcs[0])
            if len(gcs) > 1:
                query['galois'] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
        except NameError as code:
            errinfo = 'Error parsing input for Galois group: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
            # info['err'] = 'Error parsing input for Galois group: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
            raise AssertionError(errinfo)
            #return search_input_error(info, bread)



    tmp_conductor = []
    if req.get("conductor", "") != "":
        from lmfdb.utils import len_val_fn
        tmp_conductor = parse_compound(req["conductor"], fn=len_val_fn)
    # examples of tmp_conductor: [],
    # [{"len":2,"val":"44"},{"len":3,"val":"444"},{"$gte":{"len":2,"val":"44"},
    # "$lte":{"len":5,"val";"44444"}}]
    tmp_dimension = []
    if req.get("dimension", "") != "":
        tmp_dimension = parse_compound(req["dimension"], fn=int)
    # examples of tmp_dimension: [], [17], [5,7,{"$gte":4, "$lte":10}]
    tmp_both = [{"Conductor_plus": c, "Dim": d} for c in tmp_conductor for d in tmp_dimension]
    if len(tmp_conductor) == 0:
        tmp_both += [{"Dim": d} for d in tmp_dimension]
    if len(tmp_dimension) == 0:
        tmp_both += [{"Conductor_plus": c} for c in tmp_conductor]
    if len(tmp_both) == 1:
        query.update(tmp_both[0])
    elif len(tmp_both) >= 2:
        query["$or"] = tmp_both

    count = int(req.get('count', 20))

    for i in range(10):
        print query
    from pymongo import ASCENDING
    ArtinRepresentation.collection().ensure_index([("Dim", ASCENDING), ("Conductor_plus", ASCENDING)])
    data = [ArtinRepresentation(data=x) for x in ArtinRepresentation.collection(
    ).find(query).sort([("Dim", ASCENDING), ("Conductor_plus", ASCENDING)]).limit(count)]
    return render_template("artin-representation-search.html", req=req, data=data, data_count=len(data), title=title, bread=bread, query=query)


# Obsolete
#@artin_representations_page.route("/search", methods = ["GET", "POST"])
# def search():
#  if request.method == "GET":
#    val = request.args.get("val", "no value")
#    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
#    return render_template("artin-representations-search.html", title="Artin Representations Search", bread = bread, val = val)
#  elif request.method == "POST":
#    return "ERROR: we always do http get to explicitly display the search parameters"
#  else:
#    return flask.redirect(404)
@artin_representations_page.route("/<dim>/<conductor>/<index>")
def by_data_no_slash(dim, conductor, index):
    return flask.redirect(url_for(".by_data", dim=dim, conductor=conductor, index=index), code=301)


@artin_representations_page.route("/<dim>/<conductor>/<index>/")
def by_data(dim, conductor, index):
    artin_logger.debug("Asked for the Artin representation with parameters dim: %s conductor: %s index: %s" %
                       (dim, conductor, index))
    return render_artin_representation_webpage(dim, conductor, index)


@artin_representations_page.route("/<dim>/<conductor>/")
def by_partial_data(dim, conductor):
    artin_logger.debug("Asked for the set of Artin representations with parameters dim: %s conductor: %s " %
                       (dim, conductor))
    return render_artin_representation_set_webpage(dim, conductor)


# credit information should be moved to the databases themselves, not at the display level. that's too late.
tim_credit = "Tim Dokchitser on Magma"
support_credit = "Support by Paul-Olivier Dehaye."


def render_artin_representation_webpage(dim, conductor, index):
    the_rep = ArtinRepresentation.find_one(
        {'Dim': int(dim), "Conductor": str(conductor), "DBIndex": int(index)})

    artin_logger.info("Found %s" % (the_rep._data))

    bread = get_bread([(str("Dimension %s, conductor %s, index %s" % (the_rep.dimension(),
                      the_rep.conductor(), the_rep.index())), ' ')])

    title = the_rep.title()
    the_nf = the_rep.number_field_galois_group()
    from lmfdb.number_field_galois_groups import nfgg_page
    from lmfdb.number_field_galois_groups.main import by_data
    if the_rep.root_number() == 0:
        processed_root_number = "unknown"
    else:
        processed_root_number = str(the_rep.root_number())
    properties = [("Root number", processed_root_number),
                  ("Dimension", str(the_rep.dimension())),
                  ("Conductor", str(the_rep.conductor())),
                  ("Factored conductor", "$" + the_rep.factored_conductor_latex() + "$"),
                  #("Bad primes", str(the_rep.bad_primes())),
                  ("Frobenius-Schur indicator", str(the_rep.indicator()))
                  ]

    friends = []
    nf_url = the_nf.url_for()
    if nf_url:
        friends.append(("Artin Field", nf_url))

    friends.append(("L-function", url_for("l_functions.l_function_artin_page",
                                          dimension=the_rep.dimension(),
                                          conductor=the_rep.conductor(),
                                          tim_index=the_rep.index())))
              #[
              #("Same degree and conductor", url_for(".by_partial_data", dim = the_rep.dimension(), conductor = the_rep.conductor())),\
              #("L-function", url_for("l_functions.l_function_artin_page",  dimension = the_rep.dimension(), conductor = the_rep.conductor(), tim_index = the_rep.index()))
              #]
    return render_template("artin-representation-show.html", credit=tim_credit, support=support_credit, title=title, bread=bread, friends=friends, object=the_rep, properties2=properties)


def render_artin_representation_set_webpage(dim, conductor):
    try:
        the_reps = ArtinRepresentation.find({'Dim': int(dim), "Conductor": str(conductor)})
    except:
        pass

    bread = get_bread([(str("Dimension %s, conductor %s" % (dim, conductor)), ' ')])

    title = "Artin representations of dimension $%s$ and conductor $%s$" % (dim, conductor)

    return render_template("artin-representation-set-show.html", credit=tim_credit, support=support_credit, title=title, bread=bread, object=the_reps)
