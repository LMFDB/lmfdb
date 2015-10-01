# -*- coding: utf-8 -*-
# This file provides the class Sammple_Class which describes
# a sample of a collection of Sıegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

import pymongo
from sage.rings.integer import Integer
from sage.misc.sage_eval import sage_eval
import sage.structure.sage_object
from sage.rings.polynomial.polynomial_ring_constructor import PolynomialRing
from sage.rings.integer_ring import IntegerRing

DB = None
# DB_URL = 'mongodb://localhost:40000/'
    
class DataBase():
    """
    DB_URL = 'mongodb://localhost:40000/'
    """
    def __init__( self, DB_URL = None):
        if DB_URL:
            self.__client = pymongo.MongoClient( DB_URL)
        else:
            import lmfdb.base
            self.__client = lmfdb.base.getDBConnection()
        self.__db = self.__client.siegel_modular_forms_experimental
        # self.__db = self.__client.siegel_modular_forms
        
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



class Sample_class (sage.structure.sage_object.SageObject):
    """
    A wrapper around a database entry providing various
    properties as a sage object.
    """
    def __init__( self, doc):

        self.__collection = doc.get( 'collection')
        self.__name = doc.get( 'name')

        weight = doc.get( 'weight')
        self.__weight = sage_eval( weight) if weight else weight
       
        field = doc.get( 'field')
        R = PolynomialRing( IntegerRing(), name = 'x')
        self.__field = sage_eval( field, locals = R.gens_dict()) if field else field

        self.__explicit_formula = doc.get( 'explicit_formula')
        self.__type = doc.get( 'type')
        self.__is_eigenform = doc.get( 'is_eigenform')
        self.__is_integral = doc.get( 'is_integral')
        self.__representation = doc.get( 'representation')
        self.__id = doc.get( '_id')

        # eigenvalues
        # evs = doc.get( 'eigenvalues')
        # loc_f = self.__field.gens_dict()
        # self.__evs = dict( (eval(l), sage_eval( evs[l], locals = loc_f)) for l in evs)\
        #     if evs else evs

        # Fourier coefficients
        # fcs = doc.get( 'Fourier_coefficients')
        # P = PolynomialRing( self.__field, names = 'x,y')
        # loc = P.gens_dict()
        # loc.update ( loc_f)
        # self.__fcs = dict( (tuple( eval(f)),
        #                     sage_eval( fcs[f], locals = loc))
        #                    for f in fcs) if fcs else fcs

 
    def collection( self):
        return self.__collection

    def name( self):
        return self.__name

    def weight( self):
        return self.__weight

    def field( self):
        return self.__field

    def explicit_formula( self):
        return self.__explicit_formula

    def type( self):
        return self.__type

    def is_eigenform( self):
        return self.__is_eigenform

    def is_integral( self):
        return self.__is_integral

    def representation( self):
        return self.__representation
        
    def available_eigenvalues( self):
        evs = DB.find( { 'owner_id': self.__id,
                             'data_type': 'ev',
                         },
                       { 'data': 0})
        ls  = [ Integer( ev['index']) for ev in evs]
        ls.sort()
        return  ls


    def eigenvalues( self, index_list):
        evs = DB.find( { 'owner_id': self.__id,
                         'data_type': 'ev',
                         'index': { '$in': [ str(l) for l in index_list]}
                         })
        loc_f = self.__field.gens_dict() 
        return dict( (eval(ev['index']),sage_eval( ev['data'], locals = loc_f)) for  ev in evs)


    def available_Fourier_coefficients( self):
        fcs = DB.find( { 'owner_id': self.__id,
                         'data_type': 'fc',
                         },
                       { 'data': 0})
        ls  = [ Integer( fcd['det']) for fcd in fcs]
        ls.sort()
        return  ls


    def Fourier_coefficients( self, det_list):
        fcs = DB.find( { 'owner_id': self.__id,
                         'data_type': 'fc',
                         'det': { '$in': [ str(d) for d in det_list]}
                         })
        P = PolynomialRing( self.__field, names = 'x,y')
        loc = P.gens_dict()
        loc.update ( self.__field.gens_dict())
        return dict( (Integer(fcd['det']),
                      dict( (tuple( eval(f)), sage_eval( fcd['data'][f], locals = loc))
                            for f in fcd['data'] ))
                     for fcd in fcs)




def Sample( collection, name):
    """
    Return a light instance of Sample_class, where 'light' means
    'without eigenvalues and Fourier coefficients'.
    """
    global DB
    if not DB:
        DB = DataBase() 
    
    dct = { 'collection': collection, 'name': name}
    doc = DB.find_one( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return Sample_class( doc) if doc else None



def Samples( dct):
    """
    Return a result of a database query as list of light instances
    of Sample_class.
    """
    global DB
    if not DB:
        DB = DataBase() 
    
    dct.update( { 'field': { '$exists': True}})
    docs = DB.find( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return [ Sample_class( doc) for doc in docs]


def export( collection, name):
    """
    Return
    """
    global DB
    if not DB:
        DB = DataBase( DB_URL = DB_URL) 
    
    dct = { 'collection': collection, 'name': name}
    doc = DB.find_one( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    id = doc.get('_id')
    assert id != None, 'Error: the item "%s" was not accessible in the database.' % dct 

    # Fourier coefficients and eigenvalues
    fcs = DB.find( { 'owner_id': id, 'data_type': 'fc' })
    doc['Fourier_coefficients'] = dict(( ( fc['det'], fc['data']) for fc in fcs))

    evs = DB.find( { 'owner_id': id, 'data_type': 'ev'})
    print evs
    doc['eigenvalues'] = dict( ( (ev['index'], ev['data']) for ev in evs))

    doc.pop( '_id')
    label = doc['collection'][0] + '.' + doc['name']
    doc['label']= label
    
    import json
    from bson import BSON
    from bson import json_util
    return json.dumps( doc, sort_keys=True, indent=4, default = json_util.default)        

