"""
Core functions for generating the necessary data corresponding to GL(2):
 - spaces of cusp forms
 - indivdual cuspforms

By convention a 'core function' starting with get_  returns a string.

"""

from sage.all import ZZ,Newform,is_squarefree,squarefree_part,factor,is_square,divisors,DirichletGroup,QQ,xgcd,prime_factors,Gamma0,html,I,ceil,ComplexField,RealField,dimension_cusp_forms,sturm_bound,latex,join
import re


####
#### Core functions for spaces of cuspforms
####
def get_dimension_cusp_forms(k,N=1,xi=0):
    r""" Return the dimension of S_k(N,xi).

    INPUT:
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''xi''-- non-negative integer (default 0) : use character nr. xi in DirichletGroup(N)

    OUTPUT:
     - ''s'' -- string representation of d = dimension of S_k(N,xi)

    EXAMPLES::

        sage: get_dimension_cusp_forms(2,11)
        '1'
        sage: get_dimension_cusp_forms(3,14,3)
        '2'

    """
    # check input
    if(N<=0 or k<=0):
        raise ValueError,"Need positive level and weight!"
    if(xi<0):
	raise ValueError,"Need positive character index!"
    elif(xi==0):
        d=dimension_cusp_forms(N,k)
    else:
	DG=DirichletGroup(N)
        chi=list(DG)[xi]
        d=dimension_cusp_forms(chi,k)
    return str(d)

def get_sturm_bound(k,N,xi=0):
    r""" Return the Sturm bound of S_k(N,xi), i.e. the number of coefficients necessary to determine a form uniquely in the space.

    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''xi''-- non-negative integer (default 0) : use character nr. xi in DirichletGroup(N)

    OUTPUT:

     - ''s'' -- string representation of t = sturm bound of S_k(N,xi)


    EXAMPLES::


        sage: get_sturm_bound(11,2)
        '3'
        sage: get_sturm_bound(3,14,3)
        '7'

    """
    # check input
    if(N<=0 or k<=0):
        raise ValueError,"Need positive level and weight!"
    if(xi==0):
        d=sturm_bound(N,k)
    else:
        chi=DirichletGroup(N)[xi]
        S=CuspForms(chi,k)
        d=S.sturm_bound()
    return str(d)


def get_decomposition_of_newspace(N,k,xi=0):
    r"""
    Compute the decomposition of the new, cuspidal submodule S_k(Gamma0(N),chi).

    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''xi''-- non-negative integer (default 0) : use character nr. xi in DirichletGroup(N)
     
    OUTPUT:
    
     - ''s'' -- string representation of dimensions of the decomposition of S_k(N,xi) into Galois orbits.

    EXAMPLES::

        # 1 one-dimensional rational eigenspace
        sage: get_decomposition_of_newspace(11,2)
        '[1]'
        # 1 one-dimensional eigenspace over Number Field in a with defining polynomial x^2 + x - 1
        sage: get_decomposition_of_newspace(23,2)
        '[2]'
        # 1 one-dimensional rational eigenspace
        # 1 one-dimensional eigenspace over Number Field in a with defining polynomial x^2 + 2*x - 1
        sage: get_decomposition_of_newspace(39,2)
        '[1, 2]'

    
    """
    try:
        L=ModularSymbols(N,k,sign=1).new_submodule().cuspidal_submodule().decomposition()
        dims=map(dimension,L)
        return str(dims)
    except:
        return "Could not compute this decomposition!"

