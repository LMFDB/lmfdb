
from lmfdb import db
from .mf import MfChecker

class mf_gamma1_portraits(MfChecker):
    table = db.mf_gamma1_portraits
    label = ['level', 'weight']
    uniqueness_constraints = [[table._label_col],label]

    # attached to mf_gamma1:
    # check that there is a portrait present for every record in mf_gamma1 with `dim > 0` and `level <= 4000`
