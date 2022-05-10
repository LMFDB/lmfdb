# -*- coding: utf-8 -*-
# This Blueprint is about Hypergeometric motives
# Author: John Jones, Edgar Costa


import re

from flask import render_template, request, url_for, redirect, abort
from sage.all import (
    is_prime, ZZ, QQ, latex, valuation, PolynomialRing, gcd)

from lmfdb import db
from lmfdb.utils import (
    image_callback, flash_error, list_to_factored_poly_otherorder,
    clean_input, parse_ints, parse_bracketed_posints, parse_rational,
    parse_restricted, integer_options, search_wrap,
    SearchArray, TextBox, TextBoxNoEg, SelectBox, CountBox, BasicSpacer, SearchButton,
    to_dict, web_latex, integer_divisors)
from lmfdb.utils.interesting import interesting_knowls
from lmfdb.utils.search_columns import SearchColumns, MathCol, ProcessedCol, MultiProcessedCol
from lmfdb.api import datapage
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.hypergm import hypergm_page
from .web_family import WebHyperGeometricFamily

HGM_FAMILY_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+$')
HGM_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+_t-?\d+.\d+$')


def learnmore_list():
    return [('Source and acknowledgments', url_for(".how_computed_page")),
            ('Completeness of the data', url_for(".completeness_page")),
            ('Reliability of the data', url_for(".reliability_page")),
            ('Hypergeometric motive labels', url_for(".labels_page"))]

# Return the learnmore list with the matchstring entry removed


def learnmore_list_remove(matchstring):
    return [t for t in learnmore_list() if t[0].find(matchstring) < 0]


def list2string(li):
    return ','.join(str(x) for x in li)


GAP_ID_RE = re.compile(r'^\[\d+,\d+\]$')


def dogapthing(m1):
    mnew = str(m1[2])
    mnew = mnew.replace(' ', '')
    if GAP_ID_RE.match(mnew):
        mnew = mnew[1:-1]
        two = mnew.split(',')
        two = [int(j) for j in two]
        try:
            m1[2] = abstract_group_display_knowl(f"{two[0]}.{two[1]}")
        except TypeError:
            m1[2] = f'Group({two[0]}.{two[1]})'
    else:
        # Fix multiple backslashes
        m1[2] = re.sub(r'\\+', r'\\', m1[2])
        m1[2] = '$%s$'% m1[2]
    return m1


def getgroup(m1, ell):
    pind = {2: 0, 3: 1, 5: 2, 7: 3, 11: 4, 13: 5}
    if not m1[3][2]:
        return [m1[2], m1[0]]
    myA = m1[3][0]
    myB = m1[3][1]
    if not myA and not myB:  # myA = myB = []
        return [abstract_group_display_knowl("1.1", "$C_1$"), 1]
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
    aas = '.'.join(str(u) for u in a)
    bs = '.'.join(str(u) for u in b)
    if 1 in b or b[0] > a[0]:
        return 'A%s_B%s' % (aas, bs)
    return 'A%s_B%s' % (bs, aas)


def normalize_motive(label):
    m = re.match(r'^A((\d+\.)*\d+)_B((\d+\.)*\d+)_t(-?)(\d+)\.(\d+)$', label)
    a = sorted([int(u) for u in m.group(1).split('.')], reverse=True)
    b = sorted([int(u) for u in m.group(3).split('.')], reverse=True)
    aas = '.'.join(str(u) for u in a)
    bs = '.'.join(str(u) for u in b)
    if 1 in b or b[0] > a[0]:
        return 'A%s_B%s_t%s%s.%s' % (aas, bs,
                                     m.group(5), m.group(6), m.group(7))
    return 'A%s_B%s_t%s%s.%s' % (bs, aas,
                                 m.group(5), m.group(7), m.group(6))

# Convert cyclotomic indices to gamma data

# 2 utilities


def incdict(d, v):
    if v in d:
        d[v] += 1
    else:
        d[v] = 1