def get_galois_orbit(N,k,xi=0,index=0,prec=10):
    r"""
    Compute the decomposition of the new, cuspidal submodule S_k(Gamma0(N),chi) and return component nr. index

    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''xi''-- non-negative integer (default 0) : use character nr. xi in DirichletGroup(N)
     - ''index''-- non-negative integer (default 0) : return component nr. index in the decomposition

    OUTPUT:
    
     - ''s'' -- string representation of dimensions of the decomposition of S_k(N,xi) into Galois orbits.

    EXAMPLES::

        # 1 one-dimensional rational eigenspace
        sage: get_galois_orbit(11,2)
        '('x', q - 2*q^2 - q^3 + 2*q^4 + q^5 + 2*q^6 - 2*q^7 - 2*q^9 + O(q^10))'
        # 1 one-dimensional eigenspace over Number Field in a with defining polynomial x^2 + x - 1
        sage: get_galois_orbit(23,2)
        '(x^2 + x - 1, q + x*q^2 + (-2*x - 1)*q^3 + (-x - 1)*q^4 + 2*x*q^5 + (x - 2)*q^6 + (2*x + 2)*q^7 + (-2*x - 1)*q^8 + 2*q^9 + O(q^10))'
        # 1 one-dimensional rational eigenspace
        sage: get_galois_orbit(39,2,index=0)
        "('x', q + q^2 - q^3 - q^4 + 2*q^5 - q^6 - 4*q^7 - 3*q^8 + q^9 + O(q^10))"
        # 1 one-dimensional eigenspace over Number Field in a with defining polynomial x^2 + 2*x - 1
        sage: get_galois_orbit(39,2,index=1)
        '(x^2 + 2*x - 1, q + x*q^2 + q^3 + (-2*x - 1)*q^4 + (-2*x - 2)*q^5 + x*q^6 + (2*x + 2)*q^7 + (x - 2)*q^8 + q^9 + O(q^10))'

    """
    M=ModularSymbols(N,k,sign=1).new_submodule().cuspidal_submodule()
    if(dimension(M)==0):
        return ""
    try:
        f=M.decomposition()[index].q_eigenform(prec,'x')
    except IndexError:
        return ""
    K=f.base_ring()
    if(K<>QQ):
        p=K.defining_polynomial()
    else:
        p=ZZ['x'].gen()
    return str((p,f))


def get_new_and_oldspace_decomposition(k,N,xi=0):
    r"""
    Get decomposition of the new and oldspace S_k(N,xi) into submodules.



    """
    M=ModularSymbols(N,k,sign=1).cuspidal_submodule()
    L=list()
    L=[M.new_submodule().dimension()]
    check_dim=M.new_submodule().dimension()
    for d in divisors(N):
        if(d==1):
            continue
        #print "d=",d
        O=M.old_submodule(d); Od=O.dimension()
        #print "O=",O
        if(d==N and k==2 or Od==0):
            continue
        S=ModularSymbols(ZZ(N/d),k,sign=1).cuspidal_submodule().new_submodule(); Sd=S.dimension()
        #print "S=",S
        #if(Sd==0):
        #    print O,Od
        #    print S,Sd
        mult=len(divisors(ZZ(d)))
        #print "mult,N/d,Sd=",mult,ZZ(N/d),Sd
        check_dim=check_dim+mult*Sd
        L.append((ZZ(N/d),mult,Sd))
    check_dim=check_dim-M.dimension()
    if(check_dim<>0):
        raise ArithmeticError, "Something wrong! check_dim=%s" % check_dim
    return str(M.dimension(),L)



##
## Core routines for individual cusp forms 
##


def get_atkin_lehner_eigenvalues(k,N=1,chi=0,fi=0):
    r"""
    Compute all Atkin-Lehner eigenvalues that we have.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]

    OUTPUT:

    - ''s'' -- string representing a dictonary of all existing Atkin-Lehner eigenvalues.

    EXAMPLES::

        sage: get_atkin_lehner_eigenvalues(4,14,0)
        '{2: 1, 14: 1, 7: 1}'
        sage: get_atkin_lehner_eigenvalues(4,14,1)
        '{2: -1, 14: 1, 7: -1}'


    """
    if(chi<>0):
        return ""
    res=dict()
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return f
    N=f.level()
    for Q in divisors(N):
        if(Q==1):
            continue
        if(gcd(Q,ZZ(N/Q))==1):
            try:
                res[Q]=f.atkin_lehner_eigenvalue(ZZ(Q))
            except:
                pass
    tbl=dict()
    tbl['headersh']=res.keys()
    tbl['data']=[0]
    tbl['data'][0]=list()
    tbl['corner_label']="$Q$"
    tbl['headersv']=["$\epsilon_{Q}$"]
    for Q in res.keys():
        tbl['data'][0].append(res[Q])
    s=html_table(tbl)
    return s


def get_cusp_expansions_of_newform(k,N=1,fi=0,prec=10):
    r"""
    Get and return Fourier coefficients of all cusps where there exist Atkin-Lehner involutions for these cusps.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
     - ''prec'' -- integer (the number of coefficients to get)

     OUTPUT:

     - ''s'' string giving the Atkin-Lehner eigenvalues corresponding to the Cusps (where possible)
    """
    res=dict()
    (t,f) = _get_newform(k,N,0,fi)
    if(not t):
        return s
    res[Infinity]=1
    for c in f.group().cusps():
        if(c==Cusp(Infinity)):
            continue
        res[c]=list()
        cusp=QQ(c)
        q=cusp.denominator()
        p=cusp.numerator()
        d=ZZ(cusp*N)
        if(d==0):
            ep=f.atkin_lehner_eigenvalue()
        if(d.divides(N) and gcd(ZZ(N/d),ZZ(d))==1):
            ep=f.atkin_lehner_eigenvalue(ZZ(d))
        else:
            # this case is not known... 
            res[c]=None
            continue
        res[c]=ep
    s=html.table([res.keys(),res.values()])
    return s


