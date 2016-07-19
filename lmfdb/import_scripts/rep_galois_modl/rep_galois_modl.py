# -*- coding: utf-8 -*-
r""" Import mod l modular forms.  

Note: This code can be run on all files in any order. Even if you 
rerun this code on previously entered files, it should have no affect.  
This code checks if the entry exists, if so returns that and updates 
with new information. If the entry does not exist then it creates it 
and returns that.

"""

import re
import json
import os
import sys
import gzip
from lmfdb.base import getDBConnection

C= getDBConnection()
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['mod_l_galois'].authenticate('editor', password)
reps = C['mod_l_galois'].reps


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


def base_label(base_field, dim, field_order, conductor):
    return ".".join([str(base_field), str(dim), str(field_order), str(conductor)])

def last_label(base_label, n):
    return ".".join([str(base_label),str(n)])

# The following create_index command checks if there is an index and updates it

reps.create_index('base_field')
reps.create_index('field')
reps.create_index('dim')
reps.create_index('conductor')
reps.create_index('type')


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
    base_field,dim,field,conductor,primes_conductor,weight,abs_irr,rep_type,image_type,image_label,image_at,image_order,degree_proj_field,projective_type,projective_label,bad_prime_list,good_prime_list,poly_ker,poly_proj_ker,related_objects = ll
    mykeys=['base_field','dim','field','conductor','primes_conductor',
'weight','abs_irr','rep_type','image_type','image_label','image_at',
'image_order','degree_proj_field','projective_type','projective_label','bad_prime_list','good_prime_list','poly_ker','poly_proj_ker','related_objects']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]
    data['field_char']=data['field'][0]
    data['field_deg']=data['field'][1]
    data['field_order']=pow(data['field_char'], data['field_deg'])
    blabel = base_label(data['base_field'],data['field_order'],data['dim'], data['conductor'])
    data['base_label'] = blabel
    data['index'] = label_lookup(blabel)
    label= last_label(blabel, data['index'])
    data['label'] = label
# we need still to organize this better with respect to tie breaks 

    rep = reps.find_one({'label': label})

    if rep is None:
        print "new mod l Galois representation"
        rep = data
    else:
        print "mod l Galois representation already in the database"
        rep.update(data)
    if saving:
        reps.update({'label': label} , {"$set": rep}, upsert=True)



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
