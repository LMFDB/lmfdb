#!/usr/bin/env python
# -*- coding: utf-8 -*-
r""" Import abelian variety isogeny class data.

Note: This code can be run on all files in any order. Even if you
rerun this code on previously entered files, it should have no effect.
This code checks if the entry exists, if so returns that and updates
with new information. If the entry does not exist then it creates it
and returns that.

"""

import os
import sys, time
import re
import json
import sage.all
from sage.all import Integer, ZZ, QQ, PolynomialRing, NumberField, CyclotomicField, latex, AbelianGroup, polygen, euler_phi, latex, matrix, srange, PowerSeriesRing, sqrt, QuadraticForm

#mypath = os.path.realpath(__file__)
#while os.path.basename(mypath) != 'lmfdb':
#    mypath = os.path.dirname(mypath)
## now move up one more time...
#mypath = os.path.dirname(mypath)
#sys.path.append(mypath)

from pymongo.mongo_client import MongoClient
import yaml

## Main importing function

def do_import(ll, db, saving, R, show_update):
    label,g,q,polynomial,angle_numbers,angle_ranks,p_rank,slopes,A_counts,C_counts,known_jacobian,principally_polarizable,decomposition,brauer_invariants,places,primitive_models,number_field,galois_n,galois_t = ll
    mykeys = ['label','g','q','polynomial','angle_numbers','angle_ranks','p_rank','slopes','A_counts','C_counts','known_jacobian','principally_polarizable','decomposition','brauer_invariants','places','primitive_models','number_field','galois_n','galois_t']
    data = {}
    for key, val in zip(mykeys, ll):
        data[key] = val
    isoclass = db.find_one({'label': label})

    if isoclass is None:
        if show_update:
            print "new isogeny class - %s" % label
            print "***********"
        isoclass = data
    else:
        if show_update:
            print "isogeny class %s already in the database" % label
        isoclass.update(data)
    if saving:
        db.update({'label': label} , {"$set": isoclass}, upsert=True)

# Loop over files

def do_import_all(*paths, **kwds):
    start = kwds.get('start',None)
    C= MongoClient(port=37010)
    pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
    username = pw_dict['data']['username']
    password = pw_dict['data']['password']
    C['abvar'].authenticate(username, password)
    db = C.abvar.fq_isog

    saving = True

    # The following create_index command checks if there is an index on
    # these fields
    db.create_index('label')
    db.create_index('polynomial')
    db.create_index('p_rank')
    db.create_index('slopes')
    db.create_index('A_counts')
    db.create_index('C_counts')
    db.create_index('known_jacobian')
    db.create_index('principally_polarizable')

    print "finished indices"
    R = PolynomialRing(QQ,'x')

    for path in paths:
        print path
        filename = os.path.basename(path)
        fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
        counter = 0
        for line in fn.readlines():
            line = line.strip()
            if re.match(r'\S',line):
                if start is not None:
                    if line.startswith('["%s'%start):
                        start = None
                    else:
                        continue
                l = json.loads(line)
                counter += 1
                do_import(l, db, saving, R, (counter%100)==0)

def label_progress(filename, label):
    found = None
    counter = 0
    startcheck = '["%s"'%label
    with open(filename) as F:
        for line in F.readlines():
            counter += 1
            if line.startswith(startcheck):
                found = counter
    if found is None:
        print "Label %s not found" % label
    else:
        print "Label %s is at %s/%s"%(label, found, counter)
