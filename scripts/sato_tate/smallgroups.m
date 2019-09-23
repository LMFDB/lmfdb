function bsonify(obj)
    case Type(obj):
    when BoolElt:
        return obj select "True" else "False";
    when RngIntElt:
        if obj le -2^31 or obj ge 2^31 then
            printf "bson_string: integer %o is too large to fit into an int, you should use a string", obj;
            assert obj gt -2^31 and obj lt 2^31;
        end if;
        return Sprintf("int(%o)", obj);
    when MonStgElt:
        return "u'" cat obj cat "'";
    when Assoc:
        keys := Keys(obj);
        if #keys eq 0 then return "{}"; end if;
        assert &and[Type(k) eq MonStgElt : k in keys];
        objs := [<k,$$(obj[k])> : k in Sort([k: k in keys])];
        str := Sprintf("{'%o': %o", objs[1][1], objs[1][2]);
        for i:=2 to #objs do str cat:= Sprintf(", '%o': %o", objs[i][1], objs[i][2]); end for;
        return str cat "}";
    when SeqEnum:
        if #obj eq 0 then return "[]"; end if;
        str := "[" cat $$(obj[1]);
        for i:=2 to #obj do str cat:= ", " cat $$(obj[i]); end for;
        return str cat "]";
    when Tup:
        if #obj eq 0 then return "[]"; end if;
        str := "[" cat $$(obj[1]);
        for i:=2 to #obj do str cat:= ", " cat $$(obj[i]); end for;
        return str cat "]";
    when Rec:
        str := "{"; n:= 0;
        for field in Names(obj) do
            if assigned obj``field then
                if n gt 0 then str cat:= ", "; end if;
                str cat:= "'" cat field cat "': " cat $$(obj``field);
                n +:= 1;
            end if;
        end for;
        return str cat "}";
    else:
        printf "bson_string: don't know how to handle type %o", Type(obj);
        assert false;
    end case;
end function;
    
OTHER := 0; DIGIT := 1; LETTER := 2; TIMES := 3;
chartypes := [OTHER : i in [1..127]];
for i:=StringToCode("0") to StringToCode("9") do chartypes[i]:=DIGIT; end for;
for i:=StringToCode("A") to StringToCode("Z") do chartypes[i]:=LETTER; end for;
for i:=StringToCode("a") to StringToCode("z") do chartypes[i]:=LETTER; end for;
chartypes[StringToCode("*")] := TIMES;
    
function prettify(name)
    types := [chartypes[StringToCode(name[i])] : i in [1..#name]];
    pretty := name[1];
    inbrackets := false;
    for i:=2 to #name do
        c := name[i];
        case types[i]:
        when DIGIT:
            if types[i-1] eq LETTER then
                pretty cat:= "_";
                if i lt #name and types[i+1] eq DIGIT then pretty cat:= "{"; inbrackets := true; end if;
            end if;
            pretty cat:= c;
        when LETTER:
            if inbrackets then pretty cat:= "}"; inbrackets := false; end if;
            pretty cat:= c;
        when TIMES:
            if inbrackets then pretty cat:= "}"; inbrackets := false; end if;
            pretty cat:= "\\\\times ";
        else:
            if inbrackets then pretty cat:= "}"; inbrackets := false; end if;
            pretty cat:= c;
        end case;
    end for;
    if inbrackets then pretty cat:= "}"; end if;
    return pretty;
end function;

function id_to_label(id)
    return Sprintf("%o.%o",id[1],id[2]);
end function;

function small_group_data(G)
    A:=AssociativeArray();
    A["label"] := id_to_label(IdentifyGroup(G));
    A["abelian"] := IsAbelian(G);
    A["cyclic"] := IsCyclic(G);
    A["perfect"] := IsPerfect(G);
    A["simple"] := IsSimple(G);
    A["solvable"] := IsSolvable(G);
    A["order"] := Order(G);
    A["exponent"] := Exponent(G);
    A["name"] := GroupName(G);
    A["pretty"] := prettify(A["name"]);
    S:={*<c[1],c[2]>:c in ConjugacyClasses(G)*};
    S:=Sort([<c[1],c[2],Multiplicity(S,c)>:c in Set(S)]);
    A["clases"] := S;
    S:={*IdentifyGroup(H`subgroup):H in MaximalSubgroups(G)*};
    S:=Sort([<c,Multiplicity(S,c)>:c in Set(S)]);
    S:=[<id_to_label(c[1]),c[2]>:c in S];
    A["maximal_subgroups"] := S;
    S:={*IdentifyGroup(H`subgroup):H in NormalSubgroups(G)*};
    S:=Sort([<c,Multiplicity(S,c)>:c in Set(S)]);
    S:=[<id_to_label(S[i][1]),S[i][2]>  : i in [2..#S-1]]; // omit trivial and whole group
    A["normal_subgroups"] := S;
    A["center"] := id_to_label(IdentifyGroup(Center(G)));
    A["derived_group"] := id_to_label(IdentifyGroup(DerivedSubgroup(G)));
    A["abelian_quotient"] := id_to_label(IdentifyGroup(AbelianQuotient(G)));
    return A;
end function;

procedure dump_small_groups_data(maxN:filename:="")
    if #filename gt 0 then fp := Open(filename,"w"); end if;
    n:=0;
    for N:=1 to maxN do
        if #filename gt 0 then printf "Generating data for %o subgroups of order %o...\n", NumberOfSmallGroups(N), N; end if;
        for G in SmallGroups(N:Warning:=false) do
            data:=bsonify(small_group_data(G));
            if #filename gt 0 then Puts(fp,data); else print data; end if;
            n+:=1;
        end for;
    end for;
    if #filename gt 0 then
        Flush(fp);
        printf "Wrote %o records to file %o\n", n, filename;
    end if;
end procedure;
