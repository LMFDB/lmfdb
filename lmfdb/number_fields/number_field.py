# -*- coding: utf-8 -*-

import pymongo
ASC = pymongo.ASCENDING
import time, os
import lmfdb.base as base
from lmfdb.base import app, getDBConnection
from flask import render_template, request, url_for, redirect, send_file, flash
import StringIO
from lmfdb.number_fields import nf_page, nf_logger
from lmfdb.WebNumberField import field_pretty, WebNumberField, nf_knowl_guts, decodedisc

from markupsafe import Markup

import re

assert nf_logger

#import sage.all
from sage.all import ZZ, QQ, PolynomialRing, NumberField, latex, primes, pari

from lmfdb.transitive_group import group_display_knowl, cclasses_display_knowl,character_table_display_knowl, group_phrase, group_display_short, group_knowl_guts, group_cclasses_knowl_guts, group_character_table_knowl_guts, aliastable

from lmfdb.utils import web_latex, to_dict, coeff_to_poly, pol_to_html, comma, random_object_from_collection, web_latex_split_on_pm
from lmfdb.search_parsing import clean_input, nf_string_to_label, parse_galgrp, parse_ints, parse_signed_ints, parse_primes, parse_bracketed_posints, parse_count, parse_start, parse_nf_string

NF_credit = 'the PARI group, J. Voight, J. Jones, D. Roberts, J. Kl&uuml;ners, G. Malle'
Completename = 'Completeness of this data'
dnc = 'data not computed'

FIELD_LABEL_RE = re.compile(r'^\d+\.\d+\.(\d+(e\d+)?(t\d+(e\d+)?)*)\.\d+$')

nfields = None
max_deg = None
init_nf_flag = False

# For imaginary quadratic field class group data
class_group_data_directory = os.path.expanduser('~/data/class_numbers')

def init_nf_count():
    global nfields, init_nf_flag, max_deg
    if not init_nf_flag:
        nfdb = base.getDBConnection().numberfields.fields
        nfields = nfdb.count()
        max_deg = nfdb.find().sort('degree', pymongo.DESCENDING).limit(1)[0]['degree']
        init_nf_flag = True


def galois_group_data(n, t):
    C = getDBConnection()
    return group_knowl_guts(n, t, C)

def group_cclasses_data(n, t):
    C = getDBConnection()
    return group_cclasses_knowl_guts(n, t, C)

def group_character_table_data(n, t):
    C = getDBConnection()
    return group_character_table_knowl_guts(n, t, C)

def number_field_data(label):
    C = getDBConnection()
    return nf_knowl_guts(label, C)

def na_text():
    return "Not computed"


@app.context_processor
def ctx_galois_groups():
    return {'galois_group_data': galois_group_data,
            'group_cclasses_data': group_cclasses_data,
            'group_character_table_data': group_character_table_data}

@app.context_processor
def ctx_number_fields():
    return {'number_field_data': number_field_data,
            'global_numberfield_summary': global_numberfield_summary}

def global_numberfield_summary():
    init_nf_count()
    return r'This database contains %s <a title="global number fields" knowl="nf">global number fields</a> of <a title="degree" knowl="nf.degree">degree</a> $n\leq %d$.  In addition, extensive data on <a href="%s">class groups of quadratic imaginary fields</a> is available for download.' %(comma(nfields),max_deg,url_for('number_fields.render_class_group_data'))

def group_display_shortC(C):
    def gds(nt):
        return group_display_short(nt['n'], nt['t'], C)
    return gds

def poly_to_field_label(pol):
    try:
        wnf = WebNumberField.from_polynomial(pol)
        return wnf.get_label()
    except:
        return None
    #coeffs = list2string([int(c) for c in pol.coeffs()])
    #d = int(pol.degree())
    #query = {'coeffs': coeffs}
    #C = base.getDBConnection()
    #one = C.numberfields.fields.find_one(query)
    #if one:
    #    return one['label']
    #return None

