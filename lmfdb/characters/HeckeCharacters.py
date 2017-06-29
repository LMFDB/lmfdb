# -*- coding: utf-8 -*-
# HeckeCharacters.py

from sage.all import gp, xmrange, Integer, pari, gcd, LCM, prod
from sage.misc.cachefunc import cached_method
from sage.groups.abelian_gps.abelian_group import AbelianGroup_class
from sage.groups.abelian_gps.abelian_group_element import AbelianGroupElement
from sage.groups.abelian_gps.dual_abelian_group import DualAbelianGroup_class, DualAbelianGroupElement

class RayClassGroup(AbelianGroup_class):
    def __init__(self, number_field, mod_ideal = 1, mod_archimedean = None):
        if mod_archimedean == None:
            mod_archimedean = [0] * len(number_field.real_places())
        mod_ideal = number_field.ideal( mod_ideal )

        bnf = gp(number_field.pari_bnf())
        # Use PARI to compute ray class group
        bnr = bnf.bnrinit([mod_ideal, mod_archimedean],1)
        invariants = bnr[5][2]         # bnr.clgp.cyc
        invariants = tuple([ Integer(x) for x in invariants ])
        names = tuple([ "I%i"%i for i in range(len(invariants)) ])
        generators = bnr[5][3]         # bnr.gen = bnr.clgp[3]
        generators = [ number_field.ideal(pari(x)) for x in generators ]

        AbelianGroup_class.__init__(self, invariants, names)
        self.__number_field = number_field
        self.__bnr = bnr
        self.__pari_mod = bnr[2][1]
        self.__mod_ideal = mod_ideal
        self.__mod_arch = mod_archimedean
        self.__generators = generators

    #def __call__(self, *args, **kwargs):
    #    return group.Group.__call__(self, *args, **kwargs)

    def log(self,I):
        # Use PARI to compute class of given ideal
        g = self.__bnr.bnrisprincipal(I, flag = 0)
        g = [ Integer(x) for x in g ]
        return g

    def number_field(self):
        return self.__number_field

    def bnr(self):
        return self.__bnr

    def modulus(self):
        return self.__mod_ideal

    def _element_constructor_(self, *args, **kwargs):
        try:
            return AbelianGroupElement(args[0], self)
        except:
            I = self.__number_field.ideal(*args, **kwargs)
            return AbelianGroupElement(self, self.log(I))

    @cached_method
    def dual_group(self, base_ring=None):
        return HeckeCharGroup(self, base_ring)

    def __str__(self):
      return "Ray class group of modulus %s over %s" \
           %(self.modulus(),self.__number_field)

    def __repr__(self):
      return self.__str__()

    def gen_ideals(self):
        return self.__generators

    def exp(self,x):
        gens = self.gen_ideals()
        return prod( g**e for g,e in zip(gens,x) )

    def lift(self, x):
        return self.exp(x.exponents())

    def iter_exponents(self):
        for e in xmrange(self.invariants(), tuple):
            yield e

    def iter_ideals(self):
        for e in self.iter_exponents():
            yield self.exp(e)

class HeckeCharGroup(DualAbelianGroup_class):
    def __init__(self, ray_class_group, base_ring):
        names = tuple([ "chi%i"%i for i in range(ray_class_group.ngens()) ])
        if base_ring is None:
            from sage.rings.number_field.number_field import CyclotomicField
            base_ring = CyclotomicField(LCM(ray_class_group.gens_orders()))
        DualAbelianGroup_class.__init__(self, ray_class_group, names, base_ring)
        """ ray_class_group accessible as self.group() """

    def __call__(self, x):
        if isinstance(x, HeckeChar) and x.parent() is self:
            return x
        return HeckeChar(self, x)

    def __repr__(self):
        return "Group of Hecke characters on %s"%self.group()

    #def list(self):
    #    return [ HeckeChar(self, c.list()) for c in DualAbelianGroup_class.list(self) ]

    def list_primitive(self):
        return [chi for chi in self.list() if chi.is_primitive() ]

class HeckeChar(DualAbelianGroupElement):

    def __init__(self, hecke_char_group, x):
        ray_class_group = hecke_char_group.group()
        if not isinstance(x, (list,tuple)) or len(x) != ray_class_group.ngens():
            x = ray_class_group(x).list()
        DualAbelianGroupElement.__init__(self, hecke_char_group, x)
        self.__repr = None
        self.__element_vector = x

    #def __repr__(self):
    #    #return "Hecke character of index %s over %s" \
    #    #    %(self.list(),self.parent().group())
    #    return str(self.list())

    def number_field(self):
        return self.parent().group().number_field()

    def modulus(self):
        return self.parent().group().modulus()

    @cached_method
    def conductor(self):
        bnr = self.parent().group().bnr()
        pari_cond = pari(bnr.bnrconductorofchar(self.list()))
        finite, arch = pari_cond
        return self.number_field().ideal(finite)

    def is_primitive(self):
        return self.conductor() == self.modulus()

    def logvalue(self, x):
        try:
            E = self.parent().group()(x)
        except:
            return None
        E = E.exponents()
        F = self.exponents()
        D = self.parent().gens_orders()
        r = sum( e*f/d for e,f,d in zip( E, F, D) )
        if isinstance(r, (int,Integer)): return 0
        n,d = r.numerator(), r.denominator()
        return n%d/d

    def logvalues_on_gens(self):
        F = self.exponents()
        D = self.parent().gens_orders()
        return tuple( f/d for f,d in zip( F, D) )
        
    def __call__(self, x):
        try:
            logx = self.parent().group()(x)
        except:
            return 0
        return DualAbelianGroupElement.__call__(self,logx)

    def next_character(self, only_primitive=False):
        D = self.parent().gens_orders()
        F = list(self.exponents())
        i = len(D)-1
        while True:
            F[i] += 1
            if F[i] == D[i]:
                F[i] = 0
                i -= 1
                if i < 0: return None
            else:
                c = HeckeChar(self.parent(), F)
                if not only_primitive or c.is_primitive():
                    return c
               
    def prev_character(self, only_primitive=False):
        D = self.parent().gens_orders()
        F = list(self.exponents())
        i = len(D)-1
        while True:
            F[i] -= 1
            if F[i] < 0:
                F[i] = D[i] - 1
                i -= 1
                if i < 0: return None
            else:
                c = HeckeChar(self.parent(), F)
                if not only_primitive or c.is_primitive():
                    return c

    def galois_orbit(self):
        order = self.multiplicative_order()
        return [ self.__pow__(k) for k in xrange(order) if gcd(k,order) == 1 ]

"""
k.<a> = NumberField(x^4+7*x^2+13)
G = RayClassGroup(k,7)
H = G.dual_group()
H(3)
H([3,1])
"""
