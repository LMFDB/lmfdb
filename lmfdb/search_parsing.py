# -*- encoding: utf-8 -*-

import re
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')
## RE from number_field.py
#LIST_RE = re.compile(r'^(-?\d+|(-?\d+--?\d+))(,(-?\d+|(-?\d+--?\d+)))*$')
#LIST_SIMPLE_RE = re.compile(r'^(-?\d+)(,-?\d+)*$'
#PAIR_RE = re.compile(r'^\[\d+,\d+\]$')
#IF_RE = re.compile(r'^\[\]|(\[\d+(,\d+)*\])$')  # invariant factors
FLOAT_RE = re.compile(r'((\b\d+([.]\d*)?)|([.]\d+))(e[-+]?\d+)?')

from flask import flash, redirect, url_for, request
from sage.all import ZZ, QQ

from markupsafe import Markup

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)
def clean_input(inp):
    if inp is None: return None
    return re.sub(r'[\s<>]', '', str(inp))
def prep_ranges(inp):
    if inp is None: return None
    return inp.replace('..','-').replace(' ','')

def parse_list(info, query, field, name=None, qfield=None, process=None):
    """
    Parses a string representing a list of integers, e.g. '[1,2,3]'

    Flashes an error and returns true if there are problems parsing.
    """
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    try:
        out= [int(a) for a in inp.split(',')]
        if process is not None:
            query[qfield] = process(out)
        else:
            query[qfield]=out
    except Exception:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a list of integers (such as [1,2,3])." % inp), "error")
        raise ValueError

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

def parse_rational(info, query, field, name=None, qfield=None):
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    if name is None: name = field.replace('_',' ')
    cleaned = inp.replace('+', '')
    if QQ_RE.match(cleaned):
        query[qfield] = str(QQ(cleaned))
        info[field] = cleaned
    else:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It needs to be a rational number." % (inp, name)), "error")
        raise ValueError

def parse_ints(info, query, field, name=None, qfield=None):
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    if name is None: name = field.replace('_',' ')
    cleaned = prep_ranges(inp)
    if LIST_RE.match(cleaned):
        collapse_ors(parse_range2(cleaned, field), query)
        info[field] = cleaned
    else:
        err_msg = "Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % (inp,name)
        flash(Markup(err_msg), "error")
        raise ValueError

def parse_signed_ints(info, query, field, sign_field, abs_field, name=None, parse_one=None):
    inp = clean_input(info.get(field))
    if not inp: return
    if name is None: name = field
    if parse_one is None: parse_one = lambda x: (x.sign(), x.abs())
    cleaned = prep_ranges(inp)
    if LIST_RE.match(cleaned):
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
        info[field] = cleaned
    else:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % (inp, name)), "error")
        raise ValueError

def parse_primes(info, query, field, name=None, qfield=None, mode=None):
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    if name is None: name = field.replace('_',' ')
    format_ok = LIST_POSINT_RE.match(inp)
    if format_ok:
        primes = [int(p) for p in inp.split(',')]
        format_ok = all([ZZ(p).is_prime(proof=False) for p in primes])
    if format_ok:
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
        info[field] = inp
    else:
        err_msg = "Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>.  It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11)." % (inp, name)
        flash(Markup(err_msg), "error")
        raise ValueError

def parse_bracketed_posints(info, query, field, name=None, qfield=None, maxlength=None, exactlength=None, split=True, process=None):
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    if process is None: process = lambda x: x
    if name is None: name = field.replace('_',' ')
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
        err_msg = "Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It needs to be a %s in square brackets, such as %s." % (inp, name, lstr, example)
        flash(Markup(err_msg), "error")
        raise ValueError
    else:
        if split:
            query[qfield] = [process(int(a)) for a in inp[1:-1].split(',')]
        else:
            query[qfield] = inp[1:-1]
        info[field] = inp

def parse_galgrp(info, query, field='galois_group', name='Galois group', qfield='galois'):
    inp = clean_input(info.get(field))
    if not inp: return
    from lmfdb.transitive_group import complete_group_codes, make_galois_pair
    try:
        gcs = complete_group_codes(inp)
        if len(gcs) == 1:
            query[qfield] = make_galois_pair(gcs[0][0], gcs[0][1])
        elif len(gcs) > 1:
            query[qfield] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
        info[field] = inp
    except NameError as code:
        err_msg = "Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels."%(inp, name)
        flash(Markup(err_msg), "error")
        raise ValueError

def parse_bool(info, query, field, name=None, qfield=None, minus_one_to_zero=False):
    inp = clean_input(info.get(field))
    if not inp: return
    if qfield is None: qfield = field
    if name is None: name = field.replace("_", " ")
    if inp == "True":
        query[qfield] = True
    elif inp == "False":
        query[qfield] = False
    elif inp == "1":
        query[qfield] = 1
    elif inp == "-1":
        query[qfield] = 0 if minus_one_to_zero else -1
    else:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. It must be True or False." % (inp, name)))
        raise ValueError

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
