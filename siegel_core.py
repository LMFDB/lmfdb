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

    total = dimKp(wt, tp)
    newforms = total - grits - oldforms
    return (total, grits, newforms, oldforms)

    #for nonprime levels:  return ( tbi, grits, tbi, tbi);


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

########### David's code for the dimension of S_k(K(p)), originally written by Cris in Maple #########

_sage_const_3 = Integer(3); _sage_const_2 = Integer(2); _sage_const_1 = Integer(1); _sage_const_0 = Integer(0); _sage_const_7 = Integer(7); _sage_const_6 = Integer(6); _sage_const_5 = Integer(5); _sage_const_4 = Integer(4); _sage_const_9 = Integer(9); _sage_const_8 = Integer(8); _sage_const_12 = Integer(12); _sage_const_11 = Integer(11); _sage_const_10 = Integer(10)
def H1(k,p):
  return (p**_sage_const_2 +_sage_const_1 )*(_sage_const_2 *k-_sage_const_2 )*(_sage_const_2 *k-_sage_const_3 )*(_sage_const_2 *k-_sage_const_4 )/(_sage_const_2 **_sage_const_9 *_sage_const_3 **_sage_const_3 *_sage_const_5 )

def H2(k,p):
  S1=((-_sage_const_1 )**k)*(_sage_const_2 *k-_sage_const_2 )*(_sage_const_2 *k-_sage_const_4 )/(_sage_const_2 **_sage_const_8 *_sage_const_3 **_sage_const_2 )
  if p==_sage_const_2 :
    S2=((-_sage_const_1 )**k)*(_sage_const_2 *k-_sage_const_2 )*(_sage_const_2 *k-_sage_const_4 )/(_sage_const_2 **_sage_const_9 )
  else:
    S2=((-_sage_const_1 )**k)*(_sage_const_2 *k-_sage_const_2 )*(_sage_const_2 *k-_sage_const_4 )/(_sage_const_2 **_sage_const_7 *_sage_const_3 )
  return S1+S2

def tink3(a0,a1,a2,k):
  if ((k % _sage_const_3 )==_sage_const_0 ): S=a0
  if ((k % _sage_const_3 )==_sage_const_1 ): S=a1
  if ((k % _sage_const_3 )==_sage_const_2 ): S=a2
  return QQ(S)

def tink4(a0,a1,a2,a3,k):
  if ((k % _sage_const_4 )==_sage_const_0 ): S=a0
  if ((k % _sage_const_4 )==_sage_const_1 ): S=a1
  if ((k % _sage_const_4 )==_sage_const_2 ): S=a2
  if ((k % _sage_const_4 )==_sage_const_3 ): S=a3
  return QQ(S)

def tink5(a0,a1,a2,a3,a4,k):
  if ((k %_sage_const_5 )==_sage_const_0 ): S=a0
  if ((k %_sage_const_5 )==_sage_const_1 ): S=a1
  if ((k %_sage_const_5 )==_sage_const_2 ): S=a2
  if ((k %_sage_const_5 )==_sage_const_3 ): S=a3
  if ((k %_sage_const_5 )==_sage_const_4 ): S=a4
  return QQ(S)

def tink6(a0,a1,a2,a3,a4,a5,k):
  if ((k %_sage_const_6 )==_sage_const_0 ): S=a0
  if ((k %_sage_const_6 )==_sage_const_1 ): S=a1
  if ((k %_sage_const_6 )==_sage_const_2 ): S=a2
  if ((k %_sage_const_6 )==_sage_const_3 ): S=a3
  if ((k %_sage_const_6 )==_sage_const_4 ): S=a4
  if ((k %_sage_const_6 )==_sage_const_5 ): S=a5
  return QQ(S)

def tink12(a0,a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,k):
  if ((k %_sage_const_12 )==_sage_const_0 ): S=a0
  if ((k %_sage_const_12 )==_sage_const_1 ): S=a1
  if ((k %_sage_const_12 )==_sage_const_2 ): S=a2
  if ((k %_sage_const_12 )==_sage_const_3 ): S=a3
  if ((k %_sage_const_12 )==_sage_const_4 ): S=a4
  if ((k %_sage_const_12 )==_sage_const_5 ): S=a5
  if ((k %_sage_const_12 )==_sage_const_6 ): S=a6
  if ((k %_sage_const_12 )==_sage_const_7 ): S=a7
  if ((k %_sage_const_12 )==_sage_const_8 ): S=a8
  if ((k %_sage_const_12 )==_sage_const_9 ): S=a9
  if ((k %_sage_const_12 )==_sage_const_10 ): S=a10
  if ((k %_sage_const_12 )==_sage_const_11 ): S=a11
  return QQ(S)

