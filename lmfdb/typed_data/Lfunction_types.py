# Not used yet

def schema_extract(x, **types_dict):
    # each kwarg is a a key, value pair
    # the key is the name of the attribute and the field in the database
    # dtype is the datatype to be used internally in the database
    return {key : dtype(x[key]) for key, dtype in types_dict}

# We are dealing with many sources of Lfunctions, so we need to cast everything to make sure we control the type
database_format = {
        "mu_fe" : int,
        "nu_fe" : int,
        "sign": int,
        "selfdual": bool,
        "primitive": bool,
        "motivic_weight": bool,
        "algebraic": bool,
        "Ltype": str,
        "original_mathematical_object": str
    }

def query_Lfunction():
    pass
