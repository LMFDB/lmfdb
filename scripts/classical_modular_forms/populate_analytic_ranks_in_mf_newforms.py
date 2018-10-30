import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db

def get_url(newform):
    char_labels = newform['char_labels']
    if newform['dim'] == 1:
        return [ "ModularForm/GL2/Q/holomorphic/" + "/".join(newform['label'].split(".")) ]
    base_label  = newform['label'].split(".")
    res = []
    for character in char_labels:
        for j in range(newform['dim']/newform['char_degree']):
            label = base_label + [str(character), str(j + 1)]
            origin_url = 'ModularForm/GL2/Q/holomorphic/'  + '/'.join(label)
            res.append(origin_url)
    return res


def upsert_rank(id_number, skip = False):
    newform = db.mf_newforms.lucky({'id':id_number}, projection=['weight','label','char_labels','dim','char_degree','analytic_rank'])
    if newform is None:
        return
    if newform['weight'] == 1: # no Lfun for weight 1
        return
    if skip:
        if newform.get('analytic_rank', None) is not None:
            return
    urls = get_url(newform)
    rank = None
    for url in urls:
        Lhash = db.lfunc_instances.lucky({'url': url}, projection='Lhash')
        assert Lhash is not None, url
        rankL = db.lfunc_lfunctions.lucky({'Lhash' : Lhash}, projection='order_of_vanishing')
        assert rankL is not None, Lhash
        if rank is None:
            rank = rankL
        else:
            assert rank == rankL
    assert rank is not None
    print newform['label'], rank
    db.mf_newforms.upsert({'id': id_number}, {'analytic_rank' : rank})

import sys
if len(sys.argv) == 3:
    bound = db.mf_newforms.max_id()
    k = int(sys.argv[1])
    start = int(sys.argv[2])
    assert k > start
    ids = list(range(start, bound + 1, k))
    for i in ids:
        upsert_rank(i)
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