def get_fourier_coefficients_of_newform(k,N=1,chi=0,fi=0,prec=10):
    r"""
    Get and return Fourier coefficients for f as a list.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi
    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
     - ''prec'' -- integer (the number of coefficients to get)

     OUTPUT:

     - ''s'' string giving the coefficients of f as polynomals in x

     EXAMPLES::


         # a rational newform
         sage: get_fourier_coefficients_of_newform(4,14,1)
         '[1, 2, -2, 4, -12, -4, 7, 8, -23, -24]'
         # a rational newform
         sage: get_fourier_coefficients_of_newform(2,39,0)
         '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
         # a degree two newform
         sage: get_fourier_coefficients_of_newform(2,39,1,5)
         '[1, x, 1, -2*x - 1, -2*x - 2]'

    """
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return s
    K=f.base_ring()
    coeffs=f.coefficients(ZZ(prec))
    s=str(coeffs)
    ## f.coeffficients() uses alpha as a variable and we want x
    ss=re.sub('alpha','x',s)
    return ss

def get_q_expansion_of_newform(k,N=1,chi=0,fi=0,prec=10):
    r"""
    Get and return Fourier coefficients for f as a list.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi
    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
     - ''prec'' -- integer (the number of coefficients to get)

     OUTPUT:

     - ''s'' string giving the coefficients of f as polynomals in x

     EXAMPLES::


         # a rational newform
         sage: get_fourier_coefficients_of_newform(4,14,1)
         '[1, 2, -2, 4, -12, -4, 7, 8, -23, -24]'
         # a rational newform
         sage: get_fourier_coefficients_of_newform(2,39,0)
         '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
         # a degree two newform
         sage: get_fourier_coefficients_of_newform(2,39,1,5)
         '[1, x, 1, -2*x - 1, -2*x - 2]'

    """
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return s
    K=f.base_ring()
    s="$"+str(f.q_expansion(ZZ(2*prec)))+"$"
    ## f.coeffficients() uses alpha as a variable and we want x
    ss=re.sub('x1','x',s)
    s=re.sub("\^(\d+)","^{\\1}",ss)
    return s


def get_fourier_coefficients_of_newform_embeddings(k,N=1,xi=0,fi=0,prec=10):
    r"""
    Get and return all embeddings of Fourier coefficients of the newform f=Newforms(N,k)[fi] up to prec.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
     - ''prec'' -- integer (the number of coefficients to get)

     OUTPUT:

     - ''s'' string giving the coefficients of f as floating point numbers

     EXAMPLES::

         # a rational newform
         sage: get_fourier_coefficients_of_newform_embeddings(2,39,0)
         '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
         sage: get_fourier_coefficients_of_newform(2,39,0)
         '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
         # a degree two newform
         sage: get_fourier_coefficients_of_newform(2,39,1,5)
         '[1, x, 1, -2*x - 1, -2*x - 2]'
         sage: get_fourier_coefficients_of_newform_embeddings(2,39,1,5)
         '[[1.00000000000000, 1.00000000000000], [-2.41421356237309, 0.414213562373095], [1.00000000000000, 1.00000000000000], [3.82842712474619, -1.82842712474619], [2.82842712474619, -2.82842712474619]]'
 

    """
    coeffs=fourier_coefficients_of_newform_embeddings(k,N,xi,fi,prec)
    if(isinstance(coeffs,str)):
        return coeffs  ### we probably failed to compute the form
    # make a table of the coefficients
    tbl=dict()
    tbl['headersh']=range(len(coeffs))
    tbl['headersv']=list()
    tbl['data']=list()
    tbl['corner_label']="$Embedding \ n$"
    for i in range(len(coeffs[0])):
        tbl['headersv'].append("$\sigma_{%s}(a(n))$" % i)
        row=list()
        for n in range(len(coeffs)):
            row.append(coeffs[n][i])
        tbl['data'].append(row)
    #
    #print tbl
    s=html_table(tbl)
    return s


