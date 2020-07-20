# -*- coding: utf-8 -*-

from lmfdb import db
from flask import render_template, request, url_for, redirect, abort
from lmfdb.maass_forms import maass_page #, logger
from lmfdb.utils import (
    SearchArray, search_wrap, TextBox, SelectBox, CountBox, to_dict,
    parse_ints, parse_ints, parse_floats, rgbtohex, signtocolour)
from lmfdb.maass_forms.plot import paintSvgMaass
from lmfdb.maass_forms.web_maassform import WebMaassForm, MaassFormDownloader, character_link, symmetry_pretty

bread_prefix = [('Modular forms', url_for('modular_forms')),('Maass', url_for('.index'))]

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
    bread = bread_prefix
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
    info={}
    info['level'] = level
    return search(info)

@maass_page.route("/<int:level>/<int:weight>/")
def by_level_weight(level, weight):
    info={}
    info['level'] = level
    info['weight'] = weight
    return search(info)

@maass_page.route("/<int:level>/<int:weight>/<int:conrey_index>/")
def by_level_weight_character(level, weight, conrey_index):
    info={}
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
    bread = bread_prefix + [('Browse graph', '')]
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
    bread = bread_prefix + [('Completeness','')]
    return render_template('single.html', kid='rcs.cande.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@maass_page.route('/Source')
def source_page():
    t = 'Source of Maass form data'
    bread = bread_prefix + [('Source','')]
    return render_template('single.html', kid='rcs.source.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@maass_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Maass form data'
    bread = bread_prefix + [('Reliability','')]
    return render_template('single.html', kid='rcs.rigor.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

class MaassSearchArray(SearchArray):
    noun = "Maass form"
    plural_noun = "Maass forms"
    def __init__(self):       
        level = TextBox(name="level", label="Level", knowl="mf.maass.mwf.level", example="1", example_span="1 or 90-100")
        # weight = TextBox(name="weight", label="Weight", knowl="mf.maass.mwf.weight", example="0", example_span="0 or 0-3")
        # character = TextBox(name="character", label="Character", knowl="mf.maass.mwf.character", example="1.1", example_span="1.1 or 5.2")
        symmetry = SelectBox(name="symmetry", label="Symmetry",  knowl="mf.maass.mwf.symmetry", options=[("0", "any symmetry"), ("1", "even only"), ("-1", "odd only")])
        spectral_parameter = TextBox(name="spectral_parameter",
                                     label="Spectral parameter",
                                     knowl="mf.maass.mwf.spectralparameter",
                                     example="1.0-1.1",
                                     example_span="1.0-1.1 or 90-100")
        count = CountBox()

        self.browse_array = [
            [level],
            #[weight],
            #[character],
            [spectral_parameter],
            [symmetry],
            [count]]

        #self.refine_array = [[level, weight, character, spectral_parameter, symmetry]]
        self.refine_array = [[level, spectral_parameter, symmetry]]

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
    cleaners={
        "character_link": lambda v: character_link(v['level'],v['conrey_index']),
        "symmetry_pretty": lambda v: symmetry_pretty(v['symmetry']),
        "spectral_link": lambda v: '<a href="' + url_for('.by_label', label=v['maass_id']) + '>' + str(v['spectral_parameter']) + '</a>',
    },
    bread=lambda: bread_prefix + [('Search results', '')],
    learnmore=learnmore_list,
    credit=lambda: credit_string,
)
def search(info, query):
    parse_ints(info, query, 'level', 'level')
    parse_floats(info.query, 'spectral_paramter', 'spectral parameter', allow_singletons=True)
    if info.get('symmetry'):
        query['symmetry'] = int(info['symmetry'])
    if info.get('conrey_index'):
        parse_ints(info, query, 'conrey_index', 'Conrey index')

def search_by_label(label):
    try:
        mf =  WebMaassForm.by_label(label)
    except (KeyError,ValueError) as err:
        return abort(404,err.args)
    return render_template("maass_form.html",
                           properties=mf.properties,
                           credit=credit_string,
                           mf=mf,
                           bread=mf.bread,
                           learnmore=learnmore_list(),
                           title=mf.title,
                           friends=mf.friends,
                           downloads=mf.downloads,
                           KNOWL_ID="mf.maass.mwf.%s"%mf.label)
