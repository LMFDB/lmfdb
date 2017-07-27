# Different helper functions.

import re
from lmfdb.lfunctions import logger
import math
from sage.all import ZZ, QQ, RR, CC, Rational, RationalField, ComplexField, PolynomialRing, LaurentSeriesRing, O, Integer, Primes, primes, CDF, I, real_part, imag_part, latex, factor, prime_divisors, prime_pi, exp, pi, prod, floor
from lmfdb.genus2_curves.web_g2c import list_to_factored_poly_otherorder
from lmfdb.transitive_group import group_display_knowl
from lmfdb.base import getDBConnection
from lmfdb.utils import truncatenumber

###############################################################
# Functions for displaying numbers in correct format etc.
###############################################################

def p2sage(s):
    """Convert s to something sensible in Sage.  Can handle objects
    (including strings) representing integers, reals, complexes (in
    terms of 'i' or 'I'), polynomials in 'a' with integer
    coefficients, or lists of the above.
    """
    z = s
    if type(z) in [list, tuple]:
        return [p2sage(t) for t in z]
    else:
        Qa = PolynomialRing(RationalField(),"a");
        for f in [ZZ, RR, CC, Qa]:
            try:
                return f(z)
            # SyntaxError is raised by CC('??')
            # NameError is raised by CC('a')
            except (ValueError, TypeError, NameError, SyntaxError):
                try:
                    return f(str(z))
                except (ValueError, TypeError, NameError, SyntaxError):
                    pass
        if z!='??':
            logger.error('Error converting "{}" in p2sage'.format(z))
        return z

def string2number(s):
    # a start to replace p2sage (used for the paramters in the FE)

    strs = str(s).replace(' ','')
    try:
        if 'e' in strs:
            # check for e(m/n) := exp(2*pi*i*m/n), used by Dirichlet characters, for example
            r = re.match('^\$?e\\\\left\(\\\\frac\{(?P<num>\d+)\}\{(?P<den>\d+)\}\\\\right\)\$?$',strs)
            if not r:
                r = re.match('^e\((?P<num>\d+)/(?P<den>\d+)\)$',strs)
            if r:
                q = Rational(r.groupdict()['num'])/Rational(r.groupdict()['den'])
                return CDF(exp(2*pi*I*q))
        if 'I' in strs:
            return CDF(strs)
        elif '/' in strs:
            return Rational(strs)
        elif strs=='0.5':  # Temporary fix because 0.5 in db for EC
            return Rational('1/2')
        elif '.' in strs:
            return float(strs)
        else:
            return Integer(strs)
    except:
        return s

    
def pair2complex(pair):
    ''' Turns the pair into a complex number.
    '''
    local = re.match(" *([^ ]+)[ \t]*([^ ]*)", pair)
    if local:
        rp = local.group(1)
        if local.group(2):
            ip = local.group(2)
        else:
            ip = 0
    else:
        rp = 0
        ip = 0
    return float(rp) + float(ip) * I


def splitcoeff(coeff):
    local = coeff.split("\n")
    answer = []
    for s in local:
        if s:
            answer.append(pair2complex(s))

    return answer


def styleTheSign(sign):
    ''' Returns the string to display as sign
    '''
    try:
        logger.debug(1 - sign)
        if sign == 0:
            return "unknown"
        return(seriescoeff(sign, 0, "literal", "", -6, 5))
    except:
        logger.debug("no styling of sign")
        return str(sign)


def seriescoeff(coeff, index, seriescoefftype, seriestype, truncationexp, precision):
  # seriescoefftype can be: series, serieshtml, signed, literal, factor
#  truncationexp is used to determine if a number is 'really' 0 or 1 or -1 or I or -I or 0.5 or -0.5
#  precision is used to truncate decimal numbers
    truncation = float(10 ** truncationexp)
    try:
        if isinstance(coeff,str) or isinstance(coeff,unicode):
            coeff = string2number(coeff)
        if type(coeff) == complex:
            rp = coeff.real
            ip = coeff.imag
        else:
            rp = real_part(coeff)
            ip = imag_part(coeff)
    except TypeError:     # mostly a hack for Dirichlet L-functions
        if seriescoefftype == "serieshtml":
            if coeff == "I":
                return " + " + "$i$" + "&middot;" + seriesvar(index, seriestype) 
            elif coeff == "-I":
                return "&minus;" + " $i$" + "&middot;" + seriesvar(index, seriestype)
            else:
                return " +" + coeff + "&middot;" + seriesvar(index, seriestype)
        else:
            return coeff
