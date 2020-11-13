/* This gp script converts data from the format of the JR local field database
   and puts in a form for the lmfdb import script.

   To run this script, you need copies of all of JR local field database
   data files under file-src.  It needs to look up subfields to check the
   number of automorphisms to correctly compute the multiplicity of a
   subfield (since the fields themselves are classified up to isomorphism.
*/
/*
{
u'_id': ObjectId('4e637c7f0eb55b7f65000000'),
 u'aut': 1,
 u'c': 2,
 u'coeffs': [-2, 0, 0, 1],
 u'e': 3,
 u'eisen': u'y^3 - 2',
 u'f': 1,
 u'gal': [3, 2],
 u'galT': 2,
 u'gms': u'2/3',
 u'hw': u'$1$',
 u'inertia': [3, u't', [3, 1], u'<i>C</i><sub>3</sub>'],
 u'label': u'2.3.2.1',
 u'n': 3,
 u'p': 2,
 u'rf': [1, 1],
 u'slopes': u'[]',
 u't': 3,
 u'u': 2,
 u'unram': u't + 1'}
*/
/* Top slope is not done here, it is done in the import script */

\r padic.gp
\r panayi.gp

countroots(f,g,p,nf,pr,early)=return(panayi(f,g,p,1,early));

labels=readvec("label-data");
/* Format [13,2,1,[-13, 0, 1],"13.2.1.1"] (p, deg, Vecrev, label) */

findlabelpol(pol)=for(k=1,#labels,if(labels[k][4]==pol && labels[k][1]==p && labels[k][2]==n, return(k)));return(0);

labelhash=List();
findlabeldat(p,n,c)=for(k=1,#labelhash,if(labelhash[k][1]==p && labelhash[k][2]==n && labelhash[k][3]==c, return(k))); return(0);
{
for(j=1,#labels,
  k=findlabeldat(labels[j][1],labels[j][2],labels[j][3]);
  if(k==0, listput(labelhash,[labels[j][1],labels[j][2],labels[j][3],1]),
    labelhash[k][3] += 1));
}



/* Fix the conversion */
prinhw(p,invec,j,temp) = temp = (1-hilbert(2,myquaddisc(invec,p),p)+ \
  qhw(invec,p)+(1-j)) % 4; ;return(prinhwsimple(temp));

prinhwsimple(temp) = if(temp==0, return("$1$"), \
  if(temp==1, return("$-i$"), \
    if(temp==2, return("$-1$"), \
     return("$i$"))));

myquaddisc(invec,p, temp) = return(if(invec[2]==0, quaddisc(invec[1]), \
  if(p==2, return(quaddisc(5*invec[1]))); \
  temp=1; while(kronecker(prime(temp),p) != -1, temp=temp+1); \
  quaddisc(prime(temp)*invec[1])));

getdisc(poly, p) = return(pdiscclass(poldisc(poly), p));

pdiscclass(disc,p) =
{
  local(tdis, expo);
  tdis = disc;
  expo=valuation(tdis,p); tdis = tdis/p^expo;
  expo = expo % 2;
  if(p==2, tdis = tdis % 8, tdis = tdis % p);
  return(if(p==2, if(tdis==1, [p^expo, 0], if(tdis==5, [p^expo, 1], \
     if(tdis == 7, [- p^expo, 0], [- p^expo, 1]))), \
  [p^expo, if(kronecker(tdis,p)==1,0,1)]));
}



qhw(tdis, p) =
{
  my(myval);
  
  return(if(tdis[1]==1, 0,
    if(p<7,
      if(p==2,
        if(tdis==[2,0], 0,
          if((tdis==[-2,0]) || (tdis==[-1,0]) || (tdis==[-1,1]), 3,
            if(tdis==[2,1], 2, 1))),
        if(p==3, if(tdis==[3,0], 1, 3), 
          if(tdis==[5,1], 2, 0))),
      if((p % 4) == 3,
        if(tdis==[p,1], 3, (4-qhw(getdisc(x^2-p,2),2)) % 4),
        if(tdis[2]==0, 0, myval=1;
          while(kronecker(prime(myval), p) != -1, myval = myval+1);
          (4-(1-kronecker(-1,prime(myval)))/2- 
            qhw(getdisc(x^2-kronecker(-1,prime(myval)) 
          *prime(myval)*p,prime(myval)),prime(myval))) %4)))));
}

findsubaut(pol, p)=
{
  my(d=poldegree(pol));
  for(k=1,#subf[d], if(subf[d][k][1]==pol, return(subf[d][k][2])));
  error("Cannot find subfield ", pol);
}

subconv(p,f,slist)=
{
  if(!slist, return([]));
  slist = concat(apply(z->z[2], slist));
  return(apply(z->[Vecrev(z), countroots(z,f,p)/findsubaut(z,p)], slist));
}

/* Fix the count */
mylabel(l) =
{
  my(cnt,k);
  k=findlabelpol(Vecrev(l[6]));
  if(k, return(labels[k][5]));
  k=findlabeldat(l[1],l[5],l[2]);
  if(k,
    labelhash[k][4] += 1;
    cnt=labelhash[k][4];
    /* print("incrementing ", [l[1],l[5],l[2],cnt]); */
  , /* else */
    listput(labelhash, [l[1],l[5],l[2],1]);
    /* print("new ", [l[1],l[5],l[2],1]); */
    cnt = 1
  );
  return(Str(l[1],".",l[5],".",l[2],".",cnt));
}

doinertia(e9, n)=
{
  if(e9[2]=="e", if(n==1, return(["t", [1,1]]), return(["i", [1,1]])));
  return([e9[2], e9[3]]);
}

inf = concat(readvec("infile"));
p=inf[1][1];
n=inf[1][5];
dis= divisors(n);
dis = vector(max(0,#dis-2),h,dis[h+1]);
subf = if(#dis,vector(dis[#dis]),[]);
{
for(k=1,#dis, 
  temp=read(Str("file-src/p",p,"d",dis[k],"all"));
  subf[dis[k]]= apply(z->[z[6],z[22]], temp)
  );
}

for(j=1,#inf,if(#inf[j]<25, inf[j]=concat(inf[j],vector(25-#inf[j]))))
{
inf=apply(z->print1(".");[z[22], z[2], Vecrev(z[6]), z[3], Str(subst(z[12][2],x,y)), z[4],
  z[7][3], z[7][3][2], Str(z[21]), 
  prinhw(z[1],z[14],z[17]), 
  doinertia(z[9],z[5]), 
  mylabel(z), 
  z[5], z[1], z[14], Str(z[10]), z[11][1], z[11][2], Str(subst(z[12][1],x,t)), 
  subconv(z[1], z[6], z[18]), 
  Vecrev(z[25])]
 ,inf);
}

for(j=1,#inf, write("lfdata", inf[j]))

