import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import datetime as dt
#Table creation routines -------------------------------------------------------------

def get_db_id(inv_db, name):
    """ Get database id by name

    inv_db -- Connection to LMFDB inventory database
    name -- Name of db to retrieve
    """

    try:
        table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+ str(e))
        return {'err':True, 'id':0, 'exist':False}

    db_fields = inv.ALL_STRUC.db_ids[inv.STR_CONTENT]
    record = {db_fields[1]:name}
    #If record exists, just return its ID
    exists_at = coll.find_one(record)
    if exists_at is not None:
        _id = exists_at['_id']
    else:
        _id = 0
    return {'err':False, 'id':_id, 'exist':(exists_at is not None)}

def get_coll_id(inv_db, db_id, name):
    """ Get collection id by name.

    inv_db -- Connection to LMFDB inventory database
    db_id -- ID of the database this connection is in
    name -- Name of collection to retrieve
    """

    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    record = {coll_fields[1]:db_id, coll_fields[2]:name}
    exists_at = coll.find_one(record)
    if exists_at is not None:
        _id = exists_at['_id']
    else:
        _id = 0
    return {'err':False, 'id':_id, 'exist':(exists_at is not None)}

def get_db(inv_db, name):
    """ Get database record by name """

    try:
        table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+ str(e))
        return {'err':True, 'id':0, 'exist':False}

    db_fields = inv.ALL_STRUC.db_ids[inv.STR_CONTENT]
    record = {db_fields[1]:name}
    data = coll.find_one(record)
    if data is None:
        inv.log_dest.error("Error getting db "+str(name)+' ' +str(e))
        return {'err':True, 'id':0, 'exist':False, 'data':None}

    return {'err':False, 'id':data['_id'], 'exist':True, 'data':data}

def set_db(inv_db, name, nice_name):
    """ Insert a new DB with given name and optional nice name (defaults to equal name), or return id if this exists. """
    try:
        table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    db_fields = inv.ALL_STRUC.db_ids[inv.STR_CONTENT]
    record = {db_fields[1]:name}
    #If record exists, just return its ID
    exists_at = coll.find_one(record)
    if exists_at is not None:
        inv.log_dest.debug("DB exists")
        _id = exists_at['_id']
    else:
        record[db_fields[2]] = nice_name
        try:
            _id = coll.insert(record)
        except Exception as e:
            inv.log_dest.error("Error inserting new record" +str(e))
            return {'err':True, 'id':0, 'exist':False}

    return {'err':False, 'id':_id, 'exist':(exists_at is not None)}

def update_db(inv_db, db_id, name=None, nice_name=None):
    """"Update DB name or nice_name info by db id"""
    try:
        table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    db_fields = inv.ALL_STRUC.db_ids[inv.STR_CONTENT]
    #Look up by Id
    record = {db_fields[0]:db_id}
    exists_at = coll.find_one(record)

    if exists_at is None:
        inv.log_dest.debug("DB does not exist")
        return {'err':True, 'id':0, 'exist':False}

    else:
        rec_set = {}
        if name is not None:
            rec_set[db_fields[1]] = name
        if nice_name is not None:
            rec_set[db_fields[2]] = nice_name
        if rec_set:
            return update_and_check(inv_db[table_name], record, rec_set)
        else:
            return {'err':False, 'id':db_id, 'exist':True}

def get_coll(inv_db, db_id, name):
    """Return a collection entry.

    inv_db -- Connection to LMFDB inventory database
    db_id -- ID of db this collection is part of
    name -- Collection name to return
    """
    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False, 'data':None}
    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[1]:db_id, coll_fields[2]:name}

    try:
        data = coll.find_one(rec_find)
        return {'err':False, 'id':data['_id'], 'exist':True, 'data':data}
    except Exception as e:
        inv.log_dest.error("Error getting data "+str(e))
        return {'err':True, 'id':0, 'exist':True, 'data':None}

