# Some elliptic curve utilities.  These are being moved into Sage
# itself, perhaps for release 6.8, at which point this file will be
# redundant.

from sage.all import prod
from sage.rings.all import RealField, RR
from sage.schemes.elliptic_curves.all import EllipticCurve

# 1. Number field functions:

# Stopgap function waiting for Sage's divides() function to be happy with 0


def divides(I, a):
    return a.is_zero() or I.divides(a)


def CRT_nf(reslist, Ilist, check=True):
    r"""
    Solve Chinese remainder problem over a number field.

    INPUT:

    - ``reslist`` -- a list of residues, i.e. integral number field elements

    - ``Ilist`` -- a list of integral ideas, assumed pairsise coprime

    - ``check`` (boolean, default True) -- if True, result is checked

    OUTPUT:

    An integral element x such that x-reslist[i] is in Ilist[i] for all i.
    """
    n = len(reslist)
    if n == 0:
        # we have no parent field so this is all we can do
        return 0
    if n == 1:
        return reslist[0]
    if n > 2:
        # use induction / recursion
        x = CRT_nf([reslist[0], CRT_nf(reslist[1:], Ilist[1:])],
                   [Ilist[0], prod(Ilist[1:])])
        if check:
            check_CRT_nf(reslist, Ilist, x)
        return x
    # now n=2
    r = Ilist[0].element_1_mod(Ilist[1])
    x = ((1 - r) * reslist[0] + r * reslist[1]).mod(prod(Ilist))
    if check:
        check_CRT_nf(reslist, Ilist, x)
    return x


def check_CRT_nf(reslist, Ilist, x):
    r"""
    Utility for checking CRT solutions.
    """
    assert all([x - xi in Ii for xi, Ii in zip(reslist, Ilist)])

# 2. elliptic curve functions concerning minimal models over number fields:


def minimal_discriminant_ideal(E):
    r"""
    Return the minimal discriminant ideal of this elliptic curve.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    The integral ideal D whose valuation at every prime P is that of the
    local minimal model for E at P.
    """
    dat = E.local_data()
    return prod([d.prime() ** d.discriminant_valuation() for d in dat],
                E.base_field().ideal(1))


def non_minimal_primes(E):
    r"""
    Returns a list of primes at which this elliptic curve is not minimal.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    A list of prime ideals, empty if and only if this is a global minimal model.
    """
    if not E.is_global_integral_model():
        raise ValueError("not an integral model")
    dat = E.local_data()
    D = E.discriminant()
    return [d.prime() for d in dat if D.valuation(d.prime()) > d.discriminant_valuation()]


def is_global_minimal_model(E):
    r"""
    Returns whether this elliptic curve is a global minimal model.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    Boolean, False if E is not integral, else True if E is minimal at
    every prime.
    """
    if not E.is_global_integral_model():
        return False
    return non_minimal_primes(E) == []


