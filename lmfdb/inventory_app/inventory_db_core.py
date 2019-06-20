import inventory_helpers as ih
import lmfdb_inventory as inv
import datetime as dt
from lmfdb.utils import comma
from lmfdb.backend.database import db

#Table creation routines -------------------------------------------------------------

def get_db_id(name):
    """ Get database id by name

    name -- Name of db to retrieve
    """

    table_to_search = "inv_dbs"
    exists_at = db[table_to_search].search({'name':name}, limit=1, projection=3)
    if len(exists_at) > 0:
        _id = exists_at[0]['_id']
    else:
        _id = 0
    return {'err':False, 'id':_id, 'exist':(len(exists_at)>0)}

def get_coll_id(db_id, name):
    """ Get collection id by name.

    db_id -- ID of the database this connection is in
    name -- Name of collection to retrieve
    """

    table_to_search = "inv_tables"
    exists_at = db[table_to_search].search({'db_id':db_id, 'name':name}, limit=1)
    if len(exists_at) > 0:
        _id = exists_at[0]['_id']
    else:
        _id = 0

    return {'err':False, 'id':_id, 'exist':(len(exists_at)>0)}

def get_db_name(db_id):
    """Get db name from db id"""

    table_to_search = "inv_dbs"
    exists_at = db[table_to_search].search({'_id':db_id}, limit=1)
    if len(exists_at) > 0:
        name = exists_at[0]['name']
    else:
        name = ''
    return {'err':False, 'name':name, 'exist':(len(exists_at)>0)}

def get_coll_name(coll_id):
    """ Get collection name from id.

    coll_id -- ID of collection to retrieve
    """

    table_to_search = "inv_tables"
    exists_at = db[table_to_search].search({'_id':coll_id}, limit=1)
    if len(exists_at) > 0:
        name = exists_at[0]['name']
    else:
        name = ''
    return {'err':False, 'name':name, 'exist':(len(exists_at)>0)}

def get_db(name):
    """ Get database record by name """

    table_to_search = "inv_dbs"
    exists_at = db[table_to_search].search({'name':name}, limit=1, projection=3)
    if len(exists_at) > 0:
        try:
            _id = exists_at[0]['_id']
        except:
            #Happens if record is broken - shouldn't be
            _id = -1
        data = exists_at[0]
        err = False
    else:
        _id = -1
        data = None
        err = True

    return {'err':err, 'id':_id, 'exist':(len(exists_at)>0), 'data':data}

def set_db(name, nice_name):
    """ Insert a new DB with given name and optional nice name (defaults to equal name), or return id if this exists. """
    existing = get_db(name)
    if not existing['exist']:
        # This is completely absurd, but the data in the DB are so badly arranged that this is the simplest fix
        # The actual id column is completely useless, and the _id isn't auto incrementing, so we'll just have to
        # hack around it
        a=list(db['inv_dbs'].search({}, projection='_id'))
        next_id = max(a) + 1
        db['inv_dbs'].insert_many([{'name':name, 'nice_name':nice_name, '_id':next_id}])

    db_data = get_db(name)
    return db_data.pop('data')

def update_db(db_id, name=None, nice_name=None):
    """"Update DB name or nice_name info by db id"""

    #Check db exists with given id and get record for it
    rec_find = list(db['inv_dbs'].search({'_id':db_id}))
    if not rec_find:
        return {'err':True, 'id':db_id, 'exist':False}

    rec_find = rec_find[0]
    rec_set = {}
    if name is not None:
        rec_set['name'] = name
    if nice_name is not None:
        rec_set['nice_name'] = nice_name
    db['inv_dbs'].update(rec_find, rec_set)
    return {'err':False, 'id':db_id, 'exist':True}

def get_coll(db_id, name):
    """Return a collection entry.

    db_id -- ID of db this collection is part of
    name -- Collection name to return
    """

    table_to_search = "inv_tables"
    exists_at = db[table_to_search].search({'name':name, 'db_id':db_id}, limit=1)
    if len(exists_at) > 0:
        _id = exists_at[0]['_id']
        data = exists_at[0]
        err = False
    else:
        _id = 0
        data = None
        err = True

    return {'err':err, 'id':_id, 'exist':(len(exists_at)>0), 'data':data}

def get_coll_by_id(id):
    """Return a collection entry.

    id -- ID of collection
    """
    table_to_search = "inv_tables"
    exists_at = db[table_to_search].search({'_id':id}, limit=1)
    if len(exists_at) > 0:
        _id = exists_at[0]['_id']
        data = exists_at[0]
        err = False
    else:
        _id = 0
        data = None
        err = True

    return {'err':err, 'id':_id, 'exist':(len(exists_at)>0), 'data':data}

