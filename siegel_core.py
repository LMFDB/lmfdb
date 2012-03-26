# -*- coding: utf-8 -*-
from sage.all_cmdline import *

tbi = 't.b.i.'
uk = '?'



def _dimension_Sp4Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(4,Z)$.
    
    OUTPUT
        ("Total", "Eisenstein", "Klingen", "Maass", "Interesting")
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all  = 1/(1 - x**4)/(1 - x**6)/(1 - x**10)/(1 - x**12)
    H_Kl   = x**12/(1 - x**4)/(1 - x**6)
    H_MS = (x**10 + x**12)/(1 - x**4)/(1 - x**6)
    if is_even(wt):
        a,b,c,d = H_all[wt], 1 if wt>=4 else 0, H_Kl[wt], H_MS[wt]
        return (a,b,c,d,a - b - c - d)
    else:
        a = H_all[wt - 35]
        return (a,0,0,0,a)


def _dimension_Sp4Z_2(wt):
    """
    Return the dimensions of subspaces of vector-valued Siegel modular forms on $Sp(4,Z)$
    of weight integral,2.
    
    OUTPUT
        ("Total", "Non-cusp", "Cusp")

    REMARK
        Satoh's paper does not have a description of the cusp forms.
    """
    if not is_even(wt):
         return (uk,uk,uk)
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H  = 1/(1 - x**4)/(1 - x**6)/(1 - x**10)/(1 - x**12)
    V  = 1/(1 - x**6)/(1 - x**10)/(1 - x**12)
    W  = 1/(1 - x**10)/(1 - x**12)
    a = H[wt - 10]+H[wt - 14]+H[wt - 16]+V[wt - 16]+V[wt - 18]+V[wt - 22]
    return (a, uk, uk)

    
def _dimension_Sp6Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(6,Z)$.
    
    OUTPUT

    """
    raise NotImplementedError


def _dimension_Sp8Z(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms on $Sp(8,Z)$.

    OUTPUT
        ('Total', 'Ikeda lifts', 'Miyawaki lifts', 'Other')
    """
    if wt > 16:
        raise ValueError, 'Not yet implemented'
    if wt == 8: return (1,1,0,0)
    if wt == 10: return (1,1,0,0)
    if wt == 12: return (2,1,1,0)
    if wt == 14: return (3,2,1,0)
    if wt == 16: return (7,2,2,3)
    # odd weight is zero up to weight 15
    return (0,0,0,0)


