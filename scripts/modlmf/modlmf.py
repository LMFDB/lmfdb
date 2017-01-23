# -*- coding: utf-8 -*-
r""" Import mod l modular forms.  

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
C['mod_l_eigenvalues'].authenticate('editor', password)
modlmf = C['mod_l_eigenvalues'].modlmf

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


def base_label(characteristic, deg, level, weight, dirchar):
    field=str(characteristic)
    dirchar_index=str(dirchar).split('.')[2]
    if int(deg)!=1:
        field=str(characteristic)+"e"+str(deg)
    return ".".join([field,str(level),str(weight),dirchar_index])

def last_label(base_label, n):
    return ".".join([str(base_label),str(n)])

# The following create_index command checks if there is an index on
# label, dimension, determinant and level. 


modlmf.create_index('characteristic')
modlmf.create_index('deg')
modlmf.create_index('level')
modlmf.create_index('weight_grading')
modlmf.create_index('dirchar')

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
    characteristic,deg,level,weight_grading,reducible,cuspidal_lift,dirchar,atkinlehner,n_coeffs,coeffs,ordinary,min_theta_weight,theta_cycle = ll
    mykeys =['characteristic','deg','level','weight_grading','reducible','cuspidal_lift','dirchar','atkinlehner','n_coeffs','coeffs','ordinary','min_theta_weight','theta_cycle']
    data = {}
    for j in range(len(mykeys)):
        data[mykeys[j]] = ll[j]

    blabel = base_label(data['characteristic'],data['deg'],data['level'], data['weight_grading'], data['dirchar'])
    data['base_label'] = blabel
    data['index'] = label_lookup(blabel)
    label= last_label(blabel, data['index'])
    data['label'] = label
# we need still to organize this better with respect to tie breaks 

    modl_mf = modlmf.find_one({'label': label})

    if modl_mf is None:
        print "new mod l modular form"
        modl_mf = data
    else:
        print "mod l modular form already in the database"
        modl_mf.update(data)
    if saving:
        modlmf.update({'label': label} , {"$set": modl_mf}, upsert=True)



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
