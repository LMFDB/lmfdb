# -*- coding: utf-8 -*-

import pymongo
ASC = pymongo.ASCENDING
import flask
import yaml
import lmfdb.base as base
from datetime import datetime
from flask import render_template, request, make_response, url_for
from lmfdb.api import api_page, api_logger
from bson.objectid import ObjectId

# caches the database information
_databases = None


def censor(entries):
    """
    hide some of the databases and collection from the public
    """
    dontstart = ["system.", "test", "upload", "admin", "contrib"]
    censor = ["local", "userdb"]
    for entry in entries:
        if any(entry == x for x in censor) or \
           any(entry.startswith(x) for x in dontstart):
            continue
        yield entry

def init_database_info():
    global _databases
    if _databases is None:
        C = base.getDBConnection()
        _databases = {}
        for db in censor(C.database_names()):
            _databases[db] = list(censor(C[db].collection_names()))


@api_page.route("/")
def index():
    init_database_info()
    databases = _databases
    title = "LMFDB API"
    return render_template("api.html", **locals())


@api_page.route("/<db>/<collection>/<id>")
def api_query_id(db, collection, id):
    return api_query(db, collection, id = id)


@api_page.route("/<db>/<collection>")
def api_query(db, collection, id = None):
    init_database_info()

    # check what is queried for
    if db not in _databases or collection not in _databases[db]:
        return flask.abort(404)

    # parsing the meta parameters _format and _offset
    format = request.args.get("_format", "html")
    offset = int(request.args.get("_offset", 0))
    if offset > 10000:
        if format != "html":
            flask.abort(404)
        else:
            flask.flash("offset too large, please refine your query.", "error")
            return flask.redirect(url_for(".api_query", db=db, collection=collection))

    # preparing the actual database query q
    C = base.getDBConnection()
    q = {}
    
    if id is not None:
        if id.startswith("ObjectId("):
            q["_id"] = ObjectId(id[9:-1])
        else:
            q["_id"] = id
        single_object = True
    else:
        single_object = False
        
    for qkey, qval in request.args.iteritems():
        if qkey.startswith("_"):
            continue
        if qval.startswith("i"):
            qval = int(qval[1:])
        elif qval.startswith("f"):
            qval = float(qval[1:])
            
        q[qkey] = qval

    # executing the query "q" and replacing the _id in the result list
    data = list(C[db][collection].find(q).skip(offset).limit(100))
    for document in data:
        oid = document["_id"]
        if type(oid) == ObjectId:
            document["_id"] = "ObjectId(%s)" % oid
        elif isinstance(oid, basestring):
            document["_id"] = str(oid)

    # preparing the datastructure
    start = offset
    next_req = dict(request.args)
    next_req["_offset"] = offset
    url_args = next_req.copy()
    query = url_for(".api_query", db=db, collection=collection, **next_req)
    offset += len(data)
    next_req["_offset"] = offset
    next = url_for(".api_query", db=db, collection=collection, **next_req)

    # the collected result
    data = {
        "database": db,
        "collection": collection,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
        "start": start,
        "offset": offset,
        "query": query,
        "next": next
    }

    # display of the result (default html)
    if format.lower() == "json":
        return flask.jsonify(**data)
    elif format.lower() == "yaml":
        y = yaml.dump(data,
                      default_flow_style=False,
                      canonical=False,
                      allow_unicode=True)
        return flask.Response(y, mimetype='application/yaml')
    else:
        location = "%s/%s" % (db, collection)
        title = "API - " + location
        bc = [("API", url_for(".index")), (location, query)]
        return render_template("collection.html",
                               title=title,
                               single_object=single_object,
                               url_args = url_args,
                               bread=bc,
                               **data)

