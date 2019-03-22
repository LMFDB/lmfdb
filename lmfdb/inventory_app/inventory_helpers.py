
from urlparse import urlparse
from logging import getLogger
from lmfdb_inventory import LOG_ID as LOG_ID
from lmfdb_inventory import table_status

#Log for db actions
log_dest = getLogger(LOG_ID)

#LMFDB reports output helpers ---------------------------------------------

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

#End LMFDB reports output helpers -----------------------------------------

#Display helpers ----------------------------------------------------------
def transform_examples(str, backwards=False):
    """ Converts between stored and display example strings. This is sub-optimal and should probably be fixed upstream
    """
    if not backwards and len(str)>1 and str[0] == '`' and str[-1] == '`':
        return str[1:-1]
    elif backwards:
        return '`'+str+'`'
    else:
        return str

def escape_for_display(obj):
    """ Escape any newlines, just in case, and fix up example backticks """

    for item in obj:
        for field in obj[item]:
            if obj[item][field]:
                obj[item][field] = unicode(obj[item][field]).replace('\n', ' ')
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
        return table_status.keys()[list(table_status.values()).index(status)]
    except:
        return -1

def code_to_status(status):
    try:
        return table_status[status]
    except:
        return ''

#End display helpers ----------------------------------------------------------


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
        table_name = path_parts[-2]
    except Exception as e:
        db_name = ""
        table_name = ""
        log_dest.error(parts.path, e)

    parent = None
    try:
        #print path_parts[0:-1]
        parent = '/'.join(path_parts[0:-2])
    except Exception as e:
        log_dest.error(path_parts, e)

    return {'parent':parent, 'db_name':db_name, 'table_name':table_name, 'trail_slash':trail_slash}

# End extra URL and web helpers ----------------------------------------------------------

# Exceptions understood by web-front end
#Most bugs the front end can do little more than a ``something went wrong'' and diagnosis must be done backend.
#These are the exceptions to that principle
class ConnectOrAuthFail(Exception):
    """Raise for failure to connect or auth i.e. int_client in invalid state"""
    def __init__(self, message):
        mess = "Failed to connect to db"
        super(Exception, self).__init__(mess)

#  End exceptions understood by web-front end --------------------------------------------
