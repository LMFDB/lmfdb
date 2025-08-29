
import os
import re
import time

from flask import render_template, url_for, request, redirect, make_response, send_file, abort
from sage.all import ZZ, QQ, Qp, RealField, EllipticCurve, cputime, is_prime, is_prime_power, PolynomialRing, latex, Jacobian, factor, prod, CRT, primitive_root, Mod, gcd
from sage.databases.cremona import parse_cremona_label, class_to_int
from sage.schemes.elliptic_curves.constructor import EllipticCurve_from_Weierstrass_polynomial

from lmfdb.elliptic_curves.web_ec import latex_equation


from lmfdb import db
from lmfdb.app import app
from psycodict.encoding import Json
from lmfdb.utils import (coeff_to_poly, coeff_to_poly_multi,
    web_latex, to_dict, comma, flash_error, display_knowl, raw_typeset, integer_divisors, integer_squarefree_part,
    parse_rational_to_list, parse_ints, parse_floats, parse_bracketed_posints, parse_primes,
    SearchArray, TextBox, SelectBox, SubsetBox, TextBoxWithSelect, CountBox, Downloader,
    StatsDisplay, parse_element_of, parse_signed_ints, search_wrap, redirect_no_cache, web_latex_factored_integer, CodeSnippet)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, LinkCol, ProcessedCol, MultiProcessedCol, CheckCol, FloatCol, ListCol
from lmfdb.utils.common_regex import ZLLIST_RE
from lmfdb.utils.web_display import dispZmat_from_list
from lmfdb.api import datapage
from lmfdb.elliptic_curves import ec_page, ec_logger
from lmfdb.elliptic_curves.isog_class import ECisog_class
from lmfdb.elliptic_curves.web_ec import WebEC, match_lmfdb_label, match_cremona_label, split_lmfdb_label, split_cremona_label, weierstrass_eqn_regex, short_weierstrass_eqn_regex, class_lmfdb_label, curve_lmfdb_label, EC_ainvs, latex_sha, gl2_subgroup_data, CREMONA_BOUND, match_weierstrass_polys, match_coeff_vec
from sage.misc.cachefunc import cached_method
from lmfdb.ecnf.ecnf_stats import latex_tor
from .congruent_numbers import get_congruent_number_data, congruent_number_data_directory
from lmfdb.sato_tate_groups.main import st_display_knowl

q = ZZ['x'].gen()
the_ECstats = None

#########################
#   Utility functions
#########################

def sorting_label(lab1):
    """
    Provide a sorting key.
    """
    a, b, c = parse_cremona_label(lab1)
    return (int(a), class_to_int(b), int(c))

def get_bread(tail=[]):
    base = [('Elliptic curves', url_for("ecnf.index")), (r'$\Q$', url_for(".rational_elliptic_curves"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail

def get_stats():
    global the_ECstats
    if the_ECstats is None:
        the_ECstats = ECstats()
    return the_ECstats

#########################
#    Top level
#########################

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Elliptic curve labels', url_for(".labels_page")),
            ('Congruent number curves', url_for(".render_congruent_number_data")),
            ('Stein-Watkins dataset', url_for(".render_sw_ecdb")),
            ('BHKSSW dataset', url_for(".render_bhkssw"))]


def learnmore_list_add(learnmore_label, learnmore_url):
    return learnmore_list() + [(learnmore_label, learnmore_url)]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


#########################
#  Search/navigate
#########################

@ec_page.route("/")
def rational_elliptic_curves(err_args=None):
    info = to_dict(request.args, search_array=ECSearchArray())
    if err_args is None:
        if request.args:
            return elliptic_curve_search(info)
        else:
            err_args = {}
            for field in ['conductor', 'jinv', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure', 'msg']:
                err_args[field] = ''
            err_args['count'] = '50'

    counts = get_stats()

    conductor_list_endpoints = [1, 100, 1000, 10000, 100000, int(counts.max_N_Cremona) + 1]
    conductor_list = {r: r for r in ["%s-%s" % (start, end - 1) for start, end in zip(conductor_list_endpoints[:-1],
                                                                                            conductor_list_endpoints[1:])]}
    conductor_list[">{}".format(counts.max_N_Cremona)] = "{}-".format(counts.max_N_Cremona)

    rank_list = list(range(counts.max_rank + 1))
    torsion_list = list(range(1, 11)) + [12, 16]
    info['rank_list'] = rank_list
    info['torsion_list'] = torsion_list
    info['conductor_list'] = conductor_list
    info['stats'] = ECstats()
    info['stats_url'] = url_for(".statistics")

    t = r'Elliptic curves over $\Q$'
    if err_args.get("err_msg"):
        # this comes from elliptic_curve_jump_error
        flash_error(err_args.pop("err_msg"), err_args.pop("label"))
        return redirect(url_for(".rational_elliptic_curves"))
    return render_template("ec-index.html",
                           info=info,
                           title=t,
                           bread=get_bread(),
                           learnmore=learnmore_list(),
                           calling_function="ec.rational_elliptic_curves",
                           **err_args)


@ec_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "ec.q",
        db.ec_curvedata,
        url_for_label,
        label_col="lmfdb_label",
        title=r"Some interesting elliptic curves over $\Q$",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )


@ec_page.route("/random")
@redirect_no_cache
def random_curve():
    label = db.ec_curvedata.random(projection='lmfdb_label')
    cond, iso, num = split_lmfdb_label(label)
    return url_for(".by_triple_label", conductor=cond, iso_label=iso, number=num)


@ec_page.route("/curve_of_the_day")
@redirect_no_cache  # disables cache on todays curve
def todays_curve():
    from datetime import date
    mordells_birthday = date(1888, 1, 28)
    n = (date.today() - mordells_birthday).days
    label = db.ec_curvedata.lucky(projection='lmfdb_label', offset=n)
    return url_for(".by_ec_label", label=label)

################################################################################
# Statistics
################################################################################

class ECstats(StatsDisplay):
    """
    Class for creating and displaying statistics for elliptic curves over Q
    """

    def __init__(self):
        self.ncurves = db.ec_curvedata.count()
        self.ncurves_c = comma(self.ncurves)
        self.nclasses = db.ec_classdata.count()
        self.nclasses_c = comma(self.nclasses)
        self.max_N_Cremona = 500000
        self.max_N_Cremona_c = comma(self.max_N_Cremona)
        self.max_N = db.ec_curvedata.max('conductor')
        self.max_N_c = comma(self.max_N)
        self.max_N_prime = 1000000
        self.max_N_prime_c = comma(self.max_N_prime)
        self.max_rank = db.ec_curvedata.max('rank')
        self.max_rank_c = comma(self.max_rank)
        self.cond_knowl = display_knowl('ec.q.conductor', title="conductor")
        self.rank_knowl = display_knowl('ec.rank', title="rank")
        self.ec_knowl = display_knowl('ec.q', title='elliptic curves')
        self.cl_knowl = display_knowl('ec.isogeny', title="isogeny classes")

    @property
    def short_summary(self):
        stats_url = url_for(".statistics")
        return r'The database currently includes %s %s defined over $\Q$, in %s %s, with %s at most %s.  Here are some further <a href="%s">statistics and completeness information</a>.' % (self.ncurves_c, self.ec_knowl, self.nclasses_c, self.cl_knowl, self.cond_knowl, self.max_N_c, stats_url)

    @property
    def summary(self):
        return r'Currently, the database includes ${}$ {} over $\Q$ in ${}$ {}, with {} at most ${}$.'.format(self.ncurves_c, self.ec_knowl, self.nclasses_c, self.cl_knowl, self.cond_knowl, self.max_N_c)

    table = db.ec_curvedata
    baseurl_func = ".rational_elliptic_curves"

    knowls = {'rank': 'ec.rank',
              'sha': 'ec.analytic_sha_order',
              'torsion_structure': 'ec.torsion_order'}

    top_titles = {'rank': 'rank',
                  'sha': 'analytic order of &#1064;',
                  'torsion_structure': 'torsion subgroups'}

    formatters = {'torsion_structure': latex_tor,
                  'sha': latex_sha}

    query_formatters = {'torsion_structure': 'torsion={}'.format,
                        'sha': 'sha={}'.format}

    stat_list = [
        {'cols': 'rank', 'totaler': {'avg': True}},
        {'cols': 'torsion_structure', 'totaler': {'avg': False}},
        {'cols': 'sha', 'totaler': {'avg': False}},
    ]

    @cached_method
    def isogeny_degrees(self):
        # cur = db._execute(SQL("SELECT UNIQ(SORT(ARRAY_AGG(elements ORDER BY elements))) FROM ec_curvedata, UNNEST(isogeny_degreed) as elements"))
        # return cur.fetchone()[0]
        #
        # It's a theorem that the complete set of possible degrees is this:
        return list(range(1,20)) + [21,25,27,37,43,67,163]

# NB the context processor wants something callable and the summary is a *property*

@app.context_processor
def ctx_elliptic_curve_summary():
    return {'elliptic_curve_summary': lambda: ECstats().summary}

@app.context_processor
def ctx_gl2_subgroup():
    return {'gl2_subgroup_data': gl2_subgroup_data}

@app.context_processor
def ctx_ec_reduction_type():
    return {'ec_reduction_type': lambda x: ["nonsplit multiplicative","additive","split multiplicative","good"][x+1] if x >= -1 and x <= 2 else "unknown" }

@ec_page.route("/stats")
def statistics():
    title = r'Elliptic curves over $\Q$: Statistics'
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=ECstats(), title=title, bread=bread, learnmore=learnmore_list())


@ec_page.route("/<int:conductor>/")
def by_conductor(conductor):
    info = to_dict(request.args, search_array=ECSearchArray())
    info['bread'] = get_bread([('%s' % conductor, url_for(".by_conductor", conductor=conductor))])
    info['title'] = r'Elliptic curves over $\Q$ of conductor %s' % conductor
    if request.args:
        # if conductor changed, fall back to a general search
        if 'conductor' in request.args and request.args['conductor'] != str(conductor):
            return redirect(url_for(".rational_elliptic_curves", **request.args), 307)
        info['title'] += ' Search results'
        info['bread'].append(('Search results',''))
    info['conductor'] = conductor
    return elliptic_curve_search(info)


def elliptic_curve_jump_error(label, args, missing_curve=False, missing_class=False, invalid_class=False, invalid_poly=False):
    err_args = {}
    for field in ['conductor', 'torsion', 'rank', 'sha', 'optimal', 'torsion_structure']:
        err_args[field] = args.get(field, '')
    err_args['count'] = args.get('count', '100')
    err_args['label'] = label
    if missing_curve:
        err_args['err_msg'] = "The elliptic curve %s is not in the database"
    elif missing_class:
        err_args['err_msg'] = "The isogeny class %s is not in the database"
    elif invalid_class:
        err_args['err_msg'] = r"%s is not a valid label for an isogeny class of elliptic curves over $\mathbb{Q}$"
    elif invalid_poly:
        err_args['err_msg'] = "The equation defined by %s does not define an elliptic curve"
    elif not label:
        err_args['err_msg'] = "Please enter a non-empty label %s"
    else:
        err_args['err_msg'] = r"%s is not a valid label for an elliptic curve or isogeny class over $\mathbb{Q}$"
    return rational_elliptic_curves(err_args)


def ec_parse_coeff_vec(label, info):
    lab = re.sub(r'\s','',label)
    lab = re.sub(r'^\[','',lab)
    lab = re.sub(r']$','',lab)
    try:
        labvec = lab.split(',')
        labvec = [QQ(str(z)) for z in labvec] # Rationals allowed
        E = EllipticCurve(labvec).minimal_model()
        # Now we do have a valid curve over Q, but it might
        # not be in the database.
        lmfdb_label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)}, 'lmfdb_label')
        if lmfdb_label is None:
            info['conductor'] = E.conductor()
            return elliptic_curve_jump_error(label, info, missing_curve=True)
        return by_ec_label(lmfdb_label)
    except Exception:
        return elliptic_curve_jump_error(label, info)


