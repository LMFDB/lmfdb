# -*- coding: utf-8 -*-
r"""

AUTHORS: Alberto Camara, Mark Watkins, Chris Wuthrich, 2014

Example:

sage: import lmfdb
sage: from lmfdb.tensor_products.galois_reps import GaloisRepresentation
sage: V1 = GaloisRepresentation(EllipticCurve("37a1"))
sage: V1.motivic_weight
sage: V1.local_euler_factor(37)

sage: from lmfdb.WebCharacter import WebDirichletCharacter
sage: chi = WebDirichletCharacter(modulus=37,number=4)
sage: V2 = GaloisRepresentation(chi)
sage: V2.langlands
sage: V2.local_euler_factor(101)

sage: from lmfdb.artin_representations.math_classes import ArtinRepresentation
sage: rho = ArtinRepresentation(2,23,1)
sage: V3 = GaloisRepresentation(rho)
sage: V3.dim
sage: V3.local_euler_factor(43)
sage: V3.algebraic_coefficients(10)


sage: from lmfdb.classical_modular_forms import WebNewform
sage: F = WebNewform.by_label('11.10.a.a')
sage: V4 = GaloisRepresentation([F,0])
sage: V4.sign
sage: V4.algebraic_coefficients(10)

sage: VW = GaloisRepresentation([V1,V2])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)
sage: VW = GaloisRepresentation([V1,V3])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)
sage: VW = GaloisRepresentation([V1,V4])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)
sage: VW = GaloisRepresentation([V2,V3])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)
sage: VW = GaloisRepresentation([V2,V4])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)
sage: VW = GaloisRepresentation([V3,V4])
sage: VW.algebraic_coefficients(10), VW.conductor, VW.sign
sage: %time VW.lfunction(), VW.numcoeff, len(VW.dirichlet_coefficients)


sage: V = GaloisRepresentation(EllipticCurve("37a1"))
sage: W = GaloisRepresentation(EllipticCurve("37b1"))
sage: VW = GaloisRepresentation([V,W])
sage: VW.algebraic_coefficients(38)[36] == -38

"""
# TODO
#
# Issues:
#
# * The tensor product of a modular form with a representation of
# dimension > 1, requires a lot of terms to be computed (numcoeff)
#and this takes a lot of time. We instead atrificially cap the number
#by an arbitrary bound (besancon_bound). Ideally, the dirichlet_coefficients
#of objects of small conductor should be stored on the database. Or at least
#stored as soon as someone makes us compute them once.

#* Currently we use dokchitsers function to compurte numcoeff. This creates
#a gp where this number is computed. The computation is very fast there,
#but I am not sure the gp().quit() really exits the gp session. They might
#pile up.

#* Obviously this class should be moved over to sage at some point and should
#integrate well with dokchitsers package as well as lcalc
#

#* This code is specific to tensor products of dimension \leq 2.  To handle
# higher dimension there are several pieces of code which one must check 
# still hold true.
########################################################################
# (C) Alberto Camara, Martin Dickson, Mark Watkins, Chris Wuthrich 2014
#       LMFDB workshop in Besancon with Tim and Vlad Dokchitser
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################

#import os
#import weakref

import lmfdb.base
from lmfdb.lfunctions.Lfunction_base import Lfunction
from lmfdb.lfunctions.HodgeTransformations import selberg_to_hodge, root_number_at_oo, hodge_to_selberg, tensor_hodge, gamma_factors

