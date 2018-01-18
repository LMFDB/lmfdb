from pymongo import MongoClient
import json
import logging, logging.handlers

#Contains the general data and functions for all inventory handling

__version__ = '0.1.0'

#Email contact for app errors
email_contact = 'rse@warwick.ac.uk'

#DB client
int_client = None

#Sting constants
STR_NAME = 'name'
STR_CONTENT = 'content'
STR_NOTES = "(NOTES)"
STR_INFO = "(INFO)"

#Fields to edit for normal records. These will always be shown, blank if no data exists
#Value can be used to impose ordering in views
base_editable_fields = {'type':1, 'description':2, 'example':3}
#sorted(d, key=d.get) returns keys sorted by values
def display_field_order():
    return sorted(base_editable_fields, key=base_editable_fields.get)

info_editable_fields = {'nice_name':1, 'description':2, 'contact':4, 'status':3, 'code':5}
def info_field_order():
    return sorted(info_editable_fields, key=info_editable_fields.get)

record_editable_fields = {'name':1, 'descrip':2, 'extends': -3, 'schema':-4, 'count':-5}
#Negative denotes NOT editable
def record_field_order():
    return sorted(record_editable_fields, key = lambda s : abs(record_editable_fields.get(s)))

def record_noeditable():
    return [name for (name, val) in record_editable_fields.items() if val < 0]

index_fields = {'name':-1, 'keys':-2}
#Negative denotes NOT editable
def index_field_order():
    return sorted(index_fields, key = lambda s : abs(index_fields.get(s)))

coll_status = {0: 'live', 1:'ops', 2:'beta', 4: 'old'}
#Live is normal. Ops includes any stats, rand etc. Beta is beta status, not yet on prod
#Old means deprecated. Probably want to show only live and beta, and flag beta
#Object describing DB structure. This is styled after a relational model
class db_struc:
    name = 'inventory'
    n_colls = 7
    db_ids = {STR_NAME : 'DB_ids', STR_CONTENT : ['_id', 'name', 'nice_name']}
    coll_ids = {STR_NAME : 'collection_ids', STR_CONTENT :['_id', 'db_id', 'name', 'nice_name', 'NOTES', 'INFO', 'scan_date', 'status']}
    fields_auto = {STR_NAME : 'fields_auto', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}
    fields_human = {STR_NAME : 'fields_human', STR_CONTENT : ['_id', 'coll_id', 'name', 'data']}
    record_types = {STR_NAME : 'records', STR_CONTENT :['_id', 'coll_id', 'hash', 'name', 'descrip', 'schema', 'count']}
    rollback_human = {STR_NAME : 'rollback', STR_CONTENT:['_id', 'diff']}
    indexes = {STR_NAME : 'indexes', STR_CONTENT :['_id', 'name', 'coll_id', 'keys']}
    def get_fields(self, which):
        if which =='auto':
            return self.fields_auto
        elif which == 'human':
            return self.fields_human
        else:
            return None

    def get_table(self, which):
        if which =='auto':
            return self.fields_auto
        elif which == 'human':
            return self.fields_human
        elif which == 'records':
            return self.record_types
        else:
            return None


#Constant instance of db_struct
ALL_STRUC = db_struc()

_auth_as_edit = False
_auth_on_remote = False
def setup_internal_client(remote=True, editor=False):
    """Get mongo connection and set int_client to it"""

    #This is a temporary arrangement, to be replaced with LMFDB connection
    log_dest.info("Getting db client")
    global int_client, _auth_as_edit, _auth_on_remote
    if(int_client and _auth_as_edit == editor and _auth_on_remote == remote):
	return True
    try:
        if remote:
            #Attempt to connect to LMFDB
            from lmfdb.base import getDBConnection
            int_client=getDBConnection()
            return True
        else:
            int_client = MongoClient("localhost", 27017)
#           int_client = MongoClient("localhost", 37010)
            return True

#       Below was old way of doing auth. To be removed when working
#        pw_dict = yaml.load(open("passwords.yaml"))
        #if editor:
        #    key = 'data'
        #    auth_db = 'inventory'
        #else:
        #    key = 'default'
        #    auth_db = 'admin'
#        auth_db = 'inventory'
#        int_client[auth_db].authenticate(pw_dict[key]['username'], pw_dict[key]['password'])
#        int_client[auth_db].authenticate(pw_dict['webserver']['username'], pw_dict['webserver']['password'])
#        int_client[auth_db].authenticate(pw_dict['data']['username'], pw_dict['data']['password'])

    except Exception as e:
        log_dest.error("Error setting up connection "+str(e))
        int_client = None
        return(False)
    _auth_as_edit = editor
    _auth_on_remote = remote
    return True

