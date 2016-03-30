# -*- coding: utf-8 -*-
# This Blueprint is about Elliptic Curves over Number Fields
# Authors: Harald Schilly and John Cremona

import re
import pymongo
ASC = pymongo.ASCENDING
from urllib import quote, unquote
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect, flash
from lmfdb.utils import image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, make_logger
from lmfdb.search_parsing import parse_ints, parse_noop, nf_string_to_label, parse_nf_string, parse_nf_elt, parse_bracketed_posints, parse_count, parse_start
from sage.all import ZZ, var, PolynomialRing, QQ, GCD
from lmfdb.ecnf import ecnf_page, logger
from lmfdb.ecnf.ecnf_stats import get_stats
from lmfdb.ecnf.WebEllipticCurve import ECNF, db_ecnf, web_ainvs
from lmfdb.ecnf.isog_class import ECNF_isoclass
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import nf_display_knowl, WebNumberField

from markupsafe import Markup

LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
TORS_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
from lmfdb.number_fields.number_field import FIELD_LABEL_RE

def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. It must be of the form (number field label) - (conductor label) - (isogeny class label) - (curve identifier) separated by dashes, such as 2.2.5.1-31.1-a1" % lab), "error")
        raise ValueError
    field_label = data[0]
    conductor_label = data[1]
    try:
        isoclass_label = re.search("(CM)?[a-z]+", data[2]).group()
        curve_number = re.search("\d+", data[2]).group()  # (a string)
    except AttributeError:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. The last part must contain both an isogeny class label (a sequence of lower case letters), followed by a curve id (an integer), such as a1" % lab), "error")
        raise ValueError
    return (field_label, conductor_label, isoclass_label, curve_number)


def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    data = lab.split("-")
    if len(data) != 2:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. It must be of the form (conductor label) - (isogeny class label) - (curve identifier) separated by dashes, such as 31.1-a1" % lab), "error")
        raise ValueError
    conductor_label = data[0]
    try:
        isoclass_label = re.search("[a-z]+", data[1]).group()
        curve_number = re.search("\d+", data[1]).group()  # (a string)
    except AttributeError:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid elliptic curve label. The last part must contain both an isogeny class label (a sequence of lower case letters), followed by a curve id (an integer), such as a1" % lab), "error")
        raise ValueError
    return (conductor_label, isoclass_label, curve_number)


def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid isogeny class label. It must be of the form (number field label) - (conductor label) - (isogeny class label) (separated by dashes), such as 2.2.5.1-31.1-a" % lab), "error")
        raise ValueError
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label, conductor_label, isoclass_label)


def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    data = lab.split("-")
    if len(data) != 2:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid isogeny class label. It must be of the form (conductor label) - (isogeny class label) (separated by dashes), such as 31.1-a" % lab), "error")
        raise ValueError
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label, isoclass_label)


ecnf_credit = "John Cremona, Alyson Deines, Steve Donelly, Paul Gunnells, Warren Moore, Haluk Sengun, John Voight, Dan Yasaki"


def get_bread(*breads):
    bc = [("Elliptic Curves", url_for(".index"))]
    map(bc.append, breads)
    return bc

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Elliptic Curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

@ecnf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the elliptic curve data over number fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Completeness', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ecnf.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@ecnf_page.route("/Source")
def how_computed_page():
    t = 'Source of the elliptic curve data over number fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Source', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='dq.ecnf.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ecnf_page.route("/Labels")
def labels_page():
    t = 'Labels for elliptic curves over number fields'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('Labels', '')]
    credit = 'John Cremona'
    return render_template("single.html", kid='ec.curve_label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('labels'))


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

    counts = get_stats().counts()
    data['fields'] = []
    # Rationals
    data['fields'].append(['the rational field', (('1.1.1.1', [url_for('ec.rational_elliptic_curves'), '$\Q$']),)])
    # Real quadratics (only a sample)
    rqfs = ['2.2.%s.1' % str(d) for d in [5, 89, 229, 497]]
    nquadratics = counts['nfields_by_degree'][2]
    niqfs = 5
    nrqfs = nquadratics - niqfs
    data['fields'].append(['%s real quadratic fields, including' % nrqfs, ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in rqfs)])
    # Imaginary quadratics
    iqfs = ['2.0.%s.1' % str(d) for d in [4, 8, 3, 7, 11]]
    data['fields'].append(['%s imaginary quadratic fields' % niqfs, ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in iqfs)])
    # Cubics
    cubics = ['3.1.23.1'] + ['3.3.%s.1' % str(d) for d in [49,148,1957]]
    ncubics = counts['nfields_by_degree'][3]
    data['fields'].append(['%s cubic fields, including' % ncubics, ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in cubics)])
    # Quartics
    quartics = ['4.4.%s.1' % str(d) for d in [725,2777,9909,19821]]
    nquartics = counts['nfields_by_degree'][4]
    data['fields'].append(['%s totally real quartic fields, including' % nquartics,
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in quartics)])
    # Quintics
    quintics = ['5.5.%s.1' % str(d) for d in [14641]]
    nquintics = counts['nfields_by_degree'][5]
    data['fields'].append(['%s totally real quintic field' % nquintics, ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)]) for nf in quintics)])

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
                           bread=bread, learnmore=learnmore_list_remove('Completeness'))


