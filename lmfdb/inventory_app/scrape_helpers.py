from scripts.reports.jsonify_db_structure import get_lmfdb_collections as glc
import json
import inventory_helpers as ih
import inventory_viewer as iv
import lmfdb_inventory as inv
import inventory_db_core as idc
import uuid
import datetime

def check_scrapes_on(spec):
    """If collection given, check for scrapes in progress or
    queued on it. If only db, check all collections in it"""
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False
    try:
        db_id = idc.get_db_id(inv_db, spec['db'])
        spec_ids = {'db':db_id['id']}
        if spec['coll']:
            coll_id = idc.get_coll_id(inv_db, db_id['id'], spec['coll'])
            spec_ids['coll'] = coll_id['id']
        result = check_if_scraping(inv_db, spec_ids) or check_if_scraping_queued(inv_db, spec_ids)
        return result
    except Exception as e:
        return False

def register_scrape(db, coll, uid):
    """Create a suitable inventory entry for the scrape"""

    inv.log_dest.warning(db+' '+coll+' '+str(uid))
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return {'err':True, 'inprog':False}
    try:
        db_id = idc.get_db_id(inv_db, db)
        inv.log_dest.warning(str(db_id))
        db_id = db_id['id']
        inprog = False
        had_err = False
        if not coll:
            all_colls = idc.get_all_colls(inv_db, db_id)
            for coll in all_colls:
                coll_id = coll['_id']
                tmp = check_and_insert_scrape_record(inv_db, db_id, coll_id, uid)
                inprog = tmp['inprog'] and inprog
                had_err = tmp['err'] and had_err
        else:
            coll_id = idc.get_coll_id(inv_db, db_id, coll)
            inv.log_dest.warning(str(coll_id))
            coll_id = coll_id['id']
            tmp = check_and_insert_scrape_record(inv_db, db_id, coll_id, uid)['ok']
            inprog = tmp['inprog'] and inprog
            had_err = tmp['err'] and had_err

    except Exception as e:
        #Either failed to connect etc, or are already scraping
        return {'err':True, 'inprog':False}

    return {'err':had_err, 'inprog':inprog}

def check_if_scraping(inv_db, record):

    coll = inv_db['ops']
    record['running'] = True
    result = coll.find_one(record)

    return result is not None

def check_if_scraping_queued(inv_db, record):

    coll = inv_db['ops']
    record['running'] = False
    record['complete'] = False
    result = coll.find_one(record)

    return result is not None

def check_if_scraping_done(inv_db, record):

    coll = inv_db['ops']
    record['running'] = False
    record['complete'] = True
    result = coll.find_one(record)

    return result is not None

def check_and_insert_scrape_record(inv_db, db_id, coll_id, uid):

    record = {'db':db_id, 'coll':coll_id}
    #Is this either scraping or queued
    is_scraping = check_if_scraping(inv_db, record) or check_if_scraping_queued(inv_db, record)
    inv.log_dest.warning(is_scraping)
    if is_scraping : return {'err':False, 'inprog':True, 'ok':False}

    time = datetime.datetime.now()
    record = {'db':db_id, 'coll':coll_id, 'uid':uid, 'time':time, 'running':False, 'complete':False}
    #Db and collection ids. UID for scrape process. Time triggered. If this COLL is being scraped. If this coll hass been done
    try:
        inserted = insert_scrape_record(inv_db, record)
        result = {'err':False, 'inprog':False, 'ok':True}
    except Exception as e:
        inv.log_dest.warning('Failed to insert scrape '+str(e))
        result = {'err':True, 'inprog':False, 'ok':False}
    return result

def insert_scrape_record(inv_db, record):
    """Insert the scraped record"""

    coll = inv_db['ops']
    result = coll.insert_one(record)
    return result

def update_scrape_progress_helper(inv_db, db_id, coll_id, uid, complete=None, running=None):
    """Update the stored progress value
    If running is provided, then set it.
    """
    try:
        rec_find = {'db':db_id, 'coll':coll_id, 'uid':uid}
        rec_set = {}
        if complete is not None:
            rec_set['complete'] = complete
        if running is not None:
            rec_set['running'] = running
        if rec_set:
            inv_db['ops'].find_one_and_update(rec_find, {"$set":rec_set})
    except:
        pass

def update_scrape_progress(db, coll, uid, complete=None, running=None):
    """Update progress of scrape from db/coll names and uid """

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    try:
        db_id = idc.get_db_id(inv_db, db)
        coll_id = idc.get_coll_id(inv_db, db_id['id'], coll)
        update_scrape_progress_helper(inv_db, db_id['id'], coll_id['id'], uid, complete=complete, running=running)
    except Exception as e:
        inv.log_dest.error("Error updating progress "+ str(e))
        return False

def null_all_scrapes(db, coll):
    """Update all scrapes on db.coll to be 'complete' """

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    try:
        db_id = idc.get_db_id(inv_db, db)
        coll_id = idc.get_coll_id(inv_db, db_id['id'], coll)
        rec_find = {'db':db_id['id'], 'coll':coll_id['id']}
        rec_set = {}
        rec_set['complete'] = True

        rec_set['running'] = False

        inv_db['ops'].update_many(rec_find, {"$set":rec_set})
    except Exception as e:
        inv.log_dest.error("Error updating progress "+ str(e))
        return False
