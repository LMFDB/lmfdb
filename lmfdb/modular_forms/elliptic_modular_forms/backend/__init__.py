from plot_dom import *

db_name = 'modularforms2'

import lmfdb
import gridfs
def connect_to_modularforms_db(collection='',create=True):
    r"""
    Return a handle to a modular forms database or a specific collection.

    """
    try:
        C = lmfdb.base.getDBConnection()
    except Exception as e:
        emf_logger.critical("Could not connect to Database! db={0}. Error: {1}".format(db_name,e.message))
    if db_name not in C.database_names() and not create:
        emf_logger.critical("Database {0} does not exist at connection {1}".format(db_name,C))
    if collection <>'':
        if collection not in C[db_name].collection_names() and not create:
            error_st = "Collection {0} is not in database {1} at connection {2}".format(collection,db_name,C)
            emf_logger.critical(error_st)
            raise ValueError,error_st
        return C[db_name][collection]
    else:
        return C[db_name]

def get_files_from_gridfs(collection='',create=True):
    r"""
    Return a handle to a modular forms database or a specific collection.
    """
    C = connect_to_modularforms_db()
    if 'files' not in collection:
        collection_name = collection + '.files'
    else:
        collection_name = collection.split('.')[0]
    if collection_name not in C.collection_names() and not create:
        error_st = "Collection {0} is not in database {1} at connection {2}".format(collection,db_name,C)
        emf_logger.critical(error_st)
        raise ValueError,error_st
    return gridfs.GridFS(C,collection)
        

from web_newforms import WebNewForm # html_table
from web_modform_space import WebModFormSpace

