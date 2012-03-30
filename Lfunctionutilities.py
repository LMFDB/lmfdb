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
                return(ans + " + " + seriesvar(index,seriestype))
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
                return(ans + " + i" + seriesvar(index,seriestype))
        else:
            if seriescoefftype=="series":
                return(ans + truncatenumber(ip,precision) + " + i" + seriesvar(index, seriestype))
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

def lfuncDStex(L ,fmt):
    """ Returns the LaTex for displaying the Dirichlet series of the L-function L.
        fmt could be any of the values: "analytic", "langlands", "abstract"
    """


    if len(L.dirichlet_coefficients)==0:
        return '\\text{No Dirichlet coefficients supplied.}'
    
    numperline = 3
    numcoeffs=min(10,len(L.dirichlet_coefficients))
    if L.selfdual:
        numperline = 7
        numcoeffs=min(20,len(L.dirichlet_coefficients))
        ans=""
    if fmt=="analytic" or fmt=="langlands":
        ans="\\begin{align}\n"
        ans=ans+L.texname+"="+seriescoeff(L.dirichlet_coefficients[0],0,"literal","",-6,5)+"\\mathstrut&"
        for n in range(1,numcoeffs):
            ans=ans+seriescoeff(L.dirichlet_coefficients[n],n+1,"series","dirichlet",-6,5)
            if(n % numperline ==0):
                ans=ans+"\\cr\n"
                ans=ans+"&"
        ans=ans+" + \\ \\cdots\n\\end{align}"



    elif fmt=="abstract":
       if L.Ltype()=="riemann":
        ans="\\begin{equation} \n \\zeta(s) = \\sum_{n=1}^{\\infty} n^{-s} \n \\end{equation} \n"

       elif L.Ltype()=="dirichlet":
        ans="\\begin{equation} \n L(s,\\chi) = \\sum_{n=1}^{\\infty} \\chi(n) n^{-s} \n \\end{equation}"
        ans = ans+"where $\\chi$ is the character modulo "+ str(L.charactermodulus)
        ans = ans+", number "+str(L.characternumber)+"." 

       else:
        ans="\\begin{equation} \n "+L.texname+" = \\sum_{n=1}^{\\infty} a(n) n^{-s} \n \\end{equation}"
    return(ans)

#---------

def lfuncEPtex(L,fmt):
    """ Returns the LaTex for displaying the Euler product of the L-function L.
        fmt could be any of the values: "abstract"
    """
    
    ans=""
    if fmt=="abstract":
        if L.Ltype() == "SymmetricPower":
             ans = L.euler
             return ans

        ans="\\begin{equation} \n "+L.texname+" = "
        if L.Ltype()=="riemann":
             ans= ans+"\\prod_p (1 - p^{-s})^{-1}"
        elif L.Ltype()=="dirichlet":
             ans= ans+"\\prod_p (1- \\chi(p) p^{-s})^{-1}"
        elif L.Ltype()=="ellipticmodularform":
            ans= ans+"\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + p^{-2s})^{-1}"
        elif L.Ltype()=="ellipticcurve":
            ans= ans+"\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + p^{-2s})^{-1}"
        elif L.Ltype()=="maass":
            if L.group == 'GL2':
                ans= ans+"\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + p^{-2s})^{-1}"
            elif L.group == 'GL3':
                ans= ans+"\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1}  \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + \\overline{a(p)} p^{-2s} - p^{-3s})^{-1}"
            else:
                ans= ans+"\\prod_p \\ \\prod_{j=1}^{"+str(L.degree)+"} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
                
        elif L.langlands:
                ans= ans+"\\prod_p \\ \\prod_{j=1}^{"+str(L.degree)+"} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
          

        else:
            return("No information is available about the Euler product.")
        ans=ans+" \n \\end{equation}"
        return(ans)
    else:
        return("No information is available about the Euler product.")


#---------


