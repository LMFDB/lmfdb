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

def get_WNF(label):
    if not label in WNFs:
        WNFs[label] = WebNumberField(label)
    return WNFs[label]

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

#note: could be optimised by precomputing the number of primes up to each norm
def truncation_bound(form_label):
    """Given the form label of an HMF f, return a bound X on the norm 
    of the primes at which the list of eigenvalues should be truncated 
    to ensure that the list of primes P for which a_P(f) contains every 
    prime up to X. Also return the total number of primes of norm up to X
    and the number of eigenvalues stored for f.
    """
    f = forms.find_one({'label':form_label})
    num_ap = len(f['hecke_eigenvalues'])
    field_label = f['field_label']
    WebF = get_WNF(field_label)
    F = WebF.K()
    X = 0
    n = 1
    prev_totprimes = 0
    totprimes = 0
    while True:
        n += 1
        p,f = n.is_prime_power(get_data=True)
        if f>0:
            Lp = F.primes_above(p, degree=f)
            totprimes += len(Lp)
            if num_ap < totprimes:
                return X, prev_totprimes, num_ap
            else:
                X = n
                prev_totprimes = totprimes

def check_form(form_label, dofix=False):
    print "\tchecking form " + form_label
    X,nb,nbap = truncation_bound(form_label)
    if nb<nbap:
        print "\tform needs fixing";
        f = forms.find_one({'label':form_label})
        ev = f['hecke_eigenvalues']
        ev = ev[0:nb]
        update = {"$set":{'hecke_eigenvalue':ev}}
        if dofix:
            forms.update_one({'label':form_label}, update)
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
        res = check_form(f['label'], dofix=dofix)
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
    for F in fields.find(query):
        nbforms, nbtodo, nbfixed = check_field(F['label'], dofix=dofix)
        print("Total so far: %s forms, %s needed fixing, %s fixed" % (totoforms, tottodo, totfixed))

