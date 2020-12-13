# -*- coding: utf-8 -*-
from __future__ import absolute_import
from flask import (render_template, url_for, request, make_response,
                   abort, redirect)

from sage.all import srange, spline, line, ZZ, QQ, latex, real_part, imag_part, Factorization, prime_pi, Integer, PolynomialRing, next_prime

import tempfile
import os
import re
from collections import defaultdict

from . import LfunctionPlot

from .Lfunction import (
    Lfunction_from_db,
    # on the fly L-functions
    Lfunction_HMF, ArtinLfunction,
    Lfunction_Maass, Lfunction_SMF2_scalar_valued,
    RiemannZeta, DedekindZeta,
    SymmetricPowerLfunction, HypergeometricMotiveLfunction,
)
from .LfunctionComp import isogeny_class_table, genus2_isogeny_class_table
from .Lfunctionutilities import (
    p2sage, styleTheSign, get_bread, parse_codename,
    getConductorIsogenyFromLabel, string2number)

from lmfdb.characters.web_character import WebDirichlet
from lmfdb.lfunctions import l_function_page
from lmfdb.maass_forms.plot import paintSvgMaass
from lmfdb.classical_modular_forms.web_newform import convert_newformlabel_from_conrey
from lmfdb.classical_modular_forms.main import set_Trn, process_an_constraints
from lmfdb.artin_representations.main import parse_artin_label
from lmfdb.utils import (
    to_dict, signtocolour, rgbtohex, key_for_numerically_sort, display_float,
    prop_int_pretty, round_to_half_int, display_complex, bigint_knowl,
    search_wrap, parse_bool, parse_ints, parse_floats, parse_noop,
    parse_primes, parse_equality_constraints,
    SearchArray, TextBox, SelectBox, YesNoBox, CountBox,
    SubsetBox, TextBoxWithSelect, RowSpacer)
from lmfdb.utils.names_and_urls import names_and_urls
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.app import is_debug_mode, _single_knowl
from lmfdb import db
from six import string_types



credit_string = "Jonathan Bober, Andrew Booker, Edgar Costa, John Cremona, David Platt"

def get_degree(degree_string):
    if not re.match('degree[0-9]+',degree_string):
        return -1
    return int(degree_string[6:])

def learnmore_list(path=None, remove=None):
    learnmore = [('Completeness of the data', url_for('.completeness'))]
    if path:
        prepath = re.sub(r'^/L/', '', path)
        prepath = re.sub(r'/$', '', prepath)
        learnmore.extend([
            ('Source of the data', url_for('.source', prepath=prepath)),
            ('Reliability of the data', url_for('.reliability', prepath=prepath))])
    if remove:
        return [t for t in learnmore if t[0].find(remove) < 0]
    return learnmore

################################################################################
#   Route functions, navigation pages
################################################################################

# Top page #####################################################################

@l_function_page.route("/")
def index():
    info = to_dict(request.args, search_array=LFunctionSearchArray())
    if request.args:
        info['search_type'] = search_type = info.get('search_type', info.get('hst', 'List'))
        if search_type in ['List', 'Random']:
            return l_function_search(info)
        elif search_type == 'Traces':
            return trace_search(info)
        elif search_type == 'Euler':
            return euler_search(info)
        else:
            flash_error("Invalid search type; if you did not enter it in the URL please report")
    return render_template(
        "LfunctionNavigate.html",
        info=info,
        credit=credit_string,
        title="L-functions",
        learnmore=learnmore_list(),
        bread=get_bread())

def common_postprocess(res, info, query):
    origins = defaultdict(lambda: defaultdict(list))
    for rec in db.lfunc_instances.search({'Lhash': {"$in": [L['Lhash'] for L in res]}}):
        origins[rec["Lhash"]][rec["type"]].append(rec["url"])
    for L in res:
        L['origins'] = names_and_urls([urls[0] for urls in origins[L["Lhash"]].values()])
        L['url'] = url_for_lfunction(L['label'])
    return res

def process_search(res, info, query):
    res = common_postprocess(res, info, query)
    for L in res:
        if L.get('motivic_weight') is None:
            L['analytic_normalization'] = round_to_half_int(L.get('analytic_normalization'))
            L['motivic_weight'] = ''
        else:
            L['analytic_normalization'] = QQ(L['motivic_weight'])/2
        mus = [L['analytic_normalization'] + string2number(mu) for mu in L['gamma_factors'][0]]
        mus = [latex(mu) if imag_part(mu) == 0 else display_complex(real_part(mu), imag_part(mu), 3) for mu in mus]
        if len(mus) > 4 and len(set(mus)) == 1: # >4 so this case only happens for imprimitive
            mus = ["[%s]^{%s}" % (mus[0], len(mus))]
        L['mus'] = ", ".join(mus)
        nus = [L['analytic_normalization'] + string2number(nu) for nu in L['gamma_factors'][1]]
        nus = [latex(nu) if imag_part(nu) == 0 else display_complex(real_part(nu), imag_part(nu), 3) for nu in nus]
        if len(nus) > 4 and len(set(nus)) == 1:
            nus = ["[%s]^{%s}" % (nus[0], len(nus))]
        L['nus'] = ", ".join(nus)
        L['root_angle'] = display_float(L['root_angle'], 3)
        L['z1'] = display_float(L['z1'], 6, no_sci=2, extra_truncation_digits=20)
        L['analytic_conductor'] = display_float(L['analytic_conductor'], 3, extra_truncation_digits=40, latex=True)
        L['factored_conductor'] = latex(Factorization([(ZZ(p), L['conductor'].valuation(p)) for p in L['bad_primes']]))
    return res

def process_trace(res, info, query):
    return common_postprocess(res, info, query)

def process_euler(res, info, query):
    res = common_postprocess(res, info, query)
    R = PolynomialRing(ZZ, 'T')
    for L in res:
        L['euler_factor'] = {}
        p = 2
        for i, F in enumerate(L.get('euler_factors', [])):
            print(p, F, latex(R(F)))
            L['euler_factor'][p] = latex(R(F))
            p = next_prime(p)
    return res

def url_for_lfunction(label):
    try:
        kwargs = dict(zip(('degree', 'conductor', 'character', 'gamma_real', 'gamma_imag', 'index'), 
label.split('-')))
        kwargs['degree'] = int(kwargs['degree'])
    except Exception:
        return render_lfunction_exception("There is no L-function with label '%s'" % label)
    return url_for('.by_label', **kwargs)

@l_function_page.route("/<label>")
def by_full_label(label):
    return redirect(url_for_lfunction(label))

@l_function_page.route("/<int:degree>/<conductor>/<character>/<gamma_real>/<gamma_imag>/<index>")
def by_label(degree, conductor, character, gamma_real, gamma_imag, index):
    args = {'label': '-'.join(map(str, (degree, conductor, character, gamma_real, gamma_imag, index)))}
    return render_single_Lfunction(Lfunction_from_db, args, request)

def common_parse(info, query):
    info['z1'] = parse_floats(info,query,'z1', allow_singletons=True)
    parse_ints(info,query,'degree')
    parse_ints(info,query,'conductor')
    parse_bool(info,query,'primitive')
    parse_bool(info,query,'algebraic') # not the same as arithmetic....
    parse_bool(info,query,'self_dual')
    info['root_angle'] = parse_floats(info,query,'root_angle', allow_singletons=True)
    parse_ints(info,query,'order_of_vanishing')
    parse_noop(info,query,'central_character')
    parse_ints(info,query,'motivic_weight')
    parse_primes(info,query,'bad_primes',name="Primes dividing conductor", mode=info.get("prime_quantifier"), radical="conductor_radical")
    info['analytic_conductor'] = parse_floats(info,query,'analytic_conductor', allow_singletons=True)
    info['bigint_knowl'] = bigint_knowl

