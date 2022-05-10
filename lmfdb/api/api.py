# -*- coding: utf-8 -*-
from urllib.parse import unquote
import re
import yaml
import json
from collections import defaultdict
from psycopg2.extensions import QueryCanceledError
from lmfdb import db
from lmfdb.backend.encoding import Json
from lmfdb.utils import flash_error
from datetime import datetime
from flask import (render_template, request, url_for, current_app,
                   abort, redirect, Response)
from lmfdb.api import api_page, api_logger


buffer = memoryview


def pluck(n, list):
    return [_[n] for _ in list]


def quote_string(value):
    if isinstance(value, str):
        return repr(value)
    return value


def pretty_document(rec, sep=", ", id=True):
    # sort keys and remove _id for html display
    attrs = sorted([(key, quote_string(rec[key])) for key in rec.keys() if (id or key != 'id')])
    return "{" + sep.join("'%s': %s" % attr for attr in attrs) + "}"


def hidden_collection(c):
    """
    hide some collections from the main page (still available via direct requests)
    """
    return c.startswith("test") or c.endswith(".rand") or c.endswith(".stats") or c.endswith(".chunks") or c.endswith(".new") or c.endswith(".old")

#def collection_indexed_keys(collection):
#    """
#    input: cursor for the collection
#    output: a set with all the keys indexed
#    """
#    return set([t[0] for t in sum([val['key'] for name, val in collection.index_information().items() if name!='_id_'],[])])

def get_database_info(show_hidden=False):
    info = defaultdict(list)
    for table in db.tablenames:
        i = table.find('_')
        if i == -1:
            raise RuntimeError
        database = table[:i]
        coll = getattr(db, table)
        info[database].append((table, table[i+1:], coll.count()))
    return info

@api_page.route("/")
def index(show_hidden=False):
    databases = get_database_info(show_hidden)
    title = "Database"
    return render_template("api.html", **locals())

@api_page.route("/all")
def full_index():
    return index(show_hidden=True)

@api_page.route("/stats")
def stats():
    def mb(x):
        return int(round(x/2**20.))
    info={}
    info['minsizes'] = ['0','1','10','100','1000','10000','100000']
    info['minsize'] = request.args.get('minsize','1').strip()
    if not info['minsize'] in info['minsizes']:
        info['minsizes'] = '1'
    info['groupby'] = 'db' if request.args.get('groupby','').strip().lower() == 'db' else ''
    info['sortby'] = request.args.get('sortby','size').strip().lower()
    if not info['sortby'] in ['size', 'objects', 'name']:
        info['sortby'] = 'size'
    nobjects = size = dataSize = indexSize = 0
    dbSize = defaultdict(int)
    dbObjects = defaultdict(int)
    stats = {}
    table_sizes = db.table_sizes()
    def split_db(tablename):
        i = tablename.find('_')
        if i == -1:
            return '', tablename
        else:
            return tablename[:i], tablename[i+1:]
    for tablename, sizes in table_sizes.items():
        dname, name = split_db(tablename)
        dbSize[dname] += sizes['total_bytes']
        dbObjects[dname] += sizes['nrows']
    for tablename, sizes in table_sizes.items():
        tsize = sizes['total_bytes']
        size += tsize
        csize = mb(tsize)
        nobjects += sizes['nrows']
        indexSize += sizes['index_bytes']
        if csize >= int(info['minsize']):
            dname, name = split_db(tablename)
            if tablename not in db.tablenames:
                link = tablename
            else:
                link = '<a href = "' + url_for(".api_query", table=tablename) + '">' + tablename + '</a>'
            if not sizes['toast_bytes']:
                sizes['toast_bytes'] = 0
            if sizes['nrows']:
                avg_size = int(round(float(sizes['table_bytes'] + sizes['toast_bytes'] + sizes['extra_bytes']) / sizes['nrows']))
            else:
                avg_size = 0
            stats[tablename] = {
                'db':dname, 'table':link, 'dbSize':dbSize[dname], 'dbObjects':dbObjects[dname],
                'size': csize, 'avgObjSize':avg_size,
                'indexSize':mb(sizes['index_bytes']), 'dataSize':mb(sizes['table_bytes'] + sizes['toast_bytes'] + sizes['extra_bytes']),
                'countsSize':mb(sizes['counts_bytes']), 'statsSize':mb(sizes['stats_bytes']),
                'nrows': sizes['nrows'], 'nstats': sizes['nstats'], 'ncounts': sizes['ncounts']}
    dataSize = size - indexSize
    info['ntables'] = len(table_sizes)
    info['nobjects'] = nobjects
    info['size'] = mb(size)
    info['dataSize'] = mb(dataSize)
    info['indexSize'] = mb(indexSize)
    if info['sortby'] == 'name':
        sortedkeys = sorted(list(stats))
    elif info['sortby'] == 'objects' and info['groupby'] == 'db':
        sortedkeys = sorted(list(stats),key=lambda x: (-stats[x]['dbObjects'],stats[x]['db'],-stats[x]['nrows'],stats[x]['table']))
    elif info['sortby'] == 'objects':
        sortedkeys = sorted(list(stats),key=lambda x: (-stats[x]['nrows'],stats[x]['db'],stats[x]['table']))
    elif info['sortby'] == 'size' and info['groupby'] == 'db':
        sortedkeys = sorted(list(stats),key=lambda x: (-stats[x]['dbSize'],stats[x]['db'],-stats[x]['size'],stats[x]['table']))
    else:
        sortedkeys = sorted(list(stats),key=lambda x: (-stats[x]['size'],stats[x]['db'],stats[x]['table']))
    info['stats'] = [stats[key] for key in sortedkeys]
    return render_template('api-stats.html', info=info)