# below we use float(abs()) instead of abs() to avoid a sage bug
    if (float(abs(rp)) > truncation) & (float(abs(ip)) > truncation):  # has a real and an imaginary part
        ans = ""
        if seriescoefftype == "series" or seriescoefftype == "signed":
            ans += "+"
            ans += "("
            ans += truncatenumber(rp, precision)
        elif seriescoefftype == "serieshtml":
            ans += " + "
            ans += "("
            if rp > 0:
                ans += truncatenumber(rp, precision)
            else:
                ans += "&minus;"+truncatenumber(float(abs(rp)), precision)
        elif seriescoefftype == "factor":
            ans += "("
            ans += truncatenumber(rp, precision)
        else:
            ans += truncatenumber(rp, precision)
        if ip > 0:
            ans += " + "
        if seriescoefftype == "series" or seriescoefftype == "signed":
            ans += truncatenumber(ip, precision) + " i"
        elif seriescoefftype == "serieshtml":
            if ip > 0:
                ans += truncatenumber(ip, precision)
            else:
                ans += " &minus; "+truncatenumber(float(abs(ip)), precision)
            ans += "<em>i</em>"
        elif seriescoefftype == "factor":
            ans += truncatenumber(ip, precision) + "i" + ")"
        else:
            ans += truncatenumber(ip, precision) + "i"
        if seriescoefftype == "series" or seriescoefftype == "serieshtml" or seriescoefftype == "signed":
            return(ans + ")" + " " + seriesvar(index, seriestype))
        else:
            return(ans)

    elif (float(abs(rp)) < truncation) & (float(abs(ip)) < truncation):
        if seriescoefftype != "literal":
            return("")
        else:
            return("0")
# if we get this far, either pure real or pure imaginary
    ans = ""
    if rp > truncation:
        if float(abs(rp - 1)) < truncation:
            if seriescoefftype == "literal":
                return("1")
            elif seriescoefftype == "signed":
                return("+1")
            elif seriescoefftype == "factor":
                return("")
            elif seriescoefftype == "series" or seriescoefftype == "serieshtml":
                return(ans + " + " + seriesvar(index, seriestype))
        else:
            if seriescoefftype == "series" or seriescoefftype == "serieshtml":
                return(" + " + ans + truncatenumber(rp, precision) + "&middot;" + seriesvar(index, seriestype))
            elif seriescoefftype == "signed":
                return(ans + "+" + truncatenumber(rp, precision))
            elif seriescoefftype == "literal" or seriescoefftype == "factor":
                return(ans + truncatenumber(rp, precision))
    elif rp < -1 * truncation:
        if float(abs(rp + 1)) < truncation:
            if seriescoefftype == "literal":
                return("-1" + seriesvar(index, seriestype))
            elif seriescoefftype == "signed":
                return("-1" + seriesvar(index, seriestype))
            elif seriescoefftype == "factor":
                return("-" + seriesvar(index, seriestype))
            elif seriescoefftype == "series":  # adding space between minus sign and value
                return(" - " + seriesvar(index, seriestype))
            elif seriescoefftype == "serieshtml":  # adding space between minus sign and value
                return(" &minus; " + seriesvar(index, seriestype))
            else:
                return("-" + seriesvar(index, seriestype))
        else:
            if seriescoefftype == "series":
                return(ans + " - " + truncatenumber(-1*rp, precision) + seriesvar(index, seriestype))
            elif seriescoefftype == "signed":
                return(ans + "-" + truncatenumber(-1*rp, precision))
            elif seriescoefftype == "serieshtml":
                return(ans + " &minus; " + truncatenumber(-1*rp, precision) + "&middot;" +  seriesvar(index, seriestype))
            elif seriescoefftype == "literal" or seriescoefftype == "factor":
                return(ans + truncatenumber(rp, precision))

