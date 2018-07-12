# -*- coding: utf-8 -*-
import re
import time
import ast
import StringIO
import lmfdb.base
from pymongo import ASCENDING
from lmfdb.base import app
from lmfdb.utils import to_dict, make_logger, random_object_from_collection
from lmfdb.abvar.fq import abvarfq_page
from lmfdb.search_parsing import parse_ints, parse_string_start, parse_count, parse_start, parse_nf_string, parse_galgrp
from search_parsing import parse_newton_polygon, parse_abvar_decomp
from isog_class import validate_label, AbvarFq_isoclass
from stats import AbvarFqStats
from flask import flash, render_template, url_for, request, redirect, send_file
from markupsafe import Markup
from sage.misc.cachefunc import cached_function
from sage.rings.all import PolynomialRing, ZZ

logger = make_logger("abvarfq")

#########################
#   Database connection
#########################

@cached_function
def db():
    return lmfdb.base.getDBConnection().abvar.fq_isog

#########################
#    Top level
#########################

def get_bread(*breads):
    bc = [('Abelian Varieties', url_for(".abelian_varieties")),
          ('Fq', url_for(".abelian_varieties"))]
    map(bc.append, breads)
    return bc

abvarfq_credit = 'Taylor Dupuy, Kiran Kedlaya, David Roe, Christelle Vincent'

@app.route("/EllipticCurves/Fq")
def ECFq_redirect():
    return redirect(url_for("abvarfq.abelian_varieties"), **request.args)

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) < 0, learnmore_list())

#########################
#  Search/navigate
#########################

@abvarfq_page.route("/")
def abelian_varieties():
    args = request.args
    if args:
        info = to_dict(args)
        #information has been entered, but not requesting to change the parameters of the table
        if not('table_field_range' in info) and not('table_dimension_range' in info):
            return abelian_variety_search(**args)
        #information has been entered, requesting to change the parameters of the table
        else:
            return abelian_variety_browse(**args)
    # no information was entered
    else:
        return abelian_variety_browse(**args)

@abvarfq_page.route("/<int:g>/")
def abelian_varieties_by_g(g):
    D = to_dict(request.args)
    if 'g' not in D: D['g'] = g
    D['bread'] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)))
    return abelian_variety_search(**D)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    D = to_dict(request.args)
    if 'g' not in D: D['g'] = g
    if 'q' not in D: D['q'] = q
    D['bread'] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)),
                           (str(q), url_for(".abelian_varieties_by_gq", g=g, q=q)))
    return abelian_variety_search(**D)

@abvarfq_page.route("/<int:g>/<int:q>/<iso>")
def abelian_varieties_by_gqi(g, q, iso):
    label = abvar_label(g,q,iso)
    try:
        validate_label(label)
    except ValueError as err:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label: %s." % (label, str(err))), "error")
        return search_input_error()
    try:
        cl = AbvarFq_isoclass.by_label(label)
    except ValueError:
        flash(Markup("Error: <span style='color:black'>%s</span> is not in the database." % (label)), "error")
        return search_input_error()
    bread = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)),
                      (str(q), url_for(".abelian_varieties_by_gq", g=g, q=q)),
                      (iso, url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso)))

    return render_template("show-abvarfq.html",
                           properties2=cl.properties(),
                           credit=abvarfq_credit,
                           title='Abelian Variety Isogeny Class %s over $%s$'%(label, cl.field()),
                           bread=bread,
                           cl=cl,
                           learnmore=learnmore_list())


