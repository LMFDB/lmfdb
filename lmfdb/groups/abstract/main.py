# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os
from collections import defaultdict

from flask import render_template, request, url_for, redirect, Markup, make_response #, send_file, abort
from sage.all import ZZ, latex #, Permutation

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    flash_error, to_dict, display_knowl, sparse_cyclotomic_to_latex,
    SearchArray, TextBox, ExcludeOnlyBox, CountBox, YesNoBox, comma,
    parse_ints, parse_bool, clean_input,
    # parse_gap_id, parse_bracketed_posints,
    search_wrap, web_latex)
from lmfdb.utils.search_parsing import (search_parser, collapse_ors)
from lmfdb.groups.abstract import abstract_page, abstract_logger
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup, WebAbstractSubgroup, WebAbstractConjClass,
    WebAbstractRationalCharacter, WebAbstractCharacter,
    group_names_pretty, group_pretty_image)
from lmfdb.number_fields.web_number_field import formatfield

credit_string = "Michael Bush, Lewis Combes, Tim Dokchitser, John Jones, Kiran Kedlaya, Jen Paulhus, David Roberts,  David Roe, Manami Roy, Sam Schiavone, and Andrew Sutherland"

abstract_group_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))$')
abstract_subgroup_label_regex = re.compile(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)\.\d+$')

ngroups = None
max_order = None
init_absgrp_flag = False

def init_grp_count():
    global ngroups, init_absgrp_flag, max_order
    if not init_absgrp_flag or True : # Always recalculate for now
        ngroups = db.gps_groups.count()
        max_order = db.gps_groups.max('order')
        init_absgrp_flag = True

# For dynamic knowls
@app.context_processor
def ctx_abstract_groups():
    return {'cc_data': cc_data,
            'sub_data': sub_data,
            'rchar_data': rchar_data,
            'cchar_data': cchar_data,
            'abstract_group_summary': abstract_group_summary,
            'dyn_gen': dyn_gen}

def abstract_group_summary():
    init_grp_count()
    return r'This database contains {} <a title="group" knowl="group">groups</a> of <a title="order" knowl="group.order">order</a> $n\leq {}$.  <p>This portion of the LMFDB is in alpha status.  The data is not claimed to be complete, and may grow or shrink at any time.'.format(comma(ngroups),max_order)

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
def create_boolean_string(gp, short_string=False):
    if gp.abelian:
        strng = display_knowl('group.abelian','Abelian')
        if gp.cyclic:
            strng += ", " + display_knowl('group.cyclic', "Cyclic")
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

    if short_string:
        return strng

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



def url_for_label(label):
    if label == "random":
        return url_for(".random_abstract_group")
    return url_for("abstract.by_label", label=label)

#def url_for_subgroup_label(label):
#    if label == "random":
#        return url_for(".random_abstract_subgroup")
#    return url_for("abstract.by_subgroup_label", label=label)

@abstract_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=GroupsSearchArray())
    if request.args:
        info['search_type'] = search_type = info.get('search_type', info.get('hst', 'List'))
        if search_type in ['List', 'Random']:
            return group_search(info)
        elif search_type in ['Subgroups', 'RandomSubgroup']:
            return subgroup_search(info)
    info['count']= 50
    info['order_list']= ['1-10', '20-100', '101-200']
    info['nilp_list']= range(1,5)
    info['maxgrp']= db.gps_groups.max('order')

    return render_template("abstract-index.html", title="Abstract groups", bread=bread, info=info, learnmore=learnmore_list(), credit=credit_string)



@abstract_page.route("/random")
def random_abstract_group():
    label = db.gps_groups.random(projection='label')
    response = make_response(redirect(url_for(".by_label", label=label), 307))
    response.headers['Cache-Control'] = 'no-cache, no-store'
    return response



@abstract_page.route("/<label>")
def by_label(label):
    if label_is_valid(label):
        return render_abstract_group({'label': label})
    else:
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
#Should this be "Bad label instead?"

#@abstract_page.route("/sub/<label>")
#def by_subgroup_label(label):
#    if subgroup_label_is_valid(label):
#        return render_abstract_subgroup({'label': label})

