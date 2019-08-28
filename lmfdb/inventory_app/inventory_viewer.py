import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc
from inventory_db_inplace import update_fields
from inventory_live_data import get_lockout_state
from scrape_helpers import check_scrapes_by_coll_id
from copy import deepcopy
from lmfdb.utils import comma
from lmfdb.backend.database import db

#Functions to populate viewer pages

def is_valid_db(db_name):

    return is_valid_db_collection(db_name, None)

def is_valid_db_collection(db_name, collection_name):
    """Check if db and collection name (if not None) exist"""
    try:
        db_id = idc.get_db_id(db_name)
        if not db_id['exist']:
            return False
        if collection_name:
            coll_id = idc.get_coll_id(db_id['id'], collection_name)
            if not coll_id['exist']:
                return False
    except:
        return False
    return True

def get_nicename(db_name, collection_name):
    """Return the nice_name string for given db/coll pair"""

    try:
        if collection_name:
            db_id = idc.get_db_id(db_name)
            coll_rec = idc.get_coll(db_id['id'], collection_name)
            nice_name = coll_rec['data']['nice_name']
        else:
            db_rec = idc.get_db(db_name)
            #print db_rec
            nice_name = db_rec['data']['nice_name']
        return nice_name
    except:
        #Can't return nice name so return None
        return None

def gen_retrieve_db_listing(db_name=None):
    """Retrieve listing for all or given database.

    db_name -- If absent, get listing of all dbs, if present, get listing of collections in named db

    NB connection must have been setup and checked!
    """

    table_name = 'inv_dbs'
    coll_name = 'inv_tables'
    try:
        table = db[table_name]
        if db_name is None:
            query = {}
            records = list(table.search(query, {'_id': 1, 'name' : 1, 'nice_name':1}))
            records = [(rec['name'], rec['nice_name'], idc.count_colls(rec['_id'])) for rec in records]
        else:
            _id = idc.get_db_id(db_name)['id']
            table = db[coll_name]
            query = {'db_id':_id}
            records = list(table.search(query, {'_id': 1, 'name' : 1, 'nice_name':1, 'status':1}))
            records = [(rec['name'], rec['nice_name'], 0, ih.code_to_status(rec['status']), False) for rec in records]
    except:
        records = None
    if records is not None:
        return sorted(records, key=lambda s: s[0].lower())
    else:
        return records

def retrieve_db_listing(db_name=None):
    """Retrieve listing for all or given database."""

    return gen_retrieve_db_listing(db_name)

def get_edit_list(db_name=None):
    """Retrieve listing for all or given database."""

    listing = retrieve_db_listing(db_name)
    return listing

def retrieve_description(requested_db, requested_coll):
    """Retrieve inventory for named collection

    requested_db -- name of database the named collection belongs to
    requested_coll -- name of collection to fetch inventory for
    """

    try:
        _id = idc.get_db(requested_db)['id']
        coll_record = idc.get_coll(_id, requested_coll)
        _c_id = coll_record['id']
        info = coll_record['data']['INFO']

        info['nice_name'] = coll_record['data']['nice_name']
        specials = {'INFO': info, 'NOTES':coll_record['data']['NOTES']}
        request = {'table_id': _c_id}

        fields_auto = 'inv_fields_auto'
        fields_human ='inv_fields_human'

        descr_auto = db[fields_auto].search(request)

        descr_human = db[fields_human].search(request)

        return {'data':patch_records(descr_auto, descr_human), 'specials': specials, 'scrape_date':coll_record['data']['scan_date']}

    except:
        return {'data':None, 'specials':None, 'scrape_date':None}

def patch_records(first, second):
    """Patch together human and auto generated records.

    first, second -- Cursors to patch together, entry by entry. Any not None entries in the second list override those in the first
    """
    patched = list(first)
    try:
      for el,val in enumerate(patched):
        if val.get('cname',None): patched[el]['data']['cname'] = val['cname']
        if val.get('schema',None): patched[el]['data']['schema'] = val['schema']
    except:
        pass
    try:
        dic_first = {item['name']:item['data'] for item in patched}
        dic_second = {item['name']:item['data'] for item in second}
    except:
        pass
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

def retrieve_records(requested_db, requested_coll):
    """Retrieve inventory for named collection

    requested_db -- name of database the named collection belongs to
    requested_coll -- name of collection to fetch inventory for
    """

    return {'data':None, 'specials':None, 'scrape_date':None}

def retrieve_indices(requested_db, requested_coll):
    """Retrieve indices for named collection

    db -- LMFDB connection to inventory db
    requested_db -- name of database the named collection belongs to
    requested_coll -- name of collection to fetch inventory for
    """

    return {'data':None, 'specials':None, 'scrape_date':None}

def get_inventory_for_display(full_name):
    """ Get inventory description

    full_name -- fully qualified name, in form db.coll
    """

    try:
        parts = ih.get_description_key_parts(full_name)
        records = retrieve_description(parts[0], parts[1])
    except:
        return {'data': None, 'specials': None, 'scrape_date': None}

    try:
        return {'data':ih.escape_for_display(records['data']), 'specials':ih.escape_for_display(records['specials']), 'scrape_date':records['scrape_date']}
    except:
        return {'data': None, 'specials': None, 'scrape_date': None}

