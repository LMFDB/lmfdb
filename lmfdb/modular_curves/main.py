
import re
from collections import Counter
from lmfdb import db

from flask import render_template, url_for, request, redirect, abort

from sage.all import ZZ

from lmfdb.utils import (
    SearchArray,
    EmbeddedSearchArray,
    TextBox,
    TextBoxWithSelect,
    SelectBox,
    SneakyTextBox,
    YesNoBox,
    YesNoMaybeBox,
    CountBox,
    redirect_no_cache,
    display_knowl,
    flash_error,
    search_wrap,
    embed_wrap,
    to_dict,
    parse_ints,
    parse_noop,
    parse_bool,
    parse_floats,
    parse_interval,
    parse_element_of,
    parse_bool_unknown,
    parse_nf_string,
    parse_nf_jinv,
    integer_divisors,
    StatsDisplay,
    Downloader,
    comma,
    proportioners,
    totaler,
    key_for_numerically_sort
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import (
    SearchColumns, MathCol, FloatCol, CheckCol, SearchCol, LinkCol, ProcessedCol, MultiProcessedCol,
)
from lmfdb.utils.search_parsing import search_parser
from lmfdb.api import datapage
from psycodict.encoding import Json

from lmfdb.number_fields.number_field import field_pretty
from lmfdb.number_fields.web_number_field import nf_display_knowl
from lmfdb.modular_curves import modcurve_page
from lmfdb.modular_curves.web_curve import (
    WebModCurve, get_bread, canonicalize_name, name_to_latex, factored_conductor,
    formatted_dims, url_for_EC_label, url_for_ECNF_label, showj_nf, combined_data,
    learnmore_list, LABEL_RE, ISO_CLASS_RE
)
from lmfdb.modular_curves.family import ModCurveFamily
from lmfdb.modular_curves.upload import ModularCurveUploader
from lmfdb.modular_curves.isog_class import ModCurveIsog_class

from sage.databases.cremona import class_to_int

RSZB_LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")
CP_LABEL_RE = re.compile(r"\d+[A-Z]+\d+")
CP_LABEL_GENUS_RE = re.compile(r"\d+[A-Z]+(\d+)")
SZ_LABEL_RE = re.compile(r"\d+[A-Z]\d+-\d+[a-z]")
RZB_LABEL_RE = re.compile(r"X\d+[a-z]*")
S_LABEL_RE = re.compile(r"(\d+)(G|B|Cs|Cn|Ns|Nn|A4|S4|A5)(\.\d+){0,3}")
NAME_RE = re.compile(r"X_?(0|1|NS|NS\^?\+|SP|SP\^?\+|S4|ARITH)?\(\d+\)")

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def learnmore_list_add(learnmore_label, learnmore_url):
    return learnmore_list() + [(learnmore_label, learnmore_url)]


@modcurve_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@modcurve_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=ModCurveSearchArray())
    if request.args:
        return modcurve_search(info)
    title = r"Modular curves over $\Q$"
    info["level_list"] = ["1-4", "5-8", "9-12", "13-16", "17-23", "24-"]
    info["genus_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    info["rank_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    info["stats"] = ModCurve_stats()
    return render_template(
        "modcurve_browse.html",
        info=info,
        title=title,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

@modcurve_page.route("/Q/random/")
@redirect_no_cache
def random_curve():
    label = db.gps_gl2zhat_fine.random()
    return url_for_modcurve_label(label)

@modcurve_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "modcurve",
        db.gps_gl2zhat_fine,
        url_for_modcurve_label,
        title="Some interesting modular curves",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )

def modcurve_link(label):
    if int(label.split(".")[0]) <= 70:
        return '<a href=%s>%s</a>' % (url_for("modcurve.by_label", label=label), label)
    else:
        return label

@modcurve_page.route("/Q/<label>/")
def by_label(label):
    if RSZB_LABEL_RE.fullmatch(label):
        label = db.gps_gl2zhat_fine.lucky({"RSZBlabel":label},projection="label")
    if not LABEL_RE.fullmatch(label):
        if not ISO_CLASS_RE.fullmatch(label):
            flash_error("Invalid label %s", label)
            return redirect(url_for(".index"))
        iso_class = ModCurveIsog_class.by_label(label)
        return render_template("modcurve_isoclass.html",
                               iso_class=iso_class,
                               zip=zip,
                               name_to_latex=name_to_latex,
                               properties=iso_class.properties,
                               friends=iso_class.friends,
                               bread=iso_class.bread,
                               title=iso_class.title,
                               downloads=iso_class.downloads,
                               KNOWL_ID=f"modcurve.{label}",
                               learnmore=learnmore_list()
        )
    curve = WebModCurve(label)
    if curve.is_null():
        flash_error("There is no modular curve %s in the database", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(curve)
    learnmore_mcurve_pic = ('Picture description', url_for(".mcurve_picture_page"))
    return render_template(
        "modcurve.html",
        curve=curve,
        dojs=dojs,
        zip=zip,
        name_to_latex=name_to_latex,
        properties=curve.properties,
        friends=curve.friends,
        bread=curve.bread,
        title=curve.title,
        downloads=curve.downloads,
        KNOWL_ID=f"modcurve.{label}",
        learnmore=learnmore_list_add(*learnmore_mcurve_pic)
    )

@modcurve_page.route("/Q/diagram/<label>")
def lat_diagram(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    curve = WebModCurve(label)
    if curve.is_null():
        flash_error("There is no modular curve %s in the database", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(curve)
    info = {"dojs": dojs}
    info.update(display_opts)
    return render_template(
        "lat_diagram_page.html",
        dojs=dojs,
        info=info,
        title="Diagram of nearby modular curves for %s" % label,
        bread=get_bread("Subgroup diagram"),
        learnmore=learnmore_list(),
    )

def diagram_js(curve, layers, display_opts):
    ll = [
        [
            node.label, # grp.subgroup
            node.label, # grp.short_label
            node.tex, # grp.subgroup_tex
            1, # grp.count (never want conjugacy class counts)
            node.rank, # grp.subgroup_order
            node.img,
            node.x, # grp.diagramx[0] if aut else (grp.diagramx[2] if grp.normal else grp.diagramx[1])
            [node.x, node.x, node.x, node.x], # grp.diagram_aut_x if aut else grp.diagram_x
        ]
        for node in layers[0]
    ]
    if len(ll) == 0:
        display_opts["w"] = display_opts["h"] = 0
        return [], [], 0
    ranks = [node[4] for node in ll]
    rank_ctr = Counter(ranks)
    ranks = sorted(rank_ctr)
    # We would normally make rank_lookup a dictionary, but we're passing it to the horrible language known as javascript
    # The format is for compatibility with subgroup lattices
    rank_lookup = [[r, r, 0] for r in ranks]
    max_width = max(rank_ctr.values())
    display_opts["w"] = min(100 * max_width, 20000)
    display_opts["h"] = 160 * len(ranks)

    return [ll, layers[1]], rank_lookup, len(ranks)

def diagram_js_string(curve):
    display_opts = {}
    graph, rank_lookup, num_layers = diagram_js(curve, curve.nearby_lattice, display_opts)
    return f'var [sdiagram,graph] = make_sdiagram("subdiagram", "{curve.label}", {graph}, {rank_lookup}, {num_layers});', display_opts

@modcurve_page.route("/Q/curveinfo/<label>")
def curveinfo(label):
    if not LABEL_RE.fullmatch(label):
        return ""
    level, index, genus = label.split(".")[:3]

    ans = 'Information on the modular curve <a href="%s">%s</a><br>\n' % (url_for_modcurve_label(label), label)
    ans += "<table>\n"
    ans += f"<tr><td>{display_knowl('modcurve.level', 'Level')}</td><td>${level}$</td></tr>\n"
    ans += f"<tr><td>{display_knowl('modcurve.index', 'Index')}</td><td>${index}$</td></tr>\n"
    ans += f"<tr><td>{display_knowl('modcurve.genus', 'Genus')}</td><td>${genus}$</td></tr>\n"
    ans += "</table>"
    return ans

def url_for_modcurve_label(label):
    return url_for("modcurve.by_label", label=label)

def url_for_RZB_label(label):
    return "https://users.wfu.edu/rouseja/2adic/" + label + ".html"

def url_for_CP_label(label):
    genus = CP_LABEL_GENUS_RE.fullmatch(label)[1]
    return "https://mathstats.uncg.edu/sites/pauli/congruence/csg" + genus + ".html#group" + label

def modcurve_lmfdb_label(label):
    if LABEL_RE.fullmatch(label) or ISO_CLASS_RE.fullmatch(label):
        label_type = "label"
        lmfdb_label = label
    elif RSZB_LABEL_RE.fullmatch(label):
        label_type = "RSZB label"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"RSZBlabel": label}, "label")
    elif CP_LABEL_RE.fullmatch(label):
        label_type = "CP label"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"CPlabel": label}, "label")
    elif SZ_LABEL_RE.fullmatch(label):
        label_type = "SZ label"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"SZlabel": label}, "label")
    elif RZB_LABEL_RE.fullmatch(label):
        label_type = "RZB label"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"RZBlabel": label}, "label")
    elif S_LABEL_RE.fullmatch(label):
        label_type = "S label"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"Slabel": label}, "label")
    elif NAME_RE.fullmatch(label.upper()):
        label_type = "name"
        lmfdb_label = db.gps_gl2zhat_fine.lucky({"name": canonicalize_name(label)}, "label")
    else:
        label_type = "label"
        lmfdb_label = None
    return lmfdb_label, label_type

