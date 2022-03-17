# -*- coding: utf-8 -*-

import re
from lmfdb import db

from flask import render_template, url_for, request, redirect

from lmfdb.utils import (
    SearchArray,
    TextBox,
    CountBox,
    redirect_no_cache,
    flash_error,
    search_wrap,
    to_dict,
    parse_ints,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, LinkCol

from lmfdb.modular_curves import modcurve_page
from lmfdb.modular_curves.web_curve import WebModCurve, get_bread

LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")

@modcurve_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@modcurve_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=ModCurveSearchArray())
    if len(info) > 1:
        return modcurve_search(info)
    title = r"Modular curves over $\Q$"
    return render_template(
        "modcurve_browse.html",
        info=info,
        title=title,
        bread=get_bread(),
    )

@modcurve_page.route("/Q/random/")
@redirect_no_cache
def random_curve():
    label = db.gps_gl2zhat_test.random()
    return url_for_curve_label(label)

@modcurve_page.route("/Q/<label>/")
def by_label(label):
    if not LABEL_RE.match(label):
        flash_error("Invalid label")
        return redirect(".index")
    try:
        curve = WebModCurve(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    return render_template(
        "modcurve.html",
        curve=curve,
        properties=curve.properties,
        bread=curve.bread,
        title=curve.title,
        KNOWL_ID=f"modcurve.{label}",
    )

def url_for_modcurve_label(label):
    return url_for(".by_label", label=label)

def modcurve_jump(label):
    return redirect(url_for_modcurve_label(label))

modcurve_columns = SearchColumns([
    LinkCol("label", "modcurve.label", "Label", url_for_modcurve_label, default=True),
    MathCol("level", "modcurve.level", "Level", default=True),
    MathCol("index", "modcurve.index", "Index", default=True),
    MathCol("genus", "modcurve.genus", "Genus", default=True),
    MathCol("rank", "modcurve.rank", "Rank", default=True),
    MathCol("cusps", "modcurve.cusps", "Cusps", default=True),
    MathCol("rational_cusps", "modcurve.rational_cusps", r"$\Q$-cusps", default=True),
])

@search_wrap(
    table=db.gps_gl2zhat_test,
    title="Modular curve search results",
    err_title="Modular curves search input error",
    shortcuts={"jump": modcurve_jump},
    columns=modcurve_columns,
    bread=lambda: get_bread("Search results"),
    url_for_label=url_for_modcurve_label,
)
def modcurve_search(info, query):
    parse_ints(info, query, "level")
    parse_ints(info, query, "index")
    parse_ints(info, query, "genus")
    parse_ints(info, query, "rank")
    parse_ints(info, query, "cusps")
    parse_ints(info, query, "rational_cusps")

class ModCurveSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"

    def __init__(self):
        level = TextBox(
            name="level",
            knowl="modcurve.level",
            label="Level",
            example="11",
            example_span="2, 11-23",
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
        cusps = TextBox(
            name="cusps",
            knowl="modcurve.cusps",
            label="Cusps",
            example="1",
            example_span="1, 4-8",
        )
        rational_cusps = TextBox(
            name="rational_cusps",
            knowl="modcurve.rational_cusps",
            label=r"$\Q$-Cusps",
            example="1",
            example_span="0, 4-8",
        )
        count = CountBox()

        self.browse_array = [
            [level, index],
            [genus, rank],
            [cusps, rational_cusps],
            [count],
        ]

        self.refine_array = [
            [ level, index, genus, rank],
            [cusps, rational_cusps],
        ]

        sort_knowl = "modcurve.sort_order"
        sorts = [("", "level", ["level", "index", "genus", "label"]),
                 ("index", "index", ["index", "level", "genus", "label"]),
                 ("genus", "genus", ["genus", "level", "index", "label"])]
