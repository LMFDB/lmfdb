# -*- coding: utf-8 -*-
import re

from flask import render_template, url_for, request, redirect, make_response, abort
from sage.all import latex, QQ, PolynomialRing

from lmfdb import db
from lmfdb.utils import (
    to_dict, web_latex_ideal_fact, flash_error, comma, display_knowl,
    nf_string_to_label, parse_nf_string, parse_noop, parse_start, parse_count, parse_ints, parse_primes,
    SearchArray, TextBox, SelectBox, ExcludeOnlyBox, CountBox, SubsetBox, TextBoxWithSelect,
    teXify_pol, search_wrap)
from lmfdb.utils.display_stats import StatsDisplay, totaler, proportioners
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.number_fields.web_number_field import WebNumberField, nf_display_knowl, field_pretty
from lmfdb.nfutils.psort import ideal_from_label, primes_iter
from lmfdb.bianchi_modular_forms import bmf_page
from lmfdb.bianchi_modular_forms.web_BMF import WebBMF

field_label_regex = re.compile(r'2\.0\.(\d+)\.1')

def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Bianchi modular form labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]

def get_bread(tail=[]):
    base = [('Modular forms', url_for('modular_forms')),
            ('Bianchi', url_for(".index"))]
    if not isinstance(tail, list):
        tail = [(tail, " ")]
    return base + tail


def bc_info(bc):
    return 'yes' if bc > 0 else 'yes (twist)' if bc < 0 else 'no'


def cm_info(cm):
    try:
        if cm == 0:
            return 'no'
        elif cm % 4 == 1:
            return f'${cm}$'
        else:
            return f'${4*cm}$'
    except TypeError:
        return str(cm)

