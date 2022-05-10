# -*- coding: utf-8 -*-

import ast
import re
from io import BytesIO
import time

from flask import abort, render_template, url_for, request, redirect, send_file
from sage.rings.all import PolynomialRing, ZZ
from sage.databases.cremona import cremona_letter_code

from lmfdb import db
from lmfdb.logger import make_logger
from lmfdb.utils import (
    to_dict, flash_error, integer_options, display_knowl, coeff_to_poly,
    SearchArray, TextBox, TextBoxWithSelect, SkipBox, CheckBox, CheckboxSpacer, YesNoBox,
    parse_ints, parse_string_start, parse_subset, parse_submultiset, parse_bool, parse_bool_unknown,
    search_wrap, count_wrap, YesNoMaybeBox, CountBox, SubsetBox, SelectBox
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.api import datapage
from . import abvarfq_page
from .search_parsing import parse_newton_polygon, parse_nf_string, parse_galgrp
from .isog_class import validate_label, AbvarFq_isoclass
from .stats import AbvarFqStats
from lmfdb.utils import redirect_no_cache
from lmfdb.utils.search_columns import SearchColumns, SearchCol, MathCol, LinkCol
from lmfdb.abvar.fq.download import AbvarFq_download

logger = make_logger("abvarfq")

#########################
#    Top level
#########################

def get_bread(*breads):
    bc = [
        ("Abelian varieties", url_for(".abelian_varieties")),
        ("Fq", url_for(".abelian_varieties")),
    ]
    for z in breads:
        bc.append(z)
    return bc

def learnmore_list():
    return [
        ("Source and acknowledgments", url_for(".how_computed_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Labeling convention", url_for(".labels_page")),
    ]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


#########################
#    Downloads
#########################

@abvarfq_page.route("/download_all/<label>")
def download_all(label):
    return AbvarFq_download().download_all(label)

@abvarfq_page.route("/download_curves/<label>")
def download_curves(label):
    return AbvarFq_download().download_curves(label)


#########################
#  Search/navigate
#########################

@abvarfq_page.route("/")
def abelian_varieties():
    info = to_dict(request.args, search_array=AbvarSearchArray())
    if request.args:
        # hidden_search_type for prev/next buttons
        info["search_type"] = search_type = info.get("search_type", info.get("hst", "List"))
        if search_type == "Counts":
            return abelian_variety_count(info)
        elif search_type in ['List', 'Random']:
            return abelian_variety_search(info)
        else:
            flash_error("Invalid search type; if you did not enter it in the URL please report")
    return abelian_variety_browse(info)

@abvarfq_page.route("/<int:g>/")
def abelian_varieties_by_g(g):
    D = to_dict(request.args, search_array=AbvarSearchArray())
    if "g" not in D:
        D["g"] = g
    D["bread"] = get_bread((str(g), url_for(".abelian_varieties_by_g", g=g)))
    return abelian_variety_search(D)

@abvarfq_page.route("/<int:g>/<int:q>/")
def abelian_varieties_by_gq(g, q):
    D = to_dict(request.args, search_array=AbvarSearchArray())
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

    downloads = [
        ('All stored data to text', url_for('.download_all', label=label))
    ]

    if hasattr(cl, "curves") and cl.curves:
        downloads.append(('Curves to text', url_for('.download_curves', label=label)))
    downloads.append(("Underlying data", url_for('.AV_data', label=label)))

    return render_template(
        "show-abvarfq.html",
        properties=cl.properties(),
        friends=cl.friends(),
        downloads=downloads,
        title='Abelian variety isogeny class %s over $%s$'%(label, cl.field()),
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

@abvarfq_page.route("/data/<label>")
def AV_data(label):
    if not lmfdb_label_regex.fullmatch(label):
        return abort(404, f"Invalid label {label}")
    bread = get_bread((label, url_for_label(label)), ("Data", " "))
    extension_labels = list(db.av_fq_endalg_factors.search({"base_label": label}, "extension_label", sort=["extension_degree"]))
    tables = ["av_fq_isog", "av_fq_endalg_factors"] + ["av_fq_endalg_data"] * len(extension_labels)
    labels = [label, label] + extension_labels
    label_cols = ["label", "base_label"] + ["extension_label"] * len(extension_labels)
    sorts = [[], ["extension_degree"]] + [[]] * len(extension_labels)
    return datapage(labels, tables, title=f"Abelian variety isogeny class data - {label}", bread=bread, label_cols=label_cols, sorts=sorts)

class AbvarSearchArray(SearchArray):
    sorts = [("", "dimension", ['g', 'q', 'poly']),
             ("q", "field", ['q', 'g', 'poly']),
             ("p", "charactersitic", ['p', 'q', 'g', 'poly']),
             ("p_rank", "p-rank", ['p_rank', 'g', 'q', 'poly']),
             ("p_rank_deficit", "p-rank deficit", ['p_rank_deficit', 'g', 'q', 'poly']),
             ("curve_count", "curve points", ['curve_count', 'g', 'q', 'poly']),
             ("abvar_count", "abvar points", ['abvar_count', 'g', 'q', 'poly'])]
    jump_example = "2.16.am_cn"
    jump_egspan = "e.g. 2.16.am_cn or 1 - x + 2x^2 or x^2 - x + 2"
    jump_knowl = "av.fq.search_input"
    jump_prompt = "Label or polynomial"
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
            + display_knowl("nf.galois_group.name", "group names"),
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
            label="Number of hyperelliptic Jacobians",
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
        simple = YesNoBox(
            "simple",
            label="Simple",
            knowl="av.simple",
        )
        geom_simple = YesNoBox(
            "geom_simple",
            label="Geometrically simple",
            knowl="av.geometrically_simple",
            short_label="Geom. simple",
        )
        geom_squarefree = SelectBox(
            name="geom_squarefree",
            knowl="av.geometrically_squarefree",
            label="(Geometrically) Squarefree",
            short_label="(Geom.) Sq.free",
            options=[('', ''),
            ('Yes', 'yes'),
            ('YesAndGeom', 'yes; and geom.'),
            ('YesNotGeom', 'yes; not geom.'),
            ('No', 'no'),
            ('NotGeom', 'not geom.')],
            advanced=True
        )
        primitive = YesNoBox(
            "primitive",
            label="Primitive",
            knowl="ag.primitive",
        )
        polarizable = YesNoMaybeBox(
            "polarizable",
            label="Principally polarizable",
            knowl="av.princ_polarizable",
            short_label="Princ. polarizable",
        )
        jacobian = YesNoMaybeBox(
            "jacobian",
            label="Jacobian",
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
        simple_quantifier = SubsetBox(
            "simple_quantifier",
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
        count = CountBox()

        self.refine_array = [
            [q, p, g, p_rank, initial_coefficients],
            [simple, geom_simple, primitive, polarizable, jacobian],
            [newton_polygon, abvar_point_count, curve_point_count, simple_factors],
            [angle_rank, jac_cnt, hyp_cnt, twist_count, max_twist_degree],
            [geom_deg, p_rank_deficit, geom_squarefree],
            use_geom_refine,
            [dim1, dim2, dim3, dim4, dim5],
            [dim1d, dim2d, dim3d, number_field, galois_group],
        ]
        self.browse_array = [
            [q, primitive],
            [p, simple],
            [g, geom_simple],
            [initial_coefficients, polarizable],
            [p_rank, jacobian],
            [p_rank_deficit, geom_squarefree],
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

    def search_types(self, info):
        return self._search_again(info, [
            ('List', 'List of isogeny classes'),
            ('Counts', 'Counts table'),
            ('Random', 'Random isogeny class')])

def common_parse(info, query):
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
    if info.get("simple_quantifier") in ["subset", "exactly"]:
        parse_subset(info, query, "simple_factors", qfield="simple_distinct", mode=info.get("simple_quantifier"))
    else:
        parse_submultiset(info, query, "simple_factors")
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

    if 'geom_squarefree' in info:
        if info['geom_squarefree'] == 'Yes':
            query['is_squarefree'] = True

        elif info['geom_squarefree'] == 'YesAndGeom':
            query['is_squarefree'] = True
            query['is_geometrically_squarefree'] = True

        elif info['geom_squarefree'] == 'YesNotGeom':
            query['is_squarefree'] = True
            query['is_geometrically_squarefree'] = False

        elif info['geom_squarefree'] == 'No':
            query['is_squarefree'] = False

        elif info['geom_squarefree'] == 'NotGeom':
            query['is_geometrically_squarefree'] = False

def jump(info):
    jump_box = info["jump"].strip() # only called when this present
    try:
        validate_label(jump_box)
    except ValueError:
        # Also accept polynomials
        try:
            poly = coeff_to_poly(jump_box)
            cdict = poly.dict()
            deg = poly.degree()
            if deg % 2 == 1:
                raise ValueError
        except Exception:
            flash_error ("%s is not valid input.  Expected a label or Weil polynomial.", jump_box)
            return redirect(url_for(".abelian_varieties"))
        g = deg//2
        lead = cdict[deg]
        if lead == 1: # accept monic normalization
            lead = cdict[0]
            cdict = {deg-exp: coeff for (exp, coeff) in cdict.items()}
        if cdict.get(0) != 1:
            flash_error ("%s is not valid input.  Polynomial must have constant or leading coefficient 1", jump_box)
            return redirect(url_for(".abelian_varieties"))
        try:
            q = lead.nth_root(g)
            if not ZZ(q).is_prime_power():
                raise ValueError
            for i in range(1, g):
                if cdict.get(2*g-i, 0) != q**(g-i) * cdict.get(i, 0):
                    raise ValueError
        except ValueError:
            flash_error ("%s is not valid input.  Expected a label or Weil polynomial.", jump_box)
            return redirect(url_for(".abelian_varieties"))
        def extended_code(c):
            if c < 0:
                return 'a' + cremona_letter_code(-c)
            return cremona_letter_code(c)
        jump_box = "%s.%s.%s" % (g, q, "_".join(extended_code(cdict.get(i, 0)) for i in range(1, g+1)))
    return by_label(jump_box)

abvar_columns = SearchColumns([
    LinkCol("label", "ab.fq.lmfdb_label", "Label", url_for_label, default=True),
    MathCol("g", "ag.dimension", "Dimension", default=True),
    MathCol("field", "ag.base_field", "Base field", default=True),
    MathCol("p", "ag.base_field", "Base char.", short_title="base characteristic"),
    MathCol("formatted_polynomial", "av.fq.l-polynomial", "L-polynomial", short_title="L-polynomial", default=True),
    MathCol("p_rank", "av.fq.p_rank", "$p$-rank", default=True),
    MathCol("p_rank_deficit", "av.fq.p_rank", "$p$-rank deficit"),
    MathCol("curve_count", "av.fq.curve_point_counts", "points on curve"),
    MathCol("abvar_count", "ag.fq.point_counts", "points on variety"),
    SearchCol("decomposition_display_search", "av.decomposition", "Isogeny factors", default=True)],
    db_cols=["label", "g", "q", "poly", "p_rank", "p_rank_deficit", "is_simple", "simple_distinct", "simple_multiplicities", "is_primitive", "primitive_models", "curve_count", "abvar_count"])

@search_wrap(
    table=db.av_fq_isog,
    title="Abelian variety search results",
    err_title="Abelian variety search input error",
    columns=abvar_columns,
    shortcuts={
        "jump": jump,
        "download": download_search,
    },
    postprocess=lambda res, info, query: [AbvarFq_isoclass(x) for x in res],
    url_for_label=url_for_label,
    learnmore=learnmore_list,
    bread=lambda: get_bread(("Search results", " ")),
)
def abelian_variety_search(info, query):
    common_parse(info, query)

@count_wrap(
    template="abvarfq-count-results.html",
    table=db.av_fq_isog,
    groupby=["g", "q"],
    title="Abelian variety count results",
    err_title="Abelian variety search input error",
    overall=AbvarFqStats()._counts,
    bread=lambda: get_bread(("Count results", " ")),
)
def abelian_variety_count(info, query):
    common_parse(info, query)
    urlgen_info = dict(info)
    urlgen_info.pop("hst", None)

    def url_generator(g, q):
        info_copy = dict(urlgen_info)
        info_copy.pop("search_array", None)
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

def abelian_variety_browse(info):
    info["stats"] = AbvarFqStats()
    info["q_ranges"] = ["2", "3", "4", "5", "7", "8", "9", "16", "17", "19", "23", "25", "27-211", "223-1024"]
    return render_template(
        "abvarfq-index.html",
        title="Isogeny classes of abelian varieties over finite fields",
        info=info,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

def search_input_error(info=None, bread=None):
    if info is None:
        info = {"err": "", "query": {}}
    info["search_array"] = AbvarSearchArray()
    info["columns"] = abvar_columns
    if bread is None:
        bread = get_bread(("Search results", " "))
    return render_template(
        "search_results.html",
        info=info,
        title="Abelian variety search input error",
        bread=bread,
        learnmore=learnmore_list()
    )

@abvarfq_page.route("/stats")
def statistics():
    title = "Abelian variety isogeny classes: Statistics"
    return render_template(
        "display_stats.html",
        info=AbvarFqStats(),
        title=title,
        bread=get_bread(("Statistics", " ")),
        learnmore=learnmore_list(),
    )

@abvarfq_page.route("/dynamic_stats")
def dynamic_statistics():
    info = to_dict(request.args, search_array=AbvarSearchArray())
    AbvarFqStats().dynamic_setup(info)
    title = "Abelian variety isogeny classes: Dynamic statistics"
    return render_template(
        "dynamic_stats.html",
        info=info,
        title=title,
        bread=get_bread(("Dynamic Statistics", " ")),
        learnmore=learnmore_list(),
    )

@abvarfq_page.route("/<label>")
def by_label(label):
    return redirect(url_for_label(label))

@abvarfq_page.route("/random")
@redirect_no_cache
def random_class():
    label = db.av_fq_isog.random()
    g, q, iso = split_label(label)
    return url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso)

@abvarfq_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "av.fq",
        db.av_fq_isog,
        url_for_label,
        title=r"Some interesting isogeny classes of abelian varieties over $\Fq$",
        bread=get_bread(("Interesting", " ")),
        learnmore=learnmore_list()
    )

@abvarfq_page.route("/Source")
def how_computed_page():
    t = "Source and acknowledgments for Weil polynomial data"
    bread = get_bread(("Source", " "))
    return render_template(
        "multi.html",
        kids=["rcs.source.av.fq",
              "rcs.ack.av.fq",
              "rcs.cite.av.fq"],
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )

@abvarfq_page.route("/Completeness")
def completeness_page():
    t = "Completeness of Weil polynomial data"
    bread = get_bread(("Completeness", " "))
    return render_template(
        "single.html",
        kid="rcs.cande.av.fq",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )

@abvarfq_page.route("/Reliability")
def reliability_page():
    t = "Reliability of Weil polynomial data"
    bread = get_bread(("Reliability", " "))
    return render_template(
        "single.html",
        kid="rcs.rigor.av.fq",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )

@abvarfq_page.route("/Labels")
def labels_page():
    t = "Labels for isogeny classes of abelian varieties"
    bread = get_bread(("Labels", " "))
    return render_template(
        "single.html",
        kid="av.fq.lmfdb_label",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Labels"),
    )

lmfdb_label_regex = re.compile(r"(\d+)\.(\d+)\.([a-z_]+)")

def split_label(lab):
    return lmfdb_label_regex.match(lab).groups()

def abvar_label(g, q, iso):
    return "%s.%s.%s" % (g, q, iso)
