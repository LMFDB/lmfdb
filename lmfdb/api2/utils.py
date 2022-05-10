
import datetime
from lmfdb.api2 import __version__
import json
#from bson.objectid import ObjectId
from lmfdb import db

api_version = __version__

api_type_searchers = 'API_SEARCHERS'
api_type_descriptions = 'API_DESCRIPTIONS'
api_type_inventory = 'API_INVENTORY'
api_type_records = 'API_RECORDS'
api_type_error = 'API_ERROR'


class test_obj:
    def _toJSON(self):
        return ['TEST', 'OBJECT']


class APIEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return obj._toJSON()
        except Exception:
            try:
                return str(obj)
            except Exception:
                return json.JSONEncoder.default(self, obj)


def create_search_dict(table='', query=None, view_start=0, request = None):
    """
    Build an empty search dictionary
    """

    if query is None:
        query_alpha = {}
    else:
        query_alpha = query

    search = {'table':table, 'query':query_alpha, 'view_start':view_start,
        'max_count':100, 'correct_count':False, 'count_only':False}

    if request:
        search['view_start']=int(request.args.get('_view_start', search['view_start']))
        search['max_count'] = min(int(request.args.get('_max_count', search['max_count'])), 100)
        search['correct_count'] = bool(request.args.get('_correct_count', search['correct_count']))
        search['count_only'] = bool(request.args.get('_count_only', search['count_only']))
    return search

def build_api_wrapper(api_key, api_type, data, request = None):
    """
    Build the outer wrapper of an API structure. This is used both for search results and for description queries.
    Is an outer structure so that it can be extended without collisions with data

    api_key -- Key name for API call. Is not checked for correctness
    api_type -- Type of the API data being returned, should be named constant as above (api_type_*)
    data -- Container holding the inner data, should match the format expected for api_type
    request -- Flask request object to query for needed data
    """

    return json.dumps({"key":api_key, 'built_at':str(datetime.datetime.now()),
        'api_version':api_version, 'type':api_type, 'data':data},
        indent=4, sort_keys=False, cls = APIEncoder)


def build_api_records(api_key, record_count, r_c_e, view_start,
                      view_count, record_list,
                      max_count=None, request=None):
    """
    Build an API object from a set of records. Automatically calculates point to start view to get next record.
    'View' is the concept of which part of all of the records returned by a query is contained in _this_ api response

    Arguments:
    api_key -- Named API key as registered with register_search_function
    record_count -- Total number of records returned by the query
    r_c_e -- Is the record count correct or just a placeholder
    view_start -- Point at which the current view starts in records
    riew_count -- Number of records in the current view. Must be less than max_count if max_count is specified
    record_list -- Dictionary containing the records in the current view

    Keyword arguments:
    max_count -- The maximum number of records in a view that a client can request. This should be the same as
                 is returned in the main API page unless this value cannot be inferred without context
    request -- Flask request object to query for needed data

    """
    view_count = min(view_count, record_count - view_start)
    next_block = view_start + view_count if (view_start + view_count < record_count or not r_c_e) else -1
    if view_count == 0:
        next_block = -1
        view_start = -1
    keys = {"record_count": record_count,
            "record_count_correct": r_c_e,
            "view_start": view_start, "view_count": view_count,
            "view_next": next_block, "records": record_list}
    if max_count:
        keys['api_max_count'] = max_count
    return build_api_wrapper(api_key, api_type_records, keys, request)


def build_api_search(api_key, mddtuple, max_count=None, request=None):
    """
    Build an API object from a set of records. Automatically calculates point to start view to get next record.
    'View' is the concept of which part of all of the records returned by a query is contained in _this_ api response

    Arguments:
    api_key -- Named API key as registered with register_search_function
    search_dict -- Search dictionary compatible with simple_search

    Keyword arguments:
    max_count -- The maximum number of records in a view that a client can request. This should be the same as
                 is returned in the main API page unless this value cannot be inferred without context
    request -- Flask request object to query for needed data

    """

    metadata = mddtuple[0]
    data = mddtuple[1]
    search_dict = mddtuple[2]
    if metadata.get('error_string', None):
        return build_api_error(metadata['error_string'], request = request)
    return build_api_records(api_key, metadata['record_count'], metadata['correct_count'],
        search_dict['view_start'], metadata['view_count'], data, max_count = max_count, request = request)

