
from scripts.reports.jsonify_db_structure import get_lmfdb_collections as glc
import json
import inventory_helpers as ih
import inventory_viewer as iv
import lmfdb_inventory as inv
import inventory_db_core as idc
import uuid
import datetime

#Function to get list a list of all available db/collections
def get_db_lists():
    """Get list of all available DBs and Collections"""
    return glc()

#Scraping helpers and main functions

def get_uid():
    """Get a uid for a scrape process"""
    return uuid.uuid4()

def trigger_scrape(data):
    """Start the rescrape process. In particular, get a uuid for it, register it, and spawn actual scrape"""

    data = json.loads(data)
    uid = get_uid()
    cont = register_scrape(data['data']['db'], data['data']['coll'], uid)
    #Spawn scraper somehow here, as long as cont is True
    if(cont):
        return uid
    else:
        return "0"

def get_progress(uid):
    """Get progress of scrape with uid"""

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    scrapes = inv_db['ops'].find({'uid':uuid.UUID(uid), 'running':{"$exists":True}})
    #Assume all ops records with correct uid and containing 'progress' are relevant
    n_scrapes = scrapes.count()
    curr_coll = 0
    curr_item = None
    for item in scrapes:
        if item['complete'] : curr_coll = curr_coll + 1
        if item['running'] : curr_item = item

    if curr_item:
        prog_in_curr = get_progress_from_db(uid, idc.get_db_name(inv_db, curr_item['db']), idc.get_coll_name(inv_db, curr_item['coll']))
    else:
        prog_in_curr = 0

    return {'n_colls':n_scrapes, 'curr_coll':curr_coll, 'progress_in_current':prog_in_curr}

def get_progress_from_db(uid, db, coll):
    """Query db to see state of current scrape"""

    return 40

def register_scrape(db, coll, uid):
    """Create a suitable inventory entry for the scrape"""

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False
    try:
        db_id = idc.get_db_id(inv_db, db)
        db_id = db_id['id']
        ok = True

        if not coll:
            all_colls = idc.get_all_colls(inv_db, db_id)
            for coll in all_colls:
                coll_id = coll['_id']
                ok = check_and_insert_scrape_record(inv_db, db_id, coll_id, uid) and ok
        else:
            coll_id = idc.get_coll_id(inv_db, db_id, coll)
            ok = check_and_insert_scrape_record(inv_db, db_id, coll_id, uid) and ok

    except Exception as e:
        #Either failed to connect etc, or are already scraping
        return False

    return True

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
    if is_scraping : return False

    time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    record = {'db':db_id, 'coll':coll_id, 'uid':uid, 'time':time, 'running':False, 'complete':False}
    #Db and collection ids. UID for scrape process. Time triggered. If this COLL is being scraped. If this coll hass been done
    insert_scrape_record(inv_db, record)
    return True

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
        if new_prog:
            rec_set['complete'] = complete
        if running:
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
        coll_id = idc.get_coll_id(inv_db, db_id, coll)
        update_scrape_progress_helper(inv_db, db_id, coll_id, uid, complete=complete, running=running)
    except Exception as e:
        inv.log_dest.error("Error updating progress "+ str(e))
        return False

#Other live DB functions

def check_for_gone(lmfdb, db_name, coll_name):
    """Check for a collection db_name.coll_name in live db"""

    try:
        db = lmfdb[db_name]
        coll = db[coll_name]
        results = list(coll.find())
        return results == []
    except:
        pass
    return False

def mark_all_gone(main_db):
    """Set status of all removed collections to gone"""

    inv_db = main_db[inv.get_inv_db_name()]
    dbs = iv.gen_retrieve_db_listing(inv_db)
    all_colls = get_db_lists()

    gone_code = ih.status_to_code('gone')
    for db in dbs:
        try:
            cc = all_colls[db[0]]
        except:
            continue
        colls = iv.gen_retrieve_db_listing(inv_db, db[0])
        db_id = idc.get_db_id(inv_db, db[0])
        for coll in colls:
            gone = not (coll[0] in all_colls[db[0]])
            if gone:
                coll_id = idc.get_coll_id(inv_db, db_id['id'], coll[0])
                coll_id = idc.get_coll_id(inv_db, db_id['id'], coll[0])
                idc.update_coll(inv_db, coll_id['id'], status=gone_code)

def remove_all_gone():
    """Remove inventory data for 'gone' collections"""
    pass

def update_gone_lists():
    """Remove any collections that are flagged as gone, THEN check for any others that are gone

    Call twice in succession to completely get rid of any gone collection data
    """
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        main_db = inv.int_client
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    mark_all_gone(main_db)
