# -*- coding: utf-8 -*-
r""" Import integral lattices data.  

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
from sage.all import matrix
from lmfdb.lattice.isom import isom
from lmfdb.base import getDBConnection

C= getDBConnection()
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['Lattices'].authenticate('editor', password)
lat = C.Lattices.lat

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

def base_label(dimension,determinant,level,class_number):
    return ".".join([str(dimension),str(determinant),str(level),str(class_number)])

def last_label(base_label, n):
    return ".".join([str(base_label),str(n)])

# The following create_index command checks if there is an index on
# label, dimension, determinant and level. 

lat.create_index('label')
lat.create_index('dim')
lat.create_index('det')
lat.create_index('level')
lat.create_index('aut')
lat.create_index('class_number')

print "finished indices"


## Main importing function

label_dict={}

def label_lookup(base_label):
    if base_label in label_dict:
        n=label_dict[base_label]+1
        label_dict[base_label]=n
        return n
    label_dict[base_label]=1
    return 1

def do_import(ll):
    dim,det,level,gram,density,hermite,minimum,kissing,shortest,aut,theta_series,class_number,genus_reps,name,comments = ll
    mykeys = ['dim','det','level','gram','density','hermite', 'minimum','kissing','shortest','aut','theta_series','class_number','genus_reps','name','comments']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]

    blabel = base_label(data['dim'],data['det'],data['level'], data['class_number'])
    data['base_label'] = blabel
    data['index'] = label_lookup(blabel)
    label= last_label(blabel, data['index'])
    data['label'] = label
 
    lattice = lat.find_one({'label': label})

    if lattice is None:
        print "new lattice"
        print "***********"
        print "check for isometries..."
        A=data['gram'];
        n=len(A[0])
        d=matrix(A).determinant()
        result=[B for B in lat.find({'dim': int(n), 'det' : int(d)}) if isom(A, B['gram'])]
        if len(result)>0:
            print "... the lattice with base label "+ blabel + " is isometric to " + str(result[0]['gram'])
            print "***********"
        else:
            lattice = data
    else:
        print "lattice already in the database"
        lattice.update(data)
    if saving:
        lat.update({'label': label} , {"$set": lattice}, upsert=True)



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
