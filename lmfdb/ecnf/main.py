# -*- coding: utf-8 -*-
# This Blueprint is about Elliptic Curves over Number Fields
# Authors: Harald Schilly and John Cremona

import re
import pymongo
ASC = pymongo.ASCENDING
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect
from lmfdb.utils import image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, make_logger, clean_input
from sage.all import ZZ, var, PolynomialRing, QQ, GCD
from lmfdb.ecnf import ecnf_page, logger
from lmfdb.ecnf.WebEllipticCurve import ECNF, db_ecnf, make_field
from lmfdb.ecnf.isog_class import ECNF_isoclass
from lmfdb.number_fields.number_field import parse_field_string, field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField

def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = re.search("[a-z]+",data[2]).group()
    curve_number = re.search("\d+",data[2]).group() # (a string)
    return (field_label,conductor_label,isoclass_label,curve_number)

def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = re.search("[a-z]+",data[1]).group()
    curve_number = re.search("\d+",data[1]).group() # (a string)
    return (conductor_label,isoclass_label,curve_number)

def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label,conductor_label,isoclass_label)

def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label,isoclass_label)

ecnf_credit = "John Cremona, Alyson Deines, Steve Donelly, Paul Gunnells, Warren Moore, Haluk Sengun, John Voight, Dan Yasaki"

def get_bread(*breads):
    bc = [("Elliptic Curves", url_for(".index"))]
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


@ecnf_page.route("/<nf>/")
def show_ecnf1(nf):
    if nf=="1.1.1.1":
        return redirect(url_for("ec.rational_elliptic_curves", **request.args))
    if request.args:
        return elliptic_curve_search(data=request.args)
    start = 0
    count = 50
    query = {'field_label' : nf}
    cursor = db_ecnf().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('field_label', ASC), ('conductor_norm', ASC), ('conductor_label', ASC), ('iso_label', ASC), ('number', ASC)]).skip(start).limit(count)

    bread = [('Elliptic Curves', url_for(".index")),
             (nf, url_for('.show_ecnf1', nf=nf))]

    res = list(res)
    for e in res:
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), e['field_label'])
    info = {}
    info['field'] = nf
    info['query'] = query
    info['curves'] = res # [ECNF(e) for e in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start+count<nres)
    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    t = 'Elliptic Curves over %s' % field_pretty(nf)
    return render_template("ecnf-search-results.html", info=info, credit=ecnf_credit, bread=bread, title=t)

@ecnf_page.route("/<nf>/<conductor_label>/")
def show_ecnf_conductor(nf, conductor_label):
    return elliptic_curve_search(data={'nf_label':nf, 'conductor_label':conductor_label}, **request.args)

@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/")
def show_ecnf_isoclass(nf, conductor_label, class_label):
    nf_label = parse_field_string(nf)
    label = "-".join([nf_label, conductor_label, class_label])
    full_class_label = "-".join([conductor_label, class_label])
    cl = ECNF_isoclass.by_label(label)
    title = "Elliptic Curve isogeny class %s over Number Field %s" % (full_class_label, cl.ECNF.field.field_pretty())
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((cl.ECNF.field.field_pretty(),url_for(".show_ecnf1", nf=nf_label)))
    bread.append((conductor_label, url_for(".show_ecnf_conductor", nf = nf_label, conductor_label = conductor_label)))
    bread.append((class_label, url_for(".show_ecnf_isoclass", nf = nf_label, conductor_label = conductor_label, class_label = class_label)))
    info = {}
    return render_template("show-ecnf-isoclass.html",
        credit=ecnf_credit,
        title=title,
        bread=bread,
        cl=cl,
        properties2 = cl.properties,
        friends = cl.friends)


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/<number>")
def show_ecnf(nf, class_label, conductor_label, number):
    nf_label = parse_field_string(nf)
    label = "".join(["-".join([nf_label, conductor_label, class_label]),number])
    ec = ECNF.by_label(label)
    title = "Elliptic Curve %s over Number Field %s" % (ec.short_label, ec.field.field_pretty())
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((ec.field.field_pretty(),ec.urls['field']))
    bread.append((ec.conductor_label, ec.urls['conductor']))
    bread.append((ec.iso_label, ec.urls['class']))
    bread.append((ec.number, ec.urls['curve']))
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
    info = to_dict(args['data'])
    if 'jump' in info:
        label = info.get('label', '').replace(" ", "")
        # This label should be a full isogeny class label or a full
        # curve label (including the field_label component)
        label_parts = label.split("-",2)
        nf = label_parts[0]
        cond_label = label_parts[1]
        cur_label = label_parts[2]
        return show_ecnf(nf,cond_label,cur_label) ##!!!

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

    if 'conductor_label' in info:
        query['conductor_label'] = info['conductor_label']

    if 'include_isogenous' in info and info['include_isogenous'] == 'off':
        query['number'] = 1

    if 'field' in info:
        query['field_label'] = info['field']

    info['query'] = query

# process count and start if not default:

    count_default = 50
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

    bread = [('Elliptic Curves', url_for(".index")),
             ('Search Results', '.')]

    res = list(res)
    for e in res:
        e['numb'] = str(e['number'])
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), e['field_label'])

    info['curves'] = res # [ECNF(e) for e in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start+count<nres)
    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    t = 'Elliptic Curve search results'
    return render_template("ecnf-search-results.html", info=info, credit=ecnf_credit, bread=bread, title=t)

# Harald wrote the following and it is not used -- JEC
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

