# -*- coding: utf-8 -*-
# This Blueprint is about Elliptic Curves over Number Fields
# Authors: Harald Schilly and John Cremona

#import re
import pymongo
ASC = pymongo.ASCENDING
#import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect
from lmfdb.utils import image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ, GCD
from lmfdb.ecnf import ecnf_page, logger
from lmfdb.ecnf.WebEllipticCurve import ECNF, db_ecnf, make_field
from lmfdb.number_fields.number_field import parse_field_string, field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField

ecnf_credit = "John Cremona, Alyson Deines, Paul Gunnells, Warren Moore, Haluk Sengun, John Voight, Dan Yasaki"

def get_bread(*breads):
    bc = [("ECNF", url_for(".index"))]
    map(bc.append, breads)
    return bc

def web_ainvs(field_label, ainvs):
    return web_latex([make_field(field_label).parse_NFelt(x) for x in ainvs])

@ecnf_page.route("/")
def index():
#    if 'jump' in request.args:
#        return show_ecnf1(request.args['label'])
    if len(request.args)>0:
        return elliptic_curve_search(data=request.args)
    bread = get_bread()
    data = {}
    nfs = db_ecnf().distinct("field_label")
    nfs = ['2.0.4.1', '2.2.5.1', '3.1.23.1']
    data['fields'] = [(nf,field_pretty(nf)) for nf in nfs if int(nf.split(".")[2])<200]
    return render_template("ecnf-index.html",
        title="Elliptic Curves over Number Fields",
        data=data,
        bread=bread)


@ecnf_page.route("/<nf>")
def show_ecnf1(nf):
    return elliptic_curve_search(data={'field':nf})

@ecnf_page.route("/<nf>/<label>")
def show_ecnf(nf, label):
    nf_label = parse_field_string(nf)
    bread = get_bread((label, url_for(".show_ecnf", label = label, nf = nf_label)))
    label = "-".join([nf_label, label])
    #print "looking up curve with full label=%s" % label
    ec = ECNF.by_label(label)
    title = "Elliptic Curve %s over Number Field %s" % (ec.short_label, ec.field.field_pretty())
    info = {}

    return render_template("show-ecnf.html",
        credit=ecnf_credit,
        title=title,
        bread=bread,
        ec=ec,
#        properties = ec.properties,
        properties2 = ec.properties,
        friends = ec.friends,
        info=info)


def elliptic_curve_search(**args):
    #print "args=%s" % args
    info = to_dict(args['data'])
    #print "info=%s" % info
    if 'jump' in info:
        label = info.get('label', '').replace(" ", "")
        label_parts = label.split("-",1)
        nf = label_parts[0]
        label = label_parts[1]
        return show_ecnf(nf,label)

    query = {}

    if 'conductor_norm' in info:
        Nnorm = clean_input(info['conductor_norm'])
        Nnorm = Nnorm.replace('..', '-').replace(' ', '')
        tmp = parse_range2(Nnorm, 'conductor_norm')
        if tmp[0] == '$or' and '$or' in query:
            newors = []
            for y in tmp[1]:
                oldors = [dict.copy(x) for x in query['$or']]
                for x in oldors:
                    x.update(y)
                newors.extend(oldors)
            tmp[1] = newors
        query[tmp[0]] = tmp[1]

    if 'include_isogenous' in info and info['include_isogenous'] == 'off':
        query['number'] = 1

    if 'field' in info:
        query['field_label'] = info['field']

    info['query'] = query

# process count and start if not default:

    count_default = 20
    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = count_default
    else:
        count = count_default

    start_default = 0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default

# make the query and trim results according to start/count:

    cursor = db_ecnf().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('field_label', ASC), ('conductor_norm', ASC), ('conductor_label', ASC), ('iso_label', ASC), ('number', ASC)]).skip(start).limit(count)

    bread = []#[('Elliptic Curves over Number Fields', url_for(".elliptic_curve_search")),             ('Search Results', '.')]

    res = list(res)
    for e in res:
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), e['field_label'])
        print e['field_knowl']
    info['curves'] = res # [ECNF(e) for e in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    t = 'Elliptic Curves'
    #print "report = %s" % info['report']
    return render_template("ecnf-search-results.html", info=info, credit=ecnf_credit, bread=bread, title=t)

@ecnf_page.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "GET":
        val = request.args.get("val", "no value")
        bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
        return render_template("ecnf-index.html", title="Elliptic Curve Search", bread=bread, val=val)
    elif request.method == "POST":
        return "ERROR: we always do http get to explicitly display the search parameters"
    else:
        return redirect(404)

