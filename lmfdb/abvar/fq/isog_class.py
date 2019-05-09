# -*- coding: utf-8 -*-

from flask import url_for
from collections import Counter

from lmfdb.utils import encode_plot
from lmfdb.logger import make_logger

from lmfdb import db
from lmfdb.app import app

from sage.rings.all import Integer, QQ, RR
from sage.plot.all import line, points, circle, Graphics
from sage.misc import latex


from lmfdb.utils import list_to_factored_poly_otherorder, coeff_to_poly, web_latex
from lmfdb.number_fields.web_number_field import nf_display_knowl, field_pretty
from lmfdb.galois_groups.transitive_group import group_display_knowl
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
        #try:
        data = db.av_fq_isog.lookup(label)
        return cls(data)
        #except (AttributeError, TypeError):
            #raise ValueError("Label not found in database")

    def make_class(self):
        self.decompositioninfo = decomposition_display(zip(self.simple_distinct,self.simple_multiplicities))
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
    def polygon_slopes(self):
        # Remove the multiset indicators
        return [s[:-1] for s in self.slopes]

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

    def nf(self):
        if self.is_simple:
            return self.number_fields[0]
        else:
            return None
    
    def newton_plot(self):
        S = [QQ(s) for s in self.polygon_slopes]
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
        if self.has_principal_polarization == 1:
            ans.append((None, 'Principally polarizable'))
        elif self.has_principal_polarization == -1:
            ans.append((None, 'Not principally polarizable'))
        if self.has_jacobian == 1:
            ans.append((None, 'Contains a Jacobian'))
        elif self.has_jacobian == -1:
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

    def is_ordinary(self):
        return self.p_rank == self.g

    def is_supersingular(self):
        return all(slope == '1/2' for slope in self.polygon_slopes)

    def display_slopes(self):
        return '[' + ', '.join(self.polygon_slopes) + ']'

    def length_A_counts(self):
        return len(self.abvar_counts)

    def length_C_counts(self):
        return len(self.curve_counts)

    def display_number_field(self):
        if self.is_simple:
            if self.nf() == "":
                return "The number field of this isogeny class is not in the database."
            else:
                return nf_display_knowl(self.nf(),field_pretty(self.nf()))
        else:
            return "The class is not simple, so we will display the number fields later"

    def display_galois_group(self):
        if not hasattr(self, 'galois_groups') or not self.galois_groups[0]: #the number field was not found in the database
            return "The Galois group of this isogeny class is not in the database."
        else:
            group = (self.galois_groups[0]).split("T")
            return group_display_knowl(group[0], group[1])

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
    
    def alg_clo_field(self):
        if self.r == 1:
            return '\\overline{\F}_{' + '{0}'.format(self.p) + '}'
        else:
            return '\\overline{\F}_{' + '{0}^{1}'.format(self.p,self.r) + '}'
            
    def ext_field(self,s):
        n = s*self.r
        if n == 1:
            return '\F_{' + '{0}'.format(self.p) + '}'
        else:
            return '\F_{' + '{0}^{1}'.format(self.p,n) + '}'    

    def endo_extensions(self):
        #data = db.av_fq_endalg_factors.lucky({'label':self.label})
        return  list(db.av_fq_endalg_factors.search({'base_label':self.label}))

    def relevant_degs(self):
        return Integer(self.geometric_extension_degree).divisors()[1:-1]
    
    def endo_extension_by_deg(self,degree):
        return [[factor['extension_label'],factor['multiplicity']] for factor in self.endo_extensions() if factor['extension_degree']==degree]
    
    def display_endo_info(self,degree):
        #this is for degree > 1
        factors = self.endo_extension_by_deg(degree)
        print '**********************************'
        print factors
        print '**********************************'
        if factors == []:
            return 'The data at degree ' + str(degree) + ' is missing.'        
        if decomposition_display(factors) == 'simple':
            end_alg = describe_end_algebra(self.p,factors[0][0])
            ans = 'This base change is the simple isogeny class ' 
            ans += av_display_knowl(factors[0][0]) 
            ans += ' and its endomorphism algebra is ' + end_alg[1]
        elif len(factors) == 1:
            end_alg = describe_end_algebra(self.p,factors[0][0])
            ans = 'This base change factors as ' + decomposition_display(factors) + ' and its endomorphism algebra is $M_' + str(factors[0][1]) + '(' + end_alg[0] + ')$, where $' + end_alg[0] + '$ is ' + end_alg[1]
        else:
            ans = 'This base change factors as ' + decomposition_display(factors) + ' therefore its endomorphism algebra is a direct sum of the endomorphism algebras for each isotypic factor. The endomorphism algebra for each factor is:' + non_simple_loop(self.p,factors)
        return ans
           
    #to fix
    def display_base_endo_info(self):
        factors = zip(self.simple_distinct,self.simple_multiplicities)
        if decomposition_display(factors) == 'simple':
            end_alg = describe_end_algebra(self.p,factors[0][0])
            ans = 'This is a simple isogeny class and its endomorphism algebra is ' + end_alg[1]
            #ans += describe_end_algebra(self.p,factors[0][0])
        elif len(factors) == 1:
            end_alg = describe_end_algebra(self.p,factors[0][0])
            ans = 'This isogeny class factors as ' + decomposition_display(factors) + ' and its endomorphism algebra is $M_' + str(factors[0][1]) + '(' + end_alg[0] + ')$, where $' + end_alg[0] + '$ is ' + end_alg[1]
        else:
            ans = 'This isogeny class factors as ' + decomposition_display(factors) + ' therefore its endomorphism algebra is a direct sum of the endomorphism algebras for each isotypic factor. The endomorphism algebra for each factor is:' + non_simple_loop(self.p,factors)
        return ans

    def basechange_display(self):
        if self.is_primitive:
            return 'primitive'
        else:
            models = self.primitive_models
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

