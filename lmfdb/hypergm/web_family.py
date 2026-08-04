import re
from flask import url_for
from collections import defaultdict, Counter

from sage.all import (ZZ, QQ, cached_method, ceil, gcd, lcm,
                      latex, lazy_attribute,
                      matrix, valuation, I)
from sage.rings.complex_mpfr import ComplexField
from sage.geometry.newton_polygon import NewtonPolygon

from lmfdb import db
from lmfdb.utils import (
    encode_plot, list_to_factored_poly_otherorder,
    make_bigint, web_latex, integer_divisors, integer_prime_divisors, raw_typeset)
from lmfdb.groups.abstract.main import abstract_group_display_knowl
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl_C1_as_trivial
# from .plot import circle_image, piecewise_constant_image, piecewise_linear_image
from sage.plot.all import line, text, point, circle, polygon, Graphics
from sage.functions.log import exp

HMF_LABEL_RE = re.compile(r'^A(\d+\.)*\d+_B(\d+\.)*\d+$')


def HMF_valid_label(label):
    return bool(HMF_LABEL_RE.match(label))


GAP_ID_RE = re.compile(r'^\[\d+,\d+\]$')


# Convert cyclotomic indices to rational numbers
def cyc_to_QZ(A):
    return sorted(QQ(k) / Ai for Ai in A
                  for k in range(1, Ai + 1) if gcd(k, Ai) == 1)


# Given A, B, return URL for family
def AB_to_url(A,B):
    from lmfdb.hypergm.main import normalize_family, ab_label, url_for_label
    if len(A) != 0 and len(B) != 0:
        return url_for_label(normalize_family(ab_label(A,B)))
    return ""

