import sys, os, time
try:
    # Make lmfdb available
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
except NameError:
    pass
from lmfdb.backend.database import db
from sage.all import CC, prime_range, gcd
from dirichlet_conrey import DirichletGroup_conrey


def check_ap2_slow(rec):
    # Check a_{p^2} = a_p^2 - chi(p) for primes up to 31
    ls = rec['lfunction_label'].split('.')
    level, weight, chi = map(int, [ls[0], ls[1], ls[-2]])
    char = DirichletGroup_conrey(level, CC)[chi]
    Z = rec['an_normalized']
    for p in prime_range(31+1):
        if level % p != 0:
            # a_{p^2} = a_p^2 - chi(p)
            charval = CC(2*char.logvalue(int(p)) * CC.pi()*CC.gens()[0]).exp()
        else:
            charval = 0
        if  (CC(*Z[p**2 - 1]) - (CC(*Z[p-1])**2 - charval)).abs() > 1e-11:
            return False
    return True

pairs = [(m,n) for m in range(2,1000) for n in range(m, 1000) if gcd(m,n) == 1 and m*n <= 1000]

def check_amn_slow(rec):
    Z = [0] + [CC(*elt) for elt in rec['an_normalized']]
    for m, n in pairs:
        if (Z[m*n] - Z[m]*Z[n]).abs() > 1e-11:
            return False
    return True

import sys
if len(sys.argv) == 3:
    k = int(sys.argv[1])
    j = int(sys.argv[2])
    assert k > j
    assert j >= 0
    chunk_size = (db.mf_hecke_cc.max_id() - db.mf_hecke_cc.min_id())/k + 1
    start_time = time.time()
    counter = 0
    total = db.mf_hecke_cc.count({'id':{'$gte': db.mf_hecke_cc.min_id() + j*chunk_size, '$lt': db.mf_hecke_cc.min_id() + (j+1)*chunk_size}})
    print "%d: %d rows to check" % (j, total)
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'mf_hecke_cc_parallel.%d.log' % j), 'w') as F:
        for rec in db.mf_hecke_cc.search({'id':{'$gte':j*chunk_size, '$lt':(j+1)*chunk_size}},['lfunction_label', 'an_normalized']):
            counter += 1
            if not check_amn_slow(rec):
                F.write('%s:amn\n' % rec['lfunction_label'])
                F.flush()
            if not check_ap2_slow(rec):
                F.write('%s:ap2\n' % rec['lfunction_label'])
                F.flush()
            if total > 1000:
                if counter % (total/1000) == 0:
                    print "%d: %.2ff%% done -- avg %.3f s" % (j, counter*100./total, (time.time() - start_time)/counter)
    print "%d: DONE -- avg %.3f s" % (j, (time.time() - start_time)/counter)


else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