def set_coll(inv_db, db_id, name, nice_name, notes, info):
    """Create or update a collection entry.

    inv_db -- Connection to LMFDB inventory database
    db_id -- ID of db this collection is part of
    name -- Collection name to update
    notes -- The collection's Notes
    info -- The collection's Info
    """
    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[1]:db_id, coll_fields[2]:name}
    rec_set = {}
    if nice_name is not None:
        rec_set[coll_fields[3]] = nice_name
    if notes is not None:
        rec_set[coll_fields[4]] = notes
    if info is not None:
        rec_set[coll_fields[5]] = info

    return upsert_and_check(coll, rec_find, rec_set)

def update_coll(inv_db, id, name=None, nice_name=None):
    """Update a collection entry. Collection must exist.

    inv_db -- Connection to LMFDB inventory database
    id -- ID of collection

    Optional args:
    name -- new name for collection
    nice_name -- new nice_name for collection
    """

    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}
    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[0]:id}
    rec_set = {}
    if name is not None:
        rec_set[coll_fields[2]] = name
    if nice_name is not None:
        rec_set[coll_fields[3]] = nice_name
    if rec_set:
        return update_and_check(coll, rec_find, rec_set)
    else:
        return {'err':False, 'id':id, 'exist':True}

def update_coll_data(inv_db, db_id, name, item, field, content):
    """Update a collection entry. Collection must exist.

    inv_db -- Connection to LMFDB inventory database
    db_id -- ID of db this collection is part of
    item -- The collection info this specifies
    field -- The piece of information specified (for example, type, description, example)
    content -- The new value for field
    """

    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}
    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[1]:db_id, coll_fields[2]:name, item+'.'+field:{"$exists":True}}
    rec_set = {item+'.'+field:content}

    return update_and_check(coll, rec_find, rec_set)

def set_coll_scan_date(inv_db, coll_id, scan_date):
    """Update the last scanned date for given collection"""

    try:
        table_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}
    try:
        assert(isinstance(scan_date, dt.datetime))
    except Exception as e:
        inv.log_dest.error("Invalid scan_date, expected datetime.datetime "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[0]:coll_id}
    rec_set = {coll_fields[6]:scan_date}

    return update_and_check(coll, rec_find, rec_set)

def get_field(inv_db, coll_id, name, type='auto'):
    """ Return a fields entry.

    inv_db -- LMFDB connection to inventory db
    coll_id -- ID of collection field belongs to
    name -- The lmfdb key to fetch
    type -- Specifies human or autogenerated table
    """
    #fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}
    try:
        table_name = inv.ALL_STRUC.get_fields(type)[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+ str(e))
        return {'err':True, 'id':0, 'exist':False}
    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:name}
    try:
        data = coll.find_one(rec_find)
        return {'err':False, 'id':data['_id'], 'exist':True, 'data':data}
    except Exception as e:
        inv.log_dest.error("Error getting data "+str(e))
        return {'err':True, 'id':0, 'exist':True, 'data':None}

def set_field(inv_db, coll_id, name, data, type='auto'):
    """ Add or update a fields entry.

    inv_db -- LMFDB connection to inventory db
    coll_id -- ID of collection field belongs to
    name -- The lmfdb key this describes
    data -- Collection data ({field: content, ...} formatted)
    type -- Specifies human or autogenerated table
    """
    #fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}
    try:
        table_name = inv.ALL_STRUC.get_fields(type)[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+ str(e))
        return {'err':True, 'id':0, 'exist':False}

    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:name}
    data = ih.null_all_empty_fields(data)
    rec_set = {fields_fields[3]:data}

    return upsert_and_check(coll, rec_find, rec_set)

def update_field(inv_db, coll_id, item, field, content, type='auto'):
    """ Update an existing field entry. Item must exist

    inv_db -- LMFDB connection to inventory db
    coll_id -- ID of collection field belongs to
    item -- The lmfdb key this describes
    field -- The piece of information specified (for example, type, description, example)
    content -- The new value for field
    type -- Specifies human or autogenerated table
    """
    #fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}
    try:
        table_name = inv.ALL_STRUC.get_fields(type)[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection " + str(e))
        return {'err':True, 'id':0, 'exist':False}

    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:item, fields_fields[3]+'.'+field:{"$exists":True}}
    rec_set = {fields_fields[3]+'.'+field: content}

    return update_and_check(coll, rec_find, rec_set)

