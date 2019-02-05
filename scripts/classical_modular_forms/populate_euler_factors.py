# parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_euler_factors.py 40 ::: {0..39}
import  sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from  lmfdb.db_backend import db
from sage.all import PowerSeriesRing, ZZ, prime_range, prime_powers, gcd, RR


def extend_multiplicatively(Z):
    for pp in prime_powers(len(Z)-1):
        for k in range(1, (len(Z) - 1)//pp + 1):
            if gcd(k, pp) == 1:
                Z[pp*k] = Z[pp]*Z[k]

start_origin = 'ModularForm/GL2/Q/holomorphic/'
ps = prime_range(100)
PS = PowerSeriesRing(ZZ, "X")
def fix_euler(idnumber, an_list_bound = 11):
    lfun = db.lfunc_lfunctions.lucky({'id':idnumber}, sort = [])
    euler_factors = lfun['euler_factors'] # up to 30 euler factors
    bad_lfactors = lfun['bad_lfactors']
    assert lfun['origin'][:len(start_origin)] == start_origin, lfun['origin']
    label = lfun['origin'][len(start_origin):].replace('/','.')
    newform = db.mf_newforms.lucky({'label':label}, ['hecke_orbit_code', 'level'])
    lpolys = list(db.mf_hecke_lpolys.search({'hecke_orbit_code': newform['hecke_orbit_code']},['lpoly','p'],sort='p'))
    if lpolys == []:
        # we don't have exact data
        assert lfun['degree'] > 40
        return True
    assert ps == [elt['p'] for elt in lpolys]
    dirichlet = [1]*an_list_bound
    dirichlet[0] = 0


    for i, elt in enumerate(lpolys):
        p = ps[i]
        assert elt['p'] == p, "%s %s" % (p, label)
        elt['lpoly'] = map(int, elt['lpoly'])
        if None in euler_factors[i]:
            euler_factors[i] = elt['lpoly']
        else:
            assert euler_factors[i] == elt['lpoly'], "%s %s %s %s" % (p, label, euler_factors[i], lpolys[i])
        if newform['level'] % p == 0:
            # it is a bad euler factor
            for j, (pj, badl) in enumerate(bad_lfactors):
                if pj == p:
                    break;
            if None in badl:
                bad_lfactors[j][2] = lpolys[i]
            else:
                assert bad_lfactors[j][2] == lpolys[i], "%s %s %s %s" % (p, label, bad_lfactors[j][2], lpolys[i])
        if p < an_list_bound:
            k = RR(an_list_bound).log(p).floor()+1
            foo = (1/PS(euler_factors[i])).padded_list(k)
            for i in range(1, k):
                dirichlet[p**i] = foo[i]
    extend_multiplicatively(dirichlet)
    assert len(euler_factors) == 30
    row = {'euler_factors':euler_factors, 'bad_lfactors': bad_lfactors}
    # fill in ai
    for i, ai in enumerate(dirichlet):
        if i > 1:
            row['a' + str(i)] = int(dirichlet[i])
            print 'a' + str(i), dirichlet[i]
            print row['a' + str(i)]

    print row.keys()
    db.lfunc_lfunctions.update({'id':idnumber}, row, restat = False)
    return True

if len(sys.argv) == 3:
    k = int(sys.argv[1])
    start = int(sys.argv[2])
    assert k > start
    ids = sorted(db.lfunc_lfunctions.lucky({'coefficient_field':'1.1.1.1', 'load_key':'CMFs-workshop'}, 'id', sort = []))
    ids = ids[start::k]
    for j, i in enumerate(ids):
        fix_euler(i)
        if j % int(len(ids)*0.01) == 0:
            print '%d\t--> %.2f %% done' % (start, (100.*(j+1)/len(ids)))
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