import sage
from sage.all import ZZ, QQ, RealField, ComplexField, PolynomialRing, PowerSeriesRing, I, sqrt, prime_range, Dokchitser, O

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

        elif isinstance(thingy, lmfdb.WebCharacter.WebDirichletCharacter):
            self.init_dir_char(thingy)

        elif isinstance(thingy, lmfdb.artin_representations.math_classes.ArtinRepresentation):
            self.init_artin_rep(thingy)

        elif (isinstance(thingy, list) and
              len(thingy) == 2 and
              isinstance(thingy[0],lmfdb.classical_modular_forms.web_newform.WebNewform) and
              isinstance(thingy[1],sage.rings.integer.Integer) ):
            self.init_elliptic_modular_form(thingy[0],thingy[1])

        elif (isinstance(thingy, list) and
              len(thingy) == 2 and
              isinstance(thingy[0], GaloisRepresentation) and
              isinstance(thingy[1], GaloisRepresentation) ):
            self.init_tensor_product(thingy[0], thingy[1])

        else:
            raise ValueError("GaloisRepresentations are currently not implemented for that type (%s) of objects"%type(thingy))

        # set a few common variables
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
        self.coefficient_type = 2
        self.coefficient_period = 0
        self.besancon_bound = 50000
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
            R = PolynomialRing(QQ, "T")
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
        self.besancon_bound = 10000

        def eu(p):
            """
            local euler factor
            """
            if self.selfdual:
                K = QQ
            else:
                K = ComplexField()
            R = PolynomialRing(K, "T")
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
        self.coefficient_type = 0
        self.coefficient_period = 0
        self.besancon_bound = 3000

        def eu(p):
            """
            local euler factor
            """
            f = rho.local_factor(p)
            co = [ZZ(round(x)) for x in f.coefficients(sparse=False)]
            R = PolynomialRing(QQ, "T")
            T = R.gens()[0]
            return sum( co[n] * T**n for n in range(len(co)))

        self.local_euler_factor = eu
        self.ld.gp().quit()

    def init_elliptic_modular_form(self, F, number):
        """
        Initiate with an Elliptic Modular Form.
        """
        self.number = number
        self.original_object = [[F,number]]
        self.object_type = "Elliptic Modular newform"
        self.dim = 2
        self.weight = ZZ(F.weight)
        self.motivic_weight = ZZ(F.weight) - 1
        self.conductor = ZZ(F.level)
        self.bad_semistable_primes = [fa[0] for fa in self.conductor.factor() if fa[1]==1 ]
        # should be including primes of bad red that are pot good
        # however I don't know how to recognise them
        self.bad_pot_good = []
        self.langlands = True
        self.mu_fe = []
        self.nu_fe = [ZZ(F.weight-1)/ZZ(2)]
        self.primitive = True
        self.selfdual = True
        self.coefficient_type = 2
        self.coefficient_period = 0
        self.sign = (-1) ** (self.weight / 2.)
        if self.conductor != 1:
            for p, ev in F.atkin_lehner_eigenvals:
                self.sign *= ev**(self.conductor.valuation(p))
        self.gammaV = [0,1]
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        self.besancon_bound = 300

        def eu(p):
            """
            Local euler factor
            """
            # There was no function q_expansion_embeddings before the transition to postgres
            # so I'm not sure what this is supposed to do.
            ans = F.q_expansion_embeddings(p + 1)
            K = ComplexField()
            R = PolynomialRing(K, "T")
            T = R.gens()[0]
            N = self.conductor
            if N % p != 0 : # good reduction
                return 1 - ans[p-1][self.number] * T + T**2
            elif N % (p**2) != 0: # semistable reduction
                return 1 - ans[p-1][self.number] * T
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
        self.V1 = V
        self.V2 = W
        self.dim = V.dim * W.dim
        self.motivic_weight = V.motivic_weight + W.motivic_weight
        self.langlands = False # status 2014 :)
        self.besancon_bound = min(V.besancon_bound, W.besancon_bound)

        bad2 = ZZ(W.conductor).prime_factors()
        bad_primes = [x for x in ZZ(V.conductor).prime_factors() if x in bad2]
        for p in bad_primes:
            if ( p not in V.bad_semistable_primes and p not in W.bad_semistable_primes) :
                # this condition above only applies to the current type of objects
                # for general reps we would have to test the lines below
                # to be certain that the formulae are correct.
                #if ((p not in V.bad_semistable_primes or p not in W.bad_pot_good) and
                    #(p not in W.bad_semistable_primes or p not in V.bad_pot_good) and
                    #(p not in V.bad_semistable_primes or p not in W.bad_semistable_primes)):
                raise NotImplementedError("Currently tensor products of Galois representations are only implemented under some conditions.",
                                          "The behaviour at %d is too wild (both factors must be semistable)." % p)

        # check for the possibily of getting poles
        if V.weight == W.weight and V.conductor == W.conductor :
            Vans = V.algebraic_coefficients(50)
            Wans = W.algebraic_coefficients(50)
            CC = ComplexField()
            if ((Vans[2] in ZZ and Wans[2] in ZZ and
                all(Vans[n] == Wans[n] for n in range(1,50) ) ) or
                all( CC(Vans[n]) == CC(Wans[n]) for n in range(1,50) ) ):
                    raise NotImplementedError("It seems you are asking to tensor a "+
                                              "Galois representation with its dual " +
                                              "which results in the L-function having "+
                                              "a pole. This is not implemented here.")

        scommon = [x for x in V.bad_semistable_primes if x in W.bad_semistable_primes]

        N = W.conductor ** V.dim
        N *= V.conductor ** W.dim
        for p in bad_primes:
            n1_tame = V.dim - V.local_euler_factor(p).degree()
            n2_tame = W.dim - W.local_euler_factor(p).degree()
            nn = n1_tame * n2_tame
            N = N // p ** nn
            if p in scommon: # both are degree 1 in this case
                N = N // p
        self.conductor = N

        h1 = selberg_to_hodge(V.motivic_weight,V.mu_fe,V.nu_fe)
        h2 = selberg_to_hodge(W.motivic_weight,W.mu_fe,W.nu_fe)
        h = tensor_hodge(h1, h2)
        w,m,n = hodge_to_selberg(h)
        self.mu_fe = m
        self.nu_fe = n
        _, self.gammaV = gamma_factors(h)

        # this is used in getting the Dirichlet coefficients.
        self.bad_primes_info = []
        for p in bad_primes:
            # we have to check if this works in all bad cases !
            f1 = V.local_euler_factor(p)
            f2 = W.local_euler_factor(p)
            # might be dodgy if f1 or f2 is an approx to the Euler factor
            if p in scommon:
                E = tensor_local_factors(f1,f2,V.dim*W.dim)
                T = f1.parent().gens()[0] # right answer is E(T)*E(pT)
                self.bad_primes_info.append([p,E*E(p*T),1-T]) #bad_primes_info.append() with 1-T as the second argument is equivalent to taking the first argument as the results (it does a convolution, as in the next line)
            else:
                self.bad_primes_info.append([p,f1,f2])

        CC = ComplexField()
        I = CC.gens()[0]
        self.sign = I ** root_number_at_oo(h)
        self.sign /= I ** (root_number_at_oo(h1) * V.dim)
        self.sign /= I ** (root_number_at_oo(h2) * W.dim)
        self.sign *= V.sign ** W.dim
        self.sign *= W.sign ** V.dim
        for p in bad_primes:
            if p not in V.bad_semistable_primes or p not in V.bad_semistable_primes:
                f1 = V.local_euler_factor(p)
                f2 = W.local_euler_factor(p)
                det1 = f1.leading_coefficient() * (-1) ** f1.degree()
                det2 = f2.leading_coefficient() * (-1) ** f2.degree()
                n1_tame = V.dim - f1.degree()
                n2_tame = W.dim - f2.degree()
                n1_wild = ZZ(V.conductor).valuation(p) - n1_tame
                n2_wild = ZZ(W.conductor).valuation(p) - n2_tame
                # additionally, we would need to correct this by
                # replacing det1 by chi1(p) if p is semistable for V
                # however for all the possible input this currently does
                # not affect the sign
                if p in V.bad_semistable_primes:
                    chi1p = 1 # here
                else:
                    chi1p = det1
                if p in W.bad_semistable_primes:
                    chi2p = 1 # here
                else:
                    chi2p = det2

                corr = chi1p ** n2_wild
                corr *= det1 ** n2_tame
                corr *= chi2p ** n1_wild
                corr *= det2 ** n1_tame
                corr *= (-1) ** (n1_tame * n2_tame)

                self.sign *= corr/corr.abs()

        #self.primitive = False
        self.set_dokchitser_Lfunction()
        # maybe we should change this to take as many coefficients as implemented
        # in other Lfunctions
        self.set_number_of_coefficients()

        someans = self.algebraic_coefficients(50) # why not.
        if all( x in ZZ for x in someans):
            self.selfdual = True
        else:
            CC = ComplexField()
            self.selfdual = all( CC(an).imag().abs() < 0.0001 for an in someans)

        self.coefficient_type = max(V.coefficient_type, W.coefficient_type)
        self.coefficient_period = ZZ(V.coefficient_period).lcm(W.coefficient_period)
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
            # this should be implemented later:
            # one can pass a variable 'x' to the function
            # checking the functional equation
            # and it will return a linear polynomial in x
            # such that the root must be the sign
            raise NotImplementedError


    def set_number_of_coefficients(self):
        """
        Determines the number of coefficients needed using Dokchitser's
        Note is the number we SHOULD compute. However we will cap this to
        a smaller size later.
        """
        if not hasattr(self, "ld"):
            self.set_dokchitser_Lfunction()
        # note the following line only sets all the variables in the
        # gp session of Dokchitser
        self.ld._gp_eval("MaxImaginaryPart = %s"%self.max_imaginary_part)
        self.numcoeff = self.ld.num_coeffs()
        # to be on the safe side, we make sure to have a min of terms
        if self.numcoeff < 50:
            self.numcoeff = 50

