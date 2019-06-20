import lmfdb_inventory as inv
import inventory_db_core as invc
import inventory_live_data as ild
import datetime
from lmfdb import db as lmfdb_db

#Routines to upload data from reports scan into inventory DB

MAX_SZ = 10000

def upload_scraped_data(structure_data, uid):
    """Main entry point for scraper tool

    structure_data -- the json data
    uid -- string uuid from scraper process start call
    """

    upload_scraped_inventory(structure_data, uid)

def upload_scraped_inventory(structure_dat, uid):
    """Upload a json structure document and store any oprhans

        structure_dat -- JSON document containing all db/collections to upload
        uid -- UID string for uploading process
    """

    n_dbs = len(structure_dat.keys())
    progress_tracker = 0

    for db_name in structure_dat:
        progress_tracker += 1
        invc.set_db(db_name, db_name)

        for coll_name in structure_dat[db_name]:
            orphaned_keys = upload_collection_structure(db_name, coll_name, structure_dat, fresh=False)
            if len(orphaned_keys) != 0:
                db_id = invc.get_db_id(db_name)
                coll_id = invc.get_coll_id(db_id['id'], coll_name)
                ild.store_orphans(db_id['id'], coll_id['id'], uid, orphaned_keys)
    return n_dbs

def upload_collection_structure(db_name, coll_name, structure_dat, fresh=False):
    """Upload the structure description for a single collection

    Any entered descriptions for keys which still exist are preserved.
    Removed or renamed keys will be returned for handling
    Collection is entry is created if it doesn't exist,
    in which case Notes and Info are filled with dummies
    db -- LMFDB connection to inventory database
    db_name -- Name of database this collection is in (MUST exist)
    coll_name -- Name of collection to upload
    structure_dat -- lmfdb db structure as json object
    """


    dummy_info = {} #Dummy per collection info, containing basic fields we want included
    for field in inv.info_editable_fields:
        dummy_info[field] = None
    try:
        coll_entry = structure_dat[db_name][coll_name]
        db_entry = invc.get_db_id(db_name)
        if not db_entry['exist']:
            #All dbs should have been added from the struc: if not is error
            return
        #Inventory data migration includes db name in collection name for some reason
        #Work around until we can fix the data
        full_coll_name = db_name +'_' + coll_name

        _c_id = invc.get_coll_id(db_entry['id'], full_coll_name)
        if not _c_id['exist']:
	    #Collection doesn't exist, create it
            _c_id = invc.set_coll(db_entry['id'], full_coll_name, full_coll_name,  {'description':None}, dummy_info, 0)
        else:
	    #Delete existing auto-table entries (no collection => no entries)
           delete_collection_data(_c_id['id'], tbl='auto')
        try:
            scrape_date = datetime.datetime.strptime(structure_dat[db_name][coll_name]['scrape_date'], '%Y-%m-%d %H:%M:%S.%f')
        except:
            scrape_date = datetime.datetime.min

        invc.set_coll_scrape_date(_c_id['id'], scrape_date)

    except:
        pass

    try:
        for field in coll_entry['fields']:
            invc.set_field(_c_id['id'], field, coll_entry['fields'][field])
            #Add any keys needed to human_table
            invc.create_field(_c_id['id'], field, 'human')

    except:
        pass

    orphaned_keys = []
    if not fresh:
        try:
	    #Trim any human table keys which are now redundant
            orphaned_keys = invc.trim_human_table(db_entry['id'], _c_id['id'])
        except:
            pass

    return orphaned_keys

def extract_specials(coll_entry):
    """ Split coll_entry into data and specials (notes, info etc) parts """
    notes = ''
    notes_entry = ''
    info = ''
    info_entry = ''
    for item in coll_entry:
        if item == inv.STR_NOTES:
            notes = item
            notes_entry = coll_entry[item]
        elif item == inv.STR_INFO:
            info = item
            info_entry = coll_entry[item]
    try:
        coll_entry.pop(notes)
        coll_entry.pop(info)
    except:
        pass
    return {inv.STR_NOTES:notes_entry, inv.STR_INFO: info_entry, 'data': coll_entry}

