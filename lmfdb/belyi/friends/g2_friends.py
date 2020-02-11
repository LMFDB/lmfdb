# function stolen from Drew's branch g2c-eqn-lookup
def genus2_lookup_equation(f):
    f.replace(" ","")
    R = PolynomialRing(QQ,'x')
    if ("x" in f and "," in f) or "],[" in f:
        if "],[" in f:
            e = f.split("],[")
            f = [R(literal_eval(e[0][1:]+"]")),R(literal_eval("["+e[1][0:-1]))]
        else:
            e = f.split(",")
            f = [R(str(e[0][1:])),R(str(e[1][0:-1]))]
    else:
        f = R(str(f))
    try:
        C = magma.HyperellipticCurve(f)
        g2 = magma.G2Invariants(C)
    except:
        return None
    g2 = str([str(i) for i in g2]).replace(" ","")
    for r in db.g2c_curves.search({'g2_inv':g2}):
        eqn = literal_eval(r['eqn'])
        D = magma.HyperellipticCurve(R(eqn[0]),R(eqn[1]))
        if magma.IsIsomorphic(C,D):
            return r['label']
    return None
