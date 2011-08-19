# -*- coding: utf-8 -*-
# This Blueprint is about adding a Knowledge Base to the LMFDB website.
# referencing content, dynamically inserting information into the website, …
#
# author: Harald Schilly <harald.schilly@univie.ac.at>

import logging
import pymongo
import flask
from base import app, getDBConnection
from flask import render_template, request, abort, Blueprint, url_for
from flaskext.login import login_required, current_user
from knowl import Knowl

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')

@knowledge_page.route("/edit/<ID>")
@login_required
def edit(ID):
  knowl = Knowl(ID)
  return render_template("knowl_edit.html", 
         title="Edit Knowl '%s'" % ID,
         K = knowl)

@knowledge_page.route("/edit", methods=["POST"])
@login_required
def edit_form():
  ID = request.form['id']
  return flask.redirect(url_for(".edit", ID=ID))

@knowledge_page.route("/save", methods=["POST"])
@login_required
def save_form():
  return "not saved"

@knowledge_page.route("/")
def index():
  return render_template("knowl_index.html", title="Knowledge Database")


@app.context_processor
def ctx_knowledge():
  return {'Knowl' : Knowl}