@app.route("/NF")
@app.route("/NF/")
def NF_redirect():
    return redirect(url_for("number_fields.number_field_render_webpage", **request.args), 301)

@nf_page.route("/HowComputed")
def how_computed_page():
    info = {}
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), 
        ('Galois group labels', url_for(".render_groups_page")), 
        (Completename, url_for(".render_discriminants_page")) ]
    t = 'How Number Field Data was Computed'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Galois group labels', ' ')]
    return render_template("single.html", kid='dq.nf.howcomputed', 
        credit=NF_credit, title=t, bread=bread, learnmore=info.pop('learnmore'))

@nf_page.route("/GaloisGroups")
def render_groups_page():
    info = {}
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")) ]
    t = 'Galois group labels'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Galois group labels', ' ')]
    C = base.getDBConnection()
    return render_template("galois_groups.html", al=aliastable(C), info=info, credit=NF_credit, title=t, bread=bread, learnmore=info.pop('learnmore'))


@nf_page.route("/FieldLabels")
def render_labels_page():
    info = {}
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
    t = 'Number field labels'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Number field labels', '')]
    return render_template("single.html", info=info, credit=NF_credit, kid='nf.label', title=t, bread=bread, learnmore=info.pop('learnmore'))


@nf_page.route("/Discriminants")
def render_discriminants_page():
    info = {}
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
    t = 'Completeness of Global Number Field Data'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), (Completename, ' ')]
    return render_template("discriminant_ranges.html", info=info, credit=NF_credit, title=t, bread=bread, learnmore=info.pop('learnmore'))

@nf_page.route("/QuadraticImaginaryClassGroups")
def render_class_group_data():
    info = to_dict(request.args)
    #nf_logger.info('******************* ')
    #for k in info.keys():
    # nf_logger.info(str(k) + ' ---> ' + str(info[k]))
    #nf_logger.info('******************* ')
    #info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page"))]
    t = 'Class Groups of Quadratic Imaginary Fields'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), (t, ' ')]
    info['message'] =  ''
    info['filename']='none'
    if 'Fetch' in info:
        if 'k' in info:
            # remove non-digits
            k = re.sub(r'\D', '', info['k'])
            if k == "":
                info['message'] = 'The value of k is either invalid or empty'
                return class_group_request_error(info, bread)
            k = int(k)
            if k>4095:
                info['message'] = 'The value of k is too large'
                return class_group_request_error(info, bread)
        else:
            info['message'] = 'The value of k is missing'
            return class_group_request_error(info, bread)
        info['filenamebase'] = str(info['filenamebase'])
        if info['filenamebase'] in ['cl3mod8', 'cl7mod8', 'cl4mod16', 'cl8mod16']:
            filepath = "%s/%s/%s.%d.gz" % (class_group_data_directory,info['filenamebase'],info['filenamebase'],k)
            if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
                return send_file(filepath, as_attachment=True, add_etags=False)
            else:
                info['message'] = 'File not found'
                return class_group_request_error(info, bread)
        else:
            info['message'] = 'Invalid congruence requested'
            return class_group_request_error(info, bread)

    return render_template("class_group_data.html", info=info, credit="A. Mosunov and M. J. Jacobson, Jr.", title=t, bread=bread)

def class_group_request_error(info, bread):
    t = 'Class Groups of Quadratic Imaginary Fields'
    return render_template("class_group_data.html", info=info, credit="A. Mosunov and M. J. Jacobson, Jr.", title=t, bread=bread)


