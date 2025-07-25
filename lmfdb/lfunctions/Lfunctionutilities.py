# Different helper functions.
import math
import re

from flask import url_for
from sage.all import (
    ZZ, QQ, RR, CC, Rational, RationalField, ComplexField, PolynomialRing,
    PowerSeriesRing, Integer, primes, CDF, I, real_part, imag_part,
    latex, factor, exp, pi, prod, floor, is_prime, prime_range)

from lmfdb.utils import (
    display_complex, list_to_factored_poly_otherorder, make_bigint,
    list_factored_to_factored_poly_otherorder, coeff_to_poly)
from lmfdb.galois_groups.transitive_group import transitive_group_display_knowl_C1_as_trivial
from lmfdb.lfunctions import logger
from sage.databases.cremona import cremona_letter_code
from lmfdb.abvar.fq.main import url_for_label
from lmfdb.abvar.fq.stats import AbvarFqStats

AbvarFqStatslookup = AbvarFqStats._counts()


###############################################################
# Functions for displaying numbers in correct format etc.
###############################################################

def p2sage(z):
    """Convert z to something sensible in Sage.

    This can handle objects (including strings) representing integers,
    reals, complexes (in terms of 'i' or 'I'), polynomials in 'a' with
    integer coefficients, or lists of the above.
    """
    if isinstance(z, (list, tuple)):
        return [p2sage(t) for t in z]

    Qa = PolynomialRing(RationalField(), "a")
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
    if z != '??':
        logger.error(f'Error converting "{z}" in p2sage')
    return z


def string2number(s):
    # a start to replace p2sage (used for the parameters in the FE)
    strs = str(s).replace(' ', '')
    try:
        if 'e' in strs:
            # check for e(m/n) := exp(2*pi*i*m/n), used by Dirichlet characters, for example
            r = re.match(r'^\$?e\\left\(\\frac\{(?P<num>\d+)\}\{(?P<den>\d+)\}\\right\)\$?$', strs)
            if not r:
                r = re.match(r'^e\((?P<num>\d+)/(?P<den>\d+)\)$', strs)
            if r:
                q = Rational(r.groupdict()['num'])/Rational(r.groupdict()['den'])
                return CDF(exp(2*pi*I*q))
        if 'I' in strs:
            return CDF(strs)
        elif (isinstance(s, (list, tuple))) and len(s) == 2:
            return CDF(tuple(s))
        elif '/' in strs:
            return Rational(strs)
        elif strs == '0.5':  # Temporary fix because 0.5 in db for EC
            return Rational('1/2')
        elif '.' in strs:
            return float(strs)
        else:
            return Integer(strs)
    except Exception:
        return s


def styleTheSign(sign):
    ''' Returns the string to display as sign
    '''
    try:
        logger.debug(1 - sign)
        if sign == 0:
            return "unknown"
        return seriescoeff(sign, 0, "literal", "", 3)
    except Exception:
        logger.debug("no styling of sign")
        return str(sign)


def seriescoeff(coeff, index, seriescoefftype, seriestype, digits):
    # seriescoefftype can be: series, serieshtml, signed, literal, factor
    try:
        if isinstance(coeff, str):
            if coeff == "I":
                rp = 0
                ip = 1
                coeff = CDF(I)
            elif coeff == "-I":
                rp = 0
                ip = -1
                coeff = CDF(-I)
            else:
                coeff = string2number(coeff)
        if isinstance(coeff, complex):
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
    coeff_display = display_complex(rp, ip, digits, method="truncate", parenthesis=parenthesis)

    # deal with the zero case
    if coeff_display == "0":
        if seriescoefftype == "literal":
            return "0"
        else:
            return ""

    if seriescoefftype == "literal":
        return coeff_display

    if seriescoefftype == "factor":
        if coeff_display == "1":
            return ""
        elif coeff_display == "-1":
            return "-"

    # add signs and fix spacing
    if seriescoefftype in ["series", "serieshtml"]:
        if coeff_display == "1":
            coeff_display = " + "
        elif coeff_display == "-1":
            coeff_display = " - "
        # purely real or complex number that starts with -
        elif coeff_display[0] == '-':
            # add spacings around the minus
            coeff_display = coeff_display.replace('-', ' - ')
        else:
            ans += " + "
    elif seriescoefftype == 'signed' and coeff_display[0] != '-':
        # add the plus without the spaces
        ans += "+"

    ans += coeff_display

    if seriescoefftype == "serieshtml":
        ans = ans.replace('i', "<em>i</em>").replace('-', "&minus;")
        if coeff_display[-1] not in [')', ' ']:
            ans += "&middot;"
    if seriescoefftype in ["series", "serieshtml", "signed"]:
        ans += seriesvar(index, seriestype)

    return ans


