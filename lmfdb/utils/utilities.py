# -*- encoding: utf-8 -*-
import cmath
import math
import datetime
import os
import random
import re
import tempfile
import time
from copy import copy
from itertools import islice
from types import GeneratorType

from flask import make_response, flash, url_for, current_app
from markupsafe import Markup, escape
from werkzeug.utils import cached_property
from sage.all import (
    CBF,
    CC,
    CDF,
    NumberField,
    PolynomialRing,
    PowerSeriesRing,
    QQ,
    RIF,
    RealField,
    TermOrder,
    ZZ,
    floor,
    latex,
    log,
    prime_range,
    prod,
    sign,
    valuation,
)
from sage.misc.functional import round
from sage.structure.element import Element

from lmfdb.app import app, is_beta, is_debug_mode, _url_source


def integer_divisors(n):
    """ returns sorted list of positive divisors of the integer n (uses factor rather than calling pari like sage 9.3+ does) """
    if not n:
        raise ValueError("n must be nonzero")
    def _divisors(a):
        if len(a) == 0:
            return [1]
        q = a[0]
        return sum([[q[0]**e*n for n in _divisors(a[1:])] for e in range(0,q[1]+1)],[])
    return sorted(_divisors(ZZ(n).factor()))

def integer_prime_divisors(n):
    """ returns sorted list of prime divisors of the integer n (uses factor rather than calling pari like sage 9.3+ does) """
    if not n:
        raise ValueError("n must be nonzero")
    return [p for p, _ in ZZ(n).factor()]

def integer_squarefree_part(n):
    """ returns the squarefree part of the integer n (uses factor rather than calling pari like sage 9.3+ does) """
    return sign(n)*prod([p**(e%2) for p, e in ZZ(n).factor()])


def integer_is_squarefree(n):
    """ returns the squarefree part of the integer n (uses factor rather than calling pari like sage 9.3+ does) """
    return all(e == 1 for _, e in ZZ(n).factor())


def list_to_factored_poly_otherorder(s, galois=False, vari='T', p=None):
    """
        Either return the polynomial in a nice factored form,
        or return a pair, with first entry the factored polynomial
        and the second entry a list describing the Galois groups
        of the factors.
        vari allows to choose the variable of the polynomial to be returned.
    """
    # Strip trailing zeros
    if not s:
        s = [0]
    if s[-1] == 0:
        j = len(s) - 1
        while j > 0 and s[j] == 0:
            j -= 1
        s = s[:j+1]
    if len(s) == 1:
        if galois:
            return [str(s[0]), [[0,0]]]
        return str(s[0])
    ZZT = PolynomialRing(ZZ, vari)
    f = ZZT(s)
    sfacts = f.factor()
    sfacts_fc = [[g, e] for g, e in sfacts]
    if sfacts.unit() == -1:
        sfacts_fc[0][0] *= -1
    # if the factor is -1+T^2, replace it by 1-T^2
    # this should happen an even number of times, mod powers
    sfacts_fc_list = [[(-g).list() if g[0] == -1 else g.list(), e] for g, e in sfacts_fc]
    return list_factored_to_factored_poly_otherorder(sfacts_fc_list, galois, vari, p)

def list_factored_to_factored_poly_otherorder(sfacts_fc_list, galois=False, vari='T', p=None):
    """
        Either return the polynomial in a nice factored form,
        or return a pair, with first entry the factored polynomial
        and the second entry a list describing the Galois groups
        of the factors.
        vari allows to choose the variable of the polynomial to be returned.
    """
    gal_list = []
    order = TermOrder('M(0,-1,0,-1)')
    ZZpT = PolynomialRing(ZZ, ['p', vari], order=order)
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
            gtoprint = {(0, i): gi for i, gi in enumerate(g)}
        else:
            gtoprint = {}
            for i, elt in enumerate(g):
                if elt != 0:
                    val = ZZ(elt).valuation(p)
                    gtoprint[(val, i)] = elt/p**val
        glatex = latex(ZZpT(gtoprint))
        if e > 1:
            if len(glatex) != 1:
                outstr += '( %s )^{%d}' % (glatex, e)
            else:
                outstr += '%s^{%d}' % (glatex, e)
        elif len(sfacts_fc_list) > 1:
            outstr += '( %s )' % (glatex,)
        else:
            outstr += glatex

    if galois:
        # 2 factors of degree 2
        if len(sfacts_fc_list) == 2:
            if len(sfacts_fc_list[0][0]) == 3 and len(sfacts_fc_list[1][0]) == 3:
                troubletest = ZZT(sfacts_fc_list[0][0]).disc()*ZZT(sfacts_fc_list[1][0]).disc()
                if troubletest.is_square():
                    gal_list = [[2, 1]]
        return outstr, gal_list
    return outstr

