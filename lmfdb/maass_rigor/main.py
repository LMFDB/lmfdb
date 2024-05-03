# -*- coding: utf-8 -*-

import re
from lmfdb import db
from flask import render_template, request, url_for, abort
from lmfdb.maass_rigor import maass_rigor_page, logger
from lmfdb.utils import (
    SearchArray, search_wrap, TextBox, SelectBox, CountBox, to_dict, comma,
    parse_ints, parse_floats, rgbtohex, signtocolour, flash_error, redirect_no_cache)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_parsing import search_parser
from lmfdb.utils.display_stats import StatsDisplay, proportioners, totaler
from lmfdb.utils import display_knowl
from lmfdb.utils.search_columns import SearchColumns, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.maass_rigor.plot import paintSvgMaass
from lmfdb.maass_rigor.web_maassform import character_link, fricke_pretty, symmetry_pretty, WebRigorMaassForm, MaassFormDownloader
from sage.all import gcd


CHARACTER_LABEL_RE = re.compile(r"^[1-9][0-9]*\.[1-9][0-9]*")
MAASS_ID_RE = re.compile(r"^[0-9\.]+$")


def bread_prefix():
    return [
        ('Modular forms', url_for('modular_forms')),
        ('Maass', url_for('.index'))
    ]


###############################################################################
# Learnmore display functions
###############################################################################


def learnmore_list():
    return [('Source and acknowledgments', url_for('.source_page')),
            ('Completeness of the data', url_for('.completeness_page')),
            ('Reliability of the data', url_for('.reliability_page')),
            ('Rigorous Maass form labels', url_for(".labels_page"))]


def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


###############################################################################
# Utilities
###############################################################################


def search_by_label(label):
    try:
        mf = WebRigorMaassForm.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    info = to_dict(request.args)
    return render_template("maass_rigor_form.html",
                           mf=mf,
                           info=info,
                           properties=mf.properties,
                           downloads=mf.downloads,
                           bread=mf.bread,
                           title=mf.title,
                           friends=mf.friends,
                           learnmore=learnmore_list(),
                           KNOWL_ID="mf.maass_rigor.mwf.%s" % mf.label
                           )


###############################################################################
# Pages
###############################################################################



@maass_rigor_page.route('/')
def index():
    info = to_dict(request.args, search_array=MaassSearchArray(), stats=MaassStats())
    if request.args:
        return search(info)
    title = 'Rigorous Maass forms'
    bread = bread_prefix()
    return render_template(
        'maass_browse.html',
        info=info,
        title=title,
        learnmore=learnmore_list(),
        bread=bread,
        dbcount=db.maass_rigor.count()
    )


@maass_rigor_page.route('/<label>')
def by_label(label):
    return search_by_label(label)


@maass_rigor_page.route("/download/<label>")
def download(label):
    return MaassFormDownloader().download(label)


@maass_rigor_page.route("/download_coefficients/<label>")
def download_coefficients(label):
    return MaassFormDownloader().download_coefficients(label)


@maass_rigor_page.route("/data/<label>")
def maass_data(label):
    if not MAASS_ID_RE.fullmatch(label):
        return abort(404, f"Invalid id {label}")
    title = f"Rigorous Maass form data - {label}"
    bread = [("Modular forms", url_for("modular_forms")),
             ("Maass", url_for(".index")),
             (label, url_for(".by_label", label=label)),
             ("Data", " ")]
    # TODO when portraits are done, re-add 
    tables = ["maass_rigor"]
    label_cols = ["maass_label"]
    return datapage(label, tables, bread=bread, title=title, label_cols=label_cols)


@maass_rigor_page.route('/Source')
def source_page():
    t = 'Source of rigorous Maass form data'
    bread = bread_prefix() + [('Source','')]
    return render_template('multi.html', kids=['rcs.source.maass_rigor',
                                               'rcs.ack.maass_rigor',
                                               'rcs.cite.maass'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))


@maass_rigor_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of rigorous Maass form data'
    bread = bread_prefix() + [('Completeness','')]
    return render_template('single.html', kid='rcs.cande.maass_rigor',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


@maass_rigor_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Maass form data'
    bread = bread_prefix() + [('Reliability','')]
    return render_template('single.html', kid='rcs.rigor.maass_rigor',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))


@maass_rigor_page.route("/Labels")
def labels_page():
    t = 'Labels for Rigorous Maass forms'
    bread = bread_prefix() + [('Labels', '')]
    return render_template("single.html", kid='mf.maass_rigor.label',
                           title=t, bread=bread,
                           learnmore=learnmore_list_remove('labels'))


