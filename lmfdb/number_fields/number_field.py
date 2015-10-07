# -*- coding: utf-8 -*-

import pymongo
ASC = pymongo.ASCENDING
import time
import flask
import lmfdb.base as base
from lmfdb.base import app, getDBConnection, url_for
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response, redirect, g, session, Flask, send_file
import StringIO
from lmfdb.number_fields import nf_page, nf_logger
from lmfdb.WebNumberField import *

import re

import sage.all
from sage.all import ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, euler_phi, pari, prod
from sage.rings.arith import primes

from lmfdb.transitive_group import *

from lmfdb.utils import ajax_more, image_src, web_latex, to_dict, parse_range, parse_range2, coeff_to_poly, pol_to_html, comma, clean_input

NF_credit = 'the PARI group, J. Voight, J. Jones, D. Roberts, J. Kl&uuml;ners, G. Malle'
Completename = 'Completeness of this data'

# Remove whitespace first in all cases
# Matches a list of integers and ranges
LIST_RE = re.compile(r'^(-?\d+|(-?\d+--?\d+))(,(-?\d+|(-?\d+--?\d+)))*$')
LIST_SIMPLE_RE = re.compile(r'^(-?\d+)(,-?\d+)*$')
PAIR_RE = re.compile(r'^\[\d+,\d+\]$')
IF_RE = re.compile(r'^\[\]|(\[\d+(,\d+)*\])$')  # invariant factors
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
    return {'number_field_data': number_field_data}

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


def parse_field_string(F):  # parse Q, Qsqrt2, Qsqrt-4, Qzeta5, etc
    if F == 'Q':
        return '1.1.1.1'
    if F == 'Qi':
        return '2.0.4.1'
    # Change unicode dash with minus sign
    F = F.replace(u'\u2212', '-')
    # remove non-ascii characters from F
    F = F.decode('utf8').encode('ascii', 'ignore')
    fail_string = str(F + ' is not a valid field label or name or polynomial, or is not ')
    if len(F) == 0:
        return "Entry for the field was left blank.  You need to enter a field label, field name, or a polynomial."
    if F[0] == 'Q':
        if F[1:5] in ['sqrt', 'root']:
            try:
                d = ZZ(str(F[5:])).squarefree_part()
            except ValueError:
                return fail_string
            if d % 4 in [2, 3]:
                D = 4 * d
            else:
                D = d
            absD = D.abs()
            s = 0 if D < 0 else 2
            return '2.%s.%s.1' % (s, str(absD))
        if F[1:5] == 'zeta':
            try:
                d = ZZ(str(F[5:]))
            except ValueError:
                return fail_string
            if d < 1:
                return fail_string
            if d % 4 == 2:
                d /= 2  # Q(zeta_6)=Q(zeta_3), etc)
            if d == 1:
                return '1.1.1.1'
            deg = euler_phi(d)
            if deg > 23:
                return '%s is not ' % F
            adisc = CyclotomicField(d).discriminant().abs()  # uses formula!
            return '%s.0.%s.1' % (deg, adisc)
        return fail_string
    # check if a polynomial was entered
    F = F.replace('X', 'x')
    if 'x' in F:
        F1 = F.replace('^', '**')
        # print F
        F1 = poly_to_field_label(F1)
        if F1:
            return F1
        return str(F + ' is not ')
    return F


@app.route("/NF")
def NF_redirect():
    return redirect(url_for(".number_field_render_webpage", **request.args))

# function copied from classical_modular_form.py
# def set_sidebar(l):
#        res=list()
##       print "l=",l
#        for ll in l:
#                if(len(ll)>1):
#                        content=list()
#                        for n in range(1,len(ll)):
#                                content.append(ll[n])
#                        res.append([ll[0],content])
#       print "res=",res
#        return res


@nf_page.route("/GaloisGroups")
def render_groups_page():
    info = {}
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
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
    return render_template("number_field_labels.html", info=info, credit=NF_credit, title=t, bread=bread, learnmore=info.pop('learnmore'))


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
    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page"))]
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
                return send_file(filepath, as_attachment=True)
            else:
                info['message'] = 'File not found'
                return class_group_request_error(info, bread)
        else:
            info['message'] = 'Invalid congruence requested'
            return class_group_request_error(info, bread)

    return render_template("class_group_data.html", info=info, credit="A. Mosunov and M. J. Jacobson, Jr.", title=t, bread=bread, learnmore=info.pop('learnmore'))

