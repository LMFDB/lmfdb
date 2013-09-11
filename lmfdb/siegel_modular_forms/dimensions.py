# -*- coding: utf-8 -*-

from sage.misc.functional import is_odd
from sage.rings.integer import Integer
from sage.rings.power_series_ring import PowerSeriesRing
from sage.rings.integer_ring import IntegerRing


def hilbert_polynomial( j, var, group = 'Gamma(2)'):
    """
    Return for $j\ge 1$ the Hilbert polynomials of

        - $\bigoplus_{k\ge 3} M_{k,j}(\Gamma(2))$
        - $\bigoplus_{k\ge 3} M^{Eis}_{k,j}(\Gamma(2))$
    
    where $\Gamma$ can be
        - Gamma(2)
        - Gamma_0(2)
        - Gamma_1(2)
        - Sp(4,Z).

    If $f$ is the Hilbert polynomial then the Hilbert Poincare series of the
    graded space in question equals $f/(1-t^2)^5$.
    """
    j = Integer(j)
    assert j >= 0
    if 0 == j:
        raise NotImplementedError()

    if is_odd(j):
        R = var.parent()
        return R(0), R(0)

    c = dict()

    if group == 'Gamma(2)':
        cmin = 3
        cmax = 12        
        c[3] = (j-2)*(j-3)*(j-4)/24
        c[4] = j*(2*j**2 + 3*j + 166)/24
        c[5] = (-j**3 + 33*j**2 - 44*j + 72)/12
        c[6] = -(j-1)*(j**2 - 4*j + 80)/4
        c[7] = (-10*j**2 + 25*j - 20)/2
        c[8] = (j**3)/4 - (7*j**2)/2 + (63*j)/2 - 46
        c[9] = (j**3 + 39*j**2 - 172*j + 120)/12
        c[10] = -(j**3)/12 + (11*j**2)/4 - (71*j)/3 + 36
        c[11] = (-j**3 - 15*j**2 + 106*j - 120)/24
        c[12] = -(5*j**2)/8 + (25*j)/4 - 10

        e = 15*((1-j/2) * var**6 + var**4 * j/2)*(1-var**2)**3
 
    else:
        raise NotImplementedError()

    return sum( c[i] * var**i for i in range(cmin,cmax+1)), e


def vvsf_dimension( wt_range, j, group = 'Gamma(2)'):
    """
    Return the arrays
    [(k, d(k), e(k), c(k) for k in wt_range],
    where d(k), e(k), c(k) are the dimensions
    of $M_{k,j}(group)$ and its subspaces of
    Non-cusp forms and Cusp forms, respectively.

    NOTE
        Currently group can be
        - Gamma(2)
    """
    if 'Gamma(2)' == group:

        if is_odd(j):
            return [(k,(0, 0, 0)) for k in wt_range]
        if wt_range[0] < 3:
            raise NotImplementedError()
        P = PowerSeriesRing( IntegerRing(),  default_prec =wt_range[-1] + 1,  names = ('t',))
        t = P.gen()
        C, E =  hilbert_polynomial( j, t, group = group)
        c = C/(1-t**2)**5
        e = E/(1-t**2)**5
        loc = c.list()
        loe = e.list()

    else:
        raise NotImplementedError()

    return [(k,(loc[k], loe[k], loc[k]-loe[k])) for k in wt_range]


def _dimension__Sp4Z( wt, j):
    return vvsf_dimension( wt_range, j, group = 'Sp(4,Z)')

def _dimension_Gamma0_2( wt, j):
    return vvsf_dimension( wt_range, j, group = 'Gamma0(2)')

def _dimension_Gamma1_2( wt, j):
    return vvsf_dimension( wt_range, j, group = 'Gamma1(2)')

def _dimension_Gamma_2( wt_range, j):
    return vvsf_dimension( wt_range, j, group = 'Gamma(2)')
