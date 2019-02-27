#
# See https://github.com/JohnCremona/sorting
#
# This file is code/psort.py from there.  It implements the sorting
# and labelling of ideals (including prime ideals).
#
from sage.all import ZZ, GF, Set, prod, srange, flatten, cartesian_product_iterator

# sort key for number field elements.  the list() method returns a
# list of the coefficients in terms of the power basis, constant
# first.

nf_key = lambda a: a.list()

# Elements of GF(p) already have a good cmp function

# Sort key for GF(p)[X]

FpX_key = lambda a: a.list()

# Sort key for Z_p.  The start_val=0 is needed for elements whose
# parent is Qp rather than Zp since over Qp the first entry is the
# coefficient of p^v with v the the valuation

Zp_key = lambda a: a.list(start_val=0)

# Sort key for Zp[X].  For example the key for
# (7 + 8*37 + 9*37^2 + O(37^3))*x^2 + (4 + 5*37 + 6*37^2 + O(37^3))*x
# + (1 + 2*37 + 3*37^2 + O(37^3))
# is
# [2, 1, 4, 7, 2, 5, 8, 3, 6, 9]
#
# The degree comes first, followed by the 0'th p-adic digit of each
# coefficient, then the 1st, etc.  The point of the flatten(zip()) is
# essentially to transpose a matrix (list of lists)

# We need a key function which depends on a p-adic precision k, and
# which only uses the p-adic digits up to the coefficient of p^{k-1}.
# We use our own version of Sage's c.padded_list(k) which does not
# always start with the p^0 coefficient.

def padded_list(c,k):
    try:
        a = list(c.expansion(start_val=0))
    except AttributeError:
        a = c.list(start_val=0)
    return a[:k] + [ZZ(0)]* (k-len(a))

def ZpX_key(k):
    return lambda f: [f.degree()] + flatten(zip(*[padded_list(c,k) for c in f.list()]))

###################################################
#
# Sorting primes over a number field K.
#
###################################################

def make_keys(K,p):
    """Find and sort all primes of K above p, and store their sort keys in
    a dictionary with keys the primes P and values their sort keys
    (n,j,e,i) with n the norm, e the ramificatino index, i the index
    (from 1) in the list of all those primes with the same (n,e), and
    j the index (from 1) in the sorted list of all with the same norm.
    This dict is stored in K in a dict called psort_dict, whose keys
    are rational primes p.
    """
    if not hasattr(K,'psort_dict'):
        K.psort_dict = {}
        K.primes_dict = {}
    if not p in K.psort_dict:
        #print("creating keys for primes above {}".format(p))
        key_dict = {}
        Fp = GF(p)
        g = K.defining_polynomial()
        QQx = g.parent()
        a = K.gen()
        PP = K.primes_above(p)

        if not p.divides(g.discriminant()):
            # the easier unramified case
            gfact = [h for h,e in g.change_ring(Fp).factor()]
            gfact.sort(key=FpX_key)
            hh = [QQx(h) for h in gfact]
            for P in PP:
                # exactly one mod-p factor h will be such that P|h(a).
                i = 1 + next((i for i,h in enumerate(hh) if h(a).valuation(P)>0), -1)
                assert i>0
                key_dict[P] = (P.norm(),P.ramification_index(),i)
        else:
            # the general ramified case factor g over Z_p to precision
            # p^k0 until the mod p^k1 reductions of the factors are
            # distinct, with k0 >= k1 >= 1
            k0 = 20
            ok = False
            while not ok:
                gfact = [h for h,e in g.factor_padic(p,k0)]
                nfact = len(gfact)
                gf = [h.lift() for h in gfact]
                k1 = 1
                while (k1<k0) and not ok:
                    hh = [h % p**k1 for h  in gf]
                    ok = len(Set(hh))==nfact
                    if not ok:
                        k1 += 1
                if not ok:
                    k0+=10
            # now hh holds the factors reduced mod p^k1 and these are
            # distinct so we sort the p-adic factors accordingly (these
            # will be first sorted by degree)
            gfact.sort(key=ZpX_key(k1))
            #print("p-adic factors: {}".format(gfact))
            #print("with keys {}".format([ZpX_key(k1)(h) for h in gfact]))
            hh = [h.lift() % p**k1 for h  in gfact]
            #print("p-adic factors mod {}^{}: {}".format(p,k1,hh))
            degs = list(Set([h.degree() for h in gfact]))
            hd = dict([(d,[h for h in hh if h.degree()==d]) for d in degs])

            # Finally we find the index of each prime above p
            for P in PP:
                e = P.ramification_index()
                f = P.residue_class_degree()
                hs = hd[e*f]
                # work out which h in hs matches P
                m = max([h(a).valuation(P) for h in hs])
                i = 1 + next((i for i,h in enumerate(hs) if h(a).valuation(P)==m), -1)
                assert i>0
                key_dict[P] = (P.norm(),e,i)

        # Lastly we add a field j to each key (n,e,i) -> (n,j,e,i)
        # which is its index in the sublist withe same n-value.  This
        # will not affect sorting but is used in the label n.j.

        vals = key_dict.values()
        new_key_dict = {}
        for P in key_dict:
            k = key_dict[P]
            j = 1 + sorted([v for v in vals if v[0]==k[0]]).index(k)
            new_key_dict[P] = (k[0],j,k[1],k[2])

        #print("Setting psort_dict and primes_dict for p={} for K={}".format(p,K))
        K.psort_dict[p] = new_key_dict
        K.primes_dict[p] = sorted(PP,key=lambda P: new_key_dict[P])

