# Functions for getting info about elliptic curves and related modular forms

from pymongo import ASCENDING
from lmfdb.elliptic_curves.web_ec import db_ec

# TODO These should perhaps be defined in the elliptic curves codebase

def isogeny_class_table(Nmin, Nmax):
    ''' Returns a table of all isogeny classes of elliptic curves with
     conductor in the ranges NMin, NMax.
    '''
    iso_list = []

    query = {'number': 1, 'conductor': {'$lte': Nmax, '$gte': Nmin}}

    # Get all the curves and sort them according to conductor
    res, _, _ = db_ec().search_results(query)

    i = db_ec()._search_cols.index('lmfdb_iso')
    iso_list = [E[i].split('.') for E in res]

    return iso_list
    
def isogeny_class_cm(label):
    return db_ec().lucky({'lmfdb_iso':label},data_level=1)['cm']

def EC_from_modform(level, iso):
    ''' The inverse to modform_from_EC
    '''
    return str(level) + '.' + iso


# DEPRECATED
#from lmfdb.ecnf.WebEllipticCurve import db_ecnf
#from lmfdb.elliptic_curves.web_ec import lmfdb_label_regex
#def nr_of_EC_in_isogeny_class(long_isogeny_class_label, field_label = "1.1.1.1"):
#    ''' Returns the number of elliptic curves in the isogeny class
#     with given label.
#    '''
#    if field_label == "1.1.1.1":
#        return db_ec().find({'lmfdb_iso':long_isogeny_class_label}).count()
#    else:
#        return db_ecnf().find({'class_label':field_label + "." + long_isogeny_class_label}).count()
#
#def modform_from_EC(label):
#    ''' Returns the level and label for the cusp form corresponding
#     to the elliptic curve with given label.
#    '''
#    N, iso, number = lmfdb_label_regex.match(label).groups()
#    return {'level': N, 'iso': iso}
        