def ec_lookup_equation(input_str):

    R = PolynomialRing(QQ, "x")
    y = PolynomialRing(R, "y").gen()

    def read_list_coeffs(elt):
        if not elt:
            return R(0)
        else:
            return R([int(c) for c in elt.split(",")])

    if ZLLIST_RE.fullmatch(input_str):
        input_str_new = input_str.strip('[').strip(']')
        fg = [read_list_coeffs(elt) for elt in input_str_new.split('],[')]
    else:
        input_str_new = input_str.strip('[').strip(']')
        fg = [R(list(coeff_to_poly(elt))) for elt in input_str_new.split(",")]
    if len(fg) == 1:
        fg.append(R(0))

    ec_defining_poly = y**2 + y*(fg[1]) - fg[0]
    S = PolynomialRing(QQ, 2, ["x", "y"])
    x,_ = S.gens()
    ec_defining_poly = S(ec_defining_poly)

    if ec_defining_poly.coefficient(x**3) == -1:
        try:
            E = EllipticCurve_from_Weierstrass_polynomial(ec_defining_poly).minimal_model()
        except ValueError:
            C_str_latex = fr"\({latex(y**2 + y*fg[1])} = {latex(fg[0])}\)"
            return None, ("invalid_poly",C_str_latex)
    else:
        try:
            E = Jacobian(ec_defining_poly).minimal_model()
        except ValueError:
            C_str_latex = fr"\({latex(y**2 + y*fg[1])} = {latex(fg[0])}\)"
            return None, ("invalid_poly",C_str_latex)
    lmfdb_label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)}, 'lmfdb_label')

    if lmfdb_label is None:
        return None, ("not_in_db",EC_ainvs(E))
    return lmfdb_label,""


def elliptic_curve_jump(info):
    label = info.get('jump', '').replace(" ", "")
    if label is None:
        return elliptic_curve_jump_error('', info)
    elif match_lmfdb_label(label):
        try:
            return by_ec_label(label)
        except ValueError:
            return elliptic_curve_jump_error(label, info, missing_curve=True)
    elif match_cremona_label(label):
        try:
            return redirect(url_for(".by_ec_label", label=label))
        except ValueError:
            return elliptic_curve_jump_error(label, info, missing_curve=True)
    elif match_coeff_vec(label):
        # Try to parse a string like [1,0,3,2,4] as valid
        # Weistrass coefficients:
        return ec_parse_coeff_vec(label, info)
    elif match_weierstrass_polys(label):
        label, fail_reason = ec_lookup_equation(label)
        if label:
            return by_ec_label(label)
        elif label is None:
            if fail_reason[0] == "invalid_poly":
                return elliptic_curve_jump_error(fail_reason[1], info, invalid_poly=True)
            return elliptic_curve_jump_error(fail_reason[1], info, missing_curve=True)
    elif label.count('=') == 1:
        lhs_str, rhs_str = label.split('=')
        rhs_poly = coeff_to_poly_multi(rhs_str)
        main_poly_str = lhs_str + "+" + str(-rhs_poly)
        main_poly = coeff_to_poly_multi(main_poly_str)
        try:
            E = EllipticCurve_from_Weierstrass_polynomial(main_poly).minimal_model()
        except ValueError:
            C_str_latex = fr"\({latex(main_poly)}\)"
            return elliptic_curve_jump_error(C_str_latex, info, invalid_poly=True)
        lmfdb_label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)}, 'lmfdb_label')
        if lmfdb_label is None:
            return elliptic_curve_jump_error(EC_ainvs(E), info, missing_curve=True)
        return by_ec_label(lmfdb_label)
    else:
        return elliptic_curve_jump_error(label, info)


def url_for_label(label):
    if label == "random":
        return url_for(".random_curve")
    return url_for("ec.by_ec_label", label=label)

elladic_image_label_regex = re.compile(r'(\d+)\.(\d+)\.(\d+)\.(\d+)')
modell_image_label_regex = re.compile(r'(\d+)(G|B|Cs|Cn|Ns|Nn|A4|S4|A5)(\.\d+)*')

modm_full = r'(\d+)\.(\d+)\.(\d+)\.([a-z]+)\.(\d+)'
modm_not_computed = r'(\d+)\.(\d+)\.(\d+)\.(\?)'
modm_no_negative = r'(\d+)\.(\d+)\.(\d+)-(\d+)\.([a-z]+)\.(\d+)\.(\d+)'
modm_image_label_regex = re.compile(modm_full + "|" + modm_not_computed + "|" + modm_no_negative)

