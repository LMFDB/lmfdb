
import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as invc
import datetime

#TODO this should log to its own logger
#Routines to upload data from reports scan into inventory DB

MAX_SZ = 10000

def upload_scraped_data(structure_data, uid):
    """Main entry point for scraper tool

    structure_data -- the json data
    uid -- string uuid from scraper process start call
    """

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    inv.log_dest.warning('In upload with '+str(uid))
    upload_scraped_inventory(inv_db, structure_data, uid)

def upload_scraped_inventory(db, structure_dat, uid):
    """Upload a json structure document and store any oprhans

        db -- LMFDB connection to inventory database
        structure_dat -- JSON document containing all db/collections to upload
        uid -- UID string for uploading process
    """

    inv.log_dest.info("_____________________________________________________________________________________________")
    n_dbs = len(structure_dat.keys())
    progress_tracker = 0

    for db_name in structure_dat:
        progress_tracker += 1
        inv.log_dest.info("Uploading " + db_name+" ("+str(progress_tracker)+" of "+str(n_dbs)+')')
        invc.set_db(db, db_name, db_name)

        for coll_name in structure_dat[db_name]:
            inv.log_dest.info("    Uploading collection "+coll_name)
            orphaned_keys = upload_collection_structure(db, db_name, coll_name, structure_dat, fresh=False)
            if len(orphaned_keys) != 0:
                db_id = idc.get_db_id(db, db_name)
                coll_id = idc.get_coll_id(db, db_id['id'], coll_name)
                store_orphans(db, db_id['id'], coll_id['id'], uid, orphan_document)

