from lmfdb.modular_forms.elliptic_modular_forms import emf_logger

import lmfdb
import gridfs
def connect_to_modularforms_db(collection='',create=True):
    r"""
    Return a handle to a modular forms database or a specific collection.

    """
    db_name = 'modularforms2'
    try:
        C = lmfdb.base.getDBConnection()
    except Exception as e:
        emf_logger.critical("Could not connect to Database! db={0}. Error: {1}".format(db_name,e.message))
    
    try:
        if collection != '':
            return C[db_name][collection]
        else:
            return C[db_name]
    except Exception as e:
        if collection != '':
            error_st = "Either Database %s does not exist or Collection %s is not in database %s at connection %s. Error: %s" % (db_name, collection, db_name, C,e);
        else:
            error_st = "Database %s does not exist at connection %s. Error: %s" % (db_name, C,e);
            raise ValueError,error_st

def get_files_from_gridfs(collection='',create=True):
    r"""
    Return a handle to a modular forms database or a specific collection.
    """
    C = connect_to_modularforms_db()

    #FIXME collection_name is set but never used
    #if 'files' not in collection:
    #    collection_name = collection + '.files'
    #else:
    #    collection_name = collection.split('.')[0]

    try:
        return gridfs.GridFS(C,collection)
    except Exception as e:
        error_st = "Collection {0} is not in database {1}.  Error: {2}".format(collection,C,e)
        emf_logger.critical(error_st)
        raise ValueError,error_st 

from web_newforms import WebNewForm # html_table
assert WebNewForm
from web_modform_space import WebModFormSpace
assert WebModFormSpace

