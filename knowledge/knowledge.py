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

knowledge_page = Blueprint("knowledge", __name__, template_folder='templates')

@knowledge_page.route("/edit/<ID>")
@login_required
def edit(ID):
  return "ID %s" % ID