def modcurve_jump(info):
    labels = (info["jump"]).split("*")
    lmfdb_labels = []
    for label in labels:
        lmfdb_label, label_type = modcurve_lmfdb_label(label)
        if lmfdb_label is None:
            flash_error("There is no modular curve in the database with %s %s", label_type, label)
            return redirect(url_for(".index"))
        lmfdb_labels.append(lmfdb_label)
    lmfdb_labels_not_X1 = [l for l in lmfdb_labels if l != "1.1.0.a.1"]
    if len(lmfdb_labels) == 1:
        label = lmfdb_labels[0]
        return redirect(url_for_modcurve_label(label))
    elif len(lmfdb_labels_not_X1) == 1:
        label = lmfdb_labels_not_X1[0]
        return redirect(url_for_modcurve_label(label))
    else:
        # Get factorization for each label
        factors = list(db.gps_gl2zhat_fine.search({"label": {"$in": lmfdb_labels_not_X1}},
                                                  ["label","factorization"]))
        factors = [(f["factorization"] if f["factorization"] != [] else [f["label"]])
                   for f in factors]
        # Check labels are indeed distinct
        if len(factors) != len(lmfdb_labels_not_X1):
            flash_error("Fiber product decompositions cannot contain repeated terms")
            return redirect(url_for(".index"))
        # Get list of all factors, lexicographically sorted
        factors = sorted(sum(factors, []), key=key_for_numerically_sort)
        label = db.gps_gl2zhat_fine.lucky({'factorization': factors}, "label")
        if label is None:
            flash_error("There is no modular curve in the database isomorphic to the fiber product %s", info["jump"])
            return redirect(url_for(".index"))
        else:
            return redirect(url_for_modcurve_label(label))

@modcurve_page.route("/Q/upload/", methods=['GET', 'POST'])
def upload_data():
    return ModularCurveUploader().render()

@modcurve_page.route("/Q/review/", methods=['GET', 'POST'])
def review_data():
    return ModularCurveUploader().review()

@modcurve_page.route("/Q/needs_review/")
def needs_review():
    return ModularCurveUploader().needs_review()

def blankzeros(n):
    return "$%o$" % n if n else ""

