"""
This module implements completeness statements for LMFDB queries.

The interface is through the ``results_complete`` function, which takes as input a table name, a query, the LMFDB db object and optionally a search_array object (used to negate null count overrides that mark results as not complete if they refer to a column that may not all be computed).  It returns as output a triple: whether the results are complete, a string giving a reason (if so), and a string giving caveats (e.g. any dependence on conjectures; None if no caveats).

EXAMPLES::

    sage: from lmfdb import db
    sage: from lmfdb.utils.completeness import results_complete
    sage: results_complete("nf_fields", {"degree": 2, "r2": 1, "class_number": 17}, db)
    (True, 'number fields with signature [0,1], class number at most 100 (except 98)', None)
"""


from collections import defaultdict
from sage.all import factor, prod, factorial, is_prime, prime_range, ZZ, NN, ceil, floor, RealSet, infinity, cached_function, RLF

# This dictionary is filled in the __init__ method of CompletenessCheckers based on the table name;
# specific CompletenessCheckers are created at the bottom of this file.
lookup = {}

def results_complete(table, query, db, search_array=None):
    """
    Determines whether the LMFDB contains all objects satisfying the given query.

    Note that a ``False`` return value does not promise that there are more results, merely that the LMFDB is not guaranteeing that there are no more.

    INPUT:

    - ``table`` -- string, the name of the LMFDB table
    - ``query`` -- dictionary, as parsed by psycodict's db._parse_dict
    - ``db`` -- A db object for accessing the LMFDB (obtained either via lmfdb or lmfdb-lite)
    - ``search_array`` -- a search array object for overriding null counts (optional)

    OUTPUT:

    - ``complete`` -- True if every object satisfying the constraints specified by the query
      will be included in the search results

      False if there may be objects missing (depending on the query, these objects may or may not exist)

      None if the table has not implemented completeness guarantees

    - ``reason`` -- A string, giving a reason why results are complete.  Can be grammatically appended to "The LMFDB contains all".   ``None`` if not ``complete``.

    - ``caveat`` -- A string, giving any caveats (like dependence on GRH or unproven modularity theorems).  May be ``None``.
    """
    if table in lookup:
        return lookup[table].check(query, db, search_array)
    return None, None, None


#################################
# Utility functions             #
#################################

def nullcount_query(query, cols, recursing=False):
    """
    Returns a modified query with all reference to a given list of columns removed, and conditions added that the columns are null.
    """
    if isinstance(query, list): # can happen recursively in $or queries
        return [nullcount_query(D, cols, recursing=True) for D in query]
    query = dict(query)
    for key, value in list(query.items()):
        if key in ["$not", "$and", "$or"]:
            L = nullcount_query(value, cols, recursing=True)
            # Remove empty items
            L = [D for D in L if D]
            if L:
                query[key] = L
            else:
                del query[key]
        else:
            if key.split(".")[0] in cols:
                del query[key]
    if not recursing:
        for col in cols:
            query[col] = None
    return query


def display_opts(L, conj="or"):
    """
    Display a list of options with commas and an or
    """
    L = [str(x) for x in L]
    if len(L) > 1:
        L[-1] = f" {conj} " + L[-1]
    return ", ".join(L)


def tup(a, b):
    """
    range(a, b) as a tuple
    """
    return tuple(range(a,b))


def skip(a, b, L):
    """
    range(a, b) as a tuple, omitting elements of L
    """
    return tuple(x for x in range(a,b) if x not in L)


#################################
# NumberSets and IntegerSets    #
#################################

# These objects add additional functionality on top of Sage's RealSet
# can can be created from a query dictionary

def to_rset(query):
    """
    Create a Sage RealSet from various inputs

    Valid inputs:

    * None (the whole real line)
    * a RealSet or NumberSet
    * a pair (list gives closed interval, tuple open interval)
    * a set (the set of points)
    * a single value (the corresponding point)
    * a query dictionary (the RealSet described by the constraints)
    """
    if query is None:
        return RealSet.interval(-infinity, infinity, lower_closed=False, upper_closed=False)
    if isinstance(query, RealSet):
        return query
    if isinstance(query, NumberSet):
        return query.rset
    if isinstance(query, (list, tuple)) and len(query) == 2: # closed and open intervals
        return RealSet(query)
    if isinstance(query, set):
        return RealSet(*[RealSet.point(x) for x in query])
    if not isinstance(query, dict):
        return RealSet.point(query)
    ans = RealSet((-infinity, infinity))
    for k, val in query.items():
        if k == "$or":
            ans = ans.intersection(RealSet(*[to_rset(D) for D in val]))
        elif k == "$and":
            ans = ans.intersection(to_rset(D) for D in val)
        elif k in ["$not", "$ne"]:
            ans = ans.intersection(to_rset(val).complement())
        elif k == "$lte":
            ans = ans.intersection(RealSet.unbounded_below_closed(val))
        elif k == "$lt":
            ans = ans.intersection(RealSet.unbounded_below_open(val))
        elif k == "$gte":
            ans = ans.intersection(RealSet.unbounded_above_closed(val))
        elif k == "$gt":
            ans = ans.intersection(RealSet.unbounded_above_open(val))
        elif k == "$in":
            ans = ans.intersection(RealSet(*[RealSet.point(x) for x in val]))
        elif k == "$nin":
            ans = ans.intersection(RealSet(*[RealSet.point(x) for x in val]).complement())
        else:
            raise ValueError(f"Unsupported key {k}")
    return ans

def interval_sum(I, J):
    """
    {i + j : i in I, j in J}
    """
    # Neither I nor J can be empty since they arise from a RealSet's normalized intervals
    if not I or not J:
        return (0, 0) # Empty interval
    return RealSet.interval(I.lower() + J.lower(), I.upper() + J.upper(), lower_closed=(I.lower_closed() and J.lower_closed()), upper_closed=(I.upper_closed() and J.upper_closed()))

def interval_neg(I):
    """
    {-i : i in I}
    """
    if not I:
        return (0, 0)
    return RealSet.interval(-I.upper(), -I.lower(), lower_closed=I.upper_closed(), upper_closed=I.lower_closed())

Rneg = RealSet.unbounded_below_closed(0)[0]
Rpos = RealSet.unbounded_above_closed(0)[0]
inf_mone = RealSet.unbounded_below_closed(-1)[0]
one_inf = RealSet.unbounded_above_closed(1)[0]

def interval_mul(I, J):
    """
    {i * j : i in I, j in J}
    """
    if not I or not J or isinstance(I, tuple) and I == (0, 0) or isinstance(J, tuple) and J == (0, 0):
        return (0, 0) # Empty interval

    def _mul(A, B):
        a0, a1, c0, c1 = A.lower(), A.upper(), A.lower_closed(), A.upper_closed()
        b0, b1, d0, d1 = B.lower(), B.upper(), B.lower_closed(), B.upper_closed()
        if a0 >= 0 and b0 >= 0: # both positive
            a1b1 = 0 if a1 == 0 or b1 == 0 else a1 * b1 # one could be infinity
            return RealSet.interval(a0 * b0, a1b1, lower_closed=c0 and d0, upper_closed=c1 and d1)
        elif a1 <= 0 and b0 >= 0: # A negative
            a0b1 = 0 if a0 == 0 or b1 == 0 else a0 * b1
            a1b0 = 0 if a1 == 0 or b0 == 0 else a1 * b0
            return RealSet.interval(a0b1, a1b0, lower_closed=c0 and d1, upper_closed=c1 and d0)
        elif a0 >= 0 and b1 <= 0: # B negative
            a1b0 = 0 if a1 == 0 or b0 == 0 else a1 * b0
            a0b1 = 0 if a0 == 0 or b1 == 0 else a0 * b1
            return RealSet.interval(a1b0, a0b1, lower_closed=c1 and d0, upper_closed=c0 and d1)
        else: # both negative
            a0b0 = 0 if a0 == 0 or b0 == 0 else a0 * b0
            return RealSet.interval(a1 * b1, a0b0, lower_closed=c1 and d1, upper_closed=c0 and d0)

    Ineg = I.intersection(Rneg)
    Ipos = I.intersection(Rpos)
    Jneg = J.intersection(Rneg)
    Jpos = J.intersection(Rpos)
    return RealSet(_mul(Ineg, Jneg), _mul(Ineg, Jpos), _mul(Ipos, Jneg), _mul(Ipos, Jpos))

def interval_inv(I):
    """
    {1 / i : i in I, i != 0}
    """
    if not I or I.lower() == I.upper() == 0:
        return (0, 0) # empty interval
    Ineg = I.intersection(Rneg)
    Ipos = I.intersection(Rpos)
    ans = []
    if Ineg.lower() != 0:
        if Ineg.upper() == 0:
            a, c = -infinity, False
        else:
            a, c = 1 / Ineg.upper(), Ineg.upper_closed()
        if Ineg.lower() == -infinity:
            b, d = 0, False
        else:
            b, d = 1 / Ineg.lower(), Ineg.lower_closed()
        ans.append(RealSet.interval(a, b, lower_closed=c, upper_closed=d)[0])
    if Ipos.upper() != 0:
        if Ipos.lower() == 0:
            b, d = infinity, False
        else:
            b, d = 1 / Ipos.lower(), Ipos.lower_closed()
        if Ipos.upper() == infinity:
            a, c = 0, False
        else:
            a, c = 1 / Ipos.upper(), Ipos.upper_closed()
        ans.append(RealSet.interval(a, b, lower_closed=c, upper_closed=d)[0])
    return RealSet(*ans)

def interval_abs(I):
    """
    {|i| : i in I}
    """
    return RealSet(Rpos.intersection(I), interval_neg(Rneg.intersection(I)))

class NumberSet:
    """
    A set of real numbers, as specified either as a number or a query dictionary.

    Supports arithmetic operations, union, intersection and inequalities.  The subclass IntegerSet supports iteration.
    """
    def __init__(self, x):
        self.rset = to_rset(x)

    def __repr__(self):
        return repr(self.rset)

    def __bool__(self):
        return bool(self.rset)

    def __add__(self, other):
        return self.__class__(RealSet(*[interval_sum(I, J) for I in self.rset for J in other.rset]))

    def __neg__(self):
        return self.__class__(RealSet(*[interval_neg(I) for I in self.rset]))

    def __sub__(self, other):
        return self.__class__(RealSet(*[interval_sum(I, interval_neg(J)[0]) for I in self.rset for J in other.rset]))

    def __mul__(self, other):
        """
        A set containing all products of elements in this set.  The result will be sharp for real sets,
        but may be proper for integer sets (for example, [2,4] * [2,4] = [4,16] and contains 5,7,10,11,13,14,15)
        """
        return self.__class__(RealSet(*[interval_mul(I, J) for I in self.rset for J in other.rset]))

    def __invert__(self):
        """
        A set containing the inverse of elements in this set.  For utility, this will always be a NumberSet,
        even if the input is an IntegerSet.

        We never raise a zero division error, instead implicitly intersecting with the complement of 0
        """
        return NumberSet(RealSet(*[interval_inv(I) for I in self.rset]))

    def __truediv__(self, other):
        """
        A set containing the quotients of elements in this set.

        We never raise a zero division error, instead implicitly intersecting other with the complement of 0
        """
        return NumberSet(
            RealSet(*[interval_mul(I, interval_inv(J.intersection(Rneg))[0])
                      for I in self.rset for J in other.rset]).union(
            RealSet(*[interval_mul(I, interval_inv(J.intersection(Rpos))[0])
                      for I in self.rset for J in other.rset])))

    def __abs__(self):
        return self.__class__(RealSet(*[interval_abs(I) for I in self.rset]))

    def pow_cap(self, other, k):
        """
        Intersection of self with (-oo,max(other)^k]
        """
        if not other.rset:
            return other
        a = other.rset.sup()
        if a is infinity:
            return self
        return self.intersection(top(a**k))

    def union(self, *others):
        return self.__class__(self.rset.union(*[other.rset for other in others]))

    def intersection(self, *others):
        return self.__class__(self.rset.intersection(*[other.rset for other in others]))

    def difference(self, *others):
        return self.__class__(self.rset.difference(*[other.rset for other in others]))

    def is_subset(self, other):
        return self.rset.is_subset(other.rset)

    def __le__(self, other):
        """
        Every element of this set is less than or equal to every element of the other set
        """
        if not self.rset or not other.rset:
            return True
        a = self.rset[-1].upper()
        b = other.rset[0].lower()
        return a <= b

    def __lt__(self, other):
        """
        Every element of this set is less than every element of the other set
        """
        if not self.rset or not other.rset:
            return True
        a = self.rset[-1].upper()
        b = other.rset[0].lower()
        return a < b or a == b and (not self.rset[-1].upper_closed() or not other.rset[0].lower_closed())

    def __ge__(self, other):
        """
        Every element of this set is greater than or equal to every element of the other set
        """
        return other.__le__(self)

    def __gt__(self, other):
        """
        Every element of this set is greater than every element of the other set
        """
        return other.__gt__(self)

    def bounded(self, a, b=None):
        """
        If only a given, whether contained in (-oo, a].

        If a and b given, whether contained in [a, b]
        """
        if b is None:
            lower_bound, upper_bound = -infinity, a
        else:
            lower_bound, upper_bound = a, b
        S = self.rset
        return not S or lower_bound <= S[0].lower() and S[-1].upper() <= upper_bound

    def restricted(self):
        """
        Not the whole real line
        """
        return (len(list(self.rset)), self.rset.inf(), self.rset.sup()) != (1, -infinity, infinity)