################################################################################
#   number utilities
################################################################################

def prop_int_pretty(n):
    """
    This function should be called whenever displaying an integer in the
    properties table so that we can keep the formatting consistent
    """
    if abs(n) >= 10**12:
        e = floor(log(abs(n),10))
        return r'$%.3f\times 10^{%d}$' % (n/10**e, e)
    else:
        return '$%s$' % n

def try_int(foo):
    try:
        return int(foo)
    except Exception:
        return foo

def type_key(typ):
    # For now we just use a simple mechanism: strings compare at the end.
    if isinstance(typ, str):
        return 1
    else:
        return 0

def key_for_numerically_sort(elt, split=r"[\s\.\-]"):
    # In Python 3 we can no longer compare ints and strings.
    key = [try_int(k) for k in re.split(split, elt)]
    return tuple((type_key(k), k) for k in key)


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

def coeff_to_poly(c, var=None):
    """
    Convert a list or string representation of a polynomial to a sage polynomial.

    Examples:
    >>> coeff_to_poly("1 - 3x + x^2")
    x**2 - 3*x + 1
    >>> coeff_to_poly("1 - 3*x + x**2")
    x**2 - 3*x + 1
    """
    if isinstance(c, str):
        # accept latex
        c = c.replace("{", "").replace("}", "")
        # autodetect variable name
        if var is None:
            varposs = set(re.findall(r"[A-Za-z_]+", c))
            if len(varposs) == 1:
                var = varposs.pop()
            elif not(varposs):
                var = 'x'
            else:
                raise ValueError("Polynomial must be univariate")
    if var is None:
        var = 'x'
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
        # Need to deal with scientific notation
        # Replace e+ and e- with placeholders so that we can split on + and -
        s = s.replace("e+", "P").replace("E+", "P").replace("e-", "M").replace("E-", "M")
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
            b = b.rstrip().rstrip('I').rstrip('*')
        a = a.replace("M", "e-").replace("P", "e+")
        b = b.replace("M", "e-").replace("P", "e+")

        res = CBF(0)
        if a:
            res += CBF(a)
        if b:
            res  +=  sign * CBF(b)* CBF.gens()[0]
        return res

# Conversion from numbers to letters and back
def letters2num(s):
    r"""
    Convert a string into a number
    """
    letters = [ord(z)-96 for z in list(s)]
    ssum = 0
    for j in range(len(letters)):
        ssum = ssum*26+letters[j]
    return ssum

def num2letters(n):
    r"""
    Convert a number into a string of letters
    """
    if n <= 26:
        return chr(96+n)
    else:
        return num2letters(int((n-1)/26))+chr(97+(n-1)%26)


def to_dict(args, exclude = [], **kwds):
    r"""
    Input a dictionary `args` whose values may be lists.
    Output a dictionary whose values are not lists, by choosing the last
    element in a list if the input was a list.

    INPUT:

    - ``args`` -- a dictionary
    - ``exclude`` -- a list of keys to allow lists for.
    - ``kwds`` -- also included in the result

    Example:
    >>> to_dict({"not_list": 1, "is_list":[2,3,4]})
    {'is_list': 4, 'not_list': 1}
    """
    d = dict(kwds)
    for key, values in args.items():
        if key in d:
            continue
        if isinstance(values, list) and key not in exclude:
            if values:
                d[key] = values[-1]
        elif values:
            d[key] = values
    return d


def is_exact(x):
    return isinstance(x, int) or (isinstance(x, Element) and x.parent().is_exact())


