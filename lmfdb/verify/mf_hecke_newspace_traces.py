
from lmfdb import db
from .mf import TracesChecker

class mf_hecke_newspace_traces(TracesChecker):
    table = db.mf_hecke_newspace_traces
    base_table = db.mf_newspaces
    base_constraint = {'traces':{'$exists':True}}
