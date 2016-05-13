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

mypath = os.path.realpath(__file__)
while os.path.basename(mypath) != 'lmfdb':
    mypath = os.path.dirname(mypath)
# now move up one more time...
mypath = os.path.dirname(mypath)
sys.path.append(mypath)


from lmfdb.WebNumberField import WebNumberField

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['abvar'].authenticate(username, password)
db = C.abvar.fq_isog


saving = True

def sd(f):
  for k in f.keys():
    print '%s ---> %s'%(k, f[k])

def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

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

## Main importing function

def do_import(ll):
    label,g, q, polynomial,angle_numbers,p_rank,slopes,A_counts,C_counts,known_jacobian,principally_polarizable,decomposition,brauer_invariants,primitive_models = ll
    mykeys = ['label','g','q','polynomial','angle_numbers','p_rank','slopes','A_counts','C_counts','known_jacobian','principally_polarizable','decomposition','brauer_invariants','primitive_models']
    data = {}
    for key, val in zip(mykeys, ll):
        data[key] = val
    f = R(polynomial)
    nf = WebNumberField.from_polynomial(f)
    data['number_field'] = "" if nf.label == 'a' else nf.label
    isoclass = db.find_one({'label': label})

    if isoclass is None:
        print "new isogeny class"
        print "***********"
        isoclass = data
    else:
        print "isogeny class already in the database"
        isoclass.update(data)
    if saving:
        db.update({'label': label} , {"$set": isoclass}, upsert=True)

# Loop over files

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)
