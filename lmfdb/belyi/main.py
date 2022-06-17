# -*- coding: utf-8 -*-
import re

from flask import render_template, url_for, request, redirect, abort

from sage.misc.cachefunc import cached_function
from sage.all import QQ, PolynomialRing, NumberField, sage_eval, CC

from lmfdb.backend.encoding import Json
from lmfdb import db
from lmfdb.utils import (
    to_dict,
    comma,
    flash_error,
    display_knowl,
    parse_ints,
    parse_bracketed_posints,
    parse_nf_string,
    parse_bool,
    redirect_no_cache,
    search_wrap,
    Downloader,
    StatsDisplay,
    SearchArray,
    TextBox,
    SelectBox,
    YesNoBox,
    CountBox,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, SearchCol, MathCol, LinkCol, MultiProcessedCol
from lmfdb.api import datapage
from . import belyi_page
from .web_belyi import (
    WebBelyiGalmap,
    WebBelyiPassport,
)
from .web_belyi import geomtypelet_to_geomtypename_dict as geometry_types_dict
from lmfdb.classical_modular_forms.web_newform import field_display_gen


###############################################################################
# Routing for top level, random, and stats
###############################################################################


def learnmore_list():
    return [
        ("Source and acknowledgments", url_for(".how_computed_page")),
        ("Completeness of the data", url_for(".completeness_page")),
        ("Reliability of the data", url_for(".reliability_page")),
        ("Belyi labels", url_for(".labels_page")),
    ]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def get_bread(tail=None):
    if tail is None:
        tail = []
    base = [("Belyi maps", url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


@belyi_page.route("/")
def index():
    info = to_dict(request.args, search_array=BelyiSearchArray())
    if request.args:
        return belyi_search(info)
    info["stats"] = Belyi_stats()
    info["stats_url"] = url_for(".statistics")
    info["degree_list"] = list(range(1, 10))
    info["title"] = title = "Belyi maps"
    info["bread"] = bread = get_bread()

    return render_template(
        "belyi_browse.html",
        info=info,
        title=title,
        learnmore=learnmore_list(),
        bread=bread,
    )


@belyi_page.route("/random")
@redirect_no_cache
def random_belyi_galmap():
    label = db.belyi_galmaps_fixed.random()
    return url_for_belyi_galmap_label(label)


@belyi_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "belyi",
        db.belyi_galmaps_fixed,
        url_for_label,
        title=r"Some interesting Belyi maps and passports",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )


###############################################################################
# Galmaps, passports, triples and groups routes
###############################################################################

@belyi_page.route("/<group>/<sigma0>/<sigma1>/<sigmaoo>/<letnum>/")
def by_url_belyi_galmap_label(group, sigma0, sigma1, sigmaoo, letnum):
    label = "{}-{}_{}_{}-{}".format(group, sigma0, sigma1, sigmaoo, letnum)
    return render_belyi_galmap_webpage(label)


@belyi_page.route("/<group>/<sigma0>/<sigma1>/<sigmaoo>/<letnum>/<triple>/")
def by_url_embedded_belyi_map_label(group, sigma0, sigma1, sigmaoo, letnum, triple):
    label = "{}-{}_{}_{}-{}".format(group, sigma0, sigma1, sigmaoo, letnum)
    return render_embedded_belyi_map_webpage(label, triple)


@belyi_page.route("/<group>/<sigma0>/<sigma1>/<sigmaoo>/")
def by_url_belyi_passport_label(group, sigma0, sigma1, sigmaoo):
    label = "{}-{}_{}_{}".format(group, sigma0, sigma1, sigmaoo)
    return render_belyi_passport_webpage(label)


@belyi_page.route("/<group>/<abc>")
def by_url_belyi_search_group_triple(group, abc):
    info = to_dict(request.args, search_array=BelyiSearchArray())
    info["title"] = "Belyi maps with group %s and orders %s" % (group, abc)
    info["bread"] = get_bread([
        ("%s" % group, url_for(".by_url_belyi_search_group", group=group)),
        (
            "%s" % abc,
            url_for(".by_url_belyi_search_group_triple", group=group, abc=abc),
        ),
    ])
    if request.args:
        # if group or abc changed, fall back to a general search
        if "group" in request.args and (
            request.args["group"] != str(group) or request.args["abc_list"] != str(abc)
        ):
            return redirect(url_for(".index", **request.args), 307)
        info["title"] += " search results"
        info["bread"].append(("Search results", ""))
    info["group"] = group
    info["abc_list"] = abc
    return belyi_search(info)


@belyi_page.route("/<smthorlabel>")
def by_url_belyi_search_url(smthorlabel):
    split = smthorlabel.split("-")
    # strip out the last field if empty
    if split[-1] == "":
        split = split[:-1]
    if len(split) == 1:
        return by_url_belyi_search_group(group=split[0])
    elif len(split) == 2:  # passport
        sigma_spl = (split[1]).split('_')
        return redirect(
            url_for(
                ".by_url_belyi_passport_label",
                group=split[0],
                sigma0=sigma_spl[0],
                sigma1=sigma_spl[1],
                sigmaoo=sigma_spl[2],
            ),
            301,
        )
    elif len(split) == 3:  # galmap
        sigma_spl = (split[1]).split('_')
        return redirect(
            url_for(
                ".by_url_belyi_galmap_label",
                group=split[0],
                abc=split[1],
                sigma0=sigma_spl[0],
                sigma1=sigma_spl[1],
                sigmaoo=sigma_spl[2],
                letnum=split[2],
            ),
            301,
        )
    else:
        # It could be an old label
        flash_error("%s is not a valid label for a Belyi map", smthorlabel)
        return redirect(url_for(".index"))


@belyi_page.route("/<group>")
def by_url_belyi_search_group(group):
    info = to_dict(request.args, search_array=BelyiSearchArray())
    info["title"] = "Belyi maps with group %s" % group
    info["bread"] = get_bread([
        ("%s" % group, url_for(".by_url_belyi_search_group", group=group)),
    ])
    if request.args:
        # if the group changed, fall back to a general search
        if "group" in request.args and request.args["group"] != str(group):
            return redirect(url_for(".index", **request.args), 307)
        info["title"] += " search results"
        info["bread"].append(("Search results", ""))
    info["group"] = group
    return belyi_search(info)


def render_belyi_galmap_webpage(label):
    try:
        belyi_galmap = WebBelyiGalmap.by_label(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "belyi_galmap.html",
        properties=belyi_galmap.properties,
        info={},
        data=belyi_galmap.data,
        code=belyi_galmap.code,
        bread=belyi_galmap.bread,
        learnmore=learnmore_list(),
        title=belyi_galmap.title,
        downloads=belyi_galmap.downloads,
        friends=belyi_galmap.friends,
        KNOWL_ID="belyi.%s" % label,
    )


def render_embedded_belyi_map_webpage(label, triple):
    try:
        belyi_galmap = WebBelyiGalmap.by_label(label, triple=triple)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "embedded_belyi_map.html",
        properties=belyi_galmap.properties,
        info={},
        data=belyi_galmap.data,
        code=belyi_galmap.code,
        bread=belyi_galmap.bread,
        learnmore=learnmore_list(),
        title=belyi_galmap.title,
        downloads=belyi_galmap.downloads,
        friends=belyi_galmap.friends,
        KNOWL_ID="belyi.%s" % label,
    )


def render_belyi_passport_webpage(label):
    try:
        belyi_passport = WebBelyiPassport.by_label(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "belyi_passport.html",
        properties=belyi_passport.properties,
        data=belyi_passport.data,
        bread=belyi_passport.bread,
        learnmore=learnmore_list(),
        title=belyi_passport.title,
        friends=belyi_passport.friends,
        KNOWL_ID="belyi.%s" % label,
    )


def url_for_belyi_galmap_label(label):
    slabel = label.split("-")
    sigma_spl = slabel[1].split("_")
    return url_for(
        ".by_url_belyi_galmap_label",
        group=slabel[0],
        sigma0=sigma_spl[0],
        sigma1=sigma_spl[1],
        sigmaoo=sigma_spl[2],
        letnum=slabel[2]
    )


def url_for_belyi_passport_label(label):
    slabel = label.split("-")
    sigma_spl = slabel[1].split("_")
    return url_for(
        ".by_url_belyi_passport_label",
        group=slabel[0],
        sigma0=sigma_spl[0],
        sigma1=sigma_spl[1],
        sigmaoo=sigma_spl[2]
    )


def belyi_passport_from_belyi_galmap_label(label):
    return "-".join(label.split("-")[:-1])


# either a passport label or a galmap label
# TODO: update for new labels
# Note: this function is not currently used anywhere
@cached_function
def split_label(label):
    """
    >>> split_label("7T6-7_4.2.1_4.2.1-a")
    "7T6", [[7],[4,2,1],[4,2,1]], "a"
    >>> split_label("7T6-7_4.2.1_4.2.1")
    "7T6", [[7],[4,2,1],[4,2,1]], None
    """
    splitlabel = label.split("-")
    group = splitlabel[0]
    sigma_spl = (splitlabel[1]).split('_')
    ls = []
    for el in sigma_spl:
        l_i_str = el.split(".")
        l_i = [int(c) for c in l_i_str]
        ls.append(l_i)
    if len(splitlabel) == 2:  # passports
        gal = None
    elif len(splitlabel) == 3:  # galmap
        gal = splitlabel[-1]
    else:
        raise ValueError("the label must have 1 or 2 dashes")
    return group, ls, gal


def belyi_group_from_label(label):
    return split_label(label)[0]


def belyi_degree_from_label(label):
    return int(split_label(label)[0].split("T")[0])


def belyi_lambdas_from_label(label):
    return split_label(label)[1]


def belyi_orbit_from_label(label):
    return split_label(label)[-1]


################################################################################
# Searching
################################################################################

GALMAP_RE = re.compile(r"^\d+T\d+-(\d+\.)*\d+_(\d+\.)*\d+_(\d+\.)*\d+-[a-z]+$")
PASSPORT_RE = re.compile(r"^\d+T\d+-(\d+\.)*\d+_(\d+\.)*\d+_(\d+\.)*\d+$")


def belyi_jump(info):
    jump = info["jump"].strip()
    if re.match(GALMAP_RE, jump):
        # 7T6-7_4.2.1_4.2.1-b
        return redirect(url_for_belyi_galmap_label(jump), 301)
    if re.match(PASSPORT_RE, jump):
        # 7T6-7_4.2.1_4.2.1
        return redirect(url_for_belyi_passport_label(jump), 301)
    flash_error("%s is not a valid Belyi map or passport label", jump)
    return redirect(url_for(".index"))


def curve_string_parser(rec):
    if rec['g'] == 0:
        return None
    else:
        curve_str = rec["curve"]
        curve_str = curve_str.replace("^", "**")
        K = make_base_field(rec)
        nu = K.gens()[0]
        S0 = PolynomialRing(K, "x")
        x = S0.gens()[0]
        S = PolynomialRing(S0, "y")
        y = S.gens()[0]
        parts = curve_str.split("=")
        lhs_poly = sage_eval(parts[0], locals={"x": x, "y": y, "nu": nu})
        lhs_cs = lhs_poly.coefficients()
        if len(lhs_cs) == 1:
            h = S0(0)
        elif len(lhs_cs) == 2:  # if there is a cross-term
            h = lhs_poly.coefficients()[0]
        else:
            raise NotImplementedError("for genus > 2")
        # rhs_poly = sage_eval(parts[1], locals = {'x':x, 'y':y, 'nu':nu})
        f = sage_eval(parts[1], locals={"x": x, "y": y, "nu": nu})
        return f, h


def hyperelliptic_polys_to_ainvs(f, h):
    R = f.parent()
    K = R.base_ring()
    f_cs = f.coefficients(sparse=False)
    h_cs = h.coefficients(sparse=False)
    while len(h_cs) < 2:  # pad coefficients of h with 0s to get length 2
        h_cs += [0]
    a3 = h_cs[0]
    a1 = h_cs[1]
    a6 = f_cs[0]
    a4 = f_cs[1]
    a2 = f_cs[2]
    return [K(a1), K(a2), K(a3), K(a4), K(a6)]


def make_base_field(rec):
    if rec["base_field"] == [-1, 1]:
        K = QQ  # is there a Sage version of RationalsAsNumberField()?
    else:
        R = PolynomialRing(QQ, "T")
        poly = R(rec["base_field"])
        K = NumberField(poly, "nu")
    return K


class Belyi_download(Downloader):
    table = db.belyi_galmaps_fixed
    title = "Belyi maps"
    columns = "triples"
    data_format = ["permutation_triples"]
    data_description = ["where the permutation triples are in one line notation"]
    function_body = {
        "magma": [
            "deg := #(data[1][1][1]);",
            "return [[[Sym(deg) ! t: t in s]: s in triples]: triples in data];",
        ],
        "sage": [
            "deg = len(data[0][0][0])",
            "return [[map(SymmetricGroup(deg), s) for s in triples] for triples in data]",
        ],
    }

    # could use static method instead of adding self
    def make_base_field_string(self, rec, lang):
        s = ""
        if lang == "magma":
            if rec["base_field"] == [-1, 1]:
                s += "K<nu> := RationalsAsNumberField();\n"
            else:
                s += (
                    "R<T> := PolynomialRing(Rationals());\nK<nu> := NumberField(R!%s);\n\n"
                    % rec["base_field"]
                )
        elif lang == "sage":
            if rec["base_field"] == [-1, 1]:
                s += "K = QQ\n"  # is there a Sage version of RationalsAsNumberField()?
            else:
                s += (
                    "R.<T> = PolynomialRing(QQ)\nK.<nu> = NumberField(R(%s))\n\n"
                    % rec["base_field"]
                )
        else:
            raise NotImplementedError("for genus > 2")
        return s

    def perm_maker(self, rec, lang):
        d = rec["deg"]
        perms = []
        triples = rec["triples"]
        if lang == "magma":
            for triple in triples:
                pref = "[Sym(%s) | " % d
                s_trip = "%s" % triple
                s_trip = pref + s_trip[1:]
                perms.append(s_trip)
            return "[%s]" % ", ".join(perms)
        if lang == "sage":
            triples_new = []
            for triple in triples:
                triple_new = []
                for perm in triple:
                    perm_str = "Permutation(%s)" % perm
                    triple_new.append(perm_str)
                triple_str = "[%s]" % ", ".join(triple_new)
                triples_new.append(triple_str)
            return "[%s]" % ", ".join(triples_new)

    def embedding_maker(self, rec, lang):
        emb_list = []
        embeddings = rec["embeddings"]
        if lang == "magma":
            for z in embeddings:
                z_str = "ComplexField(15)!%s" % z
                emb_list.append(z_str)
            return "[%s]" % ", ".join(emb_list)
        if lang == "sage":
            return "%s" % [CC(z) for z in embeddings]

    def download_galmap_magma(self, label, lang="magma"):
        s = ""
        rec = db.belyi_galmaps_fixed.lookup(label)
        if rec is None:
            return abort(404, "Label not found: %s" % label)
        s += "// Magma code for Belyi map with label %s\n\n" % label
        s += "\n// Group theoretic data\n\n"
        s += "d := %s;\n" % rec["deg"]
        s += "i := %s;\n" % int(label.split("T")[1][0])
        s += "G := TransitiveGroup(d,i);\n"
        s += "sigmas := %s;\n" % self.perm_maker(rec, lang)
        s += "embeddings := %s;\n" % self.embedding_maker(rec, lang)
        s += "\n// Geometric data\n\n"
        s += "// Define the base field\n"
        s += self.make_base_field_string(rec, lang)
        s += "// Define the curve\n"
        if rec["g"] == 0:
            s += "X := Curve(ProjectiveSpace(PolynomialRing(K, 2)));\n"
            s += "// Define the map\n"
            s += "KX<x> := FunctionField(X);\n"
            s += "phi := %s;" % rec["map"]
        elif rec["g"] == 1:
            s += "S<x> := PolynomialRing(K);\n"
            # curve_poly = rec['curve'].split("=")[1]
            # s += "X := EllipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
            curve_polys = curve_string_parser(rec)
            s += "X := EllipticCurve(S!%s,S!%s);\n" % (curve_polys[0], curve_polys[1])
            s += "// Define the map\n"
            s += "KX<x,y> := FunctionField(X);\n"
            s += "phi := %s;" % rec["map"]
        elif rec["g"] == 2:
            s += "S<x> := PolynomialRing(K);\n"
            # curve_poly = rec['curve'].split("=")[1]
            # s += "X := HyperellipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
            curve_polys = curve_string_parser(rec)
            s += "X := HyperellipticCurve(S!%s,S!%s);\n" % (curve_polys[0], curve_polys[1])
            s += "// Define the map\n"
            s += "KX<x,y> := FunctionField(X);\n"
            s += "phi := %s;" % rec["map"]
        else:
            raise NotImplementedError("for genus > 2")
        return self._wrap(s, label, lang=lang)

    def download_galmap_sage(self, label, lang="sage"):
        s = ""
        rec = db.belyi_galmaps_fixed.lookup(label)
        if rec is None:
            return abort(404, "Label not found: %s" % label)
        s += "# Sage code for Belyi map with label %s\n\n" % label
        s += "\n# Group theoretic data\n\n"
        s += "d = %s\n" % rec["deg"]
        s += "i = %s\n" % int(label.split("T")[1][0])
        s += "G = TransitiveGroup(d,i)\n"
        s += "sigmas = %s\n" % self.perm_maker(rec, lang)
        s += "embeddings = %s\n" % self.embedding_maker(rec, lang)
        s += "\n# Geometric data\n\n"
        s += "# Define the base field\n"
        s += self.make_base_field_string(rec, lang)
        s += "# Define the curve\n"
        if rec["g"] == 0:
            s += "X = ProjectiveSpace(1,K)\n"
            s += "# Define the map\n"
            s += "K.<x> = FunctionField(K)\n"
            s += "phi = %s" % rec["map"]
        elif rec["g"] == 1:
            s += "S.<x> = PolynomialRing(K)\n"
            f, h = curve_string_parser(rec)
            ainvs = hyperelliptic_polys_to_ainvs(f, h)
            s += "X = EllipticCurve(%s)\n" % ainvs
            s += "# Define the map\n"
            s += "K0.<x> = FunctionField(K)\n"
            crv_str = rec['curve']
            crv_strs = crv_str.split("=")
            crv_str = crv_strs[0] + '-(' + crv_strs[1] + ')'
            s += "R.<y> = PolynomialRing(K0)\n"
            s += "KX.<y> = K0.extension(%s)\n" % crv_str
            s += "phi = %s" % rec["map"]
        elif rec["g"] == 2:
            s += "S.<x> = PolynomialRing(K)\n"
            curve_polys = curve_string_parser(rec)
            s += "X = HyperellipticCurve(S(%s),S(%s))\n" % (curve_polys[0], curve_polys[1])
            s += "# Define the map\n"
            s += "K0.<x> = FunctionField(K)\n"
            crv_str = rec['curve']
            crv_strs = crv_str.split("=")
            crv_str = crv_strs[0] + '-(' + crv_strs[1] + ')'
            s += "R.<y> = PolynomialRing(K0)\n"
            s += "KX.<y> = K0.extension(%s)\n" % crv_str
            s += "phi = %s" % rec["map"]
        else:
            raise NotImplementedError("for genus > 2")
        return self._wrap(s, label, lang=lang)

    def download_galmap_text(self, label, lang="text"):
        data = db.belyi_galmaps_fixed.lookup(label)
        if data is None:
            return abort(404, f"Label not found: {label}")
        return self._wrap(Json.dumps(data),
            label, title=f'Data for embedded Belyi map with label {label},')


@belyi_page.route("/download_galmap_to_magma/<label>")
def belyi_galmap_magma_download(label):
    return Belyi_download().download_galmap_magma(label)


@belyi_page.route("/download_galmap_to_sage/<label>")
def belyi_galmap_sage_download(label):
    return Belyi_download().download_galmap_sage(label)


@belyi_page.route("/download_galmap_to_text/<label>")
def belyi_galmap_text_download(label):
    return Belyi_download().download_galmap_text(label)


@belyi_page.route("/data/<label>")
def belyi_data(label):
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    if label.count("-") == 1:  # passport label length
        labels = [label, label]
        label_cols = ["plabel", "plabel"]
        tables = ["belyi_passports_fixed", "belyi_galmaps_fixed"]
    elif label.count("-") == 2:  # galmap label length
        labels = [label, "-".join(label.split("-")[:-1]), label]
        label_cols = ["label", "plabel", "label"]
        tables = ["belyi_galmaps_fixed", "belyi_passports_fixed", "belyi_galmap_portraits"]
    else:
        return abort(404, f"Invalid label {label}")
    return datapage(labels, tables, title=f"Belyi map data - {label}", bread=bread, label_cols=label_cols)


def url_for_label(label):
    return url_for(".by_url_belyi_search_url", smthorlabel=label)


belyi_columns = SearchColumns([
    LinkCol("label", "belyi.label", "Label", url_for_belyi_galmap_label, default=True),
    MathCol("deg", "belyi.degree", "Degree", default=True),
    SearchCol("group", "belyi.group", "Group", default=True),
    MathCol("abc", "belyi.abc", "abc", default=True, align="left", short_title="abc triple"),
    MathCol("lambdas", "belyi.ramification_type", "Ramification type", default=True, align="left"),
    MathCol("g", "belyi.genus", "Genus", default=True),
    MathCol("orbit_size", "belyi.orbit_size", "Orbit Size", default=True),
    MultiProcessedCol("field", "belyi.base_field", "Base field", ["base_field_label", "base_field"], lambda label, disp: field_display_gen(label, disp, truncate=16), default=True)])


@search_wrap(
    table=db.belyi_galmaps_fixed,
    title="Belyi map search results",
    err_title="Belyi map search input error",
    columns=belyi_columns,
    shortcuts={"jump": belyi_jump, "download": Belyi_download()},
    url_for_label=url_for_label,
    bread=lambda: get_bread("Search results"),
    learnmore=learnmore_list,
)
def belyi_search(info, query):
    if "group" in query:
        info["group"] = query["group"]
    parse_bracketed_posints(info, query, "abc_list", "a, b, c", maxlength=3)
    if query.get("abc_list"):
        if len(query["abc_list"]) == 3:
            a, b, c = sorted(query["abc_list"])
            query["a_s"] = a
            query["b_s"] = b
            query["c_s"] = c
        elif len(query["abc_list"]) == 2:
            a, b = sorted(query["abc_list"])
            sub_query = []
            sub_query.append({"a_s": a, "b_s": b})
            sub_query.append({"b_s": a, "c_s": b})
            query["$or"] = sub_query
        elif len(query["abc_list"]) == 1:
            a = query["abc_list"][0]
            query["$or"] = [{"a_s": a}, {"b_s": a}, {"c_s": a}]
        query.pop("abc_list")

    # a naive hack
    if info.get("abc"):
        for elt in ["a_s", "b_s", "c_s"]:
            info_hack = {}
            info_hack[elt] = info["abc"]
            parse_ints(info_hack, query, elt)

    parse_ints(info, query, "g", "g")
    parse_ints(info, query, "deg", "deg")
    parse_ints(info, query, "orbit_size", "orbit_size")
    parse_ints(info, query, "pass_size", "pass_size")
    parse_nf_string(info, query, 'field', name="base number field",
                    qfield='base_field_label')
    # invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
    for fld in ["geomtype", "group"]:
        if info.get(fld):
            query[fld] = info[fld]

    parse_bool(info, query, "is_primitive", name="is_primitive")
    if info.get("primitivization"):
        primitivization = info["primitivization"]
        if re.match(GALMAP_RE, primitivization):
            # 7T6-7_4.2.1_4.2.1-b
            query["primitivization"] = primitivization
        else:
            raise ValueError("%s is not a valid Belyi map label" % primitivization)


################################################################################
# Statistics
################################################################################


class Belyi_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for Belyi maps
    """

    def __init__(self):
        self.ngalmaps = comma(db.belyi_galmaps_fixed.stats.count())
        self.npassports = comma(db.belyi_passports_fixed.stats.count())
        self.max_deg = comma(db.belyi_passports_fixed.max("deg"))
        self.deg_knowl = display_knowl("belyi.degree", title="degree")
        self.belyi_knowl = '<a title="Belyi maps (up to Galois conjugation) [belyi.galmap]" knowl="belyi.galmap" kwargs="">Belyi maps</a>'

    table = db.belyi_galmaps_fixed
    baseurl_func = ".index"
    short_display = {"deg": "degree", "orbit_size": "size", "g": "genus"}
    top_titles = {"orbit_size": "Galois orbit size"}
    knowls = {
        "deg": "belyi.degree",
        "orbit_size": "belyi.orbit_size",
        "g": "belyi.genus",
    }
    stat_list = [
        {"cols": col, "totaler": {"avg": True}} for col in ["deg", "orbit_size", "g"]
    ]
    stat_list += [
        {"cols": "pass_size",
         "table": db.belyi_passports_fixed,
         "top_title": [("passport sizes", "belyi.pass_size")],
         "totaler": {"avg": True}},
        {"cols": "num_orbits",
         "table": db.belyi_passports_fixed,
         "top_title": [("number of Galois orbits", "belyi.num_orbits"), ("per", None), ("passport", "belyi.passport")],
         "totaler": {"avg": True}}
    ]

    @property
    def short_summary(self):
        return ('The database currently contains %s %s of %s up to %s.  Here are some <a href="%s">further statistics</a>.'
                % (self.ngalmaps, self.belyi_knowl, self.deg_knowl, self.max_deg, url_for(".statistics")))

    @property
    def summary(self):
        return ("The database currently contains %s Galois orbits of Belyi maps in %s passports, with %s at most %s."
                % (self.ngalmaps, self.npassports, self.deg_knowl, self.max_deg))


@belyi_page.route("/stats")
def statistics():
    title = "Belyi maps: statistics"
    bread = get_bread("Statistics")
    return render_template(
        "display_stats.html",
        info=Belyi_stats(),
        title=title,
        bread=bread,
        learnmore=learnmore_list(),
    )


@belyi_page.route("/Source")
def how_computed_page():
    t = "Source and acknowledgments for Belyi map data"
    bread = get_bread("Source")
    return render_template(
        "multi.html",
        kids=["rcs.source.belyi",
              "rcs.ack.belyi",
              "rcs.cite.belyi"],
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )


@belyi_page.route("/Completeness")
def completeness_page():
    t = "Completeness of Belyi map data"
    bread = get_bread("Completeness")
    return render_template(
        "single.html",
        kid="rcs.cande.belyi",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )


@belyi_page.route("/Reliability")
def reliability_page():
    t = "Reliability of Belyi map data"
    bread = get_bread("Source")
    return render_template(
        "single.html",
        kid="rcs.rigor.belyi",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Reliability"),
    )


@belyi_page.route("/Labels")
def labels_page():
    t = "Labels for Belyi maps"
    bread = get_bread("Labels")
    return render_template(
        "single.html",
        kid="belyi.label",
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("labels"),
    )


class BelyiSearchArray(SearchArray):
    noun = "map"
    plural_noun = "maps"
    sorts = [("", "degree", ['deg', 'group_num', 'g', 'label']),
             ("g", "genus", ['g', 'deg', 'group_num', 'label']),
             # ("field", "base field", ['base_field_label', 'deg', 'group_num', 'g', 'label']),
             ("orbit_size", "orbit size", ['orbit_size', 'deg', 'group_num', 'g', 'label'])]
    jump_example = "4T5-4_4_3.1-a"
    jump_egspan = "e.g. 4T5-4_4_3.1-a"
    jump_knowl = "belyi.search_input"
    jump_label = "Label"

    def __init__(self):
        deg = TextBox(
            name="deg",
            label="Degree",
            knowl="belyi.degree",
            example="5",
            example_span="4, 5-6")
        group = TextBox(
            name="group",
            label="Group",
            knowl="belyi.group",
            example="4T5")
        abc = TextBox(
            name="abc",
            label="Orders",
            knowl="belyi.orders",
            example="5",
            example_span="4, 5-6")
        abc_list = TextBox(
            name="abc_list",
            label=r"\([a,b,c]\) triple",
            knowl="belyi.abc",
            example="[4,4,3]")
        g = TextBox(
            name="g",
            label="Genus",
            knowl="belyi.genus",
            example="1",
            example_span="1, 0-2")
        pass_size = TextBox(
            name="pass_size",
            label="Passport size",
            knowl="belyi.pass_size",
            example="2",
            example_span="2, 5-6")
        orbit_size = TextBox(
            name="orbit_size",
            label="Orbit size",
            knowl="belyi.orbit_size",
            example="2",
            example_span="2, 5-6")
        geomtype = SelectBox(
            name="geomtype",
            label="Geometry type",
            knowl="belyi.geometry_type",
            options=[("", "")] + list(geometry_types_dict.items()))
        is_primitive = YesNoBox(
            name="is_primitive",
            label="Primitive",
            knowl="belyi.primitive",
            example="yes")
        primitivization = TextBox(
            name="primitivization",
            label="Primitivization",
            knowl="belyi.primitivization",
            example="2T1-2_2_1.1-a",
            example_span="2T1-2_2_1.1-a")
        field = TextBox(
            name="field",
            label="Base field",
            knowl="belyi.base_field",
            example="2.2.5.1",
            example_span="2.2.5.1 or Qsqrt5")
        count = CountBox()

        self.browse_array = [[deg], [group], [abc], [abc_list], [g], [orbit_size], [pass_size], [field], [geomtype], [is_primitive], [primitivization], [count]]

        self.refine_array = [[deg, group, abc, abc_list], [g, orbit_size, pass_size, field], [geomtype, is_primitive, primitivization]]