#Structure helpers -----------------------------------------------------------------------
def get_inv_db_name():
    """ Get name of inventory db"""

    return ALL_STRUC.name

def get_inv_table_names():
    """ Get names of all inventory db tables (collections) """

    names = []
    for key in dir(ALL_STRUC):
        value = getattr(ALL_STRUC, key)
        if isinstance(value, dict) and STR_NAME in value and STR_CONTENT in value:
            names.append(value[STR_NAME])
    return names

def validate_mongodb(db):
    """Validates the db and collection names in db against expected structure"""
    n_colls = 0
    try:
        if db.name != get_inv_db_name():
            raise KeyError('name')
        colls = db.collection_names()
        tables = get_inv_table_names()
        for coll in colls:
            #Should contain only known tables and maybe some other admin ones.
            if coll not in tables and not 'system.' in coll:
                raise KeyError(coll)
            elif coll in tables:
                n_colls += 1
        if n_colls != ALL_STRUC.n_colls and n_colls != 0:
            raise ValueError('n_colls')
    except:
        # Exception as e:
        return False
    return True

#End structure helpers -------------------------------------------------------------------
#Other data and form helpers -------------------------------------------------------------

def get_type_strings():
    """ Get list of basic known data types """

    base_types = sorted(["real", "integer", "string", "boolean", "mixed types"])
    pre_qualifier = ["", "collection of ", "comma separated list of "]
    post_qualifier = ["", " stored as string"]

    #Entire available types are then all combos of base type plus optional pre and optional post
    type_list = []
    #Create cartesian product.
    #Loop ordering is to produce all roots first, then all prefixed, then postfixed
    for postfix in post_qualifier:
        for prefix in pre_qualifier:
            for item in base_types:
                type_list.append(prefix + item + postfix)

    #Manually remove pathological combos
    final_type_list = [item for item in type_list if "string stored as string" not in item]
    return final_type_list

def get_type_strings_as_json():
    """ Get basic data types as a json string """

    encoder = json.JSONEncoder()
    json_text = encoder.encode(get_type_strings())
    return json_text

#End other data and form helpers ---------------------------------------------------------

#Logging and runtime helpers--------------------------------------------------------------
#This is intended to log the DB code side messages and not the web-front stuff, which flask handles

#This is a log of actions, submits, failures etc
LOG_ID = 'Inv_log'
LOG_FILE_NAME = "LMFDBinventory.log"
LEVELS = {'debug': logging.DEBUG,
      'info': logging.INFO,
      'warning': logging.WARNING,
      'error': logging.ERROR,
      'critical': logging.CRITICAL}
log_dest = None

#This is a list of edit transactions
TR_LOG_ID = 'Trans_log'
TR_LOG_FILE_NAME = "LMFDBtransactions_inv.log"
log_transac = None

#To disable all logging etc, can just replace the filehandler with Nullhandler
def init_run_log(level_name=None):
    """ Initialise logger for db actions """

    global log_dest
    log_dest = logging.getLogger(LOG_ID)

    if level_name:
        level = LEVELS.get(level_name, logging.NOTSET)
        log_dest.setLevel(level)

    #Add handler only if not already present
    if not len(log_dest.handlers):
        log_file_handler = logging.FileHandler(LOG_FILE_NAME)
        formatter = logging.Formatter( "%(asctime)s | %(pathname)s:%(lineno)d | %(funcName)s | %(levelname)s | %(message)s ")
        log_file_handler.setFormatter(formatter)
        log_dest.addHandler(log_file_handler)

    if level_name:
        #Print the level change in warning or above mode
        log_dest.warning("Set level to "+level_name)


def init_transac_log(level_name=None):
    """ Initialise logger for db transactions """

    global log_transac
    log_transac = logging.getLogger(TR_LOG_ID)

    if level_name:
        level = LEVELS.get(level_name, logging.NOTSET)
        log_transac.setLevel(level)

    #Add handler only if not already present
    if not len(log_transac.handlers):
        #log_file_handler = logging.FileHandler(TR_LOG_FILE_NAME)
        log_file_handler = logging.handlers.RotatingFileHandler(TR_LOG_FILE_NAME, maxBytes=1024, backupCount=2)
        formatter = logging.Formatter( "%(asctime)s | %(pathname)s:%(lineno)d | %(levelname)s | %(message)s ")
        log_file_handler.setFormatter(formatter)
        log_transac.addHandler(log_file_handler)


    if level_name:
        #Print the level change in debug mode
        log_transac.debug("Set level to "+level_name)

#End logging and runtime helpers----------------------------------------------------------
