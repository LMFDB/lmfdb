import lmfdb_inventory as inv
import inventory_db_core as idc

from lmfdb.db_backend import db

def update_scrape_progress(db_name, table_name, uid, complete=None, running=None):
    """Update progress of scrape from db/table names and uid """
    try:
        db_id = idc.get_db_id(db_name)
        table_id = idc.get_table_id(table_name)
        rec_find = {'db_id':db_id, 'table_id':table_id, 'uid':uid}
        rec_set = {}
        if complete is not None:
            rec_set['complete'] = complete
        if running is not None:
            rec_set['running'] = running
        if rec_set:
            db.inv_ops.update(rec_find, rec_set)
    except Exception as e:
        inv.log_dest.error("Error updating progress "+ str(e))
        return False
