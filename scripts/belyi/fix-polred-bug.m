// fixing wrong base field polynomial
// currently affecting 8T50-8_4.1.1.1.1_4.4-b and 8T50-8_4.1.1.1.1_6.2-a

load "8T50-8_4.1.1.1.1_4.4-b.m";
AttachSpec("~/github/CHIMP/CHIMP.spec");
Kred, mpred:= Polredabs(K);
f, _ := HyperellipticPolynomials(X);
// make isomorphic curve over polredabs-ed numfield
Xred := EllipticCurve(Polynomial([mpred(el) : el in Coefficients(f)]));
KXred := FunctionField(Xred);

// make homomorphism from KX to KXred
cf := hom< Kred -> KXred | Kred.1>;
KXalg, mp_alg := AlgorithmicFunctionField(KX);
Kx := BaseRing(KXalg);
//Kx := RationalFunctionField(K);
c_final := hom< Kx -> KXred | (mpred*cf), [KXred.1] >;
//hom< Kx -> KXred | (iota*cf), [KXred.1] >;

// final success
chg_fld := hom< KXalg -> KXred | c_final, [KXred.2]>;
chg_fld(mp_alg(phi));
