# -*- coding: utf-8 -*-
# This Blueprint is about Local Fields
# Author: John Jones

import pymongo
ASC = pymongo.ASCENDING
import flask
import base
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from utils import ajax_more, image_src, web_latex, to_dict, parse_range, coeff_to_poly, pol_to_html
from local_fields import local_fields_page, logger, logger

LF_credit = 'J. Jones and D. Roberts'

def get_bread(breads = []):
  bc = [("Local Field", url_for(".index"))]
  for b in breads:
    bc.append(b)
  return bc

@local_fields_page.route("/")
def index():
  bread = get_bread()
  if len(request.args) != 0:
    return local_field_search(**request.args)
  #info['learnmore'] = [('Number Field labels', url_for("render_labels_page")), ('Galois group labels',url_for("render_groups_page")), ('Discriminant ranges',url_for("render_discriminants_page"))]
  return render_template("lf-index.html", title ="Local Fields", bread = bread)

@local_fields_page.route("/<label>")
def by_label(label):
    return render_field_webpage({'label' : label})

@local_fields_page.route("/search", methods = ["GET", "POST"])
def search():
  if request.method == "GET":
    val = request.args.get("val", "no value")
    bread = get_bread([("Search for '%s'" % val, url_for('.search'))])
    return render_template("lf-search.html", title="Local Field Search", bread = bread, val = val)
  elif request.method == "POST":
    return "ERROR: we always do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)


def local_field_search(**args):
  info = to_dict(args)
  bread = get_bread()
  C = base.getDBConnection()
  query = {}
  for param in ['p', 'n']:
    if info.get(param):
      ran = info[param]
      ran = ran.replace('..','-')
      query[param] = parse_range(ran)


  res = C.localfields.fields.find(query).sort([('p',pymongo.ASCENDING),('n',pymongo.DESCENDING),('c',pymongo.ASCENDING)])
  nres = res.count()
  info['fields'] = res
  info['report'] = "found %s fields"%nres

  return render_template("lf-search.html", info = info, title="Local Field Search Result", bread=bread)
  
def render_field_webpage(args):
  data = None
  bread = get_bread()
  if 'label' in args:
    label = str(args['label'])
    C = base.getDBConnection()
    data = C.localfields.fields.find_one({'label': label})
    if data is None:
        return "Field: " + label + " not found in the database"
    info = {}
    title = 'Local field:' + label
    polynomial = coeff_to_poly(data['coeffs'])
    info.update({
      'polynomial': web_latex(polynomial)
      })


    return render_template("lf-show-field.html", credit=LF_credit, title = title, bread = bread, info = info )


