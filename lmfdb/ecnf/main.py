# -*- coding: utf-8 -*-
# This Blueprint is about elliptic curves over number Fields
# Authors: Harald Schilly and John Cremona

import ast
import re
from io import BytesIO
import time
from urllib.parse import quote, unquote

from flask import render_template, request, url_for, redirect, send_file, make_response, abort
from markupsafe import Markup, escape

from lmfdb import db
from lmfdb.backend.encoding import Json
from lmfdb.utils import (
    to_dict, flash_error,
    parse_ints, parse_ints_to_list_flash, parse_noop, nf_string_to_label, parse_element_of,
    parse_nf_string, parse_nf_jinv, parse_bracketed_posints, parse_bool, parse_floats, parse_primes,
    SearchArray, TextBox, ExcludeOnlyBox, SelectBox, CountBox, YesNoBox, SubsetBox, TextBoxWithSelect,
    search_wrap, redirect_no_cache
    )
from lmfdb.utils.search_parsing import search_parser

from lmfdb.utils.interesting import interesting_knowls
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.number_fields.web_number_field import nf_display_knowl, WebNumberField
from lmfdb.ecnf import ecnf_page
from lmfdb.ecnf.ecnf_stats import ECNF_stats
from lmfdb.ecnf.WebEllipticCurve import ECNF, web_ainvs
from lmfdb.ecnf.isog_class import ECNF_isoclass

# The conductor label seems to only have three parts for the trivial ideal (1.0.1)
# field 3.1.23.1 uses upper case letters for isogeny class
LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+-\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+\d+")
SHORT_LABEL_RE = re.compile(r"\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+\d+")
CLASS_LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+-\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+")
SHORT_CLASS_LABEL_RE = re.compile(r"\d+\.\d+(\.\d+)?-(CM)?[a-zA-Z]+")
FIELD_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")

def split_full_label(lab):
    r""" Split a full curve label into 4 components
    (field_label,conductor_label,isoclass_label,curve_number)
    """
    if not LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid elliptic curve label." % escape(lab)))
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = re.search("(CM)?[a-zA-Z]+", data[2]).group()
    curve_number = re.search(r"\d+", data[2]).group()  # (a string)
    return (field_label, conductor_label, isoclass_label, curve_number)


def split_short_label(lab):
    r""" Split a short curve label into 3 components
    (conductor_label,isoclass_label,curve_number)
    """
    if not SHORT_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid short elliptic curve label." % escape(lab)))
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = re.search("[a-zA-Z]+", data[1]).group()
    curve_number = re.search(r"\d+", data[1]).group()  # (a string)
    return (conductor_label, isoclass_label, curve_number)


def split_class_label(lab):
    r""" Split a class label into 3 components
    (field_label, conductor_label,isoclass_label)
    """
    if not CLASS_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid elliptic curve isogeny class label." % escape(lab)))
    data = lab.split("-")
    field_label = data[0]
    conductor_label = data[1]
    isoclass_label = data[2]
    return (field_label, conductor_label, isoclass_label)


def split_short_class_label(lab):
    r""" Split a short class label into 2 components
    (conductor_label,isoclass_label)
    """
    if not SHORT_CLASS_LABEL_RE.fullmatch(lab):
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid short elliptic curve isogeny class label." % escape(lab)))
    data = lab.split("-")
    conductor_label = data[0]
    isoclass_label = data[1]
    return (conductor_label, isoclass_label)

def conductor_label_norm(lab):
    r""" extract norm from conductor label (as a string)"""
    s = lab.replace(' ','')
    if re.match(r'\d+.\d+',s):
        return s.split('.')[0]
    else:
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid conductor label. It must be of the form N.m or [N,c,d]" % escape(lab)))

def get_nf_info(lab):
    r""" extract number field label from string and pretty"""
    try:
        label = nf_string_to_label(lab)
        pretty = field_pretty (label)
    except ValueError as err:
        raise ValueError(Markup("<span style='color:black'>%s</span> is not a valid number field label. %s" % (escape(lab),err)))
    return label, pretty


def get_bread(*breads):
    bc = [("Elliptic curves", url_for(".index"))]
    for x in breads:
        bc.append(x)
    return bc