def seriesvar(index, seriestype):
    if seriestype == "dirichlet":
        return r" \ " + str(index) + "^{-s}"
    if seriestype == "dirichlethtml":
        # WARNING: the following change has consequences which need
        # to be addressed! (DF and SK, July 29, 2015)
        # return(" " + str(index) + "<sup>-s</sup>")
        return str(index) + "<sup>-s</sup>"
    if seriestype == "":
        return ""
    if seriestype == "qexpansion":
        return r"\, " + "q^{" + str(index) + "}"
    if seriestype == "polynomial":
        if index == 0:
            return ""
        if index == 1:
            return 'T'
        return 'T^{' + str(index) + '}'
    return ""

def polynomial_unroll_get_gq(poly):
    if isinstance(poly[0], list):
        expanded_factor_list = []
        for tuple in poly:
            for _ in range(tuple[1]):
                expanded_factor_list.append(tuple[0])
        Lpoly = prod([coeff_to_poly(factor) for factor in expanded_factor_list])
    else:
        Lpoly = coeff_to_poly(poly)
    cdict = Lpoly.dict()
    deg = Lpoly.degree()
    g = deg//2
    lead = cdict[deg]
    q = lead.nth_root(g)
    return [Lpoly, cdict, g, q]

def Lfactor_to_label(poly):
    [Lpoly, cdict, g, q] = polynomial_unroll_get_gq(poly)

    def extended_code(c):
        if c < 0:
            return 'a' + cremona_letter_code(-c)
        return cremona_letter_code(c)
    return "%s.%s.%s" % (g, q, "_".join(extended_code(cdict.get(i, 0)) for i in range(1, g+1)))

def AbvarExists(g,q):
    return ((g,q) in AbvarFqStatslookup.keys())

def Lfactor_to_label_and_link_if_exists(poly):
    [Lpoly, cdict, g, q] = polynomial_unroll_get_gq(poly)
    label = Lfactor_to_label(poly)
    if not AbvarExists(g,q):
        return label
    return '<a href="%s">%s</a>' % (url_for_label(label), label)

def display_isogeny_label(L):
    g = L.degree // 2
    bad_primes = [factor[0] for factor in L.bad_lfactors]
    if not (L.motivic_weight == 1 and L.rational and g <= 6):
        return False
    if g <= 3:
        return True
    elif g == 4:
        return any(not(p in bad_primes) for p in [2,3,5])
    elif g == 5:
        return any(not(p in bad_primes) for p in [2,3])
    else: # g == 6
        return not (2 in bad_primes)

