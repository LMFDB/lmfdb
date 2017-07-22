# -*- coding: utf-8 -*-
r""" Make database lattices and number fields

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

"""

import sys
import re
import json
import os
import gzip
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

def do_import(ll):
    n_field,gram_input = ll

    R = PolynomialRing(QQ, 'x');
    nf_label = poly_to_field_label(R(n_field))

    lattice = l1.find_one({'gram': gram_input})
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
            lat_label = ""
            is_lat_in = gram_input
    
    if saving:
        l2.insert_one({"$set": {'nf_label': nf_label, 'lat_label': lat_label, 'is_lat_in' : is_lat_in} }, upsert=True)


# Loop over files

for path in sys.argv[1:]:
    print "++++++++++++++++++++++++++++++++++"
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)

