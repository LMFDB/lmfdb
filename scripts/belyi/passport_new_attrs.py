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

def assign_automorphism_group(rec):
    """
    Given a passport rec, compute its automorphism group as the centralizer of its monodromy group
    """
    galmap = db.belyi_galmaps.lucky({'plabel':rec['plabel']})
    rec['aut_group'] = galmap['aut_group']
    return rec

def base_field_deg(rec):
    rec['base_field_deg'] = len(rec['base_field']) - 1
    return rec