def get_is_minimal(k,N=1,chi=0,fi=0,prec=10):
    r"""
    Checks if f is minimal and if not, returns the associated
    minimal form to precision prec.

    INPUT:

    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
    - ''prec'' -- integer (the number of coefficients to get)

    OUTPUT:

    -''s'' -- string representing a tuple of a Bool and a list. The list contains all tuples of forms which twists to the given form.
              The actual minimal one is the first element of this list.

    EXAMPLES::
    """
    [t,l]=find_inverse_images_of_twists(k,N,chi,fi,prec)
    if(t):
        return "f is minimal."
    else:
        return "f is a twist of "+str(l[0])


def get_is_CM(k,N=1,fi=0,prec=10):
    r"""
    Checks if f is minimal and if not, returns the associaetd
    minimal form to precision prec.

    INPUT:

    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
    - ''prec'' -- integer (the number of coefficients to get)

    OUTPUT:

    -''s'' -- string representing a tuple of a Bool and a list. The list contains all tuples of forms which twists to the given form.
              The actual minimal one is the first element of this list.

    TODO: What is the field with which f has CM? 

    EXAMPLES::
    """
    [t,x]=is_CM(k,N,fi,prec)
    if(t):
        m=x.modulus()
        nr=x.parent().list().index(x)
        #K=x.base_ring()
        return "Has CM with character nr. %s modulo %s " % (nr,m)
    else:
        return "Does not have CM"



def get_values_at_CM_points(k,N=1,chi=0,fi=0,digits=12,verbose=0):
    r""" Computes and returns a list of values of f at a collection of CM points as complex floating point numbers.

    INPUT:

    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
    -''digits'' -- we want this number of corrrect digits in the value

    OUTPUT:
    -''s'' string representation of a dictionary {I:f(I):rho:f(rho)}.

    TODO: Get explicit, algebraic values if possible!
    """
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return f
    bits=max(53,ceil(digits*4))
    CF=ComplexField(bits)
    RF=ComplexField(bits)
    eps=RF(10**-(digits+1))
    if(verbose>1):
        print "eps=",eps
    K=f.base_ring()
    cm_vals=dict()
    # the points we want are i and rho. More can be added later...
    rho=CyclotomicField(3).gen()
    zi=CyclotomicField(4).gen()
    points=[rho,zi]
    maxprec=1000 # max size of q-expansion
    minprec=10 # max size of q-expansion
    for tau in points:
        q=CF(exp(2*pi*I*tau))
        fexp=dict()
        if(K==QQ):
            v1=CF(0); v2=CF(1)
            try:
                for prec in range(minprec,maxprec,10):
                    if(verbose>1):
                        print "prec=",prec
                    v2=f.q_expansion(prec)(q)
                    err=abs(v2-v1)
                    if(verbose>1):
                        print "err=",err
                    if(err< eps):
                        raise StopIteration()
                    v1=v2
                cm_vals[tau]=""
            except StopIteration:
                cm_vals[tau]=str(fq)
        else:
            v1=dict()
            v2=dict()
            err=dict()
            cm_vals[tau]=dict()
            for h in range(K.degree()):
                v1[h]=1
                v2[h]=0
            try:
                for prec in range(minprec,maxprec,10):
                    if(verbose>1):
                        print "prec=",prec
                    for h in range(K.degree()):
                        fexp[h]=list()
                        v2[h]=0
                        for n in range(prec):
                            c=f.coefficients(ZZ(prec))[n]
                            cc=c.complex_embeddings(CF.prec())[h]
                            v2[h]=v2[h]+cc*q**n
                        err[h]=abs(v2[h]-v1[h])
                        if(verbose>1):
                            print "v1[",h,"]=",v1[h]
                            print "v2[",h,"]=",v2[h]
                            print "err[",h,"]=",err[h]
                        if(max(err.values()) < eps):             
                            raise StopIteration()
                        v1[h]=v2[h]
            except StopIteration:
                pass
            for h in range(K.degree()):
                if(err[h] < eps):
                    cm_vals[tau][h]=v2[h]
                else:
                    cm_vals[tau][h]=""

    if(verbose>2):
        print "vals=",cm_vals
        print "errs=",err
    tbl=dict()
    tbl['corner_label']=['$\tau$']
    tbl['headersh']=['$\\rho=\zeta_{3}$','$i$']
    if(K==QQ):
        tbl['headersv']=['$f(\\tau)$']
        tbl['data']=[cm_vals]
    else:
        tbl['data']=list()
        tbl['headersv']=list()
        for h in range(K.degree()):
            tbl['headersv'].append("$\sigma_{%s}(f(\\tau))$" % h)
            row=list()
            for tau in points:
                row.append(cm_vals[tau][h])            
            tbl['data'].append(row)

    s=html_table(tbl)
    #s=html.table([cm_vals.keys(),cm_vals.values()])
    return s



