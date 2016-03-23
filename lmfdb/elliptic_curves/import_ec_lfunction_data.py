# -*- coding: utf-8 -*-
r""" Import L-function data (as computed from Cremona tables by Andy Booker).

Initial version (Bristol March 2016)

The documents in the collection 'Lfunctions' in the database 'elliptic_curves' have the following fields:

(1) fields which are the same for every elliptic curve over Q:

   - 'algebraic' (boolean), whether the L-function is algebraic: True
   - 'analytic_normalization' (string), translation needed to obtain the analytic normalization: '1/2'
   - 'coefficient_field' (string), label of the the coefficient field Q: '1.1.1.1'
   - 'degree' (int), degree of the L-function: 2
   - 'gamma_factors' (string), encoding of Gamma factors: '[[],[0]]'
   - 'motivic_weight' (int), motivic weight: 1
   - 'primitive' (bool), wheher this L-function is primitive: True
   - 'self_dual' (bool), wheher this L-function is self-dual: True

(2) fields which depend on the curve (isogeny class)

   - '_id': internal mogodb identifier
   - 'conductor' (int) conductor, e.g. 1225
   - 'hash' (python Long int)
   - 'origin' (strings): the URL of the object from which this L-function originated, e.g. 'EllipticCurve/11/a'
   - 'instances' (list of strings): list of URLs of objects with this L-function, e.g. ['EllipticCurve/11/a']
   - 'order_of_vanishing': (int) order of vanishing at critical point, e.g. 0
   - 'plot' (string): string representing list of [x,y] coordinates of points on the plot
   - 'bad_lfactors' (list of lists) list of pairs [p,coeffs] where p
     is a bad prime and coeffs is a list of 1 or 2 coefficients of the
     bad Euler factor at p, e.g. [[2,[1]],[3,[1,1]],[5,[1,-1]]]
   - 'euler_factors' (string reprenting list of lists of 3 ints):
     list of lists [1] or [1,1] or [1,-1] or[1,-ap,p] of coefficients
     of the p'th Euler factor for the first 100 primes (including any
     bad primes).
   - 'central_character' (string): label of associated central character, always "%s.1" % cond
   - 'root_number' (string): sign of the functional equation: '1' or '-1'
   - 'special_values': (string) string representing list of (1) list
     [1,v] where v is the value of L(1): e.g. '[[1,1.490882041449698]]'
   - 'st_group' (string): Sato-Tate group, either 'SU(2)' if not CM or 'N(U(1))'
   - 'zeros' (string): string representing list of imaginary parts of zeros between -20 and +20.

"""

import os.path
import gzip
import re
import sys
import time
import os
import random
import glob
import pymongo
from lmfdb import base
from sage.rings.all import ZZ

from lmfdb.website import DEFAULT_DB_PORT as dbport
from pymongo.mongo_client import MongoClient
print "getting connection"
C= MongoClient(port=dbport)
print "authenticating on the elliptic_curves database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.extsep, os.extsep, os.extsep, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['elliptic_curves'].authenticate(username, password)
print "setting curves"
curves = C.elliptic_curves.curves

print "authenticating on the Lfunctions database"
C['Lfunctions'].authenticate(username, password)
Lfunctions = C.Lfunctions.LfunctionsECtest

def constant_data():
    r"""
    Returns a dict containing the L-function data which is the same for all curves:

   - 'algebraic' (boolean), whether the L-function is algebraic: True
   - 'analytic_normalization' (string), translation needed to obtain the analytic normalization: '1/2'
   - 'coefficient_field' (string), label of the the coefficient field Q: '1.1.1.1'
   - 'degree' (int), degree of the L-function: 2
   - 'gamma_factors' (string), encoding of Gamma factors: '[[],[0]]'
   - 'motivic_weight' (int), motivic weight: 1
   - 'primitive' (bool), wheher this L-function is primitive: True
   - 'self_dual' (bool), wheher this L-function is self-dual: True

    """
    return {
        'algebraic': True,
        'analytic_normalization': '1/2',
        'coefficient_field': '1.1.1.1',
        'degree': 2,
        'gamma_factors': '[[],[0]]',
        'motivic_weight': 1,
        'primitive': True,
        'self_dual': True
        }

def make_one_euler_factor(E, p):
    r"""
    Returns the Euler factor at p from a Sage elliptic curve E.
    """
    ap = int(E.ap(p))
    e = E.conductor().valuation(p)
    if e==0:
        return [1,-ap,int(p)]
    if e==1:
        return [1,-ap]
    return [1]

def make_euler_factors(E, maxp=100):
    r"""
    Returns a list of the Euler factors for all primes up to max_p,
        given a Sage elliptic curve E,
    """
    return [make_one_euler_factor(E, p) for p in primes(100)]

def make_bad_lfactors(E):
    r"""
    Returns a list of the bad Euler factors, given a database elliptic curve E,
    """
    return [[int(p),make_one_euler_factor(E, p)] for p in E.conductor().support()]

def read_line(line):
    r""" Parses one line from input file.  Returns the hash and a
    dict containing fields with keys as above.
    """
    fields = line.split(":")
    assert len(fields)==6
    label = fields[1] # use this isogeny class label to get info about the curve
    E = curves.find_one({'iso': label})

    data = constant_data()

    data['hash'] = fields[0]
    data['root_number'] = fields[2]
    data['special_values'] = fields[3]
    data['zeros'] = fields[4]
    data['plot'] = fields[5]

    cond = data['conductor'] = int(E['conductor'])
    data['origin'] = ec_url = 'EllipticCurve/Q/%s' % label
    iso = E['lmfdb_iso'].split('.')[1]
    mf_url = 'ModularForms/GL2/Q/holomorphic/%s/2/1/%s' % (cond,iso)
    data['instances'] = [ec_url, mf_url]
    data['order_of_vanishing'] = r = E['rank']
    data['central_character'] = '%s.1' % cond
    data['st_group'] = 'N(U(1))' if E['cm'] else 'SU(2)'

    Esage = EllipticCurve([ZZ(eval(a)) for a in E['ainvs']])
    data['bad_lfactors'] = make_bad_lfactors(Esage)
    data['euler_factors'] = str(make_euler_factors(Esage))

    return hash, data


def comp_dict_by_label(d1, d2):
    return cmp_label(d1['label'], d2['label'])

# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile lmfdb/elliptic_curves/import_ec_data.py
#

def upload_to_db(base_path, f, test=True):
    f = os.path.join(base_path, f)
    h = open(f)
    print "opened %s" % f

    data_to_insert = {}  # will hold all the data to be inserted
    t = time.time()
    count = 0

    for line in h.readlines():
        count += 1
        if count%1000==0:
            print "read %s lines" % count
        hash, data = read_line(line)
        if hash not in data_to_insert:
            data_to_insert[hash] = data
        # if count==1:
        #     for k in data_to_insert[hash].keys():
        #         print k, type(data_to_insert[hash][k])

    print "finished reading %s lines from file" % count

    vals = data_to_insert.values()
    count = 0
    for val in vals:
        #print val
        if not test:
            Lfunctions.update({'hash': val['hash']}, {"$set": val}, upsert=True)
        count += 1
        if count % 1000 == 0:
            print "inserted %s" % (val['label'])