@search_wrap(template="LfunctionSearchResults.html",
             table=db.lfunc_search,
             postprocess=process_search,
             title="L-function search results",
             err_title="L-function search input error",
             url_for_label=url_for_lfunction,
             learnmore=learnmore_list,
             bread=lambda: get_bread(breads=[("Search results", " ")]),
             credit=lambda: credit_string)
def l_function_search(info, query):
    common_parse(info, query)

@search_wrap(template="LfunctionTraceSearchResults.html",
             table=db.lfunc_search,
             title="L-function search results",
             err_title="L-function search input error",
             postprocess=process_trace,
             learnmore=learnmore_list,
             bread=lambda: get_bread(breads=[("Search results", " ")]),
             credit=lambda: credit_string)
def trace_search(info, query):
    set_Trn(info, query)
    common_parse(info, query)
    process_an_constraints(info, query, qfield='dirichlet_coefficients', nshift=lambda n: n+1)

@search_wrap(template="LfunctionEulerSearchResults.html",
             table=db.lfunc_search,
             title="L-function search results",
             err_title="L-function search input error",
             postprocess=process_euler,
             learnmore=learnmore_list,
             bread=lambda: get_bread(breads=[("Search results", " ")]),
             credit=lambda: credit_string)
def euler_search(info, query):
    if 'n' not in info:
        info['n'] = '1-10'
    set_Trn(info, query)
    common_parse(info, query)
    d = query.get("degree")
    if not isinstance(d, (int, Integer)):
        print(d)
        raise RuntimeError("HELLO")
        raise ValueError("To search on Euler factors, you must specify one degree")
    def parse_poly(s):
        poly = coeff_to_poly(s)
        coeffs = list(poly)
        if len(coeffs) > d+1:
            raise ValueError("The degree of '%s' is larger than %s" % (s, d))
        return coeffs + [0]*(d+1-len(coeffs))
    def pi_wrap(p):
        p = ZZ(p)
        if not p.is_prime():
            raise ValueError("Euler factors only defined for primes, not %s" % p)
        return prime_pi(p)
    parse_equality_constraints(info, query, 'euler_constraints', qfield="euler_factors", prefix='E', parse_singleton=parse_poly, nshift=pi_wrap)

class LFunctionSearchArray(SearchArray):
    def __init__(self):
        z1 = TextBox(
            name="z1",
            knowl="lfunction.zeros",
            label="Lowest zero",
            example="9.22237",
            example_span="9.22237, 10-20")
        degree = TextBox(
            name="degree",
            knowl="lfunction.degree",
            label="Degree",
            example="2",
            example_span="2, 3-4")
        analytic_conductor = TextBox(
            name="analytic_conductor",
            knowl="lfunction.analytic_conductor",
            label="Analytic conductor",
            example="0.1-0.3")
        conductor = TextBox(
            name="conductor",
            knowl="lfunction.conductor",
            label="Conductor",
            example="37",
            example_span="37, 10-20")
        central_character = TextBox(
            name="central_character",
            knowl="lfunction.central_character",
            label="Central character",
            example="37.1")
        prime_quantifier = SubsetBox(
            name="prime_quantifier",
            min_width=110)
        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            knowl="lfunction.bad_prime",
            label=r"Bad \(p\)",
            example="2,3",
            select_box=prime_quantifier)
        primitive = YesNoBox(
            name="primitive",
            knowl="lfunction.primitive",
            label="Primitive",
            example_col=True)
        algebraic = YesNoBox(
            name="algebraic",
            knowl="lfunction.arithmetic",
            label="Arithmetic")
        self_dual = YesNoBox(
            name="self_dual",
            knowl="lfunction.self-dual",
            label="Self-dual")
        root_angle = TextBox(
            name="root_angle",
            knowl="lfunction.sign",
            label="Root angle",
            example="0.5",
            example_span="0.5, -0.1-0.1")
        analytic_rank = TextBox(
            name="order_of_vanishing",
            knowl="lfunction.analytic_rank",
            label="Analytic rank",
            example="2")
        motivic_weight = TextBox(
            name="motivic_weight",
            knowl="lfunction.motivic_weight",
            label="Motivic weight",
            example="2")
        count = CountBox()

        trace_coldisplay = TextBox(
            name='n',
            label='Columns to display',
            example='1-40',
            example_span='3,7,19, 40-90')

        euler_coldisplay = TextBox(
            name='n',
            label='Columns to display',
            example='2-11',
            example_span='3,7,19')

        trace_primality = SelectBox(
            name='n_primality',
            label='Show',
            options=[('', 'primes only'),
                     ('prime_powers', 'prime powers'),
                     ('all', 'all')])

        trace_an_constraints = TextBox(
            name='an_constraints',
            label='Trace constraints',
            example='a3=2,a5=0',
            example_span='a17=1, a8=0')

        euler_constraints = TextBox(
            name='euler_constraints',
            label='Euler factor constraints',
            example='E3=1-T,E5=1+T+5T^2')

        trace_an_moduli = TextBox(
            name='an_modulo',
            label='Modulo',
            example_span='5, 16')

        trace_view = SelectBox(
            name='view_modp',
            label='View',
            options=[('', 'integers'),
                     ('reductions', 'reductions')])

        self.browse_array = [
            [z1, degree],
            [conductor, analytic_conductor],
            [bad_primes, central_character],
            [analytic_rank, motivic_weight],
            [primitive, algebraic],
            [root_angle, self_dual],
            [count]
        ]

        self.refine_array = [
            [degree, conductor, analytic_conductor, analytic_rank, motivic_weight],
            [primitive, algebraic, self_dual, z1, root_angle],
            [bad_primes, central_character]
        ]

        self.traces_array = [
            RowSpacer(22),
            [trace_coldisplay, trace_primality],
            [trace_an_constraints, trace_an_moduli, trace_view]]

        self.euler_array = [
            RowSpacer(22),
            [euler_coldisplay],
            [euler_constraints]]

    def search_types(self, info):
        return self._search_again(
            info,
            [('', 'List of L-functions'),
             ('Traces', 'Traces table'),
             ('Euler', 'Euler factors'),
             ('Random', 'Random form')])

    def html(self, info=None):
        # We need to override html to add the trace and euler factor inputs
        layout = [self.hidden_inputs(info), self.main_table(info), self.buttons(info)]
        st = self._st(info)
        if st == "Traces":
            trace_table = self._print_table(self.traces_array, info, layout_type="box")
            layout.append(trace_table)
        elif st == "Euler":
            euler_table = self._print_table(self.euler_array, info, layout_type="box")
            layout.append(euler_table)
        return "\n".join(layout)

@l_function_page.route("/history")
def l_function_history():
    t = "A Brief History of L-functions"
    bc = get_bread(breads=[(t, url_for('.l_function_history'))])
    return render_template(_single_knowl, title=t, kid='lfunction.history', body_class='', bread=bc, learnmore=learnmore_list())

@l_function_page.route("/random")
def random_l_function():
    label = db.lfunc_search.random(projection="label")
    return redirect(url_for_lfunction(label), 307)

# Degree 1 L-functions browsing page ##############################################
@l_function_page.route("/degree1/")
def l_function_dirichlet_browse_page():
    info = {"bread": get_bread(1)}
    info["minModDefault"] = 1
    info["maxModDefault"] = 20
    info["maxOrder"] = 19
    info["learnmore"] = learnmore_list()
    info["contents"] = [LfunctionPlot.getOneGraphHtmlChar(info["minModDefault"], info[
                "maxModDefault"], 1, info["maxOrder"])]
    return render_template("Degree1.html", title='Degree 1 L-functions', **info)

