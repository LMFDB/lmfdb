# Different helper functions.

import re
from lmfdb.lfunctions import logger
from flask import url_for
import math
from sage.all import ZZ, QQ, RR, CC, Rational, RationalField, ComplexField, PolynomialRing, LaurentSeriesRing, O, Integer, primes, CDF, I, real_part, imag_part, latex, factor, prime_divisors, prime_pi, exp, pi, prod, floor, primes_first_n, is_prime
from lmfdb.transitive_group import group_display_knowl
from lmfdb.db_backend import db
from lmfdb.utils import display_complex, list_to_factored_poly_otherorder


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
        elif (type(s) is list or type(s) is tuple) and len(s) == 2:
            return CDF(tuple(s))
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
        return seriescoeff(sign, 0, "literal", "", 3)
    except:
        logger.debug("no styling of sign")
        return str(sign)


def seriescoeff(coeff, index, seriescoefftype, seriestype, digits):
    # seriescoefftype can be: series, serieshtml, signed, literal, factor
    try:
        if isinstance(coeff,str) or isinstance(coeff,unicode):
            if coeff == "I":
                rp = 0
                ip = 1
            elif coeff == "-I":
                rp = 0
                ip = -1
            else:
                coeff = string2number(coeff)
        if type(coeff) == complex:
            rp = coeff.real
            ip = coeff.imag
        else:
            rp = real_part(coeff)
            ip = imag_part(coeff)
    except TypeError:     # mostly a hack for Dirichlet L-functions
        if seriescoefftype == "serieshtml":
            return " +" + coeff + "&middot;" + seriesvar(index, seriestype)
        else:
            return coeff
    ans = ""
    if seriescoefftype in ["series", "serieshtml", "signed", "factor"]:
        parenthesis = True
    else:
        parenthesis = False
    coeff_display =  display_complex(rp, ip, digits, method="truncate", parenthesis=parenthesis)

    # deal with the zero case
    if coeff_display == "0":
        if seriescoefftype=="literal":
            return "0"
        else:
            return ""

    if seriescoefftype=="literal":
        return coeff_display

    if seriescoefftype == "factor":
        if coeff_display == "1":
            return ""
        elif coeff_display == "-1":
            return "-"

    #add signs and fix spacing
    if seriescoefftype in ["series", "serieshtml"]:
        if coeff_display == "1":
            coeff_display = " + "
        elif coeff_display == "-1":
            coeff_display = " - "
        # purely real or complex number that starts with -
        elif coeff_display[0] == '-':
            # add spacings around the minus
            coeff_display = coeff_display.replace('-',' - ')
        else:
            ans += " + "
    elif seriescoefftype == 'signed' and coeff_display[0] != '-':
        # add the plus without the spaces
        ans += "+"

    ans += coeff_display


    if seriescoefftype == "serieshtml":
        ans = ans.replace('i',"<em>i</em>").replace('-',"&minus;")
        if coeff_display[-1] not in [')', ' ']:
            ans += "&middot;"
    if seriescoefftype in ["series", "serieshtml", "signed"]:
        ans += seriesvar(index, seriestype)

    return ans


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
    elif seriestype == "polynomial":
        if index == 0:
            return("")
        elif index == 1:
            return('T')
        else:
            return('T' + '^{' + str(index) + '}')
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
                    "serieshtml", "dirichlethtml", 3)
            else:
                tmp = seriescoeff(L.dirichlet_coefficients[n], n + 1,
                    "serieshtml", "dirichlethtml", 3)
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
    from Lfunction import Lfunction_from_db
    if ((L.Ltype() in ["genus2curveQ"] or isinstance(L, Lfunction_from_db))) and fmt == "arithmetic":
        try:
            return lfuncEPhtml(L, fmt)
        except Exception:
            if L.Ltype() == "general" and False:
                return ("For information concerning the Euler product, see other "
                    "instances of this L-function.")
            else:
                raise

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

        elif L.Ltype() == "classical modular form" and fmt == "arithmetic":
                ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s} + \chi(p)p^{-2s})^{-1}"
            #FIXME, this is consistent with G2C and EC
            # but do we really want this?
            #else:
            #    ans += "\\prod_{p\\ \\mathrm{bad}} (1- a(p) p^{-s/2})^{-1} \\prod_{p\\ \\mathrm{good}} (1- a(p) p^{-s/2} + \chi(p)p^{-s})^{-1}"
        elif L.Ltype() == "hilbertmodularform":
            ans += "\\prod_{\mathfrak{p}\\ \\mathrm{bad}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s})^{-1} \\prod_{\mathfrak{p}\\ \\mathrm{good}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s} + (N\mathfrak{p})^{-2s})^{-1}"

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
                        "} (1 - \\alpha_{j,p}\\,    p^{" + str(L.motivic_weight) + "/2 - s})^{-1}"
                else:
                    ans += "\\prod_p \\ \\prod_{j=1}^{" + str(L.degree) + \
                        "} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
            else:
                ans += "\\prod_p \\  (1 - \\alpha_{p}\\,  p^{-s})^{-1}"


        else:
            return("\\text{No information is available about the Euler product.}")
        ans += " \n \\end{equation}"
        return(ans)
    else:
        return("\\text{No information is available about the Euler product.}")

