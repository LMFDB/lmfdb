from lmfdb import db
def assign_passport_triples(rec):
    """
    Given a passport rec, find all galmaps belonging to rec and save their triples to rec['triples']
    """
    galmaps = db.belyi_galmaps.search({'plabel':rec['plabel']})
    trips = []
    for g in galmaps:
        trips.extend(g['triples'])
    rec['triples'] = trips
    return rec

# can actually pull from galmaps like triples above
def assign_automorphism_group(rec):
    """
    Given a passport rec, compute its automorphism group as the centralizer of its monodromy group
    """
    gp = rec['group']
    d,k = [ZZ(el) for el in gp.split("T")]
    G = TransitiveGroup(d,k)
    S = SymmetricGroup(d)
    C = S.centralizer(G)
    return C