# if we get this far, it is pure imaginary
    elif ip > truncation:
        if float(abs(ip - 1)) < truncation:
            if seriescoefftype == "literal":
                return("i")
            elif seriescoefftype == "signed":
                return("+i")
            elif seriescoefftype == "factor":
                return("i")
            elif seriescoefftype == "series":
                return(ans + " + i" + seriesvar(index, seriestype))
            elif seriescoefftype == "serieshtml":
                return(ans + " + <em>i</em>" + "&middot;" + seriesvar(index, seriestype))
                  # yes, em is not the right tag, but it is styled with CSS
        else:
            if seriescoefftype == "series":
                return(ans + truncatenumber(ip, precision) + "i " + seriesvar(index, seriestype))
            elif seriescoefftype == "serieshtml":
                return(ans + " + " + truncatenumber(ip, precision) + "<em>i</em> " + "&middot;" + seriesvar(index, seriestype))
            elif seriescoefftype == "signed":
                return(ans + "+" + truncatenumber(ip, precision) + "i")
            elif seriescoefftype == "literal" or seriescoefftype == "factor":
                return(ans + truncatenumber(ip, precision) + "i")
    elif ip < -1 * truncation:
        if float(abs(ip + 1)) < truncation:
            if seriescoefftype == "factor": #assumes that factor is used in math mode
                return("- i \cdot" + seriesvar(index, seriestype))
            elif seriescoefftype == "serieshtml":
                return(" &minus; <em>i</em> &middot;" + seriesvar(index, seriestype))
            else:
                return("- i" + seriesvar(index, seriestype))
        else:
            if seriescoefftype == "series":
                return(ans + truncatenumber(ip, precision) + "i" + seriesvar(index, seriestype))
            elif seriescoefftype == "serieshtml":
                return(ans + " &minus; " + truncatenumber(float(abs(ip)), precision) + "<em>i</em>" + "&middot;" + seriesvar(index, seriestype))
            elif seriescoefftype == "signed":
                return(ans + truncatenumber(ip, precision) + " i")
            elif seriescoefftype == "literal" or seriescoefftype == "factor":
                return(ans + truncatenumber(ip, precision) + "i")

    else:
        return(latex(coeff) + seriesvar(index, seriestype))


def seriesvar(index, seriestype):
    if seriestype == "dirichlet":
        return(" \\ " + str(index) + "^{-s}")
    elif seriestype == "dirichlethtml":
      # WARNING: the following change has consequences which need to be addressed! (DF and SK, July 29, 2015)
      #  return(" " + str(index) + "<sup>-s</sup>")
        return(str(index) + "<sup>-s</sup>")
    elif seriestype == "":
        return("")
    elif seriestype == "qexpansion":
        return("\\, " + "q^{" + str(index) + "}")
    else:
        return("")


def lfuncDShtml(L, fmt):
    """ Returns the HTML for displaying the Dirichlet series of the L-function L.
        fmt could be any of the values: "analytic", "langlands", "abstract"
    """

    if len(L.dirichlet_coefficients) == 0:
        return '\\text{No Dirichlet coefficients supplied.}'

    numperline = 4
    maxcoeffs = 20
    if L.selfdual:
        numperline = 9  # Actually, we want 8 per line, and one extra addition to counter to ensure
                        # we add only one newline
        maxcoeffs = 30
    ans = ""
    # Changes to account for very sparse series, only count actual nonzero terms to decide when to go to next line
    # This actually jumps by 2 whenever we add a newline, to ensure we just add one new line
    nonzeroterms = 1
#    if fmt == "analytic" or fmt == "langlands":
    if fmt in ["analytic", "langlands", "arithmetic"]:
        ans += "<table class='dirichletseries'><tr>"
        ans += "<td valign='top'>"  # + "$" 
        if fmt == "arithmetic":
            ans += "<span class='term'>"
            ans += L.htmlname_arithmetic
            ans += "&thinsp;"
            ans += "&nbsp;=&nbsp;"
            ans += "1<sup></sup>" + "&nbsp;"
            ans += "</span>"
        elif hasattr(L, 'htmlname'):
            ans += "<span class='term'>"
            ans += L.htmlname
            ans += "&thinsp;"
            ans += "&nbsp;=&nbsp;"
            ans += "1<sup></sup>" + "&nbsp;"
            ans += "</span>"
        else:
            ans += "<span class='term'>"
            ans += '$'+L.texname+'$'
            ans += "&thinsp;"
            ans += "&nbsp;=&nbsp;"
            ans += "1<sup></sup>" + "&nbsp;"
            ans += "</span>"
        ans += "</td><td valign='top'>"

        if fmt == "arithmetic":
            ds_length = len(L.dirichlet_coefficients_arithmetic)
        else:
            ds_length = len(L.dirichlet_coefficients)

        for n in range(1, ds_length):
            if fmt == "arithmetic":
                tmp = seriescoeff(L.dirichlet_coefficients_arithmetic[n], n + 1,
                    "serieshtml", "dirichlethtml", -6, 5)
            else:
                tmp = seriescoeff(L.dirichlet_coefficients[n], n + 1,
                    "serieshtml", "dirichlethtml", -6, 5)
            if tmp != "":
                nonzeroterms += 1
            ans = ans + " <span class='term'>" + tmp + "</span> "  
                # need a space between spans to allow line breaks. css stops a break within a span
     
            if nonzeroterms > maxcoeffs:
                break
            if(nonzeroterms % numperline == 0):
                ans = ans + "\n"     # don't need  \cr in the html version
                nonzeroterms += 1   # This ensures we don t add more than one newline
        ans = ans + "<span class='term'> + &#8943;</span>\n</td></tr>\n</table>\n"

    elif fmt == "abstract":
        if L.Ltype() == "riemann":
            ans = "\[\\begin{equation} \n \\zeta(s) = \\sum_{n=1}^{\\infty} n^{-s} \n \\end{equation} \]\n"

        elif L.Ltype() == "dirichlet":
            ans = "\[\\begin{equation} \n L(s,\\chi) = \\sum_{n=1}^{\\infty} \\chi(n) n^{-s} \n \\end{equation}\]"
            ans = ans + "where $\\chi$ is the character modulo " + str(L.charactermodulus)
            ans = ans + ", number " + str(L.characternumber) + "."

        else:
            ans = "\[\\begin{equation} \n " + L.texname + \
                " = \\sum_{n=1}^{\\infty} a(n) n^{-s} \n \\end{equation}\]"
    return(ans)




