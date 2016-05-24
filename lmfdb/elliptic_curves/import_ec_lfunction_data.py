# -*- coding: utf-8 -*-
r""" Import L-function data (as computed from Cremona tables by Andy Booker).

Initial version (Bristol March 2016)

For the format of the collections Lfunctions and Instances in the
database Lfunctions, see
https://github.com/LMFDB/lmfdb-inventory/blob/master/db-Lfunctions.md.
These are duplicated here for convenience but the inventory takes
precedence in case of any discrepancy.

In general "number" means an int or double or string representing a number (e.g. '1/2').

(1) fields which are the same for every elliptic curve over Q:

   - 'algebraic' (bool), whether the L-function is algebraic: True

   - 'analytic_normalization' (number), translation needed to obtain
     the analytic normalization: 0.5

   - 'coefficient_field' (string), label of the the coefficient field Q: '1.1.1.1'
   - 'degree' (int), degree of the L-function: 2
   - 'gamma_factors' (list of length 2 of lists of numbers), encoding of Gamma factors: [[],[0]]
   - 'motivic_weight' (int), motivic weight: 1
   - 'primitive' (bool), wheher this L-function is primitive: True
   - 'self_dual' (bool), wheher this L-function is self-dual: True
   - 'load_key' (string), person who uploaded the data
   - 'type' (string), "ECQ"

(2) fields which depend on the curve (isogeny class)

   - '_id': internal mogodb identifier
   - 'Lhash' (string)
   - 'conductor' (int) conductor, e.g. 1225
   - 'url' (string): the URL of the object from which this
     L-function originated, e.g. 'EllipticCurve/Q/11/a'
   - 'instances' (list of strings): list of URLs of objects with this L-function, e.g. ['EllipticCurve/Q/11/a']
   - 'order_of_vanishing': (int) order of vanishing at critical point, e.g. 0
   - 'bad_lfactors' (list of lists) list of pairs [p,coeffs] where p
     is a bad prime and coeffs is a list of 1 or 2 numbers,
     coefficients of the bad Euler factor at p,
     e.g. [[2,[1]],[3,[1,1]],[5,[1,-1]]]
   - 'euler_factors' (list of lists of 3 ints): list of lists [1] or
     [1,1] or [1,-1] or[1,-ap,p] of coefficients of the p'th Euler
     factor for the first 100 primes (including any bad primes).
   - 'A2',...,'A10' (int): first few (integral) Dirichlet coefficients, arithmetic normalization
   - 'a2',...,'a10' (list of 2 floats): first few (complex) Dirichlet coefficients, analytic normalization
   - 'central_character' (string): label of associated central character, '%s.1' % conductor
   - 'root_number' (int): sign of the functional equation: 1 or -1
   - 'leading_term' (number): value of L^{r}(1)/r! where r=order_of_vanishing, e.g. 0.253841860856
   - 'st_group' (string): Sato-Tate group, either 'SU(2)' if not CM or 'N(U(1))' if CM
   - 'positive_zeros' (list of strings): list of strings representing strictly positive
      imaginary parts of zeros between 0 and 20.
   - 'z1', 'z2', 'z3' (numbers): the first three positive zeros
   - 'plot_delta' (number): x-increment for plot values
   - 'plot_values' (list of numbers): list of y-coordinates of points on the plot

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

from lmfdb.base import getDBConnection
print "getting connection"
C= getDBConnection()
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
Lfunctions = C.Lfunctions.Lfunctions
#Lfunctions = C.Lfunctions.LfunctionsECtest
Instances = C.Lfunctions.instances
#Instances = C.Lfunctions.instancesECtest

def constant_data():
    r"""
    Returns a dict containing the L-function data which is the same for all curves:

   - 'algebraic', whether the L-function is algebraic: True
   - 'analytic_normalization', translation needed to obtain the analytic normalization: 0.5
   - 'coefficient_field', label of the the coefficient field Q: '1.1.1.1'
   - 'degree', degree of the L-function: 2
   - 'gamma_factors', encoding of Gamma factors: [[],[0]]
   - 'motivic_weight', motivic weight: 1
   - 'primitive', wheher this L-function is primitive: True
   - 'self_dual', wheher this L-function is self-dual: True
   - 'load_key', person who uploaded the data

    """
    return {
        'algebraic': True,
        'analytic_normalization': 0.5,
        'coefficient_field': '1.1.1.1',
        'degree': 2,
        'gamma_factors': [[],[0]],
        'motivic_weight': 1,
        'primitive': True,
        'self_dual': True,
        'load_key': "Cremona"
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
    instances = {}

    # Set the fields in the Instances collection:

    cond = data['conductor'] = int(E['conductor'])
    iso = E['lmfdb_iso'].split('.')[1]
    instances['url'] = ec_url = 'EllipticCurve/Q/%s/%s' % (cond,iso)
    instances['Lhash'] = Lhash = fields[0]
    instances['type'] = 'ECQ'

    # Set the fields in the Lfunctions collection:

    data['Lhash'] = Lhash
    data['root_number'] = int(fields[2])
    data['order_of_vanishing'] = r = int(E['rank'])
    data['central_character'] = '%s.1' % cond
    data['st_group'] = 'N(U(1))' if E['cm'] else 'SU(2)'
    data['leading_term'] = float(E['special_value'])

    # Zeros

    zeros = fields[4][1:-1].split(",")
    # omit negative ones and 0, using only string tests:
    data['positive_zeros'] = [y for y in zeros if y!='0' and y[0]!='-']
    data['z1'] = data['positive_zeros'][0]
    data['z2'] = data['positive_zeros'][1]
    data['z3'] = data['positive_zeros'][2]

    # plot data

    plot_xy = [[float(v) for v in vv.split(",")] for vv in fields[5][2:-3].split("],[")]
    # constant difference in x-coordinate sequence:
    data['plot_delta'] = plot_xy[1][0]-plot_xy[0][0]
    # list of y coordinates for x>0:
    data['plot_values'] = [y for x,y in plot_xy if x>=0]

    # Euler factors: we need the ap which are currently not in the
    # database so we call Sage.  It might be a good idea to store in
    # the ec database (1) all ap for p<100; (2) all ap for bad p.
    Esage = EllipticCurve([ZZ(eval(a)) for a in E['ainvs']])
    data['bad_lfactors'] = make_bad_lfactors(Esage)
    data['euler_factors'] = make_euler_factors(Esage)

    # Dirichlet coefficients

    an = Esage.anlist(10)
    for n in range(2,11):
        data['A%s' % n] = str(an[n])
        data['a%s' % n] = [an[n]/sqrt(float(n)),0]

    return Lhash, data, instances


def comp_dict_by_label(d1, d2):
    return cmp_label(d1['label'], d2['label'])

# To run this go into the top-level lmfdb directory, run sage and give
# the command
# %runfile lmfdb/elliptic_curves/import_ec_lfunction_data.py
#
# and then run the following function.
# Unless you set test=False it will not actually upload any data.

def upload_to_db(base_path, f, test=True):
    f = os.path.join(base_path, f)
    h = open(f)
    print "opened %s" % f

    data_to_insert = {}  # will hold all the data to be inserted
    instances_to_insert = {}  # will hold all the data to be inserted
    t = time.time()
    count = 0

    for line in h.readlines():
        count += 1
        if count%1000==0:
            print "read %s lines" % count
        Lhash, data, instance = read_line(line)
        if Lhash not in data_to_insert:
            data_to_insert[Lhash] = data
            instances_to_insert[Lhash] = instance

    print "finished reading %s lines from file" % count
    vals = data_to_insert.values()

    print("Number of records to insert = %s" % len(vals))
    count = 0

    if test:
        print("Not inserting any records as in test mode")
        print("First record is %s" % vals[0])
        return

    for val in vals:
        #print val
        Lfunctions.update({'Lhash': val['Lhash']}, {"$set": val}, upsert=True)
        Instances.update({'Lhash': val['Lhash']}, {"$set": instances_to_insert[val['Lhash']]}, upsert=True)
        count += 1
        if count % 1000 == 0:
            print("inserted %s items" % count)
