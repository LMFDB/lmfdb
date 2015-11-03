# -*- coding: utf-8 -*-
r""" Import integral lattices data.  

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

"""

import sys, time
import re
import json
import sage.all
from sage.all import os

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
C['Lattices'].authenticate('editor', '282a29103a17fbad')
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
        lattice = data
    else:
        print "lattice already in the database"
        lattice.update(data)
    if saving:
        lat.save(lattice)

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
