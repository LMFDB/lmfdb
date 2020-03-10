from lmfdb import db
from lmfdb.ecnf.WebEllipticCurve import parse_NFelt, parse_ainvs
from lmfdb.belyi.main import hyperelliptic_polys_to_ainvs, curve_string_parser
from scripts.ecnf.import_utils import NFelt
from ast import literal_eval

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

def genus1_lookup_equation_QQ(rec):
    assert rec['g'] == 1
    f,h = curve_string_parser(rec)
    ainvs = hyperelliptic_polys_to_ainvs(f,h)
    E = EllipticCurve(ainvs)
    j = E.j_invariant()
    for r in db.ec_curves.search({"jinv":str(j)}): # is there a better way to search than by j-invariant? Conductor?
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
        return None
    else:
        #print "Base field found"
        nf_rec = nf_matches[0]
        # make curve
        f,h = curve_string_parser(rec)
        ainvs = hyperelliptic_polys_to_ainvs(f,h)
        E = EllipticCurve(ainvs)
        K = E.base_field()
        a = K.gens()[0]
        j = E.j_invariant()
        j_str = NFelt(j)
        #cond_nrm = (E.conductor()).norm()
        #print "Curve has j-invariant %s over %s" % (j, K)
        #print "\nCurve has j-invariant %s, represented as %s" % (j, j_str)
        j_matches = list(db.ec_nfcurves.search({"field_label":nf_rec['label'] , "jinv":j_str})) # is there a better way to search than by j-invariant? Conductor norm?
        #j_matches = list(db.ec_nfcurves.search({"field_label":nf_rec['label'] , "jinv":j_str, 'conductor_norm':cond_nrm})) # throws weird Postgres error
        #print "Found %d curves with same j-invariant" % len(j_matches)
        for r in j_matches:
            ainvs2 = parse_ainvs(K, r['ainvs'])
            E2 = EllipticCurve(ainvs2)
            assert E.base_field() == E2.base_field()
            if E.is_isomorphic(E2):
                return r['label']
    print "Curve not found in database"
    return None

# TODO: problems if curve defined over smaller field than Belyi map.
# This code won't find base changes.
def genus1_lookup_equation(rec):
    if rec['base_field'] == [-1, 1]: # if defined over QQ
        return genus1_lookup_equation_QQ(rec)
    else:
        return genus1_lookup_equation_nf(rec)

def assign_curve_label(rec):
    if rec['g'] == 0:
        return None
    elif rec['g'] == 1:
        rec['curve_label'] = genus1_lookup_equation(rec)
        return "Searched for curve for %s" % rec['label']
    elif rec['g'] == 2:
        f,h = curve_string_parser(rec)
        rec['curve_label'] = genus1_lookup_equation(str([f,h]))
        return "Searched for curve for %s" % rec['label']
    else:
        return None