def upload_collection_structure(db, db_name, coll_name, structure_dat, fresh=False):
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
        db_entry = invc.get_db_id(db, db_name)
        if not db_entry['exist']:
            #All dbs should have been added from the struc: if not is error
            inv.log_dest.error("ERROR: No inventory DB entry "+ db_name)
            inv.log_dest.error("Cannot add descriptions")
            return

        _c_id = invc.get_coll_id(db, db_entry['id'], coll_name)
        if not _c_id['exist']:
	    #Collection doesn't exist, create it
            _c_id = invc.set_coll(db, db_entry['id'], coll_name, coll_name,  {'description':None}, dummy_info, 0)
        else:
	    #Delete existing auto-table entries (no collection => no entries)
           delete_collection_data(db, _c_id['id'], tbl='auto')
        try:
            scrape_date = datetime.datetime.strptime(structure_dat[db_name][coll_name]['scrape_date'], '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            inv.log_dest.info("Scrape date parsing failed "+str(e))
            scrape_date = datetime.datetime.min
        invc.set_coll_scrape_date(db, _c_id['id'], scrape_date)

    except Exception as e:
        inv.log_dest.error("Failed to refresh collection (db, coll or scrape data) "+str(e))

    try:
        for field in coll_entry['fields']:
            inv.log_dest.info("            Processing "+field)
            invc.set_field(db, _c_id['id'], field, coll_entry['fields'][field])
        for record in coll_entry['records']:
            inv.log_dest.info("            Processing record "+str(record))
            invc.set_record(db, _c_id['id'], coll_entry['records'][record])
        #Cleanup any records which no longer exist
        orph_records = invc.cleanup_records(db, _c_id['id'], coll_entry['records'])

        inv.log_dest.info("            Processing indices")
        upload_indices(db, _c_id['id'], coll_entry['indices'])

    except Exception as e:
        inv.log_dest.error("Failed to refresh collection entries "+str(e))

    orphaned_keys = []
    if not fresh:
        try:
	    #Trim any human table keys which are now redundant
            orphaned_keys = invc.trim_human_table(db, db_entry['id'], _c_id['id'])
        except Exception as e:
            inv.log_dest.error("Failed trimming table "+str(e))
    else:
        #Ensure everything mandatory is present in human table
        try:
            invc.complete_human_table(db, db_entry['id'], _c_id['id'])
        except Exception as e:
            inv.log_dest.error("Failed padding table "+str(e))

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
    except Exception as e:
        inv.log_dest.error("Failed to get db or coll id "+str(e))
        return {'err':True, 'mess':'Failed to get db or coll'} #Probably should rethrow
    try:
        data = structure_dat[db_name][coll_name]['indices']
        #err = upload_indices(db, coll_info['id'], data)
        upload_indices(db, coll_info['id'], data)
        # TODO rethrow if err
    except Exception as e:
        inv.log_dest.error("Failed to upload index "+str(e))
        return {'err':True, 'mess':'Failed to upload'}
    return {'err':False, 'mess':''}

def upload_indices(db, coll_id, data):
    """Upload indices data for given collection"""

    for item in data:
        invc.add_index(db, coll_id, data[item])

#End upload routines -----------------------------------------------------------------

#Table removal -----------------------------------------------------------------------
def delete_contents(db, tbl_name, check=True):
    """Delete contents of tbl_name """

    if not inv.validate_mongodb(db) and check:
        raise TypeError("db does not match Inventory structure")
        return
    #Grab the possible table names
    tbl_names = inv.get_inv_table_names()
    if tbl_name in tbl_names:
        try:
            db[tbl_name].remove()
        except Exception as e:
            inv.log_dest.error("Error deleting from "+ tbl_name+' '+ str(e)+", dropping")
            #Capped tables, e.g rollback, can only be dropped, so try that
	    try:
		db[tbl_name].drop()
            except Exception as e:
                inv.log_dest.error("Error dropping "+ tbl_name+' '+ str(e))

def delete_table(db, tbl_name, check=True):
    """Delete tbl_name (must be empty) """

    if not inv.validate_mongodb(db) and check:
        raise TypeError("db does not match Inventory structure")
        return
    #Grab the possible table names
    tbl_names = inv.get_inv_table_names()
    if tbl_name in tbl_names:
        try:
	    assert(db[tbl_name].find_one() is None) #Check content is gone
            db[tbl_name].drop()
        except Exception as e:
            inv.log_dest.error("Error dropping "+ tbl_name+' '+ str(e))
            #Capped tables, e.g rollback, can only be dropped, so try that

def unsafe_delete_all_tables(db):
    """Delete inventory tables by name without checking this really is the inventory db
    use if inv.validate_mongod fails and you know some table is missing and you are sure db is the inventory"""

    tbls = inv.get_inv_table_names()
    for tbl in tbls:
        try:
            delete_contents(db, tbl, check=False)
            delete_table(db, tbl, check=False)
        except Exception as e:
            inv.log_dest.error("Error deleting "+ tbl + ' ' +str(e))

def delete_all_tables(db):
    """ Delete all tables specified by inv Note that other names can be present, see inv.validate_mongod"""

    if not inv.validate_mongodb(db):
        raise TypeError("db does not match Inventory structure")
        return
    tbls = inv.get_inv_table_names()
    for tbl in tbls:
        try:
            delete_contents(db, tbl)
            delete_table(db, tbl)
        except Exception as e:
            inv.log_dest.error("Error deleting "+ tbl + ' ' +str(e))

def delete_collection_data(inv_db, coll_id, tbl):
    """Clean out the data for given collection id
      Removes all entries for coll_id in auto, human or records
    """
    try:
        table_dat = inv.ALL_STRUC.get_table(tbl)
        fields_tbl = table_dat[inv.STR_NAME]
        fields_fields = table_dat[inv.STR_CONTENT]

        rec_find = {fields_fields[1]:coll_id}
        inv_db[fields_tbl].remove(rec_find)
    except Exception as e:
        inv.log_dest.error("Error removing fields " + str(e))

def delete_by_collection(inv_db, db_name, coll_name):
    """Remove collection entry and all its fields"""

    if not inv.validate_mongodb(inv_db):
        raise TypeError("db does not match Inventory structure")
        return

    try:
        _db_id = invc.get_db_id(inv_db, db_name)
        _c_id = invc.get_coll_id(inv_db, _db_id['id'], coll_name)
    except Exception as e:
        inv.log_dest.error("Error getting collection " + str(e))
        return {'err':True, 'id':0, 'exist':False}

    #Remove fields entries matching _c_id
    delete_collection_data(inv_db, _c_id['id'], tbl='auto')
    delete_collection_data(inv_db, _c_id['id'], tbl='human')
    delete_collection_data(inv_db, _c_id['id'], tbl='records')

    try:
        inv_db[inv.ALL_STRUC.coll_ids[inv.STR_NAME]].remove({'_id':_c_id['id']})
    except Exception as e:
        inv.log_dest.error("Error removing collection " + str(e))


#End table removal -----------------------------------------------------------------------

#Rollback table handling
def recreate_rollback_table(inv_db, sz):
    """Create anew the table for edit rollbacks

    Arguments :
    inv_db -- LMFDB db connection to inventory table
    sz -- Max size of the capped table
    If table exists, it is now deleted
    """
    try:
        table_name = inv.ALL_STRUC.rollback_human[inv.STR_NAME]
        coll = inv_db[table_name]
    except Exception as e:
        inv.log_dest.error("Error getting collection "+str(e))
        return {'err':True, 'id':0}
    #fields = inv.ALL_STRUC.rollback_human[inv.STR_CONTENT]

    try:
        coll.drop()
    except:
        #TODO Do something useful here?
        pass

    inv_db.create_collection(table_name, capped=True, size=sz)

#-----Orphan handling Functions --------------

def summarise_orphans(orphan_data):

    return orphan_data
