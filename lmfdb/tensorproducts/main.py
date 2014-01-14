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
        obj1 = args.get('obj1')
        obj2 = args.get('obj2')
        print obj1
        print obj2
        info = TensorProduct(obj1, obj2)
        if tensor_product_object == None:
            return render_template("not_yet_implemented.html")
        else:
            return render_template("tensor-products-show.html", title="Tensor products", bread=bread, info=info)

class TensorProduct:
    def __init__(self, obj1, obj2):
        self.obj1link = obj1
        self.obj2link = obj2
        self.obj1path = obj1.split('/')
        self.obj2path = obj2.split('/')
        self.obj1type = self.obj1path[0]
        self.obj2type = self.obj2path[0]

        objTypes = Set([obj1[0], obj2[0]])
        if objTypes==Set(['EllipticCurve', 'Character']):
            ellCurveLabel = obj1[1]
            charLabel = obj2[1]
            return tp_ell_curve_dirichlet_char(ellCurveLabel, charLabel)
        else:
            return None
        
def tp_ell_curve_dirichlet_char(ellCurveLabel, charLabel):
    # read ellCurve and char from database

    # put Christian's code in here

    return 'this is a tensor product object'
