from lmfdb import db
from lmfdb.ecnf.WebEllipticCurve import parse_ainvs
from lmfdb.belyi.main import hyperelliptic_polys_to_ainvs, curve_string_parser
from sage.all import EllipticCurve
import re
from lmfdb.genus2_curves.main import genus2_lookup_equation as genus2_lookup_equation_polys

def genus2_lookup_equation(rec):
    f,h = curve_string_parser(rec)
    return genus2_lookup_equation_polys(str([f,h]))

def genus1_lookup_equation_QQ(rec):
    assert rec['g'] == 1
    f,h = curve_string_parser(rec)
    ainvs = hyperelliptic_polys_to_ainvs(f,h)
    E = EllipticCurve(ainvs)
    j = E.j_invariant()
    for r in db.ec_curvedata.search({"jinv":[j.numerator(), j.denominator()]}):
        ainvs2 = r['ainvs']
        E2 = EllipticCurve(ainvs2)
        if E.is_isomorphic(E2):
            return r['lmfdb_label']
    #print("Curve not found in database")
    return None

def NFelt(a):
    r""" Returns an NFelt string encoding the element a (in a number field
    K).  This consists of d strings representing the rational
    coefficients of a (with respect to the power basis), separated by
    commas, with no spaces.

    For example the element (3+4*w)/2 in Q(w) gives '3/2,2'.
    """
    return ",".join(str(c) for c in list(a))

def genus1_lookup_equation_nf(rec):
    assert rec['g'] == 1
    # make base field
    nf_matches = list(db.nf_fields.search({'coeffs':rec['base_field']}))
    if len(nf_matches) == 0:
        return None
    else:
        nf_rec = nf_matches[0]
        # make curve
        f,h = curve_string_parser(rec)
        ainvs = hyperelliptic_polys_to_ainvs(f,h)
        E = EllipticCurve(ainvs)
        K = E.base_field()
        j = E.j_invariant()
        j_str = NFelt(j)
        j_matches = list(db.ec_nfcurves.search({"field_label":nf_rec['label'], "jinv":j_str}))
        for r in j_matches:
            ainvs2 = parse_ainvs(K, r['ainvs'])
            E2 = EllipticCurve(ainvs2)
            assert E.base_field() == E2.base_field()
            if E.is_isomorphic(E2):
                return r['label']
    #print("Curve not found in database")
    return None

# This code might not find base changes.
def genus1_lookup_equation(rec):
    if rec['base_field'] == [-1, 1]: # if defined over QQ
        return genus1_lookup_equation_QQ(rec)
    else:
        return genus1_lookup_equation_nf(rec)

def find_curve_label(rec):
    if rec['g'] == 1:
        #print("Searched for curve for %s") % rec['label']
        return genus1_lookup_equation(rec)
    elif rec['g'] == 2:
        if rec['base_field'] == [-1, 1]: # currently LMFDB only has g2 curves over QQ
            #print("Searched for curve for %s") % rec['label']
            return genus2_lookup_equation(rec)

def find_curve_url(rec):
    label = find_curve_label(rec)
    if label:
        curve_url = ''
        if rec['g'] == 1:
            curve_url += 'EllipticCurve'
            if rec['base_field'] == [-1, 1]: # over QQ
                curve_url += '/Q'
                label_spl = label.split(".")
                curve_url += '/%s' % label_spl[0] # conductor
                curve_url += '/%s/%s' % re.match(r"(\D+)(\d+)", label_spl[1]).groups() # isog class and isomorphism index
            else: # over number field
                label_spl = label.split("-")
                curve_url += "/%s/%s" % (label_spl[0], label_spl[1]) # field, conductor
                curve_url += '/%s/%s' % re.match(r"(\D+)(\d+)", label_spl[2]).groups() # isog class and isomorphism index
        if rec['g'] == 2:
            curve_url += 'Genus2Curve'
            if rec['base_field'] == [-1, 1]:
                curve_url += '/Q'
                curve_url += '/%s' % label.replace(".","/")
        return curve_url

def initialize_friends(rec):
    rec[u'friends'] = []
    return rec

def assign_curve_friends(rec):
    curve_url = find_curve_url(rec)
    if curve_url:
        rec['friends'].append(curve_url)
    return rec

def assign_curve_label(rec):
    label = find_curve_label(rec)
    if label:
        rec['curve_label'] = label
    return rec
