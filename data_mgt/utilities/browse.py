# -*- coding: utf-8 -*-
r""" 

Utility script to connect to the database (read-only) for browsing.

To run this, cd to the top-level lmfdb directory, start sage and use
the command

   sage: %runfile scripts/utilities/browse.py
"""

from lmfdb.base import getDBConnection

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