@bmf_page.route("/")
def index():
    """Function to deal with the base URL
    /ModularForm/GL2/ImaginaryQuadratic.  If there are no request.args
    we display the browse and serch page, otherwise (as happens when
    submitting a jump or search button from that page) we hand over to
    the function bianchi_modular_form_search().
    """
    info = to_dict(request.args, search_array=BMFSearchArray(), stats=BianchiStats())
    if not request.args:
        gl2_fields = ["2.0.{}.1".format(d) for d in [4,8,3,7,11,19,43,67,163, 23,31]]
        sl2_fields = gl2_fields + ["2.0.{}.1".format(d) for d in [20]]
        gl2_names = [r"\(\Q(\sqrt{-%s})\)" % d for d in [1,2,3,7,11,19,43,67,163, 23,31]]
        sl2_names = [r"\(\Q(\sqrt{-%s})\)" % d for d in [4,8,3,7,11,19,43,67,163,5]]
        info['gl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_gl2", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]
        info['sl2_field_list'] = [{'url':url_for("bmf.render_bmf_field_dim_table_sl2", field_label=f), 'name':n} for f,n in zip(sl2_fields,sl2_names)]
        info['field_forms'] = [{'url':url_for("bmf.index", field_label=f), 'name':n} for f,n in zip(gl2_fields,gl2_names)]

        t = 'Bianchi modular forms'
        bread = get_bread()
        info['learnmore'] = []
        return render_template("bmf-browse.html", info=info, title=t, bread=bread, learnmore=learnmore_list())
    else:
        return bianchi_modular_form_search(info)

@bmf_page.route("/random")
def random_bmf():    # Random Bianchi modular form
    res = db.bmf_forms.random(projection=['field_label', 'level_label', 'label_suffix'])
    return redirect(url_for(".render_bmf_webpage",
                    field_label=res['field_label'],
                    level_label=res['level_label'],
                    label_suffix=res['label_suffix']), 307)

@bmf_page.route("/interesting")
def interesting():
    return interesting_knowls(
        "mf.bianchi",
        db.bmf_forms,
        url_for_label=url_for_label,
        title="Some interesting Bianchi modular forms",
        bread=get_bread("Interesting"),
        learnmore=learnmore_list()
    )

@bmf_page.route("/stats")
def statistics():
    title = "Bianchi modular forms: statistics"
    bread = get_bread("Statistics")
    return render_template("display_stats.html", info=BianchiStats(), title=title, bread=bread, learnmore=learnmore_list())

def bianchi_modular_form_jump(info):
    label = info['jump'].strip()
    dat = label.split("-")
    if len(dat)==2: # assume field & level, display space
        return render_bmf_space_webpage(dat[0], dat[1])
    else: # assume single newform label; will display an error if invalid
        return bianchi_modular_form_by_label(label)

def bianchi_modular_form_postprocess(res, info, query):
    if info['number'] > 0:
        info['field_pretty_name'] = field_pretty(res[0]['field_label'])
    else:
        info['field_pretty_name'] = ''
    res.sort(key=lambda x: [x['level_norm'], int(x['level_number']), x['label_suffix']])
    return res

def url_for_label(label):
    return url_for(".render_bmf_webpage",
                   **dict(zip(
                       ['field_label', 'level_label', 'label_suffix'],
                       label.split('-')
                   )))

bmf_columns = SearchColumns([
    ProcessedCol("field_label", "nf", "Base field",
                 lambda fld: nf_display_knowl(fld, field_pretty(fld)),
                 default=True),
    MultiProcessedCol("level", "mf.bianchi.level", "Level", ["field_label", "level_label"],
                      lambda fld, lvl: '<a href="{}">{}</a>'.format(
                          url_for("bmf.render_bmf_space_webpage",
                                  field_label=fld,
                                  level_label=lvl),
                          lvl),
                      default=True), # teXify_pol(v['level_ideal'])
    MultiProcessedCol("label", "mf.bianchi.labels", "Label", ["field_label", "level_label", "label_suffix", "short_label"],
                      lambda fld, lvl, suff, short: '<a href="{}">{}</a>'.format(
                          url_for("bmf.render_bmf_webpage",
                                  field_label=fld,
                                  level_label=lvl,
                                  label_suffix=suff),
                          short),
                      default=True),
    # See Issue #4170
    #MathCol("dimension", "mf.bianchi.newform", "Dimension", default=True),
    ProcessedCol("sfe", "mf.bianchi.sign", "Sign",
                 lambda v: "$+1$" if v == 1 else ("$-1$" if v == -1 else ""),
                 default=True, align="center"),
    ProcessedCol("bc", "mf.bianchi.base_change", "Base change", bc_info, default=True, align="center"),
    ProcessedCol("CM", "mf.bianchi.cm", "CM", cm_info, default=True, short_title="CM", align="center")])

bmf_columns.dummy_download = True


@search_wrap(table=db.bmf_forms,
             title='Bianchi modular form search results',
             err_title='Bianchi modular forms search input error',
             columns=bmf_columns,
             shortcuts={'jump': bianchi_modular_form_jump},
             bread=lambda:get_bread("Search results"),
             url_for_label=url_for_label,
             learnmore=learnmore_list,
             properties=lambda: [])
def bianchi_modular_form_search(info, query):
    """Function to handle requests from the top page, either jump to one
    newform or do a search.
    """
    parse_nf_string(info, query, 'field_label', name='base number field')
    parse_noop(info, query, 'label')
    #parse_ints(info, query, 'dimension')
    query['dimension'] = 1
    parse_ints(info, query, 'level_norm')
    parse_primes(info, query, 'field_bad_primes', name='field bad primes',
         qfield='field_bad_primes',mode=info.get('field_bad_quantifier'))
    parse_primes(info, query, 'level_bad_primes', name='level bad primes',
         qfield='level_bad_primes',mode=info.get('level_bad_quantifier'))
    if 'sfe' not in info:
        info['sfe'] = "any"
    elif info['sfe'] != "any":
        query['sfe'] = int(info['sfe'])
    if 'include_cm' in info:
        if info['include_cm'] in ['exclude', 'off']:
            query['CM'] = 0 # will exclude NULL values
        elif info['include_cm'] == 'only':
            query['CM'] = {'$ne': 0} # will exclude NULL values
    if info.get('include_base_change') =='exclude':
        query['bc'] = 0
    elif info.get('include_base_change') == 'only':
        query['bc'] = {'$ne': 0}

@bmf_page.route('/<field_label>')
def bmf_search_field(field_label):
    return bianchi_modular_form_search({'field_label':field_label, 'search_array':BMFSearchArray()})

# For statistics, it's useful to be able to pass the field label via a request argument
@bmf_page.route('/gl2dims')
def gl2dims():
    flash_error("You must specify a field label to access dimension tables")
    return redirect(url_for(".index"))

@bmf_page.route('/sl2dims')
def sl2dims():
    flash_error("You must specify a field label to access dimension tables")
    return redirect(url_for(".index"))

@bmf_page.route('/gl2dims/<field_label>')
def render_bmf_field_dim_table_gl2(field_label):
    if not field_label_regex.match(field_label):
        flash_error("%s is not a valid label for an imaginary quadratic field", field_label)
        return redirect(url_for(".index"))
    return bmf_field_dim_table(gl_or_sl='gl2_dims', field_label=field_label)

@bmf_page.route('/sl2dims/<field_label>')
def render_bmf_field_dim_table_sl2(field_label):
    if not field_label_regex.match(field_label):
        flash_error("%s is not a valid label for an imaginary quadratic field", field_label)
        return redirect(url_for(".index"))
    return bmf_field_dim_table(gl_or_sl='sl2_dims', field_label=field_label)

def bmf_field_dim_table(**args):
    argsdict = to_dict(args)
    argsdict.update(to_dict(request.args))
    gl_or_sl = argsdict['gl_or_sl']

    field_label=argsdict['field_label']
    field_label = nf_string_to_label(field_label)

    count = parse_count(argsdict, 50)
    start = parse_start(argsdict)

    info={}
    info['gl_or_sl'] = gl_or_sl
    # level_flag controls whether to list all levels ('all'), only
    # those with positive cuspidal dimension ('cusp'), or only those
    # with positive new dimension ('new').  Default is 'cusp'.
    level_flag = argsdict.get('level_flag', 'cusp')
    info['level_flag'] = level_flag

    pretty_field_label = field_pretty(field_label)
    bread = get_bread(pretty_field_label)
    properties = []
    query = {}
    if "level_norm" in argsdict:
        parse_ints(argsdict, query, 'level_norm')
        info["level_norm"] = argsdict["level_norm"]
    query['field_label'] = field_label
    if gl_or_sl=='gl2_dims':
        info['group'] = 'GL(2)'
        info['bgroup'] = r'\GL(2,\mathcal{O}_K)'
    else:
        info['group'] = 'SL(2)'
        info['bgroup'] = r'\SL(2,\mathcal{O}_K)'
    if level_flag == 'all':
        query[gl_or_sl] = {'$exists': True}
    else:
        # Only get records where the cuspdial/new dimension is positive for some weight
        totaldim = gl_or_sl.replace('dims', level_flag) + '_totaldim'
        query[totaldim] = {'$gt': 0}
    t = ' '.join(['Dimensions of spaces of {} Bianchi modular forms over'.format(info['group']), pretty_field_label])
    data = list(db.bmf_dims.search(query, limit=count, offset=start, info=info))
    nres = info['number']
    if not info['exact_count']:
        info['number'] = nres = db.bmf_dims.count(query)
        info['exact_count'] = True
    if nres > count or start != 0:
        info['report'] = 'Displaying items %s-%s of %s levels,' % (start + 1, min(nres, start + count), nres)
    else:
        info['report'] = 'Displaying all %s levels,' % nres

    info['field'] = field_label
    info['field_pretty'] = pretty_field_label
    nf = WebNumberField(field_label)
    info['base_galois_group'] = nf.galois_string()
    info['field_degree'] = nf.degree()
    info['field_disc'] = str(nf.disc())
    info['field_poly'] = teXify_pol(str(nf.poly()))
    weights = set()
    for dat in data:
        weights = weights.union(set(dat[gl_or_sl].keys()))
    weights = [int(w) for w in weights]
    weights.sort()
    info['weights'] = weights
    info['nweights'] = len(weights)

    data.sort(key = lambda x: [int(y) for y in x['level_label'].split(".")])
    dims = {}
    for dat in data:
        dims[dat['level_label']] = d = {}
        for w in weights:
            sw = str(w)
            if sw in dat[gl_or_sl]:
                d[w] = {'d': dat[gl_or_sl][sw]['cuspidal_dim'],
                        'n': dat[gl_or_sl][sw]['new_dim']}
            else:
                d[w] = {'d': '?', 'n': '?'}
    info['nlevels'] = len(data)
    dimtable = [{'level_label': dat['level_label'],
                 'level_norm': dat['level_norm'],
                 'level_space': url_for(".render_bmf_space_webpage", field_label=field_label, level_label=dat['level_label']) if gl_or_sl=='gl2_dims' else "",
                  'dims': dims[dat['level_label']]} for dat in data]
    info['dimtable'] = dimtable
    return render_template("bmf-field_dim_table.html", info=info, title=t, properties=properties, bread=bread)

@bmf_page.route('/<field_label>/<level_label>')
def render_bmf_space_webpage(field_label, level_label):
    info = {}
    t = "Bianchi modular forms of level %s over %s" % (level_label, field_label)
    bread = get_bread([
        (field_pretty(field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=field_label)),
        (level_label, '')])
    friends = []
    properties = []
    downloads = []

    if not field_label_regex.match(field_label):
        flash_error("%s is not a valid label for an imaginary quadratic field", field_label)
    else:
        pretty_field_label = field_pretty(field_label)
        if not db.bmf_dims.exists({'field_label': field_label}):
            info['err'] = "no dimension information exists in the database for field %s" % pretty_field_label
        else:
            t = "Bianchi modular forms of level %s over %s" % (level_label, pretty_field_label)
            data = db.bmf_dims.lucky({'field_label': field_label, 'level_label': level_label})
            if not data:
                info['err'] = "no dimension information exists in the database for level %s and field %s" % (level_label, pretty_field_label)
            else:
                info['label'] = data['label']
                info['nf'] = nf = WebNumberField(field_label)
                info['field_label'] = field_label
                info['pretty_field_label'] = pretty_field_label
                info['level_label'] = level_label
                info['level_norm'] = data['level_norm']
                info['field_poly'] = teXify_pol(str(nf.poly()))
                info['field_knowl'] = nf_display_knowl(field_label, pretty_field_label)
                w = 'i' if nf.disc()==-4 else 'a'
                L = nf.K().change_names(w)
                alpha = L.gen()
                info['field_gen'] = latex(alpha)
                I = ideal_from_label(L,level_label)
                info['level_gen'] = latex(I.gens_reduced()[0])
                info['level_fact'] = web_latex_ideal_fact(I.factor(), enclose=False)
                dim_data = data['gl2_dims']
                weights = list(dim_data)
                weights.sort(key=int)
                for w in weights:
                    dim_data[w]['dim']=dim_data[w]['cuspidal_dim']
                info['dim_data'] = dim_data
                info['weights'] = weights
                info['nweights'] = len(weights)

                newdim = data['gl2_dims']['2']['new_dim']
                newforms = db.bmf_forms.search({'field_label':field_label, 'level_label':level_label})
                info['nfdata'] = [{
                    'label': f['short_label'],
                    'url': url_for(".render_bmf_webpage",field_label=f['field_label'], level_label=f['level_label'], label_suffix=f['label_suffix']),
                    'wt': f['weight'],
                    'dim': f['dimension'],
                    'sfe': "+1" if f.get('sfe',None)==1 else "-1" if f.get('sfe',None)==-1 else "?",
                    'bc': bc_info(f['bc']),
                    'cm': cm_info(f.get('CM','?')),
                    } for f in newforms]
                info['nnewforms'] = len(info['nfdata'])
                # currently we have newforms of dimension 1 and 2 only (mostly dimension 1)
                # but the dimension 2 data is untrustworthy so is ignored here
                info['nnf1'] = sum(1 for f in info['nfdata'] if f['dim']==1)
                #info['nnf2'] = sum(1 for f in info['nfdata'] if f['dim']==2)
                info['nnf_missing'] = dim_data['2']['new_dim'] - info['nnf1'] # - 2*info['nnf2']
                properties = [('Base field', pretty_field_label), ('Level',info['level_label']), ('Norm',str(info['level_norm'])), ('New dimension',str(newdim))]
                friends = [('Newform {}'.format(f['label']), f['url']) for f in info['nfdata'] ]
                downloads = [('Underlying data', url_for(".bmf_data", label=info['label']))]

    return render_template("bmf-space.html", info=info, title=t, bread=bread, properties=properties, friends=friends, downloads=downloads, learnmore=learnmore_list())

@bmf_page.route('/data/<label>')
def bmf_data(label):
    pieces = label.split("-")
    if len(pieces) == 2:
        url = url_for(".render_bmf_space_webpage", field_label=pieces[0], level_label=pieces[1])
        title = f"Bianchi modular space data - {label}"
        table = "bmf_dims"
    elif len(pieces) == 3:
        url = url_for_label(label)
        title = f"Bianchi modular form data - {label}"
        table = "bmf_forms"
    else:
        return abort(404, f"Invalid label {label}")
    bread = get_bread([(label, url), ("Data", " ")])
    return datapage(label, table, title=title, bread=bread)


@bmf_page.route('/<field_label>/<level_label>/<label_suffix>/download/<download_type>')
def render_bmf_webpage_download(**args):
    if args['download_type'] == 'magma':
        response = make_response(download_bmf_magma(**args))
        response.headers['Content-type'] = 'text/plain'
        return response
    elif args['download_type'] == 'sage':
        response = make_response(download_bmf_sage(**args))
        response.headers['Content-type'] = 'text/plain'
        return response


def download_bmf_magma(**args):
    label = "-".join([args['field_label'], args['level_label'], args['label_suffix']])

    try:
        f = WebBMF.by_label(label)
    except ValueError:
        return "Bianchi newform not found"

    hecke_pol  = f.hecke_poly_obj
    hecke_eigs = f.hecke_eigs

    F = WebNumberField(f.field_label)
    K = f.field.K()

    primes_in_K = [p for p,_ in zip(primes_iter(K),hecke_eigs)]
    prime_gens = [list(p.gens()) for p in primes_in_K]

    outstr = '/*\n  This code can be loaded, or copied and pasted, into Magma.\n'
    outstr += '  It will load the data associated to the BMF, including\n'
    outstr += '  the field, level, and Hecke and Atkin-Lehner eigenvalue data.\n'
    outstr += '  At the *bottom* of the file, there is code to recreate the\n'
    outstr += '  Bianchi modular form in Magma, by creating the BMF space\n'
    outstr += '  and cutting out the corresponding Hecke irreducible subspace.\n'
    outstr += '  From there, you can ask for more eigenvalues or modify as desired.\n'
    outstr += '  It is commented out, as this computation may be lengthy.\n'
    outstr += '*/\n\n'

    outstr += 'P<x> := PolynomialRing(Rationals());\n'
    outstr += 'g := P!' + str(F.coeffs()) + ';\n'
    outstr += 'F<{}> := NumberField(g);\n'.format(K.gen())
    outstr += 'ZF := Integers(F);\n\n'

    outstr += 'NN := ideal<ZF | {}>;\n\n'.format(set(f.level.gens()))

    outstr += 'primesArray := [\n' + ','.join([str(st).replace(' ', '') for st in prime_gens]).replace('],[',
                                                                                       '],\n[') + '];\n'
    outstr += 'primes := [ideal<ZF | {F!x : x in I}> : I in primesArray];\n\n'

    if hecke_pol != 'x':
        outstr += 'heckePol := ' + hecke_pol + ';\n'
        outstr += 'K<z> := NumberField(heckePol);\n'
    else:
        outstr += 'heckePol := x;\nK := Rationals(); e := 1;\n'

    hecke_eigs_processed = [str(st).replace(' ', '') if st != 'not known' else '"not known"' for st in hecke_eigs]
    outstr += '\nheckeEigenvaluesList := [*\n'+ ',\n'.join(hecke_eigs_processed) + '\n*];\n'
    outstr += '\nheckeEigenvalues := AssociativeArray();\n'
    outstr += 'for i in [1..#heckeEigenvaluesList] do\n    heckeEigenvalues[primes[i]] := heckeEigenvaluesList[i];\nend for;\n'


    if f.have_AL:
        AL_eigs    = f.AL_table_data
        outstr += '\nALEigenvalues := AssociativeArray();\n'
        for s in AL_eigs:
            outstr += 'ALEigenvalues[ideal<ZF | {}>] := {};\n'.format(set(s[0]), s[1])
    else:
        outstr += '\nALEigenvalues := "not known";\n'

    outstr += '\n// EXAMPLE:\n// pp := Factorization(2*ZF)[1][1];\n// heckeEigenvalues[pp];\n\n'

    outstr += '\n'.join([
        'print "To reconstruct the Bianchi newform f, type',
        '  f, iso := Explode(make_newform());";',
        '',
        'function make_newform();',
        ' M := BianchiCuspForms(F, NN);',
        ' S := NewSubspace(M);',
        ' // SetVerbose("Bianchi", 1);',
        ' NFD := NewformDecomposition(S);',
        ' newforms := [* Eigenform(U) : U in NFD *];',
        '',
        ' if #newforms eq 0 then;',
        '  print "No Bianchi newforms at this level";',
        '  return 0;',
        ' end if;',
        '',
        ' print "Testing ", #newforms, " possible newforms";',
        ' newforms := [* f: f in newforms | IsIsomorphic(BaseField(f), K) *];',
        ' print #newforms, " newforms have the correct Hecke field";',
        '',
        ' if #newforms eq 0 then;',
        '  print "No Bianchi newform found with the correct Hecke field";',
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
        '  if Valuation(NN,P) eq 0 then;',
        '   xnewforms := [* *];',
        '   for f_iso in newforms do;',
        '    f, iso := Explode(f_iso);',
        '    if HeckeEigenvalue(f,P) eq iso(heckeEigenvalues[P]) then;',
        '     Append(~xnewforms, f_iso);',
        '    end if;',
        '   end for;',
        '   newforms := xnewforms;',
        '   if #newforms eq 0 then;',
        '    print "No Bianchi newform found which matches the Hecke eigenvalues";',
        '    return 0;',
        '   else if #newforms eq 1 then;',
        '    print "success: unique match";',
        '    return newforms[1];',
        '   end if;',
        '   end if;',
        '  end if;',
        ' end for;',
        ' print #newforms, "Bianchi newforms found which match the Hecke eigenvalues";',
        ' return newforms[1];',
        '',
        'end function;'])

    return outstr


def download_bmf_sage(**args):
    """Generates the sage code for the user to obtain the BMF eigenvalues.
    As in the HMF case, and unlike the website, we export *all* eigenvalues in
    the database, not just 50, and not just those away from the level."""

    label = "-".join([args['field_label'], args['level_label'], args['label_suffix']])

    try:
        f = WebBMF.by_label(label)
    except ValueError:
        return "Bianchi newform not found"

    hecke_pol  = f.hecke_poly_obj
    hecke_eigs = f.hecke_eigs

    F = WebNumberField(f.field_label)
    K = f.field.K()

    primes_in_K = [p for p,_ in zip(primes_iter(K),hecke_eigs)]
    prime_gens = [p.gens_reduced() for p in primes_in_K]

    outstr = '"""\n  This code can be loaded, or copied and paste using cpaste, into Sage.\n'
    outstr += '  It will load the data associated to the BMF, including\n'
    outstr += '  the field, level, and Hecke and Atkin-Lehner eigenvalue data (if known).\n'
    outstr += '"""\n\n'

    outstr += 'P = PolynomialRing(QQ, "x")\nx = P.gen()\n'
    outstr += 'g = P(' + str(F.coeffs()) + ')\n'
    outstr += 'F = NumberField(g, "{}")\n'.format(K.gen())
    outstr += '{} = F.gen()\n'.format(K.gen())
    outstr += 'ZF = F.ring_of_integers()\n\n'

    outstr += 'NN = ZF.ideal({})\n\n'.format(f.level.gens())

    outstr += 'primes_array = [\n' + ','.join([str(st).replace(' ', '') for st in prime_gens]).replace('],[',
                                                                                       '],\\\n[') + ']\n'
    outstr += 'primes = [ZF.ideal(I) for I in primes_array]\n\n'

    Qx = PolynomialRing(QQ,'x')

    if hecke_pol != 'x':
        outstr += 'heckePol = P({})\n'.format(str((Qx(hecke_pol)).list()))
        outstr += 'K = NumberField(heckePol, "z")\nz = K.gen()\n'
    else:
        outstr += 'heckePol = x\nK = QQ\ne = 1\n'

    hecke_eigs_processed = [str(st).replace(' ', '') if st != 'not known' else '"not known"' for st in hecke_eigs]
    outstr += '\nhecke_eigenvalues_array = [' + ', '.join(hecke_eigs_processed) + ']'
    outstr += '\nhecke_eigenvalues = {}\n'
    outstr += 'for i in range(len(hecke_eigenvalues_array)):\n    hecke_eigenvalues[primes[i]] = hecke_eigenvalues_array[i]\n\n'

    if f.have_AL:
        AL_eigs    = f.AL_table_data
        outstr += 'AL_eigenvalues = {}\n'
        for s in AL_eigs:
            outstr += 'AL_eigenvalues[ZF.ideal(%s)] = %s\n' % (s[0],s[1])
    else:
        outstr += 'AL_eigenvalues ="not known"\n'

    outstr += '\n# EXAMPLE:\n# pp = ZF.ideal(2).factor()[0][0]\n# hecke_eigenvalues[pp]\n'

    return outstr

@bmf_page.route('/<field_label>/<level_label>/<label_suffix>/')
def render_bmf_webpage(field_label, level_label, label_suffix):
    label = "-".join([field_label, level_label, label_suffix])
    info = {}
    title = "Bianchi cusp forms"
    data = None
    properties = []
    friends = []
    bread = get_bread()

    try:
        numeigs = request.args['numeigs']
        numeigs = int(numeigs)
    except Exception:
        numeigs = 20
    info['numeigs'] = numeigs

    try:
        data = WebBMF.by_label(label, max_eigs=numeigs)
        title = "Bianchi cusp form {} over {}".format(data.short_label,field_pretty(data.field_label))
        bread = get_bread([
            (field_pretty(data.field_label), url_for(".render_bmf_field_dim_table_gl2", field_label=data.field_label)),
            (data.level_label, url_for('.render_bmf_space_webpage', field_label=data.field_label, level_label=data.level_label)),
            (data.short_label, '')])
        properties = data.properties
        friends = data.friends
        info['downloads'] = [
            ('Modular form to Magma', url_for(".render_bmf_webpage_download", field_label=field_label, label_suffix=label_suffix, level_label=level_label, download_type='magma')),
            ('Eigenvalues to Sage', url_for(".render_bmf_webpage_download", field_label=field_label, label_suffix=label_suffix, level_label=level_label, download_type='sage')),
            ('Underlying data', url_for(".bmf_data", label=label)),
        ]
    except ValueError:
        flash_error("No Bianchi modular form in the database has label %s", label)
        return redirect(url_for(".index"))
    return render_template(
        "bmf-newform.html",
        downloads=info["downloads"],
        title=title,
        bread=bread,
        data=data,
        properties=properties,
        friends=friends,
        info=info,
        learnmore=learnmore_list(),
        KNOWL_ID="mf.bianchi.%s"%label,
    )


def bianchi_modular_form_by_label(lab):
    if lab == '':
        # do nothing: display the top page
        return redirect(url_for(".index"))
    if isinstance(lab, str):
        res = db.bmf_forms.lookup(lab)
    else:
        res = lab
        lab = res['label']

    if res is None:
        flash_error("No Bianchi modular form in the database has label or name %s", lab)
        return redirect(url_for(".index"))
    else:
        return redirect(url_for(".render_bmf_webpage",
                        field_label=res['field_label'],
                        level_label=res['level_label'],
                        label_suffix=res['label_suffix']))

@bmf_page.route("/Source")
def how_computed_page():
    t = 'Source of Bianchi modular form data'
    bread = get_bread("Source")
    return render_template("multi.html", kids=['rcs.source.mf.bianchi',
                            'rcs.ack.mf.bianchi',
                            'rcs.cite.mf.bianchi'],
                            title=t,
                            bread=bread,
                            learnmore=learnmore_list_remove('Source'))

@bmf_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Bianchi modular form data'
    bread = get_bread("Completeness")
    return render_template("single.html", kid='rcs.cande.mf.bianchi',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Completeness'))

@bmf_page.route("/Reliability")
def reliability_page():
    t = 'Reliability of Bianchi modular form data'
    bread = get_bread("Reliability")
    return render_template("single.html", kid='rcs.rigor.mf.bianchi',
                           title=t, bread=bread, learnmore=learnmore_list_remove('Reliability'))

@bmf_page.route("/Labels")
def labels_page():
    t = 'Labels for Bianchi newforms'
    bread = get_bread("Labels")
    return render_template("single.html", kid='mf.bianchi.labels',
                           title=t, bread=bread, learnmore=learnmore_list_remove('labels'))


class BMFSearchArray(SearchArray):
    noun = "form"
    plural_noun = "forms"
    sorts = [("", "level norm", ['level_norm', 'label']),
             ("field", "field", ['field_deg', ('field_disc', -1), 'level_norm', 'label'])]
    jump_example = "2.0.4.1-65.2-a"
    jump_egspan = "e.g. 2.0.4.1-65.2-a (single form) or 2.0.4.1-65.2 (space of forms at a level)"
    jump_prompt = "Label"
    jump_knowl = "mf.bianchi.search_input"
    def __init__(self):
        field = TextBox(
            name='field_label',
            label='Base field',
            knowl='nf',
            example='2.0.4.1',
            example_span=r'either a field label, e.g. 2.0.4.1 for \(\mathbb{Q}(\sqrt{-1})\), or a nickname, e.g. Qsqrt-1',
            example_span_colspan=4)
        level = TextBox(
            name='level_norm',
            label='Level norm',
            knowl='mf.bianchi.level',
            example='1',
            example_span='e.g. 1 or 1-100')

        # See Issue #4170
        # dimension = TextBox(
        #     name='dimension',
        #     label='Dimension',
        #     knowl='mf.bianchi.spaces',
        #     example='1',
        #     example_span='e.g. 1 or 2')

        sign = SelectBox(
            name='sfe',
            label='Sign',
            knowl='mf.bianchi.sign',
            options=[("", ""), ("+1", "+1"), ("-1", "-1")],
            example_col=True
        )
        base_change = ExcludeOnlyBox(
            name='include_base_change',
            label='Base change',
            knowl='mf.bianchi.base_change',
            example="exclude"
        )
        CM = ExcludeOnlyBox(
            name='include_cm',
            label='CM',
            knowl='mf.bianchi.cm'
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
            knowl="mf.bianchi.level",
            example="5,13",
            select_box=level_bad_quant)
        count = CountBox()

        self.browse_array = [
            [field],
            [level, sign],
            [base_change, CM],
            [field_bad_primes, level_bad_primes],
            [count]
        ]
        self.refine_array = [
            [field, level, CM],
            [sign, base_change, field_bad_primes, level_bad_primes]
        ]

label_finder = re.compile(r"label=([0-9.]+)")
def field_unformatter(label):
    if label[0] == '<':
        label = label_finder.findall(label)[0]
    return label
def field_formatter(label):
    # Need to accept the output of nf_display_knowl
    label = field_unformatter(label)
    return nf_display_knowl(label, field_pretty(label))
def field_sortkey(label):
    D = int(label.split(".")[2])
    return D

class BianchiStats(StatsDisplay):
    table = db.bmf_forms
    baseurl_func = ".index"

    stat_list = [
        {'cols': ['field_label', 'level_norm'],
         'top_title': '%s by %s and %s' % (
             display_knowl("mf.bianchi.bianchimodularforms",
                           "Bianchi modular forms"),
             display_knowl('nf', 'base field'),
             display_knowl('mf.bianchi.level', 'level norm')),
         'constraint': {"dimension": 1},
         'totaler': totaler(),
         'proportioner': proportioners.per_row_total},
        {'cols': ['field_label', 'level_norm'],
         'top_title': 'computed %s by %s and %s' % (
             display_knowl("mf.bianchi.spaces",
                           r"$\operatorname{GL}_2$ levels"),
             display_knowl('nf', 'base field'),
             display_knowl('mf.bianchi.level', 'level norm')),
         'intro': ["The set of %s computed for each level varies." % display_knowl("mf.bianchi.weight", "weights")],
         'constraint': {"gl2_cusp_totaldim": {"$gt": 0}},
         'baseurl_func': ".gl2dims",
         'table': db.bmf_dims,
         'totaler': totaler(col_counts=False),
         'proportioner': proportioners.per_row_total},
        {'cols': ['field_label', 'level_norm'],
         'top_title': 'computed %s by %s and %s' % (
             display_knowl("mf.bianchi.spaces",
                           r"$\operatorname{SL}_2$ levels"),
             display_knowl('nf', 'base field'),
             display_knowl('mf.bianchi.level', 'level norm')),
         'intro': ["The set of %s computed for each level varies." % display_knowl("mf.bianchi.weight", "weights")],
         'constraint': {"sl2_cusp_totaldim": {"$gt": 0}},
         'baseurl_func': ".sl2dims",
         'buckets': {'level_norm': ['1-100', '101-200', '201-400', '401-800', '801-1600', '1601-3200', '3201-6400']},
         'table': db.bmf_dims,
         'totaler': totaler(col_counts=False),
         'proportioner': proportioners.per_row_total},
        # {'cols': ['dimension', 'level_norm'],
        #  'totaler': totaler(),
        #  'proportioner': proportioners.per_col_total},
        # {'cols': ['dimension', 'field_label'],
        #  'totaler': totaler(),
        #  'proportioner': proportioners.per_col_total},
    ]

    buckets = {'level_norm': ['1-100', '101-1000', '1001-10000', '10001-50000', '50001-100000', '100001-150000']}

    knowls = {'level_norm': 'mf.bianchi.level',
              'dimension': 'mf.bianchi.spaces',
              'field_label': 'nf'}
    formatters = {'field_label': field_formatter}
    query_formatters = {'field_label': (lambda x: 'field_label=%s' % (field_unformatter(x)))}
    sort_keys = {'field_label': field_sortkey}
    top_titles = {'dimension': 'newform dimensions'}
    short_display = {'field_label': 'base field'}

    def __init__(self):
        self.nforms = db.bmf_forms.count()
        self.ndims = db.bmf_dims.count()
        self.nformfields = len(db.bmf_forms.distinct('field_label'))
        self.ndimfields = len(db.bmf_dims.distinct('field_label'))

    @property
    def summary(self):
        return r"The database currently contains %s %s of weight 2 over %s imaginary quadratic fields, and %s %s over %s imaginary quadratic fields, including all with class number one." % (
            comma(self.nforms),
            display_knowl("mf.bianchi.bianchimodularforms",
                          "Bianchi modular forms"),
            self.nformfields,
            comma(self.ndims),
            display_knowl("mf.bianchi.spaces",
                          "spaces of cusp forms"),
            self.ndimfields)

    @property
    def short_summary(self):
        return r'The database currently contains %s %s of weight 2 over the nine imaginary quadratic fields of class number one.  Here are some <a href="%s">further statistics</a>.' % (comma(self.nforms), display_knowl("mf.bianchi.bianchimodularforms", "Bianchi modular forms"), url_for(".statistics"))
