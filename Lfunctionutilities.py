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


