from bson.code import Code
import dbtools
import id_object
import datetime
#import threading
#import bson
#import time
from collections import defaultdict
from lmfdb.db_backend import db

__version__ = '1.0.0'

def _is_good_database(name):
    """ Function to test if a database is one to scan """
    bad=['inv']
    if name in bad:
      return False
    return True

def _is_good_table(name):
    """ Function to test if a table should be scanned """
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

    """ Routine to execute the MapReduce operation on a specified table 
       object """

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
        results = table.inline_map_reduce(mapper,reducer)
    except Exception as err:
        print('Unable to perform map_reduce. Table or database may not exist')
        raise err
    #Strip the _id field from the results
    for doc in results:
        if '_id' in doc['_id']: doc['_id'].remove('_id')
    return results

def _jsonify_table_info(table, dbname = None):

    """Private function to turn information about one table into base 
       JSON """
    # Needs to be rewritten for Postgres
    raise NotImplementedError

    if dbname is None:
        dbname = table.search_table
    results = _get_db_records(table)

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
            rls = dbtools.get_sample_record(table, str(doc))
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

    indices = table.index_information()
    json_db_data['indices'] = {}
    for recordid, index in enumerate(indices):
        json_db_data['indices'][recordid] = {}
        json_db_data['indices'][recordid]['name'] = index
        json_db_data['indices'][recordid]['keys'] = indices[index]['key']

    return json_db_data

def parse_table_info_to_json(tablename, retval = None, date = None):
    """ Front end routine to create JSON information about a table """

    from lmfdb.db_backend import db
    json_raw = _jsonify_table_info(db[tablename], tablename)
    json_wrap = {tablename:json_raw}
    if not date:
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    json_wrap[tablename]['scrape_date'] = date
    if retval is not None: retval['data'] = json_wrap
    return json_wrap

def create_user_template(structure_json, dbname, tablename, field_subs = ['tiype',' example', 'description'],
                         info_subs = ['description', 'status','contact','code'], note_subs = ['description']):

    """Legacy routine to create blank user specified data JSON"""

    result_json = {}
    substr = structure_json[dbname][tablename]
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


def parse_lmfdb_to_json(tables = None, databases = None,
                        is_good_database = _is_good_database,
                        is_good_table = _is_good_table):

    """Legacy routine to scan any specified chunk of LMFDB to JSON"""
    raise NotImplementedError
    # connection has been deleted
#
#    if not tables:
#        tables = get_lmfdb_tables(databases = databases,
#                          is_good_database = is_good_database, is_good_table = is_good_table)
#    else:
#        if not hasattr(tables, '__iter__'): tables = [tables]
#        if not isinstance(tables, dict):
#            if not databases:
#                databases = get_lmfdb_databases(is_good_database = is_good_database)
#            if len(databases) == 1:
#                tbldict = {databases[0] : tables}
#            else:
#                tbldict = defaultdict(list)
#                for table in tables:
#                    db_name = table.split('_')[0]
#                    tbldict[db_name].append(table)
#            tables = tbldict
#        else:
#            for db_name, L in tables.items():
#                if not isinstance(L, list):
#                    if L:
#                        tables[db_name] = [L]
#                    else:
#                        tables.update(get_lmfdb_tables(databases=db_name))
#
#    db_struct = {}
#    for db_name in tables:
#        print('Running ' + db_name)
#        if is_good_database(db_name):
#            for table in tables[db_name]:
#                print('Parsing ' + table)
#                if is_good_table(table):
#                    mydict={}
#                    mythread = threading.Thread(target = parse_table_info_to_json, args = [table, mydict])
#                    mythread.start()
#                    while mythread.isAlive():
#                        u=bson.son.SON({"$ownOps":1,"currentOp":1})
#                        progress = connection['admin'].command(u)
#                        for el in progress['inprog']:
#                            if 'progress' in el.keys():
#                                if el['ns'] == table:
#                                    print("Scanning " + table + " " +
#                                        unicode(int(el['progress']['done'])) +
#                                        "\\" + unicode(int(el['progress']['total'])))
#                        time.sleep(5)
#
#                    merge_dicts(db_struct, mydict['data'])
#    return db_struct

def get_lmfdb_databases(is_good_database=_is_good_database):
    """ Routine to get list of available databases """
    return [db_name for db_name in db.inv_dbs.search({},'name') if is_good_database(db_name)]

def get_lmfdb_tables(databases=None, is_good_database=_is_good_database,
                     is_good_table=_is_good_table):

    """Routine to get a dictionary with keys of all databases and member lists
       of tables in that database"""

    if not databases:
        databases = get_lmfdb_databases(is_good_database=is_good_database)
    if not hasattr(databases, '__iter__'):
        databases = [databases]
    tables = defaultdict(list)
    for table in db.tablenames:
        db_name = table.split('_')[0]
        if db_name in databases and is_good_table(table):
            tables[db_name].append(table)
    return tables
