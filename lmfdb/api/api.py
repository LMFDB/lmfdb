# -*- coding: utf-8 -*-

import pymongo
ASC = pymongo.ASCENDING
import flask
import yaml
import lmfdb.base as base
from datetime import datetime
from flask import render_template, request, make_response, url_for
from lmfdb.api import api_page, api_logger

### INITIALIZATION
_databases = None


def censor(entries):
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
    title = "API Overview"
    return render_template("api.html", **locals())

@api_page.route("/<db>/<collection>")
def api_query(db, collection):
    init_database_info()
    if db not in _databases or collection not in _databases[db]:
        return flask.abort(404)

    format = request.args.get("_format", "json")
    offset = request.args.get("_offset", 0)
    C = base.getDBConnection()

    qargs = dict(request.args)

    q = list(C[db][collection].find().skip(offset).limit(100))
    for document in q:
        document["_id"] = str(document["_id"])
    offset += len(q)
    qargs["_offset"] = offset
    next = url_for(".api_query", db=db, collection=collection, **qargs)

    data = {
        "database": db,
        "collection": collection,
        "timestamp": datetime.utcnow().isoformat(),
        "data": q,
        "next": next
    }

    if format == "json":
        return flask.jsonify(**data)
    elif format == "yaml":
        y = yaml.dump(data,
                      default_flow_style=False,
                      canonical=False,
                      allow_unicode=True)
        return flask.Response(y, mimetype='application/yaml')
    elif format == "html":
        return make_response(str(data))

