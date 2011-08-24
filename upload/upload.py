# -*- coding: utf-8 -*-
# This Blueprint is for handling data uploads.
# Authenticated users also have access to the raw entries, 
# selected users can edit metadata, …
#
# author: 

import pymongo
import flask
import datetime
import json
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
  return render_template("upload-index.html", title = "Data Upload", bread = get_bread())

@upload_page.route("/upload", methods = ["POST"])
@login_required
def upload():
  fn = request.files['file'].filename
  metadata = {
    "name": request.form['name'],
    "full_description": request.form['full_description'],
    "data_format": request.form['data_format'],
    "creator": request.form['creator'],
    "reference": request.form['reference'],
    "bibtex": request.form['bibtex'],
    "uploader": current_user.name,
    "time": datetime.datetime.utcnow(),
    "original_file_name": fn,
    "status": "unmoderated",
    "version": "1"
  }
  flask.flash("Received file: '%s'" + fn)

  upload_db = getDBConnection().upload
  upload_fs = GridFS(upload_db)
  db_id = upload_fs.put(request.files['file'].read(), metadata = metadata, filename=fn)
  
  logging.info("file '%s' receieved and data with id '%s' stored" % (fn, db_id))
  
  return flask.redirect(url_for(".index"))

@upload_page.route("/admin", methods = ["POST"])
@admin_required
def admin_update():

  db = getDBConnection().upload
  id = request.form['id']

  if request.form.has_key('approve'):
    db.fs.files.update({"_id" : ObjectId(id)}, {"$set": {"metadata.status" : "approved"}})
    flask.flash('Approved')
  if request.form.has_key('disapprove'):
    db.fs.files.update({"_id" : ObjectId(id)}, {"$set": {"metadata.status" : "disapproved"}})
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

  return render_template("upload-admin.html", title = "Data Upload", bread = get_bread(), unmoderated=unmoderated, approved=approved, disapproved=disapproved)
