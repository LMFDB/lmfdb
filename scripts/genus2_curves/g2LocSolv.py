# -*- coding: utf-8 -*-

from sage.all import ZZ, sqrt, Set, valuation, kronecker_symbol, GF, floor, true, false, Mod, PolynomialRing, next_prime

def IsSquareInQp(x,p):
    if x==0:
        return true
    # Check parity of valuation
    v=valuation(x,p)
    if v%2:
        return false
    # Renormalise to get a unit
    x//=p**v
    # Reduce mod p and conclude
    if p==2:
        return Mod(x,8)==1
    else:
        return kronecker_symbol(x,p)==1


def HasFinitePointAt(F,p,c):
    # Tests whether y²=c*F(x) has a finite Qp-point with x and y both in Zp,
    # assuming that deg F = 6 and F integral
    Fp = GF(p)
    if p > 2 and Fp(F.leading_coefficient()): # Tests to accelerate case of large p
        # Write F(x) = c*lc(F)*R(x)²*S(x) mod p, R as big as possible
        R = F.parent()(1)
        S = F.parent()(1)
        for X in (F.base_extend(Fp)/Fp(F.leading_coefficient())).squarefree_decomposition():
            [G,v] = X # Term of the form G(x)^v in the factorisation of F(x) mod p
            S *= G**(v%2)
            R *= G**(v//2)
        r = R.degree()
        s = S.degree()
        if s == 0: # F(x) = C*R(x)² mod p, C = c*lc(F) constant
            if IsSquareInQp(c*F.leading_coefficient(),p):
                if p>r:# Then there is x s.t. R(x) nonzero and C is a square
                    return true
            #else: # C nonsquare, so if we have a Zp-point it must have R(x) = 0 mod p
            #Z = R.roots()
            ##TODO
        else:
            g = S.degree()//2 - 1 # genus of the curve y²=C*S(x)
            B = floor(p-1-2*g*sqrt(p)) # lower bound on number of points on y²=C*S(x) not at infty
            if B > r+s: # Then there is a point on y²=C*S(x) not at infty and with R(x) and S(x) nonzero
                return true
    #Now p is small, we can run a naive search
    q = p
    Z = []
    if p == 2:
        q = 8
    for x in range(q):
        y = F(x)
        # If we have found a root, save it (take care of the case p=2!)
        if (p > 2 or x < 2) and Fp(y) == 0:
            Z.append(x)
        # If we have a mod p point with y nonzero mod p, then it lifts, so we're done
        if IsSquareInQp(c*y, p):
            return true
    #So now, if we have a Qp-point, then its y-coordinate must be 0 mod p
    t = F.variables()[0]
    for z in Z:
        F1 = F(z+p*t)
        c1 = F1.content()
        F1 //= c1
        if HasFinitePointAt(F1,p,(c*c1).squarefree_part()):
            return true
    return false

def IsSolubleAt(F,p):
    # Tests whether y² = F(x) has a Qp-point, assuming F integral of degree 6 and lc(F) squarefree
    lc = F.leading_coefficient()
    if lc % p:
        # The leading coeff. a6 is not 0 mod p
        # Are the points at Infty defined over Qp ?
        if IsSquareInQp(lc,p):
            return true
        # If we have a point (x,y) with v_p(x) = -A, then v_p(f(x)) = v_p(a6*x^6) = -6A so v_p(y) = -3A
        # So we have x = x'/p^A, y = y'/p^3A, with x' and y' p-adic units
        # Renormalise : y'² = a_d x'^6 + a5 p^A x'^5 + a4 p^2A x'^4 + ...
        if p > 2:
            # Then a6 must be a square mod p, hence a square in Qp, contradiction
            # So x and y must be in Zp
            return HasFinitePointAt(F,p,1);
        else:
            # x'6 = y'² = 1 mod 8, so if A >= 3, then a6 = 1 mod 8, contradiction. So A <= 2, renormalise.
            t = F.variables()[0]
            Zx = PolynomialRing(ZZ,'x')
            return HasFinitePointAt(Zx(4**6*F(t/4)),2,1)
    else:
        # p || a6
        # In particular the points at Infty are not defined over Qp
        # Let us try points over Zp first
        if HasFinitePointAt(F,p,1):
            return true
        # Now, if we had a point with v_p(x) = -A, then v_p(a6 x^6) = 1-6A whereas the other terms have v_p >= -5A
        # So if A >= 2, then 1-6A dominates, so v_p(f(x))=1-6A is odd, contradiction.
        # So A=1, and there must be cancellation mod p to prevent v_p(f(x)) = 5
        # --> x = -a5/a6 + O(p^0), and v_p(y) >= -2
        # Just renormalise
        a5 = F[F.degree()-1]
        if a5 % p == 0:
            return false
        t = F.variables()[0]
        Zx = PolynomialRing(ZZ,'x')
        x0 = -a5/lc # v_p(x0) = -1, mustr have x = x0 + O(p^0)
        x0 = ((p*x0)%p)/p # Clear non-p-part of denominator
        return HasFinitePointAt(Zx(p**4*F(x0+t)),p,1)


def InsolublePlaces(f,h=0):
    # List of primes at which the curve y²+h(x)*y=f(x) is not soluble
    # Assumes f and h have integer coefficients
    S = [] # List of primes at which not soluble
    # Get eqn of the form y²=F(x)
    F = f
    if h:
        F = 4*f + h**2
    # Do we have a rational point an Infty ?
    if F.degree()%2 or F.leading_coefficient().is_square():
        return []
    # Treat case of RR
    if F.leading_coefficient() < 0 and F.number_of_real_roots() == 0:
        S.append(0)
    # Remove squares from lc(F)
    d = F.degree()
    lc = F.leading_coefficient()
    t = F.variables()[0]
    a = lc.squarefree_part() # lc/a is a square
    a = lc//a
    Zx = PolynomialRing(ZZ,'x')
    F = Zx(a**(d-1) * F(t/a))
    # Find primes of bad reduction for our model
    D = F.disc()
    P = Set(D.prime_divisors())
    # Add primes at which Weil bounds do not guarantee a mod p point
    g = (d-2)//2
    Weil = []
    p = 2
    while (p+1)**2 <= 4 * g**2 * p:
        Weil.append(p)
        p = next_prime(p)
    P = P.union(Set(Weil))
    # Test for solubility
    for p in P:
        if not IsSolubleAt(F,p):
            S.append(p)
    S.sort()
    return S


## The next function is meant to be used with the "rewrite_collection" script". It adds the 'insoluble_places' entry to its argument.

def Process_One(c):
    Zx = PolynomialRing(ZZ,'x')
    #label = str(c['label'])
    #print "Updating",label
    eqn = c['eqn']
    f,h = eqn.split("],[")
    f = Zx([int(x) for x in f[2:].split(",")])
    if h == "]]":
        h = Zx(0)
    else:
        h = Zx([int(x) for x in h[:-2].split(",")])
    P = InsolublePlaces(f,h)
    P = [int(p) for p in P]
    c['non_solvable_places'] = P
    # Former name, remove it
    if 'insoluble_places' in c:
        c.pop('insoluble_places')
    return c