def lfuncEPhtml(L,fmt, prec = None):
    """
        Euler product as a formula and a table of local factors.
    """


    # Formula
    texform_gen = "\[L(s) = "  # "\[L(A,s) = "
    texform_gen += "\prod_{p \\text{ prime}} F_p(p^{-s})^{-1} \]\n"
    pfactors = prime_divisors(L.level)

    if len(pfactors) == 0:
        pgoodset = None
        pbadset =  None
    elif len(pfactors) == 1:  #i.e., the conductor is prime
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
    ans += texform_gen + "where"
    if pgoodset is not None:
        ans += ", for " + pgoodset
    ans += ",\n"
    if L.motivic_weight == 1 and L.characternumber == 1 and L.degree in [2,4]:
        if L.degree == 4:
            ans += "\[F_p(T) = 1 - a_p T + b_p T^2 -  a_p p T^3 + p^2 T^4 \]"
            ans += "with $b_p = a_p^2 - a_{p^2}$. "
        elif L.degree == 2:
            ans += "\[F_p(T) = 1 - a_p T + p T^2 .\]"
    else:
        ans += "\(F_p\) is a polynomial of degree " + str(L.degree) + ". "
    if pbadset is not None:
        ans += "If " + pbadset + ", then $F_p$ is a polynomial of degree at most "
        ans += str(L.degree - 1) + ". "

    # Figuring out good and bad primes
    bad_primes = []
    for lf in L.bad_lfactors:
        bad_primes.append(lf[0])
    eulerlim = 25
    good_primes = []
    for p in primes_first_n(eulerlim):
        if p not in bad_primes:
            good_primes.append(p)


    #decide if we display galois
    display_galois = True
    if L.degree <= 2  or L.degree >= 12:
        display_galois = False
    if L.coefficient_field == "CDF":
        display_galois = False

    def pretty_poly(poly, prec = None):
        out = "1"
        for i,elt in enumerate(poly):
            if elt is None or (i == prec and prec != len(poly) - 1):
                out += "O(%s)" % (seriesvar(i, "polynomial"),)
                break;
            elif i > 0:
                out += seriescoeff(elt, i, "series", "polynomial", 3)
        return out


    eptable = r"""<div style="max-width: 100%; overflow-x: auto;">"""
    eptable += "<table class='ntdata euler'>\n"
    eptable += "<thead>"
    eptable += "<tr class='space'><th class='weight'></th><th class='weight'>$p$</th>"
    if L.degree > 2  and L.degree < 12:
        display_galois = True
        eptable += "<th class='weight galois'>$\Gal(F_p)$</th>"
    else:
        display_galois = False
    eptable += r"""<th class='weight' style="text-align: left;">$F_p$</th>"""
    eptable += "</tr>\n"
    eptable += "</thead>"
    def row(trclass, goodorbad, p, poly):
        out = ""
        try:
            if L.coefficient_field == "CDF" or None in poly:
                factors = str(pretty_poly(poly, prec = prec))
            elif not display_galois:
                factors = list_to_factored_poly_otherorder(poly, galois=display_galois, prec = prec, p = p)
            else:
                factors, gal_groups = list_to_factored_poly_otherorder(poly, galois=display_galois, p = p)
            out += "<tr" + trclass + "><td>" + goodorbad + "</td><td>" + str(p) + "</td>";
            if display_galois:
                out += "<td class='galois'>"
                if gal_groups[0]==[0,0]:
                    pass   # do nothing, because the local faco is 1
                elif gal_groups[0]==[1,1]:
                    out += group_display_knowl(gal_groups[0][0], gal_groups[0][1],'$C_1$')
                else:
                    out += group_display_knowl(gal_groups[0][0], gal_groups[0][1])
                for n, k in gal_groups[1:]:
                    out += "$\\times$"
                    out += group_display_knowl(n, k)
                out += "</td>"
            out += "<td>" +"$" + factors + "$" + "</td>"
            out += "</tr>\n"

        except IndexError:
            out += "<tr><td></td><td>" + str(j) + "</td><td>" + "not available" + "</td></tr>\n"
        return out
    goodorbad = "bad"
    trclass = ""
    for lf in L.bad_lfactors:
        eptable += row(trclass, goodorbad, lf[0], lf[1])
        goodorbad = ""
        trclass = ""
    goodorbad = "good"
    trclass = " class='first'"
    good_primes1 = good_primes[:9]
    good_primes2 = good_primes[9:]
    for j in good_primes1:
        this_prime_index = prime_pi(j) - 1
        eptable += row(trclass, goodorbad, j, L.localfactors[this_prime_index])
        goodorbad = ""
        trclass = ""
    trclass = " id='moreep'  class='more nodisplay'"
    for j in good_primes2:
        this_prime_index = prime_pi(j) - 1
        eptable += row(trclass, goodorbad, j, L.localfactors[this_prime_index])
        trclass = " class='more nodisplay'"

    eptable += r"""<tr class="less toggle"><td colspan="2"> <a onclick="show_moreless(&quot;more&quot;); return true" href="#moreep">show more</a></td>"""

    last_entry = ""
    if display_galois:
        last_entry +="<td></td>"
    last_entry += "<td></td>"
    eptable += last_entry
    eptable += "</tr>"
    eptable += r"""<tr class="more toggle nodisplay"><td colspan="2"><a onclick="show_moreless(&quot;less&quot;); return true" href="#eptable">show less</a></td>"""
    eptable += last_entry
    eptable += "</tr>\n</table>\n</div>\n"
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
            if L.level >= 10**8 and not is_prime(int(L.level)):
                ans += r"\left(%s\right)^{s/2}" % latex(L.level_factored)
            else:
                ans += latex(L.level) + "^{s/2}"
            ans += " \\, "
        def munu_str(factors_list, field):
            assert field in ['\R','\C']
            # set up to accommodate multiplicity of Gamma factors
            old = ""
            res = ""
            curr_exp = 0
            for elt in factors_list:
                if elt == old:
                    curr_exp += 1
                else:
                    old = elt
                    if curr_exp > 1:
                        res += "^{" + str(curr_exp) + "}"
                    if curr_exp > 0:
                        res += " \\, "
                    curr_exp = 1
                    res += "\Gamma_{" + field + "}(s" + seriescoeff(elt, 0, "signed", "", 3) + ")"
            if curr_exp > 1:
                res += "^{" + str(curr_exp) + "}"
            if res != "":
                res +=  " \\, "
            return res
        ans += munu_str(mu_list, '\R')
        ans += munu_str(nu_list, '\C')
        ans += texname + "\\cr\n"
        ans += "=\\mathstrut & "
        if L.sign == 0:
            ans += "\epsilon \cdot "
        else:
            ans += seriescoeff(L.sign, 0, "factor", "", 3) + "\\,"
        ans += tex_name_1ms
        if L.sign == 0 and L.degree == 1:
            ans += "\quad (\\text{with }\epsilon \\text{ not computed})"
        if L.sign == 0 and L.degree > 1:
            ans += "\quad (\\text{with }\epsilon \\text{ unknown})"
        ans += "\n\\end{align}\n"
    elif fmt == "selberg":
        ans += "(" + str(int(L.degree)) + ",\\ "
        if L.level >= 10**8 and not is_prime(int(L.level)):
            ans += latex(L.level_factored)
        else:
            ans += str(int(L.level))
        ans += ",\\ "
        ans += "("
        # this is mostly a hack for GL2 Maass forms
        def real_digits(x):
            return len(str(x).replace('.','').lstrip('-').lstrip('0'))
        def mu_fe_prec(x):
            if L._Ltype == 'maass':
                return real_digits(imag_part(x))
            else:
                return 3
        if L.mu_fe != []:
            mus = [ display_complex(CDF(mu).real(), CDF(mu).imag(),  mu_fe_prec(mu), method="round" ) for mu in L.mu_fe ]
            if len(mus) >= 6 and mus == [mus[0]]*len(mus):
                ans += '[%s]^{%d}' % (mus[0], len(mus))
            else:
                ans += ", ".join(mus)
        else:
            ans += "\\ "
        ans += ":"
        if L.nu_fe != []:
            if len(L.nu_fe) >= 6 and L.nu_fe == [L.nu_fe[0]]*len(L.nu_fe):
                ans += '[%s]^{%d}' % (L.nu_fe[0], len(L.nu_fe))
            else:
                ans += ", ".join(map(str, L.nu_fe))
        else:
            ans += "\\ "
        ans += "),\\ "
        ans += seriescoeff(L.sign, 0, "literal", "", 3)
        ans += ")"

    return(ans)


