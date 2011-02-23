from base import app, C
from flask import render_template, request

from . import mod
from utils import LazyMongoDBPagination

from copy import copy

import pymongo

@mod.route("/")
@mod.route("/<zero>")
def zero_search(**kwargs):
    if not 'zero' in kwargs:
        query = C.test.Lfunctions_test.find().sort('first_zero')
    else:
        zero = float(kwargs['zero'])
        query = C.test.Lfunctions_test.find({'first_zero' : {'$lt' : zero + .1, '$gt' : zero - .1 } }).sort('first_zero')
    pagination = LazyMongoDBPagination(query = query, per_page=50, page=request.args.get('page', 1), endpoint="zero_search", endpoint_params=kwargs)
        #result_string = ""
        #printed_arrow = False
        #for x in L:
        #    if x['zero'] > zero and printed_arrow == False:
        #        result_string = result_string + "-------->"
        #        printed_arrow = True
        #    result_string = result_string + str(x['zero']) + " " + str(x['modulus']) + " " + str(x['character']) + "<br>\n"
        #return result_string
    return render_template('zero_search/zero_search.html', pagination=pagination, info = {})

@mod.route("/list")
def list_functions(**kwargs):
    degree = request.args.get("degree", 0, type=int)
    conductor = request.args.get("conductor", 0, type=int)
    first_zero_start = request.args.get("zerolowerbound", -1.0, type=float)
    first_zero_end = request.args.get("zeroupperbound", -1.0, type=float)
    sort = request.args.get("sort", "first_zero", type=str)
    direction = request.args.get("direction", "up", type=str)

    if sort not in ['degree', 'first_zero', 'conductor']:
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
    if conductor:
        filter['conductor'] = conductor

    if first_zero_start != -1.0 or first_zero_end != -1.0:
        filter['first_zero'] = {}
    if first_zero_start != -1.0:
        filter['first_zero']['$gte'] = float(first_zero_start)
    if first_zero_end != -1.0:
        filter['first_zero']['$lte'] = float(first_zero_end)

    query = C.test.Lfunctions_test.find(filter).sort(sort, direction)
    pagination = LazyMongoDBPagination(query = query, per_page=50, page=request.args.get('page', 1), endpoint="list_functions", endpoint_params=dict(request.args))
    return render_template('zero_search/zero_search.html', pagination=pagination, info = {'blah' : 'blah'})
