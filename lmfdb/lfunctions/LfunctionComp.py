# Functions for getting info about elliptic curves and related modular forms
# TODO: These should be (is already) part of the elliptic curve code?

import re
import base
from pymongo import ASCENDING
import utils
from lfunctions import logger
from elliptic_curve import lmfdb_label_regex


def isogenyclasstable(Nmin,Nmax):
    ''' Returns a table of all isogeny classes of elliptic curves with
     conductor in the ranges NMin, NMax.
    '''
    iso_list = []

    query = {'number': 1, 'conductor': {'$lte': Nmax, '$gte': Nmin}}

    # Get all the curves and sort them according to conductor
    cursor = base.getDBConnection().elliptic_curves.curves.find(query)
    res = cursor.sort([('conductor', ASCENDING), ('lmfdb_label', ASCENDING)])

    iso_list = [E['lmfdb_iso'] for E in res]

    return iso_list
    
def nr_of_EC_in_isogeny_class(label):
    ''' Returns the number of elliptic curves in the isogeny class
     with given label.
    '''
    i = 1
    connection = base.getDBConnection()
    data = connection.elliptic_curves.curves.find_one({'lmfdb_label': label + str(i)})
    while not data is None:
        i += 1
        data = connection.elliptic_curves.curves.find_one({'lmfdb_label': label + str(i)})
    return i-1

def modform_from_EC(label):
    ''' Returns the level and label for the cusp form corresponding
     to the elliptic curve with given label.
    '''
    N, iso, number = lmfdb_label_regex.match(label).groups()
    return { 'level' : N, 'iso' : iso}

def EC_from_modform(level, iso):
    ''' The inverse to modform_from_EC
    '''
    return str(level) + '.' + iso
