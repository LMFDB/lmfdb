from lmfdb.base import getDBConnection
from data_mgt.utilities.rewrite import update_attribute_stats

def update_stats(verbose=True):
    L = getDBConnection().Lattices
    update_attribute_stats(L,'lat','class_number', nocounts=True)
    update_attribute_stats(L,'lat','dim', nocounts=True)
    update_attribute_stats(L,'lat','det', nocounts=True)

