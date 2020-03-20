#!/usr/local/bin/sage -python
from __future__ import print_function
import sys, os
import re
import json
from sage.all import ZZ

# find lmfdb and the top of the tree
mypath = os.path.realpath(__file__)
while os.path.basename(mypath) != 'lmfdb':
    mypath = os.path.dirname(mypath)
    # now move up one more time...
sys.path.append(mypath)

from lmfdb import db

rep=db.artin_reps
nfgal=db.artin_field_data

count = 0
old = 0

#utilities

# turn poly coefs into a string
def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

# turn a conductor into a sortable string
# this uses length 4 prefix
def make_cond_key(D):
  D1 = int(D.log(10))
  return '%04d%s'%(D1,str(D))

maxint = (2**63)-1

def int_or_string(a):
  if abs(a)< maxint:
    return a
  return str(a)

def fix_local_factors(gconj):
  gconj['LocalFactors'] = [ [ [int_or_string(a) for a in b ] for b in c] for c in gconj['LocalFactors']]
  return gconj

# Main programs

outrecs = []

def artrepload(l):
  global count
  global old
  global outrecs
  ar1 = rep.lucky({'Baselabel': l['Baselabel']})
  if ar1 is not None:
    old += 1
    if (count+old) % 100==0:
      print("%s new, %s old" %(str(count),str(old)))
    return 
  l['Conductor'] = ZZ(l['Conductor'])
  l['GaloisConjugates'] = [fix_local_factors(z) for z in l['GaloisConjugates']]
  # Extract containing representation from the label
  cont = l['Baselabel'].split('.')[2]
  l['Container'] = cont
  for s in ['BadPrimes', 'HardPrimes']:
    l[s] = [int(z) for z in l[s]]
  l['Galn'] = l['Galois_nt'][0]
  l['Galt'] = l['Galois_nt'][1]
  del l['Galois_nt']
  l['GalConjSigns'] = [z['Sign'] for z in l['GaloisConjugates']]
  #print str(l)
  count +=1
  outrecs.append(l)
  if (count+old) % 100==0:
    print("%s new, %s old" %(str(count),str(old)))
  return

def nfgalload(l):
  global count
  global old
  global outrecs
  ff = nfgal.lucky({'Polynomial': l['Polynomial']})
  if ff is not None:
    old += 1
    if (count+old) % 100==0:
      print("%s new, %s old" %(str(count),str(old)))
    return 

  artreps=l['ArtinReps']
  artreps=[{'Baselabel': z[0][0], 'GalConj': z[0][1], 'CharacterField': z[1],
    'Character': z[2]} for z in artreps]
  l['ArtinReps']=artreps
  l['Size'] = int(l['Size'])
  outrecs.append(l)
  count +=1
  if (count+old) % 100==0:
    print("%s new, %s old" %(str(count),str(old)))
  return


# processing file names
for path in sys.argv[1:]:
    print(path)
    count = 0
    old = 0
    filename = os.path.basename(path)
    fn = open(path)
    if re.match(r'^nfgal', filename):
      case = 'nfgal'
    if re.match(r'^art', filename):
      case = 'art rep'
    for line in fn.readlines():
        line = line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            if case == 'nfgal':
              nfgalload(l)
            if case == 'art rep':
              artrepload(l)
    if outrecs:
        if case == 'nfgal':
          nfgal.insert_many(outrecs)
        if case == 'art rep':
          rep.insert_many(outrecs)
    print("%s new, %s old" %(str(count),str(old)))
    fn.close()