@maass_rigor_page.route('/random')
@redirect_no_cache
def random():
    label = db.maass_rigor.random()
    return url_for('.by_label', label=label)


@maass_rigor_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "mf.maass_rigor.mwf",
        db.maass_rigor,
        label_col="maass_label",
        url_for_label=lambda label: url_for(".by_label", label=label),
        title="Some interesting Maass forms",
        bread=bread_prefix() + [("Interesting", " ")],
        learnmore=learnmore_list()
    )


@maass_rigor_page.route("/stats")
def statistics():
    title = "Rigorous Maass forms: statistics"
    bread = bread_prefix() + [("Statistics", " ")]
    return render_template("display_stats.html", info=MaassStats(), title=title, bread=bread, learnmore=learnmore_list())


# @maass_rigor_page.route("/<int:level>/")
# def by_level(level):
#     info = to_dict(request.args, search_array=MaassSearchArray())
#     info['level'] = level
#     return search(info)
# 
# 
# @maass_rigor_page.route("/<int:level>/<int:weight>/")
# def by_level_weight(level, weight):
#     info = to_dict(request.args, search_array=MaassSearchArray())
#     info['level'] = level
#     info['weight'] = weight
#     return search(info)
# 
# 
# @maass_rigor_page.route("/<int:level>/<int:weight>/<int:conrey_index>/")
# def by_level_weight_character(level, weight, conrey_index):
#     info = to_dict(request.args, search_array=MaassSearchArray())
#     info['level'] = level
#     info['weight'] = weight
#     info['conrey_index'] = conrey_index
#     return search(info)


@maass_rigor_page.route("/BrowseGraph/<min_level>/<max_level>/<min_R>/<max_R>/")
def browse_graph(min_level, max_level, min_R, max_R):
    r"""
    Render a page with a graph with clickable dots for all
    with min_R <= R <= max_R and levels in the similar range.
    """
    info = {}
    info['contents'] = [paintSvgMaass(min_level, max_level, min_R, max_R)]
    info['min_level'] = min_level
    info['max_level'] = max_level
    info['min_R'] = min_R
    info['max_R'] = max_R
    info['coloreven'] = rgbtohex(signtocolour(1))
    info['colorodd'] = rgbtohex(signtocolour(-1))
    bread = bread_prefix() + [('Browse graph', '')]
    info['bread'] = bread
    info['learnmore'] = learnmore_list()
    return render_template("maass_browse_graph.html", title='Browsing graph of Maass forms', **info)


class MaassSearchArray(SearchArray):
    sorts = [("", "level", ['level', 'weight', 'conrey_index', 'spectral_parameter']),
             ("spectral", "spectral parameter", ['spectral_parameter', 'weight', 'level', 'conrey_index'])]
    noun = "Rigorous Maass form"
    plural_noun = "Rigorous Maass forms"

    def __init__(self):
        level = TextBox(name="level", label="Level", knowl="mf.maass.mwf.level", example="1", example_span="2 or 1-10")
        weight = TextBox(name="weight", label="Weight", knowl="mf.maass.mwf.weight", example="0", example_span="0 (only weight 0 currently available)")
        character = TextBox(name="character", label="Character", knowl="mf.maass.mwf.character", example="1.1", example_span="1.1 or 5.1 (only trivial character currently available)")
        symmetry = SelectBox(name="symmetry", label="Symmetry", knowl="mf.maass.mwf.symmetry", options=[("", "any symmetry"), ("0", "even only"), ("1", "odd only")])
        spectral_parameter = TextBox(name="spectral_parameter",
                                     label="Spectral parameter",
                                     knowl="mf.maass.mwf.spectralparameter",
                                     example="9.5-9.6",
                                     example_span="1.23 or 1.99-2.00 or 40-50")
        count = CountBox()
        self.browse_array = [
            [level],
            [weight],
            [character],
            [spectral_parameter],
            [symmetry],
            [count]
        ]
        self.refine_array = [[level, weight, character, spectral_parameter, symmetry]]


