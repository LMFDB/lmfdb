# -*- coding: utf-8 -*-

from base import getDBConnection, app
from utils import url_for, pol_to_html
from databases.Dokchitser_databases import Dokchitser_ArtinRepresentation_Collection, Dokchitser_NumberFieldGaloisGroup_Collection
from sage.all import PolynomialRing, QQ, ComplexField, exp, pi, Integer, valuation, CyclotomicField
from lmfdb.transitive_group import group_display_knowl, group_display_short


def process_algebraic_integer(seq, root_of_unity):
    return sum(Integer(seq[i]) * root_of_unity ** i for i in range(len(seq)))

def process_polynomial_over_algebraic_integer(seq, field, root_of_unity):
    from sage.rings.all import PolynomialRing
    PP = PolynomialRing(field, "x")
    return PP([process_algebraic_integer(x, root_of_unity) for x in seq])

class ArtinRepresentation(object):
    @staticmethod
    def collection(source="Dokchitser"):
        if source == "Dokchitser":
            return Dokchitser_ArtinRepresentation_Collection(getDBConnection())

    def __init__(self, *x, **data_dict):
        if len(x) == 0:
            # Just passing named arguments
            self._data = data_dict["data"]
        else:
            self._data = self.__class__.collection(
            ).find_and_convert_one(Dim=int(x[0]), Conductor=str(x[1]), DBIndex=int(x[2]))

    @classmethod
    def find(cls, *x, **y):
        for item in cls.collection().find_and_convert(*x, **y):
            yield ArtinRepresentation(data=item)

    @classmethod
    def find_one(cls, *x, **y):
        return ArtinRepresentation(data=cls.collection().find_and_convert_one(*x, **y))

    def dimension(self):
        return self._data["Dim"]

    def conductor(self):
        return self._data["Conductor"]

    def conductor_equation(self):
        # Returns things of the type "1", "7", "49 = 7^{2}"
        factors = self.factored_conductor()
        if str(self.conductor()) == "1":
            return "1"
        if len(factors) == 1 and factors[0][1] == 1:
            return str(self.conductor())
        else:
            return str(self.conductor()) + "=" + self.factored_conductor_latex()

    def factored_conductor(self):
        return [(p, valuation(Integer(self.conductor()), p)) for p in self.bad_primes()]

    def factored_conductor_latex(self):
        if int(self.conductor()) == 1:
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

    def index(self):
        return self._data["DBIndex"]

    def galois_orbit_label(self):
        return self._data["galorbit"]

    def number_field_galois_group(self):
        try:
            return self._nf
        except AttributeError:
            tmp = self._data["NFGal"]
            query = {"TransitiveDegree": int(tmp[0]), "Size": str(tmp[1]), "DBIndex": int(tmp[2])}
            self._nf = NumberFieldGaloisGroup.find_one(query)
        return self._nf

    def is_ramified(self, p):
        return self.number_field_galois_group().discriminant() % p == 0

    def euler_polynomial(self, p):
        """
            Returns the polynomial at the prime p in the Euler product. Output is as a list of length the degree (or more), with first coefficient the independent term.
        """
        return self.local_factor(p)

    def coefficients_list(self, upperbound=100):
        from sage.rings.all import RationalField
        from utils import an_list
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
        from WebNumberField import nf_display_knowl
        nfgg = self.number_field_galois_group()
        if nfgg.url_for():
            return nf_display_knowl(nfgg.label(), getDBConnection(), nfgg.polredabshtml())
        else:
            return nfgg.polredabshtml()

    def group(self):
        return group_display_short(self._data['Galois_nt'][0],self._data['Galois_nt'][1], getDBConnection())

    def pretty_galois_knowl(self):
        C = getDBConnection()
        return group_display_knowl(self._data['Galois_nt'][0],self._data['Galois_nt'][1],C)

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
        return url_for("artin_representations.by_data", dim=self.dimension(), conductor=self.conductor(), index=self.index())

    def langlands(self):
        """
            Tim:    conjectured always true,
                    known in dimension 1,
                    most cases in dimension 2
        """
        return True

    def sign(self):
        print "ArtinRepresentation.sign now deprecated, use root_number instead"
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
        if int(self.conductor()) == 1 and int(self.dimension()) == 1:
            return [1]
        return []

    def completed_poles(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if int(self.conductor()) == 1 and int(self.dimension()) == 1:
            return [0, 1]
        return []

    def completed_residues(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if int(self.conductor()) == 1 and int(self.dimension()) == 1:
            return [-1, 1]
        return []

    def poles(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if int(self.conductor()) == 1 and int(self.dimension()) == 1:
            return [1]
        return []

    def residues(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if int(self.conductor()) == 1 and int(self.dimension()) == 1:
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
            from sage.rings.all import RealField, ComplexField
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
        return self.number_field_galois_group()

    def hard_factor(self, p):
        return self.from_conjugacy_class_index_to_polynomial(self.hard_prime_to_conjugacy_class_index(p))

    def good_factor(self, p):
        return self.from_conjugacy_class_index_to_polynomial(self.nf().from_prime_to_conjugacy_class_index(p))

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
            return "A conjugacy class in the group %s, of order %s and with representative %s" % (G, self.order(), self.representative())
        except:
            return "A conjugacy class"


class G_gens(list):
    def display(self):
        return self


class NumberFieldGaloisGroup(object):
    @staticmethod
    def collection(source="Dokchitser"):
        if source == "Dokchitser":
            tmp = Dokchitser_NumberFieldGaloisGroup_Collection(getDBConnection())
            return tmp

    def __init__(self, *x, **data_dict):
        self._data = data_dict["data"]

    @classmethod
    def find_one(cls, *x, **y):
        return NumberFieldGaloisGroup(data=cls.collection().find_and_convert_one(*x, **y))

    @classmethod
    def find(cls, *x, **y):
        for item in cls.collection().find_and_convert(*x, **y):
            yield NumberFieldGaloisGroup(data=item)

    def degree(self):
        return self._data["TransitiveDegree"]

    def polynomial(self):
        return self._data["Polynomial"]

    def polredabs(self):
        if "polredabs" in self._data.keys():
            return self._data["polredabs"]
        else:
            pol = PolynomialRing(QQ, 'x')(map(str,self.polynomial()))
            # Need to map because the coefficients are given as unicode, which does not convert to QQ
            pol *= pol.denominator()
            R = pol.parent()
            from sage.all import pari
            pol = R(pari(pol).polredabs())
            self._data["polredabs"] = pol
            return pol

    def polredabslatex(self):
        return self.polredabs()._latex_()

    def polredabshtml(self):
        return pol_to_html(self.polredabs())

    def label(self):
        if "label" in self._data.keys():
            return self._data["label"]
        else:
            from number_fields.number_field import poly_to_field_label
            pol = PolynomialRing(QQ, 'x')(map(str,self.polynomial()))
            label = poly_to_field_label(pol)
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

    def index(self):
        """
        The index in the database among entries with the same degree and group.
        """
        return self._data["DBIndex"]

    def G_gens(self):
        """
        Generators of the Galois group
        """
        return G_gens(self._data["G-Gens"])

    def G_name(self):
        """
        More-or-less standardized name of the abstract group
        """
        from WebNumberField import WebNumberField
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
            from transitive_group import WebGaloisGroup
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

    def artin_representations(self):
        x = [ArtinRepresentation.find_one({"Dim": item["Dim"], "Conductor":str(item["Conductor"]), "DBIndex":item["DBIndex"]})
             for item in self._data["ArtinReps"]]
        return x

    def ArtinReps(self):
        return self._data["ArtinReps"]

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
            from number_fields.number_field import residue_field_degrees_function
            fn_with_pari_output = residue_field_degrees_function(self.sage_object())
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
