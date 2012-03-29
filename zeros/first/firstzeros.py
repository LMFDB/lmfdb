import flask
import utils
import os
from flask import render_template, request

FirstZeros = flask.Blueprint('first L-function zeros', __name__, template_folder = "templates")
logger = utils.make_logger(FirstZeros)

import sqlite3
data_location = os.path.expanduser("~/data/zeros/")
print data_location
#try:
db = sqlite3.connect(data_location + 'first_zeros.db')
c = db.cursor()
#except:
#    pass

@FirstZeros.route("/")
def firstzeros():
    start = request.args.get('start', None, float)
    end = request.args.get('end', None, float)
    limit = request.args.get('limit', 100, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    return render_template("first_zeros.html", start=start, end=end, limit=limit)

@FirstZeros.route("/list")
def list_zeros(start = None, end = None, limit = None):
    if start is None:
        start = request.args.get('start', None, float)
    if end is None:
        end = request.args.get('end', None, float)
    if limit is None:
        limit = request.args.get('limit', 100, int)
    if limit > 1000:
        limit = 1000
    if limit < 0:
        limit = 100

    if start is None and end is None:
        start = 0

    limit = int(limit)

    if start is None:
        end = float(end)
        query = 'SELECT zero FROM (SELECT * FROM zeros WHERE zero < {} ORDER BY zero DESC LIMIT {}) ORDER BY zero ASC'.format(end, limit)
        #query = 'SELECT * FROM zeros WHERE zero < {} ORDER BY zero DESC LIMIT {}'.format(end, limit)
    elif end is None:
        start = float(start)
        query = 'SELECT zero FROM zeros WHERE zero > {} ORDER BY zero LIMIT {}'.format(start, limit)
    else:
        start = float(start)
        end = float(end)
        query = 'SELECT zero from zeros WHERE zero > {} AND zero < {} ORDER BY zero LIMIT {}'.format(start, end, limit)

    print query
    c.execute(query)
    response = flask.Response( ("1 %s\n" % (str(row[0]),) for row in c) )
    return response