def abelian_variety_search(**args):
    info = to_dict(args)

    if 'download' in info and info['download'] != 0:
        return download_search(info)

    bread = args.get('bread', get_bread(('Search Results', ' ')))
    if 'jump' in info:
        return by_label(info.get('label',''))
    query = {}

    try:
        parse_ints(info,query,'q',name='base field')
        parse_ints(info,query,'g',name='dimension')
        if 'simple' in info:
            if info['simple'] == 'yes':
                query['is_simp'] = True
            elif info['simple'] == 'no':
                query['is_simp'] = False
        if 'primitive' in info:
            if info['primitive'] == 'yes':
                query['is_prim'] = True
            elif info['primitive'] == 'no':
                query['is_prim'] = False
        if 'jacobian' in info:
            jac = info['jacobian']
            if jac == 'yes':
                query['is_jac'] = 1
            elif jac == 'not_no':
                query['is_jac'] = {'$gt' : -1}
            elif jac == 'not_yes':
                query['is_jac'] = {'$lt' : 1}
            elif jac == 'no':
                query['is_jac'] = -1
        if 'polarizable' in info:
            pol = info['polarizable']
            if pol == 'yes':
                query['is_pp'] = 1
            elif pol == 'not_no':
                query['is_pp'] = {'$gt' : -1}
            elif pol == 'not_yes':
                query['is_pp'] = {'$lt' : 1}
            elif pol == 'no':
                query['is_pp'] = -1
        parse_ints(info,query,'p_rank')
        parse_ints(info,query,'ang_rank')
        parse_newton_polygon(info,query,'newton_polygon',qfield='slps') # TODO
        parse_string_start(info,query,'initial_coefficients',qfield='poly',initial_segment=["1"])
        parse_string_start(info,query,'abvar_point_count',qfield='A_cnts')
        parse_string_start(info,query,'curve_point_count',qfield='C_cnts',first_field='pt_cnt')
        parse_abvar_decomp(info,query,'decomposition',qfield='decomp',av_stats=AbvarFqStats())
        parse_nf_string(info,query,'number_field',qfield='nf')
        parse_galgrp(info,query,qfield='gal')
    except ValueError:
        return search_input_error(info, bread)

    info['query'] = query
    count = parse_count(info, 50)
    start = parse_start(info)

    cursor = db().find(query)
    nres = cursor.count()
    if start >= nres:
        start -= (1 + (start - nres) / count) * count
    if start < 0:
        start = 0


    res = cursor.sort([('sort', ASCENDING)]).skip(start).limit(count)
    res = list(res)
    info['abvars'] = [AbvarFq_isoclass(x) for x in res]
    info['number'] = nres
    info['start'] = start
    info['count'] = count
    info['more'] = int(start + count < nres)
    if nres == 1:
        info['report'] = 'unique match'
    elif nres == 0:
        info['report'] = 'no matches'
    elif nres > count or start != 0:
        info['report'] = 'displaying matches %s-%s of %s' %(start + 1, min(nres, start+count), nres)
    else:
        info['report'] = 'displaying all %s matches' % nres
    t = 'Abelian Variety search results'
    return render_template("abvarfq-search-results.html", info=info, credit=abvarfq_credit, bread=bread, title=t)

def abelian_variety_browse(**args):
    info = to_dict(args)
    if not('table_dimension_range' in info) or (info['table_dimension_range']==''):
        info['table_dimension_range'] = "1-6"
    if not('table_field_range' in info)  or (info['table_field_range']==''):
        info['table_field_range'] = "2-27"

    table_params = {}
    av_stats=AbvarFqStats()

    # Handle dimension range
    gs = av_stats.gs
    try:
        if ',' in info['table_dimension_range']:
            flash(Markup("Error: You cannot use commas in the table ranges."), "error")
            raise ValueError
        parse_ints(info,table_params,'table_dimension_range',qfield='g')
    except (ValueError, AttributeError, TypeError):
        gmin, gmax = 1, 6
    else:
        if isinstance(table_params['g'], int):
            gmin = gmax = table_params['g']
        else:
            gmin = table_params['g'].get('$gte',min(gs) if gs else table_params['g'].get('$lte',1))
            gmax = table_params['g'].get('$lte',max(gs) if gs else table_params['g'].get('$gte',20))

    # Handle field range
    qs = av_stats.qs
    try:
        if ',' in info['table_field_range']:
            flash(Markup("Error: You cannot use commas in the table ranges."), "error")
            raise ValueError
        parse_ints(info,table_params,'table_field_range',qfield='q')
    except (ValueError, AttributeError, TypeError):
        qmin, qmax = 2, 27
    else:
        if isinstance(table_params['q'], int):
            qmin = qmax = table_params['q']
        else:
            qmin = table_params['q'].get('$gte',min(qs) if qs else table_params['q'].get('$lte',0))
            qmax = table_params['q'].get('$lte',max(qs) if qs else table_params['q'].get('$gte',1000))
    info['table'] = {}
    if gmin == gmax:
        info['table_dimension_range'] = "{0}".format(gmin)
    else:
        info['table_dimension_range'] = "{0}-{1}".format(gmin, gmax)
    if qmin == qmax:
        info['table_field_range'] = "{0}".format(qmin)
    else:
        info['table_field_range'] = "{0}-{1}".format(qmin, qmax)

    for q in qs:
        if q < qmin or q > qmax:
            continue
        info['table'][q] = {}
        L = av_stats._counts[q]
        for g in xrange(gmin, gmax+1):
            if g < len(L):
                info['table'][q][g] = L[g]
            else:
                info['table'][q][g] = 0

    info['col_heads'] = [q for q in qs if q >= qmin and q <= qmax]
    info['row_heads'] = [g for g in gs if g >= gmin and g <= gmax]

    return render_template("abvarfq-index.html", title="Isogeny Classes of Abelian Varieties over Finite Fields", info=info, credit=abvarfq_credit, bread=get_bread(), learnmore=learnmore_list())

