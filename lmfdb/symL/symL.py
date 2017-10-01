r"""

AUTHORS:

- Rishikesh, Mark Watkins 2012
- David Lowry-Duda 2017
"""

########################################################################
#       Copyright (C) 2006 William Stein <wstein@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################


from sage.structure.sage_object import SageObject
import sage.rings.all

from sage.all import binomial
from sympowlmfdb import sympowlmfdb


def tbin(a, b):
    return (binomial(a - b + 1, b) - binomial(a - b - 1, b - 2)) * (-1) ** b


class SymmetricPowerLFunction(SageObject):

    def __init__(self, E, m):
        if E.has_cm():
            raise ValueError("E should not be cm")

        from sympowlmfdb import sympowlmfdb
        bad_primes, conductor, root_number = sympowlmfdb.local_data(E, m)
        self.bad_prime_euler = {}
        self.bad_primes = [i for (i, _) in bad_primes]
        for j in bad_primes:
            a, b = j
            self.bad_prime_euler[a] = b
        self.m = m
        self.conductor = conductor
        self.root_number = root_number
        self.E = E
        self._construct_L()

    def eulerFactor(self, p):
        """
        Euler Factor, in the form [c_0,c_1,c_2,...], where \sum c_i x^i is the polynomial giving the euler factor
        """
        if p in self.bad_primes:
            return self.bad_prime_euler[p]

        m = self.m
        m = sage.rings.all.Integer(m)
        # E= EllipticCurve(E)
        R = sage.rings.all.PolynomialRing(sage.rings.all.RationalField(), 'x')
        x = R('x')
        F = R(1)
        ap = self.E.ap(p)
        for i in range(0, (m - 1) / 2 + 1):
            s = m - 2 * i
            s2 = s // 2

            TI = sum([tbin(s, s2 - k) * ap ** (2 * k) * p ** (s2 - k) for k in range(0, s2 + 1)])

            if s % 2 != 0:
                TI = ap * TI
            F = F * (1 - TI * p ** i * x + p ** m * x ** 2)

        if m % 2 == 0:
            F = F * (1 - p ** (m // 2) * x)

        return F.coefficients(sparse=False)

    def an_list(self, upperbound=100000):
        #from sage.rings.fast_arith import prime_range # imported but unused
        from lmfdb.utils import an_list
        return an_list(self.eulerFactor, upperbound=upperbound,
                       base_field=sage.rings.all.RationalField())

    def _construct_L(self, upperbound=10000):
        """Construct L function"""
        try:
            return self._L
        except AttributeError:
            pass

        import sage.libs.lcalc.lcalc_Lfunction as lcalc
        RR = sage.rings.all.RealField()
        halfm = RR(self.m) / 2.0

        anlist = self.an_list(upperbound)
        coeffs = [anlist[i] / pow(RR(i + 1), halfm) for i in range(upperbound)]

        if self.m % 2 == 1:
            u = (self.m + 1) // 2
            Q = (self.conductor / (2 * RR.pi()) ** (self.m + 1)).sqrt()

            kapp = u * [1.0]
            gamm = [self.m / 2.0 - i for i in range(u)]

            self._kappa_fe = kapp
            self._lambda_fe = gamm
            assert len(kapp) == len(gamm)

            poles = []
            residues = []

        if self.m % 2 == 0:
            v = self.m // 2
            Q = (2 * self.conductor / (2 * RR.pi()) ** (self.m + 1)).sqrt()

            kapp = v * [1.0] + [0.5]
            gamm = [self.m / 2.0 - i for i in range(v)] + [self.m / 4.0 - v // 2]

            self._kappa_fe = kapp
            self._lambda_fe = gamm
            assert len(kapp) == len(gamm)
            poles = []
            residues = []

            # return lcalc.Lfunction_D("", 0,coeffs,0,Q, self.root_number, kapp, gamm,poles,residues)

        # generate data for renderer
        self._Q_fe = Q
        self._coeffs = coeffs
        self._poles = poles
        self._residues = residues
        # self._kappa_fe=gamm
        # self._lambda_fe=[]

        self._L = lcalc.Lfunction_D("", 0, coeffs, 0, Q, self.root_number, kapp, gamm, poles, residues)
        return self._L


def symmetricEulerFactor(E, m, p):

    bad_primes, conductor, root_number = sympowlmfdb.local_data(E, m)
    bad_P_poly = {}
    bad_P_list = [i for (i, _) in bad_primes]
    for j in bad_primes:
        a, b = j
        bad_P_poly[a] = b

    if p in bad_P_list:
        return bad_P_poly[p]

    m = sage.rings.all.Integer(m)
    # E=EllipticCurve(E)
    R = sage.rings.all.PolynomialRing(sage.rings.all.RationalField(), 't')
    t = R('t')
    F = 1

    print type(F)

    for i in range(0, (m - 1) / 2 + 1):
        s = m - 2 * i
        s2 = s // 2
        ap = E.ap(p)

        TI = sum([tbin(s, s2 - k) * ap ** (2 * k) * p ** (s2 - k) for k in xrange(0, s2 + 1)])

        if s % 2 != 0:
            TI = ap * TI

        F = F * (1 - TI * p ** i * t + p ** m * t ** 2)

    if m % 2 == 0:
        F = F * (1 - p ** (m / 2) * t)

    return F.coeffs()


def symmetricPowerLfunction(E, n):
    """gives lcalc version of symmetric power L function"""
    bad_primes, conductor, root_number = sympowlmfdb.local_data(E, n)

#What is the point of this last line?
sympowlmfdb
