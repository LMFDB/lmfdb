#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
import sys
import json
import os
import gzip
import re
from collections import Counter as mset
from sage.all import euler_phi, valuation, QQ

sys.path.append('/home/jj/data/lmfdb/data_mgt/utilities')
pw_path = "../../"
pw_filename = "xyzzy"
password = open(pw_path+pw_filename, "r").readlines()[0].strip()

#from pymongo import *

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010, host='lmfdb-ib')
C['hgm'].authenticate('editor', password)

hgm = C.hgm.newmotives
#hgm = C.hgm.motives

saving = True

count = 0

#hgm.drop()
#time.sleep(3)

# New game plan:
#    - make a list of python dictionaries
#    - insert them all in one shot!

newrecs = []

def list2string(li):
    li2 = [str(x) for x in li]
    return ','.join(li2)

def fixname(s):
    a = re.sub(r'C(\d+)', r'C_{\1}',str(s))
    a = re.sub(r'S(\d+)', r'S_{\1}',a)
    a = re.sub(r'A(\d+)', r'A_{\1}',a)
    a = re.sub(r'D(\d+)', r'D_{\1}',a)
    return a

def pnotp(a,p):
    pv = p**valuation(a,p)
    return [pv, a/pv]

# Insert both forms into the database
def modvec(A,p):
    Ap = []
    for a in A:
        ap, aprime = pnotp(a,p)
        Ap.extend([ap]*euler_phi(aprime))
    Ap.sort(reverse=True)
    return Ap

def modvecupper(A,p):
    Ap = []
    for a in A:
        ap, aprime = pnotp(a,p)
        Ap.extend([aprime]*euler_phi(ap))
    Ap.sort(reverse=True)
    return Ap

def killdup(A,B):
    aa=mset(A)
    bb=mset(B)
    cc=aa & bb
    aa.subtract(cc)
    bb.subtract(cc)
    aa = list(aa.elements())
    aa.sort(reverse=True)
    bb = list(bb.elements())
    bb.sort(reverse=True)
    cc = list(cc.elements())
    cc.sort(reverse=True)
    return([aa,bb,cc])

def galmunge(gg):
    gg[1][2] = fixname(gg[1][2])
    return gg

def fixsort(gg):
    for k in range(3):
        gg[1][3][k] = sorted(gg[1][3][k], reverse=True)
    return gg

def modpair(A,B,p):
    return [modvec(A,p),modvec(B,p)]

def modupperpair(A,B,p):
    return [modvecupper(A,p),modvecupper(B,p)]

def orderAB(A,B):
    if 1 in B:
        return [A,B]
    if 1 in A:
        return [B,A]
    if A[-1]<B[-1]:
        return [A,B]
    return [B,A]

def do_addrec(F):
    global newrecs
    degree, weight, A, B, t, famhodge, hodge, conductor, sign, sig, locinfo, lcms, hardness, coeffs  = F
    A,B = orderAB(A,B)
    A.sort(reverse=True)
    B.sort(reverse=True)
    Astr = '.'.join([str(x) for x in A])
    Bstr = '.'.join([str(x) for x in B])
    myt = QQ(str(t[1])+'/'+str(t[0]))
    tstr = str(myt.numerator())+'.'+str(myt.denominator())
    label = "A%s_B%s_t%s" % (Astr, Bstr, tstr)

    data = {
        'label': label,
        'degree': degree,
        'weight': weight,
        't': str(myt),
        'A': list2string(A),
        'B': list2string(B),
        'Arev': list2string(B),
        'Brev': list2string(A),
        'hodge': list2string(hodge),
        'famhodge': list2string(famhodge),
        'sign': sign,
        'sig': sig,
        'req': hardness,
        'coeffs': coeffs,
        'lcms': lcms,
        'cond': conductor,
        'locinfo': locinfo,
        'centralval': 0
    }
    for p in [2,3,5,7]:
        mod = modpair(A,B,p)
        mod = killdup(mod[0],mod[1])
        data['A'+str(p)] = list2string(mod[0])
        data['B'+str(p)] = list2string(mod[1])
        data['C'+str(p)] = list2string(mod[2])
        mod = modpair(B,A,p)
        mod = killdup(mod[0],mod[1])
        data['A'+str(p)+'rev'] = list2string(mod[0])
        data['B'+str(p)+'rev'] = list2string(mod[1])
        mod = modupperpair(A,B,p)
        mod = killdup(mod[0],mod[1])
        data['Au'+str(p)] = list2string(mod[0])
        data['Bu'+str(p)] = list2string(mod[1])
        data['Cu'+str(p)] = list2string(mod[2])
        data['Bu'+str(p)+'rev'] = list2string(mod[0])
        data['Au'+str(p)+'rev'] = list2string(mod[1])

    is_new = True
    for field in hgm.find({'label': label}):
        is_new = False
        break

    for k in newrecs:
        if k['label'] == label:
            is_new = False
            break

    if is_new:
        #print "new family"
        newrecs.append(data)
    #else:
        #print "Have this one"

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    dat = fn.read().replace('\n', ' ')
    dat = dat.replace('>',']')
    dat = dat.replace('<','[')
    dat = dat.replace("'",'"')
    l = json.loads(dat)
    for motfam in l:
        do_addrec(motfam)
        count += 1
        #print "Count %d"%(count)
    fn.close()

hgm.insert_many(newrecs)

