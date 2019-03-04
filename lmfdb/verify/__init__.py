# Nothing in this folder should be imported from the rest of the LMFDB,
# since we don't make guarantees about safety from SQL injection.
# It is intended for use from an interactive sage prompt or from a Python script

import os, importlib

import lmfdb.backend.database as database
from lmfdb.app import is_running
if is_running():
    raise RuntimeError("Cannot verify while running website (SQL injection vulnerabilities)")
##### Need to check that the website isn't running #####

_curdir = os.path.dirname(os.path.abspath(__file__))
_prefix = 'lmfdb.verify.'
for tablename in database.db.tablenames:
    filename = os.path.join(_curdir, tablename + '.py')
    if os.path.exists(filename):
        verifier = getattr(importlib.import_module(_prefix + tablename), tablename)
        database.db[tablename]._verifier = verifier()
database.db.is_verifying = True
db = database.db
__all__ = ['db']
