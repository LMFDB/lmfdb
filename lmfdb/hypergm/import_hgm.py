# -*- coding: utf-8 -*-
import sys
import json
import os
import gzip
from sage.all import QQ

from pymongo.connection import Connection
hgm = Connection(port=37010).hgm.motives

saving = True

def fix_t(t):
    tsage = QQ("%d/%d" % (t[0], t[1]))
    return [int(tsage.numerator()), int(tsage.denominator())]

count = 0

def do_import(F):
    #print "%d of %d: " % (count, tot)
    degree, weight, A, B, tnd, hodge, sign, sig, locinfo, req, a2, b2, a3, b3, a5, b5, a7, b7, ae2, be2, ae3, be3, ae5, be5, ae7, be7, coeffs, cond, centralval = F
    tnd = fix_t(tnd)
    A.sort()
    B.sort()
    a2.sort()
    a3.sort()
    a5.sort()
    a7.sort()
    b2.sort()
    b3.sort()
    b5.sort()
    b7.sort()
    ae2.sort()
    ae3.sort()
    ae5.sort()
    ae7.sort()
    be2.sort()
    be3.sort()
    be5.sort()
    be7.sort()
    if A[0] < B[0]:
        temp = A
        A = B
        B = temp
        # May want to swap the A_p and B_p later

    Astr = '.'.join([str(x) for x in A])
    Bstr = '.'.join([str(x) for x in B])
    tstr = str(tnd[0])+'.'+str(tnd[1])
    label = "A%s_B%s_t%s" % (Astr, Bstr, tstr)
    print str(tnd)
    print "\n"
    data = {
        'label': label,
        'degree': degree,
        'weight': weight,
        'A': A,
        'B': B,
        't': tnd,
        'hodge': hodge,
        'sign': sign,
        'sig': sig,
        'locinfo': locinfo,
        'req':req,
        'a2':a2,
        'b2':b2,
        'a3':a3,
        'b3':b3,
        'a5':a5,
        'b5':b5,
        'a7':a7,
        'b7':b7,
        'ae2':ae2,
        'be2':be2,
        'ae3':ae3,
        'be3':be3,
        'ae5':ae5,
        'be5':be5,
        'ae7':ae7,
        'be7':be7,
        'coeffs':coeffs,
        'cond':cond,
        'centralval': centralval
    }
    hgm.save(data)

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    dat = fn.read().replace('\n', ' ')
    dat = dat.replace('>',']')
    dat = dat.replace('<','[')
    l = json.loads(dat)
    for mot in l:
        do_import(mot)
        count += 1
        print "Count %d"%(count)
    fn.close()

