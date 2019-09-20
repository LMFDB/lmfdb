# -*- coding: utf-8 -*-
import os
import sqlite3
from sage.all import RealField, RealIntervalField, ZZ
from flask import Blueprint, Response, render_template, request, url_for

RR = RealField(63)

dbpath = os.path.expanduser('~/data/riemann/stieltjes.db')

StieltjesConstants = Blueprint("stieltjes", __name__, template_folder="templates")


@StieltjesConstants.route("/")
def stieltjes_constants():
    start = request.args.get("start", 0, int)
    limit = request.args.get("limit", 100, int)
    return render_template('stieltjes.html',
                           start=start,
                           limit=limit,
                           title="Stieltjes Constants",
                           bread=[('Stieltjes Constants', ' '), ])


@StieltjesConstants.route("/list")
def list_constants(start=None,
                   limit=None,
                   fmt=None):
    if start is None:
        start = request.args.get("start", 0, int)
    if limit is None:
        limit = request.args.get("limit", 100, int)
    if fmt is None:
        fmt = request.args.get("format", "plain")

    if limit < 0:
        limit = 100
    if limit > 1000:
        limit = 1000
    if start < 0:
        start = 0
    s_constants = stieltjes_list(start, limit)

    if fmt == 'plain':
        response = Response(
                "%d %s %s\n" % (n, str(g), str(c))
                for (n, g, c) in s_constants)
        response.headers['content-type'] = 'text/plain'
    else:
        response = str(list(s_constants))

    return response


def stieltjes_list(start, limit):
    db = sqlite3.connect(dbpath)
    c = db.cursor()
    query = 'SELECT n, smallmantissa, smallexponent ' +\
            'FROM stieltjes WHERE n >= ? LIMIT ?'
    c.execute(query, (start, limit))
    L = []
    for (n, m, e) in c:
        g = RR(m)*RR(2)**e
        c = (-1)**n * g/RR(n+1).gamma()
        L.append((n, RR(m)*RR(2)**e, c))

    return L


@StieltjesConstants.route("/getone")
def getone(n=None, digits=None, plain=False):
    if n is None:
        n = request.args.get('n', 0, int)
    if digits is None:
        digits = request.args.get('digits', 50, int)
    db = sqlite3.connect(dbpath)
    c = db.cursor()
    query = 'SELECT error_mantissa, error_exponent, mantissa, exponent ' +\
            'FROM stieltjes WHERE n = ? LIMIT 1'
    c.execute(query, (n,))
    em, ee, mantissa, exponent = c.fetchone()

    mantissa = ZZ(mantissa)

    e = min(ee, exponent)
    em = em << (ee - e)
    mantissa = mantissa << (exponent - e)

    if digits is None:
        prec = RR(mantissa).log2() + 3
    else:
        prec = digits * 3.3219280948873626 + 3
    prec = max(2, prec)
    prec = min(prec, 200000)
    RIF = RealIntervalField(prec)
    x = RIF(mantissa - em, mantissa + em)
    if e < 0:
        x = x >> (-e)
    else:
        x = x << e
    if plain:
        return str(x)
    else:
        g, e = str(x).split('?')
        if e == '':
            g += '?'
        else:
            g += '? &times; 10<sup style="font-size:60%;">' + e[1:] + '</sup>'

        return render_template('getone.html',
                               n=n,
                               digits=digits,
                               gamma=g,
                               title="Stieltjes Constant $\gamma_{{{}}}$".format(n),
                               bread=[
                                    ('Stieltjes Constants',
                                     url_for('.stieltjes_constants')),
                                    ('$\gamma_{{{}}}$'.format(n), ' '), ])
