import pymongo
from psycopg2 import connect, DatabaseError
import psycopg2.extras, psycopg2.extensions
import json, random, time
from lmfdb.base import getDBConnection as getMongoConnection
from lmfdb.utils import random_object_from_collection
from sage.rings.integer import Integer
from sage.rings.all import RDF
_PostgresConnection = None
def getPostgresConnection():
    global _PostgresConnection
    if _PostgresConnection is None:
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
        psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
        _PostgresConnection = connect(dbname="lmfdb", user="lmfdb")
    return _PostgresConnection

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
    def lucky(self, query, data_level=0):
        """Return a label or None"""
        one = self._db.find_one(query)
        if one:
            if data_level == 0:
                return one['label']
            else:
                return one
    def search_results(self, query, limit=None, offset=0):
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
    def __init__(self, name, search_cols, extra_cols, sort, json_override=[], count_cutoff=1000, logger=None):
        self._conn = getPostgresConnection()
        cur = self._execute("SELECT NULL::numeric")
        oid = cur.description[0][1]
        NUMERIC = psycopg2.extensions.new_type((oid,), "NUMERIC", numeric_converter)
        psycopg2.extensions.register_type(NUMERIC, self._conn)
        self._json_override = set(json_override)
        if not sort:
            raise ValueError("You must provide a sort order")
        self._primary_sort = sort[0][0]
        self._sort = ", ".join((col if dir == 1 else col + " DESC") for col, dir in sort)
        self._count_cutoff = count_cutoff
        self.search_table, self.extras_table, self.count_table = name
        if logger is None:
            from lmfdb.utils import make_logger
            logger = make_logger(self.search_table)
        self.logger = logger
        DBBackend.__init__(self, name, search_cols, extra_cols)

    def _execute(self, query, vars=None):
        cur = self._conn.cursor()
        try:
            cur.execute(query, vars)
        except DatabaseError:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        return cur

    def _quick_count(self, query):
        if self.count_table is not None:
            s = "SELECT count FROM {0} WHERE query = %s;".format(self.count_table)
            cur = self._execute(s, (json.dumps(query),))
            if cur.rowcount == 1:
                return cur.fetchone()[0]

    def _approx_cost(self, selector, values):
        """Returns a pair (nrows, t) with the approximate number of rows and time measured in disk page fetches."""
        explainer = "EXPLAIN (FORMAT JSON) " + selector
        cur = self._execute(explainer, values)
        try:
            plan = cur.fetchall()[0][0][0]['Plan']
        except IndexError, KeyError:
            # This doesn't happen for the queries I've tested,
            # But maybe some queries have a different format for explain?
            raise RuntimeError("Unexpected explanation")
        t = plan['Total Cost']
        if plan['Node Type'] == 'Limit' and plan.get('Plans',[]):
            nrows = plan['Plans'][0]['Plan Rows']
            # Round to two significant digits if large
            if nrows > 1000:
                tenpow = 10**(Integer(nrows).ndigits(10)-2)
                nrows = int((RDF(nrows) / tenpow).round() * tenpow)
        else:
            nrows = plan['Plan Rows']
        return nrows, t

    def _parse_special(self, key, value, outer):
        if key == '$or':
            pairs = [self._parse_dict(clause) for clause in value]
            pairs = [pair for pair in pairs if pair[0] is not None]
            if pairs:
                strings, values = zip(*pairs)
                # flatten values
                values = [item for sublist in values for item in sublist]
                return "(" + " OR ".join(strings) + ")", values
            else:
                return None, None
        elif key == '$lte':
            return "{0} <= %s".format(outer), [value]
        elif key == '$gte':
            return "{0} >= %s".format(outer), [value]
        elif key == '$ne':
            return "{0} != %s".format(outer), [value]
        elif key == '$in':
            return "{0} = ANY(%s)".format(outer), [value]
        elif key == '$contains':
            if outer in self._json_override:
                value = psycopg2.extras.Json(value)
            return "{0} @> %s".format(outer), [value]
        elif key == '$notcontains':
            if outer in self._json_override:
                value = [psycopg2.extras.Json([v]) for v in value]
            return " AND ".join("NOT {0} @> %s".format(outer) for v in value), value
        elif key == '$containedin':
            if outer in self._json_override:
                value = psycopg2.extras.Json(value)
            return "{0} <@ %s".format(outer), [value]
        else:
            raise ValueError("Error building query: {0}".format(key))
    def _parse_dict(self, D, outer=None):
        if len(D) == 0:
            return None, None
        else:
            strings = []
            values = []
            for key, value in D.iteritems():
                if not key:
                    raise ValueError("Error building query: empty key")
                if key[0] == '$':
                    sub, vals = self._parse_special(key, value, outer)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                elif isinstance(value, dict) and all(k.startswith('$') for k in value.iterkeys()):
                    sub, vals = self._parse_dict(value, key)
                    if sub is not None:
                        strings.append(sub)
                        values.extend(vals)
                elif '.' in key:
                    raise ValueError("Error building query: subdocuments not supported")
                else:
                    strings.append("{0} = %s".format(key))
                    if key in self._json_override:
                        value = psycopg2.extras.Json(value)
                    values.append(value)
            if strings:
                return " AND ".join(strings), values
            else:
                return None, None

    def _build_query(self, query, limit=None, offset=0):
        """
        INPUT:

        - ``query`` -- a dictionary query, in the mongo style (but only supporting certain special operators)
        - ``limit`` -- a limit on the number of records returned
        - ``offset`` -- an offset on how many records to skip
        - ``qstr`` -- the string built from ``query``.  If ``False`` it is computed.
        - ``values`` -- the tuple of values to go with qstr.  If ``qstr`` is ``False`` it is computed.
        """
        qstr, values = self._parse_dict(query)
        if qstr is None:
            s = ""
        else:
            s = " WHERE " + qstr
        if self._primary_sort in query:
            s += " ORDER BY " + self._sort
        else:
            s += " ORDER BY id"
        if limit is not None:
            s += " LIMIT " + str(limit)
            if offset != 0:
                s += " OFFSET " + str(offset)
        return s, values
    def lucky(self, query, data_level=0, offset=0):
        if data_level == 0:
            vars = "label"
        elif data_level == 1 or self.extras_table is None:
            vars = ", ".join(self._search_cols)
        elif data_level == 2:
            vars = ", ".join(("id",) + self._search_cols)
        else:
            raise RuntimeError("Bad data_level %s"%data_level)
        qstr, values = self._build_query(query, 1, offset)
        selector = "SELECT {0} FROM {1}{2}".format(vars, self.search_table, qstr)
        t = time.time()
        cur = self._execute(selector, values)
        t = time.time() - t
        if t > 0.1:
            self.logger.info(selector%(tuple(values)) + " ran in %ss"%(t))
        if cur.rowcount > 0:
            rec = cur.fetchone()
            if data_level == 0:
                return rec[0]
            elif data_level == 1 or self.extras_table is None:
                return {k:v for k,v in zip(self._search_cols, rec)}
            elif data_level == 2:
                id = rec[0]
                D = {k:v for k,v in zip(self._search_cols, rec[1:])}
                vars = ", ".join(self._extra_cols)
                selector = "SELECT {0} FROM {1} WHERE id = %s".format(vars, self.extras_table)
                t = time.time()
                cur = self._execute(selector, [id])
                t = time.time() - t
                if t > 0.1:
                    self.logger.info(selector%id + " ran in %ss"%(t))
                rec = cur.fetchone()
                for k,v in zip(self._extra_cols, rec):
                    D[k] = v
                return D
    def search_results(self, query, limit=None, offset=0):
        vars = ", ".join(self._search_cols)
        if limit is None:
            qstr, values = self._build_query(query)
        else:
            nres = self._quick_count(query)
            if nres is None:
                prelimit = max(limit, self._count_cutoff - offset)
                qstr, values = self._build_query(query, prelimit, offset)
            else:
                qstr, values = self._build_query(query, limit, offset)
        selector = "SELECT {0} FROM {1}{2}".format(vars, self.search_table, qstr)
        t = time.time()
        cur = self._execute(selector, values)
        t = time.time() -t
        if t > 0.1:
            self.logger.info(selector%(tuple(values)) + " ran in %ss"%(t))
        if limit is None:
            return cur, -1, False
        if nres is None:
            exact_count = (cur.rowcount < prelimit)
            nres = offset + cur.rowcount
        else:
            exact_count = True
        res = cur.fetchmany(limit)
        res = [{k:v for k,v in zip(self._search_cols, rec)} for rec in res]
        return res, nres, exact_count
    def lookup(self, label):
        return self.lucky({'label':label}, data_level=2)
    def count(self, query={}):
        nres = self._quick_count(query)
        if nres is None:
            selector = "SELECT COUNT(*) FROM " + self.search_table
            qstr, values = self._parse_dict(query)
            if qstr is not None:
                selector += " WHERE " + qstr
            t = time.time()
            cur = self._execute(selector, values)
            t = time.time() - t
            if t > 0.1:
                self.logger.info(selector%(tuple(values)) + " ran in %ss"%(t))
            nres = cur.fetchone()[0]
        return nres
    def max(self, col):
        cur = self._execute("SELECT {0} FROM {1} ORDER BY {0} DESC LIMIT 1".format(col, self.search_table))
        return cur.fetchone()[0]
    def random(self, data_level=0):
        """Random label"""
        maxid = self.max('id')
        id = random.randint(0, maxid)
        return self.lucky({'id':id},data_level=data_level)
