
from lmfdb import db
from .mf import MfChecker

class mf_newform_portraits(MfChecker):
    table = db.mf_newform_portraits
    label = ['level', 'weight', 'char_orbit_index', 'hecke_orbit']
    label_conversion = {'char_orbit_index':-1, 'hecke_orbit':-1}
    uniqueness_constraints = [['label'], label]

    # attached to mf_newforms
    # check that there is exactly one record in mf_newform_portraits for each record in mf_newforms, uniquely identified by label