modcurve_columns = SearchColumns(
    [
        LinkCol("label", "modcurve.label", "Label", url_for_modcurve_label),
        SearchCol("RSZBlabel", "modcurve.other_labels", "RSZB label", short_title="RSZB label", default=False),
        LinkCol("RZBlabel", "modcurve.other_labels", "RZB label", url_for_RZB_label, short_title="RZB label", default=False),
        LinkCol("CPlabel", "modcurve.other_labels", "CP label", url_for_CP_label, short_title="CP label", default=False),
        ProcessedCol("SZlabel", "modcurve.other_labels", "SZ label", lambda s: s if s else "", short_title="SZ label", default=False),
        ProcessedCol("Slabel", "modcurve.other_labels", "S label", lambda s: s if s else "", short_title="S label", default=False),
        ProcessedCol("name", "modcurve.standard", "Name", lambda s: name_to_latex(s) if s else "", align="center"),
        MathCol("level", "modcurve.level", "Level"),
        MathCol("index", "modcurve.index", "Index"),
        MathCol("genus", "modcurve.genus", "Genus"),
        ProcessedCol("rank", "modcurve.rank", "Rank", lambda r: "" if r is None else r, default=lambda info: info.get("rank") or info.get("genus_minus_rank"), align="center", mathmode=True),
        ProcessedCol("q_gonality_bounds", "modcurve.gonality", r"$\Q$-gonality", lambda b: r'$%s$' % (b[0]) if b[0] == b[1] else r'$%s \le \gamma \le %s$' % (b[0],b[1]), align="center", short_title="Q-gonality"),
        MathCol("cusps", "modcurve.cusps", "Cusps"),
        MathCol("rational_cusps", "modcurve.cusps", r"$\Q$-cusps", short_title="Q-cusps"),
        CheckCol("cm_discriminants", "modcurve.cm_discriminants", "CM points", align="center"),
        ProcessedCol("conductor", "ag.conductor", "Conductor", factored_conductor, align="center", mathmode=True, default=False),
        CheckCol("simple", "modcurve.simple", "Simple", default=False),
        CheckCol("squarefree", "av.squarefree", "Squarefree", default=False),
        CheckCol("contains_negative_one", "modcurve.contains_negative_one", "Contains -1", short_title="contains -1", default=False),
        MultiProcessedCol("dims", "modcurve.decomposition", "Decomposition", ["dims", "mults"], formatted_dims, align="center", apply_download=False, default=False),
        ProcessedCol("models", "modcurve.models", "Models", blankzeros, default=False),
        MathCol("num_known_degree1_points", "modcurve.known_points", "$j$-points", default=False),
        CheckCol("pointless", "modcurve.local_obstruction", "Local obstruction", default=False),
        ProcessedCol("generators", "modcurve.level_structure", r"$\operatorname{GL}_2(\mathbb{Z}/N\mathbb{Z})$-generators", lambda gens: ", ".join(r"$\begin{bmatrix}%s&%s\\%s&%s\end{bmatrix}$" % tuple(g) for g in gens) if gens else "trivial subgroup", short_title="generators", default=False),
    ],
    db_cols=["label", "RSZBlabel", "RZBlabel", "CPlabel", "Slabel", "SZlabel", "name", "level", "index", "genus", "rank", "q_gonality_bounds", "cusps", "rational_cusps", "cm_discriminants", "conductor", "simple", "squarefree", "contains_negative_one", "dims", "mults", "models", "pointless", "num_known_degree1_points", "generators"])

@search_parser
def parse_family(inp, query, qfield):
    if inp not in ["X0", "X1", "Xpm1", "X", "Xsp", "Xspplus", "Xns", "Xnsplus", "XS4", "Xarith1", "Xarithpm1", "Xsym", "Xarith", "any"]:
        raise ValueError
    inp = inp.replace("plus", "+")
    if inp == "any":
        query[qfield] = {"$like": "X%"}
    elif inp == "X" or inp == "XS4": #add nothing
        query[qfield] = {"$like": inp + "(%"}
    elif inp == "Xns+" or inp == "Xns": #add X(1)
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(1)"]}]}
    elif inp == "Xsp": #add X(1),X(2)
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(1)","X(2)"]}]}
    elif inp == "Xarith1": # X_{arith,1}(m,mn); add X(2)
        query[qfield] = {"$or":[{"$like": inp + "(%,%"}, {"$like": "X1(2,%"}, {"$in":["X(2)"]}]}
    elif inp == "Xarithpm1": # X_{\pm1}(2,2n); add X(2)
        query[qfield] = {"$or":[{"$like": inp + "(%,%"}, {"$like": "Xpm1(2,%"}, {"$in":["X(2)"]}]}
    elif inp == "Xpm1": # Add X(1) and X0(N) for N=2,3,4,6
        query[qfield] = {"$or":[{"$like": "Xpm1(%", "$not": {"$like": "%,%"}}, {"$in": ["X(1)", "X0(2)", "X0(3)", "X0(4)", "X0(6)"]}]}
    elif inp == "X1":
        query[qfield] = {"$or":[{"$like": "X1(%", "$not": {"$like": "%,%"}}, {"$in":["X(1)", "X0(2)"]}]}
    elif inp == "Xarith": # add X(1), X(2)
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(1)","X(2)"]}]}
    elif inp == "Xarith":
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(1)","X(2)"]}]}
    else: #add X(1),X0(2)
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(1)","X0(2)"]}]}


# cols currently unused in individual page download
    #'cusp_orbits',
    #'determinant_label',
    #'dims',
    #'gassmann_class',
    #'genus_minus_rank',
    #'isogeny_orbits',
    #'kummer_orbits',
    #'level_is_squarefree',
    #'level_radical',
    #'log_conductor',
    #'newforms',
    #'nu2',
    #'nu3',
    #'num_bad_primes',
    #'obstructions',
    #'orbits',
    #'pointless',
    #'psl2index',
    #'psl2level',
    #'qtwist',
    #'rational_cusps',
    #'reductions',
    #'scalar_label',
    #'simple',
    #'sl2level',
    #'squarefree',
    #'tiebreaker',
    #'trace_hash',
    #'traces',
# cols currently unused in modcurve_models
    #'dont_display'
    #'gonality_bounds'
    #'modcurve'
# cols currently unused in modcurve_modelmaps
    #'domain_label',
    #'dont_display',
    #'factored'

