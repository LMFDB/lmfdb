# -*- coding: utf-8 -*-

import re #, StringIO, yaml, ast, os

import time
from six import BytesIO
from collections import defaultdict, Counter

from flask import render_template, request, url_for, redirect, Markup, make_response, send_file #, abort
from string import ascii_lowercase
from sage.all import ZZ, latex, factor, Permutations

from lmfdb import db
from lmfdb.app import app
from lmfdb.utils import (
    flash_error, to_dict, display_knowl,
    SearchArray, TextBox, ExcludeOnlyBox, CountBox, YesNoBox, comma,
    parse_ints, parse_bool, clean_input, parse_regex_restricted,
    dispZmat, dispcyclomat,
    search_wrap, web_latex)
from lmfdb.utils.search_parsing import (search_parser, collapse_ors, parse_multiset)
from lmfdb.groups.abstract import abstract_page, abstract_logger
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup, WebAbstractSubgroup, WebAbstractConjClass,
    WebAbstractRationalCharacter, WebAbstractCharacter,
    group_names_pretty, group_pretty_image)
from lmfdb.number_fields.web_number_field import formatfield

credit_string = "Michael Bush, Lewis Combes, Tim Dokchitser, John Jones, Kiran Kedlaya, Jen Paulhus, David Roberts,  David Roe, Manami Roy, Sam Schiavone, and Andrew Sutherland"

abstract_group_label_regex = re.compile(r'^(\d+)\.(([a-z]+)|(\d+))$')
abstract_subgroup_label_regex = re.compile(r'^(\d+)\.(\d+)\.(\d+)\.(\d+)\.\d+$')
#order_stats_regex = re.compile(r'^(\d+)(\^(\d+))?(,(\d+)\^(\d+))*')

ngroups = None
max_order = None
init_absgrp_flag = False

def yesno(val):
    if val:
        return 'yes'
    return 'no'

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
    return [ ('Source and acknowledgements', url_for(".how_computed_page")),
             ('Completeness of the data', url_for(".completeness_page")),
             ('Reliability of the data', url_for(".reliability_page")),
             ('Abstract  group labeling', url_for(".labels_page")) ]

def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def subgroup_label_is_valid(lab):
    return abstract_subgroup_label_regex.match(lab)

def label_is_valid(lab):
    return abstract_group_label_regex.match(lab)

#def get_bread(breads=[]):
#    bc = [("Groups", url_for(".index")),("Abstract", url_for(".index"))]
#    for b in breads:
#        bc.append(b)
#    return bc

