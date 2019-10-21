from lmfdb import db
belyi = db.belyi_galmaps

s = ""
#label = '5T4-[5,3,3]-5-311-311-g0-a'
#label = '6T13-[6,4,6]-6-42-321-g1-a'
label = '7T5-[7,7,4]-7-7-421-g2-a'
rec = belyi.lookup(label)
s += "// Magma code for Belyi map with label %s\n\n" % label
s += "// Define the base field\n"
if rec['base_field'] == [-1,1]:
    s += "K<nu> := RationalsAsNumberField();\n"
else:
    s += "R<T> := PolynomialRing(Rationals());\nK<nu> := NumberField(R!%s);\n\n" % rec['base_field']
s += "// Define the curve\n"
if rec['g'] == 0:
    s += "X := Curve(ProjectiveSpace(PolynomialRing(K, 2)));\n"
    s += "// Define the map\n"
    s += "KX<x> := FunctionField(X);\n";
    s += "phi := %s;\n" % rec['map']
elif rec['g'] == 1:
    s += "_<x> := PolynomialRing(K);\n"
    curve_poly = rec['curve'].split("=")[1]
    s += "X := EllipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
    s += "// Define the map\n"
    s += "KX<x,y> := FunctionField(X);\n";
    s += "phi := %s;\n" % rec['map']
elif rec['g'] == 2:
    s += "_<x> := PolynomialRing(K);\n"
    curve_poly = rec['curve'].split("=")[1]
    s += "X := HyperellipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
    s += "// Define the map\n"
    s += "KX<x,y> := FunctionField(X);\n";
    s += "phi := %s;\n" % rec['map']
else:
    print("Sorry, not implemented yet! :(")
print(s)

def make_base_field_string(rec,lang):
    s = ""
    if lang == "magma":
        if rec['base_field'] == [-1,1]:
            s += "K<nu> := RationalsAsNumberField();\n"
        else:
            s += "R<T> := PolynomialRing(Rationals());\nK<nu> := NumberField(R!%s);\n\n" % rec['base_field']
    elif lang == "sage":
        if rec['base_field'] == [-1,1]:
            s += "K = QQ\n" # is there a Sage version of RationalsAsNumberField()?
        else:
            s += "R.<T> = PolynomialRing(QQ)\nK.<nu> := NumberField(R(%s))\n\n" % rec['base_field']
    else:
        print("Sorry, not implemented! :(")
    return s

def make_base_field(rec):
    if rec['base_field'] == [-1,1]:
        K = QQ # is there a Sage version of RationalsAsNumberField()?
    else:
        R.<T> = PolynomialRing(QQ)
        poly = R(rec['base_field'])
        K.<nu> = NumberField(poly)
    return K

def curve_string_parser(rec):
    curve_str = rec['curve']
    curve_str = curve_str.replace("^","**")
    K = make_base_field(rec)
    nu = K.gens()[0]
    S0.<x> = PolynomialRing(K)
    S.<y> = PolynomialRing(S0)
    parts = curve_str.split('=')
    lhs_poly = sage_eval(parts[0], locals = {'x':x, 'y':y, 'nu':nu})
    rhs_poly = sage_eval(parts[1], locals = {'x':x, 'y':y, 'nu':nu})
