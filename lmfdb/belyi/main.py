# -*- coding: utf-8 -*-
from __future__ import absolute_import

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
    search_wrap,
    Downloader,
    StatsDisplay,
    SearchArray,
    TextBox,
    SelectBox,
    CountBox,
)
from . import belyi_page
from .web_belyi import (
    WebBelyiGalmap,
    WebBelyiPassport,
)
from .web_belyi import geomtypelet_to_geomtypename_dict as geometry_types_dict
from scripts.belyi.new_labels import add_dot_seps

credit_string = "Michael Musty, Sam Schiavone, and John Voight"

###############################################################################
# List and dictionaries needed routing and searching
###############################################################################


geometry_types_list = list(geometry_types_dict)


###############################################################################
# Routing for top level, random, and stats
###############################################################################


def learnmore_list():
    return [
        ("Completeness of the data", url_for(".completeness_page")),
        ("Source of the data", url_for(".how_computed_page")),
        ("Belyi labels", url_for(".labels_page")),
    ]


# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


@belyi_page.route("/")
def index():
    info = to_dict(request.args, search_array=BelyiSearchArray())
    if request.args:
        return belyi_search(info)
    info["stats"] = Belyi_stats()
    info["stats_url"] = url_for(".statistics")
    info["belyi_galmap_url"] = lambda label: url_for_belyi_galmap_label(label)
    belyi_galmap_labels = (
        #"7T6-[7,4,4]-7-421-421-g1-b",
        #"7T7-[7,12,12]-7-43-43-g2-d",
        #"7T5-[7,7,3]-7-7-331-g2-a",
        #"6T15-[5,5,5]-51-51-51-g1-a",
        #"7T7-[6,6,6]-61-61-322-g1-a",
        "7T6-7_4.2.1_4.2.1-b",
        "7T7-7_4.3_4.3-d",
        "7T5-7_7_3.3.1-a",
        "6T15-5.1_5.1_5.1-a",
        "7T7-6.1_6.1_3.2.2-a",
    )
    info["belyi_galmap_list"] = [
        {"label": label, "url": url_for_belyi_galmap_label(label)}
        for label in belyi_galmap_labels
    ]
    info["degree_list"] = ("1-6", "7-8", "9-10", "10-100")
    info["title"] = title = "Belyi maps"
    info["bread"] = bread = [("Belyi Maps", url_for(".index"))]

    # search options
    info["geometry_types_list"] = geometry_types_list
    info["geometry_types_dict"] = geometry_types_dict

    return render_template(
        "belyi_browse.html",
        info=info,
        credit=credit_string,
        title=title,
        learnmore=learnmore_list(),
        bread=bread,
    )


@belyi_page.route("/random")
def random_belyi_galmap():
    label = db.belyi_galmaps_test.random()
    return redirect(url_for_belyi_galmap_label(label), 307)


###############################################################################
# Galmaps, passports, triples and groups routes
###############################################################################

#@belyi_page.route("/<group>/<abc>/<sigma0>/<sigma1>/<sigmaoo>/<g>/<letnum>")
@belyi_page.route("/<group>/<sigma0>/<sigma1>/<sigmaoo>/<letnum>")
def by_url_belyi_galmap_label(group, sigma0, sigma1, sigmaoo, letnum):
    #label = ( group + "-" + abc + "-" + sigma0 + "-" + sigma1 + "-" + sigmaoo + "-" + g + "-" + letnum)
    label = "{}-{}_{}_{}-{}".format(group,sigma0,sigma1,sigmaoo,letnum)
    return render_belyi_galmap_webpage(label)

#@belyi_page.route("/<group>/<abc>/<sigma0>/<sigma1>/<sigmaoo>/<g>")
@belyi_page.route("/<group>/<sigma0>/<sigma1>/<sigmaoo>/")
def by_url_belyi_passport_label(group, sigma0, sigma1, sigmaoo):
    #label = group + "-" + abc + "-" + sigma0 + "-" + sigma1 + "-" + sigmaoo + "-" + g
    label = "{}-{}_{}_{}".format(group,sigma0,sigma1,sigmaoo)
    return render_belyi_passport_webpage(label)


