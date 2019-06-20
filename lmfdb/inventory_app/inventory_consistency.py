
#from bson import SON
import lmfdb_inventory as inv
from inventory_live_data import get_lockout_state
import inventory_helpers as ih
import inventory_db_core as idc
from lmfdb.backend.database import db


from scrape_helpers import get_completed_scrapes, get_live_scrapes_older_than
import datetime
import threading


def get_latest_report():


    reports = idc.search_ops_table({'isa':'report'})
    sorted_reports = sorted(reports, key=lambda s : s['scan_date'])
    rept = sorted_reports[-1]
    rept['report'] = rept.pop('content')

    try:
        return rept
    except:
        return {'scan_date':'NaN'}

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

    all_colls = list(idc.get_all_colls())

    report['fields'] = report_fields_tables(all_colls)
    report['latest'] = report_latest_changes(all_colls)
    report['gone'] = report_gone(all_colls)
    report['scrapes'] = report_scrapes()

    report_record = {'isa':'report', 'scan_date': datetime.datetime.now(), 'content':report}
    idc.add_to_ops_table(report_record)
#    return report

def report_connection():
    """Check connection, check is inventory, check inventory is as expected
    """
    # TODO fix this, when recreate scraper
#    roles = idb['admin'].command(SON({"connectionStatus":int(1)}))
#    can_write = 'readWrite' in [el['role'] for el in roles['authInfo']['authenticatedUserRoles'] if el['db']=='inventory']
#    inv_ok = ??
    lockout = get_lockout_state()
    can_write = False
    inv_ok = False
    lockout = False
    return {'can_write':can_write, 'inv_ok': inv_ok, 'global_lock':lockout}

def report_fields_tables(colls):
    """Generate report items for consistency of fields tables
    Checks that auto and human match in keys
    Check human.data contains expected fields
    """
    patch=[]
    for item in colls:
        #TODO fix this
         a=db['inv_fields_human'].count({'table_id':item['_id']})
         b=db['inv_fields_auto'].count({'table_id':item['_id']})
         if a != b:
             list_a = set([el['name'] for el in db['inv_fields_human'].search({'table_id':item['_id']})])
             list_b = set([el['name'] for el in db['inv_fields_auto'].search({'table_id':item['_id']})])
             keys = list(list_a.symmetric_difference(list_b))
             patch.append((item['name'], item['_id'], a, b, keys))

    bad_items = []
    for item in colls:
        all_human=db['inv_fields_human'].search({'table_id':item['_id']})
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

def report_latest_changes(colls):
    """Report on date of latest rescrapes
    """

    sorted_colls = sorted(colls, key=lambda s : s['scan_date'])
    latest_scan = sorted_colls[-1]

    return {'latest_scan': latest_scan}

def report_gone(colls):
    gone_stat = ih.status_to_code('gone')
    gone_colls = [item for item in colls if item['status'] == gone_stat]

    return {'colls_gone' :{'num':len(gone_colls), 'items': gone_colls}}

def report_scrapes():
    scrapes_hung =  get_live_scrapes_older_than()

    scrapes_last_month = get_completed_scrapes(n_days=30)


    return {'scrapes_hung': len(scrapes_hung) > 0, 'scrapes_run':len(scrapes_last_month)}
