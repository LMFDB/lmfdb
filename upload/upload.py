# -*- coding: utf-8 -*-
# This Blueprint is for handling data uploads.
# Authenticated users also have access to the raw entries, 
# selected users can edit metadata, …
#
# author: 

import pymongo
import flask
import copy
import datetime
import json
import re
import tarfile
from base import app, getDBConnection, fmtdatetime
from flask import render_template, request, abort, Blueprint, url_for
from flaskext.login import login_required, current_user
from gridfs import GridFS
from pymongo.objectid import ObjectId

from users import admin_required


upload_page = Blueprint("upload", __name__, template_folder='templates')
import utils
logging = utils.make_logger(upload_page)

# blueprint specific definition of the body_class variable
@upload_page.context_processor
def body_class():
  return { 'body_class' : 'upload' }

def get_bread():
  return [("Upload", url_for(".index")) ]

@upload_page.route("/")
@login_required
def index():
  related_to = "";
  if request.values.has_key('related_to'):
    related_to = request.values['related_to']
  return render_template("upload-index.html", title = "Data Upload", bread = get_bread(), related_to = related_to)

@upload_page.route("/upload", methods = ["POST"])
@login_required
def upload():
  fn = request.files['file'].filename
  metadata = {
    "name": request.form['name'],
    "full_description": request.form['full_description'],
    "related_to": request.form['related_to'],
    "data_format": request.form['data_format'],
    "creator": request.form['creator'],
    "reference": request.form['reference'],
    "bibtex": request.form['bibtex'],
    "uploader": current_user.name,
    "uploader_id": current_user.id,
    "time": datetime.datetime.utcnow(),
    "original_file_name": fn,
    "status": "unmoderated",
    "version": "1",
    "content_type": request.files['file'].content_type
  }
  flask.flash("Received file '%s' and awaiting moderation from an administrator" % fn)

  upload_db = getDBConnection().upload
  upload_fs = GridFS(upload_db)
  db_id = upload_fs.put(request.files['file'].read(), metadata = metadata, filename=fn)
  
  logging.info("file '%s' receieved and data with id '%s' stored" % (fn, db_id))

  if fn[-4:] == ".tgz" or fn[-4:] == ".tar" or fn[-7:] == ".tar.gz" :
    child_index = []
    tar = tarfile.open(fileobj=upload_fs.get(ObjectId(db_id)))
    for tarinfo in tar:
      if tarinfo.isfile():
        metadata2 = copy.copy(metadata)
        metadata2['parent_archive_id'] = db_id
        metadata2['parent_archive_filename'] = fn
        metadata2['status'] = "unmoderatedchild"
        metadata2['original_file_name'] = fn+"/"+tarinfo.name
        metadata2['related_to'] = ""
        id = upload_fs.put( tar.extractfile(tarinfo).read(), metadata = metadata2, filename=fn+"/"+tarinfo.name )
        child_index.append([id, tarinfo.name]);
    upload_db.fs.files.update({"_id": db_id}, {"$set": {"metadata.child_index": child_index}})
  
  return flask.redirect("/upload/view/"+str(db_id))

@upload_page.route("/admin", methods = ["POST"])
@admin_required
def admin_update():

  db = getDBConnection().upload
  fs = GridFS(db)
  id = request.form['id']

  if request.form.has_key('approve'):
    db.fs.files.update({"_id" : ObjectId(id)}, {"$set": {"metadata.status" : "approved"}})
    db.fs.files.update({"metadata.parent_archive_id" : ObjectId(id)}, {"$set": {"metadata.status" : "approvedchild"}}, multi=1)
    flask.flash('Approved')
  if request.form.has_key('disapprove'):
    db.fs.files.update({"_id" : ObjectId(id)}, {"$set": {"metadata.status" : "disapproved"}})
    db.fs.files.update({"metadata.parent_archive_id" : ObjectId(id)}, {"$set": {"metadata.status" : "disapprovedchild"}}, multi=1)
    flask.flash('Disapproved')

  return flask.redirect(url_for(".admin"))


@upload_page.route("/admin", methods = ["GET"])
@admin_required
def admin():

  db = getDBConnection().upload
  fs = GridFS(db)

  unmoderated = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "unmoderated"}) ]
  approved = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "approved"}) ]
  disapproved = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "disapproved"}) ]

  return render_template("upload-view.html", title = "Moderate uploaded data", bread = get_bread(), unmoderated=unmoderated)#, approved=approved, disapproved=disapproved)

@upload_page.route("/viewAll", methods = ["GET"])
def viewAll():

  db = getDBConnection().upload
  fs = GridFS(db)

  approved = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "approved"}) ]

  return render_template("upload-view.html", title = "Uploaded data", bread = get_bread(), approved=approved)





@upload_page.route("/download/<id>/<path:filename>", methods = ["GET"])
def download(id, filename):
  file = GridFS(getDBConnection().upload).get(ObjectId(id))
  response = flask.Response(file.__iter__())
  response.headers['content-type'] = file.metadata['content_type']
  response.content_length=file.length
  
  return response

@upload_page.route("/view/<id>", methods = ["GET"])
def view(id):
  file = GridFS(getDBConnection().upload).get(ObjectId(id))
  return render_template("upload-view.html", title = "View file", bread = get_bread(), file = file)

@upload_page.route("/updateMappingRule", methods = ["POST"])
@login_required
def updateMappingRule():
  id = request.form['id']
  print id
  rules = filter(lambda x: x.strip()!="", request.form['rule'].splitlines())
  db = getDBConnection().upload
  child_index = db.fs.files.find_one({"_id": ObjectId(id)})['metadata']['child_index']
  for child in child_index:
    url = ""
    for i in range(len(rules)/2):
      if re.search(rules[i+i], child[1]) is not None:
        url = re.sub(rules[i+i], rules[i+i+1], child[1])
        break
    db.fs.files.update({"_id": child[0]}, {"$set": {"metadata.related_to": url}})
    print child[0], child[1], url
        
  return "resp"


@upload_page.route("/updateMetadata", methods = ["GET"])
@login_required
def updateMetadata():
  db = getDBConnection().upload
  id = request.values['id']
  property = request.values['property']
  value = request.values['value']
  db.fs.files.update({"_id" : ObjectId(id)}, {"$set": {"metadata."+property : value}})
  if property == "status":
    db.fs.files.update({"metadata.parent_archive_id" : ObjectId(id)}, {"$set": {"metadata.status" : value+"child"}}, multi=1)
  return getDBConnection().upload.fs.files.find_one({"_id" : ObjectId(id)})['metadata'][property]

def getUploadedFor(path):
  files = getDBConnection().upload.fs.files.find({"metadata.related_to": path, "$or" : [{"metadata.status": "approved"}, {"metadata.status": "approvedchild"}]})
  ret =  [ [x['metadata']['name'], "/upload/view/%s" % x['_id']] for x in files ]
  ret.insert(0, ["Upload your data here", url_for("upload.index") + "?related_to=" + request.path ])
  return ret

def queryUploadDatabase(filename, path):
  file = getDBConnection().upload.fs.files.find_one({"metadata.related_to": path, "filename": filename})
  upload_fs = GridFS(getDBConnection().upload)
  return upload_fs.get(file['_id']).read()

def getFilenamesFromTar(file):
  tar = tarfile.open(mode="r", fileobj=file)
  return [ [name, ""] for name in tar.getnames() ]

@app.context_processor
def ctx_knowledge():
  return {'getUploadedFor' : getUploadedFor,
          'queryUploadDatabase' : queryUploadDatabase,
          'getFilenamesFromTar' : getFilenamesFromTar }