def specialValueString(L, s, sLatex, normalization="analytic"):
    ''' Returns the LaTex to dislpay for L(s)
        Will eventually be replaced by specialValueTriple.
    '''
    if normalization=="arithmetic":
        _, tex, Lval =  specialValueTriple(L, s, '', sLatex)
    else:
        tex, _, Lval =  specialValueTriple(L, s, sLatex, '')
    if Lval == "\\infty":
        operator = " = "
    else:
        operator = "\\approx"
    return "\\[{0} {1} {2}\\]".format(tex, operator, Lval)
#    number_of_decimals = 10
#    val = None
#    if hasattr(L,"lfunc_data"):
#        s_alg = s+p2sage(L.lfunc_data['analytic_normalization'])
#        for x in p2sage(L.lfunc_data['values']):
#            # the numbers here are always half integers
#            # so this comparison is exact
#            if x[0] == s_alg:
#                val = x[1]
#                break
#    if val is None:
#        if L.fromDB:
#            val = "not computed"
#        else:
#            val = L.sageLfunction.value(s)
#    print val
#    if normalization == "arithmetic":
#        lfunction_value_tex = L.texname_arithmetic.replace('s)',  sLatex + ')')
#    else:
#        lfunction_value_tex = L.texname.replace('(s', '(' + sLatex)
#    # We must test for NaN first, since it would show as zero otherwise
#    # Try "RR(NaN) < float(1e-10)" in sage -- GT
#    if CC(val).real().is_NaN():
#        return "\\[{0}=\\infty\\]".format(lfunction_value_tex)
#    elif val.abs() < 1e-10:
#        return "\\[{0}=0\\]".format(lfunction_value_tex)
#    elif normalization == "arithmetic":
#        return(lfunction_value_tex,
#               latex(round(val.real(), number_of_decimals)
#                         + round(val.imag(), number_of_decimals) * I))
#    else:
#        return "\\[{0} \\approx {1}\\]".format(lfunction_value_tex,
#                                               latex(round(val.real(), number_of_decimals)
#                                                     + round(val.imag(), number_of_decimals) * I))

