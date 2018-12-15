# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones 

import re

from lmfdb.db_backend import db
from flask import render_template, request, url_for, redirect, abort
from lmfdb.utils import image_callback, flash_error, list_to_factored_poly_otherorder
from lmfdb.search_parsing import clean_input, parse_ints, parse_bracketed_posints, parse_rational, parse_restricted
from lmfdb.search_wrapper import search_wrap
from lmfdb.transitive_group import small_group_display_knowl
from sage.all import ZZ, QQ, latex, matrix, valuation, PolynomialRing
from lmfdb.hypergm import hypergm_page

HGM_FAMILY_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+$')
HGM_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+_t-?\d+.\d+$')

HGM_credit = 'D. Roberts and M. Watkins'

def learnmore_list():
    return [('Completeness of the data', url_for(".completeness_page")),
            ('Source of the data', url_for(".how_computed_page")),
            ('Hypergeometric motive labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed
def learnmore_list_remove(matchstring):
    return filter(lambda t:t[0].find(matchstring) <0, learnmore_list())

def list2string(li):
    return ','.join([str(x) for x in li])

GAP_ID_RE = re.compile(r'^\[\d+,\d+\]$')

def dogapthing(m1):
    mnew = str(m1[2])
    mnew = mnew.replace(' ','')
    if GAP_ID_RE.match(mnew):
        mnew = mnew[1:-1]
        two = mnew.split(',')
        two = [int(j) for j in two]
        try:
            m1[2] = small_group_display_knowl(two[0],two[1])
        except TypeError:
            m1[2] = 'Gap[%d,%d]' % (two[0],two[1])
    else:
        m1[2] = '$%s$'% m1[2]
    return m1

def getgroup(m1,ell):
    pind = {2: 0,3:1,5:2,7:3,11:4,13:5}
    if len(m1[3][2])==0:
        return [m1[2], m1[0]]
    myA = list2string(m1[3][0])
    myB = list2string(m1[3][1])
    if len(myA)==0 and len(myB)==0:
        return [small_group_display_knowl(1,1), 1]
    mono = db.hgm_families.lucky({'A': myA, 'B': myB}, projection="mono")
    if mono is None:
        return ['??', 1]
    newthing = mono[pind[ell]]
    newthing = dogapthing(newthing[1])
    return [newthing[2], newthing[0]]

# Helper functions

# Take a family label and swap the roles of A and B
def normalize_family(label):
    m = re.match(r'^A((\d+\.)*\d+)_B((\d+\.)*\d+)$', label)
    a = sorted([int(u) for u in m.group(1).split('.')], reverse=True)
    b = sorted([int(u) for u in m.group(3).split('.')], reverse=True)
    aas = '.'.join([str(u) for u in a])
    bs = '.'.join([str(u) for u in b])
    if 1 in b or b[0]>a[0]:
        return 'A%s_B%s'%(aas, bs)
    return 'A%s_B%s'%(bs, aas)

def normalize_motive(label):
    m = re.match(r'^A((\d+\.)*\d+)_B((\d+\.)*\d+)_t(-?)(\d+)\.(\d+)$', label)
    a = sorted([int(u) for u in m.group(1).split('.')], reverse=True)
    b = sorted([int(u) for u in m.group(3).split('.')], reverse=True)
    aas = '.'.join([str(u) for u in a])
    bs = '.'.join([str(u) for u in b])
    if 1 in b or b[0]>a[0]:
        return 'A%s_B%s_t%s%s.%s'%(aas, bs,m.group(5),m.group(6),m.group(7))
    return 'A%s_B%s_t%s%s.%s'%(bs, aas, m.group(5), m.group(7), m.group(6))

# A and B are lists, tn and td are num/den for t
def ab_label(A,B):
    return "A%s_B%s"%('.'.join(str(c) for c in A),'.'.join(str(c) for c in B))

def list2Cnstring(li):
    l2 = [a for a in li if a>1]
    if l2 == []:
        return 'C_1'
    fa = [ZZ(a).factor() for a in l2]
    eds = []
    for b in fa:
        for pp in b:
            eds.append([pp[0],pp[1]])
    eds.sort()
    l2 = ['C_{%d}'% (a[0]**a[1]) for a in eds]
    return (r'\times ').join(l2)

def showlist(li):
    if len(li)==0:
        return r'[\ ]'
    return li

def splitint(a,p):
    if a==1:
        return ' '
    j = valuation(a,p)
    if j==0:
        return str(a)
    a = a/p**j
    if a==1:
        return latex(ZZ(p**j).factor())
    return str(a)+r'\cdot'+latex(ZZ(p**j).factor())


def make_abt_label(A,B,t):
    AB_str = ab_label(A,B)
    t = QQ(t)
    t_str = "_t%s.%s" % (t.numerator(), t.denominator())
    return AB_str + t_str

def make_t_label(t):
    tsage = QQ(t)
    return "t%s.%s" % (tsage.numerator(), tsage.denominator())

def get_bread(breads=[]):
    bc = [("Motives", url_for("motive.index")), ("Hypergeometric", url_for("motive.index2")), ("$\Q$", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def display_t(t):
    return str(QQ(t))

# For displaying factored conductors
def factorint(inp):
    return latex(ZZ(inp).factor())

# Returns a string of val if val = 0, 1, -1, or version with p factored out otherwise
def factor_out_p(val, p):
    val = ZZ(val)
    if val == 0 or val == -1:
        return str(val)
    if val==1:
        return '+1'
    s = 1
    if val<0:
        s = -1
        val = -val
    ord = val.valuation(p)
    val = val/p**ord
    out = ''
    if s == -1:
        out += '-'
    else:
        out += '+'
    if ord==1:
        out +=  str(p)
    elif ord>1:
        out +=  '%d^{%d}' % (p, ord)
    if val>1:
        if ord ==1:
            out += r'\cdot '
        out += str(val)
    return out

# c is a list of coefficients
def poly_with_factored_coeffs(c, p):
    c = [factor_out_p(b,p) for b in c]
    out = ''
    for j in range(len(c)):
        xpow = 'x^{'+ str(j) +'}'
        if j == 0:
            xpow = ''
        elif j==1:
            xpow = 'x'
        if c[j] != '0':
            if c[j] == '+1':
                if j==0:
                    out += '+1'
                else:
                    out += '+'+xpow
            elif c[j] == '-1':
                if j==0:
                    out += '-1'
                else:
                    out += '-'+ xpow
            else:
                if j==0:
                    out += c[j]
                else:
                    out += c[j] + xpow
    if out[0] == '+':
        out = out[1:]
    return out

@hypergm_page.route("/")
def index():
    bread = get_bread()
    if len(request.args) != 0:
        return hgm_search(request.args)
    info = {'count': 20}
    return render_template("hgm-index.html", title="Hypergeometric Motives over $\Q$", bread=bread, credit=HGM_credit, info=info, learnmore=learnmore_list())



@hypergm_page.route("/plot/circle/<AB>")
def hgm_family_circle_image(AB):
    A,B = AB.split("_")
    from plot import circle_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = circle_image(A, B)
    return image_callback(G)

@hypergm_page.route("/plot/linear/<AB>")
def hgm_family_linear_image(AB):
    # piecewise linear, as opposed to piecewise constant
    A,B = AB.split("_")
    from plot import piecewise_linear_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = piecewise_linear_image(A, B)
    return image_callback(G)

@hypergm_page.route("/plot/constant/<AB>")
def hgm_family_constant_image(AB):
    # piecewise constant
    A,B = AB.split("_")
    from plot import piecewise_constant_image
    A = map(int,A[1:].split("."))
    B = map(int,B[1:].split("."))
    G = piecewise_constant_image(A, B)
    return image_callback(G)


@hypergm_page.route("/<label>")
def by_family_label(label):
    return hgm_search({'jump_to': label})

@hypergm_page.route("/<label>/<t>")
def by_label(label, t):
    return hgm_search({'jump_to': label+'_'+t})

def hgm_jump(info):
    label = clean_input(info['jump_to'])
    if HGM_LABEL_RE.match(label):
        return render_hgm_webpage(normalize_motive(label))
    if HGM_FAMILY_LABEL_RE.match(label):
        return render_hgm_family_webpage(normalize_family(label))
    flash_error('%s is not a valid label for a hypergeometric motive or family of hypergeometric motives', label)
    return redirect(url_for(".index"))

@search_wrap(template="hgm-search.html",
             table=db.hgm_motives, # overridden if family search
             title=r'Hypergeometric Motive over $\Q$ Search Result',
             err_title=r'Hypergeometric Motive over $\Q$ Search Input Error',
             per_page=20,
             shortcuts={'jump_to':hgm_jump},
             bread=lambda:get_bread([("Search Results", '')]),
             credit=lambda:HGM_credit,
             learnmore=learnmore_list)
def hgm_search(info, query):
    family_search = False
    if info.get('Submit Family') or info.get('family'):
        family_search = True
        query['__title__'] = r'Hypergeometric Family over $\Q$ Search Result'
        query['__err_title__'] = r'Hypergeometric Family over $\Q$ Search Input Error'
        query['__table__'] = db.hgm_families

    queryab = {}
    for param in ['A', 'B', 'A2', 'B2', 'A3', 'B3', 'A5', 'B5', 'A7', 'B7',
                  'Au2', 'Bu2', 'Au3', 'Bu3', 'Au5', 'Bu5', 'Au7', 'Bu7']:
        parse_bracketed_posints(info, queryab, param, split=False,
                                listprocess=lambda a: sorted(a, reverse=True))
    # Combine the parts of the query if there are A,B parts
    if queryab:
        queryabrev = {}
        for k in queryab.keys():
            queryabrev[k+'rev'] = queryab[k]
        query['$or'] = [queryab, queryabrev]

    # generic, irreducible not in DB yet
    parse_ints(info, query, 'degree')
    parse_ints(info, query, 'weight')
    parse_bracketed_posints(info, query, 'famhodge', 'family Hodge vector',split=False)
    parse_restricted(info, query, 'sign', allowed=['+1',1,-1], process=int)
    # Make a version to search reversed way
    if not family_search:
        parse_ints(info, query, 'conductor', 'Conductor' , 'cond')
        parse_rational(info, query, 't')
        parse_bracketed_posints(info, query, 'hodge', 'Hodge vector')

    info['make_label'] = make_abt_label
    info['make_t_label'] = make_t_label
    info['ab_label'] = ab_label
    info['display_t'] = display_t
    info['family'] = family_search
    info['factorint'] = factorint

def render_hgm_webpage(label):
    data = None
    info = {}
    data = db.hgm_motives.lookup(label)
    if data is None:
        abort(404, "Hypergeometric motive " + label + " was not found in the database.")
    title = 'Hypergeometric Motive:' + label
    A = data['A']
    B = data['B']
    det = db.hgm_families.lucky({'A': A, 'B': B}, 'det')
    if det is None:
        det = 'data not computed'
    else:
        det = [det[0],str(det[1])]
        d1 = det[1]
        d1 = re.sub(r'\s','', d1)
        d1 = re.sub(r'(.)\(', r'\1*(', d1)
        R = PolynomialRing(ZZ, 't')
        if det[1]=='':
            d2 = R(1)
        else:
            d2 = R(d1)
        det = d2(QQ(data['t']))*det[0]
    t = latex(QQ(data['t']))
    typee = 'Orthogonal'
    if (data['weight'] % 2) == 1 and (data['degree'] % 2) == 0:
        typee = 'Symplectic'
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
    locinfo = data['locinfo']
    for j in range(len(locinfo)):
        locinfo[j] = [primes[j]] + locinfo[j]
        #locinfo[j][2] = poly_with_factored_coeffs(locinfo[j][2], primes[j])
        locinfo[j][2] = list_to_factored_poly_otherorder(locinfo[j][2], vari='x')
    hodge = data['hodge']
    famhodge = data['famhodge']
    prop2 = [
        ('Degree', '\(%s\)' % data['degree']),
        ('Weight',  '\(%s\)' % data['weight']),
        ('Hodge vector',  '\(%s\)' % hodge),
        ('Conductor', '\(%s\)' % data['cond']),
    ]
    # Now add factorization of conductor
    Cond = ZZ(data['cond'])
    if not (Cond.abs().is_prime() or Cond == 1):
        data['cond'] = "%s=%s" % (str(Cond), factorint(data['cond']))

    info.update({
                'A': A,
                'B': B,
                't': t,
                'degree': data['degree'],
                'weight': data['weight'],
                'sign': data['sign'],
                'sig': data['sig'],
                'hodge': hodge,
                'famhodge': famhodge,
                'cond': data['cond'],
                'req': data['req'],
                'lcms': data['lcms'],
                'type': typee,
                'det': det,
                'locinfo': locinfo
                })
    AB_data, t_data = data["label"].split("_t")
    friends = [("Motive family "+AB_data.replace("_"," "), url_for(".by_family_label", label = AB_data))]
    friends.append(('L-function', url_for("l_functions.l_function_hgm_page", label=AB_data, t='t'+t_data)))
#    if rffriend != '':
#        friends.append(('Discriminant root field', rffriend))


    bread = get_bread([(label, ' ')])
    return render_template("hgm-show-motive.html", credit=HGM_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends, learnmore=learnmore_list())

def render_hgm_family_webpage(label):
    data = None
    info = {}
    data = db.hgm_families.lookup(label)
    if data is None:
        abort(404, "Hypergeometric motive family " + label + " was not found in the database.")
    title = 'Hypergeometric Motive Family:' + label
    A = data['A']
    B = data['B']
    hodge = data['famhodge']
    mydet = data['det']
    detexp = QQ(data['weight']*data['degree'])
    detexp = -detexp/2
    mydet = r'\Q(%s)\otimes\Q(\sqrt{'%str(detexp)
    if int(data['det'][0]) != 1:
        mydet += str(data['det'][0])
    if len(data['det'][1])>0:
        mydet += data['det'][1]
    if int(data['det'][0]) == 1 and len(data['det'][1])==0:
        mydet += '1'
    mydet += '})'
    bezoutmat = matrix(data['bezout'])
    bezoutdet = bezoutmat.det()
    bezoutmat = latex(bezoutmat)
    snf = data['snf']
    snf = list2Cnstring(snf)
    typee = 'Orthogonal'
    if (data['weight'] % 2) == 1 and (data['degree'] % 2) == 0:
        typee = 'Symplectic'
    ppart = [[2, [data['A2'],data['B2'],data['C2']]],
        [3, [data['A3'],data['B3'],data['C3']]],
        [5, [data['A5'],data['B5'],data['C5']]],
        [7, [data['A7'],data['B7'],data['C7']]]]
    prop2 = [
        ('Degree', '\(%s\)' % data['degree']),
        ('Weight',  '\(%s\)' % data['weight'])
    ]
    mono = [m for m in data['mono'] if m[1] != 0]
    mono = [[m[0], dogapthing(m[1]),
      getgroup(m[1],m[0]),
      latex(ZZ(m[1][0]).factor())] for m in mono]
    mono = [[m[0], m[1], m[2][0], splitint(m[1][0]/m[2][1],m[0]), m[3]] for m in mono]
    info.update({
                'A': A,
                'B': B,
                'degree': data['degree'],
                'weight': data['weight'],
                'hodge': hodge,
                'det': mydet,
                'snf': snf,
                'bezoutmat': bezoutmat,
                'bezoutdet': bezoutdet,
                'mono': mono,
                'imprim': data['imprim'],
                'ppart': ppart,
                'type': typee,
                'junk': small_group_display_knowl(18,2),
                'showlist': showlist
                })
    friends = [('Motives in the family', url_for('hypergm.index')+"?A=%s&B=%s" % (str(A), str(B)))]
#    if unramfriend != '':
#        friends.append(('Unramified subfield', unramfriend))
#    if rffriend != '':
#        friends.append(('Discriminant root field', rffriend))

    info.update({"plotcircle":  url_for(".hgm_family_circle_image", AB  =  "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
    info.update({"plotlinear": url_for(".hgm_family_linear_image", AB  = "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
    info.update({"plotconstant": url_for(".hgm_family_constant_image", AB  = "A"+".".join(map(str,A))+"_B"+".".join(map(str,B)))})
    bread = get_bread([(label, ' ')])
    return render_template("hgm-show-family.html", credit=HGM_credit, title=title, bread=bread, info=info, properties2=prop2, friends=friends, learnmore=learnmore_list())


def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return(sl)

@hypergm_page.route("/Completeness")
def completeness_page():
    t = 'Completeness of Hypergeometric Motive Data over $\Q$'
    bread = get_bread(('Completeness',''))
    return render_template("single.html", kid='dq.hgm.extent',
           credit=HGM_credit, title=t, bread=bread,
           learnmore=learnmore_list_remove('Completeness'))

@hypergm_page.route("/Source")
def how_computed_page():
    t = 'Source of Hypergeometric Motive Data over $\Q$'
    bread = get_bread(('Source',''))
    return render_template("single.html", kid='dq.hgm.source',
           credit=HGM_credit, title=t, bread=bread,
           learnmore=learnmore_list_remove('Source'))

@hypergm_page.route("/Labels")
def labels_page():
    t = 'Labels for Hypergeometric Motives over $\Q$'
    bread = get_bread(('Labels',''))
    return render_template("single.html", kid='hgm.field.label',
           credit=HGM_credit, title=t, bread=bread,
           learnmore=learnmore_list_remove('labels'))