def subdict(d, v):
    if d[v]>1:
        d[v] -= 1
    else:
        del d[v]

# produce a pair of lists of integers


def ab2gammas(A, B):
    ab = [{}, {}]
    for x in A:
        incdict(ab[0], x)
    for x in B:
        incdict(ab[1], x)
    gamma = [[], []]
    while ab[0] or ab[1]:
        m = max(list(ab[0]) + list(ab[1]))
        wh = 0 if m in ab[0] else 1
        gamma[wh].append(m)
        subdict(ab[wh], m)
        for d in integer_divisors(m)[:-1]:
            if d in ab[wh]:
                subdict(ab[wh], d)
            else:
                incdict(ab[1-wh], d)
    gamma[1] = [-1*z for z in gamma[1]]
    gamma = gamma[1]+gamma[0]
    gamma.sort()
    return gamma

# Convert cyclotomic indices to rational numbers


def cyc_to_QZ(A):
    alpha = []
    for Ai in A:
        alpha.extend([QQ(k)/Ai for k in range(1, Ai+1) if gcd(k, Ai) == 1])
    alpha.sort()
    return alpha

# A and B are lists, tn and td are num/den for t


def ab_label(A, B):
    return "A%s_B%s" % ('.'.join(str(c) for c in A),
                        '.'.join(str(c) for c in B))


def list2Cnstring(li):
    l2 = [a for a in li if a > 1]
    if not l2:
        return 'C_1'
    fa = [ZZ(a).factor() for a in l2]
    eds = []
    for b in fa:
        for pp in b:
            eds.append([pp[0], pp[1]])
    eds.sort()
    l2 = ['C_{%d}'% (a[0]**a[1]) for a in eds]
    return (r'\times ').join(l2)


def showlist(li):
    if not li:
        return r'[\ ]'
    return li


def splitint(a, p):
    if a==1:
        return ' '
    j = valuation(a, p)
    if j==0:
        return str(a)
    a = a/p**j
    if a==1:
        return latex(ZZ(p**j).factor())
    return str(a)+r'\cdot'+latex(ZZ(p**j).factor())


def make_abt_label(A, B, t):
    AB_str = ab_label(A, B)
    t = QQ(t)
    t_str = "_t%s.%s" % (t.numerator(), t.denominator())
    return AB_str + t_str


def make_t_label(t):
    tsage = QQ(t)
    return "t%s.%s" % (tsage.numerator(), tsage.denominator())


def get_bread(breads=[]):
    bc = [("Motives", url_for("motives")),
          ("Hypergeometric", url_for(".index")),
          (r"$\Q$", url_for(".index"))]
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
    if val == 1:
        return '+1'
    s = 1
    if val < 0:
        s = -1
        val = -val
    ord = val.valuation(p)
    val = val / p**ord
    out = ''
    if s == -1:
        out += '-'
    else:
        out += '+'
    if ord == 1:
        out += str(p)
    elif ord > 1:
        out += '%d^{%d}' % (p, ord)
    if val > 1:
        if ord == 1:
            out += r'\cdot '
        out += str(val)
    return out

# c is a list of coefficients


def poly_with_factored_coeffs(c, p):
    c = [factor_out_p(b, p) for b in c]
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
    info = to_dict(request.args, search_array=HGMSearchArray())
    if request.args:
        return hgm_search(info)
    return render_template(
        "hgm-index.html",
        title=r"Hypergeometric motives over $\Q$",
        bread=get_bread(),
        info=info,
        learnmore=learnmore_list())


def hgm_family_circle_plot_data(AB):
    A, B = AB.split("_")
    from .plot import circle_image
    A = [int(n) for n in A[1:].split(".")]
    B = [int(n) for n in B[1:].split(".")]
    G = circle_image(A, B)
    P = G.plot()
    import tempfile
    import os
    _, filename = tempfile.mkstemp('.png')
    P.save(filename)
    with open(filename) as f:
        data = f.read()
    os.unlink(filename)
    return data


