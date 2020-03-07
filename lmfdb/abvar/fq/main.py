# -*- coding: utf-8 -*-

import ast
import re
from six import BytesIO
import time

from flask import abort, render_template, url_for, request, redirect, send_file
from sage.rings.all import PolynomialRing, ZZ

from lmfdb import db
from lmfdb.logger import make_logger
from lmfdb.utils import (
    to_dict, flash_error, integer_options, display_knowl,
    SearchArray, TextBox, SelectBox, TextBoxWithSelect, SkipBox, CheckBox, CheckboxSpacer,
    parse_ints, parse_string_start, parse_subset, parse_submultiset, parse_bool, parse_bool_unknown,
    search_wrap, count_wrap,
)
from . import abvarfq_page
from .search_parsing import parse_newton_polygon, parse_nf_string, parse_galgrp
from .isog_class import validate_label, AbvarFq_isoclass
from .stats import AbvarFqStats

logger = make_logger("abvarfq")

#########################
#    Top level
#########################

def get_bread(*breads):
    bc = [
        ("Abelian Varieties", url_for(".abelian_varieties")),
        ("Fq", url_for(".abelian_varieties")),
    ]
    for z in breads:
        bc.append(z)
    return bc

abvarfq_credit = "Taylor Dupuy, Kiran Kedlaya, David Roe, Christelle Vincent"

def learnmore_list():
    return [
        ("Completeness of the data", url_for(".completeness_page")),
        ("Source of the data", url_for(".how_computed_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Labels", url_for(".labels_page")),
    ]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

#########################
#  Search/navigate
#########################

@abvarfq_page.route("/")
def abelian_varieties():
    args = request.args
    if args:
        info = to_dict(args)
        # hidden_search_type for prev/next buttons
        info["search_type"] = search_type = info.get("search_type", info.get("hst", "List"))
        if search_type == "Counts":
            return abelian_variety_count(info)
        elif search_type in ['List', 'Random']:
            return abelian_variety_search(info)
        assert False
    else:
        return abelian_variety_browse(**args)

@abvarfq_page.route("/<int:g>/")
def abelian_varieties_by_g(g):
    D = to_dict(request.args)
    if "g" not in D:
        D["g"] = g
    D["bread"] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)))
    return abelian_variety_search(D)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    D = to_dict(request.args)
    if "g" not in D:
        D["g"] = g
    if "q" not in D:
        D["q"] = q
    D["bread"] = get_bread(
        (str(g), url_for(".abelian_varieties_by_g", g=g)),
        (str(q), url_for(".abelian_varieties_by_gq", g=g, q=q)),
    )
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
    except ValueError:
        return abort(404, "Isogeny class %s is not in the database." % label)
    bread = get_bread(
        (str(g), url_for(".abelian_varieties_by_g", g=g)),
        (str(q), url_for(".abelian_varieties_by_gq", g=g, q=q)),
        (iso, url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso))
    )

    return render_template(
        "show-abvarfq.html",
        properties=cl.properties(),
        credit=abvarfq_credit,
        title='Abelian Variety Isogeny Class %s over $%s$'%(label, cl.field()),
        bread=bread,
        cl=cl,
        learnmore=learnmore_list(),
        KNOWL_ID='av.fq.%s'%label
    )

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
    dltype = info["Submit"]
    R = PolynomialRing(ZZ, "x")
    delim = "bracket"
    com = r"\\"  # single line comment start
    com1 = ""  # multiline comment start
    com2 = ""  # multiline comment end
    filename = "weil_polynomials.gp"
    mydate = time.strftime("%d %B %Y")
    if dltype == "sage":
        com = "#"
        filename = "weil_polynomials.sage"
    if dltype == "magma":
        com = ""
        com1 = "/*"
        com2 = "*/"
        delim = "magma"
        filename = "weil_polynomials.m"
    s = com1 + "\n"
    s += com + " Weil polynomials downloaded from the LMFDB on %s.\n" % (mydate)
    s += com + " Below is a list (called data), collecting the weight 1 L-polynomial\n"
    s += com + " attached to each isogeny class of an abelian variety.\n"
    s += "\n" + com2
    s += "\n"

    if dltype == "magma":
        s += "P<x> := PolynomialRing(Integers()); \n"
        s += "data := ["
    else:
        if dltype == "sage":
            s += "x = polygen(ZZ) \n"
        s += "data = [ "
    s += "\\\n"
    for f in db.av_fq_isog.search(ast.literal_eval(info["query"]), "poly"):
        poly = R(f)
        s += str(poly) + ",\\\n"
    s = s[:-3]
    s += "]\n"
    if delim == "magma":
        s = s.replace("[", "[*")
        s = s.replace("]", "*]")
        s += ";"
    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)

