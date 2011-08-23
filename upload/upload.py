# -*- coding: utf-8 -*-
# This Blueprint is for handling data uploads.
# Authenticated users also have access to the raw entries, 
# selected users can edit metadata, …
#
# author: 

import logging
import pymongo
import flask
import datetime
import json
from base import app, getDBConnection, fmtdatetime
from flask import render_template, request, abort, Blueprint, url_for
from flaskext.login import login_required, current_user
from gridfs import GridFS
from pymongo.objectid import ObjectId


upload_page = Blueprint("upload", __name__, template_folder='templates')

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
  metadata = {
    "name": request.form['name'],
    "full_description": request.form['full_description'],
    "data_format": request.form['data_format'],
    "creator": request.form['creator'],
    "reference": request.form['reference'],
    "bibtex": request.form['bibtex'],
    "uploader": current_user.name,
    "time": str(datetime.datetime.utcnow()),
    "original_file_name": request.files['file'].filename,
    "status": "unmoderated",
    "version": "1"
  }
  flask.flash("Received file: " + request.files['file'].filename)

  upload_db = getDBConnection().upload
  upload_fs = GridFS(upload_db)
  upload_fs.put(request.files['file'].read(), metadata = metadata, filename=request.files['file'].filename)
  
  return flask.redirect(url_for(".index"))

@upload_page.route("/admin", methods = ["POST"])
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
def admin():

  db = getDBConnection().upload
  fs = GridFS(db)

  unmoderated = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "unmoderated"}) ]
  approved = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "approved"}) ]
  disapproved = [ fs.get(x['_id']) for x in db.fs.files.find({"metadata.status" : "disapproved"}) ]

  return render_template("upload-admin.html", title = "Data Upload", bread = get_bread(), unmoderated=unmoderated, approved=approved, disapproved=disapproved)