def show_type(label):
    wag = WebAbstractGroup(label)
    if wag.abelian:
        return 'Abelian - '+str(len(wag.smith_abelian_invariants))
    if wag.nilpotent:
        return 'Nilpotent - '+str(wag.nilpotency_class)
    if wag.solvable:
        return 'Solvable - '+str(wag.derived_length)
    return 'Non-Solvable - '+str(wag.composition_length)

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
             credit=lambda:credit_string,
             url_for_label=url_for_label)
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
    parse_bool(info, query, 'cyclic', 'is cyclic')
    parse_bool(info, query, 'solvable', 'is solvable')
    parse_bool(info, query, 'nilpotent', 'is nilpotent')
    parse_bool(info, query, 'perfect', 'is perfect')

@search_wrap(template="subgroup-search.html",
             table=db.gps_subgroups,
             title='Subgroup search results',
             err_title='Subgroup search input error',
             projection=['label', 'cyclic', 'abelian', 'solvable',
                         'cyclic_quotient', 'abelian_quotient', 'solvable_quotient',
                         'normal', 'characteristic', 'perfect', 'maximal', 'minimal_normal',
                         'central', 'direct', 'semidirect', 'hall', 'sylow',
                         'subgroup_order', 'ambient_order', 'quotient_order',
                         'subgroup', 'ambient', 'quotient',
                         'subgroup_tex', 'ambient_tex', 'quotient_tex'],
             bread=lambda:get_bread([('Search Results', '')]),
             learnmore=learnmore_list,
             credit=lambda:credit_string)
def subgroup_search(info, query):
    parse_ints(info, query, 'subgroup_order')
    parse_ints(info, query, 'ambient_order')
    parse_ints(info, query, 'quotient_order', 'subgroup index')
    parse_bool(info, query, 'abelian')
    parse_bool(info, query, 'cyclic')
    parse_bool(info, query, 'solvable')
    parse_bool(info, query, 'abelian_quotient')
    parse_bool(info, query, 'cyclic_quotient')
    parse_bool(info, query, 'solvable_quotient')
    parse_bool(info, query, 'perfect')
    parse_bool(info, query, 'normal')
    parse_bool(info, query, 'characteristic')
    parse_bool(info, query, 'maximal')
    parse_bool(info, query, 'minimal_normal')
    parse_bool(info, query, 'central')
    parse_bool(info, query, 'semidirect')
    parse_bool(info, query, 'direct')
    parse_bool(info, query, 'hall')
    parse_bool(info, query, 'sylow')
    parse_bool(info, query, '')

def get_url(label):
    return url_for(".by_label", label=label)