def get_records_for_display(full_name):
    """ Get records descriptions

    full_name -- fully qualified name, in form db.coll
    """

    try:
        parts = ih.get_description_key_parts(full_name)
        records = retrieve_records(parts[0], parts[1])
    except:
        return {'data': None, 'scrape_date': None}

    try:
        return {'data':ih.diff_records(records['data']), 'scrape_date' : records['scrape_date']}
    except:
        return {'data': None, 'scrape_date': None}

def get_indices_for_display(full_name):
    """ Get indices descriptions

    full_name -- fully qualified name, in form db.coll
    """
    try:
        parts = ih.get_description_key_parts(full_name)
        records = retrieve_indices(parts[0], parts[1])
    except:
        return {'data': None, 'scrape_date': None}

    try:
        return {'data':records['data'], 'scrape_date' : records['scrape_date']}
    except:
        return {'data': None, 'scrape_date': None}

def collate_collection_info(db_name):
    """Fetches and collates viewable info for collections in named db
    """

    db_info = idc.get_db(db_name)
    if not db_info['exist']:
        return
    colls_info = idc.get_all_colls(db_info['id'])

    for coll in colls_info:
        rec_info = idc.count_records_and_types(db, coll['_id'])
        coll['records'] = comma(rec_info)

    return colls_info

#Functions to deal with edit submissions -----------------------------------------------------------

def apply_edits(diff):
    """ Apply edits as a diff
    Use for applying edits from exports etc. Copy is explicitly made
    Note there is also apply_rollback for rollbacks
    """
    diff_to_apply = deepcopy(diff)
    try:
        validate_edits(diff_to_apply) #This throws custom exceptions
        diff_to_apply = process_edits(diff_to_apply)
        update_fields(diff_to_apply)
    except Exception as e:
        raise e


def apply_submitted_edits(response):
    """ Attempt to apply edits submitted as a diffs object via web, i.e member of response obj
    """

    #Validate the response and if good pass to the DB interface code
    try:
        decoder = json.JSONDecoder()
        resp_str = decoder.decode(response.data)
    except Exception as e:
        raise DiffDecodeError(str(e))

    try:
#        check_locks(resp_str) # Throws custom error if locked
        validate_edits(resp_str) #This throws custom exceptions
        resp_str = process_edits(resp_str)
        update_fields(resp_str)
    except Exception as e:
        #Log and re-raise
#        inv.log_dest.error("Error in edit validation "+str(e))
        raise e

def validate_edits(diff):
    """This checks we've got a valid diffs object that we can pass off to DB interface"""
    #We throw custom exceptions, and catch and rethrow anything else, so that we can access the errcode to look up info
    #        inv.log_dest.info("Updating descriptions for " + diff["db"]+'.'+diff["collection"])
    #        _id = get_db(db, diff["db"])
    #          for change in diff["diffs"]:
    try:
        tmp = diff["db"]
        assert(tmp is not None)
        tmp = diff["collection"]
        #Collection can be null in some edge cases
        tmp = diff["diffs"]
        assert(tmp is not None)
    except KeyError as e:
        raise DiffKeyError(e.message)
    except (AssertionError, TypeError) as e:
        raise DiffBadType(e.message)
    except Exception as e:
        raise DiffUnknownError(e.message)

    if not isinstance(diff["db"], basestring):
        raise DiffBadType("db")
    #Collection can be none in case of Db info edits
#    if not isinstance(diff["collection"], basestring):
#        raise DiffBadType("collection")
    if isinstance(diff["diffs"], basestring):
        raise DiffBadType("diffs (str)")

    diffs = diff["diffs"]
    try:
        iter(diffs)
    except TypeError as e:
        raise DiffBadType("diffs (not iterable)")
    except Exception as e:
        raise DiffUnknownError(e.message)
    #We want diffs to be specifically an iterable of things each containing item, field, content triplets

    try:
        for diff_item in diffs :
            a = diff_item['item']
            assert(a is not None)
            a = diff_item['field']
            assert(a is not None)
            a = diff_item['content']
            assert(a is not None)
    except (TypeError, KeyError) as e:
        raise DiffBadType("diffs (triplet errors)"+e.message)
    except Exception as e:
        raise DiffUnknownError(e.message)

def process_edits(diff):
#This has to reverse anything we did to display info
#We also edit the diff if there's anything to be done

    diffs = diff["diffs"]
    for index, diff_item in enumerate(diffs):
        if diff_item['field'] == "example":
            str = diff_item['content']
            str = ih.transform_examples(str, True)
            diffs[index]['content'] = str

    #We allow editing of nice_names in two ways, so we patch the diff accordingly here
    #If current state is {"item":"__INFO__","field":"nice_name"... we want to change __INFO__ to 'top_level'
    for index, diff_item in enumerate(diffs):
        if diff_item['item'] == '__INFO__' and diff_item['field'] == 'nice_name':
            diff_item['item'] = 'top_level'
            if not ih.is_toplevel_field(diff_item['item']):
                raise DiffKeyError("Cannot identify top-level state")

    return diff

# Check for locks oncoll before applying
def check_locked(coll_id):
    return check_scrapes_by_coll_id(coll_id)

def check_locks(resp):
    """Check if request pertains to locked coll
    or editing is locked globally
    """
    if get_lockout_state():
        raise EditLockError('Global Edit Lock')
    try:
        db_name = resp['db']
        coll_name = resp['collection']
        db_id = idc.get_db_id(db_name)
        coll_id = idc.get_coll_id(db_id['id'], coll_name)
        if check_locked(coll_id['id']):
            raise EditLockError('Collection locked')
    except Exception as e:
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
