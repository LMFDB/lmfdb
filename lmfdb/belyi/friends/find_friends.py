from lmfdb import db
from lmfdb.ecnf.WebEllipticCurve import parse_NFelt, parse_ainvs
from lmfdb.belyi.main import hyperelliptic_polys_to_ainvs, curve_string_parser
from scripts.ecnf.import_utils import NFelt

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

# No, input should be a BELYI rec, not an ellcrv rec
def genus1_lookup_equation_QQ(rec):
    assert rec['g'] == 1
    f,h = curve_string_parser(rec)
    ainvs = hyperelliptic_polys_to_ainvs(f,h)
    E = EllipticCurve(ainvs)
    j = E.j_invariant()
    for r in db.ec_curves.search({"jinv":str(j)}): # is there a better way to search than by j-invariant?
        ainvs2 = r['ainvs']
        E2 = EllipticCurve(ainvs2)
        if E.is_isomorphic(E2):
            return r['label']
    print "Curve not found in database"
    return None

def genus1_lookup_equation_nf(rec):
    assert rec['g'] == 1
    # make base field
    R = PolynomialRing(QQ, "x")
    x = R.gens()[0]
    nf_matches = list(db.nf_fields.search({'coeffs':rec['base_field']}))
    if len(nf_matches) == 0:
        print "Base field not found in database"
        #print "Curve not found in database"
        return None
    else:
        nf_rec = nf_matches[0]
        K = NumberField(R(rec['base_field']), "a")
        a = K.gens()[0]
        print "\n\nCurve defined over %s" % K
        # make curve
        f,h = curve_string_parser(rec)
        ainvs = hyperelliptic_polys_to_ainvs(f,h)
        E = EllipticCurve(ainvs)
        j = E.j_invariant()
        j_str = NFelt(j)
        print "Curve has j-invariant %s, represented as %s" % (j, j_str)
        j_matches = list(db.ec_nfcurves.search({"field_label":nf_rec['label'] , "jinv":j_str})) # is there a better way to search than by j-invariant?
        print "Found %d curves with same j-invariant" % len(j_matches)
        for r in j_matches:
            nf_lab = r['field_label']
            nf_rec = db.nf_fields.lookup(nf_lab)
            K2 = NumberField(R(nf_rec['coeffs']), 'b')
            b = K2.gens()[0]
            ainvs2 = parse_ainvs(K2, r['ainvs'])
            E2 = EllipticCurve(ainvs2)
            if E.is_isomorphic(E2):
                return r['label']
    print "Curve not found in database"
    return None

def genus1_lookup_equation(rec):
    if rec['base_field'] == [-1, 1]:
        return genus1_lookup_equation_QQ(rec)
    else:
        return genus1_lookup_equation_nf(rec)
