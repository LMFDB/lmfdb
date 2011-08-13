
include "interrupt.pxi"  # ctrl-c interrupt block support
include "stdsage.pxi"  # ctrl-c interrupt block support

include "cdefs.pxi"
# -*- coding=utf-8 -*-
#*****************************************************************************
#ö  Copyright (C) 2010  Fredrik Strömberg <stroemberg@mathematik.tu-darmstadt.de>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************


include "sage/ext/cdefs.pxi"
include "sage/ext/interrupt.pxi"  # ctrl-c interrupt block support
include "sage/ext/stdsage.pxi"  # ctrl-c interrupt block support
import cython
r"""
Low-precision algorithms for the K-Bessel function.

    AUTHOR:
    
    - Fredrik Strömberg (April 2010)


    EXAMPLES::


        sage: besselk_dp(10.0,5.0)
        -0.7183327166568183
        sage: besselk_dp_rec(10.0,3.0)
        -6.3759939798738967e-08
        sage: besselk_dp_rec(10.0,3.0,pref=1)
        -0.42308698672505796
        sage: besselk_dp_pow(10.0,3.0)
        -6.3759939798739404e-08
        sage: besselk_dp_pow(10.0,3.0,pref=1)
        -0.42308698672506084
        sage: a=besselk_dp_pow(10.0,3.0,pref=1);a
        -0.42308698672506084
        sage: b=besselk_dp_rec(10.0,3.0,pref=1);b
        -0.42308698672505796
        sage: abs(a-b)
        2.886579864025407e-15
        sage: besselk_dp_rec(100.0,3.0,pref=1)
        0.082457701468151401
        age: RF=RealField(150)
        sage: CF=ComplexField(150)
        sage: bessel_K(CF(100*I),RF(3))*exp(RF.pi()*RF(50))
        0.0824577014681303
        sage: _-besselk_dp_rec(100.0,3.0,pref=1)
        -2.1094237467877974e-14


"""

cdef extern from "complex.h":
    double complex _Complex_I
    
cdef extern from "math.h":
    double log(double)
    double exp(double)
    double cos(double)
    double sin(double)
    double sinh(double)
    double fabs(double)
    int ceil(double)
    double cabs(double complex)
    double pow(double,double)
    double complex clog(double complex)
    double cimag(double complex)
    double creal(double complex)
    double carg(double complex)

#cdef from sage.functions.special:
#    double log_gamma(double)

cdef double cppi  =<double> 3.14159265358979323846264338327950288419716939 # =pi
cdef double pihalf=<double> 1.5707963267948966192313216916397514420985847  # =pi/2
cdef double ln2PI2= <double> 0.91893853320467274178032973640561763986139747 #=ln(2pi)/2
cdef double d_one =<double> 1.0
cdef double d_half =<double> 0.5
cdef double d_two =<double> 2.0
cdef double d_ten =<double> 10.0
cdef double d_20 =<double> 20.0
cdef double d_100 =<double> 100.0
cdef double complex c_one =<double complex> 1.0
cdef double complex c_zero =<double complex> 0.0


cpdef besselk_dp(double R,double x,double prec=1e-14,int pref=0):  
    r"""
    Modified K-Bessel function in double precision. Chooses the most appropriate algorithm.

    INPUT:

       - `R` -- parameter (double)

        - `x` -- argument (double)

        - `prec` -- precision (default 1E-14, double)

        - `pref` -- use prefactor (integer, default 0) 

               = 1 => computes K_iR(x)*exp(pi*R/2)

               = 0 => computes K_iR(x)

    OUTPUT:
    
     - exp(Pi*R/2)*K_{i*R}(x)  -- double

    EXAMPLES::


        sage: besselk_dp_rec(10.0,5.0)
        -0.7183327166568183
        sage: besselk_dp_rec(10.0,3.0)
        -6.3759939798738967e-08
        sage: besselk_dp_rec(10.0,3.0,pref=1)
        -0.42308698672505796
    """
    if(R<0):
        RR=-R
    else:
        RR=R
    if(x<0):
        raise ValueError," Need x>0! Got x=%s" % x

    if(x<R*0.7):
        try:
            res=besselk_dp_pow(RR,x,prec,pref)
        except ValueError:
            res=besselk_dp_rec(RR,x,prec,pref)
    else:
        res=besselk_dp_rec(RR,x,prec,pref)
    return res

