# -*- coding: utf-8 -*-
from sage.misc.preparser import preparse
from sage.interfaces.magma import magma
from sage.all import PolynomialRing, Rationals
from lmfdb.base import getDBConnection
C = getDBConnection()

hmf_forms = C.hmfs.forms
hmf_fields = C.hmfs.fields
fields = C.numberfields.fields

P = PolynomialRing(Rationals(), 3, ['w', 'e', 'x'])
w, e, x = P.gens()


def recompute_AL(field_label=None, skip_odd=False):
    if field_label is None:
        S = hmf_forms.find({"AL_eigenvalues_fixed": None})
    else:
        S = hmf_forms.find({"field_label": field_label, "AL_eigenvalues_fixed": None})
    S = S.sort("label")

    field_label = None

    magma.eval('SetVerbose("ModFrmHil", 1);')

    v = S.next()
    while True:
        NN_label = v["level_label"]
        v_label = v["label"]

        print v_label

        if field_label is None or not field_label == v["field_label"]:
            field_label = v["field_label"]
            print "...new field " + field_label

            F = fields.find_one({"label": field_label})
            F_hmf = hmf_fields.find_one({"label": field_label})

            magma.eval('P<x> := PolynomialRing(Rationals());')
            magma.eval('F<w> := NumberField(Polynomial(' + str(F["coefficients"]) + '));')
            magma.eval('ZF := Integers(F);')
            magma.eval('ideals_str := [' + ','.join([st for st in F_hmf["ideals"]]) + '];')
            magma.eval('ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];')

            magma.eval('primes_str := [' + ','.join([st for st in F_hmf["primes"]]) + '];')
            magma.eval('primes := [ideal<ZF | {F!x : x in I}> : I in primes_str];')

            magma.eval('classno := NarrowClassNumber(F);')

        if skip_odd and F["degree"] % 2 == 1 and v["level_norm"] > 300:
            print "...level norm > 300, skipping!"
            try:
                v = S.next()
                continue
            except StopIteration:
                break

        NN_index = NN_label[NN_label.index('.') + 1:]
        magma.eval(
            'NN := [I : I in ideals | Norm(I) eq ' + str(v["level_norm"]) + '][' + str(NN_index) + '];')
        magma.eval('Mfull := HilbertCuspForms(F, NN);')
        magma.eval('M := NewSubspace(Mfull);')
        magma.eval('O := QuaternionOrder(M); B := Algebra(O); DD := Discriminant(B);')

        if v["hecke_polynomial"] != 'x':
            magma.eval('fpol := ' + v["hecke_polynomial"] + ';')
            magma.eval('K<e> := NumberField(fpol);')
        else:
            magma.eval('fpol := x;')
            magma.eval('K := Rationals(); e := 1;')

        magma.eval('hecke_eigenvalues := [' + ','.join([st for st in v["hecke_eigenvalues"]]) + '];')

        print "...Hecke eigenvalues loaded..."

        magma.eval('denom := Lcm([Denominator(a) : a in hecke_eigenvalues]); q := NextPrime(200);')
        magma.eval(
            'while #Roots(fpol, GF(q)) eq 0 or Valuation(denom,q) gt 0 do q := NextPrime(q); end while;')
        magma.eval('if K cmpeq Rationals() then mk := hom<K -> GF(q) | >; else mk := hom<K -> GF(q) | Roots(fpol,GF(q))[1][1]>; end if;')

        magma.eval(
            '_<xQ> := PolynomialRing(Rationals()); rootsofunity := [r[1] : r in Roots(xQ^(2*classno)-1,K)];')

        magma.eval('s := 0; KT := []; '
                   'while KT cmpeq [] or Dimension(KT) gt 1 do '
                   '  s +:= 1; '
                   '  if s gt Min(50,#hecke_eigenvalues) then '
                   '    q := NextPrime(q); while #Roots(fpol, GF(q)) eq 0 or Valuation(denom,q) gt 0 do q := NextPrime(q); end while; '
                   '    if K cmpeq Rationals() then mk := hom<K -> GF(q) | >; else mk := hom<K -> GF(q) | Roots(fpol,GF(q))[1][1]>; end if; '
                   '    s := 1; '
                   '    KT := []; '
                   '  end if; '
                   '  pp := primes[s]; '
                   '  if Valuation(NN, pp) eq 0 then '
                   '    T_pp := HeckeOperator(M, pp); '
                   '    T_pp := Matrix(Nrows(T_pp),Ncols(T_pp),[mk(c) : c in Eltseq(T_pp)]); '
                   '    a_pp := hecke_eigenvalues[s]; '
                   '    if KT cmpeq [] then '
                   '      KT := Kernel(T_pp-mk(a_pp)); '
                   '    else '
                   '      KT := KT meet Kernel(T_pp-mk(a_pp)); '
                   '    end if; '
                   '  end if; '
                   'end while;')
        magma.eval('assert Dimension(KT) eq 1;')

        print "...dimension 1 subspace found..."

        magma.eval('NNfact := [pp : pp in Factorization(NN) | pp[1] in primes];')
        magma.eval('f := Vector(Basis(KT)[1]); '
                   'AL_eigenvalues := []; '
                   'for pp in NNfact do '
                   '  if Valuation(DD,pp[1]) gt 0 then U_pp := -HeckeOperator(M, pp[1]); '
                   '  else U_pp := AtkinLehnerOperator(M, pp[1]); end if; '
                   '  U_pp := Matrix(Nrows(U_pp),Ncols(U_pp),[mk(c) : c in Eltseq(U_pp)]); '
                   '  U_ppf := f*U_pp; found := false; '
                   '  for mu in rootsofunity do '
                   '    if U_ppf eq mk(mu)*f then Append(~AL_eigenvalues, mu); found := true; end if; '
                   '  end for; '
                   '  assert found; '
                   'end for;')

        print "...AL eigenvalues computed!"

        AL_ind = eval(preparse(magma.eval('[Index(primes,pp[1])-1 : pp in NNfact]')))
        AL_eigenvalues_jv = eval(preparse(magma.eval('AL_eigenvalues')))
        AL_eigenvalues = [[F_hmf["primes"][AL_ind[i]], AL_eigenvalues_jv[i]] for i in range(len(AL_ind))]
        pps_exps = eval(preparse(magma.eval('[pp[2] : pp in NNfact]')))

        hecke_eigenvalues = v["hecke_eigenvalues"]
        for j in range(len(AL_ind)):
            s = AL_ind[j]
            try:
                if pps_exps[j] >= 2:
                    hecke_eigenvalues[s] = '0'
                else:
                    hecke_eigenvalues[s] = str(-AL_eigenvalues[j][1])
            except IndexError:
                pass

        AL_eigenvalues = [[a[0], str(a[1])] for a in AL_eigenvalues]

        v["hecke_eigenvalues"] = hecke_eigenvalues
        v["AL_eigenvalues"] = AL_eigenvalues
        v["AL_eigenvalues_fixed"] = 'done'
        hmf_forms.save(v)

        v = S.next()
