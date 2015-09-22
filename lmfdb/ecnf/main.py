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
from lmfdb.number_fields.number_field import parse_list, parse_field_string, field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField

LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
TORS_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')


def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = re.search("[a-z]+", data[2]).group()
    curve_number = re.search("\d+", data[2]).group()  # (a string)
    return (field_label, conductor_label, isoclass_label, curve_number)


def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = re.search("[a-z]+", data[1]).group()
    curve_number = re.search("\d+", data[1]).group()  # (a string)
    return (conductor_label, isoclass_label, curve_number)


def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label, conductor_label, isoclass_label)


def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label, isoclass_label)

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
    if len(request.args) > 0:
        return elliptic_curve_search(data=request.args)
    bread = get_bread()

# the dict data will hold additional information to be displayed on
# the main browse and search page

    data = {}

# data['fields'] holds data for a sample of number fields of different
# signatures for a general browse:

    data['fields'] = []
    # Rationals
    data['fields'].append(['the rational field', (('1.1.1.1', [url_for('ec.rational_elliptic_curves'), '$\Q$']),)])
    # Real quadratics (only a sample)
    rqfs = ['2.2.%s.1' % str(d) for d in [5, 89, 229, 497]]
    data['fields'].append(['real quadratic fields', ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in rqfs)])
    # Imaginary quadratics
    iqfs = ['2.0.%s.1' % str(d) for d in [4, 8, 3, 7, 11]]
    data['fields'].append(['imaginary quadratic fields', ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in iqfs)])
    # Cubics
    cubics = ['3.1.23.1']
    data['fields'].append(['cubic fields', ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in cubics)])

# data['highlights'] holds data (URL and descriptive text) for a
# sample of elliptic curves with interesting features:

    data['highlights'] = []
    data['highlights'].append(
        ['A curve with $C_3\\times C_3$ torsion',
         url_for('.show_ecnf', nf='2.0.3.1', class_label='a', conductor_label='[2268,36,18]', number=int(1))]
    )
    data['highlights'].append(
        ['A curve with $C_4\\times C_4$ torsion',
         url_for('.show_ecnf', nf='2.0.4.1', class_label='b', conductor_label='[5525,870,5]', number=int(9))]
    )
    data['highlights'].append(
        ['A curve with CM by $\\sqrt{-267}$',
         url_for('.show_ecnf', nf='2.2.89.1', class_label='a', conductor_label='81.1', number=int(1))]
    )
    data['highlights'].append(
        ['An isogeny class with isogenies of degree $3$ and $89$ (and $267$)',
         url_for('.show_ecnf_isoclass', nf='2.2.89.1', class_label='a', conductor_label='81.1')]
    )
    data['highlights'].append(
        ['A curve with everywhere good reduction, but no global minimal model',
         url_for('.show_ecnf', nf='2.2.229.1', class_label='a', conductor_label='1.1', number=int(1))]
    )

    return render_template("ecnf-index.html",
                           title="Elliptic Curves over Number Fields",
                           data=data,
                           bread=bread)


@ecnf_page.route("/<nf>/")
def show_ecnf1(nf):
    if nf == "1.1.1.1":
        return redirect(url_for("ec.rational_elliptic_curves", **request.args))
    if request.args:
        return elliptic_curve_search(data=request.args)
    start = 0
    count = 50
    nf_label = parse_field_string(nf)
    query = {'field_label': nf_label}
    cursor = db_ecnf().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('field_label', ASC), ('conductor_norm', ASC), ('conductor_label', ASC), ('iso_label', ASC), ('number', ASC)]).skip(start).limit(count)

    bread = [('Elliptic Curves', url_for(".index")),
             (nf_label, url_for('.show_ecnf1', nf=nf_label))]

    res = list(res)
    for e in res:
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), e['field_label'])
    info = {}
    info['field'] = nf_label
    info['query'] = query
    info['curves'] = res  # [ECNF(e) for e in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start + count < nres)
    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres
    t = 'Elliptic Curves over %s' % field_pretty(nf_label)
    return render_template("ecnf-search-results.html", info=info, credit=ecnf_credit, bread=bread, title=t)


