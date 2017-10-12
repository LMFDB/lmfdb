
import json
import inventory_helpers as ih
import lmfdb_inventory as inv
import inventory_db_core as idc
from inventory_db_inplace import update_fields

#Functions to populate viewer pages
def get_nicename(db_name, collection_name):
    """Return the nice_name string for given db/coll pair"""

    try:
        inv.setup_internal_client()
        db = inv.int_client[inv.ALL_STRUC.name]
        if collection_name:
            db_id = idc.get_db_id(db, db_name)
            coll_rec = idc.get_coll(db, db_id['id'], collection_name)
            nice_name = coll_rec['data']['nice_name']
        else:
            db_rec = idc.get_db(db, db_name)
            print db_rec
            nice_name = db_rec['data']['nice_name']
        return nice_name
    except Exception as e:
        inv.log_dest.error('Failed to get nice name for '+db_name+' '+collection_name+' '+str(e))
        #Can't return nice name so return None
        return None

def gen_retrieve_db_listing(db, db_name=None):
    """Retrieve listing for all or given database.

    db -- LMFDB connection to inventory db
    db_name -- If absent, get listing of all dbs, if present, get listing of collections in named db
    """

    table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
    coll_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
    try:
        table = db[table_name]
        if db_name is None:
            query = {}
            records = list(table.find(query, {'_id': 0, 'name' : 1, 'nice_name':1}))
            records = [(rec['name'], rec['nice_name']) for rec in records]
        else:
            _id = table.find_one({inv.STR_NAME:db_name})['_id']
            table = db[coll_name]
            query = {inv.ALL_STRUC.coll_ids[inv.STR_CONTENT][1]:_id}
            records = list(table.find(query, {'_id': 0, 'name' : 1, 'nice_name':1}))
            records = [(rec['name'], rec['nice_name']) for rec in records]
    except Exception as e:
        inv.log_dest.error("Something went wrong retrieving db info "+str(e))
        records = None
    if records is not None:
        return sorted(records, key=lambda s: s[0].lower())
    else:
        return records

def retrieve_db_listing(db_name=None):
    """Retrieve listing for all or given database."""

    inv.setup_internal_client()
    db = inv.int_client[inv.ALL_STRUC.name]
    return gen_retrieve_db_listing(db, db_name)

def get_edit_list(db_name=None):
    """Retrieve listing for all or given database."""

    listing = retrieve_db_listing(db_name)
    return listing

def retrieve_description(db, requested_db, requested_coll):
    """Retrieve inventory for named collection

    db -- LMFDB connection to inventory db
    requested_db -- name of database the named collection belongs to
    requested_coll -- name of collection to fetch inventory for
    """

    table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
    coll_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
    try:
        db_tab = db[table_name]
        coll_tab = db[coll_name]
        _id = db_tab.find_one({inv.STR_NAME:requested_db})['_id']
        coll_record = coll_tab.find_one({'db_id': _id, inv.STR_NAME:requested_coll})
        _c_id = coll_record['_id']
        info = coll_record['INFO']
        info['nice_name'] = coll_record['nice_name']
        specials = {'INFO': info, 'NOTES':coll_record['NOTES']}
        request = {'coll_id': _c_id}

        fields_auto = inv.ALL_STRUC.get_fields('auto')
        fields_human = inv.ALL_STRUC.get_fields('human')

        collection = db[fields_auto[inv.STR_NAME]]
        descr_auto = collection.find(request)

        collection = db[fields_human[inv.STR_NAME]]
        descr_human = collection.find(request)

        return {'data':patch_records(descr_auto, descr_human), 'specials': specials, 'scrape_date':coll_record['data']['scan_date']}

    except Exception as e:
        inv.log_dest.error("Error retrieving inventory "+requested_db+'.'+requested_coll+' '+str(e))
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

def retrieve_records(db, requested_db, requested_coll):
    """Retrieve inventory for named collection

    db -- LMFDB connection to inventory db
    requested_db -- name of database the named collection belongs to
    requested_coll -- name of collection to fetch inventory for
    """

    table_name = inv.ALL_STRUC.db_ids[inv.STR_NAME]
    coll_name = inv.ALL_STRUC.coll_ids[inv.STR_NAME]
    try:
        db_tab = db[table_name]
        coll_tab = db[coll_name]
        _id = db_tab.find_one({inv.STR_NAME:requested_db})['_id']
        coll_record = coll_tab.find_one({'db_id': _id, inv.STR_NAME:requested_coll})
        _c_id = coll_record['_id']

        records = idc.get_all_records(db, _c_id)
        return {'data':ih.empty_null_record_info(records['data']), 'scrape_date':coll_record['scan_date']}

    except Exception as e:
        inv.log_dest.error("Error retrieving inventory "+requested_db+'.'+requested_coll+' '+str(e))
        return {'data':None, 'specials':None, 'scrape_date':None}