def build_api_searchers(names, human_names, descriptions, request = None):

    """
    Build an API response for the list of available searchers
    human_names -- List of human readable names
    names -- List of names of searchers
    descriptions -- List of descriptions for searchers
    request -- Flask request object to query for needed data
    """
    item_list = [{n:{ 'human_name':h, 'desc':d}} for n, h, d in zip(names, human_names, descriptions)]

    return build_api_wrapper('GLOBAL', api_type_searchers, item_list, request)


def build_api_descriptions(api_key, description_object, request = None):

    """
    Build an API response for the descriptions of individual searches provided by a searcher
    api_key -- Named API key as registered with register_search_function
    description_object -- Description object
    request -- Flask request object to query for needed data
    """
    return build_api_wrapper(api_key, api_type_descriptions, description_object, request)

def build_api_inventory(api_key, description_object, request = None):

    """
    Build an API response for the keys that could be returned by the searcher
    api_key -- Named API key as registered with register_search_function
    description_object -- Description object
    request -- Flask request object to query for needed data
    """
    return build_api_wrapper(api_key, api_type_inventory, description_object, request)


def build_api_error(string, request = None):

    """
    Build an API response for an error
    string -- string to return as error
    request -- Flask request object to query for needed data
    """
    return build_api_wrapper('GLOBAL', api_type_error, string, request)


def build_description(objlist, name, desc, typ, h_name, db_name=None,
                      coll_name=None, field_name=None, request=None):
    """
    Build a description object by specifying a new searchable field
    If this maps to searching a single database field then the user should supply
    the db_name, coll_name and field_name objects
    objlist -- searcher object(dictionary) that is being built
    name -- Name of search key, must be unique
    desc -- Description of searcher, if None will be obtained from inventory if is search on single field
    typ -- type of search that can be performed. Not used yet
    h_name -- Short human readable name for search
    db_name -- Name of database to be searched by this searcher. Optional
    coll_name -- Name of collection to be searched by this searcher. Optional
    field_name -- Name of field to be searched by this searcher. Optional
    request -- Flask request object to query for needed data. Optional
    """
    objlist[name] = {}
    objlist[name]['human_name'] = h_name
    if (db_name and coll_name and field_name):
        objlist[name]['db_name'] = db_name + '/' + coll_name + '/' + field_name
    else:
        objlist[name]['db_name'] = '@@SPECIAL@@'
    if desc is None:
        desc_obj = test_obj()
    else:
        desc_obj = desc
    objlist[name]['desc'] = desc_obj
    objlist[name]['type'] = type


def get_filtered_fields(coll_pair):

    """
    Get a list of fields on which searching is possible
    coll_pair -- Two element list or tuple (prefix, name)
    """
    return None

    #data = inventory.retrieve_description(coll_pair[0], coll_pair[1])
    #field_list = data['data']
    #if not field_list : return None

    #return field_list

def get_cname_list(info):
    """
    Get a mapping from canonical name to true name
    info - data from a call to get_filtered_fields
    """
    lookup = {}
    for el in info:
        try:
            lookup[info[el]['cname']] = el
        except KeyError:
            pass
    return lookup


def patch_up_old_inventory(data, table_name):
    """
    Patch old inventory data to use new database information
    data -- old inventory data
    table_name -- Name of table in postgres database
    """

    table = db[table_name]
    result = {}
    for el in table.search_cols:
        try:
            result[el] = data[el]
        except KeyError:
            result[el] = "Missing"
    return result

def default_projection(request, cnames=None):
    """
    Build a projection from an request dictionary as returned by flask. _id always excluded

    Keywords of request dict used:
    fields -- comma separated list of fields to include (exclude if keyword set)
    cnames -- dictionary mapping canonical names to field names. Field names will be remapped if found in the list of canonical names. Optional. If not present no remapping occurs

    """
    try:
        fields = request.args.get('_fields').split(',')
        if cnames:
            fields = [cnames.get(el,el) for el in fields]
        exclude = False
        try:
            if request.args.get('_exclude'):
                exclude = True
        except Exception:
            pass
        project = build_query_projection(fields, exclude = exclude)
    except Exception:
        project = None
    return project

def build_query_projection(field_list, exclude=False):
    """
    Builds an lmfdb Postgres interface compatible query projection dictionary

    Arguments:
    field_list -- List of fields to include (exclude if keyword set)

    Keyword arguments:
    exclude -- logical for whether to build an inclusive or exclusive projection (default False)

    """
    keys = {"_id":0}
    val = 1
    if exclude:
        val = 0
    for el in field_list:
        keys[el] = val
    return keys

