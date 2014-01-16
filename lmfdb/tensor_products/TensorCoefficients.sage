
def tensor_good_local_factors(f1,f2,d):
 R.<t>=PowerSeriesRing(f1.parent().base_ring().fraction_field())
 if not f1.parent().is_exact():	# ideally f1,f2 should already be in PSR
  assert f1.prec()>=d
 if not f2.parent().is_exact(): # but the user might give them as polys...
  assert f2.prec()>=d
 f1=R(f1)
 f2=R(f2)
 if f1==1 or f2==1:
  return 1+O(t**(d+1))
 l1=f1.log().derivative()
 p1=l1.prec()
 c1=l1.list()
 while len(c1)<p1:
  c1.append(0)
 l2=f2.log().derivative()
 p2=l2.prec()
 c2=l2.list()
 while len(c2)<p2:
  c2.append(0)
 C=[0]*len(c1)
 for i in range(0,len(c1)):
  C[i]=c1[i]*c2[i]
 E=(-(R(C).integral()+O(t**(d+1)))).exp() # coerce to R
 return E

def list_to_euler_factor(L,d):
 R.<t>=PowerSeriesRing(L[0].parent().fraction_field())
 return 1/R([1]+L)+O(t**(d+1))

def get_euler_factor(L,p): # utility function to get an Euler factor, unused
 S=len(L)
 f=floor(log(S*1.0)/log(p*1.0))
 E=[]
 q=1
 for i in range(0,f):
  q=q*p
  E.append(L[q-1])
 return list_to_euler_factor(E,f)

def euler_factor_to_list(L,f):
 R.<t>=PowerSeriesRing(L[0].parent().fraction_field(),default_prec=f+1)
 return ((1/R(L.truncate().coeffs())).truncate().coeffs())[1:]

