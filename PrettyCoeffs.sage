import pymongo
import lmfdb
from lmfdb.modular_forms.elliptic_modular_forms import *
from lmfdb.number_fields.number_field import make_disc_key

Bfacto=10^6

C=lmfdb.base.getDBConnection()
NF=C['numberfields']['fields']

##from lmfdb.WebNumberField import decodedisc

M=WebModFormSpace(106,4,1)
f=M.hecke_orbits['b']

plist=[p for p in range(200) if is_prime(p)]

query={}
P=f.absolute_polynomial
print P
#n=P.degree()
#r1=len(P.real_roots())
#r2=(n-r1)/2
pKP=gp.nfinit([P,Bfacto])
[r1,r2]=pKP[2]
query['signature']=str(r1)+','+str(r2)
DpKP=pKP[3]
if len(gp.nfcertify(pKP)):
 print "Exact disc unknown"
 ur=[]
 ram=[]
 for p in plist:
  if Mod(DpKP,p):
   ur.append(str(p))
 faD=gp.factor(DpKP,Bfacto)
 faD=str(faD).replace('[','').replace(']','').replace('Mat(','').replace(')','').split(';')
 for s in faD:
  p=s.split(',')[0].replace(' ','')
  if ZZ(p)<Bfacto:
   ram.append(p)
 query['$nor'] = [{'ramps': x} for x in ur]
 query['ramps'] = {'$all': ram}
else:
 print "Exact disc known"
 s,D=make_disc_key(ZZ(DpKP))
 query['disc_sign']=s
 query['disc_abs_key']=D

LK=NF.find(query)
#print len(list(LK))

ZZx=P.parent()
QQx=ZZx.base_extend(QQ)

K0=0
Klabel=''
for K in LK:
 Q=ZZx([ZZ(a) for a in K['coeffs'].split(',')])
 print Q
 maxram=max([ZZ(a) for a in K['ramps']])
 pkQ=gp.nfinit([Q,maxram+1])
 iso=gp.nfisisom(pkQ,P)
 if iso:
  iso=QQx(str(iso[1]))
  K0=K
  Klabel=K0['label']
  print "Found "+Klabel
  break

if K0==0:
 # Field not found
 [Q,iso]=gp.polredbest(P,1)
 Q=ZZx(str(Q))
 iso=QQx(str(gp.lift(iso)))

KQ.<a>=NumberField(Q)
iso=KQ(iso)
#pKQ=gp.nfinit([Q,Bfacto])
qprec=f.prec
newcoeffs=[0 for i in range(qprec)]
for i in range(1,qprec):
 newcoeffs[i]=f.coefficient(i).lift()(iso)
 #newcoeffs[i]=gp.nfalgtobasis(pKQ,f.coefficient(i).lift()(iso).lift())
