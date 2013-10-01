# -*- coding: utf-8 -*-
import pymongo
from sage.rings.integer import Integer
from sage.misc.sage_eval import sage_eval
import sage.structure.sage_object
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.integer_ring import IntegerRing


DB = None

class DataBase():
    def __init__( self, DB_URL = None):
        if DB_URL:
            import pymongo
            self.__client = pymongo.MongoClient( DB_URL)
        else:
            import lmfdb.base
            self.__client = lmfdb.base.getDBConnection()
            self.__db = self.__client.siegel_modular_forms
          
    # def count( self, dct, collection = 'samples'):
    #     col = self.__db[collection]
    #     return col.find( dct).count()

    def find_one( self, *dct, **kwargs):
        collection = kwargs.get( 'collection', 'samples')
        col = self.__db[collection]
        return col.find_one( *dct)

    def find( self, *dct, **kwargs):
        collection = kwargs.get( 'collection', 'samples')
        col = self.__db[collection]
        return col.find( *dct)

    def __del__( self):
        self.__client.close()


# def find_sample( dct):

#     # DB_URL = 'mongodb://localhost:40000/'
#     # client = pymongo.MongoClient( DB_URL)
#     import lmfdb.base
#     client = lmfdb.base.getDBConnection()

#     db = client.siegel_modular_forms
#     smps = db.samples
#     smple = smps.find_one( dct)
#     client.close()
#     return smple



class Sample_class (sage.structure.sage_object.SageObject):
    """
    A wrapper around a database entry providing the various
    properties a sage objects.
    """
    def __init__( self, doc):

        self.__collection = doc.get( 'collection')
        self.__name = doc.get( 'name')
        weight = doc.get( 'weight')
        field = doc.get( 'field')
        fcs = None #doc.get( 'Fourier_coefficients')
        evs = None #doc.get( 'eigenvalues')
        self.__weight = Integer( weight) if weight else weight
        R = PolynomialRing( IntegerRing(), name = 'x')
        self.__field = sage_eval( field, locals = R.gens_dict()) if field else field
        loc_f = self.__field.gens_dict()
        P = PolynomialRing( self.__field, names = 'x,y')
        loc = P.gens_dict()
        loc.update ( loc_f)
        self.__fcs = dict( (tuple( eval(f)),
                            sage_eval( fcs[f], locals = loc))
                           for f in fcs) if fcs else fcs
        loc = self.field().gens_dict()
        self.__evs = dict( (eval(l), sage_eval( evs[l], locals = loc_f)) for l in evs)\
            if evs else evs
        self.__explicit_formula = doc.get( 'explicit_formula')


    def collection( self):
        return self.__collection

    def name( self):
        return self.__name

    def weight( self):
        return self.__weight

    def field( self):
        return self.__field

    def Fourier_coefficients( self):
        return self.__fcs

    def eigenvalues( self):
        return self.__evs

    def explicit_formula( self):
        return self.__explicit_formula



def Sample( collection, name):
    """

    """
    global DB
    if not DB:
        DB = DataBase() 
    
    doc = DB.find_one( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return Sample_class( doc) if doc else None



def Samples( dct):
    """

    """
    global DB
    if not DB:
        DB = DataBase() 
    
    docs = DB.find( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return [ Sample_class( doc) for doc in docs]
    
    