def lfuncEPtex(L, fmt):
    """ Returns the LaTex for displaying the Euler product of the L-function L.
        fmt could be any of the values: "abstract"
    """
    if L.Ltype() in ["genus2curveQ", "ellipticcurveQ"] and fmt == "arithmetic":
        return lfuncEPhtml(L, fmt)

    ans = ""
    if fmt == "abstract" or fmt == "arithmetic":
        if fmt == "arithmetic":
            ans = "\\begin{equation} \n " + L.texname_arithmetic + " = "
        else:
            ans = "\\begin{equation} \n " + L.texname + " = "
        if L.Ltype() == "riemann":
            ans += "\\prod_p (1 - p^{-s})^{-1}"
        elif L.Ltype() == "dirichlet":
            ans += "\\prod_p (1- \\chi(p) p^{-s})^{-1}"
        elif L.Ltype() == "ellipticmodularform":
            ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + \chi(p)p^{-2s})^{-1}"
        elif L.Ltype() == "hilbertmodularform":
            ans += "\\prod_{\mathfrak{p}\\ \\mathrm{bad}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s})^{-1} \\prod_{\mathfrak{p}\\ \\mathrm{good}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s} + (N\mathfrak{p})^{-2s})^{-1}"
        elif L.Ltype() == "ellipticcurveQ":
            ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + p^{-2s})^{-1}"
        elif L.Ltype() == "maass":
            if L.group == 'GL2':
                ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + \chi(p)p^{-2s})^{-1}"
            elif L.group == 'GL3':
                ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1}  \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + \\overline{a(p)} p^{-2s} - p^{-3s})^{-1}"
            else:
                ans += "\\prod_p \\ \\prod_{j=1}^{" + str(L.degree) + \
                    "} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
        elif L.Ltype() == "SymmetricPower":
            ans += lfuncEpSymPower(L)
        elif L.langlands:
            if L.degree > 1:
                if fmt == "arithmetic":
                    ans += "\\prod_p \\ \\prod_{j=1}^{" + str(L.degree) + \
                        "} (1 - \\alpha_{j,p}\\,  p^{" + str(L.motivic_weight) + "/2 - s})^{-1}"
                else:
                    ans += "\\prod_p \\ \\prod_{j=1}^{" + str(L.degree) + \
                        "} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
            else:
                ans += "\\prod_p \\  (1 - \\alpha_{p}\\,  p^{-s})^{-1}"

        else:
            return("No information is available about the Euler product.")
        ans += " \n \\end{equation}"
        return(ans)
    else:
        return("No information is available about the Euler product.")

