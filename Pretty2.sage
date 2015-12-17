import pymongo
import lmfdb
from lmfdb.modular_forms.elliptic_modular_forms import *
from lmfdb.number_fields.number_field import make_disc_key


def Modf_changevar(f,NF,Bfacto=10^6):
 ######
 # Usage : f a hecke_orbit, NF=lmfdb.base.getDBConnection()['numberfields']['fields']
 # Returns : [v2,label], where v2 is v expressed on a nice model of the coeff field, and label is the lmfdb label of the field (or '' if not in the database)
 ######
 
 ZZx.<x>=ZZ[]
 QQx.<x>=QQ[]
 P=f.absolute_polynomial
 # If f is rational, nothing to do :)
 if f.is_rational:
  return [f.eigenvalues.v,u'1.1.1.1']
 # Is the coefficient field already identified ?
 Klabel=f.coefficient_field.lmfdb_label
 if Klabel:
  # It is, let us make the isomorphism explicit
  K=NF.find_one({'label':Klabel})
  Q=ZZx([ZZ(a) for a in K['coeffs'].split(',')])
  # Compute max order in gp
  maxram=max([ZZ(a) for a in K['ramps']])
  pkQ=gp.nfinit([Q,maxram+1])
  iso=QQx(str(gp.nfisisom(pkQ,P)[1]))
 else:
  # It is not, let us see if it exists in the DB
  plist=[p for p in range(200) if is_prime(p)]
  query={}
  # Lazy order
  pKP=gp.nfinit([P,Bfacto])
  # Sign
  [r1,r2]=pKP[2]
  query['signature']=str(r1)+','+str(r2)
  DpKP=pKP[3]
  # Is the lazy order maximal ?
  if len(gp.nfcertify(pKP)):
   # The lazy order is not maximal
   ur=[]
   ram=[]
   # Primes<200 known to be unramified
   for p in plist:
    if Mod(DpKP,p):
     ur.append(str(p))
   # Lazy factorisation of the disc of the lazy order
   faD=gp.factor(DpKP,Bfacto)
   faD=str(faD).replace('[','').replace(']','').replace('Mat(','').replace(')','').split(';')
   # Primes known to be ramified
   for s in faD:
    p=s.split(',')[0].replace(' ','')
    if ZZ(p)<Bfacto:
     ram.append(p)
   query['$nor'] = [{'ramps': x} for x in ur]
   query['ramps'] = {'$all': ram}
  else:
   # The lazy order is maximal :)
   # Query on disc
   s,D=make_disc_key(ZZ(DpKP))
   query['disc_sign']=s
   query['disc_abs_key']=D
  LK=NF.find(query)
  Klabel=''
  for K in LK:
   # Found a candidate in the nf DB, here is its defining polynomial
   Q=ZZx([ZZ(a) for a in K['coeffs'].split(',')])
   # Compute max order in gp
   maxram=max([ZZ(a) for a in K['ramps']])
   pkQ=gp.nfinit([Q,maxram+1])
   # Check for isomorphism
   iso=gp.nfisisom(pkQ,P)
   if iso:
    iso=QQx(str(iso[1]))
    Klabel=K['label']
    break

 if Klabel=='':
  # Field not found, so we reduce the initial polynomial as we can
  [Q,iso]=gp.polredbest(P,1)
  Q=ZZx(str(Q))
  iso=QQx(str(gp.lift(iso)))

 # Finally, apply isomorphism
 KQ.<a>=NumberField(Q)
 iso=KQ(iso)
 v=f.eigenvalues.v
 newv=[l.lift()(iso) for l in v]
 return [newv,Klabel]