## produce coefficients

    def algebraic_coefficients(self, number_of_terms):
        """
        Computes the list [a1,a2,... of coefficients up
        to a bound. Note that [0] is a1.
        This is in the alg. normalisation, i.e. s <-> w+1-s
        """

        if self.object_type == "ellipticcurve":
            return self.original_object[0].anlist(number_of_terms)[1:]
        elif self.object_type == "dirichletcharacter":
            chi = self.original_object[0].chi.primitive_character()
            return [ chi(m) for m in range(1, number_of_terms) ]
        elif self.object_type == "Artin representation":
            rho = self.original_object[0]
            return rho.coefficients_list(upperbound=number_of_terms)
        elif self.object_type == "Elliptic Modular newform":
            F = self.original_object[0][0]
            i = self.original_object[0][1]
            embeddings = F.q_expansion_embeddings(number_of_terms)[1:]
            return [x[i] for x in embeddings]
        elif self.object_type == "tensorproduct":
            V = self.V1
            W = self.V2
            L1 = V.algebraic_coefficients(number_of_terms)
            L2 = W.algebraic_coefficients(number_of_terms)
            return tensor_get_an(L1, L2, V.dim, W.dim, self.bad_primes_info)
        else:
            raise ValueError("You asked for a type that we don't have")


    def renormalise_coefficients(self):
        """
        This turns a list of algebraically normalised coefficients
        as above into a list of automorphically normalised,
        i.e. s <-> 1-s
        """
        # this also turns them into floats and complex.
        for n in range(len(self.dirichlet_coefficients)):
            self.dirichlet_coefficients[n] /= sqrt(float(n+1)**self.motivic_weight)


