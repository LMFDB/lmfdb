# -*- coding: utf-8 -*-
import sys
import time
import bson
import sage.all
from sage.all import *
import os
import json

sys.path.append("../")
import base
from pymongo.connection import Connection
base._init(dbport, "")
C = base.getDBConnection()
import pymongo

gr = C.transitivegroups.groups

labels = ['label', 'n', 't', 'auts', 'order', 'parity', 'ab', 'prim', 'cyc', 'solv', 'subs', 'repns', 'resolve', 'name', 'pretty']

gps = gr.find({})
myfile = open('gg_data')

for l in myfile:
  v= json.loads(l)
  data = {}
  for j in range(len(v)):
    data[labels[j]] = v[j]


