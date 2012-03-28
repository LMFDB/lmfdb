r"""
Watkins Symmetric Power `L`-function Calculator

SYMPOW is a package to compute special values of symmetric power
elliptic curve L-functions. It can compute up to about 64 digits of
precision. This interface provides complete access to sympow, which
is a standard part of Sage (and includes the extra data files).

.. note::

   Each call to ``sympow`` runs a complete
   ``sympow`` process. This incurs about 0.2 seconds
   overhead.

AUTHORS:

- Mark Watkins (2005-2006): wrote and released sympow

- William Stein (2006-03-05): wrote Sage interface

ACKNOWLEDGEMENT (from sympow readme):


-  The quad-double package was modified from David Bailey's
   package: http://crd.lbl.gov/~dhbailey/mpdist/

-  The ``squfof`` implementation was modified from
   Allan Steel's version of Arjen Lenstra's original LIP-based code.

-  The ``ec_ap`` code was originally written for the
   kernel of MAGMA, but was modified to use small integers when
   possible.

-  SYMPOW was originally developed using PARI, but due to licensing
   difficulties, this was eliminated. SYMPOW also does not use the
   standard math libraries unless Configure is run with the -lm
   option. SYMPOW still uses GP to compute the meshes of inverse
   Mellin transforms (this is done when a new symmetric power is added
   to datafiles).
"""

########################################################################
#       Copyright (C) 2006 William Stein <wstein@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################

import os, weakref

from sage.structure.sage_object import SageObject
from sage.misc.all import pager, verbose
import sage.rings.all





from sage.schemes.elliptic_curves.constructor import EllipticCurve

from sage.rings.arith import binomial
from sympowlmfdb import sympowlmfdb


def tbin(a,b):
    return (binomial(a-b+1,b) - binomial(a-b-1, b-2)) * (-1)**b

class SymmetricPowerLFunction(SageObject):

    def __init__(self,E,m):
        if E.has_cm():
            raise ValueError "E should not be cm"

        from sympowlmfdb import sympowlmfdb 
        bad_primes,conductor, root_number=sympowlmfdb.local_data(E,m)
        self.bad_prime_euler={}
        self.bad_primes= [i for (i,_) in bad_primes]
        for j in bad_primes:
            a,b=j
            self.bad_prime_euler[a]=b
        self.m = m
        self.conductor=conductor
        self.root_number = root_number
        self.E= E



    def eulerFactor(self,p):
        """
        Euler Factor
        """
        if p in self.bad_primes:
            return self.bad_prime_euler[p]

        m = self.m
        m=sage.rings.all.Integer(m)
        #E= EllipticCurve(E)
        R=sage.rings.all.PolynomialRing(sage.rings.all.RationalField(),'x')
        x=R('x')
        F=R(1)      
        ap=self.E.ap(p)      
        for i in range(0, (m-1)/2 +1):
            s = m - 2*i
            s2 = s // 2

            TI = sum([tbin(s,s2-k) *  ap**(2*k) * p**(s2 -k) for k in range(0,s2+1)])               

            if s % 2 !=0 :
                TI = ap*TI      
            F=F* (1 - TI * p**i *x +p**m * x**2)        


        if m % 2 == 0:
            F = F * (1-p**(m // 2) * x)
    
        return F.coeffs()

    def an_list(self,upperbound=100000):
        from sage.rings.fast_arith import prime_range
        PP=sage.rings.all.PowerSeriesRing(sage.rings.all.RationalField(), 'x',30)
        x=PP('x')
        prime_l = prime_range(upperbound)
        result = upperbound *[1]

        for p in prime_l:
            #pp= self.eulerFactor(p)
            #print pp
            #euler_factor =  1/sum([x**i * pp[i] for i in range(len(pp))])
            #print self.eulerFactor(p)
            euler_factor =  (1/(PP(self.eulerFactor(p)))).padded_list()
            #print euler_factor
            if len(euler_factor) == 1:
                for j in range(1+ upperbound // p):
                    result[j*p -1]=0
                continue

            k=1
            while True:
                if p**k > upperbound:
                    break
                for j in range(1+ upperbound // (p**k)):
                    if j % p == 0:
                        continue
                    result[j* p**k -1] *= euler_factor[k]
                    #print result

                k += 1

        return result


    def _construct_L(self,upperbound=10000):
        """
        Construct L function

        """ 
        import sage.libs.lcalc.lcalc_Lfunction as lcalc
        RR=sage.rings.all.RealField()
        halfm=RR(self.m)/2.0
        

        anlist = self.an_list(upperbound)
        coeffs = [anlist[i]/pow(RR(i+1),halfm) for i in range(upperbound)]


        if self.m % 2 == 1:
            u = (self.m+1)//2
            Q= (self.conductor/(2*RR.pi())**(self.m+1)).sqrt()

            kapp = u*[1.0]
            gamm = [self.m/2.0 - i for i in range(u)]

            poles=[]
            residues=[]


        
        if self.m % 2 == 0:
            v = self.m // 2
            Q = (2*self.conductor / (2*RR.pi())**(self.m +1)).sqrt()

            kapp = v *[1.0] +[0.5]
            gamm = [self.m/2.0 - i for i in range(v)] +[self.m/4.0 - v//2]

            poles=[]
            residues=[]

            #return lcalc.Lfunction_D("", 0,coeffs,0,Q, self.root_number, kapp, gamm,poles,residues)

        
        #generate data for renderer
        self._coeffs=coeffs
        self._poles=poles
        self._residues=residues
        self._mu_fe=self.gamm
        self._nu_fe=[]

        return lcalc.Lfunction_D("", 0,coeffs,0,Q, self.root_number, kapp, gamm,poles,residues)











def symmetricEulerFactor(E,m,p):

    
    bad_primes,conductor, root_number=sympowlmfdb.local_data(E,m)
    bad_P_poly={}
    bad_P_list= [i for (i,_) in bad_primes]
    for j in bad_primes:
        a,b=j
        bad_P_poly[a]=b
    
    if  p in bad_P_list:
        return bad_P_poly[p]

    m=sage.rings.all.Integer(m)
    #E=EllipticCurve(E)
    R=sage.rings.all.PolynomialRing(sage.rings.all.RationalField(),'t')
    t=R('t')
    F=1

    print type(F)

    for i in range(0, (m-1)/2 +1):
        s = m - 2*i
        s2 = s // 2
        ap=E.ap(p)


        TI = sum([tbin(s,s2-k) *  ap**(2*k) * p**(s2 -k) for k in xrange(0,s2+1)])



        if s % 2 !=0 :
            TI = ap*TI

        F=F* (1 - TI * p**i *t +p**m * t**2)


    if m % 2 == 0:
        F = F * (1-p**(m/2) * t)

    return F.coeffs()






def symmetricPowerLfunction(E,n):
    """
    gives lcalc version of symmetric power L function
    """

    bad_primes, conductor, root_number = sympow.local_data(E,n)







sympowlmfdb
