# -*- coding: utf-8 -*-

import re
import pymongo

from lmfdb.base import app, getDBConnection
from pymongo import ASCENDING, DESCENDING
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html
from lmfdb.search_parsing import parse_list, parse_range, parse_range2
from lmfdb.bianchi_modular_forms import bmf_page, bmf_logger
from lmfdb.number_fields.number_field import field_pretty
from lmfdb.WebNumberField import *

bianchi_credit = 'John Cremona, Aurel Page, Alexander Rahm, Haluk Sengun'

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')

# parse field label, which can either be a coded label such as
# '2.0.8.1' or a nickname such as 'Qi' or 'Qsqrt-1'
def parse_field_label(lab):
    res = parse_field_string(lab)
    if 'not a valid field label' in res:
        return False
    if field_label_regex.match(res):
        if int(res.split('.')[2])%4 in [0,3]:
            return res
        return False
    return False

def teXify_pol(pol_str):  # TeXify a polynomial (or other string containing polynomials)
    o_str = pol_str.replace('*', '')
    ind_mid = o_str.find('/')
    while ind_mid != -1:
        ind_start = ind_mid - 1
        while ind_start >= 0 and o_str[ind_start] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_start -= 1
        ind_end = ind_mid + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '\\frac{' + o_str[ind_start + 1:ind_mid] + '}{' + o_str[
            ind_mid + 1:ind_end] + '}' + o_str[ind_end:]
        ind_mid = o_str.find('/')

    ind_start = o_str.find('^')
    while ind_start != -1:
        ind_end = ind_start + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '{' + o_str[ind_start + 1:ind_end] + '}' + o_str[ind_end:]
        ind_start = o_str.find('^', ind_end)

    return o_str


@bmf_page.route("/")
def bianchi_modular_form_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = bianchi_credit
        t = 'Bianchi Cusp Forms'
        bread = [('Bianchi Modular Forms', url_for(".bianchi_modular_form_render_webpage"))]
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return bianchi_modular_form_search(**args)


def bianchi_modular_form_search(**args):
    C = getDBConnection()
    C.bmfs.forms.ensure_index([('level_norm', ASCENDING), ('label', ASCENDING)])

    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        args = {'label': info['label']}
        return render_bmf_webpage(**args)
    if 'field_label' in info:
        return render_bmf_field_dim_table(**args)
    query = {}
    for field in ['field_label', 'weight', 'level_norm', 'dimension']:
        if info.get(field):
            if field == 'weight':
                try:
                    parallelweight = int(info[field])
                    query['parallel_weight'] = parallelweight
                except:
                    query['weight'] = '2'
            elif field == 'field_label':
                parse_nf_string(info,query,field,'base number field',field)
            elif field == 'label':
                query[field] = info[field]
            elif field == 'dimension':
                query[field] = parse_range(str(info[field]))
            elif field == 'level_norm':
                query[field] = parse_range(info[field])
            else:
                query[field] = info[field]

    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = 100
    else:
        info['count'] = 100
        count = 100

    info['query'] = dict(query)
    res = C.bmfs.forms.find(
        query).sort([('level_norm', ASCENDING), ('label', ASCENDING)]).limit(count)
    nres = res.count()

    if nres > 0:
        info['field_pretty_name'] = field_pretty(res[0]['field_label'])
    else:
        info['field_pretty_name'] = ''
    info['number'] = nres
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
        v_clean['field_label'] = v['field_label']
        v_clean['short_label'] = v['short_label']
        v_clean['label'] = v['label']
        v_clean['level_ideal'] = teXify_pol(v['level_ideal'])
        v_clean['dimension'] = v['dimension']
        res_clean.append(v_clean)

    info['forms'] = res_clean

    t = 'Bianchi Modular Form search results'

    bread = [('Bianchi Modular Forms', url_for(".bianchi_modular_form_render_webpage")), (
        'Search results', ' ')]
    properties = []
    return render_template("bmf-search_results.html", info=info, title=t, properties=properties, bread=bread)

