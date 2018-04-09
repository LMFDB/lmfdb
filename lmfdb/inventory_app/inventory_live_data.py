from scripts.reports.jsonify_db_structure import get_lmfdb_collections as glc
import json
import inventory_helpers as ih
import inventory_viewer as iv
import lmfdb_inventory as inv
import inventory_db_core as idc
from scrape_helpers import register_scrape
import scrape_frontend as sf
import uuid
from lmfdb.base import getDBConnection


ops_sz = 2000000
null_uid = '00000000-0000-0000-0000-000000000000'

#Deal with ops collection

def empty_ops(inv_db):

    try:
        inv_db['ops'].drop()
        inv_db.create_collection('ops', capped=True, size=ops_sz)
    except:
        pass

#Function to get list a list of all available db/collections
def get_db_lists():
    """Get list of all available DBs and Collections"""
    return glc()

#Scraping helpers and main functions

def get_uid():
    """Create a new uid for a scrape process"""
    return uuid.uuid4()

def trigger_scrape(data):
    """Start the rescrape process. In particular, get a uuid for it, register it, and spawn actual scrape"""

    data = json.loads(data)
    db = data['data']['db']
    coll = data['data']['coll']
    cont = True
    inprog = False

    uid = get_uid()
    if not coll:
        all_colls = glc(databases=db)
        inv.log_dest.warning(db+' '+str( all_colls))
        coll_list = all_colls[db]
        for each_coll in coll_list:
            tmp = register_scrape(db, each_coll, uid)
            cont = cont and not tmp['err'] and not tmp['inprog']
            inprog = inprog and tmp['inprog']
    else:
        tmp = register_scrape(db, coll, uid)
        cont = not tmp['err'] and not tmp['inprog']
        inprog = tmp['inprog']
        coll_list = [coll]
    if(cont):
        sf.scrape_and_upload_threaded(db, coll_list, uid)
        return {'uid':uid, 'locks':None, 'err':False}
    else:
        return {'uid':uuid.UUID(null_uid), 'locks':inprog, 'err':cont}

def get_progress(uid):
    """Get progress of scrape with uid"""

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    #NOTE what follows _is_ vulnerable to races but
    # this will only affect the progress meter, and should be rare
    scrapes = inv_db['ops'].find({'uid':uuid.UUID(uid), 'running':{"$exists":True}})
    #Assume all ops records with correct uid and containing 'running' are relevant
    n_scrapes = scrapes.count()
    curr_coll = 0
    curr_item = None
    for item in scrapes:
        if item['complete'] : curr_coll = curr_coll + 1
        if item['running'] : curr_item = item

    if curr_item:
        try:
            prog_in_curr = get_progress_from_db(inv_db, uid, curr_item['db'], curr_item['coll'])
        except Exception as e:
            #Web front or user can't do anything about errors here. If process
            # is failing, will become evident later
            prog_in_curr = 0
    else:
        #Nothing running. If not yet started, prog=0. If done prog=100.
        prog_in_curr = 100 * (curr_coll == n_scrapes)

    return {'n_colls':n_scrapes, 'curr_coll':curr_coll, 'progress_in_current':prog_in_curr}

def get_progress_from_db(inv_db, uid, db_id, coll_id):
    """Query db to see state of current scrape

    NOTE: this function assumed that when it is called there was a running
    process on db.coll, so if there no longer is, it must have finished
    """

    db_name = idc.get_db_name(inv_db, db_id)['name']
    coll_name = idc.get_coll_name(inv_db, coll_id)['name']
    try:
        live_progress = sf.get_scrape_progress(db_name, coll_name, getDBConnection())
        #Cheat here: we'll cap running to 99% and the last 1% is left for upload time
        #If no running record found, this assumes it completed before
        #we managed to check it, hence 99%
        percent = (live_progress[0] *99)/live_progress[1]
    except Exception as e:
        inv.log_dest.warning(e)
        percent = 0
        raise e
    return percent

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
        colls = iv.gen_retrieve_db_listing(inv_db, db[0])
        db_id = idc.get_db_id(inv_db, db[0])
        for coll in colls:
            gone = not (coll[0] in all_colls[db[0]])
            #Only mark if isn't already
            mark = gone and coll[3] != 'gone'
            if mark:
                coll_id = idc.get_coll_id(inv_db, db_id['id'], coll[0])
                idc.update_coll(inv_db, coll_id['id'], status=gone_code)
                inv.log_dest.info(str(db) +'.'+str(coll) +' is now gone')

