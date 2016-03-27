# -*- encoding: utf-8 -*-

import re
SPACES_RE = re.compile(r'\d\s+\d')
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')
SIGNED_LIST_RE = re.compile(r'^(-?\d+|(-?\d+--?\d+))(,(-?\d+|(-?\d+--?\d+)))*$')
## RE from number_field.py
#LIST_SIMPLE_RE = re.compile(r'^(-?\d+)(,-?\d+)*$'
#PAIR_RE = re.compile(r'^\[\d+,\d+\]$')
#IF_RE = re.compile(r'^\[\]|(\[\d+(,\d+)*\])$')  # invariant factors
FLOAT_RE = re.compile(r'((\b\d+([.]\d*)?)|([.]\d+))(e[-+]?\d+)?')

from flask import flash, redirect, url_for, request
from sage.all import ZZ, QQ
from sage.misc.decorators import decorator_keywords

from markupsafe import Markup

class SearchParser(object):
    def __init__(self, f, clean_info, prep_ranges, prep_plus, default_field, default_name, default_qfield):
        self.f = f
        self.clean_info = clean_info
        self.prep_ranges = prep_ranges
        self.prep_plus = prep_plus
        self.default_field = default_field
        self.default_name = default_name
        self.default_qfield = default_qfield
    def __call__(self, info, query, field=None, name=None, qfield=None, *args, **kwds):
        try:
            if field is None: field=self.default_field
            inp = info.get(field)
            if not inp: return
            if name is None:
                if self.default_name is None:
                    name = field.replace('_',' ').capitalize()
                else:
                    name = self.default_name
            inp = str(inp)
            if SPACES_RE.search(inp):
                raise ValueError("You have entered spaces in between digits. Please add a comma or delete the spaces.")
            inp = clean_input(inp)
            if qfield is None:
                if self.default_qfield is None:
                    qfield = field
                else:
                    qfield = self.default_qfield
            if self.prep_ranges:
                inp = prep_ranges(inp)
            if self.prep_plus:
                inp = inp.replace('+','')
            self.f(inp, query, qfield, *args, **kwds)
            if self.clean_info:
                info[field] = inp
        except (ValueError, AttributeError, TypeError) as err:
            flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. %s" % (inp, name, str(err))), "error")
            info['err'] = ''
            raise

@decorator_keywords
def search_parser(f, clean_info=False, prep_ranges=False, prep_plus=False, default_field=None, default_name=None, default_qfield=None):
    return SearchParser(f, clean_info, prep_ranges, prep_plus, default_field, default_name, default_qfield)

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)
def clean_input(inp):
    if inp is None: return None
    return re.sub(r'[\s<>]', '', str(inp))
def prep_ranges(inp):
    if inp is None: return None
    return inp.replace('..','-').replace(' ','')

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_list(inp, query, qfield, process=None):
    """
    Parses a string representing a list of integers, e.g. '[1,2,3]'

    Flashes an error and returns true if there are problems parsing.
    """
    cleaned = re.sub(r'[\[\]]','',inp)
    out= [int(a) for a in cleaned.split(',')]
    if process is not None:
        query[qfield] = process(out)
    else:
        query[qfield]=out

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

