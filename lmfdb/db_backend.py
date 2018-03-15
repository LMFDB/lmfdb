import pymongo
import psycopg2, psycopg2.extras, psycopg2.extensions
import json, random
from lmfdb.base import getDBConnection as getMongoConnection
from lmfdb.utils import random_object_from_collection
_PostgresConnection = None
def getPostgresConnection():
    global _PostgresConnection
    if _PostgresConnection is None:
        _PostgresConnection = psycopg2.connect(dbname="lmfdb", user="lmfdb")
    return _PostgresConnectio

def numeric_converter(value, cur):
    if value is None:
        return None
    if '.' in value:
        return float(value) # should maybe be a higher precision real sometimes?
    return int(value)

class DBBackend(object):
    def __init__(self, name, search_cols, extra_cols):
        self._search_cols = search_cols
        self._extra_cols = extra_cols
        self._name = name

class MongoBackend(DBBackend):
    def __init__(self, name, search_cols, extra_cols, sort):
        db = getMongoConnection()
        if name:
            for subname in name.split('.'):
                db = db[subname]
        self._db = db
        self._sort = sort
        DBBackend.__init__(self, name, search_cols, extra_cols)
    def lucky(self, query):
        """Return a label or None"""
        one = self._db.find_one(query)
        if one:
            return one['label']
    def search_results(self, query, limit=None, offset=None, lucky=False):
        res = self._db.find(query, self._search_cols)
        sort = self._sort
        if sort is not None:
            res = res.sort(sort)
        if limit is None:
            # Want all records
            return 0, res
        nres = res.count()
        if offset:
            res = res.skip(offset)
        res = res.limit(limit)
        return nres, res
    def lookup(self, label):
        return self._db.find_one({'label':label})
    def max(self, col):
        return self._db.find().sort(col, pymongo.DESCENDING).limit(1)[0][col]
    def count(self, query={}):
        return self._db.find(query).count()
    def random(self):
        """Random label"""
        return random_object_from_collection(self._db)['label']

class PostgresBackend(DBBackend):
    def __init__(self, name, search_cols, extra_cols, sort):
        self._conn = getPostgresConnection()
        cur = self._conn.cursor()
        cur.execute("SELECT NULL:numeric")
        oid = cur.description[0][1]
        NUMERIC = psycopg2.extensions.new_type((oid,), "NUMERIC", numeric_converter)
        psycopg2.extensions.register_type(NUMERIC, self._conn)
        self._sort = ", ".join((col if dir == 1 else col + " DESC") for col, dir in sort)
        DBBackend.__init__(self, name, search_cols, extra_cols)

    def _quick_count(self, query):
        s = "SELECT count FROM {0}_counts WHERE query = %s;".format(self._name)
        cur = self._conn.cursor()
        cur.execute(s, (json.dumps(query),))
        if cur.rowcount == 1:
            return cur.fetchone()[0]
        else:
            return None
    def _parse_special(self, key, value, outer):
        if key == '$or':
            pairs = [self._parse_dict(clause) for clause in value]
            pairs = [pair for pair in pairs if pair is not None]
            if pairs:
                strings, values = zip(*pairs)
                # flatten values
                values = [item for sublist in values for item in sublist]
                return "(" + " OR ".join(strings) + ")", values
            else:
                return None
        elif key == '$lte':
            return "{0} <= %s".format(outer), [value]
        elif key == '$get':
            return "{0} >= %s".format(outer), [value]
        elif key == '$in':
            return "{0} in %s".format(outer), [value]
        else:
            raise ValueError("Error building query: {0}".format(key))
    def _parse_dict(self, D, outer=None):
        if len(D) == 0:
            return None
        else:
            strings = []
            values = []
            for key, value in D.iteritems():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == '$':
                    sub = self._parse_special(key, value, outer)
                    if sub is not None:
                        strings.append(sub[0])
                        values.extend(sub[1])
                elif isinstance(v, dict) and all(k.startswith('$') for k in v.iterkeys()):
                    sub = self._parse_dict(v, key)
                    if sub is not None:
                        strings.append(sub[0])
                        values.extend(sub[1])
                elif '.' in key:
                    raise ValueError("Error building query: subdocuments not supported")
                else:
                    strings.append("{0} = %s".format(k))
                    values.append(value)
            if strings:
                return " AND ".join(strings), values
            else:
                return None

    def _build_query(self, query, need_count=True, limit=None, offset=None, only_label=False, only_count=False):
        if only_label:
            vars = "label"
        elif only_count:
            vars = "COUNT(*)"
        else:
            vars = ", ".join(self._search_cols)
            if need_count:
                vars += ", COUNT(*) OVER() AS full_count"
        s = "SELECT {0} FROM {1}".format(vars, self._name)
        query = self._parse_dict(query)
        if query is None:
            values = None
        else:
            query, values = query
            s += " WHERE " + query
        if self._sort:
            s += " ORDER BY " + self._sort
        if limit is not None:
            s += " LIMIT " + str(limit)
            if offset is not None:
                s += " OFFSET " + str(OFFSET)
        return query, values
    def lucky(self, query):
        query, values = self._build_query(query, False, 1, only_label=True)
        cur = self._conn.cursor()
        cur.execute(query, values)
        if cur.rowcount > 0:
            return cur.fetchone()[0]
    def search_results(self, query, limit=None, offset=None):
        if limit is None:
            nres = -1
            need_count = False
        else:
            nres = self._quick_count(query)
            need_count = (nres is None)
        query, values = self._build_query(query, need_count, limit, offset)
        cur = self._conn.cursor()
        cur.execute(query, values)
        if limit is None:
            return -1, cur
        if need_count:
            res = []
            nres = None
            for vec in cur:
                if nres is None:
                    nres = vec[-1]
                if nres != vec[-1]:
                    raise ValueError("Error processing query: inconsistent counts")
                res.append({k:v for k,v in zip(self._search_cols, vec[:-1])})
        else:
            res = [{k:v for k,v in zip(self._search_cols, vec)} for vec in cur]
        return nres, res
    def lookup(self, label):
        vars = ", ".join(self._search_cols + self._extra_cols)
        cur = self._conn.cursor()
        cur.execute("SELECT {0} FROM {1} WHERE label = %s".format(vars, self._name), (label,))
        if cur.rowcount > 0:
            vec = cur.fetchone()
            return {k:v for k,v in zip(self._search_cols + self._extra_cols, vec)}
    def count(self, query):
        nres = self._quick_count(query)
        if nres is None:
            cur = self._conn.cursor()
            query, values = self._build_query(query, only_count=True)
            cur.execute(query, values)
            nres = cur.fetchone()[0]
        return nres
    def max(self, col):
        cur = self._conn.cursor()
        cur.execute("SELECT {0} FROM {1} ORDER BY {0} DESC LIMIT 1".format(col, self._name))
        return cur.fetchone()[0]
    def random(self):
        """Random label"""
        maxid = self.max('id')
        cur = self._conn.cursor()
        while True:
            id = random.randint(0, maxid)
            cur.execute("SELECT label FROM {0} WHERE id = %s".format(self._name), (id,))
            if cur.rowcount > 0:
                return cur.fetchone()[0]