class AbvarSearchArray(SearchArray):
    def __init__(self):
        qshort = display_knowl("ag.base_field", "Base field")
        q = TextBox(
            "q",
            label="Cardinality of the %s" % (qshort),
            short_label=qshort,
            example="81",
            example_span="81 or 3-49",
        )
        pshort = display_knowl("ag.base_field", "Base char.")
        p = TextBox(
            "p",
            label="Characteristic of the %s" % (qshort),
            short_label=pshort,
            example="3",
            example_span="3 or 2-5",
        )
        g = TextBox(
            "g",
            label="Dimension",
            knowl="ag.dimension",
            example="2",
            example_span="2 or 3-5"
        )
        p_rank = TextBox(
            "p_rank",
            label="$p$-rank",
            knowl="av.fq.p_rank",
            example="2"
        )
        p_rank_deficit = TextBox(
            "p_rank_deficit",
            label="$p$-rank deficit",
            knowl="av.fq.p_rank",
            example="2",
            advanced=True,
        )
        angle_rank = TextBox(
            "angle_rank",
            label="Angle rank",
            knowl="av.fq.angle_rank",
            example="3",
            example_col=False,
            advanced=True,
        )
        newton_polygon = TextBox(
            "newton_polygon",
            label="Slopes of Newton polygon",
            knowl="lf.newton_polygon",
            example="[0,0,1/2]",
            colspan=(1, 3, 1),
            width=3*190 - 30,
            short_width=160,
            short_label="Slopes",
            advanced=True,
        )
        initial_coefficients = TextBox(
            "initial_coefficients",
            label="Initial coefficients",
            knowl="av.fq.initial_coefficients",
            example="[2, -1, 3, 9]",
        )
        abvar_point_count = TextBox(
            "abvar_point_count",
            label="Point counts of the variety",
            knowl="ag.fq.point_counts",
            example="[75,7125]",
            colspan=(1, 3, 1),
            width=3*190 - 30,
            short_width=160,
            short_label="Points on variety",
            advanced=True,
        )
        curve_point_count = TextBox(
            "curve_point_count",
            label="Point counts of the curve",
            knowl="av.fq.curve_point_counts",
            example="[9,87]",
            colspan=(1, 3, 1),
            width=3*190 - 30,
            short_width=160,
            short_label="Points on curve",
            advanced=True,
        )
        def nbsp(knowl, label):
            return "&nbsp;&nbsp;&nbsp;&nbsp;" + display_knowl(knowl, label)
        number_field = TextBox(
            "number_field",
            label=nbsp("av.fq.number_field", "Number field"),
            short_label=display_knowl("av.fq.number_field", "Number field"),
            example="4.0.29584.2",
            example_span="4.0.29584.2 or Qzeta8",
            colspan=(1, 3, 1),
            width=3*190 - 30,
            short_width=160,
            advanced=True,
        )
        galois_group = TextBox(
            "galois_group",
            label=nbsp("nf.galois_group", "Galois group"),
            short_label=display_knowl("nf.galois_group", "Galois group"),
            example="4T3",
            example_span="C4, or 8T12, a list of "
            + display_knowl("nf.galois_group.name", "group labels"),
            colspan=(1, 3, 1),
            width=3*190 - 30,
            short_width=160,
            advanced=True,
        )
        #size = TextBox(
        #    "size",
        #    label="Isogeny class size",
        #    knowl="av.fq.isogeny_class_size",
        #    example="1",
        #    example_col=False,
        #    advanced=True,
        #)
        gdshort = display_knowl("av.endomorphism_field", "End.") + " degree"
        gdlong = "Degree of " + display_knowl("av.endomorphism_field", "endomorphism_field")
        geom_deg = TextBox(
            "geom_deg",
            label=gdlong,
            short_label=gdshort,
            example="168",
            example_span="6-12, 168",
            advanced=True,
        )
        jac_cnt = TextBox(
            "jac_cnt",
            label="Number of Jacobians",
            knowl="av.jacobian_count",
            example="6",
            short_label="# Jacobians",
            advanced=True,
        )
        hyp_cnt = TextBox(
            "hyp_cnt",
            label="Number of Hyperelliptic Jacobians",
            knowl="av.hyperelliptic_count",
            example="6",
            example_col=False,
            short_label="# Hyp. Jacobians",
            advanced=True,
        )
        tcshort = display_knowl("av.twist", "# twists")
        tclong = "Number of " + display_knowl("av.twist", "twists")
        twist_count = TextBox(
            "twist_count",
            label=tclong,
            short_label=tcshort,
            example="390",
            advanced=True,
        )
        max_twist_degree = TextBox(
            "max_twist_degree",
            label="Max twist degree",
            knowl="av.twist",
            example="16",
            example_col=False,
            advanced=True,
        )
        simple = SelectBox(
            "simple",
            label="Simple",
            options=[("yes", "yes"), ("", "unrestricted"), ("no", "no")],
            knowl="av.simple",
        )
        geom_simple = SelectBox(
            "geom_simple",
            label="Geometrically simple",
            options=[("yes", "yes"), ("", "unrestricted"), ("no", "no")],
            knowl="av.geometrically_simple",
            short_label="Geom. simple",
        )
        primitive = SelectBox(
            "primitive",
            label="Primitive",
            options=[("yes", "yes"), ("", "unrestricted"), ("no", "no")],
            knowl="ag.primitive",
        )
        uopts = [
            ("yes", "yes"),
            ("not_no", "yes or unknown"),
            ("", "unrestricted"),
            ("not_yes", "no or unknown"),
            ("no", "no"),
            ("unknown", "unknown"),
        ]
        polarizable = SelectBox(
            "polarizable",
            label="Principally polarizable",
            options=uopts,
            knowl="av.princ_polarizable",
            short_label="Princ polarizable",
        )
        jacobian = SelectBox(
            "jacobian",
            label="Jacobian",
            options=uopts,
            knowl="ag.jacobian"
        )
        uglabel = "Use %s in the following inputs" % display_knowl("av.decomposition", "Geometric decomposition")
        use_geom_decomp = CheckBox(
            "use_geom_decomp",
            label=uglabel,
            short_label=uglabel
        )
        use_geom_index = CheckboxSpacer(use_geom_decomp, colspan=4, advanced=True)
        use_geom_refine = CheckboxSpacer(use_geom_decomp, colspan=5, advanced=True)
        def long_label(d):
            return nbsp("av.decomposition", "Dimension %s factors" % d)
        def short_label(d):
            return display_knowl("av.decomposition", "Dim %s factors" % d)
        dim1 = TextBox(
            "dim1_factors",
            label=long_label(1),
            example="1-3",
            example_col=False,
            short_label=short_label(1),
            advanced=True,
        )
        dim1d = TextBox(
            "dim1_distinct",
            label="Distinct factors",
            knowl="av.decomposition",
            example="1-2",
            example_span="2 or 1-3",
            short_label="(distinct)",
            advanced=True,
        )
        dim2 = TextBox(
            "dim2_factors",
            label=long_label(2),
            example="1-3",
            example_col=False,
            short_label=short_label(2),
            advanced=True,
        )
        dim2d = TextBox(
            "dim2_distinct",
            label="Distinct factors",
            knowl="av.decomposition",
            example="1-2",
            example_span="2 or 1-3",
            short_label="(distinct)",
            advanced=True,
        )
        dim3 = TextBox(
            "dim3_factors",
            label=long_label(3),
            example="2",
            example_col=False,
            short_label=short_label(3),
            advanced=True,
        )
        dim3d = TextBox(
            "dim3_distinct",
            label="Distinct factors",
            knowl="av.decomposition",
            example="1",
            example_span="2 or 0-1",
            short_label="(distinct)",
            advanced=True,
        )
        dim4 = TextBox(
            "dim4_factors",
            label=long_label(4),
            example="2",
            example_col=False,
            short_label=short_label(4),
            advanced=True,
        )
        dim5 = TextBox(
            "dim5_factors",
            label=long_label(5),
            example="2",
            example_col=False,
            short_label=short_label(5),
            advanced=True,
        )
        dim4d = dim5d = SkipBox(example_span="0 or 1", advanced=True)
        simple_quantifier = SelectBox(
            "simple_quantifier",
            width=85,
            options=[("", "include"),
                     ("contained", "subset"),
                     ("exactly", "exactly")],
        )
        simple_factors = TextBoxWithSelect(
            "simple_factors",
            label="Simple factors",
            select_box=simple_quantifier,
            knowl="av.decomposition",
            colspan=(1, 3, 2),
            width=3*190 - 30,
            short_width=2*190 - 30,
            example="1.2.b,1.2.b,2.2.a_b",
            advanced=True,
        )
        count = TextBox(
            "count",
            label="Results to display",
            example=50,
            example_col=False
        )

        refine_array = [
            [q, p, g, p_rank, initial_coefficients],
            [newton_polygon, abvar_point_count, curve_point_count, simple_factors],
            [angle_rank, jac_cnt, hyp_cnt, twist_count, max_twist_degree],
            [geom_deg, p_rank_deficit],
            #[size],
            [simple, geom_simple, primitive, polarizable, jacobian],
            use_geom_refine,
            [dim1, dim2, dim3, dim4, dim5],
            [dim1d, dim2d, dim3d, number_field, galois_group],
        ]
        browse_array = [
            [q, primitive],
            [p, simple],
            [g, geom_simple],
            [initial_coefficients, polarizable],
            [p_rank, jacobian],
            [p_rank_deficit],
            [jac_cnt, hyp_cnt],
            [geom_deg, angle_rank],
            [twist_count, max_twist_degree],
            [newton_polygon],
            [abvar_point_count],
            [curve_point_count],
            [simple_factors],
            use_geom_index,
            [dim1, dim1d],
            [dim2, dim2d],
            [dim3, dim3d],
            [dim4, dim4d],
            [dim5, dim5d],
            [number_field],
            [galois_group],
            [count],
        ]
        search_types = [('List', 'List of Results'),
                        ('Counts', 'Counts Table'),
                        ('Random', 'Random Result')]
        SearchArray.__init__(self, browse_array, refine_array, search_types=search_types)

