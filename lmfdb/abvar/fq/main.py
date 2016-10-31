# -*- coding: utf-8 -*-
import re
import time
import ast
import StringIO
from pymongo import ASCENDING, DESCENDING
import lmfdb.base
from lmfdb.base import app
from lmfdb.utils import to_dict, make_logger
from lmfdb.abvar.fq import abvarfq_page
from lmfdb.search_parsing import parse_ints, parse_list_start, parse_count, parse_start, parse_range
from search_parsing import parse_newton_polygon, parse_abvar_decomp
from isog_class import validate_label, AbvarFq_isoclass
from stats import AbvarFqStats
from flask import flash, render_template, url_for, request, redirect, make_response, send_file
from markupsafe import Markup
from sage.misc.cachefunc import cached_function
from sage.rings.all import PolynomialRing, ZZ
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import extract_limits_as_tuple

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

abvarfq_credit = 'Kiran Kedlaya'

@app.route("/EllipticCurves/Fq")
def ECFq_redirect():
    return redirect(url_for("abvarfq.abelian_varieties"), **request.args)

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for isogeny classes of abelian varieties', url_for(".labels_page"))]

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
    return abelian_variety_search(**D)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    D = to_dict(request.args)
    if 'g' not in D: D['g'] = g
    if 'q' not in D: D['q'] = q
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
    return render_template("show-abvarfq.html",
                           credit=abvarfq_credit,
                           title='Abelian Variety isogeny class %s over $%s$'%(label, cl.field()),
                           bread=get_bread(('Search Results', '.')),
                           cl=cl,
                           learnmore=learnmore_list())


def abelian_variety_search(**args):
    info = to_dict(args)

    if 'download' in info and info['download'] != 0:
        return download_search(info)

    bread = get_bread(('Search Results', '.'))
    if 'jump' in info:
        return by_label(info.get('label',''))
    query = {}

    try:
        parse_ints(info,query,'q')
        parse_ints(info,query,'g')
        if 'simple_only' in info and info['simple_only'] == 'yes':
            query['decomposition'] = {'$size' : 1}
            query['decomposition.0.1'] = 1
        if 'primitive_only' in info and info['primitive_only'] == 'yes':
            query['primitive_models'] = []
        parse_ints(info,query,'p_rank')
        parse_newton_polygon(info,query,'newton_polygon',qfield='slopes')
        parse_list_start(info,query,'initial_coefficients',qfield='polynomial',index_shift=1)
        parse_list_start(info,query,'abvar_point_count',qfield='A_counts')
        parse_list_start(info,query,'curve_point_count',qfield='C_counts')
        parse_abvar_decomp(info,query,'decomposition',av_stats=AbvarFqStats())
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

    #res = cursor.sort([]).skip(start).limit(count)
    res = cursor.skip(start).limit(count)
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

    gD = parse_range(info['table_dimension_range'])
    qD = parse_range(info['table_field_range'])
    s = {'g':gD,'q':qD}

    look = db().find(s)#.sort([('g',int(1)),('q',int(1))])
    qs = look.distinct('q')
    gs = look.distinct('g')
    info['table'] = {}
    if isinstance(qD, int):
        qmin = qmax = qD
    else:
        qmin = qD.get('$gte',min(qs) if qs else qD.get('$lte',0))
        qmax = qD.get('$lte',max(qs) if qs else qD.get('$gte',1000))
    if isinstance(gD, int):
        gmin = gmax = gD
    else:
        gmin = gD.get('$gte',min(gs) if gs else gD.get('$lte',0))
        gmax = gD.get('$lte',max(gs) if gs else gD.get('$gte',20))

    if gmin == gmax:
        info['table_dimension_range'] = "{0}".format(gmin)
    else:
        info['table_dimension_range'] = "{0}-{1}".format(gmin, gmax)
    if qmin == qmax:
        info['table_field_range'] = "{0}".format(qmin)
    else:
        info['table_field_range'] = "{0}-{1}".format(qmin, qmax)

    for q in qs:
        info['table'][q] = {}
        for g in gs:
            info['table'][q][g] = 0
    for q in qs:
        for g in gs:
            try:
                info['table'][q][g] = db().find({'g': g, 'q': q}).count()
            except KeyError:
                pass

    info['col_heads'] = sorted(int(q) for q in qs)
    info['row_heads'] = sorted(int(g) for g in gs)

    return render_template("abvarfq-index.html", title="Isogeny Classes of Abelian Varieties over Finite Fields", info=info, credit=abvarfq_credit, bread=get_bread(), learnmore=learnmore_list())

def search_input_error(info=None, bread=None):
    if info is None: info = {'err':'','query':{}}
    if bread is None: bread = get_bread(('Search Results', '.'))
    return render_template("abvarfq-search-results.html", info=info, title='Abelian Variety search input error', bread=bread)

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
        poly = R([int(c) for c in f['polynomial']])
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
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True)

@abvarfq_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Weil polynomial data'
    bread = get_bread(('Completeness', '.'))
    credit = 'Kiran Kedlaya'
    return render_template("single.html", kid='dq.av.fq.extent',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@abvarfq_page.route("/Source")
def how_computed_page():
    t = 'Source of the Weil polynomial data'
    bread = get_bread(('Source', '.'))
    credit = 'Kiran Kedlaya'
    return render_template("single.html", kid='dq.av.fq.source',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@abvarfq_page.route("/Labels")
def labels_page():
    t = 'Labels for isogeny classes of abelian varieties'
    bread = get_bread(('Labels', '.'))
    credit = 'Kiran Kedlaya'
    return render_template("single.html", kid='av.fq.lmfdb_label',
                           credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))
              
lmfdb_label_regex = re.compile(r'(\d+)\.(\d+)\.([a-z_]+)')
                                  
def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()
    
def abvar_label(g, q, iso):
    return "%s.%s.%s" % (g, q, iso)
    

                
            
    
