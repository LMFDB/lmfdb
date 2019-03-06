# -*- coding: utf-8 -*-
from lmfdb import db

# 2018: updated for postgres, but not used (ever?)

padic_db = db.ec_padic

def lookup_or_create(label, p):
    item = padic_db.lucky({'label': label, 'p': p})
    if item is None:
        return {'label': label, 'p': p}
    else:
        return item

# for path in sys.argv[1:]:
#    print path
#    D = SQLDatabase(filename=path)
#    query_dict = {'table_name': 'regulators', 'display_cols': ['p', 'val', 'zz', 'label'], 'expression': ['p','>','0']}
#    Q = D.query(query_dict)
#    for p, val, zz, label in Q.run_query():
#        p = int(p)
#        info =lookup_or_create(label,p)
#        info['val'] = val
#        info['prec'] = 20
#        info['unit'] = zz
#        padic_db.save(info)
