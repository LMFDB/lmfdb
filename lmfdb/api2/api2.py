
from lmfdb.api2 import api2_page
from flask import render_template, request, Response, make_response
from lmfdb.api2.searchers import searchers, singletons
from . import utils


@api2_page.route("/api.css")
def api_css():
    response = make_response(render_template("api.css"))
    response.headers['Content-type'] = 'text/css'
    # don't cache css file, if in debug mode.
    if True:
        response.headers['Cache-Control'] = 'no-cache, no-store'
    else:
        response.headers['Cache-Control'] = 'public, max-age=600'
    return response


@api2_page.route("/")
def index():
    title = "API Description"
    return render_template("api2.html", **locals())


@api2_page.route("/demo")
def demo():
    title = "API Demo"
    return render_template("api_demo.html", **locals())


@api2_page.route("/<other>")
def other(other):
    return Response(utils.build_api_error(other), mimetype='application/json')


@api2_page.route("/livepg/<db>")
def live_page_pg(db):
    if (db.startswith("<") and db.endswith(">")):
        title = "API Description"
        return render_template("example.html", **locals())
    search = utils.create_search_dict(table = db, request = request)
    for el in request.args:
        utils.interpret(search['query'], el, request.args[el], None)
    search_tuple = utils.simple_search(search)
    return Response(utils.build_api_search(db, search_tuple, request = request), mimetype='application/json')


@api2_page.route("/pretty/<path:path_var>")
def prettify_live(path_var):
    bread = []
    return render_template('view.html', data_url=path_var, bread=bread)


@api2_page.route("/singletons/<path:path_var>")
def handle_singletons(path_var):
    val = path_var.rpartition('/')
    label = val[2]
    baseurl = val[0]
    while baseurl not in singletons:
        val = baseurl.rpartition('/')
        if val[0] == '':
            break
        baseurl = val[0]
        label = val[2] + '/' + label

    if baseurl in singletons:
        search = utils.create_search_dict(table = singletons[baseurl]['table'],
            request = request)
        if singletons[baseurl]['full_search']:
            return Response(singletons[baseurl]['full_search'], mimetype='application/json')
        elif singletons[baseurl]['simple_search']:
            singletons[baseurl]['simple_search'](search, baseurl, label)
        else:
            search['query'] = {singletons[baseurl]['key']:label}
        search_tuple = utils.simple_search(search)
        return Response(utils.build_api_search(path_var, search_tuple, request = request), mimetype='application/json')
    return Response(utils.build_api_error(path_var), mimetype='application/json')


@api2_page.route("/description/searchers")
def list_searchers():
    names=[]
    h_names=[]
    descs=[]
    for el in searchers:
        names.append(el)
        h_names.append(searchers[el].get_name())
        descs.append(searchers[el].get_description())
    return Response(
        utils.build_api_searchers(names, h_names, descs, request=request),
        mimetype='application/json'
    )


@api2_page.route("/description/<searcher>")
def list_descriptions(searcher):
    if (searcher.startswith("<") and searcher.endswith(">")):
        title = "API Description"
        return render_template("example.html", **locals())

    try:
        val = searchers[searcher]
    except KeyError:
        val = None

    if (val):
        lst = val.get_info()
    else:
        return Response(utils.build_api_error(searcher), mimetype='application/json')
    if lst:
        return Response(
            utils.build_api_descriptions(searcher, lst, request=request),
            mimetype='application/json'
        )


@api2_page.route("/inventory/<searcher>")
def list_responses(searcher):
    if (searcher.startswith("<") and searcher.endswith(">")):
        title = "API Description"
        return render_template("example.html", **locals())

    try:
        val = searchers[searcher]
    except KeyError:
        val = None

    if (val):
        lst = val.get_inventory()
    else:
        return Response(utils.build_api_error(searcher), mimetype='application/json')
    if lst:
        return Response(
            utils.build_api_inventory(searcher, lst, request=request),
            mimetype='application/json'
        )


@api2_page.route("/data/<searcher>")
def get_data(searcher):
    if (searcher.startswith("<") and searcher.endswith(">")):
        title = "API Description"
        return render_template("example.html", **locals())

    try:
        val = searchers[searcher]
    except KeyError:
        val = None

    if not val:
        return Response(utils.build_api_error(searcher), mimetype='application/json')

    search = val.auto_search(request)

    return Response(
        utils.build_api_search('/data/'+searcher, search, request=request),
        mimetype='application/json'
    )