class ModCurve_download(Downloader):
    table = db.gps_gl2zhat_fine
    title = "Modular curves"
    inclusions = {
        "subgroup": (
            ["level", "generators"],
            {
                "magma": 'subgroup := out`level eq 1 select sub<GL(2,Integers())|> else sub<GL(2,Integers(out`level))|out`generators>;',
                "sage": 'subgroup = GL(2, Integers(out["level"])).subgroup(out["generators"])',
                "gp": 'subgroup = [Mod(Mat([a[1],a[2];a[3],a[4]]),mapget(out, "level"))|a<-mapget(out, "generators")];',
            }
        ),
    }

    def download_modular_curve_magma_str(self, label):
        s = ""
        rec = combined_data(label)
        if rec is None:
            return abort(404, "Label not found: %s" % label)
        s += "// Magma code for modular curve with label %s\n\n" % label
        if rec['name'] or rec['CPlabel'] or rec['Slabel'] or rec['SZlabel'] or rec['RZBlabel']:
            s += "// Other names and/or labels\n"
            if rec['name']:
                s += "// Curve name: %s\n" % rec['name']
            if rec['CPlabel']:
                s += "// Cummins-Pauli label: %s\n" % rec['CPlabel']
            if rec['RZBlabel']:
                s += "// Rouse-Zureick-Brown label: %s\n" % rec['RZBlabel']
            if rec['RSZBlabel']:
                s += "// Rouse-Sutherland-Zureick-Brown label: %s\n" % rec['RSZBlabel']
            if rec['Slabel']:
                s += "// Sutherland label: %s\n" % rec['Slabel']
            if rec['SZlabel']:
                s += "// Sutherland-Zywina label: %s\n" % rec['SZlabel']
        s += "\n// Group data\n"
        s += "level := %s;\n" % rec['level']
        s += "// Elements that, together with Gamma(level), generate the group\n"
        s += "gens := %s;\n" % rec['generators']
        s += "// Group contains -1?\n"
        if rec['contains_negative_one']:
            s += "ContainsMinus1 := true;\n"
        else:
            s += "ContainsMinus1 := false;\n"
        s += "// Index in Gamma(1)\n"
        s += "index := %s;\n" % rec['index']
        s += "\n// Curve data\n"
        s += "conductor := %s;\n" % rec['conductor']
        s += "bad_primes := %s;\n" % rec['bad_primes']
        s += "// Genus\n"
        s += "g := %s;\n" % rec['genus']
        s += "// Rank\n"
        s += "r := %s\n;" % rec['rank']
        if rec['q_gonality'] != -1:
            s += "// Exact gonality known\n"
            s += "gamma := %s;\n" % rec['q_gonality']
        else:
            s += "// Exact gonality unknown, but contained in following interval\n"
            s += "gamma_int := %s;\n" % rec['q_gonality_bounds']
        s += "\n// Modular data\n"
        s += "// Number of cusps\n"
        s += "Ncusps := %s\n;" % rec['cusps']
        s += "// Number of rational cusps\n"
        s += "Nrat_cusps := %s\n;" % rec['rational_cusps']
        s += "// CM discriminants\n"
        s += "CM_discs := %s;\n" % rec['cm_discriminants']
        if rec['factorization'] != []:
            s += "// Modular curve is a fiber product of the following curves"
            s += "factors := %s\n" % [f.replace("'", "\"") for f in rec['factorization']]
        s += "// Groups containing given group, corresponding to curves covered by given curve\n"
        parents_mag = "%s" % rec['parents']
        parents_mag = parents_mag.replace("'", "\"")
        s += "covers := %s;\n" % parents_mag

        s += "\n// Models for this modular curve, if computed\n"
        models = list(db.modcurve_models.search(
            {"modcurve": label, "model_type":{"$not":1}},
            ["equation", "number_variables", "model_type", "smooth"]))
        if models:
            max_nb_variables = max([m["number_variables"] for m in models])
            variables = "xyzwtuvrsabcdefghiklmnopqj"[:max_nb_variables]
            s += "Pol<%s" % variables[0]
            for x in variables[1:]:
                s += ",%s" % x
            s += "> := PolynomialRing(Rationals(), %s);\n" % max_nb_variables

        s += "// Isomorphic to P^1?\n"
        is_P1 = "true" if (rec['genus'] == 0 and rec['pointless'] is False) else "false"
        s += "is_P1 := %s;\n" % is_P1
        model_id = 0
        for m in models:
            if m["model_type"] == 0:
                name = "Canonical model"
            elif m["model_type"] == 2:
                if m["smooth"] is True:
                    name = "Smooth plane model"
                elif m["smooth"] is False:
                    name = "Singular plane model"
                else:
                    name = "Plane model"
            elif m["model_type"] == 5:
                name = "Weierstrass model"
            elif m["model_type"] == 7:
                name = "Double cover of conic"
            elif m["model_type"] == 8:
                name = "Embedded model"
            else:
                name = "Other model"
            s += "\n// %s\n" % name
            s += "model_%s := [" % model_id
            s += ",".join(m['equation'])
            s += "];\n"
            model_id += 1

        s += "\n// Maps from this modular curve, if computed\n"
        maps = list(db.modcurve_modelmaps.search(
            {"domain_label": label},
            ["domain_model_type", "codomain_label", "codomain_model_type",
             "coordinates", "leading_coefficients"]))
        codomain_labels = [m["codomain_label"] for m in maps]
        codomain_models = list(db.modcurve_models.search(
            {"modcurve": {"$in": codomain_labels}},
            ["equation", "modcurve", "model_type"]))
        map_id = 0
        #if maps and is_P1: #variable t has not been introduced above
        #     s += "Pol<t> := PolynomialRing(Rationals());\n"
        #This was using t twice when the genus was large enough that t was used above. Even when t is not defined above, t is not used below.
        for m in maps:
            prefix = "map_%s_" % map_id
            has_codomain_equation = False
            if m["codomain_label"] == "1.1.0.a.1":
                if m["codomain_model_type"] == 1:
                    name = "j-invariant map"
                elif m["codomain_model_type"] == 4:
                    name = "E4, E6"
                else:
                    name = "Other map to X(1)"
            else:
                name = "Map"
            if m["domain_model_type"] == 0:
                name += " from the canonical model"
            elif m["domain_model_type"] == 8:
                name += " from the embedded model"
            elif m["domain_model_type"] == 5:
                name += " from the Weierstrass model"
            elif m["domain_model_type"] == 2:
                name += " from the plane model"
            if m["codomain_label"] != "1.1.0.a.1":
                has_codomain_equation = True
                if m["codomain_model_type"] == 0:
                    name += " to the canonical model of modular curve"
                elif m["codomain_model_type"] == 1:
                    has_codomain_equation = False
                    name += " to a modular curve isomorphic to P^1"
                elif m["codomain_model_type"] == 2:
                    name += " to the plane model of modular curve"
                elif m["codomain_model_type"] == 5:
                    name += " to the Weierstrass model of modular curve"
                else:
                    name += " to another model of modular curve"
                name += " with label %s" % m["codomain_label"]
            s += "\n// %s\n" % name
            coord = m["coordinates"]
            if m["leading_coefficients"] is None:
                lead = [1]*len(coord)
            else:
                lead = m["leading_coefficients"]
            for j in range(len(coord)):
                s += "//   Coordinate number %s:\n" % j
                s += prefix + ("coord_%s := " % j)
                s += "%s*(" % lead[j]
                s += "%s);\n" % coord[j]
            if has_codomain_equation:
                s += "// Codomain equation:\n"
                eq = [eq for eq in codomain_models if eq["modcurve"] == m["codomain_label"] and eq["model_type"] == m["codomain_model_type"]][0]
                s += prefix + "codomain := " + "[%s];\n" % ",".join(eq["equation"])
            map_id += 1
        return s

    def download_modular_curve_magma(self, label):
        s = self.download_modular_curve_magma_str(label)
        return self._wrap(s, label, lang="magma")

    def download_modular_curve_sage(self, label):
        s = self.download_modular_curve_magma_str(label)
        s = s.replace(":=", "=")
        s = s.replace(";", "")
        s = s.replace("//", "#")
        s = s.replace("K<", "K.<")
        return self._wrap(s, label, lang="sage")

    def download_modular_curve(self, label, lang):
        if lang == "magma":
            return self.download_modular_curve_magma(label)
        elif lang == "sage":
            return self.download_modular_curve_sage(label)
        elif lang == "text":
            data = combined_data(label)
            if data is None:
                return abort(404, "Label not found: %s" % label)
            return self._wrap(Json.dumps(data),
                              label,
                              lang=lang,
                              title='Data for modular curve with label %s,' % label)

