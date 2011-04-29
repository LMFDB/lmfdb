import re
from sage.all import *

def pair2complex(pair):
    local = re.match(" *([^ ]+)[ \t]*([^ ]*)", pair)
    if local:
        rp = local.group(1)
        if local.group(2):
            ip = local.group(2)
        else:
            ip=0
    else:
        rp=0
        ip=0
    return float(rp) + float(ip)*I


def splitcoeff(coeff):
    local = coeff.split("\n")
    answer = []
    for s in local:
        if s:
            answer.append(pair2complex(s))

    return answer

def truncatenumber(numb,precision):
    localprecision = precision
    if numb < 0:
	localprecision = localprecision + 1	
    return(str(numb)[0:int(localprecision)])

def seriescoeff(coeff, index, seriescoefftype, seriestype, truncationexp, precision):
    truncation=float(10**truncationexp)
    rp=real_part(coeff)
    ip=imag_part(coeff)
# below we use float(abs()) instead of abs() to avoid a sage bug
    if (float(abs(rp))>truncation) & (float(abs(ip))>truncation):
        ans = ""
	if seriescoefftype=="series":
	    ans +="+"
        ans +="("
        ans += truncatenumber(rp, precision)
        if ip>0:
            ans +="+"
        ans += truncatenumber(ip, precision)+" i"
        return(ans+")" + seriesvar(index, seriestype))
    elif (float(abs(rp))<truncation) & (float(abs(ip))<truncation):
	if seriescoefftype != "literal":
            return("")
	else:
	    return("0")
# if we get this far, either pure real or pure imaginary
    ans=""
#    if seriescoefftype=="series":
#        ans=ans+" + "
#commenting out the above "if" code so as to fix + - problem
    if rp>truncation: 
        if float(abs(rp-1))<truncation:
            if seriescoefftype=="literal":
                return("1")
            elif seriescoefftype=="signed":
                return("+1")
            elif seriescoefftype=="factor":
                return("")
            elif seriescoefftype=="series":
                return(ans + seriesvar(index,seriestype))
        else:
            if seriescoefftype=="series":
                return(" + " + ans + truncatenumber(rp, precision) + seriesvar(index, seriestype))
            elif seriescoefftype=="signed":
                return(ans + "+"+truncatenumber(rp,precision))
            elif seriescoefftype=="literal" or seriescoefftype=="factor":
                return(ans + truncatenumber(rp,precision))
    elif rp<-1*truncation:
    	if float(abs(rp+1))<truncation:
	    if seriescoefftype == "literal":
		return("-1" + seriesvar(index, seriestype))
	    elif seriescoefftype == "signed":
		return("-1" + seriesvar(index, seriestype))
	    elif seriescoefftype == "factor":
		return("-" + seriesvar(index, seriestype))
 	    elif seriescoefftype == "series":  # adding space between minus sign and value
 		return(" - " + seriesvar(index, seriestype))
	    else:
		return("-" + seriesvar(index, seriestype))
        else:
	    if seriescoefftype=="series":
                return(ans + " - " + truncatenumber(float(abs(rp)), precision) + seriesvar(index, seriestype))
            elif seriescoefftype=="literal" or seriescoefftype=="factor":
                return(ans + truncatenumber(rp,precision))

# if we get this far, it is pure imaginary
    elif ip>truncation:
        if float(abs(ip-1))<truncation:
            if seriescoefftype=="literal":
                return("i")
            elif seriescoefftype=="signed":
                return("+i")
            elif seriescoefftype=="factor":
                return("i")
            elif seriescoefftype=="series":
                return(ans + "i" + seriesvar(index,seriestype))
        else:
            if seriescoefftype=="series":
                return(ans + truncatenumber(ip,precision) + "i" + seriesvar(index, seriestype))
            elif seriescoefftype=="signed":
                return(ans + "+"+truncatenumber(ip,precision) + "i")
            elif seriescoefftype=="literal" or seriescoefftype=="factor":
                return(ans + truncatenumber(ip,precision) + "i")
    elif ip<-1*truncation:
        if float(abs(ip+1))<truncation:
            return("-i" + seriesvar(index, seriestype))
        else:
            if seriescoefftype=="series":
                return(ans + truncatenumber(ip, precision) +"i"+ seriesvar(index, seriestype))
            elif seriescoefftype=="signed":
                return(ans + truncatenumber(ip,precision)+" i")
            elif seriescoefftype=="literal" or seriescoefftype=="factor":
                return(ans + truncatenumber(ip,precision)+" i")

#    elif float(abs(ip+1))<truncation:
#        return("-" + "i"+ seriesvar(index, seriestype))
    else:
        return(latex(coeff) + seriesvar(index, seriestype))


def seriesvar(index,seriestype):
    if seriestype=="dirichlet":
        return(" \\ " + str(index)+"^{-s}")
    elif seriestype=="":
        return("")
    elif seriestype=="qexpansion":
        return("\\, " + "q^{"+str(index)+"}")
    else:
        return("")


def make_dirichlet_series(roots):
    '''
    I assume that roots has keys for every prime and allow the values
    at prime keys to be empty lists 
    '''
    num_coeffs = next_prime(max(roots))
    from sage.rings.power_series_ring import PowerSeriesRing
    from sage.rings.complex_field import ComplexField 
    PS = PowerSeriesRing(ComplexField(),'q')
    q = PS.gen()
    ds = {1:1}
    print roots
    for p in roots:
        p_poly = 1
        for alpha in roots[p]:
            print alpha, p
            p_poly = p_poly*(1-alpha*q)
        p_factor = PS(1/p_poly)+O(q**num_coeffs)
        p_coeffs = p_factor.coefficients()
        for i in range(num_coeffs):
            if p**i < num_coeffs: 
                ds[p**i] = p_coeffs[i]
    from sage.misc.misc import srange
    for nn in srange(6, num_coeffs):
        if not nn.is_prime_power():
            nf = nn.factor()
            ds[nn] = prod([ds[a[0]**a[1]] for a in nf])
    list_ds = []
    for nn in srange(1,num_coeffs): 
        list_ds.append(ds[nn])
    return list_ds


def make_logarithmic_derivative(roots):
    '''
    I assume that roots has keys for every prime and allow the values
    at prime keys to be empty lists 
    '''
    m = max(roots)
    from sage.misc.misc import srange
    for nn in srange(m, next_prime(m)):
        if nn.is_prime_power():
            m = nn
    num_coeffs = m
    ds = {}
    for p in roots:
        i = 1
        while (p**i<num_coeffs):
            ds[p**i] = log(p).n()*sum([alpha**i for alpha in roots[p]])
            i = i+1
    return ds
