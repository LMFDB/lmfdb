def primitive(rec):
    if rec['primitivization'] == rec['label']:
        rec['is_primitive'] = True
    else:
        rec['is_primitive'] = False 
    return rec