@bmf_page.route('/<field_label>')
def render_bmf_field_dim_table(**args):
    argsdict = to_dict(args)
    start = 0
    if 'start' in request.args:
        start = int(request.args['start'])
    count = 30
    if 'count' in request.args:
        count = int(request.args['count'])
    info={}

    # parse field label, which can either be a coded label such as
    # '2.0.8.1' or a nickname such as 'Qi' or 'Qsqrt-1'
    field_label=argsdict['field_label']
    print("field label = {}".format(field_label))
    pretty_field_label = field_pretty(field_label)
    bread = [('Bianchi Modular Forms', url_for(".bianchi_modular_form_render_webpage")), (
        pretty_field_label, ' ')]
    properties = []
    t = ' '.join(['Dimensions of spaces of Bianchi modular forms over', pretty_field_label])
    C = getDBConnection()
    query = {}
    query['field_label'] = field_label
    if argsdict.get('level_norm'):
        argsdict['level_norm'] = clean_input(argsdict['level_norm'])
        ran = argsdict['level_norm']
        ran = ran.replace('..', '-').replace(' ', '')
        if not LIST_RE.match(ran):
            info['err'] = 'Error parsing input for the level norm.  It needs to be blank or an integer (such as 5), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 2,3,8 or 3-5, 7, 8-11).'
        # Past input check
        tmp = parse_range2(ran, 'level_norm')
        # work around syntax for $or
        # we have to foil out multiple or conditions
        if tmp[0] == '$or' and '$or' in query:
            newors = []
            for y in tmp[1]:
                oldors = [dict.copy(x) for x in query['$or']]
                for x in oldors:
                    x.update(y)
                newors.extend(oldors)
            tmp[1] = newors
        query[tmp[0]] = tmp[1]
    data = C.bmfs.dimensions.find(query)
    data = data.sort([('level_norm', ASCENDING)])
    print "found %s records in Bianchi dimension table for field %s" % (data.count(),field_label)
    info['field'] = field_label
    info['field_pretty'] = pretty_field_label
    nf = WebNumberField(field_label)
    info['base_galois_group'] = nf.galois_string()
    info['field_degree'] = nf.degree()
    info['field_disc'] = str(nf.disc())
    info['field_poly'] = teXify_pol(str(nf.poly()))
    weights = [str(w) for w in [2]] # need to dynamically get this from the data
    info['weights'] = weights
    info['nweights'] = len(weights)
    info['count'] = count
    info['start'] = start
    info['number'] = data.count()
    info['complete'] = int(info['number'] < info['count'])
    info['next_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(start+count), count=str(count), level_norm=argsdict.get('level_norm',''))
    info['prev_page'] = url_for(".render_bmf_field_dim_table", field_label=field_label, start=str(max(0,start-count)), count=str(count))

    dimtable = [{'level_label': dat['level_label'],
                 'level_norm': dat['level_norm'],
                 'level_space': url_for(".render_bmf_space_webpage", field_label=field_label, level_label=dat['level_label']),
                  'dims': [(dat['dimension_data'][w]['cuspidal_dim'],dat['dimension_data'][w]['new_dim']) for w in weights]} for dat in data.skip(start).limit(count)]
    info['dimtable'] = dimtable
    return render_template("bmf-field_dim_table.html", info=info, title=t, properties=properties, bread=bread)


@bmf_page.route('/<field_label>/<level_label>')
def render_bmf_space_webpage(field_label, level_label):
    info = {}
    t = "Bianchi Modular Forms of level %s over %s" % (level_label, field_label)
    credit = bianchi_credit
    bread = [('Bianchi Modular Forms', url_for(".render_bmf_space_webpage", field_label=field_label, level_label=level_label))]

    if not field_label_regex.match(field_label):
        info['err'] = "%s is not a valid label for an imaginary quadratic field" % field_label
    else:
        pretty_field_label = field_pretty(field_label)
        C = getDBConnection()
        if not C.bmfs.dimensions.find({'field_label': field_label}):
            info['err'] = "no information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi Modular Forms of level %s over %s" % (level_label, pretty_field_label)
            data = C.bmfs.dimensions.find({'field_label': field_label, 'level_label': level_label})
            n = data.count()
            if n==0:
                info['err'] = "no information exists in the database for level %s and field %s" % (level_label, pretty_field_label)
            else:
                data = data.next()
                info['label'] = data['label']
                nf = WebNumberField(field_label)
                info['base_galois_group'] = nf.galois_string()
                info['field_label'] = field_label
                info['pretty_field_label'] = pretty_field_label
                info['level_label'] = level_label
                info['level_norm'] = data['level_norm']
                info['field_degree'] = nf.degree()
                info['field_classno'] = nf.class_number()
                info['field_disc'] = str(nf.disc())
                info['field_poly'] = teXify_pol(str(nf.poly()))
                w = 'i' if nf.disc()==-4 else 'a'
                L = nf.K().change_names(w)
                phi = L.structure()[1]
                alpha = L.gen()
                info['field_gen'] = latex(alpha)
                N,c,d = [ZZ(x) for x in level_label.split('.')]
                I = L.ideal(N//d,c+d*alpha)
                info['level_gen'] = latex(I.gens_reduced()[0])
                info['level_fact'] = latex(I.factor())
                dim_data = data['dimension_data']
                for w in dim_data.keys():
                    dim_data[w]['dim']=dim_data[w]['cuspidal_dim']
                info['dim_data'] = dim_data
                weights = [str(w) for w in [2]] # need to dynamically get this from the data
                info['weights'] = weights
                info['nweights'] = len(weights)
                # info['cuspidal_dim'] = dim_data['cuspidal_dim']
                # info['new_dim'] = dim_data['new_dim']
                # info['dimension'] = info['cuspidal_dim']

    return render_template("bmf-space.html", info=info, credit=credit, title=t, bread=bread)
