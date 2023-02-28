def check_galois_data(rec):
    return (len(rec['triples']) == (len(rec['base_field'])-1))

def delete_bad_galois_orbits():
    from lmfdb import db
    bad_galmaps = []
    bad_passports = []
    for rec in db.belyi_galmaps.search(): # should probably make the table name a variable...
        if not check_galois_data(rec):
            bad_galmaps.append(rec['label'])
            bad_passports.append(rec['plabel'])
    for lab in bad_galmaps:
        db.belyi_galmaps.delete({'label':lab})
    for plab in bad_passports:
        db.belyi_passports.delete({'plabel':plab})
    return "Removed %d galmaps and %d passports with bad Galois data" % (len(bad_galmaps), len(bad_passports))
