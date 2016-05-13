# -*- coding: utf-8 -*-


from lmfdb.utils import comma, make_logger

from lmfdb.base import getDBConnection

from sage.misc.cachefunc import cached_function
from sage.rings.all import Integer
from sage.all import PolynomialRing, QQ

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
        except AttributeError:
            raise ValueError("Label not found in database")

    def make_class(self):
        self.g = self.__dict__['g']
        self.p_rank = self.__dict__['p_rank']
        self.slopes = self.__dict__['slopes']
        self.abvar_pointcount = self.__dict__['C_counts']
        self.jacobian = self.__dict__['known_jacobian']
        self.curve_pointcount = self.__dict__['A_counts']
        self.decompositioninfo = self.__dict__['decomposition']
        #pass
        
    def field(self):
        q = self.__dict__['q']
        return '\F_{%s}'%q
    
    def good_polynomial(self):
        coeffs = self.__dict__['polynomial']
        R = PolynomialRing(QQ, 'x')
        return R(coeffs)
        
    def weil_numbers(self): #FIX THIS!!
        return 'a'
        
    def galois_group(self):
        return 'b'
    
    def is_simple(self):
        if len(self.decompositioninfo) == 1:
            if self.decompositioninfo[0][1] == 1:
                return True
        else:
            return False
            
    def is_primitive(self):
        if self.__dict__['primitive_models'] == "":
            return True
        else:
            return False
            
    def is_ordinary(self):
        return "we don't know"
        
    def is_supersingular(self):
        return "we don't know"
    
    
    
    
    #de

    