def prime_key(P):
    """Return the key (n,j,e,i) of a prime ideal P, where n is the norm, e
    the ramification index, i the index in the sorted list of primes
    with the same (n,e) and j the index in the sorted list or primes
    with the same n.

    The first time this is called for a prime P above a rational prime
    p, all the keys for all primes above p are computed and stored in
    the number field, by the make_keys function.
    """
    p = P.smallest_integer()
    K = P.number_field()
    try:
        return K.psort_dict[p][P]
    except (AttributeError, KeyError):
        make_keys(K,p)
        return K.psort_dict[p][P]

def prime_label(P):
    """ Return the label of a prime ideal.
    """
    n, j, e, i = prime_key(P)
    return "%s.%s" % (n,j)

def prime_from_label(K, lab):
    """Return the prime of K from a label, or 0 is there is no such prime
    """
    n, j = [ZZ(c) for c in lab.split(".")]
    p, f = n.factor()[0]
    make_keys(K,p)
    d = K.psort_dict[p]
    try:
        return next((P for P in d if d[P][:2]==(n,j)))
    except StopIteration:
        return 0

from sage.rings.infinity import Infinity
from sage.arith.all import primes
def primes_of_degree_iter(K, deg, condition=None, sort_key=prime_label, maxnorm=Infinity):
    """Iterator through primes of K of degree deg, sorted using the
    provided sort key, optionally with an upper bound on the norm.  If
    condition is not None it should be a True/False function on
    rational primes, in which case only primes P dividing p for which
    condition(p) holds will be returned.  For example,
    condition=lambda:not p.divides(6).
    """
    for p in primes(2,stop=maxnorm):
        if condition==None or condition(p):
            make_keys(K,p)
            for P in K.primes_dict[p]:
                if P.residue_class_degree()==deg and P.norm()<=maxnorm:
                    yield P

def primes_iter(K, condition=None, sort_key=prime_label, maxnorm=Infinity):
    """Iterator through primes of K, sorted using the provided sort key,
    optionally with an upper bound on the norm.  If condition is not
    None it should be a True/False function on rational primes,
    in which case only primes P dividing p for which condition(p) holds
    will be returned.  For example, condition=lambda:not p.divides(6).
    """
    # print("starting primes_iter with K={}, maxnorm={}".format(K,maxnorm))
    # The set of possible degrees f of primes is the set of cycle
    # lengths in the Galois group acting as permutations on the roots
    # of the defining polynomial:
    dlist = Set(sum([list(g.cycle_type()) for g in K.galois_group('gap').group()],[]))

    # Create an array of iterators, one for each residue degree
    PPs = [primes_of_degree_iter(K,d, condition, sort_key, maxnorm=maxnorm)  for d in dlist]

    # pop the first prime off each iterator (allowing for the
    # possibility that there may be none):
    Ps = [0 for d in dlist]
    ns = [Infinity for d in dlist]
    for i,PP in enumerate(PPs):
        try:
            P = PP.next()
            Ps[i] = P
            ns[i] = P.norm()
        except StopIteration:
            pass

    while True:
        # find the smallest prime not yet popped; stop if this (hence
        # all) has norm > maxnorm:
        nmin = min(ns)
        if nmin > maxnorm:
            raise StopIteration

        # extract smallest prime and its index:
        i = ns.index(nmin)
        P = Ps[i]

        # pop the next prime off that sub-iterator, detecting if it has finished:
        try:
            Ps[i] = PPs[i].next()
            ns[i] = Ps[i].norm()
        except StopIteration:
            # prevent i'th sub-iterator from being used again
            ns[i] = Infinity
        yield P

########################################################
#
# Sorting prime-power-norm ideals over a number field K.
#
########################################################

# First some utility functions for working with weighted exponent
# vectors:

