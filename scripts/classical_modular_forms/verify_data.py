import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db, SQL
from sage.all import CDF



# check that we have all L-functions

def get_urls(newform):
    char_labels = newform['char_labels']
    res = [ "ModularForm/GL2/Q/holomorphic/" + "/".join(newform['label'].split(".")) ]
    if newform['dim'] == 1:
        return res
    elif newform['dim'] > 80:
        res = []
    N, k, char_orbit, hecke_letter  = newform['label'].split(".")
    base_label = [N, k]
    for character in char_labels:
        for j in range(newform['dim']/newform['char_degree']):
            label = base_label + [str(character), hecke_letter, str(j + 1)]
            origin_url = 'ModularForm/GL2/Q/holomorphic/'  + '/'.join(label)
            res.append(origin_url)
    return res


# check that we have the embedding roots and they are all different
def verify_embeddings(nf):
    if nf['dim'] <= 20 and  nf['dim'] > 1:
        hoc = nf['hecke_orbit_code']
        embeddings = list(db.mf_hecke_cc.search({'hecke_orbit_code':hoc}, projection = ['embedding_root_imag','embedding_root_real']))
        # we have the right number of embeddings
        assert len(embeddings) == nf['dim']
        # they are all distinct
        assert len(set([ CDF(elt['embedding_root_real'], elt['embedding_root_imag']) for elt in embeddings ])) == nf['dim']

# cerfies that we have all the L-functions
# and that the ranks and trace_hash match
def verify_Lfunctions(nf):
    urls = get_urls(nf)
    for url in urls:
        assert db.lfunc_instances.exists({'url':url}), url
        assert db.lfunc_lfunctions.exists({'origin':url}), url

    if nf['dim'] <= 80:
        assert db.lfunc_lfunctions.exists({'origin':urls[0], 'trace_hash' : nf['trace_hash'] }), urls[0]

    assert db.lfunc_lfunctions.exists({'origin':urls[-1], 'order_of_vanishing' : nf['analytic_rank'] }), urls[-1]




import sys
if len(sys.argv) == 3:
    bound = db.mf_newforms.max_id()
    k = int(sys.argv[1])
    if k == 0:
        # no duplicates in Lfun table
        assert len(list(db._execute(SQL('SELECT "Lhash", COUNT(*) FROM lfunc_lfunctions WHERE load_key=\'CMFs-workshop\' GROUP BY "Lhash" HAVING  COUNT(*) > 1')))) == 0
    start = int(sys.argv[2])
    assert k > start
    ids = list(range(start, bound + 1, k))
    for i in ids:
        nf = db.mf_newforms.lucky({'id':i}, projection=['label','char_labels','dim','char_degree','analytic_rank', 'trace_hash', 'dim', 'hecke_orbit_code'])
        print nf['label']
        verify_Lfunctions(nf)
        verify_embeddings(nf)
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
