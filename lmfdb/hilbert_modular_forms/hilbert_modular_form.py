# -*- coding: utf-8 -*-
from flask import abort, render_template, url_for, request, redirect, make_response

from lmfdb import db
from lmfdb.utils import (
    flash_error, to_dict,
    parse_nf_string, parse_ints, parse_hmf_weight, parse_primes,
    teXify_pol, add_space_if_positive,
    SearchArray, TextBox, ExcludeOnlyBox, CountBox, SubsetBox, TextBoxWithSelect,
    search_wrap, redirect_no_cache)
from lmfdb.ecnf.main import split_class_label
from lmfdb.number_fields.number_field import field_pretty, FIELD_LABEL_RE
from lmfdb.number_fields.web_number_field import nf_display_knowl, WebNumberField
from lmfdb.hilbert_modular_forms import hmf_page
from lmfdb.hilbert_modular_forms.hilbert_field import findvar
from lmfdb.hilbert_modular_forms.hmf_stats import HMFstats
from lmfdb.utils import names_and_urls, prop_int_pretty
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url, get_instances_by_Lhash_and_trace_hash

import re
HMF_LABEL_RE = re.compile("^"+FIELD_LABEL_RE.pattern[1:-1] + r"-\d+\.\d+-[a-z]+$")

def get_bread(tail=[]):
    base = [("Modular forms", url_for('modular_forms')),
            ('Hilbert', url_for(".hilbert_modular_form_render_webpage"))]
    if isinstance(tail, list):
        return base + tail
    else:
        return base + [(tail, " ")]

def get_hmf(label):
    """Return a complete HMF, given its label.  Note that the
    hecke_polynomial, hecke_eigenvalues and AL_eigenvalues may be in a
    separate collection.  Use of this function hides this
    implementation detail from the user.
    """
    f = db.hmf_forms.lookup(label)
    if f is None:
        return None
    if 'hecke_polynomial' not in f:
        # Hecke data now stored in separate hecke collection:
        h = db.hmf_hecke.lookup(label)
        if h:
            f.update(h)
    return f

def get_hmf_field(label):
    """Return a field from the HMF fields collection, given its label.
    Use of this function hides implementation detail from the user.
    """
    return db.hmf_fields.lookup(label)

@hmf_page.route("/random")
@redirect_no_cache
def random_hmf():    # Random Hilbert modular form
    return url_for_label(db.hmf_forms.random())

@hmf_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "mf.hilbert",
        db.hmf_forms,
        url_for_label,
        title="Some interesting Hilbert modular forms",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@hmf_page.route("/")
def hilbert_modular_form_render_webpage():
    info = to_dict(request.args, search_array=HMFSearchArray())
    if not request.args:
        t = 'Hilbert modular forms'
        info['stats'] = HMFstats()
        info['counts'] = HMFstats().counts()
        return render_template("hilbert_modular_form_all.html", info=info, title=t, bread=get_bread(), learnmore=learnmore_list())
    else:
        return hilbert_modular_form_search(info)

def split_full_label(lab):
    r""" Split a full hilbert modular form label into 3 components
    (field_label, level_label, label_suffix)
    """
    data = lab.split("-")
    if len(data) != 3:
        flash_error("%s is not a valid Hilbert modular form label. It must be of the form (number field label) - (level label) - (orbit label) separated by dashes, such as 2.2.5.1-31.1-a", lab)
        raise ValueError
    field_label = data[0]
    level_label = data[1]
    label_suffix = data[2]
    return (field_label, level_label, label_suffix)

def url_for_label(label):
    return url_for('.render_hmf_webpage',
                   field_label=split_full_label(label)[0],
                   label=label)


def hilbert_modular_form_by_label(lab):
    if isinstance(lab, str):
        res = db.hmf_forms.lookup(lab, projection=0)
    else:
        res = lab
        lab = res['label']
    if res is None:
        flash_error("No Hilbert modular form in the database has label or name %s", lab)
        return redirect(url_for(".hilbert_modular_form_render_webpage"))
    else:
        return redirect(url_for_label(lab))

# Learn more box

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Hilbert modular form labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def hilbert_modular_form_jump(info):
    lab = info['jump'].strip()
    info['label'] = lab
    try:
        split_full_label(lab)
        return hilbert_modular_form_by_label(lab)
    except ValueError:
        return redirect(url_for(".hilbert_modular_form_render_webpage"))

