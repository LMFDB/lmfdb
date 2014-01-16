# -*- coding: utf-8 -*-
# Blueprint for tensor product pages
# Author: Martin Dickson

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
from sage.schemes.elliptic_curves.constructor import EllipticCurve

from lmfdb.math_classes import *
from lmfdb.WebNumberField import *
from tensor_products_defs import TensorProduct
from galois_reps import GaloisRepresentation
from lmfdb.WebCharacter import *

def get_bread(breads=[]):
    bc = [("Tensor products", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@tensor_products_page.route("/")
def index():
    bread = get_bread()
    return render_template("tensor_products_index.html", title="Tensor products", bread=bread)

@tensor_products_page.route("/navigate/")
def navigate():
    args = request.args
    bread = get_bread()

    type1 = args.get('type1')
    type2 = args.get('type2')
    return render_template("tensor_products_navigate.html", title="Tensor products navigation", bread=bread, type1=type1 , type2=type2)

@tensor_products_page.route("/show/")
def show():
    args = request.args
    bread = get_bread()

    objLinks = args # an immutable dict of links to objects to tp

    objPaths = []
    for k, v in objLinks.items():
        objPaths.append(v.split('/')) 

    galoisRepObjs = []
    for p in objPaths:
        galoisRepObjs.append(galois_rep_from_path(p))

    # currently only implemented tp of two things
    if len(galoisRepObjs)==2:
#         tp = mult(galoisRepObjs[0], galoisRepObjs[1]) # form the multiplication in the galois reps class, which implements tensor product

#         info = {'conductor':tp.conductor()}

#         properties2 = {'Conductor':info['conductor']}
            
#         friends = []
#         friends.append(('L function', ''))
#         friends.append(('Elliptic Curve %s' % obj1[2], url_for("ec.by_ec_label", label=obj1[2])))
#         friends.append(('Dirichlet Character $\chi_{%s}(%s, \cdot)$' % (obj2[2], obj2[3]), url_for("characters.render_Dirichletwebpage", modulus=int(obj2[2]), number=int(obj2[3])) ))
#         friends.append(('L-function for Elliptic Curve %s' % obj1[2], url_for("l_functions.l_function_ec_page", label=obj1[2])))
#         friends.append(('L-function for Dirichlet Character $\chi_{%s}(%s, \cdot)$' % (obj2[2], obj2[3]), url_for("l_functions.l_function_dirichlet_page", modulus = int(obj2[2]), number=int(obj2[3])) ))
            
#         t = "Tensor product of Elliptic Curve %s and Dirichlet Character $\chi_{%s}(%s, \cdot)$" % (obj1[2], obj2[2], obj2[3])

        return render_template("tensor_products_show.html", title='', bread=bread, info=[], friends=[])

    else:
        return render_template("not_yet_implemented.html")

def galois_rep_from_path(p):
    C = getDBConnection()
    if p[0]=='EllipticCurve':
        # create the sage elliptic curve then create Galois rep object
        data = C.elliptic_curves.curves.find_one({'lmfdb_label':p[2]})
        ainvs = [int(a) for a in data['ainvs']]
        E = EllipticCurve(ainvs)
        return GaloisRepresentation(E)
    elif (p[0]=='Character' and p[1]=='Dirichlet'):
        dirichletArgs = {'type':'Dirichlet', 'modulus':int(p[2]), 'number':int(p[3])}
        chi = WebDirichletCharacter(**dirichletArgs)
        return GaloisRepresentation(chi) 
    else:
        return
