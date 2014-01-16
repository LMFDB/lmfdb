r"""

AUTHORS: Alberto Camara, Chris Wuthrich, 2014

Example:

sage: import lmfdb
sage: from lmfdb.tensor_products.galois_reps import *
sage: V = GaloisRepresentation(EllipticCurve("37a1"))
sage: V.motivic_weight
1
sage: V.local_euler_factor(37)

sage: from lmfdb.WebCharacter import *
sage: chi = WebDirichletCharacter(modulus=37,number=4)
sage: V = GaloisRepresentation(chi)
sage: V.langlands
True
sage: V.local_euler_factor(101)

sage: from lmfdb.math_classes import ArtinRepresentation
sage: rho = ArtinRepresentation(2,23,1)
sage: V = GaloisRepresentation(rho)
sage: V.dim
2
sage: V.local_euler_factor(43)

sage: from lmfdb.modular_forms.elliptic_modular_forms import WebNewForm
sage: F = WebNewForm(11,10,fi=1)
sage: V = GaloisRepresentation([F,0])
sage: V.sign
1.0
"""

########################################################################
#       Copyright (C) Alberto Camara, Chris Wuthrich 2014
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################

#import os
#import weakref

import lmfdb.base
from lmfdb.WebCharacter import * #WebDirichletCharacter
from lmfdb.lfunctions.Lfunction_base import Lfunction

from sage.structure.sage_object import SageObject
#from sage.schemes.elliptic_curves.constructor import EllipticCurve
#from sage.rings.rational import Rational
from sage.rings.integer_ring import ZZ
from sage.rings.complex_field import ComplexField
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing

class GaloisRepresentation( Lfunction):

    def __init__(self, thingy):
        """
        Class representing a L-function coming from a Galois representation.
        Typically, dirichlet characters, artin reps, elliptic curves,...
        can give rise to such a class.

        It can be used for tensor two such together (mul below) and a
        L-function class can be extracted from it.
        """

        # this is an important global variable.
        # it is the maximum of the imag parts of values s at
        # which we will compute L(s,.)
        self.max_imaginary_part = "40"

        if isinstance(thingy, sage.schemes.elliptic_curves.ell_rational_field.EllipticCurve_rational_field):
            self.init_elliptic_curve(thingy)

        if isinstance(thingy, lmfdb.WebCharacter.WebDirichletCharacter):
            self.init_dir_char(thingy)

        if isinstance(thingy, lmfdb.math_classes.ArtinRepresentation):
            self.init_artin_rep(thingy)

        if isinstance(thingy, list) and len(thingy) == 2:
            if isinstance(thingy[0],lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms.WebNewForm_class) and isinstance(thingy[1],sage.rings.integer.Integer):
                self.init_elliptic_modular_form(thingy[0],thingy[1])

        if isinstance(thingy, list) and len(thingy) == 2:
            if isinstance(thingy[0], GaloisRepresentation) and isinstance(thingy[1], GaloisRepresentation):
                self.init_tensor_product(thingy[0], thingy[1])

        self.level = self.conductor
        self.degree = self.dim
        self.poles = []
        self.residues = []
        self.algebraic = True
        self.weight = self.motivic_weight + 1

