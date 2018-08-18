#!/usr/local/bin/sage -python
import sys, time, os
assert time
import bson
assert bson
import re
import json
from sage.all import ZZ

# find lmfdb and the top of the tree
mypath = os.path.realpath(__file__)
while os.path.basename(mypath) != 'lmfdb':
    mypath = os.path.dirname(mypath)
    # now move up one more time...
#mypath = os.path.dirname(mypath)
sys.path.append(mypath)
sys.path.append(mypath+'/data_mgt/utilities')

from rewrite import reindex_collection


# load the password file
import yaml
pw_dict = yaml.load(open(os.path.join(mypath, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']

# fire it up
#from lmfdb import base
#C= base.getDBConnection()
from pymongo.mongo_client import MongoClient
C= MongoClient(host='lmfdb-ib:37010')

C['artin'].authenticate(username, password)

art=C.artin
rep=art.representations_new
nfgal=art.field_data_new

count = 0
old = 0

#ASC = pymongo.ASCENDING
#rep.create_index([('Dim', ASC), ('Hide', ASC),('Conductor_key', ASC)])
#rep.create_index([('Hide', ASC), ('Conductor_key',ASC)])
#rep.create_index([('Hide', ASC), ('Galois_nt',ASC)])
#rep.create_index('NFGal')
#rep.create_index('Baselabel')
#nfgal.create_index('Polynomial')


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
batchsize = 10000

def artrepload(l):
  global count
  global old
  global outrecs
  global batchsize
  #ar1 = rep.find_one({'Baselabel': l['Baselabel']})
  #if ar1 is not None:
    #print "Old representation"
  #  old += 1
  #  if (count+old) % 100==0:
  #    print "%s new, %s old" %(str(count),str(old))
  #  return
  cond_key = make_cond_key(ZZ(l['Conductor']))
  l['Conductor_key'] = cond_key
  l['NFGal'] = makels(l['NFGal'])
  l['GaloisConjugates'] = [fix_local_factors(z) for z in l['GaloisConjugates']]
  # Extract containing representation from the label
  cont = l['Baselabel'].split('.')[2]
  l['Container'] = cont
  #print str(l)
  count +=1
  outrecs.append(l)
  if len(outrecs) > batchsize:
    rep.insert_many(outrecs)
    outrecs=[]
  #rep.save(l)
  if (count+old) % 100==0:
    print "%s new, %s old" %(str(count),str(old))
  return

def nfgalload(l):
  global count
  global old
  global outrecs
  global batchsize
  polstr = makels(l['Polynomial'])
  #ff = nfgal.find_one({'Polynomial': polstr})
  #if ff is not None:
    # print "Old field"
  #  old += 1
  #  if (count+old) % 100==0:
  #    print "%s new, %s old" %(str(count),str(old))
  #  return 
  l['Polynomial']=polstr
  artreps=l['ArtinReps']
  artreps=[{'Baselabel': z[0][0], 'GalConj': z[0][1], 'CharacterField': z[1],
    'Character': z[2]} for z in artreps]
  l['ArtinReps']=artreps
  outrecs.append(l)
  if len(outrecs) > batchsize:
    nfgal.insert_many(outrecs)
    outrecs=[]
  #nfgal.save(l)
  count +=1
  if (count+old) % 100==0:
    print "%s new, %s old" %(str(count),str(old))
  return


# processing file names
for path in sys.argv[1:]:
    print path
    count = 0
    filename = os.path.basename(path)
    fn = open(path)
    if re.match(r'^nfgal', filename):
      case = 'nfgal'
      if 'field_data_new' in art.collection_names():
        print "Dropping field data new"
        art.field_data_new.drop()
    if re.match(r'^art', filename):
      case = 'art rep'
      if 'representations_new' in art.collection_names():
        print "Dropping representations new"
        art.representations_new.drop()
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
    if case == 'nfgal':
      reindex_collection(art, 'field_data', 'field_data_new')
    if case == 'art rep':
      reindex_collection(art, 'representations', 'representations_new')
    fn.close()

