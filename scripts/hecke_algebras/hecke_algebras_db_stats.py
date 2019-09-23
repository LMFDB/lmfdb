################################################################################
#
# Function to update the hecke_algebras.stats collection, to be run after adding data
#
################################################################################


from lmfdb.base import getDBConnection
from data_mgt.utilities.rewrite import update_attribute_stats
 
                    
def update_stats(verbose=True):
    h = getDBConnection().hecke_algebras
    update_attribute_stats(h,'hecke_algebras','level', nocounts=True)
    update_attribute_stats(h,'hecke_algebras','weight', nocounts=True)