hmf_columns = SearchColumns([
    MultiProcessedCol("label", "mf.hilbert.label", "Label",
                      ["field_label", "label", "short_label"],
                      lambda fld, label, short: '<a href="%s">%s</a>' % (url_for('hmf.render_hmf_webpage', field_label=fld, label=label), short),
                      default=True),
    ProcessedCol("field_label", "nf", "Base field", lambda fld: nf_display_knowl(fld, field_pretty(fld)), default=True),
    MathCol("deg", "nf.degree", "Field degree"),
    MathCol("disc", "nf.discriminant", "Field discriminant"),
    ProcessedCol("level_ideal", "mf.hilbert.level_norm", "Level", teXify_pol, mathmode=True, default=True),
    MathCol("level_norm", "mf.level_norm", "Level norm"),
    MathCol("weight", "mf.hilbert.weight_vector", "Weight"),
    MathCol("dimension", "mf.hilbert.dimension", "Dimension", default=True),
    ProcessedCol("is_CM", "mf.cm", "CM", lambda cm: "&#x2713;" if cm=="yes" else "", short_title="CM", align="center"),
    ProcessedCol("is_base_change", "mf.base_change", "Base change", lambda bc: "&#x2713;" if bc=="yes" else "", align="center")])
hmf_columns.dummy_download = True

@search_wrap(table=db.hmf_forms,
             title='Hilbert modular form search results',
             err_title='Hilbert modular form search error',
             columns=hmf_columns,
             per_page=50,
             shortcuts={'jump':hilbert_modular_form_jump},
             bread=lambda: get_bread("Search results"),
             learnmore=learnmore_list,
             url_for_label=url_for_label,
             properties=lambda: [])
def hilbert_modular_form_search(info, query):
    parse_nf_string(info,query,'field_label',name="Field")
    parse_ints(info,query,'deg', name='Field degree')
    parse_ints(info,query,'disc',name="Field discriminant")
    parse_ints(info,query,'dimension')
    parse_ints(info,query,'level_norm', name="Level norm")
    parse_hmf_weight(info,query,'weight',qfield=('parallel_weight','weight'))
    parse_primes(info, query, 'field_bad_primes', name='field bad primes',
         qfield='field_bad_primes',mode=info.get('field_bad_quantifier'))
    parse_primes(info, query, 'level_bad_primes', name='level bad primes',
         qfield='level_bad_primes',mode=info.get('level_bad_quantifier'))
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


def search_input_error(info=None, bread=None):
    if info is None:
        info = {'err': ''}
    info['search_array'] = HMFSearchArray()
    info['columns'] = hmf_columns
    if bread is None:
        bread = get_bread("Search results")
    return render_template("search_results.html",
                           info=info,
                           title="Hilbert modular forms search error",
                           bread=bread)


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
    label = str(args['label'])
    f = get_hmf(label)
    if f is None:
        return "No such form"

    F = WebNumberField(f['field_label'])
    F_hmf = get_hmf_field(f['field_label'])

    hecke_pol  = f['hecke_polynomial']
    hecke_eigs = [str(eig) for eig in f['hecke_eigenvalues']]
    AL_eigs    = f['AL_eigenvalues']

    outstr = '/*\n  This code can be loaded, or copied and pasted, into Magma.\n'
    outstr += '  It will load the data associated to the HMF, including\n'
    outstr += '  the field, level, and Hecke and Atkin-Lehner eigenvalue data.\n'
    outstr += '  At the *bottom* of the file, there is code to recreate the\n'
    outstr += '  Hilbert modular form in Magma, by creating the HMF space\n'
    outstr += '  and cutting out the corresponding Hecke irreducible subspace.\n'
    outstr += '  From there, you can ask for more eigenvalues or modify as desired.\n'
    outstr += '  It is commented out, as this computation may be lengthy.\n'
    outstr += '*/\n\n'

    outstr += 'P<x> := PolynomialRing(Rationals());\n'
    outstr += 'g := P!' + str(F.coeffs()) + ';\n'
    outstr += 'F<w> := NumberField(g);\n'
    outstr += 'ZF := Integers(F);\n\n'
