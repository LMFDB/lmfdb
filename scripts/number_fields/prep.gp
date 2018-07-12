allocatemem(2^30);
default(realprecision,1000);
default(new_galois_format, 1);
read("generate.gp");

/* timeouts in seconds */
/*shortt = 5; 
longt = 10;
*/
shortt = 40;
longt = 10;

savetime=0; /* in milliseconds */

assoc(entry, lis, bnd=-1) =my(b);b=#lis;if(bnd>-1,b=bnd);for(j=1,b,if(lis[j]==entry,return(j)));return(0);

/* Needs to be adjusted for higher degree polynomials */
galt(pol) = return(polgalois(pol)[3]);
galt(pol) = if(poldegree(pol)<12, return(polgalois(pol)[3]), return(galtord(pol)[1]));

mult(lis) =
{
  my(ans1=[], ans2=[], k);

  for(j=1,length(lis), if((k=assoc(lis[j], ans1)), ans2[k]+=1,
    ans1=concat(ans1,[lis[j]]);
    ans2=concat(ans2,[1])));
  return(vector(length(ans1),h,[ans1[h], ans2[h]]));
}

coeffs(pol) = return(vector(poldegree(pol)+1, h, polcoeff(pol, h-1)));

getsubs(pol)=
{
  my(sbs);
  sbs=nfsubfields(pol);
  sbs = apply(z->[z[1], poldegree(z[1])], sbs);
  sbs = vecsort(sbs, [2]);
  sbs = vector(#sbs-2,h,sbs[h+1]); /* skip Q and the field itself */
  sbs = apply(z->polredabs(z[1]),sbs);
  sbs = apply(coeffs,sbs);
  return(mult(sbs));
}

load(p,n)=return(read(Str("/home/jj/data/localfields-lmfdb/file-src/p"p"d"n"all")));

onealg(pol,p)=
{
  my(fp,degs,loc,lpols);
  if(p>200,return([]));
  fp=lift((factorpadic(pol,p,1000)[,1]~)*Mod(1,p^1000));
  degs=vecsort(apply(poldegree,fp));
  lpols=vector(#fp);
  if(last(degs)>15, return([]));
  for(j=1,#fp,
    loc=iferr(load(p,poldegree(fp[j])),E,0);
    if(loc==0, return([]);lpols[j]=fake(fp[j],p),
      lpols[j]=findinlist(fp[j],loc)[1]);
  );
  return(vector(#lpols,h,Str(lpols[h])));
}


doit(pol)=
{
    my(nf,bnf=0,elapsed=0,nogrh=0,h=-1,clgp=[],reg=0,fu="",extras=0,subs,zk);
    my(localg,rmps);
    nf=nfinit(pol);
    zk=nfbasis(pol);
    a='a;
    zk=subst(zk,x,a);
    zk=apply(z->Str(z), zk);
    rmps=factor(abs(nf.disc))[,1]~;
    gettime();
    iferr(alarm(shortt,bnf=bnfinit(nf,1)),E,1);
    if(bnf,
        alarm(longt, iferr(if(bnfcertify(bnf)==0,1/0,nogrh=1), E,1));
        elapsed = gettime();
        h= bnf.clgp[1];
        clgp=bnf.clgp[2];
        if(elapsed>savetime,
            reg = bnf.reg;
            fu = lift(bnf.fu);
            fu = subst(fu,x,a);
            fu = apply(z->Str(z), fu);
            extras=1;
        );
    );
    localg = apply(z->onealg(pol,z), rmps);
    subs = getsubs(nf);
    return([Vecrev(pol), galt(pol), nf.disc, nf.r1,h,clgp,extras,reg,fu,nogrh,subs,1,zk,rmps,localg]);
    /* reg and units if slow */
    /* grh if certify is too slow */
}

doit1(ll)=
{
    my(pol=ll[1],rmps=Set(ll[2]),nf,bnf=0,elapsed=0,nogrh=0,h=-1,clgp=[],reg=0,fu="",extras=0,subs,zk,ramli);
    ramli=getramli(ll);
    pol=polredabsx(ll);
    my(pd=poldisc(pol), nps);
    a='a;
    nf=nfinit([pol,ramli]);
    if(#nfcertify(nf)>0, error("Did not certify number field"));
    zk=nfbasis([pol,ramli]);
    rmps = vecsort(select(z->valuation(nf.disc,z)>0,ramli));
    zk=subst(zk,x,a);
    zk=apply(z->Str(z), zk);
    gettime();
    iferr(alarm(shortt,bnf=bnfinit(nf,1)),E,1);
    if(bnf,
        alarm(longt, iferr(if(bnfcertify(bnf)==0,1/0,nogrh=1), E,1));
        elapsed = gettime();
        h= bnf.clgp[1];
        clgp=bnf.clgp[2];
        if(elapsed>savetime,
            reg = bnf.reg;
            fu = lift(bnf.fu);
            fu = subst(fu,x,a);
            fu = apply(z->Str(z), fu);
            extras=1;
        );
    );
    localg = apply(z->onealg(pol,z), rmps);
    subs = getsubs(nf);
    return([Vecrev(pol), galt(pol), nf.disc, nf.r1,h,clgp,extras,reg,fu,nogrh,subs,1,zk,rmps, localg]);
    /* reg and units if slow */
    /* grh if certify is too slow */
}

doall(li)=
{
    my(ans=vector(#li),len=length(li));
    for(j=1,#li,
        ans[j]=doit(li[j]);
        print1(".");
        if(j%50==0, print(" ", j, " ", floor(100*j/len), "%"))
    );
    return(ans);
}

doall1(li)=
{
    my(ans=vector(#li));
    for(j=1,#li,
        ans[j]=doit1(li[j]);
        print1(".");
        if(j%50==0, print(" ", j))
    );
    return(ans);
}

dofix(li)=
{
  my(l2);
  l2 =apply(z->[z[2],z[1][2]], li);
  l2= doall1(l2);
  return(vector(#l2,h,[Vecrev(li[h][1][1]),l2[h]]));
}