def display_float(x, digits, method = "truncate",
                             extra_truncation_digits=3,
                             try_halfinteger=True,
                             no_sci=None,
                             latex=False):
    if abs(x) < 10.**(- digits - extra_truncation_digits):
        return "0"
    # if small, try to display it as an exact or half integer
    if try_halfinteger and abs(x) < 10.**digits:
        if is_exact(x):
            s = str(x)
            if len(s) < digits + 2: # 2 = '/' + '-'
                return str(x)
        k = round_to_half_int(x)
        if k == x:
            k2 = None
            try:
                k2 = ZZ(2*x)
            except TypeError:
                pass
            # the second statement checks for overflow
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
    if no_sci is None:
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
    if latex and "e" in s:
        s = s.replace("e", r"\times 10^{") + "}"
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

def comma(x, sep=","):
    """
    Input is an integer. Output is a string of that integer with commas.
    CAUTION: this misbehaves if the input is not an integer.

    sep is an optional separator other than a comma

    Example:
    >>> comma("12345")
    '12,345'
    """
    return x < 1000 and str(x) or ('%s%s%03d' % (comma(x // 1000, sep), sep, (x % 1000)))

def latex_comma(x):
    """
    For latex we need to use braces around the commas to get the spacing right.
    """
    return comma(x).replace(",", "{,}")

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
    s = re.sub(r"\^(\d*)", r"<sup>\1</sup>", s)
    s = re.sub(r"\_(\d*)", r"<sub>\1</sub>", s)
    s = re.sub(r"\*", r"", s)
    s = re.sub(r"x", r"<i>x</i>", s)
    return s

def factor_base_factor(n, fb):
    return [[p, valuation(n,p)] for p in fb]



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
    return u'<a title="[code]" knowl="dynamic_show" pretext="%s" kwargs="%s">%s</a>' % (code, inner, label)




################################################################################
#  pagination utilities
################################################################################

class ValueSaver():
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

class Pagination():
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
        return self.source[self.start: self.start+self.per_page]

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
    flash(Markup("Error: " + (errmsg % tuple("<span style='color:black'>%s</span>" % escape(x) for x in args))), "error")

def flash_warning(errmsg, *args):
    """ flash warning in grey with args in red; warning may contain markup, including latex math mode"""
    flash(Markup("Warning: " + (errmsg % tuple("<span style='color:red'>%s</span>" % escape(x) for x in args))), "warning")

def flash_info(errmsg, *args):
    """ flash information in grey with args in black; warning may contain markup, including latex math mode"""
    flash(Markup("Note: " + (errmsg % tuple("<span style='color:black'>%s</span>" % escape(x) for x in args))), "info")


################################################################################
#  Ajax utilities
################################################################################

# LinkedList is used in Ajax below
class LinkedList():
    __slots__ = ('value', 'next', 'timestamp')

    def __init__(self, value, nxt):
        self.value = value
        self.next = nxt
        self.timestamp = time.time()

    def append(self, value):
        self.next = LinkedList(value, self)
        return self.next


class AjaxPool():
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
    from .web_display import web_latex
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

def encode_plot(P, pad=None, pad_inches=0.1, bbox_inches=None, remove_axes = False, transparent=False, axes_pad=None):
    """
    Convert a plot object to base64-encoded png format.

    pad is passed down to matplotlib's tight_layout; pad_inches and bbox_inches to savefig.

    The resulting object is a base64-encoded version of the png
    formatted plot, which can be displayed in web pages with no
    further intervention.
    """
    from io import BytesIO as IO
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from base64 import b64encode
    from urllib.parse import quote

    virtual_file = IO()
    fig = P.matplotlib(axes_pad=axes_pad)
    fig.set_canvas(FigureCanvasAgg(fig))
    if remove_axes:
        for a in fig.axes:
            a.axis('off')
    if pad is not None:
        fig.tight_layout(pad=pad)
    fig.savefig(virtual_file, format='png', pad_inches=pad_inches, bbox_inches=bbox_inches, transparent=transparent)
    virtual_file.seek(0)
    buf = virtual_file.getbuffer()
    return "data:image/png;base64," + quote(b64encode(buf))

# conversion tools between timestamp different kinds of timestamp
epoch = datetime.datetime.utcfromtimestamp(0)
def datetime_to_timestamp_in_ms(dt):
    return int((dt - epoch).total_seconds() * 1000000)

def timestamp_in_ms_to_datetime(ts):
    return datetime.datetime.utcfromtimestamp(float(int(ts)/1000000.0))
