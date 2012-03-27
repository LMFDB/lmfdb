# -*- coding: utf-8 -*-

from base import getDBConnection, app
from utils import url_for
from databases.Dokchitser_databases import Dokchitser_ArtinRepresentation_Collection, Dokchitser_NumberFieldGaloisGroup_Collection
from sage.all import PolynomialRing, QQ

class ArtinRepresentation(object):
    @staticmethod
    def collection(source = "Dokchitser"):
        if source == "Dokchitser":
            return Dokchitser_ArtinRepresentation_Collection(getDBConnection())
    
    def __init__(self, *x, **data_dict):
        if len(x) == 0:
            self._data = data_dict["data"]
        else:
            self = ArtinRepresentation.find_one({"Dimension":x[0],"Conductor":str(x[1]),"DBIndex":x[2]})
        
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
    
    def index(self):
        return self._data["DBIndex"]
    
    def number_field_galois_group(self):
        if not hasattr(self,"_number_field_galois_group"):
            tmp = self._data["NFGal"]
            query = {"Degree" : int(tmp[0]), "Size" : str(tmp[1]), "DBIndex": int(tmp[2])}
            self._number_field_galois_group = NumberFieldGaloisGroup.find_one(query)
        return self._number_field_galois_group

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
        from artin_representations import artin_representations_page
        from artin_representations.main import *
        return url_for("artin_representations.by_data", dim = self.dimension(), conductor = self.conductor(), index = self.index())
        
class CharacterValues(list):
    def display(self):
        # The character values can be large, do not convert to int!
        return "["+",".join([str(x) for x in self])+"]"
    
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
        
class NumberFieldGaloisGroup():
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
        return self._data["Degree"]
    
    def polynomial(self):
        return self._data["Polynomial"]
                
    def polredabs(self):
        if "polredabs" in self._data.keys():
            return self._data["polredabs"]
        else:
            pol=PolynomialRing(QQ,'x')(str(self.polynomial()))
            pol *= pol.denominator()
            R = pol.parent()
            from sage.all import pari
            pol = R(pari(pol).polredabs())
            return pol
    
    def label(self):
        if "label" in self._data.keys():
            return self._data["label"]
        else:
            from number_fields.number_field import poly_to_field_label
            self._data["label"] = poly_to_field_label(self.polynomial())
            return self._data["label"]
    
    def url_for(self):
        from number_fields import nf_page
        from number_fields.number_field import *
        return url_for("number_fields.by_label", label = self.label())        
    
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
        
    def complex_conjugation(self):
        return self._data["ComplexConjugation"]
        
    def Frobenius(self):
        return self._data["Frobs"]

    def Frobenius_resolvents(self):
        return self._data["FrobResolvents"]
        
    def conjugacy_classes(self):
        return [ConjugacyClass(self.G_name(),item) for item in self._data["ConjClasses"]]
    
    def artin_representations(self):
        x = [ArtinRepresentation.find_one(dict([("Dim",item["Degree"]),\
            ("Conductor",str(item["Conductor"])), ("DBIndex",item["Index"])]))\
                for item in self._data["ArtinReps"]]
        return x
        
#    def sage_object(self):
#        from sage import *
#        X = PolynomialRing(QQ,"x")
#        return X(self.polynomial)
    
    def __str__(self):
        try:
            tmp = "The Galois group of the number field  Q[x]/(%s)"%self.polynomial()
        except:
            tmp = "The Galois group of a number field"
        return tmp
    
    def display_title(self):
        return "The Galois group of the number field $\mathbb{Q}[x]/(%s)"%self.polynomial().latex()+"$"
    