def specialValueTriple(L, s, sLatex_analytic, sLatex_arithmetic):
    ''' Returns [L_arithmetic, L_analytic, L_val]
        Currently only used for genus 2 curves
        and Dirichlet characters.
        Eventually want to use for all L-functions.
    '''
    number_of_decimals = 10
    val = None
    if L.fromDB: #getattr(L, 'fromDB', False):
        s_alg = s + L.analytic_normalization
        for x in L.values:
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

    if sLatex_arithmetic:
        lfunction_value_tex_arithmetic = L.texname_arithmetic.replace('s)',  sLatex_arithmetic + ')')
    else:
        lfunction_value_tex_arithmetic = ''
    if sLatex_analytic:
        lfunction_value_tex_analytic = L.texname.replace('(s', '(' + sLatex_analytic)
    else:
        lfunction_value_tex_analytic = ''

    if isinstance(val, basestring):
        Lval = val
    else:
        ccval = CDF(val)
        # We must test for NaN first, since it would show as zero otherwise
        # Try "RR(NaN) < float(1e-10)" in sage -- GT
        if ccval.real().is_NaN():
            Lval = "$\\infty$"
        else:
            Lval = display_complex(ccval.real(), ccval.imag(), number_of_decimals)

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

#######################################################################
# Functions for interacting with web structure
#######################################################################