def lfuncDShtml(L, fmt):
    """ Returns the HTML for displaying the Dirichlet series of the L-function L.
        fmt could be any of the values: "analytic", "langlands", "abstract"
    """

    if len(L.dirichlet_coefficients) == 0:
        return r'\text{No Dirichlet coefficients supplied.}'

    numperline = 4
    maxcoeffs = 20
    if L.selfdual:
        numperline = 9
        # Actually, we want 8 per line, and one extra addition to
        # counter to ensure we add only one newline
        maxcoeffs = 30
    ans = ""
    # Changes to account for very sparse series, only count actual
    # nonzero terms to decide when to go to next line
    # This actually jumps by 2 whenever we add a newline, to ensure we
    # just add one new line
    nonzeroterms = 1
    # if fmt == "analytic" or fmt == "langlands":
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
            # need a space between spans to allow line breaks.
            # css stops a break within a span

            if nonzeroterms > maxcoeffs:
                break
            if nonzeroterms % numperline == 0:
                # ans = ans  # don't need  \cr in the html version
                nonzeroterms += 1   # This ensures we don t add more than one newline
        ans = ans + "<span class='term'> + &#8943;</span></td></tr></table>"

    elif fmt == "abstract":
        if L.Ltype() == "riemann":
            ans = r"\[\begin{aligned} \zeta(s) = \sum_{n=1}^{\infty} n^{-s} \end{aligned} \]"

        elif L.Ltype() == "dirichlet":
            ans = r"\begin{equation}\begin{aligned} L(s,\chi) = \sum_{n=1}^{\infty} \chi(n) n^{-s} \end{aligned}\end{equation}\]"
            ans = ans + r"where $\chi$ is the character modulo " + str(L.charactermodulus)
            ans = ans + ", number " + str(L.characternumber) + "."

        else:
            ans = (r"\[\begin{aligned}" + L.texname
                   + r" = \sum_{n=1}^{\infty} a(n) n^{-s} \end{aligned}\]")
    return ans


def lfuncEPtex(L, fmt):
    """
        Returns the LaTex for displaying the Euler product of the L-function L.
        fmt could be any of the values: "abstract"
    """
    from .Lfunction import Lfunction_from_db
    if (L.Ltype() in ["genus2curveQ"] or isinstance(L, Lfunction_from_db)) and fmt == "arithmetic":
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
            ans = r"\(" + L.texname_arithmetic + " = "
        else:
            ans = r"\(" + L.texname + " = "
        if L.Ltype() == "riemann":
            ans += r"\displaystyle \prod_p (1 - p^{-s})^{-1}"

        elif L.Ltype() == "dirichlet":
            ans += r"\displaystyle\prod_p (1- \chi(p) p^{-s})^{-1}"

        elif L.Ltype() == "classical modular form" and fmt == "arithmetic":
            ans += r"\prod_{p\ \mathrm{bad}} (1- a(p) p^{-s})^{-1} \prod_{p\ \mathrm{good}} (1- a(p) p^{-s} + \chi(p)p^{-2s})^{-1}"
            # FIXME, this is consistent with G2C and EC
            # but do we really want this?
            # else:
            #    ans += r"\prod_{p\ \mathrm{bad}} (1- a(p) p^{-s/2})^{-1} \prod_{p\ \mathrm{good}} (1- a(p) p^{-s/2} + \chi(p)p^{-s})^{-1}"
        elif L.Ltype() == "hilbertmodularform":
            ans += r"\displaystyle\prod_{\mathfrak{p}\ \mathrm{bad}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s})^{-1} \prod_{\mathfrak{p}\ \mathrm{good}} (1- a(\mathfrak{p}) (N\mathfrak{p})^{-s} + (N\mathfrak{p})^{-2s})^{-1}"

        elif L.Ltype() == "maass":
            if L.group == 'GL2':
                ans += r"\displaystyle\prod_{p\ \mathrm{bad}} (1- a(p) p^{-s})^{-1} \prod_{p\ \mathrm{good}} (1- a(p) p^{-s} + \chi(p)p^{-2s})^{-1}"
            elif L.group == 'GL3':
                ans += r"\displaystyle\prod_{p\ \mathrm{bad}} (1- a(p) p^{-s})^{-1}  \prod_{p\ \mathrm{good}} (1- a(p) p^{-s} + \overline{a(p)} p^{-2s} - p^{-3s})^{-1}"
            else:
                ans += (r"\prod_p \ \prod_{j=1}^{" + str(L.degree)
                        + r"} (1 - \alpha_{j,p}\,  p^{-s})^{-1}")
        elif L.Ltype() == "SymmetricPower":
            ans += lfuncEpSymPower(L)

        elif L.langlands:
            if L.degree > 1:
                if fmt == "arithmetic":
                    ans += (r"\displaystyle\prod_p \ \prod_{j=1}^{" + str(L.degree)
                            + r"} (1 - \alpha_{j,p}\,    p^{" + str(L.motivic_weight) + "/2 - s})^{-1}")
                else:
                    ans += (r"\displaystyle\prod_p \ \prod_{j=1}^{" + str(L.degree)
                            + r"} (1 - \alpha_{j,p}\,  p^{-s})^{-1}")
            else:
                ans += r"\displaystyle\prod_p \  (1 - \alpha_{p}\,  p^{-s})^{-1}"

        else:
            return "No information is available about the Euler product."
        ans += r"\)"
        return ans
    else:
        return r"No information is available about the Euler product."