@ecnf_page.route("/<nf>/<conductor_label>/")
def show_ecnf_conductor(nf, conductor_label):
    nf_label = parse_field_string(nf)
    return elliptic_curve_search(data={'nf_label': nf_label, 'conductor_label': conductor_label}, **request.args)


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/")
def show_ecnf_isoclass(nf, conductor_label, class_label):
    nf_label = parse_field_string(nf)
    label = "-".join([nf_label, conductor_label, class_label])
    full_class_label = "-".join([conductor_label, class_label])
    cl = ECNF_isoclass.by_label(label)
    title = "Elliptic Curve isogeny class %s over Number Field %s" % (full_class_label, cl.ECNF.field.field_pretty())
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((cl.ECNF.field.field_pretty(), url_for(".show_ecnf1", nf=nf_label)))
    bread.append((conductor_label, url_for(".show_ecnf_conductor", nf=nf_label, conductor_label=conductor_label)))
    bread.append((class_label, url_for(".show_ecnf_isoclass", nf=nf_label, conductor_label=conductor_label, class_label=class_label)))
    info = {}
    return render_template("show-ecnf-isoclass.html",
                           credit=ecnf_credit,
                           title=title,
                           bread=bread,
                           cl=cl,
                           properties2=cl.properties,
                           friends=cl.friends)


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/<number>")
def show_ecnf(nf, conductor_label, class_label, number):
    nf_label = parse_field_string(nf)
    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])
    ec = ECNF.by_label(label)
    bread = [("Elliptic Curves", url_for(".index"))]
    if not ec:
        info = {}
        info['query'] = {}
        info['err'] = 'No elliptic curve in the database has label %s.' % label
        return search_input_error(info, bread)

    title = "Elliptic Curve %s over Number Field %s" % (ec.short_label, ec.field.field_pretty())
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((ec.field.field_pretty(), ec.urls['field']))
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
                           properties2=ec.properties,
                           friends=ec.friends,
                           info=info)


def elliptic_curve_search(**args):
    info = to_dict(args['data'])
    if 'jump' in info:
        label = info.get('label', '').replace(" ", "")
        # This label should be a full isogeny class label or a full
        # curve label (including the field_label component)
        try:
            nf, cond_label, iso_label, number = split_full_label(label)
        except IndexError:
            if not 'query' in info:
                info['query'] = {}
            bread = [("Elliptic Curves", url_for(".index"))]
            info['err'] = 'No elliptic curve in the database has label %s.' % label
            return search_input_error(info, bread)

        return show_ecnf(nf, cond_label, iso_label, number)

    query = {}
    bread = [('Elliptic Curves', url_for(".index")),
             ('Search Results', '.')]

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

    if 'jinv' in info:
        query['jinv'] = info['jinv']

    if info.get('torsion'):
        ran = info['torsion'] = clean_input(info['torsion'])
        ran = ran.replace('..', '-').replace(' ', '')
        if not LIST_RE.match(ran):
            info['err'] = 'Error parsing input for the torsion order.  It needs to be an integer (such as 5), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).'
            return search_input_error(info, bread)
        # Past input check
        tmp = parse_range2(ran, 'torsion_order')
        # work around syntax for $or
        # we have to foil out multiple or conditions
        if tmp[0] == '$or' and '$or' in query:
            newors = []
            for y in tmp[1]:
                oldors = [dict.copy(x) for x in query['$or']]
                for x in oldors:
                    x.update(y)
                newors.extend(oldors)
            tmp[1] = newors
        query[tmp[0]] = tmp[1]

    if 'torsion_structure' in info and info['torsion_structure']:
        info['torsion_structure'] = clean_input(info['torsion_structure'])
        if not TORS_RE.match(info['torsion_structure']):
            info['err'] = 'Error parsing input for the torsion structure.  It needs to be one or more integers in square brackets, such as [6], [2,2], or [2,4].  Moreover, each integer should be bigger than 1, and each divides the next.'
            return search_input_error(info, bread)
        query['torsion_structure'] = parse_list(info['torsion_structure'])

    if 'include_isogenous' in info and info['include_isogenous'] == 'off':
        query['number'] = 1

    if 'include_base_change' in info and info['include_base_change'] == 'off':
        query['base_change'] = []
    else:
        info['include_base_change'] = "on"

    if 'field' in info:
        query['field_label'] = parse_field_string(info['field'])

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

    res = list(res)
    for e in res:
        e['numb'] = str(e['number'])
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), e['field_label'])

    info['curves'] = res  # [ECNF(e) for e in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start + count < nres)
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


def search_input_error(info, bread):
    return render_template("ecnf-search-results.html", info=info, title='Elliptic Curve Search Input Error', bread=bread)


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
