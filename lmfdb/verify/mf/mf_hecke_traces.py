
from lmfdb import db
from .mf import TracesChecker

class mf_hecke_traces(TracesChecker):
    table = db.mf_hecke_traces_eis
    base_table = db.mf_newforms_eis
    base_constraint = {}
