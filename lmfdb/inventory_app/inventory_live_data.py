import json
from datetime import datetime
import inventory_helpers as ih
import inventory_viewer as iv
import lmfdb_inventory as inv
import inventory_db_core as idc
from scrape_helpers import register_scrape
import scrape_frontend as sf
import uuid
from lmfdb.db_backend import db

ops_sz = 2000000
null_uid = '00000000-0000-0000-0000-000000000000'

glt = lambda x : "get_list_table"

#Deal with ops table

def empty_ops():
    raise NotImplementedError
    try:
        db.drop_table('inv_ops')
        db.create_table('inv_ops')
    except Exception:
        pass

#Function to get list a list of all available db/tables
def get_db_lists():
    """Get list of all available DBs and Tables"""
    return glt()

#Scraping helpers and main functions

def get_uid():
    """Create a new uid for a scrape process"""
    return str(uuid.uuid4())

def trigger_scrape(data):
    """Start the rescrape process. In particular, get a uuid for it, register it, and spawn actual scrape"""

    data = json.loads(data)
    db_name = data['data']['db']
    table = data['data']['table']
    cont = True
    inprog = False

    uid = get_uid()
    if not table:
        all_tables = glt(databases=db_name)
        inv.log_dest.warning(db_name+' '+str( all_tables))
        table_list = all_tables[db_name]
        for each_table in table_list:
            tmp = register_scrape(db_name, each_table, uid)
            cont = cont and not tmp['err'] and not tmp['inprog']
            inprog = inprog and tmp['inprog']
    else:
        tmp = register_scrape(db_name, table, uid)
        cont = not tmp['err'] and not tmp['inprog']
        inprog = tmp['inprog']
        table_list = [table]
    if(cont):
        sf.scrape_and_upload_threaded(table_list, uid)
        return {'uid':uid, 'locks':None, 'err':False}
    else:
        return {'uid':null_uid, 'locks':inprog, 'err':cont}

def get_progress(uid):
    """Get progress of scrape with uid"""
    #NOTE what follows _is_ vulnerable to races but
    # this will only affect the progress meter, and should be rare
    scrapes = list(db.inv_ops.search({'uid':uid, 'running':{"$exists":True}}))
    #Assume all ops records with correct uid and containing 'running' are relevant
    n_scrapes = len(scrapes)
    curr_table = 0
    curr_item = None
    for item in scrapes:
        if item['complete'] : curr_table = curr_table + 1
        if item['running'] : curr_item = item

    if curr_item:
        try:
            prog_in_curr = get_progress_from_db(uid, curr_item['db'], curr_item['table'])
        except Exception: # as e:
            #Web front or user can't do anything about errors here. If process
            # is failing, will become evident later
            prog_in_curr = 0
    else:
        #Nothing running. If not yet started, prog=0. If done prog=100.
        prog_in_curr = 100 * (curr_table == n_scrapes)

    return {'n_tables':n_scrapes, 'curr_table':curr_table, 'progress_in_current':prog_in_curr}

def get_progress_from_db(uid, db_id, table_id):
    """Query db to see state of current scrape

    NOTE: this function assumed that when it is called there was a running
    process on db.table, so if there no longer is, it must have finished
    """

    #db_name = idc.get_db_name(db_id)
    table_name = idc.get_table_name(table_id)
    try:
        live_progress = sf.get_scrape_progress(table_name)
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

def check_for_gone(table_name):
    """Check for a table in live db"""

    try:
        return db[table_name].count() == 0
    except Exception:
        pass
    return False

def update_gone_list():
    """Set status of all removed tables to gone"""

    dbs = iv.retrieve_db_listing()
    all_tables = get_db_lists()

    gone_code = ih.status_to_code('gone')
    for db_rec in dbs:
        db_name = db_rec[0]
        tables = iv.retrieve_db_listing(db_name)
        #db_id = idc.get_db_id(db_name)
        for table in tables:
            table_name = table[0]
            gone = not (table_name in all_tables[db_name])
            #Only mark if isn't already
            if gone and table[3] != 'gone':
                table_id = idc.get_table_id(table_name)
                idc.update_table(table_id, status=gone_code)
                inv.log_dest.info(str(table_name) +' is now gone')

#Other scraping result handling

def store_orphans(db_id, table_id, uid, orphan_document):
    """Store orphan info into ops table"""
    try:
        record = {'db_id':db_id, 'table_id':table_id, 'uid':uid, 'orphans':orphan_document}
        db.inv_ops.insert_many([record])
    except Exception as e:
        inv.log_dest.error('Store failed with '+str(e))
        table_name = idc.get_table_name(table_id)
        filename = 'Orph_'+table_name+'.json'
        with open(filename, 'w') as file:
            file.write(json.dumps(orphan_document))
        inv.log_dest.error('Failed to store orphans, wrote to file '+filename)

def collate_orphans_by_uid(uid):
    """Fetch all orphans with given uid and return summary"""

    #All orphans records for this uid
    record = {'uid':uid, 'orphans':{"$exists":True}}
    records = db.inv_ops.search(record)
    orph_data = {}
    db_name = ''
    try:
        db_name = idc.get_db_name(records[0]['db'])
    except Exception:
        record = {'uid':uid}
        tmp_record = db.inv_ops.lucky(record)
        try:
            db_name = idc.get_db_name(tmp_record['db'])
        except Exception:
            pass

    orph_data[db_name] = {}
    for entry in records:
        table = idc.get_table_name(entry['table'])
        orph_data[db_name][table] = split_orphans(entry)

    return orph_data

def collate_orphans():
    """Fetch all orphans and return summary"""
    #All orphans records
    record = {'orphans':{"$exists":True}}
    orph_data = {}

    for entry in db.inv_ops.search(record):
        #print entry['uid']
        db_name = idc.get_db_name(entry['db'])
        orph_data[db_name] = {}
        table = idc.get_table_name(entry['table'])
        orph_tmp = split_orphans(entry)
        orph_data[db_name][table] = orph_tmp

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
        assert(state == True or state == False)
        rec_set = {'lockout':state, 'time':datetime.now()}
        db.inv_ops.insert_many([rec_set])
    except Exception:
        inv.log_dest.error('Failed to set lockout state')

def get_lockout_state():
    """Get global lockout status"""
    try:
        rec_find = {'lockout':{"$exists":True}}
        #Get latest lockout record
        res = db.inv_ops.search(rec_find, projection='lockout', sort=[['time',-1]], limit=1)
        if res: return res
    except Exception:
        pass
    return False
