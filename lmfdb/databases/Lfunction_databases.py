# Not used yet

from lmfdb.base import getDBConnection

C = getDBConnection()

lfunction_location = ("limbo", "lfunction20130910")

collection = C[lfunction_location[0]][lfunction_location[1]]

from operators import itemgetter

def schema_extract(x, **types_dict):
    # each kwarg is a a key, value pair
    # the key is the name of the attribute and the field in the database
    # value is the type to be used internally in the database
    return {key : value(itemgetter(key)(x)) for key, value in types_dict}

database_format:
    {        # We are dealing with many sources of Lfunctions, so we                     need to cast everything to make sure we control the type
        "mu_fe" : int, 
        "nu_fe" : int, 
        "sign": int, 
        "selfdual": bool,
        "primitive": bool,
        "motivic_weight": bool,
        "algebraic": bool,
        "Ltype": str,
        "original_mathematical_object": str,
        
    }
    
def query_Lfunction():
    pass