# Degree 2 L-functions browsing page ##############################################
@l_function_page.route("/degree2/")
def l_function_degree2_browse_page():
    info = {"bread": get_bread(2)}
    info["learnmore"] = learnmore_list()
    return render_template("Degree2.html", title='Degree 2 L-functions', **info)

# Degree 3 L-functions browsing page ##############################################
@l_function_page.route("/degree3/")
def l_function_degree3_browse_page():
    info = {"bread": get_bread(3)}
    info["learnmore"] = learnmore_list()
    return render_template("Degree3.html", title='Degree 3 L-functions', **info)

# Degree 4 L-functions browsing page ##############################################
@l_function_page.route("/degree4/")
def l_function_degree4_browse_page():
    info = {"bread": get_bread(4)}
    info["learnmore"] = learnmore_list()
    return render_template("Degree4.html", title='Degree 4 L-functions', **info)


# Degree browsing page #########################################################
@l_function_page.route("/<degree>/")
def l_function_degree_page(degree):
    degree = get_degree(degree)
    if degree < 0:
        return abort(404)
    info = {"degree": degree}
    info["key"] = 777
    info["bread"] = get_bread(degree)
    info["learnmore"] = learnmore_list()
    return render_template("DegreeNavigateL.html", title='Degree ' + str(degree) + ' L-functions', **info)


# L-function of holomorphic cusp form browsing page ##############################################
@l_function_page.route("/<degree>/CuspForm/")
def l_function_cuspform_browse_page(degree):
    deg = get_degree(degree)
    if deg < 0:
        return abort(404)
    info = {"bread": get_bread(deg, [("Cusp form", url_for('.l_function_cuspform_browse_page', degree=degree))])}
    info["contents"] = [LfunctionPlot.getOneGraphHtmlHolo(0.501),LfunctionPlot.getOneGraphHtmlHolo(1)]
    return render_template("cuspformGL2.html", title=r'L-functions of cusp forms on \(\Gamma_1(N)\)', **info)


# L-function of GL(2) maass forms browsing page ##############################################
@l_function_page.route("/degree2/MaassForm/")
def l_function_maass_browse_page():
    info = {"bread": get_bread(2, [("Maass form", url_for('.l_function_maass_browse_page'))])}
    info["learnmore"] = learnmore_list()
    info["contents"] = [paintSvgMaass(1, 10, 0, 10, L="/L")]
    info["colorminus1"] = rgbtohex(signtocolour(-1))
    info["colorplus1"] = rgbtohex(signtocolour(1))
    return render_template("MaassformGL2.html", title='L-functions of GL(2) Maass forms of weight 0', **info)


# L-function of elliptic curves browsing page ##############################################
@l_function_page.route("/degree2/EllipticCurve/")
def l_function_ec_browse_page():
    info = {"bread": get_bread(2, [("Elliptic curve", url_for('.l_function_ec_browse_page'))])}
    info["representation"] = ''
    info["learnmore"] = learnmore_list()
    info["contents"] = [processEllipticCurveNavigation(11, 200)]
    return render_template("ellipticcurve.html", title='L-functions of elliptic curves', **info)


# L-function of GL(n) Maass forms browsing page ##############################################
@l_function_page.route("/<degree>/MaassForm/")
def l_function_maass_gln_browse_page(degree):
    degree = get_degree(degree)
    if degree < 0:
        return abort(404)
    contents = LfunctionPlot.getAllMaassGraphHtml(degree)
    if not contents:
        return abort(404)
    info = {"bread": get_bread(degree, [("Maass form", url_for('.l_function_maass_gln_browse_page',
                                                              degree='degree' + str(degree)))])}
    info["contents"] = contents
    info["learnmore"] = learnmore_list()
    return render_template("MaassformGLn.html",
                           title='L-functions of GL(%s) Maass forms' % degree, **info)


# L-function of symmetric square of elliptic curves browsing page ##############
@l_function_page.route("/degree3/EllipticCurve/SymmetricSquare/")
def l_function_ec_sym2_browse_page():
    info = {"bread": get_bread(3, [("Symmetric square of elliptic curve",
                                    url_for('.l_function_ec_sym2_browse_page'))])}
    info["representation"] = 'Symmetric square'
    info["learnmore"] = learnmore_list()
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 26, 2)]
    return render_template("ellipticcurve.html",
                           title='Symmetric square L-functions of elliptic curves', **info)


# L-function of symmetric cube of elliptic curves browsing page ################
@l_function_page.route("/degree4/EllipticCurve/SymmetricCube/")
def l_function_ec_sym3_browse_page():
    info = {"bread": get_bread(4, [("Symmetric cube of elliptic curve", url_for('.l_function_ec_sym3_browse_page'))])}
    info["representation"] = 'Symmetric cube'
    info["learnmore"] = learnmore_list()
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 17, 3)]
    return render_template("ellipticcurve.html",
                           title='Symmetric cube L-functions of elliptic curves', **info)

# L-function of genus 2 curves browsing page ##############################################
@l_function_page.route("/degree4/Genus2Curve/")
def l_function_genus2_browse_page():
    info = {"bread": get_bread(4, [("Genus 2 curve", url_for('.l_function_genus2_browse_page'))])}
    info["representation"] = ''
    info["learnmore"] = learnmore_list()
    info["contents"] = [processGenus2CurveNavigation(169, 1000)]
    return render_template("genus2curve.html", title='L-functions of genus 2 curves', **info)

# generic/pure L-function browsing page ##############################################
@l_function_page.route("/<degree>/<gammasignature>/")
# def l_function_maass_gln_browse_page(degree):
def l_function_browse_page(degree, gammasignature):
    degree = get_degree(degree)
    nice_gammasignature = parse_codename(gammasignature)
    if degree < 0:
        return abort(404)
    contents = LfunctionPlot.getAllMaassGraphHtml(degree, gammasignature)
    if not contents:
        return abort(404)
    info = {"bread": get_bread(degree, [(gammasignature, url_for('.l_function_browse_page',
                                            degree='degree' + str(degree), gammasignature=gammasignature))])}
    info["contents"] = contents
    info["learnmore"] = learnmore_list()
    return render_template("MaassformGLn.html",
                           title='L-functions of degree %s and signature %s' % (degree, nice_gammasignature), **info)

################################################################################
#   Route functions, individual L-function homepages
################################################################################
# Riemann zeta function ########################################################
@l_function_page.route("/Riemann/")
def l_function_riemann_page():
    args = {}
    return render_single_Lfunction(RiemannZeta, args, request)


@l_function_page.route("/ArtinRepresentation/1.1.1t1.1c1")
@l_function_page.route("/Character/Dirichlet/1/1/")
@l_function_page.route("/NumberField/1.1.1.1/")
def l_function_riemann_redirect():
    return redirect(url_for('.l_function_riemann_page'), code=301)

