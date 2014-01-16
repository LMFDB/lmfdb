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

from lmfdb.math_classes import *
from lmfdb.WebNumberField import *

from galois_reps import GaloisRepresentation
from sage.schemes.elliptic_curves.constructor import EllipticCurve
from lmfdb.WebCharacter import *
from lmfdb.modular_forms.elliptic_modular_forms import WebNewForm
from lmfdb.lfunctions import *

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
        tp = galoisRepObjs[0] # TODO this should be the tensor product 
#         friends = []
#         friends.append(('L-function for Elliptic Curve %s' % obj1[2], url_for("l_functions.l_function_ec_page", label=obj1[2])))
#         friends.append(('L-function for Dirichlet Character $\chi_{%s}(%s, \cdot)$' % (obj2[2], obj2[3]), url_for("l_functions.l_function_dirichlet_page", modulus = int(obj2[2]), number=int(obj2[3])) ))
   
        return render_template("not_yet_implemented.html")  
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
 
    elif (p[0]=='ModularForm'):
        N = int(p[4])
        k = int(p[5])
        chi = p[6] # this should be zero; TODO check this is the case
        label = p[7] # this is a, b, c, etc.; chooses the galois orbit
        embedding = p[8] # this is the embedding of that galois orbit
        form = WebNewForm(N, k, chi=chi, label=label) 
        return GaloisRepresentation([form, embedding])

    elif (p[0]=='ArtinRepresentation'):
        dim = p[1]
        conductor = p[2]
        index = p[3]
        rho = ArtinRepresentation(dim, conductor, index)
        return GaloisRepresentation(rho)
    else:
        return
