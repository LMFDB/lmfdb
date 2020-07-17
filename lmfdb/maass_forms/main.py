# -*- coding: utf-8 -*-
# This Blueprint is about Crystals
# Author: Anne Schilling (lead), Mike Hansen, Harald Schilly

from flask import render_template, request, url_for, make_response, redirect
from lmfdb.crystals import maass_page, logger
from lmfdb.utils import (
    flash_error, SearchArray, TextBox, SelectBox, CountBox, to_dict,
    parse_ints, parse_count, parse_start, clean_input)

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
    bread = [('Modular forms', 'Maass forms', '.')]
    return render_template('maass_browse.html', info=info, credit=credit_string, title=title, learnmore=learnmore_list(), bread=bread, dbcount=db.mwf_newforms.count())

@maass_page.route('/random')
def random():
    label = db.mwf_newforms.random()
    return redirect(url_for('.by_label', label=label), 307)

@maass_page.route('/<label>')
def by_label(label):
    return search_by_label(label)


class MaassSearchArray(SearchArray):
    noun = "Maass form"
    plural_noun = "Maass forms"
    def __init__(self):       
        level = TextBox(
            name="level",
            label="Level",
            knowl="mf.maass.mwf.level",
            example="1",
            example_span="1 or 90-100")
        weight = TextBox(
            name="weight",
            label="Weight",
            knowl="mf.maass.mwf.weight",
            example="0",
            example_span="0 or 0-3")
        character = TextBox(
            name="character",
            label="Character",
            knowl="mf.maass.mwf.character",
            example="1.1",
            example_span="1.1 or 5.2")
        symmetry = SelectBox(
            name="symmetry",
            label="Symmetry",
            knowl="mf.maass.mwf.symmetry",
            options=[("even", "1"),
                     ("odd", "-1")])
        eigenvalue = TextBox(
            name="eigenvalue",
            label="Spectral parameter",
            knowl="mf.maass.mwf.spectralparameter",
            example="1.0-1.1",
            example_span="1.0-1.1 or 90-100")
        count = CountBox()

        self.browse_array = [
            [level],
            [weight],
            [character],
            [symmetry],
            [eigenvalue],
            [count]]

        self.refine_array = [[level, weight, character, symmetry, eigenvalue, count]]