from functools import wraps
def label_redirect_wrapper(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        url = url_for('.' + f.__name__, **kwds)[3:].rstrip('/')
        if 'Maass' in url:
            url += '/'
        label = db.lfunc_instances.lucky({'url': url}, 'label')
        if label:
            return redirect(url_for_lfunction(label))
        return f(*args, **kwds)
    return wrapper


# L-function of Dirichlet character ############################################
@l_function_page.route("/Character/Dirichlet/<modulus>/<number>/")
@label_redirect_wrapper
def l_function_dirichlet_page(modulus, number):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    return abort(404, "L-function for dirichlet character with label %s.%s not found" % (modulus,number))


# L-function of Elliptic curve #################################################
# Over QQ
@l_function_page.route("/EllipticCurve/Q/<conductor_label>/<isogeny_class_label>/")
@label_redirect_wrapper
def l_function_ec_page(conductor_label, isogeny_class_label):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    label = '.'.join(map(str, [conductor_label, isogeny_class_label]))
    return abort(404, "L-function for elliptic curve isogeny class with label %s not found" % label)


##FIXME, do we need to support this route?
#@l_function_page.route("/EllipticCurve/Q/<label>/")
#def l_function_ec_page_label(label):
#    conductor, isogeny = getConductorIsogenyFromLabel(label)
#    if conductor and isogeny:
#        return redirect(url_for('.l_function_ec_page', conductor_label = conductor,
#                                      isogeny_class_label = isogeny), 301)
#    else:
#        errmsg = 'The string %s is not an admissible elliptic curve label' % label
#        return render_lfunction_exception(errmsg)

# over a number field
@l_function_page.route("/EllipticCurve/<field_label>/<conductor_label>/<isogeny_class_label>/")
@label_redirect_wrapper
def l_function_ecnf_page(field_label, conductor_label, isogeny_class_label):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    label = '-'.join(map(str, [field_label, conductor_label, isogeny_class_label]))
    return abort(404, "L-function for elliptic curve isogeny class with label %s not found" % label)


# L-function of Cusp form ############################################



@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/<int:character>/<int:number>/")
@label_redirect_wrapper
def l_function_cmf_page(level, weight, char_orbit_label, hecke_orbit, character, number):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    # thus it must be an old label, and we redirect to the orbit
    old_label = '.'.join(map(str, [level, weight, character, hecke_orbit]))
    newform_label = convert_newformlabel_from_conrey(old_label)
    level, weight, char_orbit_label, hecke_orbit = newform_label.split('.')
    return redirect(url_for('.l_function_cmf_orbit', level=level, weight=weight,
                              char_orbit_label=char_orbit_label, hecke_orbit=hecke_orbit), code=301)

@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/<hecke_orbit>/<int:number>/")
def l_function_cmf_old(level, weight, character, hecke_orbit, number):
    char_orbit_label = db.mf_newspaces.lucky({'conrey_indexes': {'$contains': character}, 'level': level, 'weight': weight}, projection='char_orbit_label')
    if char_orbit_label is None:
        return abort(404, 'Invalid character label')
    number += 1 # There was a shift from 0-based to 1-based in the new label scheme
    return redirect(url_for('.l_function_cmf_page',
                                    level=level,
                                    weight=weight,
                                    char_orbit_label=char_orbit_label,
                                    character=character,
                                    hecke_orbit=hecke_orbit,
                                    number=number),
                                    code=301)



@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/<hecke_orbit>/")
def l_function_cmf_redirect_1(level, weight, character, hecke_orbit):
    char_orbit_label = db.mf_newspaces.lucky({'conrey_indexes': {'$contains': character}, 'level': level, 'weight': weight}, projection='char_orbit_label')
    return redirect(url_for('.l_function_cmf_page',
                                    level=level,
                                    weight=weight,
                                    char_orbit_label=char_orbit_label,
                                    character=character,
                                    hecke_orbit=hecke_orbit,
                                    number=1),
                                    code=301)

@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<char_orbit_label>/<hecke_orbit>/")
@label_redirect_wrapper
def l_function_cmf_orbit(level, weight, char_orbit_label, hecke_orbit):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    label = '.'.join(map(str, [level, weight, char_orbit_label, hecke_orbit]))
    return abort(404, "L-function for classical modular form with label %s not found" % label)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<int:character>/")
def l_function_cmf_redirect_a1(level, weight, character):
    char_orbit_label = db.mf_newspaces.lucky({'conrey_indexes': {'$contains': character}, 'level': level, 'weight': weight}, projection='char_orbit_label')
    return redirect(url_for('.l_function_cmf_page',
                                    level=level,
                                    weight=weight,
                                    char_orbit_label=char_orbit_label,
                                    character=character,
                                    hecke_orbit='a',
                                    number=1),
                                    code=301)

@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/<char_orbit_label>/")
def l_function_cmf_orbit_redirecit_a(level, weight, char_orbit_label):
    return redirect(url_for('.l_function_cmf_orbit', level=level, weight=weight,
                                  char_orbit_label=char_orbit_label, hecke_orbit="a", ), code=301)

@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<int:level>/<int:weight>/")
def l_function_cmf_orbit_redirecit_aa(level, weight):
    return redirect(url_for('.l_function_cmf_orbit', level=level, weight=weight,
                                  char_orbit_label='a', hecke_orbit="a", ), code=301)


# L-function of Bianchi modular form ###########################################
@l_function_page.route("/ModularForm/GL2/ImaginaryQuadratic/<field>/<level>/<suffix>/")
@label_redirect_wrapper
def l_function_bmf_page(field, level, suffix):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    label = '-'.join(map(str, [field, level, suffix]))
    return abort(404, "L-function for Bianchi modular form with label %s not found" % label)


# L-function of Hilbert modular form ###########################################
@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/<character>/<number>/")
def l_function_hmf_page(field, label, character, number):
    #FIXME this feels so wrong...
    if (not character and not number) or (character == '0' and number == '0'):
        url = "ModularForm/GL2/TotallyReal/" + label.split("-")[0] + "/holomorphic/" + label
        lfun_label = db.lfunc_instances.lucky({'url': url}, 'label')
        if lfun_label:
            return redirect(url_for_lfunction(lfun_label))

    args = {'field': field, 'label': label, 'character': character, 'number': number}
    return render_single_Lfunction(Lfunction_HMF, args, request)


@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/<character>/")
def l_function_hmf_redirect_1(field, label, character):
    return redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character=character, number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/")
@label_redirect_wrapper
def l_function_hmf_redirect_2(field, label):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    return redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character='0', number='0'), code=301)


# L-function of GL(2) Maass form ###############################################
@l_function_page.route("/ModularForm/GL2/Q/Maass/<maass_id>/")
def l_function_maass_page(maass_id):
    args = {'maass_id': maass_id, 'fromDB': False}
    return render_single_Lfunction(Lfunction_Maass, args, request)


# L-function of GL(n) Maass form (n>2) #########################################
@l_function_page.route("/ModularForm/<group>/Q/Maass/<level>/<char>/<R>/<ap_id>/")
@label_redirect_wrapper
def l_function_maass_gln_page(group, level, char, R, ap_id):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    maass_id = "ModularForm/%s/Q/Maass/%s/%s/%s/%s/" % (group, level, char, R, ap_id)
    return abort(404, '"L-function for modular form %s not found' % maass_id)
    #HERE


# L-function of Siegel modular form    #########################################
@l_function_page.route("/ModularForm/GSp/Q/Sp4Z/specimen/<weight>/<orbit>/<number>/")
def l_function_siegel_specimen_page(weight, orbit, number):
    return redirect(url_for('.l_function_siegel_page', weight=weight, orbit=orbit, number=number),301)

@l_function_page.route("/ModularForm/GSp/Q/Sp4Z/<weight>/<orbit>/<number>/")
def l_function_siegel_page(weight, orbit, number):
    args = {'weight': weight, 'orbit': orbit, 'number': number}
    return render_single_Lfunction(Lfunction_SMF2_scalar_valued, args, request)


# L-function of Number field    ################################################
@l_function_page.route("/NumberField/<label>/")
def l_function_nf_page(label):
    return render_single_Lfunction(DedekindZeta, {'label': label}, request)


