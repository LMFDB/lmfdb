# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: Paul-Olivier Dehaye

import pymongo
ASC = pymongo.ASCENDING
import flask
from base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from artin_representations import artin_representations_page, artin_logger

from math_classes import *

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
    return "ERROR: we always do http get to explicitly display the search parameters"
  else:
    return flask.redirect(404)


@artin_representations_page.route("/<dim>/<conductor>/<index>")
def by_data(dim,conductor,index):
    artin_logger.debug("Asked for the Artin representation with parameters dim: %s conductor: %s index: %s"%(dim, conductor, index))
    return render_artin_representation_webpage(dim,conductor,index)

@artin_representations_page.route("/<dim>/<conductor>")
def by_partial_data(dim,conductor):
    artin_logger.debug("Asked for the set of Artin representations with parameters dim: %s conductor: %s "%(dim, conductor))
    return render_artin_representation_set_webpage(dim,conductor)


# credit information should be moved to the databases themselves, not at the display level. that's too late. 
tim_credit = "Tim Dokchitser"
support_credit = "Support by Paul-Olivier Dehaye"

def render_artin_representation_webpage(dim,conductor,index):
  try:
    the_rep = ArtinRepresentation.find_one({'Dim' : int(dim),"Conductor":str(conductor),"DBIndex":int(index)})
  except:
    pass
  artin_logger.info("Found %s"%(the_rep._data))
  
  bread = get_bread([(str("Dimension %s, conductor %s, index %s"%(the_rep.dimension(),the_rep.conductor(),the_rep.index())), ' ')])

  title = the_rep.title()
  the_nf = the_rep.number_field_galois_group()
  from number_field_galois_groups import nfgg_page
  from number_field_galois_groups.main import by_data
  
  friends = [("Artin Field", url_for("number_field_galois_groups.by_data", degree = the_nf.degree(), size = the_nf.size(), index = the_nf.index())), \
            ("Same degree and conductor", url_for(".by_partial_data", dim = the_rep.dimension(), conductor = the_rep.conductor()))]
  return render_template("artin-representation-show.html", credit= tim_credit, support = support_credit, title = title, bread = bread, friends = friends, object = the_rep)

def render_artin_representation_set_webpage(dim,conductor):
  try:
    the_reps = ArtinRepresentation.find({'Dim' : int(dim),"Conductor":str(conductor)})
  except:
    pass
  
  bread = get_bread([(str("Dimension %s, conductor %s"%(dim, conductor)), ' ')])

  title = "Artin representations of dimension $%s$ and conductor $%s$"%(dim,conductor)
  
  return render_template("artin-representation-set-show.html", credit= tim_credit, support = support_credit, title = title, bread = bread, object = the_reps)



  
