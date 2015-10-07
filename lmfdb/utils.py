# -*- encoding: utf-8 -*-
# this is the caching wrapper, use it like this:
# @app.route(....)
# @cached()
# def func(): ...
import logging

import re

from flask import request, make_response
from functools import wraps
from werkzeug.contrib.cache import SimpleCache

from copy import copy
from werkzeug import cached_property
from flask import url_for

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
            self._fmt = '\033[91m' + self._fmt
        elif record.levelno >= logging.WARNING:
            self._fmt = '\033[93m' + self._fmt
        elif record.levelno <= logging.DEBUG:
            self._fmt = '\033[94m' + self._fmt
        elif record.levelno <= logging.INFO:
            self._fmt = '\033[92m' + self._fmt

        # bold, if module name matches
        if record.name == self._hl:
            self._fmt = "\033[1m" + self._fmt

        # reset, to unaffect the next line
        self._fmt += '\033[0m'

        return logging.Formatter.format(self, record)


def make_logger(bp_or_name, hl=False):
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
    formatter = LmfdbFormatter(hl=name if hl else None)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    l.addHandler(ch)
    return l


class MongoDBPagination(object):
    def __init__(self, query, per_page, page, endpoint, endpoint_params):
        self.query = query
        self.per_page = int(per_page)
        self.page = int(page)
        self.endpoint = endpoint
        self.endpoint_params = endpoint_params

    @cached_property
    def count(self):
        return self.query.count(True)

    @cached_property
    def entries(self):
        return self.query.skip(self.start).limit(self.per_page)

    has_previous = property(lambda x: x.page > 1)
    has_next = property(lambda x: x.page < x.pages)
    pages = property(lambda x: max(0, x.count - 1) // x.per_page + 1)
    start = property(lambda x: (x.page - 1) * x.per_page)
    end = property(lambda x: min(x.start + x.per_page - 1, x.count - 1))

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


class LazyMongoDBPagination(MongoDBPagination):
    @cached_property
    def has_next(self):
        return self.query.skip(self.start).limit(self.per_page + 1).count(True) > self.per_page

    @property
    def count(self):
        raise NotImplementedError

    @property
    def pages(self):
        raise NotImplementedError


def orddict_to_strlist(v):
    """
    v -- dictionary with int keys
    """


### this was formerly in utilities.py
import tempfile
import random
import os
import re
import time

from lmfdb.base import app
from flask import url_for, make_response
import sage.all

def to_dict(args):
    d = {}
    for key in args:
        values = args[key]
        if isinstance(values, list):
            if values:
                d[key] = values[-1]
        elif values:
            d[key] = values
    return d


def pair2complex(pair):
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


def an_list(euler_factor_polynomial_fn, upperbound=100000, base_field=sage.rings.all.RationalField()):
    """ Takes a fn that gives for each prime the polynomial of the associated with the prime,
        given as a list, with independent coefficient first. This list is of length the degree+1.
    """
    from sage.rings.fast_arith import prime_range
    from sage.rings.all import PowerSeriesRing
    from math import ceil, log
    PP = PowerSeriesRing(base_field, 'x', 1 + ceil(log(upperbound) / log(2.)))

    x = PP('x')
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


def splitcoeff(coeff):
    local = coeff.split("\n")
    answer = []
    for s in local:
        if s:
            answer.append(pair2complex(s))

    return answer


def pol_to_html(p):
    r"""
    Convert polynomial p to html.
    """
    s = str(p)
    s = re.sub("\^(\d*)", "<sup>\\1</sup>", s)
    s = re.sub("\_(\d*)", "<sub>\\1</sub>", s)
    s = re.sub("\*", "", s)
    s = re.sub("x", "<i>x</i>", s)
    return s


def web_latex(x):
    if isinstance(x, (str, unicode)):
        return x
    else:
        return "\( %s \)" % sage.all.latex(x)

# if you just use web_latex(x) where x is a factored ideal then the
# parentheses are doubled which does not look good!
def web_latex_ideal_fact(x):
    y = web_latex(x)
    y = y.replace("(\\left(","\\left(")
    y = y.replace("\\right))","\\right)")
    return y

def web_latex_split_on(x, on=['+', '-']):
    if isinstance(x, (str, unicode)):
        return x
    else:
        A = "\( %s \)" % sage.all.latex(x)
        for s in on:
            A = A.replace(s, '\) ' + s + ' \(')
    return A
    
def web_latex_split_on_pm(x):
    return web_latex_split_on(x)

def web_latex_split_on_re(x, r = '(q[^+-]*[+-])'):

    def insert_latex(s):
        return s.group(1) + '\) \('

    if isinstance(x, (str, unicode)):
        return x
    else:
        A = "\( %s \)" % sage.all.latex(x)
        c = re.compile(r)
        A = A.replace('+', '\)\( {}+ ')
        A = A.replace('-', '\)\( {}- ')
        A = A.replace('\left(','\left( {}\\right.') # parantheses needs to be balanced
        A = A.replace('\\right)','\left.\\right)')        
        A = c.sub(insert_latex, A)
    return A


# make latex matrix from list of lists
def list_to_latex_matrix(li):
    dim = str(len(li[0]))
    mm = r"\left(\begin{array}{*{"+dim+ r"}{r}}"
    for row in li:
        row = [str(a) for a in row]
        mm += ' & '.join(row)
        mm += r'\\'
    mm = mm[:-2] # remove final line break
    mm += r'\end{array}\right)'
    return mm

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
        return """<span id='%(nonce)s'>%(res)s <a onclick="$('#%(nonce)s').load('%(url)s', function() { MathJax.Hub.Queue(['Typeset',MathJax.Hub,'%(nonce)s']);}); return false;" href="#">%(text)s</a></span>""" % locals()
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


def parse_range(arg, parse_singleton=int):
    # TODO: graceful errors
    if type(arg) == parse_singleton:
        return arg
    if ',' in arg:
        return {'$or': [parse_range(a) for a in arg.split(',')]}
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte'] = parse_singleton(start)
        if end:
            q['$lte'] = parse_singleton(end)
        return q
    else:
        return parse_singleton(arg)


# version above does not produce legal results when there is a comma
# to deal with $or, we return [key, value]
def parse_range2(arg, key, parse_singleton=int):
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if type(arg) == parse_singleton:
        return [key, arg]
    if ',' in arg:
        tmp = [parse_range2(a, key, parse_singleton) for a in arg.split(',')]
        tmp = [{a[0]: a[1]} for a in tmp]
        return ['$or', tmp]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte'] = parse_singleton(start)
        if end:
            q['$lte'] = parse_singleton(end)
        return [key, q]
    else:
        return [key, parse_singleton(arg)]


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

# Input is an integer
# Output is a string of that integer with comma separators


def comma(x):
    return x < 1000 and str(x) or ('%s,%03d' % (comma(x // 1000), (x % 1000)))

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)


def clean_input(inp):
    return re.sub(r'[\s<>]', '', str(inp))


def coeff_to_poly(c):
    from sage.all import PolynomialRing, QQ
    return PolynomialRing(QQ, 'x')(c)

from flask import current_app


def debug():
    """
    this triggers the debug environment on purpose. you have to start
    the server via website.py --debug
    don't forget to remove the debug() from your code!!!
    """
    assert current_app.debug is False, "Don't panic! You're here by request of debug()"

def encode_plot(P):
    """
    Convert a plot object to base64-encoded png format.

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
    fig.savefig(virtual_file, format='png')
    virtual_file.seek(0)
    return "data:image/png;base64," + quote(b64encode(virtual_file.buf))
