#import scripts.reports.jsonify_db_structure as jdbs
import inventory_upload_data as iud
from scrape_progress_update import update_scrape_progress
import threading

jdbs = None  #This is not a global, this fixes pyflakes problem

def get_scrape_progress(table):
    """Routine to query database on state of MapReduce on a given table
       Will only return data for first operation if more than
       one in flight

       table - String name of table

       returns tuple containing (number of records scanned, total number of records)
    """
    raise NotImplementedError
    #progress = connection['admin'].current_op()
    #for el in progress['inprog']:
    #    if 'progress' in el.keys():
    #        if el['ns'] == table:
    #            return int(el['progress']['done']), int(el['progress']['total'])
    #return -1, -1

def scrape_worker(tables, uuid):
    """Worker function used to actually scan database and table list
       tables - List of table names as strings to scan. Must be list even
              if only scanning one table
       uuid - String containing UUID associated with scrape operation
    """

    for el in tables:
        update_scrape_progress(el, uuid, running = True)
        data = jdbs.parse_table_info_to_json(el)
        iud.upload_scraped_data(data, uuid)
        update_scrape_progress(el, uuid, running = False, complete = True)

def scrape_and_upload_threaded(tables, uuid):

    """Function to start a thread to scan a list of tables for a database.
       returns immediately.

       tables - List of table names as strings to scan. Must be list even
              if only scanning one table
       uuid - String containing UUID associated with scrape operation
    """
    worker = threading.Thread(target = scrape_worker,
        args = [tables, uuid])
    worker.start()

def scrape_and_upload(dblist):
    """ Legacy function, do not use """
    raise NotImplementedError

    data = jdbs.parse_lmfdb_to_json(tables=dblist)
    for db_name in dblist:
        for table in dblist[db_name]:
            iud.upload_table_structure(db_name, table, data)