def all_an_from_prime_powers(L): # values at prime powers to all n, slow?
 S=len(L)
 for p in prime_range(S+1):
  q=1
  for k in range(1,1+floor(log(S*1.0)/log(p*1.0))):
   q=q*p
   for m in range(2,1+(S//q)):
    if (m%p)!=0:       
     L[m*q-1]=L[m*q-1]*L[q-1]

def tensor_get_an_deg1(L,D,BadPrimeInfo): # BPI must be just [p,f] here
 s1=len(L)
 s2=len(D)
 if s1<s2:
  S=s1
 if s2<=s1:
  S=s2
 BadPrimes=[]
 for bpi in BadPrimeInfo:
  BadPrimes.append(bpi[0])
 P=prime_range(S+1)
 Z=S*[1]
 for p in P:
  f=floor(log(S*1.0)/log(p*1.0))
  q=1
  u=1
  e=D[p-1]
  if not p in BadPrimes:
   for i in range(0,f):
    q=q*p
    u=u*e
    Z[q-1]=u*L[q-1]
  else:
   i=BadPrimes.index(p)
   e=BadPrimeInfo[i][1] # This needs some help on precision?
   ld=e.degree()
   F=e.list()[0].parent().fraction_field()
   R.<z>=PowerSeriesRing(F,default_prec=ld+1)
   e=R(e)
   A=euler_factor_to_list(e,f)
   for i in range(0,f):
    q=q*p
    Z[q-1]=A[i]
 all_an_from_prime_powers(Z)
 return Z
 
def tensor_get_an_no_deg1(L1,L2,d1,d2,BadPrimeInfo):
 if d1==1 or d2==1:
  raise ValueError('d1 and d2 should not be 1, use direct method for those')
 s1=len(L1)
 s2=len(L2)
 if s1<s2:
  S=s1
 if s2<=s1:
  S=s2
 BadPrimes=[]
 for bpi in BadPrimeInfo:
  BadPrimes.append(bpi[0])
 P=prime_range(S+1)
 Z=S*[1]
 for p in P:
  f=floor(log(S*1.0)/log(p*1.0))
  q=1
  E1=[]
  E2=[]
  if not p in BadPrimes:
   for i in range(0,f):
    q=q*p
    E1.append(L1[q-1])
    E2.append(L2[q-1])
   e1=list_to_euler_factor(E1,d1*d2+1)
   e2=list_to_euler_factor(E2,d1*d2+1)
   ld1=d1
   ld2=d2
  else: # can either convolve, or have one input be the answer and other 1-t
   i=BadPrimes.index(p)
   e1=BadPrimeInfo[i][1] # This needs some help on precision?
   e2=BadPrimeInfo[i][2]
   ld1=e1.degree()
   ld2=e2.degree()
   F=e1.list()[0].parent().fraction_field()
   R.<z>=PowerSeriesRing(F,default_prec=ld1*ld2+1)
   e1=R(e1)
   e2=R(e2)
  l1=e1.log().derivative()
  l2=e2.log().derivative()
  p1=l1.prec()
  c1=l1.list()
  while len(c1)<p1:
   c1.append(0)
  p2=l2.prec()
  c2=l2.list()
  while len(c2)<p2:
   c2.append(0)
  C=[0]*len(c1)
  for i in range(0,len(c1)): # guess c1 and c2 are same size?
   C[i]=c1[i]*c2[i]
  t=(e1-e1+1).integral() # hack, very
  E=(-(e1.parent(C).integral()+O(t**(ld1*ld2+1)))).exp() # coerce to e1.parent
  A=euler_factor_to_list(E,f)
  while len(A)<f:
   A.append(0)
  q=1
  for i in range(0,f):
   q=q*p
   Z[q-1]=A[i]
 all_an_from_prime_powers(Z)
 return Z

def tensor_get_an(L1,L2,d1,d2,BadPrimeInfo):
 if d1==1:
  return tensor_get_an_deg1(L2,L1,[[bpi[0],bpi[2]] for bpi in BadPrimeInfo])
 if d2==1:
  return tensor_get_an_deg1(L1,L2,[[bpi[0],bpi[1]] for bpi in BadPrimeInfo])
 return tensor_get_an_no_deg1(L1,L2,d1,d2,BadPrimeInfo)

########################################################################

def test_tensprod_121_chi():
 C121=[1,2,-1,2,1,-2,2,0,-2,2,0,-2,-4,4,-1,-4,2,-4,0,2,-2,0,\
 -1,0,-4,-8,5,4,0,-2,7,-8,0,4,2,-4,3,0,4,0,8,-4,6,0,-2,-2,\
 8,4,-3,-8,-2,-8,-6,10,0,0,0,0,5,-2,-12,14,-4,-8,-4,0,-7,4,\
 1,4,-3,0,-4,6,4,0,0,8,10,-4,1,16,6,-4,2,12,0,0,15,-4,-8,\
 -2,-7,16,0,8,-7,-6,0,-8,-2,-4,-16,0,-2,-12,-18,10,-10,0,-3,\
 -8,9,0,-1,0,8,10,4,0,0,-24,-8,14,-9,-8,-8,0,-6,-8,18,0,0,\
 -14,5,0,-7,2,-10,4,-8,-6,0,8,0,-8,3,6,10,8,-2,0,-4,0,7,8,\
 -7,20,6,-8,-2,2,4,16,0,12,12,0,3,4,0,12,6,0,-8,0,-5,30,\
 -15,-4,7,-16,12,0,3,-14,0,16,10,0,17,8,-4,-14,4,-6,2,0,0,0]
 chi=[1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,\
 1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,\
 -1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,\
 1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,\
 1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,\
 1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,\
 -1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,\
 -1,-1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1,1,1,1,-1,-1,\
 -1,1,-1,0,1,-1,1,1,1,-1,-1,-1,1,-1,0,1,-1]
 ANS=[1,-2,-1,2,1,2,-2,0,-2,-2,1,-2,4,4,-1,-4,-2,4,0,2,2,-2,\
 -1,0,-4,-8,5,-4,0,2,7,8,-1,4,-2,-4,3,0,-4,0,-8,-4,-6,2,-2,\
 2,8,4,-3,8,2,8,-6,-10,1,0,0,0,5,-2,12,-14,4,-8,4,2,-7,-4,\
 1,4,-3,0,4,-6,4,0,-2,8,-10,-4,1,16,-6,4,-2,12,0,0,15,4,-8,\
 -2,-7,-16,0,-8,-7,6,-2,-8,2,-4,-16,0,2,12,18,10,10,-2,-3,8,\
 9,0,-1,0,-8,-10,4,0,1,-24,8,14,-9,-8,8,0,6,-8,-18,-2,0,14,\
 5,0,-7,-2,10,-4,-8,6,4,8,0,-8,3,6,-10,-8,2,0,4,4,7,-8,-7,\
 20,6,8,2,-2,4,-16,-1,12,-12,0,3,4,0,-12,-6,0,8,-4,-5,-30,\
 -15,-4,7,16,-12,0,3,14,-2,16,-10,0,17,8,4,14,-4,-6,-2,4,0,0]
 R.<t>=PowerSeriesRing(ZZ)
 assert ANS==tensor_get_an_deg1(C121,chi,[[11,1-t]])
 assert ANS==tensor_get_an(C121,chi,2,1,[[11,1-t,1]])
 assert get_euler_factor(ANS,2)==(1+2*t+2*t^2+O(t^8))
 assert get_euler_factor(ANS,3)==(1+t+3*t^2+O(t^5))
 assert get_euler_factor(ANS,5)==(1-t+5*t^2+O(t^4))

def test_tensprod_11a_17a():
 C11=[1,-2,-1,2,1,2,-2,0,-2,-2,1,-2,4,4,-1,-4,-2,4,0,2,2,-2,\
 -1,0,-4,-8,5,-4,0,2,7,8,-1,4,-2,-4,3,0,-4,0,-8,-4,-6,2,-2,\
 2,8,4,-3,8,2,8,-6,-10,1,0,0,0,5,-2,12,-14,4,-8,4,2,-7,-4,\
 1,4,-3,0,4,-6,4,0,-2,8,-10,-4,1,16,-6,4,-2,12,0,0,15,4,-8,\
 -2,-7,-16,0,-8,-7,6,-2,-8,2,-4,-16,0,2,12,18,10,10,-2,-3,8,\
 9,0,-1,0,-8,-10,4,0,1,-24,8,14,-9,-8,8,0,6,-8,-18,-2,0,14,\
 5,0,-7,-2,10,-4,-8,6,4,8,0,-8,3,6,-10,-8,2,0,4,4,7,-8,-7,\
 20,6,8,2,-2,4,-16,-1,12,-12,0,3,4,0,-12,-6,0,8,-4,-5,-30,\
 -15,-4,7,16,-12,0,3,14,-2,16,-10,0,17,8,4,14,-4,-6,-2,4,0,0]
 C17=[1,-1,0,-1,-2,0,4,3,-3,2,0,0,-2,-4,0,-1,1,3,-4,2,0,0,4,\
 0,-1,2,0,-4,6,0,4,-5,0,-1,-8,3,-2,4,0,-6,-6,0,4,0,6,-4,0,\
 0,9,1,0,2,6,0,0,12,0,-6,-12,0,-10,-4,-12,7,4,0,4,-1,0,8,\
 -4,-9,-6,2,0,4,0,0,12,2,9,6,-4,0,-2,-4,0,0,10,-6,-8,-4,0,\
 0,8,0,2,-9,0,1,-10,0,8,-6,0,-6,8,0,6,0,0,-4,-14,0,-8,-6,\
 6,12,4,0,-11,10,0,-4,12,12,8,3,0,-4,16,0,-16,-4,0,3,-6,0,\
 -8,8,0,4,0,3,-12,6,0,2,-10,0,-16,-12,-3,0,-8,0,-2,-12,0,10,\
 16,-9,24,6,0,4,-4,0,-9,2,12,-4,22,0,-4,0,0,-10,12,-6,-2,8,\
 0,12,4,0,0,0,0,-8,-16,0,2,-2,0,-9,-18,0,-20,-3]
 ANS=[1,2,0,2,-2,0,-8,8,15,-4,0,0,-8,-16,0,12,-2,30,0,-4,0,0,\
 -4,0,29,-16,0,-16,0,0,28,-8,0,-4,16,30,-6,0,0,-16,48,0,-24,\
 0,-30,-8,0,0,22,58,0,-16,-36,0,0,-64,0,0,-60,0,-120,56,-120,\
 -8,16,0,-28,-4,0,32,12,120,-24,-12,0,0,0,0,-120,-24,144,96,\
 24,0,4,-48,0,0,150,-60,64,-8,0,0,0,0,-14,44,0,58,-20,0,-128,\
 -64,0,-72,144,0,60,0,0,-96,-126,0,8,0,-120,-120,16,0,-11,-240,\
 0,56,-158,-240,64,-32,0,32,-288,0,0,-56,0,-16,42,0,-80,32,0,\
 24,0,180,0,-48,0,-12,100,0,-32,0,-30,0,-56,0,14,-240,0,16,32,\
 288,96,96,0,48,48,0,142,8,0,-48,-132,0,-232,0,0,300,-180,-60,\
 -14,128,0,-32,12,0,0,0,0,0,-272,0,8,-28,0,44,36,0,0,232]
 R.<t>=PowerSeriesRing(ZZ)
 B11=[11,1-t,1+11*t**2]
 B17=[17,1+2*t+17*t**2,1-t]
 assert ANS==tensor_get_an_no_deg1(C11,C17,2,2,[B11,B17])

test_tensprod_121_chi() # run test
test_tensprod_11a_17a() # run test
