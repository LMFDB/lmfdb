# -*- encoding: utf-8 -*-
# this is the caching wrapper, use it like this:
# @app.route(....)
# @cached()
# def func(): ...

import logging
import re
import tempfile
import random
import os
import time
import math
import cmath
import sage
from types import GeneratorType

from sage.all import latex, CC
from copy import copy
from random import randint
from functools import wraps
from itertools import islice
from flask import request, make_response, flash, url_for, current_app
from werkzeug.contrib.cache import SimpleCache
from werkzeug import cached_property
from markupsafe import Markup

from lmfdb.base import app, ctx_proc_userdata

################################################################################
#   number utilities
################################################################################

def an_list(euler_factor_polynomial_fn,
            upperbound=100000, base_field=sage.rings.all.RationalField()):
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
    from sage.rings.fast_arith import prime_range
    from sage.rings.all import PowerSeriesRing
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


def coeff_to_poly(c):
    """
    Convert a string representation of a polynomial to a sage polynomial.

    Examples:
    >>> coeff_to_poly("1 - 3x + x^2")
    x**2 - 3*x + 1
    >>> coeff_to_poly("1 - 3*x + x**2")
    x**2 - 3*x + 1
    """
    from sage.all import PolynomialRing, QQ
    return PolynomialRing(QQ, 'x')(c)


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


def round_to_half_int(num, fraction=2):
    """
    Rounds input `num` to the nearest half-integer. The optional kwarg
    `fraction` is used to round to the nearest `fraction`-part of an integer.

    Examples:
    >>> round_to_half_int(1.1)
    1.0
    >>> round_to_half_int(-0.9)
    -1.0
    """
    return round(num * 1.0 * fraction) / fraction


def to_dict(args):
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
        if isinstance(values, list):
            if values:
                d[key] = values[-1]
        elif values:
            d[key] = values
    return d


def truncate_number(num, precision):
    """
    Truncate `num` to show `precision` characters (as a string). If `num` is
    nearly an integer or half-integer, return that integer or
    half-integer instead.

    Examples:
    >>> truncate_number(1.0001, 4)
    '1'
    >>> truncate_number(1.1234567, 4)
    '1.12'
    """
    local_precision = precision
    if num < 0:
        local_precision = local_precision + 1
    truncation = float(10 ** (-1.0 * local_precision))
    test = round_to_half_int(num)
    if float(abs(num - test)) < truncation:
        if int(test) == test:
            return str(int(test))
        return str(test)
    return(str(num)[0:int(local_precision)])


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
#  SON utilities
################################################################################

def len_val_fn(value):
    """ This creates a SON pair of the type {len:len(value), val:value}, with the len first so lexicographic ordering works.
        WATCH OUT however as later manipulations of the database are likely to mess up this ordering if not careful.
        For this, use order_values below.
        Later we should implement SON_manipulators that insert and save safely.

        Detailed explanation: This is kind of a hack for mongodb:
        Mongo uses lexicographic(?) ordering on strings, which is not convenient when
        strings are used to represent integers (necessary because of large integers).
        For instance, it would not compare properly a generic 2 character/digit
        integer and a 10 character/digit one. This means we lose the ability to
        perform some range queries easily with mongo syntax.
        The solution we are using is to set up a SON ordered dict for this:
        If we had one of the field in our document called "Conductor":"342353223525",
        we replace that with "Conductor_plus":{"len": int(12), "value": "342353223525"}
        (12 is the length of that string)
        This SON object is ordered, so the "len" entry comes first.
        When comparing ordered dicts (=SON), mongo uses a recursive algorithm.
        At the ordered dict stage it uses lexicographic ordering on the keys.
        Inside each key,value pair it compares based on the default ordering of the value type.
        For "Conductor_plus", it will first compare on the length, and if those are equal
        compare on the strings.
    """
    import bson
    return bson.SON([("len", len(value)), ("val", value)])


def order_values(doc, field, sub_fields=["len", "val"]):
    """ Retrieving a document then saving it messes up the ordering in SON documents. This allows you to take a document,
        retrieve a specific field, order it according to the order of sub_fields, and return a document with a SON in place,
        which can then be saved.
    """
    import bson
    tmp = doc[field]
    doc[field] = bson.SON([(sub_field, tmp[sub_field]) for sub_field in sub_fields])
    return doc

################################################################################
#  pymongo utilities - will be removed soon
################################################################################

from pymongo.errors import ExecutionTimeout

