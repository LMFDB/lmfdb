# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os

from flask import render_template, request, url_for, redirect #, send_file, abort
from sage.all import ZZ, latex #, Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error, to_dict, 
    SearchArray, TextBox, ExcludeOnlyBox, CountBox,
    parse_ints, parse_bool, clean_input, 
    # parse_gap_id, parse_bracketed_posints, 
    search_wrap, web_latex)
from lmfdb.utils.search_parsing import (search_parser, collapse_ors)
from lmfdb.groups.abstract import abstract_page
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup, WebAbstractSubgroup, group_names_pretty,
    group_pretty_image)

credit_string = "Michael Bush, Lewis Combes, Tim Dokchitser, John Jones, Kiran Kedlaya, Jen Paulhus, David Roberts,  David Roe, Manami Roy, Sam Schiavone, and Andrew Sutherland"

abstract_group_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))$')
abstract_subgroup_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))\.\d+$')

def learnmore_list():
    return [ ('Completeness of the data', url_for(".completeness_page")),
             ('Source of the data', url_for(".how_computed_page")),
             ('Reliability of the data', url_for(".reliability_page")),
             ('Labeling convention', url_for(".labels_page")) ]

def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def sub_label_is_valid(lab):
    return abstract_subgroup_label_regex.match(lab)

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
            strng += "," + display_knowl('group.cyclic', "Cyclic")
    else:
        strng = display_knowl('group.abelian', "non-Abelian")

    if gp.solvable:
        strng += ", " +  display_knowl('group.solvable', "Solvable")
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
    info = to_dict(request.args, search_array=GroupsSearchArray())
    if request.args:
        return group_search(info)
    info['count']= 50
    info['order_list']= ['1-10', '20-100', '101-200']
    info['nilp_list']= range(1,5)

    return render_template("abstract-index.html", title="Abstract groups", bread=bread, info=info, learnmore=learnmore_list(), credit=credit_string)



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
             title='Abstract group search results',
             err_title='Abstract groups search input error',
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

        # prepare for javascript call to make the diagram
        layers = gp.subgroup_layers
        ll = [[["%s"%str(grp.subgroup), grp.label, str(grp.subgroup_tex), grp.count, grp.subgroup_order, group_pretty_image(grp.subgroup)] for grp in layer] for layer in layers[0]]
        subs = gp.subgroups
        orders = list(set(sub.subgroup_order for sub in subs.values()))
        orders.sort()
        xcoords = list(sub.diagram_x for sub in subs.values())

        info['dojs'] = 'var sdiagram = make_sdiagram("subdiagram","%s",'% str(label)
        info['dojs'] += str(ll) + ',' + str(layers[1]) + ',' + str(orders)
        info['dojs'] += ',' + str(xcoords)
        info['dojs'] += ');'
        #print info['dojs']
        totsubs = len(gp.subgroups)
        info['wide'] = totsubs > (len(layers[0])-2)*4; # boolean


        factored_order = web_latex(gp.order_factor(),False)
        aut_order = web_latex(gp.aut_order_factor(),False)

        title = 'Abstract group '  + '$' + gp.tex_name + '$'

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

def make_knowl(title, knowlid):
    return '<a title="%s" knowl="%s">%s</a>'%(title, knowlid, title)

