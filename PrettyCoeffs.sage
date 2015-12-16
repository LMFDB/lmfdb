import pymongo
import lmfdb
from lmfdb.modular_forms.elliptic_modular_forms import *
from lmfdb.number_fields.number_field import make_disc_key


C=lmfdb.base.getDBConnection()
NF=C['numberfields']['fields']

M=WebModFormSpace(106,4,1)
f=M.hecke_orbits['b']


def Modf_changevar(f,NF,Bfacto=10^6):
 # Gather information of the coefficient field and try to find it in DB
 plist=[p for p in range(200) if is_prime(p)]
 query={}
 P=f.absolute_polynomial
 print P
 ZZx=P.parent()
 QQx=ZZx.base_extend(QQ)
 # Lazy order
 pKP=gp.nfinit([P,Bfacto])
 # Sign
 [r1,r2]=pKP[2]
 query['signature']=str(r1)+','+str(r2)
 DpKP=pKP[3]
 # Is the lazy order maximal ?
 if len(gp.nfcertify(pKP)):
  # The lazy order is not maximal
  print "Exact disc unknown"
  ur=[]
  ram=[]
  # Primes<200 known to be unramified
  for p in plist:
   if Mod(DpKP,p):
    ur.append(str(p))
  # Lazy factorisation of the disc of the lazy order
  faD=gp.factor(DpKP,Bfacto)
  faD=str(faD).replace('[','').replace(']','').replace('Mat(','').replace(')','').split(';')
  #Primes known to be ramified
  for s in faD:
   p=s.split(',')[0].replace(' ','')
   if ZZ(p)<Bfacto:
    ram.append(p)
  query['$nor'] = [{'ramps': x} for x in ur]
  query['ramps'] = {'$all': ram}
 else:
  # The lazy order is maximal :)
  print "Exact disc known"
  # Query on disc
  s,D=make_disc_key(ZZ(DpKP))
  query['disc_sign']=s
  query['disc_abs_key']=D

 LK=NF.find(query)

 K0=0
 Klabel=''
 for K in LK:
  # Found a candidate in the nf DB, here is its defining polynomial
  Q=ZZx([ZZ(a) for a in K['coeffs'].split(',')])
  print Q
  # Compute max order in gp
  maxram=max([ZZ(a) for a in K['ramps']])
  pkQ=gp.nfinit([Q,maxram+1])
  # Check for isomorphism
  iso=gp.nfisisom(pkQ,P)
  if iso:
   iso=QQx(str(iso[1]))
   K0=K
   Klabel=K0['label']
   print "Found "+Klabel
   break

 if K0==0:
  # Field not found, so we reduce the initial polynomial as we can
  [Q,iso]=gp.polredbest(P,1)
  Q=ZZx(str(Q))
  iso=QQx(str(gp.lift(iso)))

 # Apply isomorphism
 KQ.<a>=NumberField(Q)
 iso=KQ(iso)
 v=f.eigenvalues.v
 newv=[l.lift()(iso) for l in v]
 #newcoeffs=[0 for i in range(qprec)]
 #for i in range(1,qprec):
  #newcoeffs[i]=f.coefficient(i).lift()(iso)
 return [newv,Klabel]
