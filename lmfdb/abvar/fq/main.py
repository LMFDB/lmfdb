
import re

from flask import abort, render_template, url_for, request, redirect
from sage.rings.all import ZZ
from sage.databases.cremona import cremona_letter_code

from lmfdb import db
from lmfdb.logger import make_logger
from lmfdb.utils import (
    to_dict, flash_error, integer_options, display_knowl, coeff_to_poly,
    SearchArray, TextBox, TextBoxWithSelect, SkipBox, CheckBox, CheckboxSpacer, YesNoBox,
    parse_ints, parse_string_start, parse_subset, parse_newton_polygon, parse_submultiset, parse_bool, parse_bool_unknown,
    search_wrap, count_wrap, YesNoMaybeBox, CountBox, SubsetBox, SelectBox
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.api import datapage
from . import abvarfq_page
from .search_parsing import parse_nf_string, parse_galgrp
from .isog_class import validate_label, AbvarFq_isoclass
from .stats import AbvarFqStats
from lmfdb.number_fields.web_number_field import nf_display_knowl, field_pretty
from lmfdb.utils import redirect_no_cache
from lmfdb.utils.search_columns import SearchColumns, SearchCol, MathCol, LinkCol, ProcessedCol, CheckCol, CheckMaybeCol
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
    bc.extend(z for z in breads)
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
        info["search_type"] = search_type = info.get("search_type", info.get("hst", ""))
        if search_type == "Counts":
            return abelian_variety_count(info)
        elif search_type in ['List', '', 'Random']:
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
        title='Abelian variety isogeny class %s over $%s$' % (label, cl.field()),
        bread=bread,
        cl=cl,
        learnmore=learnmore_list(),
        KNOWL_ID='av.fq.%s' % label
    )