def get_satake_parameters(k,N=1,chi=0,fi=0,prec=10,bits=53,angles=False):
    r""" Compute the Satake parameters and return an html-table.
    
    INPUT:
    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
    -''prec'' -- compute parameters for p <=prec
    -''bits'' -- do real embedings intoi field of bits precision
    -''angles''-- return the angles t_p instead of the alpha_p
                  here alpha_p=p^((k-1)/2)exp(i*t_p)

    """
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return f
    K=f.base_ring()
    RF=RealField(bits)
    CF=ComplexField(bits)
    if(K<>QQ):
        M=len(K.complex_embeddings())
        ems=dict()
        for j in range(M):
            ems[j]=list()
    ps=prime_range(prec)
    alphas=list()
    for p in ps:
        ap=f.coefficients(ZZ(prec))[p]
        if(K==QQ):
            f1=QQ(4*p**(k-1)-ap**2)
            alpha_p=(QQ(ap)+I*f1.sqrt())/QQ(2)
            #beta_p=(QQ(ap)-I*f1.sqrt())/QQ(2)
            #satake[p]=(alpha_p,beta_p)
            ab=RF(p**((k-1)/2))
            norm_alpha=alpha_p/ab
            t_p=CF(norm_alpha).argument()
            if(angles):
                alphas.append(t_p)
            else:
                alphas.append(alpha_p)
            
        else:
            for j in range(M):
                app=ap.complex_embeddings(bits)[j]
                f1=(4*p**(k-1)-app**2)
                alpha_p=(app+I*f1.sqrt())/RealField(bits)(2)
                #print "alpha_p(",p,app,")=",alpha_p
                #print "alpha_p(",p,app,")=",abs(alpha_p)
                ab=RF(p**((k-1)/2))
                norm_alpha=alpha_p/ab
                t_p=CF(norm_alpha).argument()
                if(angles):
                    ems[j].append(t_p)
                else:
                    ems[j].append(alpha_p)

    tbl=dict()
    tbl['headersh']=ps
    if(K==QQ):
        tbl['headersv']=[""]
        tbl['data']=[alphas]
        tbl['corner_label']="$p$"
    else:
        tbl['data']=list()
        tbl['headersv']=list()
        tbl['corner_label']="Embedding \ $p$"
        for j in ems.keys():
            tbl['headersv'].append(j)
            tbl['data'].append(ems[j])
    #print tbl
    s=html_table(tbl)
    return s



##
## Internal functions, do not return strings. 
## Should be called by the previous ones.   
##

def is_CM(k,N=1,chi=0,fi=0,prec=10):
    r"""
    Checks if f has complex multiplication and if it has then it returns the character.

    INPUT:

    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]


    OUTPUT:
    
    -''[t,x]'' -- string saying whether f is CM or not and if it is, the corresponding character

    EXAMPLES::

    

    """
    (t,f) = _get_newform(k,N,chi,fi)
    if(not t):
        return f
    max_nump=number_of_hecke_to_check(f)
    coeffs=f.coefficients(max_nump+1)
    nz=coeffs.count(0) # number of zero coefficients
    nnz = len(coeffs) - nz # number of non-zero coefficients
    if(nz==0):
        return [False,0]
    # probaly checking too many
    for D in range(3,ceil(QQ(max_nump)/QQ(2))):
        try:
            for x in DirichletGroup(D):
                if(x.order()<>2):
                    continue
                # we know that for CM we need x(p) = -1 => c(p)=0
                # (for p not dividing N)
                if(x.values().count(-1) > nz):
                    raise StopIteration() # do not have CM with this char           
                for p in prime_range(max_nump+1):
                    if(x(p)==-1 and coeffs[p]<>0):
                        raise StopIteration() # do not have CM with this char
                # if we are here we have CM with x. 
                return [True,x]
        except StopIteration:
            pass
    return [False,0]

