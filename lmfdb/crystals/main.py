# -*- coding: utf-8 -*-
# This Blueprint is about Galois Groups
# Author: Anne Schilling 

import flask
from lmfdb import base
from flask import render_template,  request, abort, url_for, make_response
import os
import re
from lmfdb.crystals import crystal_page, logger
import sage.all
from sage.all import ZZ, latex

def get_bread(breads=[]):
    bc = [("Crystals", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@crystal_page.route("/<label>")
def by_label(label):
    return render_template("crystal.html", label = label)


@crystal_page.route("/")
def index():
    bread = get_bread()
    return render_template("crystal-index.html", title="Crystal", bread=bread)


