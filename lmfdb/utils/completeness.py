
# Decision: Lean interface should not depend on Sage, but only things that are simple to pip install (so psycopg2, lmfdb-lite are okay; maybe split off parts of the LMFDB codebase
# Question: depend on Sage?  Want it for primality and smoothness testing, prime lists
# Does completeness code have access to database?  New tables with data for complicated cases (NF > HMF > Artin > Maass > ECNF > Bianchi > Groups > others)?  For many tables it'll be easier to put it source code.
# What does API look like for running LMFDB queries from Lean?  If we use parsing code in LMFDB, could have command line input that echoes search input boxes.  How is output formatted?  Json?  TSV?  Which columns?
# Should completeness code return reasons (which part of logic showed it was complete)?  Caveats (e.g. ECNF completeness depends on unproven modularity theorems)
# TODO: remove filt, add fill
# TODO: move data into postgres, write code to generate them from LMFDB when applicable

from collections import defaultdict
from sage.all import factor, prod, factorial, is_prime, next_prime, prime_range, ZZ

lookup = {}

def nullcount_query(query, cols):
    """
    Returns a modified query with all reference to a given list of columns removed, and conditions added that the columns are null.
    """
    if isinstance(query, list): # can happen recursively in $or queries
        return [remove_from_query(D, cols) for D in query]
    query = dict(query)
    for key, value in list(query.items()):
        if key in ["$not", "$and", "$or"]:
            L = remove_from_query(value, cols)
            # Remove empty items
            L = [D for D in L if D]
            if L:
                query[key] = L
            else:
                del query[key]
        else:
            if key.split(".")[0] in cols:
                del query[key]
    for col in cols:
        query[col] = None
    return query

