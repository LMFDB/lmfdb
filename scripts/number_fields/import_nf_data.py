#!/usr/local/bin/sage -python
# -*- coding: utf-8 -*-
r""" Import number field data.  

Imports from a json file directly to the database.

Data is imported to the collection 'nf_fields'.
"""

import sys
import re
import json

sys.path.append('/scratch/home/jj/lmfdb')

from lmfdb import db

fields = db.nf_fields

outrecs = []
tot = 0
for path in sys.argv[1:]:
    print (path)
    fn = open(path)
    for line in fn.readlines():
        line.strip()
        if re.match(r'\S',line):
            l = json.loads(line)
            outrecs.append(l)
            tot += 1

if len(outrecs)>0:
    fields.insert_many(outrecs)

print ("Added %d records"% tot)


