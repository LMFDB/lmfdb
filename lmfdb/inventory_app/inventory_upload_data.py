import lmfdb_inventory as inv
import inventory_db_core as invc
import inventory_live_data as ild
import datetime
from lmfdb.db_backend import db

#TODO this should log to its own logger
#Routines to upload data from reports scan into inventory DB

MAX_SZ = 10000

upload_indices = None # not a global, just for pyflakes

def upload_scraped_data(structure_data, uid):
    """Main entry point for scraper tool

    structure_data -- the json data
    uid -- string uuid from scraper process start call
    """
    inv.log_dest.warning('In upload with '+str(uid))
    upload_scraped_inventory(structure_data, uid)

def upload_scraped_inventory(structure_dat, uid):
    """Upload a json structure document and store any oprhans

        structure_dat -- JSON document containing all db/tables to upload
        uid -- UID string for uploading process
    """

    inv.log_dest.info("_____________________________________________________________________________________________")
    n_dbs = len(structure_dat.keys())
    progress_tracker = 0

    for db_name in structure_dat:
        progress_tracker += 1
        inv.log_dest.info("Uploading "+db_name+" ("+str(progress_tracker)+" of "+str(n_dbs)+')')
        invc.set_db(db_name, db_name)

        for table_name in structure_dat[db_name]:
            inv.log_dest.info("    Uploading table "+table_name)
            orphaned_keys = upload_table_structure(db_name, table_name, structure_dat, fresh=False)
            if len(orphaned_keys) != 0:
                db_id = invc.get_db_id(db_name)
                table_id = invc.get_table_id(table_name)
                ild.store_orphans(db_id, table_id, uid, orphaned_keys)

