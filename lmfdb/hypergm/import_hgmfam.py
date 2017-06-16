# -*- coding: utf-8 -*-
import sys
import json
import os
import gzip

from pymongo.connection import Connection
hgm = Connection(port=37010).hgm.families

saving = True

count = 0

def do_import(F):
    degree, weight, A, B, hodge, gal2, gal3, gal5, gal7  = F
    A.sort()
    B.sort()
    Astr = '.'.join([str(x) for x in A])
    Bstr = '.'.join([str(x) for x in B])
    label = "A%s_B%s" % (Astr, Bstr)
    data = {
        'label': label,
        'degree': degree,
        'weight': weight,
        'A': A,
        'B': B,
        'hodge': hodge,
        'gal2': gal2,
        'gal3': gal3,
        'gal5': gal5,
        'gal7': gal7
    }
    is_new = True
    for field in hgm.find({'label': label}):
        is_new = False
        break

    if is_new:
        print "new family"
        hgm.save(data)
    else:
        print "Have this one"

for path in sys.argv[1:]:
    print path
    filename = os.path.basename(path)
    fn = gzip.open(path) if filename[-3:] == '.gz' else open(path)
    dat = fn.read().replace('\n', ' ')
    dat = dat.replace('>',']')
    dat = dat.replace('<','[')
    l = json.loads(dat)
    for motfam in l:
        do_import(motfam)
        count += 1
        print "Count %d"%(count)
    fn.close()

