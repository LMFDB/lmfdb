
from os import path
import hashlib
from urlparse import urlparse
from logging import getLogger
from lmfdb_inventory import LOG_ID as LOG_ID

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

#End LMFDB reports output helpers -----------------------------------------

#Display helpers ----------------------------------------------------------
def transform_examples(str, backwards=False):
    """ Converts between stored and display example strings. This is sub-optimal and should probably be fixed upstream
    """
    if not backwards and str[0] == '`' and str[-1] == '`':
        return str[1:-1]
    elif backwards:
        return '`'+str+'`'
    else:
        return str

def escape_for_display(obj):
    """ Escape any newlines, just in case, and fix up example backticks """

    for item in obj:
        for field in obj[item]:
            obj[item][field] = obj[item][field].replace('\n', ' ')
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

#End display helpers ----------------------------------------------------------

#LMFDB report tool temporary borrows _____________________________________________________

def hash_record_schema(schema_list):
    """Compute the hash of a given record schema"""
    sorted_list = sorted(schema_list, key = lambda s: s.lower())
    strl = str(sorted_list)
    m = hashlib.md5(strl)
    return m.hexdigest()

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
        parent = '/'.join(path_parts[0:-2])
    except Exception as e:
        log_dest.error(path_parts, e)

    return {'parent':parent, 'db_name':db_name, 'collection_name':collection_name, 'trail_slash':trail_slash}

# End extra URL and web helpers ----------------------------------------------------------
