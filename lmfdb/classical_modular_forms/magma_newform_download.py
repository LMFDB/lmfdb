def magma_char_code_string(r):
    """
    Given a row r from mf_newforms containing columns 
       level,weight,char_orbit_label,char_values
    returns a string containing magma code to create the character 
    for r in magma using the default generators.
    """
    N = r.level
    o = r.char_orbit_label
    cv = r.char_values

    s = '// To make the character of type GrpDrchElt, type "MakeCharacter_%d_%s();"\n'%(N,o)
    s += "function MakeCharacter_%d_%s()\n"%(N,o)
    s += "    N := %d; n := %d; u := %s; v := %s;\n"%(cv[0],cv[1],cv[2],cv[3])
    s += "    assert UnitGenerators(DirichletGroup(N)) eq u;\n"
    s += "    F := CyclotomicField(n);\n"
    s += "    chi := DirichletCharacterFromValuesOnUnitGenerators(DirichletGroup(N,F),[F|F.1^n:n in v]);\n"
    s += "    return MinimalBaseRingCharacter(chi);\n"
    s += "end function;\n\n"
    return s

def magma_newform_modsym_cutters_code_string(r,include_char=True):
    """
    Given a row r from mf_newforms containing columns 
       label,level,weight,char_orbit_label,char_values,cutters 
    returns a string containing magma code to create the newform 
    Galois orbit as a modular symbols space using Hecke cutters in magma.
    """
    N = r.level
    k = r.weight
    o = r.char_orbit_label

    assert k >= 2   # modular symbols only in weight >= 2

    cutters = "[" + ",".join(["<%d,R!%s"%(c[0],c[1])+">" for c in r.hecke_cutters]) + "]"

    if include_char:
        s = magma_char_code_string(r)
    else:
        s = ""

    s += '// To make the Hecke irreducible modular symbols subspace (type ModSym)\n'
    s += '// containing the newform, type "MakeNewformModSym_%s();".\n'%(r.label.replace(".","_"))
    s += '// This may take a long time!  To see verbose output, uncomment the SetVerbose line below.\n'
    s += "function MakeNewformModSym_%s()\n"%(r.label.replace(".","_"))
    s += "    R<x> := PolynomialRing(Rationals());\n"
    s += "    chi := MakeCharacter_%d_%s();\n"%(N,o)
    s += "    // SetVerbose(\"ModularSymbols\", true);\n"
    s += "    Snew := NewSubspace(CuspidalSubspace(ModularSymbols(chi,%d,-1)));\n"%(k)
    s += "    Vf := Kernel(%s,Snew);\n"%(cutters)
    s += "    return Vf;\n"
    s += "end function;\n\n"
    return s

