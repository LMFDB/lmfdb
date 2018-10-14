import sys
from  lmfdb.db_backend import db

def upsert_hash(id_number, skip = False):
    row = db.lfunc_lfunctions.lucky({'id':id_number}, projection = ['id', 'Lhash','trace_hash','origin'])
    if skip and 'trace_hash' in row:
        return
    trace_hash = int(row['Lhash'])
    assert trace_hash < 2**61
    if 'origin' not in row:
        print row
        sys.exit(1)
    assert "Genus2Curve/Q/" in row['origin'] or "EllipticCurve/Q/" in row['origin'], "%s" % row
    print row['origin'], trace_hash
    db.lfunc_lfunctions.upsert({'id': row['id']}, {'trace_hash':trace_hash})

import sys
if len(sys.argv) == 3:
    mod = int(sys.argv[1])
    c = int(sys.argv[2])
    for key in ['G2Q','Cremona']:
        for i in db.lfunc_lfunctions.search({'load_key':key}, projection='id'):
            if (i % mod) == c:
                upsert_hash(i)
else:
    print r"""Usage:
        You should run this on legendre, on lmfdb root dir as (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python scripts/lfunctions/populate_trace_hash_ECQG2Q.py 40 ::: {0..39}
"""

