# -*- coding: utf-8 -*-
# This file provides functions for computing dimensions of
# collections of Siegel modular forms. It is partly based on
# code implemented together with David Yuen and Fabien Cléry.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from sage.misc.functional import is_odd, is_even
from sage.rings.integer import Integer
from sage.rings.power_series_ring import PowerSeriesRing
from sage.rings.integer_ring import IntegerRing


####################################################################
## For general dimension related data from the data base
####################################################################

# DB_URL = 'mongodb://localhost:40000/'

def fetch( dct):

    import pymongo

    # client = pymongo.MongoClient( DB_URL)
    import lmfdb.base
    client = lmfdb.base.getDBConnection()

    db = client.siegel_modular_forms
    hps = db.dimensions
    item = hps.find_one( dct)
    client.close()
    return item


####################################################################
## Dimension formulas for Gamma(2), Gamma0(2), Gamma1(2), Sp4(Z)
####################################################################

def dimension_Gamma_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma(2)')

def dimension_Gamma1_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma1(2)')

def dimension_Gamma0_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma0(2)')

def dimension_Sp4Z( wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Eisenstein</span>: The subspace of Siegel Eisenstein series.</li>
      <li><span class="emph">Klingen</span>: The subspace of Klingen Eisenstein series.</li>
      <li><span class="emph">Maass</span>: The subspace of Maass liftings.</li>
      <li><span class="emph">Interesting</span>: The subspace spanned by cuspidal eigenforms that are not Maass liftings.</li>
    </ul>
    """
    return _dimension_Sp4Z( wt_range)

def dimension_Sp4Z_2( wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The subspace of non cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp form.</li>
    </ul>
    """
    return _dimension_Gamma_2( wt_range, 2, group = 'Sp4(Z)')

def dimension_Sp4Z_j( wt_range, j):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The subspace of non cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp form.</li>
    </ul>
    """    
    return _dimension_Gamma_2( wt_range, j, group = 'Sp4(Z)')



def _dimension_Sp4Z( wt_range):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(4,Z)$.

    OUTPUT
        ("Total", "Eisenstein", "Klingen", "Maass", "Interesting")
    """
    headers = ['Total', 'Eisenstein', 'Klingen', 'Maass', 'Interesting']

    R = PowerSeriesRing( IntegerRing(), default_prec = wt_range[-1] + 1, names = ('x',))
    (x,) = R._first_ngens(1)
    H_all = 1 / (1 - x ** 4) / (1 - x ** 6) / (1 - x ** 10) / (1 - x ** 12)
    H_Kl = x ** 12 / (1 - x ** 4) / (1 - x ** 6)
    H_MS = (x ** 10 + x ** 12) / (1 - x ** 4) / (1 - x ** 6)

    dct = dict( (k,
                 { 'Total': H_all[k], 
                   'Eisenstein': 1 if k >= 4 else 0,
                   'Klingen': H_Kl[k],
                   'Maass': H_MS[k],
                   'Interesting': H_all[k]-(1 if k >= 4 else 0)-H_Kl[k]-H_MS[k]
                   }
                 if is_even(k) else
                 { 'Total': H_all[k-35], 
                   'Eisenstein': 0,
                   'Klingen': 0,
                   'Maass': 0,
                   'Interesting': H_all[k-35]
                   }
                 ) for k in wt_range)

    return headers, dct



def _dimension_Gamma_2( wt_range, j, group = 'Gamma(2)'):
    """
    Return the dict
    {(k-> partition ->  [ d(k), e(k), c(k)] for k in wt_range]},
    where d(k), e(k), c(k) are the dimensions
    of the $p$-canonical part of $M_{k,j}( \Gamma(2))$ and its subspaces of
    Non-cusp forms and Cusp forms.
    """

    partitions = [ u'6', u'51', u'42', u'411', u'33', u'321',
                   u'311', u'222', u'2211', u'21111', u'111111']

    if is_odd(j):
        dct = dict( (k,dict((h,[0,0,0]) for h in partitions)) for k in wt_range)
        for k in dct:
            dct[k]['All'] = [0,0,0]
        partitions.insert( 0,'All')
        return partitions, dct
        
    if j>=2 and  wt_range[0] < 4:
        raise NotImplementedError( 'Dimensions of \(M_{k,j}\) for \(k<4\) and even \(j\ge 2\) not implemented')

    query = { 'sym_power': str(j), 'group' : 'Gamma(2)', 'space': 'total'}
    db_total = fetch( query)
    assert db_total, '%s: Data not available' % query
    query['space'] = 'cusp'
    db_cusp = fetch( query)
    assert db_cusp, '%s: Data not available' % query
    
    P = PowerSeriesRing( IntegerRing(),  default_prec =wt_range[-1] + 1,  names = ('t',))
    t = P.gen()
    total = dict()
    cusp = dict()
    for p in partitions:
        total[p] = eval(db_total[p])
        cusp[p] = eval(db_cusp[p])
    # total = dict( ( p, eval(db_total[p])) for p in partitions)
    # cusp = dict( ( p, eval(db_cusp[p])) for p in partitions)
    
    if 'Gamma(2)' == group:
        dct = dict( (k, dict( (p, [total[p][k], total[p][k]-cusp[p][k], cusp[p][k]])
                              for p in partitions)) for k in wt_range)
        for k in dct:
            dct[k]['All'] = [sum( dct[k][p][j] for p in dct[k]) for j in range(3)]
            
        partitions.insert( 0,'All')
        headers = partitions

    elif 'Gamma1(2)' == group:
        ps = { '3': ['6', '42', '222'],
               '21': ['51', '42', '321'],
               '111': ['411', '33']}
        
        dct = dict( (k, dict( (p,[
                            sum( total[q][k] for q in ps[p]),
                            sum( total[q][k]-cusp[q][k] for q in ps[p]),
                            sum( cusp[q][k] for q in ps[p]),
                            ]) for p in ps)) for k in wt_range) 
        for k in dct:
            dct[k]['All'] = [sum( dct[k][p][j] for p in dct[k]) for j in range(3)]       

        headers = ps.keys()
        headers.sort( reverse = True)
        headers.insert( 0,'All')

    elif 'Gamma0(2)' == group:
        headers = ['Total', 'Non cusp', 'Cusp']
        ps = ['6', '42', '222']
        dct = dict( (k, { 'Total': sum( total[p][k] for p in ps),
                          'Non cusp': sum( total[p][k]-cusp[p][k] for p in ps),
                          'Cusp': sum( cusp[p][k] for p in ps)})
                    for k in wt_range)

    elif 'Sp4(Z)' == group:
        headers = ['Total', 'Non cusp', 'Cusp']
        p = '6'
        dct = dict( (k, { 'Total': total[p][k],
                          'Non cusp': total[p][k]-cusp[p][k],
                          'Cusp': cusp[p][k]})
                    for k in wt_range)
    else:
        raise NotImplemetedError( 'Dimension for %s not implemented' % group)

    return headers, dct


####################################################################
## Dimension formulas for Sp6Z
####################################################################

def dimension_Sp6Z( wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Miyawaki lifts I</span>: The subspace of Miyawaki lifts of type I.</li>
      <li><span class="emph">Miyawaki lifts II</span>: The subspace of (conjectured) Miyawaki lifts of type II.</li>
      <li><span class="emph">Other</span>: The subspace of cusp forms which are not Miyawaki lifts of type I or II.</li>
    </ul>
    """
    return _dimension_Sp6Z( wt_range)


def _dimension_Sp6Z( wt_range):
    headers = ['Total', 'Miyawaki lifts I', 'Miyawaki lifts II (conjectured)', 'Other']
    dct = dict()
    for k in wt_range:
        dims =  __dimension_Sp6Z( k)
        dct[k] = dict( (headers[j],dims[j]) for j in range(4))
    return headers, dct


def __dimension_Sp6Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(6,Z)$.

    OUTPUT
    ("Total", "Miyawaki-Type-1", "Miyawaki-Type-2 (conjectured)", "Interesting")
    Remember, Miywaki type 2 is ONLY CONJECTURED!!
    """
    if not is_even(wt):
        return (0, 0, 0, 0)
    R = PowerSeriesRing(IntegerRing(), default_prec=wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    R = PowerSeriesRing(IntegerRing(), default_prec=2 * wt - 1, names=('y',))
    (y,) = R._first_ngens(1)
    H_all = 1 / ((1 - x ** 4) * (1 - x ** 12) ** 2 * (1 - x ** 14) * (1 - x ** 18) *
                (1 - x ** 20) * (1 - x ** 30)) * (
                    1 + x ** 6 + x ** 10 + x ** 12 + 3 * x ** 16 + 2 * x ** 18 + 2 * x ** 20 +
                    5 * x ** 22 + 4 * x ** 24 + 5 * x ** 26 + 7 * x ** 28 + 6 * x ** 30 + 9 * x ** 32 +
                    10 * x ** 34 + 10 * x ** 36 + 12 * x ** 38 + 14 * x ** 40 + 15 * x ** 42 + 16 * x ** 44 +
                    18 * x ** 46 + 18 * x ** 48 + 19 * x ** 50 + 21 * x ** 52 + 19 * x ** 54 + 21 * x ** 56 +
                    21 * x ** 58 + 19 * x ** 60 + 21 * x ** 62 + 19 * x ** 64 + 18 * x ** 66 + 18 * x ** 68 +
                    16 * x ** 70 + 15 * x ** 72 + 14 * x ** 74 + 12 * x ** 76 + 10 * x ** 78 + 10 * x ** 80 +
                    9 * x ** 82 + 6 * x ** 84 + 7 * x ** 86 + 5 * x ** 88 + 4 * x ** 90 + 5 * x ** 92 +
                    2 * x ** 94 + 2 * x ** 96 + 3 * x ** 98 + x ** 102 + x ** 104 + x ** 108 + x ** 114)
    H_noncusp = 1 / (1 - x ** 4) / (1 - x ** 6) / (1 - x ** 10) / (1 - x ** 12)
    H_E = y ** 12 / (1 - y ** 4) / (1 - y ** 6)
    H_Miyawaki1 = H_E[wt] * H_E[2 * wt - 4]
    H_Miyawaki2 = H_E[wt - 2] * H_E[2 * wt - 2]
    a, b, c, d = H_all[wt], H_noncusp[wt], H_Miyawaki1, H_Miyawaki2
    return (a, c, d, a - b - c - d)



####################################################################
## Dimension formulas for Sp8Z
####################################################################

def dimension_Sp8Z( wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The subspace of cusp forms.</li>
      <li><span class="emph">Ikeda lifts</span>: The subspace of Ikeda lifts.</li>
      <li><span class="emph">Miyawaki lifts</span>: The subspace of Miyawaki lifts.</li>
      <li><span class="emph">Other</span>: The subspace that are not Ikeda or Miyawaki lifts.</li>
    </ul>
    """
    headers = ['Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Sp8Z( k)
        dct[k] = dict( (headers[j],dims[j]) for j in range(4))
    return headers, dct


def _dimension_Sp8Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(8,Z)$.

    OUTPUT
        ('Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other')
    """
    if wt > 16:
        raise NotImplementedError( 'Dimensions of $M_{k}(Sp(8,Z))$ for \(k > 16\) not implemented')
    if wt == 8:
        return (1, 1, 0, 0)
    if wt == 10:
        return (1, 1, 0, 0)
    if wt == 12:
        return (2, 1, 1, 0)
    if wt == 14:
        return (3, 2, 1, 0)
    if wt == 16:
        return (7, 2, 2, 3)
    # odd weight is zero up to weight 15
    return (0, 0, 0, 0)

# def _dimension_Sp8Z( wt_range):
#     """
#     Return the dimensions of subspaces of Siegel modular forms on $Sp(8,Z)$.

#     OUTPUT
#         ('Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other')
#     """
#     if wt_range[-1] > 16:
#         raise NotImplementedError( 'Dimensions of \(M_{k}\) for \(k > 16\) not implemented')

#     headers = ['Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other']
#     dct = dict ((k, { 'Total':0, 'Ikeda lifts':0, 'Miyawaki lifts':0, 'Other': 0}) for k in range(17))
#     dct[8]  = { 'Total':1, 'Ikeda lifts':1, 'Miyawaki lifts':0, 'Other': 0}
#     dct[10] = { 'Total':1, 'Ikeda lifts':1, 'Miyawaki lifts':0, 'Other': 0}
#     dct[12] = { 'Total':2, 'Ikeda lifts':1, 'Miyawaki lifts':1, 'Other': 0}
#     dct[14] = { 'Total':3, 'Ikeda lifts':2, 'Miyawaki lifts':1, 'Other': 0}
#     dct[16] = { 'Total':7, 'Ikeda lifts':2, 'Miyawaki lifts':2, 'Other': 3}

#     return headers, dct



####################################################################
## Dimension formulas for Gamma0_4 half integral
####################################################################

def dimension_Gamma0_4_half( wt_range):
    headers = ['Total', 'Non cusp', 'Cusp']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Gamma0_4_half( k)
        dct[k] = dict( (headers[j],dims[j]) for j in range(3))
    return headers, dct


def _dimension_Gamma0_4_half(k):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(4)$
    of half integral weight  k - 1/2.

    INPUT
        The realweight is k-1/2

    OUTPUT
        ('Total', 'Non cusp', 'Cusp')

    REMARK
        Note that formula from Hayashida's and Ibukiyama's paper has formula
        that coefficient of x^w is for weight (w+1/2). So here w=k-1.
    """
    R = PowerSeriesRing( IntegerRing(), default_prec = k, names=('x',))
    (x,) = R._first_ngens(1)
    H_all = 1 / (1 - x) / (1 - x ** 2) ** 2 / (1 - x ** 3)
    H_cusp = (2 * x ** 5 + x ** 7 + x ** 9 - 2 * x ** 11 + 4 * x ** 6 - x ** 8 + x ** 10 - 3 *
              x ** 12 + x ** 14) / (1 - x ** 2) ** 2 / (1 - x ** 6)
    a, c = H_all[k - 1], H_cusp[k - 1]
    return (a, a - c, c)
