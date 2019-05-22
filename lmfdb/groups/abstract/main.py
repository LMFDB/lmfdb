# -*- coding: utf-8 -*-

import ast, os, re, StringIO, yaml

from flask import render_template, request, url_for, redirect, send_file, abort
from sage.all import Permutation

from lmfdb import db
from lmfdb.utils import (
    flash_error,
    parse_ints, clean_input, parse_bracketed_posints, parse_gap_id,
    search_wrap, web_latex)

from lmfdb.groups.abstract import abstract_page
from lmfdb.groups.abstract.web_groups import(
    WebAbstractGroup)


#This currently allows for 6.32a  
abstract_group_label_regex = re.compile(r'(\d+)\.(([a-z]+)|(\d+))')

def label_is_valid(lab):
    return abstract_group_label_regex.match(lab)

def get_bread(breads=[]):
    bc = [("Groups", url_for(".index")),("Abstract", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

#function to create string of group characteristics 
def create_boolean_string(gp):   
    if gp.is_abelian():
        #strng = "KNOWL('group.abelian',title='Abelian')"
        strng = "Abelian"
        if gp.is_cyclic():
            strng = strng + ", Cyclic"
    else:
        #strng = "KNOWL('group.abelian',title='non-Abelian')"
        strng = "non-Abelian"

    if gp.is_solvable():
        strng = strng + ", Solvable"
        if gp.is_cyclic():
            strng = strng + ", Supersolvable"
    else:
        strng = strng + ", non-Solvable"

    if gp.is_nilpotent():
        strng = strng + ", Nilpotent"

    if gp.is_metacyclic():
        strng = strng + ", Metacyclic"

    if gp.is_metabelian():
        strng = strng + ", Metabelian"

    if gp.is_simple():
        strng = strng + ", Simple"

    if gp.is_almost_simple():
        strng = strng + ", Almost Simple"

    if gp.is_quasisimple():
        strng = strng + ", Quasisimple"
        
    if gp.is_perfect():
        strng = strng + ", Perfect"
        
    if gp.is_monomial():
        strng = strng + ", Monomial"

    if gp.is_rational():
        strng = strng + ", Rational"

    if gp.is_Zgroup():
        strng = strng + ", Zgroup"
        
    if gp.is_Agroup():
        strng = strng + ", Agroup"
        
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

        if gp.is_abelian():
            is_abelian='Yes'
        else:
            is_abelian='No'

        if gp.is_nilpotent():
            is_nilpotent='Yes'
        else:
            is_nilpotent='No'            


        factored_order = web_latex(gp.order_factor(),False)    
        aut_order = web_latex(gp.aut_order_factor(),False)    

        
        title = 'Abstract Group '  + '$' + gp.name_label() + '$'

        prop2 = [
            ('Label', '\(%s\)' %  label), ('Order', '\(%s\)' % factored_order), ('#Aut(G)', '\(%s\)' % aut_order)
        ]
        info.update({'is_abelian': is_abelian,
                    'is_nilpotent': is_nilpotent,
                   })

       
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