def ec_postprocess(res, info, query):
    labels = [rec["lmfdb_label"] for rec in res]
    mwgens = {rec["lmfdb_label"]: rec["gens"] for rec in db.ec_mwbsd.search({"lmfdb_label":{"$in":labels}}, ["lmfdb_label", "gens"])}
    for rec in res:
        gens = mwgens.get(rec["lmfdb_label"])
        if gens is not None:
            gens = [(a / c, b / c) for a, b, c in gens]
        rec["mwgens"] = gens
    return res

def make_modcurve_link(label):
    from lmfdb.modular_curves.main import modcurve_link
    return modcurve_link(label)

ec_columns = SearchColumns([
    LinkCol("lmfdb_label", "ec.q.lmfdb_label", "Label", lambda label: url_for(".by_ec_label", label=label),
             align="center", short_title="LMFDB curve label"),
    MultiProcessedCol("cremona_label", "ec.q.cremona_label", "Cremona label",
                       ["Clabel", "conductor"],
                       lambda label, conductor: '<a href="%s">%s</a>' % (url_for(".by_ec_label", label=label), label) if conductor < CREMONA_BOUND else " - ",
                       align="center", short_title="Cremona curve label", download_col="Clabel", default=False),
    LinkCol("lmfdb_iso", "ec.q.lmfdb_label", "Class", lambda label: url_for(".by_ec_label", label=label),
             align="center", short_title="LMFDB class label"),
    MultiProcessedCol("cremona_iso", "ec.q.cremona_label", "Cremona class",
                       ["Ciso", "conductor"],
                       lambda label, conductor: '<a href="%s">%s</a>' % (url_for(".by_ec_label", label=label), label) if conductor < CREMONA_BOUND else " - ",
                       align="center", short_title="Cremona class label", download_col="Ciso", default=False),
    MathCol("class_size", "ec.isogeny_class", "Class size", align="center", default=lambda info: info.get("class_size") or info.get("optimal") == "on"),
    MathCol("class_deg", "ec.isogeny_class_degree", "Class degree", align="center", default=lambda info: info.get("class_deg")),
    ProcessedCol("conductor", "ec.q.conductor", "Conductor", lambda v: web_latex_factored_integer(ZZ(v)), align="center"),
    MultiProcessedCol("disc", "ec.discriminant", "Discriminant", ["signD", "absD"], lambda s, a: web_latex_factored_integer(s*ZZ(a)),
                       default=lambda info: info.get("discriminant"), align="center", apply_download=lambda s, a: s*a),
    MathCol("rank", "ec.rank", "Rank"),
    ProcessedCol("torsion_structure", "ec.torsion_subgroup", "Torsion",
                  lambda tors: r"\oplus".join([r"\Z/%s\Z" % n for n in tors]) if tors else r"\mathsf{trivial}", mathmode=True, align="center"),
    ProcessedCol("geom_end_alg", "ag.endomorphism_algebra", r"$\textrm{End}^0(E_{\overline\Q})$",
                  lambda v: r"$\Q$" if not v else r"$\Q(\sqrt{%d})$" % (integer_squarefree_part(v)),
                  short_title="Qbar-end algebra", align="center", orig="cm", default=False),
    ProcessedCol("cm_discriminant", "ec.complex_multiplication", "CM", lambda v: "" if v == 0 else v,
                  short_title="CM discriminant", mathmode=True, align="center", orig="cm"),
    ProcessedCol("sato_tate_group", "st_group.definition", "Sato-Tate", lambda v: st_display_knowl('1.2.A.1.1a' if v == 0 else '1.2.B.2.1a'),
                  short_title="Sato-Tate group", align="center", orig="cm", apply_download=lambda v:'1.2.A.1.1a' if v == 0 else '1.2.B.2.1a', default=False),
    CheckCol("semistable", "ec.reduction", "Semistable", default=False),
    CheckCol("potential_good_reduction", "ec.reduction", "Potentially good", default=False),
    ProcessedCol("nonmax_primes", "ec.maximal_elladic_galois_rep", r"Nonmax $\ell$", lambda primes: ", ".join([str(p) for p in primes]),
                  default=lambda info: info.get("nonmax_primes"), short_title="nonmaximal primes", mathmode=True, align="center"),
    ProcessedCol("elladic_images", "ec.galois_rep_elladic_image", r"$\ell$-adic images", lambda v: ", ".join([display_knowl('gl2.subgroup_data', title=s, kwargs={'label':s}) for s in v]),
                  short_title="ℓ-adic images", default=lambda info: info.get("nonmax_primes") or info.get("galois_image"), align="center"),
    ProcessedCol("modell_images", "ec.galois_rep_modell_image", r"mod-$\ell$ images", lambda v: ", ".join([display_knowl('gl2.subgroup_data', title=s, kwargs={'label':s}) for s in v]),
                  short_title="mod-ℓ images", default=lambda info: info.get("nonmax_primes") or info.get("galois_image"), align="center"),
    MathCol("adelic_level", "ec.galois_rep", "Adelic level", default=lambda info: info.get("adelic_level") or info.get("adelic_index") or info.get("adelic_genus")),
    MathCol("adelic_index", "ec.galois_rep", "Adelic index", default=lambda info: info.get("adelic_level") or info.get("adelic_index") or info.get("adelic_genus")),
    MathCol("adelic_genus", "ec.galois_rep", "Adelic genus", default=lambda info: info.get("adelic_level") or info.get("adelic_index") or info.get("adelic_genus")),
    ProcessedCol("regulator", "ec.regulator", "Regulator", lambda v: str(v)[:11], mathmode=True, default=False),
    MathCol("sha", "ec.analytic_sha_order", r"$Ш_{\textrm{an}}$", short_title="analytic Ш", default=False),
    ProcessedCol("sha_primes", "ec.analytic_sha_order", "Ш primes", lambda primes: ", ".join(str(p) for p in primes),
                  default=lambda info: info.get("sha_primes"), mathmode=True, align="center"),
    MathCol("num_int_pts", "ec.q.integral_points", "Integral points",
             default=lambda info: info.get("num_int_pts"), align="center"),
    MathCol("degree", "ec.q.modular_degree", "Modular degree", align="center", default=False),
    ProcessedCol("faltings_height", "ec.q.faltings_height", "Faltings height", lambda v: "%.6f" % (RealField(20)(v)), short_title="Faltings height",
                  default=lambda info: info.get("faltings_height"), mathmode=True, align="right"),
    ProcessedCol("jinv", "ec.q.j_invariant", "j-invariant", lambda v: r"$%s/%s$" % (v[0],v[1]) if v[1] > 1 else r"$%s$" % v[0],
                  short_title="j-invariant", align="center", default=False),
    FloatCol("abc_quality", "ec.q.abc_quality", "$abc$ quality", short_title="abc quality", prec=5, default=False),
    FloatCol("szpiro_ratio", "ec.q.szpiro_ratio", "Szpiro ratio", prec=5, default=False),
    MathCol("ainvs", "ec.weierstrass_coeffs", "Weierstrass coefficients", short_title="Weierstrass coeffs", align="left", default=False),
    ProcessedCol("equation", "ec.q.minimal_weierstrass_equation", "Weierstrass equation", latex_equation, short_title="Weierstrass equation", align="left", orig="ainvs", download_col="ainvs"),
    ProcessedCol("modm_images", "ec.galois_rep", r"mod-$m$ images", lambda v: "<span>" + ", ".join([make_modcurve_link(s) for s in v[:5]] + ([r"$\ldots$"] if len(v) > 5 else [])) + "</span>",
                  short_title="mod-m images", default=lambda info: info.get("galois_image")),
    ListCol("mwgens", "ec.mordell_weil_group", "MW-generators", mathmode=True, default=False),
])

class ECDownloader(Downloader):
    table = db.ec_curvedata
    title = "Elliptic curves"
    def modify_query(self, info, query):
        if info.get("optimal") == "on":
            query["__one_per__"] = "lmfdb_iso"

    inclusions = {
        "curve": (
            ["ainvs"],
            {
                "sage": 'curve = EllipticCurve(out["ainvs"])',
                "magma": 'curve := EllipticCurve(out`ainvs);',
                "gp": 'curve = ellinit(mapget(out, "ainvs"));',
                "oscar": 'curve = EllipticCurve(out["ainvs"])',
            }
        )
    }

    def postprocess(self, row, info, query):
        # Unfortunately, I don't see a good way to batch these database calls
        # given how the download iterator works
        if "mwgens" in info.get("showcol", "").split("."):
            gens = db.ec_mwbsd.lucky({"lmfdb_label": row["lmfdb_label"]}, "gens")
            if gens is not None:
                gens = [(ZZ(a) / c, ZZ(b) / c) for a, b, c in gens]
            row["mwgens"] = gens
        return row