#    outstr += 'ideals_str := [' + ','.join([st for st in F_hmf["ideals"]]) + '];\n'
#    outstr += 'ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];\n\n'

    outstr += 'NN := ideal<ZF | {' + f["level_ideal"][1:-1] + '}>;\n\n'

    outstr += 'primesArray := [\n' + ','.join(F_hmf["primes"]).replace('],[', '],\n[') + '];\n'
    outstr += 'primes := [ideal<ZF | {F!x : x in I}> : I in primesArray];\n\n'

    if hecke_pol != 'x':
        outstr += 'heckePol := ' + hecke_pol + ';\n'
        outstr += 'K<e> := NumberField(heckePol);\n'
    else:
        outstr += 'heckePol := x;\nK := Rationals(); e := 1;\n'

    outstr += '\nheckeEigenvaluesArray := [' + ', '.join(hecke_eigs) + '];'
    outstr += '\nheckeEigenvalues := AssociativeArray();\n'
    outstr += 'for i := 1 to #heckeEigenvaluesArray do\n  heckeEigenvalues[primes[i]] := heckeEigenvaluesArray[i];\nend for;\n\n'

    outstr += 'ALEigenvalues := AssociativeArray();\n'
    for s in AL_eigs:
        outstr += 'ALEigenvalues[ideal<ZF | {' + s[0][1:-1] + '}>] := ' + str(s[1]) + ';\n'

    outstr += '\n// EXAMPLE:\n// pp := Factorization(2*ZF)[1][1];\n// heckeEigenvalues[pp];\n\n'

    outstr += '\n'.join([
        'print "To reconstruct the Hilbert newform f, type',
        '  f, iso := Explode(make_newform());";',
        '',
        'function make_newform();',
        ' M := HilbertCuspForms(F, NN);',
        ' S := NewSubspace(M);',
        ' // SetVerbose("ModFrmHil", 1);',
        ' NFD := NewformDecomposition(S);',
        ' newforms := [* Eigenform(U) : U in NFD *];',
        '',
        ' if #newforms eq 0 then;',
        '  print "No Hilbert newforms at this level";',
        '  return 0;',
        ' end if;',
        '',
        ' print "Testing ", #newforms, " possible newforms";',
        ' newforms := [* f: f in newforms | IsIsomorphic(BaseField(f), K) *];',
        ' print #newforms, " newforms have the correct Hecke field";',
        '',
        ' if #newforms eq 0 then;',
        '  print "No Hilbert newform found with the correct Hecke field";',
        '  return 0;',
        ' end if;',
        '',
        ' autos := Automorphisms(K);',
        ' xnewforms := [* *];',
        ' for f in newforms do;',
        '  if K eq RationalField() then;',
        '   Append(~xnewforms, [* f, autos[1] *]);',
        '  else;',
        '   flag, iso := IsIsomorphic(K,BaseField(f));',
        '   for a in autos do;',
        '    Append(~xnewforms, [* f, a*iso *]);',
        '   end for;',
        '  end if;',
        ' end for;',
        ' newforms := xnewforms;',
        '',
        ' for P in primes do;',
        '  xnewforms := [* *];',
        '  for f_iso in newforms do;',
        '   f, iso := Explode(f_iso);',
        '   if HeckeEigenvalue(f,P) eq iso(heckeEigenvalues[P]) then;',
        '    Append(~xnewforms, f_iso);',
        '   end if;',
        '  end for;',
        '  newforms := xnewforms;',
        '  if #newforms eq 0 then;',
        '   print "No Hilbert newform found which matches the Hecke eigenvalues";',
        '   return 0;',
        '  else if #newforms eq 1 then;',
        '   print "success: unique match";',
        '   return newforms[1];',
        '  end if;',
        '  end if;',
        ' end for;',
        ' print #newforms, "Hilbert newforms found which match the Hecke eigenvalues";',
        ' return newforms[1];',
        '',
        'end function;'])

    return outstr


