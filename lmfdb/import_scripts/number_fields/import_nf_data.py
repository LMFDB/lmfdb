# -*- coding: utf-8 -*-
r""" Import number field data.  Note: This code 
can be run on all files in any order. Even if you rerun this code 
on previously entered files, it should have no affect.  This code 
checks if the entry exists, if so returns that and updates with 
new information. If the entry does not exist then it creates it 
and returns that.

Initial version (Warwick 2014), modified 7/14
Adding zk, 7/15

Data is imported to the collection 'fields' in the database 'numberfields'.
The structure of the database entries is described in lmfdb/Database-info.

Each file should contain a single list, with each list entry being data for
a field: [field1, field2, ..., ]

Each field entry is a list:

  [coeffs, galois t, disc, r1, h, clgp, extras, reg, fu, nogrh, subs, reduced, zk]

where

   - coeffs: (list of ints) a polredabs'ed polynomial defining the field, so
       [3,2,1] represents x^2+2*x+3
   - galois t: (int) the T-number for the Galois group
   - disc:  (int) the field discriminant
   - r1: (int) the number of real places of the field
   - h: (int) the class number (if known)
   - clgp: (list of ints) the class group structure [a_1,a_2,...] where
        each a_i is a multiple of a_{i+1}
   - extras: (int 0 or 1) 1 if there is (optional) entries, 0 if not
   - reg: (float - optional) regulator
   - fu: (list of strings - optional) a list of fundimental units in 
        terms of a root of the defining polynomial where the root is 
        written as "a"
   - nogrh: (int 0 or 1) 1 indicates that everything above
        after class group does not depend on GRH
   - subs: list of subfields, such as 
           [[[3, 0, 1], 2], [[6, -2, 1, 0, 1], 1]]
        to indicate that there are two subfields isomorphic to the field
        defined by x^2+3 and one subfield isomorphic to the field
        defined by x^4+x^2-2*x+6
   - reduced: is the polynomial known to be polredabs'ed
   - zk: list of strings of integral basis elements in the variable a
"""

import sys, time
import bson
import sage.all
import re
import json
from sage.all import *

#from pymongo.connection import Connection
from pymongo.mongo_client import MongoClient
fields = MongoClient(port=37010).numberfields.fields

saving = True 

PR = PolynomialRing(QQ, 'a')
R = PolynomialRing(QQ, 'x')


#def coeffs(s):
#    return [a for a in s[1:-1].split(',')]

def sd(f):
  for k in f.keys():
    print '%s ---> %s'%(k, f[k])

def base_label(d,r1,D,ind):
    return str(d)+"."+str(r1)+"."+str(abs(D))+"."+str(ind)

def makeb(n,t):
  return bson.SON([('n', n), ('t', t)])

def makes(n,t):
  return '%02d,%03d'%(n,t)

def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def make_disc_key(D):
  s=1
  if D<0: s=-1
  Dz = D.abs()
  if Dz==0: D1 = 0
  else: D1 = int(Dz.log(10))
  return s, '%03d%s'%(D1,str(Dz))

def coeff_to_poly(c):
    return PolynomialRing(QQ, 'x')(c)

def web_latex(u):
  return "\( %s \)" % sage.all.latex(u)

def mismatch(oldval, newval, valtype):
    print "%s mismatch %s | %s"(valtype, str(oldval), str(newval))
    sys.exit()

# polredabs: if we want to compute on the fly
#def polredabs(pol):
#    return R(str(gp.polredabs(pol)))

# If we ever compute Galois groups here, set
#gp.set_default("new_galois_format", 1)

# only use for degree < 12
#def galt(pol):
#    return int(ZZ(gp.polgalois(str(pol))[3]))

def string2list(s):
  s = str(s)
  if s=='': return []
  return [int(a) for a in s.split(',')]

count = 0
#t = time.time()

def do_import(ll):
  global count
  print "Importing list of length %d" %(len(ll))
  for F in ll:
    count += 1
    coeffs, T, D, r1, h, clgp, extras, reg, fu, nogrh, subs, reduc = F
    print "%d: %s"%(count, F)
    mylen = len(F)
    pol = coeff_to_poly(coeffs)
    d = int(len(coeffs))-1
    D = ZZ(D)
    absD = abs(D)
    s, dstr = make_disc_key(D)
    # default for r1 is -1 if we should compute it
    sig = [int(r1), int((d-r1)/2)]
    data = {
        'degree': d,
        'disc_abs_key': dstr,
        'disc_sign': s,
        'coeffs': makels(coeffs),
        'signature': makels(sig)
    }
    # Default is that polynomials are polredabs'ed
    if reduc == 0:
        data['reduced'] = 0
    # See if we have it and build a label
    index=1
    is_new = True
    holdfield = ''
    for field in fields.find({'degree': d,
                 'signature': data['signature'],
                 'disc_abs_key': dstr}):
      index +=1
      if field['coeffs'] == data['coeffs']:
        holdfield = field # for variations where we modify data
        is_new = False
        break

    if is_new:
        print "new field"
        label = base_label(d,sig[0],absD,index)
        data['label'] = label
        data['ramps'] = [str(x) for x in prime_factors(D)]
        subs = [[makels(z[0]), z[1]] for z in subs]
        data['subs'] = subs
############
        if h>0:
            data['class_number'] = h
            data['class_group'] = makels(clgp)
        if extras>0:
            data['reg'] = reg
            fu = [web_latex(PR(str(u))) for u in fu]
            data['units'] = fu
        if nogrh==0:
            data['used_grh'] = True
        #print "entering %s into database"%info
        if saving:
            data['galois'] = makeb(d, T)
            fields.save(data)
    else:
        print "field already in database"

# Do the main work

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            do_import(l)

#sys.exit()

#from outlist  import li # this reads in the list called li


