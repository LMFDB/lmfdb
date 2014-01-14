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
        obj1 = 'EllipticCurve%2FQ%2f11.a1'
        obj2 = 'Character%2FDirichlet%2F13%2F2'
        tensor_product_object = TensorProduct(obj1, obj2)
        if tensor_product_object == None:
            return render_template("not_yet_implemented.html")
        else:
            return render_template("tensor-products-show.html", title="Tensor products", bread=bread, tensor_product_object=tensor_product_object)

class TensorProduct:
    def __init__(self, obj1, obj2):
        path_to_obj1 = obj1.split('%2F')
        path_to_obj2 = obj2.split('%2F')
        # obj[0] tells us what type of object
        objTypes = Set([obj1[0], obj2[0]])
        if objTypes==Set(['EllipticCurve', 'Character']):
            print "do something"
        else:
            return None
        
def tp_ell_curve_dirichlet_char(ellCurve, char):
    # read ellCurve and char from database
    C = lmfdb.base.getDBConnection()
    E = C.elliptic_curves.find_one({'lmfdb_label':label})
    chi = 'something'

    # put Christian's code in here

    return 'this is a tensor product object'
