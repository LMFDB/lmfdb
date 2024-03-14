
from lmfdb import db
from .mf import TracesChecker

class mf_hecke_traces(TracesChecker):
    table = db.mf_hecke_traces
    base_table = db.mf_newforms
    base_constraint = {}
