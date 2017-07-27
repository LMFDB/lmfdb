# -*- coding: utf-8 -*-

import pymongo

from lmfdb.base import getDBConnection
from flask import render_template, url_for, request, redirect, make_response, flash

from lmfdb.hilbert_modular_forms import hmf_page
from lmfdb.hilbert_modular_forms.hilbert_field import findvar
from lmfdb.hilbert_modular_forms.hmf_stats import get_stats, get_counts, hmf_degree_summary

from lmfdb.ecnf.main import split_class_label
from lmfdb.ecnf.WebEllipticCurve import db_ecnf

from lmfdb.WebNumberField import WebNumberField

from markupsafe import Markup
from lmfdb.utils import to_dict, random_object_from_collection, web_latex_split_on_pm
from lmfdb.search_parsing import parse_nf_string, parse_ints, parse_hmf_weight, parse_count, parse_start

hmf_credit =  'John Cremona, Lassina Dembele, Steve Donnelly, Aurel Page and <A HREF="http://www.math.dartmouth.edu/~jvoight/">John Voight</A>'


@hmf_page.route("/random")
def random_hmf():    # Random Hilbert modular form
    return hilbert_modular_form_by_label( random_object_from_collection( getDBConnection().hmfs.forms ) )

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
        t = 'Hilbert Modular Forms'
        bread = [("Modular Forms", url_for('mf.modular_form_main_page')),
                 ('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage"))]
        info['learnmore'] = []
        info['counts'] = get_counts()
        return render_template("hilbert_modular_form_all.html", info=info, credit=hmf_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))
    else:
        return hilbert_modular_form_search(**args)



def split_full_label(lab):
    r""" Split a full hilbert modular form label into 3 components
    (field_label, level_label, label_suffix)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid Hilbert modular form label. It must be of the form (number field label) - (level label) - (orbit label) separated by dashes, such as 2.2.5.1-31.1-a" % lab), "error")
        raise ValueError
    field_label = data[0]
    level_label = data[1]
    label_suffix = data[2]
    return (field_label, level_label, label_suffix)

def hilbert_modular_form_by_label(lab):
    if isinstance(lab, basestring):
        C = getDBConnection()
        res = C.hmfs.forms.search.find_one({'label': lab},{'label':True})
    else:
        res = lab
        lab = res['label']
    if res == None:
        flash(Markup("No Hilbert modular form in the database has label or name <span style='color:black'>%s</span>" % lab), "error")
        return redirect(url_for(".hilbert_modular_form_render_webpage"))
    else:
        return redirect(url_for(".render_hmf_webpage", field_label=split_full_label(lab)[0], label=lab))


def hilbert_modular_form_search(**args):
    info = to_dict(args)  # what has been entered in the search boxes
    if 'label' in info and info['label']:
        lab=info['label'].strip()
        info['label']=lab
        try:
            split_full_label(lab)
            return hilbert_modular_form_by_label(lab)
        except ValueError:
            return redirect(url_for(".hilbert_modular_form_render_webpage"))

    query = {}
    try:
        parse_nf_string(info,query,'field_label',name="Field")
        parse_ints(info,query,'deg', name='Field degree')
        parse_ints(info,query,'disc',name="Field discriminant")
        parse_ints(info,query,'dimension')
        parse_ints(info,query,'level_norm', name="Level norm")
        parse_hmf_weight(info,query,'weight',qfield=('parallel_weight','weight'))
    except ValueError:
        return search_input_error()
        
    if 'cm' in info:
        if info['cm'] == 'exclude':
            query['is_CM'] = 'no'
        elif info['cm'] == 'only':
            query['is_CM'] = 'yes'
                
    if 'bc' in info:
        if info['bc'] == 'exclude':
            query['is_base_change'] = 'no'
        elif info['bc'] == 'only':
            query['is_base_change'] = 'yes'
                     
    count = parse_count(info,100)
    start = parse_start(info)

    info['query'] = dict(query)
    C = getDBConnection()
    res = C.hmfs.forms.search.find(
        query).sort([('deg', pymongo.ASCENDING), ('disc', pymongo.ASCENDING), ('level_norm', pymongo.ASCENDING), ('level_label', pymongo.ASCENDING), ('label_nsuffix', pymongo.ASCENDING)]).skip(start).limit(count)
    nres = res.count()
    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['number'] = nres
    info['start'] = start
    info['more'] = int(start + count < nres)
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres == 0:
            info['report'] = 'no matches'
        else:
            if nres > count or start != 0:
                info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
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
    return render_template("hilbert_modular_form_search.html", info=info, title=t, credit=hmf_credit, properties=properties, bread=bread, learnmore=learnmore_list())

def search_input_error(info = None, bread = None):
    if info is None: info = {'err':''}
    if bread is None: bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")), ('Search results', ' ')]
    return render_template("hilbert_modular_form_search.html", info=info, title="Hilbert Modular Form Search Error", bread=bread)

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
        outstr += 'heckePol = ' + f["hecke_polynomial"] + '\n'
        outstr += 'K.<e> = NumberField(heckePol)\n'
    else:
        outstr += 'heckePol = x\nK = QQ\ne = 1\n'

    outstr += '\nhecke_eigenvalues_array = [' + ', '.join([st for st in f["hecke_eigenvalues"]]) + ']'
    outstr += '\nhecke_eigenvalues = {}\n'
    outstr += 'for i in range(len(hecke_eigenvalues_array)):\n    hecke_eigenvalues[primes[i]] = hecke_eigenvalues_array[i]\n\n'

    outstr += 'AL_eigenvalues = {}\n'
    for s in f["AL_eigenvalues"]:
        outstr += 'AL_eigenvalues[ZF.ideal(%s)] = %s\n' % (s[0],s[1])

    outstr += '\n# EXAMPLE:\n# pp = ZF.ideal(2).factor()[0][0]\n# hecke_eigenvalues[pp]\n'

    return outstr


@hmf_page.route('/<field_label>/holomorphic/<label>')
def render_hmf_webpage(**args):
    C = getDBConnection()
    if 'data' in args:
        data = args['data']
        label = data['label']
    else:
        label = str(args['label'])
        data = C.hmfs.forms.find_one({'label': label})
    if data is None:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid Hilbert modular form label. It must be of the form (number field label) - (level label) - (orbit label) separated by dashes, such as 2.2.5.1-31.1-a" % args['label']), "error")
        return search_input_error()
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
    info['numeigs'] = numeigs

    hmf_field = C.hmfs.fields.find_one({'label': data['field_label']})
    gen_name = findvar(hmf_field['ideals'])
    nf = WebNumberField(data['field_label'], gen_name=gen_name)
    info['hmf_field'] = hmf_field
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
    if hmf_field['narrow_class_no'] == 1 and nf.disc()**2 * data['level_norm'] < 40000:
        info['friends'] = [('L-function',
                            url_for("l_functions.l_function_hmf_page", field=info['field_label'], label=info['label'], character='0', number='0'))]
    else:
        info['friends'] = [('L-function not available', "")]
    if data['dimension'] == 1:   # Try to attach associated elliptic curve
        lab = split_class_label(info['label'])
        ec_from_hmf = db_ecnf().find_one({"label": label + '1'})
        if ec_from_hmf == None:
            info['friends'] += [('Elliptic curve not available', "")]
        else:
            info['friends'] += [('Isogeny class ' + info['label'], url_for("ecnf.show_ecnf_isoclass", nf=lab[0], conductor_label=lab[1], class_label=lab[2]))]

    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")), ('%s' % data[
                                                                                         'label'], ' ')]

    t = "Hilbert Cusp Form %s" % info['label']

    forms_space = C.hmfs.forms.search.find(
        {'field_label': data['field_label'], 'level_ideal': data['level_ideal']},{'dimension':True})
    dim_space = 0
    for v in forms_space:
        dim_space += v['dimension']

    info['newspace_dimension'] = dim_space

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

    info['hecke_polynomial'] = web_latex_split_on_pm(teXify_pol(info['hecke_polynomial']))

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

    max_eig_len = max([len(eig['eigenvalue']) for eig in info['eigs']])
    display_eigs = display_eigs or (max_eig_len<=300)
    info['display_eigs'] = display_eigs
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

    properties2 = [('Base field', '%s' % info['field'].field_pretty()),
                   ('Weight', '%s' % data['weight']),
                   ('Level norm', '%s' % data['level_norm']),
                   ('Level', '$' + teXify_pol(data['level_ideal']) + '$'),
                   ('Label', '%s' % data['label']),
                   ('Dimension', '%s' % data['dimension']),
                   ('CM', is_CM),
                   ('Base change', is_base_change)
                   ]

    return render_template("hilbert_modular_form.html", downloads=info["downloads"], info=info, properties2=properties2, credit=hmf_credit, title=t, bread=bread, friends=info['friends'], learnmore=learnmore_list())



# Learn more box

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Labels for Hilbert Modular Forms', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())



#data quality pages
@hmf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of the Hilbert Modular Forms data'
    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")),
             ('Completeness', '')]
    return render_template("single.html", kid='dq.mf.hilbert.extent',
                           credit=hmf_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@hmf_page.route("/Source")
def how_computed_page():
    t = 'Source of the Hilbert Modular Forms data'
    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")),
             ('Source', '')]
    return render_template("single.html", kid='dq.mf.hilbert.source',
                           credit=hmf_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@hmf_page.route("/Labels")
def labels_page():
    t = 'Label of an Hilbert Modular Form'
    bread = [('Hilbert Modular Forms', url_for(".hilbert_modular_form_render_webpage")),
             ('Labels', '')]
    return render_template("single.html", kid='mf.hilbert.label',
                           credit=hmf_credit, title=t, bread=bread, learnmore=learnmore_list_remove('Labels'))

@hmf_page.route("/browse/")
def browse():
    info = {
        'counts': get_counts()
    }
    credit = 'John Voight'
    t = 'Hilbert modular forms'
    bread = [('Hilbert modular forms', url_for("hmf.hilbert_modular_form_render_webpage")),
             ('browse', ' ')]
    return render_template("hmf_stats.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove("Completeness"))

@hmf_page.route("/browse/<int:d>/")
def statistics_by_degree(d):
    counts = get_counts()
    info = {}
    if not d in counts['degrees']:
        if d==1:
            info['error'] = "For modular forms over $\mathbb{Q}$ go <a href=%s>here</a>" % url_for('emf.render_elliptic_modular_forms')
        else:
            info['error'] = "The database does not contain any Hilbert modular forms over fields of degree %s" % d
        d = 'bad'
    else:
        info['counts'] = counts
        info['degree_stats'] = hmf_degree_summary(d)
        info['degree'] = d
        info['stats'] = get_stats(d)

    credit = 'John Cremona'
    if d==2:
        t = 'Hilbert modular forms over real quadratic number fields'
    elif d==3:
        t = 'Hilbert modular forms over totally real cubic number fields'
    elif d==4:
        t = 'Hilbert modular forms over totally real quartic number fields'
    elif d==5:
        t = 'Hilbert modular forms over totally real quintic number fields'
    elif d==6:
        t = 'Hilbert modular forms over totally real sextic number fields'
    else:
        t = 'Hilbert modular forms over totally real fields of degree %s' % d

    bread = [('Hilbert modular forms', url_for("hmf.hilbert_modular_form_render_webpage")),
              ('degree %s' % d,' ')]

    if d=='bad':
        t = 'Hilbert modular forms'
        bread = bread[:-1]

    return render_template("hmf_by_degree.html", info=info, credit=credit, title=t, bread=bread, learnmore=learnmore_list_remove("Completeness"))