def set_record(inv_db, coll_id, data, type='auto'):
    """ Add or update a record entry.

    inv_db -- LMFDB connection to inventory db
    coll_id -- ID of collection record belongs to
    data -- Data for this record. If type=auto, must be dict with 'schema' and 'count' fields. If type=human, must contain 'hash' giving the hashed schema, and can also contain a 'name' entry which itself contains 'name' and optionally 'description'
    type -- Type of record (dictates expected data format)
    """
    #record_types = {STR_NAME : 'records', STR_CONTENT :['_id', 'coll_id', 'hash', 'name', 'descrip', 'fields', 'count']}

    try:
        table_name = inv.ALL_STRUC.record_types[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0, 'exist':False}

    records_fields = inv.ALL_STRUC.record_types[inv.STR_CONTENT]
    if type == 'auto':
        #Generate the hash
        hash = ih.hash_record_schema(data['schema'])
        rec_find = {records_fields[1]:coll_id, records_fields[2]:hash}
        rec_set = {records_fields[5]:data['schema'], records_fields[6]:data['count']}
        return upsert_and_check(coll, rec_find, rec_set)
    elif type == 'human':
        #Added data for records is just a "name" field
        human_data = data['name']
        if 'description' not in human_data:
            human_data['description'] = ''
        rec_find = {records_fields[1]:coll_id, records_fields[2]:data['hash']}
        rec_set = {records_fields[3]:human_data['name'], records_fields[4]:human_data['description']}
        return upsert_and_check(coll, rec_find, rec_set)

def upsert_and_check(coll, rec_find, rec_set):
    """Upsert (insert/update) into given coll

    coll -- collection to upsert into
    rec_find -- query to identify possibly existing record
    rec_set -- new data to set

    """
    #Either insert, or update existing and return results
    try:
        result = coll.find_and_modify(query=rec_find, update={"$set":rec_set}, upsert=True, full_response=True)
        if 'upserted' in result['lastErrorObject']:
            _id = result['lastErrorObject']['upserted']
        elif 'value' in result:
            _id = result['value']['_id']
    except Exception as e:
        inv.log_dest.error("Error inserting new record"+ str(e)) #TODO this is the wrong message
        return {'err':True, 'id':0, 'exist':False}
    return {'err':False, 'id':_id, 'exist':(not 'upserted' in result['lastErrorObject'])}

def update_and_check(coll, rec_find, rec_set):
    """Update record in given coll

    coll -- collection to upsert into
    rec_find -- query to identify existing record
    rec_set -- new data to set

    """

    try:
        result = coll.find_and_modify(query=rec_find, update={"$set":rec_set}, upsert=False, full_response=True)
        _id = result['value']['_id']
    except Exception as e:
        print e
        inv.log_dest.error("Error updating record"+ str(e)) #TODO this is the wrong message
        return {'err':True, 'id':0, 'exist':False}
    return {'err':False, 'id':_id, 'exist':True}


#End table creation routines -------------------------------------------------------------

#Table sync ------------------------------------------------------------------------------

def trim_human_table(inv_db_toplevel, db_id, coll_id):
    """Trims elements from the human-readable table which do not match the canonical structure table

    inv_db_toplevel -- connection to LMFDB inventory database (no table)
    db_id -- id of database to strip
    coll_id -- id of collection to strip
    """
    invalidated_keys = []
    h_db = inv_db_toplevel[inv.ALL_STRUC.fields_auto[inv.STR_NAME]]
    a_db = inv_db_toplevel[inv.ALL_STRUC.fields_human[inv.STR_NAME]]
    fields_fields = inv.ALL_STRUC.get_fields('human')[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id}
    human_cursor = h_db.find(rec_find)
    for record in human_cursor:
        rec_find = {fields_fields[1]:coll_id, fields_fields[2]: record['name']}
        auto_record = a_db.find_one(rec_find)
        if auto_record is None:
            invalidated_keys.append({'name':record['name'], 'data':record['data']})
            h_db.remove(record)
    return invalidated_keys


#End table sync --------------------------------------------------------------------------
