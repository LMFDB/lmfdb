# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: 

import pymongo
ASC = pymongo.ASCENDING
import flask
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from artin_representations import artin_representations_page, logger, logger

def get_bread(breads = []):
  bc = [("Artin Representation", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

@artin_representations_page.route("/")
def index():
  bread = get_bread()
  return render_template("artin-representation-index.html", title ="Artin Representations", bread = bread)

@artin_representations_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("artin-representations-search.html", title="Artin Representations Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we aloways do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)



  