def find_inverse_images_of_twists(k,N=1,chi=0,fi=0,prec=10,verbose=0):
    r"""
    Checks if f is minimal and if not, returns the associated
    minimal form to precision prec.

    INPUT:

    - ''k'' -- positive integer : the weight
    - ''N'' -- positive integer (default 1) : level
    - ''chi'' -- non-neg. integer (default 0) use character nr. chi
    - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
    - ''prec'' -- integer (the number of coefficients to get)
    - ''verbose'' -- integer 
    OUTPUT:

    -''[t,l]'' -- tuple of a Bool t and a list l. The list l contains all tuples of forms which twists to the given form.
              The actual minimal one is the first element of this list.

    EXAMPLES::



    """
    (t,f) = _get_newform(k,N,chi,fi)

    if(not t):
        return f
    if(is_squarefree(ZZ(N))):
        return [True,f]
    # We need to check all square factors of N
    if(verbose>0):
        print "investigating: ",f
    N_sqfree=squarefree_part(ZZ(N))
    Nsq=ZZ(N/N_sqfree)
    twist_candidates=list()
    KF=f.base_ring()
    # check how many Hecke eigenvalues we need to check
    max_nump=number_of_hecke_to_check(f)
    maxp=max(primes_first_n(max_nump))
    for d in divisors(N):
        # we look at all d such that d^2 divdes N
        if(not ZZ(d**2).divides(ZZ(N))):
            continue
        D=DirichletGroup(d)
        # check possible candidates to twist into f
        # g in S_k(M,chi) wit M=N/d^2
        M=ZZ(N/d**2)
        if(verbose>0):
            print "Checking level ",M
        for xig in range(euler_phi(M)):
            (t,glist) = _get_newform(k,M,xig)
            if(not t):
                return glist
            for g in glist:
                if(verbose>1):
                    print "Comparing to function ",g
                KG=g.base_ring()
                # we now see if twisting of g by xi in D gives us f
                for xi in D:
                    try:
                        for p in primes_first_n(max_nump):
                            if(ZZ(p).divides(ZZ(N))):
                                continue
                            bf=f.q_expansion(maxp+1)[p]
                            bg=g.q_expansion(maxp+1)[p]
                            if(bf == 0 and bg == 0):
                                continue
                            elif(bf==0 and bg<>0 or bg==0 and bf<>0):
                                raise StopIteration()
                            if(ZZ(p).divides(xi.conductor())):
                                raise ArithmeticError,""
                            xip=xi(p)
                            # make a preliminary check that the base rings match with respect to being real or not
                            try:
                                QQ(xip)
                                XF=QQ
                                if( KF<>QQ or KG<>QQ):
                                    raise StopIteration
                            except TypeError:
                                # we have a  non-rational (i.e. complex) value of the character
                                XF=xip.parent() 
                                if( (KF == QQ or KF.is_totally_real()) and (KG == QQ or KG.is_totally_real())):
                                    raise StopIteration
                            ## it is diffcult to compare elements from diferent rings in general but we make some checcks
                            ## is it possible to see if there is a larger ring which everything can be coerced into?
                            ok=False
                            try:
                                a=KF(bg/xip); b=KF(bf)
                                ok=True
                                if(a<>b):
                                    raise StopIteration()
                            except TypeError:
                                pass
                            try:
                                a=KG(bg); b=KG(xip*bf)
                                ok=True
                                if(a<>b):
                                    raise StopIteration()
                            except TypeError:
                                pass
                            if(not ok): # we could coerce and the coefficients were equal
                                return "Could not compare against possible candidates!"
                            # otherwise if we are here we are ok and found a candidate
                        twist_candidates.append([dd,g.q_expansion(prec),xi])
                    except StopIteration:
                        # they are not equal
                        pass
    #print "Candidates=",twist_candidates
    if(len(twist_candidates)==0):
        return (True,None)
    else:
        return (False,twist_candidates)


def number_of_hecke_to_check(f):
    r""" Compute the number of Hecke eigenvalues (at primes) we need to check to identify twists of our given form with characters of conductor dividing the level.
    """
    ## initial bound
    bd=f.parent().sturm_bound()
    # we do not check primes dividing the level
    bd=bd+len(divisors(f.level()))
    return bd