@ecnf_page.route("/<nf>/")
def show_ecnf1(nf):
    if nf == "1.1.1.1":
        return redirect(url_for("ec.rational_elliptic_curves", **request.args))
    if request.args:
        return elliptic_curve_search(data=request.args)
    start = 0
    count = 50
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    query = {'field_label': nf_label}
    cursor = db_ecnf().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('field_label', ASC), ('conductor_norm', ASC), ('conductor_label', ASC), ('iso_nlabel', ASC), ('number', ASC)]).skip(start).limit(count)

    bread = [('Elliptic Curves', url_for(".index")),
             (nf_label, url_for('.show_ecnf1', nf=nf_label))]

    res = list(res)
    for e in res:
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), field_pretty(e['field_label']))
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
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    return elliptic_curve_search(data={'nf_label': nf_label, 'conductor_label': quote(conductor_label)}, **request.args)

@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/")
def show_ecnf_isoclass(nf, conductor_label, class_label):
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    conductor_label = unquote(conductor_label)
    label = "-".join([nf_label, conductor_label, class_label])
    full_class_label = "-".join([conductor_label, class_label])
    cl = ECNF_isoclass.by_label(label)
    title = "Elliptic Curve isogeny class %s over Number Field %s" % (full_class_label, cl.field)
    bread = [("Elliptic Curves", url_for(".index"))]
    bread.append((cl.field, url_for(".show_ecnf1", nf=nf_label)))
    bread.append((conductor_label, url_for(".show_ecnf_conductor", nf=nf_label, conductor_label=conductor_label)))
    bread.append((class_label, url_for(".show_ecnf_isoclass", nf=nf_label, conductor_label=quote(conductor_label), class_label=class_label)))
    info = {}
    return render_template("show-ecnf-isoclass.html",
                           credit=ecnf_credit,
                           title=title,
                           bread=bread,
                           cl=cl,
                           properties2=cl.properties,
                           friends=cl.friends,
                           learnmore=learnmore_list())


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/<number>")
def show_ecnf(nf, conductor_label, class_label, number):
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        return search_input_error()
    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])
    ec = ECNF.by_label(label)
    bread = [("Elliptic Curves", url_for(".index"))]
    if not ec:
        info = {'query':{}}
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
                           info=info,
                           learnmore=learnmore_list())


def elliptic_curve_search(**args):
    info = to_dict(args['data'])
    bread = [('Elliptic Curves', url_for(".index")),
             ('Search Results', '.')]
    if 'jump' in info:
        label = info.get('label', '').replace(" ", "")
        # This label should be a full isogeny class label or a full
        # curve label (including the field_label component)
        try:
            nf, cond_label, iso_label, number = split_full_label(label.strip())
        except ValueError:
            if not 'query' in info:
                info['query'] = {}
            info['err'] = ''
            return search_input_error(info, bread)

        return show_ecnf(nf, cond_label, iso_label, number)

    query = {}

    try:
        parse_ints(info,query,'conductor_norm')
        parse_noop(info,query,'conductor_label')
        parse_nf_string(info,query,'field',name="base number field",qfield='field_label')
        parse_nf_elt(info,query,'jinv',name='j-invariant')
        parse_ints(info,query,'torsion',name='Torsion order',qfield='torsion_order')
        parse_bracketed_posints(info,query,'torsion_structure',maxlength=2)
    except ValueError:
        return search_input_error(info, bread)

    if 'include_isogenous' in info and info['include_isogenous'] == 'off':
        info['number'] = 1
        query['number'] = 1

    if 'include_base_change' in info and info['include_base_change'] == 'off':
        query['base_change'] = []
    else:
        info['include_base_change'] = "on"

    info['query'] = query
    count = parse_count(info, 50)
    start = parse_start(info)

# make the query and trim results according to start/count:

    cursor = db_ecnf().find(query)
    nres = cursor.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    res = cursor.sort([('field_label', ASC), ('conductor_norm', ASC), ('conductor_label', ASC), ('iso_nlabel', ASC), ('number', ASC)]).skip(start).limit(count)

    res = list(res)
    for e in res:
        e['numb'] = str(e['number'])
        e['field_knowl'] = nf_display_knowl(e['field_label'], getDBConnection(), field_pretty(e['field_label']))

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


def search_input_error(info=None, bread=None):
    if info is None: info = {'err':'','query':{}}
    if bread is None: bread = [('Elliptic Curves', url_for(".index")), ('Search Results', '.')]
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

@ecnf_page.route("/stats")
def statistics():
    info = {
        'counts': get_stats().counts(),
        'stats': get_stats().stats(),
    }
    credit = 'John Cremona'
    t = 'Elliptic curves over number fields: statistics'
    bread = [('Elliptic Curves', url_for("ecnf.index")),
             ('statistics', ' ')]
    return render_template("stats.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list())
