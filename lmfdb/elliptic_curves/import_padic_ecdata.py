# -*- coding: utf-8 -*-
import os.path
import sys
from sage.all import SQLDatabase
import base

padic_db = base.getDBConnection().ellcurves.padic_db
padic_db.ensure_index("label")
padic_db.ensure_index("prime")


def lookup_or_create(label, p):
    item = padic_db.find_one({'label': label, 'p': p})
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
