/*
Lists all labels of isogeny classes for genus 1 and Fq, where q is a prime 
power ranging from 2 to 499, or q is in [512, 625, 729, 1024], except 
for when q is divisible by 2 or 3, it only lists labels for abvars with j-invariants not 0. 

For each label, and for each field of characteristic not 2 or 3,
it lists a canonical representative for each isomorphism class in the isogeny class.

For each label, and for each field of characteristic 2 or 3 and j-invariant not 0, 1728
it lists a representative for each isomorphism class in the isogeny class.

For characteristics 2 or 3 and j-invariant equal to 0 or 1728, we use 
John Cremona's sage package to pick a favourite curve of each isomorphism class.
See g1_char23_j_0.sage.
*/


// returns the LMFDB label of the isogeny class determined by the l-poly f.
IsogenyLabel := function(E)
    f := LPolynomial(E);
    q := #BaseField(E);

    g := Degree(f) div 2;
    str1 := Reverse(Prune(Coefficients(f)))[1..g];
    str2 := "";
    for a in str1 do
        if a lt 0 then
            str2 := str2 cat "a" cat Base26Encode(-a) cat "_";
            else
            str2 := str2 cat Base26Encode(a) cat "_";
        end if;
    end for;
    str2 := Prune(str2);
    isog_label := Sprintf("%o.%o.",g,q) cat str2;
    return isog_label;
end function;


EllCurveToString := function(E)
    q := #BaseField(E);
    k<a> := GF(q);
    R<x> := PolynomialRing(k);
    
    f, yCoeff := HyperellipticPolynomials(E);

    if not (q mod 2 eq 0 or q mod 3 eq 0) then
        // We assume that E is in magma's Weierstrass model. Hence the xy and y terms are 0.
        assert IsWeierstrassModel(E);
        assert yCoeff eq 0;
        return "y^2 = " cat Sprint(f);
    else 
        if yCoeff eq 0 then
            return "y^2 = " cat Sprint(f);
        elif yCoeff eq x then 
            return &cat["y^2 + x*y = ", Sprint(f)];
        else 
            return &cat["y^2 + (", Sprint(yCoeff) ,")*y = ", Sprint(f)];
        end if;
    end if;

end function;


// A helper function to the first nonsquare c in the field
// where the order is determined by magma's default enumeration
Pickc := function(F)
    for x in F do 
        if not x eq 0 and not IsSquare(x) then 
            return x;
        end if;
    end for;
    return 0;
end function;

// For char not 2 or 3, j-invariant not 0 or 1728
// the following function returns an isomorphic model of the form 

// y^2 = x^3 + Mx + M (if B/A is square)
// or 
// y^2 = x^3 + Mx + cM (if B/A is non-square)

// by replacing (A,B) with (lambda^4*A, lambda^6*B)
// where lambda = (Sqrt(B/A)^(-1)) if (B/A) is square,
// (Sqrt((B/A)*c)^(-1)) otherwise
// c is a non-square nonzero field element determined by function Pickc

// For char not 2 or 3, j-invariant equals 0 or 1728, 
// since those curves form a one-parameter family
// of the form y^2=x^3+Ax or y^2=x^3+B, 
// the isomorphic curves are parametrized by lambda^4*A or lambda^6*B.
// We pick the smallest number in this parametrization as representative.