## The tensor product

    def __mul__(self, other):
        """
        The tensor product of two galois representations
        is represented here by *
        """
        return GaloisRepresentation([self,other])

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

    def cond(self):
        """
        Conductor
        """
        return self.conductor


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

        # when tensoring a modular form with a dim > 1 rep, we run
        # into having to compute a lot of coefficients and this will
        # take a lot of time. We cut it down and print a warning
        number_of_terms = min(self.numcoeff, self.besancon_bound)
        self.dirichlet_coefficients = self.algebraic_coefficients(number_of_terms+1)
        self.renormalise_coefficients()

        self.texname = "L(s,\\rho)"
        self.texnamecompleteds = "\\Lambda(s,\\rho)"
        self.texnamecompleted1ms = "\\Lambda(1-s, \\widehat{\\rho})" 
        self.title = "$L(s,\\rho)$, where $\\rho$ is a Galois representation"

        self.credit = 'Workshop in Besancon, 2014'

        from lmfdb.lfunctions.Lfunction import generateSageLfunction
        generateSageLfunction(self)

    def Ltype(self):
        return "galoisrepresentation"

#########################
# This is copied from Mark Watkin's code:

def tensor_get_an(L1, L2, d1, d2, BadPrimeInfo):
    """
    Takes two lists of list of Dirichlet coefficients
    and returns the list of their tensor product
    Input: two lists L1, L2, two dimensions d1, d2 and
    information about bad primes.
    BadPrimeInfo is a list of list of the form [p,f1,f2]
    where p is a prime and f1, f2 are two euler factors at p.
    The function will take the tensor prod at f1,f2 at bad primes;
    if have the right answer, give this as one of the two, and the
    other as 1-t. If one of L1 and L2 is deg 1, then this calls
    a special function, with a different BadPrime methodology.
    """
    if d1==1:
        return tensor_get_an_deg1(L2,L1,[[bpi[0],tensor_local_factors(bpi[1],bpi[2],d1*d2)] for bpi in BadPrimeInfo])
    if d2==1:
        return tensor_get_an_deg1(L1,L2,[[bpi[0],tensor_local_factors(bpi[1],bpi[2],d1*d2)] for bpi in BadPrimeInfo])
    return tensor_get_an_no_deg1(L1,L2,d1,d2,BadPrimeInfo)

