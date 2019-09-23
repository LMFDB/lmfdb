# -*- coding: utf-8 -*-
r""" Import Hecke algebras.  

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

from lmfdb.base import getDBConnection

C= getDBConnection()
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['hecke_algebras'].authenticate('editor', password)
hecke_algebras = C['hecke_algebras'].hecke_algebras

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
# label, dimension, determinant and level. 


hecke_algebras.create_index('level')
hecke_algebras.create_index('weight')
hecke_algebras.create_index('num_orbits')
hecke_algebras.create_index('label')

print "finished indices"


## Main importing function

def do_import(ll):
    level,weight,num_orbits,label = ll
    mykeys = ['level','weight','num_orbits','label']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]

    alg = hecke_algebras.find_one({'label': label})

    if alg is None:
        print "new hecke algebra"
        alg = data
    else:
        print "hecke algebra already in the database"
        alg.update(data)
    if saving:
        hecke_algebras.update({'label': label} , {"$set": alg}, upsert=True)



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
