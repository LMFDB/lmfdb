# -*- coding: utf-8 -*-

import ast
import re
import StringIO
import time

from flask import render_template, url_for, request, redirect, send_file
from collections import defaultdict
from sage.rings.all import PolynomialRing, ZZ

from lmfdb import db
from lmfdb.app import app
from lmfdb.logger import make_logger
from lmfdb.utils import (
    to_dict, flash_error, integer_options,
    SearchArray, TextBox, SelectBox, TextBoxWithSelect, BasicSpacer, SkipBox, CheckBox, CheckboxSpacer,
    parse_ints, parse_string_start,
    parse_subset, parse_submultiset, parse_bool, parse_bool_unknown,
    display_knowl,
    search_wrap, count_wrap)
from . import abvarfq_page
from .search_parsing import (parse_newton_polygon, parse_nf_string, parse_galgrp)
from .isog_class import validate_label, AbvarFq_isoclass
from .stats import AbvarFqStats

logger = make_logger("abvarfq")

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
            ('Reliability of the data', url_for(".reliability_page")),
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
        # hidden_search_type for prev/next buttons
        info['search_type'] = search_type = info.get('search_type', info.get('hst', 'List'))
        info['search_array'] = AbvarSearchArray()

        if search_type == 'List':
            return abelian_variety_search(info)
        elif search_type == 'Counts':
            return abelian_variety_count(info)
        elif search_type == 'Random':
            return abelian_variety_search(info, random=True)
        assert False
    else:
        return abelian_variety_browse(**args)

@abvarfq_page.route("/<int:g>/")
def abelian_varieties_by_g(g):
    D = to_dict(request.args)
    if 'g' not in D: D['g'] = g
    D['bread'] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)))
    return abelian_variety_search(D)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    D = to_dict(request.args)
    if 'g' not in D: D['g'] = g
    if 'q' not in D: D['q'] = q
    D['bread'] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)),
                           (str(q), url_for(".abelian_varieties_by_gq", g=g, q=q)))
    return abelian_variety_search(D)

@abvarfq_page.route("/<int:g>/<int:q>/<iso>")
def abelian_varieties_by_gqi(g, q, iso):
    label = abvar_label(g, q, iso)
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return search_input_error()
    try:
        cl = AbvarFq_isoclass.by_label(label)
    except ValueError as err:
        flash_error("%s is not in the database.", label)
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
                           learnmore=learnmore_list(),
                           KNOWL_ID='av.fq.%s'%label)

def url_for_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return redirect(url_for(".abelian_varieties"))
    g, q, iso = split_label(label)
    return url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso)

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
    for f in db.av_fq_isog.search(ast.literal_eval(info["query"]), 'poly'):
        poly = R(f)
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