## Various ways to construct such a class

    def init_elliptic_curve(self, E):
        """
        Returns the Galois rep of an elliptic curve over Q
        """

        self.original_object = [E]
        self.object_type = "ellipticcurve"
        self.dim = 2
        self.motivic_weight = 1
        self.conductor = E.conductor()
        self.bad_semistable_primes = [ fa[0] for fa in self.conductor.factor() if fa[1]==1 ]
        self.bad_pot_good = [p for p in self.conductor.prime_factors() if E.j_invariant().valuation(p) > 0 ]
        self.sign = E.root_number()
        self.mu_fe = []
        self.nu_fe = [ZZ(1)/ZZ(2)]
        self.gammaV = [0, 1]
        self.langlands = True
        self.selfdual = True
        self.primitive = True
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        self.dirichlet_coefficients = E.anlist(self.numcoeff)[1:]
        self.coefficient_type = 2
        self.coefficient_period = 0
        self.ld.gp().quit()

        def eu(p):
            """
            Local Euler factor passed as a function
            whose input is a prime and
            whose output is a polynomial
            such that evaluated at p^-s,
            we get the inverse of the local factor
            of the L-function
            """
            R = PolynomialRing(ZZ, "T")
            T = R.gens()[0]
            N = self.conductor
            if N % p != 0 : # good reduction
                return 1 - E.ap(p) * T + p * T**2
            elif N % (p**2) != 0: # multiplicative reduction
                return 1 - E.ap(p) * T
            else:
                return R(1)

        self.local_euler_factor = eu

    def init_dir_char(self, chi):
        """
        Initiate with a Web Dirichlet character.
        """
        self.original_object = [chi]
        chi = chi.chi.primitive_character()
        self.object_type = "dirichletcharacter"
        self.dim = 1
        self.motivic_weight = 0
        self.conductor = ZZ(chi.conductor())
        self.bad_semistable_primes = []
        self.bad_pot_good = self.conductor.prime_factors()
        if chi.is_odd():
            aa = 1
            bb = I
        else:
            aa = 0
            bb = 1
        self.sign = chi.gauss_sum_numerical() / (bb * float(sqrt(chi.modulus())) )
        # this has now type python complex. later we need a gp complex
        self.sign = ComplexField()(self.sign)
        self.mu_fe = [aa]
        self.nu_fe = []
        self.gammaV = [aa]
        self.langlands = True
        self.selfdual = (chi.multiplicative_order() <= 2)
        # rather than all(  abs(chi(m).imag) < 0.0001 for m in range(chi.modulus() ) )
        self.primitive = True
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        self.dirichlet_coefficients = [ chi(m) for m in range(self.numcoeff + 1) ]
        if self.selfdual:
            self.coefficient_type = 2
        else:
            self.coefficient_type = 3
        self.coefficient_period = chi.modulus()

        def eu(p):
            """
            local euler factor
            """
            R = PolynomialRing(ComplexField(), "T")
            T = R.gens()[0]
            if self.conductor % p != 0:
                return  1 - ComplexField()(chi(p)) * T
            else:
                return R(1)

        self.local_euler_factor = eu
        self.ld.gp().quit()


    def init_artin_rep(self, rho):
        """
        Initiate with an Artin representation
 
        """
        self.original_object = [rho]
        self.object_type = "Artin representation"
        self.dim = rho.dimension()
        self.motivic_weight = 0
        self.conductor = ZZ(rho.conductor())
        self.bad_semistable_primes = []
        self.bad_pot_good = self.conductor.prime_factors()
        self.sign = rho.root_number()
        self.mu_fe = rho.mu_fe()
        self.nu_fe = rho.nu_fe()
        self.gammaV = [0 for i in range(rho.number_of_eigenvalues_plus_one_complex_conjugation())]
        for i in range(rho.number_of_eigenvalues_minus_one_complex_conjugation() ):
            self.gammaV.append(1)
        self.langlands = rho.langlands()
        self.selfdual = rho.selfdual()
        self.primitive = rho.primitive()
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        self.dirichlet_coefficients = rho.coefficients_list()
        self.coefficient_type = 0
        self.coefficient_period = 0

        def eu(p):
            """
            local euler factor
            """
            f = rho.local_factor(p)
            co = [ZZ(round(x)) for x in f.coeffs()]
            R = PolynomialRing(ZZ, "T")
            T = R.gens()[0]
            return sum( co[n] * T**n for n in range(len(co)))

        self.local_euler_factor = eu
        self.ld.gp().quit()

    def init_elliptic_modular_form(self, F, number):
        """
        Initiate with an Elliptic Modular Form.
        """
        self.number = number
        #self.original_object = [formlist]
        self.object_type = "Elliptic Modular newform"
        self.dim = 2
        self.weight = ZZ(F.weight())
        self.motivic_weight = ZZ(F.weight()) - 1
        self.conductor = F.level()
        self.langlands = True
        self.mu_fe = []
        self.nu_fe = [ZZ(F.weight()-1)/ZZ(2)]
        self.primitive = True
        self.selfdual = True
        self.coefficient_type = 2
        AL = F.atkin_lehner_eigenvalues()
        self.sign = AL[self.conductor] * (-1) ** (self.weight / 2.)
        self.gammaV = [0,1]
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        # Determining the Dirichlet coefficients. This code stolen from
        # lmfdb.lfunctions.Lfunction.Lfunction_EMF
        self.automorphyexp = (self.weight - 1) / 2.
        embeddings = F.q_expansion_embeddings(self.numcoeff + 1)
        self.algebraic_coefficients = []
        for n in range(1, self.numcoeff + 1):
            self.algebraic_coefficients.append(embeddings[n][self.number])
        self.dirichlet_coefficients = []
        for n in range(1, len(self.algebraic_coefficients) + 1):
            self.dirichlet_coefficients.append(self.algebraic_coefficients[n-1] / float(n ** self.automorphyexp))
        def eu(p):
            """
            Local euler factor
            """
            R = PolynomialRing(ZZ, "T")
            T = R.gens()[0]
            N = self.conductor
            embeddings = F.q_expansion_embeddings(p + 1)
            if N % p != 0 : # good reduction
                return 1 - embeddings[p-1][self.number] * T + T**2
            elif N % (p**2) != 0: # semistable reduction
                return 1 - embeddings[p-1][self.number] * T
            else:
                return R(1)
        self.local_euler_factor = eu
        self.ld.gp().quit()


    def init_tensor_product(self, V, W):
        """
        We are given two Galois representations and we
        will return their tensor product.
        """
        self.original_object = V.original_object + W.original_object
        self.object_type = "tensorproduct"
        self.dim = V.dim * W.dim
        self.motivic_weight = V.motivic_weight + W.motivic_weight

        bad2 = ZZ(W.conductor).prime_factors()
        s2 = set(bad2)
        bad_primes = [x for x in ZZ(V.conductor).prime_factors() if x in s2]
        for p in bad_primes:
            if ((p not in V.bad_semistable_primes or p not in W.bad_pot_good) and
                (p not in W.bad_semistable_primes or p not in V.bad_pot_good)):
                 raise NotImplementedError("Currently tensor products of " +
                                          "Galois representations are only" +
                                          "implemented under some conditions.\n" +
                                          "Here the behaviour at %s is too wild."%p)
        ## add a hypothesis to exclude the poles.

        N = W.conductor ** V.dimension
        N *= V.conductor ** W.dimension
        for p in bad_primes:
            n1_tame = V.dimension - V.local_euler_factor(p).degree()
            n2_tame = W.dimension - W.local_euler_factor(p).degree()
            N = N // p ** (n1_tame * n2_tame)
        self.conductor = N

        #self.sign = NotImplementedError

        from lfmdb.lfunctions.HodgeTransformations import selberg_to_hodge, tensor_hodge, gamma_factors
        h1 = selberg_to_hodge(V.motivic_weight,V.mu_fe,V.nu_fe)
        h2 = selberg_to_hodge(W.motivic_weight,W.mu_fe,W.nu_fe)
        h = tensor_hodge(h1, h2)
        w,m,n = hodge_to_selberg(h)
        self.mu_fe = m
        self.nu_fe = n
        _, self.gammaV = gamma_factors(h)

        self.langlands = False # status 2014 :)

        #self.primitive = False
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        #self.dirichlet_coefficients = NotImplementedError

        self.selfdual = all( abs(an.imag) < 0.0001 for an in self.dirichlet_coefficients[:100]) # why not 100 :)

        self.coefficient_type = max(V.coefficient_type, W.coefficient_type)
        self.coefficient_period = V.coefficient_period().lcm(W.coefficient_period)
        self.ld.gp().quit()


