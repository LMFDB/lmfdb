# -*- coding: utf-8 -*-

import re
from collections import Counter
from lmfdb import db

from flask import render_template, url_for, request, redirect, abort

from sage.all import ZZ

from lmfdb.utils import (
    SearchArray,
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
from lmfdb.shimura_curves import shimcurve_page
from lmfdb.shimura_curves.web_curve import (
    WebShimCurve, get_bread, canonicalize_name, name_to_latex, factored_conductor,
    formatted_dims, url_for_EC_label, url_for_ECNF_label, showj_nf, combined_data,
)

coarse_label_re = r"\d+\.\d+\.\d+\.\d+\.\d+\.[a-z]+\.\d+"
fine_label_re = r"\d+\.\d+\.\d+\.\d+\.\d+-\d+\.\d+\.[a-z]+\.\d+\.\d+"
LABEL_RE = re.compile(f"({coarse_label_re})|({fine_label_re})")
FINE_LABEL_RE = re.compile(fine_label_re)
NAME_RE = re.compile(r"X\(\d+(;|,)\d+\)")

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Shimura curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def learnmore_list_add(learnmore_label, learnmore_url):
    return learnmore_list() + [(learnmore_label, learnmore_url)]


@shimcurve_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@shimcurve_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=ShimCurveSearchArray())
    if request.args:
        return shimcurve_search(info)
    title = r"Shimura curves over $\Q$"
    info["level_list"] = ["1-4", "5-8", "9-12", "13-16", "17-23", "24-"]
    info["genus_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    info["rank_list"] = ["0", "1", "2", "3", "4-6", "7-20", "21-100", "101-"]
    info["stats"] = ShimCurve_stats()
    return render_template(
        "shimcurve_browse.html",
        info=info,
        title=title,
        bread=get_bread(),
        learnmore=learnmore_list(),
    )

@shimcurve_page.route("/Q/random/")
@redirect_no_cache
def random_curve():
    label = db.gps_shimura_test.random()
    return url_for_shimcurve_label(label)

@shimcurve_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "shimcurve",
        db.gps_shimura_test,
        url_for_shimcurve_label,
        title="Some interesting Shimura curves",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )

def shimcurve_link(label):
    if int(label.split(".")[0]) <= 70:
        return '<a href=%s>%s</a>' % (url_for("shimcurve.by_label", label=label), label)
    else:
        return label

