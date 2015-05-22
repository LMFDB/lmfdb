# -*- coding: utf-8 -*-
r""" Check presence of conjugates in table of Hilbert modular forms, and adds them if not present.

Assumes that the set of primes is a subset of the set of ideals.

Warning ; will not work with non-parallel weights because there is no
description of which weight corresponds to which embedding. (ordered by image of
generator in R ?)
Note that labels contain no information about weight.

Initial version (University of Warwick 2015) Aurel Page

"""

import sys
sys.path.append("../..");
import pymongo
from lmfdb import base
from lmfdb.website import dbport
from lmfdb.WebNumberField import WebNumberField
from lmfdb.hilbert_modular_forms.hilbert_field import (findvar, niceideals, conjideals, str2ideal)

print "calling base._init()"
dbport=37010
base._init(dbport, '')
print "getting connection"
conn = base.getDBConnection()
print "setting hmfs, fields and forms"
hmfs = conn.hmfs
fields = hmfs.fields
forms = hmfs.forms

# Cache of WebNumberField and FieldData objects to avoid re-creation
WNFs = {}
Fdata = {}

def get_WNF(label, gen_name):
    if not label in WNFs:
        WNFs[label] = WebNumberField(label, gen_name=gen_name)
    return WNFs[label]

def get_Fdata(label):
    if not label in Fdata:
        Fdata[label] = fields.find_one({'label':label})
    return Fdata[label]

def fldlabel2conjdata(label):
    data = {}
    Fdata = get_Fdata(label)
    gen_name = findvar(Fdata['ideals'])
    WebF = get_WNF(label, gen_name)
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
    primes = [prm[2] for prm in primes]
    cprimes = [[primes.index(cideals[(prm,ig)]) for prm in primes] for ig in range(len(auts))]
    data['conjprimes'] = cprimes
    return data

def conjstringideal(F,stridl,g):
    """Given a string representing an ideal of F and an automorpism g of F,
    return the string representing the conjugate ideal.
    """
    N,n,_,gen = str2ideal(F,stridl)
    return '[' + str(N) + ',' + str(n) + ',' + str(g(gen)) + ']'

def conjform_label(f, ig, cideals):
    level_label = cideals[(f['level_label'],ig)]
    short_label = level_label + '-' + f['label_suffix']
    return f['field_label'] + '-' + short_label

def conjform(f, g, ig, cideals, cprimes, F): #ig index of g in auts
    if f['is_base_change'][0:3] == 'yes':
        return None
    fg = copy(f)

    fg['level_label'] = cideals[(f['level_label'],ig)]
    fg['short_label'] = fg['level_label'] + '-' + fg['label_suffix']
    fg['label'] = fg['field_label'] + '-' + fg['short_label']

    fg['level_ideal'] = conjstringideal(F,f['level_ideal'],g)

    fg['AL_eigenvalues'] = [[conjstringideal(F,x[0],g),x[1]] for x in f['AL_eigenvalues']]

    H = f['hecke_eigenvalues']
    Hg = copy(f['hecke_eigenvalues'])
    fg['hecke_eigenvalues'] = Hg

    attained  = [False for i in range(len(H))]
    for i in range(len(H)):
        if cprimes[ig][i] < len(H):
            attained[cprimes[ig][i]] = True
    maxi = 0
    while maxi < len(H):
        if not attained[maxi]:
            break
        maxi += 1
    if maxi < len(H):
        print("truncating list of eigenvalues (missing conjugate prime)")
    del Hg[maxi:]

    for i in range(len(H)):
        if cprimes[ig][i] < maxi:
            Hg[cprimes[ig][i]] = H[i]

    del fg['_id']
    return fg

def checkadd_conj(label, min_level_norm=0, max_level_norm=None, fix=False):
    count = 0
    query = {}
    query['field_label'] = label
    query['level_norm'] = {'$gte' : int(min_level_norm)}
    if max_level_norm:
        query['level_norm']['$lte'] = int(max_level_norm)
    else:
        max_level_norm = oo
    ftoconj = forms.find(query)
    print("%s forms to examine of level norm between %s and %s."
          % (ftoconj.count(),min_level_norm,max_level_norm))
    if ftoconj.count() == 0:
        return None
    print("Ideals precomputations...")
    data = fldlabel2conjdata(label)
    print("...done.\n")
    auts = data['auts']
    cideals = data['conjideals']
    cprimes = data['conjprimes']
    F = data['F']
    for f in ftoconj:
        print("Testing form %s" % f['label'])
        for g in auts:
            ig = auts.index(g)
            fg_label = conjform_label(f, ig, cideals)
            fgdb = forms.find_one({'label':fg_label})
            if fgdb == None:
                print("conjugate not present")
                if fix:
                    fg = conjform(f, g, ig, cideals, cprimes, F)
                    if fg != None: #else: is a lift (self-conjugate), should have been detected
                        print("adding it : "+fg['label'])
                        forms.insert(fg)
                        count += 1
    print("\nAdded "+str(count)+" new conjugate forms.")
    return None