# L-function of Artin representation    ########################################
@l_function_page.route("/ArtinRepresentation/<label>/")
@label_redirect_wrapper
def l_function_artin_page(label):
    newlabel = parse_artin_label(label, safe=True)
    if newlabel != label:
        return redirect(url_for(".l_function_artin_page", label=newlabel), 301)
    # if it passed the label_redirect_wrapper, then the url is not in the database
    return render_single_Lfunction(ArtinLfunction, {'label': label}, request)

# L-function of hypergeometric motive   ########################################
@l_function_page.route("/Motive/Hypergeometric/Q/<label>/<t>")
def l_function_hgm_page(label,t):
    args = {'label': label+'_'+t}
    return render_single_Lfunction(HypergeometricMotiveLfunction, args, request)

# L-function of symmetric powers of Elliptic curve #############################
@l_function_page.route("/SymmetricPower/<int:power>/EllipticCurve/Q/<int:conductor>/<isogeny>/")
def l_function_ec_sym_page(power, conductor, isogeny):
    args = {'power': power, 'underlying_type': 'EllipticCurve', 'field': 'Q',
            'conductor': conductor, 'isogeny': isogeny}
    return render_single_Lfunction(SymmetricPowerLfunction, args, request)

@l_function_page.route("/SymmetricPower/<int:power>/EllipticCurve/Q/<label>/")
def l_function_ec_sym_page_label(power, label):
    conductor, isogeny = getConductorIsogenyFromLabel(label)
    if conductor and isogeny:
        return redirect(url_for('.l_function_ec_sym_page', conductor = conductor,
                                      isogeny = isogeny, power = power), 301)
    else:
        errmsg = 'The string %s is not an admissible elliptic curve label' % label
        return render_lfunction_exception(errmsg)

# L-function of genus 2 curve/Q ########################################
@l_function_page.route("/Genus2Curve/Q/<cond>/<x>/")
@label_redirect_wrapper
def l_function_genus2_page(cond,x):
    # if it passed the label_redirect_wrapper, then the url is not in the database
    label = '.'.join(map(str, [cond, x]))
    return abort(404, "L-function for genus 2 curve with label %s not found" % label)

# L-function by hash ###########################################################
@l_function_page.route("/lhash/<lhash>")
@l_function_page.route("/lhash/<lhash>/")
@l_function_page.route("/Lhash/<lhash>")
@l_function_page.route("/Lhash/<lhash>/")
def l_function_by_hash_page(lhash):
    args = {'Lhash': lhash}
    return render_single_Lfunction(Lfunction_from_db, args, request)

#by trace_hash
@l_function_page.route("/tracehash/<int:trace_hash>")
@l_function_page.route("/tracehash/<int:trace_hash>/")
def l_function_by_trace_hash_page(trace_hash):
    if trace_hash > 2**61 or trace_hash < 0:
        errmsg = r'trace_hash = %s not in [0, 2^61]' % trace_hash
        return render_lfunction_exception(errmsg)

    lhash = db.lfunc_lfunctions.lucky({'trace_hash': trace_hash}, projection = "Lhash")
    if lhash is None:
        errmsg = 'Did not find an L-function with trace_hash = %s' % trace_hash
        return render_lfunction_exception(errmsg)
    return redirect(url_for('.l_function_by_hash_page', lhash = lhash), 301)


################################################################################
#   Helper functions, individual L-function homepages
################################################################################

def render_single_Lfunction(Lclass, args, request):
    temp_args = to_dict(request.args)
    try:
        L = Lclass(**args)
        # if you move L=Lclass outside the try for debugging, remember to put it back in before committing
    except (ValueError, KeyError, TypeError) as err:  # do not trap all errors, if there is an assert error we want to see it in flasklog
        if is_debug_mode():
            raise
        else:
            return render_lfunction_exception(err)

    info = initLfunction(L, temp_args, request)
    return render_template('Lfunction.html', **info)

def render_lfunction_exception(err):
    try:
        errmsg = "Unable to render L-function page due to the following problem(s):<br><ul>" + "".join("<li>" + msg + "</li>" for msg in err.args) + "</ul>"
    except:
        errmsg = "Unable to render L-function page due to the following problem:<br><ul><li>%s</li></ul>"%err
    bread =  [('L-functions', url_for('.index')), ('Error', '')]
    info = {'explain': errmsg, 'title': 'Error displaying L-function', 'bread': bread }
    return render_template('problem.html', **info)

def initLfunction(L, args, request):
    ''' Sets the properties to show on the homepage of an L-function page.
    '''
    info = L.info
    info['args'] = args
    info['properties'] = set_gaga_properties(L)

    set_bread_and_friends(info, L, request)

    info['learnmore'] = learnmore_list(request.path)

    (info['zeroslink'], info['plotlink']) = set_zeroslink_and_plotlink(L, args)
    # info['navi']= set_navi(L)

    return info


def set_gaga_properties(L):
    ''' Sets the properties in the properties box in the
    upper right corner
    '''
    ans = []
    if hasattr(L, 'label'):
        ans.append(('Label', L.label))
    ans.append(('Degree', prop_int_pretty(L.degree)))

    ans.append(('Conductor', prop_int_pretty(L.level)))
    ans.append(('Sign', "$%s$" % styleTheSign(L.sign) ))

    if L.algebraic:
        ans.append(('Motivic weight', prop_int_pretty(L.motivic_weight)))


    primitive =  getattr(L, 'primitive', None)
    if primitive is not None:
        txt = 'yes' if primitive else 'no'
        ans.append(('Primitive', txt))

    txt = 'yes' if L.selfdual else 'no'
    ans.append(('Self-dual', txt))

    rank = getattr(L, 'order_of_vanishing', None)
    if rank is not None:
        ans.append(('Analytic rank', prop_int_pretty(rank)))

    return ans


