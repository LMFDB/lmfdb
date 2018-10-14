import sys
sys.path.append('/home/edgarcosta/lmfdb/')
from lmfdb.db_backend import db

def get_url(newform):
    char_labels = newform['char_labels']
    if newform['dim'] == 1:
        return [ "ModularForm/GL2/Q/holomorphic/" + "/".join(newform['label'].split(".")) ]
    N, k, char_orbit, hecke_letter  = newform['label'].split(".")
    base_url = "ModularForm/GL2/Q/holomorphic/%s/%s/" % (N, k)
    base_label = [N, k]
    res = []
    for character in char_labels:
        for j in range(newform['dim']/newform['char_degree']):
            label = base_label + [str(character), hecke_letter, str(j + 1)]
            origin_url = 'ModularForm/GL2/Q/holomorphic/'  + '/'.join(label)
            res.append(origin_url)
    return res


def upsert_rank(id_number, skip = False):
    newform = db.mf_newforms.lucky({'id':id_number}, projection=['label','char_labels','dim','char_degree','analytic_rank'])
    if newform is None:
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
        You should run this on legendre, on lmfdb root dir as (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_analytic_ranks_in_mf_newforms.py 40 ::: {0..39}
"""
