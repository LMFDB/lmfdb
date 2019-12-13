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
        print("Sorry, not implemented! :(") # TODO: this should be an error
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
    lhs_cs = lhs_poly.coefficients()
    if len(lhs_cs) == 1:
        h = 0
    elif len(lhs_cs) == 2: # if there is a cross-term
        h = lhs_poly.coefficients()[0]
    else:
        print("Sorry, not implemented yet! :(") # TODO: this should be an error
    #rhs_poly = sage_eval(parts[1], locals = {'x':x, 'y':y, 'nu':nu})
    f = sage_eval(parts[1], locals = {'x':x, 'y':y, 'nu':nu})
    return f,h

def perm_maker_magma(rec):
    d = rec['deg']
    perms = []
    triples = rec['triples']
    for triple in triples:
        pref = "[Sym(%s) | " % d
        s_trip = "%s" % triple
        s_trip = pref + s_trip[1:]
        perms.append(s_trip)
    return '[' + ', '.join(perms) + ']'

def embedding_maker_magma(rec):
    emb_list = []
    embeddings = rec['embeddings']
    for z in embeddings:
        z_str = "ComplexField()!%s" % z
        emb_list.append(z_str)
    return '[' + ', '.join(emb_list) + ']'

def download_string_magma(rec):
    s = ""
    label = rec['label']
    s += "// Magma code for Belyi map with label %s\n\n" % label
    s += "\n// Group theoretic data\n\n"
    s += "d := %s;\n" % rec['deg']
    s += "i := %s;\n" % int(label.split('T')[1][0])
    s += "G := TransitiveGroups(d)[i];\n"
    s += "sigmas := %s;\n" % perm_maker_magma(rec)
    s += "embeddings := %s;\n" % embedding_maker_magma(rec)
    s += "\n// Geometric data\n\n"
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
        #curve_poly = rec['curve'].split("=")[1]
        #s += "X := EllipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
        s += "X := EllipticCurve(%s);\n" % curve_string_parser(rec);
        s += "// Define the map\n"
        s += "KX<x,y> := FunctionField(X);\n";
        s += "phi := %s;\n" % rec['map']
    elif rec['g'] == 2:
        s += "_<x> := PolynomialRing(K);\n"
        #curve_poly = rec['curve'].split("=")[1]
        #s += "X := HyperellipticCurve(%s);\n" % curve_poly; # need to worry about cross-term...
        s += "X := HyperellipticCurve(%s);\n" % curve_string_parser(rec);
        s += "// Define the map\n"
        s += "KX<x,y> := FunctionField(X);\n";
        s += "phi := %s;\n" % rec['map']
    else:
        print("Sorry, not implemented yet! :(") # TODO: should be an error
    return(s)
