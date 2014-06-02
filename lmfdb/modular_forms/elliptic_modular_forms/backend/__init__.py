from plot_dom import *

db_name = 'modularforms2'
def connect_to_modularforms_db():
    try:
        C = lmfdb.base.getDBConnection()
    except Exception as e:
        emf_logger.critical("Could not connect to Database! C={0}. Error: {1}".format(C,e.message))
    if db_name not in C.database_names():
        emf_logger.critical("Database {0} does not exist at connection {1}".format(db_name,C))
    return C[db_name]

from web_modforms import WebModFormSpace, WebNewForm, html_table
from emf_classes import *