def remove_all_gone(inv_db):
    """Remove inventory data for 'gone' collections"""
    pass

def update_gone_list():
    """Check for any colections that are gone and mark
    """
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        main_db = inv.int_client
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    mark_all_gone(main_db)
    return True

def remove_gone_collections():
    """Remove any collections marked as gone
    """
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False

    remove_all_gone(inv_db)
    return True

#Other scraping result handling

def store_orphans(inv_db, db_id, coll_id, uid, orphan_document):
    """Store orphan info into ops table"""
    try:
        record = {'db':db_id, 'coll':coll_id, 'uid':uuid.UUID(uid), 'orphans':orphan_document}
        inv_db['ops'].insert_one(record)
    except Exception as e:
        inv.log_dest.error('Store failed with '+str(e))
        db_name = idc.get_db_name(inv_db, db_id)
        coll_name = idc.get_coll_name(inv_db, coll_id)
        filename = 'Orph_'+db_name['name']+'_'+coll_name['name']+'.json'
        with open(filename, 'w') as file:
            file.write(json.dumps(orphan_document))
        inv.log_dest.error('Failed to store orphans, wrote to file '+filename)

def collate_orphans_by_uid(uid):
    """Fetch all orphans with given uid and return summary"""

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False
    #All orphans records for this uid
    record = {'uid':uuid.UUID(uid), 'orphans':{"$exists":True}}
    records = inv_db['ops'].find(record)
    orph_data = {}
    db_name = ''
    try:
        db_name = idc.get_db_name(inv_db, records[0]['db'])['name']
    except:
        record = {'uid':uuid.UUID(uid)}
        tmp_record = inv_db['ops'].find_one(record)
        try:
            db_name = idc.get_db_name(inv_db, tmp_record['db'])['name']
        except:
            pass

    orph_data[db_name] = {}
    for entry in records:
        coll = idc.get_coll_name(inv_db, entry['coll'])['name']
        orph_data[db_name][coll] = split_orphans(entry)

    return orph_data

def collate_orphans():
    """Fetch all orphans and return summary"""

    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return False
    #All orphans records
    record = {'orphans':{"$exists":True}}
    records = inv_db['ops'].find(record)
    orph_data = {}

    for entry in records:
        print entry['uid']
        db_name = idc.get_db_name(inv_db, entry['db'])['name']
        orph_data[db_name] = {}
        coll = idc.get_coll_name(inv_db, entry['coll'])['name']
        orph_tmp = split_orphans(entry)
        orph_data[db_name][coll] = orph_tmp

    return orph_data


def split_orphans(entry):
    just_gone = []
    gone_w_data = []
    items = entry['orphans']
    for item in items:
        if check_orphan_empty(item):
            just_gone.append(item['name'])
        else:
            gone_w_data.append(item)

    if just_gone == []:
         just_gone = None
    if gone_w_data == []:
        gone_w_data = None

    return {'gone':just_gone, 'orphan':gone_w_data}

def check_orphan_empty(entry):
    """Check whether is empty"""

    empty = True
    for item in entry['data']:
        empty = empty and (entry['data'][item] is None)
    return empty

def set_lockout_state(state):
    """Swap state of lockout. If record exists, toggle, else create"""
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return True
    try:
        assert(state == True or state == False)
        rec_set = {'lockout':state}
        inv_db['ops'].insert_one(rec_set)
    except:
        inv.log_dest.error('Failed to set lockout state')

def get_lockout_state():
    """Get lockout status"""
    try:
        got_client = inv.setup_internal_client(editor=True)
        assert(got_client == True)
        inv_db = inv.int_client[inv.get_inv_db_name()]
    except Exception as e:
        inv.log_dest.error("Error getting Db connection "+ str(e))
        return True

    try:
        rec_find = {'lockout':{"$exists":True}}
        res = inv_db['ops'].find(rec_find).sort('_id', -1).limit(1)
    except:
        pass
    if res is None:
        return False
    else:
        return res[0]['lockout']
