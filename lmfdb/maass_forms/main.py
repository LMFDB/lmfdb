# -*- coding: utf-8 -*-

from lmfdb import db
from flask import render_template, request, url_for, redirect, abort
from lmfdb.maass_forms import maass_page #, logger
from lmfdb.utils import (
    flash_error, SearchArray, TextBox, SelectBox, CountBox, to_dict,
    parse_ints, parse_count, clean_input, rgbtohex, signtocolour)
from lmfdb.maass_forms.plot import paintSvgMaass
from lmfdb.maass_forms.web_maassform import WebMaassForm

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
    if request.args:
        return search(info)
    title = 'Maass forms'
    bread = [('Modular forms', url_for('modular_forms')), ('Maass', '')]
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
    bread = [('Modular forms', url_for('modular_forms')), ('Maass', url_for('.index')), ('Browse graph', '')]
    info['bread'] = bread
    info['learnmore'] = learnmore_list()

    return render_template("maass_browse_graph.html", title='Browsing Graph of Maass Forms', **info)


@maass_page.route('/Completeness')
def completeness_page():
    t = 'Completeness of Maass form data'
    bread = [('Modular forms', url_for('modular_forms')), ('Maass', url_for('.index')), ('Completeness','')]
    return render_template('single.html', kid='rcs.cande.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@maass_page.route('/Source')
def source_page():
    t = 'Source of Maass form data'
    bread = [('Modular forms', url_for('modular_forms')), ('Maass', url_for('.index')), ('Source','')]
    return render_template('single.html', kid='rcs.source.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@maass_page.route('/Reliability')
def reliability_page():
    t = 'Reliability of Maass form data'
    bread = [('Modular forms', url_for('modular_forms')),('Maass', url_for('.index')), ('Reliability','')]
    return render_template('single.html', kid='rcs.rigor.maass',
                           credit=credit_string, title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))


class MaassSearchArray(SearchArray):
    noun = "Maass form"
    plural_noun = "Maass forms"
    def __init__(self):       
        level = TextBox(name="level", label="Level", knowl="mf.maass.mwf.level", example="1", example_span="1 or 90-100")
        # weight = TextBox(name="weight", label="Weight", knowl="mf.maass.mwf.weight", example="0", example_span="0 or 0-3")
        # character = TextBox(name="character", label="Character", knowl="mf.maass.mwf.character", example="1.1", example_span="1.1 or 5.2")
        symmetry = SelectBox(name="symmetry", label="Symmetry",  knowl="mf.maass.mwf.symmetry", options=[("even", "1"), ("odd", "-1")])
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

def search(info):
    return redirect(url_for('.index'),307)

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
                           KNOWL_ID="mf.maass.mwf.%s"%mf.label)