# We parse into a list of singletons and pairs, like [[-5,-2], 10, 11, [16,100]]
# If split0, we split ranges [-a,b] that cross 0 into [-a, -1], [1, b]
def parse_range3(arg, name, split0 = False):
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if ',' in arg:
        return sum([parse_discs(a) for a in arg.split(',')],[])
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        if start:
            low = ZZ(str(start))
        else:
            raise ValueError("Error parsing input for the %s.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % name)
        if end:
            high = ZZ(str(end))
        else:
            raise ValueError("Error parsing input for the %s.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % name)
        if low == high: return [low]
        if split0 and low < 0 and high > 0:
            if low == -1: m = [low]
            else: m = [low,ZZ(-1)]
            if high == 1: p = [high]
            else: p = [ZZ(1),high]
            return [m,p]
        else:
            return [[low, high]]
    else:
        return [ZZ(str(arg))]

def collapse_ors(parsed, query):
    # work around syntax for $or
    # we have to foil out multiple or conditions
    if parsed[0] == '$or' and '$or' in query:
        newors = []
        for y in parsed[1]:
            oldors = [dict.copy(x) for x in query['$or']]
            for x in oldors:
                x.update(y)
            newors.extend(oldors)
        parsed[1] = newors
    query[parsed[0]] = parsed[1]

@search_parser(clean_info=True, prep_plus=True) # see SearchParser.__call__ for actual arguments when calling
def parse_rational(inp, query, qfield):
    if QQ_RE.match(inp):
        query[qfield] = str(QQ(inp))
    else:
        raise ValueError("It needs to be a rational number.")

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_ints(inp, query, qfield):
    if LIST_RE.match(inp):
        collapse_ors(parse_range2(inp, qfield), query)
    else:
        raise ValueError("It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_signed_ints(inp, query, qfield, parse_one=None):
    if parse_one is None: parse_one = lambda x: (x.sign(), x.abs())
    sign_field, abs_field = qfield
    if SIGNED_LIST_RE.match(cleaned):
        parsed = parse_range3(inp, name, split0 = True)
        # if there is only one part, we don't need an $or
        if len(parsed) == 1:
            parsed = parsed[0]
            if type(parsed) == list:
                s0, d0 = parse_one(parsed[0])
                s1, d1 = parse_one(parsed[1])
                if s0 < 0:
                    query[abs_field] = {'$gte': d1, '$lte': d0}
                else:
                    query[abs_field] = {'$lte': d1, '$gte': d0}
            else:
                s0, d0 = parse_one(parsed)
                query[abs_field] = d0
            if sign_field is not None:
                query[sign_field] = s0
        else:
            iquery = []
            for x in parsed:
                if type(x) == list:
                    s0, d0 = parse_one(x[0])
                    s1, d1 = parse_one(x[1])
                    if s0 < 0:
                        abs_D = {'$gte': d1, '$lte': d0}
                    else:
                        abs_D = {'$lte': d1, '$gte': d0}
                else:
                    s0, abs_D = parse_one(x)
                if sign_field is None:
                    iquery.append({abs_field: abs_D})
                else:
                    iquery.append({sign_field: s0, abs_field: abs_D})
            collapse_ors(['$or', iquery], query)
    else:
        raise ValueError("It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_primes(inp, query, qfield, mode=None, to_string=False):
    format_ok = LIST_POSINT_RE.match(inp)
    if format_ok:
        primes = [int(p) for p in inp.split(',')]
        format_ok = all([ZZ(p).is_prime(proof=False) for p in primes])
    if format_ok:
        if to_string:
            primes = [str(p) for p in primes]
        if mode == 'complement':
            query[qfield] = {"$nin": primes}
        elif mode == 'exact':
            query[qfield] = sorted(primes)
        elif mode == "append":
            if qfield not in query:
                query[qfield] = {}
            if "$all" in query[qfield]:
                query[qfield]["$all"].extend(primes)
            else:
                query[qfield]["$all"] = primes
        else:
            raise ValueError("Unrecognized mode: programming error in LMFDB code")
    else:
        raise ValueError("It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11).")

@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_bracketed_posints(inp, query, qfield, maxlength=None, exactlength=None, split=True, process=None, check_divisibility=None):
    if process is None: process = lambda x: x
    if (not BRACKETED_POSINT_RE.match(inp) or
        (maxlength is not None and inp.count(',') > maxlength - 1) or
        (exactlength is not None and inp.count(',') != exactlength - 1)):
        if exactlength == 2:
            lstr = "pair of integers"
            example = "[2,3] or [3,3]"
        elif exactlength == 1:
            lstr = "list of 1 integer"
            example = "[2]"
        elif exactlength is not None:
            lstr = "list of %s integers" % exactlength
            example = str(range(2,exactlength+2)).replace(" ","") + " or " + str([3]*exactlength).replace(" ","")
        elif maxlength is not None:
            lstr = "list of at most %s integers" % maxlength
            example = str(range(2,maxlength+2)).replace(" ","") + " or " + str([2]*max(1, maxlength-2)).replace(" ","")
        else:
            lstr = "list of integers"
            example = "[1,2,3] or [5,6]"
        raise ValueError("It needs to be a %s in square brackets, such as %s." % (lstr, example))
    else:
        if check_divisibility == 'decreasing':
            # Check that each entry divides the previous
            L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i] % L[i+1] != 0:
                    raise ValueError("Each entry must divide the previous, such as [4,2].")
        elif check_divisibility == 'increasing':
            # Check that each entry divides the previous
            L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i+1] % L[i] != 0:
                    raise ValueError("Each entry must divide the next, such as [2,4].")
        if split:
            query[qfield] = [process(int(a)) for a in inp[1:-1].split(',')]
        else:
            query[qfield] = inp[1:-1]

@search_parser(clean_info=True, default_field='galois_group', default_name='Galois group', default_qfield='galois') # see SearchParser.__call__ for actual arguments when calling
def parse_galgrp(inp, query, qfield):
    from lmfdb.transitive_group import complete_group_codes, make_galois_pair
    try:
        gcs = complete_group_codes(inp)
        if len(gcs) == 1:
            query[qfield] = make_galois_pair(gcs[0][0], gcs[0][1])
        elif len(gcs) > 1:
            query[qfield] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
    except NameError as code:
        raise ValueError("It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels.")

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_bool(inp, query, qfield, minus_one_to_zero=False):
    if inp == "True":
        query[qfield] = True
    elif inp == "False":
        query[qfield] = False
    elif inp == "1":
        query[qfield] = 1
    elif inp == "-1":
        query[qfield] = 0 if minus_one_to_zero else -1
    elif inp == "0":
        # On the Galois groups page, these indicate "All"
        pass
    else:
        raise ValueError("It must be True or False.")

def parse_count(info, default=20):
    try:
        info['count'] = int(info['count'])
    except (KeyError, ValueError):
        info['count'] = default
    return info['count']

def parse_start(info, default=0):
    try:
        start = int(info['start'])
        count = info['count']
        if start < 0:
            start += (1 - (start + 1) / count) * count
    except (KeyError, ValueError):
        start = default
    return start