# TODO This needs to be able to handle any sort of L-function.
# There should probably be a more relevant field
# in the database, instead of trying to extract this from a URL
# FIXME move this to somewhere else
def name_and_object_from_url(url):
    url_split = url.rstrip('/').lstrip('/').split("/");
    name = '??';
    obj_exists = False;

    if url_split[0] == "EllipticCurve":
        if url_split[1] == 'Q':
            # EllipticCurve/Q/341641/a
            label_isogeny_class = ".".join(url_split[-2:]);
            obj_exists = db.ec_curves.exists({"lmfdb_iso" : label_isogeny_class})
        else:
            # EllipticCurve/2.2.140.1/14.1/a
            label_isogeny_class =  "-".join(url_split[-3:]);
            obj_exists = db.ec_nfcurves.exists({"class_label" : label_isogeny_class})
        name = 'Isogeny class ' + label_isogeny_class;

    elif url_split[0] == "Character":
        # Character/Dirichlet/19/8
        assert url_split[1] == "Dirichlet"
        name = """Dirichlet Character \(\chi_{%s} (%s, \cdot) \)""" %  tuple(url_split[-2:])
        label = ".".join(url_split[-2:])
        obj_exists = db.char_dir_values.exists({"label" : label})

    elif url_split[0] == "Genus2Curve":
        # Genus2Curve/Q/310329/a
        assert url_split[1] == 'Q'
        label_isogeny_class = ".".join(url_split[-2:]);
        obj_exists = db.g2c_curves.exists({"class" : label_isogeny_class})
        name = 'Isogeny class ' + label_isogeny_class;


    elif url_split[0] == "ModularForm":
        if url_split[1] == 'GL2':
            if url_split[2] == 'Q' and url_split[3]  == 'holomorphic':
                if len(url_split) == 10:
                    # ModularForm/GL2/Q/holomorphic/24/2/f/a/11/2
                    newform_label = ".".join(url_split[-6:-2])
                    conrey_newform_label = ".".join(url_split[-6:])
                    name =  'Modular form ' + conrey_newform_label
                    obj_exists = db.mf_newforms.label_exists(newform_label)
                elif len(url_split) == 8:
                    # ModularForm/GL2/Q/holomorphic/24/2/f/a
                    newform_label = ".".join(url_split[-4:])
                    name =  'Modular form ' + newform_label;
                    obj_exists = db.mf_newforms.label_exists(newform_label)


            elif  url_split[2] == 'TotallyReal':
                # ModularForm/GL2/TotallyReal/2.2.140.1/holomorphic/2.2.140.1-14.1-a
                label = url_split[-1];
                name =  'Hilbert modular form ' + label;
                obj_exists = db.hmf_forms.label_exists(label);

            elif url_split[2] ==  'ImaginaryQuadratic':
                # ModularForm/GL2/ImaginaryQuadratic/2.0.4.1/98.1/a
                label = '-'.join(url_split[-3:])
                name = 'Bianchi modular form ' + label;
                obj_exists = db.bmf_forms.label_exists(label);
    elif url_split[0] == "ArtinRepresentation":
        label = url_split[1]
        name =  'Artin representation ' + label;
        obj_exists = db.artin_reps.label_exists(label.split('c')[0]);

    return name, obj_exists

def names_and_urls(instances):
    res = []
    names = []
    for instance in instances:
        if not isinstance(instance, basestring):
            instance = instance['url']
        name, obj_exists = name_and_object_from_url(instance)
        if not name:
            name = ''
        if obj_exists:
            url = "/"+instance
        else:
            name = '(%s)' % (name)
            url = ""
        # avoid duplicates
        if name not in names:
            res.append((name, url))
            names.append(name)
    return res

def get_bread(degree, breads=[]):
    """
    Returns the two top levels of bread crumbs plus the ones supplied in breads.
    """
    breadcrumb = [('L-functions', url_for('.l_function_top_page')),
          ('Degree ' + str(degree),
           url_for('.l_function_degree_page', degree='degree' + str(degree)))]
    for b in breads:
        breadcrumb.append(b)
    return breadcrumb

# Convert  r0r0c1 to (0,0;1), for example
def parse_codename(text):

    ans = text
    if 'c' in text:
        ans = re.sub('c', ';', ans, 1)
    else:
        ans += ';'
    ans = re.sub('r', '', ans, 1)
    ans = re.sub('(r|c)', ',', ans)

    return '(' + ans + ')'

