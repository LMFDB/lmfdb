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
from sage.all import *

from lmfdb.math_classes import *
from lmfdb.WebNumberField import *
from lmfdb.lfunctions.Lfunctionutilities import *
from lmfdb.lfunctions import *

from galois_reps import GaloisRepresentation
from sage.schemes.elliptic_curves.constructor import EllipticCurve
from lmfdb.WebCharacter import *
from lmfdb.modular_forms.elliptic_modular_forms import WebNewForm
from lmfdb.lfunctions import *

# The method "show" shows the page for the Lfunction of a tensor product object.  This is registered on to the tensor_products_page blueprint rather than going via the l_function blueprint, hence the idiosyncrasies.  Sorry about that.  The reason is due to a difference in implementation; the tensor products are not (currently) in the database and the current L functions framewo  

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

    if len(galoisRepObjs)==1:
        gr = galoisRepObjs[0]
        gr.lfunction()

        info = {}
        info['dirichlet'] = lfuncDShtml(tp, "analytic")
        info['eulerproduct'] = lfuncEPtex(tp, "abstract")
        info['functionalequation'] = lfuncFEtex(tp, "analytic")
        info['functionalequationSelberg'] = lfuncFEtex(tp, "selberg")

        return render_template('Lfunction.html', **info)

    # currently only implemented tp of two things
    if len(galoisRepObjs)==2:
 
        try: 
            tp = GaloisRepresentation([galoisRepObjs[0], galoisRepObjs[1]])
            tp.lfunction()

            info = {}
            info['dirichlet'] = lfuncDShtml(tp, "analytic")
            info['eulerproduct'] = lfuncEPtex(tp, "abstract")
            info['functionalequation'] = lfuncFEtex(tp, "analytic")
            info['functionalequationSelberg'] = lfuncFEtex(tp, "selberg")

            properties2 = [('Root number', '$'+str(tp.root_number()).replace('*','').replace('I','i')+'$'),
                           ('Dimension', '$'+str(tp.dimension())+'$'),
                           ('Conductor', '$'+str(tp.cond())+'$')]
            info['properties2'] = properties2

            if (tp.numcoeff > len(tp.dirichlet_coefficients)+10):
                info['zeroswarning'] = 'These zeros may be inaccurate because we use only %s terms rather than the theoretically required %s terms' %(len(tp.dirichlet_coefficients), tp.numcoeff)
                info['svwarning'] = 'These special values may also be inaccurate, for the same reason.'
            else:
                info['zeroswarning'] = ''       
                info['svwarning'] = '' 
    
            info['tpzeroslink'] = zeros(tp) 
            info['sv_edge'] = specialValueString(tp, 1, '1')
            info['sv_critical'] = specialValueString(tp, 0.5, '1/2')

#            friends = []
#            friends.append(('L-function of first object', url_for('.show', obj1=objLinks[0])))
#            friends.append(('L-function of second object', url_for('.show', obj2=objLinks[1]))) 
#            info['friends'] = friends

            info['eulerproduct'] = 'L(s, V \otimes W) = \prod_{p} \det(1 - Frob_p p^{-s} | (V \otimes W)^{I_p})^{-1}'

            return render_template('Lfunction.html', **info)
        except Exception as ex:
            info = {'content': 'Sorry, there was a problem: ' + str(ex.args), 'title':'Error'}
            return render_template('LfunctionSimple.html', **info) 
    else:
        return render_template("not_yet_implemented.html")

def zeros(L):
    website_zeros = L.compute_heuristic_zeros()          # This depends on mathematical information, all below is formatting
    # More semantic this way
    # Allow 10 seconds

    positiveZeros = []
    negativeZeros = []

    for zero in website_zeros:
        if zero.abs() < 1e-10:
            zero = 0
        if zero < 0:
            negativeZeros.append(zero)
        else:
            positiveZeros.append(zero)

    # Format the html string to render
    positiveZeros = str(positiveZeros)
    negativeZeros = str(negativeZeros)
    if len(positiveZeros) > 2 and len(negativeZeros) > 2:  # Add comma and empty space between negative and positive
        negativeZeros = negativeZeros.replace("]", ", ]")

    return "<span class='redhighlight'>{0}</span><span class='bluehighlight'>{1}</span>".format(
        negativeZeros[1:len(negativeZeros) - 1], positiveZeros[1:len(positiveZeros) - 1])

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
        return GaloisRepresentation([form, ZZ(embedding)])

    elif (p[0]=='ArtinRepresentation'):
        dim = p[1]
        conductor = p[2]
        index = p[3]
        rho = ArtinRepresentation(dim, conductor, index)
        return GaloisRepresentation(rho)
    else:
        return