def integer_normalize(S):
    """
    INPUT:

    - ``S`` -- a RealSet (normalized in the sense of real sets)

    Output:

    A RealSet ``T`` so that the set of integer points of S and T are the same, and

        - all intervals of ``T`` have endpoints that are either infinite or integral and closed
        - successive intervals have an integer in between
    """
    T = []
    for I in S:
        if I.lower() is -infinity:
            a, c = -infinity, False
        else:
            a, c = ceil(I.lower()), True
            if a == I.lower() and not I.lower_closed():
                a += 1
        if I.upper() is infinity:
            b, d = infinity, False
        else:
            b, d = floor(I.upper()), True
            if b == I.upper() and not I.upper_closed():
                b -= 1
        if a <= b:
            Iint = RealSet.interval(a, b, lower_closed=c, upper_closed=d)[0]
            # InternalRealIntervals are UniqueRepresentation, and 11.0 == 11, so we get annoying floats when doing interval division
            # We solve this by replacing _lower and _upper with integral versions
            if a is not -infinity:
                Iint._lower = RLF(a)
            if b is not infinity:
                Iint._upper = RLF(b)
            T.append(Iint)
    if not T:
        return RealSet()
    TT = []
    cur = T[0]
    for I in T[1:]:
        if I.lower() - cur.upper() > 1:
            TT.append(cur)
            cur = I
        else:
            cur = RealSet.interval(cur.lower(), I.upper(), lower_closed=cur.lower_closed(), upper_closed=I.upper_closed())[0]
    TT.append(cur)
    return RealSet(*TT)

inf_mone = RealSet.unbounded_below_closed(-1)[0]
one_inf = RealSet.unbounded_above_closed(1)[0]

