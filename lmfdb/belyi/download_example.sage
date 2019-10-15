from lmfdb import db

belyi = db.belyi
s = ""
label = '5T4-[5,3,3]-5-311-311-g0-a'
rec = belyi.lookup('5T4-[5,3,3]-5-311-311-g0-a')
s += "// Magma code for Belyi map with label %s\n\n" % label
s += "// Define the base field\n"
if rec['base_field'] == [-1,1]:
    s += "K<nu> := RationalsAsNumberField();\n"
else:
    s += "R<T> := PolynomialRing(Rationals());\nK<nu> := NumberField(R!%s)\n\n" % rec['base_field']
s += "// Define the curve\n"
if rec['g'] == 0:
    s += "X := Curve(ProjectiveSpace(PolynomialRing(%s, 2)));\n" % K
elif: rec['g'] == 1:
    _<x> := PolynomialRing(K);
    curve_poly = rec['curve'].split("=")[1]   
    s += "X := EllipticCurve(%s) % curve_poly;\n"
else:
    _<x> := PolynomialRing(K);
    curve_poly = rec['curve'].split("=")[1]   
    s += "X := HyperellipticCurve(%s) % curve_poly;\n" # need to worry about cross-term maybe...
