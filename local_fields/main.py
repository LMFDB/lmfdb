# -*- coding: utf-8 -*-
# This Blueprint is about Local Fields
# Author: John Jones

import pymongo
ASC = pymongo.ASCENDING
import flask
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from local_fields import local_fields_page, logger, logger

def get_bread(breads = []):
  bc = [("Local Field", url_for(".index"))]

@local_fields_page.route("/")
def index():
  bread = get_bread()
  return render_template("lf-index.html", title ="Local Fields", bread = bread)

@local_fields_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    bread = get_bread(("Search", url_for('.search')))
    return render_template("lf-search.html", val="no value", title="Local Fields Search", bread = bread)
  elif request.method == "POST":
    val = request.form['val']
    return render_template("lf-search.html", val = val)
  else:
    return flask.redirect(404)



  
