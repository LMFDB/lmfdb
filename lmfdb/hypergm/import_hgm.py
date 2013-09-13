# -*- coding: utf-8 -*-
import sys
import time
import bson
import sage.all
from sage.all import *

from pymongo.connection import Connection
hgm = Connection(port=37010).hgm.motives

from motdata import li

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
    degree, weight, A, B, tnd, hodge, sign, sig, locinfo, req, a2, b2, a3, b3, a5, b5, a7, b7, ae2, be2, ae3, be3, ae5, be5, ae7, be7, coeffs, cond = F
    t = makeb(tnd[0], tnd[1])
    Astr = '.'.join([str(x) for x in A])
    Bstr = '.'.join([str(x) for x in B])
    tstr = str(tnd[0])+'.'+str(tnd[1])
    label = "A%s_B%s_t%s" % (Astr, Bstr, tstr)
    data = {
        'label': label,
        'degree': degree,
        'weight': weight,
        'A': A,
        'B': B,
        't': t,
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
        'cond':cond
    }
    #index = 1
    #is_new = True
    #holdfield = ''
    #for field in fields.find({'degree': d,
    #                          'signature': data['signature'],
    #                          'disc_abs_key': dstr}):
    #    index += 1
    #    if field['coeffs'] == data['coeffs']:
    #        holdfield = field
    #        is_new = False
    #        break

    #if is_new:
    #print "new field"
    #label = base_label(d, sig[0], absD, index)
    #info = {'label': label}
    hgm.save(data)

