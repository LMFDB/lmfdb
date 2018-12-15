# -*- encoding: utf-8 -*-

## parse_newton_polygon and parse_abvar_decomp are defined in lmfdb.abvar.fq.search_parsing

import re
SPACES_RE = re.compile(r'\d\s+\d')
LIST_RE = re.compile(r'^(\d+|(\d*-(\d+)?))(,(\d+|(\d*-(\d+)?)))*$')
FLOAT_STR = r'((\d+([.]\d*)?)|([.]\d+))(e[-+]?\d+)?'
LIST_FLOAT_RE = re.compile(r'^({0}|{0}-{0})(,({0}|{0}-{0}))*$'.format(FLOAT_STR))
BRACKETED_POSINT_RE = re.compile(r'^\[\]|\[\d+(,\d+)*\]$')
QQ_RE = re.compile(r'^-?\d+(/\d+)?$')
# Single non-negative rational, allowing decimals, used in parse_range2rat
QQ_DEC_RE = re.compile(r'^\d+((\.\d+)|(/\d+))?$')
LIST_POSINT_RE = re.compile(r'^(\d+)(,\d+)*$')
LIST_RAT_RE = re.compile(r'^((\d+((\.\d+)|(/\d+))?)|((\d+((\.\d+)|(/\d+))?)-((\d+((\.\d+)|(/\d+))?))?))(,((\d+((\.\d+)|(/\d+))?)|((\d+((\.\d+)|(/\d+))?)-(\d+((\.\d+)|(/\d+))?)?)))*$')
SIGNED_LIST_RE = re.compile(r'^(-?\d+|(-?\d+--?\d+))(,(-?\d+|(-?\d+--?\d+)))*$')
## RE from number_field.py
#LIST_SIMPLE_RE = re.compile(r'^(-?\d+)(,-?\d+)*$'
#PAIR_RE = re.compile(r'^\[\d+,\d+\]$')
#IF_RE = re.compile(r'^\[\]|(\[\d+(,\d+)*\])$')  # invariant factors
FLOAT_RE = re.compile('^' + FLOAT_STR + '$')
BRACKETING_RE = re.compile(r'(\[[^\]]*\])') # won't work for iterated brackets [[a,b],[c,d]]

from flask import flash
from sage.all import ZZ, QQ, prod, euler_phi, CyclotomicField, PolynomialRing
from sage.misc.decorators import decorator_keywords
#from sage.misc.misc import subsets

from markupsafe import Markup
from collections import defaultdict, Counter

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

# This function can be used by modules to get a list of ints
# or an iterator (xrange) that matches the results of parse_ints below
# useful when a module wants to iterate over key values being
# passed into dictionary for postgres.  Input should be a string
def parse_ints_to_list(arg):
    if arg == None:
        return []
    s = str(arg)
    s = s.replace(' ','')
    if not s:
        return []
    if s[0] == '[' and s[-1] == ']':
        s = s[1:-1]
    if ',' in s:
        return [int(n) for n in s.split(',')]
    if '-' in s[1:]:
        i = s.index('-',1)
        min, max = s[:i], s[i+1:]
        return xrange(int(min),int(max)+1)
    if '..' in s:
        i = s.index('..',1)
        min, max = s[:i], s[i+2:]
        return xrange(int(min),int(max)+1)
    return [int(s)]

def parse_ints_to_list_flash(arg,name):
    try:
        return parse_ints_to_list(arg)
    except ValueError:
        errmsg = "Error: <span style='color:black'>%s</span> is not a valid input for <span style='color:black'>%s</span>." % (arg,name)
        flash(Markup(errmsg+"  It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121)."), "error")
        raise

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
        query[qfield] = out

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
def parse_range2(arg, key, parse_singleton=int, parse_endpoint=None):
    if parse_endpoint is None:
        parse_endpoint = parse_singleton
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if type(arg) == parse_singleton:
        return [key, arg]
    if ',' in arg:
        tmp = [parse_range2(a, key, parse_singleton, parse_endpoint) for a in arg.split(',')]
        tmp = [{a[0]: a[1]} for a in tmp]
        return ['$or', tmp]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte'] = parse_endpoint(start)
        if end:
            q['$lte'] = parse_endpoint(end)
        return [key, q]
    else:
        return [key, parse_singleton(arg)]

