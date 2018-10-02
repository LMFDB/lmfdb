# -*- coding: utf-8 -*-

from flask import url_for
from collections import Counter

from lmfdb.utils import make_logger, encode_plot

from lmfdb.db_backend import db
from lmfdb.base import app

from sage.rings.all import Integer, QQ, RR
from sage.plot.all import line, points, circle, Graphics

from lmfdb.utils import list_to_factored_poly_otherorder
from lmfdb.WebNumberField import nf_display_knowl, field_pretty
from lmfdb.transitive_group import group_display_knowl
from lmfdb.abvar.fq.web_abvar import av_display_knowl, av_data#, av_knowl_guts

logger = make_logger("abvarfq")

#########################
#   Label manipulation
#########################

def validate_label(label):
    parts = label.split('.')
    if len(parts) != 3:
        raise ValueError("it must be of the form g.q.iso, with g a dimension and q a prime power")
    g, q, iso = parts
    try:
        g = int(g)
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is an integer")
    try:
        q = Integer(q)
        if not q.is_prime_power(): raise ValueError
    except ValueError:
        raise ValueError("it must be of the form g.q.iso, where g is a prime power")
    coeffs = iso.split("_")
    if len(coeffs) != g:
        raise ValueError("the final part must be of the form c1_c2_..._cg, with g=%s components"%(g))
    if not all(c.isalpha() and c==c.lower() for c in coeffs):
        raise ValueError("the final part must be of the form c1_c2_..._cg, with each ci consisting of lower case letters")