findIsomorphicRepresentative := function(E)
    k := BaseField(E);
    q := #BaseField(E);
    if ((q mod 2) eq 0) or ((q mod 3) eq 0) then
        // In this case, we don't find a canonical
        // representative for its isomorphism class

        newE := E;
    elif jInvariant(E) eq (k!0) then 
        E := WeierstrassModel(E);
        B:=Coefficients(E)[5];
        // pick smallest [lambda^6 * B] where we cycle all lambda in k
        repB := Min([lambda^6 * B : lambda in k| lambda ne 0]);
        newE := EllipticCurve([0,0,0,0,repB]);
    elif jInvariant(E) eq  (k!1728) then 
        E := WeierstrassModel(E);
        A:=Coefficients(E)[4];
        // pick smallest [lambda^4 * A] where we cycle all lambda in k
        repA := Min([lambda^4 * A : lambda in k| lambda ne 0]);
        newE := EllipticCurve([0,0,0,repA,0]);
    else 
        E := WeierstrassModel(E);
        A := Coefficients(E)[4];
        B := Coefficients(E)[5];
        
        assert not (A eq 0) and not (B eq 0);
        BoverA := B/A;
        Lambda := 1;

        c := Pickc(k);

        if IsSquare(BoverA) then 
            Lambda := (Sqrt(BoverA))^(-1);
        else 
            Lambda := Sqrt((BoverA)^(-1)*(c));
        end if;

        newE := EllipticCurve([0,0,0,Lambda^4*A, Lambda^6*B]);
    end if;
    
    // validity check
    assert IsogenyLabel(E) eq IsogenyLabel(newE);
    return newE;
end function;


EnumerateIsogenyClassesG1 := function(q)
    // generate one representative for each j-invariant,
    // and for each representative, generate all its twists.
    k := GF(q);
    if (q mod 2 eq 0) or (q mod 3 eq 0) then 
        jInvReps := [EllipticCurveFromjInvariant(j) : j in k | not j in [k!0, k!1728]]; 
    else 
        jInvReps := [EllipticCurveFromjInvariant(j) : j in k]; 
    end if;
    allEllCurves := &cat[Twists(E): E in jInvReps];        
    
    /*
    In the case that char is 2 or 3, we don't have a canonical class, 
    so it's always good to check that it is not isomorphic to any existing curves
    */
    if (q mod 2 eq 0) or (q mod 3 eq 0) then 
        nonIsoCurves := [];
        for E in allEllCurves do 
            if &or[IsIsomorphic(E,existingCurve) : existingCurve in nonIsoCurves] then 
                break;
            end if;
            Append(~nonIsoCurves, E);
        end for;
        allEllCurves := nonIsoCurves;
    end if;

    labelToCurves := AssociativeArray();
    for E in allEllCurves do 
        label := IsogenyLabel(E);  
        if not label in Keys(labelToCurves) then 
            labelToCurves[label] := Set([]);
        end if;
        Include(~labelToCurves[label], EllCurveToString(findIsomorphicRepresentative(E)));
    end for;
    return labelToCurves;
end function;

// Now, generate the data for prime powers 2 <= q <= 499, and q in {512, 625, 729, 1024}, 
DictionaryToFile := procedure(g, q, ~D, filename)
    Write(filename, "\n");
    Write(filename, &cat["(g, q)= (", Sprint(g),",",Sprint(q),")"]);
    for key in Keys(D) do 
        output := key cat "|" cat Sprint(D[key]);
        output := StripWhiteSpace(output);
        Write(filename, output);
    end for;
end procedure;

PrimePowers:=[2..499] cat [512, 625, 729, 1024];

// It outputs data into two files:
// {label|isomorphism classes} -> outputFilename, this is the actual data
// {q, # of labels for each q} -> countsFilename, this is used for checking the consistency with lmfdb
OutputAllData := procedure(qs, outputFilename, countsFilename)
    QLabelPairs := [];
    Write(outputFilename, "\n" : Overwrite:=true);
    Write(countsFilename, "\n" : Overwrite:=true);
    for q in qs do 
        if IsPrimePower(q) then 
            results := EnumerateIsogenyClassesG1(q);
            DictionaryToFile(1,q,~results,outputFilename);
            Append(~QLabelPairs, [q, #Keys(results)]);
        end if;
    end for;

    Write(countsFilename, "The following are (q, #of labels produced) pairs");
    Write(countsFilename, "WARNING: for char 2 or 3, j = 0 or 1728, labels are not presented here.");
    for qLabelPair in QLabelPairs do 
        Write(countsFilename, &cat[Sprint(qLabelPair[1]), ",", Sprint(qLabelPair[2])]);
    end for;
end procedure;

OutputAllData(PrimePowers, "output.txt", "counts.txt");