def _get_newform(k,N,chi,fi):
    r"""
    Get an element of the space of newforms, incuding some error handling.
    
    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''chi'' -- non-neg. integer (default 0) use character nr. chi
     - ''fi'' -- integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]. fi=-1 returns the whole list
     - ''prec'' -- integer (the number of coefficients to get)
     
    OUTPUT:
    
    -''t'' -- bool, returning True if we succesfully created the space and picked the wanted f
    -''f'' -- equals f if t=True, otherwise contains an error message.
     
    EXAMPLES::

    
        sage: _get_newform(16,10,1)
        (False, 'Could not construct space $S^{new}_{16}(10)$')
        sage: _get_newform(10,16,1)
        (True, q - 68*q^3 + 1510*q^5 + O(q^6))
        sage: _get_newform(10,16,3)
        (True, q + 156*q^3 + 870*q^5 + O(q^6))
        sage: _get_newform(10,16,4)
        (False, '')

     """
    t=False
    #print k,N,fi
    try:
        if(chi==0):
            S=Newforms(N,k,names='x')
        else:
            S=Newforms(DirichletGroup(N)[chi],k,names='x')
        if(fi>=0 and fi <len(S)):
            f=S[fi]
            t=True
        elif(fi==-1):
            return S
        else:
            f=""
    except RuntimeError: 
        if(chi==0):
            f="Could not construct space $S^{new}_{%s}(%s)$" %(k,N)
        else:
            f="Could not construct space $S^{new}_{%s}(%s,\chi_{%s})$" %(k,N,chi)
    return (t,f)

def fourier_coefficients_of_newform_embeddings(k,N=1,xi=0,fi=0,prec=10):
    r"""
    Get and return all embeddings of Fourier coefficients of the newform f=Newforms(N,k)[fi] up to prec.

    INPUT:
 
     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''fi'' -- non-neg. integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]
     - ''prec'' -- integer (the number of coefficients to get)

     OUTPUT:

     - ''s'' string giving the coefficients of f as floating point numbers

     EXAMPLES::

         # a rational newform
         sage: get_fourier_coefficients_of_newform_embeddings(2,39,0)
         '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
         sage: get_fourier_coefficients_of_newform(2,39,0)
         [1, 1, -1, -1, 2, -1, -4, -3, 1, 2]
         # a degree two newform
         sage: get_fourier_coefficients_of_newform(2,39,1,5)
         [1, x, 1, -2*x - 1, -2*x - 2]
         sage: get_fourier_coefficients_of_newform_embeddings(2,39,1,5)
         [[1.00000000000000, 1.00000000000000], [-2.41421356237309, 0.414213562373095], [1.00000000000000, 1.00000000000000], [3.82842712474619, -1.82842712474619], [2.82842712474619, -2.82842712474619]]
 

    """
    (t,f) = _get_newform(k,N,xi,fi)
    if(not t):
        return s
    K=f.base_ring()
    if(K == QQ):
        return str(f.coefficients(ZZ(prec)))
    coeffs=list()
    for n in range(ZZ(prec)):
        coeffs.append(f.coefficients(ZZ(prec))[n].complex_embeddings())
    return coeffs


