import lmfdb_inventory as inv
import inventory_db_core as idc

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
