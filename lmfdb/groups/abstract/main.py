# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os

from flask import render_template, request, url_for, redirect #, send_file, abort
from sage.all import ZZ, latex #, Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, display_knowl,
    parse_ints, parse_bool, clean_input, 
    # parse_gap_id, parse_bracketed_posints, 
    search_wrap, web_latex)

from lmfdb.groups.abstract import abstract_page
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup)

credit_string = "Tim Dokchitser, John Jones, Kiran Kedlaya, Jen Paulhus, David Roberts,  David Roe, and Andrew Sutherland"

abstract_group_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))$')

def learnmore_list():
    return [ ('Completeness of the data', url_for(".completeness_page")),
             ('Source of the data', url_for(".how_computed_page")),
             ('Reliability of the data', url_for(".reliability_page")),
             ('Labeling convention', url_for(".labels_page")) ]

def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

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
        strng += ", " +  display_knowl('group.rational_group', "Rational")

    if gp.Zgroup:
        strng += ", " +  display_knowl('group.z_group', "Zgroup")

    if gp.Agroup:
        strng += ", " +  display_knowl('group.a_group', "Agroup")

    return strng


@abstract_page.route("/")
def index():
    bread = get_bread()
    if request.args:
        return group_search(request.args)
    info = {'count': 50,
            'order_list': ['1-10', '20-100', '101-200'],
            'nilp_list': range(1,5)
            }

    return render_template("abstract-index.html", title="Abstract Groups", bread=bread, info=info, learnmore=learnmore_list(), credit=credit_string)



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

def show_type(label):
    wag = WebAbstractGroup(label)
    if wag.abelian:
        return 'Abelian - '+str(len(wag.smith_abelian_invariants))
    if wag.nilpotent:
        return 'Nilpotent - '+str(wag.nilpotency_class)
    if wag.solvable:
        return 'Solvable - '+str(wag.derived_length)
    return 'General - ?'

#### Searching
def group_jump(info):
    return redirect(url_for('.by_label', label=info['jump']))

def group_download(info):
    t = 'Stub'
    bread = get_bread([("Jump", '')])
    return render_template("single.html", kid='rcs.groups.abstract.source',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'),
                           credit=credit_string)


@search_wrap(template="abstract-search.html",
             table=db.gps_groups,
             title='Abstract Group Search Results',
             err_title='Abstract Groups Search Input Error',
             shortcuts={'jump':group_jump,
                        'download':group_download},
             projection=['label','order','abelian','exponent','solvable',
                        'nilpotent','center_label','outer_order',
                        'nilpotency_class','number_conjugacy_classes'],
             #cleaners={"class": lambda v: class_from_curve_label(v["label"]),
             #          "equation_formatted": lambda v: list_to_min_eqn(literal_eval(v.pop("eqn"))),
             #          "st_group_link": lambda v: st_link_by_name(1,4,v.pop('st_group'))},
             bread=lambda:get_bread([('Search Results', '')]),
             learnmore=learnmore_list,
             credit=lambda:credit_string)
def group_search(info, query):
    info['group_url'] = get_url
    info['show_factor'] = lambda num: '$'+latex(ZZ(num).factor())+'$'
    info['getname'] = lambda label: '$'+WebAbstractGroup(label).tex_name+'$'
    info['show_type'] = show_type 
    parse_ints(info, query, 'order', 'order')
    parse_ints(info, query, 'exponent', 'exponent')
    parse_ints(info, query, 'nilpotency_class', 'nilpotency class')
    parse_ints(info, query, 'number_conjugacy_classes', 'number of conjugacy classes')
    parse_bool(info, query, 'abelian', 'is abelian')
    parse_bool(info, query, 'solvable', 'is solvable')
    parse_bool(info, query, 'nilpotent', 'is nilpotent')
    parse_bool(info, query, 'perfect', 'is perfect')

def get_url(label):
    return url_for(".by_label", label=label)

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
        info['dojs'] = 'make_sdiagram(document.getElementById("subdiagram"),'
        layers = gp.subgroup_layer_by_order
        info['dojs'] += str(layers[0]) + ',' + str(layers[1])
        info['dojs'] += ');'


        factored_order = web_latex(gp.order_factor(),False)
        aut_order = web_latex(gp.aut_order_factor(),False)

        title = 'Abstract Group '  + '$' + gp.tex_name + '$'

        prop2 = [
            ('Label', '\(%s\)' %  label), ('Order', '\(%s\)' % factored_order), ('#Aut(G)', '\(%s\)' % aut_order)
        ]

        bread = get_bread([(label, )])

#        downloads = [('Code to Magma', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
#                     ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]

        return render_template("abstract-show-group.html",
                               title=title, bread=bread, info=info,
                               properties2=prop2,
                               #friends=friends,
                               learnmore=learnmore_list(),
                               #downloads=downloads, 
                               credit=credit_string)





@abstract_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Abstract Groups Data'
    bread = get_bread([("Completeness", '')])
    return render_template("single.html", kid='rcs.groups.abstract.extent',
                            title=t, bread=bread,
                            learnmore=learnmore_list_remove('Complete'), 
                            credit=credit_string)


@abstract_page.route("/Labels")
def labels_page():
    t = 'Labels for Abstract Groups'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='rcs.groups.abstract.label',
                           learnmore=learnmore_list_remove('label'), 
                           title=t, bread=bread, credit=credit_string)


@abstract_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the Abstract Groups Data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.groups.abstract.reliability',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'), 
                           credit=credit_string)


@abstract_page.route("/Source")
def how_computed_page():
    t = 'Source of the Automorphisms of Curve Data'
    bread = get_bread([("Source", '')])
    return render_template("single.html", kid='rcs.groups.abstract.source',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'),
                           credit=credit_string)


