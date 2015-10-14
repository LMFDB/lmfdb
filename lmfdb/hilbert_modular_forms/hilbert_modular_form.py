# -*- coding: utf-8 -*-

import re
import pymongo

import lmfdb.base
from lmfdb.base import app, getDBConnection
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
from sage.misc.preparser import preparse
from lmfdb.hilbert_modular_forms import hmf_page, hmf_logger
from lmfdb.hilbert_modular_forms.hilbert_field import findvar

import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, coeff_to_poly, pol_to_html, parse_range

from lmfdb.number_fields.number_field import parse_list, parse_field_string

from lmfdb.WebNumberField import *


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


@hmf_page.route("/")
def hilbert_modular_form_render_webpage():
    args = request.args
    if len(args) == 0:
        info = {}
        credit = 'Lassina Dembele, Steve Donnelly and <A HREF="http://www.cems.uvm.edu/~voight/">John Voight</A>'
        t = 'Hilbert Cusp Forms'
        bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage"))]
        info['learnmore'] = []
        return render_template("hilbert_modular_form_all.html", info=info, credit=credit, title=t, bread=bread)
    else:
        return hilbert_modular_form_search(**args)


def hilbert_modular_form_search(**args):
    C = getDBConnection()
    C.hmfs.forms.ensure_index([('level_norm', pymongo.ASCENDING), ('label', pymongo.ASCENDING)])

    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info:
        args = {'label': info['label']}
        return render_hmf_webpage(**args)
    query = {}
    for field in ['field_label', 'weight', 'level_norm', 'dimension']:
        if info.get(field):
            if field == 'weight':
                try:
                    parallelweight = int(info[field])
                    query['parallel_weight'] = parallelweight
                except:
                    query[field] = str(parse_list(info[field]))
            elif field == 'field_label':
                query[field] = parse_field_string(info[field])
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
    res = C.hmfs.forms.find(
        query).sort([('level_norm', pymongo.ASCENDING), ('label', pymongo.ASCENDING)]).limit(count)
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

    t = 'Hilbert Modular Form search results'

    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")), (
        'Search results', ' ')]
    properties = []
    return render_template("hilbert_modular_form_search.html", info=info, title=t, properties=properties, bread=bread)


