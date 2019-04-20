# -*- coding: utf-8 -*-
r""" Import local field data.  

Imports from a json file directly to the database.

Data is imported directly to the table lf_fields 

"""

import sys
from sage.all import QQ
import re
import json

mypath = '../..'
sys.path.append(mypath)

from lmfdb import db

lf = db.lf_fields

def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)

def string2list(s):
    s = str(s)
    if s == '':
        return []
    return [int(a) for a in s.split(',')]

def string2slist(sl):
    sl = str(sl)
    sl = sl[1:-1]
    if sl == '':
        return []
    return [str(a) for a in sl.split(',')]

def make_slope_key(s):
    qs = QQ(s)
    sstring = str(qs*1.)
    sstring += '0'*14
    if qs < 10:
        sstring = '0'+sstring
    sstring = sstring[0:12]
    sstring += str(qs)
    return sstring

def top_slope(ent):
  sl = string2slist(ent['slopes'])
  if len(sl)>0:
    ent['top_slope'] = make_slope_key(sl[-1])
  elif int(ent['t'])>1:
    ent['top_slope'] = make_slope_key(1)
  else:
    ent['top_slope'] = make_slope_key(0)
  return ent

# Let us loop over input to load into a dictionary 
fnames = ['aut','c','coeffs','e','eisen', 'f', 'gal', 'galT', 'gms', 'hw', 'inertia', 'label', 'n', 'p', 'rf', 'slopes', 't', 'u', 'unram', 'subfields', 'gsm']

def prep_ent(l):
    l[6]=l[7]
    l[8]= str(l[8])
    l[19] = [[list2string(u[0]),u[1]] for u in l[19]]
    ent = dict(zip(fnames,l))
    ent = top_slope(ent)
    ent['rf'] = ent['rf']
    ent['coeffs'] = ent['coeffs']
    return ent

count=0

# loop over files, and in each, loop over lines
for path in sys.argv[1:]:
    print path
    fn = open(path)
    tot = 0
    outrecs = []
    for line in fn.readlines():
        line.strip()
        count += 1
        if re.match(r'\S',line):
            #print line
            l = json.loads(line)
            chck = lf.lookup(str(l[11])) # by label
            if chck is None: # we don't have it yet
                ent = prep_ent(l)
                outrecs.append(ent)
                #print str(ent['label'])
                tot += 1
    if len(outrecs)>0:
        lf.insert_many(outrecs)

#outrecs=outrecs[0:125]
#from pprint import pprint as pp
#pp(outrecs[0])
#lf.insert_many(outrecs)

print "Added %d records"% len(outrecs)


