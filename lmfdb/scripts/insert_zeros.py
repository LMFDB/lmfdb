import sys

from sage.all import DirichletGroup

import pymongo
from pymongo import Connection
import sage.libs.lcalc.lcalc_Lfunction as lc

import base
C = base.getDBConnection()
db = C.Lfunctions

first_zeros = db.first_zeros_testing

first_zeros.drop()

for q in range(3, 1500):
    print q
    sys.stdout.flush()
    G = DirichletGroup(q)
    for n in range(len(G)):
        if G[n].is_primitive():
            L = lc.Lfunction_from_character(G[n])
            z = L.find_zeros_via_N(1)[0]
            first_zeros.insert({ 'zero' : float(z), 'modulus' : int(q), 'character' : int(n) })