def get_inventory_for_display(full_name):
    """ Get inventory description

    full_name -- fully qualified name, in form db.coll
    """

    inv.setup_internal_client()
    db = inv.int_client[inv.ALL_STRUC.name]
    parts = ih.get_description_key_parts(full_name)
    try:
        records = retrieve_description(db, parts[0], parts[1])
    except Exception as e:
        inv.log_dest.error("Unable to get requested inventory "+ str(e))
        return {'data': None, 'specials': None, 'scrape_date': None}

    try:
        return {'data':ih.escape_for_display(records['data']), 'specials':ih.escape_for_display(records['specials']), 'scrape_date':records['scrape_date']}
    except Exception as e:
        inv.log_dest.error("Error decoding inventory object "+ str(e))
        return {'data': None, 'specials': None, 'scrape_date': None}

def get_records_for_display(full_name):
    """ Get records descriptions

    full_name -- fully qualified name, in form db.coll
    """

    inv.setup_internal_client()
    db = inv.int_client[inv.ALL_STRUC.name]
    parts = ih.get_description_key_parts(full_name)
    try:
        records = retrieve_records(db, parts[0], parts[1])
    except Exception as e:
        inv.log_dest.error("Unable to get requested inventory "+ str(e))
        return {'data': None, 'scrape_date': None}

    try:
        return {'data':ih.diff_records(records['data']), 'scrape_date' : records['scrape_date']}
    except Exception as e:
        inv.log_dest.error("Error decoding inventory object "+ str(e))
        return {'data': None, 'scrape_date': None}

#Functions to deal with edit submissions -----------------------------------------------------------

def apply_submitted_edits(response):
    """ Apply edits submitted as a diffs object


    Can
    """
    try:
        inv.log_transac.info(str(response.referrer)+' : '+str(response.data))
    except Exception as e:
        #If we can't log the attempt, we can still maybe log the failure. Perhaps data is missing etc
        inv.log_transac.error("Failed to log transaction "+str(e))

    #Validate the response and if good pass to the DB interface code
    try:
        decoder = json.JSONDecoder()
        resp_str = decoder.decode(response.data)
    except Exception as e:
        inv.log_dest.error("Error decoding edits "+str(e))
        raise DiffDecodeError(str(e))

    try:
        validate_edits(resp_str) #This throws custom exceptions
        resp_str = process_edits(resp_str)
        update_fields(resp_str)
    except Exception as e:
        inv.log_dest.error("Error in edit validation "+str(e))
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
        assert(tmp is not None)
        tmp = diff["diffs"]
        assert(tmp is not None)
    except KeyError as e:
        raise DiffKeyError(e.message)
    except TypeError as e:
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
            inv.log_dest.info(str)
            diffs[index]['content'] = str

    #We allow editing of nice_names in two ways, so we patch the diff accordingly here
    #If current state is {"item":"__INFO__","field":"nice_name"... we want to change __INFO__ to 'top_level'
    for index, diff_item in enumerate(diffs):
        if diff_item['item'] == '__INFO__' and diff_item['field'] == 'nice_name':
            diff_item['item'] = 'top_level'
            if not ih.is_toplevel_field(diff_item['item']):
                raise DiffKeyError("Cannot identify top-level state")

    return diff

#  Custom exceptions for diff validation


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

class DiffUnknownError(RuntimeError):
    """Raise for errors not otherwise specified"""
    errcode = 16
    def __init__(self, message):
        mess = "Unknown error "+message
        super(RuntimeError, self).__init__(mess)

err_registry = {1:DiffKeyError(" "), 2:DiffBadType(""), 4:DiffDecodeError(""), 8:DiffCollideError(""), 16:DiffUnknownError("")}

#   End custom exceptions for diff validation


#End functions to deal with edit submissions -------------------------------------------------------

if __name__ == "__main__":

    inv.setup_internal_client()
    db = inv.int_client[inv.ALL_STRUC.name]

    listing = get_edit_list()
    for item in listing:
        print(item)
        coll_listing = gen_retrieve_db_listing(db, item)
        print("   " + str(coll_listing))

#print json.dumps({'4': 5, '6': 7}, sort_keys=True,
#...                  indent=4, separators=(',', ': '))

    import random
    random.seed()
    item = random.choice(listing)
    coll_listing = gen_retrieve_db_listing(db, item)
    coll_item = random.choice(coll_listing)
    print('_________________________________________')
    print("Getting for "+str(item) +'.'+ str(coll_item))
    print(json.dumps(get_inventory_for_display(str(item)+'.'+coll_item), indent=4, separators=(',', ': ')))

else:
    #Setup the edit transactions logger
    #Swap out info for debug etc
    inv.init_transac_log('info')
