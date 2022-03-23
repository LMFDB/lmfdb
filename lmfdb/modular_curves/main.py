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
    display_knowl,
    flash_error,
    search_wrap,
    to_dict,
    parse_ints,
    parse_noop,
    parse_bool,
    parse_interval,
    parse_element_of,
    integer_divisors,
    StatsDisplay,
    Downloader,
    comma,
    proportioners,
    totaler
)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, CheckCol, LinkCol, ProcessedCol

from lmfdb.backend.encoding import Json

from lmfdb.modular_curves import modcurve_page
from lmfdb.modular_curves.web_curve import WebModCurve, get_bread, canonicalize_name, name_to_latex, factored_conductor, formatted_dims

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
    info["level_list"] = ["1-4", "5-8", "9-12", "13-16", "17-23", "23-"]
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
        flash_error("Invalid label %s", label)
        return redirect(url_for(".index"))
    curve = WebModCurve(label)
    if curve.is_null():
        flash_error("There is no modular curve %s in the database", label)
        return redirect(url_for(".index"))
    return render_template(
        "modcurve.html",
        curve=curve,
        properties=curve.properties,
        friends=curve.friends,
        bread=curve.bread,
        title=curve.title,
        downloads=curve.downloads,
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
    ProcessedCol("rank", "modcurve.rank", "Rank", lambda r: "" if r is None else r, default=lambda info: info.get("rank") or info.get("genus_minus_rank"), align="center", mathmode=True),
    ProcessedCol("gonality_bounds", "modcurve.gonality", "$K$-gonality", lambda b: r'$%s$'%(b[0]) if b[0] == b[1] else r'$%s \le \gamma \le %s$'%(b[0],b[1]), align="center", default=True),
    MathCol("cusps", "modcurve.cusps", "Cusps", default=True),
    MathCol("rational_cusps", "modcurve.cusps", r"$\Q$-cusps", default=True),
    ProcessedCol("cm_discriminants", "modcurve.cm_discriminants", "CM points", lambda d: r"$\textsf{yes}$" if d else r"$\textsf{no}$", align="center", default=True),
    ProcessedCol("conductor", "ag.conductor", "Conductor", factored_conductor, align="center", mathmode=True),
    CheckCol("simple", "modcurve.simple", "Simple"),
    CheckCol("semisimple", "modcurve.semisimple", "Semisimple"),
    CheckCol("contains_negative_one", "modcurve.contains_negative_one", "Contains -1", short_title="contains -1"),
    CheckCol("plane_model", "modcurve.plane_model", "Model"),
    ProcessedCol("dims", "modcurve.decomposition", "Decomposition", formatted_dims, align="center"),
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
    parse_interval(info, query, "gonality", quantifier_type=info.get("gonality_type", "exactly"))
    parse_ints(info, query, "rational_cusps")
    parse_bool(info, query, "simple")
    parse_bool(info, query, "semisimple")
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
    #parse_element_of(info, query, "covered_by", qfield="children")
    if "covered_by" in info:
        # sort of hacky
        parents = db.gps_gl2zhat_test.lookup(info["covered_by"], "parents")
        if parents is None:
            msg = "%s not the label of a modular curve in the database"
            flash_error(msg, info["covered_by"])
            raise ValueError(msg % info["covered_by"])
        query["label"] = {"$in": parents}

class ModCurveSearchArray(SearchArray):
    noun = "curve"
    plural_noun = "curves"
    jump_example = "13.78.3.1"
    jump_egspan = "e.g. 13.78.3.1, XNS+(13), 13Nn, or 13A3"
    jump_prompt = "Label or coefficients"
    jump_knowl = "modcurve.search_input"

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
                     ],
            min_width=85)
        gonality = TextBoxWithSelect(
            name="gonality",
            knowl="modcurve.gonality",
            label="$K$-gonality",
            example="2",
            example_span="2, 3-6",
            select_box=gonality_quantifier,
        )
        covers = TextBox(
            name="covers",
            knowl="modcurve.modular_cover",
            label="Minimally covers",
            example="1.1.0.1",
        )
        covered_by = TextBox(
            name="covered_by",
            knowl="modcurve.modular_cover",
            label="Minimally covered by",
            example="6.12.0.1",
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
        cm_opts = ([('', ''), ('yes', 'rational CM points'), ('no', 'no rational CM points')] +
                   [('-4,-16', 'CM field Q(sqrt(-1))'), ('-3,-12,-27', 'CM field Q(sqrt(-3))'), ('-7,-28', 'CM field Q(sqrt(-7))')] +
                   [('-%d'%d, 'CM discriminant -%d'%d) for  d in [3,4,7,8,11,12,16,19,27,38,43,67,163]])
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
            example_col=True,
        )
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
            [simple, semisimple],
            [covers, covered_by],
            [cm_discriminants, contains_negative_one],
            [count]
        ]

        self.refine_array = [
            [level, index, genus, rank, genus_minus_rank],
            [gonality, cusps, rational_cusps, simple, semisimple],
            [covers, covered_by, cm_discriminants, contains_negative_one, CPlabel],
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
        'rank': False,
        'genus_minus_rank': False,
    }

