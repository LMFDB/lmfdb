# -*- coding: utf-8 -*-
r""" Check presence of conjugates in table of Hilbert modular forms, and adds them if not present.
Initial version (University of Warwick 2015) Aurel Page

"""

#import os.path
import sys
sys.path.append("../..");
#import gzip
#import re
#import time
#import os
#import random
#import glob
import pymongo
from lmfdb import base
from lmfdb.website import dbport
from lmfdb.WebNumberField import *
#from sage.rings.all import ZZ

print "calling base._init()"
dbport=37010
base._init(dbport, '')
print "getting connection"
conn = base.getDBConnection()
print "setting hmfs, fields and forms"
hmfs = conn.hmfs
fields = hmfs.fields
forms = hmfs.forms

def findvar(L):
    for x in L:
        for c in x:
            if c.isalpha():
                return c.encode()
    return None

def niceideals(F, ideals): #HNF + sage ideal + label
    var = findvar(ideals)
    R = PolynomialRing(QQ,var)
    nideals = []
    ilabel = 1
    norm = ZZ(0)
    for i in range(len(ideals)):
        idlstr = ideals[i][1:-1].replace(' ','').split(',')
        N = ZZ(idlstr[0]) #norm
        n = ZZ(idlstr[1]) #smallest integer
        P = R(idlstr[2].encode()) #other generator as a polynomial
        gen = P(F.gen())
        idl = F.ideal(n,gen)
        assert idl.norm() == N and idl.smallest_integer() == n
        if N != norm:
            ilabel = ZZ(1)
            norm = N
        label = N.str() + '.' + ilabel.str()
        hnf = idl.pari_hnf().python()
        nideals.append([hnf, idl, label])
        ilabel += 1
    return nideals

def conjideals(ideals, auts): #(label,g) -> label
    cideals = {}
    ideals.sort()
    for ig in range(len(auts)):
        g = auts[ig]
        gideals = copy(ideals)
        for i in range(len(gideals)):
            gideals[i][0] = g(gideals[i][1]).pari_hnf().python()
        gideals.sort()
        for i in range(len(gideals)):
            cideals[(gideals[i][2],ig)] = ideals[i][2]
    return cideals

def fldlabel2conjdata(label):
    data = {}
    Fdata = fields.find_one({'label':label})
    assert Fdata is not None
    WebF = WebNumberField(label)
    assert WebF is not None
    F = WebF.K()
    data['F'] = F
    auts = F.automorphisms()
    if len(auts) == 1: #no nontrivial automorphism, nothing to do
        return None
    auts = [g for g in auts if not g.is_identity()]
    data['auts'] = auts
    ideals = niceideals(F, Fdata['ideals'])
    data['ideals'] = ideals
    cideals = conjideals(ideals, auts)
    data['conjideals'] = cideals
    primes = niceideals(F, Fdata['primes'])
    data['primes'] = primes
    cprimes = conjideals(primes, auts)
    data['conjprimes'] = cprimes
    return data

def conjform(f, ig, cideals, cprimes): #ig index of g in auts
    if f['is_basechange']:
        return None
    fg = copy(f)
    return None

def checkadd_conj(label, levelbound=oo):
    return None
