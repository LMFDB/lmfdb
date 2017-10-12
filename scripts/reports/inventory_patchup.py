#A collection of functions usesd to patch up uploads which had bugs

def amend_collection_info(inv_db):
    """ Fixes missing or empty string collection Notes and Info for every db
    """

    a=list(inv_db.collection_ids.find())
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