def class_group_request_error(info, bread):
    t = 'Class Groups of Quadratic Imaginary Fields'
    return render_template("class_group_data.html", info=info, credit="A. Mosunov and M. J. Jacobson, Jr.", title=t, bread=bread, learnmore=info.pop('learnmore'))


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
        info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
        return render_template("number_field_all.html", info=info, credit=NF_credit, title=t, bread=bread)  # , learnmore=info.pop('learnmore'))
    else:
        return number_field_search(**args)

@nf_page.route("/random")
def random_nfglobal():
    from sage.misc.prandom import randint
    C = getDBConnection()
    init_nf_count()
    n = randint(0,nfields-1)
    label = C.numberfields.fields.find()[n]['label']
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

    if 'label' in args:
        label = clean_input(args['label'])
        nf = WebNumberField(label)
        data = {}
    if nf.is_null():
        bread.append(('Search results', ' '))
        label2 = re.sub(r'[<>]', '', args['label'])
        if 'You need to enter a field' in label2:
            info['err'] = label2
        else:
            info['err'] = 'No such field: %s in the database' % label2
        info['label'] = args['label_orig'] if 'label_orig' in args else args['label']
        return search_input_error(info, bread)

    info['wnf'] = nf
    from lmfdb.WebNumberField import nf_display_knowl
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
    data['frob_data'], data['seeram'] = frobs(nf.K())
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
    info.update({
        'label': pretty_label,
        'label_raw': label,
        'polynomial': web_latex_split_on_pm(nf.K().defining_polynomial()),
        'ram_primes': ram_primes,
        'integral_basis': zk,
        'regulator': web_latex(nf.regulator()),
        'unit_rank': nf.unit_rank(),
        'root_of_unity': web_latex(nf.K().primitive_root_of_unity()),
        'fund_units': nf.units(),
        'grh_label': grh_label
    })

    bread.append(('%s' % info['label_raw'], ' '))
    info['downloads_visible'] = True
    info['downloads'] = [('worksheet', '/')]
    info['friends'] = []
    if nf.can_class_number():
        info['friends'].append(('L-function', "/L/NumberField/%s" % label))
    info['friends'].append(('Galois group', "/GaloisGroup/%dT%d" % (n, t)))
    if 'dirichlet_group' in info:
        info['friends'].append(('Dirichlet group', url_for("characters.dirichlet_group_table",
                                                           modulus=int(conductor),
                                                           char_number_list=','.join(
                                                               [str(a) for a in dirichlet_chars]),
                                                           poly=info['polynomial'])))
    info['learnmore'] = [('Global number field labels', url_for(
        ".render_labels_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
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

    properties2 = [('Degree:', '%s' % data['degree']),
                   ('Signature:', '$%s$' % data['signature']),
                   ('Discriminant:', '$%s$' % data['disc_factor']),
                   ('Ramified ' + primes + ':', '$%s$' % ram_primes),
                   ('Class number:', '%s %s' % (data['class_number'], grh_lab)),
                   ('Class group:', '%s %s' % (data['class_group_invs'], grh_lab)),
                   ('Galois Group:', group_display_short(data['degree'], t, C))
                   ]
    from lmfdb.math_classes import NumberFieldGaloisGroup
    try:
        info["tim_number_field"] = NumberFieldGaloisGroup.find_one({"label": label})
        v = nf.factor_perm_repn(info["tim_number_field"])
        info["mydecomp"] = ['*' if x>0 else '' for x in v]
    except AttributeError:
        pass
#    del info['_id']
    return render_template("number_field.html", properties2=properties2, credit=NF_credit, title=title, bread=bread, friends=info.pop('friends'), learnmore=info.pop('learnmore'), info=info)


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

def split_label(label):
    """
      Parses number field labels. Allows for 3.1.4e1t11e1.1
    """
    tmp = label.split(".")
    tmp[2] = parse_product(tmp[2])
    return ".".join(tmp)


def parse_product(symbol):
    tmp = symbol.split("t")
    return str(prod(parse_power(pair) for pair in tmp))


def parse_power(pair):
    try:
        tmp = pair.split("e")
        return ZZ(tmp[0]) ** ZZ(tmp[1])
    except:
        return ZZ(pair)


@nf_page.route("/<label>")
def by_label(label):
    if FIELD_LABEL_RE.match(label):
        return render_field_webpage({'label': split_label(label)})
    parsed_label = parse_field_string(label)
    # This will cause a reasonable error page to be displayed if not valid
    if FIELD_LABEL_RE.match(parsed_label):
        return render_field_webpage({'label': split_label(parsed_label)})
    else:
        return render_field_webpage({'label': parsed_label})

def parse_list(L):
    L = str(L)
    if re.search("\\d", L):
        return [int(a) for a in L[1:-1].split(',')]
    return []
    # return eval(str(L)) works but using eval() is insecure

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

# We need to have a first level parsing of discs to have it
# as sage ints
# If we have an error, raise a parse error.  Should not be needed since we screen the inputs


def parse_discs(arg):
    # parsing can be thrown off by spaces
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if ',' in arg:
        return [parse_discs(a)[0] for a in arg.split(',')]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        low, high = 'i', 'i'
        if start:
            low = ZZ(str(start))
        if end:
            high = ZZ(str(end))
        if low == 'i':
            raise Exception('parsing error')
        if high == 'i':
            raise Exception('parsing error')
        return [[low, high]]
    else:
        return [ZZ(str(arg))]

# Input is the output of parse_discs, [[-5,-2], 10, 11, [16,100]]
# Output is a list of key/value pairs for the query


def list_to_query(dlist):
    # we need to split intervals which span 0
    x = 0
    while x < len(dlist):
        if type(dlist[x]) == list:
            if dlist[x][0] < 0 and dlist[x][1] > 0:  # split into pos/neg parts
                low, high = dlist[x][0], dlist[x][1]
                dlist[x] = [low, ZZ(-1)]
                dlist.insert(x + 1, [ZZ(1), high])
                x += 1
            # elif dlist[x][0] > dlist[x][1]:  # bogus entry
            #  dlist.pop(x)
            #  x -= 1 # to offset the increment below
        x += 1

    # if there is only one part, we don't need an $or
    if len(dlist) == 1:
        dlist = dlist[0]
        if type(dlist) == list:
            s0, d0 = make_disc_key(dlist[0])
            s1, d1 = make_disc_key(dlist[1])
            if s0 < 0:
                return [['disc_sign', s0], ['disc_abs_key', {'$gte': d1, '$lte': d0}]]
            else:
                return [['disc_sign', s0], ['disc_abs_key', {'$lte': d1, '$gte': d0}]]
        else:
            s0, d0 = make_disc_key(dlist)
            return [['disc_sign', s0], ['disc_abs_key', d0]]
    # Now dlist has length >1
    ans = []
    for x in dlist:
        if type(x) == list:
            s0, d0 = make_disc_key(x[0])
            s1, d1 = make_disc_key(x[1])
            if s0 < 0:
                ans.append({'disc_sign': s0, 'disc_abs_key': {'$gte': d1, '$lte': d0}})
            else:
                ans.append({'disc_sign': s0, 'disc_abs_key': {'$lte': d1, '$gte': d0}})
        else:
            s0, d0 = make_disc_key(x)
            ans.append({'disc_sign': s0, 'disc_abs_key': d0})
    return [['$or', ans]]


def number_field_search(**args):
    info = to_dict(args)

    info['learnmore'] = [('Global number field labels', url_for(".render_labels_page")), ('Galois group labels', url_for(".render_groups_page")), (Completename, url_for(".render_discriminants_page")), ('Quadratic imaginary class groups', url_for(".render_class_group_data"))]
    t = 'Global Number Field search results'
    bread = [('Global Number Fields', url_for(".number_field_render_webpage")), ('Search results', ' ')]

    # for k in info.keys():
    #  nf_logger.debug(str(k) + ' ---> ' + str(info[k]))
    # nf_logger.debug('******************* '+ str(info['search']))
        
    if 'natural' in info:
        field_id = info['natural']
        field_id_parsed = parse_field_string(info['natural'])
        if FIELD_LABEL_RE.match(field_id_parsed):
            field_id_parsed = split_label(field_id_parsed)  # allows factored labels 11.11.11e20.1
        return render_field_webpage({'label': field_id_parsed, 'label_orig': field_id})
    query = {}
    dlist = []
    for field in ['galois_group', 'degree', 'signature', 'discriminant', 'class_number', 'class_group']:
        if info.get(field):
            info[field] = clean_input(info[field])
            if field in ['class_group', 'signature']:
                # different regex for the two types
                if (field == 'signature' and PAIR_RE.match(info[field])) or (field == 'class_group' and IF_RE.match(info[field])):
                    query[field] = info[field][1:-1]
                else:
                    name = 'class group' if field == 'class_group' else 'signature'
                    info['err'] = 'Error parsing input for %s.  It needs to be a pair of integers in square brackets, such as [2,3] or [3,3]' % name
                    return search_input_error(info, bread)
            else:
                if field == 'galois_group':
                    try:
                        gcs = complete_group_codes(info[field])
                        if len(gcs) == 1:
                            query['galois'] = make_galois_pair(gcs[0][0], gcs[0][1])
# list(gcs[0])
                        if len(gcs) > 1:
                            query['galois'] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
                    except NameError as code:
                        info['err'] = 'Error parsing input for Galois group: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or comma separated list of labels.' % code
                        return search_input_error(info, bread)
                else:  # not signature, class group, or galois group
                    ran = info[field]
                    ran = ran.replace('..', '-')
                    if LIST_RE.match(ran):
                        if field == 'discriminant':
                            # dlist will contain the disc conditions
                            # as sage ints
                            dlist = parse_discs(ran)
                            # now convert to a query
                            tmp = list_to_query(dlist)
                            # Two cases, could be a list of sign/inequalties
                            # or an '$or'
                            if len(tmp) == 1:
                                tmp = tmp[0]
                            else:
                                query[tmp[0][0]] = tmp[0][1]
                                tmp = tmp[1]
                        else:
                            tmp = parse_range2(ran, field)
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
                    else:
                        name = re.sub('_', ' ', field)
                        info['err'] = 'Error parsing input for %s.  It needs to be an integer (such as 5), a range of integers (such as 2-100 or 2..100), or a comma-separated list of these (such as 2,3,8 or 3-5, 7, 8-100).' % name
                        return search_input_error(info, bread)
    if info.get('ur_primes'):
        # now we want a list of strings, no spaces, which might be big ints
        info['ur_primes'] = clean_input(info['ur_primes'])
        if LIST_SIMPLE_RE.match(info['ur_primes']):
            ur_primes = info['ur_primes'].split(',')
            # Assuming this will be the only nor in the query
            query['$nor'] = [{'ramps': x} for x in ur_primes]
        else:
            info['err'] = 'Error parsing input for unramified primes.  It needs to be an integer (such as 5), or a comma-separated list of integers (such as 2,3,11).'
            return search_input_error(info, bread)
    if info.get('ram_primes'):
        # now we want a list of strings, no spaces, which might be big ints
        info['ram_primes'] = clean_input(info['ram_primes'])
        if LIST_SIMPLE_RE.match(info['ram_primes']):
            ram_primes = info['ram_primes'].split(',')
            if str(info['ram_quantifier']) == 'some':
                query['ramps'] = {'$all': ram_primes}
            else:
                query['ramps'] = ram_primes
        else:
            info['err'] = 'Error parsing input for ramified primes.  It needs to be an integer (such as 5), or a comma-separated list of integers (such as 2,3,11).'
            return search_input_error(info, bread)

    count_default = 20
    if info.get('count'):
        try:
            count = int(info['count'])
        except:
            count = count_default
            info['count'] = count
    else:
        info['count'] = count_default
        count = count_default
    info['count'] = int(info['count'])

    start_default = 0
    if info.get('start'):
        try:
            start = int(info['start'])
            if(start < 0):
                start += (1 - (start + 1) / count) * count
        except:
            start = start_default
    else:
        start = start_default
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
            return render_field_webpage({'label': label})

    fields = C.numberfields.fields

    res = fields.find(
        query).sort([('degree', ASC), ('disc_abs_key', ASC), ('disc_sign', ASC), ('label', ASC)])

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


def residue_field_degrees_function(K):
    """ Given a sage field, returns a function that has
            input: a prime p
            output: the residue field degrees at the prime p
    """
    k1 = pari(K)
    D = K.disc()

    def decomposition(p):
        if not ZZ(p).divides(D):
            dec = k1.idealprimedec(p)
            dec = [z[3] for z in dec]
            return dec
        else:
            raise ValueError("Expecting a prime not dividing D")
    return decomposition

# Compute Frobenius cycle types, returns string nicely presenting this


def frobs(K):
    frob_at_p = residue_field_degrees_function(K)
    D = K.disc()
    ans = []
    seeram = False
    for p in primes(2, 60):
        if not ZZ(p).divides(D):
            # [3] ,   [2,1]
            dec = frob_at_p(p)
            vals = list(set(dec))
            vals = sorted(vals, reverse=True)
            dec = [[x, dec.count(x)] for x in vals]
            dec2 = ["$" + str(x[0]) + ('^{' + str(x[1]) + '}$' if x[1] > 1 else '$') for x in dec]
            s = '$'
            old = 2
            for j in dec:
                if old == 1:
                    s += '\: '
                s += str(j[0])
                if j[1] > 1:
                    s += '^{' + str(j[1]) + '}'
                old = j[1]
            s += '$'
            ans.append([p, s])
        else:
            ans.append([p, 'R'])
            seeram = True
    return ans, seeram


def download_search(info, res):
    dltype = info['Submit']
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
    for f in res:
        wnf = WebNumberField.from_data(f)
        cgi = wnf.class_group_invariants()
        entry = ', '.join(
            [str(wnf.poly()), str(wnf.disc()), str(wnf.galois_t()), str(wnf.class_group_invariants_raw())])
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
                     as_attachment=True)
