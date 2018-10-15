import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from  lmfdb.db_backend import db


def upsert_origin(id_row):
    Lhash = db.lfunc_lfunctions.lucky({'id':id_row}, projection = 'Lhash')
    url = list(db.lfunc_instances.search({'Lhash': Lhash, 'type' : 'ECQ'}, projection = 'url'))
    assert len(url) == 1
    url = url[0]
    assert 'EllipticCurve/Q/' in url, "%s" % url
    print url, Lhash
    db.lfunc_lfunctions.upsert({'id': id_row}, {'origin': url})

import sys
if len(sys.argv) == 3:
    mod = int(sys.argv[1])
    c = int(sys.argv[2])
    for i in db.lfunc_lfunctions.search({'load_key':'Cremona', 'origin':None}, projection='id'):
        if (i % mod) == c:
            upsert_origin(i)
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]

