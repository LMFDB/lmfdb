# -*- coding: utf-8 -*-
from sage.misc.preparser import preparse
from sage.interfaces.magma import magma
from sage.all import PolynomialRing, Rationals
from lmfdb.db_backend import db
#
# This script is intended to run Magma on all Hilbert newforms (or all
# those over one base field), compute a string representing the
# q-expansion, and store it in the form.  As of August 2017 only one
# newforms had this field, so apart from testing this has not been
# run.
#
# If this is used in future we will need to decide which collection to
# store the q-expansions in.
#
# This script is intended for offline use and should be moved to the
# scripts directory.

P = PolynomialRing(Rationals(), 3, ['w', 'e', 'x'])
w, e, x = P.gens()


def qexpansion(field_label=None):
    if field_label is None:
        query = {}
    else:
        query = {"field_label": field_label}
    S = db.hmf_forms.search(query, sort=["label"])

    field_label = None

    v = S.next()
    while True:
        # NN_label = v["level_label"] # never used
        v_label = v["label"]

        print v_label

        if v.get('q_expansion') is not None:
            v = S.next()
            continue

        if field_label is None or not field_label != v["field_label"]:
            field_label = v["field_label"]
            print "...new field " + field_label

            coeffs = db.nf_fields.lookup(field_label, projection="coefficients")
            F_hmf = db.hmf_fields.lookup(field_label, projection=["ideals", "primes", "narrow_class_number"])

            magma.eval('P<x> := PolynomialRing(Rationals());')
            magma.eval('F<w> := NumberField(Polynomial(' + str(coeffs) + '));')
            magma.eval('ZF := Integers(F);')
            magma.eval('ideals_str := [' + ','.join([st for st in F_hmf["ideals"]]) + '];')
            magma.eval('ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];')

            magma.eval('primes_str := [' + ','.join([st for st in F_hmf["primes"]]) + '];')
            magma.eval('primes := [ideal<ZF | {F!x : x in I}> : I in primes_str];')

            if F_hmf.get("narrow_class_number") is None:
                F_hmf['narrow_class_number'] = eval(preparse(magma.eval('NarrowClassNumber(F);')))

        if v["hecke_polynomial"] != 'x':
            magma.eval('fpol := ' + v["hecke_polynomial"] + ';')
            magma.eval('K<e> := NumberField(fpol);')
        else:
            magma.eval('fpol := x;')
            magma.eval('K := Rationals(); e := 1;')

        magma.eval('hecke_eigenvalues := [' + ','.join([st for st in v["hecke_eigenvalues"]]) + '];')

        magma.eval('mCl := ClassGroupPrimeRepresentatives(ZF, 1*ZF, RealPlaces(F)); '
                   'Cl := [mCl(x) : x in Domain(mCl)]; '
                   'dd := Different(ZF); '
                   'ddinv := dd^(-1); '
                   'Nd := Norm(dd); '
                   'q_expansions := [* *]; '
                   'for pp in Cl do '
                   '  L0 := MinkowskiLattice(ZF!!(Nd*pp*ddinv)); '
                   '  L := LatticeWithGram( GramMatrix(L0)/Nd^2 ); '
                   '  ppdd_basis := Basis(pp*ddinv); '
                   ' '
                   '  det := Norm(pp)/Nd; '
                   '  s := 1; '
                   '  V := []; '
                   '  while #V lt 10 do '
                   '    S := ShortVectors(L, s*det); '
                   '    S := [&+[Round(Eltseq(v[1])[i])*ppdd_basis[i] : i in [1..#ppdd_basis]] : v in S]; '
                   '    S := [x : x in S | IsTotallyPositive(x)]; '
                   '    V := S; '
                   '    s +:= 1; '
                   '  end while; '
                   ' '
                   '  Append(~q_expansions, [* [F!x : x in V[1..10]], [Index(ideals, x*dd) : x in V] *]); '
                   'end for;')
        q_expansions_str = magma.eval('hecke_eigenvalues_forideals := [1]; '
                                      'm := Max(&cat[t[2] : t in q_expansions]); '
                                      'for i := 2 to m do '
                                      '  nn := ideals[i]; '
                                      '  nnfact := Factorization(nn); '
                                      '  if #nnfact eq 1 then '
                                      '    pp := nnfact[1][1]; '
                                      '    e := nnfact[1][2]; '
                                      '    if e eq 1 then '
                                      '      ann := hecke_eigenvalues[Index(primes,pp)]; '
                                      '    else '
                                      '      ann := hecke_eigenvalues_forideals[Index(ideals,pp)]* '
                                      '             hecke_eigenvalues_forideals[Index(ideals,pp^(e-1))] - '
                                      '               Norm(pp)*hecke_eigenvalues_forideals[Index(ideals,pp^(e-2))]; '
                                      '    end if; '
                                      '  else '
                                      '    ann := &*[ hecke_eigenvalues_forideals[Index(ideals,qq[1]^qq[2])] : qq in nnfact ]; '
                                      '  end if; '
                                      '  Append(~hecke_eigenvalues_forideals, ann); '
                                      'end for; '
                                      ' '
                                      'print [* [* [* q[1][i], hecke_eigenvalues_forideals[q[2][i]] *] : i in [1..#q[1]] *] : q in q_expansions *];')

        q_expansions = eval(preparse(q_expansions_str.replace('[*', '[').replace('*]', ']')))
        q_expansions = [[[str(c) for c in q[0]], [str(c) for c in q[1]]] for q in q_expansions]

        v["q_expansions"] = q_expansions

        # UPDATES DON'T WORK
        #db.hmf_forms.save(v)

        v = S.next()