def set_coll(db_id, name, nice_name, notes, info, status):
    """Create or update a collection entry.

    db_id -- ID of db this collection is part of
    name -- Collection name to update
    notes -- The collection's Notes
    info -- The collection's Info
    status -- Collection's status code
    """

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[1]:db_id, coll_fields[2]:name}
    rec_set = {}
    if nice_name is not None:
        rec_set[coll_fields[3]] = nice_name
    if notes is not None:
        rec_set[coll_fields[4]] = notes
    if info is not None:
        rec_set[coll_fields[5]] = info
    if status is not None:
        rec_set[coll_fields[7]] = status

    # This is completely absurd, but the data in the DB are so badly arranged that this is the simplest fix
    # The actual id column is completely useless, and the _id isn't auto incrementing, so we'll just have to
    # hack around it
    coll = get_coll(db_id, name)
    if not coll['exist']:
        a=list(db['inv_tables'].search({}, projection='_id'))
        next_id = max(a) + 1
        rec_set['_id'] = next_id

    return upsert_and_check(db['inv_tables'], rec_find, rec_set)

def update_coll(id, name=None, nice_name=None, status=None):
    """Update a collection entry. Collection must exist.

    id -- ID of collection

    Optional args:
    name -- new name for collection
    nice_name -- new nice_name for collection
    status -- status code
    """

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[0]:id}
    rec_set = {}
    if name is not None:
        rec_set[coll_fields[2]] = name
    if nice_name is not None:
        rec_set[coll_fields[3]] = nice_name
    if status is not None:
        rec_set[coll_fields[7]] = status
    if rec_set:
        return update_and_check(db['inv_tables'], rec_find, rec_set)
    else:
        return {'err':False, 'id':id, 'exist':True}

def update_coll_data(db_id, name, item, field, content):
    """Update a collection entry. Collection must exist.

    db_id -- ID of db this collection is part of
    item -- The collection info this specifies
    field -- The piece of information specified (for example, type, description, example)
    content -- The new value for field
    """

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[1]:db_id, coll_fields[2]:name}
    rec_set = {item+'.'+field:content}

    return update_and_check(db['inv_tables'], rec_find, rec_set)

def set_coll_scrape_date(coll_id, scrape_date):
    """Update the last scanned date for given collection"""

    try:
        assert(isinstance(scrape_date, dt.datetime))
    except:
        return {'err':True, 'id':0, 'exist':False}

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[0]:coll_id}
    rec_set = {coll_fields[6]:scrape_date}

    return update_and_check(db['inv_tables'], rec_find, rec_set)

def set_coll_status(coll_id, status):
    """Update the status code for given collection"""

    coll_fields = inv.ALL_STRUC.coll_ids[inv.STR_CONTENT]
    rec_find = {coll_fields[0]:coll_id}
    rec_set = {coll_fields[7]:status}

    return update_and_check(db['inv_tables'], rec_find, rec_set)

def get_field(coll_id, name, type='auto'):
    """ Return a fields entry.

    coll_id -- ID of collection field belongs to
    name -- The lmfdb key to fetch
    type -- Specifies human or autogenerated table
    """

    table_to_search = "inv_fields_"+type
    exists_at = db[table_to_search].search({'name':name, 'table_id':coll_id}, limit=1)
    if len(exists_at) > 0:
        _id = exists_at[0]['_id']
        data = exists_at[0]
        err = False
    else:
        _id = 0
        data = None
        err = True

    return {'err':err, 'id':_id, 'exist':(len(exists_at)>0), 'data':data}

def set_field(coll_id, name, data, type='auto'):
    """ Add or update a fields entry.

    coll_id -- ID of collection field belongs to
    name -- The lmfdb key this describes
    data -- Collection data ({field: content, ...} formatted)
    type -- Specifies human or autogenerated table
    """
    #fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}

    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:name}
    data = ih.null_all_empty_fields(data)
    rec_set = {fields_fields[3]:data}

    result = upsert_and_check(db['inv_fields_'+type], rec_find, rec_set)
    # Now generate and set the sequenctial _id until we can
    # refactor the data properly
    if not result['exist'] or result['id'] == -1:
        a=list(db['inv_fields_'+type].search({}, projection='_id'))
        next_id = max(a) + 1
        rec_set['_id'] = next_id
    db['inv_fields_'+type].update(rec_find, rec_set, restat=False)

