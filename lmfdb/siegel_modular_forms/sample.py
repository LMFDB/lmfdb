# -*- coding: utf-8 -*-
# This file provides the class Sammple_Class which describes
# a sample of a collection of Sıegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

import pymongo
import sage.structure.sage_object
from sage.all import ZZ, NumberField, Rationals, PolynomialRing
from lmfdb.base import getDBConnection

def smf_db_samples():
    return getDBConnection().siegel_modular_forms.experimental_samples

class Sample_class (sage.structure.sage_object.SageObject):
    """
    A wrapper around a database entry providing various
    properties as a sage object.
    """
    def __init__( self, doc):

        self.__collection = doc.get( 'collection')
        self.__name = doc.get( 'name')

        weight = doc.get( 'weight')
        self.__weight = ZZ( weight) if weight else weight
       
        field_poly = doc.get( 'field_poly')
        if field_poly:
            f = PolynomialRing(ZZ,name='x')(str(field_poly))
            self.__field = Rationals() if f.degree() == 1 else NumberField(f,'a')
        else:
            self.__field = None

        self.__explicit_formula = doc.get( 'explicit_formula')
        self.__type = doc.get( 'type')
        self.__is_eigenform = doc.get( 'is_eigenform')
        self.__is_integral = doc.get( 'is_integral')
        self.__representation = doc.get( 'representation')
        self.__id = doc.get( '_id')
 
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
        evs = smf_db_samples().find({ 'owner_id': self.__id, 'data_type': 'ev' }, { 'data': False})
        ls  = [ ZZ( ev['index']) for ev in evs]
        ls.sort()
        return  ls

    def eigenvalues( self, index_list):
        evs = smf_db_samples().find(
            { 'owner_id': self.__id,
              'data_type': 'ev',
              'index': { '$in': [ str(l) for l in index_list]}
            })
        return dict( (ZZ(ev['index']),self.__field(str(ev['data']))) for  ev in evs)

    def available_Fourier_coefficients( self):
        fcs = smf_db_samples().find( { 'owner_id': self.__id, 'data_type': 'fc' }, { 'data': False})
        ls  = [ ZZ( fcd['det']) for fcd in fcs]
        ls.sort()
        return  ls

    def Fourier_coefficients( self, det_list):
        fcs = smf_db_samples().find(
            { 'owner_id': self.__id,
              'data_type': 'fc',
              'det': { '$in': [ str(d) for d in det_list]}
            })
        P = PolynomialRing( self.__field, names = 'x,y')
        return dict( (ZZ(fcd['det']),
                      dict( (tuple( eval(f)), P(str(fcd['data'][f])))
                            for f in fcd['data'] ))
                     for fcd in fcs)


def Sample( collection, name):
    """
    Return a light instance of Sample_class, where 'light' means
    'without eigenvalues and Fourier coefficients'.
    """
    dct = { 'collection': collection, 'name': name}
    doc = smf_db_samples().find_one( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return Sample_class( doc) if doc else None


def Samples( dct):
    """
    Return a result of a database query as list of light instances
    of Sample_class.
    """
    dct.update( { 'field': { '$exists': True}})
    docs = smf_db_samples().find( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    return [ Sample_class( doc) for doc in docs]


def export( collection, name):
    """
    Return
    """
    dct = { 'collection': collection, 'name': name}
    doc = smf_db_samples().find_one( dct, { 'Fourier_coefficients': 0, 'eigenvalues': 0})
    id = doc.get('_id')
    assert id != None, 'Error: the item "%s" was not accessible in the database.' % dct 

    # Fourier coefficients and eigenvalues
    fcs = smf_db_samples().find( { 'owner_id': id, 'data_type': 'fc' })
    doc['Fourier_coefficients'] = dict(( ( fc['det'], fc['data']) for fc in fcs))

    evs = smf_db_samples().find( { 'owner_id': id, 'data_type': 'ev'})
    doc['eigenvalues'] = dict( ( (ev['index'], ev['data']) for ev in evs))

    doc.pop( '_id')
    label = doc['collection'][0] + '.' + doc['name']
    doc['label']= label
    
    import json
    from bson import BSON
    from bson import json_util
    return json.dumps( doc, sort_keys=True, indent=4, default = json_util.default)        
