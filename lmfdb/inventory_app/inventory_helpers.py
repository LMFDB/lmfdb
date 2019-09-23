
from os import path
import hashlib
from urlparse import urlparse
from logging import getLogger
from lmfdb_inventory import LOG_ID as LOG_ID
from lmfdb_inventory import coll_status as coll_status
import re

#Log for db actions
log_dest = getLogger(LOG_ID)

#LMFDB reports output helpers ---------------------------------------------

def get_description_key(filename):
    """Extract a db-collection name pair from filenames from report tool"""

    base = path.basename(filename)
    if base[-5:] == '.json':
        base = base[0:-5]
    return get_description_key_parts(base)

def get_description_key_parts(name):
    """Gets the db and collection parts of a key"""

    parts=name.split('.')
    if len(parts) < 2:
        if len(parts) > 0:
            return [parts[0], parts[0]]
        else:
            return ['', '']
    else:
        return parts

def is_special_field(name):
    """ Check for special (INFO, NOTES etc) fields"""

    try:
        if name[0] =='_' and name[-1]=='_':
            return True
        return False
    except:
        return False

def is_toplevel_field(name):
    """ Check for top-level fields, e.g. nice_name"""

    try:
        if name == "top_level":
            return True
        return False
    except:
        return False

def is_record_name(item):
    """ Check for record items (document schemas)"""
    try:
        if 'name' in item and not 'type' in item:
            return True
        return False
    except:
        return False
def is_probable_record_hash(name):
    """ Check whether given name seems to be a record identifier
    This is a 32 char hex string right now"""
    try:
        reg = r"([a-fA-F\d]{32})"
        #32 digits all either a-f or a number
        return (re.match(reg, name) is not None)
    except:
        return False

def make_empty_record(eg):
    """Take a record and return it, but empty
    List fields become empty lists, others become None
    """
    new = {}
    for field in eg:
        if type(eg[field]) ==type([]):
            new[field] = []
        else:
            new[field] = None
    return new

#End LMFDB reports output helpers -----------------------------------------

#Display helpers ----------------------------------------------------------
def transform_examples(str, backwards=False):
    """ Converts between stored and display example strings. This is sub-optimal and should probably be fixed upstream
    """
    try:
        if not backwards and len(str)>1 and str[0] == '`' and str[-1] == '`':
            return str[1:-1]
        elif backwards:
            return '`'+str+'`'
        else:
            return str
    except:
        return str

def escape_for_display(obj):
    """ Escape any newlines, just in case, and fix up example backticks """

    for item in obj:
        for field in obj[item]:
            if obj[item][field]:
                obj[item][field] = str(obj[item][field]).replace('\n', ' ')
            #This is not ideal, but it works for now for display etc
            if field == 'example':
                obj[item][field] = transform_examples(obj[item][field])
    return obj

def null_all_empty_fields(obj):
    """Nullify all 'empty' fields in obj (see null_empty_field for definition)"""
    try:
        for field in obj:
            obj[field] = null_empty_field(obj[field])
    except Exception as e:
        log_dest.error(e)
    return obj

def null_empty_field(value):
    """Nullify 'empty' field, defined by leading and trailing @@"""
    try:
        if value[0:2] == '@@' and value[-2:] == '@@':
            return None
        else:
            return value
    except:
        return value

def blank_all_empty_fields(obj):
    """As null_all_empty_fields but set to empty string instead"""
    try:
        for field in obj:
            obj[field] = blank_empty_field(obj[field])
    except Exception as e:
        log_dest.error(e)
    return obj

def blank_empty_field(value):
    """As null_empty_field but set to empty string instead"""
    try:
        if value[0:2] == '@@' and value[-2:] == '@@':
            return ''
        else:
            return value
    except:
        return value

def empty_null_record_info(records):
    """Empty null name or description fields in list of records"""
    try:
        for item in records:
            #print item
            item = empty_all_if_null(item)
    except Exception as e:
        log_dest.error(e)
    return records

def empty_all_if_null(obj):
    """Convert all null strings to empty"""
    try:
        for field in obj:
            obj[field] = empty_if_null(obj[field])
    except Exception as e:
        log_dest.error(e)
    return obj