@hmf_page.route('/<field_label>/holomorphic/<label>/download/<download_type>')
def render_hmf_webpage_download(**args):
    if args['download_type'] == 'magma':
        response = make_response(download_hmf_magma(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['download_type'] == 'sage':
        response = make_response(download_hmf_sage(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_hmf_magma(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    f = C.hmfs.forms.find_one({'label': label})
    if f is None:
        return "No such form"

    F = WebNumberField(f['field_label'])
    F_hmf = C.hmfs.fields.find_one({'label': f['field_label']})

    outstr = 'P<x> := PolynomialRing(Rationals());\n'
    outstr += 'g := P!' + str(F.coeffs()) + ';\n'
    outstr += 'F<w> := NumberField(g);\n'
    outstr += 'ZF := Integers(F);\n\n'
#    outstr += 'ideals_str := [' + ','.join([st for st in F_hmf["ideals"]]) + '];\n'
#    outstr += 'ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];\n\n'

    outstr += 'NN := ideal<ZF | {' + f["level_ideal"][1:-1] + '}>;\n\n'

    outstr += 'primesArray := [\n' + ','.join([st for st in F_hmf["primes"]]).replace('],[', '],\n[') + '];\n'
    outstr += 'primes := [ideal<ZF | {F!x : x in I}> : I in primesArray];\n\n'

    if f["hecke_polynomial"] != 'x':
        outstr += 'heckePol := ' + f["hecke_polynomial"] + ';\n'
        outstr += 'K<e> := NumberField(heckePol);\n'
    else:
        outstr += 'heckePol := x;\nK := Rationals(); e := 1;\n'

    outstr += '\nheckeEigenvaluesArray := [' + ', '.join([st for st in f["hecke_eigenvalues"]]) + '];'
    outstr += '\nheckeEigenvalues := AssociativeArray();\n'
    outstr += 'for i := 1 to #heckeEigenvaluesArray do\n  heckeEigenvalues[primes[i]] := heckeEigenvaluesArray[i];\nend for;\n\n'

    outstr += 'ALEigenvalues := AssociativeArray();\n'
    for s in f["AL_eigenvalues"]:
        outstr += 'ALEigenvalues[ideal<ZF | {' + s[0][1:-1] + '}>] := ' + s[1] + ';\n'

    outstr += '\n// EXAMPLE:\n// pp := Factorization(2*ZF)[1][1];\n// heckeEigenvalues[pp];\n\n'

    outstr += '/* EXTRA CODE: recompute eigenform (warning, may take a few minutes or longer!):\n'
    outstr += 'M := HilbertCuspForms(F, NN);\n'
    outstr += 'S := NewSubspace(M);\n'
    outstr += '// SetVerbose("ModFrmHil", 1);\n'
    outstr += 'newspaces := NewformDecomposition(S);\n'
    outstr += 'newforms := [Eigenform(U) : U in newspaces];\n'
    outstr += 'ppind := 0;\n'
    outstr += 'while #newforms gt 1 do\n'
    outstr += '  pp := primes[ppind];\n'
    outstr += '  newforms := [f : f in newforms | HeckeEigenvalue(f,pp) eq heckeEigenvalues[pp]];\n'
    outstr += 'end while;\n'
    outstr += 'f := newforms[1];\n'
    outstr += '// [HeckeEigenvalue(f,pp) : pp in primes] eq heckeEigenvaluesArray;\n'
    outstr += '*/\n'

    return outstr


def download_hmf_sage(**args):
    C = getDBConnection()
    data = None
    label = str(args['label'])
    f = C.hmfs.forms.find_one({'label': label})
    if f is None:
        return "No such form"

    F = WebNumberField(f['field_label'])
    F_hmf = C.hmfs.fields.find_one({'label': f['field_label']})

    outstr = 'P.<x> = PolynomialRing(QQ)\n'
    outstr += 'g = P(' + str(F.coeffs()) + ')\n'
    outstr += 'F.<w> = NumberField(g)\n'
    outstr += 'ZF = F.ring_of_integers()\n\n'

    outstr += 'NN = ZF.ideal(' + f["level_ideal"] + ')\n\n'

    outstr += 'primes_array = [\n' + ','.join([st for st in F_hmf["primes"]]).replace('],[',
                                                                                      '],\\\n[') + ']\n'
    outstr += 'primes = [ZF.ideal(I) for I in primes_array]\n\n'

    if f["hecke_polynomial"] != 'x':
        outstr += 'hecke_pol = ' + f["hecke_polynomial"] + '\n'
        outstr += 'K.<e> = NumberField(heckePol)\n'
    else:
        outstr += 'heckePol = x\nK = QQ\ne = 1\n'

    outstr += '\nhecke_eigenvalues_array = [' + ', '.join([st for st in f["hecke_eigenvalues"]]) + ']'
    outstr += '\nhecke_eigenvalues = {}\n'
    outstr += 'for i in range(len(hecke_eigenvalues_array)):\n    hecke_eigenvalues[primes[i]] = hecke_eigenvalues_array[i]\n\n'

    outstr += 'AL_eigenvalues = {}\n'
    for s in f["AL_eigenvalues"]:
        outstr += 'ALEigenvalues[ZF.ideal(s[0])] = s[1]\n'

    outstr += '\n# EXAMPLE:\n# pp = ZF.ideal(2).factor()[0][0]\n# hecke_eigenvalues[pp]\n'

    return outstr


@hmf_page.route('/<field_label>/holomorphic/<label>')
def render_hmf_webpage(**args):
    C = getDBConnection()
    data = None
    if 'label' in args:
        label = str(args['label'])
        data = C.hmfs.forms.find_one({'label': label})
    if data is None:
        return "No such field"
    info = {}
    try:
        info['count'] = args['count']
    except KeyError:
        info['count'] = 10

    try:
        numeigs = request.args['numeigs']
        numeigs = int(numeigs)
    except:
        numeigs = 20

    hmf_field = C.hmfs.fields.find_one({'label': data['field_label']})
    gen_name = findvar(hmf_field['ideals'])
    nf = WebNumberField(data['field_label'], gen_name=gen_name)
    info['field'] = nf
    info['base_galois_group'] = nf.galois_string()
    info['field_degree'] = nf.degree()
    info['field_disc'] = str(nf.disc())
    info['field_poly'] = teXify_pol(str(nf.poly()))

    info.update(data)

    info['downloads'] = [
        ('Download to Magma', url_for(".render_hmf_webpage_download", field_label=info['field_label'], label=info['label'], download_type='magma')),
        ('Download to Sage', url_for(".render_hmf_webpage_download", field_label=info['field_label'], label=info['label'], download_type='sage'))
        ]
    info['friends'] = []
    info['friends'] = [('L-function',
                        url_for("l_functions.l_function_hmf_page", field=info['field_label'], label=info['label'], character='0', number='0'))]

# info['learnmore'] = [('Number Field labels',
# url_for("render_labels_page")), ('Galois group
# labels',url_for("render_groups_page")), ('Discriminant
# ranges',url_for("render_discriminants_page"))]

    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")), ('%s' % data[
                                                                                         'label'], ' ')]

    t = "Hilbert Cusp Form %s" % info['label']
    credit = 'Lassina Dembele, Steve Donnelly and <A HREF="http://www.cems.uvm.edu/~voight/">John Voight</A>'

    forms_space = C.hmfs.forms.find(
        {'field_label': data['field_label'], 'level_ideal': data['level_ideal']})
    dim_space = 0
    for v in forms_space:
        dim_space += v['dimension']

    info['newspace_dimension'] = dim_space

    w = polygen(QQ, 'w')
    e = polygen(QQ, 'e')
    eigs = data['hecke_eigenvalues']
    eigs = eigs[:min(len(eigs), numeigs)]

    primes = hmf_field['primes']
    n = min(len(eigs), len(primes))
    info['eigs'] = [{'eigenvalue': teXify_pol(eigs[i]),
                     'prime_ideal': teXify_pol(primes[i]),
                     'prime_norm': primes[i][1:primes[i].index(',')]} for i in range(n)]

    try:
        display_eigs = request.args['display_eigs']
        if display_eigs in ['True', 'true', '1', 'yes']:
            display_eigs = True
        else:
            display_eigs = False
    except KeyError:
        display_eigs = False

    if 'numeigs' in request.args:
        display_eigs = True

    info['hecke_polynomial'] = teXify_pol(info['hecke_polynomial'])

    if 'AL_eigenvalues_fixed' in data:
        if data['AL_eigenvalues_fixed'] == 'done':
            info['AL_eigs'] = [{'eigenvalue': teXify_pol(al[1]),
                                'prime_ideal': teXify_pol(al[0]),
                                'prime_norm': al[0][1:al[0].index(',')]} for al in data['AL_eigenvalues']]
        else:
            info['AL_eigs'] = [{'eigenvalue': '?', 'prime_ideal': '?'}]
    else:
        info['AL_eigs'] = [{'eigenvalue': '?', 'prime_ideal': '?'}]
    info['AL_eigs_count'] = len(info['AL_eigs']) != 0

    if not display_eigs:
        for eig in info['eigs']:
            if len(eig['eigenvalue']) > 300:
                eig['eigenvalue'] = '...'
        for eig in info['AL_eigs']:
            if len(eig['eigenvalue']) > 300:
                eig['eigenvalue'] = '...'

    info['level_ideal'] = teXify_pol(info['level_ideal'])

    if 'is_CM' in data:
        is_CM = data['is_CM']
    else:
        is_CM = '?'
    info['is_CM'] = is_CM

    if 'is_base_change' in data:
        is_base_change = data['is_base_change']
    else:
        is_base_change = '?'
    info['is_base_change'] = is_base_change

    if 'q_expansions' in data:
        info['q_expansions'] = data['q_expansions']

    properties2 = [('Base Field', '%s' % info['field'].field_pretty()),
                   ('Weight', '%s' % data['weight']),
                   ('Level Norm', '%s' % data['level_norm']),
                   ('Level', '$' + teXify_pol(data['level_ideal']) + '$'),
                   ('Label', '%s' % data['label_suffix']),
                   ('Dimension', '%s' % data['dimension']),
                   ('CM', is_CM),
                   ('Base Change', is_base_change)
                   ]

    return render_template("hilbert_modular_form.html", downloads=info["downloads"], info=info, properties2=properties2, credit=credit, title=t, bread=bread, friends=info['friends'])