@api_page.route("/<table>/<id>")
def api_query_id(table, id):
    if id == 'schema':
        out = ''
        table = getattr(db, table)
        col_type = table.col_type
        out = """
        <table>
        <tr>
        <th> name </th><th>type</th>
        </tr>
        """
        for c in sorted(col_type.keys()):
            out += "<tr><td>%s</td><td> %s </td>\n" % (c, col_type[c])
        return out
    else:
        return api_query(table, id=id)


@api_page.route("/<table>")
@api_page.route("/<table>/")
def api_query(table, id = None):
    #if censored_table(table):
    #    return abort(404)

    # parsing the meta parameters _format and _offset
    format = request.args.get("_format", "html")
    offset = int(request.args.get("_offset", 0))
    DELIM = request.args.get("_delim", ",")
    fields = request.args.get("_fields", None)
    sortby = request.args.get("_sort", None)
    def apierror(msg, flash_extras=[], code=404, table=True):
        if format == "html":
            flash_error(msg, *flash_extras)
            if table:
                return redirect(url_for(".api_query", table=table))
            else:
                return redirect(url_for(".index"))
        else:
            return abort(code, msg % tuple(flash_extras))

    if fields:
        fields = ['id'] + fields.split(DELIM)
    else:
        fields = 3

    if sortby:
        sortby = sortby.split(DELIM)

    if offset > 10000:
        return apierror("offset %s too large, please refine your query.", [offset])

    # preparing the actual database query q
    try:
        coll = getattr(db, table)
    except AttributeError:
        return apierror("table %s does not exist", [table], table=False)
    q = {}

    # if id is set, just go and get it, ignore query parameeters
    if id is not None:
        if offset:
            return apierror("Cannot include offset with id")
        single_object = True
        api_logger.info("API query: id = '%s', fields = '%s'" % (id, fields))
        if re.match(r'^\d+$', id):
            id = int(id)
        else:
            return apierror("id '%s' must be an integer", [id])
        data = coll.lucky({'id':id}, projection=fields)
        data = [data] if data else []
    else:
        single_object = False

        for qkey, qval in request.args.items():
            from ast import literal_eval
            try:
                if qkey.startswith("_"):
                    continue
                elif qval.startswith("s"):
                    qval = qval[1:]
                elif qval.startswith("i"):
                    qval = int(qval[1:])
                elif qval.startswith("f"):
                    qval = float(qval[1:])
                elif qval.startswith("ls"):      # indicator, that it might be a list of strings
                    qval = qval[2].split(DELIM)
                elif qval.startswith("li"):
                    qval = [int(_) for _ in qval[2:].split(DELIM)]
                elif qval.startswith("lf"):
                    qval = [float(_) for _ in qval[2:].split(DELIM)]
                elif qval.startswith("py"):     # literal evaluation
                    qval = literal_eval(qval[2:])
                elif qval.startswith("cs"):     # containing string in list
                    qval = { "$contains": [qval[2:]] }
                elif qval.startswith("ci"):
                    qval = { "$contains": [int(qval[2:])] }
                elif qval.startswith("cf"):
                    qval = { "contains": [float(qval[2:])] }
                elif qval.startswith("cpy"):
                    qval = { "$contains": [literal_eval(qval[3:])] }
            except Exception:
                # no suitable conversion for the value, keep it as string
                pass

            # update the query
            q[qkey] = qval

        # assure that one of the keys of the query is indexed
        # however, this doesn't assure that the query will be fast...
        #if q != {} and len(set(q.keys()).intersection(collection_indexed_keys(coll))) == 0:
        #    flash_error("no key in the query %s is indexed.", q)
        #    return redirect(url_for(".api_query", table=table))

        # sort = [('fieldname1', 1 (ascending) or -1 (descending)), ...]
        if sortby is not None:
            sort = []
            for key in sortby:
                if key.startswith("-"):
                    sort.append((key[1:], -1))
                else:
                    sort.append((key, 1))
        else:
            sort = None

        # executing the query "q" and replacing the _id in the result list
        # So as not to preserve backwards compatibility (see test_api_usage() test)
        if table=='ec_curvedata':
            for oldkey, newkey in zip(['label', 'iso', 'number'], ['Clabel', 'Ciso', 'Cnumber']):
                if oldkey in q:
                    q[newkey] = q[oldkey]
                    q.pop(oldkey)
        try:
            data = list(coll.search(q, projection=fields, sort=sort, limit=100, offset=offset))
        except QueryCanceledError:
            return apierror("Query %s exceeded time limit.", [q], code=500)
        except KeyError as err:
            return apierror("No key %s in table %s", [err, table])
        except Exception as err:
            return apierror(str(err))

    if single_object and not data:
        return apierror("no document with id %s found in table %s.", [id, table])

    # fixup data for display and json/yaml encoding
    if 'bytea' in coll.col_type.values():
        for row in data:
            for key, val in row.items():
                if type(val) == buffer:
                    row[key] = "[binary data]"
        #data = [ dict([ (key, val if coll.col_type[key] != 'bytea' else "binary data") for key, val in row.items() ]) for row in data]
    data = Json.prep(data)

    # preparing the datastructure
    start = offset
    next_req = dict(request.args)
    next_req["_offset"] = offset
    url_args = next_req.copy()
    query = url_for(".api_query", table=table, **next_req)
    offset += len(data)
    next_req["_offset"] = offset
    nxt = url_for(".api_query", table=table, **next_req)

    # the collected result
    data = {
        "table": table,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "start": start,
        "offset": offset,
        "query": query,
        "next": nxt,
        "rec_id": 'id' if coll._label_col is None else coll._label_col,
    }

    if format.lower() == "json":
        #return flask.jsonify(**data) # can't handle binary data
        return current_app.response_class(json.dumps(data, indent=2), mimetype='application/json')
    elif format.lower() == "yaml":
        y = yaml.dump(data,
                      default_flow_style=False,
                      canonical=False,
                      allow_unicode=True)
        return Response(y, mimetype='text/plain')
    else:
        # sort displayed records by key (as jsonify and yaml_dump do)
        data["pretty"] = pretty_document
        location = table
        title = "Database - " + location
        bc = [("Database", url_for(".index")), (table,)]
        query_unquote = unquote(data["query"])
        description = coll.description()
        if description:
            title += " (%s)" % description
        search_schema = [(col, coll.col_type[col])
                         for col in sorted(coll.search_cols)]
        extra_schema = [(col, coll.col_type[col])
                        for col in sorted(coll.extra_cols)]
        return render_template("collection.html",
                               title=title,
                               search_schema={table: search_schema},
                               extra_schema={table: extra_schema},
                               single_object=single_object,
                               query_unquote = query_unquote,
                               url_args = url_args,
                               bread=bc,
                               **data)

