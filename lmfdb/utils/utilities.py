# -*- encoding: utf-8 -*-
# this is the caching wrapper, use it like this:
# @app.route(....)
# @cached()
# def func(): ...

import cmath
import math
import datetime
import os
import random
import re
import tempfile
import time
from collections import defaultdict
from copy import copy
from functools import wraps
from itertools import islice
from types import GeneratorType
from urllib import urlencode

from flask import request, make_response, flash, url_for, current_app
from markupsafe import Markup
from werkzeug.contrib.cache import SimpleCache
from werkzeug import cached_property
from sage.all import CC, CBF, CDF, Factorization, NumberField, PolynomialRing, PowerSeriesRing, RealField, RR, RIF, ZZ, QQ, latex, valuation, prime_range, floor
from sage.structure.element import Element

from lmfdb.app import app, is_beta, is_debug_mode, _url_source

def list_to_factored_poly_otherorder(s, galois=False, vari = 'T', p = None):
    """
        Either return the polynomial in a nice factored form,
        or return a pair, with first entry the factored polynomial
        and the second entry a list describing the Galois groups
        of the factors.
        vari allows to choose the variable of the polynomial to be returned.
    """
    if len(s) == 1:
        if galois:
            return [str(s[0]), [[0,0]]]
        return str(s[0])
    ZZT = PolynomialRing(ZZ, vari)
    sfacts = ZZT(s).factor()
    sfacts_fc = [[g, e] for g, e in sfacts]
    if sfacts.unit() == -1:
        sfacts_fc[0][0] *= -1
    # if the factor is -1+T^2, replace it by 1-T^2
    # this should happen an even number of times, mod powers
    sfacts_fc_list = [[(-g).list() if g[0] == -1 else g.list(), e] for g, e in sfacts_fc]
    return list_factored_to_factored_poly_otherorder(sfacts_fc_list, galois, vari, p)

def list_factored_to_factored_poly_otherorder(sfacts_fc_list, galois=False, vari = 'T', p = None):
    """
        Either return the polynomial in a nice factored form,
        or return a pair, with first entry the factored polynomial
        and the second entry a list describing the Galois groups
        of the factors.
        vari allows to choose the variable of the polynomial to be returned.
    """
    gal_list=[]
    ZZpT  = PolynomialRing(ZZ, ['p',vari], order = 'negdeglex')
    ZZT = PolynomialRing(ZZ, vari)
    outstr = ''
    for g, e in sfacts_fc_list:
        if galois:
            # hack because currently sage only handles monic polynomials:
            this_poly = ZZT(list(reversed(g)))
            this_degree = this_poly.degree()
            this_number_field = NumberField(this_poly, "a")
            this_gal = this_number_field.galois_group(type='pari')
            this_t_number = this_gal.group().__pari__()[2].sage()
            gal_list.append([this_degree, this_t_number])

        # casting from ZZT -> ZZpT
        if p is None:
            gtoprint = dict( zip( zip( [0]*len(g), range(len(g))), g) )
        else:
            gtoprint = {}
            for i, elt in enumerate(g):
                if elt != 0:
                    val =  ZZ(elt).valuation(p)
                    gtoprint[(val, i)] = elt/p**val
        glatex = latex(ZZpT(gtoprint))
        if  e > 1:
            outstr += '( %s )^{%d}' % (glatex, e)
        elif len(sfacts_fc_list) > 1:
            outstr += '( %s )' % (glatex,)
        else:
            outstr += glatex

    if galois:
        # 2 factors of degree 2
        if len(sfacts_fc_list)==2:
            if len(sfacts_fc_list[0][0]) == 3 and len(sfacts_fc_list[1][0]) == 3:
                troubletest = ZZT(sfacts_fc_list[0][0]).disc()*ZZT(sfacts_fc_list[1][0]).disc()
                if troubletest.is_square():
                    gal_list=[[2,1]]
        return outstr, gal_list
    return outstr

################################################################################
#   number utilities
################################################################################

def try_int(foo):
    try:
        return int(foo)
    except Exception:
        return foo

def key_for_numerically_sort(elt, split="[\s\.\-]"):
    return map(try_int, re.split(split, elt))