def upload_table_structure(db_name, table_name, structure_dat, fresh=False):
    """Upload the structure description for a single table

    Any entered descriptions for keys which still exist are preserved.
    Removed or renamed keys will be returned for handling
    Table entry is created if it doesn't exist,
    in which case Notes and Info are filled with dummies
    db_name -- Name of database (must exist)
    table_name -- Name of table to upload
    structure_dat -- lmfdb db structure as json object
    """


    dummy_info = {} #Dummy per table info, containing basic fields we want included
    for field in inv.info_editable_fields:
        dummy_info[field] = None

    try:
        table_entry = structure_dat[table_name]
        db_entry = invc.get_db_id(db_name)
        if db_entry is None:
            #All dbs should have been added from the struc: if not is error
            inv.log_dest.error("ERROR: No inventory DB entry "+ db_name)
            inv.log_dest.error("Cannot add descriptions")
            return []

        table_id = invc.get_table_id(table_name)
        if table_id is None:
	    #Table doesn't exist, create it
            table_id = invc.set_table(db_entry, table_name, table_name, None, dummy_info, 0)
        else:
	    #Delete existing auto-table entries (no table => no entries)
           delete_table_data(table_id, tbl='auto')
        try:
            scrape_date = datetime.datetime.strptime(structure_dat[db_name][table_name]['scrape_date'], '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            inv.log_dest.info("Scrape date parsing failed "+str(e))
            scrape_date = datetime.datetime.min
        invc.set_table_scrape_date(table_id, scrape_date)

    except Exception as e:
        inv.log_dest.error("Failed to refresh table (db, table or scrape data) "+str(e))

    try:
        for field in table_entry['fields']:
            inv.log_dest.info("            Processing "+field)
            invc.set_field(table_id, field, table_entry['fields'][field])
        for record in table_entry['records']:
            inv.log_dest.info("            Processing record "+str(record))
            invc.set_record(table_id, table_entry['records'][record])
        #Cleanup any records which no longer exist
        invc.cleanup_records(db, table_id, table_entry['records'])

        inv.log_dest.info("            Processing indices")
        #FIXME
        upload_indices(db, table_id, table_entry['indices'])

    except Exception as e:
        inv.log_dest.error("Failed to refresh table entries "+str(e))

    orphaned_keys = []
    if not fresh:
        try:
	    #Trim any human table keys which are now redundant
            orphaned_keys = invc.trim_human_table(db_entry, table_id)
        except Exception as e:
            inv.log_dest.error("Failed trimming table "+str(e))

    #Ensure everything mandatory is present in human table
    try:
        invc.complete_human_table(db_entry, table_id)
    except Exception as e:
        inv.log_dest.error("Failed padding table "+str(e))

    return orphaned_keys

def extract_specials(table_entry):
    """ Split table_entry into data and specials (notes, info etc) parts """
    notes = ''
    notes_entry = ''
    info = ''
    info_entry = ''
    for item in table_entry:
        if item == inv.STR_NOTES:
            notes = item
            notes_entry = table_entry[item]
        elif item == inv.STR_INFO:
            info = item
            info_entry = table_entry[item]
    try:
        table_entry.pop(notes)
        table_entry.pop(info)
    except:
        pass
    return {inv.STR_NOTES:notes_entry, inv.STR_INFO: info_entry, 'data': table_entry}

#End upload routines -----------------------------------------------------------------

#Table removal -----------------------------------------------------------------------
def delete_contents(db, tbl_name, check=True):
    """Delete contents of tbl_name """

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

    #Grab the possible table names
    tbl_names = inv.get_inv_table_names()
    if tbl_name in tbl_names:
        try:
	    assert(db[tbl_name].find_one() is None) #Check content is gone
            db[tbl_name].drop()
        except Exception as e:
            inv.log_dest.error("Error dropping "+ tbl_name+' '+ str(e))
            #Capped tables, e.g rollback, can only be dropped, so try that

def delete_all_tables(db):
    """ Delete all tables specified by inv. Note that other names can be present """

    tbls = inv.get_inv_table_names()
    for tbl in tbls:
        try:
            delete_contents(db, tbl)
            delete_table(db, tbl)
        except Exception as e:
            inv.log_dest.error("Error deleting "+ tbl + ' ' +str(e))

def delete_table_data(table_id, tbl, dry_run=False):
    """Clean out the data for given table id
      Removes all entries for table_id in auto, human or records

      dry_run -- print items which would be deleted, but do nothing (debugging)
    """
    try:
        table_dat = inv.ALL_STRUC.get_table(tbl)
        fields_tbl = table_dat[inv.STR_NAME]
        #fields_fields = table_dat[inv.STR_CONTENT]
        rec_find = {'table_id':table_id}

        if not dry_run:
            db[fields_tbl].delete(rec_find)
        else:
            print 'Finding '+str(rec_find)
            print 'Operation would delete:'
            curs = db[fields_tbl].search(rec_find)
            for item in curs:
                print item
    except Exception as e:
        inv.log_dest.error("Error removing fields " + str(e))

def delete_by_table(db_name, table_name):
    """Remove table entry and all its fields"""

    try:
        table_id = invc.get_table_id(table_name)
    except Exception as e:
        inv.log_dest.error("Error getting table " + str(e))
        return {'err':True, 'id':0, 'exist':False}

    #Remove fields entries matching table_id
    delete_table_data(table_id, tbl='auto')
    delete_table_data(table_id, tbl='human')
    delete_table_data(table_id, tbl='records')

    try:
        db[inv.ALL_STRUC.table_ids[inv.STR_NAME]].delete({'_id':table_id})
    except Exception as e:
        inv.log_dest.error("Error removing table " + str(e))


#End table removal -----------------------------------------------------------------------

#Rollback table handling
def recreate_rollback_table(sz):
    """Create anew the table for edit rollbacks

    Arguments :
    sz -- Max size of the capped table
    If table exists, it is now deleted
    """
    raise NotImplementedError
    db.drop_table('inv_rollback')
    db.create_table('inv_rollback')

#-----Orphan handling Functions --------------

def summarise_orphans(orphan_data):

    return orphan_data
