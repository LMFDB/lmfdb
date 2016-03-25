# -*- encoding: utf-8 -*-

import re
LIST_RE = re.compile(r'^(\d+|(\d+-(\d+)?))(,(\d+|(\d+-(\d+)?)))*$')
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')
FLOAT_RE = re.compile(r'((\b\d+([.]\d*)?)|([.]\d+))(e[-+]?\d+)?')

from flask import flash, redirect, url_for, request
from sage.all import ZZ, QQ

from markupsafe import Markup

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)
def clean_input(inp):
    return re.sub(r'[\s<>]', '', str(inp))

def _parse_list(L):
    L = str(L)
    if re.search("\\d", L):
        return [int(a) for a in L[1:-1].split(',')]
    return []
    # return eval(str(L)) works but using eval() is insecure

def parse_list(inp, query, field, test=None, url=None):
    """
    parses a string representing a list of integers, e.g. '[1,2,3]'
    """
    i=str(inp)
    if len(inp)>2:
        i = str(inp).replace(' ','').replace('[','').replace(']','')
    if not i: return
    try:
        out= [int(a) for a in i.split(',')]
        if test is not None:
            query[field] = test(out)
        else:
            query[field]=out
    except:
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input. It needs to be a list of integers (such as [1,2,3])." % inp), "error")
        if url is not None:
            return redirect(url)

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
    if not inp: return
    if name is None: name = field.replace('_',' ')
    ans = clean_input(inp)
    ans = ans.replace('+', '')
    if not QQ_RE.match(ans):
        raise ValueError("Error parsing input for the %s.  It needs to be a rational number.")
    query[name] = str(QQ(ans))

def parse_ints(inp, query, field, url=None):
    if not inp: return
    cleaned = clean_input(inp)
    cleaned = cleaned.replace('..', '-').replace(' ', '')
    if not LIST_RE.match(cleaned):
        flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input. It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)." % inp), "error")
        if url is not None:
            return redirect(url)
    else:
        collapse_ors(parse_range2(cleaned, field), query)

def parse_signed_ints(inp, query, sign_field, abs_field, name, parse_one=None):
    if parse_one is None: parse_one = lambda x: (x.sign(), x.abs())
    if not inp: return
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
    if not inp: return
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
    if not inp: return
    if process is None: process = lambda x: x
    if name is None: name = field.replace('_',' ')
    cleaned = clean_input(inp)
    if BRACKETED_POSINT_RE.match(cleaned) and (length is None or cleaned.count(',') == length - 1):
        if split:
            query[field] = [process(a) for a in _parse_list(cleaned)]
        else:
            query[field] = cleaned[1:-1]
    else:
        if length is None: lstr = "list of integers"
        elif length == 2: lstr = "pair of integers"
        else: lstr = "list of integers of length %s"%(length)
        raise ValueError("Error parsing input for %s. It needs to be a %s in square brackets, such as [2,3] or [3,3]" %(name, lstr))

def parse_galgrp(inp, query, field='galois', name='Galois group'):
    from lmfdb.transitive_group import complete_group_codes, make_galois_pair
    if not inp: return
    cleaned = clean_input(inp)
    try:
        gcs = complete_group_codes(cleaned)
        if len(gcs) == 1:
            query[field] = make_galois_pair(gcs[0][0], gcs[0][1])
        elif len(gcs) > 1:
            query[field] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
    except NameError as code:
        raise ValueError('Error parsing input for %s: unknown group label %s.  It needs to be a <a title = "Galois group labels" knowl="nf.galois_group.name">group label</a>, such as C5 or 5T1, or a comma separated list of such labels.'%(name, code))

# Function to parse search box input for finite abelian group
# invariants, e.g. torsion structure for elliptic curves or genus 2
# curves

def parse_torsion_structure(L, maxrank=2):
    r"""
    Parse a string entered into torsion structure search box
    '[]' --> []
    '[n]' --> [str(n)]
    'n' --> [str(n)]
    '[m,n]' or '[m n]' --> [str(m),str(n)]
    'm,n' or 'm n' --> [str(m),str(n)]
    ... and similarly for up to maxrank factors
    """
    # strip <whitespace> or <whitespace>[<whitespace> from the beginning:
    L1 = re.sub(r'^\s*\[?\s*', '', str(L))
    # strip <whitespace> or <whitespace>]<whitespace> from the beginning:
    L1 = re.sub(r'\s*]?\s*$', '', L1)
    # catch case where there is nothing left:
    if not L1:
        return []
    # This matches a string of 1 or more digits at the start,
    # optionally followed by up to 3 times (nontrivial <ws> or <ws>,<ws> followed by
    # 1 or more digits):
    TORS_RE = re.compile(r'^\d+((\s+|\s*,\s*)\d+){0,%s}$' % (maxrank-1))
    if TORS_RE.match(L1):
        if ',' in L1:
            # strip interior <ws> and use ',' as delimiter:
            res = [int(a) for a in L1.replace(' ','').split(',')]
        else:
            # use whitespace as delimiter:
            res = [int(a) for a in L1.split()]
        n = len(res)
        if all(x>0 for x in res) and all(res[i+1]%res[i]==0 for i in range(n-1)):
            return res
    return 'Error parsing input %s.  It needs to be a list of up to %s integers, optionally in square brackets, separated by spaces or a comma, such as [6], 6, [2,2], or [2,4].  Moreover, each integer should be bigger than 1, and each divides the next.' % (L,maxrank)

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
