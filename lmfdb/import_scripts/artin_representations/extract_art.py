# This is for generating information for computing Artin L-functions
# Run it with 
#    sage -python extract_art.py artinlabel count
#
# where artinlabel is the label for a specific artin representation
# and count is a positive integer.  It will produce a file with the
# same name as the label containing:
# n
# list of encoded polynomials
# "count" more lines containing positive integers
#
# Here, n = a field where we factored the local factor, Q(\zeta_n)
# Each polynomial is encoded as [a_1, a_2, ..., a_m] to mean the
# reciprocal roots are \zeta_n^a_i=e(a_i/n)
# On the remaining lines, the value is an index back into the list
# of polynomials so that if the j-th of these lines is k, then
# the local factor of the j-th prime is the k-th polynomial

import sys, time, os
assert time

# check arguments first

if len(sys.argv) != 3:
    print "I take two arguments, the label and a count"
    print "Don't make me tell you again."
    sys.exit()

argv=sys.argv
label=argv[1]

# internally, we will call the count "bound"
try:
    bound=int(argv[2])
    if bound is None or bound<1:
        print "Bound is not valid"
        sys.exit()
except:
    print "Bound is not valid"
    sys.exit()

import re
assert re
from sage.all import next_prime, ZZ, QQ, lcm, NumberField

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
from lmfdb import base
assert base
from lmfdb.artin_representations.math_classes import ArtinRepresentation

from pymongo.mongo_client import MongoClient
C= MongoClient(host='lmfdb-ib:37010')
C['artin'].authenticate(username, password)

art=C.artin
rep=art.representations
nfgal=art.field_data

#utilities

# turn poly coefs into a string
def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def myroots(pol, n, zeta):
    rts=[]
    j=0
    RR = pol.parent()
    while pol.degree()>0 and j<n:
        if pol(zeta**j)==0:
            rts.append((n-j) % n)
            pol = RR(pol/(y-zeta**j))
        else:
            j += 1
    return rts


# select the ones we want
#artargs = {'Dim': {'$gte': 2, '$lte': 9}}
#allarts=rep.find(artargs)

#arep = rep.find_one({'Dim': {'$gte': 2}})
#ar = ArtinRepresentation(str(arep['Baselabel'])+'c1')
#ar = ArtinRepresentation('2.2e3_3e2.6t5.1c1')

baselabel=label.split('c')
a = rep.find_one({'Baselabel': baselabel[0]})


ar=ArtinRepresentation(label)

outfile=open(label, 'w')

cf=a['CharacterField']
cfz = ZZ(cf)
nf = ar.nf()
nfcc = nf.conjugacy_classes()
nfcc = [int(z.order()) for z in nfcc]
nfcc = lcm(nfcc)
if not cfz.divides(nfcc):
    print "Failure "+str(cfz)+" divides "+str(nfcc)+" from "+label
    sys.exit()
R,x = QQ['x'].objgen()
pol1 = R.cyclotomic_polynomial(nfcc)
K,z=NumberField(R.cyclotomic_polynomial(nfcc),'z').objgen()
RR,y = K['y'].objgen()
zsmall = z**(nfcc/cfz)
allpols = [sum(y**k * sum(pp[k][j] * zsmall**j for j in range(len(pp[k]))) for k in range(len(pp))) for pp in ar.local_factors_table()]
allroots = [myroots(pp, nfcc, z) for pp in allpols]

outfile.write(str(nfcc)+"\n")
outfile.write(str(allroots)+"\n")
j=0
p=1
while j<bound:
    p = next_prime(p)
    outfile.write(str(ar.any_prime_to_cc_index(p))+"\n")
    j+=1
  
#plist = [ar.any_prime_to_cc_index(p) for p in primes_first_n(bound)]
#for j in plist:
#    outfile.write(str(j)+"\n")

outfile.close()
