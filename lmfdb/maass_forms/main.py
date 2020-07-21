# -*- coding: utf-8 -*-

import re
from lmfdb import db
from flask import render_template, request, url_for, redirect, abort
from lmfdb.maass_forms import maass_page #, logger
from lmfdb.utils import (
    SearchArray, search_wrap, TextBox, SelectBox, CountBox, to_dict,
    parse_ints, parse_floats, rgbtohex, signtocolour, flash_error)
from lmfdb.utils.search_parsing import search_parser
from lmfdb.maass_forms.plot import paintSvgMaass
from lmfdb.maass_forms.web_maassform import WebMaassForm, MaassFormDownloader, character_link, symmetry_pretty, fricke_pretty

CHARACTER_LABEL_RE = re.compile(r"^[1-9][0-9]*\.[1-9][0-9]*")

bread_prefix = lambda: [('Modular forms', url_for('modular_forms')),('Maass', url_for('.index'))]

###############################################################################
# Learnmore display functions
###############################################################################

def learnmore_list():
    return [('Completeness of the data', url_for('.completeness_page')),
            ('Source of the data', url_for('.source_page')),
            ('Reliability of the data', url_for('.reliability_page'))]

def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

###############################################################################
# Pages
###############################################################################

credit_string = "David Farmer, Stefan Lemurell, Fredrik Stromberg, and Holger Then"

@maass_page.route('/')
def index():
    info = to_dict(request.args, search_array=MaassSearchArray())
    if len(info) > 1:
        return search(info)
    title = 'Maass forms'
    bread = bread_prefix()
    return render_template('maass_browse.html', info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread, dbcount=db.maass_newforms.count())

@maass_page.route('/random')
def random():
    label = db.maass_newforms.random()
    return redirect(url_for('.by_label', label=label), 307)

@maass_page.route('/<label>')
def by_label(label):
    return search_by_label(label)

@maass_page.route("/<int:level>/")
def by_level(level):
    info = to_dict(request.args, search_array=MaassSearchArray())
    info['level'] = level
    return search(info)

@maass_page.route("/<int:level>/<int:weight>/")
def by_level_weight(level, weight):
    info = to_dict(request.args, search_array=MaassSearchArray())
    info['level'] = level
    info['weight'] = weight
    return search(info)

@maass_page.route("/<int:level>/<int:weight>/<int:conrey_index>/")
def by_level_weight_character(level, weight, conrey_index):
    info = to_dict(request.args, search_array=MaassSearchArray())
    info['level'] = level
    info['weight'] = weight
    info['conrey_index'] = conrey_index
    return search(info)

@maass_page.route("/BrowseGraph/<min_level>/<max_level>/<min_R>/<max_R>/")
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

    return render_template("maass_browse_graph.html", title='Browsing Graph of Maass Forms', **info)

@maass_page.route("/download/<label>")
def download(label):
    return MaassFormDownloader().download(label)

@maass_page.route("/download_coefficients/<label>")
def download_coefficients(label):
    return MaassFormDownloader().download_coefficients(label)

