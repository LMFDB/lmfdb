def magma_char_code_string(r):
    """
    Given a row r from mf_newforms containing columns 
       level,weight,char_orbit_label,char_values
    returns a string containing magma code to create the character 
    for r in magma using the default generators.
    """
    N = r["level"]
    k = r["weight"]
    o = r["char_orbit_label"]
    cv = r["char_values"]

    s = "function MakeCharacter_%d_%s()\n"%(N,o)
    s += "    N := %d; n := %d; u := %s; v := %s;\n"%(cv[0],cv[1],cv[2],cv[3])
    s += "    assert UnitGenerators(DirichletGroup(N)) eq u;\n"
    s += "    F := CyclotomicField(n);\n"
    s += "    return DirichletCharacterFromValuesOnUnitGenerators(DirichletGroup(N,F),[F|F.1^n:n in v]);\n"
    s += "end function;\n\n"
    return s

def magma_newform_modsym_cutters_code_string(r,include_char=True):
    """
    Given a row r from mf_newforms containing columns 
       label,level,weight,char_orbit_label,char_values,cutters 
    returns a string containing magma code to create the newform 
    Galois orbit as a modular symbols space using Hecke cutters in magma.
    """
    assert k >= 2   # modular symbols only in weight >= 2
    N = r["level"]
    k = r["weight"]
    o = r["char_orbit_label"]

    cutters = "[" + ",".join(["<%d,R!%s"%(c[0],c[1])+">" for c in r["hecke_cutters"]]) + "]"

    if include_char:
        s = magma_char_code_string(r)

    s += "function MakeNewformModSym_%s()\n"%(r["label"].replace(".","_"))
    s += "    R<x> := PolynomialRing(Rationals());\n"
    s += "    chi := MakeCharacter_%d_%s();\n"%(N,o)
    s += "    // SetVerbose(\"ModularSymbols\", true);\n"
    s += "    Snew := NewSubspace(CuspidalSubspace(ModularSymbols(chi,%d,-1)));\n"%(k)
    s += "    Vf := Kernel(%s,Snew);\n"%(cutters)
    s += "end function;\n\n"
    return s

def magma_newform_modfrm_heigs_code_string(r,v,include_char=True):
    """
    Given a row r from mf_newforms containing columns
       label,level,weight,char_orbit_label,char_values
    and v a list whose nth entry is the entry an from the table mf_hecke_nf
    (consisting of a list of integers giving the Hecke eigenvalue 
    as a linear combination of the basis specified in the orbit table)
    so in particular v[0] = 0 and v[1] = 1,
    returns a string containing magma code to create the newform
    as a representative q-expansion (type ModFrm) in magma.
    """
    N = r["level"]
    k = r["weight"]
    o = r["char_orbit_label"]
    fv = r["field_poly"]  
    Rf_num = r["hecke_ring_numerators"]  
    Rf_den = r["hecke_ring_denominators"]  
    n = len(v) # q-expansion precision

    if include_char:
        s = magma_char_code_string(r)
    
    s += "function MakeNewformModFrm_%s()\n"%(r["label"].replace(".","_"))
    s += "    chi := MakeCharacter_%d_%s();\n"%(N,o)
    s += "    // SetVerbose(\"ModularForms\", true);\n"
    s += "    // SetVerbose(\"ModularSymbols\", true);\n"
    s += "    Kf<nu> := NumberField(Polynomial(%s));\n"%(fv)   # Hecke field
    s += "    S := CuspidalSubspace(ModularForms(chi,%d));\n"%(k)   
          # weight 1 does not have NewSpace functionality, and anyway that 
          # would be an extra possibly expensive linear algebra step
    s += "    S := BaseChange(S, Kf);\n";
    s += "    S_basismat := Matrix([AbsEltseq(g) : g in Basis(S,%d)]);\n"%(n)
    s += "    S_basismat := ChangeRing(S_basismat,Kf);\n"
    s += "    Rf_basisnums := ChangeUniverse(%s,Kf);\n"%(Rf_num)   
    s += "    Rf_basisdens := %s;\n"%(Rf_den)
    s += "    Rfbasis := [Rf_basisnums[i]/Rf_basisdens[i] : i in [1..Degree(Kf)]];\n"    # Basis of Hecke ring
    s += "    f_seq := %s;\n"%(v)
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
