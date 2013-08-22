# -*- coding: utf-8 -*-
# HeckeCharacters.py

from sage.all import *
from sage.groups.abelian_gps.abelian_group import AbelianGroup_class
from sage.groups.abelian_gps.abelian_group_element import AbelianGroupElement
from sage.groups.abelian_gps.dual_abelian_group import DualAbelianGroup_class, DualAbelianGroupElement
from sage.groups.abelian_gps.dual_abelian_group import DualAbelianGroup_class, DualAbelianGroupElement

class RayClassGroup(AbelianGroup_class):
    def __init__(self, number_field, mod_ideal = 1, mod_archimedean = None):
        if mod_archimedean == None:
            mod_archimedean = [0] * len(number_field.real_places())

        bnf = gp(number_field.pari_bnf())
        # Use PARI to compute ray class group
        bnr = bnf.bnrinit([mod_ideal, mod_archimedean],1)
        invariants = bnr[5][2]         # bnr.clgp.cyc
        invariants = tuple([ ZZ(x) for x in invariants ])
        names = tuple([ "I%i"%i for i in range(len(invariants)) ])

        AbelianGroup_class.__init__(self, invariants, names)
        self.__number_field = number_field
        self.__bnr = bnr
        self.__pari_mod = bnr[2][1]
        self.__mod_ideal = mod_ideal
        self.__mod_arch = mod_archimedean

    #def __call__(self, *args, **kwargs):
    #    return group.Group.__call__(self, *args, **kwargs)

    def log(self,I):
        # Use PARI to compute class of given ideal
        g = self.__bnr.bnrisprincipal(I)[1]
        g = [ ZZ(x) for x in g ]
        return g

    def number_field(self):
        return self.__number_field

    def bnr(self):
        return self.__bnr

    def modulus(self):
        return self.__mod_ideal

    def _element_constructor_(self, *args, **kwargs):
        if isinstance(args[0], AbelianGroupElement):
            return AbelianGroupElement(self, args[0])
        else:
            I = self.__number_field.ideal(*args, **kwargs)
            return AbelianGroupElement(self.log(I), self)

    @cached_method
    def dual_group(self, base_ring=None):
        return HeckeCharGroup(self, base_ring)

    def __str__(self):
      return "Ray class group of modulus %s over %s" \
           %(self.modulus(),self.__number_field)
        
    def __repr__(self):
      return self.__str__()

class HeckeCharGroup(DualAbelianGroup_class):
    def __init__(self, ray_class_group, base_ring):
        names = tuple([ "chi%i"%i for i in range(ray_class_group.ngens()) ])
        if base_ring is None:
            from sage.rings.number_field.number_field import CyclotomicField
            from sage.rings.arith import LCM
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
        if not isinstance(x, list) or len(x) != ray_class_group.ngens():
            x = ray_class_group(x).list()
        DualAbelianGroupElement.__init__(self, x, hecke_char_group)
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

    def conductor(self):
        bnr = self.parent().group().bnr()
        pari_cond = pari(bnr.bnrconductorofchar(self.list()))
        finite, arch = pari_cond
        return self.number_field().ideal(finite)

    def is_primitive(self):
        return self.conductor() == self.modulus()

    def __call__(self, x):
        try:
            logx = self.parent().group()(x)
        except:
            return 0
        return DualAbelianGroupElement.__call__(self,logx)

"""
k.<a> = NumberField(x^4+7*x^2+13)
G = RayClassGroup(k,7)
H = G.dual_group()
H(3)
"""