@maass_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Maass form data'
    bread = bread_prefix() + [('Completeness','')]
    return render_template('single.html', kid='rcs.cande.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@maass_page.route('/Source')
def source_page():
    t = 'Source of Maass form data'
    bread = bread_prefix() + [('Source','')]
    return render_template('single.html', kid='rcs.source.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@maass_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Maass form data'
    bread = bread_prefix() + [('Reliability','')]
    return render_template('single.html', kid='rcs.rigor.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

class MaassSearchArray(SearchArray):
    noun = "Maass form"
    plural_noun = "Maass forms"
    def __init__(self):       
        level = TextBox(name="level", label="Level", knowl="mf.maass.mwf.level", example="1", example_span="997 or 1-10")
        weight = TextBox(name="weight", label="Weight", knowl="mf.maass.mwf.weight", example="0", example_span="0 (only weight 0 currenlty available)")
        character = TextBox(name="character", label="Character", knowl="mf.maass.mwf.character", example="1.1", example_span="1.1 or 5.1 (only trivial character currently available)")
        symmetry = SelectBox(name="symmetry", label="Symmetry",  knowl="mf.maass.mwf.symmetry", options=[("", "any symmetry"), ("1", "even only"), ("-1", "odd only")])
        spectral_parameter = TextBox(name="spectral_parameter",
                                     label="Spectral parameter",
                                     knowl="mf.maass.mwf.spectralparameter",
                                     example="1.0-1.1",
                                     example_span="1.0-1.1 or 90-100")
        count = CountBox()

        self.browse_array = [
            [level],
            [weight],
            [character],
            [spectral_parameter],
            [symmetry],
            [count]]

        self.refine_array = [[level, weight, character, spectral_parameter, symmetry]]

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_character(inp, query, qfield):
    if not CHARACTER_LABEL_RE.match(inp):
        raise ValueError("Character labels must be of the form q.n, where q and n are positive integers.")  
    level_field ='level'
    level, conrey_index = inp.split('.')
    level, conrey_index = int(level), int(conrey_index)
    if gcd(level,conrey_index):
        raise ValueError("Character labels q.n must have q and n relativley prime.")
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
            raise ValueError("Inconsistent level")
        del query['$or']
    elif level_field in query:
        if not contains_level(query[level_field]):
            raise ValueError("Inconsistent level")
    query[level_field] = level
    query[qfiled] = conrey_index

@search_wrap(
    template="maass_search_results.html",
    table=db.maass_newforms,
    title="Maass forms search results",
    err_title="Maass forms search input error",
    shortcuts={"download": MaassFormDownloader()},
    projection=[
        "maass_id",
        "level",
        "weight",
        "conrey_index",
        "spectral_parameter",
        "symmetry",
        "fricke_eigenvalue",
    ],
    random_projection="maass_id",
    cleaners={
        "character_link": lambda v: character_link(v['level'],v['conrey_index']),
        "symmetry_pretty": lambda v: symmetry_pretty(v['symmetry']),
        "fricke_pretty": lambda v: fricke_pretty(v['fricke_eigenvalue']),
        "spectral_link": lambda v: '<a href="' + url_for('.by_label', label=v['maass_id']) + '">' + str(v['spectral_parameter']) + '</a>',
    },
    bread=lambda: bread_prefix() + [('Search results', '')],
    learnmore=learnmore_list,
    credit=lambda: credit_string,
    url_for_label=lambda label: url_for(".by_label", label=label),
)
def search(info, query):
    parse_ints(info, query, 'level', 'level')
    parse_ints(info, query, 'weight', 'weight')
    parse_character(info, query, 'character', 'conrey_index')
    parse_floats(info, query, 'spectral_parameter', 'spectral parameter', allow_singletons=True)
    if info.get('symmetry'):
        query['symmetry'] = int(info['symmetry'])
    query['__sort__'] = ['level', 'weight', 'conrey_index', 'spectral_parameter']

def parse_rows_cols(info):
    default = { 'rows': 20, 'cols': 5 }
    errs = []
    for v in ['rows','cols']:
        if info.get('edit_'+v):
            if not re.match(r"^[1-9][0-9]*$",info['edit_'+v]):
                flash_error ("%s is not a valid input for %s, it needs to be a positive integer.", info['edit_'+v], v)
            else:
                info[v] = int(info['edit_'+v])
        if not info.get(v):
            info[v] = default[v]

def search_by_label(label):
    try:
        mf =  WebMaassForm.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    info = to_dict(request.args)
    parse_rows_cols(info)
    return render_template("maass_form.html",
                           info=info,
                           mf=mf,
                           properties=mf.properties,
                           downloads=mf.downloads,
                           credit=credit_string,
                           bread=mf.bread,
                           learnmore=learnmore_list(),
                           title=mf.title,
                           friends=mf.friends,
                           KNOWL_ID="mf.maass.mwf.%s"%mf.label)
