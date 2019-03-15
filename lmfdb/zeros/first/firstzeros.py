# -*- coding: utf-8 -*-
from lmfdb.logger import make_logger
import os
from flask import Blueprint, Response, render_template, request, url_for

FirstZeros = Blueprint('first L-function zeros',
                       __name__, template_folder="templates")
logger = make_logger(FirstZeros)

import sqlite3
data_location = os.path.expanduser("~/data/zeros/")


@FirstZeros.route("/")
def firstzeros():
    start = request.args.get('start', None, float)
    end = request.args.get('end', None, float)
    limit = request.args.get('limit', 100, int)
    degree = request.args.get('degree', None, int)
    # signature_r = request.arts.get("signature_r", None, int)
    # signature_c = request.arts.get("signature_c", None, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    # return render_template("first_zeros.html", start=start, end=end,
    # limit=limit, degree=degree, signature_r=signature_r,
    # signature_c=signature_c)
    title = "Search for First Zeros of L-functions"
    bread = [("L-functions", url_for("l_functions.l_function_top_page")),
             ("First Zeros Search", " "), ]
    return render_template("first_zeros.html",
                           start=start, end=end, limit=limit,
                           degree=degree, title=title, bread=bread)


@FirstZeros.route("/list")
def list_zeros(start=None,
               end=None,
               limit=None,
               fmt=None,
               download=None,
               degree=None):
    if start is None:
        start = request.args.get('start', None, float)
    if end is None:
        end = request.args.get('end', None, float)
    if limit is None:
        limit = request.args.get('limit', 100, int)
    if fmt is None:
        fmt = request.args.get('format', 'plain', str)
    if download is None:
        fmt = request.args.get('download', 'no')
    if degree is None:
        degree = request.args.get('degree', None, int)
    # if signature_r is None:
    #    signature_r = request.arts.get("signature_r", None, int)
    # if signature_c is None:
    #    signature_c = request.arts.get("signature_c", None, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    if start is None and end is None:
        end = 1000

    where_clause = 'WHERE 1=1 '
    values = []
    if end is not None:
        # fix up rounding errors
        # otherwise each time you resubmit the page you will lose one line
        if('.' in str(end)):
            end = float(str(end)+'999')

    if start is None:
        end = float(end)
        where_clause += ' AND zero <= ?'
        values.append(end)
    elif end is None:
        start = float(start)
        where_clause += ' AND zero >= ?'
        values.append(start)
    else:
        start = float(start)
        end = float(end)
        where_clause += ' AND zero >= ? AND zero <= ?'
        values.extend([start, end])

    if degree is not None and degree != '':
        degree = int(degree)
        where_clause += ' AND degree = ?'
        values.append(degree)

    # the where cause has been fully escaped
    values.append(int(limit))
    if end is None:
        query = ('SELECT * FROM ' +
                 '(SELECT * FROM zeros {} ORDER BY zero ASC LIMIT ?)' +
                 'ORDER BY zero DESC').format(where_clause)
    else:
        query = ('SELECT * FROM zeros {} ' +
                 'ORDER BY zero DESC LIMIT ?').format(where_clause)

    C = sqlite3.connect(data_location + 'first_zeros.db').cursor()
    C.execute(query, values)

    response = Response((" ".join([str(x) for x in row]) + "\n" for row in C))
    response.headers['content-type'] = 'text/plain'
    if download == "yes":
        response.headers['content-disposition'] =\
                'attachment; filename=zetazeros'
    # response = flask.Response( ("1 %s\n" % (str(row[0]),) for row in c) )
    return response
