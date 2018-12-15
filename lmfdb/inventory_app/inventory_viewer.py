
import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc
#from inventory_db_inplace import update_fields
from inventory_live_data import get_lockout_state
from scrape_helpers import check_scrapes_by_table_id
from collections import defaultdict
from lmfdb.utils import comma
from lmfdb.db_backend import db

#Functions to populate viewer pages

def is_valid_db(db_name):
    return is_valid_db_table(db_name, None)

def is_valid_db_table(db_name, table_name):
    """Check if db and table_name name (if not None) exist"""
    try:
        db_id = idc.get_db_id(db_name)
        if db_id is None:
            return False
        if table_name:
            table_id = idc.get_table_id(table_name)
            if table_id is None:
                return False
    except Exception as e:
        inv.log_dest.error('Failed checking existence of '+db_name+' '+str(table_name)+' '+str(e))
        return False
    return True

def get_nicename(db_name, table_name):
    """Return the nice_name string for given db/table pair"""
    try:
        if table_name:
            return idc.get_table(table_name)['nice_name']
        else:
            return idc.get_db(db_name)['nice_name']
    except Exception as e:
        inv.log_dest.error('Failed to get nice name for '+db_name+' '+table_name+' '+str(e))
        #Can't return nice name so return None
        return None

def retrieve_db_listing(db_name=None):
    """Retrieve listing for all or given database.

    db_name -- If absent, get listing of all dbs, if present, get listing of tables in named db
    """
    try:
        if db_name is None:
            #query = {}
            records = list(db.inv_dbs.search({}, ['name', 'nice_name']))
            counts = defaultdict(int)
            for tablename in db.tablenames:
                dbname = tablename.split('_')[0]
                counts[dbname] += 1
            records = [(rec['name'], rec['nice_name'], counts[rec['name']]) for rec in records]
        else:
            db_id = idc.get_db_id(db_name)
            records = list(db.inv_tables.search({'db_id': db_id},
                                                ['_id', 'name', 'nice_name', 'status']))
            records = [(rec['name'], rec['nice_name'],
                        comma(db[rec['name']].count()),
                        ih.code_to_status(rec['status']), check_locked(rec['_id'])) for rec in records]
        return sorted(records, key=lambda s: s[0].lower())
    except Exception as e:
        inv.log_dest.error("Something went wrong retrieving db info "+str(e))
        raise
        return None

def retrieve_description(requested_table):
    """Retrieve inventory for named table

    requested_table -- name of table to fetch inventory for
    """

    try:
        table_record = idc.get_table(requested_table)
        tid = table_record['_id']
        info = table_record['INFO']

        info['nice_name'] = table_record['nice_name']
        specials = {'INFO': info, 'NOTES':table_record['NOTES']}
        request = {'table_id': tid}
        descr_auto = db.inv_fields_auto.search(request)
        descr_human = db.inv_fields_human.search(request)

        return {'data':patch_records(descr_auto, descr_human), 'specials': specials, 'scrape_date':table_record['scan_date']}

    except Exception as e:
        inv.log_dest.error("Error retrieving inventory "+requested_table+' '+str(e))
        return {'data':None, 'specials':None, 'scrape_date':None}

def patch_records(first, second):
    """Patch together human and auto generated records.
    first, second -- Cursors to patch together, entry by entry. Any not None entries in the second list override those in the first
    """
    try:
        dic_first = {item['name']:item['data'] for item in first}
        dic_second = {item['name']:item['data'] for item in second}
    except Exception as e:
        inv.log_dest.error("Possible error unpacking results "+str(e))
    dic_patched = dic_first.copy()

    #Patch the not-None from second in
    for key in dic_second:
        for field in dic_second[key]:
            if dic_second[key][field] is not None and key in dic_patched:
                dic_patched[key][field] = dic_second[key][field]

    #Make sure the patched version contains all the mandatory fields with empty values
    for key in dic_patched:
        for field in inv.base_editable_fields:
            if field not in dic_patched[key]:
                dic_patched[key][field] = ''
    return dic_patched

