# -*- coding: utf-8 -*-
import sys
import bson
assert bson
import os
assert os
import json

sys.path.append("../")
from lmfdb import base
from lmfdb.website import dbport
base._init(dbport, "")
C = base.getDBConnection()

gr = C.transitivegroups.groups

labels = ['label', 'n', 't', 'auts', 'order', 'parity', 'ab', 'prim', 'cyc', 'solv', 'subs', 'repns', 'resolve', 'name', 'pretty']

gps = gr.find({})
myfile = open('gg_data')

for l in myfile:
  v= json.loads(l)
  data = {}
  for j in range(len(v)):
    data[labels[j]] = v[j]


