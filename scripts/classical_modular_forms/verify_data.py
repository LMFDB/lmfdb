import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db, SQL
from sage.all import CDF, dimension_new_cusp_forms, Gamma1
from dirichlet_conrey import DirichletGroup_conrey


# TODO
# check that the first root matches the other root to the right precision
def verify_dimensions(n,k):
    totaldim = 0
    for ns in db.mf_newspaces.search({'level':n, 'weight':k}, projection = ['hecke_orbit_dims', 'char_orbit_index','char_labels','label']):
        label = ns['label']
        index = ns['char_orbit_index']
        hecke_orbit_dims = ns['hecke_orbit_dims']
        hecke_orbit_dims.sort()
        dim = sum(hecke_orbit_dims)
        totaldim += dim
        char_labels = ns['char_labels']
        sage_dim, sage_indexes = dim_and_char_labels(n,k,index)
        assert dim == sage_dim, label
        assert sorted(sage_indexes) == sorted(char_labels), label
        hecke_orbit_dims_nf = sorted(list(db.mf_newforms.search({'space_label': ns['label']}, projection = 'dim')))
        assert hecke_orbit_dims == hecke_orbit_dims_nf, label

    assert totaldim == dimension_new_cusp_forms(Gamma1(n), k), "%s != %s" % (totaldim, dimension_new_cusp_forms(Gamma1(n), k))




def dim_and_char_labels(n,k,index):
    G = DirichletGroup_conrey(n)
    char = G[index]
    indexes = [elt.number() for elt in char.galois_orbit()]
    dim = dimension_new_cusp_forms(char.sage_character(),k)
    return dim, indexes


# compute newform dimensions in Sage and compare with dims in mf_newspaces
# compare with sum of dims in mf_newforms


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
    for i in []: #ids:
        nf = db.mf_newforms.lucky({'id':i}, projection=['label','char_labels','dim','char_degree','analytic_rank', 'trace_hash', 'dim', 'hecke_orbit_code'])
        if nf is not None:
            print "%d ->\t %.2f %s" % (start, 100*float(i)/bound, nf['label'])
            verify_Lfunctions(nf)
            verify_embeddings(nf)
    bound = db.mf_newforms.max('Nk2')
    for level in range(1, db.mf_newforms.max('level') + 1):
        print "%d ->\t %d" % (start, level)
        for weight in range(2, db.mf_newforms.max('weight') + 1):
            if level*weight*weight <= bound and (level + weight)%k == start:
                verify_dimensions(level, weight)

else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