def tensor_get_an_no_deg1(L1, L2, d1, d2, BadPrimeInfo):
    """
    Same as the above in the case no dimension is 1
    """
    if d1==1 or d2==1:
        raise ValueError('min(d1,d2) should not be 1, use direct method then')
    s1 = len(L1)
    s2 = len(L2)
    if s1 < s2:
        S = s1
    if s2 <= s1:
        S = s2
    BadPrimes = []
    for bpi in BadPrimeInfo:
        BadPrimes.append(bpi[0])
    P = prime_range(S+1)
    Z = S * [1]
    S = RealField()(S)
    for p in P:
        f = S.log(base=p).floor()
        q = 1
        E1 = []
        E2 = []
        if not p in BadPrimes:
            for i in range(f):
                q=q*p
                E1.append(L1[q-1])
                E2.append(L2[q-1])
            e1 = list_to_euler_factor(E1,f+1)
            e2 = list_to_euler_factor(E2,f+1)
            # ld1 = d1 # not used
            # ld2 = d2 # not used
        else: # either convolve, or have one input be the answer and other 1-t
            i = BadPrimes.index(p)
            e1 = BadPrimeInfo[i][1]
            e2 = BadPrimeInfo[i][2]
            # ld1 = e1.degree() # not used
            # ld2 = e2.degree() # not used
            F = e1.list()[0].parent().fraction_field()
            R = PowerSeriesRing(F, "T", default_prec=f+1)
            e1 = R(e1)
            e2 = R(e2)
        E = tensor_local_factors(e1,e2,f)
        A = euler_factor_to_list(E,f)
        while len(A) < f:
            A.append(0)
        q = 1
        for i in range(f):
            q = q*p
            Z[q-1]=A[i]
    all_an_from_prime_powers(Z)
    return Z

def tensor_get_an_deg1(L, D, BadPrimeInfo):
    """
    Same as above, except that the BadPrimeInfo
    is now a list of lists of the form
    [p,f] where f is a polynomial.
    """
    s1 = len(L)
    s2 = len(D)
    if s1 < s2:
        S = s1
    if s2 <= s1:
        S = s2
    BadPrimes = []
    for bpi in BadPrimeInfo:
        BadPrimes.append(bpi[0])
    P = prime_range(S+1)
    Z = S * [1]
    S = RealField()(S) # fix bug
    for p in P:
        f = S.log(base=p).floor()
        q = 1
        u = 1
        e = D[p-1]
        if not p in BadPrimes:
            for i in range(f):
                q = q*p
                u = u*e
                Z[q-1] = u*L[q-1]
        else:
            i = BadPrimes.index(p)
            e = BadPrimeInfo[i][1]
            F = e.list()[0].parent().fraction_field()
            R = PowerSeriesRing(F, "T", default_prec=f+1)
            e = R(e)
            A = euler_factor_to_list(e,f)
            for i in range(f):
                q = q*p
                Z[q-1] = A[i]
    all_an_from_prime_powers(Z)
    return Z