def __S1k(k):
    y = k % 12
    if k<12:
        return 0
    if y == 2:
        return (k//12) - 1
    return (k//12)


def __JacobiDimension(k, m):
    if (k%2)==0:
        x=0
        if k==2:
            x = ( len(divisors(m)) - 1)//2
        for j in range(1, m+1):
            x+=(__S1k(k+2*j) - ((j*j)//(4*m)))
        return x
    x=0
    for j in range(1, m):
        x+=( __S1k(k+2*j-1) - ((j*j)//(4*m)))
    return x


def _dimension_Kp(wt, tp):
    """
    Return the dimensions of subspaces of Siegel modular forms on $K(p)$
    for primes $p$.

    OUTPUT
        ("Total", "Gritsenko Lifts", "Nonlifts", "Oldforms")
    """
    p=tp
    one=QQ(1)
    oldforms=0
    grits=__JacobiDimension(wt, tp)

    if not is_prime(tp):
        return (uk, grits, uk, uk)

    if wt <= 1:
        return (0, 0,0,0);
    if wt == 2:
        newforms='?'
        total='' + str(grits) + ' - ?'
        if tp < 600:
           newforms=0
           total=grits
           interestingPrimes=[277, 349, 353, 389, 461, 523, 587]
           if tp in interestingPrimes:
               if tp == 587:
                   newforms = '0 - 2'
                   total = '' + str(grits) + ' - ' + str(grits+2)
               newforms = '0 - 1'
               total = '' + str(grits) + ' - ' + str(grits+1)
        return (total, grits, newforms, oldforms)
    if wt ==4:
      total=0
      if p>=5:    
        total += one*p*p/576 +one*p/8 -143*one/576
        total += one*kronecker_symbol(-1,p)*(p*one/96-one/8)
        total += one*kronecker_symbol(2,p)*one/8
        total += one*kronecker_symbol(3,p)*one/12
        total += one*kronecker_symbol(-3,p)*p*one/36
        newforms = total - grits - oldforms
        return (total, grits, newforms, oldforms)

    if wt ==3:
        p=tp
        if (p==2) or (p==3):
            return(0,0,0,0)
        total=0;
        total=-1+one/2880*(p**2 -1)+one/64*(p+1)*(1-kronecker_symbol(-1,p))
        total+=5*one/192*(p-1)*(1+kronecker_symbol(-1,p))
        total+=one/72*(p+1)*(1-kronecker_symbol(-3,p))
        total+=one/36*(p-1)*(1+kronecker_symbol(-3,p))
        pmod5 = p % 5
        if pmod5==0:
            total+=one/5
        if (pmod5==2) or (pmod5==3):
            total+=2*one/5
        if (p % 12)==5:
            total+=one/6
        total+=one/8*(1-kronecker_symbol(2,p))
        newforms = total - grits - oldforms
        return (total, grits, newforms, oldforms)

    return ( tbi, grits, tbi, 0);


def _dimension_Gamma0_2(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(2)$.
    
    OUTPUT
        ( "Total", "Eisenstein", "Klingen", "Maass", "Interesting")

    REMARK
        Only total dimension implemented.
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all  = 1/(1 - x**2)/(1 - x**4)/(1 - x**4)/(1 - x**6)
    #H_cusp  = ??
    #H_Kl   = ??
    #H_MS = ??
    if is_even(wt):
        a = H_all[wt]
        return (a, tbi, tbi, tbi, tbi)
    else:
        a = H_all[wt - 19]
        return (a,0,0,0,a)


def _dimension_Gamma0_3(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(3)$.
    
    OUTPUT
        ( "Total", "Eisenstein", "Klingen", "Maass", "Interesting")

    REMARK
        Only total dimension implemented.
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all= (1+2*x**4+x**6+ x**15*(1+2*x**2+x**6))/(1 - x**2)/(1 - x**4)/(1 - x**6)**2
    #H_cusp  = ??
    #H_Kl   = ??
    #H_MS = ??
    if is_even(wt):
        a = H_all[wt]
        return (a, tbi, tbi, tbi, tbi)
    else:
        a = H_all[wt]
        return ( a, tbi, tbi, 0, tbi)


def _dimension_Gamma0_3_psi_3(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(3)$
    with character $\psi_3$.

    OUTPUT
        ( "Total", "Eisenstein", "Klingen", "Maass", "Interesting")
    
    REMARK
        Not completely implemented
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    B =  1/(1 - x**1)/(1 - x**3)/(1 - x**4)/(1 - x**3)
    H_all_odd = B
    H_all_even  = B*x**14
    #H_cusp  = ??
    #H_Kl   = ??
    #H_MS = ??
    if is_even(wt):
        a = H_all_even[wt]
        return ( a, tbi, tbi, tbi, tbi)
    else:
        a = H_all_odd[wt]
        return ( a, tbi, tbi, 0, tbi)


def _dimension_Gamma0_4(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(4)$.

    OUTPUT
        ( "Total", "Eisenstein", "Klingen", "Maass", "Interesting")

    REMARK
        Not completely implemented
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all= (1+x**4)(1+x**11)/(1 - x**2)**3/(1 - x**6)
    #H_cusp  = ??
    #H_Kl   = ??
    #H_MS = ??
    if is_even(wt):
        a = H_all[wt]
        return ( a, tbi, tbi, tbi, tbi)
    else:
        a = H_all[wt]
        return ( a, tbi, tbi, 0, tbi)


def _dimension_Gamma0_4_psi_4(wt):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(4)$
    with character $\psi_4$.

    OUTPUT
        ( "Total", "Eisenstein", "Klingen", "Maass", "Interesting")

    REMARK
        The formula for odd weights is unknown or not obvious from the paper.
    """
    R = PowerSeriesRing(ZZ, default_prec = wt + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all_even= (x**12+x**14)/(1 - x**2)**3/(1 - x**6)
    #H_cusp  = ??
    #H_Kl   = ??
    #H_MS = ??
    if is_even(wt):
        a = H_all_even[wt]
        return ( a, tbi, tbi, tbi, tbi)
    else:
        return ( uk, uk, uk, uk, uk)


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
    R = PowerSeriesRing(ZZ, default_prec = k , names=('x',))
    (x,) = R._first_ngens(1)
    H_all= 1/(1-x)/(1 - x**2)**2/(1 - x**3)
    H_cusp= (2*x**5+x**7+ x**9 -2*x**11 +4*x**6 -x**8 +x**10 -3*x**12 +x**14)/(1 - x**2)**2/(1 - x**6)
    a,c = H_all[k-1], H_cusp[k-1]
    return (a,a-c,c)