def exp_vec_wt_iter(w, wts):
    r""" Unsorted iterator through all non-negative integer tuples v of
    length len(wts) and weight w = sum(v[i](wts[i]).
    """
    #print("w=%s, wts=%s" % (w,wts))
    if w==0:
        yield [0 for _ in wts]
    elif len(wts):
        for v0 in range(1+w/wts[-1]):
            w1 = w-wts[-1]*v0
            if w1==0:
                yield [0]* (len(wts)-1) + [v0]
            elif len(wts)>1:
                for v1 in exp_vec_wt_iter(w1,wts[:-1]):
                    yield v1+[v0]

def exp_vec_wt(w, wts):
    r""" Sorted list of all non-negative integer tuples v of length
    len(wts) and weight w = sum(v[i](wts[i]).  Sorting is first by
    unweighted weight sum(v[i]) the reverse lex.
    """
    return sorted(list(exp_vec_wt_iter(w,wts)), key = lambda v: (sum(v),[-c for c in v]))

def ppower_norm_ideals(K,p,f):
    r""" Return a sorted list of ideals of K of norm p^f with p prime
    """
    make_keys(K,p)
    if not hasattr(K,'ppower_dict'):
        K.ppower_dict = {}
    if not (p,f) in K.ppower_dict:
        PP = K.primes_dict[p]
        # These vectors are sorted, first by unweighted weight (sum of
        # values) then lexicographically with the reverse ordering on Z:
        vv = exp_vec_wt(f,[P.residue_class_degree() for P in PP])
        Qs = [prod([P**v for P,v in zip(PP,v)]) for v in vv]
        K.ppower_dict[(p,f)] = Qs
    return K.ppower_dict[(p,f)]

def ppower_norm_ideal_index(Q):
    r""" Return the index (from 1) in the sorted list of ideals with the
    same prime-power norm.
    """
    p = Q.factor()[0][0].smallest_integer()
    K = Q.number_field()
    make_keys(K,p)
    PP = K.primes_dict[p]
    vv = exp_vec_wt(ZZ(Q.norm()).log(p),
                    [P.residue_class_degree() for P in PP])
    v = [Q.valuation(P) for P in PP]
    return 1+vv.index(v)

def ppower_norm_ideal_key(Q):
    r""" Sort key for ideals of prime power norm.
    """
    return (Q.norm(), ppower_norm_ideal_index(Q))

def ppower_norm_ideal_label(Q):
    r""" return the label of an ideal of prime-power norm.
    """
    return "{}.{}".format(Q.norm(),ppower_norm_ideal_index(Q))

def ppower_norm_ideal_from_label(K,lab):
    r""" return the ideal of prime-power norm from its label.
    """
    n, i = [int(c) for c in lab.split(".")]
    p, f = ZZ(n).factor()[0]
    make_keys(K,p)
    PP = K.primes_dict[p]
    ff = [P.residue_class_degree() for P in PP]
    vec = exp_vec_wt(f,ff)[i-1]
    return prod([P**v for P,v in zip(PP,vec)])


########################################################
#
# Sorting integral ideals over a number field K.
#
########################################################

def ideals_of_norm(K,n):
    r""" Return a list of all ideals of norm n (sorted).  Cached.
    """
    if not hasattr(K,'ideal_norm_dict'):
        K.ideal_norm_dict = {}
    if not n in K.ideal_norm_dict:
        if n==1:
            K.ideal_norm_dict[n] = [K.ideal(1)]
        else:
            K.ideal_norm_dict[n] = [prod(Q) for Q in cartesian_product_iterator([ppower_norm_ideals(K,p,e) for p,e in n.factor()])]
    return K.ideal_norm_dict[n]

def ideals_key(I):
    r""" Return a sort key for ideals.
    """
    return [ppower_norm_ideal_key(P**e) for P,e in I.factor()]

def ideal_norm_index(I):
    r""" Return the index of this ideal among all ideals of the same norm.
    """
    for i,J in enumerate(ideals_of_norm(I.number_field(),I.norm())):
        if I==J:
            return i+1
    return 0

def ideal_label(I):
    r""" Return the label of an ideal.
    """
    return "{}.{}".format(I.norm(),ideal_norm_index(I))

def ideal_from_label(K,lab):
    r""" Return the ideal with a given label.
    """
    n, j = [int(c) for c in lab.split(".")]
    return ideals_of_norm(K,ZZ(n))[j-1]

def ideals_iterator(K,minnorm=1,maxnorm=Infinity):
    r""" Return an iterator over all ideals of norm n up to maxnorm (sorted).
    """
    for n in srange(minnorm,maxnorm+1):
        for I in ideals_of_norm(K,n):
            yield I
