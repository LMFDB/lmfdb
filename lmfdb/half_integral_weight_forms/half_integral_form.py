# -*- coding: utf-8 -*-

import re
import pymongo

import lmfdb.base
from lmfdb.base import app, getDBConnection
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
from sage.misc.preparser import preparse
from lmfdb.half_integral_weight_forms import hiwf_page, hiwf_logger

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range2, web_latex_split_on_pm, comma, clean_input
from lmfdb.number_fields.number_field import parse_list

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, parse_range

from lmfdb.number_fields.number_field import parse_list, parse_field_string

from lmfdb.WebNumberField import *


@hiwf_page.route("/")
def half_integral_weight_form_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = 'Samuele Anni, Soma Purkait'
        t = 'Half Integral Weight Cusp Forms'
        bread = [('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage"))]
        info['learnmore'] = []
        return render_template("half_integral_weight_form_all.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return half_integral_weight_form_search(**args)


def half_integral_weight_form_search(**args):
    C = getDBConnection()
    C.halfintegralmf.forms.ensure_index([('level', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])

    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        args = {'label': info['label']}
        return render_hiwf_webpage(**args)
    query = {}
    for field in ['character', 'weight', 'level']:
        if info.get(field):
            if field == 'weight':
                weight = int(info[field]*2)
            
	w = clean_input(info['jinv'])
        j = j.replace('+', '')
        if not QQ_RE.match(j):
            info['err'] = 'Error parsing input for the j-invariant.  It needs to be a rational number.'
            return search_input_error(info, bread)
        query['jinv'] = str(QQ(j)) # to simplify e.g. 1728/1





                query['weight'] = weight       
            elif field == 'character':
                query[field] = parse_field_string(info[field])
            elif field == 'label':
                query[field] = info[field]
            elif field == 'level':
                query[field] = int(info[field])

    info['query'] = dict(query)
    res = C.halfintegralmf.forms.find(query).sort([('level', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])
    nres = res.count()
    count = 100
	
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count:
            info['report'] = 'displaying first %s of %s matches' % (count, nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    res_clean = []
    for v in res:
        v_clean = {}
        v_clean['level'] = v['level']
        v_clean['label'] = v['label']
        v_clean['weight'] = v['weight']
        v_clean['character'] = v['character']
        res_clean.append(v_clean)

    info['forms'] = res_clean

    t = 'Half Integral Weight Cusp Forms search results'
    bread = [('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage")),('Search results', ' ')]
    properties = []
    return render_template("half_integral_weight_form_search.html", info=info, title=t, properties=properties, bread=bread)


@hiwf_page.route('/<label>')
def render_hiwf_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        label = str(args['label'])
        data = C.halfintegralmf.forms.find_one({'label': label})
    if data is None:
        return "No such field"
    info = {}
    info.update(data)

    info['friends'] = []

    bread = [('Half Integral Weight Cusp Forms', url_for(".half_integral_weight_form_render_webpage")), ('%s' % data['label'], ' ')]
    t = "Half Integral Weight Cusp Forms %s" % info['label']
    credit = 'Samuele Anni and Soma Purkait'
    f = C.halfintegralmf.forms.find_one({'level': data['level'], 'weight': data['weight']})
 
    dim = f['dim']
    dimtheta = f['dimtheta']
    dimnew=dim-dimtheta	
    info['dimension'] = dim
    info['dimtheta']= dimtheta
    info['new']= f['newpart']
    info['theta']=f['thetas']
    return render_template("half_integral_weight_form.html", info=info, credit=credit, title=t, bread=bread)


