import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
from lmfdb.db_backend import db
from sage.all import RR, prime_range

filename = '/scratch/importing/mf_dim20_hecke_cc_3000.txt'
filename = '/scratch/importing/mf_dim20_hecke_cc_3001_4000.txt'
num_lines = sum(1 for line in open(filename))
cols_header = 'hecke_orbit_code:lfunction_label:conrey_label:embedding_index:embedding_m:embedding_root_real:embedding_root_imag:an:first_an:angles:first_angles'
cols = cols_header.split(':')
del cols[10]
del cols[8]
maxNk2 = db.mf_newforms.max('Nk2')
# we store a_n with n \in [1, an_storage_bound]
an_storage_bound = 1000
# we store alpha_p with p <= an_storage_bound
primes_for_angles = prime_range(an_storage_bound)

if len(sys.argv) == 3:
    M = int(sys.argv[1])
    C = int(sys.argv[2])
    assert M > C
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]



def compare_floats(a, b, prec = 52):
    if a == b:
        return True
    if None in [a,b]:
        return False
    if b == 0:
        b, a = a, b
    if a == 0:
        return b == 0 or abs(b) < 1e-60
    else:
        return RR(abs((a - b)/a)).log(2) < -prec
def compare_row(a, b, verbose = True):
    for i,c in enumerate(cols):
        if c in ['hecke_orbit_code', 'conrey_label','embedding_index','embedding_m']:
            if a[i] != b[i]:
                print c, a[i], b[i]
                return False
        elif c in ['embedding_root_real', 'embedding_root_imag']:
            if not compare_floats(a[i], b[i]):
                print c, a[i], b[i], a[i] - b[i]
                return False
        elif c == 'an':
            for j, ((ax, ay), (bx, by)) in enumerate(zip(a[i],b[i])):
                if not compare_floats(ax, bx):
                    print c, j, ax, bx, ax-bx
                    if ax != 0:
                        print RR(abs((ax - bx)/ax)).log(2)
                    return False
                if not compare_floats(ay, by):
                    print c, j, ay, by, ay-by
                    if ay != 0:
                        print RR(abs((ay - by)/ay)).log(2)
                    return False
        elif c == 'angles':
            for j, (at, bt) in enumerate(zip(a[i],b[i])):
                if not compare_floats(at, bt):
                    print c, j, at, bt
                    if None not in [at,bt]:
                        print at - bt
                        if at !=0:
                            print RR(abs((at - bt)/at)).log(2)
                    return False
    return True

with open(filename, 'r') as F:
    linenumber = -1
    for line in F:
        linenumber += 1
        if linenumber < 3:
            if linenumber == 0:
                assert line[:-1] == cols_header
            pass
        elif linenumber % M == C:
            linesplit = line[:-1].split(':')
            del linesplit[10]
            del linesplit[8]
            N, k = map(int, linesplit[1].split('.')[:2])
            #if N*k**2 > maxNk2:
            #    continue
            for i, c in enumerate(cols):
                if c in ['hecke_orbit_code', 'conrey_label','embedding_index','embedding_m']:
                    linesplit[i] = int(linesplit[i])
                elif c in ['embedding_root_real', 'embedding_root_imag']:
                    linesplit[i] =float(linesplit[i])
                elif c == 'an':
                    linesplit[i] = [[float(x), float(y)] for x, y in eval(linesplit[i])]
                elif c == 'angles':
                    angles_dict = dict([(int(x), float(y)) for x, y in eval(linesplit[i])])
                    linesplit[i] = [ angles_dict.get(p) for p in primes_for_angles ]
            # fix trivial character
            if linesplit[2] == 0:
                linesplit[2] = 1
                lfun_label = linesplit[1].split('.')
                lfun_label[-2] = str(1)
                linesplit[1] = '.'.join(lfun_label)
            hc = db.mf_hecke_cc.lucky({'hecke_orbit_code': linesplit[0], 'lfunction_label' : linesplit[1]})
            if hc is None:
                print {'hecke_orbit_code': linesplit[0], 'lfunction_label' : linesplit[1]}
                assert False
            for c in ['an']:
                hc[c] = [[float(x), float(y)] for x, y in hc[c]]

            if 'embedding_root_real' not in hc.keys(): #FIXME
                hc['embedding_root_imag'] = 0
                hc['embedding_root_real'] = 0
            if sorted(hc.keys()) != sorted(cols):
                print {'hecke_orbit_code': linesplit[0], 'lfunction_label' : linesplit[1]}
                print sorted(hc.keys())
                print sorted(cols)
                assert False
            hc_list = [ hc[c] for c in cols]
            if not compare_row(hc_list, linesplit):
                print {'hecke_orbit_code': linesplit[0], 'lfunction_label' : linesplit[1]}
                print hc_list[-1][:10]
                print linesplit[-1][:10]
                assert False

            if (linenumber - C)/M % int(float(num_lines)/(10*M)) == 0:
                print '%.2f %%' % (100*linenumber/float(num_lines))