def url_for_label(label):
    label = label.replace(" ", "")
    try:
        validate_label(label)
    except ValueError as err:
        flash_error("%s is not a valid label: %s.", label, str(err))
        return url_for(".abelian_varieties")
    g, q, iso = split_label(label)
    return url_for(".abelian_varieties_by_gqi", g=g, q=q, iso=iso)

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
             ("p", "characteristic", ['p', 'q', 'g', 'poly']),
             ("p_rank", "p-rank", ['p_rank', 'g', 'q', 'poly']),
             ("angle_rank", "angle rank", ['angle_rank', 'g', 'q', 'poly']),
             ("elevation", "Newton elevation", ['newton_elevation', 'g', 'q', 'poly']),
             ("curve_count", "curve points", ['curve_count', 'g', 'q', 'poly']),
             ("abvar_count", "abvar points", ['abvar_count', 'g', 'q', 'poly']),
             ("jacobian_count", "Jacobian count", ['jacobian_count', 'g', 'q', 'poly']),
             ("hyp_count", "Hyp. Jacobian count", ['hyp_count', 'g', 'q', 'poly']),
             ("twist_count", "Num .twists", ['twist_count', 'g', 'q', 'poly']),
             ("max_twist_degree", "Max. twist degree", ['max_twist_degree', 'g', 'q', 'poly']),
             ("geom_deg", "End. degree", ['geometric_extension_degree', 'g', 'q', 'poly'])]
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
        p_corank = TextBox(
            "p_corank",
            label="$p$-corank",
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
        angle_corank = TextBox(
            "angle_corank",
            label="Angle corank",
            knowl="av.fq.angle_rank",
            example="3",
            example_col=False,
            advanced=True,
        )
        newton_elevation = TextBox(
            "newton_elevation",
            label="Newton elevation",
            knowl="av.fq.newton_elevation",
            example="1",
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
            return nbsp("av.decomposition", f"Dimension {d} factors")

        def short_label(d):
            return display_knowl("av.decomposition", f"Dim {d} factors")

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
            [newton_elevation, jac_cnt, hyp_cnt, twist_count, max_twist_degree],
            [angle_rank, angle_corank, geom_deg, p_corank, geom_squarefree],
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
            [p_corank, geom_squarefree],
            [jac_cnt, hyp_cnt],
            [angle_rank, angle_corank],
            [twist_count, max_twist_degree],
            [newton_elevation, geom_deg],
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
            ('', 'List of isogeny classes'),
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
    parse_ints(info, query, "p_corank", qfield="p_rank_deficit")
    parse_ints(info, query, "angle_rank")
    parse_ints(info, query, "angle_corank")
    parse_ints(info, query, "newton_elevation")
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
            flash_error("%s is not valid input.  Expected a label or Weil polynomial.", jump_box)
            return redirect(url_for(".abelian_varieties"))
        g = deg//2
        lead = cdict[deg]
        if lead == 1: # accept monic normalization
            lead = cdict[0]
            cdict = {deg-exp: coeff for (exp, coeff) in cdict.items()}
        if cdict.get(0) != 1:
            flash_error("%s is not valid input.  Polynomial must have constant or leading coefficient 1", jump_box)
            return redirect(url_for(".abelian_varieties"))
        try:
            q = lead.nth_root(g)
            if not ZZ(q).is_prime_power():
                raise ValueError
            for i in range(1, g):
                if cdict.get(2*g-i, 0) != q**(g-i) * cdict.get(i, 0):
                    raise ValueError
        except ValueError:
            flash_error("%s is not valid input.  Expected a label or Weil polynomial.", jump_box)
            return redirect(url_for(".abelian_varieties"))

        def extended_code(c):
            if c < 0:
                return 'a' + cremona_letter_code(-c)
            return cremona_letter_code(c)

        jump_box = "%s.%s.%s" % (g, q, "_".join(extended_code(cdict.get(i, 0)) for i in range(1, g+1)))
    return by_label(jump_box)

# simple, geom. simple, primitive, princ polarizable, Jacobian
# F_q^k points on curve/variety

abvar_columns = SearchColumns([
    LinkCol("label", "av.fq.lmfdb_label", "Label", url_for_label),
    MathCol("g", "ag.dimension", "Dimension"),
    MathCol("field", "ag.base_field", "Base field", download_col="q"),
    MathCol("p", "ag.base_field", "Base char.", short_title="base characteristic", default=False),
    CheckCol("is_simple", "av.simple", "Simple", default=False),
    CheckCol("is_geometrically_simple", "av.geometrically_simple", "Geom. simple", default=False),
    CheckCol("is_primitive", "ag.primitive", "Primitive", default=False),
    CheckCol("is_ordinary", "av.fq.ordinary", "Ordinary", default=False),
    CheckCol("is_almost_ordinary", "av.fq.newton_elevation", "Almost ordinary", default=False),
    CheckCol("is_supersingular", "av.fq.supersingular", "Supersingular", default=False),
    CheckMaybeCol("has_principal_polarization", "av.princ_polarizable", "Princ. polarizable", default=False),
    CheckMaybeCol("has_jacobian", "ag.jacobian", "Jacobian", default=False),
    MathCol("formatted_polynomial", "av.fq.l-polynomial", "L-polynomial", short_title="L-polynomial", download_col="polynomial"),
    MathCol("pretty_slopes", "lf.newton_polygon", "Newton slopes", default=False),
    MathCol("newton_elevation", "av.fq.newton_elevation", "Newton elevation", default=False),
    MathCol("p_rank", "av.fq.p_rank", "$p$-rank"),
    MathCol("p_rank_deficit", "av.fq.p_rank", "$p$-corank", default=False),
    MathCol("angle_rank", "av.fq.angle_rank", "Angle rank", default=False),
    MathCol("angle_corank", "av.fq.angle_rank", "Angle corank", default=False),
    MathCol("curve_count", "av.fq.curve_point_counts", r"$\mathbb{F}_q$ points on curve", short_title="Fq points on curve", default=False),
    MathCol("curve_counts", "av.fq.curve_point_counts", r"$\mathbb{F}_{q^k}$ points on curve", short_title="Fq^k points on curve", default=False),
    MathCol("abvar_count", "ag.fq.point_counts", r"$\mathbb{F}_q$ points on variety", short_title="Fq points on variety", default=False),
    MathCol("abvar_counts", "ag.fq.point_counts", r"$\mathbb{F}_{q^k}$ points on variety", short_title="Fq^k points on variety", default=False),
    MathCol("jacobian_count", "av.jacobian_count", "Jacobians", default=False),
    MathCol("hyp_count", "av.hyperelliptic_count", "Hyperelliptic Jacobians", default=False),
    MathCol("twist_count", "av.twist", "Num. twists", default=False),
    MathCol("max_twist_degree", "av.twist", "Max. twist degree", default=False),
    MathCol("geometric_extension_degree", "av.endomorphism_field", "End. degree", default=False),
    ProcessedCol("number_fields", "av.fq.number_field", "Number fields", lambda nfs: ", ".join(nf_display_knowl(nf, field_pretty(nf)) for nf in nfs), default=False),
    SearchCol("galois_groups_pretty", "nf.galois_group", "Galois groups", download_col="galois_groups", default=False),
    SearchCol("decomposition_display_search", "av.decomposition", "Isogeny factors", download_col="decompositionraw")],
    db_cols=["label", "g", "q", "poly", "p_rank", "p_rank_deficit", "is_simple", "is_geometrically_simple", "simple_distinct", "simple_multiplicities", "is_primitive", "primitive_models", "curve_count", "curve_counts", "abvar_count", "abvar_counts", "jacobian_count", "hyp_count", "number_fields", "galois_groups", "slopes", "newton_elevation", "twist_count", "max_twist_degree", "geometric_extension_degree", "angle_rank", "angle_corank", "is_supersingular", "has_principal_polarization", "has_jacobian"])

def abvar_postprocess(res, info, query):
    gals = set()
    for A in res:
        for gal in A["galois_groups"]:
            gals.add(gal)
    cache = {rec["label"]: rec for rec in db.gps_transitive.search({"label": {"$in": list(gals)}}, ["label", "pretty"])}
    for A in res:
        A["gal_cache"] = cache
    return [AbvarFq_isoclass(x) for x in res]

@search_wrap(
    table=db.av_fq_isog,
    title="Abelian variety search results",
    err_title="Abelian variety search input error",
    columns=abvar_columns,
    shortcuts={
        "jump": jump,
        "download": AbvarFq_download(),
    },
    postprocess=abvar_postprocess,
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
        info_copy.pop("search_type", None)
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
