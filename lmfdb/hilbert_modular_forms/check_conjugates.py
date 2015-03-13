# -*- coding: utf-8 -*-
r""" Check presence of conjugates in table of Hilbert modular forms, and adds them if not present.

Assumes that the set of primes is a subset of the set of ideals.

Warning ; will not work with non-parallel weights because there is no
description of which weight corresponds to which embedding. (ordered by image of
generator in R ?)
Note that labels contain no information about weight.

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

def str2fieldelt(R,F,strg):
    P = R(strg.encode())
    return P(F.gen())

def str2ideal(R,F,strg):
    idlstr = strg[1:-1].replace(' ','').split(',')
    N = ZZ(idlstr[0]) #norm
    n = ZZ(idlstr[1]) #smallest integer
    gen = str2fieldelt(R,F,idlstr[2]) #other generator
    idl = F.ideal(n,gen)
    return N,n,idl,gen

def niceideals(F, ideals): #HNF + sage ideal + label
    var = findvar(ideals)
    R = PolynomialRing(QQ,var)
    nideals = []
    ilabel = 1
    norm = ZZ(0)
    for i in range(len(ideals)):
        N,n,idl,_ = str2ideal(R,F,ideals[i])
        assert idl.norm() == N and idl.smallest_integer() == n
        if N != norm:
            ilabel = ZZ(1)
            norm = N
        label = N.str() + '.' + ilabel.str()
        hnf = idl.pari_hnf().python()
        nideals.append([hnf, idl, label])
        ilabel += 1
    return nideals,R

def conjideals(ideals, auts): #(label,g) -> label
    cideals = {}
    ideals = copy(ideals)
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
    ideals,R = niceideals(F, Fdata['ideals'])
    data['ideals'] = ideals
    data['R'] = R
    cideals = conjideals(ideals, auts)
    data['conjideals'] = cideals
    primes,_ = niceideals(F, Fdata['primes'])
    #data['primes'] = primes
    primes = [prm[2] for prm in primes]
    cprimes = [[primes.index(cideals[(prm,ig)]) for prm in primes] for ig in range(len(auts))]
    data['conjprimes'] = cprimes
    return data

def conjstringideal(F,R,stridl,g):
    N,n,_,gen = str2ideal(R,F,stridl)
    P = R(g(gen).polynomial())
    return '[' + str(N) + ',' + str(n) + ',' + str(P) + ']'

def conjform(f, g, ig, cideals, cprimes, F, R): #ig index of g in auts
    if f['is_base_change'][0:3] == 'yes':
        return None
    fg = copy(f)

    fg['level_label'] = cideals[(f['level_label'],ig)]
    fg['short_label'] = fg['level_label'] + '-' + fg['label_suffix']
    fg['label'] = fg['field_label'] + '-' + fg['short_label']

    fg['level_ideal'] = conjstringideal(F,R,f['level_ideal'],g)

    fg['AL_eigenvalues'] = [[conjstringideal(F,R,x[0],g),x[1]] for x in f['AL_eigenvalues']]

    H = f['hecke_eigenvalues']
    Hg = copy(f['hecke_eigenvalues'])
    fg['hecke_eigenvalues'] = Hg
    for i in range(len(H)):
        Hg[cprimes[ig][i]] = H[i]

    del fg['_id']
    return fg

def checkadd_conj(label, levelbound=oo):
    count = 0
    if levelbound == oo:
        ftoconj = forms.find({'field_label':label})
    else:
        ftoconj = forms.find({'field_label':label, 'level_norm':{"$lte":int(levelbound)}})
    print(str(ftoconj.count()) + " forms to examine.")
    if ftoconj.count() == 0:
        return None
    print("Ideals precomputations...")
    data = fldlabel2conjdata(label)
    print("...done.\n")
    auts = data['auts']
    cideals = data['conjideals']
    cprimes = data['conjprimes']
    F = data['F']
    R = data['R']
    for f in ftoconj:
        for g in auts:
            fg = conjform(f, g, auts.index(g), cideals, cprimes, F, R)
            if fg != None:
                fgdb = forms.find_one({'label':fg['label']})
                if fgdb == None:
                    print("conjugate not present, adding it : "+fg['label'])
                    forms.insert(fg)
                    count += 1
    print("\nAdded "+str(count)+" new conjugate forms.")
    return None

