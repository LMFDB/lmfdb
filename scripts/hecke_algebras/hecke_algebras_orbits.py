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
hecke_orb = C['hecke_algebras'].hecke_algebras_orbits

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

hecke_orb.create_index('level')
hecke_orb.create_index('weight')
hecke_orb.create_index('parent_label')

print "finished indices"


## Main importing function

def do_import(ll):
    level,weight,orbit,hecke_op,num_hecke_op,gen,num_gen,rel,parent_label,orbit_label= ll
    mykeys = ['level','weight','orbit', 'hecke_op','num_hecke_op','gen','num_gen','rel','parent_label','orbit_label']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]

    alg_orb = hecke_orb.find_one({'parent_label': parent_label, 'orbit_label': orbit_label})

    if alg_orb is None:
        print "new orbit"
        alg_orb = data
    else:
        print "orbit already in the database"
        alg_orb.update(data)
    if saving:
        hecke_orb.update({'orbit_label': orbit_label} , {"$set": alg_orb}, upsert=True)



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