class IntegerSet(NumberSet):
    """
    The set of integer points in within a real set
    """
    def __init__(self, x):
        self.rset = integer_normalize(to_rset(x))

    def __truediv__(self, other):
        """
        An interval containing all integer quotients.

        EXAMPLES::

            sage: from lmfdb.utils.completeness import IntegerSet
            sage: A = IntegerSet([2, 4]); A / A
            [1, 2]
            sage: B = IntegerSet([6, 9]); B / A
            [2, 4]
        """
        if isinstance(other, IntegerSet):
            return self.__class__(
                RealSet(*[interval_mul(I, interval_inv(J.intersection(inf_mone))[0])
                          for I in self.rset for J in other.rset]).union(
                RealSet(*[interval_mul(I, interval_inv(J.intersection(one_inf))[0])
                          for I in self.rset for J in other.rset])))

        return super().__div__(other)

    def min(self):
        return self.rset.inf()

    def max(self):
        return self.rset.sup()

    def __iter__(self):
        for I in self.rset:
            if I.lower() is -infinity:
                if I.upper() is infinity:
                    yield from ZZ
                else:
                    b = I.upper()
                    for n in NN:
                        yield b - n
            elif I.upper() is infinity:
                a = I.lower()
                for n in NN:
                    yield a + n
            else:
                yield from range(I.lower(), I.upper() + 1)

    def stickelberger(self, n, r2opts):
        """
        INPUT:

        - ``n`` -- the degree, an integer
        - ``r2opts`` -- an iterable with r2 options

        OUTPUT:

        An iterator over the possible discriminants within this set
        """
        if all(r2 % 2 == 1 for r2 in r2opts):
            mod4 = [0,3]
            div4 = [1,2]
        elif all(r2 % 2 == 0 for r2 in r2opts):
            mod4 = [0,1]
            div4 = [2,3]
        else:
            mod4 = [0,1,3]
            div4 = [1,2,3]
        for m in self:
            if m % 4 in mod4:
                if n == 2 and m % 4 == 0 and (m // 4) % 4 not in div4:
                    continue
                F = factor(m)
                if n != 2 or all(e == 1 or p == 2 and e <= 3 for (p,e) in F):
                    yield tuple(p for (p,e) in F)

    def is_finite(self):
        return self.rset.inf() is not -infinity and self.rset.sup() is not infinity

    def bound_under(self, func):
        """
        INPUT:

        - ``func`` -- an iterable of pairs (I, v) where I is valid input to IntegerSet and v is a real number

        OUTPUT:

        If this set is contained in the union of the I, the minimum of the values corresponding to the I used to greedily cover this set.  If this set is not contained in the union of the I, returns None.
        """
        M = infinity
        for I, v in func:
            I = IntegerSet(I)
            O = self.intersection(I)
            if O:
                M = min(M, v)
                self = self.difference(O)
            if not self.rset:
                return M

def top(x, cls=IntegerSet):
    """
    Utility function returnin (-oo, x]
    """
    return cls(RealSet.interval(-infinity, x, lower_closed=False, upper_closed=True))

def bottom(x, cls=IntegerSet):
    """
    Utility function returning [x, oo)
    """
    return cls(RealSet.interval(x, infinity, lower_closed=True, upper_closed=False))

#################################
# Completeness checker          #
#################################

class CompletenessChecker:
    """
    A class associated to an LMFDB designed to check whether search queries are complete.

    The main entrypoint is the ``check`` function.

    INPUT:

    - ``table`` -- string, the name of the LMFDB table
    - ``checkers`` -- a list of tuples, each of the form (cols, test), (cols, test, reason), (cols, test, reason, caveat) or (cols, test, reason, caveat, filter).
      ``cols`` can be a single column name or a tuple of columns names.
      ``reason`` is a string that describes the reason this query is complete
      ``caveat`` is a string that describes any conjectures used, or None
      ``filter`` is a function that takes the query as input and determines
                 whether this test should be run
      ``test`` will be run if all columns are present in the query and the filter (if present) passes;
               the input will be the correponding values in the query dictionary.
      The check returns true when any test passes.

      If all checkers have length 2 (just cols and test) will pass the full query dictionary to the __call__ method (after parsing through $or, $and, $not).  Otherwise, will extract the values of the columns before passing into __call__
    """
    def __init__(self, table, checkers, fill=[], null_override=[]):
        self.table = table
        lookup[table] = self
        self.extract = not all(len(check) == 2 for check in checkers)
        for i, check in enumerate(checkers):
            if len(check) == 2:
                cols, test = check
                reason = caveat = None
                def filt(query): return True
            elif len(check) == 3:
                cols, test, reason = check
                caveat = None
                def filt(query): return True
            elif len(check) == 4:
                cols, test, reason, caveat = check
                def filt(query): return True
            else:
                cols, test, reason, caveat, filt = check
            if not isinstance(cols, tuple):
                cols = (cols,)
            checkers[i] = (cols, test, reason, caveat, filt)
        self.checkers = checkers
        self.fill = fill
        self.null_override = null_override

    def _standardize(self, query):
        """
        Different queries can yield equivalent logical expressions.
        If ``$or`` is present, this function moves everything into the ``$or``
        for simplified processing.
        """
        query = dict(query)

        def merge(v1, v2):
            if v1 is None:
                return v2
            # TODO: Make this more robust
            if isinstance(v1, dict) and isinstance(v2, dict):
                v2 = dict(v2)
                v2.update(v1)
                return v2
            if isinstance(v1, dict):
                # Actually need to check that v2 satisfies v1
                return v2
            if isinstance(v2, dict):
                # Need to check that v1 satisfies v2
                return v1
            if v1 == v2:
                return v2
            # Need a way to show incompatibility
        if "$or" in query:
            # Should probably recurse here
            opts = query["$or"]
            for k, v in query.items():
                if k != "$or":
                    for D in opts:
                        D[k] = merge(D.get(k), v)
            query = {"$or": opts}
        # Need to handle $and, $not as well
        return query

    def check(self, query, db, search_array=None):
        if not query:
            return False, None, None
        query = self._standardize(query)
        if "$or" in query:
            reasons, caveats = set(), set()
            for D in query["$or"]:
                D = dict(D)
                assert len(set(D).intersection(query)) == 0
                D.update(query)
                del D["$or"]
                ok, reason, caveat = self.check(D, db, search_array)
                if not ok:
                    return False, None, None
                reasons.add(reason)
                if caveat is not None:
                    caveats.add(caveat)
            if caveats:
                caveats = ", ".join(caveats)
            else:
                caveats = None
            return True, "; ".join(reasons), caveats
        if "$and" in query:
            assert len(query) == 1
            for D in query["$and"]:
                ok, reason, caveat = self.check(D, db, search_array)
                if ok:
                    return ok, reason, caveat
            return False, None, None
        # Ignore $not: it just imposes additional constraints, and if we're complete without it then we're complete.  Note that it is accounted for in _columns_searched
        table = db[self.table]
        nulls = table.stats.null_counts()
        if nulls:
            search_columns = set(nulls).intersection(table._columns_searched(query)).difference(self.null_override)
            # Ignore columns based on search_array
            if search_array is not None:
                search_columns = {col for col in search_columns if search_array.null_column_explanations.get(col) is not False}
            if search_columns and table.exists(nullcount_query(query, search_columns)):
                # Query referred to a column where not all data was computed, so we cannot guarantee completeness
                return False, None, None
        for fill in self.fill:
            fill(query)
        for cols, test, reason, caveat, filt in self.checkers:
            if all(col in query for col in cols) and filt(query):
                if self.extract:
                    # In this case, we use the reason specified in the list of checkers
                    if test(db, [query[col] for col in cols]):
                        return True, reason, caveat
                else:
                    # Here we delegate the reason and caveat to the test function
                    return test(db, query)
        return False, None, None

#################################
# Column tests                  #
#################################

# These objects are designed to be used as inputs for the ``test`` argument of the ``check`` method on a CompletnessChecker

class ColTest:
    pass

class Bound(ColTest):
    """
    Check that the inputs lie in a box.
    """
    def __init__(self, *bounds, cls=IntegerSet):
        self.cls = cls
        self.bounds = [cls(b) if isinstance(b, (list, tuple, RealSet)) else cls(RealSet.unbounded_below_closed(b)) for b in bounds]

    def __call__(self, db, Ds):
        return all(self.cls(D).is_subset(B) for D, B in zip(Ds, self.bounds))

class CBound(Bound):
    """
    Given constraints on a set of values, check that the last value lies in an interval

    Note that overlapping Bound boxes is better when applicable,
    since this test will only match queries where the constraints are specified exactly
    """
    def __init__(self, *constraints, cls=IntegerSet):
        self.constraints = tuple(constraints[:-1])
        super().__init__(constraints[-1], cls=cls)

    def __call__(self, db, Ds):
        return self.constraints == tuple(Ds[:-1]) and super().__call__(db, [Ds[-1]])

class PrimeBound(Bound):
    def __call__(self, db, Ds):
        Ds = [self.cls(D) for D in Ds]
        return all(D.is_finite() and all(is_prime(p) for p in D) for D in Ds)

class Smooth(ColTest):
    def __init__(self, M, cls=IntegerSet):
        self.cls = cls
        self.M = M

    def __call__(self, db, ms):
        M = self.M
        P = prime_range(M)

        def is_smooth(n):
            return -M < n < M or n == prod(p**ZZ(n).valuation(p) for p in P)
        return all(is_smooth(n) for n in self.cls(ms[0]))

class Specific(ColTest):
    def __init__(self, *constraints):
        self.constraints = constraints

    def __call__(self, db, Ds):
        return all(D in constraint for (D, constraint) in zip(Ds, self.constraints))


class CPrimeBound(CBound):
    """
    Similar to CBound, but requires Ds to all be prime
    """
    def __call__(self, db, Ds):
        last = self.cls(Ds[-1])
        return last.is_finite() and super().__call__(db, Ds) and all(is_prime(p) for p in last)

#################################
# Fillers                       #
#################################

# These classes are used to fill entries in for a query dictionary that can be derived from other entries

class FieldLabelFiller:
    def __init__(self, ec):
        self.ec = ec

    def __call__(self, query):
        if "field_label" in query:
            label = query["field_label"]
            if isinstance(label, str) and label.count(".") == 3:
                d, r, D, i = label.split(".")
                if d.isdigit() and r.isdigit() and D.isdigit():
                    if "signature" not in query:
                        query["signature"] = [int(d), int(r)]
                    if self.ec and "abs_disc" not in query:
                        query["abs_disc"] = int(D)
                    elif not self.ec and "field_disc" not in query:
                        query["field_disc"] = -int(D)


class MulFiller:
    def __init__(self, n, e, f, backfill=False, cls=IntegerSet):
        self.n, self.e, self.f = n, e, f
        self.backfill, self.cls = backfill, cls

    def __call__(self, query):
        C = self.cls
        n, e, f = self.n, self.e, self.f
        if e in query and f in query:
            query[n] = C(query.get(n)).intersection(C(query[e]) * C(query[f]))
        if self.backfill:
            if n in query and e in query:
                query[f] = C(query.get(f)).intersection(C(query[n]) / C(query[e]))
            if n in query and f in query:
                query[e] = C(query.get(e)).intersection(C(query[n]) / C(query[f]))


class SumFiller:
    def __init__(self, a, b, c, backfill=False, cls=IntegerSet):
        self.a, self.b, self.c = a, b, c
        self.backfill, self.cls = backfill, cls

    def __call__(self, query):
        C = self.cls
        a, b, c = self.a, self.b, self.c
        if b in query and c in query:
            query[a] = C(query.get(a)).intersection(C(query[b]) + C(query[c]))
        if self.backfill:
            if a in query and b in query:
                query[c] = C(query.get(c)).intersection(C(query[a]) - C(query[b]))
            if a in query and c in query:
                query[b] = C(query.get(b)).intersection(C(query[a]) - C(query[c]))


class CMFFiller:
    def __call__(self, query):
        C = IntegerSet
        if query.get("projective_image"):
            query["weight"] = 1
        # TODO: set weigt/level from analytic conductor
        N, k = query.get("level"), query.get("weight")
        if N is not None and k is not None:
            query["Nk2"] = C(N) * C(k) * C(k)
        if query.get("char_orbit_index") == 1 or query.get("prim_orbit_index") == 1:
            query["char_order"] = 1


#################################
# Specific CompletenessCheckers #
#################################

# This section contains completeness checkers tailored for specific LMFDB tables,
# for cases when the previous generic options are not sufficient.

#### Maass forms ####

# We cache the intervals for Maass forms, since we'll need to reimplement this function anyway if the db gets expanded (any will likely include other weights/characters)
maxR = {
    1: 184.9239,
    2: 25.1193,
    3: 24.9526,
    5: 24.3767,
    6: 25.8128,
    7: 24.8119,
    10: 26.2206,
    11: 25.1115,
    13: 24.1069,
    14: 22.4246,
    15: 21.8123,
    17: 21.6894,
    19: 20.5855,
    21: 19.9897,
    22: 19.4628,
    23: 19.5899,
    26: 19.0296,
    29: 17.8751,
    30: 18.4508,
    31: 18.0663,
    33: 18.3093,
    34: 18.1504,
    35: 18.2470,
    37: 15.9750,
    38: 17.8932,
    39: 17.6166,
    41: 15.9529,
    42: 17.2648,
    43: 14.7934,
    46: 16.9195,
    47: 13.9142,
    51: 16.5449,
    53: 14.1707,
    55: 16.1894,
    57: 16.2665,
    58: 16.1047,
    59: 12.8281,
    61: 11.3236,
    62: 15.9467,
    65: 16.0760,
    66: 15.7452,
    67: 10.2802,
    69: 15.8350,
    70: 15.5741,
    71: 9.6346,
    73: 8.7967,
    74: 15.5368,
    77: 15.7849,
    78: 15.3004,
    79: 6.9669,
    82: 15.3011,
    83: 7.3430,
    85: 15.5549,
    86: 15.1230,
    87: 15.2365,
    89: 6.1712,
    91: 15.1940,
    93: 15.0326,
    94: 15.2433,
    95: 15.1521,
    97: 5.8923,
    101: 7.2205,
    102: 14.6673,
    103: 5.6533,
    105: 14.7330
}
class MaassBound(ColTest):
    def __call__(self, db, query):
        level = IntegerSet(query["level"])
        spectral_parameter = NumberSet(query["spectral_parameter"])
        if level.is_finite() and level.max() <= 105:
            levels = list(level)
            if levels:
                if all(N in maxR for N in levels):
                    Rbound = min(maxR[N] for N in levels)
                    if spectral_parameter.bounded(Rbound):
                        levels = ", ".join(str(N) for N in levels)
                        return True, f"Maass forms with level {levels} and spectral parameter at most {Rbound:.4f}", None
            else:
                return True, "Maass forms with specified level (empty)", None
        return False, None, None


#### Hilbert modular forms ####

@cached_function
def hmf_bounds(db):
    return {label: D["max"] for (label, D) in db.hmf_forms.stats.numstats("level_norm", "field_label").items()}


class HMFBound(ColTest):
    def __call__(self, db, query):
        bounds = hmf_bounds(db)
        level_norm = IntegerSet(query["level_norm"])
        cols = db.hmf_forms._columns_searched(query)
        caveat = []
        if "is_base_change" in cols:
            caveat.append("positive base change information computed heuristically")
        if "is_CM" in cols:
            caveat.append("positive CM information computed heuristically")
        caveat = ", ".join(caveat)
        if not caveat:
            caveat = None
        if "field_label" in query:
            label = query["field_label"]
            M = None
            if isinstance(label, str):
                M = bounds[label]
                labels = label
            elif isinstance(label, dict) and "$in" in label and label["$in"] and all(lab in bounds for lab in label["$in"]):
                M = min(bounds[lab] for lab in label["$in"])
                labels = ", ".join(label["$in"])
            if M is not None and level_norm.bounded(M):
                return True, f"Hilbert modular forms over {labels} of level norm at most {M}", caveat
        # Missing discriminants in degree
        # 2: up to 497 except 253, 257, 264, 309, 312
        # 3: everything up to disc 1957 (next 2021)
        # 4: everything up to disc 19821 (next 20032)
        # 5: everything up to disc 195829 (next 202817)
        # 6: everything up to disc 1997632 (next 2115281)
        by_deg = {2: 252, 3: 2020, 4: 20031, 5: 202816, 6: 2115280}
        if query.get("disc") is not None and query.get("deg") is not None:
            disc = IntegerSet(query["disc"])
            deg = IntegerSet(query["deg"])
            if deg.is_subset(IntegerSet([2,6])): #################
                deg = list(deg)
                if not deg:
                    return True, "Hilbert modular forms satisfying query (no matching degrees)", None
                M = min(by_deg[n] for n in deg)
                if disc.bounded(M):
                    # query specifies only fields where we have HMFs,
                    # now we need to find the list of discriminants satisfying the query
                    allowed = IntegerSet({"$in":set(int(label.split(".")[2]) for label in bounds)})
                    discs = list(disc.intersection(allowed))
                    fields = [label for label in bounds if int(label.split(".")[0]) in deg and int(label.split(".")[2]) in discs]
                    if fields:
                        M = min(bounds[label] for label in fields)
                        if level_norm.bounded(M):
                            fields.sort(key=lambda label: [int(x) for x in label.split(".")])
                            labels = ", ".join(fields)
                            return True, f"Hilbert modular forms over {labels} of level norm at most {M}", caveat
                    else:
                        return True, "Hilbert modular forms satisfying the query (no matching fields)", caveat
        return False, None, None


#### Bianchi modular forms and elliptic curves over number fields ####

class BianchiBound(ColTest):
    def __init__(self, ec):
        self.ec = ec

    def __call__(self, db, query):
        if self.ec:
            sig = query.get("signature")
            if not (isinstance(sig, list) and len(sig) == 2):
                return False, None, None
            n, r = sig
            D = IntegerSet(query.get("abs_disc")).intersection(bottom(3))
            N = IntegerSet(query["conductor_norm"])
            caveat = "Only modular elliptic curves are included"

            def reason(n, r, D, M):
                if isinstance(D, int):
                    Ds = str(D)
                elif D.max() == D.min():
                    Ds = str(D.max())
                else:
                    Ds = f" in {D}"
                if n == 2 and r == 0:
                    return f"elliptic curves with conductor norm at most {M} over imaginary quadratic fields with absolute discriminant {Ds}"
                if r == n:
                    if n == 2:
                        return f"elliptic curves with conductor norm at most {M} over real quadratic fields with discriminant {Ds}"
                    if n == 3:
                        adj = "cubic"
                    elif n == 4:
                        adj = "quartic"
                    elif n == 5:
                        adj = "quintic"
                    elif n == 6:
                        adj = "sextic"
                    return f"elliptic curves with conductor norm at most {M} over totally real {adj} fields with discriminant {Ds}"
                if n == 3 and r == 1:
                    return f"elliptic curves over 3.1.23.1 with conductor norm at most {M}"
        else:
            n, r = 2, 0
            D = (-IntegerSet(query.get("field_disc"))).intersection(bottom(3))
            N = IntegerSet(query["level_norm"])
            caveat = None

            def reason(n, r, D, M):
                if not D:
                    return "Bianchi modular forms with specified discriminant (no fields with given discriminants)"
                if D.max() == D.min():
                    Ds = str(D.max())
                else:
                    Ds = f"in {D}"
                return f"Bianchi modular forms with level norm at most {M} over imaginary quadratic fields with absolute discriminant {Ds}"
        if n == 2 and r == 0: # imaginary quadratic, either EC or BMF
            M = D.bound_under([
                (top(3), 150000), # 3
                (4, 100000), # 4
                ([5,14], 50000), # 7,8,11
                (15, 1000), # 15
                ([16,19], 15000), # 19
                (20, 1000), # 20
                ([21,23], 3000), # 23
                (24, 1000), # 24
                ([25,34], 5000), # 31
                ([35,40], 1000), # 35,39,40
                ([41,46], 15000), # 43
                ([47, 59], 1000), # 47,51,52,55,56,59
                ([60, 67], 10000), # 67
                ([68, 120], 1000),
                ([121, 159], 100),
                ([160, 163], 5000), # 163
                ([164, 702], 100), # 703 is the first missing
            ])
            if M is None or not N.bounded(M):
                return False, None, None
            return True, reason(n, r, D, M), caveat
        if r == n: # totally real, EC
            if n == 2:
                return D.bounded(497) and N.bounded(5000), reason(2, 2, 497, 5000), None
            if n == 3:
                return D.bounded(1957) and N.bounded(2059), reason(3, 3, 1957, 2059), None
            if n == 4:
                return D.bounded(19821) and N.bounded(4091), reason(4, 4, 19821, 4091), None
            if n == 5:
                return D.bounded(195829) and N.bounded(1013), reason(5, 5, 195829, 1013), None
            if n == 6:
                return D.bounded(1997632) and N.bounded(961), reason(6, 6, 1997632, 961), None
        if n == 3 and r == 1: # mixed case, EC
            return D.bounded(30) and N.bounded(20000), reason(3, 1, 23, 20000), None
        return False, None, None


#### Number fields ####

class NFBound(ColTest):
    def __init__(self):
        # maxD[n][r2] is an integer M so that we have completeness in signature [n-2*r2, r2] as long as the absolute discriminant is at most M.
        self._maxD = [
            None, # n=0
            None, # n=1
            [2*10**6, 2*10**6], # n=2
            [150**3, 150**3], # n=3
            [10**7, 4*10**6, 4*10**6], # n=4
            [10**8, 12*10**6, 12*10**6], # n=5
            [28**6, 10**7, 10**7, 10**7], # n=6
            [214942297, 2*10**8, 2*10**8, 2*10**8], # n=7
            [17**8, 79259702, 20829049, 5726300, 1656109], # n=8
            [15**9, 27316369, 27316369, 146723910, 39657561], # n=9
            [190612177]*6, # n=10
            [5154074557]*6, # n=11
            [37250695278]*7, # n=12
        ]

        # num_trans[n] is the number of transitive permutation groups in degree n
        self._num_trans = [0, 1, 1, 2, 5, 5, 16, 7, 50, 34, 45, 8, 301, 9, 63, 104, 1954, 10, 983, 8, 1117, 164, 59, 7]

        # ab.get(n, {1}) gives the values of t so that nTt is abelian (for n<48)
        self._ab = {
            4: {1,2},
            8: {1,2,3},
            9: {1,2},
            12: {1,2},
            16: {1,2,3,4,5},
            18: {1,2},
            20: {1,3},
            24: {1,2,3},
            25: {1,2},
            27: {1,2,4},
            28: {1,2},
            32: {32,33,34,36,37,39,43},
            36: {1,2,3,4},
            40: {1,2,7},
            44: {1,2},
            45: {1,2}}

        # nab_gal[n] gives the values of t so that nTt is nonabelian of order n (for n<24)
        self._nab_gal = {
            6: {2},
            8: {4,5},
            10: {2},
            12: {3,4,5},
            14: {2},
            16: {6,7,8,9,10,11,12,13,14},
            18: {3,4,5},
            20: {2,4,5},
            21: {2},
            22: {2}}

        # nsolv.get(n, set()) gives the values of t so that nTt is nonsolvable (for n<24)
        self._nsolv = {
            5: {4,5},
            6: {12,14,15,16},
            7: {5,6,7},
            8: {37,43,48,49,50},
            9: {27,32,33,34},
            10: {7,11,12,13,22,26,30,31,32,34,35,36,37,38,39,40,41,42,43,44,45},
            11: {5,6,7,8},
            12: {33,74,75,76,123,124,179,180,181,182,183,218,219,220,230,255,256,257,269,270,272,277,278,279,285,286,287,288,293,295,296,297,298,299,300,301},
            13: {7,8,9},
            14: {10,16,17,19,30,33,34,39,42,43,46,47,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63},
            15: {5,10,15,16,20,21,22,23,24,28,29,47,53,61,62,63,69,70,72,76,77,78,83,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104},
            16: {713,714,715,1035,1036,1080,1081,1328,1329,1504,1505,1506,1507,1508,1653,1654,1753,1801,1802,1803,1804,1805,1838,1839,1840,1842,1843,1844,1861,1873,1878,1882,1883,1902,1903,1906,1916,1938,1940,1944,1945,1946,1948,1949,1950,1951,1952,1953,1954},
            17: {6,7,8,9,10},
            18: {90,144,145,146,227,260,261,262,362,363,364,365,377,427,452,468,596,664,665,666,722,723,736,787,788,789,790,791,802,845,846,847,848,849,855,856,886,887,888,890,897,898,899,900,911,913,914,925,933,934,935,936,937,938,946,947,948,949,950,952,953,954,955,956,957,958,959,960,961,962,963,964,965,966,967,968,969,970,971,972,973,974,975,976,977,978,979,980,981,982,983},
            19: {7,8},
            20: {15,30,31,32,35,36,62,63,64,65,66,70,89,116,117,118,119,120,123,145,146,147,148,149,150,151,152,172,174,175,176,177,197,198,199,200,201,202,203,204,205,206,207,208,217,218,219,220,221,222,223,224,225,226,227,228,229,230,264,265,266,267,272,273,274,275,276,277,278,279,280,281,283,284,285,287,288,289,290,291,358,362,363,365,366,367,368,369,370,373,375,376,452,453,456,457,458,459,460,461,466,467,468,531,532,539,540,541,542,543,544,545,546,547,548,555,556,558,560,561,562,564,565,566,567,568,569,570,571,573,635,654,655,656,657,658,659,663,664,665,666,667,668,669,671,672,673,674,675,676,677,679,680,681,682,684,685,686,687,688,689,690,691,692,693,694,695,752,753,754,781,790,791,792,793,794,795,796,797,798,799,800,801,802,803,804,805,806,807,808,809,810,812,855,856,857,858,885,886,887,888,912,913,914,915,916,917,918,919,920,921,922,933,934,935,936,937,938,939,947,948,949,950,951,952,953,954,962,963,964,965,966,967,968,969,970,971,972,973,974,975,976,977,978,981,985,989,990,991,992,993,994,995,996,997,998,999,1000,1001,1006,1007,1008,1009,1010,1011,1012,1013,1015,1016,1019,1021,1022,1023,1024,1025,1026,1027,1028,1029,1030,1031,1033,1034,1035,1036,1037,1038,1039,1040,1041,1042,1044,1045,1046,1047,1048,1052,1053,1054,1058,1059,1060,1061,1062,1063,1064,1065,1066,1068,1069,1070,1071,1072,1073,1074,1075,1076,1077,1078,1079,1080,1081,1082,1083,1084,1085,1086,1087,1088,1089,1090,1091,1092,1093,1094,1095,1096,1097,1098,1099,1100,1101,1102,1103,1104,1105,1106,1107,1108,1109,1110,1111,1112,1113,1114,1115,1116,1117},
            21: {14,20,22,27,33,38,44,56,57,58,67,74,85,91,103,104,111,113,115,118,119,121,125,126,128,129,130,132,135,136,138,139,140,141,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164},
            22: {13,14,22,26,27,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59},
            23: {5,6,7}
        }

        # rdgrd[n][t] gives a ratio r so that grd <= rd^(1/r) for fields with Galois group nTt
        # See https://arxiv.org/abs/1208.5806
        self._rdgrd = [
            [],
            [1], # 1
            [1], # 2
            [1, 2/3], # 3
            [1, 1, 1/2, 3/4, 1/2], # 4
            [1, 4/5, 4/5, 3/5, 2/5], # 5
            [1, 1, 2/3, 2/3, 1/2, 1/3, 2/3, 2/3, 1/2, 1/2, 1/3, 2/3, 1/3, 2/3, 1/2, 1/3],  #6
            [1, 6/7, 6/7, 6/7, 4/7, 3/7, 2/7],  # 7
            [1, 1, 1, 1, 1, 3/4, 1/2, 3/4, 1/2, 1/2, 1/2, 3/4, 3/4, 3/4, 1/2, 1/2,
             1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 3/4, 1/2, 7/8, 1/2, 1/4, 1/2, 1/2, 1/2,
             1/4, 1/2, 1/2, 1/2, 1/4, 3/4, 3/4, 1/4, 1/2, 1/2, 1/2, 3/8, 3/4, 1/4,
             3/8, 3/8, 1/4, 1/2, 3/8, 1/4],  #8
            [1, 1, 8/9, 2/3, 8/9, 2/3, 2/3, 2/3, 8/9, 2/3, 2/3, 2/3, 2/3, 8/9, 8/9,
             2/3, 1/3, 2/3, 2/3, 1/3, 1/3, 1/3, 2/3, 1/3, 1/3, 2/3, 7/9, 2/9, 1/3,
             1/3, 2/9, 2/3, 1/3, 2/9],  #9
            [1, 1, 4/5, 4/5, 4/5, 1/2, 4/5, 2/5, 1/2, 1/2, 3/5, 3/5, 3/5, 1/5, 2/5,
             2/5, 1/2, 1/2, 1/2, 1/2, 2/5, 2/5, 1/5, 2/5, 2/5, 4/5, 2/5, 2/5, 1/5,
             4/5, 4/5, 3/5, 2/5, 2/5, 3/5, 1/5, 2/5, 2/5, 1/5, 3/10, 3/10, 3/10,
             1/5, 3/10, 1/5], # 10
            [1, 10/11, 10/11, 10/11, 8/11, 8/11, 3/11, 2/11],  # 11
            [1, 1, 1, 1, 1, 2/3, 2/3, 5/6, 2/3, 2/3, 2/3, 5/6, 5/6, 1/2, 1/2, 1/2,
             1/2, 1/2, 1/2, 3/4, 1/3, 2/3, 2/3, 2/3, 1/3, 2/3, 2/3, 1/2, 1/3, 1/3,
             2/3, 2/3, 5/6, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 2/3, 3/4,
             1/2, 2/3, 2/3, 1/3, 2/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3,
             1/2, 2/3, 1/2, 2/3, 2/3, 2/3, 2/3, 2/3, 2/3, 2/3, 1/3, 1/2, 1/2, 1/2,
             1/2, 2/3, 2/3, 2/3, 1/3, 1/2, 1/3, 1/2, 1/2, 1/2, 1/2, 2/3, 2/3, 1/3,
             1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3,
             1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/2, 1/2, 2/3, 2/3, 1/2,
             1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 1/2, 2/3, 2/3, 2/3, 1/3, 1/3, 2/3, 2/3,
             1/2, 1/4, 1/4, 1/2, 1/2, 1/6, 1/6, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3,
             1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/2,
             2/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/2, 1/3, 1/4, 1/4, 1/4, 1/4,
             1/4, 1/4, 1/4, 1/4, 1/2, 1/2, 1/2, 1/2, 5/6, 1/2, 2/3, 2/3, 1/2, 1/3,
             1/3, 1/3, 1/3, 1/6, 1/3, 1/3, 1/3, 1/3, 1/6, 1/4, 1/3, 1/3, 1/3, 1/3,
             1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/3, 1/6, 1/4, 1/4, 1/4, 1/4,
             1/2, 1/4, 1/4, 1/4, 1/4, 5/6, 1/3, 2/3, 1/3, 1/6, 1/3, 1/6, 1/3, 1/3,
             1/6, 1/3, 1/3, 1/3, 1/4, 1/4, 1/4, 1/4, 1/3, 1/3, 1/3, 1/3, 1/3, 1/6,
             1/6, 1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/4, 1/6, 1/3, 1/3, 1/3, 1/3,
             1/6, 1/3, 1/3, 1/4, 1/4, 1/6, 1/6, 1/4, 1/4, 1/6, 1/4, 1/4, 1/4, 1/3,
             1/3, 1/6, 1/4, 2/3, 1/4, 1/6, 1/4, 1/4, 1/3, 1/3, 1/3, 1/6, 1/4, 1/4,
             1/4, 1/4, 1/3, 1/6, 1/3, 1/3, 1/6, 1/4, 1/4, 1/6, 1/6, 1/6, 2/3, 1/4,
             1/4, 1/4, 1/6, 1/4, 1/6],  # 12
            [1, 12/13, 12/13, 12/13, 12/13, 12/13, 8/13, 3/13, 2/13], # 13
            [1, 1, 6/7, 6/7, 6/7, 4/7, 6/7, 1/2, 3/7, 6/7, 4/7, 1/2, 1/2, 1/2, 1/2,
             4/7, 5/7, 3/7, 4/7, 3/7, 2/7, 1/2, 1/2, 1/2, 1/2, 3/7, 2/7, 2/7, 1/7,
             6/7, 3/7, 3/7, 4/7, 4/7, 2/7, 3/7, 3/7, 1/7, 6/7, 2/7, 2/7, 3/7, 3/7,
             1/7, 3/7, 3/7, 3/7, 1/7, 2/7, 2/7, 1/7, 2/7, 2/7, 2/7, 2/7, 1/7, 1/7,
             3/14, 3/14, 3/14, 1/7, 3/14, 1/7],  # 14
            [1, 14/15, 4/5, 2/3, 4/5, 4/5, 2/3, 4/5, 2/3, 4/5, 2/3, 2/3, 2/3, 2/3,
             4/5, 3/5, 2/3, 2/3, 2/3, 4/5, 4/5, 3/5, 3/5, 2/5, 1/3, 2/5, 2/3, 8/15,
             2/5, 1/3, 1/3, 1/3, 2/5, 2/5, 2/5, 1/5, 1/3, 1/3, 1/3, 1/3, 2/5, 2/5,
             2/5, 1/5, 1/5, 1/5, 4/5, 1/3, 1/3, 4/15, 1/3, 2/5, 2/5, 1/5, 1/5, 1/5,
             1/3, 4/15, 4/15, 4/15, 2/5, 2/5, 2/5, 1/5, 1/3, 1/3, 4/15, 4/15, 1/5,
             2/5, 1/5, 8/15, 4/15, 4/15, 4/15, 1/5, 1/5, 1/5, 1/5, 1/5, 2/15, 4/15,
             1/5, 1/5, 1/5, 2/15, 2/15, 1/5, 1/5, 2/15, 1/5, 1/5, 2/15, 1/5, 1/5,
             1/5, 1/5, 1/5, 1/5, 1/5, 2/15, 2/15, 1/5, 2/15], # 15
            [1,1,1,1,1,1,1,1,1,1,1,1,1,1], #16
            [1], #17
            [1,1,1,1,1], #18
            [1], #19
            [1,1,1,1,1], #20
            [1,1], #21
            [1,1], #22
            [1], #23
        ]

        od = 44.76323219095532388621866759
        # grd[n] is a list of pairs(ts, M) so that we have completeness for fields with Galois group nTt (t in ts) as long as grd <= M
        self._grd = {
            2: [((1,), 1500)],
            3: [((1,), 500),
                ((2,), 250)],
            4: [((1,2,3), 200), # quad over quad
                ((4,5), 150)],
            5: [((1,2), 200),
                ((3,), 200),
                ((4,5), 85)],
            6: [((12,14), 85), # pumped up
                ((15,16), 60),
                ((1,2,3,5,9), 200), # just did 6t3 as composita
                ((10,), 150),
                ((4,5,6,7,8,11,13), 150)],
            7: [((4,), 75),
                ((1,3), 200),
                ((2,), 200),
                ((5,6), 45),
                ((7,), 35)],
            8: [((3,5,23,24,39,40,41,44,45,46), 100),
                ((4,6,8,9,10,15,17,18,19,26,28,29,30,35), 125), # over 4T3
                ((1,2,7,16,20,27), 125), # over 4T1
                ((12,13,32,38), 250), # over 4T4
                ((11,21,22,31), 100), # over 4T2
                ((14,33), 150),
                ((25,36), 200), #prim
                ((34,), 110),
                ((37,), 45),
                ((42,), 135),
                ((47,), 150),
                ((48,), 45)],
            9: [((16,), od),
                ((26,), 75),
                ((9,13,14,15,19,22,23,24,25,29), 100),
                ((31,), 100),
                ((18,), 150), # using 6T9
                ((30,), 115),
                ((1,2,4,6,7,17), 500), #C3 over C3
                ((1,2,3,4,5,6,7,8,10,11,12,20,21,24,29,30,31), 200),
                ((20,28), 150)],
            10: [(tup(1,28)+(29,32,34,36,37,38,39), od),
                 ((4,), 100), # F_5
                 ((20,), 50),
                 ((1,2,6), 200)], # C_5 over C_2
            11: [((1,), 200),
                 ((2,3), od),
                 ((4,), 22.5)],
            12: [((1,2,5), od),
                 (tup(1,20)+tup(21,43)+tup(48,70)+tup(74,83), od/2),
                 ((1,5), 150)],
            13: [((1,), 200),
                 ((2,), od),
                 ((3,4,5,6), od/2)],
            14: [((1,), od),
                 ((2,), 50),
                 ((3,4,5,6,7,8,9,10,11,17,18,19,21,27,28,29,33,34,35,38,40,41,42,43,44,47,48,50,51,53,56), 23)],
            15: [((1,2), od)],
            16: [((1,2,3,4,5), od),
                 (tup(6,57)+tup(67,178)+tup(197,414), od/2)],
            17: [((1,), 200),
                 ((2,), od)],
            18: [((1,2,3,4,5), 100)],
            19: [((1,), 200),
                 ((2,), od)],
            20: [((1,2,3,4,5), 100)],
            21: [((1,2), 100)],
            22: [((1,), 100)],
            23: [((1,2), od)],
        }

        quartic_2_group = (1,2,3)
        octic_2_group = (1,2,3,4,5,6,7,8,9,10,11,15,16,17,18,19,20,21,22,26,27,28,29,30,31,35)
        octwith4 = (1,2,4,6,7,8,10,12,13,14,16,17,19,20,21,23,27,28,30,38,40)
        octic_with_quartic = tup(1,25)+tup(26,33)+(35,38,39,40,44)
        octic_type_2 = (33,34,41,42,45,46,47)
        decic_with_quint = (1,2,3,4,5,8,11,12,14,15,16,22,23,24,25,29,34,36,37,38,39)
        decic_with_quad = (1,2,3,4,5,6,9,10,11,12,17,18,19,20,21,22,27,28,33,40,41,42,43)

        # r2G[n] is a list of triples (r2, ts, M) so that we have all number fields with signature [n-2*r2, r2] and Galois group nTt (for t in ts) as long as the absolute discriminant is at most M (if M is None, there is no discriminant restriction since that signature/Galois group combination is impossible)
        self._r2G = {
            3: [(1, (1,), None)],
            4: [(0, (1,2,3), 150**4),
                (0, (4,), 10**10), # from megrez
                (1, (1,2,4), None),
                (1, (3,), 15**6),
                (2, (1,2,3), 15**6),
                (2, (4,), 10**10)], # from megrez
            5: [(0, (1,2), 10**10),
                (0, (4,), 2**38),
                (1, (1,2,3,4), None),
                (2, (1,), None),
                (2, (2,4), 10**8)],
            6: [# r2=0 bound for arbitrary t is 28^6
                (0, (1,2), 250**6), # Base changing S_3 grd up, using Belabash, disc filter, moving them up; redid 6T2 by Rachel/grd, which picks up 6T1
                (0, (3,), 10**11), # from Kluners
                (0, (4,), 100**6), # from Kluners
                (0, (5,), 10**10), # matches Kluners
                (0, (6,), 50**6), # higher than Kluners
                (0, (7,), 18**9), # Computed with a special version for even groups
                (0, (8,), 10**12), # from Kluners
                (0, (9,), 2*10**10), # from Kluners
                (0, (10,), 10**11), # from Kluners
                (0, (11,), 35**6),
                (0, (12,), 2**38), # from A5 quintics pushed up
                (0, (14,), 35**6), # from S5 quintics pushed up
                # r2=1 bound for arbitrary t is 10^7
                (1, (1,2,3,4,5,7,8,9,10,12,14,15), None),
                (1, (6,), 10**9), # from Kluners
                (1, (11,), 10**9), # from Kluners
                (1, (13,), 10**8-1), # from Eric Driver
                # r2=2 bound for arbitrary t is 10^7
                (2, (1,2,5), None),
                (2, (3,), 64**6), # Done by composita
                (2, (4,), 100**6), # from Kluners
                (2, (6,), 10**9), # from Kluners
                (2, (7,), 18**9), # Computed with a special version for even groups
                (2, (8,), 15**9), # JJ has double checked
                (2, (9,10), 5*10**9), # from Eric Driver
                (2, (11,), 10**8), # from Kluners
                (2, (12,14), 35**6),
                (2, (13,), 10**8-1), # from Eric Driver
                # r2=3 bound for arbitrary t is 10^7
                (3, (4,7,10,12,15), None),
                (3, (1,2), 250**6), # Base changing S_3 grd up, using Belabash, disc filter, moving them up; redid 6T2 by Rachel/grd, which picks up 6T1
                (3, (3,), 64**6), # Done by composita
                (3, (5,), 10**10), # matches Kluners
                (3, (6,), 10**9), # from Kluners
                (3, (8,), 15**9), # JJ has double checked
                (3, (9,), 5*10**9), # from Eric Driver
                (3, (11,), 10**8), # from Kluners
                (3, (13,), 10**8-1), # from Eric Driver
                (3, (14,), 35**6)],
            7: [# r2=0 bound for arbitrary t is 214942297
                (0, (3,), 26**7), # LMFDB
                (0, (5,), 38**7), # LMFDB
                (0, (6,), 988410720),
                # r2=1,2,3 bound for arbitrary t is 2*10^8
                (1, tup(1,7), None),
                (2, tup(1,5), None),
                (3, (1,3,5,6), None)],
            8: [# r2=0 bound for arbitrary t is 17^8
                (0, (1,2), 150**8), # also 5
                (0, (5,), 512**8), # LMFDB
                (0, octic_with_quartic, 10**12),
                (0, (4,), 55**8),
                (0, (12,), 56**8),
                (0, (37,), 30**8),
                (0, (45,), 3*15**8),
                # r2=1 bound for arbitrary t is 79259702
                (1, skip(1,50,{27,32,35,38,44,47}), None),
                (1, (27,32,35,38,44), 10**12),
                (1, (47,), 3*10**9),
                # r2=2 bound for arbitrary t is 20829049
                (2, tup(1,7)+(8,12,13,14,23,25,36,37,43), None),
                (2, octic_with_quartic, 4*10**10),
                (2, octic_type_2, 3*10**9), # from Eric Driver, quartic over quadratic
                (2, (45,), 3*15**8),
                (2, (48,), 35831808), # special computation using 7t5 results
                # r2=3 bound for arbitrary t is 5726300
                (3, skip(1,50,{6,8,15,23,26,27,30,31,35,38,40,43,44,47}), None),
                (3, octic_with_quartic, 144*10**8),
                (3, (8,), 20**9),
                (3, octic_type_2, 3*10**9), # from Eric Driver, quartic over quadratic
                # r2=4 bound for arbitrary t is 1656109
                (4, octic_with_quartic, 49*10**8),
                (4, (4,), 55**8),
                (4, (5,), 512**8), # LMFDB
                (4, (8,), 20**9),
                (4, octic_type_2, 3*10**9), # from Eric Driver, quartic over quadratic
                (4, (36,), 15**8), # LMFDB
                (4, (37,), 30**8),
                (4, (45,), 3*15**8),
                (4, (48,), 35831808)], # special computation using 7t5 results
            9: [# r2=0 bound for arbitrary t is 15^9
                (0, (1,2,6,7,17), 50**9), # C3 over C3
                (0, (3,10,11,21), 56**9),
                (0, (4,8,12,20,29,31), 25**9),
                (0, (5,), 20**9), # LMFDB
                (0, (13,22), 32**9),
                (0, (14,15), 85.96137**9),
                (0, (16,), 22**9),
                (0, (18,19,24), 50**9),
                (0, (23,), 67**9),
                (0, (25,), 28**9),
                (0, (26,30), 35**9),
                # r2=1 bound for arbitrary t is 27316369
                (1, skip(1,34,{28,31}), None),
                (1, (28,31), 15**9),
                # r2=2 bound for arbitrary t is 27316369
                (2, skip(1,28,{25})+(32,), None),
                (2, (25,), 23**9),
                (2, (28,30,31), 15**9),
                (2, (29,), 18**9),
                # r2=3 bound for arbitrary t is 146723910
                (3, (1,2,3,5,6,7,9,10,11,14,15,17,21,23,25,27,30,32,33), None),
                (3, (4,8,12,20,28,31), 15**9), # 8 is LMFDB
                (3, (13,16), 12**9), # LMFDB
                (3, (18,24), 16**9),
                (3, (19,21,26), 20**9),
                (3, (22,29), 18**9),
                # r2=4 bound for arbitrary t is 39657561
                (4, (1,2,4,6,7,12,13,17,20,22,25,28,29), None),
                (4, (3,8,10,11,30,31), 15**9), # 8 from LMFDB
                (4, (5,), 20**9), # LMFDB
                (4, (14,15), 18**9), # LMFDB
                (4, (16,), 12**9), # LMFDB
                (4, (18,24), 16**9),
                (4, (19,21,26), 20**9),
                (4, (23,), 17**9)], # LMFDB
            10: [# bound for arbitrary r2,t is 190612177
                 (0, decic_with_quad, 12*10**10),
                 (0, decic_with_quint, 10**13),
                 (1, skip(1,45,{14,23,29,36,39,43}), None),
                 (1, (14,23,29,36,39), 10**13), # decic with quintic
                 (1, (43,), 12*10**10), # decic with quadratic
                 (2, skip(1,14,{8})+(17,18,19,20,26,30,31,32,35), None),
                 (2, decic_with_quad, 12*10**10),
                 (2, decic_with_quint, 10**12),
                 (3, skip(1,45,{13,14,23,29,32,35,36,38,39,43}), None),
                 (3, (14,23,29,36,38,39), 10**12), # decic with quintic
                 (3, (43,), 12*10**10), # decic with quadratic
                 (4, (1,2,6), None),
                 (4, decic_with_quad, 12*10**10),
                 (4, decic_with_quint, 10**12),
                 (5, (4,7,8,10,13,15,18,20,24,25,26,28,31,32,34,37,42,44), None),
                 (5, decic_with_quad, 12*10**10),
                 (5, decic_with_quint, 10**12)],
            11: [(1, tup(1,8), None),
                 (2, tup(1,7), None),
                 (3, tup(1,8), None),
                 (4, tup(1,5), None),
                 (5, (1,3,5,6,7), None)],
        }

        # nS[n] consists of specific sets S so that we have completeness in degree n for number fields unramified outside S.
        self._nS = {
            5: {(2,191), (3,163), (3,181), (3,211), (3,241), (3,401), (3,431), (3,461), (5,211), (5,241), (7,163), (7,181), (2,7,31), (2,7,41), (2,11,31)},
            6: {(2,3,7)},
            7: {(2,11), (2,13), (3,11), (11,13)}
        }

        # If nSp[n][k] = M then we have completeness in degree n for number fields unramified outside of S for all S of size k consisting of primes less than M.
        self._nSp = {
            2: {1: 12000, 2: 500, 3: 100, 4: 30, 5: 30, 6: 30, 7: 30, 8: 30, 9: 30, 10: 30},
            #2: {1: 12000, 2: 500, 3: 100, 4: 30, 5: 18, 6: 18, 7: 18},
            3: {1: 12000, 2: 500, 3: 100, 4: 30, 5: 30, 6: 30, 7: 30, 8: 30, 9: 30, 10: 30},
            #3: {1: 12000, 2: 500, 3: 100, 4: 30, 5: 24, 6: 24, 7: 24, 8: 24, 9: 24},
            4: {1: 12000, 2: 500, 3: 100, 4: 30, 5: 14, 6: 14},
            5: {1: 7500, 2: 150, 3: 24, 4: 8},
            6: {1: 2000, 2: 32},
            7: {1: 192, 2: 6},
        }

        # nSGp[n][k] is a list of pairs (M, Gs) so that we have completeness in degree n for number fields with Galois group nTt for t in Gs and unramified outside a set S of size k all of whose primes are less than M
        self._nSGp = {
            6: {1: [(5000, tup(1,15))],
                2: [(100, (12,14))],
                3: [(12, (12,14)), (8, tup(1,15))],
                4: [(8, tup(1,15))]},
            7: {1: [(5000, (1,2,3)), (1500, (4,)), (228, (5,6))],
                2: [(42, (1,)), (14, (3,)), (8, (2,)), (6, (4,))],
                3: [(42, (1,)), (14, (3,)), (8, (2,)), (6, (4,))],
                4: [(42, (1,)), (14, (3,)), (8, (2,))],
                5: [(42, (1,)), (14, (3,))],
                6: [(42, (1,)), (14, (3,))],
                7: [(42, (1,))],
                8: [(42, (1,))],
                9: [(42, (1,))],
                10: [(42, (1,))],
                11: [(42, (1,))],
                12: [(42, (1,))],
                13: [(42, (1,))]},
            8: {1: [(2500, octic_2_group), (230, octwith4), (228, (37,)), (200, (25,)), (8, octic_with_quartic), (8, (25,36)), (6, (33,34,41,42,45,46,47))],
                2: [(250, octic_2_group), (8, octic_with_quartic), (8, (25,36)), (6, (33,34,41,42,45,46,47))],
                3: [(8, octic_with_quartic), (8, (25,36)), (6, (33,34,41,42,45,46,47))],
                4: [(8, (25,36))]},
            9: {1: [(6, tup(1,19)+tup(20,26)+(28,29,31)), (6, (19,26,30))],
                2: [(6, tup(1,19)+tup(20,26)+(28,29,31)), (6, (19,26,30))],
                3: [(6, tup(1,19)+tup(20,26)+(28,29,31))]},
            10: {1: [(20, (32,)), (6, decic_with_quint), (6, (6,7,9,10,13,17)), (4, (18,19,20,21,26,27,32,33))],
                 2: [(20, (32,)), (6, decic_with_quint), (6, (6,7,9,10,13,17)), (4, (18,19,20,21,26,27,32,33))],
                 3: [(6, decic_with_quint), (6, (6,7,9,10,13,17))]},
            11: {1: [(200, (1,)), (5000, (2,)), (12, (3,))],
                 2: [(8, (1,2,3))],
                 3: [(8, (1,2,3))],
                 4: [(8, (1,2,3))]},
            13: {1: [(5000, (2,))]},
            24: {1: [(1000, (1,))]},
            25: {1: [(1000, (1,))]},
        }

        # nSGp1[n] is a list of triples (p, M, Gs) so that we have completeness in degree n for number fields with Galois group nTt for t in Gs and unramified outside {p,q} for q < M.
        self._nSGp1 = {
            4: [(2, 2500, quartic_2_group)],
            5: [(3, 1328, (1,2,4)), (2, 980, (1,2,4))],
            8: [(2, 2500, octic_2_group), (2, 200, (25,))],
        }

        # nSG[n] is a list of pairs (T, Gs) so that we have completeness in degree n for number fields with Galois group nTt for t in Gs and unramified outside S for any subset S of T.
        self._nSG = {
            5: [((2,3,7,11), (1,2,4)),
                ((2,3,7,31), (1,2,4)),
                ((2,3,11,19), (1,2,4)),
                ((2,3,31), (1,2,4)),
                ((2,3,37), (1,2,4)),
                ((2,3,41), (1,2,4)),
                ((2,3,43), (1,2,4)),
                ((2,3,53), (1,2,4)),
                ((2,3,61), (1,2,4)),
                ((2,3,79), (1,2,4)),
                ((2,3,89), (1,2,4)),
                ((2,3,101), (1,2,4)),
                ((2,3,103), (1,2,4)),
                ((2,3,107), (1,2,4)),
                ((2,3,113), (1,2,4)),
                ((2,3,127), (1,2,4)),
                ((2,3,131), (1,2,4)),
                ((2,3,137), (1,2,4)),
                ((2,3,151), (1,2,4)),
                ((2,5,13), (1,2,4)),
                ((2,5,17), (1,2,4)),
                ((2,5,23), (1,2,4)),
                ((2,5,29), (1,2,4)),
                ((2,5,31), (1,2,4)),
                ((2,7,17), (1,2,4)),
                ((2,7,19), (1,2,4)),
                ((2,7,59), (1,2,4)),
                ((2,7,61), (1,2,4)),
                ((2,7,71), (1,2,4)),
                ((2,7,103), (1,2,4)),
                ((2,7,127), (1,2,4)),
                ((2,7,131), (1,2,4)),
                ((2,13,71), (1,2,4)),
                ((2,17,31), (1,2,4)),
                ((2,19,23), (1,2,4)),
                ((2,23,41), (1,2,4)),
                ((2,29,31), (1,2,4)),
                ((2,11,13), (1,2,4)),
                ((2,11,17), (1,2,4)),
                ((2,11,19), (1,2,4)),
                ((2,11,23), (1,2,4)),
                ((2,11,29), (1,2,4)),
                ((2,11,31), (1,2,4)),
                ((2,11,37), (1,2,4)),
                ((2,11,41), (1,2,4)),
                ((2,11,43), (1,2,4)),
                ((2,11,47), (1,2,4)),
                ((2,11,53), (1,2,4)),
                ((2,11,59), (1,2,4)),
                ((2,11,61), (1,2,4)),
                ((2,11,67), (1,2,4)),
                ((2,11,71), (1,2,4)),
                ((2,11,73), (1,2,4)),
                ((2,13,29), (1,2,4)),
                ((2,13,31), (1,2,4)),
                ((2,13,37), (1,2,4)),
                ((2,13,41), (1,2,4)),
                ((2,13,43), (1,2,4)),
                ((2,13,47), (1,2,4)),
                ((2,13,53), (1,2,4)),
                ((2,13,59), (1,2,4)),
                ((2,13,61), (1,2,4)),
                ((2,13,67), (1,2,4)),
                ((2,13,71), (1,2,4)),
                ((2,13,73), (1,2,4)),
                ((2,17,31), (1,2,4)),
                ((2,19,23), (1,2,4)),
                ((2,23,41), (1,2,4)),
                ((2,29,31), (1,2,4)),
                ((3,5,17), (1,2,4)),
                ((3,5,31), (1,2,4)),
                ((3,5,37), (1,2,4)),
                ((3,7,11), (1,2,4)),
                ((3,7,11,17), (1,2,4)),
                ((3,7,17), (1,2,4)),
                ((3,7,31), (1,2,4)),
                ((3,7,41), (1,2,4)),
                ((3,7,61), (1,2,4)),
                ((3,7,101), (1,2,4)),
                ((3,7,107), (1,2,4)),
                ((3,7,131), (1,2,4)),
                ((3,7,139), (1,2,4)),
                ((3,7,163), (1,2,4)),
                ((3,7,181), (1,2,4)),
                ((3,11,13), (1,2,4)),
                ((3,11,17), (1,2,4)),
                ((3,11,19), (1,2,4)),
                ((3,11,29), (1,2,4)),
                ((3,11,31), (1,2,4)),
                ((3,11,41), (1,2,4)),
                ((3,11,61), (1,2,4)),
                ((3,11,71), (1,2,4)),
                ((3,11,73), (1,2,4)),
                ((3,11,101), (1,2,4)),
                ((3,11,103), (1,2,4)),
                ((3,11,109), (1,2,4)),
                ((3,13,31), (1,2,4)),
                ((3,13,41), (1,2,4)),
                ((3,13,61), (1,2,4)),
                ((3,13,71), (1,2,4)),
                ((3,13,89), (1,2,4)),
                ((3,17,37), (1,2,4)),
                ((3,17,41), (1,2,4)),
                ((3,17,43), (1,2,4)),
                ((3,17,71), (1,2,4)),
                ((3,19,61), (1,2,4)),
                ((3,29,37), (1,2,4)),
                ((3,29,41), (1,2,4)),
                ((3,31,41), (1,2,4)),
                ((5,7,13), (1,2,4)),
                ((5,7,17), (1,2,4)),
                ((5,7,71), (1,2,4)),
                ((5,7,97), (1,2,4)),
                ((5,11,13), (1,2,4)),
                ((5,11,19), (1,2,4)),
                ((5,11,31), (1,2,4)),
                ((5,11,41), (1,2,4)),
                ((5,11,43), (1,2,4)),
                ((5,11,71), (1,2,4)),
                ((5,13,23), (1,2,4)),
                ((5,151), (1,2,4)),
                ((5,163), (1,2,4)),
                ((5,223), (1,2,4)),
                ((5,241), (1,2,4)),
                ((5,367), (1,2,4)),
                ((5,571), (1,2,4)),
                ((5,631), (1,2,4)),
                ((7,11,17), (1,2,4)),
                ((7,11,23), (1,2,4)),
                ((7,11,37), (1,2,4)),
                ((7,13,31), (1,2,4)),
                ((7,13,37), (1,2,4)),
                ((7,13,41), (1,2,4)),
                ((7,151), (1,2,4)),
                ((7,163), (1,2,4)),
                ((7,181), (1,2,4)),
                ((7,191), (1,2,4)),
                ((7,211), (1,2,4)),
                ((7,241), (1,2,4)),
                ((7,257), (1,2,4)),
                ((7,281), (1,2,4)),
                ((7,313), (1,2,4)),
                ((7,331), (1,2,4)),
                ((7,379), (1,2,4)),
                ((7,401), (1,2,4)),
                ((7,409), (1,2,4)),
                ((7,421), (1,2,4)),
                ((7,433), (1,2,4)),
                ((7,431), (1,2,4)),
                ((7,491), (1,2,4)),
                ((7,541), (1,2,4)),
                ((7,571), (1,2,4)),
                ((11,13,23), (1,2,4)),
                ((11,17,19), (1,2,4)),
                ((11,151), (1,2,4)),
                ((11,167), (1,2,4)),
                ((11,179), (1,2,4)),
                ((11,181), (1,2,4)),
                ((11,191), (1,2,4)),
                ((11,211), (1,2,4)),
                ((11,251), (1,2,4)),
                ((11,269), (1,2,4)),
                ((11,263), (1,2,4)),
                ((11,271), (1,2,4)),
                ((11,281), (1,2,4)),
                ((11,283), (1,2,4)),
                ((11,311), (1,2,4)),
                ((11,293), (1,2,4)),
                ((11,307), (1,2,4)),
                ((11,331), (1,2,4)),
                ((11,331), (1,2,4)),
                ((11,359), (1,2,4)),
                ((13,191), (1,2,4)),
                ((13,223), (1,2,4)),
                ((13,211), (1,2,4)),
                ((13,307), (1,2,4)),
                ((17,227), (1,2,4)),
                ((17,211), (1,2,4)),
                ((19,191), (1,2,4)),
                ((19,157), (1,2,4)),
                ((19,181), (1,2,4)),
                ((19,193), (1,2,4)),
                ((23,151), (1,2,4)),
                ((23,173), (1,2,4))],
            8: [((2,3), (37,48)),
                ((2,5), (37,48)),
                ((2,29), (25,)),
                ((7,29), (25,)),
                ((41, 241), octic_2_group)],
            9: [((3,7,13), (1,2,6,7,17))],
            10: [((2,3,7), (32,)),
                 ((2,7), decic_with_quad),
                 ((2,5), (19,20,21,26,32)),
                 ((3,5), (18,19,20,21,26,27,32,33))],
            11: [((2,11), (3,)),
                 ((3,11), (3,)),
                 ((7,11), (3,))],
        }

    def display_reason(self, reasons):
        """
        Convert a set of collected reasons into a single string to display.

        INPUT:

        - ``reasons`` -- a set of reasons, which are either a string or
          a tuple of the form ``(n, r2, galt, ramps, D_bound, grd_bound)``,
          where entries are None if they are not applicable.
        """
        # Current tuples created:
        # (n, r2, None, None, M, None)
        # (n, r2, Gs, None, M, None)
        # (n, None, Gs, None, None, M)
        # (n, None, None, S, None, None)
        # (n, None, Gs, S, None, None)
        # We group by None pattern
        def describe(tups):
            ans = []
            if tups[0][0] is not None:
                degs = [str(tup[0]) for tup in tups]
                if len(set(degs)) == 1:
                    ans.append(f"degree {degs[0]}")
                else:
                    ans.append(f"degree {','.join(degs)}")
            if tups[0][1] is not None:
                sigs = [f"[{tup[0]-2*tup[1]},{tup[1]}]" for tup in tups]
                if len(set(sigs)) == 1:
                    ans.append(f"signature {sigs[0]}")
                else:
                    ans.append(f"signature {','.join(sigs)}")
            if tups[0][2] is not None:
                ts = [f"({','.join(str(t) for t in tup[2])})" if len(tup[2]) > 1 else str(tup[2][0]) for tup in tups]
                gals = [f"{tup[0]}T{tt}" for (tup, tt) in zip(tups, ts)]
                if len(set(gals)) == 1:
                    ans.append(f"Galois group {gals[0]}")
                else:
                    ans.append(f"Galois group {','.join(gals)}")
            if tups[0][3] is not None:
                rams = ['{'+','.join(str(p) for p in tup[3])+'}' for tup in tups]
                if len(set(rams)) == 1:
                    ans.append(f"unramified outside {rams[0]}")
                else:
                    ans.append(f"unramified outside {','.join()}")
            if tups[0][4] is not None:
                Dbounds = [str(tup[4]) for tup in tups]
                if len(set(Dbounds)) == 1:
                    ans.append(f"absolute discriminant at most {Dbounds[0]}")
                else:
                    ans.append(f"absolute discriminant at most {','.join(Dbounds)}")
            if tups[0][5] is not None:
                grd = [str(tup[5]) for tup in tups]
                if len(set(grd)) == 1:
                    ans.append(f"Galois root discriminant at most {grd[0]}")
                else:
                    ans.append(f"Galois root discriminant at most {','.join(grd)}")
            return ", ".join(ans)
        strings = []
        by_pattern = defaultdict(list)
        non_incomp = []
        for reason in reasons:
            if isinstance(reason, str):
                strings.append(reason)
                if not reason.startswith("incompatible conditions"):
                    non_incomp.append(reason)
            else:
                by_pattern[tuple(i for i in range(6) if reason[i] is None)].append(reason)
        if len(non_incomp) + len(by_pattern) > 0:
            strings = non_incomp
        return "number fields with " + "; ".join(strings + [describe(V) for V in by_pattern.values()])

    def clear_signatures(self, n, D, r2opts, reasons):
        if 2 <= n < len(self._maxD):
            m = infinity
            for r2 in set(r2opts):
                M = self._maxD[n][r2]
                if D.bounded(M):
                    r2opts.remove(r2)
                    reasons.add((n, r2, None, None, M, None))
                m = min(m, M)
            if m is not infinity:
                D = D.intersection(bottom(m + 1))
        return D

    def clear_r2G(self, n, D, r2opts, galt, reasons):
        r2G = defaultdict(dict)
        for (r2, Gs, M) in self._r2G.get(n, []):
            if r2 in r2opts and D.bounded(M):
                for t in galt.intersection(Gs):
                    r2G[t][r2] = (r2, Gs, M)
        for t in galt.intersection(r2G):
            if set(r2G[t]) == set(r2opts):
                galt.remove(t)
                for r2, Gs, M in r2G[t].values():
                    reasons.add((n, r2, Gs, None, M, None))

    def clear_grd(self, n, grd, galt, reasons):
        by_t = {}
        for (Gs, M) in self._grd.get(n, []):
            if grd.bounded(M):
                for t in galt.intersection(Gs):
                    by_t[t] = (Gs, M)
        for t in galt.intersection(by_t):
            galt.remove(t)
            Gs, M = by_t[t]
            reasons.add((n, None, Gs, None, None, M))

    def clear_S(self, n, S, nram, galt, reasons, update_galt=True):
        """
        When False, if update_galt is True, update galt to remove t that can be proven complete.
        """
        if galt is not None and not update_galt:
            galt = set(galt)
        if nram is None:
            nram = len(S)

        if S in self._nS.get(n, {}):
            reasons.add((n, None, None, S, None, None))
            return True

        M = self._nSp.get(n, {}).get(nram)
        if M is not None and all(p < M for p in S):
            reasons.add((n, None, None, S, None, None))
            return True

        if galt is None:
            return False

        for (M, Gs) in self._nSGp.get(n, {}).get(nram, []):
            if all(p < M for p in S):
                I = galt.intersection(Gs)
                if I:
                    reasons.add((n, None, Gs, S, None, None))
                    galt.difference_update(I)
                    if not galt:
                        return True

        if len(S) == 2:
            for (p0, M, Gs) in self._nSGp1.get(n, []):
                if min(S) == p0 and max(S) < M:
                    I = galt.intersection(Gs)
                    if I:
                        reasons.add((n, None, Gs, S, None, None))
                        galt.difference_update(I)
                        if not galt:
                            return True

        SS = set(S)
        for T, Gs in self._nSG.get(n, []):
            if SS.issubset(T):
                I = galt.intersection(Gs)
                if I:
                    reasons.add((n, None, Gs, S, None, None))
                    galt.difference_update(I)
                    if not galt:
                        return True

        return False

    def galt(self, n, gal, isgal, cyc, ab, solv):
        pos_constraints = []
        neg_constraints = []
        if isinstance(gal, str) and gal.count("T") == 1:
            N, t = gal.split("T")
            if N == str(n) and t.isdigit():
                pos_constraints.append({int(t)})
            else:
                return # incompatible constraints
        elif isinstance(gal, dict) and list(gal) == ["$in"]:
            galt = set()
            n = str(n)
            for G in gal["$in"]:
                if not isinstance(G, str) or G.count("T") != 1:
                    raise ValueError
                N, t = G.split("T")
                if N == n and t.isdigit():
                    galt.add(int(t))
            pos_constraints.append(galt)
        elif gal is not None or n >= len(self._num_trans):
            raise ValueError
        if cyc == 1:
            if n == 32:
                pos_constraints.append({33})
            else:
                pos_constraints.append({1})
        elif cyc == 0:
            if n == 32:
                neg_constraints.append({33})
            else:
                neg_constraints.append({1})
        elif cyc is not None:
            raise ValueError

        if ab == 1:
            pos_constraints.append(self._ab.get(n, {1}))
        elif ab == 0:
            neg_constraints.append(self._ab.get(n, {1}))
        elif ab is not None:
            raise ValueError

        gal_set = self._ab.get(n, {1}).union(self._nab_gal.get(n, set()))
        if isgal == 1:
            pos_constraints.append(gal_set)
        elif isgal == 0:
            neg_constraints.append(gal_set)
        elif isgal is not None:
            raise ValueError

        if solv == 1:
            if n in self._nsolv:
                neg_constraints.append(self._nsolv[n])
        elif solv == 0:
            if n in self._nsolv:
                pos_constraints.append(self._nsolv[n])
        elif solv is not None:
            raise ValueError

        if pos_constraints:
            galt = pos_constraints[0]
            for Gs in pos_constraints[1:]:
                galt.intersection_update(Gs)
        else:
            galt = set(range(1, self._num_trans[n] + 1))
        for Gs in neg_constraints:
            galt.difference_update(Gs)
        return galt

    def rd_grd_ratio(self, n, galt):
        if n < len(self._rdgrd) and max(galt) <= len(self._rdgrd[n]):
            return max(1 / self._rdgrd[n][t - 1] for t in galt)

    def get_S(self, ramps, radical):
        S = None
        if radical is not None:
            if isinstance(radical, dict):
                if not (list(radical) == ["$lte"] and isinstance(ramps, dict) and "$containedin" in ramps and prod(ramps["$containedin"]) == radical["$lte"]):
                    # Such constraints are not created by parsing code, so we give up
                    return
                # Now we can just fall back on ramps parsing below
            else:
                S = set(p for p,e in factor(radical))
        if ramps is not None:
            if isinstance(ramps, dict):
                if "$containedin" in ramps:
                    if S is not None:
                        if not S.issubset(ramps["$containedin"]):
                            # incompatible, so result is complete.  We return an S that will be accepted for all n <= 11
                            return []
                    else:
                        S = ramps["$containedin"]
                else:
                    # $notcontains and $contains do not yield finite S
                    return
            if isinstance(ramps, list):
                if S is not None:
                    if not S.issubset(ramps):
                        # incompatible, so result is complete.  We return an S that will be accepted for all n <= 11
                        return []
                else:
                    S = ramps
        if S is not None:
            return tuple(sorted(S))

    def _initial(self, db, query, reasons):
        """
        Attempt to prove completeness without splitting on degree
        """
        D, rd, grd = IntegerSet(query.get("disc_abs")), NumberSet(query.get("rd")), NumberSet(query.get("grd"))
        if D.bounded(1656109):
            reasons.add("absolute discriminant at most 1656109")
            return True, None
        if rd.bounded(5.989):
            reasons.add("root discriminant at most 5.989")
            return True, None
        if grd.bounded(5.989):
            reasons.add("Galois root discriminant at most 5.989")
            return True, None
        # Can also guarantee completeness based on regulator bounds and non-CMness: see https://arxiv.org/pdf/2112.15268

        # TODO: use Odlyzko bounds to get upper bound on degree
        return False, None

    def _one_n(self, db, query, reasons):
        n = query.get("degree")
        if n == 1:
            reasons.add("degree 1")
            return True, None
        # For now, we just do not guarantee completeness for any degrees larger than 25.
        # TODO: improve this using Minkowski and Odlyzko bounds (which give us guarantees that there are no number fields
        if n is None or n > 25:
            return False, None

        r2, D, sign, rd, grd = IntegerSet(query.get("r2")), IntegerSet(query.get("disc_abs")), query.get("disc_sign"), NumberSet(query.get("rd")), NumberSet(query.get("grd"))
        r2opts = list(r2.intersection(IntegerSet([0, n//2])))
        if sign == 1:
            r2opts = [r2 for r2 in r2opts if r2 % 2 == 0]
        elif sign == -1:
            r2opts = [r2 for r2 in r2opts if r2 % 2 == 1]
        if not r2opts:
            reasons.add("incompatible conditions: signature and discriminant")
            return True, None
        if n == 2 and r2opts == [1]:
            # Imaginary quadratic fields, where we can use Mark Watkins' paper (Class groups of imaginary quadratic fields) to guarantee completeness based on class number
            h = query.get("class_number")
            C = query.get("class_group")
            if isinstance(C, list) and h is None:
                h = prod(C)
            h = IntegerSet(h)
            if h.is_subset(top(97).union(IntegerSet([99,100]))):
                # Class number 98 has entries slightly outside our bounds
                # Watkins' result is actually unconditional
                reasons.add("signature [0,1], class number at most 100 (except 98)")
                return True, None

            # We can also use https://msp.org/obs/2019/2-1/obs-v2-n1-p16-s.pdf
            if isinstance(C, list) and all(c == 2 for c in C):
                reasons.add("signature [0,1], class group of exponent 2")
                return True, "depends on GRH"

        if n > 2 and any(col in query for col in ["class_group", "class_number", "narrow_class_group", "narrow_class_number"]):
            caveat = "depends on GRH"
        else:
            caveat = None

        ## Completeness 1: degree, signature, discriminant ##
        if grd.restricted():
            rd = rd.pow_cap(grd, 1)
            if not rd:
                reasons.add("incompatible conditions: root discriminant and Galois root discriminant")
                return True, None
        if rd.restricted():
            D = D.pow_cap(rd, n)
            if not D:
                reasons.add("incompatible conditions: root discriminant and discriminant")
                return True, None
        if D.restricted():
            D = self.clear_signatures(n, D, r2opts, reasons)
            if not r2opts:
                return True, caveat

        ## Completeness 2: degree, signature, Galois group, discriminant
        gal, isgal, cyc, ab, solv, = query.get("galois_label"), query.get("is_galois"), query.get("gal_is_cyclic"), query.get("gal_is_abelian"), query.get("gal_is_solvable")
        if gal or isgal or cyc or ab or solv:
            try:
                galt = self.galt(n, gal, isgal, cyc, ab, solv)
            except ValueError:
                # Parsing problem
                return False, None
            if not galt:
                reasons.add("incompatible conditions: Galois group")
                return True, None
            if D.restricted():
                self.clear_r2G(n, D, r2opts, galt, reasons)
                if not galt:
                    return True, caveat

            ## Completeness 3: degree, Galois group, Galois root discriminant ##
            if D.restricted():
                rd = rd.pow_cap(D, 1/n)
                if not rd:
                    reasons.add("incompatible conditions: root discriminant and discriminant")
                    return True, None
            if rd.restricted():
                ratio = self.rd_grd_ratio(n, galt)
                if ratio is not None:
                    grd = grd.pow_cap(rd, ratio)
                    if not grd:
                        reasons.add("incompatible conditions: root discriminant and Galois root discriminant")
                        return True, None
            if grd.restricted():
                self.clear_grd(n, grd, galt, reasons)
                if not galt:
                    return True, caveat
        else:
            galt = None

        ## Completeness 4: degree, ramified primes, and Galois group (optional)
        # Can fill rams from discriminant range, or from radical
        ramps, radical, nram = query.get("ramps"), query.get("disc_rad"), query.get("num_ram")
        if isinstance(nram, dict):
            if "$lte" in nram:
                nram = nram["$lte"]
            else:
                # nram is complicated, so we give up on using it
                nram = None
        if ramps or radical:
            S = self.get_S(ramps, radical)
            if S == []: # incompatible
                reasons.add("incompatible conditions: ramps and radical")
                return True, None
            if S is not None and self.clear_S(n, S, nram, galt, reasons):
                return True, caveat

        # Can also iterate over valid discriminants in a discriminant range
        if D.restricted():
            for S in D.stickelberger(n, r2opts):
                if not self.clear_S(n, S, nram, galt, reasons, update_galt=False):
                    break
            else:
                if not reasons:
                    reasons.add("incompatible conditions: no valid discriminants in range")
                return True, caveat

            # Minkowski bound (only relevant for n>12)
            if n >= len(self._maxD):
                mbound = (3.14159265358979/4)**n * n**(2*n) / factorial(n)**2
                if D.bounded(mbound):
                    reasons.add(f"number fields of degree {n} with discriminant at most {floor(mbound)} (Minkowski)")
                    return True, None
            # TODO: Odlyzko bounds

        return False, None

    def __call__(self, db, query):
        n = query.get("degree")

        # We collect reasons that have contributed to completeness
        # These have the following format:
        # (n, r2, galt, ramps, D_bound, grd_bound)
        # Where entries can be None if they are not applicable
        reasons = set()
        # First check completeness without splitting on degree
        # This may also add an upper bound on degree, based on other inputs
        done, caveat = self._initial(db, query, reasons)
        if done:
            return True, self.display_reason(reasons), caveat
        if isinstance(n, dict):
            nopts = IntegerSet(n).intersection(bottom(1))
            if nopts.max() >= 48:
                return False, None, None
            caveats = set()
            # Reverse order since we're less likely to have completeness in higher degree
            for n in reversed(list(nopts)):
                nquery = dict(query)
                nquery["degree"] = n
                ok, caveat = self._one_n(db, nquery, reasons)
                if not ok:
                    return False, None, None
                if caveat:
                    caveats.add(caveat)
            if caveats:
                caveats = ", ".join(caveats)
            else:
                caveats = None
        else:
            ok, caveats = self._one_n(db, query, reasons)
            if not ok:
                return False, None, None
        return True, self.display_reason(reasons), caveats


#### Artin representations ####

minimal_label = {
    '2T1': '2T1',
    '3T1': '3T1',
    '3T2': '3T2',
    '6T2': '3T2',
    '4T1': '4T1',
    '4T3': '4T3',
    '8T4': '4T3',
    '4T4': '4T4',
    '6T4': '4T4',
    '12T4': '4T4',
    '4T5': '4T5',
    '6T7': '4T5',
    '6T8': '4T5',
    '8T14': '4T5',
    '12T8': '4T5',
    '12T9': '4T5',
    '24T10': '4T5',
    '5T1': '5T1',
    '5T2': '5T2',
    '10T2': '5T2',
    '5T3': '5T3',
    '10T4': '5T3',
    '20T5': '5T3',
    '5T4': '5T4',
    '6T12': '5T4',
    '10T7': '5T4',
    '12T33': '5T4',
    '15T5': '5T4',
    '20T15': '5T4',
    '30T9': '5T4',
    '5T5': '5T5',
    '6T14': '5T5',
    '10T12': '5T5',
    '10T13': '5T5',
    '12T74': '5T5',
    '15T10': '5T5',
    '20T30': '5T5',
    '20T32': '5T5',
    '20T35': '5T5',
    '24T202': '5T5',
    '30T22': '5T5',
    '30T25': '5T5',
    '30T27': '5T5',
    '40T62': '5T5',
    '6T1': '6T1',
    '6T3': '6T3',
    '12T3': '6T3',
    '6T5': '6T5',
    '9T4': '6T5',
    '18T3': '6T5',
    '6T6': '6T6',
    '8T13': '6T6',
    '12T6': '6T6',
    '12T7': '6T6',
    '24T9': '6T6',
    '6T9': '6T9',
    '9T8': '6T9',
    '12T16': '6T9',
    '18T9': '6T9',
    '18T11': '6T9',
    '36T13': '6T9',
    '6T10': '6T10',
    '9T9': '6T10',
    '12T17': '6T10',
    '18T10': '6T10',
    '36T14': '6T10',
    '6T11': '6T11',
    '8T24': '6T11',
    '12T21': '6T11',
    '12T22': '6T11',
    '12T23': '6T11',
    '12T24': '6T11',
    '16T61': '6T11',
    '24T46': '6T11',
    '24T47': '6T11',
    '24T48': '6T11',
    '6T13': '6T13',
    '9T16': '6T13',
    '12T34': '6T13',
    '12T35': '6T13',
    '12T36': '6T13',
    '18T34': '6T13',
    '18T36': '6T13',
    '24T72': '6T13',
    '36T53': '6T13',
    '36T54': '6T13',
    '6T15': '6T15',
    '10T26': '6T15',
    '15T20': '6T15',
    '20T89': '6T15',
    '30T88': '6T15',
    '36T555': '6T15',
    '40T304': '6T15',
    '45T49': '6T15',
    '6T16': '6T16',
    '10T32': '6T16',
    '12T183': '6T16',
    '15T28': '6T16',
    '20T145': '6T16',
    '20T149': '6T16',
    '30T164': '6T16',
    '30T166': '6T16',
    '30T176': '6T16',
    '36T1252': '6T16',
    '40T589': '6T16',
    '40T592': '6T16',
    '45T96': '6T16',
    '7T1': '7T1',
    '7T2': '7T2',
    '14T2': '7T2',
    '7T3': '7T3',
    '21T2': '7T3',
    '8T1': '8T1',
    '8T5': '8T5',
    '9T1': '9T1'}
class ArtinBound(ColTest):
    def __call__(self, db, query):
        group, dim, container, N = query.get("GaloisLabel"), query.get("Dim"), query.get("Container"), IntegerSet(query.get("Conductor"))
        if isinstance(group, dict) and "$in" in group:
            # Artin reps are stored using the minimal transitive rep for the group
            groups = set(minimal_label.get(G) for G in group["$in"])
            if None in groups:
                return False, None, None
        elif group not in minimal_label:
            return False, None, None
        else:
            groups = [minimal_label[group]]
        if isinstance(dim, dict) or isinstance(container, dict):
            # This could be improved, but for simplicity we just don't guarantee completeness in this case
            return False, None, None
        bounds = {
            "2T1": [(1, "2t1", 10000)], # C2
            "3T1": [(1, "3t1", 11180)], # C3
            "4T1": [(1, "4t1", 796)], # C4
            "5T1": [(1, "5t1", 752)], # C5
            "6T1": [(1, "6t1", 577)], # C6
            "3T2": [(2, "3t2", 177662241)], # S3
            "7T1": [(1, "7t1", 483)], # C7
            "8T1": [(1, "8t1", 249)], # C8
            "4T3": [(2, "4t3", 22500)], # D4
            "8T5": [(2, "8t5", 215444)], # Q8
            "9T1": [(1, "9t1", 387)], # C9
            "5T2": [(2, "5t2", 40000)], # D5
            "4T4": [(3, "4t4", 3375000)], # A4
            "6T3": [(2, "6t3", 22500)], # D6
            "7T2": [(2, "7t2", 40000)], # D7
            "6T5": [(2, "6t5", 2828)], # C3 x S3
            "5T3": [(4, "5t3", 1600000000)], # F5
            "7T3": [(3, "7t3", 1000000)], # C7:C3
            "4T5": [(3, "4t5", 22497), (3, "6t8", 635168)], # S4
            "6T6": [(3, "6t6", 22497)], # A4 x C2
            "6T10": [(4, "6t10", 3374494)], # C3^2:C4
            "6T9": [(4, "6t9", 7998219)], # S3^2
            "6T11": [(3, "6t11", 22497)], # S4 x C2
            "5T4": [(3, "12t33", 66627), (4, "5t4", 613778), (5, "6t12", 52222435)], # A5
            "6T13": [(4, "6t13", 22500), (4, "12t34", 3375000)], # SO+(4,2)
            "5T5": [(4, "5t5", 7225), (4, "10t12", 614125), (5, "6t14", 52200625), (5, "10t13", 52200625), (6, "20t30", 4437053125)], # S5
            "6T15": [(5, "6t15", 287296), (8, "36t1252", 23534089616228), (9, "10t26", 174981250375214), (10, "30t88", 10077696000000000)], # A6
            "6T16": [(5, "6t16", 3600), (5, "12t183", 216000), (9, "10t32", 52753592444), (9, "20t145", 174981250375214), (10, "30t176", 167961600000000), (16, "36t1252", 553853374064674583164228907)], # S6
        }
        reasons = set()
        for group in groups:
            if group in bounds:
                L = bounds[group]
                for i, (d, P, M) in enumerate(L):
                    if dim in [d, None] and container in [P, None]:
                        if N.bounded(M):
                            if i == 0:
                                dimcon = ""
                            elif all(trip[0] < d for trip in L[:i]):
                                dimcon = f" dimension {d},"
                            else:
                                dimcon = f" dimension {d}, container {P},"
                            reasons.add(f"group {group},{dimcon} and conductor at most {M}")
                            break
                        else:
                            return False, None, None
                else:
                    dimcon = [f"group {group}"]
                    if dim is not None:
                        dimcon.append(f"dimension {dim}")
                    if container is not None:
                        dimcon.append(f"container {container}")
                    dimcon = display_opts(dimcon, "and")
                    reasons.add(f"{dimcon} (no such Artin representations)")
        return True, "Artin representations with " + "; ".join(sorted(reasons)), None


#### Finite groups ####

class GroupBound(ColTest):
    def __call__(self, db, query):
        N, td, pd, Qd, perfect, simple, abelian = IntegerSet(query.get("order")), IntegerSet(query.get("transitive_degree")), IntegerSet(query.get("permutation_degree")), IntegerSet(query.get("linQ_dim")), query.get("perfect"), query.get("simple"), query.get("abelian")
        # First missing
        # PSL(2,2729) = 10162031880
        #POmega-(4,53)= 11082179160
        # PSU(3,23)   = 26056457856
        # 2B(2,128)   = 34093383680
        # Suz         = 448345497600
        # ON          = 460815505920
        # G(2,7)      = 664376138496
        # PSL(4,7)    = 2317591180800
        # PSp(4,23)   = 20674026236160
        #POmega+(10,2)= 23499295948800
        # PSU(5,4)    = 53443952640000
        # PSU(4,9)    = 101798586432000
        # PSp(10,2)   = 24815256521932800
        # 2G(2,243)   = 49825657439340552
        #POmega+(8,4) = 67010895544320000
        #POmega-(8,4) = 67536471195648000
        # 3D(4,4)     = 67802350642790400
        # PSp(6,7)    = 273457218604953600
        # PSL(8,2)    = 5348063769211699200
        #POmega-(12,2)= 51615733565620224000
        # PSL(5,7)    = 187035198320488089600
        # PSL(6,4)    = 361310134959341568000
        #POmega-(10,3)= 650084965259666227200
        # PSU(6,4)    = 1120527288631296000000
        # Omega(9,4)  = 4408780839651901440000
        # PSp(8,4)    = 4408780839651901440000
        # PSU(7,3)    = 72853912155490594652160
        # 2F(4,8)     = 264905352699586176614400
        # PSU(9,2)    = 325473292721108444774400
        # F(4,3)      = 5734420792816671844761600
        # PSL(7,4)    = 72736898347485916060188672000
        # PSU(8,3)    = 261303669649855006027009228800
        ord2000 = IntegerSet({"$lte": 2000, "$nin":[512,640,768,896,1024,1152,1280,1408,1536,1664,1792,1920]})
        if N.is_subset(ord2000):
            return True, "groups of order at most 2000 except orders larger than 500 that are multiples of 128", None
        if perfect is True and N.bounded(50000):
            return True, "perfect groups of order at most 50000", None
        if simple is True and abelian is False and N.bounded(10162031879):
            return True, "nonabelian simple groups of order less than 10162031880", None
        td48 = IntegerSet(top(31)).union(IntegerSet([33,47]))
        if td.is_subset(td48):
            return True, "groups with minimal transitive degree at most 47 (except 32)", None
        if td.bounded(47) and N.bounded(40000000000, infinity):
            return True, "groups with minimal transitive degree 32 and order at least 40 billion", None
        if pd.bounded(15):
            return True, "groups with minimal permutation degree at most 15", None
        if Qd.bounded(6):
            return True, r"groups with linear $\Q$-degree at most 6", None
        return False, None, None


##################################
# Specific completeness checkers #
##################################

CompletenessChecker("lfunc_search", [
    (("degree", "rational", "conductor"), CBound(1, True, 2800), "L-functions with degree 1 and conductor at most 2800"),
    ])


CompletenessChecker("mf_newforms", [
    ("Nk2", Bound(4000), "newforms with $Nk^2$ at most 4000"),
    (("char_order", "Nk2"), CBound(1, 40000), "newforms with trivial character and $Nk^2$ at most 40000"),
    (("level", "Nk2"), Bound(24, 40000), "newforms with level $N$ at most 24 and $Nk^2$ at most 40000"),
    (("level", "Nk2"), Bound(10, 100000), "newforms with level $N$ at most 10 and $Nk^2$ at most 100000"),
    (("level", "weight"), Bound(100, 12), "newforms with level at most 100 and weight at most 12"),
    # k > 1, dim S_k^new(N,chi) <= 100, Nk2 <= 40000
    (("weight", "char_order", "level"), CBound(2, 1, 50000), "newforms with trivial character, weight 2, and level at most 50000"),
    (("weight", "char_order", "level"), CPrimeBound(2, 1, 1000000), "newforms with trivial character, weight 2 and prime level at most a million")],
                    fill=[CMFFiller()])


CompletenessChecker("maass_rigor", [(("level", "spectral_parameter"), MaassBound())])


CompletenessChecker("hmf_forms", [(("level_norm"), HMFBound())])


CompletenessChecker("bmf_forms", [("level_norm", BianchiBound(ec=False))], fill=[FieldLabelFiller(False)])


# No completeness guarantees for Siegel modular forms


CompletenessChecker("ec_curvedata", [
    ("conductor", Bound(500000), "elliptic curves with conductor at most 500000"),
    ("conductor", PrimeBound(300000000), "elliptic curves with prime conductor at most 300 million"),
    ("conductor", Smooth(10), "elliptic curves with 7-smooth conductor"),
    ("absD", Bound(500000), "elliptic curves with minimal discriminant at most 500000")])


CompletenessChecker("ec_nfcurves", [("conductor_norm", BianchiBound(ec=True))], fill=[FieldLabelFiller(True)])


# No completeness guarantees for genus 2 curves


# Skip modular curves for the moment


CompletenessChecker("hgcwa_passports", [
    ("genus", Bound([2, 4]), "groups acting as automorphisms of curves of genus 2, 3 or 4"),
    (("genus", "g0"), Bound([2, 15], 0), "groups G acting as automorphisms of curves X with the genus of X at most 15 and the genus of X/G equal to 0")])


CompletenessChecker("av_fq_isog", [
    (("g", "q"), Bound(1, RealSet((-infinity, 503), [510, 520], [620, 630], [728,732], [1022,1030])), "isogeny classes of elliptic curves over fields of cardinality less than 500 or 512, 625, 729, 1024"),
    (("g", "q"), Bound(2, RealSet((-infinity, 223), [242, 250], [252, 256], [338, 346], [510, 520], [620, 630], [728,732], [1022,1030])), "isogeny classes of abelian varieties of dimension at most 2 over fields of cardinality at most 211 or 243, 256, 343, 512, 625, 729, 1024"),
    (("g", "q"), Bound(3, 25), "isogeny classes of abelian varieties of dimension at most 3 over fields of cardinality at most 25"),
    (("g", "q"), Bound(4, 5), "isogeny classes of abelian varieties of dimension at most 4 over fields of cardinality at most 5"),
    (("g", "q"), Bound(5, 3), "isogeny classes of abelian varieties of dimension at most 5 over GF(2) and GF(3)"),
    (("g", "q"), Bound(6, 2), "isogeny classes of abelian varieties of dimension at most 6 over GF(2)")],
                    fill=[SumFiller("g", "p_rank", "p_rank_deficit"),
                          SumFiller("g", "angle_rank", "angle_corank")])


CompletenessChecker("belyi_galmaps", [("deg", Bound(6), "Belyi maps of degree at most 6")])


CompletenessChecker("nf_fields", [((), NFBound())])


CompletenessChecker("lf_fields", [(("n", "p"), Bound(23, 199), "p-adic fields of degree at most 23 and residue characteristic at most 199")], fill=[MulFiller("n", "e", "f")])


CompletenessChecker("lf_families", [(("n0", "n", "p"), Bound(1, 47, 199), "families of p-adic fields of degree at most 47 and residue characteristic at most 199"),
                                    (("n0", "n_absolute", "p"), Bound(15, 47, 199), "families of p-adic extensions with absolute degree at most 47, base degree at most 15 and residue characteristic at most 199")],
                    fill=[MulFiller("e_absolute", "e0", "e", backfill=True),
                          MulFiller("f_absolute", "f0", "f", backfill=True),
                          MulFiller("n", "e", "f"),
                          MulFiller("n0", "e0", "f0"),
                          MulFiller("n_absolute", "n0", "n", backfill=True),
                          MulFiller("n_absolute", "e_absolute", "f_absolute")])


CompletenessChecker("char_dirichlet", [("modulus", Bound(1000000), "Dirichlet characters with modulus at most a million")])


CompletenessChecker("artin_reps", [(("GaloisLabel", "Conductor"), ArtinBound())])


CompletenessChecker("hgm_families", [("degree", Bound(7), "hypergeometric families with degree at most 7")])


CompletenessChecker("gps_transitive", [
    ("n", Bound(RealSet((-infinity, 32), [33, 47])), "transitive groups of degree at most 47 (except 32)"),
    (("n", "order"), Bound(47, 511), "transitive groups of degree 32 and order at most 511"),
    (("n", "order"), Bound(47, (39999999999, infinity)), "transitive groups of degree at most 47 and order at least 40 billion")])


CompletenessChecker("gps_st", [
    (("rational", "weight", "degree"), CBound(True, 1, 6), "rational Sato-Tate groups of weight at most 1 and degree at most 6"),
    (("rational", "weight", "degree"), Specific([True], [0], [1]), "rational Sato-Tate groups of weight 0 and degree 1"),
    (("weight", "degree", "components"), CBound(0, 1, 10000), "Sato-Tate groups of weight 0, degree 1 and at most 10000 components")])


CompletenessChecker("gps_groups", [((), GroupBound())], null_override=["transitive_degree", "permutation_degree", "linQ_dim"])


# Nothing for lat_lattices
