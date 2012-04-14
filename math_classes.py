# -*- coding: utf-8 -*-

from base import getDBConnection, app
from utils import url_for
from databases.Dokchitser_databases import Dokchitser_ArtinRepresentation_Collection, Dokchitser_NumberFieldGaloisGroup_Collection
from sage.all import PolynomialRing, QQ, ComplexField, exp, pi

def process_algebraic_integer(seq, root_of_unity):
    return sum(seq[i] * root_of_unity**i for i in range(len(seq)))

def process_polynomial_over_algebraic_integer(seq, field, root_of_unity):
    from sage.rings.all import PolynomialRing
    PP = PolynomialRing(field, "x")
    return PP([process_algebraic_integer(x, root_of_unity) for x in seq])

class ArtinRepresentation(object):
    @staticmethod
    def collection(source = "Dokchitser"):
        if source == "Dokchitser":
            return Dokchitser_ArtinRepresentation_Collection(getDBConnection())
    
    def __init__(self, *x, **data_dict):
        if len(x) == 0:
            # Just passing named arguments
            self._data = data_dict["data"]
        else:
            self._data = self.__class__.collection().find_and_convert_one(Dim = int(x[0]), Conductor = str(x[1]), DBIndex = int(x[2]))

    @classmethod
    def find(cls, *x, **y):
        for item in cls.collection().find_and_convert(*x, **y):
            yield ArtinRepresentation(data = item)
    
    @classmethod
    def find_one(cls, *x, **y):
        return ArtinRepresentation(data = cls.collection().find_and_convert_one(*x, **y))    
    
    def dimension(self):
        return self._data["Dim"]
    
    def conductor(self):
        return self._data["Conductor"]
    
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
        
    def number_field_galois_group(self):
        try:
            return self._nf
        except AttributeError:
            tmp = self._data["NFGal"]
            query = {"TransitiveDegree" : int(tmp[0]), "Size" : str(tmp[1]), "DBIndex": int(tmp[2])}
            self._nf = NumberFieldGaloisGroup.find_one(query)
        return self._nf
            
    def is_ramified(self, p):
        return self.number_field_galois_group().discriminant() % p == 0
    
    def euler_polynomial(self,p):
        """
            Returns the polynomial at the prime p in the Euler product. Output is as a list of length the degree (or more), with first coefficient the independent term.
        """
        return self.local_factor(p)
        
    def coefficients_list(self, upperbound = 100):
        from sage.rings.all import RationalField
        from utils import an_list
        return an_list(lambda p: self.euler_polynomial(p), upperbound = upperbound, base_field = ComplexField())

    def character(self):
        return CharacterValues(self._data["Character"])
    
    def __str__(self):
        try:
            return "An Artin representation of conductor "+\
                    str(self.conductor())+" and dimension "+str(self.dimension())
            #+", "+str(self.index())
        except:
            return "An Artin representation"

    def title(self):
        try:
            return "An Artin representation of conductor $"+\
                    str(self.conductor())+"$ and dimension $"+str(self.dimension())+"$"
        except:
            return "An Artin representation"
    
    def url_for(self):
        return url_for("artin_representations.by_data", dim = self.dimension(), conductor = self.conductor(), index = self.index())
        
    def langlands(self):
        """
            Tim:    conjectured always true,
                    known in dimension 1,
                    most cases in dimension 2
        """
        return True

    def sign(self):
        try:
            return int(self._data["Sign"])
        except KeyError:
            return "?"      # Could try to implement guessing of the sign
    
    def trace_complex_conjugation(self):
        """ Computes the trace of complex conjugation, and returns an int
        """
        tmp = (self.character()[self.number_field_galois_group().index_complex_conjugation()-1])
        try:
            assert len(tmp) == 1
            trace_complex = tmp[0]  
        except AssertionError:            
        # We are looking for the character value on the conjugacy class of complex conjugation.
        # This is always an integer, so we don't expect this to be a more general algebraic integer, and we can simply convert to sage
            raise TypeError, "Expecting a character values that converts easily to integers, but that's not the case: %s"% tmp
        return trace_complex
    
    def number_of_eigenvalues_plus_one_complex_conjugation(self):
        return int((self.dimension() + self.trace_complex_conjugation())/2)
    
    def number_of_eigenvalues_minus_one_complex_conjugation(self):
        return int((self.dimension() - self.trace_complex_conjugation())/2)
        
    def kappa_fe(self):
        return [1/2 for i in range(self.dimension())]
    
    def lambda_fe(self):
        return [0 for i in range(self.number_of_eigenvalues_plus_one_complex_conjugation())] + \
                    [1/2 for i in range(self.number_of_eigenvalues_minus_one_complex_conjugation())]
    
    def primitive(self):
        return True

    def mu_fe(self):
        return [0 for i in range(self.number_of_eigenvalues_plus_one_complex_conjugation())] + \
                    [1 for i in range(self.number_of_eigenvalues_minus_one_complex_conjugation())]
        
    def nu_fe(self):
        return []
    
    def self_dual(self):
        return "?"
        raise NotImplementedError
    
    def selfdual(self):
        return self.self_dual()
    
    def poles(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() == 1:
            return [1]
        return []
    
    def residues(self):
        try:
            assert self.primitive()
        except AssertionError:
            raise NotImplementedError
        if self.conductor() == 1 and self.dimension() ==1:
            return [1]
        return []
    
    def local_factors_table(self):
        return self._data["LocalFactors"]
    
    
    def from_conjugacy_class_index_to_polynomial_fn(self):
        """ This is in the good case
        """
        try:
            return self._from_conjugacy_class_index_to_polynomial_fn
        except AttributeError:
            # Returns an index starting a 1
            local_factors = self.local_factors_table()
            def tmp(conjugacy_class_index_start_1):
                pol = local_factors[conjugacy_class_index_start_1-1]
                # We now have an array of arrays, because we have a polynomial over algebraic integers
                from sage.rings.all import RealField, ComplexField
                field = ComplexField()
                root_of_unity = exp(2*field.pi()/int(self.character_field()))
                pol2 = process_polynomial_over_algebraic_integer(pol, field, root_of_unity)
                return pol2
            self._from_conjugacy_class_index_to_polynomial_fn = tmp 
            return self._from_conjugacy_class_index_to_polynomial_fn
    
    def bad_factors(self):
        return self._data["BadFactors"]
    
    def bad_factor(self, p):
        factor_double_pol = self.from_conjugacy_class_index_to_polynomial_fn()(self.bad_factor_index(p))
        # We get a polynomial over algebraic integers
        field = ComplexField()
        return factor_double_pol
        
    def bad_factor_index(self, p):
        # Index in the conjugacy classes, but starts at 1
        try:
            i = self.bad_primes().index(p)
        except:
            raise IndexError, "Not a bad prime%"%p
        return self.bad_factors()[i]
        
    def from_cycle_type_to_conjugacy_class_index(self, cycle_type):
        # Needs data stored in the number field
        try:
            return self._from_cycle_type_to_conjugacy_class_index_fn(cycle_type)
        except AttributeError:
            self._from_cycle_type_to_conjugacy_class_index_fn = self.number_field_galois_group().from_cycle_type_to_conjugacy_class_index_fn()
            return self._from_cycle_type_to_conjugacy_class_index_fn(cycle_type)
    
    def nf(self):
        return self.number_field_galois_group()
        
    
    def from_prime_to_conjugacy_class_index(self, p):
        cycle_type = self.nf().frobenius_cycle_type(p)
        conjugacy_class_index = self.from_cycle_type_to_conjugacy_class_index(cycle_type)
        return conjugacy_class_index
    
    def good_factor(self, p):
        return self.from_conjugacy_class_index_to_polynomial_fn()(self.from_prime_to_conjugacy_class_index(p))
        

    ### if p is good: NumberFieldGaloisGroup.frobenius_cycle_type :     p -> Frob --NF---> cycle type
    ###               ArtinRepresentation.from_cycle_type_to_conjugacy_class_index : Uses data stored in the number field originally, but allows
    ###                                                                 cycle type ---> conjugacy_class_index
    ###               
    ###               ArtinRepresentation.from_conjugacy_class_index_to_polynomial : conjugacy_class_index ---Artin----> local_factor
    ### if p is bad:  ArtinRepresentation.bad_factor :                  p --Artin-> bad_factor 
    
    def local_factor(self, p):
        if self.is_bad_prime(p):
            return self.bad_factor(p)
        else:
            return self.good_factor(p)
        
    def Lfunction(self):
        from Lfunction import ArtinLfunction
        return ArtinLfunction(self.dimension(), self.conductor(), self.index())

    
class CharacterValues(list):
    def display(self):
        # The character values can be large, do not convert to int!
        return "["+",".join([x.latex() for x in self])+"]"
    
class ConjugacyClass(object):
    def __init__(self,G,data):
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
            return "A conjugacy class in the group %s, of order %s and with representative %s"%(G,self.order(),self.representative())
        except:
            return "A conjugacy class"
        
    

class G_gens(list):
    def display(self):
        return self
        
class NumberFieldGaloisGroup(object):
    @staticmethod
    def collection(source = "Dokchitser"):
        if source == "Dokchitser":
            tmp = Dokchitser_NumberFieldGaloisGroup_Collection(getDBConnection())
            return tmp
            
    
    def __init__(self, *x, **data_dict):
        self._data = data_dict["data"]
            
    @classmethod
    def find_one(cls, *x, **y):
        return NumberFieldGaloisGroup(data = cls.collection().find_and_convert_one(*x, **y))    
    
    @classmethod
    def find(cls, *x, **y):
        for item in cls.collection().find_and_convert(*x, **y):
            yield NumberFieldGaloisGroup(data = item)
    
    def degree(self):
        return self._data["TransitiveDegree"]
    
    def polynomial(self):
        return self._data["Polynomial"]
                
    def polredabs(self):
        if "polredabs" in self._data.keys():
            return self._data["polredabs"]
        else:
            pol = PolynomialRing(QQ,'x')(self.polynomial())
            pol *= pol.denominator()
            R = pol.parent()
            from sage.all import pari
            pol = R(pari(pol).polredabs())
            self._data["polredabs"] = pol
            return pol
    
    def label(self):
        if "label" in self._data.keys():
            return self._data["label"]
        else:
            from number_fields.number_field import poly_to_field_label
            pol = PolynomialRing(QQ,'x')(self.polynomial())
            label =  poly_to_field_label(pol)
            if label:
                self._data["label"] = label
            return label
    
    def url_for(self):
        if self.label():
            return url_for("number_fields.by_label", label = self.label())
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
        Standardized name of the abstract group
        """
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
        tmp =  [str(x)  for x in self._data["QpRts"]]
        return tmp
        
    def index_complex_conjugation(self):
        # This is an index starting at 1
        return self._data["ComplexConjugation"]
        
    def Frobenius_fn(self):
        try:
            return self._Frobenius
        except:
            tmp = self._data["Frobs"]

    def Frobenius_resolvents(self):
        return self._data["FrobResolvents"]
        
    def conjugacy_classes(self):
        return [ConjugacyClass(self.G_name(),item) for item in self._data["ConjClasses"]]
    
    def artin_representations(self):
        x = [ArtinRepresentation.find_one({"Dim":item["Dim"], "Conductor":str(item["Conductor"]), "DBIndex":item["DBIndex"]})\
                for item in self._data["ArtinReps"]]
        return x
        
    def discriminant(self):
        return self.sage_object().discriminant()
        
    def sage_object(self):
        X = PolynomialRing(QQ,"x")
        from sage.rings.number_field.number_field import NumberField
        return NumberField(X(self.polynomial()),"x")
    
    def from_cycle_type_to_conjugacy_class_index_fn(self):
        try:
            return self._from_cycle_type_to_conjugacy_class_index
        except AttributeError:
            # Returns an index starting a 1
            resolvents = self.Frobenius_resolvents()
            # Slow below
            def tmp(cycle_type):
                try:
                    return [d for d in resolvents if d["CycleType"] == cycle_type and d["Algorithm"] == "CYC"][0]["Classes"]
                    # Simplest case. If the entry has a "CYC", then it also has a "Classes" entry
                except IndexError:
                    raise NotImplementedError, "At the moment we assume it is of type 'CYC'"
            self._from_cycle_type_to_conjugacy_class_index = tmp
            return tmp

        
    def frobenius_cycle_type(self, p):
        try:
            assert not self.discriminant() % p == 0
        except:
            raise AssertionError, "Expecting a prime not dividing the discriminant", p
        return self.residue_field_degrees(p)

    
    def increasing_frobenius_cycle_type(self, p):
        return sorted(self.frobenius_cycle_type(p), reverse = True)
        
    def residue_field_degrees(self, p):
        """ This function returns the residue field degrees at p.
        """
        try:
            return self._residue_field_degrees(p)
        except AttributeError:
            from number_fields.number_field import residue_field_degrees_function
            self._residue_field_degrees = residue_field_degrees_function(self.sage_object())
            return self._residue_field_degrees(p)
        
    
    
    
    def __str__(self):
        try:
            tmp = "The Galois group of the number field  Q[x]/(%s)"%self.polynomial()
        except:
            tmp = "The Galois group of a number field"
        return tmp
    
    def display_title(self):
        return "The Galois group of the number field $\mathbb{Q}[x]/(%s)"%self.polynomial().latex()+"$"
    