def lfuncEPhtml(L, fmt):
    """
        Euler product as a formula and a table of local factors.
    """

    # Formula
    ans = r"\(L(s) = "  # r"\[L(A,s) = "
    ans += r"\displaystyle \prod_{p} F_p(p^{-s})^{-1} \)"

    # Figuring out good and bad primes
    bad_primes = [p for p, _ in L.bad_lfactors]
    good_primes = [p for p in prime_range(100) if p not in bad_primes]
    p_index = {p: i for i, p in enumerate(prime_range(100))}

    # decide if we display galois
    display_galois = True
    if L.degree <= 2 or L.degree >= 12:
        display_galois = False
    elif L.coefficient_field == "CDF":
        display_galois = False
    elif all(None in elt for elt in (L.localfactors + L.bad_lfactors)):
        display_galois = False

    def pretty_poly(poly, prec=None):
        out = "1"
        for i, elt in enumerate(poly):
            if elt is None or (i == prec and prec != len(poly) - 1):
                out += "+O(%s)" % (seriesvar(i, "polynomial"),)
                break
            elif i > 0:
                out += seriescoeff(elt, i, "series", "polynomial", 3)
        return out

    eptable = r"""<div style="max-width: 100%; overflow-x: auto;">"""
    eptable += "<table class='ntdata'>"
    eptable += "<thead>"
    eptable += "<tr class='space'><th class='weight'></th><th class='weight'>$p$</th>"
    if display_galois:
        eptable += r"<th class='weight galois'>$\Gal(F_p)$</th>"
    eptable += r"""<th class='weight' style="text-align: left;">$F_p(T)$</th>"""
    if display_isogeny_label(L):
        eptable += r"""<th class='weight' style="text-align: left; font-weight: normal;">Isogeny Class over $\mathbf{F}_p$</th>"""
    eptable += "</tr>"
    eptable += "</thead>"

    def row(trclass, goodorbad, p, poly):
        if isinstance(poly[0], list):
            galois_pretty_factors = list_factored_to_factored_poly_otherorder
        else:
            galois_pretty_factors = list_to_factored_poly_otherorder
        out = ""
        try:
            isog_class = ''
            if L.coefficient_field == "CDF" or None in poly:
                factors = r'\( %s \)' % pretty_poly(poly)
                gal_groups = [[0, 0]]
            elif not display_galois:
                factors = galois_pretty_factors(poly, galois=display_galois, p=p)
                factors = make_bigint(r'\( %s \)' % factors)
                if display_isogeny_label(L) and p not in bad_primes:
                    isog_class = Lfactor_to_label_and_link_if_exists(poly)
            else:
                factors, gal_groups = galois_pretty_factors(poly, galois=display_galois, p=p)
                factors = make_bigint(r'\( %s \)' % factors)
                if display_isogeny_label(L) and p not in bad_primes:
                    isog_class = Lfactor_to_label_and_link_if_exists(poly)
            out += "<tr" + trclass + "><td>" + goodorbad + "</td><td>" + str(p) + "</td>"
            if display_galois:
                out += "<td class='galois'>"
                if gal_groups[0] == [0, 0]:
                    pass   # do nothing, because the local factor is 1
                else:
                    out += r"$\times$".join(transitive_group_display_knowl_C1_as_trivial(f"{n}T{k}") for n, k in gal_groups)
                out += "</td>"
            out += "<td> %s </td>" % factors
            if display_isogeny_label(L):
                out += "<td> %s </td>" % isog_class
            out += "</tr>"

        except IndexError:
            out += "<tr><td></td><td>" + str(j) + "</td><td>" + "not available" + "</td></tr>" + "not available" + "</td></tr>"
        return out
    goodorbad = "bad"
    trclass = ""
    for p, lf in L.bad_lfactors:
        if p in L.localfactors_factored_dict:
            lf = L.localfactors_factored_dict[p]
        eptable += row(trclass, goodorbad, p, lf)
        goodorbad = ""
        trclass = ""
    goodorbad = "good"
    trclass = " class='first'"
    for j, good_primes in enumerate([good_primes[:9], good_primes[9:]]):
        for p in good_primes:
            if p in L.localfactors_factored_dict:
                lf = L.localfactors_factored_dict[p]
            else:
                lf = L.localfactors[p_index[p]]
            eptable += row(trclass, goodorbad, p, lf)
            goodorbad = ""
            if j == 0:
                trclass = ""
            elif j == 1:
                trclass = " class='more nodisplay'"
        else:
            if j == 0:
                trclass = " id='moreep'  class='more nodisplay'"

    eptable += r"""<tr class="less toggle"><td colspan="2"> <a onclick="show_moreless(&quot;more&quot;); return true" href="#moreep">show more</a></td>"""

    last_entry = ""
    if display_galois:
        last_entry += "<td></td>"
    last_entry += "<td></td>"
    eptable += last_entry
    eptable += "</tr>"
    eptable += r"""<tr class="more toggle nodisplay"><td colspan="2"><a onclick="show_moreless(&quot;less&quot;); return true" href="#eptable">show less</a></td>"""
    eptable += last_entry
    eptable += "</tr></table></div>"
    ans += eptable
    return ans