@cython.cdivision(True) 
cdef double besselk_dp_rec(double R,double x,double prec=1e-14,int pref=0):   # |r| <<1000, x >> 0 !
    r"""
    Modified K-Bessel function in double precision using the backwards Miller-recursion algorithm. 

    INPUT:
     - ''R'' -- double
     - ''x'' -- double
     - ''prec'' -- (default 1E-12) double
     - ''pref'' -- (default 1) int
                =1 => computes K_iR(x)*exp(pi*R/2)
                =0 => computes K_iR(x)

    OUTPUT:
     - exp(Pi*R/2)*K_{i*R}(x)  -- double
     
    EXAMPLES::


        sage: besselk_dp_rec(10.0,5.0)
        -0.7183327166568183
        sage: besselk_dp_rec(10.0,3.0)
        -6.3759939798738967e-08
        sage: besselk_dp_rec(10.0,3.0,pref=1)
        -0.42308698672505796
        sage: besselk_dp_pow(10.0,3.0)
        -6.3759939798739404e-08
        sage: besselk_dp_pow(10.0,3.0,pref=1)
        -0.42308698672506084
        sage: a=besselk_dp_pow(10.0,3.0,pref=1);a
        -0.42308698672506084
        sage: b=besselk_dp_rec(10.0,3.0,pref=1);b
        -0.42308698672505796
        sage: abs(a-b)
        2.886579864025407e-15
        sage: besselk_dp_rec(100.0,3.0,pref=1)
        0.082457701468151401
        age: RF=RealField(150)
        sage: CF=ComplexField(150)
        sage: bessel_K(CF(100*I),RF(3))*exp(RF.pi()*RF(50))
        0.0824577014681303
        sage: _-besselk_dp_rec(100.0,3.0,pref=1)
        -2.1094237467877974e-14


    """
    if(x<0):
        raise ValueError,"X<0"
    #! To make a specific test is time-consuming
    cdef double p=0.25+R*R
    cdef double q=2.0*(x-1.0)
    cdef double t=0.0 #/*arbitrary*/
    cdef double k=d_one #/*arbitrary*/;
    cdef double err=d_one
    cdef int NMAX=5000
    cdef int n_start=1 #128
    cdef double ef1=log(d_two*x/cppi)
    cdef double mr
    cdef int n=n_start
    cdef double tmp,tmp2,ef,nr,mr_p1,mr_m1,efarg
    cdef int nn
    cdef double den
    for nn from 1 <= nn <= NMAX:
        err=fabs(t-k)
        if(err < prec):
            if(n>n_start+40):
                break
        n=n+20       
        t=k 
        y=d_one #               !/*arbitrary*/1; 
        k=d_one
        d=d_one
        tmp=d_two*x-R*cppi
        nr=<double> n
        if(tmp>1300.0):
            return 0.0
        ef = exp((ef1 + tmp)/((<double>2.0) *nr))
        mr_p1=<double> n+1   # m+1
        mr=<double> n        # m 
        for m from n >=m>=1:
            mr_m1=<double> m-1 # m-1
            den = (q+(mr_p1)*(d_two-y))
            y=(mr_m1+p/mr)/den
            k=ef*(d+y*k)
            d=d*ef
            mr_p1=mr
            mr=mr_m1
        if(k==0.0):
            s='the K-bessel routine failed (k large) for x,R=%s,%s, value=%s' 
            raise ValueError,s%(x,R,k)
        k=d_one/k;
    if( k > 1E30 ): #something big... 
        s='the K-bessel routine failed (k large) for x,R=%s,%s, value=%s' 
        raise ValueError,s%(x,R,k)
    if(nn>=NMAX):
        s='the K-bessel routine failed (too many iterations) for x,R=%s,%s, value=%s' 
        raise ValueError,s%(x,R,k)
    #!k= exp( pi*r/2) * K_ir( x) !
    if(pref==1):
        return k
    else:
        return k*exp(-cppi*R/d_two)