def lfuncEPhtml(L,fmt):
    """ Euler product as a formula and a table of local factors.
    """
    texform_gen = "\[L(s) = "  # "\[L(A,s) = "
    texform_gen += "\prod_{p \\text{ prime}} F_p(p^{-s})^{-1} \]\n"

    pfactors = prime_divisors(L.level)
    if len(pfactors) == 1:  #i.e., the conductor is prime
        pgoodset = "$p \\neq " + str(pfactors[0]) + "$"
        pbadset = "$p = " + str(pfactors[0]) + "$"
    else:
        badset = "\\{" + str(pfactors[0])
        for j in range(1,len(pfactors)):
            badset += ",\\;"
            badset += str(pfactors[j])
        badset += "\\}"
        pgoodset = "$p \\notin " + badset + "$"
        pbadset = "$p \\in " + badset + "$"


    ans = ""
    ans += texform_gen + "where, for " + pgoodset + ",\n"
    if L.degree == 4 and L.motivic_weight == 1:
        ans += "\[F_p(T) = 1 - a_p T + b_p T^2 -  a_p p T^3 + p^2 T^4 \]"
        ans += "with $b_p = a_p^2 - a_{p^2}$. "
    elif L.degree == 2 and L.motivic_weight == 1:
        ans += "\[F_p(T) = 1 - a_p T + p T^2 .\]"
    else:
        ans += "\(F_p\) is a polynomial of degree " + str(L.degree) + ". "
    ans += "If " + pbadset + ", then $F_p$ is a polynomial of degree at most "
    ans += str(L.degree - 1) + ". "
    bad_primes = []
    for lf in L.bad_lfactors:
        bad_primes.append(lf[0])
    eulerlim = 25
    good_primes = []
    for j in range(0, eulerlim):
        this_prime = Primes().unrank(j)
        if this_prime not in bad_primes:
            good_primes.append(this_prime)
    eptable = "<table id='eptable' class='ntdata euler'>\n"
    eptable += "<thead>"
    eptable += "<tr class='space'><th class='weight'></th><th class='weight'>$p$</th><th class='weight'>$F_p$</th>"
    if L.degree > 2:
        eptable += "<th class='weight galois'>$\Gal(F_p)$</th>"
    eptable += "</tr>\n"
    eptable += "</thead>"
    goodorbad = "bad"
    C = getDBConnection()
    for lf in L.bad_lfactors:
        try:
            thispolygal = list_to_factored_poly_otherorder(lf[1], galois=True)
            eptable += ("<tr><td>" + goodorbad + "</td><td>" + str(lf[0]) + "</td><td>" + 
                        "$" + thispolygal[0] + "$" +
                        "</td>")
            if L.degree > 2:
                eptable += "<td class='galois'>" 
                this_gal_group = thispolygal[1]
                if this_gal_group[0]==[0,0]:
                    pass   # do nothing, because the local faco is 1
                elif this_gal_group[0]==[1,1]:
                    eptable += group_display_knowl(this_gal_group[0][0],this_gal_group[0][1],C,'$C_1$') 
                else:
                    eptable += group_display_knowl(this_gal_group[0][0],this_gal_group[0][1],C) 
                for j in range(1,len(thispolygal[1])):
                    eptable += "$\\times$"
                    eptable += group_display_knowl(this_gal_group[j][0],this_gal_group[j][1],C)
                eptable += "</td>"
            eptable += "</tr>\n"

        except IndexError:
            eptable += "<tr><td></td><td>" + str(j) + "</td><td>" + "not available" + "</td></tr>\n"
        goodorbad = ""
    goodorbad = "good"
    firsttime = " class='first'"
    good_primes1 = good_primes[:9]
    good_primes2 = good_primes[9:]
    for j in good_primes1:
        this_prime_index = prime_pi(j) - 1
        thispolygal = list_to_factored_poly_otherorder(L.localfactors[this_prime_index],galois=True)
        eptable += ("<tr" + firsttime + "><td>" + goodorbad + "</td><td>" + str(j) + "</td><td>" +
                    "$" + thispolygal[0] + "$" +
                    "</td>")
        if L.degree > 2:
            eptable += "<td class='galois'>"
            this_gal_group = thispolygal[1]
            eptable += group_display_knowl(this_gal_group[0][0],this_gal_group[0][1],C) 
            for j in range(1,len(thispolygal[1])):
                eptable += "$\\times$"
                eptable += group_display_knowl(this_gal_group[j][0],this_gal_group[j][1],C)
            eptable += "</td>"
        eptable += "</tr>\n"


#        eptable += "<td>" + group_display_knowl(4,1,C) + "</td>"
#        eptable += "</tr>\n"
        goodorbad = ""
        firsttime = ""
    firsttime = " id='moreep'"
    for j in good_primes2:
        this_prime_index = prime_pi(j) - 1
        thispolygal = list_to_factored_poly_otherorder(L.localfactors[this_prime_index],galois=True)
        eptable += ("<tr" + firsttime +  " class='more nodisplay'" + "><td>" + goodorbad + "</td><td>" + str(j) + "</td><td>" +
                    "$" + list_to_factored_poly_otherorder(L.localfactors[this_prime_index], galois=True)[0] + "$" +
                    "</td>")
        if L.degree > 2:
            this_gal_group = thispolygal[1]
            eptable += "<td class='galois'>"
            eptable += group_display_knowl(this_gal_group[0][0],this_gal_group[0][1],C)
            for j in range(1,len(thispolygal[1])):
                eptable += "$\\times$"
                eptable += group_display_knowl(this_gal_group[j][0],this_gal_group[j][1],C)
            eptable += "</td>"

        eptable += "</tr>\n"
        firsttime = ""

    eptable += "<tr class='less toggle'><td></td><td></td><td> <a onclick='"
    eptable += 'show_moreless("more"); return true' + "'"
    eptable += ' href="#moreep" '
    eptable += ">show more</a></td></tr>\n"
    eptable += "<tr class='more toggle nodisplay'><td></td><td></td><td> <a onclick='"
    eptable += 'show_moreless("less"); return true' + "'"
    eptable += ' href="#eptable" '
    eptable += ">show less</a></td></tr>\n"
    eptable += "</table>\n"
    ans += "\n" + eptable
    return(ans)

