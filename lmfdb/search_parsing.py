# -*- encoding: utf-8 -*-

import re
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')

from lmfdb.transitive_group import complete_group_codes, make_galois_pair

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)
def clean_input(inp):
    return re.sub(r'[\s<>]', '', str(inp))

def parse_list(s):
    """
    parses a string representing a list of integers, e.g. '[1,2,3]'
    """
    s = s.replace(' ','')[1:-1]
    if s:
        return [int(a) for a in s.split(",")]
    return []

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

def parse_list(L):
    L = str(L)
    if re.search("\\d", L):
        return [int(a) for a in L[1:-1].split(',')]
    return []
    # return eval(str(L)) works but using eval() is insecure

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

def parse_rational(inp, query, field, name=None):
    if inp is None: return
    if name is None: name = field.replace('_',' ')
    ans = clean_input(inp)
    ans = ans.replace('+', '')
    if not QQ_RE.match(ans):
        raise ValueError("Error parsing input for the %s.  It needs to be a rational number.")
    query[name] = str(QQ(ans))

def parse_ints(inp, query, field, name=None):
    if inp is None: return
    if name is None: name = field.replace('_',' ')
    cleaned = clean_input(inp)
    cleaned = cleaned.replace('..', '-').replace(' ', '')
    if not LIST_RE.match(cleaned):
        raise ValueError("Error parsing input for the %s.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % name)
    # Past input check
    collapse_ors(parse_range2(cleaned, field), query)

def parse_signed_ints(inp, query, sign_field, abs_field, name, parse_one=None):
    if parse_one is None: parse_one = lambda x: (x.sign(), x.abs())
    if inp is None: return
    cleaned = clean_input(info[field])
    cleaned = cleaned.replace('..', '-').replace(' ', '')
    if not LIST_RE.match(cleaned):
        raise ValueError("Error parsing input for %s.  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % name)
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
        query[sign_field] = s0
    else:
        iquery = []
        for x in parsed:
            if type(x) == list:
                s0, d0 = parse_one(x[0])
                s1, d1 = parse_one(x[1])
                if s0 < 0:
                    iquery.append({sign_field: s0, abs_field: {'$gte': d1, '$lte': d0}})
                else:
                    iquery.append({sign_field: s0, abs_field: {'$lte': d1, '$gte': d0}})
            else:
                s0, d0 = parse_one(x)
                iquery.append({sign_field: s0, abs_field: d0})
        collapse_ors(['$or', iquery], query)

def parse_primes(inp, query, field, name=None, mode=None):
    if inp is None: return
    if name is None: name = field.replace('_',' ')
    cleaned = clean_input(inp)
    format_ok = LIST_POSINT_RE.match(cleaned)
    if format_ok:
        primes = [int(p) for p in cleaned.split(',')]
        format_ok = all([ZZ(p).is_prime(proof=False) for p in primes])
    if format_ok:
        if mode == 'complement':
            query[field] = {"$nin": primes}
        elif mode == 'exact':
            query[field] = sorted(primes)
        elif mode == "append":
            if field in query:
                if "$all" in query[field]:
                    query[field]["$all"].extend(primes)
                else:
                    query[field]["$all"] = primes
        else:
            raise ValueError("Unrecognized mode: programming error in LMFDB code")
    else:
        raise ValueError("Error parsing input for %s.  It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11)."%name)

def parse_bracketed_posints(inp, query, field, name=None, length=None,split=False,process=None):
    if inp is None: return
    if process is None: process = lambda x: x
    if name is None: name = field.replace('_',' ')
    cleaned = clean_input(inp)
    if BRACKETED_POSINT_RE.match(cleaned) and (length is None or cleaned.count(',') == length - 1):
        if split:
            query[field] = [process(a) for a in parse_list(cleaned)]
        else:
            query[field] = cleaned[1:-1]
    else:
        if length is None: lstr = "list of integers"
        elif length == 2: lstr = "pair of integers"
        else: lstr = "list of integers of length %s"%(length)
        raise ValueError("Error parsing input for %s. It needs to be a %s in square brackets, such as [2,3] or [3,3]" %(name, lstr))

def parse_galgrp(inp, query, field='galois', name='Galois group'):
    if inp is None: return
    cleaned = clean_input(inp)
    try:
        gcs = complete_group_codes(cleaned)
        if len(gcs) == 1:
            query[field] = make_galois_pair(gcs[0][0], gcs[0][1])
        elif len(gcs) > 1:
            query[field] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
    except NameError as code:
        raise ValueError('Error parsing input for %s: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or a comma separated list of such labels.'%(name, code))

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
