# -*- coding: utf-8 -*-

from flask import url_for

from lmfdb.utils import comma, make_logger

from lmfdb.base import app, getDBConnection

from sage.misc.cachefunc import cached_function
from sage.rings.all import Integer
from sage.all import PolynomialRing, QQ, factor, PariError

from lmfdb.genus2_curves.web_g2c import list_to_factored_poly_otherorder
from lmfdb.transitive_group import group_display_knowl
from lmfdb.WebNumberField import WebNumberField, nf_display_knowl, field_pretty

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
        self.decompositioninfo = decomposition_display(self,self.decomposition)
        self.formatted_polynomial = list_to_factored_poly_otherorder(self.polynomial,galois=False,vari = 'x')
        #in some cases the abelian variety can be simple but not have a field or Galois group attached because the Weil polynomial is not irreducible. This gives them then.
        if self.is_simple():
            if self.number_field == "":
                factors = factor(PolynomialRing(QQ, 'x')(self.polynomial))
                factors_list = [[v[0],v[1]] for v in factors]
                if len(factors_list) > 1: #then the isogeny class is not really simple...
                    logger.debug("WARNING! The class thought it was simple but it wasnt")
                else: 
                    try:
                        self.galois_n = factors_list[0][0].degree()
                        nf = WebNumberField.from_polynomial(factors_list[0][0])
                        if nf.label == 'a':
                            nf = None
                    except PariError:
                        nf = None
                    if nf is None:                    
                        self.number_field = ""
                        self.galois_t = ""
                    else:
                        self.number_field = nf.label
                        self.galois_t = nf.galois_t()
            #for those whose galois group was computed before, this sets galois_n to be the right thing
            else:
                self.galois_n = 2*self.g
        
    def p(self):
        q = Integer(self.q)
        p, _ = q.is_prime_power(get_data=True)
        return p
    
    def r(self):
        q = Integer(self.q)
        _, r = q.is_prime_power(get_data=True)
        return r
        
    def field(self):
        p = self.p()
        r = self.r()
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
        if len(self.decomposition)== 1:
            #old simple_maker just outputed the label, with no multiplicity
            if len(self.decomposition[0]) == 1:
                return True
            #new simple_maker outputs the label and multiplicity 1
            elif self.decomposition[0][1] == 1:
                return True
        else:
            return False
    
        ### This is what this will look like once all self.decomposition is fixed:
        #if len(self.decomposition) == 1:
        #    if self.decomposition[0][1] == 1:
        #        return True
        #else:
        #    return False
            
    
    
    def is_primitive(self): 
        pass
    ### Not implemented yet
    #    if self.primitive_models == '':
    #        return True
    #    else:
    #        return False
            
    def is_ordinary(self):
        if self.p_rank == self.g:
            return True
        else:
            return False
        
    def is_supersingular(self):
        for slope in self.slopes:
            if slope != '1/2':
                return False
        return True
        
    def display_slopes(self):
        ans = '['
        for slope in self.slopes:
            if ans != '[':
                ans += ', '
            ans += slope
        ans += ']'
        return ans
        
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

def decomposition_display(current_class, factors):
    if len(factors) == 1 and factors[0][1] == 1:
        return 'simple'
    ans = ''
    for factor in factors:
        if ans != '':
            ans += '$\\times$ '
        if factor[1] == 1:
            ans += factor_display_knowl(factor[0]) + ' '
        else:
            ans += factor_display_knowl(factor[0]) + '<sup> {0} </sup> '.format(factor[1])
    return ans
    
def factor_display_knowl(label):
    return '<a title = "[av.decomposition.data]" knowl="av.decomposition.data" kwargs="label=' + str(label) + '">' + label + '</a>'

def decomposition_data(label):
    C = getDBConnection()
    return decomposition_knowl_guts(label,C)
    
def decomposition_knowl_guts(label,C):
    abvar = C.abvar.fq_isog.find_one({ 'label' : label })
    wnf = WebNumberField(abvar['number_field'])
    inf = '<div>Dimension: ' + str(abvar['g']) + '<br />'
    if not wnf.is_null():
        inf += 'Number field: ' + nf_display_knowl(abvar['number_field'], C, name = abvar['number_field']) + '<br />'
        inf += 'Galois group: ' + group_display_knowl(abvar['galois_n'],abvar['galois_t'],C) + '<br />'
    inf += '$p$-rank: ' + str(abvar['p_rank']) + '</div>'
    inf += '<div align="right">'
    inf += '<a href="/Variety/Abelian/%s">%s home page</a>' % (label, label)
    inf += '</div>'
    return inf
            
@app.context_processor
def ctx_decomposition():
    return {'decomposition_data': decomposition_data}
            
        

    
