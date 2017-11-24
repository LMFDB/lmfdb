from bson.code import Code
import dbtools
import id_object
from lmfdb.base import getDBConnection

__version__ = '1.0.0'

def _is_good_database(name):
    bad=['admin','test','contrib','local','userdb','upload', 'inventory']
    if name in bad:
      return False
    return True

def _is_good_collection(dbname, name):
    if '.' in name:
      return False
    return True


def merge_dicts(d1, d2):
    for key, value2 in d2.items():
        if key in d1:
            if type(value2) is dict: 
                merge_dicts(d1[key], value2)
        else:
            d1[key] = value2

def _get_db_records(coll):

    mapper = Code("""
                  function() {
                    var names = Object.keys(this).sort();
                    emit(names,1);
                    }
                    """)

    reducer = Code("""
                    function (key,values) {
                      return Array.sum(values);
                    }
                    """)

    try:
        results = coll.inline_map_reduce(mapper,reducer)
    except Exception as err:
        print('Unable to perform map_reduce. Collection or database may not exist')
        raise err
    #Strip the _id field from the results
    for doc in results:
        if '_id' in doc['_id']: doc['_id'].remove('_id')
    return results

def _jsonify_collection_info(coll, dbname = None):

    if dbname is None:
        dbname = coll.name
    results = _get_db_records(coll)

    json_db_data = {}
    json_db_data['dbinfo'] ={}
    json_db_data['dbinfo']['name'] = dbname
    json_db_data['records'] = {}
    json_db_data['fields'] = {}

    lst=set()
    for doc in results:
        lst = lst | set(doc['_id'])
    lst=list(lst)
    lst.sort()

    for doc in lst:
        try:
            rls = dbtools.get_sample_record(coll, str(doc))
            try:
                typedesc = id_object.get_description(rls[str(doc)])
            except:
                typedesc = 'Type cannot be identified (' \
                           + str(type(rls[str(doc)])) + ')'
            try:
                strval =  str(rls[str(doc)]).decode('unicode_escape').\
                          encode('ascii','ignore')
            except:
                strval = 'Record cannot be stringified'
        except:
            typedesc = 'Record cannot be found containing key'
            strval = 'N/A'

        lstr = len(strval)
        strval = strval.replace('\n',' ').replace('\r','')
        strval = '`' + strval[:100].strip() + '`'
        if lstr > 100:
            strval = strval + ' ...'
        json_db_data['fields'][str(doc)] = {}
        json_db_data['fields'][str(doc)]['type'] = typedesc
        json_db_data['fields'][str(doc)]['example'] = strval


    for recordid, doc in enumerate(results):
        json_db_data['records'][recordid] = {}
        json_db_data['records'][recordid]['count'] = int(doc['value'])
        json_db_data['records'][recordid]['schema'] = doc['_id']

    indices = coll.index_information()
    json_db_data['indices'] = {}
    for recordid, index in enumerate(indices):
        json_db_data['indices'][recordid] = {}
        json_db_data['indices'][recordid]['name'] = index
        json_db_data['indices'][recordid]['keys'] = indices[index]['key']

    return json_db_data

def parse_collection_info_to_json(dbname, collname, connection = None):

    if connection is None:
        connection = getDBConnection()

    dbstring = dbname + '\\' + collname
    coll = connection[dbname][collname]
    json_raw = _jsonify_collection_info(coll, dbstring)
    json_wrap = {dbname:{collname:json_raw}}
    return json_wrap

def create_user_template(structure_json, dbname, collname, field_subs = ['type',' example', 'description'],
                         info_subs = ['description', 'status','contact','code'], note_subs = ['description']):

    result_json = {}
    substr = structure_json[dbname][collname]
    result_json['(INFO)'] = {}
    for el in info_subs:
        result_json['(INFO)'][el] = ""
    for el in substr['fields']:
        result_json[el] = {}
        for iel in field_subs:
            result_json[el][iel] = ""
    result_json['(NOTES)'] = {}
    for el in note_subs:
        result_json['(NOTES)'][el] = ""
    return result_json

def parse_lmfdb_to_json(collections = None, databases = None, connection = None, 
                        is_good_database = _is_good_database, 
                        is_good_collection = _is_good_collection):

    if connection is None:
        connection = getDBConnection()

    if not collections:
        collections = get_lmfdb_collections(connection = connection, databases = databases,
                          is_good_database = is_good_database, is_good_collection = is_good_collection)
    else:
        if not hasattr(collections, '__iter__'): collections = [collections]
        if type(collections) is not dict:
            if not databases:
                databases = get_lmfdb_databases(connection = connection, is_good_database = is_good_database)
            if len(databases) == 1:
                coldict = {databases[0] : collections}
            else:
                coldict = {}
                for db in databases:
                    coldict[db] = []
                    for coll in connection[db].collection_names():
                        if coll in collections and is_good_collection(db, coll):
                            coldict[db].append(coll)
            collections = coldict
        else:
            for coll in collections:
                if type(collections[coll]) is not list:
                    if collections[coll]:
                        collections[coll] = [collections[coll]]
                    else:
                        collections[coll] = connection[coll].collection_names()

    db_struct = {}
    for db in collections:
        if is_good_database(db):
            for coll in collections[db]:
                if is_good_collection(db, coll):
                    merge_dicts(db_struct,parse_collection_info_to_json\
                                        (db, coll, connection = connection))
    return db_struct

def get_lmfdb_databases(connection = None, is_good_database = _is_good_database):
    if connection is None:
        connection = getDBConnection()
    el = []

    for db in connection.database_names():
        if is_good_database(db): el.append(db)

    return el

def get_lmfdb_collections(connection = None, databases = None, is_good_database =
                          _is_good_database, is_good_collection = _is_good_collection):

    if connection is None:
        connection = getDBConnection()
    if not databases: databases = get_lmfdb_databases(connection = connection,
                                      is_good_database = is_good_database)
    if not hasattr(databases, '__iter__'): databases = [databases]
    collections = {}
    for db in databases:
        if is_good_database(db):
            collections[db] = []
            for coll in connection[db].collection_names():
                if is_good_collection(db, coll): collections[db].append(coll)

    return collections
