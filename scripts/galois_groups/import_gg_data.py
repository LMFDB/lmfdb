#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
import sys
#import os
import json

sys.path.append("../..")
from lmfdb import db

gr = db.gps_transitive

# moddecompuniq and pretty are added later if known

mykeys = ['ab', 'arith_equiv', 'auts', 'cyc', 'gapid', 'n', 'order', 'parity', 'prim', 'repns', 'resolve', 'solv', 'subs', 't', 'name']

myfile = open(sys.argv[1])

outrecs=[]

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
      outrecs.append(data)

if len(outrecs)>0:
  gr.insert_many(outrecs)

      #for fld in ['ab', 'arith_equiv', 'auts', 'cyc', 'gapid', 'n', 'order', 'parity', 'prim', 'repns', 'resolve', 'solv', 'subs', 't']:
      #  if data[fld] != old[fld]:
      #    print "Mismatch (%d,%d) on %s: %s --- %s"%(data['n'],data['t'],fld, str(data[fld]), str(old[fld]))