# Like parse_range2, but to deal with strings which could be rational numbers
# process is a function to apply to arguments after they have been parsed
def parse_range2rat(arg, key, process):
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if QQ_DEC_RE.match(arg):
        return [key, process(arg)]
    if ',' in arg:
        tmp = [parse_range2rat(a, key, process) for a in arg.split(',')]
        tmp = [{a[0]: a[1]} for a in tmp]
        return ['$or', tmp]
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        q = {}
        if start:
            q['$gte'] = process(start)
        if end:
            q['$lte'] = process(end)
        return [key, q]
    else:
        return [key, process(arg)]

# We parse into a list of singletons and pairs, like [[-5,-2], 10, 11, [16,100]]
# If split0, we split ranges [-a,b] that cross 0 into [-a, -1], [1, b]
def parse_range3(arg, split0 = False):
    if type(arg) == str:
        arg = arg.replace(' ', '')
    if ',' in arg:
        return sum([parse_range3(a, split0) for a in arg.split(',')],[])
    elif '-' in arg[1:]:
        ix = arg.index('-', 1)
        start, end = arg[:ix], arg[ix + 1:]
        if start:
            low = ZZ(str(start))
        else:
            raise ValueError("It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")
        if end:
            high = ZZ(str(end))
        else:
            raise ValueError("It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")
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