def create_field(coll_id, name, type='auto'):
    """ Add a blank fields entry IFF it doesen't exist.

    coll_id -- ID of collection field belongs to
    name -- The lmfdb key this describes
    type -- Specifies human or autogenerated table
    """

    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:name}

    record = list(db['inv_fields_'+type].search(rec_find, projection='_id'))
    rec_set = rec_find
    rec_set['data'] = {'type':None, 'example':None, 'description':None}
    if not record:
        result = upsert_and_check(db['inv_fields_'+type], rec_find, rec_set)
        # Now generate and set the sequenctial _id until we can
        # refactor the data properly
        if not result['exist'] or result['id'] == -1:
            a=list(db['inv_fields_'+type].search({}, projection='_id'))
            next_id = max(a) + 1
            rec_set = rec_find
            rec_set['_id'] = next_id
            db['inv_fields_'+type].update(rec_find, rec_set, restat=False)


def update_field(coll_id, item, field, content, type='auto'):
    """ Update an existing field entry. Item must exist

    coll_id -- ID of collection field belongs to
    item -- The lmfdb key this describes
    field -- The piece of information specified (for example, type, description, example)
    content -- The new value for field
    type -- Specifies human or autogenerated table
    """
    #fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}

    fields_fields = inv.ALL_STRUC.get_fields(type)[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id, fields_fields[2]:item}
    dat = list(db['inv_fields_'+type].search(rec_find))[0][fields_fields[3]]
    dat[field] = content
    rec_set = {fields_fields[3]:dat}

    return update_and_check(db['inv_fields_'+type], rec_find, rec_set)

def add_index(coll_id, index_data):
    """Add an index entry for given coll_id"""
    #indexes = {STR_NAME : 'indexes', STR_CONTENT :['_id', 'name', 'coll_id', 'keys']}

    indexes_fields = inv.ALL_STRUC.indexes[inv.STR_CONTENT]
    record = {indexes_fields[1]:index_data['name'], indexes_fields[2]:coll_id}
    #If record exists, just return its ID
    exists_at = db['inv_indices'].lookup(record)
    if exists_at is not None:
        _id = exists_at['_id']
    else:
        record[indexes_fields[2]] = coll_id
        record[indexes_fields[3]] = index_data['keys']
        try:
            upsert_and_check(db['inv_indices'], {}, record)
        except:
            return {'err':True, 'id':0, 'exist':False}

    return {'err':False, 'id':_id, 'exist':(exists_at is not None)}

def get_all_indices(coll_id):
    """ Return a list of all indices for coll_id.

    coll_id -- ID of collection field belongs to
    """
    #indexes = {STR_NAME : 'indexes', STR_CONTENT :['_id', 'name', 'coll_id', 'keys']}

    table_to_search = "inv_indices"

    indexes_fields = inv.ALL_STRUC.indexes[inv.STR_CONTENT]
    rec_find = {indexes_fields[2]:coll_id}
    try:
        data = list(db[table_to_search].search(rec_find))
        return {'err':False, 'id':-1, 'exist':True, 'data':data}
    except:
        return {'err':True, 'id':0, 'exist':True, 'data':None}

def upsert_and_check(table, rec_find, rec_set):
    """Upsert (insert/update) into given coll

    table -- table to upsert into (not name)
    rec_find -- query to identify possibly existing record
    rec_set -- new data to set

    """
    try:
        result = table.upsert(rec_find, rec_set)
        upserted = result[0]
        if result[0]:
            #Upsert doesn't allow returning data, so search now...
            dat = list(table.search({'id':result[1]}))
            _id = dat[0]['_id']
        else:
            _id = -1
    except:
        return {'err':True, 'id':0, 'exist':False}
    return {'err':False, 'id':_id, 'exist':(not upserted)}

def update_and_check(table, rec_find, rec_set):
    """Update record in given coll

    table -- table to upsert into
    rec_find -- query to identify existing record
    rec_set -- new data to set

    """

    try:
        table.update(rec_find, rec_set, restat=False)
        #Update returns nothing, so we have to search now...
        # Yes the update routine can have butchered the data we gave it...
        result = list(table.search(rec_find))
        if len(result) == 0:
            raise(ValueError)
    except:
        return {'err':True, 'id':-1, 'exist':False}
    return {'err':False, 'id':result[0]['_id'], 'exist':True}

#End table creation routines -------------------------------------------------------------

#Ops stuff ------------------------------------------------------------------------------

def search_ops_table(rec_find):

    table_to_search = "inv_ops"
    try:
        result = db[table_to_search].search(rec_find)
        return result
    except:
        return []