def get_bread(tail=[]):
    base = [("Groups", url_for(".index")), ('Abstract', url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail



#function to create string of group characteristics
def create_boolean_string(gp, short_string=False):
    cyclic_str = display_knowl('group.cyclic', 'cyclic') 
    abelian_str = display_knowl('group.abelian','abelian')
    nonabelian_str =  display_knowl('group.abelian', "nonabelian")
    nilpotent_str = display_knowl('group.nilpotent', "nilpotent")
    supersolvable_str = display_knowl('group.supersolvable', "supersolvable")
    monomial_str = display_knowl('group.monomial', "monomial")
    solvable_str = display_knowl('group.solvable', "solvable")
    nonsolvable_str = display_knowl('group.solvable', "nonsolvable")
    zgroup_str = display_knowl('group.z_group', "Z-group")
    agroup_str = display_knowl('group.a_group', "A-group")
    metacyclic_str = display_knowl('group.metacyclic', "metacyclic")
    metabelian_str = display_knowl('group.metabelian', "metabelian")
    quasisimple_str = display_knowl('group.quasisimple', "quasisimple")
    almostsimple_str = display_knowl('group.almost_simple', "almost simple")
    simple_str = display_knowl('group.simple', "simple")
    perfect_str = display_knowl('group.perfect', "perfect")
    rational_str= display_knowl('group.rational_group', "rational")

    hence_str = display_knowl('group.properties_interdependencies', 'hence')


    if short_string:
        if gp.cyclic:
            if gp.simple:
                strng = cyclic_str + ", " +  solvable_str + ", and " + simple_str
            else:
                strng = cyclic_str + " and " + solvable_str

        elif gp.abelian:
            strng = abelian_str + " and " + solvable_str

        else:
            strng = nonabelian_str
            if gp.solvable:
                strng+= " and " + solvable_str
            else:
                strng+= " and " + nonsolvable_str

            if gp.perfect:
                strng+= " and " + perfect_str
    else:           

    #nilpotent implies supersolvable for finite groups
    #supersolvable imples monomial for finite groups
    #Zgroup implies metacyclic for finite groups
    
        if gp.cyclic:
            if gp.rational:
                strng = "This group is " + cyclic_str + " (" + hence_str + " " + abelian_str + ", " + nilpotent_str + ", " + supersolvable_str + ", " + monomial_str + ", " + solvable_str + ", a " + zgroup_str + ", " + metacyclic_str + ", " + metabelian_str + ", and an " + agroup_str +  ") and " + rational_str +"."
            else:
                 strng = "This group is " +  cyclic_str + " (" + hence_str + " " + abelian_str + ", " + nilpotent_str + ", " + supersolvable_str + ", " + monomial_str + ", " + solvable_str + ", a " + zgroup_str + ", " + metacyclic_str + ", " + metabelian_str + ", and an " + agroup_str +  ")."
            
            if gp.simple:
                strng += "<br> It is also " + simple_str + "."
                

        elif gp.abelian:
            if gp.rational:
                strng = "This group is " + abelian_str + " (" + hence_str + " " + nilpotent_str + ", " + supersolvable_str + ", " + monomial_str + ",  " + solvable_str +  ", " +  metabelian_str + ", and an " + agroup_str +  ") and " + rational_str + "."
            else:
                strng = "This group is " + abelian_str + " (" + hence_str + " " + nilpotent_str + ", " + supersolvable_str + ", " + monomial_str + ",  " + solvable_str +  ", " +  metabelian_str + ", and an " + agroup_str +  ")."
            if gp.Zgroup:
                strng += "It is also a " + zgroup_str + " (" + hence_str + " " +  metacyclic_str + ")."

            
#rest will assume non-abelian            
        else:
            strng = "This group is " + nonabelian_str 

        #finite nilpotent is Agroup iff group is abelian (so can't be Zgroup/Agroup)
            if gp.nilpotent:
                strng += ". It is " + nilpotent_str + " (" + hence_str + " " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + ")"
                if gp.rational:
                    if gp.metacyclic:
                        strng += ", "  + metacyclic_str + " (" + hence_str + " " + metabelian_str + ") and " + rational_str + "."
                    elif gp.metabelian:
                        strng += ", " + metabelian_str + " and " + rational_str +"."
                else:
                    if gp.metacyclic:
                        strng += "and "  + metacyclic_str + " (" + hence_str + " " + metabelian_str + ")."
                    elif gp.metabelian:
                        strng += ", and " + metabelian_str + "."
                        

            elif gp.Zgroup:
                if gp.rational:
                    strng += ". It is a  " + zgroup_str + " (" + hence_str + " " + metacyclic_str + ", " + metabelian_str + ",  an " + agroup_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + ") and " + rational_str + "."
                else:
                    strng += ". It is a  " + zgroup_str + " (" + hence_str + " " + metacyclic_str + ", " + metabelian_str + ",  an " + agroup_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + ")."


            elif gp.metacyclic:   
                if gp.rational and gp.Agroup:
                    strng += ". It is " + metacyclic_str +  " (" + hence_str + " " + metabelian_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + "), an  " + agroup_str + ", and " + rational_str + "."
                elif gp.rational:
                    strng += ". It is " + metacyclic_str +  " (" + hence_str + " " + metabelian_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + "), and  "  + rational_str + "."
                elif gp.Agroup:
                    strng += ". It is " + metacyclic_str +  " (" + hence_str + " " + metabelian_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + "), and  " + agroup_str + "."
                else:
                    strng += ". It is " + metacyclic_str +  " (" + hence_str + " " + metabelian_str + ", " + supersolvable_str + ", " + monomial_str + ", and " + solvable_str + ")."                    



                    
            elif gp.supersolvable:
                strng += ". It is  " + supersolvable_str + " (" + hence_str + " " + monomial_str + " and " + solvable_str + ")"
                if gp.metabelian:
                    if gp.rational and gp.Agroup:
                        strng += ", " + metabelian_str + ", an " + agroup_str + ", and " + rational_str + "."
                    elif gp.rational:
                         strng += ", " + metabelian_str + ", and " + rational_str + "."
                    elif gp.Agroup:
                         strng += ", " + metabelian_str + ", and an " + agroup_str + "."

                else: #not metabelian
                    if gp.rational and gp.Agroup:
                        strng += ",  an " + agroup_str + ", and " + rational_str + "."
                    elif gp.rational:
                         strng += "and " + rational_str + "."
                    elif gp.Agroup:
                         strng += "and an " + agroup_str + "."
                    else:
                        strng +="."


                    
            elif gp.metabelian:
                strng += ". It is " + metabelian_str + " (" + hence_str + " " + solvable_str + ")"
                if gp.monomial:
                    if gp.rational and gp.Agroup:
                        strng += ", " + monomial_str + ", an " + agroup_str + ", and " + rational_str + "."
                    elif gp.rational:
                         strng += ", " + monomial_str + ", and " + rational_str + "."
                    elif gp.Agroup:
                         strng += ", " + monomial_str + ", and an " + agroup_str + "."

                else: #not metabelian
                    if gp.rational and gp.Agroup:
                        strng += ",  an " + agroup_str + ", and " + rational_str + "."
                    elif gp.rational:
                         strng += "and " + rational_str + "."
                    elif gp.Agroup:
                         strng += "and an " + agroup_str + "."
                    else:
                        strng +="."


            elif gp.monomial:
                strng += ". It is " + monomial_str + " (" + hence_str + solvable_str + ")"
                if gp.rational:
                    if gp.Agroup:
                        strng += ", an " + agroup_str + " and  " + rational_str
                    else:
                        strng += " and  " + rational_str
                strng += "."

                
            elif gp.solvable:
                if gp.rational:
                    if gp.Agroup:
                        strng += ", " + solvable_str + ",  an " + agroup_str + " and  " + rational_str
                    else:
                        strng += ", " + solvable_str + ", and  " + rational_str
                elif gp.Agroup:  #agroup but not rational
                    strng += ", " + solvable_str + ", and  an " + agroup_str
                else:  # only solvable
                    strng += " and " + solvable_str
                strng += "."

            else:
                if gp.rational:
                    if gp.Agroup:
                        strng += ", " + nonsolvable_str + ", an " + agroup_str + " and  " + rational_str
                    else:
                        strng += ", " + nonsolvable_str + " and  " + rational_str
                elif gp.Agroup:  #agroup but not rational
                    strng += ", " + nonsolvable_str + ", and  an " + agroup_str
                else:  # only solvable
                    strng += " and " + nonsolvable_str
                strng += "."

                
        #nonabelian only here so QS and perfect and AS too        
            if gp.simple:
                strng += "<br> It is also " + simple_str + " (" + hence_str + " "  + quasisimple_str + ", " + perfect_str + ", and " + almostsimple_str + ")."


            elif gp.quasisimple:
                strng += "<br> It is also " + quasisimple_str + " (" + hence_str  + " " + perfect_str + ")"
                if gp.almost_simple:
                    strng += " and " + almostsimple_str
                strng += "."

                
            elif gp.perfect:
                strng += "<br> It is also " + perfect_str
                if gp.almost_simple:
                    strng += "and " +  almostsimple_str
                strng += "."
      
            elif  gp.almost_simple:
                strng += "It is " +  almostsimple_str + "."

            
    return strng



def url_for_label(label):
    if label == "random":
        return url_for(".random_abstract_group")
    return url_for("abstract.by_label", label=label)

def url_for_subgroup_label(label):
    if label == "random":
        return url_for(".random_abstract_subgroup")
    return url_for("abstract.by_subgroup_label", label=label)

@abstract_page.route("/")
def index():
    bread = get_bread()
    info = to_dict(request.args, search_array=GroupsSearchArray())
    if request.args:
        info['search_type'] = search_type = info.get('search_type', info.get('hst', 'List'))
        if search_type in ['List', 'Random']:
            return group_search(info)
        elif search_type in ['Subgroups', 'RandomSubgroup']:
            info['search_array'] = SubgroupSearchArray()
            return subgroup_search(info)
    info['count']= 50
    info['order_list']= ['1-10', '20-100', '101-200']
    info['nilp_list']= range(1,5)
    info['maxgrp']= db.gps_groups.max('order')

    return render_template("abstract-index.html", title="Abstract groups", bread=bread, info=info, learnmore=learnmore_list())



@abstract_page.route("/random")
def random_abstract_group():
    label = db.gps_groups.random(projection='label')
    response = make_response(redirect(url_for(".by_label", label=label), 307))
    response.headers['Cache-Control'] = 'no-cache, no-store'
    return response



@abstract_page.route("/<label>")
def by_label(label):
    if label_is_valid(label):
        return render_abstract_group(label)
    else:
        flash_error( "The label %s is invalid.", label)
        return redirect(url_for(".index"))

AB_LABEL_RE = re.compile(r"\d+(_\d+)?(\.\d+(_\d+)?)*")
@abstract_page.route("/ab/<label>")
def by_abelian_label(label):
    print("ABELIAN")
    # For convenience, we provide redirects for abelian groups:
    # m1_e1.m2_e2... represents C_{m1}^e1 x C_{m2}^e2 x ...
    if not AB_LABEL_RE.match(label):
        flash_error(r"The abelian label %s is invalid; it must be of the form m1_e1.m2_e2... representing $C_{m_1}^{e_1} \times C_{m_2}^{e_2} \times \cdots$", label)
        return redirect(url_for(".index"))
    parts = defaultdict(list)
    for piece in label.split("."):
        if "_" in piece:
            base, exp = map(ZZ, piece.split("_"))
        else:
            base = ZZ(piece)
            exp = 1
        for p,e in base.factor():
            parts[p].extend([p**e] * exp)
    for v in parts.values():
        v.sort()
    print(parts)
    primary = sum((parts[p] for p in sorted(parts)), [])
    label = db.gps_groups.lucky({"abelian": True, "primary_abelian_invariants": primary}, "label")
    if label is None:
        # We want latex, so don't use the escape
        flash_error("The database does not contain the abelian group $%s$" % (r" \times ".join("C_{%s}^{%s}" % (q, e) for (q, e) in Counter(primary).items())))
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".by_label", label=label))