@abstract_page.route("/subinfo/<label>")
def shortsubinfo(label):
    if not sub_label_is_valid(label):
        # Should only come from code, so return nothing if label is bad
        return ''
    wsg = WebAbstractSubgroup(label)
    ambientlabel = str(wsg.ambient)
    # helper function
    def subinfo_getsub(title, knowlid, count):
        h = WebAbstractSubgroup("%s.%s"%(ambientlabel,str(count)))
        prop = make_knowl(title, knowlid)
        return '<tr><td>%s<td><span class="%s" data-sgid="%d">$%s$</span>\n' % (
            prop, h.spanclass(), h.label, h.subgroup_tex)

    ans = 'Information on subgroup <span class="%s" data-sgid="%d">$%s$</span><br>\n' % (wsg.spanclass(), wsg.label, wsg.subgroup_tex)
    ans += '<table>'
    ans += '<tr><td>%s <td> %s\n' % (
        make_knowl('Cyclic', 'group.cyclic'),wsg.cyclic)
    ans += '<tr><td>%s<td>' % make_knowl('Normal', 'group.subgroup.normal')
    if wsg.normal:
        ans += 'True with quotient group '
        ans +=  '$'+group_names_pretty(wsg.quotient)+'$\n'
    else:
        ans += 'False, and it has %d subgroups in its conjugacy class\n'% wsg.count
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Characteristic', 'group.characteristic_subgroup'), wsg.characteristic)

    h = WebAbstractSubgroup("%s.%s"%(ambientlabel,str(wsg.normalizer)))
    ans += subinfo_getsub('Normalizer', 'group.subgroup.normalizer',wsg.normalizer)
    ans += subinfo_getsub('Normal closure', 'group.subgroup.normal_closure', wsg.normal_closure)
    ans += subinfo_getsub('Centralizer', 'group.subgroup.centralizer', wsg.centralizer)
    ans += subinfo_getsub('Core', 'group.core', wsg.core)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Central', 'group.central'), wsg.central)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Hall', 'group.subgroup.hall'), wsg.hall>0)
    #ans += '<tr><td>Coset action <td>%s\n' % wsg.coset_action_label
    p = wsg.sylow
    nt = 'Yes for $p$ = %d' % p if p>0 else 'No'
    ans += '<tr><td>%s<td> %s'% (make_knowl('Sylow subgroup', 'group.sylow_subgroup'), nt)
    #print ""
    #print ans
    ans += '</table>'
    return ans


@abstract_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the abstract groups data'
    bread = get_bread([("Completeness", '')])
    return render_template("single.html", kid='rcs.groups.abstract.extent',
                            title=t, bread=bread,
                            learnmore=learnmore_list_remove('Complete'), 
                            credit=credit_string)


@abstract_page.route("/Labels")
def labels_page():
    t = 'Labels for abstract groups'
    bread = get_bread([("Labels", '')])
    return render_template("single.html", kid='rcs.groups.abstract.label',
                           learnmore=learnmore_list_remove('label'), 
                           title=t, bread=bread, credit=credit_string)


@abstract_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the abstract groups data'
    bread = get_bread([("Reliability", '')])
    return render_template("single.html", kid='rcs.groups.abstract.reliability',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'), 
                           credit=credit_string)


@abstract_page.route("/Source")
def how_computed_page():
    t = 'Source of the abstract group data'
    bread = get_bread([("Source", '')])
    return render_template("single.html", kid='rcs.groups.abstract.source',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'),
                           credit=credit_string)



class GroupsSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    jump_example = "[8,3]"
    jump_egspan = "e.g. [8,3] or [16,1]"
    def __init__(self):
        order = TextBox(
            name="order",
            label="Order",
            knowl="group.order",
            example="3",
            example_span="4, or a range like 3..5")
        exponent = TextBox(
            name="exponent",
            label="Exponent",
            knowl="group.exponent",
            example="2, 4, 6",
            example_span="list of integers?")
        nilpclass = TextBox(
            name="nilpotency_class",
            label="Nilpotency Class",
            knowl="group.nilpotent",
            example="3",
            example_span="4, or a range like 3..5")
        group = TextBox(
            name="group",
            label="Group identifier",
            knowl="group.small_group_label",
            example="[4,2]")
        abelian = ExcludeOnlyBox(
            name="abelian",
            label="Abelian",
            knowl="group.abelian")
        solvable = ExcludeOnlyBox(
            name="solvable",
            label="Solvable",
            knowl="group.solvable")
        nilpotent = ExcludeOnlyBox(
            name="nilpotent",
            label="Nilpotent",
            knowl="group.nilpotent")
        perfect = ExcludeOnlyBox(
            name="perfect",
            label="Perfect",
            knowl="group.perfect")
        count = CountBox()

        self.browse_array = [
            [order],
            [exponent],
            [nilpclass],
            [group],
            [abelian],
            [solvable],
            [nilpotent],
            [perfect],
            [count]]

        self.refine_array = [
            [order, exponent, nilpclass, group],
            [abelian, solvable, nilpotent, perfect]]

    sort_knowl = "group.sort_order"
    def sort_order(self, info):
        return [("", "order"),
                ("descorder", "order descending")]