def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Elliptic curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


@ecnf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of elliptic curve data over number fields'
    bread = [('Elliptic curves', url_for("ecnf.index")),
             ('Completeness', '')]
    return render_template("single.html", kid='rcs.cande.ec',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@ecnf_page.route("/Source")
def how_computed_page():
    t = 'Source of elliptic curve data over number fields'
    bread = [('Elliptic curves', url_for("ecnf.index")),
             ('Source', '')]
    return render_template("double.html", kid='rcs.source.ec', kid2='rcs.ack.ec',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ecnf_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of elliptic curve data over number fields'
    bread = [('Elliptic curves', url_for("ecnf.index")),
             ('Source', '')]
    return render_template("single.html", kid='rcs.rigor.ec',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@ecnf_page.route("/Labels")
def labels_page():
    t = 'Labels for elliptic curves over number fields'
    bread = [('Elliptic curves', url_for("ecnf.index")),
             ('Labels', '')]
    return render_template("single.html", kid='ec.curve_label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))


@ecnf_page.route("/")
def index():
    #    if 'jump' in request.args:
    #        return show_ecnf1(request.args['label'])
    info = to_dict(request.args, search_array=ECNFSearchArray(), stats=ECNF_stats())
    if request.args:
        return elliptic_curve_search(info)
    bread = get_bread()

    # the dict data will hold additional information to be displayed on
    # the main browse and search page


    # info['fields'] holds data for a sample of number fields of different
    # signatures for a general browse:

    info['fields'] = []
    # Rationals
    # info['fields'].append(['the rational field', (('1.1.1.1', [url_for('ec.rational_elliptic_curves'), '$\Q$']),)]) # Removed due to ambiguity

    # Real quadratics (sample)
    rqfs = ['2.2.{}.1'.format(d) for d in [8, 12, 5, 24, 28, 40, 44, 13, 56, 60]]
    info['fields'].append(['By <a href="{}">real quadratic field</a>'.format(url_for('.statistics_by_signature', d=2, r=2)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in rqfs)])

    # Imaginary quadratics (sample)
    iqfs = ['2.0.{}.1'.format(d) for d in [4, 8, 3, 7, 11, 19, 43, 67, 163]]
    info['fields'].append(['By <a href="{}">imaginary quadratic field</a>'.format(url_for('.statistics_by_signature', d=2, r=0)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in iqfs)])

    # Cubics (sample)
    cubics = ['3.1.23.1'] + ['3.3.{}.1'.format(d) for d in [49,81,148,169,229,257,316]]
    info['fields'].append(['By <a href="{}">cubic field</a>'.format(url_for('.statistics_by_degree', d=3)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in cubics)])

    # Quartics (sample)
    quartics = ['4.4.{}.1'.format(d) for d in [725,1125,1600,1957,2000,2048,2225,2304]]
    info['fields'].append(['By <a href="{}">totally real quartic field</a>'.format(url_for('.statistics_by_degree', d=4)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in quartics)])

    # Quintics (sample)
    quintics = ['5.5.{}.1'.format(d) for d in [14641, 24217, 36497, 38569, 65657, 70601, 81509]]
    info['fields'].append(['By <a href="{}">totally real quintic field</a>'.format(url_for('.statistics_by_degree', d=5)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in quintics)])

    # Sextics (sample)
    sextics = ['6.6.{}.1'.format(d) for d in [300125, 371293, 434581, 453789, 485125, 592661, 703493]]
    info['fields'].append(['By <a href="{}">totally real sextic field</a>'.format(url_for('.statistics_by_degree', d=6)),
                           ((nf, [url_for('.show_ecnf1', nf=nf), field_pretty(nf)])
                            for nf in sextics)])

    return render_template("ecnf-index.html",
                           title="Elliptic curves over number fields",
                           info=info,
                           bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/random/")
@redirect_no_cache
def random_curve():
    E = db.ec_nfcurves.random(projection=['field_label', 'conductor_label', 'iso_label', 'number'])
    return url_for(".show_ecnf", nf=E['field_label'], conductor_label=E['conductor_label'], class_label=E['iso_label'], number=E['number'])


@ecnf_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "ec",
        db.ec_nfcurves,
        url_for_label=url_for_label,
        regex=LABEL_RE, # include so that we don't catch elliptic curves over Q also
        title="Some interesting elliptic curves over number fields",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@ecnf_page.route("/stats")
def statistics():
    title = "Elliptic curves: statistics"
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=ECNF_stats(), title=title, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/<nf>/")
def show_ecnf1(nf):
    if LABEL_RE.fullmatch(nf):
        nf, cond_label, iso_label, number = split_full_label(nf)
        return redirect(url_for(".show_ecnf", nf=nf, conductor_label=cond_label, class_label=iso_label, number=number), 301)
    if CLASS_LABEL_RE.fullmatch(nf):
        nf, cond_label, iso_label = split_class_label(nf)
        return redirect(url_for(".show_ecnf_isoclass", nf=nf, conductor_label=cond_label, class_label=iso_label), 301)
    if not FIELD_RE.fullmatch(nf):
        return abort(404)
    try:
        nf_label, nf_pretty = get_nf_info(nf)
    except ValueError:
        return abort(404)
    if nf_label == '1.1.1.1':
        return redirect(url_for("ec.rational_elliptic_curves", **request.args), 301)
    info = to_dict(request.args, search_array=ECNFSearchArray())
    info['title'] = 'Elliptic curves over %s' % nf_pretty
    info['bread'] = [('Elliptic curves', url_for(".index")), (nf_pretty, url_for(".show_ecnf1", nf=nf))]
    if len(request.args) > 0:
        # if requested field differs from nf, redirect to general search
        if 'field' in request.args and request.args['field'] != nf_label:
            return redirect (url_for(".index", **request.args), 307)
        info['title'] += ' Search results'
        info['bread'].append(('Search results',''))
    info['field'] = nf_label
    return elliptic_curve_search(info)

@ecnf_page.route("/<nf>/<conductor_label>/")
def show_ecnf_conductor(nf, conductor_label):
    if not FIELD_RE.fullmatch(nf):
        return abort(404)
    conductor_label = unquote(conductor_label)
    try:
        nf_label, nf_pretty = get_nf_info(nf)
        conductor_norm = conductor_label_norm(conductor_label)
    except ValueError:
        return abort(404)
    info = to_dict(request.args, search_array=ECNFSearchArray())
    info['title'] = 'Elliptic curves over %s of conductor %s' % (nf_pretty, conductor_label)
    info['bread'] = [('Elliptic curves', url_for(".index")), (nf_pretty, url_for(".show_ecnf1", nf=nf)), (conductor_label, url_for(".show_ecnf_conductor",nf=nf,conductor_label=conductor_label))]
    if len(request.args) > 0:
        # if requested field or conductor norm differs from nf or conductor_lable, redirect to general search
        if ('field' in request.args and request.args['field'] != nf_label) or \
           ('conductor_norm' in request.args and request.args['conductor_norm'] != conductor_norm):
            return redirect (url_for(".index", **request.args), 307)
        info['title'] += ' Search results'
        info['bread'].append(('Search results',''))
    info['field'] = nf_label
    info['conductor_label'] = conductor_label
    info['conductor_norm'] = conductor_norm
    return elliptic_curve_search(info)

@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/")
def show_ecnf_isoclass(nf, conductor_label, class_label):
    if not FIELD_RE.fullmatch(nf):
        return abort(404)
    conductor_label = unquote(conductor_label)
    try:
        nf_label, nf_pretty = get_nf_info(nf)
    except ValueError:
        flash_error("%s is not a valid number field label", nf_label)
        return redirect(url_for(".index"))
    label = "-".join([nf_label, conductor_label, class_label])
    if not CLASS_LABEL_RE.fullmatch(label):
        flash_error("%s is not a valid elliptic curve isogeny class label", label)
        return redirect(url_for(".index"))
    full_class_label = "-".join([conductor_label, class_label])
    cl = ECNF_isoclass.by_label(label)
    if not isinstance(cl, ECNF_isoclass):
        flash_error("There is no elliptic curve isogeny class with label %s in the database", label)
        return redirect(url_for(".index"))
    bread = [("Elliptic curves", url_for(".index"))]
    title = "Elliptic curve isogeny class %s over number field %s" % (full_class_label, cl.field_name)
    bread.append((nf_pretty, url_for(".show_ecnf1", nf=nf)))
    bread.append((conductor_label, url_for(".show_ecnf_conductor", nf=nf_label, conductor_label=conductor_label)))
    bread.append((class_label, url_for(".show_ecnf_isoclass", nf=nf_label, conductor_label=quote(conductor_label), class_label=class_label)))
    return render_template("ecnf-isoclass.html",
                           title=title,
                           bread=bread,
                           cl=cl,
                           properties=cl.properties,
                           friends=cl.friends,
                           learnmore=learnmore_list())


@ecnf_page.route("/<nf>/<conductor_label>/<class_label>/<int:number>")
def show_ecnf(nf, conductor_label, class_label, number):
    if not FIELD_RE.fullmatch(nf):
        return abort(404)
    conductor_label = unquote(conductor_label)
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        flash_error("%s is not a valid number field label", nf_label)
        return redirect(url_for(".index"))
    label = "".join(["-".join([nf_label, conductor_label, class_label]), str(number)])
    if not LABEL_RE.fullmatch(label):
        flash_error("%s is not a valid elliptic curve label", label)
        return redirect(url_for(".index"))
    ec = ECNF.by_label(label)
    if not isinstance(ec, ECNF):
        flash_error("There is no elliptic curve with label %s in the database", label)
        return redirect(url_for(".index"))
    bread = [("Elliptic curves", url_for(".index"))]
    title = "Elliptic curve %s over number field %s" % (ec.short_label, ec.field.field_pretty())
    bread = [("Elliptic curves", url_for(".index"))]
    bread.append((ec.field.field_pretty(), ec.urls['field']))
    bread.append((ec.conductor_label, ec.urls['conductor']))
    bread.append((ec.iso_label, ec.urls['class']))
    bread.append((ec.number, ec.urls['curve']))
    code = ec.code()
    code['show'] = {'magma':'','pari':'','sage':''} # use default show names
    info = {}
    return render_template("ecnf-curve.html",
                           title=title,
                           bread=bread,
                           ec=ec,
                           code = code,
                           properties=ec.properties,
                           friends=ec.friends,
                           downloads=ec.downloads,
                           info=info,
                           KNOWL_ID="ec.%s"%label,
                           learnmore=learnmore_list())

def download_search(info):
    dltype = info['Submit']
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'elliptic_curves.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'elliptic_curves.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'elliptic_curves.m'
    s = com1 + "\n"
    s += com + ' Elliptic curves downloaded from the LMFDB downloaded on %s.\n'%(mydate)
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [[field_poly],[Weierstrass Coefficients, constant first in increasing degree]]\n'
    s += '\n' + com2
    s += '\n'

    if dltype == 'magma':
        s += 'P<x> := PolynomialRing(Rationals()); \n'
        s += 'data := ['
    elif dltype == 'sage':
        s += 'R.<x> = QQ[]; \n'
        s += 'data = [ '
    else:
        s += 'data = [ '
    s += '\\\n'
    nf_dict = {}
    for f in db.ec_nfcurves.search(ast.literal_eval(info["query"]), ['field_label', 'ainvs']):
        nf = str(f['field_label'])
        # look up number field and see if we already have the min poly
        if nf in nf_dict:
            poly = nf_dict[nf]
        else:
            poly = str(WebNumberField(f['field_label']).poly())
            nf_dict[nf] = poly
        entry = str(f['ainvs'])
        entry = entry.replace('u','')
        entry = entry.replace('\'','')
        entry = entry.replace(';','],[')
        s += '[[' + poly + '], [[' + entry + ']]],\\\n'
    s = s[:-3]
    s += ']\n'

    if delim == 'brace':
        s = s.replace('[', '{')
        s = s.replace(']', '}')
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)

def elliptic_curve_jump(info):
    label = info.get('jump', '').replace(" ", "")
    if info.get('jump','') == "random":
        return random_curve()
    if LABEL_RE.fullmatch(label):
        nf, cond_label, iso_label, number = split_full_label(label.strip())
        return redirect(url_for(".show_ecnf", nf=nf, conductor_label=cond_label, class_label=iso_label, number=number), 301)
    elif CLASS_LABEL_RE.fullmatch(label):
        nf, cond_label, iso_label = split_class_label(label.strip())
        return redirect(url_for(".show_ecnf_isoclass", nf=nf, conductor_label=cond_label, class_label=iso_label), 301)
    else:
        flash_error("%s is not a valid elliptic curve or isogeny class label.", label)
        return redirect(url_for("ecnf.index"))

def url_for_label(label):
    if label == 'random':
        return url_for(".random")
    nf, cond_label, iso_label, number = split_full_label(label.strip())
    return url_for(".show_ecnf", nf=nf, conductor_label=cond_label, class_label=iso_label, number=number)

def make_cm_query(cm_disc_str):
    cm_list = parse_ints_to_list_flash(cm_disc_str, "CM discriminant", max_val=None)
    for d in cm_list:
        if not ((d < 0) and (d % 4 in [0,1])):
            raise ValueError("A CM discriminant must be a fundamental discriminant of an imaginary quadratic field.")
    cm_list += [-el for el in cm_list]
    return cm_list

@search_parser
def parse_cm_list(inp, query, qfield):
    query[qfield] = {'$in': make_cm_query(inp)}

@search_wrap(template="ecnf-search-results.html",
             table=db.ec_nfcurves,
             title='Elliptic curve search results',
             err_title='Elliptic curve search input error',
             shortcuts={'jump':elliptic_curve_jump,
                        'download':download_search},
             cleaners={'numb':lambda e: str(e['number']),
                       'field_knowl':lambda e: nf_display_knowl(e['field_label'], field_pretty(e['field_label']))},
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             bread=lambda:[('Elliptic curves', url_for(".index")), ('Search results', '.')])
def elliptic_curve_search(info, query):
    parse_nf_string(info,query,'field',name="base number field",qfield='field_label')
    if query.get('field_label') == '1.1.1.1':
        return redirect(url_for("ec.rational_elliptic_curves", **request.args), 301)
    parse_ints(info,query,'conductor_norm')
    if info.get('conductor_type'):
        if info['conductor_type'] == 'prime':
            query['num_bad_primes'] = 1
            query['semistable'] = True
        elif info['conductor_type'] == 'prime_power':
            query['num_bad_primes'] = 1
        elif info['conductor_type'] == 'squarefree':
            query['semistable'] = True
        elif info['conductor_type'] == 'divides':
            if not isinstance(query.get('conductor_norm'), int):
                raise ValueError("You must specify a single level")
            else:
                query['conductor_norm'] = {'$in': ZZ(query['conductor_norm']).divisors()}
    parse_noop(info,query,'conductor_label')
    parse_ints(info,query,'rank')
    parse_ints(info,query,'torsion',name='Torsion order',qfield='torsion_order')
    parse_bracketed_posints(info,query,'torsion_structure',maxlength=2)
    if 'torsion_structure' in query and 'torsion_order' not in query:
        t_o = 1
        for n in query['torsion_structure']:
            t_o *= int(n)
        query['torsion_order'] = t_o
    parse_element_of(info,query,'isodeg',split_interval=1000,contained_in=ECNF_stats().isogeny_degrees)
    parse_bool(info,query,'semistable','semistable')
    parse_bool(info,query,'potential_good_reduction','potential_good_reduction')
    parse_ints(info,query,'class_size','class_size')
    parse_ints(info,query,'class_deg','class_deg')
    parse_ints(info,query,'sha','analytic order of &#1064;')
    parse_floats(info,query,'reg','regulator')
    parse_nf_jinv(info,query,'jinv','j-invariant',field_label=query.get('field_label'))

    if info.get('one') == "yes":
        info['number'] = 1
        query['number'] = 1

    if 'include_base_change' in info:
        if info['include_base_change'] in ['exclude', 'off']: # off for backward compat with urls
            query['base_change'] = []
        if info['include_base_change'] == 'only':
            query['base_change'] = {'$ne':[]}
    else:
        info['include_base_change'] = "on"

    if 'include_Q_curves' in info:
        if info['include_Q_curves'] == 'exclude':
            query['q_curve'] = False
        elif info['include_Q_curves'] == 'only':
            query['q_curve'] = True

    parse_cm_list(info,query,field='cm_disc',qfield='cm',name="CM discriminant")

    if 'include_cm' in info:
        if info['include_cm'] == 'PCM':
            tmp = {'$ne' : 0}
            if 'cm' in query:
                query['cm'] = {'$and': [tmp, query['cm']]}
            else:
                query['cm'] = tmp
        elif info['include_cm'] == 'PCMnoCM':
            tmp = {'$lt' : 0}
            if 'cm' in query:
                query['cm'] = {'$and': [tmp, query['cm']]}
            else:
                query['cm'] = tmp
        elif info['include_cm'] == 'CM':
            tmp = {'$gt' : 0}
            if 'cm' in query:
                query['cm'] = {'$and': [tmp, query['cm']]}
            else:
                query['cm'] = tmp
        elif info['include_cm'] == 'noPCM':
            tmp = 0
            if 'cm' in query:
                query['cm'] = {'$and': [tmp, query['cm']]}
            else:
                query['cm'] = tmp

    parse_primes(info, query, 'conductor_norm_factors', name='bad primes',
             qfield='conductor_norm_factors',mode=info.get('bad_quantifier'))
    info['field_pretty'] = field_pretty
    info['web_ainvs'] = web_ainvs
    parse_ints(info,query,'bf_deg',name='Base field degree',qfield='degree')

@ecnf_page.route("/browse/")
def browse():
    data = ECNF_stats().sigs_by_deg
    # We could use the dict directly but then could not control the order
    # of the keys (degrees), so we use a list
    info = [[d,['%s,%s'%sig for sig in data[d]]] for d in sorted(data.keys())]
    t = 'Elliptic curves over number fields'
    bread = [('Elliptic curves', url_for("ecnf.index")),
             ('Browse', ' ')]
    return render_template("ecnf-stats.html", info=info, title=t, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/browse/<int:d>/")
def statistics_by_degree(d):
    if d==1:
        return redirect(url_for("ec.statistics"))
    info = {}

    sigs_by_deg = ECNF_stats().sigs_by_deg
    if d not in sigs_by_deg:
        info['error'] = "The database does not contain any elliptic curves defined over fields of degree %s" % d
    else:
        info['degree'] = d

    fields_by_sig = ECNF_stats().fields_by_sig
    counts_by_sig = ECNF_stats().sig_normstats
    counts_by_field = ECNF_stats().field_normstats

    def field_counts(f):
        return [f,counts_by_field[f]]

    def sig_counts(sig):
        return ['%s,%s'%sig, counts_by_sig[sig], [field_counts(f) for f in fields_by_sig[sig]]]

    info['summary'] = ECNF_stats().degree_summary(d)
    info['sig_stats'] = [sig_counts(sig) for sig in sigs_by_deg[d]]
    if d==2:
        t = 'Elliptic curves over quadratic number fields'
    elif d==3:
        t = 'Elliptic curves over cubic number fields'
    elif d==4:
        t = 'Elliptic curves over quartic number fields'
    elif d==5:
        t = 'Elliptic curves over quintic number fields'
    elif d==6:
        t = 'Elliptic curves over sextic number fields'
    else:
        t = 'Elliptic curves over number fields of degree {}'.format(d)

    bread = [('Elliptic curves', url_for("ecnf.index")),
              ('Degree %s' % d,' ')]
    return render_template("ecnf-by-degree.html", info=info, title=t, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/browse/<int:d>/<int:r>/")
def statistics_by_signature(d,r):
    if d==1:
        return redirect(url_for("ec.statistics"))

    info = {}

    sigs_by_deg = ECNF_stats().sigs_by_deg
    if d not in sigs_by_deg:
        info['error'] = "The database does not contain any elliptic curves defined over fields of degree %s" % d
    else:
        info['degree'] = d

    if r not in range(d%2,d+1,2):
        info['error'] = "Invalid signature %s" % info['sig']
    s = (d-r)//2
    sig = (r,s)
    info['sig'] = '%s,%s' % sig
    info['summary'] = ECNF_stats().signature_summary(sig)

    fields_by_sig = ECNF_stats().fields_by_sig
    counts_by_field = ECNF_stats().field_normstats

    def field_counts(f):
        return [f,counts_by_field[f]]

    info['sig_stats'] = [field_counts(f) for f in fields_by_sig[sig]]
    if info['sig'] == '2,0':
        t = 'Elliptic curves over real quadratic number fields'
    elif info['sig'] == '0,1':
        t = 'Elliptic curves over imaginary quadratic number fields'
    elif info['sig'] == '3,0':
        t = 'Elliptic curves over totally real cubic number fields'
    elif info['sig'] == '1,1':
        t = 'Elliptic curves over mixed cubic number fields'
    elif info['sig'] == '4,0':
        t = 'Elliptic curves over totally real quartic number fields'
    elif info['sig'] == '5,0':
        t = 'Elliptic curves over totally real quintic number fields'
    elif info['sig'] == '6,0':
        t = 'Elliptic curves over totally real sextic number fields'
    else:
        t = 'Elliptic curves over number fields of degree %s, signature (%s)' % (d,info['sig'])
    bread = [('Elliptic curves', url_for("ecnf.index")),
              ('Degree %s' % d,url_for("ecnf.statistics_by_degree", d=d)),
              ('Signature (%s)' % info['sig'],' ')]
    return render_template("ecnf-by-signature.html", info=info, title=t, bread=bread, learnmore=learnmore_list())

@ecnf_page.route("/download_all/<nf>/<conductor_label>/<class_label>/<number>")
def download_ECNF_all(nf,conductor_label,class_label,number):
    conductor_label = unquote(conductor_label)
    try:
        nf_label = nf_string_to_label(nf)
    except ValueError:
        flash_error("%s is not a valid number field label", nf_label)
        return redirect(url_for(".index"))
    label = "".join(["-".join([nf_label, conductor_label, class_label]), number])
    if not LABEL_RE.fullmatch(label):
        flash_error("%s is not a valid elliptic curve label.", label)
        return redirect(url_for(".index"))
    data = db.ec_nfcurves.lookup(label)
    if data is None:
        flash_error("%s is not the label of an elliptic curve in the database.", label)
        return redirect(url_for(".index"))

    response = make_response(Json.dumps(data))
    response.headers['Content-type'] = 'text/plain'
    return response

@ecnf_page.route('/<nf>/<conductor_label>/<class_label>/<number>/download/<download_type>')
def ecnf_code_download(**args):
    try:
        response = make_response(ecnf_code(**args))
    except ValueError:
        return abort(404)
    response.headers['Content-type'] = 'text/plain'
    return response

def ecnf_code(**args):
    label = "".join(["-".join([args['nf'], args['conductor_label'], args['class_label']]), args['number']])
    if not LABEL_RE.fullmatch(label):
        return abort(404)
    lang = args['download_type']
    if lang=='gp':
        lang = 'pari'

    from lmfdb.ecnf.WebEllipticCurve import make_code, Comment, Fullname, code_names, sorted_code_names
    Ecode =  make_code(label, lang)
    code = "{} {} code for working with elliptic curve {}\n\n".format(Comment[lang],Fullname[lang],label)
    code += "{} (Note that not all these functions may be available, and some may take a long time to execute.)\n".format(Comment[lang])
    for k in sorted_code_names:
        if Ecode[k]:
            code += "\n{} {}: \n".format(Comment[lang],code_names[k])
            code += Ecode[k] + ('\n' if '\n' not in Ecode[k] else '')
    return code

def disp_tor(t):
    if len(t) == 1:
        return "[%s]" % t, "C%s" % t
    else:
        return "[%s,%s]" % t, "C%s&times;C%s" % t

class ECNFSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"
    jump_example = "2.2.5.1-31.1-a1"
    jump_egspan = "e.g. 2.2.5.1-31.1-a1 or 2.2.5.1-31.1-a"
    jump_knowl = "ec.search_input"
    jump_prompt = "Label"
    def __init__(self):
        field = TextBox(
            name="field",
            label="Base field",
            knowl="ag.base_field",
            example="2.2.5.1",
            example_span="2.2.5.1 or Qsqrt5")
        include_base_change = ExcludeOnlyBox(
            name="include_base_change",
            label="Base change curves",
            knowl="ec.base_change")
        include_Q_curves = ExcludeOnlyBox(
            name="include_Q_curves",
            label=r"\(\Q\)-curves",
            knowl="ec.q_curve")
        cond_quantifier = SelectBox(
            name='conductor_type',
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides','divides'),
                     ],
            min_width=85)
        conductor_norm = TextBox(
            name="conductor_norm",
            label="Conductor norm",
            short_label="Cond norm",
            knowl="ec.conductor",
            example="31",
            example_span="31 or 1-100")
        one = SelectBox(
            name="one",
            label="Curves per isogeny class",
            knowl="ec.isogeny_class",
            example="all, one",
            options=[("", "all"),
                     ("yes", "one")])
        include_cm = SelectBox(
            name="include_cm",
            label="CM",
            knowl="ec.complex_multiplication",
            options=[('', ''), ('PCM', 'potential CM'), ('PCMnoCM', 'potential CM but no CM'), ('CM', 'CM'), ('noPCM', 'no potential CM')])
        cm_disc = TextBox(
            name="cm_disc",
            label= "CM discriminant",
            example="-4",
            example_span="-4 or -3,-8",
            knowl="ec.complex_multiplication"
            )
        jinv = TextBox(
            name="jinv",
            label="j-invariant",
            knowl="ec.j_invariant",
            width=685,
            short_width=160,
            colspan=(1, 4, 1),
            example_span_colspan=2,
            example="105474/49 + a*34213/49",
            example_span="")
        rank = TextBox(
            name="rank",
            label="Rank*",
            knowl="ec.rank",
            example="2")
        torsion = TextBox(
            name="torsion",
            label="Torsion order",
            knowl="ec.torsion_order",
            example="2")
        bf_deg = SelectBox(
            name="bf_deg",
            label="Base field degree",
            knowl="nf.degree",
            options=[("",""),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6")]
            )

        tor_opts = ([("", ""),
                     ("[]", "trivial")] +
                    [disp_tor(tuple(t)) for t in ECNF_stats().torsion_counts if t])
        torsion_structure = SelectBox(
            name="torsion_structure",
            label="Torsion structure",
            knowl="ec.torsion_subgroup",
            options=tor_opts)
        sha = TextBox(
            name="sha",
            label="Analytic order* of &#1064;",
            knowl="ec.analytic_sha_order",
            example="4")
        regulator = TextBox(
            name="regulator",
            label="Regulator*",
            knowl="ec.regulator",
            example="8.4-9.1")
        bad_quant = SubsetBox(
            name="bad_quantifier")
        bad_primes = TextBoxWithSelect(
            name="conductor_norm_factors",
            label="Bad primes",
            knowl="ec.reduction_type",
            example="5,13",
            select_box=bad_quant)
        isodeg = TextBox(
            name="isodeg",
            label="Cyclic isogeny degree",
            knowl="ec.isogeny",
            example="16")
        semistable = YesNoBox(
            name="semistable",
            label="Semistable",
            example="Yes",
            knowl="ec.semistable")
        potential_good_reduction = YesNoBox(
            name="potential_good_reduction",
            label="Potential good reduction",
            example="Yes",
            knowl="ec.potential_good_reduction")
        class_size = TextBox(
            name="class_size",
            label="Isogeny class size",
            knowl="ec.isogeny",
            example="4")
        class_deg = TextBox(
            name="class_deg",
            label="Isogeny class degree",
            knowl="ec.isogeny",
            example="16")
        count = CountBox()

        self.browse_array = [
            [field, bf_deg],
            [conductor_norm, include_base_change],
            [rank, include_Q_curves],
            [torsion, torsion_structure],
            [cm_disc, include_cm],
            [sha, regulator],
            [isodeg, one],
            [class_size, class_deg],
            [semistable, potential_good_reduction],
            [jinv],
            [count, bad_primes]
            ]

        self.refine_array = [
            [field, conductor_norm, rank, torsion, cm_disc],
            [bf_deg, include_base_change, include_Q_curves, torsion_structure, include_cm],
            [sha, isodeg, class_size, semistable, jinv],
            [regulator, one, class_deg, potential_good_reduction, bad_primes],
            ]
