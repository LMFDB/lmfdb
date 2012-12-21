import base


def get_distinct_keys(dbname, key):
    res = []
    db = base.DBConnect(dbname)
    for c in db.collection_names():
        res.extend(db[c].distinct(key))
    res = set(res)
    res = list(res)
    return res


def my_get(dict, key, default, f=None):
    r"""
    Improved version of dict.get where an empty string also gives default.
    and before returning we apply f on the result.
    """
    x = dict.get(key, default)
    if x == '':
        x = default
    if f is not None:
        try:
            x = f(x)
        except:
            pass
    return x
