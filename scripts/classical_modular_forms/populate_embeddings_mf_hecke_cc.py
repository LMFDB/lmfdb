# parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_embeddings_mf_hecke_cc.py 40 ::: {0..39}
from sage.all import matrix, vector, PolynomialRing, ZZ, NumberField, ComplexField
import  sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from  lmfdb.db_backend import db
ZZx = PolynomialRing(ZZ, "x")

def convert_eigenvals_to_qexp(basis, eigenvals, normalization):
    qexp = []
    for j, ev in enumerate(eigenvals, 1):
        an = sum(elt * basis[i] * j**normalization for i, elt in enumerate(ev))
        qexp.append(an)
    return qexp


def upsert_embedding(id_number, skip = True):
    rowcc = db.mf_hecke_cc.lucky({'id':id_number}, projection=['an_normalized', 'hecke_orbit_code','id','lfunction_label', 'embedding_root_imag','embedding_root_real'])
    if rowcc is None:
        return
    if skip:
        if rowcc.get("embedding_root_imag", None) is not None:
            if rowcc.get("embedding_root_real", None) is not None:
                return
    row_embeddings =  {}
    hecke_orbit_code = rowcc['hecke_orbit_code']
    newform = db.mf_newforms.lucky({'hecke_orbit_code':hecke_orbit_code},['label','weight','field_poly','dim'])
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
        hecke_nf = db.mf_hecke_nf.lucky({'hecke_orbit_code':hecke_orbit_code}, ['hecke_ring_cyclotomic_generator','an','field_poly','hecke_ring_numerators','hecke_ring_denominators', 'hecke_ring_power_basis'])
        assert hecke_nf is not None
        assert newform['field_poly'] == hecke_nf['field_poly']
        assert hecke_nf['hecke_ring_cyclotomic_generator'] == 0
        if hecke_nf['hecke_ring_power_basis']:
            v = HF.gens()[0]
            betas = [ v**i for i in range(len(newform['field_poly'])) ]
        else:
            numerators =  hecke_nf.get('hecke_ring_numerators')
            denominators = hecke_nf.get('hecke_ring_denominators')
            betas = [HF(elt)/denominators[i] for i, elt in enumerate(numerators)]

        embeddings = HF.complex_embeddings(prec=2000)
        an_nf = hecke_nf['an']
        betas_embedded = [map(elt, betas) for elt in embeddings]
        CCC = betas_embedded[0][0].parent()
        normalization = -CCC(newform['weight'] - 1).real()/2
        qexp = [convert_eigenvals_to_qexp(elt, an_nf, normalization) for elt in betas_embedded]
        min_len = min(len(rowcc['an_normalized']), len(qexp[0]))
        an_cc = vector(CCC, map(lambda x: CCC(x[0], x[1]), rowcc['an_normalized'][:min_len]))
        #qexp_diff = [ (vector(CCC, elt[:min_len]) - an_cc).norm() for elt in qexp ]
        # normalized, to avoid the unstability comming from large weight
        qexp_diff = [ vector([(elt- an_cc[i])/elt.abs() for i, elt in enumerate(q) if elt != 0]).norm() for j,q in enumerate(qexp)]

        qexp_diff_sorted = sorted(qexp_diff)
        min_diff = qexp_diff_sorted[0]

        #assuring that is something close to zero, and that no other value is close to it
        assert min_diff < 1e-6 and min_diff/qexp_diff_sorted[1] < 1e-15, "id = %d label = %s\nmin_diff = %.2e \t min_diff/2nd = %.2e\nan_cc = %s\nqexp = %s" % (id_number, rowcc['lfunction_label'], min_diff, min_diff/qexp_diff_sorted[1], vector(ComplexField(20), an_cc[:5]), matrix(ComplexField(20), [elt[:5] for elt in qexp]))

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
    ids = sorted(list(db.mf_hecke_cc.search({'hecke_orbit_code':{'$in': hoc}, 'embedding_root_real':{'$exists':False}}, projection='id', sort = [])))
    ids = ids[start::k]
    for j, i in enumerate(ids):
        upsert_embedding(i)
        if j % int(len(ids)*0.01) == 0:
            print '%d\t--> %.2f %% done' % (start, (100.*(j+1)/len(ids)))
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
