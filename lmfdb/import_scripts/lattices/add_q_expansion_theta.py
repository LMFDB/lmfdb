# -*- coding: utf-8 -*-
r""" Check presence if the first 150 coefficients of the q expansion of the theta series attached to an integral lattice are stored, and adds them otherwise.

Initial version: Samuele Anni

"""

import sys, time
import re
import json
import sage.all
from sage.all import os, gp, matrix

from pymongo.mongo_client import MongoClient
C= MongoClient(port=37010)
C['Lattices'].authenticate('editor', '282a29103a17fbad')
lat = C.Lattices.lat

def check_add_qexp(dim, min_det=1, max_det=None, fix=False):
    count = 0
    query = {}
    query['dim'] = int(dim)
    query['det'] = {'$gte' : int(min_det)}
    if max_det:
        query['det']['$lte'] = int(max_det)
    else:
        max_det = "infinity"
    lat_set = lat.find(query)
    print("%s lattices to examine of dimension %s and determinant between %s and %s."
          % (lat_set.count(), dim, min_det, max_det))
    if lat_set.count() == 0:
        return None
    print("checking wheter the q expansion is stored...")
    for l in lat_set:
        print("Testing lattice %s" % l['label'])
        if l['theta_series'] == "":
            print("q expansion NOT stored")
            if fix:
                M=l['gram']
                exp=[int(i) for i in gp("Vec(1+2*'x*Ser(qfrep("+str(gp(matrix(M)))+",150,0)))")]
                lat.update({'theta_series': l['theta_series']}, {"$set": {'theta_series': exp}}, upsert=True)
                print("Fixed lattice %s" % l['label'])
        else:
            print("q expansion stored")

