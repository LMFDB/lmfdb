import sys
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
        You should run this on legendre, on lmfdb root dir as (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python scripts/lfunctions/populate_origin_ECQ.py 40 ::: {0..39}
"""