def get_inventory_for_display(table_name):
    """ Get inventory description """
    try:
        records = retrieve_description(table_name)
    except Exception as e:
        inv.log_dest.error("Unable to get requested inventory "+ str(e))
        return {'data': None, 'specials': None, 'scrape_date': None}

    try:
        return {'data':ih.escape_for_display(records['data']), 'specials':ih.escape_for_display(records['specials']), 'scrape_date':records['scrape_date']}
    except Exception as e:
        inv.log_dest.error("Error decoding inventory object "+ str(e))
        return {'data': None, 'specials': None, 'scrape_date': None}

def get_indices_for_display(table_name):
    records = db[table_name].list_indexes()
    # has keys type, columns, modifiers
    return {'data':[{'name':name,'keys':ind['columns'],'type':ind['type']} for name, ind in records.items()]}

#Functions to deal with edit submissions -----------------------------------------------------------

def apply_edits(diff):
    """ Apply edits as a diff
    Use for applying edits from exports etc. Copy is explicitly made
    Note there is also apply_rollback for rollbacks
    """
    raise NotImplementedError
#    diff_to_apply = deepcopy(diff)
#    try:
#        validate_edits(diff_to_apply) #This throws custom exceptions
#        diff_to_apply = process_edits(diff_to_apply)
#        update_fields(diff_to_apply)
#    except Exception as e:
#        inv.log_dest.error("Error in edit validation or apply "+str(e))
#        raise e


def apply_submitted_edits(response):
    """ Attempt to apply edits submitted as a diffs object via web, i.e member of response obj
    """
    raise NotImplementedError
#    try:
#        inv.log_transac.info(str(response.referrer)+' : '+str(response.data))
#    except Exception as e:
#        #If we can't log the attempt, we can still maybe log the failure. Perhaps data is missing etc
#        inv.log_transac.error("Failed to log transaction "+str(e))
#
#    #Validate the response and if good pass to the DB interface code
#    try:
#        decoder = json.JSONDecoder()
#        resp_str = decoder.decode(response.data)
#    except Exception as e:
#        inv.log_dest.error("Error decoding edits "+str(e))
#        raise DiffDecodeError(str(e))
#
#    try:
#        check_locks(resp_str) # Throws custom error if locked
#        validate_edits(resp_str) #This throws custom exceptions
#        resp_str = process_edits(resp_str)
#        update_fields(resp_str)
#    except Exception as e:
#        #Log and re-raise
#        inv.log_dest.error("Error in edit validation "+str(e))
#        raise e

def validate_edits(diff):
    """This checks we've got a valid diffs object that we can pass off to DB interface"""
    raise NotImplementedError
    #We throw custom exceptions, and catch and rethrow anything else, so that we can access the errcode to look up info
    #        inv.log_dest.info("Updating descriptions for " + diff["db"]+'.'+diff["collection"])
    #        _id = get_db(db, diff["db"])
    #          for change in diff["diffs"]:
#    try:
#        tmp = diff["db"]
#        assert(tmp is not None)
#        tmp = diff["collection"]
#        #Collection can be null in some edge cases
#        tmp = diff["diffs"]
#        assert(tmp is not None)
#    except KeyError as e:
#        raise DiffKeyError(e.message)
#    except (AssertionError, TypeError) as e:
#        raise DiffBadType(e.message)
#    except Exception as e:
#        raise DiffUnknownError(e.message)
#
#    if not isinstance(diff["db"], basestring):
#        raise DiffBadType("db")
#    #Collection can be none in case of Db info edits
##    if not isinstance(diff["collection"], basestring):
##        raise DiffBadType("collection")
#    if isinstance(diff["diffs"], basestring):
#        raise DiffBadType("diffs (str)")
#
#    diffs = diff["diffs"]
#    try:
#        iter(diffs)
#    except TypeError as e:
#        raise DiffBadType("diffs (not iterable)")
#    except Exception as e:
#        raise DiffUnknownError(e.message)
#    #We want diffs to be specifically an iterable of things each containing item, field, content triplets
#
#    try:
#        for diff_item in diffs :
#            a = diff_item['item']
#            assert(a is not None)
#            a = diff_item['field']
#            assert(a is not None)
#            a = diff_item['content']
#            assert(a is not None)
#    except (TypeError, KeyError) as e:
#        raise DiffBadType("diffs (triplet errors)"+e.message)
#    except Exception as e:
#        raise DiffUnknownError(e.message)

