# -*- coding: utf-8 -*-
# This file provides the class Sammple_Class which describes
# a sample of a collection of Sıegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from sage.structure.sage_object import SageObject
from sage.all import ZZ, QQ, NumberField, PolynomialRing
from ast import literal_eval
from random import randint
from lmfdb.base import getDBConnection

def smf_db_samples():
    return getDBConnection().siegel_modular_forms.samples
    
def count_samples():
    return smf_db_samples().find({'data_type':'sample'}).count()

def random_sample_name():
    # do this ourselves rather than using random_object_from_collection, but use
    # the random object index if it exists (it should only contain records for samples, not evs of fcs)
    n = getDBConnection().siegel_modular_forms.samples.rand.count()
    if n:
        id = getDBConnection().siegel_modular_forms.samples.rand.find_one({'num':randint(1,n)})['_id']
        data = smf_db_samples().find_one({'_id':id},{'_id':False,'collection':True,'name':True})
    else:
        # do it the hard way, don't bother with aggregate (there are currently only a few hundred records in any case)
        recs = [r for r in smf_db_samples().find({'data_type':'sample'},{'_id':False,'collection':True,'name':True})]
        data = recs[randint(0,len(recs)-1)]
    return (data['collection'][0], data['name'])

class Sample_class (SageObject):
    """
    A wrapper around a database entry providing various
    properties as a sage object.
    """
    def __init__(self, doc):

        self.__collection = doc.get('collection')
        self.__name = doc.get('name')
        self.__weight = doc.get('wt')
        self.__degree_of_field = doc.get('fdeg')
        self.__field_poly = PolynomialRing(QQ,'x')(str(doc.get('field_poly')))
        self.__field = None # created on demand
        self.__explicit_formula = None # create on demand
        self.__explicit_formula_set = False # set to true once we try to get it to avoid repeatedly trying to fetch an explicit formula that is not thre
        self.__type = doc.get('type')
        self.__is_eigenform = doc.get('is_eigenform')
        self.__is_integral = doc.get('is_integral')
        self.__representation = doc.get('representation')
        self.__id = doc.get('_id')
 
    def collection(self):
        return self.__collection

    def name(self):
        return self.__name

    def full_name(self):
        return self.__collection[0] + "." + self.__name

    def weight(self):
        return self.__weight

    def degree_of_field(self):
        return self.__degree_of_field

    def field_poly(self):
        return self.__field_poly

    def field(self):
        if not self.__field:
            f = PolynomialRing(ZZ,name='x')(str(self.__field_poly))
            self.__field = QQ if f.degree() == 1 else NumberField(f,'a')
        return self.__field

    def explicit_formula(self):
        if not self.__explicit_formula_set:
            self.__explicit_formula = smf_db_samples().find_one({'_id':self.__id},{'explicit_formula':True}).get('explicit_formula')
            self.__explicit_formula_set = True
        return self.__explicit_formula

    def type(self):
        return self.__type

    def is_eigenform(self):
        return self.__is_eigenform

    def is_integral(self):
        return self.__is_integral

    def representation(self):
        return self.__representation
        
    def available_eigenvalues(self, index_list=None):
        query = { 'owner_id': self.__id, 'data_type': 'ev' }
        if index_list:
            query['ev_index'] = { '$in' : [ l for l in index_list ] }
        evs = smf_db_samples().find(query, {'_id':False, 'ev_index':True})
        return sorted([ ev['ev_index'] for ev in evs])

    def eigenvalues(self, index_list):
        query = {'owner_id': self.__id, 'data_type': 'ev', 'ev_index': { '$in': [ l for l in index_list] } }
        evs = smf_db_samples().find(query, {'_id':False, 'ev_index':True, 'data':True})
        return dict((ev['ev_index'],self.__field(str(ev['data']))) for  ev in evs)

    def available_Fourier_coefficients(self, det_list=None):
        query = { 'owner_id': self.__id, 'data_type': 'fc' }
        if det_list:
            query['det_index'] = { '$in' : [ l for l in det_list ] }
        fcs = smf_db_samples().find(query, { '_id': False, 'fc_det':True })
        return sorted([ fcd['fc_det'] for fcd in fcs])

    def Fourier_coefficients(self, det_list):
        query = { 'owner_id': self.__id, 'data_type': 'fc', 'fc_det': { '$in': [ d for d in det_list] } }
        fcs = smf_db_samples().find(query,{'_id':False, 'fc_det':True, 'data':True})
        P = PolynomialRing(self.__field, names = 'x,y')
        return dict((fcd['fc_det'], dict((tuple(literal_eval(f)), P(str(fcd['data'][f]))) for f in fcd['data'] )) for fcd in fcs)


def Sample(collection, name):
    """
    Return a light instance of Sample_class, where 'light' means 'without eigenvalues, Fourier coefficients or explicit formula'.
    """
    query = { 'collection': collection, 'name': name}
    doc = smf_db_samples().find_one(query, { 'Fourier_coefficients': False, 'eigenvalues': False, 'explicit_formula': False })
    return Sample_class(doc) if doc else None


def Samples(query):
    """
    Return a result of a database query as list of light instances of Sample_class.
    """
    query.update({ 'data_type': 'sample'})
    docs = smf_db_samples().find(query, { 'Fourier_coefficients': False, 'eigenvalues': False, 'explicit_formula': False }).sort('name')
    return [ Sample_class(doc) for doc in docs]


def export(collection, name):
    """
    Return
    """
    query = { 'data_type': 'sample', 'collection': collection, 'name': name}
    doc = smf_db_samples().find_one(query, { 'Fourier_coefficients': False, 'eigenvalues': False })
    id = doc.get('_id')
    assert id != None, 'Error: the item "%s.%s" was not found in the database.' % (collection, name)

    # Fourier coefficients and eigenvalues
    fcs = smf_db_samples().find({ 'owner_id': id, 'data_type': 'fc' })
    doc['Fourier_coefficients'] = dict(((fc['fc_det'], fc['data']) for fc in fcs))

    evs = smf_db_samples().find({ 'owner_id': id, 'data_type': 'ev'})
    doc['eigenvalues'] = dict(((ev['ev_index'], ev['data']) for ev in evs))

    doc.pop('_id')
    label = doc['collection'][0] + '.' + doc['name']
    doc['label']= label
    
    import json
    from bson import json_util
    return json.dumps(doc, sort_keys=True, indent=4, default = json_util.default)        
