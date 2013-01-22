# -*- coding: utf-8 -*-
# This Blueprint is about Permutations
# Author: Sebastien Labbe

import flask
from lmfdb import base
from flask import render_template, request, abort, url_for, make_response, redirect
import os
import re
from lmfdb.permutations import permutations_page, logger
import sage.all
from sage.all import Permutation, DiGraph

def get_bread(breads=[]):
    bc = [("Permutations", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@permutations_page.route("/show", methods = ["GET"])
def show():
    try:
        data = eval(request.args.get('data', None))
    except SyntaxError:
        logger.info("Impossible to parse the input.")
        raise
    try:
        p = Permutation(data)
    except ValueError:
        logger.info("Impossible to create a permutation from input.")
        raise
    digraph_plot = DiGraph(p.to_matrix()).plot()
    return render_template("permutations.html", permutation=p,
            digraph_plot=digraph_plot, rankbread=get_bread())

@permutations_page.route("/")
def index():
    bread = get_bread()
    return render_template("permutations-index.html", title="Permutations", bread=bread)


