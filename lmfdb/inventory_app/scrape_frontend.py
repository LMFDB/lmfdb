import scripts.reports.jsonify_db_structure as jdbs
import scripts.reports.inventory_upload_data as iud
from lmfdb.base import getDBConnection
import threading
import datetime

def scrape_worker(db, coll, uuid, connection):

    date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    invdb =  connection['inventory']
    for el in coll:
        data = jdbs. parse_collection_info_to_json(db, el, 
            connection = connection, date = date)
        iud.upload_collection_structure(invdb, db, el, data)
        iud.upload_collection_indices(invdb, db, el, data)

def scrape_and_upload_threaded(db, coll, uuid, connection = None):

    if not connection:
        connection = getDBConnection()

    worker = threading.Thread(target = scrape_worker,
        args = [db, coll, uuid, connection])
    worker.start()

def scrape_and_upload(dblist, connection = None):
    if not connection:
        connection = getDBConnection()

    data = jdbs.parse_lmfdb_to_json(collections=dblist, connection = connection)
    invdb = connection['inventory']
    for db in dblist:
        for coll in dblist[db]:
            iud.upload_collection_structure(invdb, db, coll, data)
            iud.upload_collection_indices(invdb, db, coll, data)
