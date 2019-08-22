
import re
from flask import render_template, request, url_for, redirect, abort
from sage.all import ZZ, QQ, latex, matrix, valuation, PolynomialRing, gcd

from lmfdb import db
from lmfdb.utils import (
    encode_plot, flash_error, list_to_factored_poly_otherorder,
    clean_input, parse_ints, parse_bracketed_posints, parse_rational,
    parse_restricted, search_wrap, web_latex)
from plot import circle_image, piecewise_constant_image, piecewise_linear_image
from lmfdb.galois_groups.transitive_group import small_group_display_knowl
from lmfdb import db


GAP_ID_RE = re.compile(r'^\[\d+,\d+\]$')

def dogapthing(m1):
    mnew = str(m1[2])
    mnew = mnew.replace(' ', '')
    if GAP_ID_RE.match(mnew):
        mnew = mnew[1:-1]
        two = mnew.split(',')
        two = [int(j) for j in two]
        try:
            m1[2] = small_group_display_knowl(two[0],two[1])
        except TypeError:
            m1[2] = 'Gap[%d,%d]' % (two[0],two[1])
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
        return [small_group_display_knowl(1, 1), 1]
    mono = db.hgm_families.lucky({'A': myA, 'B': myB}, projection="mono")
    if mono is None:
        return ['??', 1]
    newthing = mono[pind[ell]]
    newthing = dogapthing(newthing[1])
    return [newthing[2], newthing[0]]

class WebHyperGeometricFamily(object):
    def __init__(self, data):
        for elt in db.hgm_families.col_type:
            if elt not in data:
                data[elt] = None

        self.__dict__.update(data)

        self.alpha = cyc_to_QZ(A)
        self.beta = cyc_to_QZ(B)
        self.hodge = data['famhodge']
        self.bezout = matrix(self.bezout)


    @lazy_attribute
    def alpha_latex(self):
        return web_latex(self.alpha)

    @lazy_attribute
    def beta_latex(self):
        return web_latex(self.beta)

    @lazy_attribute
    def motivic_det_char(self):
        exp = -QQ(self.weight * sel.data)/2
        first = r'\Q({})'.format(exp)

        foo = str(self.det[0]) if self.det[0] != 1 else ""
        foo += selt.det[1]
        if foo == "":
            foo = "1"
        second = r'\Q(\sqrt{ {} })'.format(foo)

        return r'{} \otimes {}'.format(first, second)

    @lazy_attribute
    def bezout_det(self):
        return self.bezout.det()

    @lazy_attribute
    def bezout_latex(self):
        return latex(self.bezout)


    @lazy_attribute
    def bezout_module(self):
        l2 = [a for a in self.snf if a > 1]
        if l2 == []:
            return 'C_1'
        fa = [ZZ(a).factor() for a in l2]
        eds = []
        for b in fa:
            for pp in b:
                eds.append([pp[0], pp[1]])
        eds.sort()
        l2 = ['C_{{}}'.format(a[0]**a[1]) for a in eds]
        return (r' \times ').join(l2)

    @lazy_attribute
    def type(self):
        if (self.weight % 2) == 1 and (self.degree % 2) == 0:
            return 'Symplectic'
        else:
            return 'Orthogonal'

    @lazy_attribute
    def ppart(self):
        return [[2, [self.A2, self.B2, self.C2]],
                [3, [self.A3, self.B3, self.C3]],
                [5, [self.A5, self.B5, self.C5]],
                [7, [self.A7, self.B7, self.C7]]]

    @cached_method
    def plot(self, typ="circle"):
        assert typ in ['circle', 'linear', 'constant']
        if typ == 'circle':
            G = circle_image(self.A, self.B)
        elif typ == 'linear':
            G = piecewise_linear_image(self.A, self.B)
        else:
            G = piecewise_constant_image(self.A, self.B)
        return encode_plot(G.plot())

    @lazy_attribute
    def plot_link(self):
        return '<a href="{0}"><img src="{0}" width="150" height="150"/></a>'.format(self.plot())

    @lazy_attribute
    def properties(self):
        return [
                ('Label', self.label),
                (None, plot_link),
                ('A', '\({}\)'.format(self.A)),
                ('B', '\({}\)'.format(self.B)),
                ('Degree', '\({}\)'.format(self.degree)),
                ('Weight',  '\({}\)'.format(self.weight)),
                ('Type', self.type)
                ]

    @lazy_attribute
    def monodromy(self):

        def dogapthing(m1):
            mnew = str(m1[2])
            mnew = mnew.replace(' ', '')
            if GAP_ID_RE.match(mnew):
                mnew = mnew[1:-1]
                two = mnew.split(',')
                two = [int(j) for j in two]
                try:
                    m1[2] = small_group_display_knowl(two[0],two[1])
                except TypeError:
                    m1[2] = 'Gap[%d,%d]' % (two[0],two[1])
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
                return [small_group_display_knowl(1, 1), 1]
            mono = db.hgm_families.lucky({'A': myA, 'B': myB}, projection="mono")
            if mono is None:
                return ['??', 1]
            newthing = mono[pind[ell]]
            newthing = dogapthing(newthing[1])
            return [newthing[2], newthing[0]]

        # this will have a new data format in the future
        converted = [[ell,
            dogapthing(m1),
            getgroup(m1, ell),
            latex(ZZ(m1[0]).factor())] for ell, m1 in mono if m1 != 0]
        return [[m[0], m[1], m[2][0],
                splitint(m[1][0]/m[2][1], m[0]), m[3]] for m in converted]

    @lazy_attribute
    def friends(self):
        return [('Motives in the family',
                 url_for('hypergm.index') +
                 "?A={}&B={}".format(str(self.A), str(self.B)))]

    @lazy_attribute
    def bread(self):
        AB = 'A = '+str(A)+', B = '+str(B)
        return get_bread(
                [('family A = {}, B = {}'.format(str(self.A), str(self.B)),
                   '')])


    @lazy_attribute
    def euler_factors(self):
        return dict([(elt['p'], elt['eulers']) for elt in
                     db.hgm_euler_survey.search({'label': self.label},
                                          projection=['p', 'eulers'],
                                          sort=[])])











