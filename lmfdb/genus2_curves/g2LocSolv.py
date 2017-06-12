# -*- coding: utf-8 -*-

from sage.all import ZZ, sqrt, Set, valuation, kronecker_symbol, GF, floor, true, false, Mod, lift, oo

def QpName(p):
 if p==oo:
  return "$\\R$"
 return "$\\Q_{"+str(p)+"}$"


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


def IsSolvableAt(F,p,c): # Tests whether the curve y²=c*F(x) has a point over Qp
 # Assumes deg F even, F in ZZ[x], and content(F)=1
 # Are the points at infty defined over Qp ?
 if IsSquareInQp(c*F.leading_coefficient(),p):
  return true
 Fp=GF(p)
 if p>2 and Fp(F.leading_coefficient()): # Tests to accelerate case of large p
  # Write F(x)=c*lc(F)*R(x)²*S(x) mod p, R as big as possible
  R=F.parent(1)
  S=F.parent(1)
  for X in (F.base_extend(Fp)/Fp(F.leading_coefficient())).squarefree_decomposition():
   [G,v]=X # Term of the form G(x)^v in the factorisation of F(x) mod p
   S*=G**(v%2)
   R*=G**(v//2)
  r=R.degree()
  s=S.degree()
  if s==0: # F(x)=C*R(x)² mod p, C=c*lc(F) constant
   if IsSquareInQp(c*F.leading_coefficient(),p):
    if p>r:# Then there is x s.t. R(x) nonzero and C is a square
     return true
    # TODO It would save time to do something clever when p is large and leading coeff not a square
  else: # Now S(x) is not constant
   g=S.degree()//2-1 # genus of the curve y²=C*S(x)
   B=floor(p-1-2*g*sqrt(p)) # lower bound on number of points on y²=C*S(x) not at infty
   if B>r+s: # Then there is a point on y²=C*S(x) not at infty and with R(x) and S(x) nonzero
    return true
 #Now p is small, we can run a naive search
 q=p
 if p==2:
  q=8
 for x in range(q):
  if IsSquareInQp(c*F(x),p):
   return true
 #So now, if we have a Qp-point, its y-coordinate must be 0 mod p
 Z=F.roots(Fp) # So the x-coordinate must reduce to one of these
 t=F.variables()[0]
 for z in Z:
  F1=F(lift(z[0])+p*t) # Change variable to center around candidate x-coordinate (i.e. we are blowing up without saying it) 
  c1=F1.content()
  F1//=c1 # Sotre and clear new content
  if IsSolvableAt(F1,p,(c*c1).squarefree_part()): # Throw away squares from new content
   return true
 return false
 
def NonLocSolvPlaces(f,h=0): # List of primes at which the curve y²+h(x)*y=f(x) is not solvable
 # Assumes f and h have integer coefficients
 S=[] # List of primes at which not solvable
 # Get eqn of the form y²=F(x)
 F=f
 if h:
  F=4*f+h**2
 # Do we have a rational point an infty ?
 if F.degree()%2 or F.leading_coefficient().is_square():
  return []
 # Points over RR ?
 if F.leading_coefficient()<0 and len(F.real_roots())==0:
  S.append(oo)
 D=ZZ(F.disc()) # Primes of bad red for our model
 P=Set(D.prime_divisors()).union(Set([2,3,5,7,11,13])) # Add primes at which Weil bounds do not guarantee a mod p point
 c=F.content()
 F//=c # Store content and clear it
 for p in P:
  if not IsSolvableAt(F,p,c.squarefree_part()): # Throw away squares from content
   S.append(p)
 return S
