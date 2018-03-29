import scripts.reports.jsonify_db_structure as jdbs
import inventory_upload_data as iud
from lmfdb.base import getDBConnection
from scrape_progress_update import update_scrape_progress
import threading
import bson

def get_scrape_progress(db, coll, connection):
    """Routine to query database on state of MapReduce on a given db
       collection. Will only return data for first operation if more than
       one in flight

       db - String name of database
       coll - String name of collection
       connection - MongoDB connection object. Should be same role as called
                    scrape_and_upload_threaded

       returns tuple containing (number of records scanned, total number of records)
    """
    u=bson.son.SON({"$ownOps":1,"currentOp":1})
    progress = connection['admin'].current_op(u)
    for el in progress['inprog']:
        if 'progress' in el.keys():
            if el['ns'] == db + "." + coll:
                return int(el['progress']['done']), int(el['progress']['total'])
    return -1, -1

def scrape_worker(db, coll, uuid, connection):
    """Worker function used to actually scan database and collection list
       db - String name of database
       coll - List of collection names as strings to scan. Must be list even
              if only scanning one collection
       uuid - String containing UUID associated with scrape operation
       connection - MongoDB connection object. Passed through from
                    scrape_and_upload_threaded
    """

    for el in coll:
        update_scrape_progress(db, el, uuid, running = True)
        data = jdbs.parse_collection_info_to_json(db, el,
            connection = connection)
        iud.upload_scraped_data(data, uuid)
        update_scrape_progress(db, el, uuid, running = False, complete = True)

def scrape_and_upload_threaded(db, coll, uuid, connection = None):

    """Function to start a thread to scan a list of collections for a database.
       returns immediately.

       db - String name of database
       coll - List of collection names as strings to scan. Must be list even
              if only scanning one collection
       uuid - String containing UUID associated with scrape operation
       connection - MongoDB connection object. If not provided, obtained from
                    lmfdb.base.getDBConnection()
    """

    if not connection:
        connection = getDBConnection()

    worker = threading.Thread(target = scrape_worker,
        args = [db, coll, uuid, connection])
    worker.start()

def scrape_and_upload(dblist, connection = None):
    """ Legacy function, do not use """
    if not connection:
        connection = getDBConnection()

    data = jdbs.parse_lmfdb_to_json(collections=dblist, connection = connection)
    invdb = connection['inventory']
    for db in dblist:
        for coll in dblist[db]:
            iud.upload_collection_structure(invdb, db, coll, data)
            iud.upload_collection_indices(invdb, db, coll, data)