@modcurve_page.route("/download_to_magma/<label>")
def modcurve_magma_download(label):
    return ModCurve_download().download_modular_curve(label, lang="magma")

@modcurve_page.route("/download_to_sage/<label>")
def modcurve_sage_download(label):
    return ModCurve_download().download_modular_curve(label, lang="sage")

@modcurve_page.route("/download_to_text/<label>")
def modcurve_text_download(label):
    return ModCurve_download().download_modular_curve(label, lang="text")

# !!! TODO : currently there is a lot of overlapping with code creating the Gassmann class. Should solve this more generally by refactoring the search and download
def modcurve_Gassmann_download(request, lang):
    query_dict = to_dict(request.args)
    print("query_dict", query_dict)
    ncurves = db.gps_gl2zhat_fine.count(query_dict)
    info = {}
    info["Submit"] = lang
    info["query"] = str(query_dict)
    print("info query = ", info["query"])
    info["results"] = []
    for i in range(ncurves):
        query_dict.update({'coarse_num' : i+1})
        info["results"].append(db.gps_gl2zhat_fine.lucky(query_dict))
    info["search_table"] = db.gps_gl2zhat_fine
    info["columns"] = modcurve_columns
    info["showcol"] = ".".join(["CPlabel", "RSZBlabel", "RZBlabel", "SZlabel", "Slabel", "rank", "cusps", "conductor", "simple", "squarefree", "decomposition", "models", "j-points", "local obstruction", "generators"])
    return ModCurve_download()(info)

@modcurve_page.route("/download_Gassmann_to_magma/")
def modcurve_Gassmann_magma_download():
    return modcurve_Gassmann_download(request, lang="magma")

@modcurve_page.route("/download_Gassmann_to_sage/")
def modcurve_Gassmann_sage_download():
    return modcurve_Gassmann_download(request, lang="sage")

@modcurve_page.route("/download_Gassmann_to_text/")
def modcurve_Gassmann_text_download():
    return modcurve_Gassmann_download(request, lang="text")

@search_wrap(
    table=db.gps_gl2zhat_fine,
    title="Modular curve search results",
    err_title="Modular curves search input error",
    shortcuts={"jump": modcurve_jump, "download": ModCurve_download()},
    columns=modcurve_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_modcurve_label,
)
def modcurve_search(info, query):
    parse_ints(info, query, "level")
    if info.get('level_type'):
        if info['level_type'] == 'prime':
            query['num_bad_primes'] = 1
            query['level_is_squarefree'] = True
        elif info['level_type'] == 'prime_power':
            query['num_bad_primes'] = 1
        elif info['level_type'] == 'squarefree':
            query['level_is_squarefree'] = True
        elif info['level_type'] in ['divides', 'multiple']:
            if not isinstance(query.get('level'), int):
                err = "You must specify a single level"
                flash_error(err)
                raise ValueError(err)
            elif info['level_type'] == 'divides':
                query['level'] = {'$in': integer_divisors(ZZ(query['level']))}
            else:
                query['level'] = {'$mod': [0, ZZ(query['level'])]}
    parse_family(info, query, "family", qfield="name")
    parse_ints(info, query, "index")
    parse_ints(info, query, "genus")
    parse_ints(info, query, "rank")
    parse_ints(info, query, "genus_minus_rank")
    parse_ints(info, query, "cusps")
    parse_interval(info, query, "q_gonality", quantifier_type=info.get("gonality_type", "exactly"))
    parse_ints(info, query, "rational_cusps")
    parse_ints(info, query, "nu2")
    parse_ints(info, query, "nu3")
    if not info.get("points_type"): # default, which is non-cuspidal
        parse_ints(info, query, "points", qfield="num_known_degree1_noncusp_points")
    elif info["points_type"] == "noncm":
        parse_ints(info, query, "points", qfield="num_known_degree1_noncm_points")
    elif info["points_type"] == "all":
        parse_ints(info, query, "points", qfield="num_known_degree1_points")
    parse_bool_unknown(info, query, "has_obstruction")
    parse_bool(info, query, "simple")
    parse_bool(info, query, "squarefree")
    parse_bool(info, query, "contains_negative_one")
    if "cm_discriminants" in info:
        if info["cm_discriminants"] == "yes":
            query["cm_discriminants"] = {"$ne": []}
        elif info["cm_discriminants"] == "no":
            query["cm_discriminants"] = []
        elif info["cm_discriminants"] == "-3,-12,-27":
            query["cm_discriminants"] = {"$or": [{"$contains": int(D)} for D in [-3,-12,-27]]}
        elif info["cm_discriminants"] == "-4,-16":
            query["cm_discriminants"] = {"$or": [{"$contains": int(D)} for D in [-4,-16]]}
        elif info["cm_discriminants"] == "-7,-28":
            query["cm_discriminants"] = {"$or": [{"$contains": int(D)} for D in [-7,-28]]}
        else:
            query["cm_discriminants"] = {"$contains": int(info["cm_discriminants"])}
    parse_noop(info, query, "CPlabel")
    parse_element_of(info, query, "covers", qfield="parents", parse_singleton=str)
    parse_element_of(info, query, "factor", qfield="factorization", parse_singleton=str)
    if "covered_by" in info:
        # sort of hacky
        lmfdb_label, label_type = modcurve_lmfdb_label(info["covered_by"])
        if lmfdb_label is None:
            parents = None
        else:
            if "-" in lmfdb_label:
                # fine label
                rec = db.gps_gl2zhat_fine.lookup(lmfdb_label, ["parents", "coarse_label"])
                parents = [rec["coarse_label"]] + rec["parents"]
            else:
                # coarse label
                parents = db.gps_gl2zhat_fine.lookup(lmfdb_label, "parents")
        if parents is None:
            msg = "%s not the label of a modular curve in the database"
            flash_error(msg, info["covered_by"])
            raise ValueError(msg % info["covered_by"])
        query["label"] = {"$in": parents}