class ModCurve_stats(StatsDisplay):
    def __init__(self):
        self.ncurves = comma(db.gps_gl2zhat_test.count())
        self.max_level = db.gps_gl2zhat_test.max("level")

    @property
    def short_summary(self):
        modcurve_knowl = display_knowl("modcurve", title="modular curves")
        return (
            fr'The database currently contains {self.ncurves} {modcurve_knowl} of level $N\le {self.max_level}$ parameterizing elliptic curves $E/\Q$.  You can <a href="{url_for(".statistics")}">browse further statistics</a>.'
        )

    @property
    def summary(self):
        modcurve_knowl = display_knowl("modcurve", title="modular curves")
        return (
            fr'The database currently contains {self.ncurves} {modcurve_knowl} of level $N\le {self.max_level}$ parameterizing elliptic curves $E/\Q$.'
        )

    table = db.gps_gl2zhat_test
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
         'proportioner': proportioners.per_col_total,
         'totaler': totaler()},
        {'cols': ['genus', 'rank'],
         'proportioner': proportioners.per_col_total,
         'totaler': totaler()},
        {'cols': ['genus', 'gonality'],
         'proportioner': proportioners.per_col_total,
         'totaler': totaler()},
    ]

@modcurve_page.route("/Q/stats")
def statistics():
    title = 'Modular curves: Statistics'
    return render_template("display_stats.html", info=ModCurve_stats(), title=title, bread=get_bread('Statistics'), learnmore=learnmore_list())

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

class ModCurve_download(Downloader):
    table = db.gps_gl2zhat_test
    title = "Modular curves"
    #columns = ['level', 'genus', 'plane_model']
    #data_format = []
    #data_description = []

    function_body = {
        "magma": [
            #"return data[3];"
        ],
        "sage": [
            #"return data[3]"
        ],
    }