@cython.cdivision(True) 
cdef double besselk_dp_pow(double R,double x,double prec=1E-12,int pref=0):
    r"""
    Computes the modified K-Bessel function: K_iR(x) using power series.

    INPUT:

        - `R` -- parameter (double)

        - `x` -- argument (double)

        - `prec` -- precision (double)

        - `pref` -- use prefactor (integer, default 0) 

               = 1 => computes K_iR(x)*exp(pi*R/2)

               = 0 => computes K_iR(x)

    OUTPUT:

        - `res` -- double
    
    EXAMPLES::


        sage: besselk_dp_pow(10.0,3.0)
        -6.3759939798739404e-08
        sage: besselk_dp_pow(10.0,3.0,pref=1)
        -0.42308698672506084
        sage: a=besselk_dp_pow(10.0,3.0,pref=1);a
        -0.42308698672506084
        sage: b=besselk_dp_rec(10.0,3.0,pref=1);b
        -0.42308698672505796
        sage: abs(a-b)
        2.886579864025407e-15

    REFERENCES:
    - A. Gil, J. Segura, and N. M. Temme, Evaluation of the modified Bessel function of the third kind of imaginary orders, J. Comput. Phys. 175 (2002), no. 2, 398-411.


    """
    cdef double xh=d_half*x
    cdef double xh2=xh*xh
    cdef double complex iR
    iR=_Complex_I*R
    cdef double complex gamma0=my_lngamma(d_one,R)
    cdef double sigma0=cimag(gamma0)
    cdef double rsigma0=creal(gamma0)
    cdef double th=R*log(xh)-sigma0
    cdef double tmp_sin = sin(th)
    cdef double tmp_cos = cos(th)      
    cdef double tmp_factor=sqrt(cppi/(R*sinh(cppi*R)))
    cdef double f0=-tmp_factor*tmp_sin
    cdef double Rsq=R*R
    cdef double pi_halfR=pihalf*R
    cdef double r0=R*tmp_factor*tmp_cos
    cdef double r1=R*tmp_factor/(d_one+Rsq)*(tmp_cos+R*tmp_sin)
    cdef double c0=d_one
    cdef double rk1=r0  # r(k-1)
    cdef double fk1=f0  # f(k-1)
    cdef double summa=f0
    cdef double exp_Pih_R=exp(pi_halfR)   
    cdef double fk=(fk1+rk1)/(d_one+Rsq)
    cdef double rk=r1
    cdef double ck=xh2
    summa=summa+ck*fk
    fk1=fk
    rk1=r1
    cdef double rk2=r0
    cdef double ck1=ck
    cdef double test
    cdef int N_max=1000
    cdef int k
    for k from  2<=k<=N_max:
        kk=<double> k
        den=(kk*kk+Rsq)
        fk=(kk*fk1+rk1)/den
        rk=((d_two*kk-d_one)*rk1-rk2)/den
        ck=xh2*ck1/kk
        summa=summa+ck*fk
        test = ck*fk/summa*exp_Pih_R
        test = fabs(test)
        if test < prec:
            break
        fk1=fk
        rk2=rk1
        rk1=rk
        ck1=ck
    if(k>=N_max):
        s="Maximum numbber of iterations reached x,R=%s,%s val=%s"
        raise ValueError,s%(x,R,summa)
        stat=1  #! We reached end of loop
    if(pref==1):
        res=summa*exp_Pih_R
    else:
        res=summa
    return res



### Scaled Bernoulli numbers
cdef int num_ber=50
cdef double Ber[51] # Ber[n]=B[2n]/(2n*(2n-1))

