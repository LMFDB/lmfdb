#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Script for adding Siegel data to Warwicks mongodb
#
# author: Nils Skoruppa <nils.skoruppa@gmail.com>
#

import pymongo
import json

# Before running this script,
# run the script warwick.py in the top level of lmfdb.

# Run with care: not yet sufficiently tested.


DB_URL = 'mongodb://localhost:40000/'
# DB_URL = 'mongodb://localhost:37010/'


def upload_to_mongodb( filename):
    """
    INPUT
        A path to a json file with SMF data. It should be of the form:

        {
            "Fourier_coefficients": {
                "100": {
                    "(1, 0, 25)": "-24912060077550240*x^2 + 32778648407484000*y^2", 
                    "(2, 2, 13)": "1165564167203520*x^2 + 1165564167203520*x*y - 87856335897120*y^2", 
                    "(5, 0, 5)": "-56936396059200*x^2 - 56936396059200*y^2"
                },
                ...
            }
            "eigenvalues": {
                "11": "-77471324747256", 
                "13": "1419674440557100",
                ...
            }
            "collection": [
                "Sp4Z_2", 
                "Sp4Z_j"
            ], 
            "courtesy_of": "Alex Ghitza, 2011", 
            "degree": "2", 
            "degree_of_field": "1", 
            "eigenvalues": {}, 
            "field": "RationalField()", 
            "is_eigenform": "True", 
            "label": "Sp4Z_2.10_E", 
            "name": "10_E", 
            "representation": "2", 
            "type": "Eisenstein series", 
            "weight": "10"
        }
    
        If your number field is, say, of the form "NumberField(x^2 - x - 27, 'a')",
        the also the Fourier coeficients and the eigenvalues must use
        the same letter "a".

        If the genus is > 2, you have to redefine the function det(i) below.

    EXAMPLE USAGE
        for f in JOBS:
            upload_to_mongodb( f)

    """
    try:
        f = open( filename, 'r')
        sample = json.load( f)
        f.close()
    except:
        print 'Error: %s' % sys.exc_info()
        
    sample.update( { 'name': filename,
                     'field': 'RationalField()',
                     'collection': ['Sp6Z'],
                     'degree': '3',
                     'representation': '0',
                     'degree_of_field': '1'
                     })

    fcs = sample.pop( 'Fourier_coefficients', None) 
    evs = sample.pop( 'eigenvalues', None) 

    try:
        client = pymongo.MongoClient( DB_URL)
        db = client.siegel_modular_forms_experimental
        
        smps = db.samples
        smps.remove({'collection': sample['collection'], 'name': sample['name']})
        id = smps.insert( sample)

        if fcs:
            smps.remove( {'owner_id': id, 'data_type': 'ev'})
            # This function might need to be redefined
            def disc(i):
                a,b,c = i
                return 4*a*c - b^2
            ks = Set( map( disc, fcs.keys()))
            for D in ks:
                tmp = {'owner_id': id, 'data_type': 'fc', 'det' : str(D)}
                tmp['data'] = dict( (i,fcs[i]) for i in fcs if disc(i) == D)
                smps.insert( tmp)

        if evs:
            smps.remove( {'owner_id': id, 'data_type': 'ev'})
            for k in evs:
                tmp = {'owner_id': id, 'data_type': 'ev', 'index': k, 'data': evs[k]}
                smps.insert( tmp)

        client.close()
    except:
        print 'Error: %s' % sys.exc_info()
        return

    print '%s: Done' % filename    
    return



if __name__ == '__main__':

    import sys
    filename = sys.argv[1]
    return upload_to_mongodb( filename):