def an_list(euler_factor_polynomial_fn,
            upperbound=100000, base_field=QQ):
    """
    Takes a fn that gives for each prime the Euler polynomial of the associated
    with the prime, given as a list, with independent coefficient first. This
    list is of length the degree+1.
    Output the first `upperbound` coefficients built from the Euler polys.

    Example:
    The `euler_factor_polynomial_fn` should in practice come from an L-function
    or data. For a simple example, we construct just the 2 and 3 factors of the
    Riemann zeta function, which have Euler factors (1 - 1*2^(-s))^(-1) and
    (1 - 1*3^(-s))^(-1).
    >>> euler = lambda p: [1, -1] if p <= 3 else [1, 0]
    >>> an_list(euler)[:20]
    [1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0]
    """
    from math import ceil, log
    PP = PowerSeriesRing(base_field, 'x', 1 + ceil(log(upperbound) / log(2.)))

    prime_l = prime_range(upperbound + 1)
    result = [1 for i in range(upperbound)]
    for p in prime_l:
        euler_factor = (1 / (PP(euler_factor_polynomial_fn(p)))).padded_list()
        if len(euler_factor) == 1:
            for j in range(1, 1 + upperbound // p):
                result[j * p - 1] = 0
            continue

        k = 1
        while True:
            if p ** k > upperbound:
                break
            for j in range(1, 1 + upperbound // (p ** k)):
                if j % p == 0:
                    continue
                result[j * p ** k - 1] *= euler_factor[k]
            k += 1
    return result

def coeff_to_poly(c, var='x'):
    """
    Convert a list or string representation of a polynomial to a sage polynomial.

    Examples:
    >>> coeff_to_poly("1 - 3x + x^2")
    x**2 - 3*x + 1
    >>> coeff_to_poly("1 - 3*x + x**2")
    x**2 - 3*x + 1
    """
    return PolynomialRing(QQ, var)(c)

def coeff_to_power_series(c, var='q', prec=None):
    """
    Convert a list or dictionary giving coefficients to a sage power series.
    """
    return PowerSeriesRing(QQ, var)(c, prec)

def display_multiset(mset, formatter=str, *args):
    """
    Input mset is a list of pairs [item, multiplicity]
    Return a string for display of the multi-set.  The
    function formatter is a function whose first argument
    is the item, and *args are the other arguments
    and is applied to each item.

    Example:
    >>> display_multiset([["a", 5], [1, 3], ["cat", 2]])
    'a x5, 1 x3, cat x2'
    """
    return ', '.join([formatter(pair[0], *args)+(' x%d'% pair[1] if pair[1]>1 else '') for pair in mset])


def pair2complex(pair):
    """
    Converts a string of two white-space delimited numbers to a
    list representation of a complex number.

    Examples:
    >>> pair2complex("1 2")
    [1.0, 2.0]
    >>> pair2complex("-1.5 3")
    [-1.5, 3.0]
    """
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
    return [float(rp), float(ip)]

def round_RBF_to_half_int(x):
    x = RIF(x)
    try:
        k = x.unique_round()
        if (x - k).contains_zero():
            return int(k)
    except ValueError:
        pass
    try:
        k = (2*x).unique_round()
        if (2*x - k).contains_zero():
            return float(k)/2
    except ValueError:
        pass
    try:
        return float(x)
    except TypeError: # old version of Sage
        return float(x.n(x.prec()))

def round_CBF_to_half_int(x):
    return CDF(tuple(map(round_RBF_to_half_int, [x.real(), x.imag()])))

def str_to_CBF(s):
    # in sage 8.2 or earlier this is equivalent to CBF(s)
    s = str(s) # to convert from unicode
    try:
        return CBF(s)
    except TypeError:
        sign = 1
        s = s.lstrip('+')
        if '+' in s:
            a, b = s.rsplit('+', 1)
        elif '-' in s:
            a, b = s.rsplit('-',1)
            sign = -1
        else:
            a = ''
            b = s
        a = a.lstrip(' ')
        b = b.lstrip(' ')
        if 'I' in a:
            b, a = a, b
        assert 'I' in b or b == ''
        if b == 'I':
            b = '1'
        else:
            b = b.rstrip(' ').rstrip('I').rstrip('*')
        
        res = CBF(0)
        if a:
            res += CBF(a)
        if b:
            res  +=  sign * CBF(b)* CBF.gens()[0]
        return res



def to_dict(args, exclude = []):
    r"""
    Input a dictionary `args` whose values may be lists.
    Output a dictionary whose values are not lists, by choosing the last
    element in a list if the input was a list.

    Example:
    >>> to_dict({"not_list": 1, "is_list":[2,3,4]})
    {'is_list': 4, 'not_list': 1}
    """
    d = {}
    for key in args:
        values = args[key]
        if isinstance(values, list) and key not in exclude:
            if values:
                d[key] = values[-1]
        elif values:
            d[key] = values
    return d

def is_exact(x):
    return (type(x) in [int, long]) or (isinstance(x, Element) and x.parent().is_exact())

def display_float(x, digits, method = "truncate",
                             extra_truncation_digits=3,
                             try_halfinteger=True):
    if abs(x) < 10.**(- digits - extra_truncation_digits):
        return "0"
    # if small, try to display it as an exact or half integer
    if try_halfinteger and abs(x) < 10.**digits:
        if is_exact(x):
            s = str(x)
            if len(s) < digits + 2: # 2 = '/' + '-'
                return str(x)
        k = round_to_half_int(x)
        if k == x :
            k2 = None
            try:
                k2 = ZZ(2*x)
            except TypeError:
                pass
            # the second statment checks for overflow
            if k2 == 2*x and (2*x + 1) - k2 == 1:
                if k2 % 2 == 0:
                    s = '%s' % (k2/2)
                else:
                    s = '%s' % (float(k2)/2)
                return s
    if method == 'truncate':
        rnd = 'RNDZ'
    else:
        rnd = 'RNDN'
    no_sci = 'e' not in "%.{}g".format(digits) % float(x)
    try:
        s = RealField(max(53,4*digits),  rnd=rnd)(x).str(digits=digits, no_sci=no_sci)
    except TypeError:
        # older versions of Sage don't support the digits keyword
        s = RealField(max(53,4*digits),  rnd=rnd)(x).str(no_sci=no_sci)
        point = s.find('.')
        if point != -1:
            if point < digits:
                s = s[:digits+1]
            else:
                s = s[:point]
    return s

def display_complex(x, y, digits, method = "truncate",
                                  parenthesis = False,
                                  extra_truncation_digits=3,
                                  try_halfinteger=True):
    """
    Examples:
    >>> display_complex(1.0001, 0, 3, parenthesis = True)
    '1.000'
    >>> display_complex(1.0, -1, 3, parenthesis = True)
    '(1 - i)'
    >>> display_complex(0, -1, 3, parenthesis = True)
    '-i'
    >>> display_complex(0, 1, 3, parenthesis = True)
    'i'
    >>> display_complex(0.49999, -1.001, 3, parenthesis = True)
    '(0.500 - 1.000i)'
    >>> display_complex(0.02586558415542463,0.9996654298095432, 3)
    '0.025 + 0.999i
    >>> display_complex(0.00049999, -1.12345, 3, parenthesis = False, extra_truncation_digits = 3)
    '0.000 - 1.123i'
    >>> display_complex(0.00049999, -1.12345, 3, parenthesis = False, extra_truncation_digits = 2)
    '0.000 - 1.123i'
    >>> display_complex(0.00049999, -1.12345, 3, parenthesis = False, extra_truncation_digits = 1)
    '-1.123i'
    """
    if abs(y) < 10.**(- digits - extra_truncation_digits):
        return display_float(x, digits,
                method=method,
                extra_truncation_digits=extra_truncation_digits,
                try_halfinteger=try_halfinteger)

    if abs(x) < 10.**(- digits - extra_truncation_digits):
        x = ""
    else:
        x = display_float(x, digits,
                method=method,
                extra_truncation_digits=extra_truncation_digits,
                try_halfinteger=try_halfinteger)
    if y < 0:
        y = -y
        if x == "":
            sign = "-"
        else:
            sign = " - "
    else:
        if x == "":
            sign = ""
        else:
            sign = " + "
    y = display_float(y, digits, method = method,
                                 extra_truncation_digits = extra_truncation_digits,
                                 try_halfinteger=try_halfinteger)
    if y == "1":
        y = ""
    if len(y) > 0 and y[-1] == '.':
        y += ' '
    res = x + sign + y + r"i"
    if parenthesis and x != "":
        res = "(" + res + ")"
    return res

def round_to_half_int(num, fraction=2):
    """
    Rounds input `num` to the nearest half-integer. The optional kwarg
    `fraction` is used to round to the nearest `fraction`-part of an integer.

    Examples:
    >>> round_to_half_int(1.1)
    1
    >>> round_to_half_int(-0.9)
    -1
    >>> round_to_half_int(0.5)
    1/2
    """
    return round(num * 1.0 * fraction) / fraction

def splitcoeff(coeff):
    """
    Return a list of list-represented complex numbers given a string of the
    form "r0 i0 \n r1 i1 \n r2 i2", where r0 is the real part of the 0th number
    and i0 is the imaginary part of the 0th number, and so on.

    Example:
    >>> splitcoeff("1 1 \n -1 2")
    [[1.0, 1.0], [-1.0, 2.0]]
    """
    local = coeff.split("\n")
    answer = []
    for s in local:
        if s:
            answer.append(pair2complex(s))
    return answer



################################################################################
#  display and formatting utilities
################################################################################

def comma(x):
    """
    Input is an integer. Output is a string of that integer with commas.
    CAUTION: this misbehaves if the input is not an integer.

    Example:
    >>> comma("12345")
    '12,345'
    """
    return x < 1000 and str(x) or ('%s,%03d' % (comma(x // 1000), (x % 1000)))


def format_percentage(num, denom):
    if denom == 0:
        return 'NaN'
    return "%10.2f"%((100.0*num)/denom)


def signtocolour(sign):
    """
    Assigns an rgb string colour to a complex number based on its argument.
    """
    argument = cmath.phase(CC(str(sign)))
    r = int(255.0 * (math.cos((1.0 * math.pi / 3.0) - (argument / 2.0))) ** 2)
    g = int(255.0 * (math.cos((2.0 * math.pi / 3.0) - (argument / 2.0))) ** 2)
    b = int(255.0 * (math.cos(argument / 2.0)) ** 2)
    return("rgb(" + str(r) + "," + str(g) + "," + str(b) + ")")


def rgbtohex(rgb):
    """
    Converts an rgb string color representation into a hex string color
    representation. For example, this converts rgb(63,255,100) to #3fff64
    """
    r,g,b = rgb[4:-1].split(',')
    r = int(r)
    g = int(g)
    b = int(b)
    return "#{:02x}{:02x}{:02x}".format(r,g,b)

def pol_to_html(p):
    r"""
    Convert polynomial p with variable x to html.

    Example:
    >>> pol_to_html("x^2 + 2*x + 1")
    '<i>x</i><sup>2</sup> + 2<i>x</i> + 1'
    """
    s = str(p)
    s = re.sub("\^(\d*)", "<sup>\\1</sup>", s)
    s = re.sub("\_(\d*)", "<sub>\\1</sub>", s)
    s = re.sub("\*", "", s)
    s = re.sub("x", "<i>x</i>", s)
    return s



################################################################################
#  latex/math rendering utilities
################################################################################

def web_latex(x, enclose=True):
    """
    Convert input to latex string unless it's a string or unicode. The key word
    argument `enclose` indicates whether to surround the string with
    `\(` and `\)` to tag it as an equation in html.

    Note:
    if input is a factored ideal, use web_latex_ideal_fact instead.

    Example:
    >>> x = var('x')
    >>> web_latex(x**23 + 2*x + 1)
    '\\( x^{23} + 2 \\, x + 1 \\)'
    """
    if isinstance(x, (str, unicode)):
        return x
    if enclose == True:
        return "\( %s \)" % latex(x)
    return " %s " % latex(x)


def web_latex_ideal_fact(x, enclose=True):
    """
    Convert input factored ideal to latex string.  The key word argument
    `enclose` indicates whether to surround the string with `\(` and
    `\)` to tag it as an equation in html.

    sage puts many parentheses around latex representations of factored ideals.
    This function removes excessive parentheses.

    Example:
    >>> x = var('x')
    >>> K = NumberField(x**2 - 5, 'a')
    >>> a = K.gen()
    >>> I = K.ideal(2/(5+a)).factor()
    >>> print(latex(I))
    (\left(-a\right))^{-1}
    >>> web_latex_ideal_fact(I)
    '\\( \\left(-a\\right)^{-1} \\)'
    """
    y = web_latex(x, enclose=enclose)
    y = y.replace("(\\left(","\\left(")
    y = y.replace("\\right))","\\right)")
    return y


def web_latex_split_on(x, on=['+', '-']):
    """
    Convert input into a latex string. A different latex surround `\(` `\)` is
    used, with splits occuring at `on` (+ - by default).

    Example:
    >>> x = var('x')
    >>> web_latex_split_on(x**2 + 1)
    '\\( x^{2} \\) + \\(  1 \\)'
    """
    if isinstance(x, (str, unicode)):
        return x
    else:
        A = "\( %s \)" % latex(x)
        for s in on:
            A = A.replace(s, '\) ' + s + ' \( ')
    return A


# web_latex_split_on was not splitting polynomials, so we make an expanded version
def web_latex_split_on_pm(x):
    """
    Convert input into a latex string, with specific handling of expressions
    including `+` and `-`.

    Example:
    >>> x = var('x')
    >>> web_latex_split_on_pm(x**2 + 1)
    '\\(x^{2} \\) \\(\\mathstrut +\\mathstrut  1 \\)'
    """
    on = ['+', '-']
 #   A = "\( %s \)" % latex(x)
    try:
        A = "\(" + x + "\)"  # assume we are given LaTeX to split on
    except:
        A = "\( %s \)" % latex(x)

       # need a more clever split_on_pm that inserts left and right properly
    A = A.replace("\\left","")
    A = A.replace("\\right","")
    for s in on:
  #      A = A.replace(s, '\) ' + s + ' \( ')
   #     A = A.replace(s, '\) ' + ' \( \mathstrut ' + s )
        A = A.replace(s, '\)' + ' \(\mathstrut ' + s + '\mathstrut ')
    # the above will be re-done using a more sophisticated method involving
    # regular expressions.  Below fixes bad spacing when the current approach
    # encounters terms like (-3+x)
    for s in on:
        A = A.replace('(\) \(\mathstrut '+s,'(' + s)
    A = A.replace('( {}','(')
    A = A.replace('(\) \(','(')
    A = A.replace('\(+','\(\mathstrut+')
    A = A.replace('\(-','\(\mathstrut-')
    A = A.replace('(  ','(')
    A = A.replace('( ','(')

    return A
    # return web_latex_split_on(x)

def web_latex_split_on_re(x, r = '(q[^+-]*[+-])'):
    """
    Convert input into a latex string, with splits into separate latex strings
    occurring on given regex `r`.
    CAUTION: this gives a different result than web_latex_split_on_pm

    Example:
    >>> x = var('x')
    >>> web_latex_split_on_re(x**2 + 1)
    '\\(x^{2} \\) \\(\\mathstrut+  1 \\)'
    """

    def insert_latex(s):
        return s.group(1) + '\) \('

    if isinstance(x, (str, unicode)):
        return x
    else:
        A = "\( %s \)" % latex(x)
        c = re.compile(r)
        A = A.replace('+', '\) \( {}+ ')
        A = A.replace('-', '\) \( {}- ')
#        A = A.replace('\left(','\left( {}\\right.') # parantheses needs to be balanced
#        A = A.replace('\\right)','\left.\\right)')
        A = A.replace('\left(','\\bigl(')
        A = A.replace('\\right)','\\bigr)')
        A = c.sub(insert_latex, A)

    # the above will be re-done using a more sophisticated method involving
    # regular expressions.  Below fixes bad spacing when the current approach
    # encounters terms like (-3+x)
    A = A.replace('( {}','(')
    A = A.replace('(\) \(','(')
    A = A.replace('\(+','\(\mathstrut+')
    A = A.replace('\(-','\(\mathstrut-')
    A = A.replace('(  ','(')
    A = A.replace('( ','(')
    A = A.replace('+\) \(O','+O')
    return A

def display_knowl(kid, title=None, kwargs={}):
    """
    Allows for the construction of knowls from python code
    (to be displayed using the ``safe`` flag in jinja);
    the only difference with the KNOWL macro is that
    there will be no edit link for authenticated users.
    """
    from lmfdb.knowledge.knowl import knowl_title
    ktitle = knowl_title(kid)
    if ktitle is None:
        # Knowl not found
        if title is None:
            return """<span class="knowl knowl-error">'%s'</span>""" % kid
        else:
            return title
    else:
        if title is None:
            if len(ktitle) == 0:
                title = kid
            else:
                title = ktitle
        if len(title) > 0:
            return '<a title="{0} [{1}]" knowl="{1}" kwargs="{2}">{3}</a>'.format(ktitle, kid, urlencode(kwargs), title)
        else:
            return ''

def bigint_knowl(n, cutoff=20, max_width=70, sides=2):
    if abs(n) >= 10**cutoff:
        short = str(n)
        short = short[:sides] + r'\!\cdots\!' + short[-sides:]
        lng = str(n)
        if len(lng) > max_width:
            lines = 1 + (len(lng)-1) // (max_width-1)
            width = 1 + (len(lng)-1) // lines
            lng = [lng[i:i+width] for i in range(0,len(lng),width)]
            for i in range(len(lng)-1):
                lng[i] = r"<tr><td>%s\</td></tr>" % lng[i]
            lng[-1] = r"<tr><td>%s</td></tr>" % lng[-1]
            lng = "<table>" + "".join(lng) + "</table>"
        else:
            lng = r"\(%s\)" % lng
        return r'<a title="[bigint]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(lng, short)
    else:
        return r'\(%s\)'%n
def too_big(L, threshold):
    r"""
    INPUT:

    - ``L`` -- nested lists of integers
    - ``threshold`` -- an integer

    OUTPUT:

    Whether any integer in ``L`` is at least ``threshold``
    """
    if isinstance(L, (list, tuple)):
        return any(too_big(x, threshold) for x in L)
    return L >= threshold

def make_bigint(s, cutoff=20, max_width=70):
    r"""
    INPUT:

    - ``s`` -- A string, the latex representation of an integer or polynomial.
      It should include outer \( and \).
    - ``cutoff`` -- an integer

    OUTPUT:

    The string ``s`` with integers at least 10^cutoff replaced by bigint_knowls.
    """
    Zmatcher = re.compile(r'([0-9]{%s,})' % (cutoff+1))
    def knowl_replacer(M):
        return r'\)' + bigint_knowl(int(M.group(1)), cutoff, max_width=max_width) + r'\('
    return Zmatcher.sub(knowl_replacer, s)


def bigpoly_knowl(f, nterms_cutoff=8, bigint_cutoff=12, var='x'):
    lng = web_latex_split_on_pm(coeff_to_poly(f, var))
    if bigint_cutoff:
        lng = make_bigint(lng, bigint_cutoff, max_width=70).replace('"',"'")
    if len([c for c in f if c != 0]) > nterms_cutoff:
        short = "%s^{%s}" % (latex(coeff_to_poly([0,1], var)), len(f) - 1)
        i = len(f) - 2
        while i >= 0 and f[i] == 0:
            i -= 1
        if i >= 0: # nonzero terms
            if f[i] > 0:
                short += r" + \cdots"
            else:
                short += r" - \cdots"
        return r'<a title="[poly]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(lng, short)
    else:
        return lng

def factor_base_factor(n, fb):
    return [[p, valuation(n,p)] for p in fb]

def factor_base_factorization_latex(fbf):
    if len(fbf) == 0:
        return '1'
    ans = ''
    sign = 1
    for p, e in fbf:
        if p == -1:
            if (e % 2) == 1:
                sign *= -1
        elif e == 1:
            ans += r'\cdot %d' % p
        elif e != 0:
            ans += r'\cdot %d^{%d}' % (p, e)
    # get rid of the initial '\cdot '
    ans = ans[6:]
    return '- ' + ans if sign == -1 else ans



def polyquo_knowl(f, disc=None, unit=1, cutoff=None):
    quo = "x^{%s}" % (len(f) - 1)
    i = len(f) - 2
    while i >= 0 and f[i] == 0:
        i -= 1
    if i >= 0: # nonzero terms
        if f[i] > 0:
            quo += r" + \cdots"
        else:
            quo += r" - \cdots"
    short = r'\mathbb{Q}[x]/(%s)'%(quo)
    long = r'Defining polynomial: %s' % (web_latex_split_on_pm(coeff_to_poly(f)))
    if cutoff:
        long = make_bigint(long, cutoff, max_width=70).replace('"',"'")
    if disc is not None:
        if isinstance(disc, list):
            long += '\n<br>\nDiscriminant: \\(%s\\)' % (factor_base_factorization_latex(disc))
        else:
            long += '\n<br>\nDiscriminant: \\(%s\\)' % (Factorization(disc, unit=unit)._latex_())
    return r'<a title="[poly]" knowl="dynamic_show" kwargs="%s">\(%s\)</a>'%(long, short)

def code_snippet_knowl(D, full=True):
    r"""
    INPUT:

    - ``D`` -- a dictionary with the following keys
      - ``filename`` -- a filename within the lmfdb repository
      - ``code`` -- a list of code lines (without trailing \n)
      - ``lines`` -- (optional) a list of line numbers
    - ``full`` -- if False, display only the filename rather than the full path.
    """
    filename = D['filename']
    code = D['code']
    lines = D.get('lines')
    code = '\n'.join(code).replace('<','&lt;').replace('>','&gt;').replace('"', '&quot;')
    if is_debug_mode():
        branch = "master"
    elif is_beta():
        branch = "dev"
    else:
        branch = "web"
    url = "%s%s/%s" % (_url_source, branch, filename)
    link_text = "%s on Github" % (filename)
    if not full:
        filename = filename.split('/')[-1]
    if lines:
        if len(lines) == 1:
            label = '%s (line %s)' % (filename, lines[0])
        else:
            lines = sorted(lines)
            label = '%s (lines %s-%s)' % (filename, lines[0], lines[-1])
        url += "#L%s" % lines[0]
    else:
        label = filename
    inner = u"<div>\n<pre></pre>\n</div>\n<div align='right'><a href='%s' target='_blank'>%s</a></div>"
    inner = inner % (url, link_text)
    return ur'<a title="[code]" knowl="dynamic_show" pretext="%s" kwargs="%s">%s</a>'%(code, inner, label)

def web_latex_poly(coeffs, var='x', superscript=True, bigint_cutoff=20,  bigint_overallmin=400):
    """
    Generate a web latex string for a given integral polynomial, or a linear combination
    (using subscripts instead of exponents).  In either case, the constant term is printed
    without a variable and bigint knowls are used if the coefficients are large enough.

    INPUT:

    - ``coeffs`` -- a list of integers
    - ``var`` -- a variable name
    - ``superscript`` -- whether to use superscripts (as opposed to subscripts)
    - ``bigint_cutoff`` -- the string length above which a knowl is used for a coefficient
    - ``bigint_overallmin`` -- the number of characters by which we would need to reduce the output to replace the large ints by knowls
    """
    plus = r"\mathstrut +\mathstrut \) "
    minus = r"\mathstrut -\mathstrut \) "
    m = len(coeffs)
    while m and coeffs[m-1] == 0:
        m -= 1
    if m == 0:
        return r"\(0\)"
    s = ""
    # we will have under/overflows if we try to use floats
    def cutout_digits(elt):
        digits = 1 if elt == 0 else floor(RR(abs(elt)).log(10)) + 1
        if digits > bigint_cutoff:
            # a large number would be replaced by ab...cd
            return digits - 7
        else:
            return 0

    if sum(cutout_digits(elt) for elt in coeffs) < bigint_overallmin:
        # this effectively disables the bigint
        bigint_cutoff = bigint_overallmin + 7

    for n in reversed(xrange(m)):
        c = coeffs[n]
        if n == 1:
            if superscript:
                varpow = r"\(" + var
            else:
                varpow = r"\(%s_{1}"%var
        elif n > 1:
            if superscript:
                varpow = r"\(%s^{%s}"%(var, n)
            else:
                varpow = r"\(%s_{%s}"%(var, n)
        else:
            if c > 0:
                s += plus + bigint_knowl(c, bigint_cutoff)
            elif c < 0:
                s += minus + bigint_knowl(-c, bigint_cutoff)
            break
        if c > 0:
            s += plus
        elif c < 0:
            s += minus
        else:
            continue
        if abs(c) != 1:
            s += bigint_knowl(abs(c), bigint_cutoff) + " "
        s += varpow
    if coeffs[0] == 0:
        s += r"\)"
    if s.startswith(plus):
        return s[len(plus):]
    else:
        return r"\(-\)" + s[len(minus):]

# make latex matrix from list of lists
def list_to_latex_matrix(li):
    """
    Given a list of lists representing a matrix, output a latex representation
    of that matrix as a string.

    Example:
    >>> list_to_latex_matrix([[1,0],[0,1]])
    '\\left(\\begin{array}{rr}1 & 0\\\\0 & 1\\end{array}\\right)'
    """
    dim = len(li[0])
    mm = r"\left(\begin{array}{"+dim*"r" +"}"
    mm += r"\\".join([" & ".join([str(a) for a in row]) for row in li])
    mm += r'\end{array}\right)'
    return mm

################################################################################
#  pagination utilities
################################################################################

class ValueSaver(object):
    """
    Takes a generator and saves values as they are generated so that values can be retrieved multiple times.
    """
    def __init__(self, source):
        self.source = source
        self.store = []
    def fill(self, stop):
        """
        Consumes values from the source until there are at least ``stop`` entries in the store.
        """
        if stop > len(self.store):
            self.store.extend(islice(self.source, stop - len(self.store)))
    def __getitem__(self, i):
        if isinstance(i, slice):
            if (i.start is not None and i.start < 0) or i.stop is None or i.stop < 0 or (i.step is not None and i.step < 0):
                raise ValueError("Only positive indexes supported")
            self.fill(i.stop)
            return self.store[i]
        else:
            self.fill(i+1)
            return self.store[i]
    def __len__(self):
        raise TypeError("Unknown length")

class Pagination(object):
    """
    INPUT:

    - ``source`` -- a list or generator containing results.
        If a generator, won't support the ``count`` or ``pages`` attributes
    - ``per_page`` -- an integer, the number of results shown per page
    - ``page`` -- the current page (initial value is 1)
    - ``endpoint`` -- an argument for ``url_for`` to get more pages
    - ``endpoint_params`` -- keyword arguments for the ``url_for`` call
    """
    def __init__(self, source, per_page, page, endpoint, endpoint_params):
        if isinstance(source, GeneratorType):
            source = ValueSaver(source)
        self.source = source
        self.per_page = int(per_page)
        self.page = int(page)
        self.endpoint = endpoint
        self.endpoint_params = endpoint_params

    @cached_property
    def count(self):
        return len(self.source)

    @cached_property
    def entries(self):
        return self.source[self.start : self.start+self.per_page]

    @cached_property
    def has_next(self):
        try:
            self.source[self.start + self.per_page]
        except IndexError:
            return False
        else:
            return True

    has_previous = property(lambda x: x.page > 1)
    pages = property(lambda x: max(0, x.count - 1) // x.per_page + 1)
    start = property(lambda x: (x.page - 1) * x.per_page)
    end = property(lambda x: min(x.start + x.per_page - 1, x.count - 1))

    @property
    def end(self):
        if isinstance(self.source, ValueSaver):
            self.source.fill(self.start + self.per_page)
            return len(self.source.store) - 1
        else:
            return min(self.start + self.per_page, self.count) - 1

    @property
    def previous(self):
        kwds = copy(self.endpoint_params)
        kwds['page'] = self.page - 1
        return url_for(self.endpoint, **kwds)

    @property
    def next(self):
        kwds = copy(self.endpoint_params)
        kwds['page'] = self.page + 1
        return url_for(self.endpoint, **kwds)

################################################################################
#  web development utilities
################################################################################

def debug():
    """
    this triggers the debug environment on purpose. you have to start
    the server via website.py --debug
    don't forget to remove the debug() from your code!!!
    """
    assert current_app.debug is False, "Don't panic! You're here by request of debug()"


def flash_error(errmsg, *args):
    """ flash errmsg in red with args in black; errmsg may contain markup, including latex math mode"""
    flash(Markup("Error: %s"%(errmsg%tuple(map(lambda x: "<span style='color:black'>%s</span>"%x, args)))),"error")


cache = SimpleCache()
def cached(timeout=15 * 60, key='cache::%s::%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key % (request.path, request.args)
            rv = cache.get(cache_key)
            if rv is None:
                rv = f(*args, **kwargs)
                cache.set(cache_key, rv, timeout=timeout)
            ret = make_response(rv)
            # this header basically says that any cache can store this infinitely long
            # set this down to 600, because we have pagespeed now (hsy)
            ret.headers['Cache-Control'] = 'max-age=600, public'
            return ret
        return decorated_function
    return decorator

################################################################################
#  Ajax utilities
################################################################################

# LinkedList is used in Ajax below
class LinkedList(object):
    __slots__ = ('value', 'next', 'timestamp')

    def __init__(self, value, next):
        self.value = value
        self.next = next
        self.timestamp = time.time()

    def append(self, value):
        self.next = LinkedList(value, self)
        return self.next


class AjaxPool(object):
    def __init__(self, size=1e4, expiration=3600):
        self._size = size
        self._key_list = self._head = LinkedList(None, None)
        self._expiration = expiration
        self._all = {}

    def get(self, key, value=None):
        return self._all.get(key, value)

    def __contains__(self, key):
        return key in self._all

    def __setitem__(self, key, value):
        self._key_list = self._key_list.append(key)
        self._all[key] = value

    def __getitem__(self, key):
        res = self._all[key]
        self.purge()
        return res

    def __delitem__(self, key):
        del self._all[key]

    def pop_key(self):
        head = self._head
        if head.next is None:
            return None
        else:
            key = head.value
            self._head = head.next
            return key

    def purge(self):
        if self._size:
            while len(self._all) > self._size:
                key = self.pop_key()
                if key in self._all:
                    del self._all[key]
        if self._expiration:
            oldest = time.time() - self._expiration
            while self._head.timestamp < oldest:
                key = self.pop_key()
                if key in self._all:
                    del self._all[key]


pending = AjaxPool()
def ajax_url(callback, *args, **kwds):
    if '_ajax_sticky' in kwds:
        _ajax_sticky = kwds.pop('_ajax_sticky')
    else:
        _ajax_sticky = False
    if not isinstance(args, tuple):
        args = args,
    nonce = hex(random.randint(0, 1 << 128))
    pending[nonce] = callback, args, kwds, _ajax_sticky
    return url_for('ajax_result', id=nonce)


@app.route('/callback_ajax/<id>')
def ajax_result(id):
    if id in pending:
        f, args, kwds, _ajax_sticky = pending[id]
        if not _ajax_sticky:
            del pending[id]
        return f(*args, **kwds)
    else:
        return "<expired>"


def ajax_more(callback, *arg_list, **kwds):
    inline = kwds.get('inline', True)
    text = kwds.get('text', 'more')
    nonce = hex(random.randint(0, 1 << 128))
    if inline:
        args = arg_list[0]
        arg_list = arg_list[1:]
        if isinstance(args, tuple):
            res = callback(*arg_list)
        elif isinstance(args, dict):
            res = callback(**args)
        else:
            res = callback(args)
        res = web_latex(res)
    else:
        res = ''
    if arg_list:
        url = ajax_url(ajax_more, callback, *arg_list, inline=True, text=text)
        return """<span id='%(nonce)s'>%(res)s <a onclick="$('#%(nonce)s').load('%(url)s', function() { renderMathInElement($('#%(nonce)s').get(0),katexOpts);}); return false;" href="#">%(text)s</a></span>""" % locals()
    else:
        return res

def image_src(G):
    return ajax_url(image_callback, G, _ajax_sticky=True)

def image_callback(G):
    P = G.plot()
    _, filename = tempfile.mkstemp('.png')
    P.save(filename)
    data = open(filename).read()
    os.unlink(filename)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

def encode_plot(P, pad=None, pad_inches=0.1, bbox_inches=None, remove_axes = False):
    """
    Convert a plot object to base64-encoded png format.

    pad is passed down to matplotlib's tight_layout; pad_inches and bbox_inches to savefig.

    The resulting object is a base64-encoded version of the png
    formatted plot, which can be displayed in web pages with no
    further intervention.
    """
    from StringIO import StringIO
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from base64 import b64encode
    from urllib import quote

    virtual_file = StringIO()
    fig = P.matplotlib()
    fig.set_canvas(FigureCanvasAgg(fig))
    if remove_axes:
        for a in fig.axes:
            a.axis('off')
    if pad is not None:
        fig.tight_layout(pad=pad)
    fig.savefig(virtual_file, format='png', pad_inches=pad_inches, bbox_inches=bbox_inches)
    virtual_file.seek(0)
    return "data:image/png;base64," + quote(b64encode(virtual_file.buf))

class KeyedDefaultDict(defaultdict):
    """
    A defaultdict where the default value takes the key as input.
    """
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError((key,))
        self[key] = value = self.default_factory(key)
        return value

def make_tuple(val):
    """
    Converts lists and dictionaries into tuples, recursively.  The main application
    is so that the result can be used as a dictionary key.
    """
    if isinstance(val, (list, tuple)):
        return tuple(make_tuple(x) for x in val)
    elif isinstance(val, dict):
        return tuple((make_tuple(a), make_tuple(b)) for a,b in val.items())
    else:
        return val

def range_formatter(x):
    if isinstance(x, dict):
        if '$gte' in x:
            a = x['$gte']
        elif '$gt' in x:
            a = x['$gt'] + 1
        else:
            a = None
        if '$lte' in x:
            b = x['$lte']
        elif '$lt' in x:
            b = x['$lt'] - 1
        else:
            b = None
        if a == b:
            return str(a)
        elif b is None:
            return "{0}-".format(a)
        elif a is None:
            raise ValueError
        else:
            return "{0}-{1}".format(a,b)
    return str(x)



# conversion tools between timestamp different kinds of timestamp
epoch = datetime.datetime.utcfromtimestamp(0)
def datetime_to_timestamp_in_ms(dt):
    return int((dt - epoch).total_seconds() * 1000000)

def timestamp_in_ms_to_datetime(ts):
    return datetime.datetime.utcfromtimestamp(float(int(ts)/1000000.0))

# copied here from hilbert_modular_forms.hilbert_modular_form as it
# started to cause circular imports:

def teXify_pol(pol_str):  # TeXify a polynomial (or other string containing polynomials)
    if not isinstance(pol_str, basestring):
        pol_str = str(pol_str)
    o_str = pol_str.replace('*', '')
    ind_mid = o_str.find('/')
    while ind_mid != -1:
        ind_start = ind_mid - 1
        while ind_start >= 0 and o_str[ind_start] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_start -= 1
        ind_end = ind_mid + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '\\frac{' + o_str[ind_start + 1:ind_mid] + '}{' + o_str[
            ind_mid + 1:ind_end] + '}' + o_str[ind_end:]
        ind_mid = o_str.find('/')

    ind_start = o_str.find('^')
    while ind_start != -1:
        ind_end = ind_start + 1
        while ind_end < len(o_str) and o_str[ind_end] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']:
            ind_end += 1
        o_str = o_str[:ind_start + 1] + '{' + o_str[ind_start + 1:ind_end] + '}' + o_str[ind_end:]
        ind_start = o_str.find('^', ind_end)

    return o_str

def add_space_if_positive(texified_pol):
    """
    Add a space if texified_pol is positive to match alignment of positive and
    negative coefficients.

    Examples:
    >>> add_space_if_positive('1')
    '\phantom{-}1'
    >>> add_space_if_positive('-1')
    '-1'
    """
    if texified_pol[0] == '-':
        return texified_pol
    return "\phantom{-}" + texified_pol

