# -*- coding: utf-8 -*-

import re
from lmfdb import db

from flask import render_template, url_for, request, redirect

from sage.all import ZZ

from lmfdb.utils import (
    SearchArray,
    TextBox,
    TextBoxWithSelect,
    SelectBox,
    SneakyTextBox,
    YesNoBox,
    CountBox,
    redirect_no_cache,
    flash_error,
    search_wrap,
    to_dict,
    parse_ints,
    parse_noop,
    parse_bool,
    integer_divisors,
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, LinkCol, ProcessedCol

from lmfdb.modular_curves import modcurve_page
from lmfdb.modular_curves.web_curve import WebModCurve, get_bread, canonicalize_name, name_to_latex

LABEL_RE = re.compile(r"\d+\.\d+\.\d+\.\d+")
CP_LABEL_RE = re.compile(r"\d+[A-Z]\d+")
SZ_LABEL_RE = re.compile(r"\d+[A-Z]\d+-\d+[a-z]")
RZB_LABEL_RE = re.compile(r"X\d+")
S_LABEL_RE = re.compile(r"\d+(G|B|Cs|Cn|Ns|Nn|A4|S4|A5)(\.\d+){0,3}")
NAME_RE = re.compile(r"X_?(0|1|NS|NS\^?\+|SP|SP\^?\+|S4)?\(\d+\)")

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Modular curve labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

@modcurve_page.route("/")
def index():
    return redirect(url_for(".index_Q", **request.args))

@modcurve_page.route("/Q/")
def index_Q():
    info = to_dict(request.args, search_array=ModCurveSearchArray())
    if len(info) > 1:
        return modcurve_search(info)
    title = r"Modular curves over $\Q$"
    info["level_list"] = ["1-10", "11-100"]
    info["genus_list"] = ["0", "1", "2", "3", "4-6", "7-20", "20-100", "101-"]
    info["rank_list"] = ["0", "1", "2", "3", "4-6", "7-20", "20-100", "101-"]
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
    label = db.gps_gl2zhat_test.random()
    return url_for_modcurve_label(label)

@modcurve_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "modcurve",
        db.gps_gl2zhat_test,
        url_for_modcurve_label,
        title="Some interesting modular curves",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list(),
    )

@modcurve_page.route("/Q/<label>/")
def by_label(label):
    if not LABEL_RE.fullmatch(label):
        flash_error("Invalid label")
        return redirect(url_for(".index"))
    curve = WebModCurve(label)
    if curve.is_null():
        flash_error("There is no modular curve %s in the database", label)
        return redirect(url_for(".index"))
    return render_template(
        "modcurve.html",
        curve=curve,
        properties=curve.properties,
        bread=curve.bread,
        title=curve.title,
        KNOWL_ID=f"modcurve.{label}",
        learnmore=learnmore_list(),
    )

def url_for_modcurve_label(label):
    return url_for(".by_label", label=label)

def modcurve_jump(info):
    label = info["jump"]
    print("JUMPING", label)
    if CP_LABEL_RE.fullmatch(label):
        print("MATCHED")
        return redirect(url_for(".index", CPlabel=label))
    elif SZ_LABEL_RE.fullmatch(label):
        lmfdb_label = db.gps_gl2zhat_test.lucky({"SZlabel": label}, "label")
        if lmfdb_label is None:
            flash_error("There is no modular curve in the database with Sutherland & Zywina label %s", label)
            return redirect(url_for(".index"))
        label = lmfdb_label
    elif RZB_LABEL_RE.fullmatch(label):
        lmfdb_label = db.gps_gl2zhat_test.lucky({"RZBlabel": label}, "label")
        if lmfdb_label is None:
            flash_error("There is no modular curve in the database with Rousse & Zureick-Brown label %s", label)
            return redirect(url_for(".index"))
        label = lmfdb_label
    elif S_LABEL_RE.fullmatch(label):
        lmfdb_label = db.gps_gl2zhat_test.lucky({"Slabel": label}, "label")
        if lmfdb_label is None:
            flash_error("There is no modular curve in the database with Sutherland label %s", label)
            return redirect(url_for(".index"))
        label = lmfdb_label
    elif NAME_RE.fullmatch(label.upper()):
        lmfdb_label = db.gps_gl2zhat_test.lucky({"name": canonicalize_name(label)}, "label")
        if lmfdb_label is None:
            flash_error("There is no modular curve in the database with name %s", label)
            return redirect(url_for(".index"))
        label = lmfdb_label
    return redirect(url_for_modcurve_label(label))

modcurve_columns = SearchColumns([
    LinkCol("label", "modcurve.label", "Label", url_for_modcurve_label, default=True),
    ProcessedCol("name", "modcurve.name", "Name", lambda s: name_to_latex(s) if s else "", align="center", default=True),
    MathCol("level", "modcurve.level", "Level", default=True),
    MathCol("index", "modcurve.index", "Index", default=True),
    MathCol("genus", "modcurve.genus", "Genus", default=True),
    ProcessedCol("rank", "modcurve.rank", "Rank", lambda r: "" if r==-1 else f"${r}$", align="center", default=True),
    ProcessedCol("gonality_bounds", "modcurve.gonality", "Gonality", lambda b: r'$%s$'%(b[0]) if b[0] == b[1] else r'$%s \le %s$'%(b[0],b[1]), align="center", default=True),
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
    parse_ints(info, query, "index")
    parse_ints(info, query, "genus")
    parse_ints(info, query, "rank")
    parse_ints(info, query, "genus_minus_rank")
    parse_ints(info, query, "cusps")
    parse_ints(info, query, "gonality")
    parse_ints(info, query, "rational_cusps")
    parse_bool(info, query, "simple")
    parse_bool(info, query, "semisimple")
    parse_noop(info, query, "CPlabel")

class ModCurveSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"

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
            knowl="modcurve.rational_cusps",
            label=r"$\Q$-cusps",
            example="1",
            example_span="0, 4-8",
        )
        gonality = TextBox(
            name="gonality",
            knowl="modcurve.gonality",
            label="Gonality",
            example="2",
            example_span="2, 3-6",
        )
        simple = YesNoBox(
            name="simple",
            knowl="modcurve.simple",
            label="Simple",
            example_col=True,
        )
        semisimple = YesNoBox(
            name="semisimple",
            knowl="modcurve.semisimple",
            label="Semisimple",
            example_col=True,
        )
        CPlabel = SneakyTextBox(
            name="CPlabel",
            knowl="modcurve.cp_label",
            label="CP label",
            example="3B0")
        count = CountBox()

        self.browse_array = [
            [level, index],
            [genus, rank],
            [genus_minus_rank, gonality],
            [cusps, rational_cusps],
            [simple, semisimple],
            [count],
        ]

        self.refine_array = [
            [ level, index, genus, rank, genus_minus_rank],
            [gonality, cusps, rational_cusps, simple, semisimple],
            [CPlabel],
        ]

    sort_knowl = "modcurve.sort_order"
    sorts = [
        ("", "level", ["level", "index", "genus", "label"]),
        ("index", "index", ["index", "level", "genus", "label"]),
        ("genus", "genus", ["genus", "level", "index", "label"]),
        ("rank", "rank", ["rank", "genus", "level", "index", "label"]),
    ]
    null_column_explanations = {
        'simple': False,
        'semisimple': False,
    }

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
    return render_template("single.html", kid='modcurve.lmfdb_label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))