modcurve_sorts = [
    ("", "level", ["level", "index", "genus", "label"]),
    ("index", "index", ["index", "level", "genus", "label"]),
    ("genus", "genus", ["genus", "level", "index", "label"]),
    ("rank", "rank", ["rank", "genus", "level", "index", "label"]),

]
class ModCurveSearchArray(SearchArray):
    noun = "curve"
    jump_example = "13.78.3.a.1"
    jump_egspan = "e.g. 13.78.3.a.1, 13.78.3.a, 13.78.3.1, XNS+(13), 13Nn, 13A3, or X0(3)*X1(5) (fiber product over $X(1)$)"
    jump_prompt = "Label or name"
    jump_knowl = "modcurve.search_input"

    def __init__(self):
        level_quantifier = SelectBox(
            name="level_type",
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides', 'divides'),
                     ('multiple', 'multiple of'),
                     ],
            min_width=85)
        level = TextBoxWithSelect(
            name="level",
            knowl="modcurve.level",
            label="Level",
            example="11",
            example_span="2, 11-23",
            select_box=level_quantifier,
        )
        index = TextBox(
            name="index",
            knowl="modcurve.index",
            label="Index",
            example="6",
            example_span="6, 12-100",
        )
        genus = TextBox(
            name="genus",
            knowl="modcurve.genus",
            label="Genus",
            example="1",
            example_span="0, 2-3",
        )
        rank = TextBox(
            name="rank",
            knowl="modcurve.rank",
            label="Rank",
            example="1",
            example_span="0, 2-3",
        )
        genus_minus_rank = TextBox(
            name="genus_minus_rank",
            knowl="modcurve.genus_minus_rank",
            label="Genus-rank difference",
            example="0",
            example_span="0, 1",
        )
        cusps = TextBox(
            name="cusps",
            knowl="modcurve.cusps",
            label="Cusps",
            example="1",
            example_span="1, 4-8",
        )
        rational_cusps = TextBox(
            name="rational_cusps",
            knowl="modcurve.cusps",
            label=r"$\Q$-cusps",
            example="1",
            example_span="0, 4-8",
        )
        gonality_quantifier = SelectBox(
            name="gonality_type",
            options=[('', 'exactly'),
                     ('possibly', 'possibly'),
                     ('atleast', 'at least'),
                     ('atmost', 'at most'),
                     ('inexactly', 'inexactly'),
                     ],
            min_width=86,
        )
        gonality = TextBoxWithSelect(
            name="q_gonality",
            knowl="modcurve.gonality",
            label=r"$\Q$-gonality",
            example="2",
            example_span="2, 3-6",
            select_box=gonality_quantifier,
        )
        nu2 = TextBox(
            name="nu2",
            knowl="modcurve.elliptic_points",
            label="Elliptic points of order 2",
            example="1",
            example_span="1,3-5",
        )
        nu3 = TextBox(
            name="nu3",
            knowl="modcurve.elliptic_points",
            label="Elliptic points of order 3",
            example="1",
            example_span="1,3-5",
        )
        factor = TextBox(
            name="factor",
            knowl="modcurve.fiber_product",
            label="Fiber product with",
            example="3.4.0.a.1",
        )
        covers = TextBox(
            name="covers",
            knowl="modcurve.modular_cover",
            label="Minimally covers",
            example="1.1.0.a.1",
        )
        covered_by = TextBox(
            name="covered_by",
            knowl="modcurve.modular_cover",
            label="Minimally covered by",
            example="6.12.0.a.1",
        )
        simple = YesNoBox(
            name="simple",
            knowl="modcurve.simple",
            label="Simple",
            example_col=True,
        )
        squarefree = YesNoBox(
            name="squarefree",
            knowl="av.squarefree",
            label="Squarefree",
            example_col=True,
        )
        cm_opts = ([('', ''), ('yes', 'rational CM points'), ('no', 'no rational CM points')]
                   + [('-4,-16', 'CM field Q(sqrt(-1))'), ('-3,-12,-27', 'CM field Q(sqrt(-3))'), ('-7,-28', 'CM field Q(sqrt(-7))')]
                   + [('-%d' % d, 'CM discriminant -%d' % d) for d in [3,4,7,8,11,12,16,19,27,38,43,67,163]])
        cm_discriminants = SelectBox(
            name="cm_discriminants",
            options=cm_opts,
            knowl="modcurve.cm_discriminants",
            label="CM points",
            example="yes, no, CM discriminant -3"
        )
        contains_negative_one = YesNoBox(
            name="contains_negative_one",
            knowl="modcurve.contains_negative_one",
            label="Contains $-I$",
            example="yes",
            example_col=True,
            example_span="",
        )
        points_type = SelectBox(
            name="points_type",
            options=[('', 'non-cusp'),
                     ('noncm', 'non-CM/cusp'),
                     ('all', 'all'),
                     ],
            min_width=114,
        )
        points = TextBoxWithSelect(
            name="points",
            knowl="modcurve.known_points",
            label="Points",
            example="0, 3-5",
            select_box=points_type,
        )
        obstructions = SelectBox(
            name="has_obstruction",
            options=[("", ""),
                     ("yes", "Known obstruction"),
                     ("not_yes", "No known obstruction"),
                     ("no", "No obstruction")],
            knowl="modcurve.local_obstruction",
            label="Obstructions")
        family = SelectBox(
            name="family",
            options=[("", ""),
                     ("X0", "X0(N)"),
                     ("X1", "X1(N)"),
                     ("Xpm1", "X±1(N)"),
                     ("X", "X(N)"),
                     ("Xarith1", "Xarith1(M,MN)"),
                     ("Xarithpm1", "Xarith±1(M,MN)"),
                     ("Xsp", "Xsp(N)"),
                     ("Xns", "Xns(N)"),
                     ("Xspplus", "Xsp+(N)"),
                     ("Xnsplus", "Xns+(N)"),
                     ("XS4", "XS4(N)"),
                     ("Xarith", "Xarith(N)"),
                     ("any", "any")],
            knowl="modcurve.standard",
            label="Family",
            example="X0(N), Xsp(N)")
        CPlabel = SneakyTextBox(
            name="CPlabel",
            knowl="modcurve.other_labels",
            label="CP label",
            example="3B0",
        )
        count = CountBox()

        self.browse_array = [
            [level, index],
            [genus, rank],
            [genus_minus_rank, gonality],
            [cusps, rational_cusps],
            [nu2, nu3],
            [simple, squarefree],
            [cm_discriminants, factor],
            [covers, covered_by],
            [contains_negative_one, family],
            [points, obstructions],
            [count],
        ]

        self.refine_array = [
            [level, index, genus, rank, genus_minus_rank],
            [gonality, cusps, rational_cusps, nu2, nu3],
            [simple, squarefree, cm_discriminants, factor, covers],
            [covered_by, contains_negative_one, points, obstructions, family],
            [CPlabel],
        ]

    sorts = modcurve_sorts

    null_column_explanations = {
        'simple': False,
        'squarefree': False,
        'rank': False,
        'genus_minus_rank': False,
        'name': False,
    }

class FamilySearchArray(EmbeddedSearchArray):
    sorts = modcurve_sorts

