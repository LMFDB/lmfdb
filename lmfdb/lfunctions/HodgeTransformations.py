
# A file for passing between
#  * Hodge structures and Gamma Factors (motivic normalisation)
#  * different normalisation (GammaFactors vs SelbergParameters)

# Copied from Magma code largely for GammaFactors and HodgeStructure
# Format of HodgeStructure is <p,q,eps>, where eps is 2 when p!=q (else 0,1)

from sage.rings.integer_ring import ZZ

def hodge_structure(wt,gamma): # gamma is motivic, max is 1
 """
 Input wt an integer
       gamma a list of integers.

 Output : list of lists of integers
 """
 t=1
 H=[]
 while 2*t > 2-wt:
  m=gamma.count(t)
  n=gamma.count(t-1)
  if n < m:
   raise ValueError('Gamma factors are not Hodge')
  for i in range(1,m+1):
   gamma.remove(t)
   gamma.remove(t-1)
   H.append([wt-1+t,1-t,2]) # eps is 2 when p!=q
   H.append([1-t,wt-1+t,2]) # eps is 2 when p!=q
  t = t-1
 if wt%2 == 0:
  wt2 = wt//2
  e=1-wt2
  m=gamma.count(e)
  for i in range(1,m+1):
   gamma.remove(e)
   H.append([wt2,wt2,1])
  e=-wt2
  m=gamma.count(e)
  for i in range(1,m+1):
   gamma.remove(e)
   H.append([wt2,wt2,0])
 if len(gamma) != 0:
  raise ValueError('Gamma factors not Hodge')
 H.sort()
 return H

def gamma_factors(hodge):
 """
 inverse of HodgeStructure
 weight is just the sum, format is <p,q,eps>
 """
 wt=hodge[0][0]+hodge[0][1]
 G=[]
 for h in hodge:
  if h[0] == h[1]:
   G.append(-h[1]+h[2])
  if h[0] > h[1]:
   G.append(-h[1])
   G.append(-h[1]+1)
 G.sort()
 return wt,G # also returns the weight, convention is it comes first

def tensor_hodge(H1,H2):
 """
 Takes two hodge structures and returns
 the hodge structure of the tensor product
 """
 H=[]
 for h1 in H1:
  for h2 in H2:
   e=2
   v1=h1[0]+h2[0]
   v2=h1[1]+h2[1]
   if v1 == v2:
    if h1[0] > h1[1]:
     e=1
    if h1[0] < h1[1]:
     e=0
    if h1[0] == h1[1]:
     e=(h1[2]+h2[2])%2
   H.append([v1,v2,e])
 H.sort()
 return H

def hodge_to_selberg(hodge): # normalised for s->(1-s)
 """
 Takes a Hodge structure, returns a
 weight, mu, nu
 """
 R=[]
 C=[]
 wt=hodge[0][0]+hodge[0][1]
 for h in hodge:
  if h[0] > h[1]:
   C.append(-h[1]+ZZ(wt)/2) # sage rational
  if h[0]==h[1]: # R-pairs could go in C, but LMFDB does not do this!
   R.append(h[2]) # either 0 or 1
 R.sort()
 C.sort() # everything in C must be positive, according to convention
 return wt, R, C # R and C are called mu and nu elsewhere

def selberg_to_hodge(wt,R,C):
 """
 inverse of the above
 """
 S=[]
 for r in R: # weight must be even in any case
  S.append(r-ZZ(wt)/2)
 for c in C:
  S.append(c-ZZ(wt)/2)
  S.append(c-ZZ(wt)/2+1)
 return hodge_structure(wt,S)

def root_number_at_oo(hodge): # Table 5.3 of Deligne, page 17
 """
 takes a Hodge structures and returns
 0,1,2,3 such that
 the root number at oo is I^it
 """
 u=0
 for h in hodge:
  if h[0]<h[1]:
   u=u+(h[1]-h[0]+1)
  if h[0]==h[1]:
   u=u+h[2] # h[2] is simply eps in Deligne's notation
 return u%4

# Some testing code

def test_me():
 assert root_number_at_oo(hodge_structure(2,[0,0,1]))==0 # Sym^2 E
 assert root_number_at_oo([[0,0,1]])==1 # imaginary quad field
 assert root_number_at_oo(hodge_structure(1,[0,1]))==2 # ec
 assert root_number_at_oo(hodge_structure(3,[0,1]))==0 # modform wt 4
 assert hodge_structure(1,[0,1])==[[0,1,2],[1,0,2]]
 assert hodge_structure(2,[0,0,1])==[[0,2,2],[1,1,1],[2,0,2]]
 assert hodge_structure(2,[0,-1,1])==[[0,2,2],[1,1,0],[2,0,2]]
 assert gamma_factors([[0,3,2],[1,2,2],[2,1,2],[3,0,2]])==(3,[-1,0,0,1])
 assert gamma_factors([[0,0,0],[0,0,0],[0,0,1]])==(0,[0,0,1])
 assert gamma_factors([[0,1,2],[1,0,2]])==(1,[0,1])

 assert hodge_to_selberg(hodge_structure(3,[-1,0,0,1]))\
        ==(3,[],[ZZ(1)/2,ZZ(3)/2])
 assert hodge_to_selberg([[0,0,0],[0,0,1],[0,0,1]])==(0,[0,1,1],[])
 assert hodge_to_selberg([[0,0,0],[0,0,0],[0,0,1]])==(0,[0,0,1],[])
 assert selberg_to_hodge(3,[],[ZZ(1)/2,ZZ(3)/2])\
        ==[[0,3,2],[1,2,2],[2,1,2],[3,0,2]]
 assert selberg_to_hodge(1,[],[ZZ(1)/2])==[[0,1,2],[1,0,2]]

 U=[[0,1,2],[1,0,2]]
 assert hodge_to_selberg(tensor_hodge(U,U))==(2,[0,1],[1])
 A=[[0,2,2],[2,0,2],[1,1,1]]
 B=[[0,2,2],[2,0,2],[1,1,0]]
 assert hodge_to_selberg(tensor_hodge(A,B))==(4,[0,1,1],[1,1,2])
 assert tensor_hodge(A,A)==tensor_hodge(B,B)
 assert hodge_to_selberg(tensor_hodge(A,A))==(4,[0,0,1],[1,1,2])
 Y=hodge_structure(0,[0,0,0,0,1,1])
 Z=hodge_structure(0,[0,1,1,1,1,1])
 assert hodge_to_selberg(tensor_hodge(A,Y))==(2,[0,0,1,1,1,1],[1,1,1,1,1,1])
 assert hodge_to_selberg(tensor_hodge(A,Z))==(2,[0,0,0,0,0,1],[1,1,1,1,1,1])
 assert hodge_to_selberg(tensor_hodge(B,Y))==(2,[0,0,0,0,1,1],[1,1,1,1,1,1])
 assert hodge_to_selberg(tensor_hodge(B,Z))==(2,[0,1,1,1,1,1],[1,1,1,1,1,1])

# test_me()