# This function is used to show the data associated to a given homepage, which could possibly be from multiple tables.
def datapage(labels, tables, title, bread, label_cols=None, sorts=None):
    """
    INPUT:

    - ``labels`` -- a string giving a label used in the tables (e.g. '11.a1' for an elliptic curve), or a list of strings (one per table)
    - ``tables`` -- a search table or list of search tables (as strings)
    - ``title`` -- title for the page
    - ``bread`` -- bread for the page
    - ``label_cols`` -- a list of column names of the same length; defaults to using ``label`` everywhere
    - ``sorts`` -- lists for sorting each table; defaults to None
    """
    format = request.args.get("_format", "html")
    if not isinstance(tables, list):
        tables = [tables]
    if not isinstance(labels, list):
        labels = [labels for table in tables]
    if label_cols is None:
        label_cols = ["label" for table in tables]
    if sorts is None:
        sorts = [None for table in tables]
    assert len(labels) == len(tables) == len(label_cols)

    def apierror(msg, flash_extras=[], code=404, table=False):
        if format == "html":
            flash_error(msg, *flash_extras)
            if table:
                return redirect(url_for("API.api_query", table=table))
            else:
                return redirect(url_for("API.index"))
        else:
            return abort(code, msg % tuple(flash_extras))
    data = []
    search_schema = {}
    extra_schema = {}
    for label, table, col, sort in zip(labels, tables, label_cols, sorts):
        q = {col: label}
        coll = db[table]
        try:
            data.append(list(coll.search(q, projection=3, sort=sort)))
        except QueryCanceledError:
            return apierror("Query %s exceeded time limit.", [q], code=500, table=table)
        except KeyError as err:
            return apierror("No key %s in table %s", [err, table], table=table)
        except Exception as err:
            return apierror(str(err), table=table)
        search_schema[table] = [(col, coll.col_type[col])
                                for col in sorted(coll.search_cols)]
        extra_schema[table] = [(col, coll.col_type[col])
                               for col in sorted(coll.extra_cols)]
    data = Json.prep(data)

    # the collected result
    data = {
        "labels": labels,
        "tables": tables,
        "label_cols": label_cols,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
    }
    if format.lower() == "json":
        return current_app.response_class(json.dumps(data, indent=2), mimetype='application/json')
    elif format.lower() == "yaml":
        y = yaml.dump(data,
                      default_flow_style=False,
                      canonical=False,
                      allow_unicode=True)
        return Response(y, mimetype='text/plain')
    else:
        return render_template("apidata.html",
                               title=title,
                               search_schema=search_schema,
                               extra_schema=extra_schema,
                               bread=bread,
                               pretty=pretty_document,
                               **data)
