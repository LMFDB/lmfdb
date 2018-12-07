from sage.all import  vector, PolynomialRing, ZZ, NumberField
import  sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from  lmfdb.db_backend import db
ZZx = PolynomialRing(ZZ, "x")
def convert_eigenvals_to_qexp(basis, eigenvals):
    qexp = []
    for i, ev in enumerate(eigenvals):
        if ev['n'] != i+1:
            raise ValueError("Missing eigenvalue")
        if 'an' in ev:
            an = sum(elt * basis[i] for i, elt in enumerate(ev['an']))
            qexp.append(an)
        else:
            raise ValueError("Missing eigenvalue")
    return qexp


def upsert_embedding(id_number, skip = False):
    rowcc = db.mf_hecke_cc.lucky({'id':id_number}, projection=['an', 'hecke_orbit_code','id','lfunction_label', 'embedding_root_imag','embedding_root_real'])
    if rowcc is None:
        return
    if skip:
        if rowcc.get("embedding_root_imag", None) is not None:
            if rowcc.get("embedding_root_real", None) is not None:
                return
    row_embeddings =  {}
    hecke_orbit_code = rowcc['hecke_orbit_code']
    newform = db.mf_newforms.lucky({'hecke_orbit_code':hecke_orbit_code})
    if newform is None:
        # No newform in db
        return
    if newform['dim'] == 1:
        row_embeddings['embedding_root_imag'] = 0
        row_embeddings['embedding_root_real'] = 0
    elif newform['weight'] == 1:
        return
    elif newform.get('field_poly', None) is None:
	    return
    else:
        # print rowcc['lfunction_label']
        HF = NumberField(ZZx(newform['field_poly']), "v")
        numerators =  newform['hecke_ring_numerators']
        denominators = newform['hecke_ring_denominators']
        betas = [HF(elt)/denominators[i] for i, elt in enumerate(numerators)]

        embeddings = HF.complex_embeddings(prec=2000)
        an_nf = list(db.mf_hecke_nf.search({'hecke_orbit_code':hecke_orbit_code}, ['n','an'], sort=['n']))
        betas_embedded = [map(elt, betas) for elt in embeddings]
        CCC = betas_embedded[0][0].parent()
        qexp = [convert_eigenvals_to_qexp(elt, an_nf) for elt in betas_embedded]
        min_len = min(len(rowcc['an']), len(qexp[0]))
        an_cc = vector(CCC, map(lambda x: CCC(x[0], x[1]), rowcc['an'][:min_len]))
        #qexp_diff = [ (vector(CCC, elt[:min_len]) - an_cc).norm() for elt in qexp ]
        # normalized, to avoid the unstability comming from large weight
        qexp_diff = [ vector([(elt- an_cc[i])/elt.abs() for i, elt in enumerate(q) if elt != 0]).norm() for j,q in enumerate(qexp)]

        qexp_diff_sorted = sorted(qexp_diff)
        min_diff = qexp_diff_sorted[0]
        #print "min_diff = %.2e \t min_diff/2nd = %.2e" % (min_diff, min_diff/qexp_diff_sorted[1])

        #assuring that is something close to zero, and that no other value is close to it
        assert min_diff < 1e-6
        assert min_diff/qexp_diff_sorted[1] < 1e-15

        for i, elt in enumerate(qexp_diff):
            if elt == min_diff:
                row_embeddings['embedding_root_real'] = float(embeddings[i](HF.gen()).real())
                row_embeddings['embedding_root_imag'] = float(embeddings[i](HF.gen()).imag())
                break
    assert len(row_embeddings) == 2
    db.mf_hecke_cc.upsert({'id': rowcc['id']}, row_embeddings)


import sys
if len(sys.argv) == 3:
    bound = db.mf_hecke_cc.max_id()
    k = int(sys.argv[1])
    start = int(sys.argv[2])
    assert k > start
    hoc = list(db.mf_newforms.search({'dim':{'$lt': 21}, 'weight':{'$ne': 1}}, projection='hecke_orbit_code'))
    ids = sorted(list(db.mf_hecke_cc.search({'hecke_orbit_code':{'$in': hoc}}, projection='id')))
    ids = ids[start::k]
    for j, i in enumerate(ids):
        upsert_embedding(i)
        if j % int(len(ids)*0.01) == 0:
            print '%d\t--> %.2f %% done' % (start, (100.*(j+1)/len(ids)))
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