def global_minimality_class(E):
    r"""
    Returns the ideal class representing the obstruction to this
    elliptic curve having a global minimal model.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    An ideal class of the base number field, which is trivial if and
    only if E has a global minimal model, and which can be used to
    find global and semi-global minimal models.
    """
    K = E.base_field()
    Cl = K.class_group()
    if K.class_number() == 1:
        return Cl(1)
    D = E.discriminant()
    dat = E.local_data()
    primes = [d.prime() for d in dat]
    vals = [d.discriminant_valuation() for d in dat]
    I = prod([P ** ((D.valuation(P) - v) // 12) for P, v in zip(primes, vals)],
             E.base_field().ideal(1))
    return Cl(I)


def has_global_minimal_model(E):
    r"""
    Returns whether this elliptic curve has a global minimal model.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    Boolean, True iff E has a global minimal model, i.e. an integral
    model which is minimal at every prime.
    """
    return global_minimality_class(E).is_one()

# 3. Elliptic curve functions concerning Kraus's conditions over
# number fields.  Here Kraus's conditions on a pair (c4,c6) are
# satisfied locally at a prime P if c4, c6 are integral at P and
# (c4^3-c6^2)/1728 is integral and nonzero, and there is a Weierstrass
# model integral at P and with invariants c4, c6.  They are satisfied
# globally if satisfied locally at all primes.


def check_c4c6_nonsingular(c4, c6):
    r"""
    Check if c4, c6 are integral with valid associated discriminant.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    OUTPUT:

    Boolean, True if c4, c6 are both integral and c4^3-c6^2 is a
    nonzero multiple of 1728.
    """
    if not (c4.is_integral() and c6.is_integral()):
        return False
    D = (c4 ** 3 - c6 ** 2) / 1728
    return not D.is_zero() and D.is_integral()

# Wrapper function for local Kraus check, outsources the real work to
# other functions for primes dividing 2 or 3:


def check_Kraus_local(c4, c6, P, assume_nonsingular=False):
    r"""
    Check Kraus's condictions locally at a prime P.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``P`` - a prime ideal of the number field

    - ``assume_nonsingular`` (boolean, default False) -- if True,
      check for integrality and nosingularity.

    OUTPUT:

    Boolean, True if there is a Weierstrass model integral at P and
    with invariants c4, c6.
    """
    if not assume_nonsingular:
        if not check_c4c6_nonsingular(c4, c6):
            return False, None
    if P.divides(2):
        return check_Kraus_local_2(c4, c6, P, True)
    if P.divides(3):
        return check_Kraus_local_3(c4, c6, P, True)
    return True, 0


def c4c6_model(c4, c6, assume_nonsingular=False):
    r"""
    Return the elliptic curve [0,0,0,-c4/48,-c6/864] with given c-invariants.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``assume_nonsingular`` (boolean, default False) -- if True,
      check for integrality and nosingularity.

    OUTPUT:

    The elliptic curve with a-invariants [0,0,0,-c4/48,-c6/864], whose
    c-invariants are the given c4, c6.  If the supplied invariants are
    singular, returns None when ``assume_nonsingular`` is False and
    raises an ArithmeticError otherwise.
    """
    if not assume_nonsingular:
        if not check_c4c6_nonsingular(c4, c6):
            return None
    return EllipticCurve([0, 0, 0, -c4 / 48, -c6 / 864])

# Kraus test and check for primes dividing 3:


def red_mod(a, P):
    r"""
    Reduce a mod P assuming only that a is P-integral
    """
    K = P.ring()
    OK = K.ring_of_integers()
    F = OK.residue_field(P)
    return OK(F(a))


def make_integral(a, P, e):
    r"""
    Given a in O_{K,P} return b in O_K with P^e|(a-b)
    """
    for b in (P ** e).residues():
        if (a - b).valuation(P) >= e:
            return b
    raise ArithmeticError("Cannot lift %s to O_K mod (%s)^%s" % (a, P, e))


def test_b2_local(c4, c6, P, b2):
    r"""
    Test if b2 is valid at a prime P dividing 3.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``P`` - a prime ideal of the number field which divides 3

    - ``b2`` -- an element of the number field

    OUTPUT:

    The elliptic curve which is the (b2/12,0,0)-transform of
    [0,0,0,-c4/48,-c6/864] if this is integral at P, else False.
    """
    E = c4c6_model(c4, c6).rst_transform(b2 / 12, 0, 0)
    if not (c4, c6) == E.c_invariants():
        print("test_b2_local: wrong c-invariants at P=%s" % P)
        return False
    if not E.is_local_integral_model(P):
        print("test_b2_local: not integral at %s" % P)
        return False
    return E


def test_b2_global(c4, c6, b2):
    r"""
    Test if b2 is valid at all primes P dividing 3.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``b2`` -- an element of the number field

    OUTPUT:

    The elliptic curve which is the (b2/12,0,0)-transform of
    [0,0,0,-c4/48,-c6/864] if this is integral at all primes P
    dividing 3, else False.
    """
    E = c4c6_model(c4, c6).rst_transform(b2 / 12, 0, 0)
    if not (c4, c6) == E.c_invariants():
        print("test_b2_global: wrong c-invariants")
        return False
    if not all([E.is_local_integral_model(P) for P in c4.parent().primes_above(3)]):
        print("test_b2_global: not integral at all primes dividing 3")
        return False
    return E


def check_Kraus_local_3(c4, c6, P, assume_nonsingular=False):
    r"""
    Test if c4,c6 satisfy Kraus's conditions at a prime P dividing 3.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``P`` - a prime ideal of the number field which divides 3

    - ``assume_nonsingular`` (boolean, default False) -- if True,
      check for integrality and nosingularity.

    OUTPUT:

    Either (False, 0) if Kraus's condictions fail, or (True, b2) if
    they pass, in which case the elliptic curve which is the
    (b2/12,0,0)-transform of [0,0,0,-c4/48,-c6/864] is integral at P.
    """
    if not assume_nonsingular:
        if not check_c4c6_nonsingular(c4, c6):
            return False, 0
    e = P.ramification_index()
    P3 = P ** e
    if c4.valuation(P) == 0:
        b2 = (-c6 * c4.inverse_mod(P3)).mod(P3)
        assert test_b2_local(c4, c6, P, b2)
        return True, b2
    if c6.valuation(P) >= 3 * e:
        b2 = c6.parent().zero()
        assert test_b2_local(c4, c6, P, b2)
        return True, b2
    # check for a solution x to x^3-3*x*c4-26=0 (27), such an x must
    # also satisfy x*c4+c6=0 (3) and x^2=c4 (3) and x^3=-c6 (9), and
    # if x is a solution then so is any x'=x (3).
    P27 = P3 ** 3
    for x in P3.residues():
        if (x * c4 + c6).valuation(P) >= e:
            if (x * (x * x - 3 * c4) - 2 * c6).valuation(P) >= 3 * e:
                assert test_b2_local(c4, c6, P, x)
                return True, x
    return False, 0

# Kraus test and check for primes dividing 2:


def sqrt_mod_4(x, P):
    r"""
    Returns a local square root mod 4, if it exists.

    INPUT:

    - ``x`` -- an integral number field element

    - ``P`` -- a prime ideal of the number field dividing 2

    OUTPUT:

    A local solution to \(r^2\equiv x\mod 4\).  If \(e\) is the
    ramification index, this means that \(r^2-x\) has valuation at
    least \(2e\); it only depends on \(r\mod P^e\).
    """
    K = x.parent()
    e = P.ramification_index()
    P2 = P ** e
    for r in P2.residues():
        if (r * r - x).valuation(P) >= 2 * e:
            return True, r
    return False, 0


def test_a1a3_local(c4, c6, P, a1, a3):
    r"""
    Test if a1,a3 are valid at a prime P dividing 2.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``P`` - a prime ideal of the number field which divides 2

    - ``a1``, ``a3`` -- elements of the number field

    OUTPUT:

    The elliptic curve which is the (a1^2/12,a1/2,a3/2)-transform of
    [0,0,0,-c4/48,-c6/864] if this is integral at P, else False.
    """
    E = c4c6_model(c4, c6).rst_transform(a1 ** 2 / 12, a1 / 2, a3 / 2)
    if not (c4, c6) == E.c_invariants():
        print("test_a1a3_local: wrong c-invariants at P=%s" % P)
        return False
    if not E.is_local_integral_model(P):
        print("test_a1a3_local: not integral at %s" % P)
        return False
    return E


def test_a1a3_global(c4, c6, a1, a3):
    r"""
    Test if a1,a3 are valid at all primes P dividing 2.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``a1``, ``a3`` -- elements of the number field

    OUTPUT:

    The elliptic curve which is the (a1^2/12,a1/2,a3/2)-transform of
    [0,0,0,-c4/48,-c6/864] if this is integral at all primes P
    dividing 2, else False.
    """
    E = c4c6_model(c4, c6).rst_transform(a1 ** 2 / 12, a1 / 2, a3 / 2)
    if not (c4, c6) == E.c_invariants():
        print "wrong c-invariants"
        return False
    if not all([E.is_local_integral_model(P) for P in c4.parent().primes_above(2)]):
        print "not integral at all primes above 2"
        return False
    return E


def test_rst_global(c4, c6, r, s, t):
    r"""
    Test if the (r,s,t)-transform of the standard c4,c6-model is integral.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``r``, ``s``, ``t`` -- elements of the number field

    OUTPUT:

    The elliptic curve which is the (r,s,t)-transform of
    [0,0,0,-c4/48,-c6/864] if this is integral at all primes P, else
    False.
    """
    E = c4c6_model(c4, c6).rst_transform(r, s, t)
    if not (c4, c6) == E.c_invariants():
        print("test_rst_global: wrong c-invariants")
        return False
    if not E.is_global_integral_model():
        print("test_rst_global: not integral at some prime")
        print(E.ainvs())
        return False
    return E


def check_Kraus_local_2(c4, c6, P, assume_nonsingular=False):
    r"""
    Test if c4,c6 satisfy Kraus's conditions at a prime P dividing 2.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``P`` - a prime ideal of the number field which divides 2

    - ``assume_nonsingular`` (boolean, default False) -- if True,
      check for integrality and nosingularity.

    OUTPUT:

    Either (False, 0, 0) if Kraus's condictions fail, or (True, a1,
    a3) if they pass, in which case the elliptic curve which is the
    (a1**2/12,a1/2,a3/2)-transform of [0,0,0,-c4/48,-c6/864] is
    integral at P.
    """
    if not assume_nonsingular:
        if not check_c4c6_nonsingular(c4, c6):
            return False, 0, 0
    e = P.ramification_index()
    P2 = P ** e
    c4val = c4.valuation(P)
    if c4val == 0:
        flag, t = sqrt_mod_4(-c6, P)
        if not flag:
            return False, 0, 0
        # In the next 2 lines we are dividing by units at P,
        # but the results may not be globally integral
        a1 = make_integral(c4 / t, P, e)
        a3 = make_integral((c6 + a1 ** 6) / (4 * a1 ** 3), P, e)
        assert test_a1a3_local(c4, c6, P, a1, a3)
        return True, a1, a3
    if c4val >= 4 * e:
        flag, a3 = sqrt_mod_4(c6 / 8, P)
        if not flag:
            return False, 0, 0
        a1 = 0
        assert test_a1a3_local(c4, c6, P, a1, a3)
        return True, a1, a3
    # general case, val(c4) strictly between 0 and 4e
    for a1 in P2.residues():
        Px = -a1 ** 6 + 3 * a1 ** 2 * c4 + 2 * c6
        if Px.valuation(P) >= 4 * e:
            Px16 = Px / 16
            flag, a3 = sqrt_mod_4(Px16, P)
            if flag and (4 * a1 * a1 * Px - (a1 ** 4 - c4) ** 2).valuation(P) >= 8 * e:
                assert test_a1a3_local(c4, c6, P, a1, a3)
                return True, a1, a3
    return False, 0, 0


def check_Kraus_global(c4, c6, assume_nonsingular=False, debug=False):
    r"""
    Test if c4,c6 satisfy Kraus's conditions at all primes.

    INPUT:

    - ``c4``, ``c6`` -- elements of a number field

    - ``assume_nonsingular`` (boolean, default False) -- if True,
      check for integrality and nosingularity.

    OUTPUT:

    Either False if Kraus's condictions fail, or, if they pass, an
    elliptic curve E which is integral and has c-invarinats c4,c6.
    """
    if not assume_nonsingular:
        if not check_c4c6_nonsingular(c4, c6):
            return False

    # Check all primes dividing 3; for each get the value of b2
    K = c4.parent()
    three = K.ideal(3)
    Plist3 = K.primes_above(3)
    dat = [check_Kraus_local_3(c4, c6, P, True) for P in Plist3]
    if not all([d[0] for d in dat]):
        if debug:
            print("Local Kraus condition for (c4,c6)=(%s,%s) fails at some prime dividing 3" % (c4, c6))
        return False
    if debug:
        print("Local Kraus conditions for (c4,c6)=(%s,%s) pass at all primes dividing 3" % (c4, c6))

    # OK at all these primes; now use CRT to combine the b2 values to
    # get a single residue class for b2 mod 3:
    b2list = [d[1] for d in dat]
    P3list = [P ** three.valuation(P) for P in Plist3]
    b2 = CRT_nf(b2list, P3list).mod(three)

    # test that this b2 value works at all P|3:
    E = test_b2_global(c4, c6, b2)
    if not E:
        raise RuntimeError("Error in check_Kraus_global at some prime dividing 3")
    else:
        if debug:
            print("Using b2=%s gives a model integral at 3:\n%s" % (b2, E.ainvs()))

    # Check all primes dividing 2; for each get the value of a1,a3
    two = K.ideal(2)
    Plist2 = K.primes_above(2)
    dat = [check_Kraus_local_2(c4, c6, P, True) for P in Plist2]
    if not all([d[0] for d in dat]):
        if debug:
            print("Local Kraus condition for (c4,c6)=(%s,%s) fails at some prime dividing 2" % (c4, c6))
        return False
    if debug:
        print("Local Kraus conditions for (c4,c6)=(%s,%s) pass at all primes dividing 2" % (c4, c6))

    # OK at all these primes; now use CRT to combine the a1,a3 values
    # to get residue classes mod 2:
    a1list = [d[1] for d in dat]
    a3list = [d[2] for d in dat]
    P2list = [P ** two.valuation(P) for P in Plist2]
    a1 = CRT_nf(a1list, P2list)
    a3 = CRT_nf(a3list, P2list)
    # These are integral at all primes dividing 2 but not necessarily
    # globally, yet we want to reduce them modulo 2!

    def is_2integral(a):
        return all([a.valuation(P) >= 0 for P in Plist2])

    def red_mod2(a):
        for r in K.ideal(2).residues():
            if is_2integral((a - r) / 2):
                return r
        raise ArithmeticError("%s cannot be reduced mod 2" % a)
    if debug:
        print("Before reduction mod 2, (a1,a3)=(%s,%s)" % (a1, a3))
    # a1 = red_mod2(a1)
    # a3 = red_mod2(a3)
    if debug:
        print("After  reduction mod 2, (a1,a3)=(%s,%s)" % (a1, a3))

    # test that these a1,a3 values work at all P|2:
    E = test_a1a3_global(c4, c6, a1, a3)
    if not E:
        raise RuntimeError("Error in check_Kraus_global at some prime dividing 2")
    else:
        if debug:
            print("Using (a1,a3)=(%s,%s) gives a model integral at 2:\n%s" % (a1, a3, E.ainvs()))

    # Now we put together the 2-adic and 3-adic transforms to get a
    # global (r,s,t)-transform from [0,0,0,-c4/48,-c6/864] to a global
    # integral model.
    #
    # We need the combined transform (r,s,t) to have both the forms
    # (r,s,t) = (a1^2/12,a1/2,a3/2)*(r2,0,0) with 2-integral r2, and
    # (r,s,t) = (b2/12,0,0,0)*(r3,s3,t3) with 3-integral r3,s3,t3.
    #
    # A solution is r2=(b2-a1^2)/3, r3=(b2-a1^2)/4, s3=a1/2,
    # t3=(a1*r2+a3)/2, provided that a1 =0 (mod 3) (to make t3
    # 3-integral).  Since a1 was only determined mod 2 this can be
    # fixed first.

    a1 = CRT_nf([0, a1], [K.ideal(three), K.ideal(two)])
    r = b2 / 3 - a1 ** 2 / 4
    s = a1 / 2
    t = s * (b2 - a1 ** 2) / 3 + a3 / 2
    if debug:
        print("Using (r,s,t)=%s should give a global integral model..." % [r, s, t])

    # Final computation of the curve E:
    E = test_rst_global(c4, c6, r, s, t)
    if not E:
        E = c4c6_model(c4, c6).rst_transform(r, s, t)
        for P in Plist2 + Plist3:
            if not E.is_local_integral_model(P):
                print("Not integral at P=%s" % P)
        raise RuntimeError("Error in check_Kraus_global combining transforms at 2 and 3")

    # Success!
    return E


def scale_by_units(E):
    r""" Return a model of E reduced with respect to scaling by units, then
    w.r.t. q1,q2,q3 mod 2,3,2.  The latter is Sage's
    E._reduce_model().  The former is new (but the function here is
    similar to both one which Nook write for Magma and the
    ReducedModel() function in Magma); it is only implemented for real
    quadratic fields so far.

    INPUT:

    - ``E`` -- an elliptic curve over a number field K, assumed integral

    OUTPUT:

    A model for E, optimally scaled with repect to units when K is
    real quadratic; unchanged otherwise.
    """
    K = E.base_field()
    if not K.signature() == (2, 0):
        return E

    embs = K.embeddings(RealField(1000))  # lower precision works badly!
    u = K.units()[0]
    uv = [e(u).abs().log() for e in embs]

    c4, c6 = E.c_invariants()
    c4s = [e(c4) for e in embs]
    c6s = [e(c6) for e in embs]
    v = [(x4.abs() ** (1 / 4) + x6.abs() ** (1 / 6)).log() for x4, x6 in zip(c4s, c6s)]
    kr = -(v[0] * uv[0] + v[1] * uv[1]) / (uv[0] ** 2 + uv[1] ** 2)
    k1 = kr.floor()
    k2 = kr.ceil()
    nv1 = (v[0] + k1 * uv[0]) ** 2 + (v[1] + k1 * uv[1]) ** 2
    nv2 = (v[0] + k2 * uv[0]) ** 2 + (v[1] + k2 * uv[1]) ** 2
    if nv1 < nv2:
        k = k1
    else:
        k = k2
    return E.scale_curve(u ** k)


def first_prime_in_class(c, norm_bound=1000):
    Cl = c.parent()  # the class group
    K = Cl.number_field()
    for P in K.primes_of_bounded_norm_iter(RR(norm_bound)):
        if Cl(P) == c:
            return P
    raise RuntimeError("No prime of norm less than %s found in class %s" % (norm_bound, c))


def semi_global_minimal_model(E, debug=False):
    r"""
    Return a global minimal model for this elliptic curve if it
    exists, or a model minimal at all but one prime otherwise.

    INPUT:

    - ``E`` -- an elliptic curve over a number field

    OUTPUT:

    An elliptic curve Emin which is either a global minimal model of E
    if one exists (i.e., an integral model which is minimal at every
    prime), or a semin-global minimal model (i.e., an integral model
    which is minimal at every prime except one).
    """
    c = global_minimality_class(E)
    I = c.ideal()
    c4, c6 = E.c_invariants()
    if c.is_one():
        P = E.base_field().ideal(1)
    else:
        if debug:
            print("No global minimal model, obstruction class = %s of order %s" % (c, c.order()))
        P = first_prime_in_class(c)
        if debug:
            print("Using a prime in that class: %s" % P)
        I = I / P
    u = I.gens_reduced()[0]
    rc4 = c4 / u ** 4
    rc6 = c6 / u ** 6
    Emin = check_Kraus_global(rc4, rc6, assume_nonsingular=True, debug=debug)
    if Emin:
        Emin = scale_by_units(Emin)._reduce_model()
        return Emin, P
    else:
        raise RuntimeError("failed to compute global minimal model")
        return E, K.ideal(0)


def test_run(fld):
    for E in read_curves("/home/jec/ecnf-data/RQF/curves.%s" % fld):
        label = E[0] + "-" + E[2] + E[3]
        E = E[4]
        print("%s: %s --> " % (label, E.ainvs()))
        Emin, I = semi_global_minimal_model(E)
        if I.is_one():
            print("          %s (global minimal model)" % (Emin.ainvs(),))
        else:
            print("          %s (minimal model away from %s)" % (Emin.ainvs(), I))
