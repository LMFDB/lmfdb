from flask import Flask, render_template, request, url_for, make_response, jsonify, Blueprint
from flask_login import login_required, LoginManager, UserMixin, login_user
import inventory_viewer
import lmfdb_inventory as linv
import inventory_helpers as ih
import sys, os
from datetime import datetime as dt

# Initialize the Flask application
inventory_app = Blueprint('inventory_app', __name__, template_folder='./templates', static_folder='./static', static_url_path = 'static/')
url_pref = '/inventory/'

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
#Set to info, debug etc
linv.init_run_log('debug')

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
    return render_template('edit_show_list.html', db_name = None, nice_name=None, listing=inventory_viewer.get_edit_list(), bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')]])

#Edit page per DB, lists collections
@inventory_app.route('<string:id>/')
def show_edit_child(id):
    nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = None)
    return render_template('edit_show_list.html', db_name=id, nice_name=nice_name, listing=inventory_viewer.get_edit_list(id), bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')],[id, url_for('inventory_app.show_edit_child', id=id)]])

#Viewer page per collection, shows formatted fields
@inventory_app.route('<string:id>/<string:id2>/')
def show_inventory(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)]]
    return render_template('view_inventory.html', db_name=id, collection_name=id2, bread=bread, table_fields=linv.display_field_order(), info_fields=linv.info_field_order())

@inventory_app.route('<string:id>/<string:id2>/records/')
def show_records(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['records', url_for('inventory_app.show_records', id=id, id2=id2)]]
    nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = id2)
    return render_template('view_records.html', db_name=id, collection_name=id2, bread=bread, record_fields=linv.record_field_order(), nice_name=nice_name)

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
    results = inventory_viewer.get_inventory_for_display(id+'.'+id2)
    return jsonify(results)

#Edit page per collection, shows editable fields
@inventory_app.route('<string:id>/<string:id2>/records/edit/')
@login_required
def show_edit_records(id, id2):
    bread=[['&#8962;', url_for('index')],[url_pref.strip('/'), url_for('inventory_app.show_edit_root')], [id, url_for('inventory_app.show_edit_child', id=id)], [id2, url_for('inventory_app.show_inventory', id=id, id2=id2)], ['records', url_for('inventory_app.show_records', id=id, id2=id2)], ['edit', url_for('inventory_app.show_edit_records', id=id, id2=id2)]]
    nice_name = inventory_viewer.get_nicename(db_name = id, collection_name = id2)
    return render_template('edit_records.html', db_name=id, collection_name=id2, type_data=linv.get_type_strings_as_json(), record_fields=linv.record_field_order(), bread=bread, nice_name =nice_name, record_noedit=linv.record_noeditable())

#Edit data source to populate inventory pages
@inventory_app.route('<string:id>/<string:id2>/records/data/')
@inventory_app.route('<string:id>/<string:id2>/records/edit/data/')
def fetch_edit_records(id, id2):
    results = inventory_viewer.get_records_for_display(id+'.'+id2)
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
