#A collection of functions usesd to patch up uploads which had bugs
import lmfdb.inventory_app.lmfdb_inventory as inv
import lmfdb.inventory_app.inventory_db_core as idc


def amend_collection_info(inv_db):
    """ Fixes missing or empty string collection Notes and Info for every db
    """

    a=list(inv_db.collection_ids.find())
    dummy_info = {} #Dummy per collection info, containing basic fields we want included
    for field in inv.info_editable_fields:
        dummy_info[field] = None

    for collection in a:
         if collection['INFO'] == '' or collection['NOTES'] == '':
             print 'Fixing ', collection['name']
             idc.set_coll(inv_db, collection['db_id'], collection['name'], collection['name'], {'description':''}, dummy_info)

def get_sample_of_table(inv_db, table_name, size=10, condition=None):

    if condition and type(condition) is not dict:
        raise TypeError('Condition must be dict')
    if condition:
        curs =  inv_db[table_name].aggregate([ {'$match':condition}, {'$sample':{'size':int(size)} } ] )
    else:
        curs =  inv_db[table_name].aggregate([{'$sample':{'size':int(size)}}])
    return list(curs)