def integer_options(arg, max_opts=None):
    intervals = parse_range3(arg)
    if max_opts is not None and len(intervals) > max_opts:
        raise ValueError("Too many options.")
    ans = set()
    for interval in intervals:
        if isinstance(interval, list):
            a,b = interval
            if max_opts is not None and len(ans) + b - a + 1 > max_opts:
                raise ValueError("Too many options")
            for n in range(a,b+1):
                ans.add(n)
        elif max_opts is not None and len(ans) == max_opts:
            raise ValueError("Too many options")
        else:
            ans.add(int(interval))
    return sorted(list(ans))

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
        raise ValueError("It needs to be an integer (such as 25), a range of integers (such as 2-10 or 2..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_floats(inp, query, qfield):
    parse_endpoint = float
    def parse_singleton(a):
        if isinstance(a, basestring) and '.' in a:
            prec = len(a) - a.find('.') - 1
        else:
            prec = 0
        a = float(a)
        return {'$gte': a - 0.5 * 10**(-prec), '$lte': a + 0.5 * 10**(-prec)}
    if LIST_FLOAT_RE.match(inp):
        collapse_ors(parse_range2(inp, qfield, parse_singleton, parse_endpoint), query)
    else:
        raise ValueError("It needs to be an float (such as 25 or 25.0), a range of floats (such as 2.1-8.7), or a comma-separated list of these (such as 4,9.2,16 or 4-25.1, 81-121).")

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_element_of(inp, query, qfield, split_interval=False, parse_singleton=int):
    if split_interval:
        options = integer_options(inp, max_opts=split_interval)
        if len(options) == 1:
            query[qfield] = {'$contains': options}
        elif len(options) > 1:
            query[qfield] = {'$or': [{'$contains': [n]} for n in options]}
    else:
        query[qfield] = {'$contains': [parse_singleton(inp)]}

# Parses signed ints as an int and a sign the fields these are stored are passed in as qfield = (sign_field, abs_field)
@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_signed_ints(inp, query, qfield, parse_one=None):
    if parse_one is None: parse_one = lambda x: (int(x.sign()), int(x.abs()))
    sign_field, abs_field = qfield
    if SIGNED_LIST_RE.match(inp):
        parsed = parse_range3(inp, split0 = True)
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
                    if len(x) == 1:
                        s0, abs_D = parse_one(x[0])
                    else:
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

@search_parser(clean_info=True, prep_ranges=True) # see SearchParser.__call__ for actual arguments when calling
def parse_rats(inp, query, qfield, process=None):
    if process is None: process = lambda x: x
    if LIST_RAT_RE.match(inp):
        collapse_ors(parse_range2rat(inp, qfield, process), query)
    else:
        raise ValueError("It needs to be a non-negative rational number (such as 4/3), a range of non-negative rational numbers (such as 2-5/2 or 2.5..10), or a comma-separated list of these (such as 4,9,16 or 4-25, 81-121).")

def _parse_subset(inp, query, qfield, mode, radical, product):
    def add_condition(kwd):
        if qfield in query:
            query[qfield][kwd] = inp
        else:
            query[qfield] = {kwd: inp}
    if mode == 'complement':
        add_condition('$notcontains')
    elif mode == 'subsets':
        # sadly, jsonb GIN indexes don't support <@, so we don't want to use
        # $containedin if we can help it.
        # Even more sadly, even switching to querying on the radical doesn't help,
        # since the query planner still uses an index scan on the primary key.
        #if len(inp) <= 5 and radical is not None:
        #    if radical in query:
        #        raise ValueError("Cannot specify containment and equality simultaneously")
        #    query[radical] = {'$or': [product(X) for X in subsets(inp)]}
        #else:
        add_condition('$containedin')
    elif mode == 'append':
        add_condition('$contains')
    elif mode == 'exact':
        if radical is not None:
            query[radical] = product(inp)
            return
        inp = sorted(inp)
        if inp:
            print inp
            dup_free = [inp[0]]
            for i,x in enumerate(inp[1:]):
                if x != inp[i]:
                    dup_free.append(x)
            print dup_free
        else:
            dup_free = []
        if qfield in query:
            raise ValueError("Cannot specify containment and equality simultaneously")
        query[qfield] = dup_free
    else:
        raise ValueError("Unrecognized mode: programming error in LMFDB code")

@search_parser
def parse_subset(inp, query, qfield, parse_singleton=None, mode='append', radical=None, product=prod):
    # Note that you can do sanity checking using parse_singleton
    # Just raise a ValueError if it fails.
    inp = inp.split(',')
    if parse_singleton is not None:
        inp = [parse_singleton(x) for x in inp]
    _parse_subset(inp, query, qfield, mode, radical, product)

def _multiset_code(n):
    # We encode multiplicities by appending consecutive letters: A, B,..., BA, BB, BC,...
    if n == 0:
        return 'A'
    return ''.join(chr(65+d) for d in reversed(ZZ(n).digits(26)))

def _multiset_encode(L):
    # L should be a list of strings
    distinguished = []
    seen = Counter()
    for x in L:
        distinguished.append(x + _multiset_code(seen[x]))
        seen[x] += 1
    return distinguished

@search_parser(clean_info=True)
def parse_submultiset(inp, query, qfield, mode='append'):
    # Only multisets of strings are supported.
    if mode == 'complement':
        # Searches for multisets whose multiplicity is strictly less than the
        # provided set at each given element.  This notion reduces to
        # the standard complement in the multiplicity free case.
        counts = Counter(inp.split(','))
        query[qfield] = {'$notcontains': [label + _multiset_code(n-1) for label,n in counts.items]}
    else:
        # radical doesn't make sense (you should use subset instead of multiset)
        _parse_subset(_multiset_encode(inp.split(',')), query, qfield, mode, None, None)

@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_primes(inp, query, qfield, mode=None, radical=None):
    format_ok = LIST_POSINT_RE.match(inp)
    if format_ok:
        primes = [int(p) for p in inp.split(',')]
        format_ok = all([ZZ(p).is_prime(proof=False) for p in primes])
    if not format_ok:
        raise ValueError("It needs to be a prime (such as 5), or a comma-separated list of primes (such as 2,3,11).")
    _parse_subset(primes, query, qfield, mode, radical, prod)

@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_bracketed_posints(inp, query, qfield, maxlength=None, exactlength=None, split=True, process=None, check_divisibility=None, keepbrackets=False, extractor=None):
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
            if split:
                query[qfield] = []
            else:
                query[qfield] = ''
            return
        L = [int(a) for a in inp[1:-1].split(',')]
        if check_divisibility == 'decreasing':
            # Check that each entry divides the previous
            #L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i] % L[i+1] != 0:
                    raise ValueError("Each entry must divide the previous, such as [4,2].")
        elif check_divisibility == 'increasing':
            # Check that each entry divides the previous
            # L = [int(a) for a in inp[1:-1].split(',')]
            for i in range(len(L)-1):
                if L[i+1] % L[i] != 0:
                    raise ValueError("Each entry must divide the next, such as [2,4].")
        if process is not None:
            L = [process(a) for a in L]
        if extractor is not None:
            for qf, v in zip(qfield, extractor(L)):
                if qf in query and query[qf] != v:
                    raise ValueError("Inconsistent specification of %s: %s vs %s"%(qf, query[qf], v))
                query[qf] = v
        elif split:
            query[qfield] = L
        else:
            inp = '[%s]'%','.join([str(a) for a in L])
            query[qfield] = inp if keepbrackets else inp[1:-1]

def parse_gap_id(info, query, field='group', name='Group', qfield='group'):
    parse_bracketed_posints(info,query,field, split=False, exactlength=2, keepbrackets=True, name=name, qfield=qfield)

@search_parser(clean_info=True, default_field='galois_group', default_name='Galois group', default_qfield='galois') # see SearchParser.__call__ for actual arguments when calling
def parse_galgrp(inp, query, qfield):
    from lmfdb.transitive_group import complete_group_codes
    try:
        gcs = complete_group_codes(inp)
        nfield, tfield = qfield
        if nfield in query:
            gcs = [t for n,t in gcs if n == query[nfield]]
            if len(gcs) == 0:
                raise ValueError("Degree inconsistent with Galois group.")
            elif len(gcs) == 1:
                query[tfield] = gcs[0]
            else:
                query[tfield] = {'$in': gcs}
        else:
            gcsdict = defaultdict(list)
            for n,t in gcs:
                gcsdict[n].append(t)
            if len(gcsdict) == 1:
                query[nfield] = n # left over from the loop
                if len(gcs) == 1:
                    query[tfield] = t # left over from the loop
                else:
                    query[tfield] = {'$in': gcsdict[n]}
            else:
                options = []
                for n, T in gcsdict.iteritems():
                    if len(T) == 1:
                        options.append({nfield: n, tfield: T[0]})
                    else:
                        options.append({nfield: n, tfield: {'$in': T}})
                collapse_ors(['$or', options], query)
    except NameError:
        raise ValueError("It needs to be a <a title = 'Galois group labels' knowl='nf.galois_group.name'>group label</a>, such as C5 or 5T1, or a comma separated list of such labels.")

def nf_string_to_label(F):  # parse Q, Qsqrt2, Qsqrt-4, Qzeta5, etc
    if F == 'Q':
        return '1.1.1.1'
    if F == 'Qi' or F == 'Q(i)':
        return '2.0.4.1'
    # Change unicode dash with minus sign
    F = F.replace(u'\u2212', '-')
    # remove non-ascii characters from F
    F = F.decode('utf8').encode('ascii', 'ignore')
    if len(F) == 0:
        raise ValueError("Entry for the field was left blank.  You need to enter a field label, field name, or a polynomial.")
    if F[0] == 'Q':
        if '(' in F and ')' in F:
            F=F.replace('(','').replace(')','')
        if F[1:5] in ['sqrt', 'root']:
            try:
                d = ZZ(str(F[5:])).squarefree_part()
            except (TypeError, ValueError):
                d = 0
            if d == 0:
                raise ValueError("After {0}, the remainder must be a nonzero integer.  Use {0}5 or {0}-11 for example.".format(F[:5]))
            if d == 1:
                return '1.1.1.1'
            if d % 4 in [2, 3]:
                D = 4 * d
            else:
                D = d
            absD = D.abs()
            s = 0 if D < 0 else 2
            return '2.%s.%s.1' % (s, str(absD))
        if F[1:5] == 'zeta':
            if '_' in F:
                F = F.replace('_','')
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
        raise ValueError('It is not a valid field name or label, or a defining polynomial.')
    # check if a polynomial was entered
    F = F.replace('X', 'x')
    if 'x' in F:
        F1 = F.replace('^', '**')
        # print F
        from lmfdb.number_fields.number_field import poly_to_field_label
        F1 = poly_to_field_label(F1)
        if F1:
            return F1
        raise ValueError('%s does not define a number field in the database.'%F)
    # Expand out factored labels, like 11.11.11e20.1
    if not re.match(r'\d+\.\d+\.[0-9e_]+\.\d+',F):
        raise ValueError("It must be of the form d.r.D.n, such as 2.2.5.1.")
    parts = F.split(".")
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

@search_parser(clean_info=True) # see SearchParser.__call__ for actual arguments when calling
def parse_container(inp, query, qfield):
    inp = inp.replace('T','t')
    format_ok = re.match(r'^\d+(t\d+)?$',inp)
    if format_ok:
        query[qfield] = str(inp)
    else:
        raise ValueError("You must specify a permutation representation, such as 6T13" )

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
def parse_bool(inp, query, qfield, process=None, blank=[]):
    if inp in blank:
        return
    if process is None: process = lambda x: x
    if inp in ["True", "yes", "1"]:
        query[qfield] = process(True)
    elif inp in ["False", "no", "-1", "0"]:
        query[qfield] = process(False)
    elif inp == "Any":
        # On the Galois groups page, these indicate "All"
        pass
    else:
        raise ValueError("It must be True or False.")

@search_parser # see SearchParser.__call__ for actual arguments when calling
def parse_bool_unknown(inp, query, qfield):
    # yes, no, not_no, not_yes, unknown
    if inp == 'yes':
        query[qfield] = 1
    elif inp == 'not_no':
        query[qfield] = {'$gt' : -1}
    elif inp == 'not_yes':
        query[qfield] = {'$lt' : 1}
    elif inp == 'no':
        query[qfield] = -1
    elif inp == 'unknown':
        query[qfield] = 0

@search_parser
def parse_restricted(inp, query, qfield, allowed, process=None, blank=[]):
    if inp in blank:
        return
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

@search_parser
def parse_equality_constraints(inp, query, qfield, prefix='a', parse_singleton=int, shift=0): # Note that postgres -> index is one-based
    for piece in inp.split(','):
        piece = piece.strip().split('=')
        if len(piece) != 2:
            raise ValueError("It must be a comma separated list of expressions of the form %sN=T"%(prefix))
        n,t = piece
        n = n.strip()
        if not n.startswith(prefix):
            raise ValueError("%s does not start with %s"%(n, prefix))
        n = int(n[len(prefix):]) + shift
        t = parse_singleton(t.strip())
        query[qfield + '.%s'%n] = t

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

@search_parser
def parse_list_start(inp, query, qfield, index_shift=0, parse_singleton=int):
    bparts = BRACKETING_RE.split(inp)
    parts = []
    for part in bparts:
        if not part:
            continue
        if part[0] == '[':
            parts.append(part)
        else:
            subparts = part.split(',')
            for subpart in subparts:
                subpart = subpart.strip()
                if subpart:
                    parts.append(subpart)
    def make_sub_query(part):
        sub_query = {}
        if part[0] == '[':
            ispec = part[1:-1].split(',')
            for i, val in enumerate(ispec):
                key = qfield + '.' + str(i+index_shift)
                sub_query[key] = parse_range2(val, key, parse_singleton)[1]

            # MongoDB is not aware that all the queries above imply that qfield
            # must all contain all those elements, we aid MongoDB by explicitly
            # saying that, and hopefully it will use a multikey index.
            parsed_values = sub_query.values();
            # asking for each value to be in the array
            if parse_singleton is str:
                all_operand = [val for val in parsed_values if  type(val) == parse_singleton and '-' not in val and ','  not in val ]
            else:
                all_operand = [val for val in parsed_values if  type(val) == parse_singleton]

            if len(all_operand) > 0:
                sub_query[qfield] = {'$all' : all_operand};


            # if there are other condition, we can add the first of those
            # conditions the query, in the hope of reducing the search space
            elemMatch_operand = [val for val in parsed_values if type(val) != parse_singleton and type(val) is dict];
            if len(elemMatch_operand) > 0:
                if qfield in sub_query:
                    sub_query[qfield]['$elemMatch'] = elemMatch_operand[0];
                else:
                    sub_query[qfield] = {'$elemMatch' : elemMatch_operand[0]}
            # we could add more than one $elemMatch operand, but 
            # at the moment, the operator $all cannot handle other $ operators 
            # A workaround would be to wrap everything around with an $and
            # but that doesn't end up speeding up things. 
        else:
            key = qfield + '.' + str(index_shift)
            sub_query[key] = parse_range2(part, key, parse_singleton)[1]
        return sub_query
    if len(parts) == 1:
        query.update(make_sub_query(parts[0]))
    else:
        collapse_ors(['$or',[make_sub_query(part) for part in parts]], query)

@search_parser
def parse_string_start(inp, query, qfield, sep=" ", first_field=None, parse_singleton=int, initial_segment=[]):
    bparts = BRACKETING_RE.split(inp)
    parts = []
    for part in bparts:
        if not part:
            continue
        if part[0] == '[':
            parts.append(part)
        else:
            subparts = part.split(',')
            for subpart in subparts:
                subpart = subpart.strip()
                if subpart:
                    parts.append(subpart)
    def make_sub_query(part):
        sub_query = {}
        part = part.strip()
        if not part:
            raise ValueError("Every count specified must be nonempty.")
        if part[0] == '[':
            ispec = initial_segment + [x.strip() for x in part[1:-1].split(',')]
            if not all(ispec):
                raise ValueError("Every count specified must be nonempty.")
            if len(ispec) == 1 and first_field is not None:
                sub_query[first_field] = parse_range2(ispec[0], first_field, parse_singleton)[1]
            else:
                if any('-' in x[1:] for x in ispec):
                    raise ValueError("Ranges not supported.")
                sub_query[qfield] = {'$startswith':' '.join(ispec) + ' '}
        elif first_field is not None:
            sub_query[first_field] = parse_range2(part, first_field, parse_singleton)[1]
        else:
            if '-' in part[1:]:
                raise ValueError("Ranges not supported.")
            sub_query[qfield] = {'$startswith':'%s %s '%(' '.join(initial_segment), part)}
        return sub_query
    if len(parts) == 1:
        query.update(make_sub_query(parts[0]))
    else:
        collapse_ors(['$or',[make_sub_query(part) for part in parts]], query)

def parse_count(info, default=50):
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