class WebHyperGeometricFamily():
    def __init__(self, data):
        for elt in db.hgm_families.col_type:
            if elt not in data:
                data[elt] = None

        self.__dict__.update(data)

        self.alpha = cyc_to_QZ(self.A)
        self.beta = cyc_to_QZ(self.B)
        self.hodge = data['famhodge']
        self.bezout = matrix(self.bezout)
        self.hinf = matrix(self.hinf)
        self.h0 = matrix(self.h0)
        self.h1 = matrix(self.h1)
        # FIXME
        self.rotation_number = self.imprim

    @staticmethod
    def by_label(label):
        if not HMF_valid_label(label):
            raise ValueError("Hypergeometric motive family label %s." % label)

        data = db.hgm_families.lookup(label)
        if data is None:
            raise ValueError("Hypergeometric motive family label %s not found."
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
            if d[v] > 1:
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
            for d in integer_divisors(m)[:-1]:
                if d in ab[wh]:
                    subdict(ab[wh], d)
                else:
                    ab[1 - wh][d] += 1
        gamma[1] = [-1 * z for z in gamma[1]]
        gamma = sorted(gamma[1] + gamma[0])
        return gamma

    @lazy_attribute
    def wild_primes(self):
        return integer_prime_divisors(lcm(lcm(self.A), lcm(self.B)))

    @lazy_attribute
    def wild_primes_string(self):
        ps = self.wild_primes
        return raw_typeset(', '.join(str(p) for p in ps), ', '.join(web_latex(p) for p in ps))

    @lazy_attribute
    def motivic_det_char(self):
        exp = -QQ(self.weight * self.degree) / 2
        tate_twist = r'\Q({})'.format(exp)

        if self.det[0] == 1:
            foo = ""
        elif self.det[0] == -1:
            foo = "-"
        else:
            foo = str(self.det[0])
        foo += self.det[1]
        if foo == "":
            return tate_twist
        quad_char = r'\chi_{%s}' % foo
        return r'{} \otimes {}'.format(quad_char, tate_twist)

    @lazy_attribute
    def bezout_det(self):
        return self.bezout.det()

    @lazy_attribute
    def hinf_latex(self):
        return latex(self.hinf)

    @lazy_attribute
    def h0_latex(self):
        return latex(self.h0)

    @lazy_attribute
    def h1_latex(self):
        return latex(self.h1)

    @lazy_attribute
    def bezout_latex(self):
        return latex(self.bezout)

    @lazy_attribute
    def bezout_module(self):
        l2 = [a for a in self.snf if a > 1]
        if not l2:
            return 'C_1'
        fa = [ZZ(a).factor() for a in l2]
        eds = sorted((pp[0], pp[1])
                     for b in fa
                     for pp in b)
        l2 = ('C_{{{}}}'.format(a[0]**a[1]) for a in eds)
        return (r' \times ').join(l2)

    @lazy_attribute
    def type(self):
        if (self.weight % 2) and not (self.degree % 2):
            return 'Symplectic'
        else:
            return 'Orthogonal'

    @lazy_attribute
    def ppart(self):
        p_data = [[p, getattr(self, f"A{p}"), getattr(self, f"B{p}"), getattr(self, f"C{p}")] for p in [2,3,5,7]]
        # make URLs
        for row in p_data:
            A = row[1]
            B = row[2]
            row.append(AB_to_url(A,B))
        return p_data

    @cached_method
    def circle_image(self):
        alpha = self.alpha
        beta = self.beta
        alpha_counter = dict(Counter(alpha))
        beta_counter = dict(Counter(beta))
        G = Graphics()
        G += circle((0, 0), 1, color='gray', thickness=2, zorder=3)
        G += circle((0, 0), 1.4, color='black', alpha=0, zorder=2)  # Adds invisible framing circle, which protects the aspect ratio from being skewed.
        C = ComplexField()
        for a in alpha_counter.keys():
            P = exp(C(2*3.14159*I*a))
            P1 = exp(C(2*3.14159*(a + 0.007)*I))
            P2 = exp(C(2*3.14159*(a - 0.007)*I))
            P3 = (1+alpha_counter[a]/30)*exp(C(2*3.14159*I*a))
            G += polygon([P1,P2,P3], color="red", thickness=1)
            G += line([P,1.3*P], color="red", zorder=1)
        for b in beta_counter.keys():
            P = exp(C(2*3.14159*I*b))
            P1 = exp(C(2*3.14159*(b + 0.007)*I))
            P2 = exp(C(2*3.14159*(b - 0.007)*I))
            P3 = (1-beta_counter[b]/30)*exp(C(2*3.14159*I*b))
            G += polygon([P1,P2,P3], color="blue", thickness=1)
            G += line([P,0.7*P], color="blue", zorder=1)
        return G

    @cached_method
    def plot(self, typ="circle"):
        G = self.circle_image()

        return encode_plot(
            G.plot(),
            pad=0,
            pad_inches=0,
            bbox_inches='tight',
            transparent=True,
            remove_axes=True)

    @lazy_attribute
    def plot_link(self):
        return '<a href="{0}"><img src="{0}" width="150" height="150"/></a>'.format(self.plot())

    @lazy_attribute
    def zigzag(self):
        # alpha is color red
        # beta is color blue
        alpha = self.alpha
        beta = self.beta
        alpha_dicts = [dict(value=entry,color="red") for entry in alpha]
        beta_dicts = [dict(value=entry,color="blue") for entry in beta]
        zigzag_dicts = sorted(alpha_dicts + beta_dicts, key=lambda d: d["value"])
        y = 0
        y_values = [y] # zigzag graph will start at (0,0)
        colors = [entry["color"] for entry in zigzag_dicts]
        for entry in zigzag_dicts:
            if entry["color"] == "red":
                y += 1
                y_values.append(y)
            elif entry["color"] == "blue":
                y += -1
                y_values.append(y)
        return [y_values, colors, zigzag_dicts]

    @cached_method
    def zigzag_plot(self):
        zz = self.zigzag
        y_values = zz[0]
        colors = zz[1]
        x_labels = zz[2]
        y_max = max(y_values)
        y_min = min(y_values)
        x_values = list(range(len(y_values)))
        x_max = len(y_values)
        pts = [(i, y_values[i]) for i in x_values]
        L = Graphics()
        # grid
        for x in x_values:
            L += line([(x, y_min), (x, y_max)], color="grey", zorder=1, thickness=0.4)
        for y in y_values:
            L += line([(0, y), (x_max-1, y)], color="grey", zorder=1, thickness=0.4)
        # zigzag
        L += line(pts, thickness=1, color="black", zorder=2)
        # points
        x_values.pop()
        for x in x_values:
            L += point((x, y_values[x]), marker='o', size=36, color=colors[x], zorder=3)

        j = 0
        for label in x_labels:
            if label["color"] == "red":
                L += text("$"+latex(QQ(label["value"]))+"$", (j,y_max + 0.4), color=label["color"])
                j += 1
            else:
                L += text("$"+latex(QQ(label["value"]))+"$", (j,y_min - 0.4), color=label["color"])
                j += 1
        L.axes(False)
        L.set_aspect_ratio(1)
        return encode_plot(L, pad=0, pad_inches=0, bbox_inches="tight")

    @lazy_attribute
    def zigzag_plot_link(self):
        return '<a href="{0}"><img src="{0}" width="150" height="150"/></a>'.format(self.zigzag_plot())

    @lazy_attribute
    def properties(self):
        return [('Label', self.label),
                (None, self.plot_link),
                ('A', r'\({}\)'.format(self.A)),
                ('B', r'\({}\)'.format(self.B)),
                ('Degree', r'\({}\)'.format(self.degree)),
                ('Weight', r'\({}\)'.format(self.weight)),
                ('Type', self.type)]

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
                    m1[2] = abstract_group_display_knowl(f"{two[0]}.{two[1]}")
                except TypeError:
                    m1[2] = 'Gap[%d,%d]' % (two[0], two[1])
            else:
                # Fix multiple backslashes
                m1[2] = re.sub(r'\\+', r'\\', m1[2])
                m1[2] = '$%s$' % m1[2]
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

        def splitint(a, p):
            if a == 1:
                return ' '
            j = valuation(a, p)
            if j == 0:
                return str(a)
            a = a / p**j
            if a == 1:
                return latex(ZZ(p**j).factor())
            return str(a) + r'\cdot' + latex(ZZ(p**j).factor())

        # # this will have a new data format in the future
        # converted = [[ell,
        #     dogapthing(m1),
        #     getgroup(m1, ell),
        #     latex(ZZ(m1[0]).factor())] for ell, m1 in self.mono if m1 != 0]
        # return [[m[0], m[1], m[2][0],
        #         splitint(m[1][0]/m[2][1], m[0]), m[3]] for m in converted]

        mono = (m for m in self.mono if m[1] != 0)
        mono = [[m[0], dogapthing(m[1]),
                 getgroup(m[1], m[0]),
                 latex(ZZ(m[1][0]).factor())] for m in mono]

        mono = [[m0, m1, m2[0], splitint(ZZ(m1[0]) / m2[1], m0), m3] for m0, m1, m2, m3 in mono]
        # make URLs
        for row in mono:
            A = row[1][3][0]
            B = row[1][3][1]
            row.append(AB_to_url(A,B))

        return mono

    @lazy_attribute
    def friends(self):
        return [('Motives in the family',
                 url_for('hypergm.index') + f"?A={self.A}&B={self.B}")]

    @lazy_attribute
    def downloads(self):
        return [("Underlying data", url_for(".hgm_data", label=self.label))]

    @lazy_attribute
    def title(self):
        return 'Hypergeometric motive family: {}'.format(self.label)

    @lazy_attribute
    def bread(self):
        return [("Motives", url_for("motive.index")),
                ("Hypergeometric", url_for("motive.index2")),
                (r"$\Q$", url_for(".index")),
                ('family A = {}, B = {}'.format(str(self.A), str(self.B)), '')]

    @lazy_attribute
    def euler_factors(self):
        return {elt['p']: elt['eulers'] for elt in
                db.hgm_euler_survey.search({'label': self.label},
                                           projection=['p', 'eulers'],
                                           sort=[])}

    @lazy_attribute
    def defaultp(self):
        if not self.euler_factors:
            return []
        return sorted(self.euler_factors)[:4]

    @lazy_attribute
    def default_prange(self):
        if not self.defaultp:
            return ""
        return "{}-{}".format(self.defaultp[0], self.defaultp[-1])

    @lazy_attribute
    def maxp(self):
        return -1 if not self.euler_factors else max(self.euler_factors)  # max of keys

    @lazy_attribute
    def hodge_polygon(self):
        expand_hodge = []
        for i, h in enumerate(self.hodge):
            expand_hodge += [i] * h
        return NewtonPolygon(expand_hodge).vertices()

    @lazy_attribute
    def ordinary(self):
        if self.weight > 0:
            middle = ceil(ZZ(len(self.hodge_polygon)) / 2)

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
                if gal_groups[0] == [0, 0]:
                    gal_groups = ""
                else:
                    gal_groups = r"$\times$".join(
                        transitive_group_display_knowl_C1_as_trivial(f"{n}T{t}")
                        for n, t in gal_groups)
            return [gal_groups, factors, self.ordinary(f, p)]
        return process_euler

    @lazy_attribute
    def display_galois_groups(self):
        return not (self.degree <= 2 or self.degree >= 12)

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
