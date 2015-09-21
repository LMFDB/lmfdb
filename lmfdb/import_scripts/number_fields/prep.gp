allocatemem(2^30);
default(realprecision,1000);
default(new_galois_format, 1);

/* timeouts */
shortt = 2*60; /* in seconds */
longt = 5*60;
/*
shortt = 2;
longt = 5;
*/
savetime=500; /* in milliseconds */

assoc(entry, lis, bnd=-1) =my(b);b=#lis;if(bnd>-1,b=bnd);for(j=1,b,if(lis[j]==entry,return(j)));return(0);

/* Needs to be adjusted for higher degree polynomials */
galt(pol) = return(polgalois(pol)[3]);

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

doit(pol)=
{
    my(nf,bnf=0,elapsed=0,nogrh=0,h=-1,clgp=[],reg=0,fu="",extras=0,subs,zk);
    nf=nfinit(pol);
    zk=nfbasis(pol);
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
    subs = getsubs(pol);
    return([Vecrev(pol), galt(pol), nf.disc, nf.r1,h,clgp,extras,reg,fu,nogrh,subs,1,zk]);
    /* reg and units if slow */
    /* grh if certify is too slow */
}

doall(li)=
{
    my(ans=vector(#li));
    for(j=1,#li,
        ans[j]=doit(li[j]);
        print1(".");
        if(j%50==0, print(" ", j))
    );
    return(ans);
}