def lfuncFEtex(L,fmt):
    """ Returns the LaTex for displaying the Functional equation of the L-function L.
        fmt could be any of the values: "analytic", "selberg"
    """
    
    ans=""
    if fmt=="analytic":
        ans="\\begin{align}\n"+L.texnamecompleteds+"=\\mathstrut &"
        if L.level>1:
            #ans+=latex(L.level)+"^{\\frac{s}{2}}"
            ans+=latex(L.level)+"^{s/2}"
        for mu in L.mu_fe:
           ans += "\Gamma_{\mathbb{R}}(s"+seriescoeff(mu,0,"signed","",-6,5)+")"
        for nu in L.nu_fe:
           ans += "\Gamma_{\mathbb{C}}(s"+seriescoeff(nu,0,"signed","",-6,5)+")"
        ans += " \\cdot "+L.texname+"\\cr\n"
        ans += "=\\mathstrut & "+seriescoeff(L.sign,0,"factor","",-6,5)
        ans += L.texnamecompleted1ms+"\n\\end{align}\n"
    elif fmt=="selberg":
        print L.nu_fe,"!!!!!!!"
        ans+="("+str(int(L.degree))+","
        ans+=str(int(L.level))+","
        ans+="("
        if L.mu_fe != []:
            for mu in range(len(L.mu_fe)-1):
                ans+=seriescoeff(L.mu_fe[mu],0,"literal","",-6,5)+", "
            ans+=seriescoeff(L.mu_fe[-1],0,"literal","",-6,5)
        ans = ans+":"
        if L.nu_fe != []:
            for nu in range(len(L.nu_fe)-1):
                ans+=str(L.nu_fe[nu])+", "
            ans+=str(L.nu_fe[-1])
        ans+="), "
        ans+=seriescoeff(L.sign, 0, "literal","", -6,5)
        ans+=")"

    return(ans)
                       

#------

NN = 500
CF = ComplexField(NN)


def euler_p_factor(root_list,PREC):
  # computes the coefficients of the pth Euler factor expanded as a geometric series
  # ax^n is the Dirichlet series coefficient p^(-ns)
  PREC = floor(PREC);
  #return satake_list
  R = LaurentSeriesRing(CF,'x')
  x = R.gens()[0]
  ep = prod([1/(1-a*x) for a in root_list])
  return ep + O(x**(PREC+1))


def compute_dirichlet_series(p_list, PREC):
  # p_list is a list of pairs (p,y) where p is a prime and y is the list of roots of the Euler factor at x
  LL = [0]*PREC;
  # create an empty list of the right size and now populate it with the powers of p
  for (p,y) in p_list:
      p_prec = log(PREC)/log(p)+1;
      ep = euler_p_factor(y,PREC);
      for n in range(ep.prec()):
          if p**n < PREC:
              LL[p**n] = ep.coefficients()[n]
  for i in range(1,PREC):
      f = factor(i);
      if len(f)>1: #not a prime power
          LL[i] = prod([LL[p**e] for (p,e) in f])
  return LL

def compute_local_roots_SMF2_scalar_valued(ev_data, k, embedding):
    K = ev_data[0].parent().fraction_field() # field of definition for the eigenvalues
    ev = ev_data[1] # dict of eigenvalues
    L = ev.keys()
    m = ZZ(max(L)).isqrt() + 1
    ev2 = {}
    for p in primes(m):
        try:
            ev2[p] = (ev[p],ev[p*p])

        except:
            break
        
    ret = []
    for p in ev2:
        R = PolynomialRing(QQ,'x')
        x = R.gens()[0]
        f =  (1 - ev2[p][0]*x+(ev2[p][0]**2-ev2[p][1]-p**(2*k-4))*x**2 -ev2[p][0]*p**(2*k-3)*x**3+p**(4*k-6)*x**4)
        Rnum = PolynomialRing(CF, 'y')
        x = Rnum.gens()[0]
        fnum = Rnum(0)
        if K != QQ:
            for i in range(int(f.degree())+1):
                fnum = fnum + f[i].complex_embeddings(NN)[embedding]*x**i
        else:
            print "here"
            fnum = Rnum(f)
        r = fnum.roots(CF)
        r = [1/a[0] for a in r]
        #a1 = r[1][0]/r[0][0]
        #a2 = r[2][0]/r[0][0]
        #a0 = 1/r[3][0]
        ret.append((p,r))

    return ret
