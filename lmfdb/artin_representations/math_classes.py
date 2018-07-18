# -*- coding: utf-8 -*-

from lmfdb.db_backend import db
from lmfdb.utils import url_for, pol_to_html
from lmfdb.typed_data.standard_types import PolynomialAsSequenceTooLargeInt
from sage.all import PolynomialRing, QQ, ComplexField, exp, pi, Integer, valuation, CyclotomicField, RealField, log, I, factor, crt, euler_phi, primitive_root, mod, next_prime
from lmfdb.transitive_group import group_display_knowl, group_display_short, tryknowl
from lmfdb.WebNumberField import WebNumberField
from lmfdb.WebCharacter import WebSmallDirichletCharacter


# fun is the function, N the modulus, and n the denominator
# for values (value a means e(a/n))
def id_dirichlet(fun, N, n):
    N = Integer(N)
    if N==1:
        return (1,1)
    p2 = valuation(N, 2)
    N2 = 2**p2
    Nodd = N/N2
    Nfact = list(factor(Nodd))
    #print "n = "+str(n)
    #for j in range(20):
    #    print "chi(%d) = e(%d/%d)"%(j+2, fun(j+2,n), n)
    plist = [z[0] for z in Nfact]
    ppows = [z[0]**z[1] for z in Nfact]
    ppows2 = list(ppows)
    idems = [1 for z in Nfact]
    proots = [primitive_root(z) for z in ppows]
    # Get CRT idempotents
    if p2>0:
        ppows2.append(N2)
    for j in range(len(plist)):
        exps = [1 for z in idems]
        if p2>0:
            exps.append(1)
        exps[j] = proots[j]
        idems[j] = crt(exps, ppows2)
    idemvals = [fun(z,n) for z in idems]
    # now normalize to right root of unity base
    idemvals = [idemvals[j] * euler_phi(ppows[j])/n for j in range(len(idemvals))]
    ans = [Integer(mod(proots[j], ppows[j])**idemvals[j]) for j in range(len(proots))]
    ans = crt(ans, ppows)
    # There are cases depending on 2-part of N
    if p2==0:
        return (N, ans)
    if p2==1:
        return (N, crt([1, ans], [2, Nodd]))
    if p2==2:
        my3=crt([3, 1], [N2, Nodd])
        if fun(my3,n) == 0:
            return (N, crt([1, ans], [4, Nodd]))
        else:
            return (N, crt([3, ans], [4, Nodd]))
    # Final case 2^3 | N

    my5=crt([5, 1], [N2, Nodd])
    test1 = fun(my5,n) * N2/4/n
    test1 = Integer(mod(5,N2)**test1)
    minusone = crt([-1,1], [N2, Nodd])
    test2 = (fun(minusone, n) * N2/4/n) % (N2/4)
    if test2 > 0:
        test1 = Integer(mod(-test1, N2))
    return (N, crt([test1, ans], [N2, Nodd]))

def process_algebraic_integer(seq, root_of_unity):
    return sum(Integer(seq[i]) * root_of_unity ** i for i in range(len(seq)))

def process_polynomial_over_algebraic_integer(seq, field, root_of_unity):
    from sage.rings.all import PolynomialRing
    PP = PolynomialRing(field, "x")
    return PP([process_algebraic_integer(x, root_of_unity) for x in seq])

def _search_and_convert_iterator(cls, source):
    for x in source:
        yield cls(data=x)