def lfuncEpSymPower(L):
    """ Helper funtion for lfuncEPtex to do the symmetric power L-functions
    """
    ans = ''
    for p in L.S.bad_primes:
        poly = L.S.eulerFactor(p)
        poly_string = " "
        if len(poly) > 1:
            poly_string = "(1"
            if poly[1] != 0:
                if poly[1] == 1:
                    poly_string += "+%d^{ -s}" % p
                elif poly[1] == -1:
                    poly_string += "-%d^{- s}" % p
                elif poly[1] < 0:
                    poly_string += "%d\\ %d^{- s}" % (poly[1], p)
                else:
                    poly_string += "+%d\\ %d^{- s}" % (poly[1], p)

            for j in range(2, len(poly)):
                if poly[j] == 0:
                    continue
                if poly[j] == 1:
                    poly_string += "%d^{-%d s}" % (p, j)
                elif poly[j] == -1:
                    poly_string += "-%d^{-%d s}" % (p, j)
                elif poly[j] < 0:
                    poly_string += "%d \\ %d^{-%d s}" % (poly[j], p, j)
                else:
                    poly_string += "+%d\\ %d^{-%d s}" % (poly[j], p, j)
            poly_string += ")^{-1}"
        ans += poly_string
    ans += '\\prod_{p \\nmid %d }\\prod_{j=0}^{%d} ' % (L.E.conductor(),L.m)
    ans += '\\left(1- \\frac{\\alpha_p^j\\beta_p^{%d-j}}' % L.m
    ans += '{p^{s}} \\right)^{-1}'    
    return ans

#---------


def lfuncFEtex(L, fmt):
    """ Returns the LaTex for displaying the Functional equation of the L-function L.
        fmt could be any of the values: "analytic", "selberg"
    """
    if fmt == "arithmetic":
        mu_list = [mu - L.motivic_weight/2 for mu in L.mu_fe]
        nu_list = [nu - L.motivic_weight/2 for nu in L.nu_fe]
        mu_list.sort()
        nu_list.sort()
        texname = L.texname_arithmetic
        try:
            tex_name_s = L.texnamecompleteds_arithmetic
            tex_name_1ms = L.texnamecompleted1ms_arithmetic
        except AttributeError:
            tex_name_s = L.texnamecompleteds
            tex_name_1ms = L.texnamecompleted1ms

    else:
        mu_list = L.mu_fe[:]
        nu_list = L.nu_fe[:]
        texname = L.texname
        tex_name_s = L.texnamecompleteds
        tex_name_1ms = L.texnamecompleted1ms
    ans = ""
    if fmt == "arithmetic" or fmt == "analytic":
        ans = "\\begin{align}\n" + tex_name_s + "=\\mathstrut &"
        if L.level > 1:
            # ans+=latex(L.level)+"^{\\frac{s}{2}}"
            ans += latex(L.level) + "^{s/2}"
        # set up to accommodate multiplicity of Gamma factors
        old_mu = ""
        curr_mu_exp = 0
        for mu in mu_list:
            if mu == old_mu:
                curr_mu_exp += 1
            else:
                old_mu = mu
                if curr_mu_exp > 1:
                    ans += "^{" + str(curr_mu_exp) + "}"
                curr_mu_exp = 1
                ans += "\Gamma_{\R}(s" + seriescoeff(mu, 0, "signed", "", -6, 5) + ")"
        if curr_mu_exp >= 2:
            ans += "^{" + str(curr_mu_exp) + "}"
        # set up to accommodate multiplicity of Gamma factors
        old_nu = ""
        curr_nu_exp = 0
        for nu in nu_list:
            if nu == old_nu:
                curr_nu_exp += 1
            else:
                old_nu = nu
                if curr_nu_exp > 1:
                    ans += "^{" + str(curr_nu_exp) + "}"
                curr_nu_exp = 1
                ans += "\Gamma_{\C}(s" + seriescoeff(nu, 0, "signed", "", -6, 5) + ")"
        if curr_nu_exp >= 2:
            ans += "^{" + str(curr_nu_exp) + "}"
        ans += " \\cdot " + texname + "\\cr\n"
        ans += "=\\mathstrut & "
        if L.sign == 0:
            ans += "\epsilon \cdot "
        else:
            ans += seriescoeff(L.sign, 0, "factor", "", -6, 5)
        ans += tex_name_1ms
        if L.sign == 0 and L.degree == 1:
            ans += "\quad (\\text{with }\epsilon \\text{ not computed})"
        if L.sign == 0 and L.degree > 1:
            ans += "\quad (\\text{with }\epsilon \\text{ unknown})"
        ans += "\n\\end{align}\n"
    elif fmt == "selberg":
        ans += "(" + str(int(L.degree)) + ",\\ "
        ans += str(int(L.level)) + ",\\ "
        ans += "("
        if L.mu_fe != []:
            for mu in range(len(L.mu_fe) - 1):
                prec = len(str(L.mu_fe[mu]))
                ans += seriescoeff(L.mu_fe[mu], 0, "literal", "", -6, prec) + ", "
            prec = len(str(L.mu_fe[-1]))
            ans += seriescoeff(L.mu_fe[-1], 0, "literal", "", -6, prec)
        else:
            ans += "\\ "
        ans += ":"
        if L.nu_fe != []:
            for nu in range(len(L.nu_fe) - 1):
                ans += str(L.nu_fe[nu]) + ", "
            ans += str(L.nu_fe[-1])
        else:
            ans += "\\ "
        ans += "),\\ "
        ans += seriescoeff(L.sign, 0, "literal", "", -6, 5)
        ans += ")"

    return(ans)


