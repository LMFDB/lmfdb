# -*- coding: utf-8 -*-
import sys, time
import bson
import sage.all
from sage.all import PolynomialRing, QQ, pari, ZZ

from pymongo.connection import Connection
fields = Connection(port=37010).numberfields.fields

def coeffs(s):
    return [a for a in s[1:-1].split(',')]

def base_label(d,r1,D,ind):
    return str(d)+"."+str(r1)+"."+str(abs(D))+"."+str(ind)

def makeb(n,t):
  return bson.SON([('n', n), ('t', t)])

def makes(n,t):
  return '%02d,%03d'%(n,t)

def makels(li):
  li2 = [str(x) for x in li]
  return ','.join(li2)

def make_disc_key(D):
  s=1
  if D<0: s=-1
  Dz = D.abs()
  if Dz==0: D1 = 0
  else: D1 = int(Dz.log(10))
  return s, '%03d%s'%(D1,str(Dz))


from outlist  import li # this reads in the list called li

print "finished importing li, number = %s"%len(li)

for F in li:
#for F in li[0:1]:
    print F
    t = time.time()
    d, sig, D, coeffs, h, cyc, T, ramps = F
    absD = abs(ZZ(D))
    gal = makeb(d, T)
    s, dstr = make_disc_key(ZZ(D))
    ramps = [str(x) for x in ramps]
    data = {
        'degree': d,
        'disc_abs_key': dstr,
        'disc_sign': s,
        'class_number': h,
        'galois': gal,
        'ramps': ramps,
        'coeffs': makels(coeffs),
        'sig': makels(sig),
        'cl_group': makels(cyc),
        'class_group': cyc,
        'coefficients': coeffs,
        'discriminant': D,
        'gal': [d,T],
        'disc_string': str(ZZ(D)),
        'signature': sig,
        'T': T
    }
    D = int(D)

    index=1
    is_new = True
    for field in fields.find({'degree': d, 
                 'signature': sig,
                 'discriminant': D}):
        index +=1
        if field['coefficients'] == coeffs:
            is_new = False
            break

    if is_new:
        print "new field"
        label = base_label(d,sig[0],absD,index)
        info =  {'label': label}
        info.update(data)
        print "entering %s into database"%info
        fields.save(info)
    else:
        print "field already in database"
    if time.time() - t > 5:
        print "\t", label
        t = time.time()
    print ""

