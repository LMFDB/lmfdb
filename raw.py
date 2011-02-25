import json

from base import app
from flask import Flask, session, g, render_template, url_for, request, redirect, make_response
from utilities import to_dict, parse_range
import base

def is_safe(name):
    return name not in ('admin', 'local', 'system.indexes')

@app.route("/raw")
def database_list():
    all_db = []
    C = base.getDBConnection()
    for db_name in C.database_names():
        if db_name in ('admin', 'local'):
            continue
        db = getattr(C, db_name)
        all_db.append((db_name, filter(is_safe, db.collection_names())))
    return render_template("raw/index.html", all_db = all_db, info={})

@app.route("/raw/<db_name>/<coll_name>")
def database_query(db_name, coll_name):
    if not is_safe(db_name) or not is_safe(coll_name):
        return "Nope."
    C = base.getDBConnection()
    if db_name not in C.database_names():
        return "No such database."
    db = getattr(C, db_name)
    if coll_name not in db.collection_names():
        return "No such collection."
    
    args = to_dict(request.args)
    info = dict(args)
    collection = getattr(db, coll_name)
    collection.ensure_index('metadata', background=True)
    metadata = collection.find_one({'metadata': 'metadata'})
    if metadata:
        del metadata['_id']
        info['metadata'] = json.dumps(metadata, sort_keys=True, indent=4)
    else:
        info['metadata'] = "No metadata."
    indices = set()
    for name, index in collection.index_information().items():
        key = index['key'][0][0]
        if key == '_id':
            continue
        indices.add(key)
    try:
        indices.remove('metadata')
    except ValueError:
        pass
    if args.get('_fields'):
        info['default_fields'] = args['_fields'].split(',')
    else:
        # TODO: pull from metadata
        info['default_fields'] = list(indices)
    try:
        limit = int(args.pop('_limit'))
    except (TypeError, KeyError):
        info['_limit'] = limit = 100
    if '_search' in args:
        query = {}
        for key, value in args.items():
            if key[0] == '_':
                continue
            try:
                query[key] = parse_range(value, int)
            except (TypeError, ValueError):
                try:
                    query[key] = parse_range(value, float)
                except (TypeError, ValueError):
                    query[key] = parse_range(value, str)
        res = collection.find(query).limit(limit)
    else:
        res = None
    # TODO: is there a better way to do [this url] + "&format=..."?
    non_format_args = to_dict(request.args)
    if '_format' in non_format_args:
        del non_format_args['_format']
    info['formats'] = [(format, url_for('database_query', db_name=db_name, coll_name=coll_name, _format=format, **non_format_args)) for format in ('text', 'csv', 'json')]
    format = args.get('_format', 'html')
    if format in ('txt', 'text'):
        info['sep'] = ' '
    elif format == 'csv':
        info['sep'] = ','
    elif format == 'json':
        res = json_iter(res)
        info['default_fields'] = ['all']
        info['sep'] = ''
    else:
        return render_template("raw/query.html", db=db_name, coll=coll_name, info=info, indices=indices, res=res)
    # not html
    response = make_response(render_template("raw/query_download.html", db=db_name, coll=coll_name, info=info, indices=indices, res=res))
    response.headers['Content-type'] = 'text/plain'
    return response

def json_iter(iterator):
    for item in iterator:
        del item['_id']
        yield {'all': json.dumps(item, sort_keys=True, indent=4)}
