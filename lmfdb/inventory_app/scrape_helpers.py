import lmfdb_inventory as inv
import inventory_db_core as idc
import datetime
from scrape_frontend import get_scrape_progress
from lmfdb.db_backend import db

#Max time before scrape is considered to have failed
DEFAULT_MAX_TIME = 6

def check_scrapes_on(spec=None):
    """If table given, check for scrapes in progress or
    queued on it. If only db, check all tables in it. If spec is None, check everything"""
    spec_ids = {}
    if spec is not None:
        if spec.get('db'):
            spec_ids['db'] = idc.get_db_id(spec['db'])
        if spec.get('table'):
            spec_ids['table'] = idc.get_table_id(spec['table'])
    return check_if_scraping(spec_ids) or check_if_scraping_queued(spec_ids)

def check_scrapes_by_table_id(table_id):
    """Check for scrapes queued or in progress for table_id"""
    spec_ids = {'table_id':table_id}
    return check_if_scraping(spec_ids) or check_if_scraping_queued(spec_ids)

def register_scrape(db, table, uid):
    """Create a suitable inventory entry for the scrape"""

    inv.log_dest.warning(db+' '+table+' '+str(uid))
    try:
        db_id = idc.get_db_id(db)
        inv.log_dest.warning(str(db_id))
        inprog = False
        had_err = False
        if not table:
            all_tables = idc.get_all_tables(db_id)
            for table in all_tables:
                table_id = table['_id']
                tmp = check_and_insert_scrape_record(db_id, table_id, uid)
                inprog = tmp['inprog'] and inprog
                had_err = tmp['err'] and had_err
        else:
            table_id = idc.get_table_id(table)
            inv.log_dest.warning(str(table_id))
            tmp = check_and_insert_scrape_record(db_id, table_id, uid)
            inprog = tmp['inprog'] and inprog
            had_err = tmp['err'] and had_err

    except Exception as e:
        #Either failed to connect etc, or are already scraping
        inv.log_dest.warning('Error resistering scrape '+str(e))
        return {'err':True, 'inprog':False}

    return {'err':had_err, 'inprog':inprog}

def check_if_scraping(record):
    record = dict(record) # copy
    record['running'] = True
    return db.inv_ops.exists(record)

def check_if_scraping_queued(record):
    record = dict(record) # copy
    record['running'] = False
    record['complete'] = False
    return db.inv_ops.exists(record)

def check_if_scraping_done(record):
    record = dict(record) # copy
    record['running'] = False
    record['complete'] = True
    return db.inv_ops.exists(record)

def check_and_insert_scrape_record(db_id, table_id, uid):
    record = {'db_id':db_id, 'table_id':table_id}
    #Is this either scraping or queued
    is_scraping = check_if_scraping(record) or check_if_scraping_queued(record)
    inv.log_dest.warning(is_scraping)
    if is_scraping : return {'err':False, 'inprog':True, 'ok':False}

    time = datetime.datetime.now()
    record = {'db_id':db_id, 'table_id':table_id, 'uid':uid, 'time':time, 'running':False, 'complete':False}
    #Db and table ids. UID for scrape process. Time triggered. If this TABLE is being scraped. If this table has been done
    try:
        insert_scrape_record(record)
        result = {'err':False, 'inprog':False, 'ok':True}
    except Exception as e:
        inv.log_dest.warning('Failed to insert scrape '+str(e))
        result = {'err':True, 'inprog':False, 'ok':False}
    return result

def insert_scrape_record(record):
    """Insert the scraped record"""
    db.inv_ops.insert_many([record])

#----- Helpers handling old etc scrape records

def null_all_scrapes(table_name):
    """Update all scrapes on table to be 'complete' """

    try:
        table_id = idc.get_table_id(table_name)
        rec_find = {'table_id':table_id}
        rec_set = {'complete':True, 'running':False}
        db.inv_ops.update(rec_find, rec_set)
    except Exception as e:
        inv.log_dest.error("Error updating progress "+ str(e))
        return False

def null_old_scrapes(time=DEFAULT_MAX_TIME):
    """Update any old, incomplete AND not running scrapes to be 'complete'"""
    lst = get_live_scrapes_older_than(time)
    new_lst = check_scrapes_running(lst)
    null_scrapes_by_list(new_lst)
    return len(new_lst)

def get_live_scrapes_older_than(min_hours_old=DEFAULT_MAX_TIME, db_id=None, table_id=None):
    """Get all scrapes that are not marked complete and are at least min_hour_old

    Generally we expect scrapes to take only a few hours so an entire DB scrape should
    not take more than 4-6 hours at worst.

    min_hour_old -- Find only records older than this many hours

    Optional:
    db_id -- Find only records relating to this db id
    table_id -- Find only records relating to this table id

    """
    try:
        start = datetime.datetime.now() - datetime.timedelta(hours=min_hours_old)
        #Currently this is enough to identify scrape records
        rec_test = {'time':{"$lt":start}, 'complete':False}
        if db_id: rec_test['db_id'] = db_id
        if table_id: rec_test['table_id'] = table_id
        return list(db.inv_ops.search(rec_test))
    except Exception as e:
        inv.log_dest.warning('Failed to get old scrapes '+str(e))
        return []

def check_scrapes_running(scrape_list):
    """Given a list of scrapes, check for actual running state and
    return a new list containing only those which are NOT running"""

    new_list = []
    for item in scrape_list:
        db_name = idc.get_db_name(item['db'])
        table_name = idc.get_table_name(item['table'])
        try:
            prog = get_scrape_progress(db_name, table_name)
            if prog == (-1, -1):
                new_list.append(item)
        except Exception as e:
            inv.log_dest.warning('Failed to get progress '+db_name+' '+table_name+' '+str(e))
    return new_list

def null_scrapes_by_list(scrape_list):
    """Given a list of scrape records, nullify each
    Since we can't delete them, we set Running False and Complete True
    """
    try:
        for item in scrape_list:
            db.inv_ops.update({'uid':item['uid']}, {'running':False, 'complete':True})
    except Exception as e:
        inv.log_dest.warning('Failed to nullify scrapes '+str(e))

def get_completed_scrapes(n_days=7):
    """Get successfully completed scrapes from the last n days
    """

    try:
        start = datetime.datetime.now() - datetime.timedelta(days=n_days)
        #Currently this is enough to identify scrape records
        rec_test = {'time':{"$gt":start}, 'complete':True}
        return list(db.inv_ops.search(rec_test))
    except Exception as e:
        inv.log_dest.warning('Failed to get completed scrapes '+str(e))
        return []
