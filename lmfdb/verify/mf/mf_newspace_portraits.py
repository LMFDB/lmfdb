
from lmfdb import db

from .mf import MfChecker

class mf_newspace_portraits(MfChecker):
    table = db.mf_newspace_portraits
    label = ['level', 'weight', 'char_orbit_index']
    uniqueness_constraints = [[table._label_col], label]
    label_conversion = {'char_orbit_index': -1}

    # attached to mf_newspaces:
    # check that there is a portrait present for every nonempty newspace in box where straces is set