class AbvarSearchArray(SearchArray):
    def __init__(self):
        qshort = display_knowl('ag.base_field', 'base field')
        qtext = 'Cardinality of the %s' % (qshort)
        q = TextBox('q', label=qtext, short_label=qshort, example='81', example_span='81 or 3-49')
        g = TextBox('g', 'Dimension', 'ag.dimension', example='2', example_span='2 or 3-5')
        p_rank = TextBox('p_rank', '$p$-rank', 'av.fq.p_rank', example='2')
        angle_rank = TextBox('angle_rank', 'Angle rank', 'av.fq.angle_rank', example='3', advanced=True)
        newton_polygon = TextBox('newton_polygon', 'Slopes of Newton polygon', 'lf.newton_polygon', example='[0,0,1/2]', colspan=(1,3,1), width=40, short_label='slopes')
        initial_coefficients = TextBox('initial_coefficients', 'Initial coefficients', 'av.fq.initial_coefficients', example='[2, -1, 3, 9]', colspan=(1,3,1), width=40, advanced=True)
        abvar_point_count = TextBox('abvar_point_count', 'Point counts of the abelian variety', knowl='ag.fq.point_counts', example='[75,7125]', colspan=(1,3,1), width=40, short_label='points on variety', advanced=True)
        curve_point_count = TextBox('curve_point_count', 'Point counts of the curve', 'av.fq.curve_point_counts', example='[9,87]', colspan=(1,3,1), width=40, short_label='points on curve', advanced=True)
        number_field = TextBox('number_field', 'Number field', 'av.fq.number_field', example='4.0.29584.2', example_span='4.0.29584.2 or Qzeta8', colspan=(1,3,1), width=40, advanced=True)
        galois_group = TextBox('galois_group', 'Galois group', 'nf.galois_group', example='4T3', example_span='C4, or 8T12, a list of ' + display_knowl('nf.galois_group.name','group labels'), colspan=(1,3,1), width=40, short_label='Galois group', advanced=True)
        size = TextBox('size', 'Isogeny class size', 'av.fq.isogeny_class_size', example='1', example_col=False, advanced=True)
        gdshort = display_knowl('av.endomorphism_field', 'End.') + ' degree'
        gdlong = 'Degree of ' + display_knowl('av.endomorphism_field', 'endomorphism_field')
        geom_deg = TextBox('geom_deg', label=gdlong, short_label=gdshort, example='168', example_span='6-12, 168')
        jac_cnt = TextBox('jac_cnt', 'Number of Jacobians', 'av.jacobian_count', example='6', short_label='# Jacobians', advanced=True)
        hyp_cnt = TextBox('hyp_cnt', 'Number of Hyperelliptic Jacobians', 'av.hyperelliptic_count', example='6', short_label='# Hyp. Jacobians', advanced=True)
        tcshort = display_knowl('av.twist', '# twists')
        tclong = 'Number of ' + display_knowl('av.twist', 'twists')
        twist_count = TextBox('twist_count', label=tclong, short_label=tcshort, example='390', example_col=False, advanced=True)
        simple = SelectBox('simple', 'Simple', [('yes', 'yes'), ('', 'unrestricted'), ('no', 'no')], knowl='av.simple')
        geom_simple = SelectBox('geom_simple', 'Geometrically simple', [('yes', 'yes'), ('', 'unrestricted'), ('no', 'no')], knowl='av.geometrically_simple', short_label='geom. simple')
        primitive = SelectBox('primitive', 'Primitive', [('yes', 'yes'), ('', 'unrestricted'), ('no', 'no')], knowl='ag.primitive')
        uopts = [('yes', 'yes'), ('not_no', 'yes or unknown'), ('', 'unrestricted'), ('not_yes', 'no or unknown'), ('no', 'no')]
        polarizable = SelectBox('polarizable', 'Principally polarizable', uopts, knowl='av.princ_polarizable', short_label='princ polarizable')
        jacobian = SelectBox('jacobian', 'Jacobian', uopts, knowl='ag.jacobian')
        uglabel = 'Use ' + display_knowl('av.decomposition', 'geometric decomposition') + ' in the following inputs'
        use_geom_decomp = CheckBox('use_geom_decomp', label=uglabel, short_label=uglabel)
        use_geom_index = CheckboxSpacer(use_geom_decomp, colspan=4, advanced=True)
        use_geom_refine = CheckboxSpacer(use_geom_decomp, colspan=5, advanced=True)
        def long_label(d):
            return '&nbsp;&nbsp;&nbsp;&nbsp;' + display_knowl('av.decomposition', 'Dimension %s factors'%d)
        def short_label(d):
            return display_knowl('av.decomposition', 'dim %s factors'%d)
        dim1 = TextBox('dim1_factors', label=long_label(1), example='1-3', example_col=False, short_label=short_label(1), advanced=True)
        dim1d = TextBox('dim1_distinct', 'Distinct factors', 'av.decomposition', example='1-2', example_span='2 or 1-3', short_label='(distinct)', advanced=True)
        dim2 = TextBox('dim2_factors', label=long_label(2), example='1-3', example_col=False, short_label=short_label(2), advanced=True)
        dim2d = TextBox('dim2_distinct', 'Distinct factors', 'av.decomposition', example='1-2', example_span='2 or 1-3', short_label='(distinct)', advanced=True)
        dim3 = TextBox('dim3_factors', label=long_label(3), example='2', example_col=False, short_label=short_label(3), advanced=True)
        dim3d = TextBox('dim3_distinct', 'Distinct factors', 'av.decomposition', example='1', example_span='2 or 0-1', short_label='(distinct)', advanced=True)
        dim4 = TextBox('dim4_factors', label=long_label(4), example='2', example_col=False, short_label=short_label(4), advanced=True)
        dim5 = TextBox('dim5_factors', label=long_label(5), example='2', example_col=False, short_label=short_label(5), advanced=True)
        dim4d = dim5d = SkipBox(example_span='0 or 1', advanced=True)
        simple_quantifier = SelectBox('simple_quantifier', options=[('contained', 'subset of'), ('exactly', 'exactly'), ('', 'superset of')])
        simple_factors = TextBoxWithSelect('simple_factors', 'Simple factors', simple_quantifier, knowl='av.decomposition', colspan=(1,3,2), width=40, short_width=20, example='1.2.b,1.2.b,2.2.a_b', advanced=True)
        count = TextBox('count', 'Maximum number of isogeny classes to display', colspan=(2,1,1), width=10)
        refine_array = [
            [q, g, p_rank, geom_deg, newton_polygon],
            [initial_coefficients, abvar_point_count, curve_point_count, number_field, galois_group],
            [angle_rank, size, jac_cnt, hyp_cnt, twist_count],
            [simple, geom_simple, primitive, polarizable, jacobian],
            use_geom_refine,
            [dim1, dim2, dim3, dim4, dim5],
            [dim1d, dim2d, dim3d, simple_factors]]
        browse_array = [
            [q, primitive], [g, simple], [p_rank, geom_simple],
            [geom_deg, polarizable], [jac_cnt, jacobian],
            [hyp_cnt, size], [angle_rank, twist_count],
            [newton_polygon], [initial_coefficients], [abvar_point_count],
            [curve_point_count], [simple_factors], use_geom_index,
            [dim1, dim1d], [dim2, dim2d], [dim3, dim3d], [dim4, dim4d],
            [dim5, dim5d], [number_field], [galois_group], [count]]
        SearchArray.__init__(self, browse_array, refine_array)