class CompletenessChecker:
    """
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
    def __init__(self, table, checkers, fill=None):
        self.table = table
        lookup[table] = self
        self.extract = not all(len(check) == 2 for check in checkers)
        for i, check in enumerate(checkers):
            if len(check) == 2:
                cols, test = check
                reason = caveat = None
                filt = lambda query: True
            elif len(check) == 3:
                cols, test, reason = check
                caveat = None
                filt = lambda query: True
            elif len(check) == 4:
                cols, test, reason, caveat = check
                filt = lambda query: True
            else:
                cols, test, reason, caveat, filt = check
            if not isinstance(cols, tuple):
                cols = (cols,)
            checkers[i] = (cols, test, reason, caveat, filt)
        self.checkers = checkers
        self.fill = fill

    def _standardize(self, query):
        """
        Different queries can yield equivalent logical expressions.
        If ``$or`` is present, this function moves everything into the ``$or``
        for simplified processing.
        """
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
            reasons, caveats = set()
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
            search_columns = set(nulls).intersection(table._columns_searched(query))
            # Ignore columns based on search_array
            if search_array is not None:
                search_columns = {col for col in search_columns if search_array.null_column_explanations.get(col) is not False}
            if search_columns and table.exists(nullcount_query(query, search_columns)):
                # Query referred to a column where not all data was computed, so we cannot guarantee completeness
                return False, None, None
        if self.fill:
            self.fill(query)
        for cols, test, reason, caveat, filt in self.checkers:
            print(all(col in query for col in cols), filt(query))
            if all(col in query for col in cols) and filt(query):
                if self.extract:
                    # In this case, we use the reason specified in the list of checkers
                    if test(db, *[query[col] for col in cols]):
                        return True, reason, caveat
                else:
                    # Here we delegate the reason and caveat to the test function
                    return test(db, query)
        return False, None, None

class ColTest:
    def _upper_bound(self, D, n):
        if n is None:
            return True # No constrait; for one ended intervals
        if D is None:
            return False # No information
        if isinstance(D, dict):
            return ("$lt" in D and D["$lt"] <= n or # For integer valued columns, this could be strengthed a bit, but $lte constraints are more common in the LMFDB because they're entered using ranges
                     "$lte" in D and D["$lte"] <= n or
                     "$in" in D and all(d <= n for d in D["$in"]))
        return D <= n

    def _lower_bound(self, D, n):
        if n is None:
            return True # No constrait; for one ended intervals
        if D is None:
            return False # No information
        if isinstance(D, dict):
            return ("$gt" in D and D["$gt"] >= n or
                     "$gte" in D and D["$gte"] >= n or
                     "$in" in D and all(d >= n for d in D["$in"]))
        return D >= n

class Bound(ColTest):
    """
    Check that the inputs lie in a box.
    """
    def __init__(self, *bounds):
        self.bounds = bounds

    def __call__(self, db, Ds):
        ub, lb = self._upper_bound, self._lower_bound
        return all((isinstance(bound, tuple) and lb(D, bound[0]) and ub(D, bound[1]) or
                    not isinstance(bound, tuple) and ub(D, bound))
                   for (D, bound) in zip(Ds, self.bounds))

class CBound(ColTest):
    """
    Given constraints on a set of values, check that the last value lies in an interval

    Note that overlapping Bound boxes is better when applicable,
    since this test will only match queries where the constraints are specified exactly
    """
    def __init__(self, *constraints):
        self.constraints = constraints[:-1]
        self.bound = constraints[-1]

    def __call__(self, db, Ds):
        b, ub, lb, D = self.bound, self._upper_bound, self._lower_bound, Ds[-1]
        return (self.constraints == Ds[:-1] and
                (isinstance(b, tuple) and lb(D, b[0]) and ub(D, b[1]) or
                 not isinstance(b, tuple) and ub(D, b)))

def all_prime(D):
    if isinstance(D, dict):
        return list(D) == ["$in"] and all(is_prime(p) for p in D["$in"])
    return is_prime(D)

class PrimeBound(ColTest):
    def __init__(self, *bounds):
        self.bounds = bounds

    def __call__(self, db, Ds):
        ub, lb = self._upper_bound, self._lower_bound
        return all((isinstance(bound, tuple) and lb(D, bound[0]) and ub(D, bound[1]) or
                    not isinstance(bound, tuple) and ub(D, bound)) and
                   all_prime(D)
                   for (D, bound) in zip(Ds, self.bounds))

class Smooth(ColTest):
    def __init__(self, M):
        self.M = M

    def __call__(self, db, m):
        ub = self._upper_bound
        m, M = ZZ(m), self.M
        # Could improve this slightly to allow larger ranges that all happen to be smooth.
        return ub(m, next_prime(M) - 1) or not isinstance(m, dict) and m == prod(p**m.valuation(p) for p in prime_range(M))

class Specific(ColTest):
    def __init__(self, *constraints):
        self.constraints = constraints

    def __call__(self, db, Ds):
        return all(D in constraint for (D, constraint) in zip(Ds, self.constraints))


class CPrimeBound(ColTest):
    """
    Similar to CBound, but requires Ds to all be prime
    """
    def __init__(self, *constraints):
        self.constraints = constraints[:-1]
        self.bound = constraints[-1]

    def __call__(self, db, Ds):
        b, D = self.bound, Ds[-1]
        return (self.constraints == Ds[:-1] and
                (isinstance(b, tuple) and lb(D, b[0]) and ub(D, b[1]) or
                not isinstance(b, tuple) and ub(D, b)) and
                all_prime(D))

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
        level = query["level"]
        spectral_parameter = query["spectral_parameter"]
        try:
            Rbound = maxR[int(level)]
            complete = self._upper_bound(spectral_parameter, Rbound)
            if complete:
                return True, f"Maass forms with level {level} and spectral parameter at most {Rbound:.4f}", None
        except (TypeError, KeyError): # Level might be a dictionary, or level might not be in it
            return False, None, None

class BianchiBound(ColTest):
    def __init__(self, ec):
        self.ec = ec

    def __call__(self, db, query):
        # Set degree/abs_disc or field_disc from field_label
        # Set conductor_norm/level_norm from conductor_ideal
        if self.ec:
            n, r = query.get("signature")
            D = query.get("abs_disc")
            N = query["conductor_norm"]
            caveat = "Only modular elliptic curves are included"
            def reason(n, r, D, M):
                if r == 0:
                    d = D // 4 if D % 4 == 0 else D
                    return r"elliptic curves over \Q(\sqrt{-%s}) with conductor norm at most %s" % (d, M)
                if n == r:
                    if n == 2:
                        d = D // 4 if D % 4 == 0 else d
                        return r"elliptic curves over \Q(\sqrt{%s}) with conductor norm at most %s" % (d, M)
                    if n == 3:
                        adj = "cubic"
                    elif n == 4:
                        adj = "quartic"
                    elif n == 5:
                        adj = "quintic"
                    elif n == 6:
                        adj = "sextic"
                    return f"elliptic curves with conductor norm at most {M} over totally real {adj} fields with discriminant at most {D}"
                if n == 3 and r == 1:
                    return f"elliptic curves over 3.1.23.1 with conductor norm at most {M}"
        else:
            n, r = 2, 0
            D = query.get("field_disc")
            if D is not None:
                D = abs(D)
            N = query["level_norm"]
            caveat = None
            def reason(n, r, D, M):
                d = D // 4 if D % 4 == 0 else D
                return r"Bianchi modular forms over \Q(\sqrt{-%s}) with level norm at most %s" % (d, M)
        ub = self._upper_bound
        if n == 2 and r == 0: # imaginary quadratic, either EC or BMF
            if D == 3:
                M = 150000
            elif D == 4:
                M = 100000
            elif D < 12:
                M = 50000
            elif D in [19, 43]:
                M = 15000
            elif D == 67:
                M = 10000
            elif D in [31, 163]:
                M = 5000
            elif D == 23:
                M = 3000
            elif D < 121:
                M = 1000
            elif D < 700:
                M = 100
            else:
                return False, None, None
            return ub(N, M), reason(n, r, D, M), caveat
        if n == r: # totally real, EC
            if n == 2:
                return (D <= 497) and ub(N, 5000), reason(2, 2, D, 5000), None
            if n == 3:
                return (D <= 1957) and ub(N, 2059), reason(3, 3, 1957, 2059), None
            if n == 4:
                return (D <= 19821) and ub(N, 4091), reason(4, 4, 19821, 4091), caveat
            if n == 5:
                return (D <= 195829) and ub(N, 1013), reason(5, 5, 195829, 1013), caveat
            if n == 6:
                return (D <= 1997632) and ub(N, 961), reason(6, 6, 1997632, 961), caveat
        if n == 3 and r == 1: # mixed case, EC
            return (D == 23) and ub(N, 20000), reason(3, 1, D, 20000), caveat
        return False, None, None

def minNone(*args):
    """
    A version of min that treats None as infinity.
    """
    args = [x for x in args if x is not None]
    if args:
        return min(args)

def integer_options(X, bound1=None, bound2=None, limit=None, stickelberger=None):
    """
    Given a query for X, returns the list of all integers satisfying the query.  ``None`` will be returned if the result exceeds a provided limit (or if no limit is provided and result is not bounded)

    INPUT:

    - ``X`` -- an integer or query dictionary
    - ``bound1`` and ``bound2`` -- if both provided, act as lower and upper bound on integers returned.  If only ``bound1`` provided, only non-negative integers at most this value will be returned.
    - ``limit`` -- if provided, gives a maximum number of integers returned.  If too many would be returned, returns ``None`` instead.
    - ``stickelberger`` -- if provided, only integers congruent to an element of the given list modulo 4 are returned
    """
    if bound2 is None:
        lower_bound, upper_bound = 0, bound1
    elif bound1 is not None:
        lower_bound, upper_bound = bound1, bound2
    else:
        raise ValueError("Do not specify bound2 as a keyword argument")
    if isinstance(X, dict):
        lb = max(X.get("$gte", lower_bound), X.get("$gt", lower_bound - 1) + 1)
        nin = set(X.get("$nin", []))
        if upper_bound is None and "$lte" not in X and "$lt" not in X:
            return
        ub = minNone(upper_bound, X["$lte"] + 1 if "$lte" in X else None, X.get("$lt"))
        ne = X.get("$ne")
        opts = X.get("$in")
        if opts is None:
            opts = range(lb, ub)
        ans = []
        for N in opts:
            if lb <= N < ub and (stickelberger is None or N % 4 in stickelberger) and (ne is None or N != ne) and (N not in nin):
                ans.append(N)
                if limit is not None and len(ans) > limit:
                    return
        return ans
    elif X is None:
        return list(range(lower_bound, upper_bound))
    if upper_bound is not None and X >= upper_bound:
        return []
    if X < lower_bound:
        return []
    return [X]

def cap(X, Y, k):
    """
    Return X, modified to be bounded above by Y^k.

    INPUT:

    - ``X`` -- a number or query dictionary
    - ``Y`` -- a number or query dictionary
    - ``k`` -- a positive exponent

    OUTPUT:

    - a number or query dictionary of numbers matching X and at most Y^k.  None indicates no constraint, False an incompatibility.
    """
    def kpow(a):
        if a is not None:
            return a**k
    if Y is None:
        return X
    elif isinstance(Y, dict):
        if isinstance(X, dict):
            X = dict(X)
            if "$lte" in Y:
                X["$lte"] = minNone(X.get("$lte"), kpow(Y["$lte"]))
            if "$lt" in Y:
                X["$lt"] = minNone(X.get("$lt"), kpow(Y["$lt"]))
            if "$in" in Y:
                X["$lte"] = minNone(X.get("$lte"), kpow(max(Y["$in"])))
        elif ("$lte" in Y and kpow(Y["$lte"]) < X or
              "$lt" in Y and kpow(Y["$lt"]) <= X or
              "$in" in Y and kpow(max(Y["$in"])) < X):
            return False
    elif isinstance(X, dict):
        X = dict(X)
        X["$lte"] = minNone(X.get("$lte"), kpow(Y))
    elif kpow(Y) < X:
        return False
    return X

def display_opts(L):
    """
    Display a list of options with commas and an or
    """
    L = [str(x) for x in L]
    if len(L) == 2:
        L = [L[0] + " or " + L[1]]
    elif len(L) > 1:
        L[-1] = " or " + L[-1]
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
        octic_2_group = gps2 = (1,2,3,4,5,6,7,8,9,10,11,15,16,17,18,19,20,21,22,26,27,28,29,30,31,35)
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
            5: {1: 7500,  2: 150, 3: 24,  4: 8},
            6: {1: 2000,  2: 32},
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

        # nSG[n] is a list of pairs (T, Gs) so that we hae completeness in degree n for number fields with Galois group nTt for t in Gs and unramified outside S for any subset S of T.
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


    def ram_reason(n, S, galt):
        if galt is None:
            gals = f"of degree {n}"
        else:
            gals = display_opts([f"{n}T{t}" for t in galt])
            gals = f"with Galois group {gals}"
        if isinstance(next(iter(S)), tuple):
            S = ["{" + ",".join(str(p) for p in sorted(s)) + "}" for s in S]
            S = display_opts(S)
        else:
            S = "{" + ",".join(str(p) for p in sorted(S)) + "}"
        return "number fields {gals} that are unramified outside {S}"

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
                ans.append(f"degree {','.join(str(tup[0]) for tup in tups)}")
            if tups[0][1] is not None:
                sigs = [f"[{tup[0]-2*tup[1]},{tup[1]}]" for tup in tups]
                ans.append(f"signature {','.join(sigs)}")
            if tups[0][2] is not None:
                ts = [f"({','.join(str(t) for t in tup[2])})" if len(tup[2]) > 1 else str(tup[2][0]) for tup in tups]
                gals = [f"{tup[0]}T{tt}" for (tup, tt) in zip(tups, ts)]
                ans.append(f"Galois group {','.join(gals)}")
            if tups[0][3] is not None:
                ans.append(f"unramified outside {','.join('{'+','.join(str(p) for p in tup[3])+'}' for tup in tups)}")
            if tups[0][4] is not None:
                ans.append(f"absolute discriminant at most {','.join(str(tup[4]) for tup in tups)}")
            if tups[0][5] is not None:
                ans.append(f"Galois root discriminant at most {','.join(str(tup[5]) for tup in tups)}")
            return ", ".join(ans)
        strings = []
        by_pattern = defaultdict(list)
        for reason in reasons:
            if isinstance(reason, str):
                strings.append(reason)
            else:
                by_pattern[tuple(i for i in range(6) if reason[i] is None)].append(reason)
        print(by_pattern)
        return "number fields with " + "; ".join(strings + [describe(V) for V in by_pattern.values()])

    def clear_signatures(self, n, D, r2opts, reasons):
        ub = self._upper_bound
        if 2 <= n < len(self._maxD):
            for r2 in set(r2opts):
                M = self._maxD[n][r2]
                if M is not None and ub(D, M):
                    r2opts.remove(r2)
                    reasons.add((n, r2, None, None, M, None))

    def clear_r2G(self, n, D, r2opts, galt, reasons):
        ub = self._upper_bound
        r2G = defaultdict(dict)
        for (r2, Gs, M) in self._r2G.get(n, []):
            if r2 in r2opts and ub(D, M):
                for t in galt.intersection(Gs):
                    r2G[t][r2] = (r2, Gs, M)
        for t in galt.intersection(r2G):
            if set(r2G[t]) == r2opts:
                galt.remove(t)
                for r2, Gs, M in r2G[t].values():
                    reasons.add((n, r2, Gs, None, M, None))

    def clear_grd(self, n, grd, galt, reasons):
        ub = self._upper_bound
        by_t = {}
        for (Gs, M) in self._grd.get(n, []):
            if ub(grd, M):
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
        if not update_galt:
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

        for T, Gs in self._nSG.get(n, []):
            if S.issubset(T):
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
            galt = set()
            for Gs in pos_constraints:
                galt.update(Gs)
        else:
            galt = set(range(1, self._num_trans[n] + 1))
        for Gs in neg_constraints:
            galt.difference_update(Gs)
        return galt

    def rd_grd_ratio(self, n, galt):
        if n < len(self._rdgrd) and galt <= len(self._rdgrd[n]):
            return 1 / self._rdgrd[n][galt - 1]

    def get_S(self, ramps, radical):
        S = None
        if radical is not None:
            if isinstance(radical, dict):
                if not (list(radical) == ["$lte"] and isinstance(ramps, dict) and "$containedin" in ramps and prod(ramps["$containedin"]) == radical["$lte"]):
                    # Such constraints are not created by parsing code, so we give up
                    return
                # Now we can just fall back on ramps parsing below
            else:
                S = set(factor(radical))
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
        ub = self._upper_bound
        D, rd, grd = query.get("disc_abs"), query.get("rd"), query.get("grd")
        if ub(D, 1656109):
            reasons.add("discriminant at most 1656109")
            return True, None
        if ub(rd, 5.989):
            reasons.add("root discriminant at most 5.989")
            return True, None
        if ub(grd, 5.989):
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
        if n > 25:
            return False, None
        ub, lb = self._upper_bound, self._lower_bound

        r2, D, sign, rd, grd = query.get("r2"), query.get("disc_abs"), query.get("disc_sign"), query.get("rd"), query.get("grd")
        r2opts = integer_options(r2, n//2+1)
        if sign == 1:
            r2opts = [r2 for r2 in r2opts if r2 % 2 == 0]
        elif sign == -1:
            r2opts = [r2 for r2 in r2opts if r2 % 2 == 1]
        if n == 2 and r2opts == [1]:
            # Imaginary quadratic fields, where we can use Mark Watkins' paper (Class groups of imaginary quadratic fields) to guarantee completeness based on class number
            h = query.get("class_number")
            C = query.get("class_group")
            if isinstance(C, list) and h is None:
                h = prod(C)
            if ub(h, 97) or lb(h, 99) and up(h, 100):
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
        if grd is not None:
            rd = cap(rd, grd, 1)
            if rd is False:
                reasons.add("incompatible conditions: root discriminant and Galois root discriminant")
                return True, None
        if rd is not None:
            D = cap(D, rd, n)
            if D is False:
                reasons.add("incompatible conditions: root discriminant and discriminant")
                return True, None
        if D is not None:
            self.clear_signatures(n, D, r2opts, reasons)
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
            if D is not None:
                self.clear_r2G(n, D, r2opts, galt, reasons)
                if not galt:
                    return True, caveat

            ## Completeness 3: degree, Galois group, Galois root discriminant ##
            if D is not None:
                rd = cap(rd, D, 1/n)
                if rd is False:
                    reasons.add("incompatible conditions: root discriminant and discriminant")
                    return True, None
            if rd is not None:
                ratio = self.rd_grd_ratio(n, galt)
                if ratio is not None:
                    grd = cap(grd, rd, ratio)
                    if grd is False:
                        reasons.add("incompatible conditions: root discriminant and Galois root discriminant")
                        return True, None
            if grd is not None:
                self.clear_grd(n, grd, galt, reasons)
                if not galt:
                    return True, caveat
        else:
            galt = None

        ## Completeness 4: degree, ramified primes, and Galois group (optional)
        # Can fill rams from discriminant range, or from radical
        ramps, radical, nram = query.get("ramps"), query.get("radical"), query.get("num_ram")
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
        if D is not None:
            if all(r2 % 2 == 1 for r2 in r2opts):
                stickelberger = [0,3]
            elif all(r2 % 2 == 0 for r2 in r2opts):
                stickelberger = [0,1]
            else:
                stickelberger = [0,1,3]
            opts = integer_options(D, limit=10, stickelberger=stickelberger)
            if opts is not None:
                for d in opts:
                    S = tuple(p for (p,e) in factor(d))
                    if not self.clear_S(n, S, galt, reasons, update_galt=False):
                        break
                else:
                    return True, caveat

            # Minkowski bound (only relevant for n>12)
            if n >= self._maxD:
                mbound = (3.14159265358979/4)**n * n**(2*n) / factorial(n)**2
                if ub(D, mbound):
                    reasons.add(f"number fields of degree {n} with discriminant at most {floor(mbound)} (Minkowski)")
                    return True, None
            # TODO: Odlyzko bounds

        return False, None


    def __call__(self, db, query):
        n = query.get("degree")
        print("n", n)

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
            nopts = integer_options(n, 48)
            if nopts is None:
                return False, None, None
            # Reverse order since we're less likely to have completeness in higher degree
            nopts.sort(reverse=False)
            caveats = set()
            for n in nopts:
                nquery = dict(query)
                nquery["n"] = n
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
            print("query", query)
            ok, caveats = self._one_n(db, query, reasons)
            if not ok:
                return False, None, None
        if len(reasons) > 1:
            reasons = {reason for reason in reasons if not reason.startswith("incompatible conditions")}
        return True, self.display_reason(reasons), caveats


class ArtinBound(ColTest):
    def __call__(self, db, query):
        group, dim, container, N = query.get("Group"), query.get("Dim"), query.get("Container"), query.get("Conductor")
        # TODO: need to ensure dim and container aren't complicated
        ub = self._upper_bound
        bounds = {
            "2.1": [(1, "2t1", 10000)], # C2
            "3.1": [(1, "3t1", 11180)], # C3
            "4.1": [(1, "4t1", 796)], # C4
            "5.1": [(1, "5t1", 752)], # C5
            "6.2": [(1, "6t1", 577)], # C6
            "6.1": [(2, "3t2", 177662241)], # S3
            "7.1": [(1, "7t1", 483)], # C7
            "8.1": [(1, "8t1", 249)], # C8
            "8.3": [(2, "4t3", 22500)], # D4
            "8.4": [(2, "8t5", 215444)], # Q8
            "9.1": [(1, "9t1", 387)], # C9
            "10.1": [(2, "5t2", 40000)], # D5
            "12.3": [(3, "4t4", 3375000)], # A4
            "12.4": [(2, "6t3", 22500)], # D6
            "14.1": [(2, "7t2", 40000)], # D7
            "18.3": [(2, "6t5", 2828)], # C3 x S3
            "20.3": [(4, "5t3", 1600000000)], # F5
            "21.1": [(3, "7t3", 1000000)], # C7:C3
            "24.12": [(3, "4t5", 22497), (3, "6t8", 635168)], # S4
            "24.13": [(3, "6t6", 22497)], # A4 x C2
            "36.9": [(4, "6t10", 3374494)], # C3^2:C4
            "36.10": [(4, "6t9", 7998219)], # S3^2
            "48.48": [(3, "6t11", 22497)], # S4 x C2
            "60.5": [(3, "12t33", 66627), (4, "5t4", 613778), (5, "6t12", 52222435)], # A5
            "72.40": [(4, "6t13", 22500), (4, "12t34", 3375000)], # SO+(4,2)
            "120.34": [(4, "5t5", 7225), (4, "10t12", 614125), (5, "6t14", 52200625), (5, "10t13", 52200625), (6, "20t30", 4437053125)], # S5
            "360.118": [(5, "6t15", 287296), (8, "36t1252", 23534089616228), (9, "10t26", 174981250375214), (10, "30t88", 10077696000000000)], # A6
            "720.763": [(5, "6t16", 3600), (5, "12t183", 216000), (9, "10t32", 52753592444), (9, "20t145", 174981250375214), (10, "30t176", 167961600000000), (16, "36t1252", 553853374064674583164228907)], # S6
        }
        if group in bounds:
            L = bounds[group]
            for i, (d, P, M) in enumerate(L):
                if dim in [d, None] and container in [P, None]:
                    if i == 0:
                        dimcon = ""
                    elif all(trip[0] < d for trip in L[:i]):
                        dimcon = f" dimension {d},"
                    else:
                        dimcon = f" dimension {d}, container {P},"
                    return ub(N, M), f"Artin representations with group {group},{dimcon} and conductor at most {M}", None
            dimcon = [f"group {group},"]
            if dim is not None:
                dimcon.append(f"dimension {dim},")
            if container is not None:
                dimcon.append(f"container {container},")
            if len(dimcon) > 1:
                dimcon[-1] = " and " + dimcon[-1]
            dimcon = " ".join(dimcon)[:-1]
            return True, f"There are no Artin representations with {dimcon}", None
        return False, None, None

class GroupBound(ColTest):
    def __call__(self, db, query):
        N, td, pd, Qd, perfect, simple, abelian = query.get("order"), query.get("transitive_degree"), query.get("permutation_degree"), query.get("linQ_dim"), query.get("perfect"), query.get("simple"), query.get("abelian")
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
        ub, lb = self._upper_bound, self._lower_bound
        if (ub(N, 511) or
            lb(N, 513) and ub(N, 639) or
            lb(N, 641) and ub(N, 767) or
            lb(N, 769) and ub(N, 895) or
            lb(N, 897) and ub(N, 1023) or
            lb(N, 1025) and ub(N, 1151) or
            lb(N, 1153) and ub(N, 1279) or
            lb(N, 1281) and ub(N, 1407) or
            lb(N, 1409) and ub(N, 1535) or
            lb(N, 1537) and ub(N, 1663) or
            lb(N, 1665) and ub(N, 1791) or
            lb(N, 1793) and ub(N, 1919) or
            lb(N, 1921) and ub(N, 2000)):
            return True, "groups of order at most 2000 except orders larger than 500 that are multiples of 128", None
        if perfect is True and ub(N, 50000):
            return True, "perfect groups of order at most 50000", None
        if simple and abelian is False and ub(N, 10162031879):
            return True, "nonabelian simple groups of order less than 10162031880", None
        if ub(td, 31):
            return True, "groups with minimal transitive degree at most 31", None
        if lb(td, 33) and ub(td, 47):
            return True, "groups with minimal transitive degree between 33 and 47", None
        if ub(td, 47) and lb(N, 40000000000):
            return True, "groups with minimal transitive degree 32 and order at least 40 billion", None
        if ub(pd, 15):
            return True, "groups with minimal permutation degree at most 15", None
        if ub(Qd, 6):
            return True, r"groups with linear $\Q$-degree at most 6", None
        return False, None, None

# Nothing for lfunc_search?
CompletenessChecker("mf_newforms", [
    ("Nk2", Bound(4000), "newforms with $Nk^2$ at most 4000"),
    (("char_order", "Nk2"), CBound(1, 40000), "newforms with trivial character and $Nk^2$ at most 40000"),
    (("level", "Nk2"), Bound(24, 40000), "newforms with level $N$ at most 24 and $Nk^2$ at most 40000"),
    (("level", "Nk2"), Bound(10, 100000), "newforms with level $N$ at most 10 and $Nk^2$ at most 100000"),
    (("level", "weight"), Bound(100, 12), "newforms with level at most 100 and weight at most 12"),
    # k > 1, dim S_k^new(N,chi) <= 100, Nk2 <= 40000
    (("weight", "char_order", "level"), CBound(2, 1, 50000), "newforms with trivial character, weight 2, and level at most 50000"),
    (("weight", "char_order", "level"), CPrimeBound(2, 1, 1000000), "newforms with trivial character, weight 2 and prime level at most a million")])
CompletenessChecker("maass_rigor", [(("level", "spectral_parameter"), MaassBound())])
# hmf_forms : upper bound on level norm by field; query from database?
CompletenessChecker("bmf_forms", [("level_norm", BianchiBound(ec=False))])
CompletenessChecker("ec_curvedata", [
    ("conductor", Bound(500000), "elliptic curves with conductor at most 500000"),
    ("conductor", PrimeBound(300000000), "elliptic curves with prime conductor at most 300 million"),
    ("conductor", Smooth(7), "elliptic curves with 7-smooth conductor")]) # TODO
CompletenessChecker("ec_nfcurves", [("conductor_norm", BianchiBound(ec=True))])
# Nothing for g2c_curves?
# Skip modular curves for the moment
CompletenessChecker("hgcwa_passports", [
    ("genus", Bound((2, 4)), "groups acting as automorphisms of curves of genus 2, 3 or 4"),
    (("genus", "g0"), Bound((2, 15), 0), "groups G acting as automorphisms of curves X with the genus of X at most 15 and the genus of X/G equal to 0")])
CompletenessChecker("av_fqisog", [
    (("g", "q"), Bound(1, 499), "isogeny classes of elliptic curves over fields of cardinality less than 500"),
    (("g", "q"), Bound(2, 211), "isogeny classes of abelian varieties of dimension at most 2 over fields of cardinality at most 211"),
    (("g", "q"), Bound(3, 25), "isogeny classes of abelian varieties of dimension at most 3 over fields of cardinality at most 25"),
    (("g", "q"), Bound(4, 5), "isogeny classes of abelian varieties of dimension at most 4 over fields of cardinality at most 5"),
    (("g", "q"), Bound(5, 3), "isogeny classes of abelian varieties of dimension at most 5 over GF(2) and GF(3)"),
    (("g", "q"), Bound(6, 2), "isogeny classes of abelian varieties of dimension at most 6 over GF(2)"),
    (("g", "q"), Specific([1], [512, 625, 729, 1024]), "isogeny classes of elliptic curves over fields of cardinality 512, 625, 729 and 1024"),
    (("g", "q"), Specific([2], [243, 256, 343, 512, 625, 729, 1024]), "isogeny classes of abelian surfaces over fields of cardinality a power of 2, 3, 5 or 7 up to 1024")])
CompletenessChecker("belyi_galmaps", [("deg", Bound(6), "Belyi maps of degree at most 6")])
CompletenessChecker("nf_fields", [((), NFBound())]) # Complicated, so delegate completely
CompletenessChecker("lf_fields", [(("n", "p"), Bound(23, 199), "p-adic fields of degree at most 23 and residue characteristic at most 199")])
CompletenessChecker("lf_families", [(("n0", "n", "p"), Bound(1, 47, 199), "families of p-adic fields of degree at most 47 and residue characteristic at most 199"),
                                    (("n0", "n_absolute", "p"), Bound(15, 47, 199), "families of p-adic extensions with absolute degree at most 47, base degree at most 15 and residue characteristic at most 199")]) # Should update query based on relations between ns, es, fs
CompletenessChecker("char_dirichlet", [("modulus", Bound(1000000), "Dirichlet characters with modulus at most a million")])
CompletenessChecker("artin_reps", [(("Group", "Conductor"), ArtinBound())])
CompletenessChecker("hgm_families", [("degree", Bound(7), "hypergeometric families with degree at most 7")])
CompletenessChecker("gps_transitive", [
    ("n", Bound(31), "transitive groups of degree at most 31"),
    ("n", Bound((33,47)), "transitive groups of degree at between 33 and 47"),
    (("n", "order"), Bound(47, 511), "transitive groups of degree 32 and order at most 511"),
    (("n", "order"), Bound(47, (40000000000, None)), "transitive groups of degree 32 and order at least 40 billion")])
CompletenessChecker("gps_st", [
    (("rational", "weight", "degree"), CBound(True, 1, 6), "rational Sato-Tate groups of weight at most 1 and degree at most 6"),
    (("rational", "weight", "degree"), Specific([True], [0], [1]), "rational Sato-Tate groups of weight 0 and degree 1"),
    (("weight", "degree", "components"), CBound(0, 1, 10000), "Sato-Tate groups of weight 0, degree 1 and at most 10000 components")])
CompletenessChecker("gps_groups", [((), GroupBound())]) # delegate completely
# Nothing for lat_lattices

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
