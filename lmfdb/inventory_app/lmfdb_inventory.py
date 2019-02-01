import json
import logging, logging.handlers

#Contains the general data and functions for all inventory handling

__version__ = '0.3.0'

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
base_editable_fields = {'type':1, 'description':2, 'example':3, 'nulls':-4}
#Negative denotes NOT editable
def display_field_order():
    return sorted(base_editable_fields, key=lambda s: abs(base_editable_fields.get(s)))

info_editable_fields = {'nice_name':1, 'description':2, 'contact':4, 'status':3, 'code':5}
def info_field_order():
    return sorted(info_editable_fields, key=info_editable_fields.get)

index_fields = {'name':-1, 'keys':-2, 'type':-3}
#Negative denotes NOT editable
def index_field_order():
    return sorted(index_fields, key = lambda s : abs(index_fields.get(s)))

table_status = {0: 'live', 1:'ops', 2:'beta', 4: 'old', 5:'gone'}
#Live is normal. Ops includes any stats, rand etc. Beta is beta status, not yet on prod
#Old means deprecated. Probably want to show only live and beta, and flag beta
#Gone means a table in inventory which is no longer in live data
#Object describing DB structure. This is styled after a relational model
class db_struc:
    name = 'inventory'
    n_tables = 6
    db_ids = {STR_NAME : 'inv_dbs', STR_CONTENT : ['_id', 'name', 'nice_name']}
    table_ids = {STR_NAME : 'inv_tables', STR_CONTENT :['_id', 'db_id', 'name', 'nice_name', 'NOTES', 'INFO', 'scan_date', 'status']}
    fields_auto = {STR_NAME : 'inv_fields_auto', STR_CONTENT : ['_id', 'table_id', 'name', 'data']}
    fields_human = {STR_NAME : 'inv_fields_human', STR_CONTENT : ['_id', 'table_id', 'name', 'data']}
    rollback_human = {STR_NAME : 'inv_rollback', STR_CONTENT:['diff']}
    ops = {STR_NAME : 'inv_ops', STR_CONTENT:[]} #Ops has no fixed format
    def get_fields(self, which):
        if which =='auto':
            return self.fields_auto
        elif which == 'human':
            return self.fields_human
        else:
            return None

    def get_table(self, which):
        """Get table content from name
        """
        if which =='auto':
            return self.fields_auto
        elif which == 'human':
            return self.fields_human
        elif which == 'records':
            return self.record_types
        elif which == 'indices' or which == 'indexes':
            return self.indexes
        else:
            return None


#Constant instance of db_struct
ALL_STRUC = db_struc()

#Structure helpers -----------------------------------------------------------------------
def get_inv_table_names():
    """ Get names of all inventory db tables """

    names = []
    for key in dir(ALL_STRUC):
        value = getattr(ALL_STRUC, key)
        if isinstance(value, dict) and STR_NAME in value and STR_CONTENT in value:
            names.append(value[STR_NAME])
    return names

#End structure helpers -------------------------------------------------------------------
#Other data and form helpers -------------------------------------------------------------

def get_type_strings():
    """ Get list of basic known data types """

    base_types = sorted(["real", "integer", "string", "boolean", "mixed types"])
    pre_qualifier = ["", "table of ", "comma separated list of "]
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
LOG_FILE_NAME = "logs/LMFDBinventory.log"
LEVELS = {'debug': logging.DEBUG,
      'info': logging.INFO,
      'warning': logging.WARNING,
      'error': logging.ERROR,
      'critical': logging.CRITICAL}
log_dest = None

#This is a list of edit transactions
TR_LOG_ID = 'Trans_log'
TR_LOG_FILE_NAME = "logs/LMFDBtransactions_inv.log"
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