def common_parse(info, query):
    info["search_array"] = AbvarSearchArray()
    parse_ints(info, query, "q", name="base field")
    parse_ints(info, query, "p", name="base cardinality")
    parse_ints(info, query, "g", name="dimension")
    parse_ints(info, query, "geom_deg", qfield="geometric_extension_degree")
    parse_bool(info, query, "simple", qfield="is_simple")
    parse_bool(info, query, "geom_simple", qfield="is_geometrically_simple")
    parse_bool(info, query, "primitive", qfield="is_primitive")
    parse_bool_unknown(info, query, "jacobian", qfield="has_jacobian")
    parse_bool_unknown(info, query, "polarizable", qfield="has_principal_polarization")
    parse_ints(info, query, "p_rank")
    parse_ints(info, query, "p_rank_deficit")
    parse_ints(info, query, "angle_rank")
    parse_ints(info, query, "jac_cnt", qfield="jacobian_count", name="Number of Jacobians")
    parse_ints(info, query, "hyp_cnt", qfield="hyp_count", name="Number of Hyperelliptic Jacobians")
    parse_ints(info, query, "twist_count")
    parse_ints(info, query, "max_twist_degree")
    parse_ints(info, query, "size")
    parse_newton_polygon(info, query, "newton_polygon", qfield="slopes")
    parse_string_start(info, query, "initial_coefficients", qfield="poly_str", initial_segment=["1"])
    parse_string_start(info, query, "abvar_point_count", qfield="abvar_counts_str", first_field="abvar_count")
    parse_string_start(info, query, "curve_point_count", qfield="curve_counts_str", first_field="curve_count")
    if info.get("simple_quantifier") == "contained":
        parse_subset(info, query, "simple_factors", qfield="simple_distinct", mode="subsets")
    elif info.get("simple_quantifier") == "exactly":
        parse_subset(info, query, "simple_factors", qfield="simple_distinct", mode="exact")
    else:
        parse_submultiset(info, query, "simple_factors", mode="append")
    if info.get("use_geom_decomp") == "on":
        dimstr = "geom_dim"
        nf_qfield = "geometric_number_fields"
        gal_qfield = "geometric_galois_groups"
    else:
        dimstr = "dim"
        nf_qfield = "number_fields"
        gal_qfield = "galois_groups"
    for n in range(1, 6):
        parse_ints(info, query, "dim%s_factors" % n, qfield="%s%s_factors" % (dimstr, n))
    for n in range(1, 4):
        parse_ints(info, query, "dim%s_distinct" % n, qfield="%s%s_distinct" % (dimstr, n))
    parse_nf_string(info, query, "number_field", qfield=nf_qfield)
    parse_galgrp(info, query, "galois_group", qfield=gal_qfield)