@modcurve_page.route("/Q/family/<name>")
def family_page(name):
    info = to_dict(request.args, search_array=FamilySearchArray(), name=name)
    try:
        info["family"] = family = ModCurveFamily(name)
    except ValueError:
        flash_error(f"There is no family with name {name}")
        return redirect(url_for(".index_Q"))
    info["title"] = family.title
    info["bread"] = family.bread
   # info["properties"] = family.properties
    return render_family(info)

@embed_wrap(
    table=db.gps_gl2zhat_fine,
    template="modcurve_family.html",
    err_title="Modular curve family error",
    columns=modcurve_columns,
    learnmore=learnmore_list,
    # Each of the following arguments is set here so that it overridden when constructing template_kwds,
    # which prioritizes values found in info (which are set in family_page() before calling render_family)
    bread=lambda:None,
    properties=lambda:None,
    family=lambda:None,
)
def render_family(info, query):
    parse_family(info, query, 'name')

@modcurve_page.route("/Q/low_degree_points")
def low_degree_points():
    info = to_dict(request.args, search_array=RatPointSearchArray())
    return rational_point_search(info)

ratpoint_columns = SearchColumns([
    LinkCol("curve_label", "modcurve.label", "Label", url_for_modcurve_label),
    #SearchCol("curve_RSZBlabel", "modcurve.other_labels", "RSZB label", short_title="RSZB label", default=False),
    ProcessedCol("curve_name", "modcurve.standard", "Name", name_to_latex, default=False),
    MathCol("curve_genus", "modcurve.genus", "Genus"),
    MathCol("degree", "modcurve.point_degree", "Degree"),
    ProcessedCol("isolated", "modcurve.isolated_point", "Isolated",
                 lambda x: r"&#x2713;" if x == 4 else (r"" if x in [2,-1,-2,-3,-4] else r"<i>?</i>"), align="center"),
    ProcessedCol("cm_discriminant", "ec.complex_multiplication", "CM", lambda v: "" if v == 0 else v,
                 short_title="CM discriminant", mathmode=True, align="center", orig="cm"),
    LinkCol("Elabel", "modcurve.elliptic_curve_of_point", "Elliptic curve", lambda Elabel: url_for_ECNF_label(Elabel) if "-" in Elabel else url_for_EC_label(Elabel)),
    ProcessedCol("residue_field", "modcurve.point_residue_field", "Residue field", lambda field: nf_display_knowl(field, field_pretty(field)), align="center"),
    ProcessedCol("j_field", "ec.j_invariant", r"$\Q(j)$", lambda field: nf_display_knowl(field, field_pretty(field)), align="center", short_title="Q(j)"),
    MultiProcessedCol("jinv", "ec.j_invariant", "$j$-invariant", ["jinv", "j_field", "jorig", "residue_field"], showj_nf, download_col="jinv"),
    FloatCol("j_height", "nf.weil_height", "$j$-height"),
])

def ratpoint_postprocess(res, info, query):
    labels = list({rec["curve_label"] for rec in res})
    RSZBlabels = {rec["label"]: rec["RSZBlabel"] for rec in db.gps_gl2zhat_fine.search({"label":{"$in":labels}}, ["label", "RSZBlabel"])}
    for rec in res:
        rec["curve_RSZBlabel"] = RSZBlabels.get(rec["curve_label"], "")
    return res

@search_wrap(
    table=db.modcurve_points,
    title="Modular curve low-degree point search results",
    err_title="Modular curves low-degree point search input error",
    columns=ratpoint_columns,
    shortcuts={"download": Downloader(db.modcurve_points)},
    bread=lambda: get_bread("Low-degree point search results"),
    #postprocess=ratpoint_postprocess,
)
def rational_point_search(info, query):
    parse_noop(info, query, "curve", qfield="curve_label")
    parse_ints(info, query, "genus", qfield="curve_genus")
    parse_ints(info, query, "level", qfield="curve_level")
    parse_family(info, query, "family", qfield="curve_name")
    parse_ints(info, query, "degree")
    parse_nf_string(info, query, "residue_field")
    parse_nf_string(info, query, "j_field")
    j_field = query.get("j_field")
    if not j_field:
        j_field = query.get("residue_field")
    parse_nf_jinv(info, query, "jinv", field_label=j_field)
    parse_floats(info, query, "j_height")
    if 'cm' in info:
        if info['cm'] == 'noCM':
            query['cm'] = 0
        elif info['cm'] == 'CM':
            query['cm'] = {'$ne': 0}
        else:
            parse_ints(info, query, 'cm')
    if "isolated" in info:
        if info['isolated'] == "yes":
            query['isolated'] = 4
        elif info['isolated'] == "no":
            query['isolated'] = { "$in" : [2,-1,-2,-3,-4] }
        elif info['isolated'] == "not_yes":
            query['isolated'] = { "$ne" : 4 }
        elif info['isolated'] == "not_no":
            query['isolated'] = { "$in" : [0,1,3,4] }
        elif info['isolated'] == "unknown":
            query['isolated'] = { "$in" : [0,1,3] }
    parse_bool(info, query, "cusp")