def empty_if_null(value):
    """Convert true null into empty string"""
    try:
        if value is None:
            return ''
        else:
            return value
    except:
        return value

def status_to_code(status):
    try:
        return coll_status.keys()[list(coll_status.values()).index(status)]
    except:
        return -1

def code_to_status(status):
    try:
        return coll_status[status]
    except:
        return ''

#End display helpers ----------------------------------------------------------


#LMFDB report tool temporary borrows _____________________________________________________

def hash_record_schema(schema_list):
    """Compute the hash of a given record schema"""
    sorted_list = sorted(schema_list, key = lambda s: s.lower())
    strl = str(sorted_list)
    m = hashlib.md5(strl)
    return m.hexdigest()


def diff_records(all_records):
    """Take record data and calculate diffed schema
    Adds base record (if exists) to head of list and also
    sorts list so diffed records are ahead of undiffed.
    Adapted from lmfdb_reprt_tool (bradyc)
    """
    if(len(all_records) == 0):
        return

    base = None
    base_len = 0
    #Select the longest record in the database and cut down from that
    for doc in all_records:
        lnl = len(doc['schema'])
        if lnl > base_len:
          base_len = lnl
          base = doc['schema']
    #Calculate diffs for each record
    diffed = -1
    for doc in all_records:
        temp = list(set(base).intersection(doc['schema']))
        if len(temp) != 0:
          base = temp
          doc['diffed'] = True
          diffed+=1
        else:
          doc['diffed'] = False
    base_hash = hash_record_schema(base)

    diffed_recs = [record for record in all_records if record['diffed']]
    non_diffed_recs = [record for record in all_records if not record['diffed']]
    new_records = diffed_recs + non_diffed_recs
    #base is now the minimal intersection
    #Create a new field in each record whicj is full schema, as we want to display
    #diffs in general
    for doc in new_records:
        schema = doc['schema']
        diffed_schema = [val for val in schema if val not in base]
        if doc['diffed'] and len(diffed_schema) > 0:
            doc['schema'] = diffed_schema
            doc['oschema'] = schema
            doc['base'] = False
        elif doc['diffed']:
            #is base record
            doc['oschema'] =[]
            base_rec = doc
            doc['base'] = True
        else:
            doc['oschema'] = []
            doc['base'] = False

    if base_hash not in [item['hash'] for item in new_records]:
        record = make_empty_record(all_records[0])
        record['count'] = 0
        record['schema'] = base
        record['hash'] = base_hash
        record['base'] = True
        all_records.insert(0,record)
    else:
        #Move base record to start of list
        all_records.remove(base_rec)
        all_records.insert(0, base_rec)

    return all_records
#End LMFDB report tool temporary borrows _________________________________________________

# Extra URL and web helpers --------------------------------------------------------------

def parse_edit_url(url):
    """ Take a url and return dict for various parts and derived urls """
    #This is not the best way to handle paths but we're reasonably sure of their format

    trail_slash = True
    if(url[-1] != '/'):
        url = url + '/' #Ensure trailing slash
        trail_slash = False
    parts = urlparse(url)
    #print parts
    #Parts is properly split with path being all directory stuff
    try:
        path_parts = parts.path.split('/')
        db_name = path_parts[-3]
        collection_name = path_parts[-2]
    except Exception as e:
        db_name = ""
        collection_name = ""
        log_dest.error(parts.path, e)

    parent = None
    try:
        #print path_parts[0:-1]
        parent = '/'.join(path_parts[0:-2])
    except Exception as e:
        log_dest.error(path_parts, e)

    return {'parent':parent, 'db_name':db_name, 'collection_name':collection_name, 'trail_slash':trail_slash}

# End extra URL and web helpers ----------------------------------------------------------

# Exceptions understood by web-front end
#Most bugs the front end can do little more than a ``something went wrong'' and diagnosis must be done backend.
#These are the exceptions to that principle
class ConnectOrAuthFail(Exception):
    """Raise for failure to connect or auth"""
    def __init__(self, message):
        mess = "Failed to connect to db"
        super(Exception, self).__init__(mess)

#  End exceptions understood by web-front end --------------------------------------------
