# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: Paul-Olivier Dehaye, John Jones

import pymongo
ASC = pymongo.ASCENDING
from lmfdb.base import getDBConnection
from flask import render_template, request, url_for, flash, redirect
from markupsafe import Markup

from lmfdb.artin_representations import artin_representations_page
from lmfdb.utils import to_dict, random_object_from_collection
from lmfdb.search_parsing import parse_primes, parse_restricted, parse_galgrp, parse_ints, parse_container, parse_count, parse_start, clean_input

from math_classes import ArtinRepresentation
from lmfdb.transitive_group import group_display_knowl

from sage.all import ZZ

import re, random


def get_bread(breads=[]):
    bc = [("Artin Representations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def make_cond_key(D):
    D1=ZZ(D)
    if D1<1: D1=ZZ(1)
    D1 = int(D1.log(10))
    return '%04d%s'%(D1,str(D))

def parse_artin_label(label):
    label = clean_input(label)
    if re.compile(r'^\d+\.\d+(e\d+)?(_\d+(e\d+)?)*\.\d+(t\d+)?\.\d+c\d+$').match(label):
        return label
    else:
        raise ValueError("Error parsing input %s.  It is not in a valid form for an Artin representation label, such as 9.2e12_587e3.10t32.1c1"% label)


@artin_representations_page.route("/")
def index():
    args = request.args
    bread = get_bread()
    if len(args) == 0:
        learnmore = [#('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page")),
                ('Artin representations labels', url_for(".labels_page"))]
        return render_template("artin-representation-index.html", title="Artin Representations", bread=bread, learnmore=learnmore)
    else:
        return artin_representation_search(**args)

def artin_representation_search(**args):
    info = to_dict(args)
    if 'natural' in info:
        label = info['natural']
        # test if it is ok
        try:
            label = parse_artin_label(label)
        except ValueError as err:
            flash(Markup("Error: %s" % (err)), "error")
            bread = get_bread([('Search Results','')])
            return search_input_error({'err':''}, bread)
        return redirect(url_for(".render_artin_representation_webpage", label=label), 307)

    title = 'Artin Representation Search Results'
    bread = [('Artin Representations', url_for(".index")), ('Search Results', ' ')]
    sign_code = 0
    query = {'Hide': 0}
    try:
        parse_primes(info,query,"unramified",name="Unramified primes",
                     qfield="BadPrimes",mode="complement",to_string=True)
        parse_primes(info,query,"ramified",name="Ramified primes",
                     qfield="BadPrimes",mode="append",to_string=True)
        parse_restricted(info,query,"root_number",qfield="GaloisConjugates.Sign",
                         allowed=[1,-1],process=int)
        parse_restricted(info,query,"frobenius_schur_indicator",qfield="Indicator",
                         allowed=[1,0,-1],process=int)
        parse_container(info,query, 'container',qfield='Container', name="Smallest permutation representation")
        parse_galgrp(info,query,"group",name="Group",qfield="Galois_nt",use_bson=False)
        parse_ints(info,query,'dimension',qfield='Dim')
        parse_ints(info,query,'conductor',qfield='Conductor_key', parse_singleton=make_cond_key)
        #parse_paired_fields(info,query,field1='conductor',qfield1='Conductor_key',parse1=parse_ints,kwds1={'parse_singleton':make_cond_key},
                                       #field2='dimension',qfield2='Dim', parse2=parse_ints)
    except ValueError:
        return search_input_error(info, bread)

    count = parse_count(info,10)
    start = parse_start(info)

    data = ArtinRepresentation.collection().find(query).sort([("Dim", ASC), ("Conductor_key", ASC)])
    nres = data.count()
    data = data.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0
    if nres == 1:
        report = 'unique match'
    else:
        if nres > count or start != 0:
            report = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            report = 'displaying all %s matches' % nres
    if nres == 0:
        report = 'no matches'


    initfunc = ArtinRepresentation

    return render_template("artin-representation-search.html", req=info, data=data, title=title, bread=bread, query=query, start=start, report=report, nres=nres, initfunc=initfunc, sign_code=sign_code)


def search_input_error(info, bread):
    return render_template("artin-representation-search.html", req=info, title='Artin Representation Search Error', bread=bread)

@artin_representations_page.route("/<dim>/<conductor>/")
def by_partial_data(dim, conductor):
    return artin_representation_search(**{'dimension': dim, 'conductor': conductor})


# credit information should be moved to the databases themselves, not at the display level. that's too late.
tim_credit = "Tim Dokchitser, John Jones, and David Roberts"
support_credit = "Support by Paul-Olivier Dehaye."

@artin_representations_page.route("/<label>/")
@artin_representations_page.route("/<label>")
def render_artin_representation_webpage(label):
    if re.compile(r'^\d+$').match(label):
        return artin_representation_search(**{'dimension': label})

    bread = get_bread([(label, ' ')])

    # label=dim.cond.nTt.indexcj, c is literal, j is index in conj class
    # Should we have a big try around this to catch bad labels?
    clean_label = clean_input(label)
    if clean_label != label:
        return redirect(url_for('.render_artin_representation_webpage', label=clean_label), 301)
    try:
        the_rep = ArtinRepresentation(label)
    except:
        flash(Markup("Error: <span style='color:black'>%s</span> is not the label of an Artin representation in the database." % (label)), "error")
        return search_input_error({'err':''}, bread)
              

    extra_data = {} # for testing?
    C = getDBConnection()
    extra_data['galois_knowl'] = group_display_knowl(5,3,C) # for testing?
    #artin_logger.info("Found %s" % (the_rep._data))


    title = "Artin Representation %s" % label
    the_nf = the_rep.number_field_galois_group()
    if the_rep.sign() == 0:
        processed_root_number = "not computed"
    else:
        processed_root_number = str(the_rep.sign())
    properties = [("Label", label),
                  ("Dimension", str(the_rep.dimension())),
                  ("Group", the_rep.group()),
                  #("Conductor", str(the_rep.conductor())),
                  ("Conductor", "$" + the_rep.factored_conductor_latex() + "$"),
                  #("Bad primes", str(the_rep.bad_primes())),
                  ("Root number", processed_root_number),
                  ("Frobenius-Schur indicator", str(the_rep.indicator()))
                  ]

    friends = []
    nf_url = the_nf.url_for()
    if nf_url:
        friends.append(("Artin Field", nf_url))
    cc = the_rep.central_character()
    if cc is not None:
        if the_rep.dimension()==1:
            if cc.order == 2:
                cc_name = cc.symbol
            else:
                cc_name = cc.texname
            friends.append(("Dirichlet character "+cc_name, url_for("characters.render_Dirichletwebpage", modulus=cc.modulus, number=cc.number)))
        else:
            detrep = the_rep.central_character_as_artin_rep()
            friends.append(("Determinant representation "+detrep.label(), detrep.url_for()))

    # once the L-functions are in the database, the link can always be shown
    #if the_rep.dimension() <= 6:
    if the_rep.dimension() == 1:
        # Zeta is loaded differently
        if cc.modulus == 1 and cc.number == 1:
            friends.append(("L-function", url_for("l_functions.l_function_dirichlet_page", modulus=cc.modulus, number=cc.number)))
        else:
            lfuncdb = getDBConnection().Lfunctions.instances
            # looking for Lhash dirichlet_L_modulus.number
            mylhash = 'dirichlet_L_%d.%d'%(cc.modulus,cc.number)
            lres = lfuncdb.find_one({'Lhash': mylhash})
            if lres is not None:
                friends.append(("L-function", url_for("l_functions.l_function_dirichlet_page", modulus=cc.modulus, number=cc.number)))

    # Dimension > 1
    elif int(the_rep.conductor())**the_rep.dimension() <= 729000000000000:
        friends.append(("L-function", url_for("l_functions.l_function_artin_page",
                                          label=the_rep.label())))
    info={}
    #mychar = the_rep.central_char()
    #info['pol2']= str([((j+1),mychar(j+1, 2*the_rep.character_field())) for j in range(50)])
    #info['pol3']=str(the_rep.central_character())
    #info['pol3']=str(the_rep.central_char(3))
    #info['pol5']=str(the_rep.central_char(5))
    #info['pol7']=str(the_rep.central_char(7))
    #info['pol11']=str(the_rep.central_char(11))
    learnmore=[('Artin representations labels', url_for(".labels_page"))]

    return render_template("artin-representation-show.html", credit=tim_credit, support=support_credit, title=title, bread=bread, friends=friends, object=the_rep, properties2=properties, extra_data=extra_data, info=info, learnmore=learnmore)

@artin_representations_page.route("/random")
def random_representation():
    rep = random_object_from_collection(ArtinRepresentation.collection())
    num = random.randrange(0, len(rep['GaloisConjugates']))
    label = rep['Baselabel']+"c"+str(num+1)
    return redirect(url_for(".render_artin_representation_webpage", label=label), 307)


@artin_representations_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Artin Representation Data'
    bread = get_bread([("Completeness", )])
    learnmore = [('Source of the data', url_for(".how_computed_page")),
                ('Artin representation labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.artin.extent',
                           credit=tim_credit, title=t, bread=bread, 
                           learnmore=learnmore)

@artin_representations_page.route("/Labels")
def labels_page():
    t = 'Labels for Artin Representations'
    bread = get_bread([("Labels", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                ('Source of the data', url_for(".how_computed_page"))]
    return render_template("single.html", kid='artin.label',learnmore=learnmore, credit=tim_credit, title=t, bread=bread)

@artin_representations_page.route("/Source")
def how_computed_page():
    t = 'Source of Artin Representation Data'
    bread = get_bread([("Source", '')])
    learnmore = [('Completeness of the data', url_for(".completeness_page")),
                #('Source of the data', url_for(".how_computed_page")),
                ('Artin representation labels', url_for(".labels_page"))]
    return render_template("single.html", kid='dq.artin.source',
                           credit=tim_credit, title=t, bread=bread, 
                           learnmore=learnmore)

