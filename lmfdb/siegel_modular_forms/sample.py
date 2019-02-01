# -*- coding: utf-8 -*-
# This file provides the class Sammple_Class which describes
# a sample of a collection of Sıegel modular forms.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from sage.structure.sage_object import SageObject
from sage.all import ZZ, QQ, NumberField, PolynomialRing
from ast import literal_eval
from lmfdb.db_backend import db

def random_sample_name():
    data = db.smf_samples.random(projection=['collection', 'name'])
    return (data['collection'][0], data['name'])

class Sample_class (SageObject):
    """
    A wrapper around a database entry providing various
    properties as a sage object.
    """
    def __init__(self, doc):

        self.__collection = doc.get('collection')
        self.__name = doc.get('name')
        self.__weight = doc.get('weight')
        self.__degree_of_field = doc.get('fdeg')
        self.__field_poly = PolynomialRing(QQ,'x')(str(doc.get('field_poly')))
        self.__field = None # created on demand
        self.__explicit_formula = None # create on demand
        self.__explicit_formula_set = False # set to true once we try to get it to avoid repeatedly trying to fetch an explicit formula that is not thre
        self.__type = doc.get('type')
        self.__is_eigenform = doc.get('is_eigenform')
        self.__is_integral = doc.get('is_integral')
        self.__representation = doc.get('representation')
        self.__id = doc.get('id_link')
 
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
            self.__explicit_formula = db.smf_samples.lucky({'id_link':self.__id}, 'explicit_formula')
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
        query = {'owner_id': self.__id}
        if index_list:
            query['index'] = {'$in': index_list}
        return list(db.smf_ev.search(query, 'index'))

    def eigenvalues(self, index_list):
        query = {'owner_id': self.__id, 'index': {'$in': index_list}}
        evs = db.smf_ev.search(query, ['index', 'data'])
        return dict((ev['index'], self.__field(str(ev['data']))) for ev in evs)

    def available_Fourier_coefficients(self, det_list=None):
        query = {'owner_id': self.__id}
        if det_list:
            query['det'] = {'$in' : det_list}
        return list(db.smf_fc.search(query, 'det'))

    def Fourier_coefficients(self, det_list):
        query = {'owner_id': self.__id, 'det': {'$in': det_list}}
        fcs = db.smf_fc.search(query, ['det', 'data'])
        P = PolynomialRing(self.__field, names = 'x,y')
        return dict((fcd['det'], dict((tuple(literal_eval(f)), P(str(poly))) for f, poly in fcd['data'].items() )) for fcd in fcs)


def Sample(collection, name):
    """
    Return a light instance of Sample_class, where 'light' means 'without eigenvalues, Fourier coefficients or explicit formula'.
    """
    query = {'collection': {'$contains': [collection]}, 'name': name}
    doc = db.smf_samples.lucky(query, {'Fourier_coefficients': False, 'eigenvalues': False, 'explicit_formula': False})
    return Sample_class(doc) if doc else None


def Samples(query):
    """
    Return a result of a database query as list of light instances of Sample_class.
    """
    docs = db.smf_samples.search(query, {'Fourier_coefficients': False, 'eigenvalues': False, 'explicit_formula': False })
    return [ Sample_class(doc) for doc in docs]


def export(collection, name):
    """
    Return
    """
    query = {'collection': {'$contains': [collection]}, 'name': name}
    doc = db.smf_samples.lucky(query, {'Fourier_coefficients': False, 'eigenvalues': False})
    if doc is None:
        raise ValueError('Error: the item "%s.%s" was not found in the database.' % (collection, name))
    id_link = doc.pop('id_link')

    # Fourier coefficients and eigenvalues
    fcs = db.smf_fc.search({'owner_id': id_link}, ['det', 'data'])
    doc['Fourier_coefficients'] = dict(((fc['det'], fc['data']) for fc in fcs))

    evs = db.smf_ev.search({'owner_id': id_link}, ['index', 'data'])
    doc['eigenvalues'] = dict(((ev['index'], ev['data']) for ev in evs))

    label = doc['collection'][0] + '.' + doc['name']
    doc['label']= label

    import json
    return json.dumps(doc, sort_keys=True, indent=4)