def LS5(p):     #  Gives the Legendre Symbol (5/p)
  return tink5(_sage_const_0 ,_sage_const_1 ,-_sage_const_1 ,-_sage_const_1 ,_sage_const_1 ,p)

def LS2(p):     #  Gives the Legendre Symbol (2/p)
  S1=(p**_sage_const_2 -_sage_const_1 )/_sage_const_8 
  S=(-_sage_const_1 )**(S1)
  if p==_sage_const_2 : S=_sage_const_0 
  return S

def LSminus1(p):   #  Gives the Legendre Symbol (-1/p)
  S1=(p-_sage_const_1 )/_sage_const_2 
  S=(-_sage_const_1 )**(S1)
  if p==_sage_const_2 : S=_sage_const_1 
  return S

def LSminus3(p):    #  Gives the Legendre Symbol (-3/p) ==(p/3)
  return tink3(_sage_const_0 ,_sage_const_1 ,-_sage_const_1 ,p)

def H3(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink4(k-_sage_const_2 ,_sage_const_1 -k,_sage_const_2 -k,k-_sage_const_1 ,k)
  if p==_sage_const_2 : S=_sage_const_5 *S1/(_sage_const_2 **_sage_const_5 *_sage_const_3 )
  else: S=S1/(_sage_const_2 **_sage_const_4 *_sage_const_3 )
  return S

def H4(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink3(_sage_const_2 *k-_sage_const_3 ,_sage_const_1 -k,_sage_const_2 -k,k)
  if p==_sage_const_3 : S=_sage_const_5 *S1/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_3 )
  else:  S=S1/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_3 )
  return S

def H5(k,p):
  S=_sage_const_0 
  S=tink6(-_sage_const_1 ,_sage_const_1 -k,_sage_const_2 -k,_sage_const_1 ,k-_sage_const_1 ,k-_sage_const_2 ,k)/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_2 )
  return S

def H6(k,p):
  S=_sage_const_0 
  if ((p % _sage_const_4 )==_sage_const_1 ): S=_sage_const_5 *(_sage_const_2 *k-_sage_const_3 )*(p+_sage_const_1 )/(_sage_const_2 **_sage_const_7 *_sage_const_3 )+(-_sage_const_1 )**k*(p+_sage_const_1 )/(_sage_const_2 **_sage_const_7 )
  if ((p % _sage_const_4 )==_sage_const_3 ): S=(_sage_const_2 *k-_sage_const_3 )*(p-_sage_const_1 )/(_sage_const_2 **_sage_const_7 )+_sage_const_5 *(-_sage_const_1 )**k*(p-_sage_const_1 )/(_sage_const_2 **_sage_const_7 *_sage_const_3 )
  if p==_sage_const_2 : S=_sage_const_3 *(_sage_const_2 *k-_sage_const_3 )/(_sage_const_2 **_sage_const_7 )+_sage_const_7 *(-_sage_const_1 )**k/(_sage_const_2 **_sage_const_7 *_sage_const_3 )
  return S

def H7(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink3(_sage_const_0 ,-_sage_const_1 ,_sage_const_1 ,k)
  if ((p % _sage_const_3 )==_sage_const_1 ): S=(_sage_const_2 *k-_sage_const_3 )*(p+_sage_const_1 )/(_sage_const_2 *_sage_const_3 **_sage_const_3 )+S1*(p+_sage_const_1 )/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_3 )
  if ((p % _sage_const_3 )==_sage_const_2 ): S=(_sage_const_2 *k-_sage_const_3 )*(p-_sage_const_1 )/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_3 )+S1*(p-_sage_const_1 )/(_sage_const_2 *_sage_const_3 **_sage_const_3 )
  if p==_sage_const_3 : S=_sage_const_5 *(_sage_const_2 *k-_sage_const_3 )/(_sage_const_2 **_sage_const_2 *_sage_const_3 **_sage_const_3 )+S1/(_sage_const_3 **_sage_const_3 )
  return S

def H8(k,p):
  S=_sage_const_0 
  S=tink12(_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,-_sage_const_1 ,-_sage_const_1 ,-_sage_const_1 ,-_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,_sage_const_1 ,_sage_const_1 ,_sage_const_1 ,k)/(_sage_const_2 *_sage_const_3 )
  return S

