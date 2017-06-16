# -*- coding: utf-8 -*-
r""" Script written just for use at June 2017 LMFDB workshop at Warwick.  Output is text files describing the number of a_p that are in that database.  Modify as needed.
Initial version Dan Yasaki, modified by Aurel Page (2017)

"""

import os
sys.path.append("../..");
from pymongo.mongo_client import MongoClient
from lmfdb.WebNumberField import WebNumberField

print "getting connection"
C = MongoClient(port=int(37010))
C['admin'].authenticate('lmfdb','lmfdb')
hmfs = C.hmfs
forms = hmfs.forms
fields = hmfs.fields
flabels = fields.distinct('label')

print "authenticating on the hmfs database"
import yaml
pw_dict = yaml.load(open(os.path.join(os.getcwd(), os.pardir, os.pardir, "passwords.yaml")))
username = pw_dict['data']['username']
password = pw_dict['data']['password']
C['hmfs'].authenticate(username, password) ## read/write on hmfs

#Caching WebNumberFields
WNFs = {}
nf_data = {}

def get_WNF(label):
    if not label in WNFs:
        WNFs[label] = WebNumberField(label)
    return WNFs[label]

def get_nf_data(label):
    """List of allowed numbers of eigenvalues for an HMF over that field.
    """
    if not label in nf_data:
        WebF = get_WNF(label)
        F = WebF.K()
        Fhmf = fields.find_one({'label':label})
        primes = Fhmf['primes']
        N = len(primes)
        last = primes[N-1]
        last = last.encode()[1:]
        last = last.split(",")[0]
        last = ZZ(last)
        L = [0]
        for n in range(last+1):
            p,f = ZZ(n).is_prime_power(get_data=True)
            if f > 0:
                Lp = F.primes_above(p, degree=f)
                L.append(L[len(L)-1]+len(Lp))
        L.append(Infinity)
        nf_data[label] = L
    return nf_data[label]

def find_discrepancies():
    with open('numap2-done-fields.txt','w') as donefile:
        with open('hmf-numap-Np-missing.txt','w') as datafile:
            for flabel in flabels:
                print flabel
                F = fields.find_one({'label':flabel})
                primes = F['primes']
                for f in forms.find({'field_label':flabel}):
                    num_ap = len(f['hecke_eigenvalues'])
                    discrepancy = len(primes) - num_ap
                    if discrepancy != 0:
                      print f['label']
                      Np = F['primes'][num_ap - 1].split(',')[0][1:]  #already a string
                      datafile.write(':'.join([f['label'],str(num_ap),Np,str(discrepancy)])+'\n')
                donefile.write(flabel+'\n')
                donefile.flush()

def binary_search(L,x):
    N = len(L)
    #this case happens if the form has all the eigenvalues
    if x == L[N-2]:
        return x
    i = 0
    j = N-1
    while j-i > 1:
      k = (i+j)//2
      if x < L[k]:
        j = k
      else:
        i = k
    return L[i]

#note: could be optimised by precomputing the number of primes up to each norm
def truncation_bound(f):
    """Given an HMF f or its label, compute a bound X on the norm 
    of the primes at which the list of eigenvalues should be truncated 
    to ensure that the list of primes P for which a_P(f) contains every 
    prime up to X. Return the total number of primes of norm up to X
    and the number of eigenvalues stored for f.
    """
    if type(f) == str:
        f = forms.find_one({'label':f})
    num_ap = len(f['hecke_eigenvalues'])
    field_label = f['field_label']
    data = get_nf_data(field_label)
    nb = binary_search(data,num_ap)
    assert abs(nb - num_ap) <= int(f['label'].split('.')[0]) - 1
    return nb,num_ap

def check_form(f, dofix=False):
    if type(f) == str:
        f = forms.find_one({'label':f})
    form_label = f['label']
    print "\tchecking form " + form_label
    nb, nbap = truncation_bound(f)
    if nb < nbap:
        print ("\tform needs fixing: %s eigenvalues -> truncate at %s eigenvalues" % (nbap, nb));
        ev = f['hecke_eigenvalues']
        ev = ev[0:nb]
        update = {"$set":{'hecke_eigenvalues':ev}}
        if dofix:
            res = forms.update_one({'label':form_label}, update)
            assert res.acknowledged and res.modified_count == 1
            print "\tform fixed";
            return 2
        else:
            return 1
    return 0

def check_field(field_label, dofix=False):
    print "\nchecking field " + field_label
    nbforms = 0
    nbtodo = 0
    nbfixed = 0
    for f in forms.find({'field_label':field_label}):
        res = check_form(f, dofix=dofix)
        nbforms += 1
        if res>0:
            nbtodo += 1
        if res==2:
            nbfixed += 1
    print("%s forms, %s forms needed fixing, %s forms fixed" % (nbforms, nbtodo, nbfixed)) 
    return nbforms, nbtodo, nbfixed

def check_all(degree, disc_bound=Infinity, dofix=False):
    totforms = 0
    tottodo = 0
    totfixed = 0
    query = {}
    query['degree'] = int(degree)
    if disc_bound < Infinity:
        query['discriminant'] = {"$lte":int(disc_bound)}
    LF = fields.find(query)
    Llab = [F['label'] for F in LF]
    for field_label in Llab:
        nbforms, nbtodo, nbfixed = check_field(field_label, dofix=dofix)
        print("Total so far: %s forms, %s needed fixing, %s fixed" % (totforms, tottodo, totfixed))
