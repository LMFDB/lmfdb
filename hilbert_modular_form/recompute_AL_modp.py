import os.path, gzip, re, sys, time
import sage.misc.preparser
import subprocess
from pymongo import Connection

hmf_forms = Connection(port=int(37010)).hmfs.forms
hmf_fields = Connection(port=int(37010)).hmfs.fields

fields = Connection(port=int(37010)).numberfields.fields

P = PolynomialRing(Rationals(), 3, ['w','e','x'])
w,e,x = P.gens()

def recompute_AL(field_label = None):
    if field_label == None:
        S = hmf_forms.find({})
    else:
        S = hmf_forms.find({ "field_label" : field_label })
    S = S.sort("label")

    field_label = None

    v = S.next()
    while true:
        NN_label = v["level_label"]
        v_label = v["label"]

        print v_label

        try:
            if v["AL_eigenvalues_fixed"] == 'done':
#            if v["AL_eigenvalues_fixed"] == 'done' or v["AL_eigenvalues_fixed"] == 'working':
#                u_label = v_label
#                while u_label[-1] <> '-':
#                    u_label = u_label[:-1]
#                while v["label"].find(u_label) <> -1:
#                    v = S.next()
#                assert v["label"].find('-a') <> -1
                v = S.next()
                continue
        except KeyError:
            print "...new, computing!" 
            v["AL_eigenvalues_fixed"] = 'working'
            hmf_forms.save(v)

        if field_label == None or not field_label == v["field_label"]:
            field_label = v["field_label"]
            print "...new field " + field_label

            F = fields.find_one({"label" : field_label})
            F_hmf = hmf_fields.find_one({"label" : field_label})

            magma.eval('P<x> := PolynomialRing(Rationals());')
            magma.eval('F<w> := NumberField(Polynomial(' + str(F["coefficients"]) + '));')
            magma.eval('ZF := Integers(F);')
            magma.eval('ideals_str := [' + ','.join([st for st in F_hmf["ideals"]]) + '];')
            magma.eval('ideals := [ideal<ZF | {F!x : x in I}> : I in ideals_str];')

            magma.eval('primes_str := [' + ','.join([st for st in F_hmf["primes"]]) + '];')
            magma.eval('primes := [ideal<ZF | {F!x : x in I}> : I in primes_str];')

        if F["degree"] % 2 == 1 and v["level_norm"] > 300:
            print "...level norm > 300, skipping!"
            try:
                v = S.next()
                continue
            except StopIteration:
                break

        NN_index = NN_label[NN_label.index('.')+1:]        
        magma.eval('NN := [I : I in ideals | Norm(I) eq ' + str(v["level_norm"]) + '][' + str(NN_index) + '];')
        magma.eval('M := HilbertCuspForms(F, NN);')

        if v["hecke_polynomial"] <> 'x':
            magma.eval('fpol := ' + v["hecke_polynomial"] + ';')
            magma.eval('K<e> := NumberField(fpol);')
        else:
            magma.eval('fpol := x;')
            magma.eval('K := Rationals(); e := 1;')

        magma.eval('hecke_eigenvalues := [' + ','.join([st for st in v["hecke_eigenvalues"]]) + '];')

        print "...Hecke eigenvalues loaded..."

        magma.eval('denom := Lcm([Denominator(a) : a in hecke_eigenvalues]);')
        magma.eval('q := NextPrime(200); while #Roots(fpol, GF(q)) eq 0 or Valuation(denom,q) gt 0 do q := NextPrime(q); end while;')
        magma.eval('if K cmpeq Rationals() then mk := hom<K -> GF(q) | >; else mk := hom<K -> GF(q) | Roots(fpol,GF(q))[1][1]>; end if;')

        magma.eval('s := 0; KT := []; '\
                   'while KT cmpeq [] or Dimension(KT) gt 1 do '\
                   '  s +:= 1; '\
                   '  if s gt Min(50,#hecke_eigenvalues) then '\
                   '    q := NextPrime(q); while #Roots(fpol, GF(q)) eq 0 or Valuation(denom,q) gt 0 do q := NextPrime(q); end while; '\
                   '    if K cmpeq Rationals() then mk := hom<K -> GF(q) | >; else mk := hom<K -> GF(q) | Roots(fpol,GF(q))[1][1]>; end if; '\
                   '    s := 1; '\
                   '    KT := []; '\
                   '  end if; '\
                   '  pp := primes[s]; '\
                   '  if Valuation(NN, pp) eq 0 then '\
                   '    T_pp := HeckeOperator(M, pp); '\
                   '    T_pp := Matrix(Nrows(T_pp),Ncols(T_pp),[mk(c) : c in Eltseq(T_pp)]); '\
                   '    a_pp := hecke_eigenvalues[s]; '\
                   '    if KT cmpeq [] then '\
                   '      KT := Kernel(T_pp-mk(a_pp)); '\
                   '    else '\
                   '      KT := KT meet Kernel(T_pp-mk(a_pp)); '\
                   '    end if; '\
                   '  end if; '\
                   'end while;')
        magma.eval('assert Dimension(KT) eq 1;')

        print "...dimension 1 subspace found..."

        magma.eval('NNfact := [pp : pp in Factorization(NN) | pp[1] in primes];')
        magma.eval('f := Vector(Basis(KT)[1]); '\
                   'AL_eigenvalues := []; '\
                   'for pp in NNfact do '\
                   '  U_pp := AtkinLehnerOperator(M, pp[1]); '\
                   '  U_pp := Matrix(Nrows(U_pp),Ncols(U_pp),[mk(c) : c in Eltseq(U_pp)]); '\
                   '  U_ppf := f*U_pp; '\
                   '  assert U_ppf eq f or U_ppf eq -f; '\
                   '  if U_ppf eq f then '\
                   '    Append(~AL_eigenvalues, 1); '\
                   '  else '\
                   '    Append(~AL_eigenvalues, -1); '\
                   '  end if; '\
                   'end for;')

#                   '  T_ppf := f*ChangeRing(HeckeOperator(M, pp[1]),K); '\
#                   '  if pp[2] ge 2 then assert T_ppf eq 0*f; else assert T_ppf eq -U_ppf; end if; '\

        print "...AL eigenvalues computed!"

        AL_ind = eval(preparse(magma.eval('[Index(primes,pp[1])-1 : pp in NNfact]')))
        AL_eigenvalues_jv = eval(preparse(magma.eval('AL_eigenvalues')))
        AL_eigenvalues = [ [F_hmf["primes"][AL_ind[i]], AL_eigenvalues_jv[i] ] for i in range(len(AL_ind))]
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
                
        AL_eigenvalues = [ [a[0], str(a[1])] for a in AL_eigenvalues]
       
        v["hecke_eigenvalues"] = hecke_eigenvalues
        v["AL_eigenvalues"] = AL_eigenvalues
        v["AL_eigenvalues_fixed"] = 'done'
        hmf_forms.save(v)

        v = S.next()
