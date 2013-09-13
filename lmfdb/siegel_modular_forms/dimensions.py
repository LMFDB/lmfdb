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

