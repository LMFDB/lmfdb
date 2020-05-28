#!/usr/local/bin/sage -python

# This version writes the data to a file, deletes all records from the database,
# then reloads from the files. 
from __future__ import print_function
from six import text_type
import sys
import os
import re
import json
import numpy

# find lmfdb and the top of the tree
mypath = os.path.realpath(__file__)
while os.path.basename(mypath) != 'lmfdb':
    mypath = os.path.dirname(mypath)
    # now move up one more time...
#mypath = os.path.dirname(mypath)
sys.path.append(mypath)

from lmfdb import db
from lmfdb.backend.encoding import copy_dumps

rep=db.artin_reps
nfgal=db.artin_field_data

count = 0

nottest = False
nottest = True

#utilities

# turn poly coefs into a string
def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

maxint = (2**63)-1

def int_or_string(a):
  if abs(a)< maxint:
    return a
  return str(a)

def fix_local_factors(gconj):
  gconj['LocalFactors'] = [ [ [int_or_string(a) for a in b ] for b in c] for c in gconj['LocalFactors']]
  return gconj

# Main programs

# There are two parts since we need to deal with two files/databases
# The two functions below take our for one entry as a dictionary, and reformats
# the dictionary

outrecs = []

def artrepload(l):
  global count
  global outrecs
  l['Conductor'] = int(l['Conductor'])
  l['GaloisConjugates'] = [fix_local_factors(z) for z in l['GaloisConjugates']]
  sortord = numpy.argsort([z['GalOrbIndex'] for z in l['GaloisConjugates']])
  l['GaloisConjugates'] = [l['GaloisConjugates'][z] for z in sortord]
  assert [z['GalOrbIndex'] for z in l['GaloisConjugates']] == [u for u in range(1,len(l['GaloisConjugates'])+1)]
  # Extract containing representation from the label
  cont = l['Baselabel'].split('.')[2]
  l['Container'] = cont
  for s in ['BadPrimes', 'HardPrimes']:
    l[s] = [int(z) for z in l[s]]
  l['Galn'] = l['Galois_nt'][0]
  l['Galt'] = l['Galois_nt'][1]
  l['GaloisLabel'] = "%sT%s"%(str(l['Galois_nt'][0]),str(l['Galois_nt'][1]))
  del l['Galois_nt']
  l['GalConjSigns'] = [z['Sign'] for z in l['GaloisConjugates']]
  l['Dets'] = [z['Det'] for z in l['GaloisConjugates']]
  for j in range(len(l['GaloisConjugates'])):
    del l['GaloisConjugates'][j]['Det']
  aproj = l['Proj']
  aproj = {'GAP': aproj[0], 'nTj': aproj[1], 'Polynomial': aproj[2]}
  l['Proj'] = aproj
  chival = int(l['Chi_of_complex'])
  dim = int(l['Dim'])
  minusones = (dim - chival)/2
  iseven = (minusones % 2) == 0
  l['Is_Even'] = iseven
  #print str(l)
  count +=1
  outrecs.append(l)
  if count % 10000==0:
    print("Count %s" % count)
  return

def nfgalload(l):
  global count
  global outrecs

  artreps=l['ArtinReps']
  artreps=[{'Baselabel': z[0][0], 'GalConj': z[0][1], 'CharacterField': z[1],
    'Character': z[2]} for z in artreps]
  l['ArtinReps']=artreps
  l['Size'] = int(l['Size'])
  outrecs.append(l)
  count +=1
  if count % 10000==0:
    print("Count %s" % count)
  return

def strx(val, k):
    if k == 'Algorithm':
        return '"'+str(val)+'"'
    if k == 'Baselabel':
        return '"'+str(val)+'"'
    return str(val)

def fixdict(d):
    kys = d.keys()
    start = ['"'+str(k)+'": '+strx(d[k],k) for k in kys]
    return "{"+','.join(start)+"}"

def fixlist(d):
    return [str(k) for k in d]

reloadme = []
# processing file names
for path in sys.argv[1:]:
    print(path)
    count = 0
    outrecs = []
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
    # We have loaded the file, now dump it
    if outrecs:
        if case == 'nfgal':
            fnout = open("nfgal.dump", "w")
            cols = nfgal.col_type
            del cols['id']
            head1 = [str(z) for z in cols.keys()]
            fnout.write('|'.join(head1)+"\n")
            fnout.write('|'.join([str(cols[z]) for z in head1])+"\n\n")
            for ent in outrecs:
                for kk in head1:
                    if isinstance(ent[kk], text_type):
                        ent[kk] = str(ent[kk])
                    if not isinstance(ent[kk], str):
                        ent[kk] = json.dumps(ent[kk])
                fnout.write('|'.join([ent[z].replace("'",'"') for z in head1])+'\n')
            fnout.close()
            reloadme.append('nfgal')
        if case == 'art rep':
            fnout = open("art.dump", "w")
            cols = rep.col_type
            del cols['id']
            head1 = [str(z) for z in cols.keys()]
            fnout.write('|'.join(head1)+"\n")
            fnout.write('|'.join([str(cols[z]) for z in head1])+"\n\n")
            for ent in outrecs:
                for kk in head1:
                    if isinstance(ent[kk], text_type):
                        ent[kk] = str(ent[kk])
                    if kk == 'Dets':
                        ent[kk] = copy_dumps(ent[kk], 'text[]', recursing=False)
                    elif not isinstance(ent[kk], str):
                        ent[kk] = json.dumps(ent[kk])
                fnout.write('|'.join([ent[z] for z in head1])+'\n')
            fnout.close()
            reloadme.append('art')
    print("%s entries" % count)
    fn.close()

if nottest:
  for k in reloadme:
    if k == 'nfgal':
        nfgal.reload('nfgal.dump', sep='|')
    if k == 'art':
        rep.reload('art.dump', sep='|')