@hypergm_page.route("/plot/circle/<AB>")
def hgm_family_circle_image(AB):
    A, B = AB.split("_")
    from .plot import circle_image
    A = [int(n) for n in A[1:].split(".")]
    B = [int(n) for n in B[1:].split(".")]
    G = circle_image(A, B)
    return image_callback(G)


@hypergm_page.route("/plot/linear/<AB>")
def hgm_family_linear_image(AB):
    # piecewise linear, as opposed to piecewise constant
    A, B = AB.split("_")
    from .plot import piecewise_linear_image
    A = [int(n) for n in A[1:].split(".")]
    B = [int(n) for n in B[1:].split(".")]
    G = piecewise_linear_image(A, B)
    return image_callback(G)


@hypergm_page.route("/plot/constant/<AB>")
def hgm_family_constant_image(AB):
    # piecewise constant
    A, B = AB.split("_")
    from .plot import piecewise_constant_image
    A = [int(n) for n in A[1:].split(".")]
    B = [int(n) for n in B[1:].split(".")]
    G = piecewise_constant_image(A, B)
    return image_callback(G)


@hypergm_page.route("/<label>")
def by_family_label(label):
    if HGM_FAMILY_LABEL_RE.match(label):
        return render_hgm_family_webpage(normalize_family(label))
    else:
        flash_error('%s is not a valid label for a family of hypergeometric motives', label)
        return redirect(url_for(".index"))


@hypergm_page.route("/<label>/<t>")
def by_label(label, t):
    if HGM_FAMILY_LABEL_RE.match(label):
        full_label = normalize_family(label) + "_" + t
        return render_hgm_webpage(full_label)
    else:
        flash_error('%s is not a valid label for a family of hypergeometric motives', label)
        return redirect(url_for(".index"))


def hgm_jump(info):
    label = clean_input(info['jump'])
    if HGM_LABEL_RE.match(label):
        return redirect(url_for_label(normalize_motive(label)), 301)
    if HGM_FAMILY_LABEL_RE.match(label):
        return redirect(url_for_label(normalize_family(label)), 301)
    flash_error('%s is not a valid label for a hypergeometric motive or family of hypergeometric motives', label)
    return redirect(url_for(".index"))


def url_for_label(label):
    if label.count("_") == 2:
        ab, t = label.rsplit("_", 1)
        return url_for(".by_label", label=ab, t=t)
    else:
        return url_for(".by_family_label", label=label)


hgm_columns = SearchColumns([
    MultiProcessedCol("label", None, "Label",
                      ["A", "B", "t"],
                      lambda A, B, t: '<a href="%s">%s</a>' % (
                          url_for('.by_family_label', label=ab_label(A, B)) if t is None else
                          url_for('.by_label', label=ab_label(A, B), t=make_t_label(t)),
                          ab_label(A, B) if t is None else
                          make_abt_label(A, B, t)),
                      default=True),
    MathCol("A", None, "$A$", default=True, short_title="A"),
    MathCol("B", None, "$B$", default=True, short_title="B"),
    ProcessedCol("t", None, "$t$", display_t, contingent=lambda info: info["search_type"] == "Motive", default=True, mathmode=True, align="center"),
    ProcessedCol("cond", None, "Conductor", factorint, contingent=lambda info: info["search_type"] == "Motive", default=True, mathmode=True, align="center"),
    MathCol("degree", None, "Degree", default=True),
    MathCol("weight", None, "Weight", default=True),
    MathCol("famhodge", None, "Hodge", default=True)])

hgm_columns.dummy_download = True
hgm_columns.db_cols = 1  # all cols, since the table varies


@search_wrap(table=db.hgm_motives,  # overridden if family search
             title=r'Hypergeometric motive over $\Q$ search resultS',
             err_title=r'Hypergeometric motive over $\Q$ search input error',
             columns=hgm_columns,
             per_page=50,
             shortcuts={'jump': hgm_jump},
             url_for_label=url_for_label,
             bread=lambda: get_bread([("Search results", '')]),
             learnmore=learnmore_list)
