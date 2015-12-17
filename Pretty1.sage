import pymongo
import lmfdb
from lmfdb.modular_forms.elliptic_modular_forms import *
from lmfdb.number_fields.number_field import make_disc_key


def Modf_changevar(f,NF,Bfacto=10^6):
 ######
 # Usage : f a hecke_orbit, NF=lmfdb.base.getDBConnection()['numberfields']['fields']
 # Returns : [v2,E2,Q,emb,label], where v2 and E2 are v and E expressed on a nice model of the coeff field, Q is the absolute defining polynomial of this model, emb is the embeddding of the generator of the cycltomic subfield (for Gamma1), and label is the lmfdb label of the field (or '' if not in the database)
 ######
 
 ZZx.<x>=ZZ[]
 QQx.<x>=QQ[]
 P=f.absolute_polynomial
 # If f is rational, nothing to do :)
 if P.degree()==1:
  return [f.eigenvalues.v,u'1.1.1.1']
 # Is the coefficient field already identified ?
 Klabel=f.coefficient_field.lmfdb_label
 if Klabel:
  # It is, let us make the isomorphism explicit
  K=NF.find_one({'label':Klabel})
  Q=ZZx([ZZ(a) for a in K['coeffs'].split(',')])
  # Compute max order in gp
  pkQ=gp.nfinit([Q,[ZZ(p) for p in K['ramps']]])
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
   pkQ=gp.nfinit([Q,[ZZ(p) for p in K['ramps']]])
   # Check for isomorphism
   iso=gp.nfisisom(pkQ,P)
   if iso:
    iso=QQx(str(iso[1]))
    Klabel=K['label']
    break

 if Klabel=='':
  # Field not found, so we reduce the initial polynomial as we can
  print "Not found"
  [Q,iso]=gp.polredbest(P,1)
  Q=ZZx(str(Q))
  pkQ=gp.nfinit([Q,Bfacto])
  iso=QQx(str(gp.lift(iso)))

 # Now we have the model we want for the absolute field.
 # We now want the explicit embedding of the cyclotomic field, the relative polynomial for this new field, and the relative version of the isomorphism
 E=f.eigenvalues.E
 v=f.eigenvalues.v
 print Q
 print "iso",iso
 KQ.<a>=NumberField(Q)
 Kcyc=v[0].parent().base_ring()
 if Kcyc.degree()>1:
  polcyc=Kcyc.defining_polynomial()
  relP=v[0].parent().defining_polynomial()
  print relP
  emb=QQx(str(gp.nfisincl(polcyc,pkQ)[1]))(a)
  print "emb",emb
  Krel.<a>=Kcyc.extension(relP)
  osi=gp.lift(gp.modreverse(gp.Mod(iso,Q)))
  osi=QQx(str(osi))
  relQ=osi(a).charpoly()
  print relQ
  R.<a>=Kcyc.extension(relQ)
  relIso=iso(a)
  newv=[l.lift()(relIso) for l in v]
  if E.base_ring() != Kcyc:
   E=E.apply_map(lambda x:x[0])
  return [newv,E,Q,emb,Klabel]

 # Finally, apply isomorphism
 KQ.<a>=NumberField(Q)
 iso=KQ(iso)
 newv=[l.lift()(iso) for l in v]
 return [newv,E,Q,QQx.gen(),Klabel]