@search_wrap(
    template="abvarfq-search-results.html",
    table=db.av_fq_isog,
    title="Abelian Variety Search Results",
    err_title="Abelian Variety Search Input Error",
    shortcuts={
        "jump": lambda info: by_label(info.get("label", "")),
        "download": download_search,
    },
    postprocess=lambda res, info, query: [AbvarFq_isoclass(x) for x in res],
    url_for_label=url_for_label,
    bread=lambda: get_bread(("Search Results", " ")),
    credit=lambda: abvarfq_credit,
)
def abelian_variety_search(info, query):
    common_parse(info, query)

@count_wrap(
    template="abvarfq-count-results.html",
    table=db.av_fq_isog,
    groupby=["g", "q"],
    title="Abelian Variety Count Results",
    err_title="Abelian Variety Search Input Error",
    overall=AbvarFqStats()._counts,
    bread=lambda: get_bread(("Count Results", " ")),
    credit=lambda: abvarfq_credit,
)
def abelian_variety_count(info, query):
    common_parse(info, query)
    urlgen_info = dict(info)
    urlgen_info.pop("hst", None)

    def url_generator(g, q):
        info_copy = dict(urlgen_info)
        info_copy["search_type"] = "List"
        info_copy["g"] = g
        info_copy["q"] = q
        return url_for("abvarfq.abelian_varieties", **info_copy)

    av_stats = AbvarFqStats()
    if "g" in info:
        info["row_heads"] = integer_options(info["g"], contained_in=av_stats.gs)
    else:
        info["row_heads"] = av_stats.gs
    if "q" in info:
        info["col_heads"] = integer_options(info["q"], contained_in=av_stats.qs)
    else:
        info["col_heads"] = av_stats.qs
    if "p" in query:
        ps = integer_options(info["p"], contained_in=av_stats.qs)
        info["col_heads"] = [q for q in info["col_heads"] if any(q % p == 0 for p in ps)]
    if not info["col_heads"]:
        raise ValueError("Must include at least one base field")
    info["na_msg"] = '"n/a" means that the isogeny classes of abelian varieties of this dimension over this field are not in the database yet.'
    info["row_label"] = "Dimension"
    info["col_label"] = r"Cardinality of base field \(q\)"
    info["url_func"] = url_generator