def common_parse(info, query):
    parse_ints(info,query,'q',name='base field')
    parse_ints(info,query,'g',name='dimension')
    parse_ints(info,query,'geom_deg',qfield='geometric_extension_degree')
    parse_bool(info,query,'simple',qfield='is_simple')
    parse_bool(info,query,'geom_simple',qfield='is_geometrically_simple')
    parse_bool(info,query,'primitive',qfield='is_primitive')
    parse_bool_unknown(info, query, 'jacobian', qfield='has_jacobian')
    parse_bool_unknown(info, query, 'polarizable', qfield='has_principal_polarization')
    parse_ints(info,query,'p_rank')
    parse_ints(info,query,'angle_rank')
    parse_ints(info,query,'jac_cnt', qfield='jacobian_count', name='Number of Jacobians')
    parse_ints(info,query,'hyp_cnt', qfield='hyp_count', name='Number of Hyperelliptic Jacobians')
    parse_ints(info,query,'twist_count')
    parse_ints(info,query,'size')
    parse_newton_polygon(info,query,'newton_polygon',qfield='slopes')
    parse_string_start(info,query,'initial_coefficients',qfield='poly_str',initial_segment=["1"])
    parse_string_start(info,query,'abvar_point_count',qfield='abvar_counts_str')
    parse_string_start(info,query,'curve_point_count',qfield='curve_counts_str',first_field='curve_count')
    if info.get('simple_quantifier') == 'contained':
        parse_subset(info,query,'simple_factors',qfield='simple_distinct',mode='subsets')
    elif info.get('simple_quantifier') == 'exactly':
        parse_subset(info,query,'simple_factors',qfield='simple_distinct',mode='exact')
    elif info.get('simple_quantifier') == '':
        parse_submultiset(info,query,'simple_factors',mode='append')
    if info.get('use_geom_decomp') == 'on':
        dimstr = 'geom_dim'
    else:
        dimstr = 'dim'
    for n in range(1,6):
        parse_ints(info,query,'dim%s_factors'%n, qfield='%s%s_factors'%(dimstr,n))
    for n in range(1,4):
        parse_ints(info,query,'dim%s_distinct'%n, qfield='%s%s_distinct'%(dimstr,n))
    parse_nf_string(info,query,'number_field',qfield='number_fields')
    parse_galgrp(info,query,'galois_group',qfield='galois_groups')
    # Determine whether to show advanced search boxes:
    info['advanced_search'] = False
    for search_box in info['search_array'].all_search:
        if search_box.advanced and search_box.name in info:
            info['advanced_search'] = True
            break

@search_wrap(template="abvarfq-search-results.html",
             table=db.av_fq_isog,
             title='Abelian Variety Search Results',
             err_title='Abelian Variety Search Input Error',
             shortcuts={'jump': lambda info:by_label(info.get('label','')),
                        'download': download_search},
             postprocess=lambda res, info, query: [AbvarFq_isoclass(x) for x in res],
             url_for_label=url_for_label,
             bread=lambda:get_bread(('Search Results', ' ')),
             credit=lambda:abvarfq_credit)
def abelian_variety_search(info, query):
    common_parse(info, query)

@count_wrap(template="abvarfq-count-results.html",
            table=db.av_fq_isog,
            groupby=['g', 'q'],
            title='Abelian Variety Count Results',
            err_title='Abelian Variety Search Input Error',
            overall=AbvarFqStats()._counts,
            bread=lambda:get_bread(('Count Results', ' ')),
            credit=lambda:abvarfq_credit)
