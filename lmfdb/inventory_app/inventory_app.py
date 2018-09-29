from flask import render_template, request, url_for, make_response, jsonify, Blueprint
from flask_login import login_required
from lmfdb.users import admin_required
import inventory_viewer
import inventory_live_data
import inventory_control
import inventory_consistency
import lmfdb_inventory as linv
import inventory_helpers as ih
from datetime import datetime as dt
import json

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            u = obj.__str__()
            return u
        except:
            return json.JSONEncoder.default(self, obj)

# Initialize the Flask application
inventory_app = Blueprint('inventory_app', __name__, template_folder='./templates', static_folder='./static', static_url_path = 'static/')
url_pref = '/inventory/'

#sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
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

#------ Listing pages -----------------------------------
#Custom error for bad table names
class BadNameError(KeyError):
    """Raise when requested DB or table doesn't exist"""
    def __init__(self, message):
        mess = "Requested db or table does not exist"
        super(KeyError, self).__init__(mess)

#The root of edit pages, lists databases having inventory data
@inventory_app.route('')
def show_edit_root():
    try:
        listing = inventory_viewer.retrieve_db_listing()
        lockout = inventory_live_data.get_lockout_state()
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('edit_show_list.html', db_name = None, nice_name=None, listing=listing, lockout=lockout, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]])

#Page per DB, lists tables
@inventory_app.route('<string:id>/')
def show_edit_child(id):
    try:
        valid = inventory_viewer.is_valid_db(id)
        if not valid:
            raise BadNameError('')
        nice_name = inventory_viewer.get_nicename(db_name = id, table_name = None)
        listing = inventory_viewer.retrieve_db_listing(id)
        lockout = inventory_live_data.get_lockout_state()
    except BadNameError as e:
        return render_template('edit_bad_name.html', db_name=id, table_name=None, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)]])
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")
        new_url = str(request.referrer)
        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('edit_show_list.html', db_name=id, nice_name=nice_name, listing=listing, lockout=lockout, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)]])

#-------- Viewer pages -----------------------------------

#Viewer page per table, shows formatted fields
@inventory_app.route('<string:id>/<string:id2>/')
def show_inventory(id, id2):
    try:
        valid = inventory_viewer.is_valid_db_table(id, id2)
        if not valid:
            raise BadNameError('')
    except BadNameError:
        return render_template('edit_bad_name.html', db_name=id, table_name=id2, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)]])
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)]]
    return render_template('view_inventory.html', db_name=id, table_name=id2, bread=bread, table_fields=linv.display_field_order(), info_fields=linv.info_field_order())

#Viewer page for indices
@inventory_app.route('<string:id>/<string:id2>/indices/')
def show_indices(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['indices', url_for('inventory_app.show_indices', id=id, id2=id2)]]
    try:
        valid = inventory_viewer.is_valid_db_table(id, id2)
        if not valid:
            raise BadNameError('')
        nice_name = inventory_viewer.get_nicename(db_name = id, table_name = id2)
    except BadNameError as e:
        return render_template('edit_bad_name.html', db_name=id, table_name=id2, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_indices', id=id, id2=id2)]])
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")

        new_url = str(request.referrer)

        bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)
    return render_template('view_indices.html', db_name=id, table_name=id2, bread=bread, nice_name=nice_name, index_fields=linv.index_field_order())

#-------- Editing pages ----------------------------------------

#Inventory edit page per table
@inventory_app.route('<string:id>/<string:id2>/edit/')
@login_required
def show_edit_inventory(id, id2):
    try:
        valid = inventory_viewer.is_valid_db_table(id, id2)
        if not valid:
            raise BadNameError('')
        locked = inventory_live_data.get_lockout_state()
    except BadNameError:
        return render_template('edit_bad_name.html', db_name=id, table_name=id2, bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_edit_inventory', id=id, id2=id2)]])
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['edit', url_for('inventory_app.show_edit_inventory', id=id, id2=id2)]]
    if locked:
        return render_template('edit_locked.html')
    else:
        return render_template('edit_inventory.html', db_name=id, table_name=id2, type_data=linv.get_type_strings_as_json(), bread=bread, table_fields=linv.display_field_order())

#-------- Data sources (json returns) ----------------------------------------

#Live (direct from LMFDB) list of database/table names
@inventory_app.route('live/')
def generate_live_listing():
    try:
        results = inventory_live_data.get_db_lists()
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Connection failure, returning no data")
        return "{}"
    return jsonify(results)

#Data source to populate inventory pages
@inventory_app.route('<string:id>/<string:id2>/edit/data/')
@inventory_app.route('<string:id>/<string:id2>/data/')
def fetch_edit_inventory(id, id2):
    try:
        results = inventory_viewer.get_inventory_for_display(id2)
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#Data source to populate indices pages
@inventory_app.route('<string:id>/<string:id2>/indices/data/')
def fetch_indices(id, id2):
    try:
        results = inventory_viewer.get_indices_for_display(id2)
    except ih.ConnectOrAuthFail:
        linv.log_dest.error("Returning auth fail page")
        return "{}"
    return jsonify(results)