## These are used when creating the classes with the above

    def set_dokchitser_Lfunction(self):
        """
        The L-function calling Dokchitser's code
        """
        if hasattr(self, "sign"):
            # print type(self.sign)
            # type complex would yield an error here.
            self.ld = Dokchitser(conductor = self.conductor,
                                gammaV = self.gammaV,
                                weight = self.motivic_weight,
                                eps = self.sign,
                                poles = [],
                                residues = [])
        else:
            # find the sign from the functional equation
            raise NotImplementedError


    def set_number_of_coefficients(self):
        """
        Determines the number of coefficients needed using Dokchitser's
        """
        if not hasattr(self, "ld"):
            self.set_dokchitser_Lfunction()
        # note the following line only sets all the variables in the
        # gp session of Dokchitser
        self.ld._gp_eval("MaxImaginaryPart = %s"%self.max_imaginary_part)
        self.numcoeff = self.ld.num_coeffs()

## The tensor product

    def __mul__(self, other):
        """
        The tensor product of two galois representations
        is represented here by *
        """
        return GaloisRepresentation([self,other])

## A function that gives back a L-function class as used later

    def Lfunction(self):
        """
        The L-function object associated to this class
        """
        from lmfdb.lfunctions.Lfunction import Lfunction_TensorProduct
        return Lfunction_GaloisRep(self)

## various direct accessible functions


    def root_number(self):
        """
        Root number
        """
        return self.sign


    def dimension(self):
        """
        Dimension = Degree
        """
        return self.dim


## Now to the L-function itself

    def lfunction(self):
        """
        This method replaces the class LFunction in lmfdb.lfunctions.Lfunction
        to generate the page for this sort of class.

        After asking for this method the object should have all
        methods and attributes as one of the subclasses of Lfunction in
        lmfdb.lfunctions.Lfunction.
        """
        self.compute_kappa_lambda_Q_from_mu_nu()

        self.texname = "L(s,\\rho)"
        self.texnamecompleteds = "\\Lambda(s,\\rho)"
        self.title = "$L(s,\\rho)$, where $\\rho$ is a Galois representation"

        self.credit = 'Workshop in Besancon, 2014'

        from lmfdb.lfunctions.Lfunction import generateSageLfunction
        generateSageLfunction(self)

    def Ltype(self):
        return "galoisrepresentation"

    # does not have keys in the previous sense really.
    def Lkey(self):
        return {"galoisrepresentation":self.title}