@belyi_page.route("/<group>/<abc>")
def by_url_belyi_search_group_triple(group, abc):
    info = to_dict(request.args, search_array=BelyiSearchArray())
    info["title"] = "Belyi maps with group %s and orders %s" % (group, abc)
    info["bread"] = [
        ("Belyi Maps", url_for(".index")),
        ("%s" % group, url_for(".by_url_belyi_search_group", group=group)),
        (
            "%s" % abc,
            url_for(".by_url_belyi_search_group_triple", group=group, abc=abc),
        ),
    ]
    if request.args:
        # if group or abc changed, fall back to a general search
        if "group" in request.args and (
            request.args["group"] != str(group) or request.args["abc_list"] != str(abc)
        ):
            return redirect(url_for(".index", **request.args), 307)
        info["title"] += " search results"
        info["bread"].append(("search results", ""))
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
    elif len(split) == 2: # passport
        sigma_spl = (split[1]).split('_')
        return redirect(
            url_for(
                ".by_url_belyi_passport_label",
                group=split[0],
                sigma0=sigmaspl[0],
                sigma1=sigmaspl[1],
                sigmaoo=sigmaspl[2],
            ),
            301,
        )
    elif len(split) == 3: # galmap
        sigma_spl = (split[1]).split('_')
        return redirect(
            url_for(
                ".by_url_belyi_galmap_label",
                group=split[0],
                abc=split[1],
                sigma0=sigmaspl[0],
                sigma1=sigmaspl[1],
                sigmaoo=sigmaspl[2],
                letnum=split[2],
            ),
            301,
        )


@belyi_page.route("/<group>")
def by_url_belyi_search_group(group):
    info = to_dict(request.args, search_array=BelyiSearchArray())
    info["title"] = "Belyi maps with group %s" % group
    info["bread"] = [
        ("Belyi Maps", url_for(".index")),
        ("%s" % group, url_for(".by_url_belyi_search_group", group=group)),
    ]
    if request.args:
        # if the group changed, fall back to a general search
        if "group" in request.args and request.args["group"] != str(group):
            return redirect(url_for(".index", **request.args), 307)
        info["title"] += " search results"
        info["bread"].append(("search results", ""))
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
        credit=credit_string,
        info={},
        data=belyi_galmap.data,
        code=belyi_galmap.code,
        #TODO: fix this
        #bread=belyi_galmap.bread,
        bread=[],
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
        credit=credit_string,
        data=belyi_passport.data,
        #TODO: fix this
        #bread=belyi_passport.bread,
        bread=[],
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
# is this even used anywhere?
@cached_function
def break_label(label):
    """
    >>> break_label("4T5-[4,4,3]-4-4-31-g1-a")
    "4T5", [4,4,3], [[4],[4],[3,1]], 1, "a"
    >>> break_label("4T5-[4,4,3]-4-4-31-g1")
    "4T5", [4,4,3], [[4],[4],[3,1]], 1, None
    >>> break_label("12T5-[4,4,3]-10,4-11,1-31-g1")
    "12T5", [4,4,3], [[10,4],[11,1],[3,1]], 1, None
    """
    splitlabel = label.split("-")
    sigma_spl = (splitlabel[1]).split('_')
    if len(splitlabel) == 2: # passports
        group, abc, l0, l1, l2, genus = splitlabel
        gal = None
    elif len(splitlabel) == 3: # galmap
        group, abc, l0, l1, l2, genus, gal = splitlabel
    else:
        raise ValueError("the label must have 5 or 6 dashes")

    abc = [int(z) for z in abc[1:-1].split(",")]
    lambdas = [l0, l1, l2]
    for i, elt in lambdas:
        if "," in elt:
            elt = [int(t) for t in elt.split(",")]
        else:
            elt = [int(t) for t in list(elt)]
    genus = int(genus[1:])
    return group, lambdas, genus, gal


def belyi_group_from_label(label):
    return break_label(label)[0]


def belyi_degree_from_label(label):
    return int(break_label(label)[0].split("T")[0])


def belyi_abc_from_label(label):
    return break_label(label)[1]


def belyi_lambdas_from_label(label):
    return break_label(label)[2]


def belyi_genus_from_label(label):
    return break_label(label)[3]


