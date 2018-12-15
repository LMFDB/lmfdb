
import lmfdb_inventory as inv
from inventory_live_data import get_lockout_state
import inventory_helpers as ih
from scrape_helpers import get_completed_scrapes, get_live_scrapes_older_than
import datetime
import threading
from lmfdb.db_backend import db


def get_latest_report():
    sorted_reports = db.inv_ops.search({'report':{'$exists':True}}, sort=[['time',-1]], limit=1)
    return None if not sorted_reports else sorted_reports[0]

def generate_report_threaded():

    """Function to start a thread to generate inventory report.
       returns immediately.
    """

    worker = threading.Thread(target = generate_report)
    worker.start()

def generate_report():
    """Generate a JSON document describing current state
       of the inventory database.
       Can take a while to run
    """
    report = {}

    #Check connection, editor status etc
    report['connection'] = report_connection()

    all_tables=list(db.inv_tables.search())

    report['fields'] = report_fields_tables(all_tables)
    report['latest'] = report_latest_changes(all_tables)
    report['gone'] = report_gone(all_tables)
    report['scrapes'] = report_scrapes()

    report_record = {'time': datetime.datetime.now(), 'report':report}
    db.inv_ops.insert_many([report_record])
#    return report

def report_connection():
    """Check connection, check is inventory, check inventory is as expected
    """
    can_write = not db._read_only
    lockout = get_lockout_state()
    return {'can_write':can_write, 'global_lock':lockout}

def report_fields_tables(tables):
    """Generate report items for consistency of fields tables
    Checks that auto and human match in keys
    Check human.data contains expected fields
    """

    patch=[]
    for item in tables:
        a = db.inv_fields_human.count({'table_id':item['_id']})
        b = db.inv_fields_auto.count({'table_id':item['_id']})
        if a != b:
            list_a = set(db.inv_fields_human.search({'table_id':item['_id']}, 'name'))
            list_b = set(db.inv_fields_auto.search({'table_id':item['_id']}, 'name'))
            keys = list(list_a.symmetric_difference(list_b))
            patch.append((item['name'], item['_id'], a, b, keys))

    bad_items = []
    for item in tables:
        all_human=db.inv_fields_human.search({'table_id':item['_id']})
        key_list = []
        for field in all_human:
                for key in inv.base_editable_fields:
                    try:
                        name=field['data'][key]
                        assert(name or not name)
                    except:
                        key_list.append((field, key))
        if len(key_list) > 0 : bad_items.append((item['name'], item['_id'], key_list))
    return {'table_match':{'num':len(patch), 'items':patch}, 'human_missing':{'num':len(bad_items), 'items':bad_items}}

def report_latest_changes(tables):
    """Report on date of latest rescrapes
    """

    sorted_tables = sorted(tables, key=lambda s : s['scan_date'])
    latest_scan = sorted_tables[-1]

    return {'latest_scan': latest_scan}

def report_gone(tables):
    gone_stat = ih.status_to_code('gone')
    gone_tables = [item for item in tables if item['status'] == gone_stat]

    return {'tables_gone' :{'num':len(gone_tables), 'items': gone_tables}}

def report_scrapes():
    scrapes_hung =  get_live_scrapes_older_than()
    scrapes_last_month = get_completed_scrapes(n_days=30)
    return {'scrapes_hung': len(scrapes_hung) > 0, 'scrapes_run':len(scrapes_last_month)}
