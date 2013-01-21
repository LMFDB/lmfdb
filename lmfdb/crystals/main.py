# -*- coding: utf-8 -*-
# This Blueprint is about Crystals
# Author: Anne Schilling 

import flask
from lmfdb import base
from flask import render_template, request, abort, url_for, make_response, redirect
import os
import re
from lmfdb.crystals import crystals_page, logger
import sage.all
from sage.all import ZZ, latex

def get_bread(breads=[]):
    bc = [("Crystals", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@crystals_page.route("/show", methods = ["GET"])
def show():
    label = request.args.get('label', None)
    i = int(label)
    j = 4 *i
    return render_template("crystals.html", label = j, bread = get_bread())


@crystals_page.route("/")
def index():
    bread = get_bread()
    return render_template("crystals-index.html", title="Crystals", bread=bread)


