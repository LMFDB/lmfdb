from flask import render_template, request, url_for, make_response, jsonify, Blueprint
from flask_login import login_required
import inventory_viewer
import inventory_live_data
import lmfdb_inventory as linv
import inventory_helpers as ih
import sys, os
from datetime import datetime as dt

# Initialize the Flask application
inventory_app = Blueprint('inventory_app', __name__, template_folder='./templates', static_folder='./static', static_url_path = 'static/')
url_pref = '/inventory/'

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
#Set to info, debug etc
linv.init_run_log(level_name='warning')

@inventory_app.route("style.css")
def css():
    response = make_response(render_template("inv_style.css"))
    response.headers['Content-type'] = 'text/css'
    # don't cache css file, if in debug mode.
    if True:
        response.headers['Cache-Control'] = 'no-cache, no-store'
    else:
        response.headers['Cache-Control'] = 'public, max-age=600'
    return response

#The root of edit pages, lists databases having inventory data
@inventory_app.route('')
def show_edit_root():
    try:
        listing = inventory_viewer.get_edit_list()
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('edit_show_list.html', db_name = None, nice_name=None, listing=listing, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]])

@inventory_app.route('livedata')
def generate_live_listing():
    try:
        results = inventory_live_data.get_db_lists()
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#Edit page per DB, lists collections
@inventory_app.route('<string:id>/')
def show_edit_child(id):
    try:
        nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = None)
        listing = inventory_viewer.get_edit_list(id)
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('edit_show_list.html', db_name=id, nice_name=nice_name, listing=listing, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)]])

#Viewer page per collection, shows formatted fields
@inventory_app.route('<string:id>/<string:id2>/')
def show_inventory(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)]]
    return render_template('view_inventory.html', db_name=id, collection_name=id2, bread=bread, table_fields=linv.display_field_order(), info_fields=linv.info_field_order())

@inventory_app.route('<string:id>/<string:id2>/records/')
def show_records(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['records', url_for('inventory_app.show_records', id=id, id2=id2)]]

    try:
        nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = id2)
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)
    return render_template('view_records.html', db_name=id, collection_name=id2, bread=bread, record_fields=linv.record_field_order(), nice_name=nice_name)

@inventory_app.route('<string:id>/<string:id2>/indices/')
def show_indices(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['indices', url_for('inventory_app.show_indices', id=id, id2=id2)]]
    try:
        nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = id2)
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)
    return render_template('view_indices.html', db_name=id, collection_name=id2, bread=bread, nice_name=nice_name, index_fields=linv.index_field_order())

#Edit page per collection, shows editable fields
@inventory_app.route('<string:id>/<string:id2>/edit/')
@login_required
def show_edit_inventory(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['edit', url_for('inventory_app.show_edit_inventory', id=id, id2=id2)]]
    return render_template('edit_inventory.html', db_name=id, collection_name=id2, type_data=linv.get_type_strings_as_json(), bread=bread, table_fields=linv.display_field_order())

#Edit data source to populate inventory pages
@inventory_app.route('<string:id>/<string:id2>/edit/data/')
@inventory_app.route('<string:id>/<string:id2>/data/')
def fetch_edit_inventory(id, id2):
    try:
        results = inventory_viewer.get_inventory_for_display(id+'.'+id2)
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#Edit page per collection, shows editable fields
@inventory_app.route('<string:id>/<string:id2>/records/edit/')
@login_required
def show_edit_records(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['records', url_for('inventory_app.show_records', id=id, id2=id2)], ['edit', url_for('inventory_app.show_edit_records', id=id, id2=id2)]]
    nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = id2)
    return render_template('edit_records.html', db_name=id, collection_name=id2, type_data=linv.get_type_strings_as_json(), record_fields=linv.record_field_order(), bread=bread, nice_name =nice_name, record_noedit=linv.record_noeditable())

#Data source to populate inventory pages
@inventory_app.route('<string:id>/<string:id2>/records/data/')
@inventory_app.route('<string:id>/<string:id2>/records/edit/data/')
def fetch_edit_records(id, id2):
    try:
        results = inventory_viewer.get_records_for_display(id+'.'+id2)
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#Data source to populate inventory pages
@inventory_app.route('<string:id>/<string:id2>/indices/data/')
def fetch_indices(id, id2):
    try:
        results = inventory_viewer.get_indices_for_display(id+'.'+id2)
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#Page shown after successful edit submission
@inventory_app.route('success/')
def edit_success(request=request):
    #Check response for referrer and return redirect page
    #We want to send user back to the parent of the page they got here from
    referrer = str(request.referrer)
    url_info = ih.parse_edit_url(referrer)
    if not url_info['parent']:
        new_url = url_for('inventory_app.show_edit_root')
    else:
        new_url = url_info['parent']
    print url_info, new_url
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
    return render_template('edit_success.html', new_url=new_url, db_name=url_info['db_name'], collection_name=url_info['collection_name'], bread=bread)

#Page shown after failing edits
#These failures should only be severe code failures, or possibly collisions
@inventory_app.route('failure/', methods=['GET'])
def edit_failure(request=request):
    #Check response for referrer and return redirect page
    #We want to send user back to the page they got here from to retry
    try:
        errcode = int(request.args.get('code'))
        errstr = inventory_viewer.err_registry[errcode].message
    except:
        errcode = -1
        errstr = "Undefined"
        pass
    linv.log_dest.error("Returning fail page "+ errstr)

    new_url = str(request.referrer)
    url_info = ih.parse_edit_url(new_url)

    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
    mess = "Error "+str(errcode)+": ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+errstr+" for "+url_info['db_name']+"."+url_info['collection_name']
    return render_template('edit_failure.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)


#Destination for submission
@inventory_app.route('submit', methods=['POST'])
@login_required
def submit_edits():
    #Do the submission
    try:
        inventory_viewer.apply_submitted_edits(request)
    except Exception as e:
        #apply_submitted_edits only throws for serious code errors
        return jsonify({'url':url_for('inventory_app.edit_failure', code=e.errcode), 'code':302, 'success':False})

    #Return a redirect to be done on client
    return jsonify({'url':url_for('inventory_app.edit_success'), 'code':302, 'success':True})

#Functions for rescraping etc
@inventory_app.route('rescrape/')
@login_required
def show_rescrape_page():
    try:
        listing = inventory_live_data.get_db_lists()
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_rescrape_page')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('scrape_main.html', listing=listing, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_rescrape_page')]])

@inventory_app.route('rescrape/progress/<string:uid>/')
@login_required
def show_rescrape_poll(uid):
    try:
        progress = inventory_live_data.get_progress(uid)
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_rescrape_poll', uid=uid)]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('scrape_progress.html', uid=uid, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_rescrape_poll', uid=uid)]])

@inventory_app.route('rescrape/progress/<string:uid>/monitor/')
@login_required
def fetch_progress_data(uid):
    try:
        progress = inventory_live_data.get_progress(uid)
    except ih.ConnectOrAuthFail as e:
        progress = {'n_colls':0, 'curr_coll':0, 'progress_in_current':0}
    return jsonify(progress)

@inventory_app.route('rescrape/progress/<string:uid>/complete/')
@login_required
def fetch_summary_data(uid):
    try:
        data = inventory_live_data.collate_orphans_by_uid(uid)
    except ih.ConnectOrAuthFail as e:
        data = {}
    return jsonify(data)

@inventory_app.route('rescrape/submit', methods=['POST'])
@login_required
def submit_rescrape_request():
    uid = inventory_live_data.trigger_scrape(request.data)
    return jsonify({'url':url_for('inventory_app.show_rescrape_poll', uid=uid), 'uid':uid})