@shimcurve_page.route("/Q/<label>/")
def by_label(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    curve = WebShimCurve(label)
    if curve.is_null():
        flash_error("There is no Shimura curve %s in the database", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(curve)
    learnmore_mcurve_pic = ('Picture description', url_for(".scurve_picture_page"))
    return render_template(
        "shimcurve.html",
        curve=curve,
        dojs=dojs,
        zip=zip,
        name_to_latex=name_to_latex,
        properties=curve.properties,
        friends=curve.friends,
        bread=curve.bread,
        title=curve.title,
        downloads=curve.downloads,
        KNOWL_ID=f"shimcurve.{label}",
        learnmore=learnmore_list_add(*learnmore_mcurve_pic)
    )

@shimcurve_page.route("/Q/diagram/<label>")
def lat_diagram(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    curve = WebShimCurve(label)
    if curve.is_null():
        flash_error("There is no Shimura curve %s in the database", label)
        return redirect(url_for(".index"))
    dojs, display_opts = diagram_js_string(curve)
    info = {"dojs": dojs}
    info.update(display_opts)
    return render_template(
        "lat_diagram_page.html",
        dojs=dojs,
        info=info,
        title="Diagram of nearby Shimura curves for %s" % label,
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

@shimcurve_page.route("/Q/curveinfo/<label>")
def curveinfo(label):
    if not LABEL_RE.fullmatch(label):
        return ""
    level, index, genus = label.split(".")[:3]

    ans = 'Information on the Shimura curve <a href="%s">%s</a><br>\n' % (url_for_shimcurve_label(label), label)
    ans += "<table>\n"
    ans += f"<tr><td>{display_knowl('shimcurve.level', 'Level')}</td><td>${level}$</td></tr>\n"
    ans += f"<tr><td>{display_knowl('shimcurve.index', 'Index')}</td><td>${index}$</td></tr>\n"
    ans += f"<tr><td>{display_knowl('shimcurve.genus', 'Genus')}</td><td>${genus}$</td></tr>\n"
    ans += "</table>"
    return ans

def url_for_shimcurve_label(label):
    return url_for(".by_label", label=label)

def url_for_RZB_label(label):
    return "https://users.wfu.edu/rouseja/2adic/" + label + ".html"

def url_for_CP_label(label):
    genus = CP_LABEL_GENUS_RE.fullmatch(label)[1]
    return "https://mathstats.uncg.edu/sites/pauli/congruence/csg" + genus + ".html#group" + label

def shimcurve_lmfdb_label(label):
    if LABEL_RE.fullmatch(label):
        label_type = "label"
        lmfdb_label = label
    elif NAME_RE.fullmatch(label.upper()):
        label_type = "name"
        lmfdb_label = db.gps_shimura_test.lucky({"name": canonicalize_name(label)}, "label")
    else:
        label_type = "label"
        lmfdb_label = None
    return lmfdb_label, label_type

def shimcurve_jump(info):
    labels = (info["jump"]).split("*")
    lmfdb_labels = []
    for label in labels:
        lmfdb_label, label_type = shimcurve_lmfdb_label(label)
        if lmfdb_label is None:
            flash_error("There is no Shimura curve in the database with %s %s", label_type, label)
            return redirect(url_for(".index"))
        lmfdb_labels.append(lmfdb_label)
    lmfdb_labels_not_X1 = [l for l in lmfdb_labels if l != "1.1.0.a.1"]
    if len(lmfdb_labels) == 1:
        label = lmfdb_labels[0]
        return redirect(url_for_shimcurve_label(label))
    elif len(lmfdb_labels_not_X1) == 1:
        label = lmfdb_labels_not_X1[0]
        return redirect(url_for_shimcurve_label(label))
    else:
        # Get factorization for each label
        factors = list(db.gps_shimura_test.search({"label": {"$in": lmfdb_labels_not_X1}},
                                                  ["label","factorization"]))
        factors = [(f["factorization"] if f["factorization"] != [] else [f["label"]])
                   for f in factors]
        # Check labels are indeed distinct
        if len(factors) != len(lmfdb_labels_not_X1):
            flash_error("Fiber product decompositions cannot contain repeated terms")
            return redirect(url_for(".index"))
        # Get list of all factors, lexicographically sorted
        factors = sorted(sum(factors, []), key=key_for_numerically_sort)
        label = db.gps_shimura_test.lucky({'factorization': factors}, "label")
        if label is None:
            flash_error("There is no Shimura curve in the database isomorphic to the fiber product %s", info["jump"])
            return redirect(url_for(".index"))
        else:
            return redirect(url_for_shimcurve_label(label))

def blankzeros(n):
    return "$%o$"%n if n else ""

shimcurve_columns = SearchColumns(
    [
        LinkCol("label", "shimcurve.label", "Label", url_for_shimcurve_label),
        ProcessedCol("name", "shimcurve.standard", "Name", lambda s: name_to_latex(s) if s else "", align="center"),
        MathCol("level", "shimcurve.level", "Level"),
        MathCol("index", "shimcurve.index", "Index"),
        MathCol("discB", "shimcurve.discb", r"$\operatorname{Disc}(B)$"),
        MathCol("discO", "shimcurve.disco", r"$\operatorname{nrd}(O)$"),
        MathCol("genus", "shimcurve.genus", "Genus"),
        ProcessedCol("rank", "shimcurve.rank", "Rank", lambda r: "" if r is None else r, default=lambda info: info.get("rank") or info.get("genus_minus_rank"), align="center", mathmode=True),
        ProcessedCol("q_gonality_bounds", "shimcurve.gonality", r"$\Q$-gonality", lambda b: r'$%s$'%(b[0]) if b[0] == b[1] else r'$%s \le \gamma \le %s$'%(b[0],b[1]), align="center", short_title="Q-gonality"),
        CheckCol("cm_discriminants", "shimcurve.cm_discriminants", "CM points", align="center"),
        ProcessedCol("conductor", "ag.conductor", "Conductor", factored_conductor, align="center", mathmode=True, default=False),
        CheckCol("simple", "shimcurve.simple", "Simple", default=False),
        CheckCol("squarefree", "av.squarefree", "Squarefree", default=False),
        CheckCol("contains_negative_one", "shimcurve.contains_negative_one", "Contains -1", short_title="contains -1", default=False),
        MultiProcessedCol("dims", "shimcurve.decomposition", "Decomposition", ["dims", "mults"], formatted_dims, align="center", apply_download=False, default=False),
        ProcessedCol("models", "shimcurve.models", "Models", blankzeros, default=False),
        MathCol("num_known_degree1_points", "shimcurve.known_points", "$j$-points", default=False),
        CheckCol("pointless", "shimcurve.local_obstruction", "Local obstruction", default=False),
        ProcessedCol("generators", "shimcurve.level_structure", r"$N_{B^{\times}}(O) \ltimes \operatorname{GL}_2(\mathbb{Z}/N\mathbb{Z})$-generators", lambda gens: ", ".join(r"$ \langle %s+%si+%sj+%sk, \begin{bmatrix}%s&%s\\%s&%s\end{bmatrix}$" % tuple(g) for g in gens) if gens else "trivial subgroup", short_title="generators", default=False),
    ],
    db_cols=["label", "name", "level", "index", "discB", "discO", "genus", "rank", "q_gonality_bounds", "cm_discriminants", "conductor", "simple", "squarefree", "contains_negative_one", "dims", "mults", "models", "pointless", "num_known_degree1_points", "generators"])

@search_parser
def parse_family(inp, query, qfield):
    if inp not in ["XD", "XDN", "XDstar", "XDNstar", "any"]:
        raise ValueError
    if inp == "any":
        query[qfield] = {"$like": "X%"}
    elif inp == "XD": #add nothing
        query[qfield] = {"$like": "X" + "(%;1)"}
    elif inp == "XDN":
        query[qfield] = {"$or":[{"$like": "X(%;%)", "$not": {"$like": "%,%"}}, {"$in":["X(6;1)", "X(6;2)"]}]}
    elif inp == "XDstar":
        query[qfield] = {"$like": "X^*" + "(%;1)"}
    elif inp == "XDNstar":
        query[qfield] = {"$like": "X^*" + "(%;%)"}
    else: #add X(6;1),X(6;2)
        query[qfield] = {"$or":[{"$like": inp + "(%"}, {"$in":["X(6;1)","X(6;2)"]}]}

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
    #'reductions',
    #'scalar_label',
    #'simple',
    #'sl2level',
    #'squarefree',
    #'tiebreaker',
    #'trace_hash',
    #'traces',
# cols currently unused in shimcurve_models
    #'dont_display'
    #'gonality_bounds'
    #'shimcurve'
# cols currently unused in shimcurve_modelmaps
    #'domain_label',
    #'dont_display',
    #'factored'

class ShimCurve_download(Downloader):
    table = db.gps_shimura_test
    title = "Shimura curves"
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

    def download_shimura_curve_magma_str(self, label):
        s = ""
        rec = combined_data(label)
        if rec is None:
            return abort(404, "Label not found: %s" % label)
        s += "// Magma code for Shimura curve with label %s\n\n" % label
        if rec['name']:
            s += "// Other names and/or labels\n"
            if rec['name']:
                s += "// Curve name: %s\n" % rec['name']
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
        s += "// CM discriminants\n"
        s += "CM_discs := %s;\n" % rec['cm_discriminants']
        if rec['factorization'] != []:
            s += "// Shimura curve is a fiber product of the following curves"
            s += "factors := %s\n" % [f.replace("'", "\"") for f in rec['factorization']]
        s += "// Groups containing given group, corresponding to curves covered by given curve\n"
        parents_mag = "%s" % rec['parents']
        parents_mag = parents_mag.replace("'", "\"")
        s += "covers := %s;\n" % parents_mag

        s += "\n// Models for this Shimura curve, if computed\n"
        models = list(db.shimcurve_models.search(
            {"shimcurve": label, "model_type":{"$not":1}},
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

        s += "\n// Maps from this Shimura curve, if computed\n"
        maps = list(db.shimcurve_modelmaps.search(
            {"domain_label": label},
            ["domain_model_type", "codomain_label", "codomain_model_type",
             "coordinates", "leading_coefficients"]))
        codomain_labels = [m["codomain_label"] for m in maps]
        codomain_models = list(db.shimcurve_models.search(
            {"shimcurve": {"$in": codomain_labels}},
            ["equation", "shimcurve", "model_type"]))
        map_id = 0
        if maps and is_P1: #variable t has not been introduced above
            s += "Pol<t> := PolynomialRing(Rationals());\n"

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
                    name += " to the canonical model of Shimura curve"
                elif m["codomain_model_type"] == 1:
                    has_codomain_equation = False
                    name += " to a modular curve isomorphic to P^1"
                elif m["codomain_model_type"] == 2:
                    name += " to the plane model of Shimura curve"
                elif m["codomain_model_type"] == 5:
                    name += " to the Weierstrass model of Shimura curve"
                else:
                    name += " to another model of Shimura curve"
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
                eq = [eq for eq in codomain_models if eq["shimcurve"] == m["codomain_label"] and eq["model_type"] == m["codomain_model_type"]][0]
                s += prefix + "codomain := " + "[%s];\n" % ",".join(eq["equation"])
            map_id += 1
        return s

    def download_shimura_curve_magma(self, label):
        s = self.download_shimura_curve_magma_str(label)
        return self._wrap(s, label, lang="magma")

    def download_shimura_curve_sage(self, label):
        s = self.download_shimura_curve_magma_str(label)
        s = s.replace(":=", "=")
        s = s.replace(";", "")
        s = s.replace("//", "#")
        s = s.replace("K<", "K.<")
        return self._wrap(s, label, lang="sage")

    def download_shimura_curve(self, label, lang):
        if lang == "magma":
            return self.download_shimura_curve_magma(label)
        elif lang == "sage":
            return self.download_shimura_curve_sage(label)
        elif lang == "text":
            data = combined_data(label)
            if data is None:
                return abort(404, "Label not found: %s" % label)
            return self._wrap(Json.dumps(data),
                              label,
                              lang=lang,
                              title='Data for Shimura curve with label %s,'%label)

@shimcurve_page.route("/download_to_magma/<label>")
def shimcurve_magma_download(label):
    return ShimCurve_download().download_shimura_curve(label, lang="magma")

@shimcurve_page.route("/download_to_sage/<label>")
def shimcurve_sage_download(label):
    return ShimCurve_download().download_Shimura_curve(label, lang="sage")

@shimcurve_page.route("/download_to_text/<label>")
def shimcurve_text_download(label):
    return ShimCurve_download().download_shimura_curve(label, lang="text")

@search_wrap(
    table=db.gps_shimura_test,
    title="Shimura curve search results",
    err_title="Shimura curves search input error",
    shortcuts={"jump": shimcurve_jump, "download": ShimCurve_download()},
    columns=shimcurve_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_shimcurve_label,
)
def shimcurve_search(info, query):
    parse_ints(info, query, "level")
    if info.get('level_type'):
        if info['level_type'] == 'prime':
            query['num_bad_primes'] = 1
            query['level_is_squarefree'] = True
        elif info['level_type'] == 'prime_power':
            query['num_bad_primes'] = 1
        elif info['level_type'] == 'squarefree':
            query['level_is_squarefree'] = True
        elif info['level_type'] == 'divides':
            if not isinstance(query.get('level'), int):
                err = "You must specify a single level"
                flash_error(err)
                raise ValueError(err)
            else:
                query['level'] = {'$in': integer_divisors(ZZ(query['level']))}
    parse_family(info, query, "family", qfield="name")
    parse_ints(info, query, "index")
    parse_ints(info, query, "genus")
    parse_ints(info, query, "discB")
    parse_ints(info, query, "discO")
    parse_ints(info, query, "rank")
    parse_ints(info, query, "genus_minus_rank")
    parse_interval(info, query, "q_gonality", quantifier_type=info.get("gonality_type", "exactly"))
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
    parse_element_of(info, query, "covers", qfield="parents", parse_singleton=str)
    parse_element_of(info, query, "factor", qfield="factorization", parse_singleton=str)
    if "covered_by" in info:
        # sort of hacky
        lmfdb_label, label_type = shimcurve_lmfdb_label(info["covered_by"])
        if lmfdb_label is None:
            parents = None
        else:
            if "-" in lmfdb_label:
                # fine label
                rec = db.gps_shimura_test.lookup(lmfdb_label, ["parents", "coarse_label"])
                parents = [rec["coarse_label"]] + rec["parents"]
            else:
                # coarse label
                parents = db.gps_shimura_test.lookup(lmfdb_label, "parents")
        if parents is None:
            msg = "%s not the label of a Shimura curve in the database"
            flash_error(msg, info["covered_by"])
            raise ValueError(msg % info["covered_by"])
        query["label"] = {"$in": parents}


class ShimCurveSearchArray(SearchArray):
    noun = "curve"
    jump_example = "6.1.1.4.0.a.1"
    jump_egspan = "e.g. 6.1.1.4.0.a.1, X(6;1), or X(6,1)"
    jump_prompt = "Label or name"
    jump_knowl = "shimcurve.search_input"

    def __init__(self):
        level_quantifier = SelectBox(
            name="level_type",
            options=[('', ''),
                     ('prime', 'prime'),
                     ('prime_power', 'p-power'),
                     ('squarefree', 'sq-free'),
                     ('divides', 'divides'),
                     ],
            min_width=85)
        level = TextBoxWithSelect(
            name="level",
            knowl="shimcurve.level",
            label="Level",
            example="11",
            example_span="2, 11-23",
            select_box=level_quantifier,
        )
        index = TextBox(
            name="index",
            knowl="shimcurve.index",
            label="Index",
            example="6",
            example_span="6, 12-100",
        )
        genus = TextBox(
            name="genus",
            knowl="shimcurve.genus",
            label="Genus",
            example="1",
            example_span="0, 2-3",
        )
        discB = TextBox(
            name="discB",
            knowl="shimcurve.discb",
            label=r"Discriminant of $B$",
            example="6",
            example_span="6",
        )
        discO = TextBox(
            name="discO",
            knowl="shimcurve.disco",
            label=r"Reduced discriminant of $O$",
            example="6",
            example_span="6",
        )
        rank = TextBox(
            name="rank",
            knowl="shimcurve.rank",
            label="Rank",
            example="1",
            example_span="0, 2-3",
        )
        genus_minus_rank = TextBox(
            name="genus_minus_rank",
            knowl="shimcurve.genus_minus_rank",
            label="Genus-rank difference",
            example="0",
            example_span="0, 1",
        )
        gonality_quantifier = SelectBox(
            name="gonality_type",
            options=[('', 'exactly'),
                     ('possibly', 'possibly'),
                     ('atleast', 'at least'),
                     ('atmost', 'at most'),
                     ],
            min_width=85)
        gonality = TextBoxWithSelect(
            name="q_gonality",
            knowl="shimcurve.gonality",
            label=r"$\Q$-gonality",
            example="2",
            example_span="2, 3-6",
            select_box=gonality_quantifier,
        )
        nu2 = TextBox(
            name="nu2",
            knowl="shimcurve.elliptic_points",
            label="Elliptic points of order 2",
            example="1",
            example_span="1,3-5",
        )
        nu3 = TextBox(
            name="nu3",
            knowl="shimcurve.elliptic_points",
            label="Elliptic points of order 3",
            example="1",
            example_span="1,3-5",
        )
        factor = TextBox(
            name="factor",
            knowl="shimcurve.fiber_product",
            label="Fiber product with",
            example="3.4.0.a.1",
        )
        covers = TextBox(
            name="covers",
            knowl="shimcurve.modular_cover",
            label="Minimally covers",
            example="1.1.0.a.1",
        )
        covered_by = TextBox(
            name="covered_by",
            knowl="shimcurve.modular_cover",
            label="Minimally covered by",
            example="6.12.0.a.1",
        )
        simple = YesNoBox(
            name="simple",
            knowl="shimcurve.simple",
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
                   + [('-%d'%d, 'CM discriminant -%d'%d) for d in [3,4,7,8,11,12,16,19,27,38,43,67,163]])
        cm_discriminants = SelectBox(
            name="cm_discriminants",
            options=cm_opts,
            knowl="shimcurve.cm_discriminants",
            label="CM points",
            example="yes, no, CM discriminant -3"
        )
        contains_negative_one = YesNoBox(
            name="contains_negative_one",
            knowl="shimcurve.contains_negative_one",
            label="Contains $-I$",
            example="yes",
            example_col=True,
            example_span="",
        )
        points_type = SelectBox(
            name="points_type",
            options=[('noncm', 'non-CM'),
                     ('all', 'all'),
                     ],
            min_width=105)
        points = TextBoxWithSelect(
            name="points",
            knowl="shimcurve.known_points",
            label="$j$-points",
            example="0, 3-5",
            select_box=points_type,
        )
        obstructions = SelectBox(
            name="has_obstruction",
            options=[("", ""),
                     ("yes", "Known obstruction"),
                     ("not_yes", "No known obstruction"),
                     ("no", "No obstruction")],
            knowl="shimcurve.local_obstruction",
            label="Obstructions")
        family = SelectBox(
            name="family",
            options=[("", ""),
                     ("XD", "X(D;1)"),
                     ("XDN", "X(D;N)"),
                     ("XDstar", "X^*(D;1)"),
                     ("XDNstar", "X^*(D;N)"),
                     ("any", "any")],
            knowl="shimcurve.standard",
            label="Family",
            example="X(D;N)")

        count = CountBox()

        self.browse_array = [
            [level, index],
            [genus, rank],
            [discB, discO],
            [genus_minus_rank, gonality],
            [nu2, nu3],
            [simple, squarefree],
            [cm_discriminants, factor],
            [covers, covered_by],
            [contains_negative_one, family],
            [points, obstructions],
            [count],
        ]

        self.refine_array = [
            [level, index, genus, discB, discO, rank, genus_minus_rank],
            [gonality, nu2, nu3],
            [simple, squarefree, cm_discriminants, factor, covers],
            [covered_by, contains_negative_one, points, obstructions, family],
        ]

    sorts = [
        ("", "level", ["level", "index", "genus", "label"]),
        ("index", "index", ["index", "level", "genus", "label"]),
        ("genus", "genus", ["genus", "level", "index", "label"]),
        ("rank", "rank", ["rank", "genus", "level", "index", "label"]),
    ]
    null_column_explanations = {
        'simple': False,
        'squarefree': False,
        'rank': False,
        'genus_minus_rank': False,
        'name': False,
    }

@shimcurve_page.route("/Q/low_degree_points")
def low_degree_points():
    info = to_dict(request.args, search_array=RatPointSearchArray())
    return rational_point_search(info)

ratpoint_columns = SearchColumns([
    LinkCol("curve_label", "shimcurve.label", "Label", url_for_shimcurve_label),
    ProcessedCol("curve_name", "shimcurve.standard", "Name", name_to_latex, default=False),
    MathCol("curve_genus", "shimcurve.genus", "Genus"),
    MathCol("degree", "shimcurve.point_degree", "Degree"),
    ProcessedCol("isolated", "shimcurve.isolated_point", "Isolated",
                 lambda x: r"&#x2713;" if x == 4 else (r"" if x in [2,-1,-2,-3,-4] else r"<i>?</i>"), align="center"),
    ProcessedCol("cm_discriminant", "ec.complex_multiplication", "CM", lambda v: "" if v == 0 else v,
                 short_title="CM discriminant", mathmode=True, align="center", orig="cm"),
    LinkCol("Elabel", "shimcurve.elliptic_curve_of_point", "Elliptic curve", lambda Elabel: url_for_ECNF_label(Elabel) if "-" in Elabel else url_for_EC_label(Elabel)),
    ProcessedCol("residue_field", "shimcurve.point_residue_field", "Residue field", lambda field: nf_display_knowl(field, field_pretty(field)), align="center"),
    ProcessedCol("j_field", "ec.j_invariant", r"$\Q(j)$", lambda field: nf_display_knowl(field, field_pretty(field)), align="center", short_title="Q(j)"),
    MultiProcessedCol("jinv", "ec.j_invariant", "$j$-invariant", ["jinv", "j_field", "jorig", "residue_field"], showj_nf, download_col="jinv"),
    FloatCol("j_height", "nf.weil_height", "$j$-height"),
])

def ratpoint_postprocess(res, info, query):
    labels = list({rec["curve_label"] for rec in res})
    return res

@search_wrap(
    table=db.shimcurve_points,
    title="Shimura curve low-degree point search results",
    err_title="Shimura curves low-degree point search input error",
    columns=ratpoint_columns,
    shortcuts={"download": Downloader(db.shimcurve_points)},
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
            knowl="shimcurve.label",
            label="Curve",
            example="11.12.1.1",
        )
        genus = TextBox(
            name="genus",
            knowl="shimcurve.genus",
            label="Genus",
            example="1-3",
        )
        level = TextBox(
            name="level",
            knowl="shimcurve.level",
            label="Level",
            example="37"
        )
        degree = TextBox(
            name="degree",
            knowl="shimcurve.point_degree",
            label="Degree",
            example="2-4",
        )
        residue_field = TextBox(
            name="residue_field",
            knowl="shimcurve.point_residue_field",
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
                   + [('-%d'%d, 'CM discriminant -%d'%d) for d in [3,4,7,8,11,12,16,19,27,38,43,67,163]])
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
            knowl="shimcurve.isolated_point",
        )
        family = SelectBox(
            name="family",
            options=[("", ""),
                     ("XD", "X(D;1)"),
                     ("XDN", "X(D;N)"),
                     ("XDstar", "X^*(D;1)"),
                     ("XDNstar", "X^*(D;N)"),
                     ("any", "any")],
            knowl="shimcurve.standard",
            label="Family",
            example="X(D;1), X(D;N)")
        

        self.refine_array = [[curve, level, genus, degree, cm],
                             [residue_field, j_field, jinv, j_height, isolated],
                             [family]]

    def search_types(self, info):
        # There is no homepage for a point, so we disable the random link
        return [("List", "Search again")]

class ShimCurve_stats(StatsDisplay):
    def __init__(self):
        # !!! For some reason counting the empty query returns 0 ?
        self.ncurves = comma(db.gps_shimura_test.count({'discB' : {'$gt' : 0}}))
        # self.ncurves = comma(db.gps_shimura_test.count())
        self.max_level = db.gps_shimura_test.max("level")

    @property
    def short_summary(self):
        shimcurve_knowl = display_knowl("shimcurve", title="Shimura curves")
        return (
            fr'The database currently contains {self.ncurves} {shimcurve_knowl} of level $N\le {self.max_level}$ parameterizing abelian surfaces $A$ over $\Q$ with potential quaternionic multiplication.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.'
        )

    @property
    def summary(self):
        shimcurve_knowl = display_knowl("shimcurve", title="Shimura curves")
        return (
            fr'The database currently contains {self.ncurves} {shimcurve_knowl} of level $N\le {self.max_level}$ parameterizing abelian surfaces $A/\Q$ with potential quaternionic multiplication.'
        )

    table = db.gps_shimura_test
    baseurl_func = ".index"
    buckets = {'level': ['1-4', '5-8', '9-12', '13-16', '17-20', '21-'],
               'genus': ['0', '1', '2', '3', '4-6', '7-20', '21-100', '101-'],
               }
    knowls = {'level': 'shimcurve.level',
              'genus': 'shimcurve.genus',
              }
    stat_list = [
        {'cols': ['level', 'genus'],
         'proportioner': proportioners.per_row_total,
         'totaler': totaler()},
    ]

@shimcurve_page.route("/Q/stats")
def statistics():
    title = 'Shimura curves: Statistics'
    return render_template("display_stats.html", info=ShimCurve_stats(), title=title, bread=get_bread('Statistics'), learnmore=learnmore_list())

@shimcurve_page.route("/ShimuraCurvePictures")
def scurve_picture_page():
    t = r'Pictures for Shimura curves'
    bread = get_bread("Shimura Curve Picture")
    return render_template(
        "single.html",
        kid='portrait.shimcurve',
        title=t,
        bread=bread,
        learnmore=learnmore_list()
    )

@shimcurve_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for Shimura curve data'
    bread = get_bread('Source')
    return render_template("multi.html",
                           kids=['rcs.source.shimcurve',
                           'rcs.ack.shimcurve',
                           'rcs.cite.shimcurve'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@shimcurve_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of Shimura curve data'
    bread = get_bread('Completeness')
    return render_template("single.html", kid='rcs.cande.shimcurve',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@shimcurve_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of Shimura curve data'
    bread = get_bread('Reliability')
    return render_template("single.html", kid='rcs.rigor.shimcurve',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@shimcurve_page.route("/Labels")
def labels_page():
    t = r'Labels for Shimura curves'
    bread = get_bread('Labels')
    return render_template("single.html", kid='shimcurve.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@shimcurve_page.route("/data/<label>")
def shimcurve_data(label):
    coarse_label = db.gps_shimura_test.lookup(label, "coarse_label")
    bread = get_bread([(label, url_for_shimcurve_label(label)), ("Data", " ")])
    if not LABEL_RE.fullmatch(label):
        return abort(404)
    if label == coarse_label:
        labels = [label]
    else:
        labels = [label, coarse_label]
    tables = ["gps_shimura_test" for lab in labels]
    return datapage(labels, tables, title=f"Shimura curve data - {label}", bread=bread)
