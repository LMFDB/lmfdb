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
    return [f,h]