def hgm_search(info, query):
    info["search_type"] = search_type = info.get("search_type", info.get("hst", "Motive"))
    if search_type in ["Family", "RandomFamily"]:
        query['__title__'] = r'Hypergeometric family over $\Q$ search result'
        query['__err_title__'] = r'Hypergeometric family over $\Q$ search input error'
        query['__table__'] = db.hgm_families

    queryab = {}
    p = info.get('p', '2')
    for param in ['A', 'B']:
        parse_bracketed_posints(info, queryab, param, split=True,
                                keepbrackets=True,
                                listprocess=lambda a: sorted(a, reverse=True))
    parse_bracketed_posints(info, queryab, 'Ap', qfield='A'+p, split=True,
                            keepbrackets=True,
                            listprocess=lambda a: sorted(a, reverse=True))
    parse_bracketed_posints(info, queryab, 'Bp', qfield='B'+p, split=True,
                            keepbrackets=True,
                            listprocess=lambda a: sorted(a, reverse=True))
    parse_bracketed_posints(info, queryab, 'Apperp', qfield='Au'+p, split=True,
                            keepbrackets=True,
                            listprocess=lambda a: sorted(a, reverse=True))
    parse_bracketed_posints(info, queryab, 'Bpperp', qfield='Bu'+p, split=True,
                            keepbrackets=True,
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
    parse_bracketed_posints(info, query, 'famhodge', 'family Hodge vector', split=True)
    parse_restricted(info, query, 'sign', allowed=['+1', 1, -1], process=int)
    # Make a version to search reversed way
    if search_type not in ["Family", "RandomFamily"]:
        parse_ints(info, query, 'conductor', 'Conductor', 'cond')
        parse_rational(info, query, 't')
        parse_bracketed_posints(info, query, 'hodge', 'Hodge vector')

    # Should search on analytic conductor when available
    # Sorts A and B first by length, then by the elements of the list; could go another way

    info['make_label'] = make_abt_label
    info['make_t_label'] = make_t_label
    info['ab_label'] = ab_label
    info['display_t'] = display_t
    info['factorint'] = factorint


def render_hgm_webpage(label):
    data = None
    info = {}
    data = db.hgm_motives.lookup(label)
    if data is None:
        abort(404, "Hypergeometric motive " + label + " was not found in the database.")
    title = 'Hypergeometric motive:' + label
    A = data['A']
    B = data['B']

    alpha = cyc_to_QZ(A)
    beta = cyc_to_QZ(B)
    gammas = ab2gammas(A, B)

    det = db.hgm_families.lucky({'A': A, 'B': B}, 'det')
    if det is None:
        det = 'data not computed'
    else:
        det = [det[0], str(det[1])]
        d1 = det[1]
        d1 = re.sub(r'\s', '', d1)
        d1 = re.sub(r'(.)\(', r'\1*(', d1)
        R = PolynomialRing(ZZ, 't')
        if det[1]=='':
            d2 = R(1)
        else:
            d2 = R(d1)
        det = d2(QQ(data['t']))*det[0]
    t = latex(QQ(data['t']))
    typee = 'Orthogonal'
    if data['weight'] % 2 and not data['degree'] % 2:
        typee = 'Symplectic'
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71]
    locinfo = data['locinfo']
    for j in range(len(locinfo)):
        locinfo[j] = [primes[j]] + locinfo[j]
        # locinfo[j][2] = poly_with_factored_coeffs(locinfo[j][2], primes[j])
        locinfo[j][2] = list_to_factored_poly_otherorder(locinfo[j][2], vari='x')
    hodge = data['hodge']
    famhodge = data['famhodge']
    prop2 = [
        ('Label', '%s' % data['label']),
        ('A', r'\(%s\)' % A),
        ('B', r'\(%s\)' % B),
        ('Degree', r'\(%s\)' % data['degree']),
        ('Weight', r'\(%s\)' % data['weight']),
        ('Hodge vector', r'\(%s\)' % hodge),
        ('Conductor', r'\(%s\)' % data['cond']),
    ]
    # Now add factorization of conductor
    Cond = ZZ(data['cond'])
    if not (Cond.abs().is_prime() or Cond == 1):
        data['cond'] = "%s=%s" % (str(Cond), factorint(data['cond']))

    info.update({
                'A': A,
                'B': B,
                'alpha': web_latex(alpha),
                'beta': web_latex(beta),
                'gammas': gammas,
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
    friends = [("Motive family "+AB_data.replace("_", " "), url_for(".by_family_label", label=AB_data))]
    friends.append(('L-function', url_for("l_functions.l_function_hgm_page", label=AB_data, t='t'+t_data)))
#    if rffriend != '':
#        friends.append(('Discriminant root field', rffriend))
    downloads = [("Underlying data", url_for(".hgm_data", label=data["label"]))]

    AB = 'A = '+str(A)+', B = '+str(B)
    t_data = str(QQ(data['t']))

    bread = get_bread([('family '+str(AB), url_for(".by_family_label", label=AB_data)), ('t = '+t_data, ' ')])
    return render_template(
        "hgm-show-motive.html",
        title=title,
        bread=bread,
        info=info,
        properties=prop2,
        friends=friends,
        downloads=downloads,
        learnmore=learnmore_list(),
        KNOWL_ID="hgm.%s" % label,
    )


@hypergm_page.route("/data/<label>")
def hgm_data(label):
    bread = get_bread([(label, url_for_label(label)), ("Data", " ")])
    if HGM_LABEL_RE.match(label):
        title = f"Hypergeometric motive data - {label}"
        fam_label = label.split("_t")[0]
        return datapage([label, fam_label], ["hgm_motives", "hgm_families"], bread=bread, title=title)
    elif HGM_FAMILY_LABEL_RE.match(label):
        title = f"Hypergeometric motive family data - {label}"
        return datapage(label, "hgm_families", bread=bread, title=title)
    else:
        return abort(404, f"Invalid label {label}")


def parse_pandt(info, family):
    errs = []
    if family.euler_factors.keys():
        try:
            info['ps'] = [elt for elt in
                    integer_options(info.get('p', family.default_prange), family.maxp)
                    if elt <= family.maxp and is_prime(elt) and elt not in family.wild_primes]
        except (ValueError, TypeError) as err:
            info['ps'] = family.defaultp
            if err.args and err.args[0] == 'Too many options':
                errs.append(r"Only p up to %s are available" % (family.maxp))
            else:
                errs.append("<span style='color:black'>p</span> must be an integer, range of integers or comma separated list of integers")

        try:
            if info.get('t'):
                info['ts'] = sorted(list(set(map(QQ, info.get('t').split(",")))))
                info['t'] = ",".join(map(str, info['ts']))
            else:
                info['ts'] = None
        except (ValueError, TypeError):
            info['ts'] = None
            errs.append("<span style='color:black'>t</span> must be a rational or comma separated list of rationals")
    return errs


def render_hgm_family_webpage(label):
    try:
        family = WebHyperGeometricFamily.by_label(label)
    except (KeyError, ValueError) as err:
        return abort(404, err.args)
    info = to_dict(request.args)
    errs = parse_pandt(info, family)
    if errs:
        flash_error("<br>".join(errs))

    return render_template("hgm_family.html",
                           info=info,
                           family=family,
                           properties=family.properties,
                           bread=family.bread,
                           title=family.title,
                           friends=family.friends,
                           downloads=family.downloads,
                           KNOWL_ID="hgm.%s" % label,
                           learnmore=learnmore_list())


def show_slopes(sl):
    if str(sl) == "[]":
        return "None"
    return(sl)


@hypergm_page.route("/random_family")
def random_family():
    label = db.hgm_families.random()
    return redirect(url_for(".by_family_label", label=label))


@hypergm_page.route("/random_motive")
def random_motive():
    label = db.hgm_motives.random()
    s = label.split('_t')
    return redirect(url_for(".by_label", label=s[0], t='t'+s[1]))


@hypergm_page.route("/interesting_families")
def interesting_families():
    return interesting_knowls(
        "hgm",
        db.hgm_families,
        url_for_label,
        regex=HGM_FAMILY_LABEL_RE,
        title=r"Some interesting families of hypergeometric motives",
        bread=get_bread([("Interesting", " ")]),
        learnmore=learnmore_list()
    )


@hypergm_page.route("/interesting_motives")
def interesting_motives():
    return interesting_knowls(
        "hgm",
        db.hgm_motives,
        url_for_label,
        regex=HGM_LABEL_RE,
        title=r"Some interesting hypergeometric motives",
        bread=get_bread([("Interesting motives", " ")]),
        learnmore=learnmore_list()
    )


@hypergm_page.route("/Source")
def how_computed_page():
    t = r'Source and acknowledgments for hypergeometric motives over $\Q$'
    bread = get_bread(('Source', ''))
    return render_template("multi.html", kids=['rcs.source.hgm',
                                               'rcs.ack.hgm',
                                               'rcs.cite.hgm'],
           title=t, bread=bread,
           learnmore=learnmore_list_remove('Source'))


@hypergm_page.route("/Completeness")
def completeness_page():
    t = r'Completeness of hypergeometric motive data over $\Q$'
    bread = get_bread(('Completeness', ''))
    return render_template("single.html", kid='rcs.cande.hgm',
           title=t, bread=bread,
           learnmore=learnmore_list_remove('Completeness'))


@hypergm_page.route("/Reliability")
def reliability_page():
    t = r'Reliability of hypergeometric motive data over $\Q$'
    bread = get_bread(('Reliability', ''))
    return render_template("single.html", kid='rcs.rigor.hgm',
           title=t, bread=bread,
           learnmore=learnmore_list_remove('Reliability'))


@hypergm_page.route("/Labels")
def labels_page():
    t = r'Labels for hypergeometric motives over $\Q$'
    bread = get_bread(('Labels', ''))
    return render_template("single.html", kid='hgm.field.label',
           title=t, bread=bread,
           learnmore=learnmore_list_remove('labels'))


class HGMSearchArray(SearchArray):
    _sort = [('', 'degree', ['degree', 'weight', 'A', 'B', 'label']),
            ('weight', 'weight', ['weight', 'degree', 'A', 'B', 'label']),
            ('cond', 'conductor', ['cond', 'degree', 'weight', 'A', 'B', 'label']),
            ('famhodge', 'Family Hodge vector', ['degree', 'famhodge', 'weight', 'A', 'B', 'label'])]
    sorts = {
        "Family": _sort[:2] + _sort[3:],
        "Motive": _sort,
    }
    jump_example = "A2.2_B1.1_t1.2"
    jump_egspan = "an HGM label encoding the triple $(A, B, t)$"
    jump_knowl = 'hgm.search_input'
    jump_prompt = 'Label'

    def __init__(self):
        degree = TextBox(
            name="degree",
            label="Degree",
            knowl="hgm.degree",
            example="4",
            extra=['class="family"'])
        weight = TextBox(
            name="weight",
            label="Weight",
            knowl="hgm.weight",
            example="3",
            extra=['class="family"'])
        famhodge = TextBox(
            name="famhodge",
            label="Family Hodge vector",
            knowl="hgm.familyhodgevector",
            example="[1,1,1,1]",
            extra=['class="family"'])
        A = TextBox(
            name="A",
            label="$A$",
            knowl="hgm.defining_parameters",
            example="[3,2,2]",
            extra=['class="family"'])
        B = TextBox(
            name="B",
            label="$B$",
            knowl="hgm.defining_parameters",
            example="[6,4]",
            extra=['class="family"'])
        p = SelectBox(
            name="p",
            label="Prime $p$",
            example_col=True,
            options=[("", 2),
                     ("3", 3),
                     ("5", 5),
                     ("7", 7)])
        Ap = TextBox(
            name="Ap",
            label="$A_p$",
            knowl="hgm.defining_parameter_ppart",
            example="[2,2,1,1]",
            extra=['class="family"'])
        Bp = TextBox(
            name="Bp",
            label="$B_p$",
            knowl="hgm.defining_parameter_ppart",
            example="[2,2,1,1]",
            extra=['class="family"'])
        Apperp = TextBox(
            name="Apperp",
            label=r"$A^\perp_p$",
            knowl="hgm.defining_parameter_primetoppart",
            example="[2,2,1,1]",
            extra=['class="family"'])
        Bpperp = TextBox(
            name="Bpperp",
            label=r"$B^\perp_p$",
            knowl="hgm.defining_parameter_primetoppart",
            example="[2,2,1,1]",
            extra=['class="family"'])
        spacer = BasicSpacer("")

        conductor = TextBox(
            name="conductor",
            label="Conductor",
            knowl="hgm.conductor",
            example="64",
            example_span="a value, like 32, a list, like 32,64, or a range like 1..10000")
        hodge = TextBox(
            name="hodge",
            label="Hodge vector",
            knowl="mot.hodgevector",
            example="[1,1,1,1]")
        t = TextBox(
            name="t",
            label="Specialization point $t$",
            knowl="hgm.specpoint",
            example="3/2",
            example_span="3/2 (1 has an associated degree drop and is always in the database)")
        sign = TextBoxNoEg(
            name="sign",
            label=r"Root number $\epsilon$",
            knowl="lfunction.sign",
            example="-1",
            example_span="1 or -1, with -1 occurring only in the symplectic case")
        # The following two boxes are not yet enabled
        # generic = YesNoBox(
        #    name="generic",
        #    label="Generic",
        #    knowl="hgm.generic")
        # irreducible = YesNoBox(
        #    name="irreducible",
        #    label="Irreducible",
        #    knowl="hgm.irreducible")
        count = CountBox()

        self.family_array = [
            [degree, weight],
            [famhodge, A, B],
            [p, Ap, Bp],
            [spacer, Apperp, Bpperp]]

        self.motive_array = [
            [conductor],
            [hodge],
            [t],
            [sign],
            [count]]

        self.refine_family_array = [
            [degree, weight, famhodge, A, B],
            [p, Ap, Bp, Apperp, Bpperp]]

        self.refine_motive_array = [
            [degree, weight, famhodge, A, B],
            [conductor, t, hodge, sign],
            [p, Ap, Bp, Apperp, Bpperp]]

    def search_types(self, info):
        st = self._st(info)
        if st is None:
            # We need a custom button for the family search so that it can be clicked by javascript
            class FamilySearchButton(SearchButton):
                def _input(self, info):
                    btext = "<button type='submit' id='family' name='search_type' value='Family' style='width: {width}px;'>{desc}</button>"
                    return btext.format(width=self.width, desc=self.description)
            return [("Motive", "List of motives"),
                    FamilySearchButton("Family", "List of families"),
                    ("Random", "Random motive"),
                    ("RandomFamily", "Random family")]
        elif st == "Family":
            return [("Family", "Search again"),
                    ("RandomFamily", "Random family")]
        else:
            return [("Motive", "Search again"),
                    ("Random", "Random motive")]

    def main_array(self, info):
        # Unused for info=None, since the browse page uses family_html() and motive_html() instead
        if self._st(info) == "Family":
            return self.refine_family_array
        else:
            return self.refine_motive_array

    def family_html(self):
        return self._print_table(self.family_array, None, "horizontal")

    def motive_html(self):
        table = self._print_table(self.motive_array, None, "horizontal")
        buttons = self.buttons()
        return "\n".join([table, buttons])
