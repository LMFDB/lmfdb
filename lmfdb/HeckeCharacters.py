# -*- coding: utf-8 -*-
# HeckeCharacters.py

from sage.all import *

class RayClassGroup(AbelianGroup_class):
    def __init__(self, number_field, mod_ideal = 1, mod_archimedean = None):
        if mod_archimedean == None:
            mod_archimedean = [0] * len(number_field.real_places())

        bnf = gp(number_field.pari_bnf())
        # Use PARI to compute ray class group
        bnr = bnf.bnrinit([mod_ideal, mod_archimedean],1)
        invariants = bnr[5][2]         # bnr.clgp.cyc
        invariants = [ ZZ(x) for x in invariants ] 

        AbelianGroup_class.__init__(self, len(invariants), invariants)
        self.__number_field = number_field
        self.__bnr = bnr
        self.__pari_mod = bnr[2][1]

    def __call__(self, *args, **kwargs):
        return group.Group.__call__(self, *args, **kwargs)

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
      return self.__pari_mod

    def _element_constructor_(self, *args, **kwargs):
        if isinstance(args[0], AbelianGroupElement):
            return AbelianGroupElement(self, args[0])
        else:
            I = self.__number_field.ideal(*args, **kwargs)
            return AbelianGroupElement(self, self.log(I))

    def dual_group(self):
        return HeckeCharGroup(self)

    def __str__(self):
      return "Ray class group of modulus %s over %s" \
           %(self.modulus(),self.__number_field)
        
    def __repr__(self):
      return self.__str__()

class HeckeCharGroup(DualAbelianGroup_class):
    def __init__(self, ray_class_group):
        DualAbelianGroup_class.__init__(self, ray_class_group)
        """ ray_class_group accessible as self.__group """

    def __call__(self, x):
        if isinstance(x, HeckeChar) and x.parent() is self:
            return x
        return HeckeChar(self, x)

    def __repr__(self):
        return "Group of Hecke characters on %s"%self.group()

    def list(self):
        return [ HeckeChar(self,c.list()) for c in DualAbelianGroup_class.list(self) ]

    def list_primitive(self):
        return [chi for chi in self.list() if chi.is_primitive() ]

class HeckeChar(DualAbelianGroupElement):
    def __init__(self, hecke_char_group, X):
        ray_class_group = hecke_char_group.group()
        if not isinstance(X, list) or len(X) != ray_class_group.ngens():
            X = ray_class_group(X).list()
        DualAbelianGroupElement.__init__(self, hecke_char_group, X)
        self.__repr = None
        self.__element_vector = X

    def __repr__(self):
        #return "Hecke character of index %s over %s" \
        #    %(self.list(),self.parent().group())
        return str(self.list())

    def modulus(self):
        return self.parent().group().modulus()

    def conductor(self):
        bnr = self.parent().group().bnr()
        return bnr.bnrconductorofchar(self.list())

    def is_primitive(self):
        return self.conductor() == self.modulus()

    def __call__(self, x):
        logx = self.parent().group()(x)
        return DualAbelianGroupElement.__call__(self,logx)