def specialValueString(L, s, sLatex, normalization="analytic"):
    ''' Returns the LaTex to dislpay for L(s)
        Will eventually be replaced by specialValueTriple.
    '''
    number_of_decimals = 10
    val = None
    if hasattr(L,"lfunc_data"):
        s_alg = s+p2sage(L.lfunc_data['analytic_normalization'])
        for x in p2sage(L.lfunc_data['values']):
            # the numbers here are always half integers
            # so this comparison is exact
            if x[0] == s_alg:
                val = x[1]
                break
    if val is None:
        if L.fromDB:
            val = "not computed"
        else:
            val = L.sageLfunction.value(s)
    if normalization == "arithmetic":
        lfunction_value_tex = L.texname_arithmetic.replace('s)',  sLatex + ')')
    else:
        lfunction_value_tex = L.texname.replace('(s', '(' + sLatex)
    # We must test for NaN first, since it would show as zero otherwise
    # Try "RR(NaN) < float(1e-10)" in sage -- GT
    if CC(val).real().is_NaN():
        return "\\[{0}=\\infty\\]".format(lfunction_value_tex)
    elif val.abs() < 1e-10:
        return "\\[{0}=0\\]".format(lfunction_value_tex)
    elif normalization == "arithmetic":
        return(lfunction_value_tex,
               latex(round(val.real(), number_of_decimals)
                         + round(val.imag(), number_of_decimals) * I))
    else:
        return "\\[{0} \\approx {1}\\]".format(lfunction_value_tex,
                                               latex(round(val.real(), number_of_decimals)
                                                     + round(val.imag(), number_of_decimals) * I))

def specialValueTriple(L, s, sLatex_analytic, sLatex_arithmetic):
    ''' Returns [L_arithmetic, L_analytic, L_val]
        Currently only used for genus 2 curves
        and Dirichlet characters.
        Eventually want to use for all L-functions.
    '''
    number_of_decimals = 10
    val = None
    if hasattr(L,"lfunc_data"):
        s_alg = s+p2sage(L.lfunc_data['analytic_normalization'])
        if 'values' in L.lfunc_data.keys():
            for x in p2sage(L.lfunc_data['values']):
            # the numbers here are always half integers
            # so this comparison is exact
                if x[0] == s_alg:
                    val = x[1]
                    break
    if val is None:
        if L.fromDB:
            val = "not computed"
        else:
            val = L.sageLfunction.value(s)
    # We must test for NaN first, since it would show as zero otherwise
    # Try "RR(NaN) < float(1e-10)" in sage -- GT

    lfunction_value_tex_arithmetic = L.texname_arithmetic.replace('s)',  sLatex_arithmetic + ')')
    lfunction_value_tex_analytic = L.texname.replace('(s', '(' + sLatex_analytic)

    try:
        if CC(val).real().is_NaN():
            Lval = "\\infty"
        elif val.abs() < 1e-10:
            Lval = "0"
        else:
            Lval = latex(round(val.real(), number_of_decimals)
                         + round(val.imag(), number_of_decimals) * I)
    except (TypeError, NameError):
        Lval = val    # if val is text

    return [lfunction_value_tex_analytic, lfunction_value_tex_arithmetic, Lval]

###############################################################
# Functions for Siegel dirichlet series
###############################################################
NN = 500
CF = ComplexField(NN)


