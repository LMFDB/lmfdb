# -*- coding: utf-8 -*-
import sys
import time
import bson
import sage.all
from sage.all import *

from pymongo.connection import Connection
hgm = Connection(port=37010).hgm.families

from famdata import li

saving = True

def makeb(n, d):
    return bson.SON([('n', n), ('d', d)])

tot = len(li)
print "finished importing li, number = %s" % tot
count = 0

for F in li:
# for F in li[0:1]:
    count += 1
    print "%d of %d: %s" % (count, tot, F)
    degree, weight, A, B, hodge, gal2, gal3, gal5, gal7  = F
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

