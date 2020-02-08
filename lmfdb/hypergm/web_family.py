from __future__ import absolute_import

import re
from flask import url_for
from collections import defaultdict
from sage.all import ZZ, QQ, LCM
from sage.all import (cached_method, ceil, divisors, gcd,
                      latex, lazy_attribute,
                      matrix, valuation)
from sage.geometry.newton_polygon import NewtonPolygon

from lmfdb import db
from lmfdb.utils import (
    encode_plot, list_to_factored_poly_otherorder,
    make_bigint, web_latex)
from lmfdb.galois_groups.transitive_group import small_group_display_knowl, group_display_knowl_C1_as_trivial
from .plot import circle_image, piecewise_constant_image, piecewise_linear_image

HMF_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+$')

def HMF_valid_label(label):
    return bool(HMF_LABEL_RE.match(label))

GAP_ID_RE = re.compile(r'^\[\d+,\d+\]$')

# Convert cyclotomic indices to rational numbers
def cyc_to_QZ(A):
    alpha = []
    for Ai in A:
        alpha.extend([QQ(k)/Ai for k in range(1,Ai+1) if gcd(k,Ai) == 1])
    alpha.sort()
    return alpha

class WebHyperGeometricFamily(object):
    def __init__(self, data):
        for elt in db.hgm_families.col_type:
            if elt not in data:
                data[elt] = None

        self.__dict__.update(data)

        self.alpha = cyc_to_QZ(self.A)
        self.beta = cyc_to_QZ(self.B)
        self.hodge = data['famhodge']
        self.bezout = matrix(self.bezout)
        #FIXME
        self.rotation_number = self.imprim

    @staticmethod
    def by_label(label):
        if not HMF_valid_label(label):
            raise ValueError("Hypergeometric Motive Family label %s." % label)

        data = db.hgm_families.lookup(label)
        if data is None:
            raise ValueError("Hypergeometric Motive Family label %s not found."
                             % label)
        return WebHyperGeometricFamily(data)

    @lazy_attribute
    def alpha_latex(self):
        return web_latex(self.alpha)

    @lazy_attribute
    def beta_latex(self):
        return web_latex(self.beta)

    @lazy_attribute
    def gammas(self):
        def subdict(d, v):
            if d[v]>1:
                d[v] -= 1
            else:
                del d[v]

        a = defaultdict(int)
        b = defaultdict(int)
        for x in self.A:
            a[x] += 1
        for x in self.B:
            b[x] += 1
        gamma = [[], []]
        ab = [a, b]
        while a or b:
            m = max(list(a) + list(b))
            wh = 0 if m in a else 1
            gamma[wh].append(m)
            subdict(ab[wh], m)
            for d in divisors(m)[:-1]:
                if d in ab[wh]:
                    subdict(ab[wh], d)
                else:
                    ab[1-wh][d] += 1
        gamma[1] = [-1*z for z in gamma[1]]
        gamma = gamma[1] + gamma[0]
        gamma.sort()
        return gamma

    @lazy_attribute
    def wild_primes(self):
        return LCM(LCM(self.A), LCM(self.B)).prime_divisors()



    @lazy_attribute
    def motivic_det_char(self):
        exp = -QQ(self.weight * self.degree)/2
        first = r'\Q({})'.format(exp)

        if self.det[0] == 1:
            foo = ""
        elif self.det[0] == -1:
            foo = "-"
        else:
            foo = str(self.det[0])
        foo += self.det[1]
        if foo == "":
            foo = "1"
        second = r'\Q(\sqrt{{ {} }})'.format(foo)

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
        if not l2:
            return 'C_1'
        fa = [ZZ(a).factor() for a in l2]
        eds = []
        for b in fa:
            for pp in b:
                eds.append([pp[0], pp[1]])
        eds.sort()
        l2 = ['C_{{{}}}'.format(a[0]**a[1]) for a in eds]
        return (r' \times ').join(l2)

    @lazy_attribute
    def type(self):
        if (self.weight % 2) and (self.degree % 2) == 0:
            return 'Symplectic'
        else:
            return 'Orthogonal'

    @lazy_attribute
    def ppart(self):
        return [[2, self.A2, self.B2, self.C2],
                [3, self.A3, self.B3, self.C3],
                [5, self.A5, self.B5, self.C5],
                [7, self.A7, self.B7, self.C7]]

    @cached_method
    def plot(self, typ="circle"):
        assert typ in ['circle', 'linear', 'constant']
        if typ == 'circle':
            G = circle_image(self.A, self.B)
        elif typ == 'linear':
            G = piecewise_linear_image(self.A, self.B)
        else:
            G = piecewise_constant_image(self.A, self.B)

        return encode_plot(
                    G.plot(),
                    pad=0,
                    pad_inches=0,
                    bbox_inches='tight',
                    remove_axes=True)

    @lazy_attribute
    def plot_link(self):
        return '<a href="{0}"><img src="{0}" width="150" height="150"/></a>'.format(self.plot())

    @lazy_attribute
    def properties(self):
        return [
                ('Label', self.label),
                (None, self.plot_link),
                ('A', r'\({}\)'.format(self.A)),
                ('B', r'\({}\)'.format(self.B)),
                ('Degree', r'\({}\)'.format(self.degree)),
                ('Weight',  r'\({}\)'.format(self.weight)),
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
        def splitint(a, p):
            if a == 1:
                return ' '
            j = valuation(a, p)
            if j == 0:
                return str(a)
            a = a/p**j
            if a == 1:
                return latex(ZZ(p**j).factor())
            return str(a)+r'\cdot'+latex(ZZ(p**j).factor())

        # # this will have a new data format in the future
        # converted = [[ell,
        #     dogapthing(m1),
        #     getgroup(m1, ell),
        #     latex(ZZ(m1[0]).factor())] for ell, m1 in self.mono if m1 != 0]
        # return [[m[0], m[1], m[2][0],
        #         splitint(m[1][0]/m[2][1], m[0]), m[3]] for m in converted]

        mono = [m for m in self.mono if m[1] != 0]
        mono = [[m[0], dogapthing(m[1]),
          getgroup(m[1],m[0]),
          latex(ZZ(m[1][0]).factor())] for m in mono]
        mono = [[m[0], m[1], m[2][0], splitint(ZZ(m[1][0])/m[2][1], m[0]), m[3]] for m in mono]
        return mono

    @lazy_attribute
    def friends(self):
        return [('Motives in the family',
                 url_for('hypergm.index') +
                 "?A={}&B={}".format(str(self.A), str(self.B)))]



    @lazy_attribute
    def title(self):
        return 'Hypergeometric Motive Family: {}'.format(self.label)

    @lazy_attribute
    def bread(self):
        return [("Motives", url_for("motive.index")),
                ("Hypergeometric", url_for("motive.index2")),
                (r"$\Q$", url_for(".index")),
                ('family A = {}, B = {}'.format(str(self.A), str(self.B)), '')]

    @lazy_attribute
    def euler_factors(self):
        return dict([(elt['p'], elt['eulers']) for elt in
                     db.hgm_euler_survey.search({'label': self.label},
                                                 projection=['p', 'eulers'],
                                                 sort=[])])

    @lazy_attribute
    def defaultp(self):
        if not self.euler_factors:
            return []
        else:
            return sorted(self.euler_factors)[:4]

    @lazy_attribute
    def default_prange(self):
        if not self.defaultp:
            return ""
        else:
            return "{}-{}".format(self.defaultp[0], self.defaultp[-1])


    @lazy_attribute
    def maxp(self):
        return -1 if not self.euler_factors else max(self.euler_factors) # max of keys

    @lazy_attribute
    def hodge_polygon(self):
        expand_hodge = []
        for i, h in enumerate(self.hodge):
            expand_hodge += [i]*h
        return NewtonPolygon(expand_hodge).vertices()

    @lazy_attribute
    def ordinary(self):
        if self.weight > 0:
            middle = ceil(ZZ(len(self.hodge_polygon))/2)
            def ordinary(f, p):
                return all(valuation(f[i], p) == v
                           for i, v in self.hodge_polygon[:middle])
                # return [valuation(elt, p) for elt in f] == self.hodge_polygon
        else:
            def ordinary(f, p):
                return None

        return ordinary

    @lazy_attribute
    def process_euler(self):
        galois = self.display_galois_groups
        def process_euler(f, p):
            fG = list_to_factored_poly_otherorder(f, galois=galois, p=p)
            if galois:
                factors, gal_groups = fG
            else:
                factors, gal_groups = fG, ""

            factors = make_bigint(r'\( %s \)' % factors)

            if gal_groups:
                if gal_groups[0] == [0,0]:
                    gal_groups = ""
                else:
                    gal_groups = r"$\times$".join(
                            [group_display_knowl_C1_as_trivial(n, t)
                                for n, t in gal_groups])
            return [gal_groups, factors, self.ordinary(f, p)]
        return process_euler
    @lazy_attribute
    def display_galois_groups(self):
        return False if self.degree <= 2 or self.degree >= 12 else True

    def table_euler_factors_p(self, p):
        if p not in self.euler_factors:
            return []

        ef = self.euler_factors[p]
        assert len(ef) == p - 2
        return [[t] + self.process_euler(f, p)
                for t, f in enumerate(ef, 2)]

    def table_euler_factors_t(self, t, plist=None):
        if plist is None:
            plist = sorted(self.euler_factors)
        t = QQ(t)
        tmodp = [(p, t.mod_ui(p)) for p in plist if t.denominator() % p != 0]
        # filter
        return [[p] + self.process_euler(self.euler_factors[p][tp - 2], p)
                for p, tp in tmodp if tp > 1]

    def table_euler_factors_generic(self, plist=None, tlist=None):
        if tlist is None:
            if plist is None:
                plist = self.defaultp
            return [('p', p, 't', self.table_euler_factors_p(p)) for p in plist]
        else:
            return [('t', t, 'p', self.table_euler_factors_t(t, plist)) for t in tlist]