def compare_db_strings(str1, str2):
    """
    Compare two database strings for compatibility. Same db and collection, not same field
    str1 -- First database string to compare
    str2 -- Second database string to compare
    """

    splt1 = str1.split('/')
    splt2 = str2.split('/')

    if (len(splt1) < 3 or len(splt2) < 3):
        return False
    return (splt1[0] == splt2[0]) and (splt1[1] == splt2[1])

def trim_comparator(value, comparators):

    """
    Check for a comparator value and trim it off if found
    value -- Value to test
    comparators -- List of comparators to test
    """

    value_new = value
    result = None
    for el in comparators:
        if value.startswith(el[0]):
            value_new = value[len(el[0]):]
            result = el[1]
            break
    return value_new, result

def interpret(query, qkey, qval, type_info):

    """
    Try to interpret a user supplied value into a mongo query
    query -- Existing (can be blank) dictionary to build the query in
    qkey -- Key (field to be searched in)
    qval -- Value (taken from user)
    type_info -- String defining type of qval. Used if present and interpretable
    """

    DELIM = ','

    from ast import literal_eval

    qkey = qkey.replace('"','')
    qval = qval.replace('"','')

    user_infer = True

    if type_info and not qval.startswith("|"):
        user_infer = False
        qval, comparator = trim_comparator(qval, [(">","$gt"),("<","$lt"), ("%","$in"), ("<=","$le"), (">=","$ge")])

        try:
            if type_info == 'string':
                pass #Already a string
            elif type_info == 'integer':
                try:
                    qval = int(qval)
                except Exception:
                    qval = [int(_) for _ in qval.split(DELIM)]
            elif type_info == 'real':
                qval = float(qval)
            elif type_info == 'list of integers':
                qval = [int(_) for _ in qval.split(DELIM)]
            elif type_info == 'list of integers stored as string':
                qval = str([int(_) for _ in qval.split(DELIM)])
            elif type_info == 'boolean':
                qval = bool(qval)
            else:
                user_infer = True

            print(type_info)

            if not user_infer and comparator:
                qval = {comparator: qval}

        except Exception:
            user_infer = True
    else:
        if qval.startswith("|"):
            qval = qval[1:]

    if user_infer:
        try:
            if qkey.startswith("_"):
                return
            elif qval.startswith("s"):
                qval = qval[1:]
            elif qval.startswith("i"):
                qval = int(qval[1:])
            elif qval.startswith("f"):
                qval = float(qval[1:])
#            elif qval.startswith("o"):
#                qval = ObjectId(qval[1:])
            elif qval.startswith("ls"):      # indicator, that it might be a list of strings
                qval = qval[2:].split(DELIM)
            elif qval.startswith("li"):
                qval = [int(_) for _ in qval[2:].split(DELIM)]
            elif qval.startswith("lf"):
                qval = [float(_) for _ in qval[2:].split(DELIM)]
            elif qval.startswith("py"):     # literal evaluation
                qval = literal_eval(qval[2:])
            elif qval.startswith("cs"):     # containing string in list
                qval = { "$in": [qval[2:]] }
            elif qval.startswith("ci"):
                qval = { "$in": [int(qval[2:])] }
            elif qval.startswith("cf"):
                qval = { "$in": [float(qval[2:])] }
            elif qval.startswith("cpy"):
                qval = { "$in": [literal_eval(qval[3:])] }
        except Exception:
            # no suitable conversion for the value, keep it as string
            return
    query[qkey] = qval


def simple_search(search_dict, projection=None):
    """
    Perform a simple search from a request
    """
    return simple_search_postgres(search_dict, projection)

def simple_search_postgres(search_dict, projection=None):
    """
    Perform a simple search from a request
    """

    offset = search_dict.get('view_start', 0)
    rcount = search_dict.get('max_count', 100)

    if not projection:
        projection = 2
    else:
        # Strip out removal of mongo _id fields
        p2 = {}
        for el in projection:
            if el != "_id":
                p2[el] = projection[el]
        projection = p2

    metadata = {}
    C = db[search_dict['table']]
    info = {}
    try:
        data = C.search(search_dict['query'], projection = projection, limit = rcount,
            offset = offset, info = info)
    except Exception as e:
        data = []
        info['number'] = 0
        info['exact_count'] = False
        metadata['error_string'] = str(e)
    metadata['record_count'] = info['number']
    metadata['correct_count'] = info['exact_count']
    if data:
        data_out = list(list(data))
    else:
        data_out = []
    metadata['view_count'] = len(data_out)
    return metadata, list(data_out), search_dict
