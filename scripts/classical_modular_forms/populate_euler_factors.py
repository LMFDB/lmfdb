# parallel -u -j 40 --halt 2 --progress sage -python scripts/classical_modular_forms/populate_euler_factors.py 40 ::: {0..39}
import  sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from  lmfdb.db_backend import db
from sage.all import PowerSeriesRing, ZZ, prime_range, prime_powers, gcd, RR, PolynomialRing, prod

ola = [1, 0, 304, 0, 43320, 0, 3841040, 0, 237184220, 0, 10815600432, 0, 376743415048, 0, 10225892694160, 0, 218578456337670, 0, 3691547262591760, 0, 49097578592470408, 0, 508829450867420592, 0, 4028233152700413020, 0, 23549670738863953040L, 0, 95880802293946094520L, 0, 242898032477996772784L, 0, 288441413567621167681L  ]
fact_ola = PolynomialRing(ZZ, 'T', implementation='NTL')(ola).factor()

ZZT = PolynomialRing(ZZ, "T")
ps = prime_range(100)
def extend_multiplicatively(Z):
    for pp in prime_powers(len(Z)-1):
        for k in range(1, (len(Z) - 1)//pp + 1):
            if gcd(k, pp) == 1:
                Z[pp*k] = Z[pp]*Z[k]
def strip_zeros(L):
    for i, v in reversed(list(enumerate(L))):
        if v != 0:
            break
    else:
        i = -1
    L[i+1:] = []

def factorization(original_poly):
    print original_poly
    print PolynomialRing(ZZ, 'T', implementation='NTL')(ola).factor()
    poly = ZZT(original_poly)
    assert poly[0] == 1
    if poly == 1:
        return [1]
    if original_poly == ola:
        print "equal ola"
    try:
        facts = poly.factor()
    except NotImplementedError:
        try:
            facts = PolynomialRing(ZZ, 'T', implementation='NTL')(original_poly).factor()
        except NotImplementedError:
            print original_poly
            raise
    # if the factor is -1+T^2, replace it by 1-T^2
    # this should happen an even number of times, mod powers
    out = [[-g if g[0] == -1 else g, e] for g, e in facts]
    assert prod( g**e for g, e in out ) == poly, "%s != %s" % (prod( [g**e] for g, e in out ), poly)
    return [[g.list(), e] for g,e  in out]



start_origin = 'ModularForm/GL2/Q/holomorphic/'
PS = PowerSeriesRing(ZZ, "X")
def fix_euler(idnumber, an_list_bound = 11):
    lfun = db.lfunc_lfunctions.lucky({'id':idnumber}, sort = [])
    euler_factors = lfun['euler_factors'] # up to 30 euler factors
    bad_lfactors = lfun['bad_lfactors']
    print lfun['origin']
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

    euler_factors_factorization = []

    for i, elt in enumerate(lpolys):
        p = ps[i]
        assert elt['p'] == p, "%s %s" % (p, label)
        new_lpoly = map(int, elt['lpoly'])
        strip_zeros(new_lpoly)
        if None in euler_factors[i]:
            euler_factors[i] = new_lpoly
        else:
            assert euler_factors[i] == new_lpoly, "%s %s %s %s" % (p, label, euler_factors[i], new_lpoly)
        if newform['level'] % p == 0:
            # it is a bad euler factor
            for j, (pj, badl) in enumerate(bad_lfactors):
                if pj == p:
                    break;
            if None in badl:
                bad_lfactors[j][1] = new_lpoly
            else:
                assert bad_lfactors[j][1] == new_lpoly, "%s %s %s %s" % (p, label, bad_lfactors[j][1], new_lpoly)

        euler_factors_factorization.append(factorization(new_lpoly))

        if p < an_list_bound:
            k = RR(an_list_bound).log(p).floor()+1
            foo = (1/PS(euler_factors[i])).padded_list(k)
            for i in range(1, k):
                dirichlet[p**i] = foo[i]

    for i, elt in enumerate(euler_factors[len(lpolys):], len(lpolys)):
        if None not in elt:
            euler_factors_factorization.append(factorization(elt))
        else:
            break

    extend_multiplicatively(dirichlet)
    assert len(euler_factors) == 30
    row = {'euler_factors':euler_factors, 'bad_lfactors': bad_lfactors, 'euler_factors_factorization': euler_factors_factorization}
    # fill in ai
    for i, ai in enumerate(dirichlet):
        if i > 1:
            row['a' + str(i)] = int(dirichlet[i])

    #print row.keys()
    db.lfunc_lfunctions.update({'id':idnumber}, row, restat = False, resort = False)
    return True

if len(sys.argv) == 2:
    fix_euler(int(sys.argv[1]))

if len(sys.argv) == 3:
    k = int(sys.argv[1])
    start = int(sys.argv[2])
    assert k > start
    ids = sorted(list(db.lfunc_lfunctions.search({'coefficient_field':'1.1.1.1', 'load_key':'CMFs-workshop', 'euler_factors_factorization': None}, 'id', sort = [])))
    ids = ids[start::k]
    for j, i in enumerate(ids):
        fix_euler(i)
        if j % int(len(ids)*0.01) == 0:
            print '%d\t--> %.2f %% done' % (start, (100.*(j+1)/len(ids)))
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