def set_bread_and_friends(info, L, request):
    """
    Populates the info dictionary with:
        - bread -- bread crumbs on top
        - origins -- objects the give rise to this L-functions, shows as "Origins"
        - friends -- dual L-fcn and other objects that this L-fcn divides, shows as related objects
        - factors_origins -- objects that give rise to the factors of this L-fcn, shows as "Origins of factors"
        - Linstances -- displays the instances that give rise to this Lhash, only shows up through the Lhash route
        - downloads -- download links
    Returns the list of friends to link to and the bread crumbs.
    Depends on the type of L-function and needs to be added to for new types
    """

    # bread crums on top
    info['bread'] = []
    info['origins'] = []
    info['friends'] = []
    info['factors_origins'] = []
    info['Linstances'] = []
    info['downloads'] = []

    # Create default friendlink by removing 'L/' and ending '/'
    friendlink = request.path.replace('/L/', '/').replace('/L-function/', '/').replace('/Lfunction/', '/')
    splitlink = friendlink.rpartition('/')
    friendlink = splitlink[0] + splitlink[2]

    if L.Ltype() == 'riemann':
        info['friends'] = [(r'\(\mathbb Q\)', url_for('number_fields.by_label', label='1.1.1.1')),
                           (r'Dirichlet character \(\chi_{1}(1,\cdot)\)',url_for('characters.render_Dirichletwebpage',
                                                                                  modulus=1, number=1)),
                           ('Artin representation 1.1.1t1.1c1', url_for('artin_representations.render_artin_representation_webpage',label='1.1.1t1.1c1'))]
        info['bread'] = get_bread(1, [('Riemann Zeta', request.path)])

    elif L.Ltype() == 'dirichlet':
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        charname = WebDirichlet.char2tex(smod, snum)
        info['friends'] = [('Dirichlet character ' + str(charname), friendlink)]
        if L.fromDB and not L.selfdual:
            info['friends'].append(('Dual L-function', L.dual_link))
        info['bread'] = get_bread(1, [(charname, request.path)])

    elif isinstance(L, Lfunction_from_db):
        info['bread'] = L.bread + [(L.label, request.path)]
        info['origins'] = L.origins
        info['friends'] = L.friends
        info['factors_origins'] = L.factors_origins
        info['Linstances'] = L.instances
        info['downloads'] = L.downloads

        for elt in [info['origins'], info['friends'], info['factors_origins'], info['Linstances']]:
            if elt is not None:
                elt.sort(key=lambda x: key_for_numerically_sort(x[0]))

    elif L.Ltype() == 'maass':
        if L.group == 'GL2':
            info['friends'] = [('Maass form ', friendlink)]
            info['bread'] = get_bread(2, [('Maass form',
                                           url_for('.l_function_maass_browse_page')),
                                          (r'\(' + L.texname + r'\)', request.path)])

        else:
            if L.fromDB and not L.selfdual:
                info['friends'] = [('Dual L-function', L.dual_link)]

            info['bread'] = get_bread(L.degree,
                                      [(L.maass_id.partition('/')[2], request.path)])

    elif L.Ltype() == 'hilbertmodularform':
        friendlink = '/'.join(friendlink.split('/')[:-1])
        info['friends'] = [('Hilbert modular form ' + L.origin_label, friendlink.rpartition('/')[0])]
        if L.degree == 4:
            info['bread'] = get_bread(4, [(L.origin_label, request.path)])
        else:
            info['bread'] = [('L-functions', url_for('.index'))]

    elif (L.Ltype() == 'siegelnonlift' or L.Ltype() == 'siegeleisenstein' or
          L.Ltype() == 'siegelklingeneisenstein' or L.Ltype() == 'siegelmaasslift'):
        weight = str(L.weight)
        label = 'Sp4Z.' + weight + '_' + L.orbit
        friendlink = '/'.join(friendlink.split('/')[:-3]) + '.' + weight + '_' + L.orbit
        info['friends'] = [('Siegel modular form ' + label, friendlink)]
        if L.degree == 4:
            info['bread'] = get_bread(4, [(label, request.path)])
        else:
            info['bread'] = [('L-functions', url_for('.index'))]

    elif L.Ltype() == 'dedekindzeta':
        info['friends'] = [('Number field', friendlink)]
        if L.degree <= 4:
            info['bread'] = get_bread(L.degree, [(L.origin_label, request.path)])
        else:
            info['bread'] = [('L-functions', url_for('.index'))]

    elif L.Ltype() == "artin":
        info['friends'] = [('Artin representation', L.artin.url_for())]
        if L.degree <= 4:
            info['bread'] = get_bread(L.degree, [(L.origin_label, request.path)])
        else:
            info['bread'] = [('L-functions', url_for('.index'))]

    elif L.Ltype() == "hgmQ":
        # The /L/ trick breaks down for motives,
        # because we have a scheme for the L-functions themselves
        newlink = friendlink.rpartition('t')
        friendlink = newlink[0]+'/t'+newlink[2]
        info['friends'] = [('Hypergeometric motive ', friendlink)]
        if L.degree <= 4:
            info['bread'] = get_bread(L.degree, [(L.origin_label, request.path)])
        else:
            info['bread'] = [('L-functions', url_for('.index'))]


    elif L.Ltype() == 'SymmetricPower':
        def ordinal(n):
            if n == 2:
                return "Square"
            elif n == 3:
                return "Cube"
            elif 10 <= n % 100 < 20:
                return str(n) + "th Power"
            else:
                return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, "th") + " Power"

        if L.m == 2:
            info['bread'] = get_bread(3, [("Symmetric square of elliptic curve",
                                           url_for('.l_function_ec_sym2_browse_page')),
                                          (L.origin_label, url_for('.l_function_ec_sym_page_label',
                                                            label=L.origin_label,power=L.m))])
        elif L.m == 3:
            info['bread'] = get_bread(4, [("Symmetric cube of elliptic curve",
                                           url_for('.l_function_ec_sym3_browse_page')),
                                          (L.origin_label, url_for('.l_function_ec_sym_page_label',
                                                            label=L.origin_label,power=L.m))])
        else:
            info['bread'] = [('L-functions', url_for('.index')),
                             ('Symmetric %s of Elliptic curve ' % ordinal(L.m)
                              + str(L.origin_label),
                              url_for('.l_function_ec_sym_page_label',
                                      label=L.origin_label,power=L.m))]

        friendlink = request.path.replace('/L/SymmetricPower/%d/' % L.m, '/')
        splitlink = friendlink.rpartition('/')
        friendlink = splitlink[0] + splitlink[2]

        friendlink2 = request.path.replace('/L/SymmetricPower/%d/' % L.m, '/L/')
        splitlink = friendlink2.rpartition('/')
        friendlink2 = splitlink[0] + splitlink[2]

        info['friends'] = [('Isogeny class ' + L.origin_label, friendlink), ('Symmetric 1st Power', friendlink2)]
        for j in range(2, L.m + 2):
            if j != L.m:
                friendlink3 = request.path.replace('/L/SymmetricPower/%d/' % L.m, '/L/SymmetricPower/%d/' % j)
                info['friends'].append(('Symmetric %s' % ordinal(j), friendlink3))


def set_zeroslink_and_plotlink(L, args):
    ''' Returns the url for the zeros and the plot.
    Turning off either of them could be done here
    '''
    # AVS 07/10/2016
    # only set zeroslink and plot if we actually have the ability to determine zeros and plot the Z function
    # this could either be because we already know them (in which case lfunc_data is set), or we can compute them via sageLfunction)
    # in the former case there is really no reason to use zeroslink at all, we could just fill them in now
    # but keep it as is for the moment for backward compatibility
    # Lemurell 13/06/2017
    # The zeros are now filled in for those in the Lfunctions database, but this is kept for the moment
    if hasattr(L,'lfunc_data') or (hasattr(L,'sageLfunction') and L.sageLfunction):
        zeroslink = request.path.replace('/L/', '/L/Zeros/')
        plotlink = request.path.replace('/L/', '/L/Plot/')
    else:
        zeroslink = ''
        plotlink = ''
    return (zeroslink, plotlink)


def set_navi(L):
    ''' Returns the data for navigation to previous/next
    L-function when this makes sense. If not it returns None
    '''
    prev_data = None
    if L.Ltype() == 'maass' and L.group == 'GL2':
        next_form_id = L.mf.next_maass_form()
        if next_form_id:
            next_data = ("next",r"$L(s,f_{\text next})$", '/L' +
                         url_for('maass.by_label',
                         label = next_form_id) )
        else:
            next_data = ('','','')
        prev_form_id = L.mf.prev_maass_form()
        if prev_form_id:
            prev_data = ("previous", r"$L(s,f_{\text prev}$)", '/L' +
                         url_for('maass.by_lavel',
                         label = prev_form_id) )
        else:
            prev_data = ('','','')

    elif L.Ltype() == 'dirichlet':
        mod, num = L.charactermodulus, L.characternumber
        Lpattern = r"\(L(s,\chi_{%s}(%s,&middot;))\)"
        if mod > 1:
            pmod,pnum = WebDirichlet.prevprimchar(mod, num)
            prev_data = ("previous",Lpattern%(pmod,pnum) if pmod > 1 else r"\(\zeta(s)\)",
                     url_for('.l_function_dirichlet_page',
                             modulus=pmod,number=pnum))
        else:
            prev_data = ('','','')
        nmod,nnum = WebDirichlet.nextprimchar(mod, num)
        next_data = ("next",Lpattern%(nmod,nnum) if nmod > 1 else r"\(\zeta(s)\)",
                 url_for('.l_function_dirichlet_page',
                         modulus=nmod,number=nnum))

    if prev_data is None:
        return None
    else:
        return ( prev_data, next_data )