class ArtinRepresentation(object):
    def __init__(self, *x, **data_dict):
        if len(x) == 0:
            # Just passing named arguments
            self._data = data_dict["data"]
            label=self._data['label']
        else:
            if len(x) == 1: # Assume we got a label
                label = x[0]
                parts = x[0].split("c")
                base = parts[0]
                conjindex = int(parts[1])
            elif len(x) == 2: # base and gorb index
                base = x[0]
                conjindex = x[1]
                label = "%sc%s"%(str(x[0]),str(x[1]))
            else:
                raise ValueError("Invalid number of positional arguments")
            self._data = db.artin_reps.convert_lucky({'Baselabel':str(base)})
            conjs = self._data["GaloisConjugates"]
            conj = [xx for xx in conjs if xx['GalOrbIndex'] == conjindex]
            self._data['label'] = label
            self._data.update(conj[0])

    @classmethod
    def search(cls, query={}, projection=1, limit=None, offset=0, sort=None, info=None):
        results = db.artin_reps.search_and_convert(query, projection, limit=limit, offset=offset, sort=sort, info=info)
        if limit is None:
            return _search_and_convert_iterator(cls, results)
        else:
            return [cls(data=x) for x in results]

    @classmethod
    def lucky(cls, *args, **kwds):
        # What about label?
        return cls(data=db.artin_reps.convert_lucky(*args, **kwds))

    @classmethod
    def find_one_in_galorbit(cls, baselabel):
        return cls(baselabel,1)

    def baselabel(self):
        return str(self._data["Baselabel"])

    def label(self):
        return str(self._data['label'])

    def dimension(self):
        return int(self._data["Dim"])

    def conductor(self):
        return int(self._data["Conductor"])

    def NFGal(self):
        return  map(int, self._data["NFGal"]);

    def conductor_equation(self):
        # Returns things of the type "1", "7", "49 = 7^{2}"
        factors = self.factored_conductor()
        if self.conductor() == 1:
            return "1"
        if len(factors) == 1 and factors[0][1] == 1:
            return str(self.conductor())
        else:
            return str(self.conductor()) + "=" + self.factored_conductor_latex()

    def factored_conductor(self):
        return [(p, valuation(Integer(self.conductor()), p)) for p in self.bad_primes()]

    def factored_conductor_latex(self):
        if self.conductor() == 1:
            return "1"

        def power_prime(p, exponent):
            if exponent == 1:
                return " " + str(p) + " "
            else:
                return " " + str(p) + "^{" + str(exponent) + "}"
        tmp = " \cdot ".join(power_prime(p, val) for (p, val) in self.factored_conductor())
        return tmp

    def hard_primes(self):
        try:
            return self._hard_primes
        except AttributeError:
            from sage.rings.all import Integer
            self._hard_primes = [Integer(str(x)) for x in self._data["HardPrimes"]]
            return self._hard_primes

    def is_hard_prime(self, p):
        return p in self.hard_primes()

    def bad_primes(self):
        try:
            return self._bad_primes
        except AttributeError:
            from sage.rings.all import Integer
            self._bad_primes = [Integer(str(x)) for x in self._data["BadPrimes"]]
            return self._bad_primes

    def is_bad_prime(self, p):
        return p in self.bad_primes()

    def character_field(self):
        return self._data["CharacterField"]

    def GaloisConjugates(self):
        return self._data["GaloisConjugates"]

    def number_field_galois_group(self):
        try:
            return self._nf
        except AttributeError:
            self._nf = NumberFieldGaloisGroup.lucky({"Polynomial":  self.NFGal()})
        return self._nf

    def galois_conjugacy_size(self):
    	return len(self.GaloisConjugates())

    def smallest_gal_t(self):
        try:
            return self._small_nt
        except AttributeError:
            tmp = str(self._data["Baselabel"])
            bits = tmp.split('.')
            tmp = bits[2]
            bits = tmp.split('t')
            self._small_nt = [int(z) for z in bits]
    	return self._small_nt

    def smallest_gal_t_format(self):
        galnt = self.smallest_gal_t()
        if len(galnt)==1:
            return galnt[0]
        return tryknowl(galnt[0],galnt[1])

    def is_ramified(self, p):
        return self.number_field_galois_group().discriminant() % p == 0

    # sets up, and returns a function to compute the central character
    # as a function
    def central_char_function(self):
        dim = self.dimension()
        dfactor = (-1)**dim
        # doubling insures integers below
        # we could test for when we need it, but then we carry the "if"
        # throughout
        charf = 2*self.character_field()
        localfactors = self.local_factors_table()
        bad = [0 if dim+1>len(z) else 1 for z in localfactors]
        localfactors = [self.from_conjugacy_class_index_to_polynomial(j+1) for j in range(len(localfactors))]
        localfactors = [z.leading_coefficient()*dfactor for z in localfactors]
        # Now take logs to figure out what power these are
        mypi = RealField(100)(pi)
        localfactors = [charf*log(z)/(2*I*mypi) for z in localfactors]
        localfactorsa = [z.real().round() % charf for z in localfactors]
        # Test to see if we are ok?
        localfactorsa = [localfactorsa[j] if bad[j]>0 else -1 for j in range(len(localfactorsa))]
        def myfunc(inp, n):
            fn = list(factor(inp))
            pvals = [[localfactorsa[self.any_prime_to_cc_index(z[0])-1], z[1]] for z in fn]
            # -1 is the marker that the prime divides the conductor
            for j in range(len(pvals)):
                if pvals[j][0] < 0:
                    return -1
            pvals = sum([z[0]*z[1] for z in pvals])
            return (pvals % n)
        return myfunc

    def central_character_as_artin_rep(self):
        """
          Returns the central character, i.e., determinant character
          as a web character, but as an Artin representation
        """
        if self.dimension() == 1:
            return self
        if 'central_character_as_artin_rep' in self._data:
            return self._data['central_character_as_artin_rep']
        myfunc = self.central_char_function()
        # Get the Artin field
        nfgg = self.number_field_galois_group()
        # Get its artin reps
        arts = nfgg.ArtinReps()
        # Filter for 1-dim
        arts = [a for a in arts if ArtinRepresentation(str(a['Baselabel'])+"c1").dimension()==1]
        artfull = [ArtinRepresentation(str(a['Baselabel'])+"c"+str(a['GalConj'])) for a in arts]
        # hold = artfull
        # Loop as we evaluate at primes until there is only one left
        # Fix the return value to be what we want
        artfull = [[a, a.central_char_function(),2*a.character_field()] for a in artfull]
        n = 2*self.character_field()
        p = 2
        disc = nfgg.discriminant()
        while len(artfull)>1:
            if (disc % p) != 0:
              k=0
              while k<len(artfull):
                  if n*artfull[k][1](p,artfull[k][2]) == artfull[k][2]*myfunc(p,n):
                      k += 1
                  else:
                      # Quick deletion of k-th term
                      artfull[k] = artfull[-1]
                      del artfull[-1]
            p = next_prime(p)
        self._data['central_character_as_artin_rep'] = artfull[0][0]
        return artfull[0][0]

    def central_character(self):
        """
          Returns the central character, i.e., determinant character
          as a web character.
        """
        if 'central_character' in self._data:
            return self._data['central_character']
        # Build it as a python function, id it, make a lmfdb character
        # But, if the conductor is too large, this can stall because
        # the function has to factor arbitrary integers modulo N
        if Integer(self.conductor()) > 10**40:
            return None

        myfunc = self.central_char_function()
        wc = id_dirichlet(myfunc, self.conductor(), 2*self.character_field())
        wc = WebSmallDirichletCharacter(modulus=wc[0], number=wc[1])
        self._data['central_character'] = wc
        return wc

    def det_display(self):
        cc= self.central_character()
        if cc is None:
            return 'Not available'
        if cc.order == 2:
            return cc.symbol
        return cc.texname

    def det_as_artin_display(self):
        return self.central_character_as_artin_rep().label()

    def det_url(self):
        cc= self.central_character()
        if cc is None:
           return 'Not available'
        return url_for("characters.render_Dirichletwebpage", modulus=cc.modulus, number=cc.number)

    def central_char_old(self, p):
        """
          Returns the value of the central character at p.
          Test with is_bad_prime(p) or YMMV
        """
        eulerp = self.local_factors_table()[self.any_prime_to_cc_index(p)-1]
        eulerp = self.euler_polynomial(p)
        if eulerp.degree() < self.dimension():
            return 0
        return eulerp.leading_coefficient()

    def euler_polynomial(self, p):
        """
            Returns the polynomial at the prime p in the Euler product. Output is as a list of length the degree (or more), with first coefficient the independent term.
        """
        return self.local_factor(p)

    def coefficients_list(self, upperbound=100):
        from lmfdb.utils import an_list
        return an_list(lambda p: self.euler_polynomial(p), upperbound=upperbound, base_field=ComplexField())

    def character(self):
        return CharacterValues(self._data["Character"])

    def character_formatted(self):
        char_vals = self.character()
        charfield = int(self.character_field())
        zet = CyclotomicField(charfield).gen()
        s = [sum([y[j] * zet**j for j in range(len(y))])._latex_() for y in char_vals]
        return s

    def parity(self):
        par = (self.dimension()-self.trace_complex_conjugation())/2
        if (par % 2) == 0: return "Even"
        return "Odd"
        #return (-1)**par

    def field_knowl(self):
        from lmfdb.WebNumberField import nf_display_knowl
        nfgg = self.number_field_galois_group()
        if nfgg.url_for():
            return nf_display_knowl(nfgg.label(), nfgg.polredabshtml())
        else:
            return nfgg.polredabshtml()

    def group(self):
        return group_display_short(self._data['Galn'],self._data['Galt'])

    def pretty_galois_knowl(self):
        return group_display_knowl(self._data['Galn'],self._data['Galt'])

    def __str__(self):
        try:
            return "An Artin representation of conductor " +\
                str(self.conductor()) + " and dimension " + str(self.dimension())
            #+", "+str(self.index())
        except:
            return "An Artin representation"

    def title(self):
        try:
            return "An Artin representation of conductor $" +\
                str(self.conductor()) + "$ and dimension $" + str(self.dimension()) + "$"
        except:
            return "An Artin representation"

    def url_for(self):
        return url_for("artin_representations.render_artin_representation_webpage", label=self.label())

    def langlands(self):
        """
            Tim:    conjectured always true,
                    known in dimension 1,
                    most cases in dimension 2
        """
        return True

    def sign(self):
        return self.root_number()

    def root_number(self):
        return int(self._data["Sign"])

    def processed_root_number(self):
        tmp = self.root_number()
        if tmp == 0:
            return "?"
        else:
            return str(tmp)

    def trace_complex_conjugation(self):
        """ Computes the trace of complex conjugation, and returns an int
        """
        tmp = (self.character()[self.number_field_galois_group().index_complex_conjugation() - 1])
        try:
            assert len(tmp) == 1
            trace_complex = tmp[0]
        except AssertionError:
        # We are looking for the character value on the conjugacy class of complex conjugation.
        # This is always an integer, so we don't expect this to be a more general
        # algebraic integer, and we can simply convert to sage
            raise TypeError, "Expecting a character values that converts easily to integers, but that's not the case: %s" % tmp
        return trace_complex

    def number_of_eigenvalues_plus_one_complex_conjugation(self):
        return int(Integer(self.dimension() + self.trace_complex_conjugation()) / 2)

    def number_of_eigenvalues_minus_one_complex_conjugation(self):
        return int(Integer(self.dimension() - self.trace_complex_conjugation()) / 2)

    def kappa_fe(self):
        return [Integer(1) / 2 for i in range(self.dimension())]
        # this becomes gamma[1] in lcalc.lcalc_Lfunction._print_data_to_standard_output

    def lambda_fe(self):
        return [0 for i in range(self.number_of_eigenvalues_plus_one_complex_conjugation())] + \
            [Integer(
             1) / 2 for i in range(self.number_of_eigenvalues_minus_one_complex_conjugation())]
        # this becomes lambda[1] in lcalc.lcalc_Lfunction._print_data_to_standard_output

    def primitive(self):
        return True

    def mu_fe(self):
        return [0 for i in range(self.number_of_eigenvalues_plus_one_complex_conjugation())] + \
            [1 for i in range(self.number_of_eigenvalues_minus_one_complex_conjugation())]

    def nu_fe(self):
        return []

    def poles(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() == 1:
            return [1]
        return []

    def completed_poles(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() == 1:
            return [0, 1]
        return []

    def completed_residues(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() == 1:
            return [-1, 1]
        return []

    def residues(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() == 1:
            return [1]
        return []

    def local_factors_table(self):
        return self._data["LocalFactors"]

    def from_conjugacy_class_index_to_polynomial(self, index):
        """ A function converting from a conjugacy class index (starting at 1) to the local Euler polynomial.
            Saves a sequence of processed polynomials, obtained from the local factors table, so it can reuse computations from prime to prime
            This sequence is indexed by conjugacy class indices (starting at 1, filled with dummy first) and gives the corresponding polynomials in the form
            [coeff_deg_0, coeff_deg_1, ...], where coeff_deg_i is in ComplexField(). This could be changed later, or made parametrizable
        """
        try:
            return self._from_conjugacy_class_index_to_polynomial_fn(index)
        except AttributeError:
            local_factors = self.local_factors_table()
            field = ComplexField()
            root_of_unity = exp((field.gen()) * 2 * field.pi() / int(self.character_field()))
            local_factor_processed_pols = [0]   # dummy to account for the shift in indices
            for pol in local_factors:
                local_factor_processed_pols.append(
                    process_polynomial_over_algebraic_integer(pol, field, root_of_unity))

            def tmp(conjugacy_class_index_start_1):
                return local_factor_processed_pols[conjugacy_class_index_start_1]
            self._from_conjugacy_class_index_to_polynomial_fn = tmp
            return self._from_conjugacy_class_index_to_polynomial_fn(index)

    def hard_factors(self):
        return self._data["HardFactors"]

    def hard_prime_to_conjugacy_class_index(self, p):
        # Index in the conjugacy classes, but starts at 1
        try:
            i = self.hard_primes().index(p)
        except:
            raise IndexError, "Not a 'hard' prime%" % p
        return self.hard_factors()[i]

    def nf(self):
        if not 'nf' in self._data:
            self._data['nf']= self.number_field_galois_group()
        return self._data['nf']

    def hard_factor(self, p):
        return self.from_conjugacy_class_index_to_polynomial(self.hard_prime_to_conjugacy_class_index(p))

    def good_factor(self, p):
        return self.from_conjugacy_class_index_to_polynomial(self.nf().from_prime_to_conjugacy_class_index(p))

    def any_prime_to_cc_index(self, p):
        if self.is_hard_prime(p):
            return self.hard_prime_to_conjugacy_class_index(p)
        else:
            return self.nf().from_prime_to_conjugacy_class_index(p)


    ### if p is good: NumberFieldGaloisGroup.frobenius_cycle_type :     p -> Frob --NF---> cycle type
    ###               NumberFieldGaloisGroup.from_cycle_type_to_conjugacy_class_index : Uses data stored in the number field originally, but allows
    ###                                                                 cycle type ---> conjugacy_class_index
    ###
    # if p is hard:  ArtinRepresentation.hard_prime_to_conjugacy_class_index :
    # p --Artin-> conjugacy_class_index
    # in both cases:
    # ArtinRepresentation.from_conjugacy_class_index_to_polynomial :
    # conjugacy_class_index ---Artin----> local_factor
    def local_factor(self, p):
        if self.is_hard_prime(p):
            return self.hard_factor(p)
        else:
            return self.good_factor(p)

    def Lfunction(self):
        from lfunctions.Lfunction import ArtinLfunction
        return ArtinLfunction(dimension = self.dimension(), conductor = self.conductor(), tim_index = self.index())

    def indicator(self):
        """ The Frobenius-Schur indicator of the Artin L-function. Will be
                +1 if rho is orthogonal,
                -1 if rho is symplectic and
                0 if the character of rho is not defined over the reals, i.e. the representation is not self-dual.
        """
        return self._data["Indicator"]

    def self_dual(self):
        if self.indicator() == 0:
            return False
        else:
            return True

    def selfdual(self):
        return self.self_dual()


class CharacterValues(list):
    def display(self):
        # The character values can be large, do not convert to int!
        return "[" + ",".join([x.latex() for x in self]) + "]"


class ConjugacyClass(object):
    def __init__(self, G, data):
        self._G = G
        self._data = data

    def group(self):
        return self._G

    def size(self):
        return self._data["Size"]

    def order(self):
        return self._data["Order"]

    def representative(self):
        return self._data["Representative"]

    def __str__(self):
        try:
            return "A conjugacy class in the group %s, of order %s and with representative %s" % (self._G, self.order(), self.representative())
        except:
            return "A conjugacy class"


class G_gens(list):
    def display(self):
        return self


class NumberFieldGaloisGroup(object):
    def __init__(self, *x, **data_dict):
        if len(x) == 0:
            # Just passing named arguments
            self._data = data_dict["data"]
        elif len(x) > 1:
            raise ValueError("Only one positional argument allowed")
        else:
            if isinstance(x[0], basestring):
                if x[0]:
                    coeffs = x[0].split(',')
                else:
                    coeffs = []
            else:
                coeffs = x[0]
            coeffs = [int(c) for c in coeffs]
            self._data = db.artin_field_data.convert_lucky({'Polynomial':coeffs})
            if self._data is None:
                # This should probably be a ValueError, but we use an AttributeError for backward compatibility
                raise AttributeError("No Galois group data for polynonial %s"%(coeffs))

    @classmethod
    def search(cls, query={}, projection=1, limit=None, offset=0, sort=None, info=None):
        results = db.artin_field_data.search_and_convert(query, projection, limit=limit, offset=offset, sort=sort, info=info)
        if limit is None:
            return _search_and_convert_iterator(cls, results)
        else:
            return [cls(data=x) for x in results]

    @classmethod
    def lucky(cls, *args, **kwds):
        result = db.artin_field_data.convert_lucky(*args, **kwds)
        if result is not None:
            return cls(data=result)

    def degree(self):
        return self._data["TransitiveDegree"]

    def polynomial(self):
        return PolynomialAsSequenceTooLargeInt(self._data["Polynomial"])

    def polynomial_latex(self):
	from sage.rings.all import PolynomialRing, QQ
	PP = PolynomialRing(QQ, 'x')
    	return PP(self.polynomial())._latex_()

    # WebNumberField of the object
    def wnf(self):
        return WebNumberField.from_polredabs(self.polredabs())

    def polredabs(self):
        # polynomials are all polredabs'ed now
        return PolynomialRing(QQ, 'x')(map(str,self.polynomial()))
        #if "polredabs" in self._data.keys():
        #    return self._data["polredabs"]
        #else:
        #    pol = PolynomialRing(QQ, 'x')(map(str,self.polynomial()))
        #    # Need to map because the coefficients are given as unicode, which does not convert to QQ
        #    pol *= pol.denominator()
        #    R = pol.parent()
        #    from sage.all import pari
        #    pol = R(pari(pol).polredabs())
        #    self._data["polredabs"] = pol
        #    return pol

    def polredabslatex(self):
        return self.polredabs()._latex_()

    def polredabshtml(self):
        return pol_to_html(self.polredabs())

    def label(self):
        if "label" in self._data.keys():
            return self._data["label"]
        else:
            #from number_fields.number_field import poly_to_field_label
            #pol = PolynomialRing(QQ, 'x')(map(str,self.polynomial()))
            #label = poly_to_field_label(pol)
            label = WebNumberField.from_coeffs(self._data["Polynomial"]).get_label()
            if label:
                self._data["label"] = label
            return label

    def url_for(self):
        if self.label():
            return url_for("number_fields.by_label", label=self.label())
        else:
            None

    def size(self):
        return self._data["Size"]

    def G_gens(self):
        """
        Generators of the Galois group
        """
        return G_gens(self._data["G-Gens"])

    def G_name(self):
        """
        More-or-less standardized name of the abstract group
        """
        import re
        wnf = WebNumberField.from_polredabs(self.polredabs())
        if not wnf.is_null():
            mygalstring = wnf.galois_string()
            if re.search('Trivial', mygalstring) is not None:
                return '$C_1$'
            # Have to remove dollar signs
            return mygalstring
        if self.polredabs().degree() < 12:
            # Let pari compute it for us now
            from sage.all import pari
            galt = int(list(pari('polgalois(' + str(self.polredabs()) + ')'))[2])
            from lmfdb.transitive_group import WebGaloisGroup
            tg = WebGaloisGroup.from_nt(self.polredabs().degree(), galt)
            return tg.display_short()
        return self._data["G-Name"]

    def computation_data(self):
        return tuple([self._data[k] for k in ["QpRts-p", "QpRts-minpoly", "QpRts-prec", "QpRts"]])

    def residue_characteristic(self):
        return self._data["QpRts-p"]

    def computation_precision(self):
        return self._data["QpRts-prec"]

    def computation_minimal_polynomial(self):
        return self._data["QpRts-minpoly"]

    def computation_roots(self):
        return [x for x in self._data["QpRts"]]

    def index_complex_conjugation(self):
        # This is an index starting at 1
        return self._data["ComplexConjugation"]

    # def Frobenius_fn(self):
    #    try:
    #        return self._Frobenius
    #    except:
    #        tmp = self._data["Frobs"]

    def Frobenius_resolvents(self):
        return self._data["FrobResolvents"]

    def conjugacy_classes(self):
        return [ConjugacyClass(self.G_name(), item) for item in self._data["ConjClasses"]]

    def ArtinReps(self):
        return self._data["ArtinReps"] # list of dictionaries

    def artin_representations_full_characters(self):
        return [[z['Character'],z['CharacterField']] for z in self.ArtinReps()]

    def artin_representations(self):
        return [ArtinRepresentation(z['Baselabel'],z['GalConj']) for z in self.ArtinReps()]

    def discriminant(self):
        return self.sage_object().discriminant()

    def sage_object(self):
        X = PolynomialRing(QQ, "x")
        from sage.rings.number_field.number_field import NumberField
        return NumberField(X(map(str,self.polynomial())), "x")

    def from_cycle_type_to_conjugacy_class_index(self, cycle_type, p):
        try:
            dict_to_use = self._from_cycle_type_to_conjugacy_class_index_dict
        except AttributeError:
            import cyc_alt_res_engine
            self._from_cycle_type_to_conjugacy_class_index_dict = cyc_alt_res_engine.from_cycle_type_to_conjugacy_class_index_dict(map(str,self.polynomial()), self.Frobenius_resolvents())
            # self._from_cycle_type_to_conjugacy_class_index_dict is now a dictionary with keys the the cycle types (as tuples),
            # and values functions of the prime that output the conjugacy class index (using different methods depending on local information)
            # cyc_alt_res_engine.from_cycle_type_to_conjugacy_class_index_dict constructs this dictionary,
            # and only needs to know the defining polynomial of the number field and the frobenius resolvent
            # CAUTION: this is not meant to be used for hard primes, even though it would seemingly work
            # This is a consequence of Tim's definition of hard primes.
            dict_to_use = self._from_cycle_type_to_conjugacy_class_index_dict
        try:
            fn_to_use = dict_to_use[cycle_type]
        except KeyError:
            raise KeyError, "Expecting to find key %s, whose entries have type %s, in %s. For info, keys there have entries of type %s" % \
                (cycle_type, type(cycle_type[0]), self._from_cycle_type_to_conjugacy_class_index_dict,
                 type(self._from_cycle_type_to_conjugacy_class_index_dict.keys()[0][0]))
        return fn_to_use(p)

    def from_prime_to_conjugacy_class_index(self, p):
        return self.from_cycle_type_to_conjugacy_class_index(self.frobenius_cycle_type(p), p)

    def frobenius_cycle_type(self, p):
        try:
            assert not self.discriminant() % p == 0
        except:
            raise AssertionError, "Expecting a prime not dividing the discriminant", p
        return tuple(self.residue_field_degrees(p))
        # tuple allows me to use this for indexing of a dictionary

    # def increasing_frobenius_cycle_type(self, p):
    #    try:
    #        assert not self.discriminant() % p == 0
    #    except:
    #        raise AssertionError, "Expecting a prime not dividing the discriminant", p
    #    return tuple(sorted(self.residue_field_degrees(p), reverse = True))
    def residue_field_degrees(self, p):
        """ This function returns the residue field degrees at p.
        """
        try:
            return self._residue_field_degrees(p)
        except AttributeError:
            # Try to make WebNumberField, but only helps if the field is in our database
            wnf = self.wnf()
            if wnf._data is None:
                from lmfdb.number_fields.number_field import sage_residue_field_degrees_function
                fn_with_pari_output = sage_residue_field_degrees_function(self.sage_object())
            else:
                from lmfdb.number_fields.number_field import residue_field_degrees_function
                fn_with_pari_output = residue_field_degrees_function(wnf)
            self._residue_field_degrees = lambda p: map(Integer, fn_with_pari_output(p))
            # This function is better, becuase its output has entries in Integer
            return self._residue_field_degrees(p)

    def __str__(self):
        try:
            tmp = "The Galois group of the number field  Q[x]/(%s)" % map(str,self.polynomial())
        except:
            tmp = "The Galois group of a number field"
        return tmp

    def display_title(self):
        return "The Galois group of the number field $\mathbb{Q}[x]/(%s)" % self.polynomial().latex() + "$"