@search_wrap(table=db.ec_curvedata,
             title='Elliptic curve search results',
             err_title='Elliptic curve search input error',
             columns=ec_columns,
             per_page=50,
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             shortcuts={'jump':elliptic_curve_jump,
                        'download':ECDownloader()},
             bread=lambda:get_bread('Search results'),
             postprocess=ec_postprocess)
def elliptic_curve_search(info, query):
    parse_rational_to_list(info, query, 'jinv', 'j-invariant')
    parse_ints(info, query, 'conductor')
    if info.get('conductor_type'):
        if info['conductor_type'] == 'prime':
            query['num_bad_primes'] = 1
            query['semistable'] = True
        elif info['conductor_type'] == 'prime_power':
            query['num_bad_primes'] = 1
        elif info['conductor_type'] == 'squarefree':
            query['semistable'] = True
        elif info['conductor_type'] in ['divides', 'multiple']:
            if not isinstance(query.get('conductor'), int):
                err = "You must specify a single conductor"
                flash_error(err)
                raise ValueError(err)
            elif info['conductor_type'] == 'divides':
                query['conductor'] = {'$in': integer_divisors(ZZ(query['conductor']))}
            else:
                query['conductor'] = {'$mod': [0, ZZ(query['conductor'])]}
    parse_signed_ints(info, query, 'discriminant', qfield=('signD', 'absD'))
    parse_ints(info,query,'rank')
    parse_ints(info,query,'adelic_level')
    parse_ints(info,query,'adelic_index')
    parse_ints(info,query,'adelic_genus')
    parse_ints(info,query,'sha','analytic order of &#1064;')
    parse_ints(info,query,'num_int_pts','num_int_pts')
    parse_ints(info,query,'class_size','class_size')
    if info.get('class_deg'):
        parse_ints(info,query,'class_deg','class_deg')
        if not isinstance(query.get('class_deg'), int):
            err = "You must specify a single isogeny class degree"
            flash_error(err)
            raise ValueError(err)
    parse_floats(info,query,'regulator','regulator')
    parse_floats(info,query,'faltings_height','faltings_height')
    parse_floats(info,query,'abc_quality')
    parse_floats(info,query,'szpiro_ratio')
    if info.get('reduction'):
        if info['reduction'] == 'semistable':
            query['semistable'] = True
        elif info['reduction'] == 'not semistable':
            query['semistable'] = False
        elif info['reduction'] == 'potentially good':
            query['potential_good_reduction'] = True
        elif info['reduction'] == 'not potentially good':
            query['potential_good_reduction'] = False
    if info.get('torsion'):
        if info['torsion'][0] == '[':
            parse_bracketed_posints(info,query,'torsion',qfield='torsion_structure',maxlength=2,check_divisibility='increasing')
        else:
            parse_ints(info,query,'torsion')
    # speed up slow torsion_structure searches by also setting torsion
    #if 'torsion_structure' in query and not 'torsion' in query:
    #    query['torsion'] = reduce(mul,[int(n) for n in query['torsion_structure']],1)
    if 'cm' in info:
        if info['cm'] == 'noCM':
            query['cm'] = 0
        elif info['cm'] == 'CM':
            query['cm'] = {'$ne': 0}
        else:
            parse_ints(info,query,field='cm',qfield='cm')
    parse_element_of(info,query,'isogeny_degrees',split_interval=200,contained_in=get_stats().isogeny_degrees)
    parse_primes(info, query, 'nonmax_primes', name='non-maximal primes',
                 qfield='nonmax_primes', mode=info.get('nonmax_quantifier'), radical='nonmax_rad')
    parse_primes(info, query, 'bad_primes', name='bad primes',
                 qfield='bad_primes',mode=info.get('bad_quantifier'))
    parse_primes(info, query, 'sha_primes', name='sha primes',
                 qfield='sha_primes',mode=info.get('sha_quantifier'))
    if info.get('galois_image'):
        labels = [a.strip() for a in info['galois_image'].split(',')]
        elladic_labels = [a for a in labels if elladic_image_label_regex.fullmatch(a) and is_prime_power(elladic_image_label_regex.match(a)[1])]
        modell_labels = [a for a in labels if modell_image_label_regex.fullmatch(a) and is_prime(modell_image_label_regex.match(a)[1])]
        modm_labels = [a for a in labels if modm_image_label_regex.fullmatch(a)]
        if len(elladic_labels)+len(modell_labels)+len(modm_labels) != len(labels):
            err = "Unrecognized Galois image label, it should be the label of a subgroup of GL(2,Z_ell), such as %s, or the label of a subgroup of GL(2,F_ell), such as %s, or a list of such labels"
            flash_error(err, "13.91.3.2", "13S4")
            raise ValueError(err)
        if elladic_labels:
            query['elladic_images'] = {'$contains': elladic_labels}
        if modell_labels:
            query['modell_images'] = {'$contains': modell_labels}
        if modm_labels:
            query['modm_images'] = {'$contains': modm_labels}
        if 'cm' not in query:
            query['cm'] = 0
            info['cm'] = "noCM"
        if query['cm']:
            # try to help the user out if they specify the normalizer of a Cartan in the CM case (these are either maximal or impossible
            if any(a.endswith("Nn") for a in modell_labels) or any(a.endswith("Ns") for a in modell_labels):
                err = "To search for maximal images, exclude non-maximal primes"
                flash_error(err)
                raise ValueError(err)
        else:
            # if the user specifies full mod-ell image with ell > 3, automatically exclude nonmax primes (if possible)
            max_labels = [a for a in modell_labels if a.endswith("G") and int(modell_image_label_regex.match(a)[1]) > 3]
            if max_labels:
                if info.get('nonmax_primes') and info['nonmax_quantifier'] != 'exclude':
                    err = "To search for maximal images, exclude non-maximal primes"
                    flash_error(err)
                    raise ValueError(err)
                else:
                    modell_labels = [a for a in modell_labels if a not in max_labels]
                    max_primes = [modell_image_label_regex.match(a)[1] for a in max_labels]
                    if info.get('nonmax_primes'):
                        max_primes += [l.strip() for l in info['nonmax_primes'].split(',') if l.strip() not in max_primes]
                    max_primes.sort(key=int)
                    info['nonmax_primes'] = ','.join(max_primes)
                    info['nonmax_quantifier'] = 'exclude'
                    parse_primes(info, query, 'nonmax_primes', name='non-maximal primes',
                                 qfield='nonmax_primes', mode=info.get('nonmax_quantifier'), radical='nonmax_rad')
                    info['galois_image'] = ','.join(modell_labels + elladic_labels)
                query['modell_images'] = { '$contains': modell_labels }

    # The button which used to be labelled Optimal only no/yes"
    # (default: no) has been renamed "Curves per isogeny class
    # all/one" (default: all).  When this option is "one" we only list
    # one curve in each class, currently choosing the curve with
    # minimal Faltings heights, which is conjecturally the
    # Gamma_1(N)-optimal curve.
    if 'optimal' in info and info['optimal'] == 'on':
        query["__one_per__"] = "lmfdb_iso"

    info['curve_ainvs'] = lambda dbc: str([ZZ(ai) for ai in dbc['ainvs']])
    info['curve_url_LMFDB'] = lambda dbc: url_for(".by_triple_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1], number=dbc['lmfdb_number'])
    info['iso_url_LMFDB'] = lambda dbc: url_for(".by_double_iso_label", conductor=dbc['conductor'], iso_label=split_lmfdb_label(dbc['lmfdb_iso'])[1])
    info['cremona_bound'] = CREMONA_BOUND
    info['curve_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['Clabel'])
    info['iso_url_Cremona'] = lambda dbc: url_for(".by_ec_label", label=dbc['Ciso'])
    info['FH'] = lambda dbc: RealField(20)(dbc['faltings_height'])

##########################
#  Specific curve pages
##########################

@ec_page.route("/<int:conductor>/<iso_label>/")
def by_double_iso_label(conductor,iso_label):
    full_iso_label = class_lmfdb_label(conductor,iso_label)
    return render_isogeny_class(full_iso_label)

@ec_page.route("/<int:conductor>/<iso_label>/<int:number>")
def by_triple_label(conductor,iso_label,number):
    full_label = curve_lmfdb_label(conductor,iso_label,number)
    return render_curve_webpage_by_label(full_label)

# The following function determines whether the given label is in
# LMFDB or Cremona format, and also whether it is a curve label or an
# isogeny class label, and calls the appropriate function

@ec_page.route("/<label>/")
def by_ec_label(label):
    ec_logger.debug(label)

    # First see if we have an LMFDB label of a curve or class:
    try:
        N, iso, number = split_lmfdb_label(label)
        if number:
            return redirect(url_for(".by_triple_label", conductor=N, iso_label=iso, number=number))
        else:
            return redirect(url_for(".by_double_iso_label", conductor=N, iso_label=iso))

    except AttributeError:
        ec_logger.debug("%s not a valid lmfdb label, trying cremona")
        # Next see if we have a Cremona label of a curve or class:
        try:
            N, iso, number = split_cremona_label(label)
        except AttributeError:
            ec_logger.debug("%s not a valid cremona label either, trying Weierstrass")
            eqn = label.replace(" ","")
            if weierstrass_eqn_regex.match(eqn) or short_weierstrass_eqn_regex.match(eqn):
                return by_weierstrass(eqn)
            else:
                return elliptic_curve_jump_error(label, {})

        if number: # it's a curve
            label_type = 'Clabel'
        else:
            label_type = 'Ciso'

        data = db.ec_curvedata.lucky({label_type: label})
        if data is None:
            return elliptic_curve_jump_error(label, {}, missing_curve=True)
        ec_logger.debug(url_for(".by_ec_label", label=data['lmfdb_label']))
        if number:
            return render_curve_webpage_by_label(label)
        else:
            return render_isogeny_class(label)


def by_weierstrass(eqn):
    w = weierstrass_eqn_regex.match(eqn)
    if not w:
        w = short_weierstrass_eqn_regex.match(eqn)
    if not w:
        return elliptic_curve_jump_error(eqn, {})
    try:
        ainvs = [ZZ(ai) for ai in w.groups()]
    except TypeError:
        return elliptic_curve_jump_error(eqn, {})
    E = EllipticCurve(ainvs).global_minimal_model()
    label = db.ec_curvedata.lucky({'ainvs': EC_ainvs(E)},'lmfdb_label')
    if label is None:
        N = E.conductor()
        return elliptic_curve_jump_error(eqn, {'conductor':N}, missing_curve=True)
    return redirect(url_for(".by_ec_label", label=label), 301)

def render_isogeny_class(iso_class):
    class_data = ECisog_class.by_label(iso_class)
    if class_data == "Invalid label":
        return elliptic_curve_jump_error(iso_class, {}, invalid_class=True)
    if class_data == "Class not found":
        return elliptic_curve_jump_error(iso_class, {}, missing_class=True)
    class_data.modform_display = url_for(".modular_form_display", label=class_data.lmfdb_iso+"1", number="")
    learnmore_isog_picture = ('Picture description', url_for(".isog_picture_page"))
    return render_template("ec-isoclass.html",
                           properties=class_data.properties,
                           info=class_data,
                           code=class_data.code,
                           bread=class_data.bread,
                           title=class_data.title,
                           friends=class_data.friends,
                           KNOWL_ID="ec.q.%s" % iso_class,
                           downloads=class_data.downloads,
                           learnmore=learnmore_list_add(*learnmore_isog_picture) if class_data.class_size > 1 else learnmore_list())

@ec_page.route("/modular_form_display/<label>")
@ec_page.route("/modular_form_display/<label>/<number>")
def modular_form_display(label, number):
    try:
        number = int(number)
    except ValueError:
        number = 10
    number = max(number, 10)
    number = min(number, 1000)
    ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_label')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})
    E = EllipticCurve(ainvs)
    modform = E.q_eigenform(number)
    modform_string = raw_typeset(modform)
    return modform_string

def render_curve_webpage_by_label(label):
    cpt0 = cputime()
    t0 = time.time()
    data = WebEC.by_label(label)
    if data == "Invalid label":
        return elliptic_curve_jump_error(label, {})
    if data == "Curve not found":
        return elliptic_curve_jump_error(label, {}, missing_curve=True)
    try:
        lmfdb_label = data.lmfdb_label
    except AttributeError:
        return elliptic_curve_jump_error(label, {})

    data.modform_display = url_for(".modular_form_display", label=lmfdb_label, number="")

    code = data.code()
    code['show'] = {'magma':'','pari':'','sage':'','oscar':''} # use default show names
    learnmore_curve_picture = ('Picture description', url_for(".curve_picture_page"))
    T = render_template("ec-curve.html",
                        properties=data.properties,
                        data=data,
                        # set default show names but actually code snippets are filled in only when needed
                        code=code,
                        bread=data.bread, title=data.title,
                        friends=data.friends,
                        downloads=data.downloads,
                        KNOWL_ID="ec.q.%s" % lmfdb_label,
                        BACKUP_KNOWL_ID="ec.q.%s" % data.lmfdb_iso,
                        learnmore=learnmore_list_add(*learnmore_curve_picture))
    ec_logger.debug("Total walltime: %ss" % (time.time() - t0))
    ec_logger.debug("Total cputime: %ss" % (cputime(cpt0)))
    return T


@ec_page.route("/data/<label>")
def EC_data(label):
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    if match_lmfdb_label(label):
        conductor, iso_class, number = split_lmfdb_label(label)
        if not number: # isogeny class
            return datapage(label, ["ec_classdata", "ec_padic", "ec_curvedata"], title=f"Elliptic curve isogeny class data - {label}", bread=bread, label_cols=["lmfdb_iso", "lmfdb_iso", "lmfdb_iso"], sorts=[[], ["p"], ['conductor', 'iso_nlabel', 'lmfdb_number']])
        iso_label = class_lmfdb_label(conductor, iso_class)
        labels = [label] * 8
        label_cols = ["lmfdb_label"] * 8
        labels[1] = labels[7] = iso_label
        label_cols[1] = label_cols[7] = "lmfdb_iso"
        sorts = [[], [], [], [], ["degree", "field"], ["prime"], ["prime"], ["p"]]
        return datapage(labels, ["ec_curvedata", "ec_classdata", "ec_mwbsd", "ec_iwasawa", "ec_torsion_growth", "ec_localdata", "ec_galrep", "ec_padic"], title=f"Elliptic curve data - {label}", bread=bread, label_cols=label_cols, sorts=sorts)
    return abort(404, f"Invalid label {label}")

@ec_page.route("/padic_data/<label>/<int:p>")
def padic_data(label, p):
    try:
        N, iso, number = split_lmfdb_label(label)
    except AttributeError:
        return abort(404)
    info = {'p': p}
    if db.ec_curvedata.lookup(label, label_col='lmfdb_label', projection="rank") == 0:
        info['reg'] = 1
    elif number == '1':
        data = db.ec_padic.lucky({'lmfdb_iso': N + '.' + iso, 'p': p})
        if data is None:
            info['reg'] = 'no data'
        else:
            val = int(data['val'])
            aprec = data['prec']
            reg = Qp(p, aprec)(int(data['unit']), aprec - val) << val
            info['reg'] = web_latex(reg)
    else:
        info['reg'] = "no data"
    return render_template("ec-padic-data.html", info=info)


@ec_page.route("/download_qexp/<label>/<int:limit>")
def download_EC_qexp(label, limit):
    try:
        _, _, number = split_lmfdb_label(label)
    except (ValueError, AttributeError):
        return elliptic_curve_jump_error(label, {})
    if number:
        ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_label')
    else:
        ainvs = db.ec_curvedata.lookup(label, 'ainvs', 'lmfdb_iso')
    if ainvs is None:
        return elliptic_curve_jump_error(label, {})
    if limit > 100000:
        return redirect(url_for('.download_EC_qexp',label=label,limit=10000), 301)
    E = EllipticCurve(ainvs)
    response = make_response(','.join(str(an) for an in E.anlist(int(limit), python_ints=True)))
    response.headers['Content-type'] = 'text/plain'
    return response

#TODO: get all the data from all the relevant tables, not just the search table.

@ec_page.route("/download_all/<label>")
def download_EC_all(label):
    try:
        _, _, number = split_lmfdb_label(label)
    except (ValueError, AttributeError):
        return elliptic_curve_jump_error(label, {})
    if number:
        data = db.ec_curvedata.lookup(label, label_col='lmfdb_label')
        if data is None:
            return elliptic_curve_jump_error(label, {})
        data_list = [data]
    else:
        data_list = list(db.ec_curvedata.search({'lmfdb_iso': label}, sort=['lmfdb_number']))
        if not data_list:
            return elliptic_curve_jump_error(label, {})

    response = make_response('\n\n'.join(Json.dumps(d) for d in data_list))
    response.headers['Content-type'] = 'text/plain'
    return response

@ec_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for elliptic curve data over $\Q$'
    bread = get_bread('Source')
    return render_template("multi.html",
                           kids=['rcs.source.ec.q',
                           'rcs.ack.ec.q',
                           'rcs.cite.ec.q'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@ec_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of elliptic curve data over $\Q$'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.ec.q',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@ec_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of elliptic curve data over $\Q$'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.ec.q',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@ec_page.route("/CurvePictures")
def curve_picture_page():
    t = r'Pictures for elliptic curves over $\Q$'
    bread = get_bread('Curve Pictures')
    return render_template(
        "single.html", kid='portrait.ec.q',
        title=t, bread=bread, learnmore=learnmore_list(),
    )

@ec_page.route("/IsogenyPictures")
def isog_picture_page():
    t = r'Pictures of isogeny graphs of elliptic curves over $\Q$'
    bread = get_bread('Isogeny Pictures')
    return render_template(
        "single.html", kid='ec.isogeny_graph',
        title=t, bread=bread, learnmore=learnmore_list(),
    )

@ec_page.route("/Labels")
def labels_page():
    t = r'Labels for elliptic curves over $\Q$'
    bread = get_bread('Labels')
    return render_template("single.html", kid='ec.q.lmfdb_label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@ec_page.route('/<conductor>/<iso>/<number>/download/<download_type>')
def ec_code_download(**args):
    response = make_response(ec_code(**args))
    response.headers['Content-type'] = 'text/plain'
    return response

@ec_page.route("/CongruentNumbers")
def render_congruent_number_data():
    info = to_dict(request.args)
    if 'lookup' in info:
        return redirect(url_for(".render_single_congruent_number", n=info['lookup']))
    learnmore = learnmore_list_remove('Congruent numbers and curves')
    t = 'Congruent numbers and congruent number curves'
    bread = [("Datasets", url_for("datasets")), (t, " ")]
    if 'filename' in info:
        filepath = os.path.join(congruent_number_data_directory,info['filename'])
        if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
            return send_file(filepath, as_attachment=True)
        else:
            flash_error('File {} not found'.format(info['filename']))
            return redirect(url_for(".render_congruent_number_data"))

    return render_template("congruent_number_data.html", info=info, title=t, bread=bread, learnmore=learnmore)

@ec_page.route("/CongruentNumber/<int:n>")
def render_single_congruent_number(n):
    if 0 < n and n <= 1000000:
        info = get_congruent_number_data(n)
    else:
        info = {'n': n, 'error': 'out of range'}
    t = "Is {} a congruent number?".format(n)
    bread = get_bread() + [("Congruent numbers", url_for(".render_congruent_number_data")), (n, "")]
    return render_template("single_congruent_number.html", info=info, title=t, bread=bread, learnmore=learnmore_list())

@ec_page.route("/stein-watkins")
def render_sw_ecdb():
    info = to_dict(request.args)
    learnmore = learnmore_list_remove('Stein-Watkins dataset')
    t = 'Stein-Watkins elliptic curve database'
    bread = [("Datasets", url_for("datasets")), ("Stein-Watkins dataset", " ")]
    if 'Fetch' in info:
        errors = []
        if info.get("ctype") == "all":
            fname = "a.{:03d}"
            kmax = 999
        elif info.get("ctype") == "prime":
            fname = "p.{:02d}"
            kmax = 99
        else:
            errors.append("Invalid conductor type")
        if 'k' in info and not errors:
            k = info["k"].strip()
            if k.isdigit():
                k = int(k)
                if k <= kmax:
                    fname = fname.format(k)
                else:
                    errors.append(f"k must be at most {kmax}")
            else:
                errors.append(f"k must be a nonnegative integer at most {kmax}")
        if not errors:
            filepath = os.path.expanduser('~/data/stein_watkins_ecdb/' + fname)
            if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
                return send_file(filepath, as_attachment=True)
            errors.append(f"File {fname} not found")
        for err in errors:
            flash_error(err)

    return render_template("sw_ecdb.html", info=info, comma=comma, title=t, bread=bread, learnmore=learnmore)

@ec_page.route("/BHKSSW")
def render_bhkssw():
    info = to_dict(request.args)
    learnmore = learnmore_list_remove('BHKSSW dataset')
    t = 'Balakrishnan-Ho-Kaplan-Spicer-Stein-Watkins elliptic curve database'
    bread = [("Datasets", url_for("datasets")), ("BHKSSW dataset", " ")]
    #if 'filename' in info:
    #    filepath = os.path.join(os.path.expanduser('~/data/bhkssw_ecdb/' + info['filename']))
    #    if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
    #        return send_file(filepath, as_attachment=True)
    #    else:
    #        flash_error('File {} not found'.format(info['filename']))
    #        return redirect(url_for(".render_bhkssw"))
    # This format was nice, but not possible with the 30-second timeout limitation
    #info['files'] = [ # number of curves, size in MB, lower bound, upper bound, filename
    #    (2249362, 151, "0", r"1 \cdot 10^8", "1e8db.txt"),
    #    (1758056, 123, r"1 \cdot 10^8", r"2 \cdot 10^8", "2e8db.txt"),
    #    (11300506, 798, r"2 \cdot 10^8", r"1 \cdot 10^9", "1e9db.txt"),
    #    (11982016, 866, r"1 \cdot 10^9", r"2 \cdot 10^9", "2e9db.txt"),
    #    (10976368, 800, r"2 \cdot 10^9", r"3 \cdot 10^9", "3e9db.txt"),
    #    (10395560, 768, r"3 \cdot 10^9", r"4 \cdot 10^9", "4e9db.txt"),
    #    (9932368, 744, r"4 \cdot 10^9", r"5 \cdot 10^9", "5e9db.txt"),
    #    (9584588, 720, r"5 \cdot 10^9", r"6 \cdot 10^9", "6e9db.txt"),
    #    (9385318, 707, r"6 \cdot 10^9", r"7 \cdot 10^9", "7e9db.txt"),
    #    (9071666, 685, r"7 \cdot 10^9", r"8 \cdot 10^9", "8e9db.txt"),
    #    (8975214, 679, r"8 \cdot 10^9", r"9 \cdot 10^9", "9e9db.txt"),
    #    (8788686, 666, r"9 \cdot 10^9", r"1.0 \cdot 10^{10}", "10e9db.txt"),
    #    (8642210, 664, r"1.0 \cdot 10^{10}", r"1.1 \cdot 10^{10}", "11e9db.txt"),
    #    (8477024, 652, r"1.1 \cdot 10^{10}", r"1.2 \cdot 10^{10}", "12e9db.txt"),
    #    (8383290, 645, r"1.2 \cdot 10^{10}", r"1.3 \cdot 10^{10}", "13e9db.txt"),
    #    (8275108, 638, r"1.3 \cdot 10^{10}", r"1.4 \cdot 10^{10}", "14e9db.txt"),
    #    (8143456, 628, r"1.4 \cdot 10^{10}", r"1.5 \cdot 10^{10}", "15e9db.txt"),
    #    (8106334, 626, r"1.5 \cdot 10^{10}", r"1.6 \cdot 10^{10}", "16e9db.txt"),
    #    (7959996, 615, r"1.6 \cdot 10^{10}", r"1.7 \cdot 10^{10}", "17e9db.txt"),
    #    (7903210, 611, r"1.7 \cdot 10^{10}", r"1.8 \cdot 10^{10}", "18e9db.txt"),
    #    (7849564, 607, r"1.8 \cdot 10^{10}", r"1.9 \cdot 10^{10}", "19e9db.txt"),
    #    (7781996, 602, r"1.9 \cdot 10^{10}", r"2.0 \cdot 10^{10}", "20e9db.txt"),
    #    (7822372, 605, r"2.0 \cdot 10^{10}", r"2.1 \cdot 10^{10}", "21e9db.txt"),
    #    (7636198, 591, r"2.1 \cdot 10^{10}", r"2.2 \cdot 10^{10}", "22e9db.txt"),
    #    (7562706, 586, r"2.2 \cdot 10^{10}", r"2.3 \cdot 10^{10}", "23e9db.txt"),
    #    (7593218, 588, r"2.3 \cdot 10^{10}", r"2.4 \cdot 10^{10}", "24e9db.txt"),
    #    (7505566, 582, r"2.4 \cdot 10^{10}", r"2.5 \cdot 10^{10}", "25e9db.txt"),
    #    (7409408, 575, r"2.5 \cdot 10^{10}", r"2.6 \cdot 10^{10}", "26e9db.txt"),
    #    (7312946, 567, r"2.6 \cdot 10^{10}", r"2.7 \cdot 10^{10}", "27e9db.txt"),
    #]
    if 'Fetch' in info:
        fname = "{}.txt"
        kmax = 2699
        errors = []
        if 'k' in info and not errors:
            k = info["k"].strip()
            if k.isdigit():
                k = int(k)
                if k <= kmax:
                    fname = fname.format(k)
                else:
                    errors.append(f"k must be at most {kmax}")
            else:
                errors.append(f"k must be a positive integer at most {kmax}")
        if not errors:
            filepath = os.path.expanduser('~/data/bhkssw_split/' + fname)
            if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
                return send_file(filepath, as_attachment=True)
            errors.append(f"File {fname} not found")
        for err in errors:
            flash_error(err)

    return render_template("bhkssw.html", info=info, comma=comma, title=t, bread=bread, learnmore=learnmore)

sorted_code_names = ['curve', 'simple_curve', 'mwgroup', 'gens', 'tors', 'intpts', 'cond', 'disc', 'jinv', 'cm', 'faltings', 'stable_faltings', 'rank', 'analytic_rank', 'reg', 'real_period', 'cp', 'ntors', 'sha', 'L1', 'bsd_formula', 'qexp', 'moddeg', 'manin', 'localdata', 'galrep']


Fullname = {
    'magma': 'Magma',
    'sage': 'SageMath',
    'gp': 'Pari/GP',
    'oscar': 'Oscar'
}

def ec_code(**args):
    label = curve_lmfdb_label(args['conductor'], args['iso'], args['number'])
    E = WebEC.by_label(label)
    if E == "Invalid label":
        return elliptic_curve_jump_error(label, {})
    if E == "Curve not found":
        return elliptic_curve_jump_error(label, {}, missing_curve=True)
    Ecode = E.code()
    lang = args['download_type']
    if lang not in Fullname:
        abort(404,"Invalid code language specified: " + lang)
    code = CodeSnippet(Ecode)
    return code.export_code(label, lang, sorted_code_names)


def tor_struct_search_Q(prefill="any"):
    def fix(t):
        return t + ' selected = "yes"' if prefill == t else t

    def cyc(n):
        return [fix(f"[{n}]"), "C{}".format(n)]

    def cyc2(m, n):
        return [fix("[{},{}]".format(m, n)), "C{}&times;C{}".format(m, n)]

    gps = [[fix(""), "any"], [fix("[]"), "trivial"]]
    for n in range(2,13):
        if n != 11:
            gps.append(cyc(n))
    for n in range(1,5):
        gps.append(cyc2(2,2*n))
    return "\n".join(["<select name='torsion_structure', style='width: 155px'>"] + ["<option value={}>{}</option>".format(a,b) for a,b in gps] + ["</select>"])

# route for modm reduction. Called by modm_reduction in lmfdb.js.
@ec_page.route("/adelic_image_modm_reduce")
def modm_reduce():
    label = request.args.get('label')
    data = db.ec_curvedata.lookup(label, ["adelic_level", "modm_images"])
    galois_image = db.ec_galrep.lucky({"lmfdb_label":label, "prime":0}, "adelic_gens")
    cur_lang = request.args.get('cur_lang')

    if data is None or galois_image is None:
        return "\\text{Invalid curve or adelic image not computed}"
    try:
        new_mod = int(request.args.get('m'))
        if new_mod <= 0:
            raise ValueError
    except ValueError:
        return "\\text{Invalid input, please enter a positive integer}"

    galois_level = data['adelic_level']
    modm_images = data['modm_images']
    modm_level_index = [image.split('.')[:2] for image in modm_images]
    if modm_level_index:
        relevant_m = gcd(new_mod, int(modm_level_index[-1][0]))
        index = '1' # the case where level gcd is 1
        for level_index in reversed(modm_level_index):
            if (relevant_m % int(level_index[0]) == 0):
                index = level_index[1]
                break
    else:
        # should not happen if adelic image is computed
        index = '-1'

    ans = gl2_lift(galois_image, galois_level, new_mod)
    if ans == []:
        result = "\\text{trivial group}"
    else:
        result = ",".join([str(latex(dispZmat_from_list(z,2))) for z in ans])
    result += '.' + str(new_mod) + '.' + str(ans) + '.' + cur_lang + '.' + index
    return result

def gl1_gen(M):
    # Returns a list of generators of gl1 mod M
    a = sorted(factor(M))
    q = [p[0]**p[1] for p in a]
    gens = []
    if a[0][0] == 2:
        if a[0][1] > 1:
            gens.append(CRT([-1, 1], [q[0], M/q[0]]))
        if a[0][1] > 2:
            gens.append(CRT([5, 1], [q[0], M/q[0]]))
        q.pop(0)
    for p in q:
        gens.append(CRT([primitive_root(p), 1], [p, M/p]))
    return gens

def gl1_ker(N, M):
    # Returns a list of generators for kernel of gl1 mod M projecting to mod N
    gens = gl1_gen(M)
    gens = [Mod(g, M)**(Mod(g, N).multiplicative_order()) for g in gens]
    return [int(g) for g in gens if g != 1]

def gl2_element_lifter(N, M):
    # Returns a function that lift elements of gl2 mod N to gl2 mod M.
    # Requires N | M, positive integers.
    a = factor(M)
    m = prod([p[0]**p[1] for p in a if (N % p[0]) == 0])
    # `mat` is an element of gl2 mod N written as a list
    mat_id = [1, 0, 0, 1]

    def lifter(mat):
        return [CRT([mat[i], mat_id[i]], [m, M/m]) for i in range(4)]
    return lifter

def gl2_lift_divisible(subgroup_gen, N, M):
    # Input: generators of a subgroup of gl2 mod N, integers N and M
    # Returns the lift to mod M where N | M, positive integers
    if N == M:
        return subgroup_gen.copy()
    lifter = gl2_element_lifter(N, M)
    result = [lifter(x) for x in subgroup_gen]
    result += [[1, N, 0, 1], [1, 0, N, 1], [1+N, N, M-N, 1+M-N]]
    result += [[g, 0, 0, 1] for g in gl1_ker(N, M)]
    return result

def gl2_project(subgroup_gen, M):
    # Input: generators of a subgroup of gl2 (implicitly mod N divisible by M)
    # Returns the projection to mod M (removes duplicates)
    if M == 1:
        return []

    def project(x):
        return int(Mod(x, M))
    gens = []
    unique = set()
    for g in subgroup_gen:
        reduced = tuple(project(x) for x in g)
        if reduced in unique or reduced == (1, 0, 0, 1):
            continue
        unique.add(reduced)
        gens.append(list(reduced))
    return gens

def gl2_lift(subgroup_gen, N, M):
    # Input: generators of a subgroup of gl2 mod N, and some positive integer M
    # Returns the projection and/or lift to mod M
    n = gcd(N, M)
    gens = gl2_project(subgroup_gen, n)
    return gl2_lift_divisible(gens, n, M)

# the following allows the preceding function to be used in any template via {{...}}
app.jinja_env.globals.update(tor_struct_search_Q=tor_struct_search_Q)

class ECSearchArray(SearchArray):
    noun = "curve"
    sorts = [("", "conductor", ["conductor", "iso_nlabel", "lmfdb_number"]),
             #("cremona_label", "cremona label", ["conductor", "Ciso", "Cnumber"]), # Ciso is text so this doesn't sort correctly
             ("rank", "rank", ["rank", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("torsion", "torsion", ["torsion", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("cm_discriminant", "CM discriminant", [("cm", -1), "conductor", "iso_nlabel", "lmfdb_number"]),
             ("regulator", "regulator", ["regulator", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("sha", "analytic &#1064;", ["sha", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("class_size", "isogeny class size", ["class_size", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("class_deg", "isogeny class degree", ["class_deg", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("num_int_pts", "integral points", ["num_int_pts", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("degree", "modular degree", ["degree", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("adelic_level", "adelic level", ["adelic_level", "adelic_index", "adelic_genus"]),
             ("adelic_index", "adelic index", ["adelic_index", "adelic_level", "adelic_genus"]),
             ("adelic_genus", "adelic genus", ["adelic_genus", "adelic_level", "adelic_index"]),
             ("faltings_height", "Faltings height", ["faltings_height", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("abc_quality", "$abc$ quality", ["abc_quality", "conductor", "iso_nlabel", "lmfdb_number"]),
             ("szpiro_ratio", "Szpiro ratio", ["szpiro_ratio", "conductor", "iso_nlabel", "lmfdb_number"])]
    jump_example = "11.a2"
    jump_egspan = "e.g. 11.a2 or 389.a or 11a1 or 389a or [0,1,1,-2,0] or [-3024, 46224] or y^2 = x^3 + 1"
    jump_prompt = "Label or coefficients"
    jump_knowl = "ec.q.search_input"
    null_column_explanations = {
                                 'adelic_level': False, # not applicable to CM curves, computed for all non-CM curves
                                 'adelic_index': False, # not applicable to CM curves, computed for all non-CM curves
                                 'adelic_genus': False, # not applicable to CM curves, computed for all non-CM curves
                               }

    def __init__(self):
        conductor_quantifier = SelectBox(
            name='conductor_type',
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides','divides'),
                     ('multiple','multiple of'),
                     ],
            min_width=85)
        cond = TextBoxWithSelect(
            name="conductor",
            label="Conductor",
            knowl="ec.q.conductor",
            example="389",
            example_span="389 or 100-200",
            select_box=conductor_quantifier)
        disc = TextBox(
            name="discriminant",
            label="Discriminant",
            knowl="ec.discriminant",
            example="389",
            example_span="389 or 100-200")
        jinv = TextBox(
            name="jinv",
            label="j-invariant",
            knowl="ec.q.j_invariant",
            example="1728",
            example_span="0 or 1728 or -4096/11")
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="ec.rank",
            example="0")
        # ℤ is &#8484; in html
        torsion_opts = ([("", ""), ("[]", "trivial")]
                        + [("%s" % n, "order %s" % n) for n in range(4, 16, 4)]
                        + [("[%s]" % n, "ℤ/%sℤ" % n) for n in range(2, 13) if n != 11]
                        + [("[2,%s]" % n, "ℤ/2ℤ&oplus;ℤ/%sℤ" % n) for n in range(2, 10, 2)])
        torsion = SelectBox(
            name="torsion",
            label="Torsion",
            knowl="ec.torsion_subgroup",
            example="C3",
            options=torsion_opts)
        cm_opts = ([('', ''), ('noCM', 'no potential CM'), ('CM', 'potential CM')]
                   + [('-4,-16', 'CM field Q(sqrt(-1))'), ('-3,-12,-27', 'CM field Q(sqrt(-3))'), ('-7,-28', 'CM field Q(sqrt(-7))')]
                   + [('-%d' % d, 'CM discriminant -%d' % d) for d in [3,4,7,8,11,12,16,19,27,28,43,67,163]])
        cm = SelectBox(
            name="cm",
            label="Complex multiplication",
            example="potential CM by Q(i)",
            knowl="ec.complex_multiplication",
            options=cm_opts)
        optimal = SelectBox(
            name="optimal",
            label="Curves per isogeny class",
            knowl="ec.isogeny_class",
            example="all, one",
            options=[("", "all"),
                     ("on", "one")])
        bad_quant = SubsetBox(
            name="bad_quantifier")
        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            label="Bad primes $p$&emsp;", # trailing &emsp; prevents caption moving when toggling advanced search opts
            short_label=r"Bad$\ p$",
            knowl="ec.q.reduction_type",
            example="5,13",
            select_box=bad_quant)
        sha = TextBox(
            name="sha",
            label="Analytic order of &#1064;",
            knowl="ec.analytic_sha_order",
            example="4",
            advanced=True)
        isodeg = TextBox(
            name="isogeny_degrees",
            label="Cyclic isogeny degree",
            knowl="ec.isogeny",
            example="16",
            advanced=True)
        class_size = TextBox(
            name="class_size",
            label="Isogeny class size",
            knowl="ec.isogeny_class",
            example="4",
            advanced=True)
        class_deg = TextBox(
            name="class_deg",
            label="Isogeny class degree",
            knowl="ec.isogeny_class_degree",
            example="16",
            advanced=True)
        num_int_pts = TextBox(
            name="num_int_pts",
            label="Integral points",
            knowl="ec.q.integral_points",
            example="2",
            example_span="2 or 4-15",
            advanced=True)
        sha_quant = SubsetBox(
            name="sha_quantifier")
        sha_primes = TextBoxWithSelect(
            name="sha_primes",
            label="$p$ dividing |&#1064;|",
            short_label=r"$p\ $div$\ $|&#1064;|",
            knowl="ec.analytic_sha_order",
            example="3,5",
            select_box=sha_quant,
            advanced=True)
        regulator = TextBox(
            name="regulator",
            label="Regulator",
            knowl="ec.q.regulator",
            example="8.4-9.1",
            advanced=True)
        faltings_height = TextBox(
            name="faltings_height",
            label="Faltings height",
            knowl="ec.q.faltings_height",
            example="-1-2",
            advanced=True)
        reduction_opts = ([("", ""),
                           ("semistable", "semistable"),
                           ("not semistable", "not semistable"),
                           ("potentially good", "potentially good"),
                           ("not potentially good", "not potentially good")])
        reduction = SelectBox(
            name="reduction",
            label="Reduction",
            example="semistable",
            knowl="ec.reduction",
            options=reduction_opts,
            advanced=True)
        galois_image = TextBox(
            name="galois_image",
            label=r"Galois image",
            short_label=r"Galois image",
            example="13S4 or 13.91.3.2",
            knowl="ec.galois_image_search",
            advanced=True)
        nonmax_quant = SubsetBox(
            name="nonmax_quantifier")
        nonmax_primes = TextBoxWithSelect(
            name="nonmax_primes",
            label=r"Nonmaximal $\ell$",
            short_label=r"Nonmax$\ \ell$",
            knowl="ec.maximal_elladic_galois_rep",
            example="2,3",
            select_box=nonmax_quant,
            advanced=True)
        adelic_level = TextBox(
            name="adelic_level",
            label="Adelic level",
            knowl="ec.galois_rep_adelic_image",
            example="550",
            advanced=True)
        adelic_index = TextBox(
            name="adelic_index",
            label="Adelic index",
            knowl="ec.galois_rep_adelic_image",
            example="1200",
            advanced=True)
        adelic_genus = TextBox(
            name="adelic_genus",
            label="Adelic genus",
            knowl="ec.galois_rep_adelic_image",
            example="3",
            advanced=True)
        abc_quality = TextBox(
            name="abc_quality",
            label="$abc$ quality",
            knowl="ec.q.abc_quality",
            example="1.5-",
            advanced=True)
        szpiro_ratio = TextBox(
            name="szpiro_ratio",
            label="Szpiro ratio",
            knowl="ec.q.szpiro_ratio",
            example="8-",
            advanced=True)

        manin_constant = TextBox(
            name="manin_constant",
            label="Manin constant",
            knowl="ec.q.manin_constant",
            example="2",
            advanced=True)

        count = CountBox()

        self.browse_array = [
            [cond, bad_primes],
            [disc, optimal],
            [jinv, cm],
            [rank, torsion],
            [class_size, class_deg],
            [num_int_pts, isodeg],
            [sha, sha_primes],
            [regulator, reduction],
            [galois_image, nonmax_primes],
            [adelic_level, adelic_index],
            [adelic_genus, faltings_height],
            [abc_quality, szpiro_ratio],
            [count, manin_constant]
            ]

        self.refine_array = [
            [cond, disc, jinv, rank],
            [bad_primes, optimal, cm, torsion],
            [class_deg, isodeg, class_size, num_int_pts],
            [sha, sha_primes, regulator, reduction, faltings_height],
            [galois_image, adelic_level, adelic_index, adelic_genus],
            [nonmax_primes, abc_quality, szpiro_ratio, manin_constant],
            ]
