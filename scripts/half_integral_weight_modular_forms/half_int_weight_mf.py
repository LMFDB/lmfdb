# -*- coding: utf-8 -*-
r""" Import half-integral weight modular form data.  

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

The rest of this should be updated for modular forms:

Data is imported to the collection 'fields' in the database 'numberfields'.
The structure of the database entries is described in lmfdb/Database-info.

Each file should contain a single list, with each list entry being data for
a field: [field1, field2, ..., ]

Each field entry is a list:

  [coeffs, galois t, disc, r1, h, clgp, extras, reg, fu, nogrh, subs, reduced]

where

   - coeffs: (list of ints) a polredabs'ed polynomial defining the field, so
       [3,2,1] represents x^2+2*x+3
   - clgp: (list of ints) the class group structure [a_1,a_2,...] where
"""

import sys
import re
import json
import os
import gzip

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['halfintegralmf'].authenticate('editor', password)
forms = C.forms


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

def base_label(level,weight,character):
    return str(level)+"."+str(weight)+"_2."+character

## Main importing function

def do_import(ll):
    level,weight,character,dim,dimtheta,thetas,newpart0  = ll
    mykeys = ['level', 'weight', 'character', 'dim', 'dimtheta', 'thetas', 'newpart']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
    newpart = []
    for mf_label,nf_label,dim_image,half_forms in newpart0:
        entry = {'mf_label' : mf_label, 'nf_label' : nf_label, 'dim_image' : dim_image, 'half_forms' : half_forms}
        newpart.append(entry)
    data['newpart'] = newpart
        
    label = base_label(data['level'],data['weight'],data['character'])
    data['label'] = label
    form = forms.find_one({'label': label})

    if form is None:
        print "new form"
        form = data
    else:
        print "form already in database"
        form.update(data)
    if saving:
        forms.save(form)

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


