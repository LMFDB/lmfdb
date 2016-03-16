# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: Paul-Olivier Dehaye, John Jones

import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.artin_representations import artin_representations_page, artin_logger
from lmfdb.utils import to_dict
from lmfdb.transitive_group import *
import re


from lmfdb.math_classes import *
from lmfdb.WebNumberField import *

def initialize_indices():
    try:
#        ArtinRepresentation.collection().ensure_index([("Dim", ASC), ("Conductor_plus", ASC),("galorbit", ASC)])
#        ArtinRepresentation.collection().ensure_index([("Dim", ASC), ("Conductor", ASC)])
#        ArtinRepresentation.collection().ensure_index([("Conductor", ASC), ("Dim", ASC)])
	pass
    except pymongo.errors.OperationFailure:
        pass

def get_bread(breads=[]):
    bc = [("Artin Representations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def make_cond_key(D):
    D1=ZZ(D)
    if D1<1: D1=ZZ(1)
    D1 = int(D1.log(10))
    return '%04d%s'%(D1,str(D))


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
    if 'natural' in req:
        label = req['natural']
        # test if it is ok
        return render_artin_representation_webpage(label)

    title = 'Artin representation search results'
    bread = [('Artin representation', url_for(".index")), ('Search results', ' ')]
    sign_code = 0
    query = {'Hide': 0}
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
        sign_code= int(req["root_number"])
        query["GaloisConjugates.Sign"] = sign_code

    if req.get("frobenius_schur_indicator", "") != "":
        try:
            assert req["frobenius_schur_indicator"] in ["1", "-1", "0"]
        except:
            raise AssertionError("The Frobenius-Schur indicator can only be 0, 1 or -1")
        query["Indicator"] = int(req["frobenius_schur_indicator"])
    if req.get("group", "") != "":
        try:
            gcs = complete_group_codes(req['group'])
            if len(gcs) == 1:
                query['Galois_nt'] = gcs[0]
            if len(gcs) > 1:
                query['Galois_nt'] = {'$in': [x for x in gcs]}
        except NameError as code:
            info = {}
            info['err'] = 'Error parsing input for Galois group: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
            return search_input_error(info, bread)


    tmp_conductor = []
    if req.get("conductor", "") != "":
        tmp_conductor = parse_compound(req["conductor"], fn=make_cond_key)
    # examples of tmp_conductor: [],
    # [{"len":2,"val":"44"},{"len":3,"val":"444"},{"$gte":{"len":2,"val":"44"},
    # "$lte":{"len":5,"val";"44444"}}]
    tmp_dimension = []
    if req.get("dimension", "") != "":
        tmp_dimension = parse_compound(req["dimension"], fn=int)
    # examples of tmp_dimension: [], [17], [5,7,{"$gte":4, "$lte":10}]
    tmp_both = [{"Conductor_key": c, "Dim": d} for c in tmp_conductor for d in tmp_dimension]
    if len(tmp_conductor) == 0:
        tmp_both += [{"Dim": d} for d in tmp_dimension]
    if len(tmp_dimension) == 0:
        tmp_both += [{"Conductor_key": c} for c in tmp_conductor]
    if len(tmp_both) == 1:
        query.update(tmp_both[0])
    elif len(tmp_both) >= 2:
        query["$or"] = tmp_both

    count_default = 50
    if req.get('count'):
        try:
            count = int(req['count'])
        except:
            count = count_default
    else:
        count = count_default
    req['count'] = count

    start_default = 0
    if req.get('start'):
        try:
            start = int(req['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default
    if req.get('paging'):
        try:
            paging = int(req['paging'])
            if paging == 0:
                start = 0
        except:
            pass


    data = ArtinRepresentation.collection().find(query).sort([("Dim", ASC), ("Conductor_key", ASC)])
    nres = data.count()
    data = data.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    if nres == 1:
        report = 'unique match'
    else:
        if nres > count or start != 0:
            report = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            report = 'displaying all %s matches' % nres
    if nres == 0:
        report = 'no matches'


    initfunc = ArtinRepresentation

    return render_template("artin-representation-search.html", req=req, data=data, title=title, bread=bread, query=query, start=start, report=report, nres=nres, initfunc=initfunc, sign_code=sign_code)


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
#
#@artin_representations_page.route("/<label>/")
#def by_label_with_slash(label):
#    print "here"
#    return flask.redirect(url_for(".render_artin_representation_webpage", label=label), code=301)

def search_input_error(info, bread):
    return render_template("artin-representation-search.html", req=info, title='Artin Representation Search Error', bread=bread)

@artin_representations_page.route("/<dim>/<conductor>/")
def by_partial_data(dim, conductor):
    return artin_representation_search(**{'dimension': dim, 'conductor': conductor})


# credit information should be moved to the databases themselves, not at the display level. that's too late.
tim_credit = "Tim Dokchitser, John Jones, and David Roberts"
support_credit = "Support by Paul-Olivier Dehaye."

@artin_representations_page.route("/<label>")
@artin_representations_page.route("/<label>/")
def render_artin_representation_webpage(label):
    if re.compile(r'^\d+$').match(label):
        return artin_representation_search(**{'dimension': label})

    # label=dim.cond.nTt.indexcj, c is literal, j is index in conj class
    # Should we have a big try around this to catch bad labels?
    the_rep = ArtinRepresentation(label)

    extra_data = {} # for testing?
    C = getDBConnection()
    extra_data['galois_knowl'] = group_display_knowl(5,3,C) # for testing?
    #artin_logger.info("Found %s" % (the_rep._data))

    bread = get_bread([(label, ' ')])

    title = "Artin representation %s" % label
    the_nf = the_rep.number_field_galois_group()
    from lmfdb.number_field_galois_groups import nfgg_page
    from lmfdb.number_field_galois_groups.main import by_data
    if the_rep.sign() == 0:
        processed_root_number = "not computed"
    else:
        processed_root_number = str(the_rep.sign())
    properties = [("Dimension", str(the_rep.dimension())),
                  ("Group", the_rep.group()),
                  #("Conductor", str(the_rep.conductor())),
                  ("Conductor", "$" + the_rep.factored_conductor_latex() + "$"),
                  #("Bad primes", str(the_rep.bad_primes())),
                  ("Root number", processed_root_number),
                  ("Frobenius-Schur indicator", str(the_rep.indicator()))
                  ]

    friends = []
    nf_url = the_nf.url_for()
    if nf_url:
    	friends.append(("Artin Field", nf_url))

    friends.append(("L-function", url_for("l_functions.l_function_artin_page",
                                          label=the_rep.label())))
    info={}
    #info['pol2']=str(the_rep.central_char(2))
    #info['pol3']=str(the_rep.central_char(3))
    #info['pol5']=str(the_rep.central_char(5))
    #info['pol7']=str(the_rep.central_char(7))
    #info['pol11']=str(the_rep.central_char(11))

    return render_template("artin-representation-show.html", credit=tim_credit, support=support_credit, title=title, bread=bread, friends=friends, object=the_rep, properties2=properties, extra_data=extra_data, info=info)

