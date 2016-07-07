# Functions for getting info about elliptic curves and related modular forms

from pymongo import ASCENDING
from lmfdb.elliptic_curves.web_ec import lmfdb_label_regex, db_ec


def isogeny_class_table(Nmin, Nmax):
    ''' Returns a table of all isogeny classes of elliptic curves with
     conductor in the ranges NMin, NMax.
    '''
    iso_list = []

    query = {'number': 1, 'conductor': {'$lte': Nmax, '$gte': Nmin}}

    # Get all the curves and sort them according to conductor
    cursor = db_ec().find(query,{'_id':False,'conductor':True,'lfmdb_label':True,'lmfdb_iso':True})
    res = cursor.sort([('conductor', ASCENDING), ('lmfdb_label', ASCENDING)])

    iso_list = [E['lmfdb_iso'] for E in res]

    return iso_list
    
def isogeny_class_cm(label):
    return db_ec().find_one({'lmfdb_iso':label},{'_id':False,'cm':True})['cm']


def nr_of_EC_in_isogeny_class(label):
    ''' Returns the number of elliptic curves in the isogeny class
     with given label.
    '''
    return db_ec().find({'lmfdb_iso':label}).count()


def modform_from_EC(label):
    ''' Returns the level and label for the cusp form corresponding
     to the elliptic curve with given label.
    '''
    N, iso, number = lmfdb_label_regex.match(label).groups()
    return {'level': N, 'iso': iso}


def EC_from_modform(level, iso):
    ''' The inverse to modform_from_EC
    '''
    return str(level) + '.' + iso
