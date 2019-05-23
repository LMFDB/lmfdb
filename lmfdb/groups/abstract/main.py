# -*- coding: utf-8 -*-

import ast, os, re, StringIO, yaml

from flask import render_template, request, url_for, redirect, send_file, abort
from sage.all import Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, display_knowl,
    parse_ints, clean_input, parse_bracketed_posints, parse_gap_id,
    search_wrap, web_latex)

from lmfdb.groups.abstract import abstract_page
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup)

abstract_group_label_regex = re.compile(r'(\d+)\.(([a-z]+)|(\d+))$')

def label_is_valid(lab):
    return abstract_group_label_regex.match(lab)

def get_bread(breads=[]):
    bc = [("Groups", url_for(".index")),("Abstract", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

#function to create string of group characteristics
def create_boolean_string(gp):
    if gp.abelian:
        strng = display_knowl('group.abelian','Abelian')
        if gp.cyclic:
            strng += ", Cyclic"
    else:
        strng = display_knowl('group.abelian', "non-Abelian")

    if gp.solvable:
        strng += ", "+  display_knowl('group.solvable', "Solvable")
        if gp.supersolvable:
            strng += ", " + display_knowl('group.supersolvable', "Supersolvable")
    else:
        strng += ", " + display_knowl('group.solvable', "non-Solvable")

    if gp.nilpotent:
        strng += ", " + display_knowl('group.nilpotent', "Nilpotent")

    if gp.metacyclic:
        strng += ", " +  display_knowl('group.metacyclic', "Metacyclic")

    if gp.metabelian:
        strng += ", " +  display_knowl('group.metabelian', "Metabelian")

    if gp.simple:
        strng += ", " +  display_knowl('group.simple', "Simple")

    if gp.almost_simple:
        strng += ", " +  display_knowl('group.almost_simple', "Almost Simple")

    if gp.quasisimple:
        strng += ", " +  display_knowl('group.quasisimple', "Quasisimple")

    if gp.perfect:
        strng += ", " +  display_knowl('group.perfect', "Perfect")

    if gp.monomial:
        strng += ", " +  display_knowl('group.monomial', "Monomial")

    if gp.rational:
        strng += ", " +  display_knowl('group.rational', "Rational")

    if gp.Zgroup:
        strng += ", " +  display_knowl('group.zgroup', "Zgroup")

    if gp.Agroup:
        strng += ", " +  display_knowl('group.agroup', "Agroup")

    return strng


@abstract_page.route("/")
def index():
    bread = get_bread()
#    if request.args:
#        return abstract_search(request.args)
    info = {'count': 50,
            }

    learnmore = [ ('Completeness of the data', url_for(".completeness_page")),
                  ('Source of the data', url_for(".how_computed_page")),
                  ('Reliability of the data', url_for(".reliability_page")),
                ('Labeling convention', url_for(".labels_page")),
               ]

    return render_template("abstract-index.html", title="Abstract Groups", bread=bread, info=info, learnmore=learnmore)



@abstract_page.route("/random")
def random_abstract_group():
    label = db.gps_groups.random(projection='label')
    return redirect(url_for(".by_label", label=label))


@abstract_page.route("/<label>")
def by_label(label):
    if label_is_valid(label):
        return render_abstract_group({'label': label})
    else:
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
#Should this be "Bad label instead?"


#Search Setup
#def abstract_search(info, query):
#    parse_ints(info,query,'genus',name='Genus')
#    parse_ints(info,query,'dim',name='Dimension of the family')
#    parse_ints(info,query,'group_order', name='Group orders')
#    if 'inc_hyper' in info:
#        if info['inc_hyper'] == 'exclude':
#            query['hyperelliptic'] = False
#        elif info['inc_hyper'] == 'only':
#            query['hyperelliptic'] = True
#    info['group_display'] = sg_pretty
#    info['sign_display'] = sign_display

#Writes individual pages
def render_abstract_group(args):
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        gp = WebAbstractGroup(label)
        if gp.is_null():
            flash_error( "No group with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        #check if it fails to be a potential label even]


        info['boolean_characteristics_string']=create_boolean_string(gp)


        info['gpc'] = gp

        factored_order = web_latex(gp.order_factor(),False)
        aut_order = web_latex(gp.aut_order_factor(),False)

        title = 'Abstract Group '  + '$' + gp.tex_name + '$'

        prop2 = [
            ('Label', '\(%s\)' %  label), ('Order', '\(%s\)' % factored_order), ('#Aut(G)', '\(%s\)' % aut_order)
        ]

        bread = get_bread([(label, )])
        learnmore =[('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                    ('Reliability of the data', url_for(".reliability_page")),
                ('Labeling convention', url_for(".labels_page"))]

#        downloads = [('Code to Magma', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
#                     ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        return render_template("abstract-show-group.html",
                               title=title, bread=bread, info=info,
                               properties2=prop2,
                               #friends=friends,
                               learnmore=learnmore,)

                               #downloads=downloads, credit=credit)





@abstract_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Abstract Groups Data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Reliability of the data', url_for(".reliability_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='rcs.groups.abstract.extent',
                            title=t, bread=bread,learnmore=learnmore,) #credit=credit


@abstract_page.route("/Labels")
def labels_page():
    t = 'Label Scheme for the Data'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                 ('Source of the data', url_for(".how_computed_page")),
                ('Reliability of the data', url_for(".reliability_page"))]
    return render_template("single.html", kid='rcs.groups.abstract.label',
                           learnmore=learnmore, title=t, bread=bread,) #credit=credit)


@abstract_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the Abstract Groups Data'
    bread = get_bread([("Reliability", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                  ('Source of the data', url_for(".how_computed_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='rcs.groups.abstract.reliability',
                           title=t, bread=bread, learnmore=learnmore,) #credit=credit)


@abstract_page.route("/Source")
def how_computed_page():
    t = 'Source of the Automorphisms of Curve Data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                  ('Reliability of the data', url_for(".reliability_page")),
                ('Labeling convention', url_for(".labels_page"))]
    return render_template("single.html", kid='rcs.groups.abstract.source',
                           title=t, bread=bread, learnmore=learnmore,) #credit=credit)