def compute_dirichlet_series(p_list, PREC):
    ''' computes the dirichlet series for a Lfunction_SMF2_scalar_valued
    '''
    # p_list is a list of pairs (p,y) where p is a prime and y is the list of roots of the Euler factor at x
    LL = [0] * PREC
    # create an empty list of the right size and now populate it with the powers of p
    for (p, y) in p_list:
        # FIXME p_prec is never used, but perhaps it should be?
        # p_prec = log(PREC) / log(p) + 1
        ep = euler_p_factor(y, PREC)
        for n in range(ep.prec()):
            if p ** n < PREC:
                LL[p ** n] = ep.coefficients()[n]
    for i in range(1, PREC):
        f = factor(i)
        if len(f) > 1:  # not a prime power
            LL[i] = prod([LL[p ** e] for (p, e) in f])
    return LL[1:]


def euler_p_factor(root_list, PREC):
    ''' computes the coefficients of the pth Euler factor expanded as a geometric series
      ax^n is the Dirichlet series coefficient p^(-ns)
    '''
    PREC = floor(PREC)
    # return satake_list
    R = LaurentSeriesRing(CF, 'x')
    x = R.gens()[0]
    ep = prod([1 / (1 - a * x) for a in root_list])
    return ep + O(x ** (PREC + 1))


def compute_local_roots_SMF2_scalar_valued(K, ev, k, embedding):
    ''' computes the dirichlet series for a Lfunction_SMF2_scalar_valued
    '''

    L = ev.keys()
    m = ZZ(max(L)).isqrt() + 1
    ev2 = {}
    for p in primes(m):

        try:
            ev2[p] = (ev[p], ev[p * p])
        except:
            break

    logger.debug(str(ev2))
    ret = []
    for p in ev2:
        R = PolynomialRing(K, 'x')
        x = R.gens()[0]

        f = (1 - ev2[p][0] * x + (ev2[p][0] ** 2 - ev2[p][1] - p ** (
            2 * k - 4)) * x ** 2 - ev2[p][0] * p ** (2 * k - 3) * x ** 3 + p ** (4 * k - 6) * x ** 4)

        Rnum = PolynomialRing(CF, 'y')
        x = Rnum.gens()[0]
        fnum = Rnum(0)
        if K != QQ:
            for i in range(int(f.degree()) + 1):
                fnum = fnum + f[i].complex_embeddings(NN)[embedding] * (x / p ** (k - 1.5)) ** i
        else:
            for i in range(int(f.degree()) + 1):
                fnum = fnum + f[i] * (x / CF(p ** (k - 1.5))) ** i

        r = fnum.roots(CF)
        r = [1 / a[0] for a in r]
        # a1 = r[1][0]/r[0][0]
        # a2 = r[2][0]/r[0][0]
        # a0 = 1/r[3][0]

        ret.append((p, r))

    return ret


###############################################################
# Functions for cusp forms
###############################################################


def signOfEmfLfunction(level, weight, coefs, tol=10 ** (-7), num=1.3):
    """ Computes the sign of a EMF with give level, weight and
        coefficients numerically by computing the value of the EMF
        at two points related by the Atkin-Lehner involution.
        If the absolute value of the result is more than tol from 1
        then it returns "Not able to compute" which indicates to few
        (or wrong) coeffcients.
        The parameter num chooses the related points and shouldn't be 1.
    """
    sum1 = 0
    sum2 = 0
    for i in range(1, len(coefs)):
        sum1 += coefs[i - 1] * math.exp(- 2 * math.pi * i * num / math.sqrt(level))
        logger.debug("Sum1: {0}".format(sum1))
        sum2 += coefs[i - 1].conjugate() * math.exp(- 2 * math.pi * i / num / math.sqrt(level)) / \
            num ** weight
        logger.debug("Sum2: {0}".format(sum2))
    sign = sum1 / sum2
    if abs(abs(sign) - 1) > tol:
        logger.critical("Not enough coefficients to compute the sign of the L-function.")
        sign = "Not able to compute."
        sign = 1 # wrong, but we need some type of error handling here.
    return sign

###############################################################
# Functions for elliptic curves
###############################################################

def getConductorIsogenyFromLabel(label):
    ''' Returns the pair (conductor, isogeny) where label is either
        a LMFDB label or a Cremona label of either an elliptic curve
        or an isogeny class.
    '''
    try:
        if '.' in label:
            #LMFDB label
            cond, iso = label.split('.')
        else:
            # Cremona label
            cond = ''
            iso = label
            while iso[0].isdigit():
                cond += iso[0]
                iso = iso[1:]
                
        # Strip off the curve number
        while iso[-1].isdigit():
            iso = iso[:-1]
        return cond, iso

    except:
        return None, None
    


