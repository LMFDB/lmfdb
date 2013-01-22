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
from sage.all import ZZ, latex, Partition

def get_bread(breads=[]):
    bc = [("Crystals", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

def make_tableaux_crystal(crystal):
    from sage.all_cmdline import CrystalOfTableaux
    cartan, rank, weight = crystal.split("-")
    weight = weight.split(".")
    return CrystalOfTableaux([str(cartan), int(rank)],shape = tuple(map(int, weight)))

def make_path_crystal(crystal):
    from sage.all_cmdline import CrystalOfLSPaths
    cartan, rank, weight = crystal.split("-")
    weight = weight.split(".")
    return CrystalOfLSPaths([str(cartan), int(rank)],map(int, weight))

@crystals_page.route("/<crystal>", methods = ["GET"])
def show(crystal):
    #weight = request.args.get('weight', None)
    #cartan_type = str(request.args.get('cartan_type', None))
    #rank = int(request.args.get('rank', None))
    #logger.info("weight = %s" % weight)
    #p = Partition(map(int,weight.split(",")))
    #crystal = CrystalOfTableaux([cartan_type,rank], shape=p)

    C = make_tableaux_crystal(crystal)
    #from sage.misc.latex import png
    #png(crystal, "/Users/anne/lmfdb/lmfdb/static/crystal.png", debug=True, pdflatex=True)
    return render_template("crystals.html", crystal = C, bread = get_bread())

@crystals_page.route("/<crystal>/littelmann")
def show_littelmann(crystal):
    C = make_path_crystal(crystal)
    max_i = str(max(C.index_set()))
    max_element = str(C.cardinality())
    return render_template("littelmann-paths.html", title = "Littelmann Paths", crystal = crystal, max_element = max_element, max_i = max_i)

@crystals_page.route("/littelmann-image")
def littelmann_image():
    from sage.all_cmdline import vector, line

    def line_of_path(path):
        if path is None:
            result = []
        else:
            L = path.parent().weight.parent()
            v = vector(L.zero())
            result = [v]
            for d in path.value:
               v = v + vector(d)
               result.append(v)
        result = list(result)
        result = line(result)
        result.set_axes_range(-10,10,-10,10)
        return result

    crystal = request.args.get("crystal")
    C = make_path_crystal(crystal)
    element = int(request.args.get("element"))
    i = int(request.args.get("i"))
    l = int(request.args.get("l"))
    x = C[element]
    if l >= 0 :
        y = x.f_string([i] * l)
    else:
        y = x.e_string([i] * -l)

    from lmfdb.utils import image_callback
    return image_callback(line_of_path(y))

@crystals_page.route("/")
def index():
    bread = get_bread()
    return render_template("crystals-index.html", title="Crystals", bread=bread)