#Writes individual pages
def render_abstract_group(args):
    abstract_logger.info("A")
    info = {}
    if 'label' in args:
        label = clean_input(args['label'])
        gp = WebAbstractGroup(label)
        if gp.is_null():
            flash_error( "No group with label %s was found in the database.", label)
            return redirect(url_for(".index"))
        #check if it fails to be a potential label even

        info['boolean_characteristics_string']=create_boolean_string(gp)

        info['gpc'] = gp

        # prepare for javascript call to make the diagram
        if gp.diagram_ok:
            layers = gp.subgroup_layers
            ll = [[["%s"%str(grp.subgroup), grp.label, str(grp.subgroup_tex), grp.count, grp.subgroup_order, group_pretty_image(grp.subgroup), grp.diagram_x] for grp in layer] for layer in layers[0]]
            subs = gp.subgroups
            orders = list(set(sub.subgroup_order for sub in subs.values()))
            orders.sort()

            info['dojs'] = 'var sdiagram = make_sdiagram("subdiagram","%s",'% str(label)
            info['dojs'] += str(ll) + ',' + str(layers[1]) + ',' + str(orders)
            info['dojs'] += ');'
            #print info['dojs']
            totsubs = len(gp.subgroups)
            info['wide'] = (totsubs-2) > (len(layers[0])-2)*4; # boolean
        else:
            prof = list(gp.subgroup_profile.items())
            info['subgroup_profile'] = [(z[0], display_profile_line(z[1])) for z in prof]
            info['dojs'] = ''

        abstract_logger.info("B0")
        factored_order = web_latex(gp.order_factor(), False)
        abstract_logger.info("B1")
        aut_order = web_latex(gp.aut_order_factor(), False)
        abstract_logger.info("B2")
        out_order = web_latex(gp.out_order_factor(), False)
        abstract_logger.info("B3")
        z_order = web_latex(gp.cent_order_factor(), False)
        abstract_logger.info("B4")
        Gab_order = web_latex(gp.Gab_order_factor(), False)

        abstract_logger.info("C1")
        info['sparse_cyclotomic_to_latex'] = sparse_cyclotomic_to_latex
        info['ccdata'] = gp.conjugacy_classes
        abstract_logger.info("C2")
        info['chardata'] = gp.characters
        abstract_logger.info("C3")
        info['qchardata'] = gp.rational_characters
        abstract_logger.info("C4")
        ccdivs = gp.conjugacy_class_divisions
        abstract_logger.info("C5")
        ccdivs = [{'label': k, 'classes': ccdivs[k]} for k in ccdivs.keys()]
        ccdivs.sort(key=lambda x: x['classes'][0].counter)
        info['ccdivisions'] = ccdivs
        info['ccdisplayknowl'] = cc_display_knowl
        info['chtrdisplayknowl'] = char_display_knowl
        # Need to map cc's to their divisions
        ctor = {}
        for k in ccdivs:
            for v in k['classes']:
                ctor[v.label] = k['label']
        info['ctor'] = ctor
        abstract_logger.info("D0")

        s = r",\ "

        def sortkey(x):
            if x[0] is None:
                return (0, 0)
            return tuple(int(m) for m in x[0].split("."))
        def show_cnt(x, cnt):
            if cnt == 1:
                return x
            else:
                return x + " (%s)" % cnt
        max_subs = defaultdict(lambda: defaultdict(int))
        for sup in gp.maximal_subgroup_of:
            if sup.normal:
                max_subs[sup.ambient, sup.ambient_tex, sup.ambient_order][sup.quotient, sup.quotient_tex] += 1
            else:
                max_subs[sup.ambient, sup.ambient_tex, sup.ambient_order][None, None] += 1
        max_subs = [A + (", ".join(
            show_cnt("Non-normal" if quo is None else '<a href="%s">$%s$</a>' % (quo, quo_tex),
                     max_subs[A][quo, quo_tex])
            for (quo, quo_tex) in sorted(max_subs[A], key=sortkey)),)
                    for A in sorted(max_subs, key=sortkey)]
        abstract_logger.info("D1")
        max_quot = defaultdict(lambda: defaultdict(int))
        for sup in gp.maximal_quotient_of:
            print(sup.ambient, sup.ambient_tex, sup.ambient_order)
            max_quot[sup.ambient, sup.ambient_tex, sup.ambient_order][sup.subgroup, sup.subgroup_tex] += 1
        print("LEN", len(max_quot))
        max_quot = [A + (", ".join(
            show_cnt('<a href="%s">$%s$</a>' % (sub, sub_tex),
                     max_quot[A][sub, sub_tex])
            for (sub, sub_tex) in sorted(max_quot[A], key=sortkey)),)
                    for A in sorted(max_quot, key=sortkey)]
        abstract_logger.info("D2")
        info['max_subs'] = max_subs
        info['max_quot'] = max_quot

        title = 'Abstract group '  + '$' + gp.tex_name + '$'

        properties = [
            ('Label', label),
            ('Order', '$%s$' % factored_order),
            #('#$\operatorname{Aut}(G)$', '$%s$' % aut_order),
            #('#$\operatorname{Out}(G)$', '$%s$' % out_order),
            #('#$Z(G)$', '$%s$' % z_order),
            #(r'#$G^{\mathrm{ab}}$', '$%s$' % Gab_order),
        ]

        bread = get_bread([(label, )])