Ber[ 1 ]= 0.083333333333333333333333333333333333333333333                                        
Ber[ 2 ]= -0.0027777777777777777777777777777777777777777778                                      
Ber[ 3 ]= 0.00079365079365079365079365079365079365079365079                                      
Ber[ 4 ]= -0.00059523809523809523809523809523809523809523810                                     
Ber[ 5 ]= 0.00084175084175084175084175084175084175084175084                                      
Ber[ 6 ]= -0.0019175269175269175269175269175269175269175269                                      
Ber[ 7 ]= 0.0064102564102564102564102564102564102564102564                                       
Ber[ 8 ]= -0.029550653594771241830065359477124183006535948                                       
Ber[ 9 ]= 0.17964437236883057316493849001588939669435025
Ber[ 10 ]= -1.3924322169059011164274322169059011164274322
Ber[ 11 ]= 13.402864044168391994478951000690131124913734
Ber[ 12 ]= -156.84828462600201730636513245208897382810426
Ber[ 13 ]= 2193.1033333333333333333333333333333333333333
Ber[ 14 ]= -36108.771253724989357173265219242230736483610
Ber[ 15 ]= 691472.26885131306710839525077567346755333407
Ber[ 16 ]= -1.5238221539407416192283364958886780518659077e7
Ber[ 17 ]= 3.8290075139141414141414141414141414141414141e8
Ber[ 18 ]= -1.0882266035784391089015149165525105374729435e10
Ber[ 19 ]= 3.4732028376500225225225225225225225225225225e11
Ber[ 20 ]= -1.2369602142269274454251710349271324881080979e13
Ber[ 21 ]= 4.8878806479307933507581516251802290210847054e14
Ber[ 22 ]= -2.1320333960919373896975058982136838557465453e16
Ber[ 23 ]= 1.0217752965257000775652876280535855003940110e18
Ber[ 24 ]= -5.3575472173300203610827709191969204484849041e19
Ber[ 25 ]= 3.0615782637048834150431510513296227581941868e21
Ber[ 26 ]= -1.8999917426399204050293714293069429029473425e23
Ber[ 27 ]= 1.2763374033828834149234951377697825976541634e25
Ber[ 28 ]= -9.2528471761204163072302423483476227795193312e26
Ber[ 29 ]= 7.2188225951856102978360501873016379224898404e28
Ber[ 30 ]= -6.0451834059958569677431482387545472860661444e30
Ber[ 31 ]= 5.4206704715700945451934778148261000136612022e32
Ber[ 32 ]= -5.1929578153140819467001947643918576846997063e34
Ber[ 33 ]= 5.3036588551197005966548392430697586436992926e36
Ber[ 34 ]= -5.7633253481649640138944358507809925551907376e38
Ber[ 35 ]= 6.6511557148484539375165201458105559510397394e40
Ber[ 36 ]= -8.1373783581366805387161726320935756918406892e42
Ber[ 37 ]= 1.0536966953357141803754804927641810189648373e45
Ber[ 38 ]= -1.4418180599962206261805377801511812809570332e47
Ber[ 39 ]= 2.0817356522089565462424808241263562311317343e49
Ber[ 40 ]= -3.1670226634886661827413495567742561342918070e51
Ber[ 41 ]= 5.0700064612111373431792648153174876567629628e53
Ber[ 42 ]= -8.5299728203005518816208400522162278887807045e55
Ber[ 43 ]= 1.5064172809340598576695117360379879076101931e58
Ber[ 44 ]= -2.7893494703831636871288381686312781712347569e60
Ber[ 45 ]= 5.4093504352860415005763561871884152582336290e62
Ber[ 46 ]= -1.0975337821508519855016788726170795167099903e65
Ber[ 47 ]= 2.3274876202618479173478641032052184930193480e67
Ber[ 48 ]= -5.1539291620653213901946552121717171770391159e69
Ber[ 49 ]= 1.1906210230890226457684816176871380462750227e72
Ber[ 50 ]= -2.8668938960296673696226420541900772462913819e74

@cython.cdivision(True) 
cdef  double complex my_lngamma(double x,double R,double prec=1E-16):
    r"""
    Logarithm of Gamma function for the argument x+i*R
    (using principal branch of the logarithm)
    INPUT:
     - ''x'' -- double 
     - ''R'' -- double 
    OUTPUT:
    - ''my_loggamma' -- double complex = ln(Gamma(x+i*R))

    EXAMPLES::


        sage: timeit('my_lngamma(3.0)')
        625 loops, best of 3: 7.01 \mu s per loop
        sage: my_lngamma(3.0)
        (-3.2441442995897556+1.053350771068613j)
        sage: import mpmath
        sage: a=mpmath.mpc(my_lngamma(3.0));a
        mpc(real='-3.2441442995897556', imag='1.053350771068613')
        sage: b=mpmath.loggamma(mpmath.mpc(1,3)); b
        mpc(real='-3.244144299589756', imag='1.0533507710686132')
        sage: a-b
        mpc(real='4.4408920985006262e-16', imag='-2.2204460492503131e-16')
        sage: abs(a-b)
        mpf('4.9650683064945462e-16')


    """
    cdef double a,jr,lnw,argw,Ims,Res,R2,S,r
    cdef double complex cr,tmp, res,iR,d_c_i
    cdef double complex z,w ,w2,ww, summa , stirling 
    cdef int i,j ,N ,m,M,k
    R2=R*R
    d_c_i=(<double complex>_Complex_I)
    z=iR+x
    y=R
    iR=d_c_i*R 
    N=10
    Nr=<double> N # d_ten
    u=Nr+x   
    v=y
    w=iR+u
    w2=w*w   #d_100-R*R+d_20*iR  #w*w
    summa=c_zero
    ww=c_one/w
    #ns=50
    for i from 1 <=i <num_ber:
        tmp=(<double complex >Ber[i])*ww
        summa=summa+tmp
        if( cabs(tmp) < prec):
            break
        ww=ww/(w2)
    a=cabs(w) #d_100+R2  # cabs(w) # sqrt(u*u+y*y)
    lnw=log(a)
    argw=carg(w)
    Res=(u-d_half)*lnw-R*argw-u+ln2PI2
    Ims=R*(lnw-d_one)+(u-d_half)*argw
    stirling=<double complex>Res+(<double complex>Ims)*d_c_i
    #  this was really for GAMMA(z+N)
    res=stirling+summa
    for j from 0 <=j<=N-1:
        cr=<double complex> j
        tmp=iR+cr+d_one
        res=res-clog(tmp)
    return res