def belyi_orbit_from_label(label):
    return break_label(label)[-1]


################################################################################
# Searching
################################################################################


def belyi_jump(info):
    jump = info["jump"].strip()
    #TODO: these regexes need to be updated for new labels
    #if re.match(r"^\d+T\d+-\[\d+,\d+,\d+\]-\d+-\d+-\d+-g\d+-[a-z]+$", jump):
    if re.match(r"^\d+T\d+-\d+_\d+_\d+-[a-z]+$", jump):
        return redirect(url_for_belyi_galmap_label(jump), 301)
    else:
    #TODO: these regexes need to be updated for new labels
        #if re.match(r"^\d+T\d+-\[\d+,\d+,\d+\]-\d+-\d+-\d+-g\d+$", jump):
        if re.match(r"^\d+T\d+-\d+_\d+_\d$", jump):
            return redirect(url_for_belyi_passport_label(jump), 301)
        else:
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

def hyperelliptic_polys_to_ainvs(f,h):
    R = f.parent()
    K = R.base_ring()
    f_cs = f.coefficients(sparse = False)
    h_cs = h.coefficients(sparse = False)
    while len(h_cs) < 2: # pad coefficients of h with 0s to get length 2
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
    table = db.belyi_galmaps_test
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
        rec = db.belyi_galmaps_test.lookup(label)
        s += "// Magma code for Belyi map with label %s\n\n" % label
        s += "\n// Group theoretic data\n\n"
        s += "d := %s;\n" % rec["deg"]
        s += "i := %s;\n" % int(label.split("T")[1][0])
        s += "G := TransitiveGroup(d,i);\n"
        s += "sigmas := %s;\n" % self.perm_maker(rec,lang)
        s += "embeddings := %s;\n" % self.embedding_maker(rec, lang)
        s += "\n// Geometric data\n\n"
        s += "// Define the base field\n"
        s += self.make_base_field_string(rec,lang)
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
        rec = db.belyi_galmaps_test.lookup(label)
        s += "# Sage code for Belyi map with label %s\n\n" % label
        s += "\n# Group theoretic data\n\n"
        s += "d = %s\n" % rec["deg"]
        s += "i = %s\n" % int(label.split("T")[1][0])
        s += "G = TransitiveGroup(d,i)\n"
        s += "sigmas = %s\n" % self.perm_maker(rec,lang)
        s += "embeddings = %s\n" % self.embedding_maker(rec,lang)
        s += "\n# Geometric data\n\n"
        s += "# Define the base field\n"
        s += self.make_base_field_string(rec,lang)
        s += "# Define the curve\n"
        if rec["g"] == 0:
            s += "X = ProjectiveSpace(1,K)\n"
            s += "# Define the map\n"
            s += "K.<x> = FunctionField(K)\n"
            s += "phi = %s" % rec["map"]
        elif rec["g"] == 1:
            s += "S.<x> = PolynomialRing(K)\n"
            f, h = curve_string_parser(rec)
            ainvs = hyperelliptic_polys_to_ainvs(f,h)
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
        data = db.belyi_galmaps_test.lookup(label)
        return self._wrap(Json.dumps(data),
        label,
        title='Data for embedded Belyi map with label %s,'%label)


@belyi_page.route("/download_galmap_to_magma/<label>")
def belyi_galmap_magma_download(label):
    return Belyi_download().download_galmap_magma(label)

@belyi_page.route("/download_galmap_to_sage/<label>")
def belyi_galmap_sage_download(label):
    return Belyi_download().download_galmap_sage(label)

@belyi_page.route("/download_galmap_to_text/<label>")
def belyi_galmap_text_download(label):
    return Belyi_download().download_galmap_text(label)

@search_wrap(
    template="belyi_search_results.html",
    table=db.belyi_galmaps_test,
    title="Belyi map search results",
    err_title="Belyi Maps Search Input Error",
    shortcuts={"jump": belyi_jump, "download": Belyi_download()},
    projection=["label", "group", "deg", "g", "orbit_size", "geomtype"],
    url_for_label=lambda label: url_for(".by_url_belyi_search_url", smthorlabel=label),
    cleaners={"geomtype": lambda v: geometry_types_dict[v["geomtype"]]},
    bread=lambda: [("Belyi Maps", url_for(".index")), ("Search Results", ".")],
    credit=lambda: credit_string,
    learnmore=learnmore_list,
)