def H9(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink6(_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,-_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,k)
  if p==_sage_const_2 : S=S1/(_sage_const_2 *_sage_const_3 **_sage_const_2 )
  else:  S=_sage_const_2 *S1/(_sage_const_3 **_sage_const_2 )
  return S

def H10(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink5(_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,-_sage_const_1 ,_sage_const_0 ,k)
  S=(LS5(p)+_sage_const_1 )*S1/_sage_const_5 
  return S

def H11(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink4(_sage_const_1 ,_sage_const_0 ,_sage_const_0 ,-_sage_const_1 ,k)
  S=(LS2(p)+_sage_const_1 )*S1/(_sage_const_2 **_sage_const_3 )
  if p==_sage_const_2 : S=S1/(_sage_const_2 **_sage_const_3 )
  return S

def H12(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S2=_sage_const_0 
  S3=_sage_const_0 
  S1=tink3(_sage_const_0 ,_sage_const_1 ,-_sage_const_1 ,k)/(_sage_const_2 *_sage_const_3 )
  S2=(-_sage_const_1 )**k/(_sage_const_2 *_sage_const_3 )
  S3=(-_sage_const_1 )**k/(_sage_const_2 **_sage_const_2 *_sage_const_3 )
  S=tink12(_sage_const_0 ,S1,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,_sage_const_0 ,S2,p)
  if p==_sage_const_2 : S=S3
  if p==_sage_const_3 : S=S3
  return S

def H(k,p):
  S= H1(k,p)+H2(k,p)+H3(k,p)+H4(k,p)+H5(k,p)+H6(k,p)
  S = S+H7(k,p)+H8(k,p)+H9(k,p)+H10(k,p)+H11(k,p)+H12(k,p)
  return S

def I1(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink6(_sage_const_0 ,_sage_const_1 ,_sage_const_1 ,_sage_const_0 ,-_sage_const_1 ,-_sage_const_1 ,k)
  S=S1/_sage_const_6 
  return S

def I2(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink3(-_sage_const_2 ,_sage_const_1 ,_sage_const_1 ,k)
  S=S1/(_sage_const_2 *_sage_const_3 **_sage_const_2 )
  return S

def I3(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S2=_sage_const_0 
  S3=_sage_const_0 
  S1=tink3(-_sage_const_2 ,_sage_const_1 ,_sage_const_1 ,k)/(_sage_const_3 **_sage_const_2 )
  S2=_sage_const_2 *tink3(-_sage_const_1 ,_sage_const_1 ,_sage_const_0 ,k)/(_sage_const_3 **_sage_const_2 )
  S3=_sage_const_2 *tink3(-_sage_const_1 ,_sage_const_0 ,_sage_const_1 ,k)/(_sage_const_3 **_sage_const_2 )
  S=tink3(_sage_const_0 ,S2,S3,p)
  if p==_sage_const_3 : S=S1
  return S

def I4(k,p):
  S=_sage_const_0 
  S1=_sage_const_0 
  S1=tink4(-_sage_const_1 ,_sage_const_1 ,_sage_const_1 ,-_sage_const_1 ,k)
  S=S1/(_sage_const_2 **_sage_const_2 )
  return S

def I5(k,p):
  return (-_sage_const_1 )**k/(_sage_const_2 **_sage_const_3 )

def I6(k,p):
 return (_sage_const_2 -LSminus1(p))*(-_sage_const_1 )**k/(_sage_const_2 **_sage_const_4 )

def I7(k,p):
  return -(-_sage_const_1 )**k*(_sage_const_2 *k-_sage_const_3 )/(_sage_const_2 **_sage_const_3 *_sage_const_3 )

def I8(k,p):
  return -p*(_sage_const_2 *k-_sage_const_3 )/(_sage_const_2 **_sage_const_4 *_sage_const_3 **_sage_const_2 )

def I9(k,p):
  return QQ(-_sage_const_1 )/(_sage_const_2 **_sage_const_3 *_sage_const_3 )

def I10(k,p):
  return (p+_sage_const_1 )/(_sage_const_2 **_sage_const_3 *_sage_const_3 )

def I11(k,p):
  return (_sage_const_1 +LSminus1(p))*(-_sage_const_1 )/(_sage_const_8 )

def I12(k,p):
  return (_sage_const_1 +LSminus3(p))*(-_sage_const_1 )/(_sage_const_6 )

def II(k,p):
  S= I1(k,p)+I2(k,p)+I3(k,p)+I4(k,p)+I5(k,p)+I6(k,p)
  S=S+I7(k,p)+I8(k,p)+I9(k,p)+I10(k,p)+I11(k,p)+I12(k,p)
  return S

def dimKp(k,p): 
# This returns the dimension of cusp forms for K(p)
# of weight k>=3 and PRIME level p
  S= H(k,p)+II(k,p)
  if k==_sage_const_3 : S=H(k,p)+II(k,p)+_sage_const_1 
  return S








