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
from sage.all import ZZ, QQ, prod, euler_phi, CyclotomicField, PolynomialRing
from sage.misc.decorators import decorator_keywords

from markupsafe import Markup

class SearchParser(object):
    def __init__(self, f, clean_info, prep_ranges, prep_plus, pass_name, default_field, default_name, default_qfield):
        self.f = f
        self.clean_info = clean_info
        self.prep_ranges = prep_ranges
        self.prep_plus = prep_plus
        self.pass_name = pass_name
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
                if field is None:
                    qfield = self.default_qfield
                else:
                    qfield = field
            if self.prep_ranges:
                inp = prep_ranges(inp)
            if self.prep_plus:
                inp = inp.replace('+','')
            if self.pass_name:
                self.f(inp, query, name, qfield, *args, **kwds)
            else:
                self.f(inp, query, qfield, *args, **kwds)
            if self.clean_info:
                info[field] = inp
        except (ValueError, AttributeError, TypeError) as err:
            flash(Markup("Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>. %s" % (inp, name, str(err))), "error")
            info['err'] = ''
            raise

@decorator_keywords
def search_parser(f, clean_info=False, prep_ranges=False, prep_plus=False, pass_name=False,
                  default_field=None, default_name=None, default_qfield=None):
    return SearchParser(f, clean_info, prep_ranges, prep_plus, pass_name, default_field, default_name, default_qfield)

# Remove whitespace for simpler parsing
# Remove brackets to avoid tricks (so we can echo it back safely)
def clean_input(inp):
    if inp is None: return None
    return re.sub(r'[\s<>]', '', str(inp))
def prep_ranges(inp):
    if inp is None: return None
    return inp.replace('..','-').replace(' ','')

# Various modules need to split a list of integers more simply
def split_list(s):
    s = s.replace(' ','')[1:-1]
    if s:
        return [int(a) for a in s.split(",")]
    return []

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

def parse_range(arg, parse_singleton=int, use_dollar_vars=True):
    # TODO: graceful errors
    if type(arg) == parse_singleton:
        return arg
    if ',' in arg:
        if use_dollar_vars:
            return {'$or': [parse_range(a) for a in arg.split(',')]}
        else:
            return [parse_range(a) for a in arg.split(',')]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte' if use_dollar_vars else 'min'] = parse_singleton(start)
        if end:
            q['$lte' if use_dollar_vars else 'max'] = parse_singleton(end)
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
def parse_ints(inp, query, qfield, parse_singleton=int):
    if LIST_RE.match(inp):
        collapse_ors(parse_range2(inp, qfield, parse_singleton), query)
    else:
        raise ValueError("It needs to be a positive integer (such as 25), a range of positive integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_signed_ints(inp, query, qfield, parse_one=None):
    if parse_one is None: parse_one = lambda x: (x.sign(), x.abs())
    sign_field, abs_field = qfield
    if SIGNED_LIST_RE.match(inp):
        parsed = parse_range3(inp, qfield, split0 = True)
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
        primes = sorted(primes)
        format_ok = all([ZZ(p).is_prime(proof=False) for p in primes])
    if format_ok:
        if to_string:
            primes = [str(p) for p in primes]
        if mode == 'complement':
            query[qfield] = {"$nin": primes}
        elif mode == 'liststring':
            primes = [str(p) for p in primes]
            query[qfield] = ",".join(primes)
        elif mode == 'subsets':
            # need all subsets of the list of primes 
            powerset = [[]]
            for p in primes:
                powerset.extend([a+[p] for a in powerset])
            # now set up a big $or clause
            powerset = [','.join([str(p) for p in a]) for a in powerset]
            powerset = [{qfield: a} for a in powerset]
            collapse_ors(['$or', powerset], query)
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
        (exactlength is not None and inp.count(',') != exactlength - 1) or
        (exactlength is not None and inp == '[]' and exactlength > 0)):
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
        if inp == '[]': # fixes bug in the code below (split never returns an empty list)
            query[qfield] = []
            return
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
def parse_galgrp(inp, query, qfield, use_bson=True):
    from lmfdb.transitive_group import complete_group_codes, make_galois_pair
    if not use_bson:
        make_galois_pair = lambda x,y: [x,y]
    try:
        gcs = complete_group_codes(inp)
        if len(gcs) == 1:
            query[qfield] = make_galois_pair(gcs[0][0], gcs[0][1])
        elif len(gcs) > 1:
            query[qfield] = {'$in': [make_galois_pair(x[0], x[1]) for x in gcs]}
    except NameError as code:
        raise ValueError("It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels.")