def generateLfunctionFromUrl(*args, **kwds):
    ''' Returns the L-function object corresponding to the supplied argumnents
    from the url. kwds contains possible arguments after a question mark.
    '''
    try:
        deg = int(args[0])
        assert deg
        return Lfunction_from_db(label='-'.join(map(str, args)))
    except ValueError:
        pass

    # we only need to consider on the fly L-functions
    if args[0] == 'Riemann':
        return RiemannZeta()
    elif args[0] == 'ModularForm' and args[1] == 'GL2' and args[2] == 'TotallyReal' and args[4] == 'holomorphic':  # Hilbert modular form
        return Lfunction_HMF(label=args[5], character=args[6], number=args[7])

    elif args[0] == 'ModularForm' and args[1] == 'GL2' and args[2] == 'Q' and args[3] == 'Maass':
        maass_id = args[4]
        return Lfunction_Maass(maass_id = maass_id, fromDB = False)

    elif args[0] == 'ModularForm' and (args[1] == 'GSp4' or args[1] == 'GL4' or args[1] == 'GL3') and args[2] == 'Q' and args[3] == 'Maass':
        return Lfunction_Maass(fromDB = True, group = args[1], level = args[4],
                char = args[5], R = args[6], ap_id = args[7])

    elif args[0] == 'ModularForm' and args[1] == 'GSp' and args[2] == 'Q' and args[3] == 'Sp4Z':
        return Lfunction_SMF2_scalar_valued(weight=args[4], orbit=args[5], number=args[6])

    elif args[0] == 'NumberField':
        return DedekindZeta(label=str(args[1]))

    elif args[0] == "ArtinRepresentation":
        label = args[1]
        label = parse_artin_label(label, safe=True)
        return ArtinLfunction(label=label)

    elif args[0] == "SymmetricPower":
        return SymmetricPowerLfunction(power=args[1], underlying_type=args[2], field=args[3],
                                       conductor=args[4], isogeny = args[5])

    elif args[0] == "Motive" and args[1] == "Hypergeometric" and args[2] == "Q":
        if args[4]:
            return HypergeometricMotiveLfunction(family = args[3], t = args[4])
        else:
            return HypergeometricMotiveLfunction(label = args[3])
    elif args[0] in ['lhash', 'Lhash']:
        return Lfunction_from_db(Lhash=str(args[1]))

    elif is_debug_mode():
        raise Exception
    else:
        return None

################################################################################
#   Route functions, plotting L-function and displaying zeros
################################################################################

# L-function of Elliptic curve #################################################
@l_function_page.route("/Plot/EllipticCurve/Q/<label>/")
def l_function_ec_plot(label):
    return render_plotLfunction(request, 'EllipticCurve', 'Q', label, None, None, None,
                                    None, None, None)

@l_function_page.route("/Plot/<path:args>/")
def plotLfunction(args):
    args = tuple(args.split('/'))
    return render_plotLfunction(request, *args)


@l_function_page.route("/Zeros/<path:args>/")
def zerosLfunction(args):
    args = tuple(args.split('/'))
    return render_zerosLfunction(request, *args)

