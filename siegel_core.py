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
        ("Total", "Eisenstein", "Klingen", "Maass", "Interesting")
    """
    raise NotImplementedError

    
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
    for j in range(1, m+1):
        x+=( __S1k(k+2*j-1) - ((j*j)//(4*m)))
    return x


def _dimension_Kp(wt, tp):
    """
    Return the dimensions of subspaces of Siegel modular forms on $K(p)$
    for primes $p$.

    OUTPUT
        ("Total", "Gritsenko Lifts", "Nonlifts", "Oldforms")
    """
    if not is_prime(tp):
       raise ValueError, "Not yet implemented for nonprime Kp levels"

    if wt <= 1:
        return (0, 0,0,0);
    grits=__JacobiDimension(wt, tp)
    if wt == 2:
        oldforms=0
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
        oldforms=0
        p=tp
        total=0
        one=QQ(1)
        print one/8
        total += p*p/576 +p/8 -143*one/576
        total += kronecker_symbol(-1,p)*(p/96-one/8)
        total += kronecker_symbol(2,p)*one/8
        total += kronecker_symbol(3,p)*one/12
        total += kronecker_symbol(-3,p)*p/36
        newforms = total - grits - oldforms
        return (total, grits, newforms, oldforms)

    return ( tbi, grits, uk , uk);


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
        return ( tbi, tbi, tbi, tbi, tbi)


def _dimension_Gamma0_4_half(wtMinusHalf):
    """
    Return the dimensions of subspaces of Siegel modular forms$Gamma0(4)$
    of half integral weight.

    INPUT
        The realweight is wtMinusHalf+1/2

    OUTPUT
        ('Total', 'Non cusp', 'Cusp')
    """
    R = PowerSeriesRing(ZZ, default_prec = wtMinusHalf + 1 , names=('x',))
    (x,) = R._first_ngens(1)
    H_all= 1/(1-x)/(1 - x**2)**2/(1 - x**3)
    H_cusp= (2*x**5+x**7+ x**9 -2*x**11 +4*x**6 -x**8 +x**10 -3*x**12 +x**14)/(1 - x**2)**2/(1 - x**6)
    a,c = H_all[wtMinusHalf], H_cusp[wtMinusHalf]
    return (a,a-c,c)







