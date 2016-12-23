# -*- coding: utf-8 -*-

from flask import url_for

from lmfdb.utils import comma, make_logger

from lmfdb.base import app, getDBConnection

from sage.misc.cachefunc import cached_function
from sage.rings.all import Integer
from sage.all import PolynomialRing, QQ, factor, PariError

from lmfdb.genus2_curves.web_g2c import list_to_factored_poly_otherorder
from lmfdb.WebNumberField import nf_display_knowl, field_pretty
from lmfdb.transitive_group import group_display_knowl
from lmfdb.abvar.fq.web_abvar import av_display_knowl, av_data#, av_knowl_guts

logger = make_logger("abvarfq")

#########################
#   Database connection
#########################

@cached_function
def db():
    return getDBConnection().abvar.fq_isog

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
            data = db().find_one({"label": label})
            return cls(data)
        except (AttributeError, TypeError):
            raise ValueError("Label not found in database")

    def make_class(self):
        self.decompositioninfo = self.decomposition_display()
        self.basechangeinfo = self.basechange_display()
        self.formatted_polynomial = list_to_factored_poly_otherorder(self.polynomial,galois=False,vari = 'x')

    def p(self):
        q = Integer(self.q)
        p, _ = q.is_prime_power(get_data=True)
        return p

    def r(self):
        q = Integer(self.q)
        _, r = q.is_prime_power(get_data=True)
        return r

    def field(self, q=None):
        if q is None:
            p = self.p()
            r = self.r()
        else:
            p, r = Integer(q).is_prime_power(get_data=True)
        if r == 1:
            return '\F_{' + '{0}'.format(p) + '}'
        else:
            return '\F_{' + '{0}^{1}'.format(p,r) + '}'

    # at some point we were going to display the weil_numbers instead of the frobenius angles
    # this is not covered by the tests
    #def weil_numbers(self):
    #    q = self.q
    #    ans = ""
    #    for angle in self.angle_numbers:
    #        if ans != "":
    #            ans += ", "
    #        ans += '\sqrt{' +str(q) + '}' + '\exp(\pm i \pi {0}\ldots)'.format(angle)
            #ans += "\sqrt{" +str(q) + "}" + "\exp(-i \pi {0}\ldots)".format(angle)
    #    return ans

    def frob_angles(self):
        ans = ''
        eps = 0.00000001
        for angle in self.angle_numbers:
            if ans != '':
                ans += ', '
            if abs(angle) > eps and abs(angle - 1) > eps:
                angle = r'\pm' + str(angle)
            else:
                angle = str(angle)
            ans += angle
        return ans

    def is_simple(self):
        return len(self.decomposition) == 1 and self.decomposition[0][1] == 1

    def is_primitive(self):
        return len(self.primitive_models) == 0

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
        if self.number_field == "":
            return "The number field of this isogeny class is not in the database."
        else:
            C = getDBConnection()
            return nf_display_knowl(self.number_field,C,field_pretty(self.number_field))

    def display_galois_group(self):
        if self.galois_t == "": #the number field was not found in the database
            return "The Galois group of this isogeny class is not in the database."
        else:
            C = getDBConnection()
            return group_display_knowl(self.galois_n,self.galois_t,C)

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
        factors = self.decomposition
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
        models = self.primitive_models
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
