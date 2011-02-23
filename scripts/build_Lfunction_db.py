import sys

from sage.all import DirichletGroup
from sage.all import CC, EllipticCurve, sqrt

import pymongo
from pymongo import Connection
import sage.libs.lcalc.lcalc_Lfunction as lc

C = Connection(port=37010)

Lfunctions = C.test.Lfunctions_test

def remove_all():
    Lfunctions.drop()

def insert_dirichlet_L_functions(Q):
    print "Putting Dirichlet L-functions into database."
    for q in range(3, Q):
        print "Working on modulus", q
        sys.stdout.flush()
        G = DirichletGroup(q)
        for n in range(len(G)):
            chi = G[n]
            if chi.is_primitive():
                L = lc.Lfunction_from_character(chi)
                z = L.find_zeros_via_N(1)[0]
                Lfunction_data = {}
                Lfunction_data['first_zero'] = float(z)
                Lfunction_data['description'] = "Dirichlet L-function for character number " + str(n) + " modulo " + str(q)
                Lfunction_data['degree'] = 1
                Lfunction_data['signature_R'] = 1
                Lfunction_data['signature_C'] = 0
                if chi.is_odd():
                    Lfunction_data['mu_real'] = [1.0,]
                    Lfunction_data['mu_imag'] = [0.0,]
                else:
                    Lfunction_data['mu_real'] = [0.0,]
                    Lfunction_data['mu_imag'] = [0.0,]

                Lfunction_data['conductor'] = q

                coeffs = []

                for k in range(0, 10):
                    coeffs.append(CC(chi(k)))
                
                Lfunction_data['coeffs_real'] = [float(x.real()) for x in coeffs]
                Lfunction_data['coeffs_imag'] = [float(x.imag()) for x in coeffs]

                Lfunctions.insert(Lfunction_data)

def update_entries():
    # one time function to run to update everything in the database with an extra tag
    everything = Lfunctions.find()
    for L in everything:
        if L['description'].startswith("Dirichlet"):
            n, q = L['description'][42:].split(" modulo ")
            #print n, q
            n = int(n)
            q = int(q)
            L['special'] = {'type' : 'dirichlet', 'modulus' : q, 'number' : n}
            Lfunctions.save(L)
        elif L['description'].startswith("Elliptic"):
            label = L['description'][36:]
            L['special'] = {'type' : 'elliptic', 'label' : label}
            Lfunctions.save(L)




def insert_EC_L_functions(start=1, end=100):
    curves = C.ellcurves.curves
    for N in range(start, end):
        print "Processing conductor", N
        sys.stdout.flush()
        query = curves.find({'conductor' : N, 'number' : 1})
        for curve in query:
            E = EllipticCurve([int(x) for x in curve['ainvs']])
            L = lc.Lfunction_from_elliptic_curve(E)
            first_zeros = L.find_zeros_via_N(curve['rank'] + 1)
            if len(first_zeros) > 1:
                if not first_zeros[-2] == 0:
                    print "problem"

            z = float(first_zeros[-1])

            Lfunction_data = {}
            Lfunction_data['first_zero'] = z
            Lfunction_data['description'] = 'Elliptic curve L-function for curve ' + str(curve['label'])
            Lfunction_data['degree'] = 2
            Lfunction_data['signature_R'] = 0
            Lfunction_data['signature_C'] = 1
            Lfunction_data['eta_real'] = [1.0,]
            Lfunction_data['eta_imag'] = [0.0,]

            Lfunction_data['conductor'] = N

            coeffs = []

            for k in range(1, 11):
                coeffs.append(CC(E.an(k)/sqrt(k)))
            
            Lfunction_data['coeffs_real'] = [float(x.real()) for x in coeffs]
            Lfunction_data['coeffs_imag'] = [float(x.imag()) for x in coeffs]

            Lfunctions.insert(Lfunction_data)

def build_indices():
    Lfunctions.create_index("first_zero")
    Lfunctions.create_index("degree")
    Lfunctions.create_index("conductor")
    

if __name__=="__main__":
    #insert_EC_L_functions(800, 1300)
    #build_indices()
    update_entries()
    pass
    #remove_all()
    #insert_dirichlet_L_functions(50)
