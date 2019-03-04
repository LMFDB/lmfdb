import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db




def upsert_trace_hash(id_number):
    newform = db.mf_newforms.lucky({'id':id_number}, projection=['label','trace_hash','dim','weight'])
    if newform is None or newform['dim'] > 81 or newform['weight'] == 1:
        return
    if 'trace_hash' not in newform:
        assert newform['dim'] > 20
        newform['trace_hash'] = None
    base_url = "ModularForm/GL2/Q/holomorphic/" + newform['label'].replace(".","/")
    trace_hash = newform['trace_hash']
    Lhash = db.lfunc_instances.lucky({'url': base_url}, projection='Lhash')
    assert Lhash is not None
    db.lfunc_lfunctions.upsert({'Lhash': Lhash}, {'trace_hash' : trace_hash})

import sys
if len(sys.argv) == 3:
    bound = db.mf_newforms.max_id()
    k = int(sys.argv[1])
    start = int(sys.argv[2])
    assert k > start
    ids = list(range(start, bound + 1, k))
    for i in ids:
        upsert_trace_hash(i)
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