#        downloads = [('Code to Magma', url_for(".hgcwa_code_download",  label=label, download_type='magma')),
#                     ('Code to Gap', url_for(".hgcwa_code_download", label=label, download_type='gap'))]
        abstract_logger.info("Z")

        return render_template("abstract-show-group.html",
                               title=title, bread=bread, info=info,
                               properties=properties,
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
    def subinfo_getsub(title, knowlid, lab):
        h = WebAbstractSubgroup(lab)
        prop = make_knowl(title, knowlid)
        return '<tr><td>%s<td>%s\n' % (
            prop, h.make_span())

    ans = 'Information on subgroup <span class="%s" data-sgid="%s">$%s$</span><br>\n' % (wsg.spanclass(), wsg.label, wsg.subgroup_tex)
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

    h = WebAbstractSubgroup(str(wsg.normalizer))
    ans += subinfo_getsub('Normalizer', 'group.subgroup.normalizer',wsg.normalizer)
    ans += subinfo_getsub('Normal closure', 'group.subgroup.normal_closure', wsg.normal_closure)
    ans += subinfo_getsub('Centralizer', 'group.subgroup.centralizer', wsg.centralizer)
    ans += subinfo_getsub('Core', 'group.core', wsg.core)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Central', 'group.central'), wsg.central)
    ans += '<tr><td>%s <td>%s\n' % (make_knowl('Hall', 'group.subgroup.hall'), wsg.hall>0)
    #ans += '<tr><td>Coset action <td>%s\n' % wsg.coset_action_label
    p = wsg.sylow
    nt = 'Yes for $p$ = %d' % p if p>1 else 'No'
    ans += '<tr><td>%s<td> %s'% (make_knowl('Sylow subgroup', 'group.sylow_subgroup'), nt)
    ans += '<tr><td><td style="text-align: right"><a href="%s">$%s$ home page</a>' % (url_for_label(wsg.subgroup), wsg.subgroup_tex)
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

def display_profile_line(data):
    datad = dict(data)
    l = []
    for ky in sorted(datad, key=datad.get, reverse=True):
        l.append(group_display_knowl(ky, pretty=True)+ (' x '+str(datad[ky]) if datad[ky]>1 else '' ))
    return ', '.join(l)

class GroupsSearchArray(SearchArray):
    noun = "group"
    plural_noun = "groups"
    jump_example = "8.3"
    jump_egspan = "e.g. 8.3 or 16.1"
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
        abelian = YesNoBox(
            name="abelian",
            label="Abelian",
            knowl="group.abelian")
        cyclic = YesNoBox(
            name="cyclic",
            label="Cyclic",
            knowl="group.cyclic")
        solvable = YesNoBox(
            name="solvable",
            label="Solvable",
            knowl="group.solvable")
        nilpotent = YesNoBox(
            name="nilpotent",
            label="Nilpotent",
            knowl="group.nilpotent")
        perfect = YesNoBox(
            name="perfect",
            label="Perfect",
            knowl="group.perfect")
        count = CountBox()

        self.browse_array = [
            [order],
            [exponent],
            [nilpclass],
            [abelian],
            [cyclic],
            [solvable],
            [nilpotent],
            [perfect],
            [count]]

        self.refine_array = [
            [order, exponent, nilpclass],
            [abelian,cyclic,solvable, nilpotent, perfect]]

    sort_knowl = "group.sort_order"
    def sort_order(self, info):
        return [("", "order"),
                ("descorder", "order descending")]

class SubgroupSearchArray(SearchArray):
    def __init__(self):
        abelian = YesNoBox(
            name="abelian",
            label="Abelian",
            knowl="group.abelian")
        cyclic = YesNoBox(
            name="cyclic",
            label="Cyclic",
            knowl="group.cyclic")
        solvable = YesNoBox(
            name="solvable",
            label="Solvable",
            knowl="group.solvable")
        abelian_quotient = YesNoBox(
            name="abelian_quotient",
            label="Abelian quotient",
            knowl="group.abelian")
        cyclic_quotient = YesNoBox(
            name="cyclic_quotient",
            label="Cyclic quotient",
            knowl="group.cyclic")
        solvable_quotient = YesNoBox(
            name="solvable_quotient",
            label="Solvable quotient",
            knowl="group.solvable")
        perfect = YesNoBox(
            name="perfect",
            label="Perfect",
            knowl="group.perfect")
        normal = YesNoBox(
            name="normal",
            label="Normal",
            knowl="group.subgroup.normal")
        characteristic = YesNoBox(
            name="characteristic",
            label="Characteristic",
            knowl="group.characteristic_subgroup")
        maximal = YesNoBox(
            name="maximal",
            label="Maximal",
            knowl="group.maximal_subgroup")
        minimal_normal = YesNoBox(
            name="minimal_normal",
            label="Maximal quotient",
            knowl="group.maximal_quotient")
        central = YesNoBox(
            name="central",
            label="Central",
            knowl="group.central")
        direct = YesNoBox(
            name="direct",
            label="Direct product",
            knowl="group.direct_product")
        semidirect = YesNoBox(
            name="semidirect",
            label="Semidirect product",
            knowl="group.semidirect_product")
        #stem = YesNoBox(
        #    name="stem",
        #    label="Stem",
        #    knowl="group.stem")
        hall = YesNoBox(
            name="hall",
            label="Hall subgroup",
            knowl="group.subgroup.hall")
        sylow = YesNoBox(
            name="sylow",
            label="Sylow subgroup",
            knowl="group.sylow_subgroup")
        subgroup = TextBox(
            name="subgroup",
            label="Subgroup label",
            knowl="group.subgroup_isolabel",
            example="8.4")
        quotient = TextBox(
            name="quotient",
            label="Quotient label",
            knowl="group.quotient_isolabel",
            example="16.5")
        ambient = TextBox(
            name="ambient",
            label="Ambient label",
            knowl="group.ambient_isolabel",
            example="128.207")
        subgroup_order = TextBox(
            name="subgroup_order",
            label="Subgroup Order",
            knowl="group.order",
            example="3",
            example_span="4, or a range like 3..5")
        quotient_order = TextBox(
            name="quotient_order",
            label="Subgroup Index",
            knowl="group.subgroup.index",
            example="4")
        ambient_order = TextBox(
            name="ambient_order",
            label="Ambient Order",
            knowl="group.order",
            example="24")

        self.refine_array = [
            [cyclic, abelian, solvable, cyclic_quotient, abelian_quotient, solvable_quotient],
            [normal, characteristic, perfect, maximal, minimal_normal, central],
            [direct, semidirect, hall, sylow],
            [subgroup_order, ambient_order, subgroup_index, subgroup, ambient, quotient]]

def cc_display_knowl(gp, label, typ, name=None):
    if not name:
        name = 'Conjugacy class {}'.format(label)
    return '<a title = "{} [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=cc_data&args={}%7C{}%7C{}">{}</a>'.format(name, gp, label, typ, name)

def group_display_knowl(label, name=None, pretty=False):
    if pretty:
        name = '$'+group_names_pretty(label)+'$'
    if not name:
        name = 'Group {}'.format(label)
    return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args=%s&func=group_data">%s</a>' % (name, label, name)

def sub_display_knowl(label, name=None):
    if not name:
        name = 'Subgroup {}'.format(label)
    return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="args=%s&func=sub_data">%s</a>' % (name, label, name)

def char_display_knowl(label, field, name=None):
    if field=='C':
        fname='cchar_data'
    else:
        fname='rchar_data'
    if not name:
        name = 'Character {}'.format(label)
    return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=%s&args=%s">%s</a>' % (name, fname, label, name)

#def crep_display_knowl(label, name=None):
#    if not name:
#        name = 'Subgoup {}'.format(label)
#    return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=crep_data&args=%s">%s</a>' % (name, label, name)
#
#def qrep_display_knowl(label, name=None):
#    if not name:
#        name = 'Subgoup {}'.format(label)
#    return '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=qrep_data&args=%s">%s</a>' % (name, label, name)

def cc_data(gp,label,typ='complex'):
    if typ=='rational':
        wag = WebAbstractGroup(gp)
        rcc = wag.conjugacy_class_divisions
        if not rcc:
            return 'Data for conjugacy class {} not found.'.format(label)
        classes = rcc[label]
        wacc = classes[0]
        mult = len(classes)
        ans = '<h3>Rational conjugacy class {}</h3>'.format(label)
        if mult > 1:
            ans +='<br>Rational class is a union of {} conjugacy classes'.format(mult)
            ans += '<br>Total size of class: {}'.format(wacc.size*mult)
        else:
            ans += '<br>Rational class is a single conjugacy class'
            ans += '<br>Size of class: {}'.format(wacc.size)
    else:
        wacc = WebAbstractConjClass(gp,label)
        if not wacc:
            return 'Data for conjugacy class {} not found.'.format(label)
        ans = '<h3>Conjugacy class {}</h3>'.format(label)
        ans += '<br>Size of class: {}'.format(wacc.size)
    ans += '<br>Order of elements: {}'.format(wacc.order)
    centralizer = wacc.centralizer
    wcent = WebAbstractSubgroup(centralizer)
    ans += '<br>Centralizer: {}'.format(sub_display_knowl(centralizer,'$'+wcent.subgroup_tex+'$'))
    return Markup(ans)

def rchar_data(label):
  mychar = WebAbstractRationalCharacter(label)
  ans = '<h3>Rational character {}</h3>'.format(label)
  ans += '<br>Degree: {}'.format(mychar.qdim)
  if mychar.faithful:
    ans += '<br>Faithful character'
  else:
    ans += '<br>Not faithful'
  ans += '<br>Multiplicity: {}'.format(mychar.multiplicity)
  ans += '<br>Schur index: {}'.format(mychar.schur_index)
  nt = mychar.nt
  ans += '<br>Smallest container: {}T{}'.format(nt[0],nt[1])
  if 'image' in mychar._data:
    txt = "Image"
    if mychar.schur_index > 1:
      txt = r'Image of ${}\ *\ ${}'.format(mychar.schur_index, label)
    ans += '<br>{}: <a href="{}">{}</a>'.format(txt, url_for('glnQ.by_label', label=mychar.image), mychar.image)
  else:
      ans += '<br>Image: not computed'
  return Markup(ans)

def cchar_data(label):
  mychar = WebAbstractCharacter(label)
  ans = '<h3>Complex character {}</h3>'.format(label)
  ans += '<br>Degree: {}'.format(mychar.dim)
  if mychar.faithful:
    ans += '<br>Faithful character'
  else:
    ker = WebAbstractSubgroup(mychar.kernel)
    ans += '<br>Not faithful with kernel {}'.format(sub_display_knowl(ker.label,"$"+ker.subgroup_tex+'$'))
  nt = mychar.nt
  ans += '<br>Frobenius-Schur indicator: {}'.format(mychar.indicator)
  ans += '<br>Smallest container: {}T{}'.format(nt[0],nt[1])
  ans += '<br>Field of character values: {}'.format(formatfield(mychar.field))
  if 'image' in mychar._data:
    ans += '<br>Image: <a href="{}">{}</a>'.format(url_for('glnC.by_label', label=mychar.image), mychar.image)
  else:
      ans += '<br>Image: not computed'
  return Markup(ans)

def sub_data(label):
  return Markup(shortsubinfo(label))

def group_data(label):
  gp = WebAbstractGroup(label)
  ans = 'Group ${}$: '.format(gp.tex_name)
  ans += create_boolean_string(gp, short_string=True)
  ans += '<br />Order: {}<br />'.format(gp.order)
  ans += 'Gap small group number: {}<br />'.format(gp.counter)
  ans += 'Exponent: {}<br />'.format(gp.exponent)

  ans += 'There are {} subgroups'.format(gp.number_subgroups)
  if gp.number_normal_subgroups < gp.number_subgroups:
    ans += ' in {} conjugacy classes, {} normal, '.format(gp.number_subgroup_classes, gp.number_normal_subgroups)
  else:
    ans += ', all normal, '
  if gp.number_characteristic_subgroups < gp.number_normal_subgroups:
    ans += str(gp.number_characteristic_subgroups)
  else:
    ans += 'all'
  ans += ' characteristic.<br />'
  ans += '<div align="right"><a href="{}">{} home page</a></div>'.format(url_for('abstract.by_label',label=label), label)
  return Markup(ans)

def dyn_gen(f,args):
    r"""
    Called from the generic dynamic knowl.
    f is the name of a function to call, which has to be in flist, which
      is at the bottom of this file
    args is a string with the arguments, which are concatenated together
      with %7C, which is the encoding of the pipe symbol
    """
    func = flist[f]
    arglist = args.split('|')
    return func(*arglist)

#list if legal dynamic knowl functions
flist= {'cc_data': cc_data,
        'sub_data': sub_data,
        'rchar_data': rchar_data,
        'cchar_data': cchar_data,
        'group_data': group_data}

