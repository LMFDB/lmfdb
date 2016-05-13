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
from lmfdb.WebNumberField import WebNumberField

from pymongo.mongo_client import MongoClient
import yaml

## Main importing function

def do_import(ll, db, saving, R, show_update):
    label,g,q,polynomial,angle_numbers,p_rank,slopes,A_counts,C_counts,known_jacobian,principally_polarizable,decomposition,brauer_invariants,primitive_models = ll
    mykeys = ['label','g','q','polynomial','angle_numbers','p_rank','slopes','A_counts','C_counts','known_jacobian','principally_polarizable','decomposition','brauer_invariants','primitive_models']
    data = {}
    for key, val in zip(mykeys, ll):
        data[key] = val
    f = R(polynomial)
    try:
        nf = WebNumberField.from_polynomial(f)
        if nf.label == 'a': nf = None
    except PariError:
        nf = None
    data['number_field'] = "" if nf is None else nf.label
    data['galois_t'] = "" if nf is None else nf.galois_t()
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

def do_import_all(*paths):
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
            line.strip()
            if re.match(r'\S',line):
                l = json.loads(line)
                counter += 1
                do_import(l, db, saving, R, (counter%100)==0)