def search_cursor_timeout_decorator(cursor, skip, limit):
    r"""
    INPUT:
            - pymongo cursor
            - skip value to pass to cursor (after cursor.count())
            - limit value to pass to cursor (after cursor.count())

    OUTPUT:
            If the query doesn't time out returns the tuple (skip, cursor.count(), cursor.skip(skip).limit(limit))
            If the query times out, it raises a ValueError
    """

    # 25 seconds, timeout, hopefully enough to avoid google's and gunicorn's timeout of 30s
    cursor = cursor.max_time_ms(25000)
    try:
        ncursor = cursor.count()

        # adjusts skip if necessary
        if(skip >= ncursor):
            skip -= (1 + (skip - ncursor) / limit) * limit
        if(skip < 0):
            skip = 0

        cursor = cursor.skip(skip).limit(limit)
    except ExecutionTimeout as err:
        ctx = ctx_proc_userdata()
        flash_error('The search query took longer than expected! Please help us improve by reporting this error  <a href="%s" target=_blank>here</a>.' % ctx['feedbackpage']);
        raise ValueError(err)

    return skip, ncursor, cursor


def random_object_from_collection(collection):
    """ retrieves a random object from mongo db collection; uses collection.rand to improve performance if present """
    import pymongo
    n = collection.rand.count()
    if n:
        m = collection.count()
        if m != n:
            current_app.logger.warning("Random object index {0}.rand is out of date ({1} != {2}), proceeding anyway.".format(collection,n,m))
        obj = collection.find_one({'_id':collection.rand.find_one({'num':randint(1,n)})['_id']})
        if obj: # we could get null here if objects have been deleted without recreating the collection.rand index, if this happens, just rever to old method
            return obj
    if pymongo.version_tuple[0] < 3:
        return collection.aggregate({ '$sample': { 'size': int(1) } }, cursor = {} ).next()
    else:
        # Changed in version 3.0: The aggregate() method always returns a CommandCursor. The pipeline argument must be a list.
        return collection.aggregate([{ '$sample': { 'size': int(1) } } ]).next()

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
#  logging utilities
################################################################################

class LmfdbFormatter(logging.Formatter):
    """
    This Formatter adds some colors, in the future it might do even more ;)

    TODO: the _hl highlighting condition could be a function
          evaluating to true or false
    """
    fmtString = '%(levelname)s:%(name)s@%(asctime)s: %(message)s [%(pathname)s]'

    def __init__(self, *args, **kwargs):
        self._hl = kwargs.pop('hl', None)
        self._fmt_orig = kwargs.pop('fmt', None)
        logging.Formatter.__init__(self, self._fmt_orig, *args, **kwargs)

    def format(self, record):
        """modify the _mft string, call superclasses format method"""
        # reset fmt string
        self._fmt = self._fmt_orig or LmfdbFormatter.fmtString
        fn = os.path.split(record.pathname)[-1]
        record.pathname = "%s:%s" % (fn, record.lineno)

        # some colors for severity level
        if record.levelno >= logging.CRITICAL:
            self._fmt = '\033[31m' + self._fmt
        elif record.levelno >= logging.ERROR:
            self._fmt = '\033[35m' + self._fmt
        elif record.levelno >= logging.WARNING:
            self._fmt = '\033[33m' + self._fmt
        elif record.levelno <= logging.DEBUG:
            self._fmt = '\033[34m' + self._fmt
        elif record.levelno <= logging.INFO:
            self._fmt = '\033[32m' + self._fmt

        # bold, if module name matches
        if record.name == self._hl:
            self._fmt = "\033[1m" + self._fmt

        # reset, to unaffect the next line
        self._fmt += '\033[0m'

        return logging.Formatter.format(self, record)


def make_logger(bp_or_name, hl = False, extraHandlers = [] ):
    """
    creates a logger for the given blueprint. if hl is set
    to true, the corresponding lines will be bold.
    """
    import flask
    import lmfdb.base
    logfocus = lmfdb.base.get_logfocus()
    if type(bp_or_name) == flask.Blueprint:
        name = bp_or_name.name
    else:
        assert isinstance(bp_or_name, basestring)
        name = bp_or_name
    l = logging.getLogger(name)
    l.propagate = False
    if logfocus is None:
        l.setLevel(logging.INFO)
    elif logfocus == name:
        # this will NEVER BE TRUE, because logfocus is set AFTER
        # we have created all of the loggers. This is ok for now,
        # because we are setting the log level later when we set
        # the logfocus variable.
        #
        # Maybe someday someone will rewrite this so that it makes
        # sense...
        l.setLevel(logging.DEBUG)
    else:
        l.setLevel(logging.WARNING)
    if len(l.handlers) == 0:
        formatter = LmfdbFormatter(hl=name if hl else None)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        l.addHandler(ch)
        for elt in extraHandlers:
            l.addHandler(elt)
    return l



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

def encode_plot(P, pad=None, pad_inches=0.1, bbox_inches=None):
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
    if pad is not None:
        fig.tight_layout(pad=pad)
    fig.savefig(virtual_file, format='png', pad_inches=pad_inches, bbox_inches=bbox_inches)
    virtual_file.seek(0)
    return "data:image/png;base64," + quote(b64encode(virtual_file.buf))