def describe_end_algebra(p,extension_label):
    factor_data = db.av_fq_endalg_data.lookup(extension_label)
    center = factor_data['center']
    divalg_dim = factor_data['divalg_dim']
    places = factor_data['places']
    brauer_invariants = factor_data['brauer_invariants']
    ans = ['','']
    if center == '1.1.1.1' and divalg_dim == 4:
        ans[0] = 'B'
        ans[1] = 'the quaternion division algebra over ' +  nf_display_knowl(center,field_pretty(center)) + ' ramified at ${0}$ and $\infty$'.format(p) + '.'
    elif int(center.split('.')[1]) > 0:
        ans[0] = 'B'
        ans[1] = 'the division algebra over ' + nf_display_knowl(center,field_pretty(center)) + ' ramified at both real infinite places.'
    elif divalg_dim == 1:
        ans[0] = 'K'
        ans[1] = nf_display_knowl(center,field_pretty(center)) + '.'
    else:
        ans[0] = 'B'
        ans[1] = 'the division algebra of dimension ${0}$ over '.format(divalg_dim) + nf_display_knowl(center,field_pretty(center)) + ' with the following ramification data at primes above ${0}$, and unramified at all archimedean primes:'.format(p)
        ans[1]  += '</td></tr><tr><td><table class = "ntdata"><tr><td>$v$</td>'
        for prime in places:
            ans[1] += '<td class="center"> {0} </td>'.format(primeideal_display(p,prime))
        ans[1] += '</tr><tr><td>$\operatorname{inv}_v$</td>'
        for inv in brauer_invariants:
            ans[1] += '<td class="center">${0}$</td>'.format(inv)
        ans[1] += '</tr></table>'
    return ans


def primeideal_display(p,prime_ideal):
    ans = '($ {0} $'.format(p)
    if prime_ideal == ['0']:
        ans += ')'
        return ans
    else:
        ans += ',' + web_latex(coeff_to_poly(prime_ideal,'pi')) + ')'
        return ans


def decomposition_display(factors):
    if len(factors) == 1 and factors[0][1] == 1:
        return 'simple'
    factor_str = ''
    for factor in factors:
        if factor_str != '':
            factor_str += ' $\\times$ '
        factor_str += av_display_knowl(factor[0])
        if factor[1] > 1:
            factor_str += '<sup> {0} </sup>'.format(factor[1])
    return factor_str


def non_simple_loop(p,factors):
    ans = '<ul>'
    for factor in factors:
        ans += '<li>'
        ans += av_display_knowl(factor[0]) 
        if factor[1] > 1:
           ans += '<sup> {0} </sup>'.format(factor[1]) 
        ans += ' : '
        end_alg = describe_end_algebra(p,factor[0])
        if factor[1] == 1:
            ans += end_alg[1]
        else:
            ans += '$M_' + str(factor[1]) + '(' + end_alg[0] + ')$, where $' + end_alg[0] + '$ is ' + end_alg[1]
        ans += '</li>'
    ans += '</ul>'
    return ans