def all_an_from_prime_powers(L):
    """
    L is a list of an such that the terms
    are correct for all n which are prime powers
    and all others are equal to 1;
    this function changes the list in place to make
    the correct ans for all n
    """
    S = ZZ(len(L))
    for p in prime_range(S+1):
        q = 1
        Sr = RealField()(len(L))
        f = Sr.log(base=p).floor()
        for k in range(f):
            q = q*p
            for m in range(2, 1+(S//q)):
                if (m%p) != 0:
                    L[m*q-1] = L[m*q-1] * L[q-1]


def euler_factor_to_list(P, prec):
    """
    P a polynomial (or power series)
    returns the list [a_p, a_p^2, ...
    """
    K = P[0].parent()
    R = PowerSeriesRing(K, "T", default_prec=prec+1)
    L = ((1/R(P.truncate().coefficients(sparse=False))).truncate().coefficients(sparse=False))[1:]
    while len(L) < prec: # include zeros at end
        L.append(0)
    return L

def get_euler_factor(L,p):
    """
    takes L list of all ans and p is a prime
    it returns the euler factor at p
    # utility function to get an Euler factor, unused
    """
    S = RealField()(len(L))
    f = S.log(base=p).floor()
    E = []
    q = 1
    for i in range(f):
        q = q*p
        E.append(L[q-1])
    return list_to_euler_factor(E,f)


def list_to_euler_factor(L,d):
    """
    takes a list [a_p, a_p^2,...
    and returns the euler factor
    """
    if isinstance(L[0], int):
        K = QQ
    else:
        K = L[0].parent()
    R = PowerSeriesRing(K, "T")
    # T = R.gens()[0]
    f =  1/ R([1]+L)
    f = f.add_bigoh(d+1)
    return f

def tensor_local_factors(f1, f2, d):
    """
    takes two euler factors f1, f2 and a prec and
    returns the euler factor for the tensor
    product (with respect to that precision d
    """
    # base rings are either QQ or CC
    K1 = f1.base_ring()
    K2 = f2.base_ring()
    if K1 == ComplexField() or K2 == ComplexField():
        K = ComplexField()
    else:
        K = QQ
    R = PowerSeriesRing(K, "T")
    if not f1.parent().is_exact(): # ideally f1,f2 should already be in PSR
        if f1.prec() < d:
            raise ValueError
    if not f2.parent().is_exact(): # but the user might give them as polys...
        if f2.prec() < d:
            raise ValueError
    f1 = R(f1)
    f2 = R(f2)
    if f1==1 or f2==1:
        f = R(1)
        f = f.add_bigoh(d+1)
        return f
    l1 = f1.log().derivative()
    p1 = l1.prec()
    c1 = l1.list()
    while len(c1) < p1:
        c1.append(0)
    l2 = f2.log().derivative()
    p2 = l2.prec()
    c2 = l2.list()
    while len(c2) < p2:
        c2.append(0)
    C = [0] * len(c1)
    for i in range(len(c1)):
        C[i] = c1[i] * c2[i]
    E = - R(C).integral()
    E = E.add_bigoh(d+1)
    E = E.exp() # coerce to R
    return E

## test functions to check if the above agrees with magma

def test_tensprod_121_chi():
    C121=[1,2,-1,2,1,-2,2,0,-2,2,0,-2,-4,4,-1,-4,2,-4,0,2,-2,0,\
    -1,0,-4,-8,5,4,0,-2,7,-8,0,4,2,-4,3,0,4,0,8,-4,6,0,-2,-2,\
    8,4,-3,-8,-2,-8,-6,10,0,0,0,0,5,-2,-12,14,-4,-8,-4,0,-7,4,\
    1,4,-3,0,-4,6,4,0,0,8,10,-4,1,16,6,-4,2,12,0,0,15,-4,-8,\
    -2,-7,16,0,8,-7,-6,0,-8,-2,-4,-16,0,-2,-12,-18,10,-10,0,-3,\
    -8,9,0,-1,0,8,10,4,0,0,-24,-8,14,-9,-8,-8,0,-6,-8,18,0,0,\
    -14,5,0,-7,2,-10,4,-8,-6,0,8,0,-8,3,6,10,8,-2,0,-4,0,7,8,\
    -7,20,6,-8,-2,2,4,16,0,12,12,0,3,4,0,12,6,0,-8,0,-5,30,\
    -15,-4,7,-16,12,0,3,-14,0,16,10,0,17,8,-4,-14,4,-6,2,0,0,0]
    chi=[1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,\
    1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,\
    -1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,\
    1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,\
    1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,\
    1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,\
    -1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,\
    -1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,\
    -1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1]
    ANS=[1,-2,-1,2,1,2,-2,0,-2,-2,1,-2,4,4,-1,-4,-2,4,0,2,2,-2,\
    -1,0,-4,-8,5,-4,0,2,7,8,-1,4,-2,-4,3,0,-4,0,-8,-4,-6,2,-2,\
    2,8,4,-3,8,2,8,-6,-10,1,0,0,0,5,-2,12,-14,4,-8,4,2,-7,-4,\
    1,4,-3,0,4,-6,4,0,-2,8,-10,-4,1,16,-6,4,-2,12,0,0,15,4,-8,\
    -2,-7,-16,0,-8,-7,6,-2,-8,2,-4,-16,0,2,12,18,10,10,-2,-3,8,\
    9,0,-1,0,-8,-10,4,0,1,-24,8,14,-9,-8,8,0,6,-8,-18,-2,0,14,\
    5,0,-7,-2,10,-4,-8,6,4,8,0,-8,3,6,-10,-8,2,0,4,4,7,-8,-7,\
    20,6,8,2,-2,4,-16,-1,12,-12,0,3,4,0,-12,-6,0,8,-4,-5,-30,\
    -15,-4,7,16,-12,0,3,14,-2,16,-10,0,17,8,4,14,-4,-6,-2,4,0,0]
    R = PowerSeriesRing(ZZ, "T")
    T = R.gens()[0]
    assert ANS==tensor_get_an_deg1(C121,chi,[[11,1-T]])
    assert ANS==tensor_get_an(C121,chi,2,1,[[11,1-T,1-T]])
    assert get_euler_factor(ANS,2)==(1+2*T+2*T**2+O(T**8))
    assert get_euler_factor(ANS,3)==(1+T+3*T**2+O(T**5))
    assert get_euler_factor(ANS,5)==(1-T+5*T**2+O(T**4))

def test_tensprod_11a_17a():
    C11=[1,-2,-1,2,1,2,-2,0,-2,-2,1,-2,4,4,-1,-4,-2,4,0,2,2,-2,\
    -1,0,-4,-8,5,-4,0,2,7,8,-1,4,-2,-4,3,0,-4,0,-8,-4,-6,2,-2,\
    2,8,4,-3,8,2,8,-6,-10,1,0,0,0,5,-2,12,-14,4,-8,4,2,-7,-4,\
    1,4,-3,0,4,-6,4,0,-2,8,-10,-4,1,16,-6,4,-2,12,0,0,15,4,-8,\
    -2,-7,-16,0,-8,-7,6,-2,-8,2,-4,-16,0,2,12,18,10,10,-2,-3,8,\
    9,0,-1,0,-8,-10,4,0,1,-24,8,14,-9,-8,8,0,6,-8,-18,-2,0,14,\
    5,0,-7,-2,10,-4,-8,6,4,8,0,-8,3,6,-10,-8,2,0,4,4,7,-8,-7,\
    20,6,8,2,-2,4,-16,-1,12,-12,0,3,4,0,-12,-6,0,8,-4,-5,-30,\
    -15,-4,7,16,-12,0,3,14,-2,16,-10,0,17,8,4,14,-4,-6,-2,4,0,0]
    C17=[1,-1,0,-1,-2,0,4,3,-3,2,0,0,-2,-4,0,-1,1,3,-4,2,0,0,4,\
    0,-1,2,0,-4,6,0,4,-5,0,-1,-8,3,-2,4,0,-6,-6,0,4,0,6,-4,0,\
    0,9,1,0,2,6,0,0,12,0,-6,-12,0,-10,-4,-12,7,4,0,4,-1,0,8,\
    -4,-9,-6,2,0,4,0,0,12,2,9,6,-4,0,-2,-4,0,0,10,-6,-8,-4,0,\
    0,8,0,2,-9,0,1,-10,0,8,-6,0,-6,8,0,6,0,0,-4,-14,0,-8,-6,\
    6,12,4,0,-11,10,0,-4,12,12,8,3,0,-4,16,0,-16,-4,0,3,-6,0,\
    -8,8,0,4,0,3,-12,6,0,2,-10,0,-16,-12,-3,0,-8,0,-2,-12,0,10,\
    16,-9,24,6,0,4,-4,0,-9,2,12,-4,22,0,-4,0,0,-10,12,-6,-2,8,\
    0,12,4,0,0,0,0,-8,-16,0,2,-2,0,-9,-18,0,-20,-3]
    ANS=[1,2,0,2,-2,0,-8,8,15,-4,0,0,-8,-16,0,12,-2,30,0,-4,0,0,\
    -4,0,29,-16,0,-16,0,0,28,-8,0,-4,16,30,-6,0,0,-16,48,0,-24,\
    0,-30,-8,0,0,22,58,0,-16,-36,0,0,-64,0,0,-60,0,-120,56,-120,\
    -8,16,0,-28,-4,0,32,12,120,-24,-12,0,0,0,0,-120,-24,144,96,\
    24,0,4,-48,0,0,150,-60,64,-8,0,0,0,0,-14,44,0,58,-20,0,-128,\
    -64,0,-72,144,0,60,0,0,-96,-126,0,8,0,-120,-120,16,0,-11,-240,\
    0,56,-158,-240,64,-32,0,32,-288,0,0,-56,0,-16,42,0,-80,32,0,\
    24,0,180,0,-48,0,-12,100,0,-32,0,-30,0,-56,0,14,-240,0,16,32,\
    288,96,96,0,48,48,0,142,8,0,-48,-132,0,-232,0,0,300,-180,-60,\
    -14,128,0,-32,12,0,0,0,0,0,-272,0,8,-28,0,44,36,0,0,232]
    R = PowerSeriesRing(ZZ, "T")
    T = R.gens()[0]
    B11=[11,1-T,1+11*T**2]
    B17=[17,1+2*T+17*T**2,1-T]
    assert ANS==tensor_get_an_no_deg1(C11,C17,2,2,[B11,B17])

### comparison with previous implementation.

#sage: E = EllipticCurve("11a1")
#sage: from lmfdb.tensor_products.galois_reps import GaloisRepresentation
#sage: V = GaloisRepresentation(E)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.0,
 #-1.414213562373095,
 #-0.5773502691896258,
 #1.0,
 #0.4472135954999579,
 #0.8164965809277261,
 #-0.7559289460184544,
 #0.0,
 #-0.6666666666666666,
 #-0.6324555320336759]

#sage: chi = WebDirichletCharacter(modulus=5,number=2)
#sage: V = GaloisRepresentation(chi)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[(1+0j),
 #(6.123233995736766e-17+1j),
 #(-1.8369701987210297e-16-1j),
 #(-1+1.2246467991473532e-16j),
 #0j,
 #(1+0j),
 #(6.123233995736766e-17+1j),
 #(-1.8369701987210297e-16-1j),
 #(-1+1.2246467991473532e-16j),
 #0j]
#sage: chi = WebDirichletCharacter(modulus=5,number=4)
#sage: V = GaloisRepresentation(chi)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[(1+0j),
 #(-1+1.2246467991473532e-16j),
 #(-1+1.2246467991473532e-16j),
 #(1+0j),
 #0j,
 #(1+0j),
 #(-1+1.2246467991473532e-16j),
 #(-1+1.2246467991473532e-16j),
 #(1+0j),
 #0j]

#sage: rho = ArtinRepresentation(1,5,1)
#sage: V = GaloisRepresentation(rho)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.0,
 #-1.00000000000000,
 #-1.00000000000000,
 #1.00000000000000,
 #0.0,
 #1.00000000000000,
 #-1.00000000000000,
 #-1.00000000000000,
 #1.00000000000000,
 #0.0]
#sage: rho = ArtinRepresentation(1,5,2)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.0,
 #-1.00000000000000,
 #-1.00000000000000,
 #1.00000000000000,
 #0.0,
 #1.00000000000000,
 #-1.00000000000000,
 #-1.00000000000000,
 #1.00000000000000,
 #0.0]
#sage: rho = ArtinRepresentation(1,4,1)
#sage: V = GaloisRepresentation(rho)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.0,
 #0.0,
 #-1.00000000000000,
 #0.0,
 #1.00000000000000,
 #0.000000000000000,
 #-1.00000000000000,
 #0.0,
 #1.00000000000000,
 #0.000000000000000]
#sage: rho = ArtinRepresentation(2,23,1)
#sage: V = GaloisRepresentation(rho)
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.0,
 #-1.00000000000000,
 #-1.00000000000000,
 #0.000000000000000,
 #0.000000000000000,
 #1.00000000000000,
 #0.000000000000000,
 #1.00000000000000,
 #0.000000000000000,
 #0.000000000000000]
#sage: F = WebNewForm(13,6,fi=1)
#sage: V = GaloisRepresentation([F,2])
#sage: V.lfunction()
#sage: V.dirichlet_coefficients[:10]
#[1.00000000000000,
 #1.93884868019520,
 #-1.01350067313149,
 #2.75913420469466,
 #-0.923149364468465,
 #-1.96502444247794,
 #-0.581577296211895,
 #3.41069503105848,
 #0.0271836144379852,
 #-1.78984692692272]