def process_edits(diff):
    raise NotImplementedError
##This has to reverse anything we did to display info
##We also edit the diff if there's anything to be done
#
#    diffs = diff["diffs"]
#    for index, diff_item in enumerate(diffs):
#        if diff_item['field'] == "example":
#            str = diff_item['content']
#            str = ih.transform_examples(str, True)
#            inv.log_dest.info(str)
#            diffs[index]['content'] = str
#
#    #We allow editing of nice_names in two ways, so we patch the diff accordingly here
#    #If current state is {"item":"__INFO__","field":"nice_name"... we want to change __INFO__ to 'top_level'
#    for index, diff_item in enumerate(diffs):
#        if diff_item['item'] == '__INFO__' and diff_item['field'] == 'nice_name':
#            diff_item['item'] = 'top_level'
#            if not ih.is_toplevel_field(diff_item['item']):
#                raise DiffKeyError("Cannot identify top-level state")
#
#    return diff

# Check for locks on table before applying
def check_locked(table_id):
    return check_scrapes_by_table_id(table_id)

def check_locks(resp):
    """Check if request pertains to locked table
    or editing is locked globally
    """
    if get_lockout_state():
        raise EditLockError('Global Edit Lock')
    try:
        #db_name = resp['db']
        table_name = resp['table']
        #db_id = idc.get_db_id(db_name)
        table_id = idc.get_table_id(table_name)
        if check_locked(table_id):
            raise EditLockError('Table locked')
    except Exception as e:
        inv.log_dest.error("Error in locking "+str(e))
        raise e

#  Custom exceptions for diff validation ++++++++++++++++++++++++++++++++++

class DiffKeyError(KeyError):
    """Raise in place of KeyError for edit diffs"""
    errcode = 1
    def __init__(self, message):
        mess = "Cannot access key "+message+" in diff"
        super(KeyError, self).__init__(mess)

class DiffBadType(TypeError):
    """Raise in place of TypeError for edit diffs"""
    errcode = 2
    def __init__(self, message):
        mess = "Invalid type for diff field "+message
        super(TypeError, self).__init__(mess)

class DiffDecodeError(ValueError):
    """Raise in place of ValueError for edit diffs"""
    errcode = 4
    def __init__(self, message):
        mess = "Diffs cannot be decoded "+message
        super(ValueError, self).__init__(mess)

class DiffCollideError(RuntimeError):
    """Raise when two diff submissions irreparably collide"""
    errcode = 8
    def __init__(self, message):
        mess = "Edits collided "+message
        super(RuntimeError, self).__init__(mess)

class EditLockError(RuntimeError):
    """Use when editing is locked"""
    errcode = 16
    def __init__(self, message):
        mess = message
        super(RuntimeError, self).__init__(mess)

class DiffUnknownError(RuntimeError):
    """Raise for errors not otherwise specified"""
    errcode = 32
    def __init__(self, message):
        mess = "Unknown error "+message
        super(RuntimeError, self).__init__(mess)

err_registry = {1:DiffKeyError(" "), 2:DiffBadType(""), 4:DiffDecodeError(""), 8:DiffCollideError(""), 16:EditLockError(""), 32:DiffUnknownError("")}

#   End custom exceptions for diff validation


#End functions to deal with edit submissions -------------------------------------------------------

if __name__ == "__main__":
    listing = retrieve_db_listing()
    for item in listing:
        print(item)
        table_listing = retrieve_db_listing(item)
        print("   " + str(table_listing))

#print json.dumps({'4': 5, '6': 7}, sort_keys=True,
#...                  indent=4, separators=(',', ': '))

    import random
    random.seed()
    item = random.choice(listing)
    table_listing = retrieve_db_listing(item)
    table_item = random.choice(table_listing)
    print('_________________________________________')
    print("Getting for "+ str(table_item))
    print(json.dumps(get_inventory_for_display(table_item), indent=4, separators=(',', ': ')))

else:
    #Setup the edit transactions logger
    #Swap out info for debug etc
    inv.init_transac_log(level_name='warning')
