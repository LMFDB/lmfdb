# -*- coding: utf-8 -*-

from sage.misc.functional import is_odd, is_even
from sage.rings.integer import Integer
from sage.rings.power_series_ring import PowerSeriesRing
from sage.rings.integer_ring import IntegerRing


####################################################################
## For general dimension related data from the data base
####################################################################

DB_URL = 'mongodb://localhost:40000/'

def fetch( dct):

    import pymongo

    client = pymongo.MongoClient( DB_URL)
    db = client.siegel_modular_forms
    hps = db.dimensions
    item = hps.find_one( dct)
    client.close()
    return item


####################################################################
## Dimension formulas for Gamma(2)
####################################################################

def dimension_Gamma_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma(2)')

def dimension_Gamma1_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma1(2)')

def dimension_Gamma0_2( wt_range, j):
    return _dimension_Gamma_2( wt_range, j, group = 'Gamma0(2)')

def dimension_Sp4Z( wt_range, j):
    if 0 == j:
        return _dimension_Sp4Z( wt_range)
    else:
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
        raise NotImplementedError()

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
        #['3', '21', '111']
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
        raise NotImplemetedError()

    return headers, dct

################### cut here ######################################

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


def fetch_hilbert_polynomial( j, var, group = 'Gamma(2)'):
    
    item = None
    series = dict()
    import pymongo
    try:
        client = pymongo.MongoClient( DB_URL)
        db = client.siegel_modular_forms
        hps = db.Hilbert_Poincare_series
        item = hps.find_one( { 'sym_power': str(j), 'group': 'Gamma(2)'})
        client.close()
        if not item:
            raise NotImplementedError()
    except: 
        pass

    if item:
        p = [
         u'6',
         u'51',
         u'42',
         u'411',
         u'33',
         u'321',
         u'311',
         u'222',
         u'2211',
         u'21111',
         u'111111']
        # the polynomials are strings with variable 't'
        t = var
        for key in p:
            series[key] = eval( item[key])

    return series




# def __vvsf_dimension( wt_range, j, group = 'Gamma(2)'):
#     """
#     Return the arrays
#     [(k, d(k), e(k), c(k), p_{6}(k), ... for k in wt_range],
#     where d(k), e(k), c(k), p_{6}(k) are the dimensions
#     of $M_{k,j}(group)$ and its subspaces of
#     Non-cusp forms, Cusp forms, p_{6} canonical part, etc., respectively.

#     NOTE
#         Currently group can be
#         - Gamma(2)
#     """
#     if 'Gamma(2)' == group:
#         if is_odd(j):
#             return [(k,(0,)*15) for k in wt_range]
#         if j>=2 and  wt_range[0] < 4:
#             raise NotImplementedError()
#         P = PowerSeriesRing( IntegerRing(),  default_prec =wt_range[-1] + 1,  names = ('t',))
#         t = P.gen()
#         p_series = fetch_hilbert_polynomial( j, t, group = group)
#         Eis_series = 15*((1-j/2) * t**6 + t**4 * j/2)/(1-t**2)**2
    
#         dct = dict( (k, dict( (p, p_series[p][k]) for p in p_series))
#                   for k in wt_range)

#         for k in dct:
#             dct[k]['Total'] = sum( dct[k][p] for p in dct[k])
#             dct[k]['Non cusp'] = Eis_series[k]
#             dct[k]['Cusp'] =  dct[k]['Total'] - dct[k]['Non cusp']

#         headers = [ 'Total',
#                     'Non cusp',
#                     'Cusp',
#                     u'6',
#                     u'51',
#                     u'42',
#                     u'411',
#                     u'33',
#                     u'321',
#                     u'311',
#                     u'222',
#                     u'2211',
#                     u'21111',
#                     u'111111'
#                     ]
#     else:
#         raise NotImplementedError()

#     return headers, dct


 