def upload_collection_indices(db, db_name, coll_name, structure_dat):
    """Extract index data and upload"""

    try:
        db_info = invc.get_db(db, db_name)
        coll_info = invc.get_coll(db, db_info['id'], coll_name)
    except:
        return {'err':True, 'mess':'Failed to get db or coll'} #Probably should rethrow
    try:
        data = structure_dat[db_name][coll_name]['indices']
        #err = upload_indices(db, coll_info['id'], data)
        upload_indices(db, coll_info['id'], data)
        # TODO rethrow if err
    except:
        return {'err':True, 'mess':'Failed to upload'}
    return {'err':False, 'mess':''}

def upload_indices(db, coll_id, data):
    """Upload indices data for given collection
    Note: this assumed the given data is complete, so first
    removes any existing indices before uploading.
    """
    delete_collection_data(db, coll_id, 'indices')
    for item in data:
        invc.add_index(db, coll_id, data[item])

#End upload routines -----------------------------------------------------------------

#Table removal -----------------------------------------------------------------------
def delete_contents(tbl_name, check=True):
    """Delete contents of tbl_name """
    # This should be named unsafe, but shouldn't bother re-doing the checks

    try:
        #TODO if keep, below should delete all records
        lmfdb_db[tbl_name].empty()
    except:
        pass

def delete_all_tables():
    """ Delete all tables specified by inv Note that other names can be present"""
    # TODO remove this completely???
    # TODO this should create the list of tables to delete and do any checking it can they are correct
    tbls = inv.get_inv_table_names()

    for tbl in tbls:
        # Any possible checking here
        pass

    for tbl in tbls:
        try:
            delete_contents(tbl)
        except:
            pass

def delete_collection_data(coll_id, tbl, dry_run=False):
    """Clean out the data for given collection id
      Removes all entries for coll_id in auto, human or records

      dry_run -- print items which would be deleted, but do nothing (debugging)
    """
    try:
        table_dat = inv.ALL_STRUC.get_table(tbl)
        fields_tbl = table_dat[inv.STR_NAME]
        fields_fields = table_dat[inv.STR_CONTENT]

        if tbl != 'indexes' and tbl != 'indices':
            rec_find = {fields_fields[1]:coll_id}
        else:
            rec_find = {fields_fields[2]:coll_id}

        if not dry_run:
            lmfdb_db[fields_tbl].delete(rec_find)
        else:
            print 'Finding '+str(rec_find)
            print 'Operation would delete:'
            curs = lmfdb_db[fields_tbl].search(rec_find)
            for item in curs:
                print item
    except:
        pass

def delete_by_collection(db_name, coll_name):
    """Remove collection entry and all its fields"""

    try:
        _db_id = invc.get_db_id(db_name)
        _c_id = invc.get_coll_id(_db_id['id'], coll_name)
    except:
        return {'err':True, 'id':0, 'exist':False}

    #Remove fields entries matching _c_id
    delete_collection_data(_c_id['id'], tbl='auto')
    delete_collection_data(_c_id['id'], tbl='human')
    delete_collection_data(_c_id['id'], tbl='records')

    try:
        lmfdb_db[inv.ALL_STRUC.coll_ids[inv.STR_NAME]].delete({'_id':_c_id['id']})
    except:
        pass

#End table removal -----------------------------------------------------------------------

#Rollback table handling
def recreate_rollback_table(sz):
    """Create anew the table for edit rollbacks

    Arguments :
    sz -- Max size of the capped table
    If table exists, it is now deleted
    """
    try:
        #TODO clearout rollbacks here
        pass
    except:
        #TODO Do something useful here?
        pass
    #TODO replace with a recreate of rollbacks
    #lmfdb_db.create_collection(table_name, capped=True, size=sz)

#-----Orphan handling Functions --------------

def summarise_orphans(orphan_data):

    return orphan_data