#TODO: this probably needs to be updated, too
def belyi_search(info, query):
    info["geometry_types_list"] = geometry_types_list
    info["geometry_types_dict"] = geometry_types_dict
    info["belyi_galmap_url"] = lambda label: url_for_belyi_galmap_label(label)
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
    # invariants and drop-list items don't require parsing -- they are all strings (supplied by us, not the user)
    for fld in ["geomtype", "group"]:
        if info.get(fld):
            query[fld] = info[fld]


################################################################################
# Statistics
################################################################################


class Belyi_stats(StatsDisplay):
    """
    Class for creating and displaying statistics for Belyi maps
    """

    def __init__(self):
        ngalmaps = comma(db.belyi_galmaps_test.stats.count())
        npassports = comma(db.belyi_passports_test.stats.count())
        max_deg = comma(db.belyi_passports_test.max("deg"))
        deg_knowl = display_knowl("belyi.degree", title="degree")
        belyi_knowl = '<a title="Belyi maps (up to Galois conjugation) [belyi.galmap]" knowl="belyi.galmap" kwargs="">Belyi maps</a>'
        stats_url = url_for(".statistics")
        self.short_summary = (
            'The database currently contains %s %s of %s up to %s.  Here are some <a href="%s">further statistics</a>.'
            % (ngalmaps, belyi_knowl, deg_knowl, max_deg, stats_url)
        )
        self.summary = (
            "The database currently contains %s Galois orbits of Belyi maps in %s passports, with %s at most %s."
            % (ngalmaps, npassports, deg_knowl, max_deg)
        )

    table = db.belyi_galmaps_test
    baseurl_func = ".index"
    row_titles = {"deg": "degree", "orbit_size": "size", "g": "genus"}
    top_titles = {"orbit_size": "Galois orbit size"}
    knowls = {
        "deg": "belyi.degree",
        "orbit_size": "belyi.orbit_size",
        "g": "belyi.genus",
    }
    stat_list = [
        {"cols": col, "totaler": {"avg": True}} for col in ["deg", "orbit_size", "g"]
    ]


@belyi_page.route("/stats")
def statistics():
    title = "Belyi maps: statistics"
    bread = (("Belyi Maps", url_for(".index")), ("Statistics", " "))
    return render_template(
        "display_stats.html",
        info=Belyi_stats(),
        credit=credit_string,
        title=title,
        bread=bread,
        learnmore=learnmore_list(),
    )


@belyi_page.route("/Completeness")
def completeness_page():
    t = "Completeness of Belyi map data"
    bread = (("Belyi Maps", url_for(".index")), ("Completeness", ""))
    return render_template(
        "single.html",
        kid="dq.belyi.extent",
        credit=credit_string,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Completeness"),
    )


@belyi_page.route("/Source")
def how_computed_page():
    t = "Source of Belyi map data"
    bread = (("Belyi Maps", url_for(".index")), ("Source", ""))
    return render_template(
        "single.html",
        kid="dq.belyi.source",
        credit=credit_string,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("Source"),
    )


@belyi_page.route("/Labels")
def labels_page():
    t = "Labels for Belyi maps"
    bread = (("Belyi Maps", url_for(".index")), ("Labels", ""))
    return render_template(
        "single.html",
        kid="belyi.label",
        credit=credit_string,
        title=t,
        bread=bread,
        learnmore=learnmore_list_remove("labels"),
    )

class BelyiSearchArray(SearchArray):
    noun = "map"
    plural_noun = "maps"
    #jump_example = "4T5-[4,4,3]-4-4-31-g1-a"
    jump_example = "4T5-4_4_3.1-a"
    #jump_egspan = "e.g. 4T5-[4,4,3]-4-4-31-g1-a"
    jump_egspan = "e.g. 4T5-4_4_3.1-a"
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
        count = CountBox()

        self.browse_array = [[deg], [group], [abc], [abc_list], [g], [orbit_size], [geomtype], [count]]

        self.refine_array = [[deg, group, abc, abc_list], [g, orbit_size, geomtype]]
