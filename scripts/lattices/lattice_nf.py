# -*- coding: utf-8 -*-
r""" Make database lattices and number fields

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

"""

import os
import os.path

from sage.all import QQ, PolynomialRing, matrix
from lmfdb.lattice.isom import isom
from lmfdb.number_fields.number_field import poly_to_field_label


from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['Lattices'].authenticate('editor', password)
l1 = C.Lattices.lat
l2 = C.Lattices.lat_nf

saving = True 


## Main importing function

def add_lattice_nf(ll):
    n_field,gram_input = ll
    gram_input=[[int(i) for i in l] for l in gram_input] 

    R = PolynomialRing(QQ, 'x');
    nf_label = poly_to_field_label(R(n_field))

    lattice = l1.find_one({'gram': gram_input })
    if lattice is None:
        n=len(gram_input[0])
        d=matrix(gram_input).determinant()
        result=[B for B in l1.find({'dim': int(n), 'det' : int(d)}) if isom(gram_input, B['gram'])]
        if len(result)==1:
            lat_label =result[0]['label']
            is_lat_in = "yes"
        elif len(result)>1:
            print "... need to be checked ..."
            print "***********"
        else :
            lat_label = "new"
            is_lat_in = gram_input
    else:
       lat_label=lattice['label']
       is_lat_in = "yes"
    
    try:
        lab=nf_label+lat_label
    except:
        print nf_label, lat_label
        print "fail"
            
    res=l2.find_one({'label': lab })
    if res is None:
        print "new data"
        if saving:
            l2.insert_one({'nf_label': nf_label, 'lat_label': lat_label, 'is_lat_in' : is_lat_in, 'label': lab})
    else:
        print "data already in the database"