#-------- Submit and result pages ----------------------------------------

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
    #print url_info, new_url
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
    return render_template('edit_success.html', new_url=new_url, db_name=url_info['db_name'], table_name=url_info['table_name'], bread=bread)

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
        if inventory_live_data.get_lockout_state():
            errcode = 16
            errstr = inventory_viewer.err_registry[errcode].message
        else:
            errcode = -1
            errstr = "Undefined"
    linv.log_dest.error("Returning fail page "+ errstr)

    new_url = str(request.referrer)
    url_info = ih.parse_edit_url(new_url)

    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]]
    mess = "Error "+str(errcode)+": ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+errstr+" for "+url_info['db_name']+"."+url_info['table_name']
    return render_template('edit_failure.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

#Destination for edit submissions
@inventory_app.route('submit/', methods=['POST'])
@login_required
def submit_edits():
    #Do the submission
    try:
        inventory_viewer.apply_submitted_edits(request)
    except inventory_viewer.EditLockError as e:
        return jsonify({'url':url_for('inventory_app.edit_failure', code=e.errcode), 'code':400, 'success':False, 'fail':'Editing disallowed'})
    except Exception as e:
        #apply_submitted_edits only throws for serious code errors
        return jsonify({'url':url_for('inventory_app.edit_failure', code=e.errcode), 'code':302, 'success':False, 'fail':'Unknown Error'})

    #Return a redirect to be done on client
    return jsonify({'url':url_for('inventory_app.edit_success'), 'code':302, 'success':True})

# ---Functions for rescraping etc -----------------------------------
@inventory_app.route('rescrape/')
@login_required
@admin_required
def show_rescrape_page():

    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], ['rescrape', url_for('inventory_app.show_rescrape_page')]]
    try:
        listing = inventory_live_data.get_db_lists()
    except ih.ConnectOrAuthFail as e:
        linv.log_dest.error("Returning auth fail page")
        new_url = str(request.referrer)
        mess = "Connect or Auth failure: ("+str(dt.now().strftime('%d/%m/%y %H:%M:%S'))+") "+e.message
        return render_template('edit_authfail.html', new_url=new_url, message = mess, submit_contact=linv.email_contact, bread=bread)

    return render_template('scrape_main.html', listing=listing, bread=bread)

#++++++++ Rescrape progress display and monitoring +++++++++++++++
#Show progress page for uid
@inventory_app.route('rescrape/progress/<string:uid>/')
@login_required
def show_rescrape_poll(uid):

    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], ['rescrape', url_for('inventory_app.show_rescrape_page')], ['progress', url_for('inventory_app.show_rescrape_poll', uid=uid)]]
    return render_template('scrape_progress.html', uid=uid, bread=bread)

#Progress data source
@inventory_app.route('rescrape/progress/<string:uid>/monitor/')
@login_required
def fetch_progress_data(uid):
    try:
        progress = inventory_live_data.get_progress(uid)
    except ih.ConnectOrAuthFail:
        progress = {'n_tables':0, 'curr_table':0, 'progress_in_current':0}
    return jsonify(progress)

#Progress data source on completion
@inventory_app.route('rescrape/progress/<string:uid>/complete/')
@login_required
def fetch_summary_data(uid):
    try:
        data = inventory_live_data.collate_orphans_by_uid(uid)
    except ih.ConnectOrAuthFail:
        data = {}
    return jsonify(data)

#++++++++ Rescrape subission +++++++++++++++
@inventory_app.route('rescrape/submit', methods=['POST'])
@login_required
@admin_required
def submit_rescrape_request():
    scrape_info = inventory_live_data.trigger_scrape(request.data)
    return jsonify({'url':url_for('inventory_app.show_rescrape_poll', uid=scrape_info['uid']), 'uid':scrape_info['uid'], 'locks':scrape_info['locks']})

# Control panel functions and endpoints ---------------------------------------
@inventory_app.route('controlpanel/')
@login_required
@admin_required
def show_panel():
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'),  url_for('inventory_app.show_edit_root')], ['control panel', url_for('inventory_app.show_panel')]]
    return render_template('control_panel.html', bread=bread)

@inventory_app.route('controlpanel/trigger', methods=['POST'])
@login_required
@admin_required
def trigger_control_functions():
    outcome = inventory_control.act(request.data)
    return jsonify(outcome)

@inventory_app.route('controlpanel/report/')
@login_required
@admin_required
def show_inventory_report():
    return render_template('inv_report.html', rept=inventory_consistency.get_latest_report())

@inventory_app.route('controlpanel/report/data')
@login_required
@admin_required
def get_inventory_report():
    outcome = inventory_consistency.get_latest_report()
    return json.dumps(outcome, cls=CustomEncoder)
