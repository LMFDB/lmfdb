# -*- coding: utf-8 -*-
# This file provides functions for computing dimensions of
# collections of Siegel modular forms. It is partly based on
# code implemented together with David Yuen and Fabien Cléry.
#
# Author: Nils Skoruppa <nils.skoruppa@gmail.com>

from flask import flash
from markupsafe import Markup
from sage.all import is_odd, is_even, ZZ, QQ, FunctionField, PowerSeriesRing
from lmfdb.db_backend import db
from lmfdb.search_parsing import parse_ints_to_list_flash

MAXWT = 9999
MAXWTRANGE = 100
MAXJ = 99

####################################################################
## For general dimension related data from the data base
## For Release 1.0 this is only relevant to Gamma_2
####################################################################

def parse_dim_args(dim_args, default_dim_args):
    res={}
    for v in ['k','j']:
        arg = dim_args.get(v) if dim_args else None
        if not arg:
            arg = default_dim_args.get(v) if default_dim_args else None
        if arg:
            res[v] = parse_ints_to_list_flash(arg, "$"+v+"$")
    args={}
    if 'k' in res:
        if res['k'][-1] > MAXWT:
            flash(Markup("Error: <span style='color:black'>$k$</span> cannot exceed <span style='color:black'>%s</span>." % MAXWT), "error")
            raise ValueError("dim_args")
        if len(res['k']) > MAXWTRANGE:
            flash(Markup("Error: range for <span style='color:black'>$k$</span> cannot include more than %s</span> values." % MAXWTRANGE), "error")
            raise ValueError("dim_args")
        args = {'k_range':res['k']}
    if 'j' in res:
        if res['j'][-1] > MAXJ:
            flash(Markup("Error: <span style='color:black'>$j$</span> cannot exceed <span style='color:black'>%s</span>." % MAXJ), "error")
            raise ValueError("dim_args")
        args['j_range'] = [j for j in res['j'] if j%2 == 0]
        if not args['j_range']:
            flash(Markup("Error: <span style='color:black'>$j$</span> should be a nonnegative even integer."), "error")
            raise ValueError("dim_args")
    return args

####################################################################
## Dimension formulas for Gamma(2), Gamma0(2), Gamma1(2), Sp4(Z)
####################################################################

def dimension_Gamma_2(wt_range, j):
    """
    <ul>
      <li>First entry of the respective triple: The full space.</li>
      <li>Second entry: The codimension of the subspace of cusp forms.</li>
      <li>Third entry: The subspace of cusp forms.</li>
    </ul>
    <p> More precisely, The triple $[a,b,c]$ in
    <ul>
      <li>
        row <span class="emph">All</span>
        and in in the $k$th column shows the dimension of
        the full space $M_{k,j}(\Gamma(2))$,
        of the non cusp forms, and of the cusp forms.</li>
      <li>
        in row <span class="emph">$p$</span>, where $p$ is a partition of $6$,
        and in in the $k$th column shows the multiplicity of the
        $\mathrm{Sp}(4,\Z)$-representation
        associated to $p$ in the full $\mathrm{Sp}(4,\Z)$-module
        $M_{k,j}(\Gamma(2))$,
        in the submodule of non cusp forms and of cusp forms.
        (See below for details.)
      </li>
    </ul>

    """
    return _dimension_Gamma_2(wt_range, j, group = 'Gamma(2)')

def dimension_Gamma1_2(wt_range, j):
    """
    <ul>
      <li>First entry of the respective triple: The full space.</li>
      <li>Second entry: The codimension of the subspace of cusp forms.</li>
      <li>Third entry: The subspace of cusp forms.</li>
    </ul>
    <p> More precisely, The triple $[a,b,c]$ in
    <ul>
      <li>
        row <span class="emph">All</span>
        and in in the $k$th column shows the dimension of
        the full space $M_{k,j}(\Gamma(2))$,
        of the non cusp forms, and of the cusp forms.</li>
      <li>
        in row <span class="emph">$p$</span>, where $p$ is a partition of $3$,
        and in in the $k$th column shows the multiplicity of the
        $\Gamma_1(2)$-representation
        associated to $p$ in the full $\Gamma_1(2)$-module $M_{k,j}(\Gamma(2))$,
        in the submodule of non cusp forms and of cusp forms.
        (See below for details.)
      </li>
    </ul>
    """
    return _dimension_Gamma_2(wt_range, j, group = 'Gamma1(2)')

