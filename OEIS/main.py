# -*- coding: utf-8 -*-
# This Blueprint is about mathematical objects
# This is a stub, to make it easy for new people to add objects onto the website
# Author: 

import pymongo
ASC = pymongo.ASCENDING
import flask
from base import app
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from OEIS import OEIS_object_page, logger, logger

def get_bread(breads = []):
  bc = [("Integer Sequence", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

@OEIS_object_page.route("/")
def index():
  bread = get_bread()
  return render_template("OEIS_object-index.html", title ="Integer Sequence", bread = bread)

@OEIS_object_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("OEIS_object-search.html", title="Integer Sequences Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we always do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)



  