@l_function_page.route("/download_euler/<path:args>/")
def download_euler(args):
    args = tuple(args.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    return L.download_euler_factors()

@l_function_page.route("/download_zeros/<path:args>/")
def download_zeros(args):
    args = tuple(args.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    return L.download_zeros()

@l_function_page.route("/download_dirichlet_coeff/<path:args>/")
def download_dirichlet_coeff(args):
    args = tuple(args.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    return L.download_dirichlet_coeff()

@l_function_page.route("/download/<path:args>/")
def download(args):
    args = tuple(args.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    return L.download()


################################################################################
#   Render functions, plotting L-function and displaying zeros
################################################################################


def render_plotLfunction(request, *args):
    try:
        data = getLfunctionPlot(request, *args)
    except Exception as err: # depending on the arguments, we may get an exception or we may get a null return, we need to handle both cases
        raise
        if not is_debug_mode():
            return render_lfunction_exception(err)
    if not data:
        # see note about missing "hardy_z_function" in plotLfunction()
        return abort(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response


def getLfunctionPlot(request, *args):
    try:
        pythonL = generateLfunctionFromUrl(*args, **to_dict(request.args))
        assert pythonL
    except:
        return ""

    plotrange = 30
    if hasattr(pythonL, 'plotpoints'):
        F = p2sage(pythonL.plotpoints)
        #  F[0][0] is the lowest t-coordinated that we have a value for L
        #  F[-1][0] is the highest t-coordinated that we have a value for L
        plotrange = min(plotrange, -F[0][0], F[-1][0])
        # aim to display at most 25 axis crossings
        # if the L-function is nonprimitive
        if (hasattr(pythonL, 'positive_zeros') and
            hasattr(pythonL, 'primitive') and
            not pythonL.primitive):
            # we stored them ready to display
            zeros = [float(z) for z in pythonL.positive_zeros.split(",")]
            if len(zeros) >= 25:
                zero_range = zeros[24]
            else:
                zero_range = zeros[-1]*25/len(zeros)
            zero_range *= 1.2
            plotrange = min(plotrange, zero_range)
    else:
    # obsolete, because lfunc_data comes from DB?
        L = pythonL.sageLfunction
        if not hasattr(L, "hardy_z_function"):
            return None
        plotStep = .1
        if pythonL._Ltype not in ["riemann", "maass"]:
            plotrange = 12
        F = [(i, L.hardy_z_function(i).real()) for i in srange(-1*plotrange, plotrange, plotStep)]

    interpolation = spline(F)
    F_interp = [(i, interpolation(i)) for i in srange(-1*plotrange, plotrange, 0.05)]
    p = line(F_interp)

    styleLfunctionPlot(p, 10)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fn:
        p.save(filename=fn.name)
    with open(fn.name, 'rb') as f:
        data = f.read()
    os.remove(fn.name)
    return data


def styleLfunctionPlot(p, fontsize):
    p.fontsize(fontsize)
    p.axes_color((0.5, 0.5, 0.5))
    p.tick_label_color((0.5, 0.5, 0.5))
    p.axes_width(0.2)


def render_zerosLfunction(request, *args):
    ''' Renders the first few zeros of the L-function with the given arguments.
    '''
    try:
        L = generateLfunctionFromUrl(*args, **to_dict(request.args))
    except Exception as err:
        return render_lfunction_exception(err)

    if not L:
        return abort(404)
    if hasattr(L,"lfunc_data"):
        if L.lfunc_data is None:
            return "<span>" + L.zeros + "</span>"
        else:
            website_zeros = L.negative_zeros + L.positive_zeros
    else:
        # This depends on mathematical information, all below is formatting
        # More semantic this way
        # Allow 10 seconds
        website_zeros = L.compute_web_zeros(time_allowed = 10)

    # Handle cases where zeros are not available
    if isinstance(website_zeros, string_types):
        return website_zeros

    positiveZeros = []
    negativeZeros = []

    for zero in website_zeros:
        if abs(float(zero)) < 1e-10:
            zero = "0"
        else:
            zero = display_float(zero, 12, 'round')
        if float(zero) < 0:
            negativeZeros.append(zero)
        else:
            positiveZeros.append(zero)

    zero_truncation = 25   # show at most 25 positive and negative zeros
                           # later: implement "show more"
    negativeZeros = negativeZeros[-1*zero_truncation:]
    positiveZeros = positiveZeros[:zero_truncation]
    # Format the html string to render
    positiveZeros = ", ".join(positiveZeros)
    negativeZeros = ", ".join(negativeZeros)
    if len(positiveZeros) > 2 and len(negativeZeros) > 2:  # Add comma and empty space between negative and positive
        negativeZeros = negativeZeros + ", "

    return "<span class='redhighlight'>{0}</span><span class='positivezero'>{1}</span>".format(
     #   negativeZeros[1:len(negativeZeros) - 1], positiveZeros[1:len(positiveZeros) - 1])
        negativeZeros.replace("-","&minus;"), positiveZeros)

################################################################################
#   Route functions, graphs for browsing L-functions
################################################################################
@l_function_page.route("/browseGraph/")
def browseGraph():
    return render_browseGraph(request.args)


@l_function_page.route("/browseGraphTMP/")
def browseGraphTMP():
    return render_browseGraphTMP(request.args)


@l_function_page.route("/browseGraphHolo/")
def browseGraphHolo():
    return render_browseGraphHolo(request.args)


@l_function_page.route("/browseGraphHoloNew/")
def browseGraphHoloNew():
    return render_browseGraphHoloNew(request.args)

@l_function_page.route("/browseGraphChar/")
def browseGraphChar():
    return render_browseGraphChar(request.args)


###########################################################################
#   Functions for rendering graphs for browsing L-functions.
###########################################################################
def render_browseGraph(args):
    data = LfunctionPlot.paintSvgFileAll([[args['group'],
                                           int(args['level'])]])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


def render_browseGraphHolo(args):
    data = LfunctionPlot.paintSvgHolo(args['Nmin'], args['Nmax'], args['kmin'], args['kmax'])
    response = make_response((data,200,{'Content-type':'image/svg+xml'}))
    return response


def render_browseGraphHoloNew(args):
    data = LfunctionPlot.paintSvgHoloNew(args['condmax'])
    response = make_response((data,200,{'Content-type':'image/svg+xml'}))
    return response


def render_browseGraphTMP(args):
    data = LfunctionPlot.paintSvgHoloGeneral(
        args['Nmin'], args['Nmax'], args['kmin'], args['kmax'], args['imagewidth'], args['imageheight'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


def render_browseGraphChar(args):
    data = LfunctionPlot.paintSvgChar(
        args['min_cond'], args['max_cond'], args['min_order'], args['max_order'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


###########################################################################
# Functions for displaying examples of degree n L-functions on the
# degree browsing page (used when plots are not available)
###########################################################################
def processEllipticCurveNavigation(startCond, endCond):
    """
    Produces a table of all L-functions of elliptic curves with conductors
    from startCond to endCond
    """
    try:
        N = startCond
        if N < 11:
            N = 11
        elif N > 100:
            N = 100
    except:
        N = 11

    try:
        if endCond > 1000:
            end = 1000
        else:
            end = endCond

    except:
        end = 1000

    iso_list = isogeny_class_table(N, end)
    s = '<h5>Examples of L-functions attached to isogeny classes of elliptic curves</h5>'
    s += '<table>'

    counter = 0
    nr_of_columns = 10
    for cond, iso in iso_list:
        label = str(cond) + '.' + iso
        if counter == 0:
            s += '<tr>'

        counter += 1
        s += '<td><a href="' + url_for('.l_function_ec_page', conductor_label=cond,
                                       isogeny_class_label = iso) + '">%s</a></td>\n' % label

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s


def processGenus2CurveNavigation(startCond, endCond):
    """
    Produces a table of all L-functions of elliptic curves with conductors
    from startCond to endCond
    """
    try:
        N = startCond
        if N < 169:
            N = 169
        elif N > 1000:
            N = 1000
    except:
        N = 169

    try:
        if endCond > 1000:
            end = 1000
        else:
            end = endCond

    except:
        end = 1000

    iso_list = genus2_isogeny_class_table(N, end)
    s = '<h5>Examples of L-functions attached to isogeny classes of Jacobians of genus 2 curves</h5>'
    s += '<table>'

    counter = 0
    nr_of_columns = 10
    for cond, x in iso_list:
        label = str(cond) + '.' + x
        if counter == 0:
            s += '<tr>'

        counter += 1
        s += '<td><a href="' + url_for('.l_function_genus2_page', cond=cond, x=x) + '">%s</a></td>\n' % label

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s


def processSymPowerEllipticCurveNavigation(startCond, endCond, power):
    """
    Produces a table of all symmetric power L-functions of elliptic curves
    with conductors from startCond to endCond
    """
    try:
        N = startCond
        if N < 11:
            N = 11
        elif N > 100:
            N = 100
    except:
        N = 11

    try:
        if endCond > 500:
            end = 500
        else:
            end = endCond

    except:
        end = 100

    iso_list = isogeny_class_table(N, end)
    if power == 2:
        powerName = 'square'
    elif power == 3:
        powerName = 'cube'
    else:
        powerName = str(power) + '-th power'

    s = '<h5>Examples of symmetric ' + powerName + \
        ' L-functions attached to isogeny classes of elliptic curves</h5>'
    s += '<table>'

    counter = 0
    nr_of_columns = 10
    for cond, iso in iso_list:
        label = str(cond) + '.' + iso
        if counter == 0:
            s += '<tr>'

        counter += 1
        s += '<td><a href="' + url_for('.l_function_ec_sym_page', power=str(power),
                                       conductor=cond, isogeny=iso) + '">%s</a></td>\n' % label

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s

@l_function_page.route("/<path:prepath>/Reliability")
def reliability(prepath):
    t = 'Reliability of L-function data'
    args = tuple(prepath.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    info={'bread': ()}
    set_bread_and_friends(info, L, request)
    if L.fromDB:
        Ldb = db.lfunc_lfunctions.lucky({'Lhash': L.Lhash}, projection=['load_key'])
        if 'load_key' in Ldb:
            knowl = db.lfunc_rs_knowls.lucky({'load_key': Ldb['load_key']}, projection=['reliability'])['reliability']
        else:
            knowl = 'rcs.rigor.lfunction.lcalc'
    else:
        knowl = 'rcs.rigor.lfunction.lcalc'
    bread = info['bread']
    target = bread.pop()
    bread.append((target[0], re.sub(r'/Reliability$','',target[1])))
    bread.append(('Reliability', ' '))
    return render_template("single.html", kid=knowl, title=t, bread=bread,
        learnmore=learnmore_list(prepath, remove='Reliability'))

@l_function_page.route("/Completeness")
def completeness():
    t = 'Completeness of L-function data'
    bread = [('Completeness', ' ')]
    return render_template("single.html", kid='rcs.cande.lfunction', title=t, 
        bread=bread)

@l_function_page.route("/<path:prepath>/Source")
def source(prepath):
    t = 'Source of L-function data'
    args = tuple(prepath.split('/'))
    try:
        L = generateLfunctionFromUrl(*args)
        assert L
    except:
        return abort(404)
    info={'bread': ()}
    set_bread_and_friends(info, L, request)
    if L.fromDB:
        Ldb = db.lfunc_lfunctions.lucky({'Lhash': L.Lhash}, projection=['load_key'])
        if 'load_key' in Ldb:
            knowl = db.lfunc_rs_knowls.lucky({'load_key': Ldb['load_key']}, projection=['source'])['source']
        else:
            knowl = 'rcs.source.lfunction.lcalc'
    else:
        knowl = 'rcs.source.lfunction.lcalc'
    bread = info['bread']
    target = bread.pop()
    bread.append((target[0], re.sub(r'/Source$','',target[1])))
    bread.append(('Source', ' '))
    return render_template("single.html", kid=knowl, title=t, bread=bread,
        learnmore=learnmore_list(prepath, remove='Source'))

