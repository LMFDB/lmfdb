import inventory_db_core as idc

def update_scrape_progress_helper(db_id, coll_id, uid, complete=None, running=None):
    """Update the stored progress value
    If running is provided, then set it.
    """
    try:
        rec_find = {'db':db_id, 'table':coll_id, 'uid':uid}
        rec_set = {}
        if complete is not None:
            rec_set['complete'] = complete
        if running is not None:
            rec_set['running'] = running
        if rec_set:
            idc.update_ops(rec_find, rec_set)
    except:
        pass

def update_scrape_progress(db_name, coll, uid, complete=None, running=None):
    """Update progress of scrape from db/coll names and uid """

    try:
        db_id = idc.get_db_id(db_name)
        coll_id = idc.get_coll_id(db_id['id'], coll)
        update_scrape_progress_helper(db_id['id'], coll_id['id'], uid, complete=complete, running=running)
    except:
        return False
