# -*- coding: utf-8 -*-
r""" Import data from Alex Bartel on the Galois module structure
of unit groups of Galois number fields.  This script imports information
on the Galois modules themselves.

Initial version 7/14

Data is imported to the collection 'fields' in the database 'numberfields'.
The structure of the database entries is described in lmfdb/Database-info.

Each file is a list of lists
  [[n,t], name, generator matrices...]

The number of generator matrices depends on the group

This expects there to be one group per file

Database entries have fields n, t, index, name, gens

The first entry should be the trivial representation, and it has a fourth
argument 1=complete, 0=incomplete (inf many), -1 =incomplete (just partial
list)

"""

import sys
import re
import json
import gzip
from sage.all import os

from pymongo.mongo_client import MongoClient
gmods = MongoClient(port=37010).transitivegroups.Gmodules

def sd(f):
  for k in f.keys():
    print '%s ---> %s'%(k, f[k])

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)

def do_import(ll):
  global count
  #print "Importing data %s" % str(ll)
  data = {}
  data['n'] = ll[0][0]
  data['t'] = ll[0][1]
  data['name'] = ll[1]
  data['index'] = count
#  gens = []
#  for j in range(2,len(ll)):
#    gens.append(ll[j])
#  data['gens'] = gens
  data['gens'] = ll[2]
  data['dim']= len(ll[2][0][1][0])
  data['complete'] = -1
  if len(ll)>3:
    data['complete'] = ll[3]
  gmods.save(data)
  #print data
  count += 1

# Do the main work

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    count = 0
    for line in fn.readlines():
        line = line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)

