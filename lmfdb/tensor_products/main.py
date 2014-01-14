# -*- coding: utf-8 -*-
# This Blueprint is about Artin representations
# Author: Paul-Olivier Dehaye

import pymongo
ASC = pymongo.ASCENDING
import flask
from lmfdb.base import app, getDBConnection
from flask import render_template, render_template_string, request, abort, Blueprint, url_for, make_response
from lmfdb.tensor_products import tensor_products_page, tensor_products_logger
from lmfdb.utils import to_dict
from lmfdb.transitive_group import *
from string import split
from sets import Set

from lmfdb.math_classes import *
from lmfdb.WebNumberField import *
from tensor_products_defs import TensorProduct

def get_bread(breads=[]):
    bc = [("Tensor products", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@tensor_products_page.route("/")
def index():
    args = request.args
    bread = get_bread()
    if len(args)==0:
        return render_template("tensor-products-index.html", title="Tensor products", bread=bread)
    else:
        obj1 = args.get('obj1').split('/')
        obj2 = args.get('obj2').split('/')
        obj1type = obj1[0]
        obj2type = obj2[0]
        if (obj1type, obj2type)==('EllipticCurve', 'Character'):
            tp = TensorProduct(obj1[2], int(obj2[2]), int(obj2[3]))
            info = {'conductor':tp.conductor(),
                    'root_number':tp.root_number()}
            friends = [('Elliptic curve %s' % obj1[2], obj1)]
            t = "Tensor product of elliptic curve %s and Dirichlet character " % obj1[2]
            return render_template("tensor-products-show.html", title=t, bread=bread, info=info)
        else:
            info = None
            return render_template("not_yet_implemented.html")