favorite_isocls_labels = [[
    ("2.64.a_abp", "Most isomorphism classes"),
    ("2.167.a_hi", "Most Jacobians"),
    ("4.2.ad_c_a_b", "Jacobian of function field with claa number 1"),
    ("6.2.ak_cb_ahg_sy_abme_ciq", "Largest twist class"),
    ("6.2.ag_r_abd_bg_ay_u", "Large endomorphism degree"),
]]

def abelian_variety_browse(**args):
    info = to_dict(args)
    info["search_array"] = AbvarSearchArray()
    info["stats"] = AbvarFqStats()
    info["q_ranges"] = ["2", "3", "4", "5", "7-16", "17-25", "27-211", "223-1024"]
    info["iso_list"] = [
        [
            {"label": label, "url": url_for_label(label), "reason": reason}
            for label, reason in sublist
        ]
        for sublist in favorite_isocls_labels
    ]
    return render_template(
        "abvarfq-index.html",
        title="Isogeny Classes of Abelian Varieties over Finite Fields",
        info=info,
        credit=abvarfq_credit,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

def search_input_error(info=None, bread=None):
    if info is None:
        info = {"err": "", "query": {}}
    info["search_array"] = AbvarSearchArray()
    if bread is None:
        bread = get_bread(("Search Results", "."))
    return render_template(
        "abvarfq-search-results.html",
        info=info,
        title="Abelian Variety Search Input Error",
        bread=bread,
    )

@abvarfq_page.route("/stats")
def statistics():
    title = "Abelian Varity Isogeny Classes: Statistics"
    return render_template(
        "display_stats.html",
        info=AbvarFqStats(),
        credit=abvarfq_credit,
        title=title,
        bread=get_bread(("Statistics", ".")),
        learnmore=learnmore_list(),
    )

@abvarfq_page.route("/dynamic_stats")
def dynamic_statistics():
    if len(request.args) > 0:
        info = to_dict(request.args)
    else:
        info = {}
    info["search_array"] = AbvarSearchArray()
    AbvarFqStats().dynamic_setup(info)
    title = "Abelian Varity Isogeny Classes: Dynamic Statistics"
    return render_template(
        "dynamic_stats.html",
        info=info,
        credit=abvarfq_credit,
        title=title,
        bread=get_bread(("Dynamic Statistics", ".")),
        learnmore=learnmore_list(),
    )

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
    t = "Completeness of the Weil Polynomial Data"
    bread = get_bread(("Completeness", "."))
    return render_template(
        "single.html",
        kid="rcs.cande.av.fq",
        credit=abvarfq_credit,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )

@abvarfq_page.route("/Reliability")
def reliability_page():
    t = "Reliability of the Weil Polynomial Data"
    bread = get_bread(("Reliability", "."))
    return render_template(
        "single.html",
        kid="rcs.rigor.av.fq",
        credit=abvarfq_credit,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )

@abvarfq_page.route("/Source")
def how_computed_page():
    t = "Source of the Weil Polynomial Data"
    bread = get_bread(("Source", "."))
    return render_template(
        "single.html",
        kid="rcs.source.av.fq",
        credit=abvarfq_credit,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )

@abvarfq_page.route("/Labels")
def labels_page():
    t = "Labels for Isogeny Classes of Abelian Varieties"
    bread = get_bread(("Labels", "."))
    return render_template(
        "single.html",
        kid="av.fq.lmfdb_label",
        credit=abvarfq_credit,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Labels"),
    )

lmfdb_label_regex = re.compile(r"(\d+)\.(\d+)\.([a-z_]+)")

def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def abvar_label(g, q, iso):
    return "%s.%s.%s" % (g, q, iso)
