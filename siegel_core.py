from sage.all_cmdline import *


def S1k(k):
    y = k % 12
    if k<12:
        return 0
    if y == 2:
        return (k//12) - 1
    return (k//12)


def JacobiDimension(k, m):
    if (k%2)==0:
        x=0
        if k==2:
            x = ( len(divisors(m)) - 1)//2
        for j in range(1, m+1):
            x+=(S1k(k+2*j) - ((j*j)//(4*m)))
        return x
    x=0
    for j in range(1, m+1):
        x+=( S1k(k+2*j-1) - ((j*j)//(4*m)))
    return x


def _dimension_Kp(wt, tp):
    """
    Return (total, gritsenko lifts, newforms, oldforms)
    """
    if not is_prime(tp):
       raise ValueError, "Not yet implemented"

    oldforms=0
    newforms='?'
    grits=JacobiDimension(wt, tp)
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


def _dimension_Sp4Z(wt):
    """
    Return the dimensions of all, Klingen Eisenstein, Maass cusp,
    and interesting cusp Siegel modular forms.
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


def _dimension_Sp8Z(wt):
    """
    Return total dim of cuspforms, Ikeda, Miyawaki, other
    """
    if wt > 16:
        raise ValueError, 'Not yet implemented'
    if wt == 8: return (1,1,0,0)
    if wt == 10: return (1,1,0,0)
    if wt == 12: return (2,1,1,0)
    if wt == 14: return (3,2,1,0)
    if wt == 16: return (7,2,2,3)
    return (0,0,0,0)


    
def dimension( wt, group, char = None, tp = 0):
    """
    Return the dimensions of all, Klingen Eisenstein, Maass cusp,
    and interesting cusp Siegel modular forms.
    For Sp(8,Z), returns total dim of cuspforms, Ikeda, Miyawaki, other ...
    """
    if ('K(p)', None) == (group, char):
        return _dimension_Kp(wt, tp)

    if ('Sp(4,Z)', None, 0) == (group, char, tp):
        return _dimension_Sp4Z(wt)

    if ('Sp(8,Z)', None, 0) == (group, char, tp):
        return  _dimension_Sp8Z(wt)
         
##     elif ('Gamma_0(2)', None, 0) == (group, char, tp):
##         raise ValueError, 'Not yet implemented'
        
##     elif ('Gamma_0(3)', None, 0) == (group, char, tp):

##         H_all = ((1 + 2*x**4 + x**6)  +  x**15*(1 + 2*x**2 + x**6))/(1 - x**2)/(1 - x**4)/(1 - x**6)**2
##         H_cusp = ((1 + 2*x**4 + x**6)*(x**4 + x**6 - x**10)  +  x**15*(1 + 2*x**2 + x**6))/(1 - x**2)/(1 - x**4)/(1 - x**6)**2
##         a = H_all[wt]
##         b = c = d = 0
        
    else:
        raise ValueError, 'Not yet implemented'
