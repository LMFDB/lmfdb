#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
import sys
#import os
import json

sys.path.append("../..")
from lmfdb import db

gr = db.gps_transitive

# moddecompuniq and pretty are added later if known

mykeys = ['ab', 'arith_equiv', 'auts', 'cyc', 'gapid', 'n', 'order', 'parity', 'prim', 'siblings', 'quotients', 'solv', 'subfields', 't', 'name', 'bound_siblings', 'bound_quotients', 'num_conj_classes', 'gens']

myfile = open(sys.argv[1])

outrecs=[]

def dosubs(ent):
    lis = ent['subfields']
    lis2 = [(j[0], j[1]) for j in lis]
    diflis = list(set(lis2))
    diflis.sort()
    ans = [[[j[0], j[1]], lis2.count(j)] for j in diflis]
    ent['subfields'] = ans

    lis = ent['siblings']
    lis2 = [(j[0], j[1]) for j in lis]
    diflis = list(set(lis2))
    diflis.sort()
    ans = [[[j[0], j[1]], lis2.count(j)] for j in diflis]
    ent['siblings'] = ans

    lis = ent['quotients']
    lis2 = [(j[0], j[1][0], j[1][1]) for j in lis]
    diflis = list(set(lis2))
    diflis.sort()
    ans = [[j[0], [j[1], j[2]], lis2.count(j)] for j in diflis]
    ent['quotients'] = ans

    return(ent)

for l in myfile:
  v= json.loads(l)
  for dd in v:
    for vals in dd:
      data=dict(zip(mykeys, vals))
      # need to fix parity
      if data['parity'] == 0:
        data['parity'] = -1
      data['label'] = "%dT%d"%(data['n'], data['t'])
      data['gapidfull'] = ""
      if data['gapid']>0:
          data['gapidfull'] = "[%d,%d]"%(data['order'],data['gapid'])
      # no longer needed
      # data = dosubs(data)
      data['siblings'] = [[z[0],z[1][0]] for z in data['siblings']]
      outrecs.append(data)

if len(outrecs)>0:
  gr.insert_many(outrecs)

      #for fld in ['ab', 'arith_equiv', 'auts', 'cyc', 'gapid', 'n', 'order', 'parity', 'prim', 'repns', 'resolve', 'solv', 'subs', 't']:
      #  if data[fld] != old[fld]:
      #    print "Mismatch (%d,%d) on %s: %s --- %s"%(data['n'],data['t'],fld, str(data[fld]), str(old[fld]))