@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_character(inp, query, qfield):
    if not CHARACTER_LABEL_RE.match(inp):
        raise ValueError("Character labels must be of the form q.n, where q and n are positive integers.")
    level_field, conrey_index_field ='level', 'conrey_index'
    level, conrey_index = inp.split('.')
    level, conrey_index = int(level), int(conrey_index)
    if conrey_index > level:
        raise ValueError("Character labels q.n must have Conrey index n no greater than the modulus q.")
    if gcd(level, conrey_index) != 1:
        raise ValueError("Character labels q.n must have Conrey index coprime to the modulus q.")

    def contains_level(D):
        if D == level:
            return True
        if isinstance(D, dict):
            a = D.get('$gte')
            b = D.get('$lte')
            return (a is None or level >= a) and (b is None or level <= b)

    # Check that the provided constraint on level is consistent with the one
    # given by the character, and update level/$or
    if '$or' in query and all(level_field in D for D in query['$or']):
        if not any(contains_level(D) for D in query['$or']):
            raise ValueError("The modulus is not consistent with the specified level.")
        del query['$or']
    elif level_field in query:
        if not contains_level(query[level_field]):
            raise ValueError("The modulus is not consistent with the specified level.")
    query[level_field] = level
    query[conrey_index_field] = conrey_index


def spectral_parameter_link(maass_label, spectral_parameter):
    url = url_for('.by_label', label=maass_label)
    return f"<a href=\"{url}\">{str(spectral_parameter)[:10]}</a>"


maass_columns = SearchColumns([
    MathCol("level", "mf.maass.mwf.level", "Level"),
    MathCol("weight", "mf.maass.mwf.weight", "Weight"),
    MultiProcessedCol("character", "mf.maass.mwf.character", "Char",
                      ["level", "conrey_index"],
                      character_link, short_title="character",
                      align="center", apply_download=False),
    MultiProcessedCol("spectral", "mf.maass.mwf.spectralparameter", "Spectral parameter",
                      ["maass_label", "spectral_parameter"],
                      spectral_parameter_link,
                      download_col="spectral_parameter"),
    ProcessedCol("symmetry", "mf.maass.mwf.symmetry", "Symmetry",
                 symmetry_pretty,
                 align="center"),
    ProcessedCol("fricke_eigenvalue", "cmf.fricke", "Fricke",
                 fricke_pretty, short_title="Fricke",
                 align="center")],
    db_cols=["maass_label", "level", "weight", "conrey_index", "spectral_parameter", "symmetry", "fricke_eigenvalue"])


@search_wrap(
    table=db.maass_rigor,
    title="Rigorous Maass forms search results",
    err_title="Rigorous Maass forms search input error",
    columns=maass_columns,
    shortcuts={"download": MaassFormDownloader()},
    random_projection="maass_label",
    bread=lambda: bread_prefix() + [('Search results', '')],
    learnmore=learnmore_list,
    url_for_label=lambda label: url_for(".by_label", label=label),
)
def search(info, query):
    parse_ints(info, query, 'level', name='Level')
    parse_ints(info, query, 'weight', name='Weight')
    parse_character(info, query, 'character', name='Character')
    parse_floats(info, query, 'spectral_parameter', name='Spectral parameter')
    if info.get('symmetry'):
        query['symmetry'] = int(info['symmetry'])


class MaassStats(StatsDisplay):
    table = db.maass_rigor
    baseurl_func = ".index"

    stat_list = [
        {'cols': ['level', 'spectral_parameter'],
         'totaler': totaler(),
         'proportioner': proportioners.per_row_total},
        {'cols': ['symmetry', 'level'],
         'totaler': totaler(),
         'proportioner': proportioners.per_col_total},
        {'cols': ['symmetry', 'spectral_parameter'],
         'totaler': totaler(),
         'proportioner': proportioners.per_col_total},
    ]

    top_titles = {'symmetry': 'symmetries'}

    buckets = {'level': ['1', '2-13', '14-20', '21-30', '31-100', '101-997'],
               'spectral_parameter': ['0-1', '1-2', '2-3', '3-4', '4-6', '6-10', '10-20', '20-32', '32-50']}

    knowls = {'level': 'mf.maass.mwf.level',
              'spectral_parameter': 'mf.maass.mwf.spectralparameter',
              'symmetry': 'mf.maass.mwf.symmetry'}

    formatters = {'symmetry': (lambda t: 'even' if t in [0, '0'] else 'odd')}
    query_formatters = {'symmetry': (lambda t: 'symmetry=%s' % (1 if t in [1, '1', 'odd'] else 0))}

    def __init__(self):
        self.nforms = self.table.count()
        self.max_level = self.table.max('level')

    @property
    def short_summary(self):
        return self.summary + '  Here are some <a href="%s">further statistics</a>.' % (url_for(".statistics"))

    @property
    def summary(self):
        return r"The database currently contains %s %s of %s 0 on $\Gamma_0(N)$ for $N$ in the range from 1 to %s." % (comma(self.nforms), display_knowl('mf.maass.mwf', 'Maass forms'), display_knowl('mf.maass.mwf.weight', 'weight'), self.max_level)
