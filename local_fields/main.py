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
  for b in breads:
    bc.append(b)
  return bc

@local_fields_page.route("/")
def index():
  bread = get_bread()
  return render_template("lf-index.html", title ="Local Fields", bread = bread)

@local_fields_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("lf-search.html", title="Local Fields Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we aloways do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)



  
