################################################################################
#
# Function to update the hecke_algebras.stats collection, to be run after adding data
#
################################################################################


from lmfdb.base import getDBConnection
 
                    
def update_stats(verbose=True):
    h = getDBConnection().hecke_algebras
    hh= h.hecke_algebras
    heckedbstats = h.stats
    
    data = {}
    data['num_hecke'] = int(hh.count())
    data['max_lev_hecke'] = int(max(hh.find().distinct('level')))
    data['max_weight_hecke'] = int(max(hh.find().distinct('weight')))
    stats = heckedbstats.find_one()
    print stats
    heckedbstats.update_one({'label': 'statistics'},{"$set": data}, upsert=True)
    print stats
    print "done updating stats"
    
