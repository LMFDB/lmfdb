# -*- coding: utf-8 -*-

import re
from ast import literal_eval
from collections import defaultdict

from flask import render_template, url_for, request, redirect, abort
from sage.all import ZZ, QQ, PolynomialRing, cached_function, magma, prod

from lmfdb import db
from lmfdb.utils import (
    CountBox,
    Downloader,
    SearchArray,
    SelectBox,
    StatsDisplay,
    SubsetBox,
    TextBox,
    TextBoxWithSelect,
    YesNoBox,
    comma,
    display_knowl,
    flash_error,
    formatters,
    parse_bool,
    parse_bracketed_posints,
    parse_bracketed_rats,
    parse_ints,
    parse_primes,
    redirect_no_cache,
    search_wrap,
    to_dict,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.sato_tate_groups.main import st_link_by_name
from lmfdb.genus2_curves import g2c_page
from lmfdb.genus2_curves.web_g2c import WebG2C, min_eqn_pretty, st0_group_name

###############################################################################
# List and dictionaries needed for routing and searching
###############################################################################

# lists determine display order in drop down lists, dictionary key is the
# database entry, dictionary value is the display value
st_group_list = [
    "J(C_2)",
    "J(C_4)",
    "J(C_6)",
    "J(D_2)",
    "J(D_3)",
    "J(D_4)",
    "J(D_6)",
    "J(T)",
    "J(O)",
    "C_{2,1}",
    "C_{6,1}",
    "D_{2,1}",
    "D_{3,2}",
    "D_{4,1}",
    "D_{4,2}",
    "D_{6,1}",
    "D_{6,2}",
    "O_1",
    "E_1",
    "E_2",
    "E_3",
    "E_4",
    "E_6",
    "J(E_1)",
    "J(E_2)",
    "J(E_3)",
    "J(E_4)",
    "J(E_6)",
    "F_{a,b}",
    "F_{ac}",
    "N(U(1)xSU(2))",
    "SU(2)xSU(2)",
    "N(SU(2)xSU(2))",
    "USp(4)",
]
st_group_dict = {a: a for a in st_group_list}

# End_QQbar tensored with RR determines ST0 (which is the search parameter):
real_geom_end_alg_list = ["M_2(C)", "M_2(R)", "C x C", "C x R", "R x R", "R"]
real_geom_end_alg_to_ST0_dict = {
    "M_2(C)": "U(1)",
    "M_2(R)": "SU(2)",
    "C x C": "U(1) x U(1)",
    "C x R": "U(1) x SU(2)",
    "R x R": "SU(2) x SU(2)",
    "R": "USp(4)",
}

# End tensored with QQ
end_alg_list = ["Q", "RM", "CM", "Q x Q", "M_2(Q)"]
end_alg_dict = {x: x for x in end_alg_list}

# End_QQbar tensored with QQ
geom_end_alg_list = [
    "Q",
    "RM",
    "CM",
    "QM",
    "Q x Q",
    "CM x Q",
    "CM x CM",
    "M_2(Q)",
    "M_2(CM)",
]
geom_end_alg_dict = {x: x for x in geom_end_alg_list}

aut_grp_list = ["2.1", "4.1", "4.2", "6.2", "8.3", "12.4"]
aut_grp_dict = {
    "2.1": "C2",
    "4.1": "C4",
    "4.2": "V4",
    "6.2": "C6",
    "8.3": "D4",
    "12.4": "D6",
}
aut_grp_dict_pretty = {
    "2.1": "$C_2$",
    "4.1": "$C_4$",
    "4.2": "$C_2^2$",
    "6.2": "$C_6$",
    "8.3": "$D_4$",
    "12.4": "$D_6$",
}

geom_aut_grp_list = ["2.1", "4.2", "8.3", "10.2", "12.4", "24.8", "48.29"]
geom_aut_grp_dict = {
    "2.1": "C2",
    "4.2": "V4",
    "8.3": "D4",
    "10.2": "C10",
    "12.4": "D6",
    "24.8": "C3:D4",
    "48.29": "GL(2,3)",
}
geom_aut_grp_dict_pretty = {
    "2.1": "$C_2$",
    "4.2": "$C_2^2$",
    "8.3": "$D_4$",
    "10.2": "$C_{10}$",
    "12.4": "$D_6$",
    "24.8": "$C_3:D_4$",
    "48.29": r"$\GL(2,3)$",
}

###############################################################################
# Routing for top level and random_curve
###############################################################################


def learnmore_list():
    return [
        ("Source and acknowledgments", url_for(".source_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Genus 2 curve labels", url_for(".labels_page")),
    ]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def get_bread(tail=[]):
    base = [("Genus 2 curves", url_for(".index")), (r"$\Q$", url_for(".index_Q"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


@g2c_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))


@g2c_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=G2CSearchArray())
    if len(info) > 1:
        return genus2_curve_search(info)
    info["stats"] = G2C_stats()
    info["stats_url"] = url_for(".statistics")
    info["conductor_list"] = (
        "1-499",
        "500-999",
        "1000-9999",
        "10000-99999",
        "100000-1000000",
    )
    info["discriminant_list"] = (
        "1-499",
        "500-999",
        "1000-9999",
        "10000-99999",
        "100000-1000000",
    )
    info["equation_search"] = has_magma()
    title = r"Genus 2 curves over $\Q$"
    return render_template(
        "g2c_browse.html",
        info=info,
        title=title,
        learnmore=learnmore_list(),
        bread=get_bread(),
    )


@g2c_page.route("/Q/random/")
@redirect_no_cache
def random_curve():
    label = db.g2c_curves.random()
    return url_for_curve_label(label)


@g2c_page.route("/Q/interesting")
def interesting():
    return interesting_knowls(
        "g2c",
        db.g2c_curves,
        url_for_curve_label,
        regex=re.compile(r"\d+\.[a-z]+\.\d+\.\d+"),
        title="Some interesting genus 2 curves",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )


###############################################################################
# Curve and isogeny class pages
###############################################################################


@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/<int:num>")
def by_url_curve_label(cond, alpha, disc, num):
    label = str(cond) + "." + alpha + "." + str(disc) + "." + str(num)
    return render_curve_webpage(label)


@g2c_page.route("/Q/<int:cond>/<alpha>/<int:disc>/")
def by_url_isogeny_class_discriminant(cond, alpha, disc):
    data = to_dict(request.args, search_array=G2CSearchArray())
    clabel = str(cond) + "." + alpha
    # if the isogeny class is not present in the database, return a 404 (otherwise title and bread crumbs refer to a non-existent isogeny class)
    if not db.g2c_curves.exists({"class": clabel}):
        return abort(404, "Genus 2 isogeny class %s not found in database." % clabel)
    data["title"] = "Genus 2 curves in isogeny class %s of discriminant %s" % (
        clabel,
        disc,
    )
    data["bread"] = get_bread(
        [
            ("%s" % cond, url_for(".by_conductor", cond=cond)),
            (
                "%s" % alpha,
                url_for(".by_url_isogeny_class_label", cond=cond, alpha=alpha),
            ),
            (
                "%s" % disc,
                url_for(
                    ".by_url_isogeny_class_discriminant",
                    cond=cond,
                    alpha=alpha,
                    disc=disc,
                ),
            ),
        ]
    )
    if len(request.args) > 0:
        # if conductor or discriminant changed, fall back to a general search
        if ("cond" in request.args and request.args["cond"] != str(cond)) or (
            "abs_disc" in request.args and request.args["abs_disc"] != str(disc)
        ):
            return redirect(url_for(".index", **request.args), 307)
        data["title"] += " Search results"
        data["bread"].append(("Search results", ""))
    data["cond"] = cond
    data["class"] = clabel
    data["abs_disc"] = disc
    return genus2_curve_search(data)


@g2c_page.route("/Q/<int:cond>/<alpha>/")
def by_url_isogeny_class_label(cond, alpha):
    return render_isogeny_class_webpage(str(cond) + "." + alpha)


@g2c_page.route("/Q/<int:cond>/")
def by_conductor(cond):
    data = to_dict(request.args, search_array=G2CSearchArray())
    data["title"] = "Genus 2 curves of conductor %s" % cond
    data["bread"] = get_bread([("%s" % cond, url_for(".by_conductor", cond=cond))])
    if len(request.args) > 0:
        # if conductor changed, fall back to a general search
        if "cond" in request.args and request.args["cond"] != str(cond):
            return redirect(url_for(".index", **request.args), 307)
        data["title"] += " Search results"
        data["bread"].append(("Search results", ""))
    data["cond"] = cond
    return genus2_curve_search(data)


@g2c_page.route("/Q/<label>")
def by_label(label):
    # handles curve, isogeny class, and Lhash labels
    if not label.strip():  # just spaces
        return redirect(url_for(".index"))
    return genus2_curve_search({"jump": label})


def render_curve_webpage(label):
    try:
        g2c = WebG2C.by_label(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "g2c_curve.html",
        properties=g2c.properties,
        info={"aut_grp_dict": aut_grp_dict, "geom_aut_grp_dict": geom_aut_grp_dict},
        data=g2c.data,
        code=g2c.code,
        bread=g2c.bread,
        learnmore=learnmore_list(),
        title=g2c.title,
        friends=g2c.friends,
        KNOWL_ID="g2c.%s" % label,
    )


def render_isogeny_class_webpage(label):
    try:
        g2c = WebG2C.by_label(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "g2c_isogeny_class.html",
        properties=g2c.properties,
        data=g2c.data,
        bread=g2c.bread,
        learnmore=learnmore_list(),
        title=g2c.title,
        friends=g2c.friends,
        KNOWL_ID="g2c.%s" % label,
    )


def url_for_curve_label(label):
    slabel = label.split(".")
    return url_for(
        ".by_url_curve_label",
        cond=slabel[0],
        alpha=slabel[1],
        disc=slabel[2],
        num=slabel[3],
    )


def url_for_isogeny_class_label(label):
    slabel = label.split(".")
    return url_for(".by_url_isogeny_class_label", cond=slabel[0], alpha=slabel[1])


def class_from_curve_label(label):
    return ".".join(label.split(".")[:2])


################################################################################
# Searching
################################################################################
@cached_function
def has_magma():
    try:
        magma.eval("2")
        return True
    except (TypeError, RuntimeError):
        return False


def genus2_lookup_equation(f):
    if not has_magma():
        return None
    f.replace(" ", "")
    # TODO allow other variables, if so, fix the error message accordingly
    R = PolynomialRing(QQ, "x")
    if ("x" in f and "," in f) or "],[" in f:
        if "],[" in f:
            e = f.split("],[")
            f = [R(literal_eval(e[0][1:] + "]")), R(literal_eval("[" + e[1][0:-1]))]
        else:
            e = f.split(",")
            f = [R(str(e[0][1:])), R(str(e[1][0:-1]))]
    else:
        f = R(str(f))
    try:
        C = magma.HyperellipticCurve(f)
        g2 = magma.G2Invariants(C)
    except TypeError:
        return None
    g2 = str([str(i) for i in g2]).replace(" ", "")
    for r in db.g2c_curves.search({"g2_inv": g2}):
        eqn = literal_eval(r["eqn"])
        D = magma.HyperellipticCurve(R(eqn[0]), R(eqn[1]))
        # there is recursive bug in sage
        if str(magma.IsIsomorphic(C, D)) == "true":
            return r["label"]
    return None


def geom_inv_to_G2(inv):
    def igusa_clebsch_to_G2(Ilist):
        # first Igusa-Clebsch to Igusa, i.e., I |-> J
        I2, I4, I6, I10 = Ilist
        J2 = I2 / 8
        J4 = (4 * J2 ** 2 - I4) / 96
        J6 = (8 * J2 ** 3 - 160 * J2 * J4 - I6) / 576
        J8 = (J2 * J6 - J4 ** 2) / 4  # we won't use this one at all
        J10 = I10 / 4096
        return igusa_to_G2([J2, J4, J6, J8, J10])

    def igusa_to_G2(Jlist):
        monomials = [
            [5, 0, 0, 0, -1],  # g1
            [3, 1, 0, 0, -1],  # g2
            [2, 0, 1, 0, -1],  # g3
            # if J2 = 0
            [0, 5, 0, 0, -2],  # g2'
            [0, 1, 1, 0, -1],  # g3'
            # if J2 = J4 = 0
            [0, 0, 5, 0, -3],  # g3''
        ]
        # the affine invariants defining G2
        g1, g2, g3, g2a, g3a, g3b = tuple(
            prod(j ** w for j, w in zip(Jlist, m)) for m in monomials
        )
        if g1 != 0:  # if J2 != 0
            return (g1, g2, g3)
        elif g2a != 0:  # ie J2 = 0 and J4 !=0
            return (0, g2a, g3a)
        else:  # if J2 = J4 = 0
            return (0, 0, g3b)

    if len(inv) == 3:
        return inv
    elif len(inv) == 4:
        return igusa_clebsch_to_G2(inv)
    else:  # len(inv) == 5
        return igusa_to_G2(inv)


TERM_RE = r"(\+|-)?(\d*x|\d+\*x|\d+)(\^\d+)?"
STERM_RE = r"(\+|-)(\d*x|\d+\*x|\d+)(\^\d+)?"
POLY_RE = TERM_RE + "(" + STERM_RE + ")*"
ZLIST_RE = r"\[\d+(,\d+)*\]"


def genus2_jump(info):
    jump = info["jump"].replace(" ", "")
    if re.match(r"^\d+\.[a-z]+\.\d+\.\d+$", jump):
        return redirect(url_for_curve_label(jump), 301)
    elif re.match(r"^\d+\.[a-z]+$", jump):
        return redirect(url_for_isogeny_class_label(jump), 301)
    elif re.match(r"^\#\d+$", jump) and ZZ(jump[1:]) < 2 ** 61:
        # Handle direct Lhash input
        c = db.g2c_curves.lucky({"Lhash": jump[1:].strip()}, projection="class")
        if c:
            return redirect(url_for_isogeny_class_label(c), 301)
        else:
            errmsg = "hash %s not found"
    elif has_magma() and (
        re.match(r"^" + POLY_RE + r"$", jump)
        or re.match(r"^\[" + POLY_RE + r"," + POLY_RE + r"\]$", jump)
        or re.match(r"^" + ZLIST_RE + r"$", jump)
        or re.match(r"^\[" + ZLIST_RE + r"," + ZLIST_RE + r"\]$", jump)
    ):
        label = genus2_lookup_equation(jump)
        if label:
            return redirect(url_for_curve_label(label), 301)
        errmsg = "y^2 = %s is not the equation of a genus 2 curve in the database"
    else:
        errmsg = "%s is not valid input. Expected a label, e.g., 169.a.169.1"
        if has_magma():
            errmsg += ", or a univariate polynomial in $x$, e.g., x^5 + 1"
        else:
            errmsg += "."
    flash_error(errmsg, jump)
    return redirect(url_for(".index"))


class G2C_download(Downloader):
    table = db.g2c_curves
    title = "Genus 2 curves"
    columns = "eqn"
    column_wrappers = {"eqn": literal_eval}
    data_format = ["[[f coeffs],[h coeffs]]"]
    data_description = "defining the hyperelliptic curve y^2+h(x)y=f(x)."
    function_body = {
        "magma": [
            "R<x>:=PolynomialRing(Rationals());",
            "return [HyperellipticCurve(R![c:c in r[1]],R![c:c in r[2]]):r in data];",
        ],
        "sage": [
            "R.<x>=PolynomialRing(QQ)",
            "return [HyperellipticCurve(R(r[0]),R(r[1])) for r in data]",
        ],
        "gp": ["[apply(Polrev,c)|c<-data];"],
    }


def parse_sort(info, query):
    default = ["cond", "class", "abs_disc", "disc_sign", "label"]
    d = defaultdict(
        lambda: default,
        (
            ("", default),
            ("abs_disc", ["abs_disc"] + default),
            ("num_rat_pts1", [("num_rat_pts", 1)] + default),
            ("num_rat_pts-1", [("num_rat_pts", -1)] + default),
            ("num_rat_wpts1", [("num_rat_wpts", 1)] + default),
            ("num_rat_wpts-1", [("num_rat_wpts", -1)] + default),
            ("torsion_order1", [("torsion_order", 1)] + default),
            ("torsion_order-1", [("torsion_order", -1)] + default),
            ("analytic_sha1", [("analytic_sha", 1)] + default),
            ("analytic_sha-1", [("analytic_sha", -1)] + default),
        ),
    )
    query["__sort__"] = d[info.get("sort_order")]


@search_wrap(
    template="g2c_search_results.html",
    table=db.g2c_curves,
    title="Genus 2 curve search results",
    err_title="Genus 2 curves search input error",
    shortcuts={"jump": genus2_jump, "download": G2C_download()},
    projection=[
        "label",
        "eqn",
        "st_group",
        "is_gl2_type",
        "is_simple_geom",
        "analytic_rank",
    ],
    cleaners={
        "class": lambda v: class_from_curve_label(v["label"]),
        "equation_formatted": lambda v: min_eqn_pretty(literal_eval(v.pop("eqn"))),
        "st_group_link": lambda v: st_link_by_name(1, 4, v.pop("st_group")),
    },
    bread=lambda: get_bread("Search results"),
    learnmore=learnmore_list,
    url_for_label=lambda label: url_for(".by_label", label=label),
)
def genus2_curve_search(info, query):
    parse_ints(info, query, "abs_disc", "absolute discriminant")
    parse_bool(info, query, "is_gl2_type", "is of GL2-type")
    parse_bool(info, query, "has_square_sha", "has square Sha")
    parse_bool(info, query, "locally_solvable", "is locally solvable")
    parse_bool(info, query, "is_simple_geom", "is geometrically simple")
    parse_ints(info, query, "cond", "conductor")
    if info.get("analytic_sha") == "None":
        query["analytic_sha"] = None
    else:
        parse_ints(info, query, "analytic_sha", "analytic order of sha")
    parse_ints(info, query, "num_rat_pts", "rational points")
    parse_ints(info, query, "num_rat_wpts", "rational Weierstrass points")
    parse_bracketed_posints(
        info,
        query,
        "torsion",
        "torsion structure",
        maxlength=4,
        check_divisibility="increasing",
    )
    parse_ints(info, query, "torsion_order", "torsion order")
    if "torsion" in query and "torsion_order" not in query:
        t_o = 1
        for n in query["torsion"]:
            t_o *= int(n)
        query["torsion_order"] = t_o
    if "torsion" in query:
        query["torsion_subgroup"] = str(query["torsion"]).replace(" ", "")
        query.pop("torsion")  # search using string key, not array of ints
    parse_bracketed_rats(
        info,
        query,
        "geometric_invariants",
        qfield="g2_inv",
        minlength=3,
        maxlength=5,
        listprocess=geom_inv_to_G2,
        split=False,
        keepbrackets=True,
    )

    parse_ints(info, query, "two_selmer_rank", "2-Selmer rank")
    parse_ints(info, query, "analytic_rank", "analytic rank")
    # G2 invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
    if "g20" in info and "g21" in info and "g22" in info:
        query["g2_inv"] = "['%s','%s','%s']" % (info["g20"], info["g21"], info["g22"])
    if "class" in info:
        query["class"] = info["class"]
    # Support legacy aut_grp_id
    if info.get("aut_grp_id"):
        info["aut_grp_label"] = ".".join(info.pop("aut_grp_id")[1:-1].split(","))
    if info.get("geom_aut_grp_id"):
        info["geom_aut_grp_label"] = ".".join(info.pop("aut_grp_id")[1:-1].split(","))
    for fld in (
        "st_group",
        "real_geom_end_alg",
        "aut_grp_label",
        "geom_aut_grp_label",
        "end_alg",
        "geom_end_alg",
    ):
        if info.get(fld):
            query[fld] = info[fld]
    parse_primes(
        info,
        query,
        "bad_primes",
        name="bad primes",
        qfield="bad_primes",
        mode=info.get("bad_quantifier"),
    )
    info["curve_url"] = url_for_curve_label
    info["class_url"] = url_for_isogeny_class_label
    parse_sort(info, query)


################################################################################
# Statistics
################################################################################


class G2C_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for genus 2 curves over Q
    """

    def __init__(self):
        self.ncurves = comma(db.g2c_curves.count())
        self.max_D = comma(db.g2c_curves.max("abs_disc"))
        self.disc_knowl = display_knowl(
            "g2c.abs_discriminant", title="absolute discriminant"
        )

    @property
    def short_summary(self):
        stats_url = url_for(".statistics")
        g2c_knowl = display_knowl("g2c.g2curve", title="genus 2 curves")
        return (
            r'The database currently contains %s %s over $\Q$ of %s up to %s.  Here are some <a href="%s">further statistics</a>.'
            % (self.ncurves, g2c_knowl, self.disc_knowl, self.max_D, stats_url)
        )

    @property
    def summary(self):
        nclasses = comma(db.lfunc_instances.count({"type": "G2Q"}))
        return (
            "The database currently contains %s genus 2 curves in %s isogeny classes, with %s at most %s."
            % (self.ncurves, nclasses, self.disc_knowl, self.max_D)
        )

    table = db.g2c_curves
    baseurl_func = ".index_Q"
    knowls = {
        "num_rat_pts": "g2c.num_rat_pts",
        "num_rat_wpts": "g2c.num_rat_wpts",
        "aut_grp_label": "g2c.aut_grp",
        "geom_aut_grp_label": "g2c.geom_aut_grp",
        "analytic_rank": "g2c.analytic_rank",
        "two_selmer_rank": "g2c.two_selmer_rank",
        "analytic_sha": "g2c.analytic_sha",
        "has_square_sha": "g2c.has_square_sha",
        "locally_solvable": "g2c.locally_solvable",
        "is_gl2_type": "g2c.gl2type",
        "real_geom_end_alg": "g2c.st_group_identity_component",
        "st_group": "g2c.st_group",
        "torsion_order": "g2c.torsion_order",
    }
    short_display = {
        "num_rat_pts": "rational points",
        "num_rat_wpts": "Weierstrass points",
        "aut_grp_label": "automorphism group",
        "geom_aut_grp_label": "automorphism group",
        "two_selmer_rank": "2-Selmer rank",
        "analytic_sha": "analytic order of &#1064;",
        "has_square_sha": "has square &#1064;",
        "is_gl2_type": "is of GL2-type",
        "real_geom_end_alg": "identity component",
        "st_group": "Sato-Tate group",
        "torsion_order": "torsion order",
    }
    top_titles = {
        "num_rat_pts": "rational points",
        "num_rat_wpts": "rational Weierstrass points",
        "aut_grp_label": r"$\mathrm{Aut}(X)$",
        "geom_aut_grp_label": r"$\mathrm{Aut}(X_{\overline{\mathbb{Q}}})$",
        "analytic_sha": "analytic order of &#1064;",
        "has_square_sha": "squareness of &#1064;",
        "locally_solvable": "local solvability",
        "is_gl2_type": r"$\mathrm{GL}_2$-type",
        "real_geom_end_alg": "Sato-Tate group identity components",
        "st_group": "Sato-Tate groups",
        "torsion_order": "torsion subgroup orders",
    }
    formatters = {
        "aut_grp_label": lambda x: aut_grp_dict_pretty.get(x, x),
        "geom_aut_grp_label": lambda x: geom_aut_grp_dict_pretty[x],
        "has_square_sha": formatters.boolean,
        "is_gl2_type": formatters.boolean,
        "real_geom_end_alg": lambda x: "\\(" + st0_group_name(x) + "\\)",
        "st_group": lambda x: st_link_by_name(1, 4, x),
    }
    query_formatters = {
        "aut_grp_label": lambda x: "aut_grp_label=%s" % x,
        "geom_aut_grp_label": lambda x: "geom_aut_grp_label=%s" % x,
        "real_geom_end_alg": lambda x: "real_geom_end_alg=%s" % x,
        "st_group": lambda x: "st_group=%s" % x,
    }

    stat_list = [
        {"cols": "num_rat_pts", "totaler": {"avg": True}},
        {"cols": "num_rat_wpts", "totaler": {"avg": True}},
        {"cols": "aut_grp_label"},
        {"cols": "geom_aut_grp_label"},
        {"cols": "analytic_rank", "totaler": {"avg": True}},
        {"cols": "two_selmer_rank", "totaler": {"avg": True}},
        {"cols": "has_square_sha"},
        {"cols": "analytic_sha", "totaler": {"avg": True}},
        {"cols": "locally_solvable"},
        {"cols": "is_gl2_type"},
        {"cols": "real_geom_end_alg"},
        {"cols": "st_group"},
        {"cols": "torsion_order", "totaler": {"avg": True}},
    ]


@g2c_page.route("/Q/stats")
def statistics():
    title = r"Genus 2 curves over $\Q$: Statistics"
    bread = get_bread("Statistics")
    return render_template(
        "display_stats.html",
        info=G2C_stats(),
        title=title,
        bread=bread,
        learnmore=learnmore_list(),
    )


@g2c_page.route("/Q/Source")
def source_page():
    t = r"Source and acknowledgments for genus 2 curve data over $\Q$"
    bread = get_bread("Source")
    return render_template(
        "double.html",
        kid="rcs.source.g2c",
        kid2="rcs.ack.g2c",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )


@g2c_page.route("/Q/Completeness")
def completeness_page():
    t = r"Completeness of genus 2 curve data over $\Q$"
    bread = get_bread("Completeness")
    return render_template(
        "single.html",
        kid="rcs.cande.g2c",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )


@g2c_page.route("/Q/Reliability")
def reliability_page():
    t = r"Reliability of genus 2 curve data over $\Q$"
    bread = get_bread("Reliability")
    return render_template(
        "single.html",
        kid="rcs.rigor.g2c",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )


@g2c_page.route("/Q/Labels")
def labels_page():
    t = r"Labels for genus 2 curves over $\Q$"
    bread = get_bread("Labels")
    return render_template(
        "single.html",
        kid="g2c.label",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("labels"),
    )


class G2CSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"

    def __init__(self):
        geometric_invariants = TextBox(
            name="geometric_invariants",
            knowl="g2c.geometric_invariants",
            label=r"\(\overline{\Q}\)-invariants",
            example="[8,3172,30056,-692224] or [-1/169,33/169,43/169]",
            width=689,
            short_width=190 * 3 - 10 * 3,
            colspan=(1, 4, 3),
            example_span="",
        )

        bad_quantifier = SubsetBox(
            name="bad_quantifier",
            min_width=115,
        )

        bad_primes = TextBoxWithSelect(
            name="bad_primes",
            knowl="g2c.good_reduction",
            label="Bad primes",
            short_label=r"Bad \(p\)",
            example="5,13",
            example_span="2 or 2,3,5",
            select_box=bad_quantifier,
        )

        conductor = TextBox(
            name="cond",
            knowl="ag.conductor",
            label="Conductor",
            example="169",
            example_span="169, 100-1000",
        )

        discriminant = TextBox(
            name="abs_disc",
            knowl="g2c.abs_discriminant",
            label="Absolute discriminant",
            short_label="Absolute discriminant",
            example="169",
            example_span="169, 0-1000",
        )

        rational_points = TextBox(
            name="num_rat_pts",
            knowl="g2c.num_rat_pts",
            label="Rational points*",
            example="1",
            example_span="0, 20-26",
        )

        rational_weirstrass_points = TextBox(
            name="num_rat_wpts",
            knowl="g2c.num_rat_wpts",
            label="Rational Weierstrass points",
            short_label="Weierstrass points",
            example="1",
            example_span="1, 0-6",
        )

        torsion_order = TextBox(
            name="torsion_order",
            knowl="g2c.torsion_order",
            label="Torsion order",
            example="2",
        )

        torsion_structure = TextBox(
            name="torsion",
            knowl="g2c.torsion",
            label="Torsion structure",
            short_label="Torsion",
            example="[2,2,2]",
        )

        two_selmer_rank = TextBox(
            name="two_selmer_rank",
            knowl="g2c.two_selmer_rank",
            label="2-Selmer rank",
            example="1",
        )

        analytic_sha = TextBox(
            name="analytic_sha",
            knowl="g2c.analytic_sha",
            label="Analytic order of &#1064;*",
            short_label="Analytic &#1064;*",
            example="2",
        )

        analytic_rank = TextBox(
            name="analytic_rank",
            knowl="g2c.analytic_rank",
            label="Analytic rank*",
            example="1",
        )

        is_gl2_type = YesNoBox(
            name="is_gl2_type",
            knowl="g2c.gl2type",
            label=r"$\GL_2$-type",
        )

        st_group = SelectBox(
            name="st_group",
            knowl="g2c.st_group",
            label="Sato-Tate group",
            short_label=r"\(\mathrm{ST}(X)\)",
            options=([("", "")] + [(elt, st_group_dict[elt]) for elt in st_group_list]),
        )

        st_group_identity_component = SelectBox(
            name="real_geom_end_alg",
            knowl="g2c.st_group_identity_component",
            label="Sate-Tate identity component",
            short_label=r"\(\mathrm{ST}^0(X)\)",
            options=(
                [("", "")]
                + [
                    (elt, real_geom_end_alg_to_ST0_dict[elt])
                    for elt in real_geom_end_alg_list
                ]
            ),
        )

        Q_automorphism = SelectBox(
            name="aut_grp_label",
            knowl="g2c.aut_grp",
            label=r"\(\Q\)-automorphism group",
            short_label=r"\(\mathrm{Aut}(X)\)",
            options=([("", "")] + [(elt, aut_grp_dict[elt]) for elt in aut_grp_list]),
        )

        geometric_automorphism = SelectBox(
            name="geom_aut_grp_label",
            knowl="g2c.aut_grp",
            label=r"\(\overline{\Q}\)-automorphism group",
            short_label=r"\(\mathrm{Aut}(X_{\overline{\Q}})\)",
            options=(
                [("", "")]
                + [(elt, geom_aut_grp_dict[elt]) for elt in geom_aut_grp_list]
            ),
        )

        Q_endomorphism = SelectBox(
            name="end_alg",
            knowl="g2c.end_alg",
            label=r"\(\Q\)-endomorphism algebra",
            short_label=r"\(\Q\)-end algebra",
            options=([("", "")] + [(elt, end_alg_dict[elt]) for elt in end_alg_list]),
        )

        geometric_endomorphism = SelectBox(
            name="geom_end_alg",
            knowl="g2c.geom_end_alg",
            label=r"\(\overline{\Q}\)-endomorphism algebra",
            short_label=r"\(\overline{\Q}\)-end algebra",
            options=(
                [("", "")]
                + [(elt, geom_end_alg_dict[elt]) for elt in geom_end_alg_list]
            ),
        )

        locally_solvable = YesNoBox(
            name="locally_solvable",
            knowl="g2c.locally_solvable",
            label="Locally solvable",
        )

        has_square_sha = YesNoBox(
            name="has_square_sha",
            knowl="g2c.analytic_sha",
            label=r"Order of &#1064; is square*",
            short_label=r"Square &#1064;*",
        )

        geometrically_simple = YesNoBox(
            name="is_simple_geom",
            knowl="ag.geom_simple",
            label="Geometrically simple",
            short_label=r"\(\overline{\Q}\)-simple",
        )

        count = CountBox()

        self.browse_array = [
            [geometric_invariants],
            [bad_primes, geometrically_simple],
            [conductor, is_gl2_type],
            [discriminant, st_group],
            [rational_points, st_group_identity_component],
            [rational_weirstrass_points, Q_automorphism],
            [torsion_order, geometric_automorphism],
            [torsion_structure, Q_endomorphism],
            [two_selmer_rank, geometric_endomorphism],
            [analytic_sha, has_square_sha],
            [analytic_rank, locally_solvable],
            [count],
        ]

        self.refine_array = [
            [
                conductor,
                discriminant,
                rational_points,
                rational_weirstrass_points,
                torsion_order,
            ],
            [
                bad_primes,
                two_selmer_rank,
                analytic_rank,
                analytic_sha,
                torsion_structure,
            ],
            [
                Q_endomorphism,
                st_group,
                Q_automorphism,
                has_square_sha,
                geometrically_simple,
            ],
            [
                geometric_endomorphism,
                st_group_identity_component,
                geometric_automorphism,
                locally_solvable,
                is_gl2_type,
            ],
            [geometric_invariants],
        ]

    sort_knowl = "g2c.sort_order"

    def sort_order(self, info):
        X = [
            ("", "label"),
            ("abs_disc", "absolute discriminant"),
            ("num_rat_pts1", "rational points (inc)"),
            ("num_rat_pts-1", "rational points (dec)"),
            ("num_rat_wpts1", "Weierstrass points (inc)"),
            ("num_rat_wpts-1", "Weierstrass points (dec)"),
            ("torsion_order1", "torsion order (inc)"),
            ("torsion_order-1", "torsion order (dec)"),
            ("analytic_sha1", "analytic sha (inc)"),
            ("analytic_sha-1", "analytic sha (dec)"),
        ]
        return X

    def jump_box(self, info):
        info["jump_example"] = "169.a.169.1"
        info["jump_egspan"] = "e.g. 169.a.169.1 or 169.a or 1088.b"
        info["jump_knowl"] = "g2c.search_input"
        info["jump_prompt"] = "Label"
        if info.get("equation_search"):
            info["jump_egspan"] += " or x^5 + 1"
        return SearchArray.jump_box(self, info)
