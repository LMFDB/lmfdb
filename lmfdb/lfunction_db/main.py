from lmfdb.db_backend import db
import flask
from flask import render_template, request
from lmfdb.utils import Pagination

mod = flask.Blueprint('LfunctionDB', __name__, template_folder="templates")
title = "L-function search"


@mod.context_processor
def body_class():
    return {'body_class': 'LfunctionDB'}


@mod.route("/")
@mod.route("/<zero>")
def zero_search(**kwargs):
    if not 'zero' in kwargs:
        results = db.lfunc_zeros.search()
    else:
        zero = float(kwargs['zero'])
        results = db.lfunc_zeros.search({'first_zero': {'$lt': zero + .1, '$gt': zero - .1}})
    pagination = Pagination(results, per_page=50, page=request.args.get(
        'page', 1), endpoint=".zero_search", endpoint_params=kwargs)
        # result_string = ""
        # printed_arrow = False
        # for x in L:
        #    if x['zero'] > zero and printed_arrow == False:
        #        result_string = result_string + "-------->"
        #        printed_arrow = True
        #    result_string = result_string + str(x['zero']) + " " + str(x['modulus']) + " " + str(x['character']) + "<br>\n"
        # return result_string
    return render_template('lf-list.html', pagination=pagination, title=title)


@mod.route("/query")
def query(**kwargs):
    degree = request.args.get("degree", 0, type=int)
    level = request.args.get("level", 0, type=int)
    first_zero_start = request.args.get("zerolowerbound", -1.0, type=float)
    first_zero_end = request.args.get("zeroupperbound", -1.0, type=float)
    sort = request.args.get("sort", "first_zero", type=str)
    direction = request.args.get("direction", "up", type=str)

    if direction not in ["up", "down"]:
        direction = "up"
    direction = 1 if direction == "up" else -1
    if sort not in ['degree', 'first_zero', 'level', 'coeffs']:
        sort = "first_zero"
    if (sort, direction) == ('first_zero', 1):
        sort = None # uses id if available
    else:
        sort = [(sort, direction)]

    query = {}
    if degree:
        query['degree'] = degree
    if level:
        query['level'] = level

    if first_zero_start != -1.0 or first_zero_end != -1.0:
        query['first_zero'] = {}
    if first_zero_start != -1.0:
        query['first_zero']['$gte'] = float(first_zero_start)
    if first_zero_end != -1.0:
        query['first_zero']['$lte'] = float(first_zero_end)

    results = db.lfunc_zeros.search(query, sort=sort)
    pagination = Pagination(results, per_page=50, page=request.args.get(
        'page', 1), endpoint=".query", endpoint_params=dict(request.args))
    return render_template('lf-list.html', pagination=pagination, title=title)
