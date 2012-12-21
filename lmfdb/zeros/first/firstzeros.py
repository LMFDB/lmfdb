import flask
import utils
import os
from flask import render_template, request

FirstZeros = flask.Blueprint('first L-function zeros', __name__, template_folder = "templates")
logger = utils.make_logger(FirstZeros)

import sqlite3
data_location = os.path.expanduser("~/data/zeros/")
print data_location
try:
    db = sqlite3.connect(data_location + 'first_zeros.db')
    c = db.cursor()
except:
    pass

@FirstZeros.route("/")
def firstzeros():
    start = request.args.get('start', None, float)
    end = request.args.get('end', None, float)
    limit = request.args.get('limit', 100, int)
    degree = request.args.get('degree', None, int)
    #signature_r = request.arts.get("signature_r", None, int)
    #signature_c = request.arts.get("signature_c", None, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    #return render_template("first_zeros.html", start=start, end=end, limit=limit, degree=degree, signature_r=signature_r, signature_c=signature_c)
    return render_template("first_zeros.html", start=start, end=end, limit=limit, degree=degree, title="First zero search", bread=[("First zeros search"," "),])

@FirstZeros.route("/list")
def list_zeros(start = None,
               end = None,
               limit = None,
               fmt = None,
               download = None,
               degree = None):
               #signature_r = None,
               #signature_c = None):
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
    #if signature_r is None:
    #    signature_r = request.arts.get("signature_r", None, int)
    #if signature_c is None:
    #    signature_c = request.arts.get("signature_c", None, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    if start is None and end is None:
        start = 0

    limit = int(limit)

    where_clause = 'WHERE 1=1 '

    if start is None:
        end = float(end)
        where_clause += ' AND zero < ' + str(end)
    elif end is None:
        start = float(start)
        where_clause += ' AND zero > ' + str(start)
    else:
        start = float(start)
        end = float(end)
        where_clause += ' AND zero > {} AND zero < {}'.format(start, end)

    if degree is not None and degree != '':
        where_clause += ' AND degree = ' + str(degree)

    #if signature_r is not None:
    #    where_clause += ' AND signature_r = ' + str(signature_r)

    if start is None:
        end = float(end)
        query = 'SELECT * FROM (SELECT * FROM zeros {} ORDER BY zero DESC LIMIT {}) ORDER BY zero ASC'.format(where_clause, limit)
        #query = 'SELECT * FROM zeros WHERE zero < {} ORDER BY zero DESC LIMIT {}'.format(end, limit)
    else:
        query = 'SELECT * FROM zeros {} ORDER BY zero LIMIT {}'.format(where_clause, limit)

    print query
    c.execute(query)

    response = flask.Response( (" ".join([str(x) for x in row]) + "\n" for row in c) )
    response.headers['content-type'] = 'text/plain'
    if download == "yes":
        response.headers['content-disposition'] = 'attachment; filename=zetazeros'
    #response = flask.Response( ("1 %s\n" % (str(row[0]),) for row in c) )
    return response