class RatPointSearchArray(SearchArray):
    noun = "point"
    sorts = [("", "level", ["curve_level", "curve_genus", "curve_index", "curve_label", "degree", "j_height", "jinv"]),
             ("curve_genus", "genus", ["curve_genus", "curve_level", "curve_index", "curve_label", "degree", "j_height", "jinv"]),
             ("degree", "degree", ["degree", "curve_level", "curve_genus", "curve_index", "curve_label", "j_height", "jinv"]),
             ("j_height", "height of j-invariant", ["j_height", "jinv", "degree", "curve_level", "curve_genus", "curve_index", "curve_label"]),
             ("conductor", "minimal conductor norm", ["conductor_norm", "j_height", "jinv", "degree", "curve_level", "curve_genus", "curve_index", "curve_label"]),
             ("residue_field", "residue field", ["degree", "residue_field", "curve_level", "curve_genus", "curve_index", "curve_label", "j_height", "jinv"]),
             ("cm", "CM discriminant", ["cm", "degree", "curve_level", "curve_genus", "curve_index", "curve_label", "j_height", "jinv"])]
    def __init__(self):
        curve = TextBox(
            name="curve",
            knowl="modcurve.label",
            label="Curve",
            example="11.12.1.1",
        )
        genus = TextBox(
            name="genus",
            knowl="modcurve.genus",
            label="Genus",
            example="1-3",
        )
        level = TextBox(
            name="level",
            knowl="modcurve.level",
            label="Level",
            example="37"
        )
        degree = TextBox(
            name="degree",
            knowl="modcurve.point_degree",
            label="Degree",
            example="2-4",
        )
        residue_field = TextBox(
            name="residue_field",
            knowl="modcurve.point_residue_field",
            label="Residue field",
            example="2.0.4.1",
        )
        j_field = TextBox(
            name="j_field",
            knowl="ec.j_invariant",
            label=r"$\Q(j)$",
            example="2.0.4.1",
        )
        jinv = TextBox(
            name="jinv",
            knowl="ec.j_invariant",
            label="$j$-invariant",
            example="30887/73-9927/73*a",
        )
        j_height = TextBox(
            name="j_height",
            knowl="nf.weil_height",
            label="$j$-height",
            example="1.0-4.0",
        )
        cm_opts = ([('', ''), ('noCM', 'no potential CM'), ('CM', 'potential CM')]
                   + [('-4,-16', 'CM field Q(sqrt(-1))'), ('-3,-12,-27', 'CM field Q(sqrt(-3))'), ('-7,-28', 'CM field Q(sqrt(-7))')]
                   + [('-%d' % d, 'CM discriminant -%d' % d) for d in [3,4,7,8,11,12,16,19,27,38,43,67,163]])
        cm = SelectBox(
            name="cm",
            label="Complex multiplication",
            example="potential CM by Q(i)",
            knowl="ec.complex_multiplication",
            options=cm_opts,
        )
        isolated = YesNoMaybeBox(
            "isolated",
            label="Isolated",
            knowl="modcurve.isolated_point",
        )
        family = SelectBox(
            name="family",
            options=[("", ""),
                     ("X0", "X0(N)"),
                     ("X1", "X1(N)"),
                     ("Xpm1", "Xpm1(N)"),
                     ("X", "X(N)"),
                     ("Xarith1", "Xarith1(M,MN)"),
                     ("Xarithpm1", "Xarith±1(M,MN)"),
                     ("Xsp", "Xsp(N)"),
                     ("Xns", "Xns(N)"),
                     ("Xspplus", "Xsp+(N)"),
                     ("Xnsplus", "Xns+(N)"),
                     ("XS4", "XS4(N)"),
                     ("Xarith", "Xarith(N)"),
                     ("any", "any")],
            knowl="modcurve.standard",
            label="Family",
            example="X0(N), Xsp(N)")
        cusp = YesNoBox(
            "cusp",
            label="Cusp",
            knowl="modcurve.cusps")

        self.refine_array = [[curve, level, genus, degree, cm],
                             [residue_field, j_field, jinv, j_height, isolated],
                             [family, cusp]]

    def search_types(self, info):
        # There is no homepage for a point, so we disable the random link
        return [("List", "Search again")]

class ModCurve_stats(StatsDisplay):
    def __init__(self):
        self.ncurves = comma(db.gps_gl2zhat_fine.count())
        self.max_level = db.gps_gl2zhat_fine.max("level")

    @property
    def short_summary(self):
        modcurve_knowl = display_knowl("modcurve", title="modular curves")
        return (
            fr'The database currently contains {self.ncurves} {modcurve_knowl} of level $N\le {self.max_level}$ parameterizing elliptic curves $E$ over $\Q$.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.'
        )

    @property
    def summary(self):
        modcurve_knowl = display_knowl("modcurve", title="modular curves")
        return (
            fr'The database currently contains {self.ncurves} {modcurve_knowl} of level $N\le {self.max_level}$ parameterizing elliptic curves $E/\Q$.'
        )

    table = db.gps_gl2zhat_fine
    baseurl_func = ".index"
    buckets = {'level': ['1-4', '5-8', '9-12', '13-16', '17-20', '21-'],
               'genus': ['0', '1', '2', '3', '4-6', '7-20', '21-100', '101-'],
               'rank': ['0', '1', '2', '3', '4-6', '7-20', '21-100', '101-'],
               'gonality': ['1', '2', '3', '4', '5-8', '9-'],
               }
    knowls = {'level': 'modcurve.level',
              'genus': 'modcurve.genus',
              'rank': 'modcurve.rank',
              'gonality': 'modcurve.gonality',
              }
    stat_list = [
        {'cols': ['level', 'genus'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
        {'cols': ['genus', 'rank'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
        {'cols': ['genus', 'q_gonality'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
    ]

@modcurve_page.route("/Q/stats")
def statistics():
    title = 'Modular curves: Statistics'
    return render_template("display_stats.html", info=ModCurve_stats(), title=title, bread=get_bread('Statistics'), learnmore=learnmore_list())

@modcurve_page.route("/ModularCurvePictures")
def mcurve_picture_page():
    t = r'Pictures for modular curves'
    bread = get_bread("Modular Curve Picture")
    return render_template(
        "single.html",
        kid='portrait.modcurve',
        title=t,
        bread=bread,
        learnmore=learnmore_list()
    )

@modcurve_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for modular curve data'
    bread = get_bread('Source')
    return render_template("multi.html",
                           kids=['rcs.source.modcurve',
                           'rcs.ack.modcurve',
                           'rcs.cite.modcurve'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@modcurve_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of modular curve data'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.modcurve',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@modcurve_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of modular curve data'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.modcurve',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@modcurve_page.route("/Labels")
def labels_page():
    t = r'Labels for modular curves'
    bread = get_bread('Labels')
    return render_template("single.html", kid='modcurve.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

# !! TODO - overlapping code between the two options coming from different merges
@modcurve_page.route("/data/<label>")
def modcurve_data(label):
    coarse_label = db.gps_gl2zhat_fine.lookup(label, "coarse_label")
    bread = get_bread([(label, url_for_modcurve_label(label)), ("Data", " ")])
    if not LABEL_RE.fullmatch(label):
        if not ISO_CLASS_RE.fullmatch(label):
            return abort(404)
        N, i, g, iso = label.split(".")
        iso_num = class_to_int(iso)+1
        labels = db.gps_gl2zhat_fine.search({"coarse_level" : N,
                                             "coarse_index" : i,
                                             "genus" : g,
                                             "coarse_class_num" : iso_num,
                                             "contains_negative_one" : "yes"},
                                            "label")
        labels = list(labels)
        label_tables_cols = [(label, "gps_gl2zhat_fine", "label") for label in labels]
    else:
        label_tables_cols = [(label, "gps_gl2zhat_fine", "label")]
        if label != coarse_label:
            label_tables_cols.append((coarse_label, "gps_gl2zhat_fine", "label"))
        # modcurve_models
        label_tables_cols.append((coarse_label, "modcurve_models", "modcurve"))
        # modcurve_modelmaps
        label_tables_cols.append((coarse_label, "modcurve_modelmaps", "domain_label"))
        # modcurve_points
        label_tables_cols.append((coarse_label, "modcurve_points", "curve_label"))

    labels, tables, label_cols = map(list, zip(*label_tables_cols)) # transpose
    return datapage(labels, tables, title=f"Modular curve data - {label}", bread=bread, label_cols=label_cols)