def download_hmf_sage(**args):
    label = str(args['label'])
    f = get_hmf(label)
    if f is None:
        return "No such form"

    hecke_pol  = f['hecke_polynomial']
    hecke_eigs = [str(eig) for eig in f['hecke_eigenvalues']]
    AL_eigs    = f['AL_eigenvalues']

    F = WebNumberField(f['field_label'])
    F_hmf = get_hmf_field(f['field_label'])

    outstr = '/*\n  This code can be loaded, or copied and paste using cpaste, into Sage.\n'
    outstr += '  It will load the data associated to the HMF, including\n'
    outstr += '  the field, level, and Hecke and Atkin-Lehner eigenvalue data.\n'
    outstr += '*/\n\n'

    outstr += 'P.<x> = PolynomialRing(QQ)\n'
    outstr += 'g = P(' + str(F.coeffs()) + ')\n'
    outstr += 'F.<w> = NumberField(g)\n'
    outstr += 'ZF = F.ring_of_integers()\n\n'

    outstr += 'NN = ZF.ideal(' + f["level_ideal"] + ')\n\n'

    outstr += 'primes_array = [\n' + ','.join(F_hmf["primes"]).replace('],[',
                                                                                      '],\\\n[') + ']\n'
    outstr += 'primes = [ZF.ideal(I) for I in primes_array]\n\n'

    if hecke_pol != 'x':
        outstr += 'heckePol = ' + hecke_pol + '\n'
        outstr += 'K.<e> = NumberField(heckePol)\n'
    else:
        outstr += 'heckePol = x\nK = QQ\ne = 1\n'

    outstr += '\nhecke_eigenvalues_array = [' + ', '.join(hecke_eigs) + ']'
    outstr += '\nhecke_eigenvalues = {}\n'
    outstr += 'for i in range(len(hecke_eigenvalues_array)):\n    hecke_eigenvalues[primes[i]] = hecke_eigenvalues_array[i]\n\n'

    outstr += 'AL_eigenvalues = {}\n'
    for s in AL_eigs:
        outstr += 'AL_eigenvalues[ZF.ideal(%s)] = %s\n' % (s[0],s[1])

    outstr += '\n# EXAMPLE:\n# pp = ZF.ideal(2).factor()[0][0]\n# hecke_eigenvalues[pp]\n'

    return outstr