@abstract_page.route("/sub/<label>")
def by_subgroup_label(label):
    if subgroup_label_is_valid(label):
        return render_abstract_subgroup(label)
    else:
        flash_error("The label %s is invalid.", label)
        return redirect(url_for(".index"))

@abstract_page.route("/char_table/<label>")
def char_table(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    return render_template("character_table_page.html",
                           gp=gp,
                           title="Character table for %s" % label,
                           bread=get_bread([("Character table", " ")]),
                           learnmore=learnmore_list())

@abstract_page.route("/Qchar_table/<label>")
def Qchar_table(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    return render_template("rational_character_table_page.html",
                           gp=gp,
                           title="Rational character table for %s" % label,
                           bread=get_bread([("Rational character table", " ")]),
                           learnmore=learnmore_list())

@abstract_page.route("/diagram/<label>")
def sub_diagram(label):
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    layers = gp.subgroup_layers
    maxw = max([len(z) for z in layers[0]])
    h = 160*(len(layers[0])-1)
    h = min(h, 1000)
    w = 200*maxw
    w = min(w,1500)
    info = {'dojs': diagram_js(gp,layers), 'w': w, 'h': h}
    return render_template("diagram_page.html", 
        info=info,
        title="Rational character table for %s" % label,
        bread=get_bread([("Subgroup diagram", " ")]),
        learnmore=learnmore_list())

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
                           learnmore=learnmore_list_remove('Source'))


@search_wrap(template="abstract-search.html",
             table=db.gps_groups,
             title='Abstract group search results',
             err_title='Abstract groups search input error',
             shortcuts={'jump':group_jump,
                        'download':group_download},
             projection=['label','order','abelian','exponent','solvable',
                        'nilpotent','center_label','outer_order', 'tex_name',
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
    info['show_type'] = show_type
    parse_ints(info, query, 'order', 'order')
    parse_ints(info, query, 'exponent', 'exponent')
    parse_ints(info, query, 'nilpotency_class', 'nilpotency class')
    parse_ints(info, query, 'number_conjugacy_classes', 'number of conjugacy classes')
    parse_ints(info, query, 'aut_order', 'aut_order')
    parse_ints(info, query, 'outer_order', 'outer_order')
    parse_ints(info, query, 'derived_length', 'derived_length')
    parse_ints(info, query, 'rank', 'rank')
    parse_multiset(info, query, 'order_stats', 'order_stats')
    parse_bool(info, query, 'abelian', 'is abelian')
    parse_bool(info, query, 'cyclic', 'is cyclic')
    parse_bool(info, query, 'metabelian', 'is metabelian')
    parse_bool(info, query, 'metacyclic', 'is metacyclic')
    parse_bool(info, query, 'solvable', 'is solvable')
    parse_bool(info, query, 'supersolvable', 'is supersolvable')
    parse_bool(info, query, 'nilpotent', 'is nilpotent')
    parse_bool(info, query, 'perfect', 'is perfect')
    parse_bool(info, query, 'simple', 'is simple')
    parse_bool(info, query, 'almost_simple', 'is almost simple')
    parse_bool(info, query, 'quasisimple', 'is quasisimple')
    parse_bool(info, query, 'direct_product', 'is direct product')
    parse_bool(info, query, 'semidirect_product', 'is semidirect product')
    parse_bool(info, query, 'Agroup', 'is A-group')
    parse_bool(info, query, 'Zgroup', 'is Z-group')
    parse_bool(info, query, 'monomial', 'is monomial')
    parse_bool(info, query, 'rational', 'is rational')
    parse_regex_restricted(info, query, 'center_label', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'aut_group', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'commutator_label', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'central_quotient', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'abelian_quotient', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'frattini_label', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'outer_group', regex=abstract_group_label_regex)

@search_wrap(template="subgroup-search.html",
             table=db.gps_subgroups,
             title='Subgroup search results',
             err_title='Subgroup search input error',
             projection=['label', 'cyclic', 'abelian', 'solvable',
                         'quotient_cyclic', 'quotient_abelian', 'quotient_solvable',
                         'normal', 'characteristic', 'perfect', 'maximal', 'minimal_normal',
                         'central', 'direct', 'split', 'hall', 'sylow',
                         'subgroup_order', 'ambient_order', 'quotient_order',
                         'subgroup', 'ambient', 'quotient',
                         'subgroup_tex', 'ambient_tex', 'quotient_tex'],
             bread=lambda:get_bread([('Search Results', '')]),
             learnmore=learnmore_list,
             credit=lambda:credit_string)
def subgroup_search(info, query):
    info['group_url'] = get_url
    info['subgroup_url'] = get_sub_url
    info['show_factor'] = lambda num: '$'+latex(ZZ(num).factor())+'$'
    info['search_type'] = 'Subgroups'
    parse_ints(info, query, 'subgroup_order')
    parse_ints(info, query, 'ambient_order')
    parse_ints(info, query, 'quotient_order', 'subgroup index')
    parse_bool(info, query, 'abelian')
    parse_bool(info, query, 'cyclic')
    parse_bool(info, query, 'solvable')
    parse_bool(info, query, 'quotient_abelian')
    parse_bool(info, query, 'quotient_cyclic')
    parse_bool(info, query, 'quotient_solvable')
    parse_bool(info, query, 'perfect')
    parse_bool(info, query, 'normal')
    parse_bool(info, query, 'characteristic')
    parse_bool(info, query, 'maximal')
    parse_bool(info, query, 'minimal_normal')
    parse_bool(info, query, 'central')
    parse_bool(info, query, 'split')
    parse_bool(info, query, 'direct')
    parse_bool(info, query, 'hall')
    parse_bool(info, query, 'sylow')
    parse_bool(info, query, 'proper')
    parse_regex_restricted(info, query, 'subgroup', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'ambient', regex=abstract_group_label_regex)
    parse_regex_restricted(info, query, 'quotient', regex=abstract_group_label_regex)

def get_url(label):
    return url_for(".by_label", label=label)
def get_sub_url(label):
    return url_for(".by_subgroup_label", label=label)

def factor_latex(n):
    return '$%s$' % web_latex(factor(n), False)

def diagram_js(gp, layers):
    ll = [[["%s"%str(grp.subgroup), grp.label, str(grp.subgroup_tex), grp.count, grp.subgroup_order, group_pretty_image(grp.subgroup), grp.diagram_x] for grp in layer] for layer in layers[0]]
    subs = gp.subgroups
    orders = list(set(sub.subgroup_order for sub in subs.values()))
    orders.sort()

    myjs = 'var sdiagram = make_sdiagram("subdiagram", "%s",'% str(gp.label)
    myjs += str(ll) + ',' + str(layers[1]) + ',' + str(orders)
    myjs += ');'
    return myjs

#Writes individual pages
def render_abstract_group(label):
    abstract_logger.info("A")
    info = {}
    label = clean_input(label)
    gp = WebAbstractGroup(label)
    if gp.is_null():
        flash_error( "No group with label %s was found in the database.", label)
        return redirect(url_for(".index"))
    #check if it fails to be a potential label even

    info['boolean_characteristics_string']=create_boolean_string(gp)

    prof = list(gp.subgroup_profile.items())
    prof.sort(key=lambda z: - z[0]) # largest to smallest
    info['subgroup_profile'] = [(z[0], display_profile_line(z[1])) for z in prof]
    # prepare for javascript call to make the diagram
    if gp.diagram_ok:
        layers = gp.subgroup_layers
        info['dojs'] = diagram_js(gp, layers)
        totsubs = len(gp.subgroups)
        info['wide'] = (totsubs-2) > (len(layers[0])-2)*4; # boolean
    else:
        info['dojs'] = ''

    factored_order = factor_latex(gp.order)
    #abstract_logger.info("B1")
    #aut_order = factor_latex(gp.aut_order)
    #abstract_logger.info("B2")
    #out_order = factor_latex(gp.outer_order)
    #abstract_logger.info("B3")
    #z_order = factor_latex(gp.cent_order())
    #abstract_logger.info("B4")
    #Gab_order = factor_latex(gp.Gab_order())

    abstract_logger.info("D0")

    s = r",\ "

    info['max_sub_cnt'] = db.gps_subgroups.count_distinct('ambient', {'subgroup': label, 'maximal': True})
    info['max_quo_cnt'] = db.gps_subgroups.count_distinct('ambient', {'quotient': label, 'minimal_normal': True})
    #def sortkey(x):
    #    if x[0] is None:
    #        return (0, 0)
    #    return tuple(int(m) for m in x[0].split("."))
    #def show_cnt(x, cnt):
    #    if cnt == 1:
    #        return x
    #    else:
    #        return x + " (%s)" % cnt
    #max_subs = defaultdict(lambda: defaultdict(int))
    #for sup in gp.maximal_subgroup_of:
    #    if sup.normal:
    #        max_subs[sup.ambient, sup.ambient_tex, sup.ambient_order][sup.quotient, sup.quotient_tex] += 1
    #    else:
    #        max_subs[sup.ambient, sup.ambient_tex, sup.ambient_order][None, None] += 1
    #max_subs = [A + (", ".join(
    #    show_cnt("Non-normal" if quo is None else '<a href="%s">$%s$</a>' % (quo, quo_tex),
    #             max_subs[A][quo, quo_tex])
    #    for (quo, quo_tex) in sorted(max_subs[A], key=sortkey)),)
    #            for A in sorted(max_subs, key=sortkey)]
    #abstract_logger.info("D1")
    #max_quot = defaultdict(lambda: defaultdict(int))
    #for sup in gp.maximal_quotient_of:
    #    print(sup.ambient, sup.ambient_tex, sup.ambient_order)
    #    max_quot[sup.ambient, sup.ambient_tex, sup.ambient_order][sup.subgroup, sup.subgroup_tex] += 1
    #print("LEN", len(max_quot))
    #max_quot = [A + (", ".join(
    #    show_cnt('<a href="%s">$%s$</a>' % (sub, sub_tex),
    #             max_quot[A][sub, sub_tex])
    #    for (sub, sub_tex) in sorted(max_quot[A], key=sortkey)),)
    #            for A in sorted(max_quot, key=sortkey)]
    #abstract_logger.info("D2")
    #info['max_subs'] = max_subs
    #info['max_quot'] = max_quot

    title = 'Abstract group '  + '$' + gp.tex_name + '$'


    if gp.cyclic:
        abelian_property_string = "cyclic"
    elif gp.abelian:
        abelian_property_string = "abelian"
    else:
        abelian_property_string ="nonabelian"

    if gp.solvable:
        solvable_property_string = "solvable"
    else:
        solvable_property_string ="nonsolvable"
       
    
    properties = [
        ('Label', label),
        ('Order', '$%s$' % factored_order),
        (abelian_property_string, ' '),
        (solvable_property_string, ' '),
        #('#$\operatorname{Aut}(G)$', '$%s$' % aut_order),
        #('#$\operatorname{Out}(G)$', '$%s$' % out_order),
        #('#$Z(G)$', '$%s$' % z_order),
        #(r'#$G^{\mathrm{ab}}$', '$%s$' % Gab_order),
    ]


    downloads = [('Code for Magma', url_for(".download_group",  label=label, download_type='magma')),
                     ('Code for Gap', url_for(".download_group", label=label, download_type='gap'))]




    #"internal" friends
    sbgp_of_url=" /Groups/Abstract/?hst=Subgroups&subgroup="+label+"&search_type=Subgroups"
    sbgp_url = "/Groups/Abstract/?hst=Subgroups&ambient="+label+"&search_type=Subgroups"
    quot_url ="/Groups/Abstract/?hst=Subgroups&quotient="+label+"&search_type=Subgroups"


    
    
    friends =  [("Subgroups", sbgp_url),("Extensions",quot_url),("Supergroups",sbgp_of_url)]

    #"external" friends
    gap_ints =  [int(y) for y in label.split(".")]
    gap_str = str(gap_ints).replace(" ","")
    if db.g2c_curves.count({'aut_grp_id':gap_str}) > 0:
        g2c_url = '/Genus2Curve/Q/?hst=List&aut_grp_id=%5B' + str(gap_ints[0]) + '%2C'+  str(gap_ints[1])  + '%5D&search_type=List'
        friends += [("As the automorphism of a genus 2 curve",g2c_url)]
        if db.hgcwa_passports.count({'group':gap_str}) > 0:
            auto_url = "/HigherGenus/C/Aut/?group=%5B"+str(gap_ints[0])+ "%2C" + str(gap_ints[1]) + "%5D"
        friends += [( "... and of a higher genus curve",auto_url)]
    elif db.hgcwa_passports.count({'group':gap_str}) > 0:
        auto_url = "/HigherGenus/C/Aut/?group=%5B"+str(gap_ints[0])+ "%2C" + str(gap_ints[1]) + "%5D"
        friends += [("As the automorphism of a curve",auto_url)]

    if db.gps_transitive.count({'gapidfull': gap_str}) > 0:
        gal_gp_url= "/GaloisGroup/?gal=%5B" + str(gap_ints[0]) + "%2C" + str(gap_ints[1])  +"%5D"
        friends +=[("As a transitive group", gal_gp_url)]


    if db.gps_st.count({'component_group': label}) > 0:
        st_url='/SatoTateGroup/?hst=List&component_group=%5B'+  str(gap_ints[0])+ '%2C' +   str(gap_ints[1]) + '%5D&search_type=List'
        friends += [("As the component group of a Sato-Tate group", st_url)]
    
    
    bread = get_bread([(label, '')])

    abstract_logger.info("Z")

    return render_template("abstract-show-group.html",
                           title=title, bread=bread, info=info,
                           gp=gp,
                           properties=properties,
                           friends=friends,
                           learnmore=learnmore_list(),
                           downloads=downloads)

def render_abstract_subgroup(label):
    info = {}
    label = clean_input(label)
    seq = WebAbstractSubgroup(label)

    info['create_boolean_string'] = create_boolean_string
    info['factor_latex'] = factor_latex

    if seq.normal:
        title = r'Normal subgroup $%s \trianglelefteq %s$'
    else:
        title = r'Non-normal subgroup $%s \subseteq %s$'
    title = title % (seq.subgroup_tex, seq.ambient_tex)

    properties = [
        ('Label', label),
        ('Order', factor_latex(seq.subgroup_order)),
        ('Index', factor_latex(seq.quotient_order)),
        ('Normal', 'Yes' if seq.normal else 'No'),
    ]

    bread = get_bread([(label, )])

    return render_template("abstract-show-subgroup.html",
                           title=title, bread=bread, info=info,
                           seq=seq,
                           properties=properties,
                           #friends=friends,
                           learnmore=learnmore_list())

def make_knowl(title, knowlid):
    return '<a title="%s" knowl="%s">%s</a>'%(title, knowlid, title)

@abstract_page.route("/subinfo/<label>")
def shortsubinfo(label):
    if not subgroup_label_is_valid(label):
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
    ans += '<tr><td><td style="text-align: right"><a href="%s">$%s$ home page</a>' % (url_for_subgroup_label(wsg.label), wsg.subgroup_tex)
    #print ""
    #print ans
    ans += '</table>'
    return ans


@abstract_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the abstract groups data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.groups.abstract',
                            title=t, bread=bread,
                            learnmore=learnmore_list_remove('Complete'))


@abstract_page.route("/Labels")
def labels_page():
    t = 'Labels for abstract groups'
    bread = get_bread("Labels")
    return render_template("single.html", kid='rcs.label.groups.abstract',
                           learnmore=learnmore_list_remove('label'), 
                           title=t, bread=bread)


@abstract_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of the abstract groups data'
    bread = get_bread("Reliability")
    return render_template("single.html", kid='rcs.rigor.groups.abstract',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Reliability'))


@abstract_page.route("/Source")
def how_computed_page():
    t = 'Source of the abstract group data'
    bread = get_bread("Source")
    return render_template("double.html", kid='rcs.source.groups.abstract', kid2='rcs.ack.groups.abstract',
                           title=t, bread=bread, 
                           learnmore=learnmore_list_remove('Source'))


@abstract_page.route("/<label>/download/<download_type>")
def download_group(**args):
    dltype = args['download_type']
    label = args['label']
    delim = "bracket"
    com = "#"  # single line comment start
    com1 = ""  # multiline comment start
    com2 = ""  # multiline comment end

    gp_data = db.gps_groups.lucky({"label": label}) 
    
    filename = "group" +  label
    mydate = time.strftime("%d %B %Y")
    if dltype == "gap":
        filename += ".gp"
    if dltype == "magma":
        com = ""
        com1 = "/*"
        com2 = "*/"
        delim = "magma"
        filename += ".m"
    s = com1 + "\n"
    s += com + " Group " + label + " downloaded from the LMFDB on %s.\n" % (mydate)
    s += com + " If the group is solvable, G is the  polycyclic group  matching the one presented in LMFDB."
    s += com + " Generators will be stored as a, b, c,... to match LMFDB.  \n"
    s += com + " If the group is nonsolvable, G is a permutation group giving with generators as in LMFDB."
    s += com + " \n"
    s += "\n" + com2
    s += "\n"


    if gp_data['solvable']:
        s += "gpsize:=  " + str(gp_data['order']) + "; \n"
        s +="encd:= " + str(gp_data['pc_code']) + "; \n"

        if dltype == "magma":
            s += "G:=SmallGroupDecoding(encd,gpsize); \n"
        elif dltype == "gap":
            s += "G:=PcGroupCode(encd, gpsize); \n"

        gen_index = gp_data['gens_used']
        num_gens = len(gen_index)
        for i in range(num_gens):
            s += ascii_lowercase[i] + ":= G." + str(gen_index[i]) + "; \n" 

    #otherwise nonsolvable MAY NEED TO CHANGE WITH MATRIX GROUPS??       
    else:
        d = -gp_data['elt_rep_type']
        s += "d:=" +str(d) + "; \n"
        s += "Sd:=SymmetricGroup(d); \n"

        #Turn Lehmer code into permutations
        list_gens = []
        for perm in gp_data['perm_gens']:
            perm_decode = Permutations(d).unrank(perm)
            list_gens.append(perm_decode)

        if dltype == "magma":
            s += "G:=sub<Sd | " + str(list_gens) + ">; \n"
        elif dltype == "gap":
#          MAKE LIST2
            s += "List_Gens:="+ str(list_gens)+ "; \n \n"
            s +="LGens:=[]; \n"
            s += "for gens in List_Gens do AddSet(LGens,PermList(gens)); od;\n"
            s += "G:=Subgroup(Sd,LGens);"
      

    strIO = BytesIO()
    strIO.write(s.encode('utf-8'))
    strIO.seek(0)
    return send_file(strIO, attachment_filename=filename, as_attachment=True, add_etags=False)





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
            label="Nilpotency class",
            knowl="group.nilpotent",
            example="3",
            example_span="4, or a range like 3..5")
        aut_group = TextBox(
            name="aut_group",
            label="Automorphism group",
            knowl="group.automorphism",
            example="4.2",
            example_span="4.2"
            )
        aut_order = TextBox(
            name="aut_order",
            label="Automorphism group order",
            knowl="group.automorphism",
            example="3",
            example_span="4, or a range like 3..5")
        derived_length = TextBox(
            name="derived_length",
            label="Derived length",
            knowl="group.derived_series",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
            )
        frattini_label= TextBox(
            name="frattini_label",
            label="Frattini subgroup",
            knowl="group.frattini_subgroup",
            example="4.2",
            example_span="4.2",
            advanced=True
            )
        outer_group = TextBox(
            name="outer_group",
            label="Outer automorphism group",
            knowl="group.outer_aut",
            example="4.2",
            example_span="4.2",
            advanced=True
            )
        outer_order = TextBox(
            name="outer_order",
            label="Outer automorphism group order",
            knowl="group.outer_aut",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
            )
        rank = TextBox(
            name="rank",
            label="Rank",
            knowl="group.rank",
            example="3",
            example_span="4, or a range like 3..5",
            advanced=True
            )
        abelian = YesNoBox(
            name="abelian",
            label="Abelian",
            knowl="group.abelian",
            example_col=True
            )
        metabelian = YesNoBox(
            name="metabelian",
            label="Metabelian",
            knowl="group.metabelian",
            advanced=True,
            example_col=True
            )
        cyclic = YesNoBox(
            name="cyclic",
            label="Cyclic",
            knowl="group.cyclic")
        metacyclic = YesNoBox(
            name="metacyclic",
            label="Metacyclic",
            knowl="group.metacyclic",
            advanced=True
            )
        solvable = YesNoBox(
            name="solvable",
            label="Solvable",
            knowl="group.solvable",
            example_col=True
            )
        supersolvable = YesNoBox(
            name="supersolvable",
            label="Supersolvable",
            knowl="group.supersolvable",
            advanced=True,
            example_col=True
            )
        nilpotent = YesNoBox(
            name="nilpotent",
            label="Nilpotent",
            knowl="group.nilpotent")
        simple = YesNoBox(
            name="simple",
            label="Simple",
            knowl="group.simple",
            example_col=True
            )
        almost_simple= YesNoBox(
            name="almost_simple",
            label="Almost simple",
            knowl="group.almost_simple",
            example_col=True,
            advanced=True
            )
        quasisimple= YesNoBox(
            name="quasisimple",
            label="Quasisimple",
            knowl="group.quasisimple",
            advanced=True
            )
        perfect = YesNoBox(
            name="perfect",
            label="Perfect",
            knowl="group.perfect")
        direct_product = YesNoBox(
            name="direct_product",
            label="Direct product",
            knowl="group.direct_product",
            example_col=True
            )
        semidirect_product = YesNoBox(
            name="semidirect_product",
            label="Semidirect product",
            knowl="group.semidirect_product")
        Agroup = YesNoBox(
            name="Agroup",
            label="A-group",
            knowl="group.a_group",
            advanced=True,
            example_col=True
            )
        Zgroup = YesNoBox(
            name="Zgroup",
            label="Z-group",
            knowl="group.z_group",
            advanced=True,
            )
        monomial = YesNoBox(
            name="monomial",
            label="Monomial",
            knowl="group.monomial",
            advanced=True,
            )
        rational = YesNoBox(
            name="rational",
            label="Rational",
            knowl="group.rational_group",
            advanced=True,
            example_col=True
            )
        center_label = TextBox(
            name="center_label",
            label="Center",
            knowl="group.center_isolabel",
            example="4.2",
            example_span="4.2"
            )
        commutator_label = TextBox(
            name="commutator_label",
            label="Commutator",
            knowl="group.commutator_isolabel",
            example="4.2",
            example_span="4.2"
            )
        abelian_quotient = TextBox(
            name="abelian_quotient",
            label="Abelianization",
            knowl="group.abelianization_isolabel",
            example="4.2",
            example_span="4.2"
            )
        central_quotient = TextBox(
            name="central_quotient",
            label="Central quotient",
            knowl="group.central_quotient_isolabel",
            example="4.2",
            example_span="4.2"
            )
        order_stats = TextBox(
            name="order_stats",
            label="Order statistics",
            knowl="group.order_stats",
            example="1^1,2^3,3^2",
            example_span="1^1,2^3,3^2"
            )
        count = CountBox()

        self.browse_array = [
            [order, exponent],
            [nilpclass],
            [aut_group, aut_order],
            [center_label, commutator_label],
            [central_quotient, abelian_quotient],
            [abelian, cyclic],
            [simple, perfect],
            [solvable, nilpotent],
            [direct_product, semidirect_product],
            [outer_group, outer_order],
            [metabelian, metacyclic],
            [almost_simple, quasisimple],
            [Agroup, Zgroup],
            [derived_length, frattini_label],
            [supersolvable, monomial],
            [rational, rank],
            [order_stats],
            [count]
        ]

        self.refine_array = [
            [order, exponent, nilpclass, nilpotent],
            [center_label, commutator_label, central_quotient, abelian_quotient],
            [abelian, cyclic, solvable, simple],
            [perfect, direct_product, semidirect_product],
            [aut_group, aut_order, outer_group, outer_order],
            [metabelian, metacyclic, almost_simple, quasisimple],
            [Agroup, Zgroup, derived_length, frattini_label],
            [supersolvable, monomial, rational, rank],
            [order_stats]
        ]

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
        quotient_abelian = YesNoBox(
            name="quotient_abelian",
            label="Abelian quotient",
            knowl="group.abelian")
        quotient_cyclic = YesNoBox(
            name="quotient_cyclic",
            label="Cyclic quotient",
            knowl="group.cyclic")
        quotient_solvable = YesNoBox(
            name="quotient_solvable",
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
        split = YesNoBox(
            name="split",
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
            example="8",
            example_span="4, or a range like 3..5")
        quotient_order = TextBox(
            name="quotient_order",
            label="Subgroup Index",
            knowl="group.subgroup.index",
            example="16")
        ambient_order = TextBox(
            name="ambient_order",
            label="Ambient Order",
            knowl="group.order",
            example="128")
        proper = YesNoBox(
            name="proper",
            label="Proper",
            knowl="group.proper_subgroup")

        self.refine_array = [
            [subgroup, subgroup_order, cyclic, abelian, solvable],
            [normal, characteristic, perfect, maximal, central, proper],
            [ambient, ambient_order, direct, split, hall, sylow],
            [quotient, quotient_order, quotient_cyclic, quotient_abelian, quotient_solvable, minimal_normal]]

    def search_types(self, info):
        if info is None:
            return [("Subgroups", "List of subgroups"), ("Random", "Random subgroup")]
        else:
            return [("Subgroups", "Search again"), ("Random", "Random subgroup")]

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

def cc_data(gp, label, typ='complex'):
    if typ == 'rational':
        wag = WebAbstractGroup(gp)
        rcc = wag.conjugacy_class_divisions
        if not rcc:
            return 'Data for conjugacy class {} not found.'.format(label)
        for div in rcc:
            if div.label == label:
                break
        else:
            return 'Data for conjugacy class {} missing.'.format(label)
        classes = div.classes
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
    if mychar._data.get('image'):
        txt = "Image"
        imageknowl = '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=qrep_data&args=%s">%s</a>' % (mychar.image, mychar.image, mychar.image)
        if mychar.schur_index > 1:
            txt = r'Image of ${}\ *\ ${}'.format(mychar.schur_index, label)
        ans += '<br>{}: {}'.format(txt, imageknowl)
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
    if mychar._data.get('image'):
        imageknowl = '<a title = "%s [lmfdb.object_information]" knowl="lmfdb.object_information" kwargs="func=crep_data&args=%s">%s</a>' % (mychar.image, mychar.image, mychar.image)
        ans += '<br>Image: {}'.format(imageknowl)
    else:
        ans += '<br>Image: not computed'
    return Markup(ans)

def crep_data(label):
    info = db.gps_crep.lookup(label)
    ans = '<h3>Subgroup of $\GL_{{ {}  }}(\C)$: {}</h3>'.format(info['dim'], label)
    ans += '<br>Order: ${}$'.format(info['order'])
    ans += '<br>Abstract group: {}'.format(group_display_knowl(info['group'], info['group']))
    ans += '<br>Group name: ${}$'.format(group_names_pretty(info['group']))
    ans += '<br>Dimension: ${}$'.format(info['dim'])
    ans += '<br>Irreducible: {}'.format(info['irreducible'])
    plural = '' if len(info['gens'])==1 else 's'
    ans += '<br>Matrix generator{}: '.format(plural)
    N=info['cyc_order_mat']
    genlist = ['$'+dispcyclomat(N, gen)+'$' for gen in info['gens']]
    ans += ','.join(genlist)
    return Markup(ans)

def qrep_data(label):
    info = db.gps_qrep.lookup(label)
    ans = '<h3>Subgroup of $\GL_{{ {}  }}(\Q)$: {}</h3>'.format(info['dim'], label)
    ans += '<br>Order: ${}$'.format(info['order'])
    ans += '<br>Abstract group: {}'.format(group_display_knowl(info['group'], info['group']))
    ans += '<br>Group name: ${}$'.format(group_names_pretty(info['group']))
    ans += '<br>Dimension: ${}$'.format(info['dim'])
    ans += '<br>Irreducible: {}'.format(info['irreducible'])
    plural = '' if len(info['gens'])==1 else 's'
    ans += '<br>Matrix generator{}: '.format(plural)
    genlist = ['$'+dispZmat(gen)+'$' for gen in info['gens']]
    ans += ','.join(genlist)
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
        'group_data': group_data,
        'crep_data': crep_data,
        'qrep_data': qrep_data}

def order_stats_list_to_string(o_list):
    s = ""
    for pair in o_list:
        assert len(pair) == 2
        s += "%s^%s" % (pair[0],pair[1])
        if o_list.index(pair) != len(o_list)-1:
            s += ","
    return s