def add_to_ops_table(rec_set):

    table_to_change = "inv_ops"
    try:
        # TODO Interface seems to lack any way of inserting a single record????
        db[table_to_change].insert_many([rec_set])
        return {'err':False}
    except:
        return {'err':True}

#End ops ---------------------------------------------------------------------------------

#Table sync ------------------------------------------------------------------------------

def trim_human_table(inv_db_toplevel, db_id, coll_id):
    """Trims elements from the human-readable table which do not match the canonical structure table

    inv_db_toplevel -- connection to LMFDB inventory database (no table)
    db_id -- id of database to strip
    coll_id -- id of collection to strip
    """
    invalidated_keys = []
    a_tbl = db['inv_fields_auto']
    h_tbl = db['inv_fields_human']

    fields_fields = inv.ALL_STRUC.get_fields('human')[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id}
    human_cursor = h_tbl.search(rec_find)
    for record in human_cursor:
        rec_find = {fields_fields[1]:coll_id, fields_fields[2]: record['name']}
        auto_record = a_tbl.search(rec_find)
        if auto_record is None:
            invalidated_keys.append({'name':record['name'], 'data':record['data']})
            h_tbl.delete(record)
    return invalidated_keys

def complete_human_table(inv_db_toplevel, db_id, coll_id):
    """Add missing entries into human-readable table. 'Missing' means anything
    present in the auto-generated data but not in the human, AND adds keys present only in the
    human data in also (currently, description)

    inv_db_toplevel -- connection to LMFDB inventory database (no table)
    db_id -- id of database to strip
    coll_id -- id of collection to strip
    """
    h_db = inv_db_toplevel[inv.ALL_STRUC.fields_human[inv.STR_NAME]]
    a_db = inv_db_toplevel[inv.ALL_STRUC.fields_auto[inv.STR_NAME]]
    fields_fields = inv.ALL_STRUC.get_fields('human')[inv.STR_CONTENT]
    rec_find = {fields_fields[1]:coll_id}
    auto_cursor = a_db.search(rec_find)
    for record in auto_cursor:
        rec_find = {fields_fields[1]:coll_id, fields_fields[2]: record['name']}
        human_record = h_db.search(rec_find)
        #Should never be two records with same coll-id and name
        alter = False
        try:
            rec_set = human_record['data']
        except:
            rec_set = {}
        for field in inv.base_editable_fields:
            try:
                a = human_record['data'][field]
                assert(a or not a) #Use a for Pyflakes, but we don't care what is is
            except:
                rec_set[field] = None
                alter = True
        #Rec_set is now original data plus any missing base_editable_fields
        if alter:
            #Creates if absent, else updates with missing fields
            set_field(coll_id, record['name'], rec_set, type='human')

def cleanup_records(coll_id, record_list):
    """Trims records for this collection that no longer exist

    coll_id -- id of collection to strip
    record_list -- List of all existing records
    """
    table_to_search = "inv_records"

    try:
        records_fields = inv.ALL_STRUC.record_types[inv.STR_CONTENT]
        rec_find = {records_fields[1]:coll_id}
        db_record_list = db[table_to_search].search(rec_find)
        extant_hashes = []
        for key in record_list:
            item = record_list[key]
            extant_hashes.append(ih.hash_record_schema(item['schema']))
        for item in db_record_list:
            if item['hash'] not in extant_hashes:
                db[table_to_search].delete(item)

    except:
        return {'err':True}

#End table sync --------------------------------------------------------------------------
#Assorted helper access functions --------------------------------------------------------

def count_colls(db_id):
    """Count collections with given db_id
    """

    table_to_search = "inv_tables"
    info = {}
    db[table_to_search].search({'db_id':db_id}, info=info)
    return info['number']

def get_all_colls(db_id=None):
    """Fetch all collections with given db_id
    """

    table_to_search = "inv_tables"
    if db_id is not None:
        values = db[table_to_search].search({'db_id':db_id}, count_only=True)
    else:
        values = db[table_to_search].search(count_only=True)
    return list(values)

def count_records_and_types(coll_id, as_string=False):
    """ Count the number of record types in given collection.
    If as_string is true, return a formatted string pair rather than a pair of ints
    """
    counts = (-1, -1)
    try:
        tbl = 'inv_records'
        recs = list(db[tbl].search({'table_id': coll_id}))
        n_types = len(recs)
        n_rec = sum([rec['count'] for rec in recs])
        counts = (n_rec, n_types)
    except:
        pass
    if as_string:
        counts = (comma(counts[0]), comma(counts[1]))
    return counts
#End assorted helper access functions ----------------------------------------------------
