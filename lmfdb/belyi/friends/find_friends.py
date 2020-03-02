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
    ainvs = hyperelliptic_polys_to_ainvs(curve_string_parser(rec))
    E = EllipticCurve(ainvs)
    j = E.j_invariant()
    for r in db.ec_curves.search({"jinv":str(j)}): # is there a better way to search than by j-invariant?
        ainvs2 = r['ainvs']
        E2 = EllipticCurve(ainvs2)
        if E.is_isomorphic(E2):
            return r['label']
    print "Curve not found in database"
    return None

# TODO: have to add numfld parsing everywhere; see WebEllipticCurve.py
def genus1_lookup_equation_nf(rec):
    assert rec['g'] == 1
    # make base field
    R.<x> = PolynomialRing(QQ)
    K.<a> = NumberField(R(rec['base_field']))
    # make curve
    ainvs = hyperelliptic_polys_to_ainvs(curve_string_parser(rec))
    E = EllipticCurve(ainvs)
    j = E.j_invariant()
    j_str = NFelt(j)
    for r in db.ec_nfcurves.search({"jinv":j_str}): # is there a better way to search than by j-invariant?
        nf_lab = rec['field_label']
        nf_rec = db.nf_fields.lookup(nf_lab)
        K2.<a> = NumberField(R(nf_rec['coeffs']))
        ainvs2 = parse_ainvs(K2, r['ainvs'])
        E2 = EllipticCurve(ainvs2)
        if E.is_isomorphic(E2):
            return r['label']
    print "Curve not found in database"
    return None