@hmf_page.route('/<field_label>/holomorphic/<label>')
def render_hmf_webpage(**args):
    if 'data' in args:
        data = args['data']
        label = data['label']
    else:
        label = str(args['label'])
        data = get_hmf(label)
    if data is None:
        flash_error("%s is not a valid Hilbert modular form label. It must be of the form (number field label) - (level label) - (orbit label) separated by dashes, such as 2.2.5.1-31.1-a", args['label'])
        return search_input_error()
    info = {}
    try:
        info['count'] = args['count']
    except KeyError:
        info['count'] = 50

    hmf_field = get_hmf_field(data['field_label'])
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
        ('Modular form to Magma', url_for(".render_hmf_webpage_download", field_label=info['field_label'], label=info['label'], download_type='magma')),
        ('Eigenvalues to Sage', url_for(".render_hmf_webpage_download", field_label=info['field_label'], label=info['label'], download_type='sage')),
        ('Underlying data', url_for(".hmf_data", label=info['label'])),
        ]


    # figure out friends
    # first try to see if there is an instance of this HMF on Lfun db
    url = 'ModularForm/GL2/TotallyReal/{}/holomorphic/{}'.format(
            info['field_label'],
            info['label'])
    Lfun = get_lfunction_by_url(url)
    if Lfun:
        instances = get_instances_by_Lhash_and_trace_hash(Lfun['Lhash'],
                                                          Lfun['degree'],
                                                          Lfun['trace_hash'])

        # This will also add the EC/G2C, as this how the Lfun was computed
        info['friends'] = names_and_urls(instances, exclude={url})

        info['friends'] += [('L-function',
                            url_for("l_functions.l_function_hmf_page", field=info['field_label'], label=info['label'], character='0', number='0'))]

    else:
        # if there is no instance
        # old code
        if hmf_field['narrow_class_no'] == 1 and nf.disc()**2 * data['level_norm'] < 40000:
            info['friends'] = [('L-function',
                                url_for("l_functions.l_function_hmf_page", field=info['field_label'], label=info['label'], character='0', number='0'))]
        else:
            info['friends'] = [('L-function not available', "")]


        if data['dimension'] == 1:   # Try to attach associated elliptic curve
            lab = split_class_label(info['label'])
            ec_from_hmf = db.ec_nfcurves.lookup(label + '1')
            if ec_from_hmf is None:
                info['friends'] += [('Elliptic curve not available', "")]
            else:
                info['friends'] += [('Isogeny class ' + info['label'], url_for("ecnf.show_ecnf_isoclass", nf=lab[0], conductor_label=lab[1], class_label=lab[2]))]

    bread = get_bread(data["label"])
    t = "Hilbert cusp form %s" % info['label']

    forms_dims = db.hmf_forms.search({'field_label': data['field_label'], 'level_ideal': data['level_ideal']}, projection='dimension')

    info['newspace_dimension'] = sum(forms_dims)

    # Get hecke_polynomial, hecke_eigenvalues and AL_eigenvalues
    try:
        numeigs = request.args['numeigs']
        numeigs = int(numeigs)
    except Exception:
        numeigs = 20
    info['numeigs'] = numeigs

    hecke_pol  = data['hecke_polynomial']
    eigs       = [str(eig) for eig in data['hecke_eigenvalues']]
    eigs = eigs[:min(len(eigs), numeigs)]
    AL_eigs    = data['AL_eigenvalues']

    primes = hmf_field['primes']
    n = min(len(eigs), len(primes))
    info['eigs'] = [{'eigenvalue': add_space_if_positive(teXify_pol(eigs[i])),
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

    info['hecke_polynomial'] = r"\(" + teXify_pol(hecke_pol) + r"\)"

    if not AL_eigs: # empty list
        if data['level_norm'] == 1: # OK, no bad primes
            info['AL_eigs'] = 'none'
        else:                     # not OK, AL eigs are missing
            info['AL_eigs'] = 'missing'
    else:
        info['AL_eigs'] = [{'eigenvalue': teXify_pol(al[1]),
                            'prime_ideal': teXify_pol(al[0]),
                            'prime_norm': al[0][1:al[0].index(',')]} for al in data['AL_eigenvalues']]

    max_eig_len = max([len(eig['eigenvalue']) for eig in info['eigs']])
    display_eigs = display_eigs or (max_eig_len<=300)
    info['display_eigs'] = display_eigs
    if not display_eigs:
        for eig in info['eigs']:
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

    properties = [
        ('Label', '%s' % data['label']),
        ('Base field', '%s' % info['field'].field_pretty()),
        ('Weight', '$%s$' % data['weight']),
        ('Level norm', prop_int_pretty(data['level_norm'])),
        ('Level', '$' + teXify_pol(data['level_ideal']) + '$'),
        ('Dimension', prop_int_pretty(data['dimension'])),
        ('CM', is_CM),
        ('Base change', is_base_change)
    ]

    return render_template(
        "hilbert_modular_form.html",
        downloads=info["downloads"],
        info=info,
        properties=properties,
        title=t,
        bread=bread,
        friends=info['friends'],
        learnmore=learnmore_list(),
        KNOWL_ID="mf.hilbert.%s"%label,
    )

@hmf_page.route("/data/<label>")
def hmf_data(label):
    if not HMF_LABEL_RE.match(label):
        return abort(404, f"Invalid label {label}")
    field_label = label.split("-")[0]
    title = f"Hilbert modular form data - {label}"
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    return datapage([label, label, field_label, field_label], ["hmf_forms", "hmf_hecke", "hmf_fields", "nf_fields"], title=title, bread=bread)

#data quality pages
@hmf_page.route("/Source")
def how_computed_page():
    t = 'Source and acknowledgments for Hilbert modular form data'
    bread = get_bread("Source")
    return render_template("multi.html", kids=['rcs.source.mf.hilbert',
                                               'rcs.ack.mf.hilbert',
                                               'rcs.cite.mf.hilbert'],
                           title=t, bread=bread, learnmore=learnmore_list_remove('Source'))

@hmf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Hilbert modular form data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.mf.hilbert',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))
@hmf_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of Hilbert modular form data'
    bread = get_bread("Reliability")
    return render_template("single.html", kid='rcs.rigor.mf.hilbert',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@hmf_page.route("/Labels")
def labels_page():
    t = 'Labels for Hilbert Modular forms'
    bread = get_bread("Labels")
    return render_template("single.html", kid='mf.hilbert.label',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))

@hmf_page.route("/browse/")
def browse():
    t = 'Hilbert modular forms'
    bread = get_bread("Browse")
    return render_template("hmf_stats.html", info=HMFstats(), title=t, bread=bread, learnmore=learnmore_list())

@hmf_page.route("/stats")
def statistics():
    title = r'Hilbert modular forms: statistics'
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=HMFstats(), title=title, bread=bread, learnmore=learnmore_list())

@hmf_page.route("/browse/<int:d>/")
def statistics_by_degree(d):
    counts = HMFstats().counts()
    info = {}
    if d not in counts['degrees']:
        if d==1:
            info['error'] = r"For modular forms over $\mathbb{Q}$ go <a href=%s>here</a>" % url_for('cmf.index')
        else:
            info['error'] = "The database does not contain any Hilbert modular forms over fields of degree %s" % d
        d = 'bad'
    else:
        info['counts'] = counts
        info['degree_stats'] = HMFstats().degree_summary(d)
        info['degree'] = d
        info['stats'] = HMFstats().statistics(d)

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

    bread = get_bread("Degree %s" % d)

    if d=='bad':
        t = 'Hilbert modular forms'
        bread = bread[:-1]

    return render_template("hmf_by_degree.html", info=info, title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))


