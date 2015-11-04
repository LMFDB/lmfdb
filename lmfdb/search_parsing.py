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