def lfuncEpSymPower(L):
    """ Helper function for lfuncEPtex to do the symmetric power L-functions
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
                    poly_string += r"%d\ %d^{- s}" % (poly[1], p)
                else:
                    poly_string += r"+%d\ %d^{- s}" % (poly[1], p)

            for j in range(2, len(poly)):
                if poly[j] == 0:
                    continue
                if poly[j] == 1:
                    poly_string += "%d^{-%d s}" % (p, j)
                elif poly[j] == -1:
                    poly_string += "-%d^{-%d s}" % (p, j)
                elif poly[j] < 0:
                    poly_string += r"%d \ %d^{-%d s}" % (poly[j], p, j)
                else:
                    poly_string += r"+%d\ %d^{-%d s}" % (poly[j], p, j)
            poly_string += ")^{-1}"
        ans += poly_string
    ans += r'\prod_{p \nmid %d }\prod_{j=0}^{%d} ' % (L.E.conductor(), L.m)
    ans += r'\left(1- \frac{\alpha_p^j\beta_p^{%d-j}}' % L.m
    ans += r'{p^{s}} \right)^{-1}'
    return ans


# ---------

def lfuncFEtex(L, fmt):
    """
    Return the LaTex for displaying the Functional equation of the L-function L.
    fmt could be any of the values: "analytic", "selberg"
    """
    if fmt == "arithmetic":
        mu_list = [mu - L.motivic_weight / 2 for mu in L.mu_fe]
        nu_list = [nu - L.motivic_weight / 2 for nu in L.nu_fe]
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
        ans = r"\begin{aligned}" + tex_name_s + r"=\mathstrut &"
        if L.level > 1:
            if L.level >= 10 ** 8 and not is_prime(int(L.level)):
                ans += r"\left(%s\right)^{s/2}" % latex(L.level_factored)
            else:
                ans += latex(L.level) + "^{s/2}"
            ans += r" \, "

        def munu_str(factors_list, field):
            assert field in [r"\R", r"\C"]
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
                        res += r" \, "
                    curr_exp = 1
                    res += (
                        r"\Gamma_{"
                        + field
                        + "}(s"
                        + seriescoeff(elt, 0, "signed", "", 3)
                        + ")"
                    )
            if curr_exp > 1:
                res += "^{" + str(curr_exp) + "}"
            if res != "":
                res += r" \, "
            return res

        ans += munu_str(mu_list, r"\R")
        ans += munu_str(nu_list, r"\C")
        ans += texname + r"\cr"
        ans += r"=\mathstrut & "
        if L.sign == 0:
            ans += r"\epsilon \cdot "
        else:
            ans += seriescoeff(L.sign, 0, "factor", "", 3) + r"\,"
        ans += tex_name_1ms
        if L.sign == 0 and L.degree == 1:
            ans += r"\quad (\text{with }\epsilon \text{ not computed})"
        if L.sign == 0 and L.degree > 1:
            ans += r"\quad (\text{with }\epsilon \text{ unknown})"
        ans += r"\end{aligned}"
    elif fmt == "selberg":
        ans += "(" + str(int(L.degree)) + r",\ "
        if L.level >= 10 ** 8 and not is_prime(int(L.level)):
            ans += latex(L.level_factored)
        else:
            ans += str(int(L.level))
        ans += r",\ "
        ans += "("
        # this is mostly a hack for GL2 Maass forms

        def real_digits(x):
            return len(str(x).replace(".", "").lstrip("-").lstrip("0"))

        def mu_fe_prec(x):
            if not L.algebraic:
                return real_digits(imag_part(x))
            else:
                return 3

        if L.mu_fe:
            mus = [
                display_complex(
                    CDF(mu).real(), CDF(mu).imag(), mu_fe_prec(mu), method="round"
                )
                for mu in L.mu_fe
            ]
            if len(mus) >= 6 and mus == [mus[0]] * len(mus):
                ans += "[%s]^{%d}" % (mus[0], len(mus))
            else:
                ans += ", ".join(mus)
        else:
            ans += r"\ "
        ans += ":"
        if L.nu_fe:
            if len(L.nu_fe) >= 6 and L.nu_fe == [L.nu_fe[0]] * len(L.nu_fe):
                ans += "[%s]^{%d}" % (L.nu_fe[0], len(L.nu_fe))
            else:
                ans += ", ".join(map(str, L.nu_fe))
        else:
            ans += r"\ "
        ans += r"),\ "
        ans += seriescoeff(L.sign, 0, "literal", "", 3)
        ans += ")"

    return ans


def specialValueString(L, s, sLatex, normalization="analytic"):
    ''' Returns the LaTex to display for L(s)
        Will eventually be replaced by specialValueTriple.
    '''
    if normalization == "arithmetic":
        _, tex, Lval = specialValueTriple(L, s, '', sLatex)
    else:
        tex, _, Lval = specialValueTriple(L, s, sLatex, '')
    if Lval == r"\infty":
        operator = " = "
    else:
        operator = r"\approx"
    return r"\[{0} {1} {2}\]".format(tex, operator, Lval)
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
#        return r"\[{0}=\infty\]".format(lfunction_value_tex)
#    elif val.abs() < 1e-10:
#        return r"\[{0}=0\]".format(lfunction_value_tex)
#    elif normalization == "arithmetic":
#        return(lfunction_value_tex,
#               latex(round(val.real(), number_of_decimals)
#                         + round(val.imag(), number_of_decimals) * I))
#    else:
#        return r"\[{0} \approx {1}\]".format(lfunction_value_tex,
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
    if L.fromDB:  # getattr(L, 'fromDB', False):
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
            logger.warning("a value of an L-function has been computed on the fly")

    if sLatex_arithmetic:
        lfunction_value_tex_arithmetic = L.texname_arithmetic.replace('s)', sLatex_arithmetic + ')')
    else:
        lfunction_value_tex_arithmetic = ''
    if sLatex_analytic:
        lfunction_value_tex_analytic = L.texname.replace('(s', '(' + sLatex_analytic)
    else:
        lfunction_value_tex_analytic = ''

    if isinstance(val, str):
        Lval = val
    else:
        ccval = CDF(val)
        # We must test for NaN first, since it would show as zero otherwise
        # Try "RR(NaN) < float(1e-10)" in sage -- GT
        if ccval.real().is_NaN():
            Lval = r"$\infty$"
        else:
            Lval = display_complex(ccval.real(), ccval.imag(), number_of_decimals)

    return [lfunction_value_tex_analytic, lfunction_value_tex_arithmetic, Lval]


##################################################################
# Function to help display Lvalues when scientific notation is used
##################################################################

def scientific_notation_helper(lval_string):
    return re.sub(r"[Ee](-?\d+)", r"\\times10^{\1}", lval_string)


###############################################################
# Functions for Siegel Dirichlet series
###############################################################
NN = 500
CF = ComplexField(NN)


def compute_dirichlet_series(p_list, PREC):
    ''' computes the Dirichlet series for a Lfunction_SMF2_scalar_valued
    '''
    # p_list is a list of pairs (p,y) where p is a prime and y is the list of roots of the Euler factor at x
    LL = [0] * PREC
    # create an empty list of the right size and now populate it with the powers of p
    for p, y in p_list:
        # FIXME p_prec is never used, but perhaps it should be?
        # p_prec = log(PREC) / log(p) + 1
        ep = euler_p_factor(y, PREC)
        for n in range(ep.prec()):
            if p ** n < PREC:
                LL[p ** n] = ep.coefficients()[n]
    for i in range(1, PREC):
        f = factor(i)
        if len(f) > 1:  # not a prime power
            LL[i] = prod([LL[p ** e] for p, e in f])
    return LL[1:]


def euler_p_factor(root_list, PREC):
    ''' computes the coefficients of the pth Euler factor expanded
      as a geometric series.
      ax^n is the Dirichlet series coefficient p^(-ns)
    '''
    PREC = floor(PREC)
    # return Satake_list
    R = PowerSeriesRing(CF, 'x', default_prec=PREC + 1)
    # TODO: This could use the lazy power series ring.
    x = R.gen()
    return ~R.prod([1 - a * x for a in root_list])


def compute_local_roots_SMF2_scalar_valued(K, ev, k, embedding):
    ''' computes the Dirichlet series for a Lfunction_SMF2_scalar_valued
    '''
    L = ev.keys()
    m = ZZ(max(L)).isqrt() + 1
    ev2 = {}
    for p in primes(m):
        try:
            ev2[p] = (ev[p], ev[p * p])
        except KeyError:
            break

    logger.debug(str(ev2))
    ret = []
    for p, (cp, cp2) in ev2.items():
        R = PolynomialRing(K, 'x')
        x = R.gen()
        f = (1 - cp * x + (cp**2 - cp2 - p**(2 * k - 4)) * x**2
             - cp * p**(2 * k - 3) * x**3 + p**(4 * k - 6) * x**4)

        Rnum = PolynomialRing(CF, 'y')
        x = Rnum.gen()
        fnum = Rnum.zero()
        if K != QQ:
            for i in range(int(f.degree()) + 1):
                fnum += f[i].complex_embeddings(NN)[embedding] * (x / p**(k - 1.5)) ** i
        else:
            for i in range(int(f.degree()) + 1):
                fnum += f[i] * (x / CF(p**(k - 1.5)))**i

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
    """ Computes the sign of a EMF with given level, weight and
        coefficients numerically by computing the value of the EMF
        at two points related by the Atkin-Lehner involution.
        If the absolute value of the result is more than tol from 1
        then it returns "Not able to compute" which indicates to few
        (or wrong) coefficients.
        The parameter num chooses the related points and shouldn't be 1.
    """
    sum1 = 0
    sum2 = 0
    exponent = - 2 * math.pi / math.sqrt(level)
    for i in range(1, len(coefs)):
        sum1 += coefs[i - 1] * math.exp(exponent * i * num)
        logger.debug("Sum1: {0}".format(sum1))
        sum2 += (coefs[i - 1].conjugate() * math.exp(exponent * i / num)
                 / num ** weight)
        logger.debug("Sum2: {0}".format(sum2))
    sign = sum1 / sum2
    if abs(abs(sign) - 1) > tol:
        logger.critical("Not enough coefficients to compute the sign of the L-function.")
        sign = "Not able to compute."
        sign = 1  # wrong, but we need some type of error handling here.
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
            # LMFDB label
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

    except Exception:
        return None, None


def get_bread(breads=[]):
    """
    Returns the top level of bread crumbs plus the ones supplied in breads.
    """
    bread = [('L-functions', url_for('.index'))]
    bread.extend(breads)
    return bread


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