class HMFSearchArray(SearchArray):
    noun = "form"
    plural_noun = "forms"
    sorts = [("", "base field", ['deg', 'disc', 'level_norm', 'level_label', 'label_nsuffix']),
             ("level_norm", "level norm", ['level_norm', 'deg', 'disc', 'level_label', 'label_nsuffix']),
             ("dimension", "dimension", ['dimension', 'deg', 'disc', 'level_norm', 'level_label', 'label_nsuffix'])]
    jump_example = "2.2.5.1-31.1-a"
    jump_egspan = "e.g. 2.2.5.1-31.1-a"
    jump_knowl = "mf.hilbert.search_input"
    jump_prompt = "Label"
    def __init__(self):
        field = TextBox(
            name='field_label',
            label='Base field',
            knowl='nf',
            example='2.0.4.1',
            example_span=r'either a field label, e.g. 2.0.4.1 for \(\mathbb{Q}(\sqrt{-1})\), or a nickname, e.g. Qsqrt-1',
            example_span_colspan=4)

        degree = TextBox(
            name='deg',
            label='Base field degree',
            knowl='nf.degree',
            example='2',
            example_span='2, 2..3')

        discriminant = TextBox(
            name='disc',
            label='Base field discriminant',
            knowl='nf.discriminant',
            example='5',
            example_span='5 or 1-100')

        weight = TextBox(
            name='weight',
            label='Weight',
            knowl='mf.hilbert.weight_vector',
            example='[2,2]',
            example_span='2 or [2,2]'
        )

        level = TextBox(
            name='level_norm',
            label='Level norm',
            knowl='mf.hilbert.level_norm',
            example='1',
            example_span='1 or 1-100')

        dimension = TextBox(
            name='dimension',
            label='Dimension',
            knowl='mf.hilbert.dimension',
            example='1',
            example_span='1 or 2')

        base_change = ExcludeOnlyBox(
            name='bc',
            label='Base change',
            knowl='mf.base_change',
        )
        CM = ExcludeOnlyBox(
            name='cm',
            label='CM',
            knowl='mf.cm',
        )
        field_bad_quant = SubsetBox(
            name="field_bad_quantifier")
        field_bad_primes = TextBoxWithSelect(
            name="field_bad_primes",
            label="Field bad primes",
            knowl="nf.ramified_primes",
            example="5,13",
            select_box=field_bad_quant)
        level_bad_quant = SubsetBox(
            name="level_bad_quantifier")
        level_bad_primes = TextBoxWithSelect(
            name="level_bad_primes",
            label="Level bad primes",
            knowl="mf.hilbert.level_norm",
            example="5,13",
            select_box=level_bad_quant)
        count = CountBox()

        self.browse_array = [
            [field],
            [degree, discriminant],
            [level, weight],
            [dimension, base_change],
            [count, CM],
            [field_bad_primes, level_bad_primes]
        ]
        self.refine_array = [
            [field, degree, discriminant, CM, field_bad_primes],
            [weight, level, dimension, base_change, level_bad_primes],
        ]
