# -*- coding: utf-8 -*-

from sage.all import matrix, ZZ, QuadraticForm

# function for checking isometries
def isom(A,B):
    # First check that A is a symmetric matrix.
    if not matrix(A).is_symmetric():
        return False
    # Then check A against the viable database candidates.
    else:
        n=len(A[0])
        m=len(B[0])
        Avec=[]
        Bvec=[]
        for i in range(n):
            for j in range(i,n):
                if i==j:
                    Avec+=[A[i][j]]
                else:
                    Avec+=[2*A[i][j]]
        for i in range(m):
            for j in range(i,m):
                if i==j:
                    Bvec+=[B[i][j]]
                else:
                    Bvec+=[2*B[i][j]]
        Aquad=QuadraticForm(ZZ,len(A[0]),Avec)
    # check positive definite
        if Aquad.is_positive_definite():
            Bquad=QuadraticForm(ZZ,len(B[0]),Bvec)
            return Aquad.is_globally_equivalent_to(Bquad)
        else:
            return False