def nf_string_to_label(F):  # parse Q, Qsqrt2, Qsqrt-4, Qzeta5, etc
    if F == 'Q':
        return '1.1.1.1'
    if F == 'Qi':
        return '2.0.4.1'
    # Change unicode dash with minus sign
    F = F.replace(u'\u2212', '-')
    # remove non-ascii characters from F
    F = F.decode('utf8').encode('ascii', 'ignore')
    fail_string = str(F + ' is not a valid field label or name or polynomial, or is not ')
    if len(F) == 0:
        raise ValueError("Entry for the field was left blank.  You need to enter a field label, field name, or a polynomial.")
    if F[0] == 'Q':
        if F[1:5] in ['sqrt', 'root']:
            try:
                d = ZZ(str(F[5:])).squarefree_part()
            except ValueError:
                d = 0
            if d == 0:
                raise ValueError("After {0}, the remainder must be a nonzero integer.  Use {0}5 or {0}-11 for example.".format(F[:5]))
            if d % 4 in [2, 3]:
                D = 4 * d
            else:
                D = d
            absD = D.abs()
            s = 0 if D < 0 else 2
            return '2.%s.%s.1' % (s, str(absD))
        if F[1:5] == 'zeta':
            try:
                d = ZZ(str(F[5:]))
            except ValueError:
                d = 0
            if d < 1:
                raise ValueError("After {0}, the remainder must be a positive integer.  Use {0}5 for example.".format(F[:5]))
            if d % 4 == 2:
                d /= 2  # Q(zeta_6)=Q(zeta_3), etc)
            if d == 1:
                return '1.1.1.1'
            deg = euler_phi(d)
            if deg > 23:
                raise ValueError('%s is not in the database.' % F)
            adisc = CyclotomicField(d).discriminant().abs()  # uses formula!
            return '%s.0.%s.1' % (deg, adisc)
        return fail_string
    # check if a polynomial was entered
    F = F.replace('X', 'x')
    if 'x' in F:
        F1 = F.replace('^', '**')
        # print F
        from lmfdb.number_fields.number_field import poly_to_field_label
        F1 = poly_to_field_label(F1)
        if F1:
            return F1
        raise ValueError('%s is not in the database.'%F)
    # Expand out factored labels, like 11.11.11e20.1
    parts = F.split(".")
    if len(parts) != 4:
        raise ValueError("It must be of the form <deg>.<real_emb>.<absdisc>.<number>, such as 2.2.5.1.")
    def raise_power(ab):
        if ab.count("e") == 0:
            return ZZ(ab)
        elif ab.count("e") == 1:
            a,b = ab.split("e")
            return ZZ(a)**ZZ(b)
        else:
            raise ValueError("Malformed absolute discriminant.  It must be a sequence of strings AeB for A and B integers, joined by _s.  For example, 2e7_3e5_11.")
    parts[2] = str(prod(raise_power(c) for c in parts[2].split("_")))
    return ".".join(parts)

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_nf_string(inp, query, qfield):
    query[qfield] = nf_string_to_label(inp)

def pol_string_to_list(pol, deg=None, var=None):
    if var is None:
        from lmfdb.hilbert_modular_forms.hilbert_field import findvar
        var = findvar(pol)
        if not var:
            var = 'a'
    pol = PolynomialRing(QQ, var)(str(pol))
    if deg is None:
        fill = 0
    else:
        fill = deg - pol.degree() - 1
    return [str(c) for c in pol.coefficients(sparse=False)] + ['0']*fill

@search_parser(pass_name=True) # see SearchParser.__call__ for actual arguments when calling
def parse_nf_elt(inp, query, name, qfield, field_label='field_label'):
    if field_label not in query:
        raise ValueError("You must specify a field when searching by %s"%name)
    deg = int(query[field_label].split('.')[0])
    query[qfield] = pol_string_to_list(inp, deg=deg)

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_hmf_weight(inp, query, qfield):
    parallel_field, normal_field = qfield
    try:
        query[parallel_field] = int(inp)
    except ValueError:
        try:
            query[normal_field] = str(split_list(inp))
        except ValueError:
            raise ValueError("It must be either an integer (parallel weight) or a comma separated list of integers, such as 2 or 2,4,6.")

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

@search_parser
def parse_restricted(inp, query, qfield, allowed, process=None):
    if process is None: process = lambda x: x
    allowed = [str(a) for a in allowed]
    if inp not in allowed:
        if len(allowed) == 0:
            allowed_str = "unspecified"
        if len(allowed) == 1:
            allowed_str = allowed[0]
        elif len(allowed) == 2:
            allowed_str = " or ".join(allowed)
        else:
            allowed_str = ", ".join(allowed[:-1]) + " or " + allowed[-1]
        raise ValueError("It must be %s"%allowed_str)
    query[qfield] = process(inp)

@search_parser
def parse_noop(inp, query, qfield):
    query[qfield] = inp

def parse_paired_fields(info, query, field1=None, name1=None, qfield1=None, parse1=None, kwds1={},
                                     field2=None, name2=None, qfield2=None, parse2=None, kwds2={}):
    tmp_query1 = {}
    tmp_query2 = {}
    parse1(info,tmp_query1,field1,name1,qfield1,**kwds1)
    parse2(info,tmp_query2,field2,name2,qfield2,**kwds2)
    #print tmp_query1
    #print tmp_query2
    def remove_or(D):
        assert len(D) <= 1
        if '$or' in D: return D['$or']
        elif D: return [D]
        else: return []
    def combine(D1, D2):
        # For key='qfield',
        # Values can be singletons or a dict with keys '$lte' and '$gte' and values singletons.
        # For key='$or',
        # Values are lists of such dicts (with key qfield)
        # Analogous to collapse_ors, we update D2
        L1 = remove_or(D1)
        L2 = remove_or(D2)
        #print L1
        #print L2
        if not L1:
            return L2
        elif not L2:
            return L1
        else:
            return [{A.keys()[0]:A.values()[0], B.keys()[0]:B.values()[0]} for A in L1 for B in L2]
    L = combine(tmp_query1,tmp_query2)
    #print L
    if len(L) == 1:
        query.update(L[0])
    else:
        collapse_ors(['$or',L], query)

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
    try:
        paging = int(info['paging'])
        if paging == 0:
            start = 0
    except (KeyError, ValueError, TypeError):
        pass
    return start
