# -*- coding: utf-8 -*-
r""" 

Utility script to connect to the database (read-only) for browsing.

To run this, cd to the top-level lmfdb directory, start sage and use
the command

   sage: %runfile scripts/usilities/browse.py
"""

import os.path
import re
import os
import pymongo
from lmfdb.base import getDBConnection
from lmfdb.utils import web_latex
from sage.all import NumberField, PolynomialRing, cm_j_invariants_and_orders, EllipticCurve, ZZ, QQ, Set
from sage.databases.cremona import cremona_to_lmfdb
from lmfdb.ecnf.ecnf_stats import field_data
from lmfdb.ecnf.WebEllipticCurve import ideal_from_string, ideal_to_string, ideal_HNF, parse_ainvs, parse_point

print "getting connection"
C= getDBConnection()

print "setting databases..."

for db in C.database_names():
    if db in ['admin', 'userdb', 'local', 'contrib']:
        continue
    print("============================")
    print("assigning identifier {} to the database {}".format(db,db))
    exec("{} = C['{}']".format(db,db))
    for coll in C[db].collection_names():
        if not 'system' in coll and not "." in coll:
            lcoll = coll.replace("-","_")
            print("assigning identifier {} to the collection {} in database {}".format(lcoll,coll,db))
            exec("{} = {}['{}']".format(lcoll,db,coll))

