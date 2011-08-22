# -*- coding: utf-8 -*-
# This Blueprint is for handling data uploads.
# Authenticated users also have access to the raw entries, 
# selected users can edit metadata, …
#
# author: 

import logging
import pymongo
import flask
from base import app, getDBConnection, fmtdatetime
from flask import render_template, request, abort, Blueprint, url_for
from flaskext.login import login_required, current_user

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
  name = request.form['name']
  you = current_user.name
  from datetime import datetime
  current_time = datetime.utcnow()
  flask.flash("Upload Form: name = %s, user = %s, time = %s" % (name, you, fmtdatetime(current_time)))
  return flask.redirect(url_for(".index"))


