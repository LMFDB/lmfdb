import dbtools
import id_object
from lmfdb.backend.database import db
import datetime

__version__ = '1.0.0'

def _is_good_table(name):
    """ Function to test if a database is one to scan """
    if '.' in name: return False
    return True

def merge_dicts(d1, d2):
    """ Merge two dictionaries into one """
    for key, value2 in d2.items():
        if key in d1:
            if type(value2) is dict:
                merge_dicts(d1[key], value2)
        else:
            d1[key] = value2

def _get_db_records(table):

    """ Routine to get the keys for a specified table """

    results = db[table]._search_cols
    return results

def _jsonify_record(name, record, parse_jsonb = False, inferred = False):
    vals = {}
    if isinstance(record, dict) and parse_jsonb:
        for el in record:
          merge_dicts(vals, _jsonify_record(name + "." + str(el), record[el], parse_jsonb = parse_jsonb, inferred = True))

    if isinstance(record, list) and parse_jsonb:
        if len(record) > 0 and isinstance(record[0], dict): merge_dicts(vals, _jsonify_record(name, record[0], parse_jsonb = parse_jsonb, inferred = True))

    try:
        typedesc = id_object.get_description(record)
    except:
        typedesc = 'Type cannot be identified (' \
            + str(type(record)) + ')'
    try:
        strval =  str(record).decode('unicode_escape').\
            encode('ascii','ignore')
    except:
        strval = 'Record cannot be stringified'

    lstr = len(strval)
    strval = strval.replace('\n',' ').replace('\r','')
    strval = '`' + strval[:100].strip() + '`'
    if lstr > 100:
        strval = strval + ' ...'
    vals[str(name)] = {}
    vals[str(name)]['type'] = typedesc
    vals[str(name)]['example'] = strval
    vals[str(name)]['inferred'] = inferred
    return vals


def _jsonify_collection_info(table, parse_jsonb = False):

    """Private function to turn information about one collection into base 
       JSON """

    results = _get_db_records(table)

    json_db_data = {}
    json_db_data['dbinfo'] ={}
    json_db_data['dbinfo']['name'] = table
    json_db_data['records'] = {}
    json_db_data['fields'] = {}

    for doc in results:
        rls = dbtools.get_pg_sample_record(table, str(doc))
        try:
            merge_dicts(json_db_data['fields'], _jsonify_record(str(doc), rls[doc], parse_jsonb = parse_jsonb))
	except:
 	    pass

    indices = db[table].list_indexes()
    json_db_data['indices'] = {}
    for recordid, index in enumerate(indices):
        json_db_data['indices'][recordid] = {}
        json_db_data['indices'][recordid]['name'] = index
        json_db_data['indices'][recordid]['keys'] = indices[index]['columns']

    return json_db_data

def parse_collection_info_to_json(table, retval = None, date = None, parse_jsonb = False):

    """ Front end routine to create JSON information about a collection """

    name_list = table.split("_",1)
    db = name_list[0]
    coll = name_list[1]

    json_raw = _jsonify_collection_info(table, parse_jsonb = parse_jsonb)
    json_wrap = {db:{coll:json_raw}}
    if not date:
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    json_wrap[db][coll]['scrape_date'] = date
    if retval is not None: retval['data'] = json_wrap
    return json_wrap

def _get_db_name(name):
    return name.split("_",1)[0]

def _get_coll_name(name):
    return name.split("_",1)[1]

def get_lmfdb_databases(is_good_table = _is_good_table):
    tables = db.tablenames
    databases = []
    for el in tables:
        if is_good_table(el):
            databases.append(_get_db_name(el))
    return list(set(databases))

def get_lmfdb_collections(databases = None, is_good_table = _is_good_table):

    """Routine to get a dictionary with keys of all databases and member lists
       of collections in that database"""

    if not databases: databases = get_lmfdb_databases(is_good_table = is_good_table)
    if not hasattr(databases, '__iter__'): databases = [databases]

    tables = db.tablenames

    collections = {}
    for table in tables:
        db_name = _get_db_name(table)
        if is_good_table(table) and db_name in databases:
            collections[db_name] = []

    for table in tables:
        db_name = _get_db_name(table)
        if is_good_table(table) and db_name in databases:
            collections[db_name].append(_get_coll_name(table))

    return collections