def magma_newform_modfrm_heigs_code_string(prec, r, h, include_char=True):
    """
    Given a row r from mf_newforms containing columns
       label,level,weight,char_orbit_label,char_values
    and h a row from mf_hecke_nf containing columns
       hecke_ring_numerators,hecke_ring_denominators,
       hecke_ring_cyclotomic_generator
    and v a list whose nth entry is the entry an from the table mf_hecke_nf
    (consisting of a list of integers giving the Hecke eigenvalue 
    as a linear combination of the basis specified in the orbit table)
    so in particular v[0] = 0 and v[1] = 1,
    returns a string containing magma code to create the newform
    as a representative q-expansion (type ModFrm) in magma.
    """
    N = r.level
    k = r.weight
    o = r.char_orbit_label
    v = h['ap']
    fv = r.field_poly
    Rf_powbasis = h['hecke_ring_power_basis']
    m = h['hecke_ring_cyclotomic_generator']
    if not Rf_powbasis:
        Rf_num = str(h['hecke_ring_numerators']).replace("L","")
        Rf_den = str(h['hecke_ring_denominators']).replace("L","")

    if include_char:
        s = magma_char_code_string(r)
    else:
        s = ""

    s += '// To make the newform (type ModFrm), type "MakeNewformModFrm_%s();".\n' % (r.label.replace(".","_"),)
    s += '// This may take a long time!  To see verbose output, uncomment the SetVerbose lines below.\n'
    s += "function MakeNewformModFrm_%s(:prec:=%d)\n"%(r.label.replace(".","_"), prec)
    s += "    prec := Min(prec, NextPrime(%d) - 1);\n" % h['maxp']
    s += "    chi := MakeCharacter_%d_%s();\n" % (N, o)
    s += "    // SetVerbose(\"ModularForms\", true);\n"
    s += "    // SetVerbose(\"ModularSymbols\", true);\n"
    if m > 0: # sparse generic representation
        s += "    Kf := CyclotomicField(%d);\n" % m;
    else:
        s += "    Kf := NumberField(Polynomial(%s));\n" % (fv,)   # Hecke field
    s += '    if Degree(Kf) gt 1 then AssignNames(~Kf, ["nu"]); end if;\n'
    s += "    S := CuspidalSubspace(ModularForms(chi,%d));\n" % k
          # weight 1 does not have NewSpace functionality, and anyway that
          # would be an extra possibly expensive linear algebra step
    s += "    S := BaseChange(S, Kf);\n"
    s += "    primes := PrimesUpTo(prec);\n"
    s += "    indexes := [ i + 1 : i in [1] cat primes];\n"
    s += "    B := Basis(S, prec + 1);\n"
    s += "    S_basismat := Matrix([AbsEltseq(g)[indexes]: g in B]);\n"
    s += "    S_basismat := ChangeRing(S_basismat,Kf);\n"
    s += "    f_seq_untruncated := %s;\n" % (v,)
    s += "    f_seq := f_seq_untruncated[1..#primes];\n"
    if m > 0:
        s += "    f_vec := Vector([Kf!1] cat [ #ap eq 0 select 0 else &+[ elt[1]*Kf.1^elt[2] : elt in ap]  : ap in f_seq]);\n"
    else:
        if Rf_powbasis:
            s += "    Rfbasis := [Kf.1^i : i in [0..Degree(Kf)-1]];\n"
        else:
            s += "    Rf_basisnums := ChangeUniverse(%s,Kf);\n"%(Rf_num)
            s += "    Rf_basisdens := %s;\n"%(Rf_den)
            s += "    Rfbasis := [Rf_basisnums[i]/Rf_basisdens[i] : i in [1..Degree(Kf)]];\n"    # Basis of Hecke ring
        s += "    f_seq := [[1] cat [0 : i in [2..Degree(Kf)]]] cat f_seq;\n"
        s += "    f_vec := Vector(Rfbasis)*ChangeRing(Transpose(Matrix(f_seq)),Kf);\n"
    s += "    f_lincom := Solution(S_basismat,f_vec);\n"
    s += "    f := &+[f_lincom[i]*Basis(S)[i] : i in [1..#Basis(S)]];\n"
    s += "    return f;\n"
    s += "end function;\n\n"
    return s



"""
For possible later use: functions to cut out a space of modular symbols using a linear combination of T_n's.

function ModularSymbolsDual(M, V)   // copied from modsym.m
   assert V subset DualRepresentation(M); MM := New(ModSym); MM`root := AmbientSpace(M); MM`is_ambient_space := false;
   MM`dual_representation := V; MM`dimension := Dimension(V); MM`sign := M`sign; MM`F := M`F; MM`k := M`k;
   return MM;
end function;

function KernelLinearCombo(I, M)
  //The kernel of I on M, the subspace of M defined as the kernel of sum_i I[i][1]*T_{I[i][2]}.

  cutter := &+[c[2]*DualHeckeOperator(M,c[1]) : c in I];
  W := RowSpace(KernelMatrix(cutter)*BasisMatrix(DualRepresentation(M)));
  N := ModularSymbolsDual(AmbientSpace(M),W);
  return N;
end function;
"""