def search_input_error(info=None, bread=None):
    if info is None: info = {'err':'','query':{}}
    if bread is None: bread = get_bread(('Search Results', '.'))
    return render_template("abvarfq-search-results.html", info=info, title='Abelian Variety Search Input Error', bread=bread)

@abvarfq_page.route("/<label>")
def by_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid label: %s." % (label, str(err))), "error")
        return search_input_error()
    g, q, iso = split_label(label)
    return redirect(url_for(".abelian_varieties_by_gqi", g = g, q = q, iso = iso))

@abvarfq_page.route("/random")
def random_class():
    label = random_object_from_collection(db())['label']
    g, q, iso = split_label(label)
    return redirect(url_for(".abelian_varieties_by_gqi", g = g, q = q, iso = iso))

def download_search(info):
    dltype = info['Submit']
    R = PolynomialRing(ZZ, 'x')
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'weil_polynomials.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'weil_polynomials.sage'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'weil_polynomials.m'
    s = com1 + "\n"
    s += com + " Weil polynomials downloaded from the LMFDB on %s.\n"%(mydate)
    s += com + " Below is a list (called data), collecting the weight 1 L-polynomial\n"
    s += com + " attached to each isogeny class of an abelian variety.\n"
    s += "\n" + com2
    s += "\n"

    if dltype == 'magma':
        s += 'P<x> := PolynomialRing(Integers()); \n'
        s += 'data := ['
    else:
        if dltype == 'sage':
            s += 'x = polygen(ZZ) \n'
        s += 'data = [ '
    s += '\\\n'
    res = db().find(ast.literal_eval(info["query"]))
    for f in res:
        poly = R([int(c) for c in f['poly'].split(" ")])
        s += str(poly) + ',\\\n'
    s = s[:-3]
    s += ']\n'
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

@abvarfq_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Weil Polynomial Data'
    bread = get_bread(('Completeness', '.'))
    return render_template("single.html", kid='dq.av.fq.extent',
                           credit=abvarfq_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@abvarfq_page.route("/Source")
def how_computed_page():
    t = 'Source of the Weil Polynomial Data'
    bread = get_bread(('Source', '.'))
    return render_template("single.html", kid='dq.av.fq.source',
                           credit=abvarfq_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@abvarfq_page.route("/Labels")
def labels_page():
    t = 'Labels for Isogeny Classes of Abelian Varieties'
    bread = get_bread(('Labels', '.'))
    return render_template("single.html", kid='av.fq.lmfdb_label',
                           credit=abvarfq_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

lmfdb_label_regex = re.compile(r'(\d+)\.(\d+)\.([a-z_]+)')

def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def abvar_label(g, q, iso):
    return "%s.%s.%s" % (g, q, iso)
