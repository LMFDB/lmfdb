import traceback, time, sys, os, inspect, argparse, textwrap
from timeout_decorator import timeout, TimeoutError
try:
    # Make lmfdb available
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)),"../.."))
except NameError:
    pass
from lmfdb.backend.database import db, SQL, Composable, IdentifierWrapper as Identifier, Literal
from types import MethodType
from collections import defaultdict
from lmfdb.utils import names_and_urls
from sage.all import (Integer, prod, floor, mod, euler_phi, prime_pi,
        cached_function, ZZ, RR, ComplexField, Gamma1, Gamma0, PolynomialRing,
        dimension_new_cusp_forms, dimension_eis, prime_range,
        dimension_cusp_forms, dimension_modular_forms, kronecker_symbol,
        gap, psi, infinity, CC, gcd)
from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
from datetime import datetime



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

def check_amn_slow(rec):
    Z = [0] + [CC(*elt) for elt in rec['an_normalized']]
    for pp in prime_range(len(Z)-1):
        for k in range(1, (len(Z) - 1)//pp + 1):
            if gcd(k, pp) == 1:
                if (Z[pp*k] - Z[pp]*Z[k]).abs() > 1e-11:
                    return False
    return True

import sys
if len(sys.argv) == 3:
    bound = db.mf_hecke_cc.max_id()
    k = int(sys.argv[1])
    j = int(sys.argv[2])
    assert k > j
    assert j >= 0
    chunk_size = bound/k + 1
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'mf_hecke_cc_parallel.%d.log' % j), 'w') as F:
    for rec in db.mf_hecke_cc.search({'id':{'$gte':j*chunk_size, '$lt':(j+1)*chunk_size}},['lfunction_label', 'an_normalized']):
        if !check_amn_slow(rec):
            F.write('%s:amn\n' % rec['lfunction_label'])
            F.flush()
        if !check_ap2_slow(rec):
            F.write('%s:ap2\n' % rec['lfunction_label'])
            F.flush()
else:
    print r"""Usage:
        You should run this on legendre as: (this will use 40 cores):
        # parallel -u -j 40 --halt 2 --progress sage -python %s 40 ::: {0..39}""" % sys.argv[0]
