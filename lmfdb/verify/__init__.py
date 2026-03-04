# Nothing in this folder should be imported from the rest of the LMFDB,
# since we don't make guarantees about safety from SQL injection.
# It is intended for use from an interactive sage prompt or from a Python script

import os
import importlib

import lmfdb.lmfdb_database as database
from lmfdb.app import is_running
if is_running():
    raise RuntimeError("Cannot verify while running website (SQL injection vulnerabilities)")
##### Need to check that the website isn't running #####

_curdir = os.path.dirname(os.path.abspath(__file__))
_prefix = 'lmfdb.verify.'

for dirpath, dirs, filenames in os.walk(_curdir):
    filenames = [f for f in filenames if f[0] != '_']
    filenames = [f for f in filenames if os.path.splitext(f)[-1] == '.py']  # this filters out any table names that end up in log files
    dirs[:] = [d for d in dirs if d[0] != '_']
    for f in filenames:
        tablename = os.path.splitext(f)[0]
        if tablename in database.db.tablenames:
            other_thing = os.path.basename(os.path.normpath(dirpath)) + '.'
            verifier = getattr(importlib.import_module(_prefix + other_thing + tablename), tablename)
            database.db[tablename]._verifier = verifier()
database.db.is_verifying = True
db = database.db
__all__ = ['db']
