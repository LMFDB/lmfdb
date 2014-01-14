
# A file for passing between
#  * Hodge structures and Gamma Factors (motivic normalisation)
#  * different normalisation (GammaFactors vs SelbergParameters)

# Copied from Magma code largely for GammaFactors and HodgeStructure
# Format of HodgeStructure is <p,q,eps>, where eps is 2 when p!=q (else 0,1)

def HodgeStructure(wt,gamma): # gamma is motivic, max is 1
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
  e=1-(wt/2)
  m=gamma.count(e)
  for i in range(1,m+1):
   gamma.remove(e)
   H.append([wt/2,wt/2,1])
  e=-wt/2
  m=gamma.count(e)
  for i in range(1,m+1):
   gamma.remove(e)
   H.append([wt/2,wt/2,0])
 if len(gamma) != 0:
  raise ValueError('Gamma factors not Hodge')
 H.sort()
 return H

def GammaFactors(hodge): # weight is just the sum, format is <p,q,eps>
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

def TensorHodge(H1,H2):
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

def HodgeToSelberg(hodge): # normalised for s->(1-s)
 R=[]
 C=[]
 wt=hodge[0][0]+hodge[0][1]
 for h in hodge:
  if h[0] > h[1]:
   C.append(-h[1]+wt/2) # sage rational
 E=[] # also, R-pairs should be put in C
 for h in hodge:
  if h[0] == h[1]:
   E.append(h[2])
 m=E.count(0)
 n=E.count(1)
 if m >= n:
  for i in range(0,n):
   C.append(0)
  for i in range(0,m-n):
   R.append(0)
 if m < n:
  for i in range(0,m):
   C.append(0)
  for i in range(0,n-m):
   R.append(1)
 R.sort()
 C.sort()
 return wt,R,C # R and C are called mu and nu elsewhere

def SelbergToHodge(wt,R,C):
 S=[]
 for r in R: # weight must be even in any case
  S.append(r-wt/2)
 for c in C:
  S.append(c-wt/2)
  S.append(c-wt/2+1)
 return HodgeStructure(wt,S)


# Some testing code

def test_me():
 assert HodgeStructure(1,[0,1])==[[0,1,2],[1,0,2]]
 assert HodgeStructure(2,[0,0,1])==[[0,2,2],[1,1,1],[2,0,2]]
 assert HodgeStructure(2,[0,-1,1])==[[0,2,2],[1,1,0],[2,0,2]]
 assert GammaFactors([[0,3,2],[1,2,2],[2,1,2],[3,0,2]])==(3,[-1,0,0,1])
 assert GammaFactors([[0,0,0],[0,0,0],[0,0,1]])==(0,[0,0,1])
 assert GammaFactors([[0,1,2],[1,0,2]])==(1,[0,1])

 assert HodgeToSelberg(HodgeStructure(3,[-1,0,0,1]))==(3,[],[1/2,3/2])
 assert HodgeToSelberg([[0,0,0],[0,0,1],[0,0,1]])==(0,[1],[0])
 assert HodgeToSelberg([[0,0,0],[0,0,0],[0,0,1]])==(0,[0],[0])
 assert SelbergToHodge(3,[],[1/2,3/2])==[[0,3,2],[1,2,2],[2,1,2],[3,0,2]]
 assert SelbergToHodge(1,[],[1/2])==[[0,1,2],[1,0,2]]
 assert GammaFactors(SelbergToHodge(0,[1],[0]))==(0,[0,1,1])

 U=[[0,1,2],[1,0,2]]
 assert HodgeToSelberg(TensorHodge(U,U))==(2,[],[0,1])
 A=[[0,2,2],[2,0,2],[1,1,1]]
 B=[[0,2,2],[2,0,2],[1,1,0]]
 assert HodgeToSelberg(TensorHodge(A,B))==(4,[1],[0,1,1,2])
 assert TensorHodge(A,A)==TensorHodge(B,B)
 assert HodgeToSelberg(TensorHodge(A,A))==(4,[0],[0,1,1,2])
 Y=HodgeStructure(0,[0,0,0,0,1,1])
 Z=HodgeStructure(0,[0,1,1,1,1,1])
 assert HodgeToSelberg(TensorHodge(A,Y))==(2,[1,1],[0,0,1,1,1,1,1,1])
 assert HodgeToSelberg(TensorHodge(A,Z))==(2,[0,0,0,0],[0,1,1,1,1,1,1])
 assert HodgeToSelberg(TensorHodge(B,Y))==(2,[0,0],[0,0,1,1,1,1,1,1])
 assert HodgeToSelberg(TensorHodge(B,Z))==(2,[1,1,1,1],[0,1,1,1,1,1,1])

test_me()