class AbvarFq_isoclass(object):
    """
    Class for an isogeny class of abelian varieties over a finite field
    """
    def __init__(self,dbdata):
        self.__dict__.update(dbdata)
        self.make_class()

    @classmethod
    def by_label(cls,label):
        """
        Searches for a specific isogeny class in the database by label.
        """
        try:
            data = db.av_fqisog.lookup(label)
            return cls(data)
        except (AttributeError, TypeError):
            raise ValueError("Label not found in database")

    def make_class(self):
        self.decompositioninfo = self.decomposition_display()
        self.basechangeinfo = self.basechange_display()
        self.formatted_polynomial = list_to_factored_poly_otherorder(self.polynomial,galois=False,vari = 'x')

    @property
    def p(self):
        q = Integer(self.q)
        p, _ = q.is_prime_power(get_data=True)
        return p

    @property
    def r(self):
        q = Integer(self.q)
        _, r = q.is_prime_power(get_data=True)
        return r

    @property
    def slopes(self):
        # Remove the multiset indicators
        return [s[:-1] for s in self.slps]

    @property
    def C_counts(self):
        return [str(ct) for ct in self.C_cnts]

    @property
    def A_counts(self):
        return [str(ct) for ct in self.A_cnts]

    @property
    def polynomial(self):
        return self.poly

    def field(self, q=None):
        if q is None:
            p = self.p
            r = self.r
        else:
            p, r = Integer(q).is_prime_power(get_data=True)
        if r == 1:
            return '\F_{' + '{0}'.format(p) + '}'
        else:
            return '\F_{' + '{0}^{1}'.format(p,r) + '}'

    def newton_plot(self):
        S = [QQ(s) for s in self.slopes]
        C = Counter(S)
        pts = [(0,0)]
        x = y = 0
        for s in sorted(C):
            c = C[s]
            x += c
            y += c*s
            pts.append((x,y))
        L = Graphics()
        L += line([(0,0),(0,y+0.2)],color="grey")
        for i in range(1,y+1):
            L += line([(0,i),(0.06,i)],color="grey")
        for i in range(1,C[0]):
            L += line([(i,0),(i,0.06)],color="grey")
        for i in range(len(pts)-1):
            P = pts[i]
            Q = pts[i+1]
            for x in range(P[0],Q[0]+1):
                L += line([(x,P[1]),(x,P[1] + (x-P[0])*(Q[1]-P[1])/(Q[0]-P[0]))],color="grey")
            for y in range(P[1],Q[1]):
                L += line([(P[0] + (y-P[1])*(Q[0]-P[0])/(Q[1]-P[1]),y),(Q[0],y)],color="grey")
        L += line(pts, thickness = 2)
        L.axes(False)
        L.set_aspect_ratio(1)
        return encode_plot(L, pad=0, pad_inches=0, bbox_inches='tight')

    def circle_plot(self):
        pts = []
        pi = RR.pi()
        for angle in self.angles:
            angle = RR(angle)*pi
            c = angle.cos()
            s = angle.sin()
            if abs(s) < 0.00000001:
                pts.append((c,s))
            else:
                pts.extend([(c,s),(c,-s)])
        P = points(pts,size=100) + circle((0,0),1,color='black')
        P.axes(False)
        P.set_aspect_ratio(1)
        return encode_plot(P)

    def _make_jacpol_property(self):
        ans = []
        if self.is_pp == 1:
            ans.append((None, 'Principally polarizable'))
        elif self.is_pp == -1:
            ans.append((None, 'Not principally polarizable'))
        if self.is_jac == 1:
            ans.append((None, 'Contains a Jacobian'))
        elif self.is_jac == -1:
            ans.append((None, 'Does not contain a Jacobian'))
        return ans

    def properties(self):
        return [('Label', self.label),
                ('Base Field', '$%s$'%(self.field(self.q))),
                ('Dimension', '$%s$'%(self.g)),
                (None, '<img src="%s" width="200" height="150"/>' % self.circle_plot()),
                #('Weil polynomial', '$%s$'%(self.formatted_polynomial)),
                ('$p$-rank', '$%s$'%(self.p_rank))] + self._make_jacpol_property()

    # at some point we were going to display the weil_numbers instead of the frobenius angles
    # this is not covered by the tests
    #def weil_numbers(self):
    #    q = self.q
    #    ans = ""
    #    for angle in self.angles:
    #        if ans != "":
    #            ans += ", "
    #        ans += '\sqrt{' +str(q) + '}' + '\exp(\pm i \pi {0}\ldots)'.format(angle)
            #ans += "\sqrt{" +str(q) + "}" + "\exp(-i \pi {0}\ldots)".format(angle)
    #    return ans

    def frob_angles(self):
        ans = ''
        eps = 0.00000001
        for angle in self.angles:
            if ans != '':
                ans += ', '
            if abs(angle) > eps and abs(angle - 1) > eps:
                angle = r'$\pm' + str(angle) + '$'
            else:
                angle = '$' + str(angle) + '$'
            ans += angle
        return ans

    def is_simple(self):
        return self.is_simp

    def is_primitive(self):
        return self.is_prim

    def is_ordinary(self):
        return self.p_rank == self.g

    def is_supersingular(self):
        return all(slope == '1/2' for slope in self.slopes)

    def display_slopes(self):
        return '[' + ', '.join(self.slopes) + ']'

    def length_A_counts(self):
        return len(self.A_counts)

    def length_C_counts(self):
        return len(self.C_counts)

    def display_number_field(self):
        if self.nf == "":
            return "The number field of this isogeny class is not in the database."
        else:
            return nf_display_knowl(self.nf,field_pretty(self.nf))

    def display_galois_group(self):
        if not hasattr(self, 'galois_t') or not self.galois_t: #the number field was not found in the database
            return "The Galois group of this isogeny class is not in the database."
        else:
            return group_display_knowl(self.galois_n, self.galois_t)

    def decomposition_display_search(self,factors):
        if len(factors) == 1 and factors[0][1] == 1:
            return 'simple'
        ans = ''
        for factor in factors:
            url = url_for('abvarfq.by_label',label=factor[0])
            if ans != '':
                ans += '$\\times$ '
            if factor[1] == 1:
                ans += '<a href="{1}">{0}</a>'.format(factor[0],url)
                ans += ' '
            else:
                ans += '<a href="{1}">{0}</a>'.format(factor[0],url) + '<sup> {0} </sup> '.format(factor[1])
        return ans

    def decomposition_display(self):
        factors = self.decomp
        if len(factors) == 1 and factors[0][1] == 1:
            return 'simple'
        ans = ''
        for factor in factors:
            if ans != '':
                ans += '$\\times$ '
            if factor[1] == 1:
                ans += av_display_knowl(factor[0]) + ' '
            else:
                ans += av_display_knowl(factor[0]) + '<sup> {0} </sup> '.format(factor[1])
        return ans

    def basechange_display(self):
        models = self.prim_models
        if len(models) == 0:
            return 'primitive'
        ans = '<table class = "ntdata">\n'
        ans += '<tr><td>Subfield</td><td>Primitive Model</td></tr>\n'
        for model in models:
            ans += '  <tr><td class="center">$%s$</td><td>'%(self.field(model.split('.')[1]))
            ans += av_display_knowl(model) + ' '
            ans += '</td></tr>\n'
        ans += '</table>\n'
        return ans


@app.context_processor
def ctx_decomposition():
    return {'av_data': av_data}