def dimension_Gamma0_2(wt_range, j):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The codimension of the subspace of cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp forms.</li>
    </ul>
    """    
    return _dimension_Gamma_2(wt_range, j, group = 'Gamma0(2)')

def dimension_Sp4Z(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Eisenstein</span>: The subspace of Siegel Eisenstein series.</li>
      <li><span class="emph">Klingen</span>: The subspace of Klingen Eisenstein series.</li>
      <li><span class="emph">Maass</span>: The subspace of Maass liftings.</li>
      <li><span class="emph">Interesting</span>: The subspace spanned by cuspidal eigenforms that are not Maass liftings.</li>
    </ul>
    """
    return _dimension_Sp4Z(wt_range)

def dimension_Sp4Z_2(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The subspace of non cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp forms.</li>
    </ul>
    """
    return _dimension_Gamma_2(wt_range, 2, group = 'Sp4(Z)')

def dimension_table_Sp4Z_j(wt_range, j_range):
    result = {}
    for wt in wt_range:
        result[wt] = {}
    for j in j_range:
        if is_odd(j):
            for wt in wt_range:
                result[wt][j]=0
        else:
            _,olddim= dimension_Sp4Z_j(wt_range, j)
            for wt in wt_range:
                result[wt][j]=olddim[wt]['Total']
    return result

def dimension_Sp4Z_j(wt_range, j):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The subspace of non cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp forms.</li>
    </ul>
    """    
    return _dimension_Gamma_2(wt_range, j, group = 'Sp4(Z)')



def _dimension_Sp4Z(wt_range):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(4,Z)$.

    OUTPUT
        ("Total", "Eisenstein", "Klingen", "Maass", "Interesting")
    """
    headers = ['Total', 'Eisenstein', 'Klingen', 'Maass', 'Interesting']

    R = PowerSeriesRing(ZZ, default_prec = wt_range[-1] + 1, names = ('x',))
    (x,) = R._first_ngens(1)
    H_all = 1 / (1 - x ** 4) / (1 - x ** 6) / (1 - x ** 10) / (1 - x ** 12)
    H_Kl = x ** 12 / (1 - x ** 4) / (1 - x ** 6)
    H_MS = (x ** 10 + x ** 12) / (1 - x ** 4) / (1 - x ** 6)

    dct = dict((k,
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



def _dimension_Gamma_2(wt_range, j, group = 'Gamma(2)'):
    """
    Return the dict
    {(k-> partition ->  [ d(k), e(k), c(k)] for k in wt_range]},
    where d(k), e(k), c(k) are the dimensions
    of the $p$-canonical part of $M_{k,j}(\Gamma(2))$ and its subspaces of
    Non-cusp forms and Cusp forms.
    """

    partitions = [ u'6', u'51', u'42', u'411', u'33', u'321', u'3111', u'222', u'2211', u'21111', u'111111']
    latex_names = { 'Gamma(2)':'\\Gamma(2)', 'Gamma0(2)':'\\Gamma_0(2)', 'Gamma1(2)':'\\Gamma_1(2)', 'Sp4(Z)':'\\mathrm{Sp}(4,\mathbb{Z})' }

    if is_odd(j):
        dct = dict((k,dict((h,[0,0,0]) for h in partitions)) for k in wt_range)
        for k in dct:
            dct[k]['All'] = [0,0,0]
        partitions.insert(0,'All')
        return partitions, dct

    if 'Sp4(Z)' == group and 2 == j and wt_range[0] < 4:
        wt_range1 = [ k for k in wt_range if k < 4]
        wt_range2 = [ k for k in wt_range if k >= 4]
        if wt_range2 != []: 
            headers, dct = _dimension_Gamma_2(wt_range2, j, group)
        else:
            headers, dct = ['Total', 'Non cusp', 'Cusp'], {}
        for k in wt_range1:
            dct[k] = dict([(h,0) for h in headers])
        return headers, dct
    
    if j>=2 and  wt_range[0] < 4:
        raise NotImplementedError("Dimensions of \(M_{k,j}(%s)\) for <span style='color:black'>\(k<4\)</span> and <span style='color:black'>\(j\ge 2\)</span> not implemented" % latex_names.get(group,group))

    query = { 'sym_power': str(j), 'group' : 'Gamma(2)', 'space': 'total' }
    db_total = db.smf_dims.lucky(query)
    if not db_total:
        raise NotImplementedError('Dimensions of \(M_{k,j}\) for \(j=%d\) not implemented' % j)
    query['space'] = 'cusp'
    db_cusp = db.smf_dims.lucky(query)
    if not db_cusp:
        raise NotImplementedError('Dimensions of \(M_{k,j}\) for \(j=%d\) not implemented' % j)
    
    P = PowerSeriesRing(ZZ,  default_prec =wt_range[-1] + 1,  names = ('t'))
    Qt = FunctionField(QQ, names=('t'))
    total = dict()
    cusp = dict()
    for p in partitions:
        f = Qt(str(db_total[p]))
        total[p] = P(f.numerator())/P(f.denominator())
        f = Qt(str(db_cusp[p]))
        cusp[p] = P(f.numerator())/P(f.denominator())
    
    if 'Gamma(2)' == group:
        dct = dict((k, dict((p, [total[p][k], total[p][k]-cusp[p][k], cusp[p][k]])
                              for p in partitions)) for k in wt_range)
        for k in dct:
            dct[k]['All'] = [sum(dct[k][p][i] for p in dct[k]) for i in range(3)]
            
        partitions.insert(0,'All')
        headers = partitions

    elif 'Gamma1(2)' == group:
        ps = { '3': ['6', '42', '222'],
               '21': ['51', '42', '321'],
               '111': ['411', '33']}
        
        dct = dict((k, dict((p,[
                            sum(total[q][k] for q in ps[p]),
                            sum(total[q][k]-cusp[q][k] for q in ps[p]),
                            sum(cusp[q][k] for q in ps[p]),
                            ]) for p in ps)) for k in wt_range) 
        for k in dct:
            dct[k]['All'] = [sum(dct[k][p][i] for p in dct[k]) for i in range(3)]       

        headers = ps.keys()
        headers.sort(reverse = True)
        headers.insert(0,'All')

    elif 'Gamma0(2)' == group:
        headers = ['Total', 'Non cusp', 'Cusp']
        ps = ['6', '42', '222']
        dct = dict((k, { 'Total': sum(total[p][k] for p in ps),
                          'Non cusp': sum(total[p][k]-cusp[p][k] for p in ps),
                          'Cusp': sum(cusp[p][k] for p in ps)})
                    for k in wt_range)

    elif 'Sp4(Z)' == group:
        headers = ['Total', 'Non cusp', 'Cusp']
        p = '6'
        dct = dict((k, { 'Total': total[p][k],
                          'Non cusp': total[p][k]-cusp[p][k],
                          'Cusp': cusp[p][k]})
                    for k in wt_range)
    else:
        raise NotImplementedError('Dimension for %s not implemented' % group)

    return headers, dct


####################################################################
## Dimension formulas for Sp6Z
####################################################################

def dimension_Sp6Z(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Miyawaki lifts I</span>: The subspace of Miyawaki lifts of type I.</li>
      <li><span class="emph">Miyawaki lifts II</span>: The subspace of (conjectured) Miyawaki lifts of type II.</li>
      <li><span class="emph">Other</span>: The subspace of cusp forms which are not Miyawaki lifts of type I or II.</li>
    </ul>
    """
    return _dimension_Sp6Z(wt_range)


def _dimension_Sp6Z(wt_range):
    headers = ['Total', 'Miyawaki lifts I', 'Miyawaki lifts II (conjectured)', 'Other']
    dct = dict()
    for k in wt_range:
        dims =  __dimension_Sp6Z(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(4))
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
    R = PowerSeriesRing(ZZ, default_prec=wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    S = PowerSeriesRing(ZZ, default_prec=max(2 * wt - 1,1), names=('y',))
    (y,) = S._first_ngens(1)
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

def dimension_Sp8Z(wt_range):
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
        dims =  _dimension_Sp8Z(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(4))
    return headers, dct


def _dimension_Sp8Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(8,Z)$.

    OUTPUT
        ('Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other')
    """
    if wt > 16:
        raise NotImplementedError('Dimensions of $M_{k}(Sp(8,Z))$ for \(k > 16\) not implemented')
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

# def _dimension_Sp8Z(wt_range):
#     """
#     Return the dimensions of subspaces of Siegel modular forms on $Sp(8,Z)$.

#     OUTPUT
#         ('Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other')
#     """
#     if wt_range[-1] > 16:
#         raise NotImplementedError('Dimensions of \(M_{k}\) for \(k > 16\) not implemented')

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

def dimension_Gamma0_4_half(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
      <li><span class="emph">Non cusp</span>: The codimension of the subspace of cusp forms.</li>
      <li><span class="emph">Cusp</span>: The subspace of cusp forms.</li>
    </ul>
    """
    headers = ['Total', 'Non cusp', 'Cusp']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Gamma0_4_half(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(3))
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
    if k < 1:
        raise ValueError("$k$ must be a positive integer")
    R = PowerSeriesRing(ZZ, default_prec = k, names=('x',))
    (x,) = R._first_ngens(1)
    H_all = 1 / (1 - x) / (1 - x ** 2) ** 2 / (1 - x ** 3)
    H_cusp = (2 * x ** 5 + x ** 7 + x ** 9 - 2 * x ** 11 + 4 * x ** 6 - x ** 8 + x ** 10 - 3 *
              x ** 12 + x ** 14) / (1 - x ** 2) ** 2 / (1 - x ** 6)
    a, c = H_all[k - 1], H_cusp[k - 1]
    return (a, a - c, c)



####################################################################
## Dimension formulas for Gamma0_3_psi_3
####################################################################

def dimension_Gamma0_3_psi_3(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
    </ul>
    """
    headers = ['Total']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Gamma0_3_psi_3(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(len(headers)))
#    print headers, dct
    return headers, dct


def _dimension_Gamma0_3_psi_3(wt):
    """
    Return the dimensions of the space of Siegel modular forms
    on $Gamma_0(3)$ with character $\psi_3$.

    OUTPUT
        ("Total")

    REMARK
        Not completely implemented
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    B = 1 / (1 - x ** 1) / (1 - x ** 3) / (1 - x ** 4) / (1 - x ** 3)
    H_all_odd = B
    H_all_even = B * x ** 14
    if is_even(wt):
        return (H_all_even[wt],)
    else:
        return (H_all_odd[wt],)



####################################################################
## Dimension formulas for Gamma0_4_psi_4
####################################################################

def dimension_Gamma0_4_psi_4(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
    </ul>
    <p> Odd weights are not yet implemented.</p>
    """
    headers = ['Total']
    dct = dict()
    for k in wt_range:
        if is_odd(k): continue
        dims =  _dimension_Gamma0_4_psi_4(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(len(headers)))
    return headers, dct


def _dimension_Gamma0_4_psi_4(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms
    on $Gamma_0(4)$
    with character $\psi_4$.

    OUTPUT
        ("Total")

    REMARK
        The formula for odd weights is unknown or not obvious from the paper.
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    H_all_even = (x ** 12 + x ** 14) / (1 - x ** 2) ** 3 / (1 - x ** 6)
    if is_even(wt):
        return (H_all_even[wt],)
    else:
        raise NotImplementedError('Dimensions of $M_{k}(\Gamma_0(4), \psi_4)$ for odd $k$ not implemented')




####################################################################
## Dimension formulas for Gamma0_4
####################################################################

def dimension_Gamma0_4(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
    </ul>
    """
    headers = ['Total']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Gamma0_4(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(len(headers)))
    return headers, dct


def _dimension_Gamma0_4(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Gamma0(4)$.

    OUTPUT
        ("Total",)

    REMARK
        Not completely implemented
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    H_all = (1 + x ** 4)(1 + x ** 11) / (1 - x ** 2) ** 3 / (1 - x ** 6)
    return (H_all[wt],)



####################################################################
## Dimension formulas for Gamma0_3
####################################################################

def dimension_Gamma0_3(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The full space.</li>
    </ul>
    """
    headers = ['Total']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Gamma0_3(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(len(headers)))
    return headers, dct


def _dimension_Gamma0_3(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Gamma0(3)$.

    OUTPUT
        ("Total")

    REMARK
        Only total dimension implemented.
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1, names=('x',))
    (x,) = R._first_ngens(1)
    H_all = (1 + 2 * x ** 4 + x ** 6 + x ** 15 * (1 + 2 * x ** 2 + x ** 6)) / (1 - x ** 2) / (1 - x ** 4) / (1 - x ** 6) ** 2
    return (H_all[wt],)




####################################################################
## Dimension formulas for DUMMY_0
####################################################################

def dimension_Dummy_0(wt_range):
    """
    <ul>
      <li><span class="emph">Total</span>: The subspace of cusp forms.</li>
      <li><span class="emph">Yoda lifts</span>: The subspace of Master Yoda lifts.</li>
      <li><span class="emph">Hinkelstein series</span>: The subspace of Hinkelstein series.</li>
    </ul>
    """
    headers = ['Total', 'Yoda lifts', 'Hinkelstein series']
    dct = dict()
    for k in wt_range:
        dims =  _dimension_Dummy_0(k)
        dct[k] = dict((headers[j],dims[j]) for j in range(4))
    return headers, dct


def _dimension_Dummy_0(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms in the collection Dummy_0.

    OUTPUT
        ('Total', 'Yoda lifts', 'Hinkelstein series')
    """
    # Here goes your code ike e.g.:
    if wt > 37:
        raise NotImplementedError('Dimensions of $Dummy_0$ for \(k > 37\) not implemented')
    a,b,c = 1728, 28, 37

    return (a,b,c)
