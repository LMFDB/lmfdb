from lmfdb import db

def primitive(rec):
    if rec['primitivization'] == rec['label']:
        rec['is_primitive'] = True
    else:
        rec['is_primitive'] = False 
    return rec

# get primitivization for passports by pulling from galmaps
def primitive_passport(rec):
    map_rec = db.belyi_galmaps_fixed.lucky({"plabel":rec["plabel"]})
    rec["is_primitive"] = map_rec["is_primitive"]
    map_prim = db.belyi_galmaps_fixed.lookup(map_rec["primitivization"])
    rec["primitivization"] = map_prim["plabel"]
    return rec