# cols currently unused in individual page download
    #'determinant_label',
    #'scalar_label',
    #'reductions',
    #'orbits',
    #'kummer_orbits',
    #'isogeny_orbits',
    #'obstructions',
    #'gassmann_class',
    #'newforms',
    #'dims',
    #'simple',
    #'semisimple',
    #'trace_hash',
    #'traces',

    def download_modular_curve(self, label, lang):
        s = ""
        rec = db.gps_gl2zhat_test.lookup(label)
        if rec is None:
            return abort(404, "Label not found: %s" % label)
        if lang == "magma":
            s += "// Magma code for modular curve with label %s\n\n" % label
            if rec['name'] or rec['CPlabel'] or rec['Slabel'] or rec['SZlabel'] or rec['RZBlabel']:
                s += "// other names and/or labels\n"
                if rec['name']:
                    s += "// Curve name: %s\n" % rec['name']
                if rec['CPlabel']:
                    s += "// Cummins-Pauli label: %s\n" % rec['CPlabel']
                if rec['RZBlabel']:
                    s += "// Rouse-Zureick-Brown label: %s\n" % rec['RZBlabel']
                if rec['Slabel']:
                    s += "// Sutherland label: %s\n" % rec['Slabel']
                if rec['SZlabel']:
                    s += "// Sutherland-Zywina label: %s\n" % rec['SZlabel']
            s += "\n// Group data\n"
            s += "level := %s;\n" % rec['level']
            s += "// Elements that, together with Gamma(level), generate the group\n"
            s += "gens := %s;\n" % rec['generators']
            s += "// Group contains -1?\n"
            s += "ContainsMinus1 := %s;\n" % rec['contains_negative_one']
            s += "// Index in Gamma(1)\n"
            s += "index := %s;\n" % rec['index']
            s += "\n// Curve data\n"
            s += "conductor := %s;\n" % rec['conductor']
            s += "bad_primes := %s;\n" % rec['bad_primes']
            s += "// Make plane model, if computed;\n"
            if rec["plane_model"]:
                s += "QQ := Rationals();\n"
                s += "R<X,Y,Z> := PolynomialRing(QQ,3);\n"
                s += "XX := Curve(ProjectiveSpace(R), %s);\n" % rec['plane_model']
            s += "// Genus\n"
            s += "g := %s;\n" % rec['genus']
            s += "// Rank\n"
            s += "r := %s;\n" % rec['rank']
            if rec['gonality'] != -1:
                s += "// Exact gonality known\n"
                s += "gamma := %s;\n" % rec['gonality']
            else:
                s += "// Exact gonality unknown, but contained in following interval\n"
                s += "gamma_int := %s;\n" % rec['gonality_bounds']
            s += "\n// Modular data\n"
            s += "// Number of cusps\n"
            s += "Ncusps := %s;\n" % rec['cusps']
            s += "// Number of rational cusps\n"
            s += "Nrat_cusps := %s;\n" % rec['cusps']
            if rec['jmap']:
                s += "// Map to j-line\n"
                s += "jmap := %s;\n" % rec['jmap']
            if rec['Emap']:
                s += "// Map to j-line\n"
                s += "Emap := %s;\n" % rec['Emap']
            s += "// CM discriminants\n"
            s += "CM_discs := %s;\n" % rec['cm_discriminants']
            s += "// groups containing given group, corresponding to curves covered by given curve\n"
            s += "covers := %s;\n" % rec['parents'].replace("'",'"')
            return(self._wrap(s, label, lang=lang))

        # once more with feeling
        elif lang == "sage":
            s += "# Sage code for modular curve with label %s\n\n" % label

            if rec['name'] or rec['CPlabel'] or rec['Slabel'] or rec['SZlabel'] or rec['RZBlabel']:
                s += "# other names and/or labels\n"
                if rec['name']:
                    s += "# Curve name: %s\n" % rec['name']
                if rec['CPlabel']:
                    s += "# Cummins-Pauli label: %s\n" % rec['CPlabel']
                if rec['RZBlabel']:
                    s += "# Rouse-Zureick-Brown label: %s\n" % rec['RZBlabel']
                if rec['Slabel']:
                    s += "# Sutherland label: %s\n" % rec['Slabel']
                if rec['SZlabel']:
                    s += "# Sutherland-Zywina label: %s\n" % rec['SZlabel']
            s += "\n# Group data\n"
            s += "level = %s\n" % rec['level']
            s += "# Elements that, together with Gamma(level), generate the group\n"
            s += "gens = %s\n" % rec['generators']
            s += "# Group contains -1?\n"
            s += "ContainsMinus1 = %s\n" % rec['contains_negative_one']
            s += "# Index in Gamma(1)\n"
            s += "index = %s\n" % rec['index']
            s += "\n# Curve data\n"
            s += "conductor = %s\n" % rec['conductor']
            s += "bad_primes = %s\n" % rec['bad_primes']
            s += "# Make plane model, if computed\n"
            if rec["plane_model"]:
                s += "QQ = Rationals()\n"
                s += "R<X,Y,Z> = PolynomialRing(QQ,3)\n"
                s += "XX = Curve(ProjectiveSpace(R), %s)\n" % rec['plane_model']
            s += "# Genus\n"
            s += "g = %s\n" % rec['genus']
            s += "# Rank\n"
            s += "r = %s\n" % rec['rank']
            if rec['gonality'] != -1:
                s += "# Exact gonality known\n"
                s += "gamma = %s\n" % rec['gonality']
            else:
                s += "# Exact gonality unknown, but contained in following interval\n"
                s += "gamma_int = %s\n" % rec['gonality_bounds']
            s += "\n# Modular data\n"
            s += "# Number of cusps\n"
            s += "Ncusps = %s\n" % rec['cusps']
            s += "# Number of rational cusps\n"
            s += "Nrat_cusps = %s\n" % rec['cusps']
            if rec['jmap']:
                s += "# Map to j-line\n"
                s += "jmap = %s\n" % rec['jmap']
            if rec['Emap']:
                s += "# Map to j-line\n"
                s += "Emap = %s\n" % rec['Emap']
            s += "# CM discriminants\n"
            s += "CM_discs = %s\n" % rec['cm_discriminants']
            s += "# groups containing given group, corresponding to curves covered by given curve\n"
            s += "covers = %s\n" % rec['parents']
            return(self._wrap(s, label, lang=lang))
        if lang == "text":
            data = db.gps_gl2zhat_test.lookup(label)
            if data is None:
                return abort(404, "Label not found: %s" % label)
            return self._wrap(Json.dumps(data),
                              label,
                              title='Data for modular curve with label %s,'%label)

@modcurve_page.route("/download_to_magma/<label>")
def modcurve_magma_download(label):
    return ModCurve_download().download_modular_curve(label, lang="magma")

@modcurve_page.route("/download_to_sage/<label>")
def modcurve_sage_download(label):
    return ModCurve_download().download_modular_curve(label, lang="sage")

@modcurve_page.route("/download_to_text/<label>")
def modcurve_text_download(label):
    return ModCurve_download().download_modular_curve(label, lang="text")