def abelian_variety_count(info, query):
    common_parse(info, query)
    urlgen_info = dict(info)
    urlgen_info.pop('hst', None)
    def url_generator(g, q):
        info_copy = dict(urlgen_info)
        info_copy['search_type'] = 'List'
        info_copy['g'] = g
        info_copy['q'] = q
        return url_for('abvarfq.abelian_varieties', **info_copy)
    av_stats = AbvarFqStats()
    if 'g' in info:
        info['row_heads'] = integer_options(info['g'], contained_in=av_stats.gs)
    else:
        info['row_heads'] = av_stats.gs
    if 'q' in info:
        info['col_heads'] = integer_options(info['q'], contained_in=av_stats.qs)
    else:
        info['col_heads'] = av_stats.qs
    if 'p' in query:
        ps = integer_options(info['p'], contained_in=av_stats.qs)
        info['col_heads'] = [q for q in info['col_heads'] if any(q % p == 0 for p in ps)]
    if not info['col_heads']:
        raise ValueError("Must include at least one base field")
    info['na_msg'] = '"n/a" means that the isogeny classes of abelian varieties of this dimension over this field are not in the database yet.'
    info['row_label'] = 'Dimension'
    info['col_label'] = r'Cardinality of base field \(q\)'
    info['url_func'] = url_generator

favorite_isocls_labels = [[
    ('6.2.ag_r_abd_bg_ay_u', 'Large endomorphism degree'),
    ('6.2.ak_cb_ahg_sy_abme_ciq', 'Largest twist class'),
    ('2.167.a_hi', 'Most Jacobians'),
    ('2.64.a_abp', 'Most isomorphism classes'),
    ('4.2.ad_c_a_b', 'Jacobian of function field with claa number 1')]]

def abelian_variety_browse(**args):
    info = to_dict(args)
    info['search_array'] = AbvarSearchArray()
    info['stats'] = AbvarFqStats()
    info['q_ranges'] = ['2', '3', '4', '5', '7-16', '17-25', '27-211', '223-1024']
    info['iso_list'] = [[{'label':label,'url':url_for_label(label),'reason':reason} for label, reason in sublist] for sublist in favorite_isocls_labels]

    return render_template("abvarfq-index.html", title="Isogeny Classes of Abelian Varieties over Finite Fields", info=info, credit=abvarfq_credit, bread=get_bread(), learnmore=learnmore_list())

def search_input_error(info=None, bread=None):
    if info is None: info = {'err':'','query':{}}
    if bread is None: bread = get_bread(('Search Results', '.'))
    return render_template("abvarfq-search-results.html", info=info, title='Abelian Variety Search Input Error', bread=bread)

@abvarfq_page.route("/stats")
def statistics():
    title = 'Abelian Varity Isogeny Classes: Statistics'
    return render_template("display_stats.html", info=AbvarFqStats(), credit=abvarfq_credit, title=title, bread=get_bread(('Statistics', '.')), learnmore=learnmore_list())

@abvarfq_page.route("dynamic_stats")
def dynamic_statistics():
    if len(request.args) > 0:
        info = to_dict(request.args)
    else:
        info = {}
    info['search_array'] = AbvarSearchArray()
    AbvarFqStats().dynamic_setup(info)
    title = 'Abelian Varity Isogeny Classes: Dynamic Statistics'
    return render_template("dynamic_stats.html", info=info, credit=abvarfq_credit, title=title, bread=get_bread(('Dynamic Statistics', '.')), learnmore=learnmore_list())

@abvarfq_page.route("/<label>")
def by_label(label):
    return redirect(url_for_label(label))

@abvarfq_page.route("/random")
def random_class():
    label = db.av_fq_isog.random()
    g, q, iso = split_label(label)
    return redirect(url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso))

@abvarfq_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Weil Polynomial Data'
    bread = get_bread(('Completeness', '.'))
    return render_template("single.html", kid='dq.av.fq.extent',
                           credit=abvarfq_credit, title=t, bread=bread,
                           learnmore=learnmore_list_remove('Completeness'))

@abvarfq_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the Weil Polynomial Data'
    bread = get_bread(('Reliability', '.'))
    return render_template("single.html", kid='dq.av.fq.reliability',
                           credit=abvarfq_credit, title=t, bread=bread,
                           learnmore=learnmore_list_remove('Reliability'))

@abvarfq_page.route("/Source")
def how_computed_page():
    t = 'Source of the Weil Polynomial Data'
    bread = get_bread(('Source', '.'))
    return render_template("single.html", kid='dq.av.fq.source',
                           credit=abvarfq_credit, title=t, bread=bread,
                           learnmore=learnmore_list_remove('Source'))

@abvarfq_page.route("/Labels")
def labels_page():
    t = 'Labels for Isogeny Classes of Abelian Varieties'
    bread = get_bread(('Labels', '.'))
    return render_template("single.html", kid='av.fq.lmfdb_label',
                           credit=abvarfq_credit, title=t, bread=bread,
                           learnmore=learnmore_list_remove('Labels'))

lmfdb_label_regex = re.compile(r'(\d+)\.(\d+)\.([a-z_]+)')

def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def abvar_label(g, q, iso):
    return "%s.%s.%s" % (g, q, iso)