@nf_page.route("/")
def number_field_render_webpage():
    args = request.args
    sig_list = sum([[[d - 2 * r2, r2] for r2 in range(
        1 + (d // 2))] for d in range(1, 7)], []) + sum([[[d, 0]] for d in range(7, 11)], [])
    sig_list = sig_list[:10]
    if len(args) == 0:
        init_nf_count()
        discriminant_list_endpoints = [-10000, -1000, -100, 0, 100, 1000, 10000]
        discriminant_list = ["%s..%s" % (start, end - 1) for start, end in zip(
            discriminant_list_endpoints[:-1], discriminant_list_endpoints[1:])]
        info = {
            'degree_list': range(1, max_deg + 1),
            'signature_list': sig_list,
            'class_number_list': range(1, 6) + ['6..10'],
            'count': '20',
            'nfields': comma(nfields),
            'maxdeg': max_deg,
            'discriminant_list': discriminant_list
        }
        t = 'Global Number Fields'
        bread = [('Global Number Fields', url_for(".number_field_render_webpage"))]
        info['learnmore'] = [(Completename, url_for(".render_discriminants_page")), ('How data was computed', url_for(".how_computed_page")), ('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
        return render_template("number_field_all.html", info=info, credit=NF_credit, title=t, bread=bread, learnmore=info.pop('learnmore'))
    else:
        return number_field_search(**args)

@nf_page.route("/random")
def random_nfglobal():
    label = random_object_from_collection( getDBConnection().numberfields.fields )['label']
    #This version leaves the word 'random' in the URL:
    #return render_field_webpage({'label': label})
    #This version uses the number field's own URL:
    #url =
    return redirect(url_for(".by_label", label= label))


def coeff_to_nf(c):
    return NumberField(coeff_to_poly(c), 'a')


def sig2sign(sig):
    return [1, -1][sig[1] % 2]

## Turn a list into a string (without brackets)


def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)


def string2list(s):
    s = str(s)
    if s == '':
        return []
    return [int(a) for a in s.split(',')]


def render_field_webpage(args):
    data = None
    C = base.getDBConnection()
    info = {}
    bread = [('Global Number Fields', url_for(".number_field_render_webpage"))]

    # This function should not be called unless label is set.
    label = clean_input(args['label'])
    nf = WebNumberField(label)
    data = {}
    if nf.is_null():
        bread.append(('Search results', ' '))
        info['err'] = 'There is no field with label %s in the database' % label
        info['label'] = args['label_orig'] if 'label_orig' in args else args['label']
        return search_input_error(info, bread)

    info['wnf'] = nf
    data['degree'] = nf.degree()
    data['class_number'] = nf.class_number()
    t = nf.galois_t()
    n = nf.degree()
    data['is_galois'] = nf.is_galois()
    data['is_abelian'] = nf.is_abelian()
    if nf.is_abelian():
        conductor = nf.conductor()
        data['conductor'] = conductor
        dirichlet_chars = nf.dirichlet_group()
        if len(dirichlet_chars)>0:
            data['dirichlet_group'] = ['<a href = "%s">$\chi_{%s}(%s,&middot;)$</a>' % (url_for('characters.render_Dirichletwebpage',modulus=data['conductor'], number=j), data['conductor'], j) for j in dirichlet_chars]
            data['dirichlet_group'] = r'$\lbrace$' + ', '.join(data['dirichlet_group']) + r'$\rbrace$'
        if data['conductor'].is_prime() or data['conductor'] == 1:
            data['conductor'] = "\(%s\)" % str(data['conductor'])
        else:
            data['conductor'] = "\(%s=%s\)" % (str(data['conductor']), latex(data['conductor'].factor()))
    data['galois_group'] = group_display_knowl(n, t, C)
    data['cclasses'] = cclasses_display_knowl(n, t, C)
    data['character_table'] = character_table_display_knowl(n, t, C)
    data['class_group'] = nf.class_group()
    data['class_group_invs'] = nf.class_group_invariants()
    data['signature'] = nf.signature()
    data['coefficients'] = nf.coeffs()
    nf.make_code_snippets()
    D = nf.disc()
    ram_primes = D.prime_factors()
    data['disc_factor'] = nf.disc_factored_latex()
    if D.abs().is_prime() or D == 1:
        data['discriminant'] = "\(%s\)" % str(D)
    else:
        data['discriminant'] = "\(%s=%s\)" % (str(D), data['disc_factor'])
    npr = len(ram_primes)
    ram_primes = str(ram_primes)[1:-1]
    if ram_primes == '':
        ram_primes = r'\textrm{None}'
    data['frob_data'], data['seeram'] = frobs(nf)
    data['phrase'] = group_phrase(n, t, C)
    zk = nf.zk()
    Ra = PolynomialRing(QQ, 'a')
    zk = [latex(Ra(x)) for x in zk]
    zk = ['$%s$' % x for x in zk]
    zk = ', '.join(zk)
    grh_label = '<small>(<a title="assuming GRH" knowl="nf.assuming_grh">assuming GRH</a>)</small>' if nf.used_grh() else ''
    # Short version for properties
    grh_lab = nf.short_grh_string()
    if 'Not' in str(data['class_number']):
        grh_lab=''
        grh_label=''
    pretty_label = field_pretty(label)
    if label != pretty_label:
        pretty_label = "%s: %s" % (label, pretty_label)

    info.update(data)
    if nf.degree() > 1:
        gpK = nf.gpK()
        rootof1coeff = gpK.nfrootsof1()[2]
        rootofunity = Ra(str(pari("lift(%s)" % gpK.nfbasistoalg(rootof1coeff))).replace('x','a'))
    else:
        rootofunity = Ra('-1')

    info.update({
        'label': pretty_label,
        'label_raw': label,
        'polynomial': web_latex_split_on_pm(nf.poly()),
        'ram_primes': ram_primes,
        'integral_basis': zk,
        'regulator': web_latex(nf.regulator()),
        'unit_rank': nf.unit_rank(),
        'root_of_unity': web_latex(rootofunity),
        'fund_units': nf.units(),
        'grh_label': grh_label
    })

    bread.append(('%s' % info['label_raw'], ' '))
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet', '/')]
    info['friends'] = []
    if nf.can_class_number():
        # hide ones that take a lond time to compute on the fly
        # note that the first degree 4 number field missed the zero of the zeta function
        if abs(D**n) < 50000000:
            info['friends'].append(('L-function', "/L/NumberField/%s" % label))
    info['friends'].append(('Galois group', "/GaloisGroup/%dT%d" % (n, t)))
    if 'dirichlet_group' in info:
        info['friends'].append(('Dirichlet group', url_for("characters.dirichlet_group_table",
                                                           modulus=int(conductor),
                                                           char_number_list=','.join(
                                                               [str(a) for a in dirichlet_chars]),
                                                           poly=info['polynomial'])))
    resinfo=[]
    galois_closure = nf.galois_closure()
    if galois_closure[0]>0:
        if len(galois_closure[1])>0:
            resinfo.append(('gc', galois_closure[1]))
            if len(galois_closure[2]) > 0:
                info['friends'].append(('Galois closure',url_for(".by_label", label=galois_closure[2][0])))
        else:
            resinfo.append(('gc', [dnc]))

    sextic_twins = nf.sextic_twin()
    if sextic_twins[0]>0:
        if len(sextic_twins[1])>0:
            resinfo.append(('sex', r' $\times$ '.join(sextic_twins[1])))
        else:
            resinfo.append(('sex', dnc))

    siblings = nf.siblings()
    # [degsib list, label list]
    # first is list of [deg, num expected, list of knowls]
    if len(siblings[0])>0:
        for sibdeg in siblings[0]:
            if len(sibdeg[2]) ==0:
                sibdeg[2] = dnc
            else:
                sibdeg[2] = [z[0] for z in sibdeg[2]]
                sibdeg[2] = ', '.join(sibdeg[2])
                if len(sibdeg[2])<sibdeg[1]:
                    sibdeg[2] += ', some '+dnc
                
        resinfo.append(('sib', siblings[0]))
        for lab in siblings[1]:
            if lab != '':
                labparts = lab.split('.')
                info['friends'].append(("Degree %s sibling"%labparts[0] ,url_for(".by_label", label=lab)))

    arith_equiv = nf.arith_equiv()
    if arith_equiv[0]>0:
        if len(arith_equiv[1])>0:
            resinfo.append(('ae', ', '.join(arith_equiv[1]), len(arith_equiv[1])))
            for aelab in arith_equiv[2]:
                info['friends'].append(('Arithmetically equivalent sibling',url_for(".by_label", label=aelab)))
        else:
            resinfo.append(('ae', dnc, len(arith_equiv[1])))

    info['resinfo'] = resinfo
    info['learnmore'] = [('Global number field labels', url_for(
        ".render_labels_page")), 
        (Completename, url_for(".render_discriminants_page")),
        ('How data was computed', url_for(".how_computed_page"))]
    if info['signature'] == [0,1]:
        info['learnmore'].append(('Quadratic imaginary class groups', url_for(".render_class_group_data")))
    # With Galois group labels, probably not needed here
    # info['learnmore'] = [('Global number field labels',
    # url_for(".render_labels_page")), ('Galois group
    # labels',url_for(".render_groups_page")),
    # (Completename,url_for(".render_discriminants_page"))]
    title = "Global Number Field %s" % info['label']

    if npr == 1:
        primes = 'prime'
    else:
        primes = 'primes'

    properties2 = [('Label', label),
                   ('Degree', '%s' % data['degree']),
                   ('Signature', '$%s$' % data['signature']),
                   ('Discriminant', '$%s$' % data['disc_factor']),
                   ('Ramified ' + primes + '', '$%s$' % ram_primes),
                   ('Class number', '%s %s' % (data['class_number'], grh_lab)),
                   ('Class group', '%s %s' % (data['class_group_invs'], grh_lab)),
                   ('Galois Group', group_display_short(data['degree'], t, C))
                   ]
    from lmfdb.artin_representations.math_classes import NumberFieldGaloisGroup
    try:
        info["tim_number_field"] = NumberFieldGaloisGroup(nf._data['coeffs'])
        v = nf.factor_perm_repn(info["tim_number_field"])
        def dopow(m):
            if m==0: return ''
            if m==1: return '*'
            return '*<sup>%d</sup>'% m

        info["mydecomp"] = [dopow(x) for x in v]
    except AttributeError:
        pass
#    del info['_id']
    return render_template("number_field.html", properties2=properties2, credit=NF_credit, title=title, bread=bread, code=nf.code, friends=info.pop('friends'), learnmore=info.pop('learnmore'), info=info)


def format_coeffs2(coeffs):
    return format_coeffs(string2list(coeffs))


def format_coeffs(coeffs):
    return pol_to_html(str(coeff_to_poly(coeffs)))
#    return web_latex(coeff_to_poly(coeffs))


#@nf_page.route("/")
# def number_fields():
#    if len(request.args) != 0:
#        return number_field_search(**request.args)
#    info['learnmore'] = [('Global Number Field labels', url_for(".render_labels_page")), ('Galois group labels',url_for(".render_groups_page")), (Completename,url_for(".render_discriminants_page"))]
#    return render_template("number_field_all.html", info = info)

@nf_page.route("/<label>")
def by_label(label):
    try:
        nflabel = nf_string_to_label(clean_input(label))
        if label != nflabel:
            return redirect(url_for(".by_label", label=nflabel), 301)
        return render_field_webpage({'label': nf_string_to_label(label)})
    except ValueError as err:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid number field. %s" % (label,err)), "error")
        bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Search results', ' ')]
        return search_input_error({'err':''}, bread)

# input is a sage int


def make_disc_key(D):
    s = 1
    if D < 0:
        s = -1
    Dz = D.abs()
    if Dz == 0:
        D1 = 0
    else:
        D1 = int(Dz.log(10))
    return s, '%03d%s' % (D1, str(Dz))

def number_field_search(**args):
    info = to_dict(args)

    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
    t = 'Global Number Field search results'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Search results', ' ')]

    # for k in info.keys():
    #  nf_logger.debug(str(k) + ' ---> ' + str(info[k]))
    # nf_logger.debug('******************* '+ str(info['search']))

    if 'natural' in info:
        query = {'label_orig': info['natural']}
        try:
            parse_nf_string(info,query,'natural',name="Label",qfield='label')
            return redirect(url_for(".by_label", label= clean_input(query['label_orig'])))
        except ValueError:
            query['err'] = info['err']
            return search_input_error(query, bread)

    if 'algebra' in info:
        fields=info['algebra'].split('_')
        fields2=[WebNumberField.from_coeffs(a) for a in fields]
        for j in range(len(fields)):
            if fields2[j] is None:
                fields2[j] = WebNumberField.fakenf(fields[j])
        t = 'Number field algebra'
        info = {}
        info = {'fields': fields2}
        return render_template("number_field_algebra.html", info=info, title=t, bread=bread)



    query = {}
    try:
        parse_galgrp(info,query, qfield='galois')
        parse_ints(info,query,'degree')
        parse_bracketed_posints(info,query,'signature',split=False,exactlength=2)
        parse_signed_ints(info,query,'discriminant',qfield=('disc_sign','disc_abs_key'),parse_one=make_disc_key)
        parse_ints(info,query,'class_number')
        parse_bracketed_posints(info,query,'class_group',split=False,check_divisibility='increasing')
        parse_primes(info,query,'ur_primes',name='Unramified primes',qfield='ramps',mode='complement',to_string=True)
        # modes are now contained (in), exactly, include
        if 'ram_quantifier' in info and str(info['ram_quantifier']) == 'include':
            mode = 'append'
            parse_primes(info,query,'ram_primes','ramified primes','ramps',mode,to_string=True)
        elif 'ram_quantifier' in info and str(info['ram_quantifier']) == 'contained':
            parse_primes(info,query,'ram_primes','ramified primes','ramps_all','subsets',to_string=False)
            pass # build list
        else:
            mode = 'liststring'
            parse_primes(info,query,'ram_primes','ramified primes','ramps_all',mode)
    except ValueError:
        return search_input_error(info, bread)
    count = parse_count(info)
    start = parse_start(info)

    if info.get('paging'):
        try:
            paging = int(info['paging'])
            if paging == 0:
                start = 0
        except:
            pass

    C = base.getDBConnection()
    # nf_logger.debug(query)
    info['query'] = dict(query)
    if 'lucky' in args:
        one = C.numberfields.fields.find_one(query)
        if one:
            label = one['label']
            return redirect(url_for(".by_label", label=clean_input(label)))

    fields = C.numberfields.fields

    res = fields.find(query)
    res = res.sort([('degree', ASC), ('disc_abs_key', ASC),('disc_sign', ASC)])

    if 'download' in info and info['download'] != '0':
        return download_search(info, res)

    nres = res.count()
    res = res.skip(start).limit(count)

    if(start >= nres):
        start -= (1 + (start - nres) / count) * count
    if(start < 0):
        start = 0

    info['fields'] = res
    info['number'] = nres
    info['start'] = start
    if nres == 1:
        info['report'] = 'unique match'
    else:
        if nres > count or start != 0:
            info['report'] = 'displaying matches %s-%s of %s' % (start + 1, min(nres, start + count), nres)
        else:
            info['report'] = 'displaying all %s matches' % nres

    info['wnf'] = WebNumberField.from_data
    return render_template("number_field_search.html", info=info, title=t, bread=bread)


def search_input_error(info, bread):
    return render_template("number_field_search.html", info=info, title='Global Number Field Search Error', bread=bread)


def residue_field_degrees_function(nf):
    """ Given a WebNumberField, returns a function that has
            input: a prime p
            output: the residue field degrees at the prime p
    """
    k1 = nf.gpK()
    D = nf.disc()
    return main_work(k1,D,'pari')

def sage_residue_field_degrees_function(nf):
    """ Version of above which takes a sage number field
        Used by Artin representation code when the Artin field is not
        in the database.
    """
    D = nf.disc()
    return main_work(pari(nf),D,'sage')

def main_work(k1, D, typ):
    # Difference for sage vs pari array indexing
    ind = 3 if typ is 'sage' else 4
    def decomposition(p):
        if not ZZ(p).divides(D):
            dec = k1.idealprimedec(p)
            dec = [z[ind] for z in dec]
            return dec
        else:
            raise ValueError("Expecting a prime not dividing D")
    return decomposition

# Compute Frobenius cycle types, returns string nicely presenting this


def frobs(nf):
    frob_at_p = residue_field_degrees_function(nf)
    D = nf.disc()
    ans = []
    seeram = False
    for p in primes(2, 60):
        if not ZZ(p).divides(D):
            # [3] ,   [2,1]
            dec = frob_at_p(p)
            vals = list(set(dec))
            vals = sorted(vals, reverse=True)
            dec = [[x, dec.count(x)] for x in vals]
            #dec2 = ["$" + str(x[0]) + ('^{' + str(x[1]) + '}$' if x[1] > 1 else '$') for x in dec]
            s = '$'
            firstone = 1
            for j in dec:
                if firstone == 0:
                    s += '{,}\,'
                s += str(j[0])
                if j[1] > 1:
                    s += '^{' + str(j[1]) + '}'
                firstone = 0
            s += '$'
            ans.append([p, s])
        else:
            ans.append([p, 'R'])
            seeram = True
    return ans, seeram


def download_search(info, res):
    dltype = info.get('Submit')
    delim = 'bracket'
    com = r'\\'  # single line comment start
    com1 = ''  # multiline comment start
    com2 = ''  # multiline comment end
    filename = 'fields.gp'
    mydate = time.strftime("%d %B %Y")
    if dltype == 'sage':
        com = '#'
        filename = 'fields.sage'
    if dltype == 'mathematica':
        com = ''
        com1 = '(*'
        com2 = '*)'
        delim = 'brace'
        filename = 'fields.ma'
    if dltype == 'magma':
        com = ''
        com1 = '/*'
        com2 = '*/'
        delim = 'magma'
        filename = 'fields.m'
    s = com1 + "\n"
    s += com + ' Global number fields downloaded from the LMFDB downloaded %s\n'% mydate
    s += com + ' Below is a list called data. Each entry has the form:\n'
    s += com + '   [polynomial, discriminant, t-number, class group]\n'
    s += com + ' Here the t-number is for the Galois group\n'
    s += com + ' If a class group was not computed, the entry is [-1]\n'
    s += '\n' + com2
    s += '\n'
    if dltype == 'magma':
        s += 'data := ['
    else:
        s += 'data = ['
    s += '\\\n'
    Qx = PolynomialRing(QQ,'x')
    str2pol = lambda s: Qx([QQ(str(c)) for c in s.split(',')])
    for f in res:
        ##  We should try to avoid using database specific information here
        ##  Kept for now for speed
#        wnf = WebNumberField.from_data(f)
#        entry = ', '.join(
#            [str(wnf.poly()), str(wnf.disc()), str(wnf.galois_t()), str(wnf.class_group_invariants_raw())])
        pol = str2pol(f['coeffs'])
        D = decodedisc(f['disc_abs_key'], f['disc_sign'])
        gal_t = f['galois']['t']
        if 'class_group' in f:
            cl = string2list(f['class_group'])
        else:
            cl = [-1]
        entry = ', '.join([str(pol), str(D), str(gal_t), str(cl)])
        s += '[' + entry + ']' + ',\\\n'
    s = s[:-3]
    if dltype == 'gp':
        s += '];\n'
    else:
        s += ']\n'
    if delim == 'brace':
        s = s.replace('[', '{')
        s = s.replace(']', '}')
    if delim == 'magma':
        s = s.replace('[', '[*')
        s = s.replace(']', '*]')
        s += ';'
    strIO = StringIO.StringIO()
    strIO.write(s)
    strIO.seek(0)
    return send_file(strIO,
                     attachment_filename=filename,
                     as_attachment=True,
                     add_etags=False)