def html_table(tbl):
    r""" Takes a dictonary and returns an html-table.

    INPUT:
    
    -''tbl'' -- dictionary with the following keys
              - headersh // horozontal headers
              - headersv // vertical headers
              - rows -- dictionary of rows of data
              
    """
    ncols=len(tbl["headersh"])
    nrows=len(tbl["headersv"])
    data=tbl['data']
    if(len(data)<>nrows):
        print "wrong number of rows!"
    for i in range(nrows):
        print "len(",i,")=",len(data[i])
        if(len(data[i])<>ncols):
            print "wrong number of cols!"        

    if(tbl.has_key('atts')):
        s="<table "+str(tbl['atts'])+">\n"
    else:
        s="<table>\n"
    format = dict()
    for i in range(ncols):
        format[i]=''
        if(tbl.has_key('data_format')):
            if isinstance(tbl['data_format'],dict):
                if(tbl['data_format'].has_key(i)):
                    format[i]=tbl['data_format'][i]
            elif(isinstance(tbl['data_format'],str)):
                format[i]=tbl['data_format']
    if(tbl.has_key('header')):
        s+="<thead><tr><th><td colspan=\""+str(ncols)+"\">"+tbl['header']+"</td></th></tr></thead>"
    s=s+"<tbody>"
    #smath="<span class=\"math\">"
    # check which type of content we have
    h1=tbl['headersh'][0]
    sheaderh="";    sheaderv=""
    h1=tbl['headersv'][0]
    col_width=dict()
    if not tbl.has_key('col_width'):
        # use maximum width as default
        maxw = 0
        for k in range(ncols):
            for r in range(nrows):
                l =len_as_printed(str(data[r][k]))
                if l>maxw:
                    maxw = l
                    #print "l=",l," max=",data[r][k]
        l = l*10.0 # use true font size?
        for k in range(ncols):
            col_width[k]=maxw
    else:
        for i in range(ncols):        
            col_width[i]=0
            if tbl.has_key('col_width'):
                if tbl['col_width'].has_key(i):
                    col_width[i]=tbl['col_width'][i]
    #print "col width=",col_width
    #print "format=",format
    if(tbl.has_key("corner_label")):
        l = len_as_printed(str(tbl["corner_label"]))*10
        row="<tr><td width=\"%s\">" % l
        row+=str(tbl["corner_label"])+"</td>"
    else:
        row="<tr><td></td>"
    for k in range(ncols):
        row=row+"<td>"+sheaderh+str(tbl['headersh'][k])+"</td> \n"

    row=row+"</tr> \n"
    s=s+row
    for r in range(nrows):
        l = len_as_printed(str(tbl["headersv"][r]))*10
        print "l=",l,"head=",tbl["headersv"]
        row="<tr><td width=\"%s\">" %l
        row+=sheaderv+str(tbl['headersv'][r])+"</td>"
        for k in range(ncols):
            wid = col_width[k]
            if format[k]=='html' or format[k]=='text':
                row=row+"\t<td halign=\"center\" width=\""+str(wid)+"\">"
                #print "HTML=",data[r][k]
                if isinstance(data[r][k],list):
                    for ss in data[r][k]:
                        sss = str(ss)
                        if(len(sss)>0):
                            row+=sss
                else:
                    sss = str(data[r][k])
                    row+=sss
                row=row+"</td> \n"
            else:
                row=row+"\t<td width=\""+str(wid)+"\">"
                if isinstance(data[r][k],list):
                    #print "LATEX list=",data[r][k]
                    for ss in data[r][k]:
                        sss = latex(ss)
                        if(len(sss)>0):
                            row+="\("+sss+"\)"
                else:
                    sss=latex(data[r][k])
                    if(len(sss)>0):
                        row=row+"\("+sss+"\)</td> \n"
                row+="</td>\n"
        # allow for different format in different columns
        row=row+"</tr> \n"
        s=s+row
    s=s+"</tbody></table>"
    return s


def len_as_printed(s,format='latex'):
    r"""
    Returns the length of s, as it will appear after being math_jax'ed
    """
    lenq=1
    lendig=1
    lenpm=1.5
    lenpar=0.5
    lenexp=0.75
    lensub=0.75
    ## remove all html first since it is not displayed
    ss = re.sub("<[^>]*>","",s)
    print "ss=",ss
    ss = re.sub(" ","",ss)    # remove white-space
    ss = re.sub("\*","",ss)    # remove *
    num_exp = s.count("^")    # count number of exponents
    exps = re.findall("\^{?(\d*)",s) # a list of all exponents
    sexps = "".join(exps)
    num_subs = s.count("_")    # count number of exponents
    subs = re.findall("_{?(\d*)",s) # a list of all  subscripts
    ssubs = "".join(subs)
    ss = re.sub("\^{?(\d*)}?","",ss)  # remove exponenents
    print join([ss,ssubs,sexps])
    tot_len=(ss.count(")")+ss.count("("))*lenpar
    tot_len+=ss.count("q")*lenq
    tot_len+=len(re.findall("\d",s))*lendig
    tot_len+=len(re.findall("\w",s))*lenq
    tot_len+=(s.count("+")+s.count("-"))*lenpm
    tot_len+=num_subs*lensub
    tot_len+=num_exp*lenexp
    #
    #tot_len = len(ss)+ceil((len(ssubs)+len(sexps))*0.67)
    return tot_len
    


def print_geometric_data_Gamma0N(N):
        r""" Print data about Gamma0(N).
        """
        G=Gamma0(N)
        s = ""
        s="<table>"
        s+="<tr><td>index:</td><td>%s</td></tr>" % G.index()
        s+="<tr><td>genus:</td><td>%s</td></tr>" % G.genus()
        s+="<tr><td>Cusps:</td><td>\(%s\)</td></tr>" % latex(G.cusps())
        s+="<tr><td colspan=\"2\">Number of elliptic fixed points</td></tr>"
        s+="<tr><td>order 2:</td><td>%s</td></tr>" % G.nu2()
        s+="<tr><td>order 3:</td><td>%s</td></tr>" % G.nu3()
        s+="</table>"
        return s


def pol_to_html(p):
    r"""
    Convert polynomial p to html
    """
    s = str(p)
    s = re.sub("\^(\d*)","<sup>\\1</sup>",s)
    s = re.sub("\_(\d*)","<sub>\\1</suB>",s)
    return s
