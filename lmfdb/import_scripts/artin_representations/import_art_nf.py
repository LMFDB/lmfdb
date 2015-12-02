import sys, time
import bson
import sage.all
import re
import json
from sage.all import *

#pw_filename = "../../../xyzzy"
#password = open(pw_filename, "r").readlines()[0].strip()

# find lmfdb and the top of the tree
mypath = os.path.realpath(__file__)
while os.path.basename(mypath) != 'lmfdb':
    mypath = os.path.dirname(mypath)
    # now move up one more time...
mypath = os.path.dirname(mypath)
sys.path.append(mypath)

# load the password file
import yaml
pw_dict = yaml.load(open(os.path.join(mypath, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']

# fire it up
#from lmfdb import base
#C= base.getDBConnection()
from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)

C['artin'].authenticate(username, password)

art=C.artin
rep=art.representations
nfgal=art.field_data

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


# Main programs

def artrepload(l):
  global count
  global old
  ar1 = rep.find_one({'Baselabel': l['Baselabel']})
  if ar1 is not None:
    #print "Old representation"
    old += 1
    if (count+old) % 100==0:
      print "%s new, %s old" %(str(count),str(old))
    return
  cond_key = make_cond_key(ZZ(l['Conductor']))
  l['Conductor_key'] = cond_key
  l['NFGal'] = makels(l['NFGal'])
  rep.save(l)
  count +=1
  if (count+old) % 100==0:
    print "%s new, %s old" %(str(count),str(old))
  return

def nfgalload(l):
  global count
  global old
  polstr = makels(l['Polynomial'])
  ff = nfgal.find_one({'Polynomial': polstr})
  if ff is not None:
    # print "Old field"
    old += 1
    if (count+old) % 100==0:
      print "%s new, %s old" %(str(count),str(old))
    return 
  l['Polynomial']=polstr
  artreps=l['ArtinReps']
  artreps=[{'Baselabel': z[0][0], 'GalConj': z[0][1], 'CharacterField': z[1],
    'Character': z[2]} for z in artreps]
  l['ArtinReps']=artreps
  nfgal.save(l)
  count +=1
  if (count+old) % 100==0:
    print "%s new, %s old" %(str(count),str(old))
  return


# processing file names
for path in sys.argv[1:]:
    print path
    count = 0
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    if re.match(r'^nfgal', filename):
      case = 'nfgal'
    if re.match(r'^art', filename):
      case = 'art rep'
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
	    if case == 'nfgal':
	      nfgalload(l)
	    if case == 'art rep':
	      artrepload(l)


