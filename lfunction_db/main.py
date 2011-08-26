from base import app, getDBConnection
import flask
from flask import render_template, request

from utils import LazyMongoDBPagination
from copy import copy

import pymongo

mod = flask.Blueprint('LfunctionDB', __name__, template_folder="templates")
title = "First Zero Search Example"

@mod.context_processor
def body_class():
  return { 'body_class' : 'LfunctionDB' }

@mod.route("/")
@mod.route("/<zero>")
def zero_search(**kwargs):
    C = getDBConnection()
    if not 'zero' in kwargs:
        query = C.test.Lfunctions_test2.find().sort('first_zero')
    else:
        zero = float(kwargs['zero'])
        query = C.test.Lfunctions_test2.find({'first_zero' : {'$lt' : zero + .1, '$gt' : zero - .1 } }).sort('first_zero')
    pagination = LazyMongoDBPagination(query = query, per_page=50, page=request.args.get('page', 1), endpoint=".zero_search", endpoint_params=kwargs)
        #result_string = ""
        #printed_arrow = False
        #for x in L:
        #    if x['zero'] > zero and printed_arrow == False:
        #        result_string = result_string + "-------->"
        #        printed_arrow = True
        #    result_string = result_string + str(x['zero']) + " " + str(x['modulus']) + " " + str(x['character']) + "<br>\n"
        #return result_string
    return render_template('lf-list.html', pagination=pagination, title=title)

@mod.route("/query")
def query(**kwargs):
    C = getDBConnection()
    degree = request.args.get("degree", 0, type=int)
    level = request.args.get("level", 0, type=int)
    first_zero_start = request.args.get("zerolowerbound", -1.0, type=float)
    first_zero_end = request.args.get("zeroupperbound", -1.0, type=float)
    sort = request.args.get("sort", "first_zero", type=str)
    direction = request.args.get("direction", "up", type=str)

    if sort not in ['degree', 'first_zero', 'level', 'coeffs']:
        sort = "first_zero"
    if direction not in ["up", "down"]:
        direction = "up"

    if direction == "up":
        direction = pymongo.ASCENDING
    else:
        direction = pymongo.DESCENDING

    filter = {}
    if degree:
        filter['degree'] = degree
    if level:
        filter['level'] = level

    if first_zero_start != -1.0 or first_zero_end != -1.0:
        filter['first_zero'] = {}
    if first_zero_start != -1.0:
        filter['first_zero']['$gte'] = float(first_zero_start)
    if first_zero_end != -1.0:
        filter['first_zero']['$lte'] = float(first_zero_end)

    query = C.test.Lfunctions_test2.find(filter).sort(sort, direction)
    pagination = LazyMongoDBPagination(query = query, per_page=50, page=request.args.get('page', 1), endpoint=".query", endpoint_params=dict(request.args))
    return render_template('lf-list.html', pagination=pagination, title=title)
