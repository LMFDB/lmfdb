# -*- coding: utf-8 -*-
# Blueprint for tensor product pages
# Author: Martin Dickson

from lmfdb.db_backend import db
from flask import render_template, request, url_for
from lmfdb.tensor_products import tensor_products_page 

from galois_reps import GaloisRepresentation
from sage.all import ZZ, EllipticCurve
from lmfdb.artin_representations.main import ArtinRepresentation
from lmfdb.WebCharacter import WebDirichletCharacter
from lmfdb.classical_modular_forms.web_newform import convert_newformlabel_from_conrey, WebNewform
from lmfdb.lfunctions.Lfunctionutilities import lfuncDShtml, lfuncEPtex, lfuncFEtex, specialValueString
from lmfdb.lfunctions.main import render_lfunction_exception

# The method "show" shows the page for the Lfunction of a tensor product object.  This is registered on to the tensor_products_page blueprint rather than going via the l_function blueprint, hence the idiosyncrasies.  Sorry about that.  The reason is due to a difference in implementation; the tensor products are not (currently) in the database and the current L functions framewo  

def get_bread(breads=[]):
    bc = [("L-functions", url_for("l_functions.l_function_top_page")),
          ("Tensor Products", url_for(".index"))]
    for b in breads:
        bc.append(b)
    return bc

@tensor_products_page.route("/")
def index():
    bread = get_bread()
    return render_template("tensor_products_index.html", title="Tensor Products", bread=bread)

@tensor_products_page.route("/navigate/")
def navigate():
    args = request.args
    bread = get_bread()

    type1 = args.get('type1')
    type2 = args.get('type2')
    return render_template("tensor_products_navigate.html", title="Tensor Products Navigation", bread=bread, type1=type1 , type2=type2)

@tensor_products_page.route("/show/")
def show():
    args = request.args

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
        info['dirichlet'] = lfuncDShtml(gr, "analytic")
        info['eulerproduct'] = lfuncEPtex(gr, "abstract")
        info['functionalequation'] = lfuncFEtex(gr, "analytic")
        info['functionalequationSelberg'] = lfuncFEtex(gr, "selberg")
        info['bread'] = get_bread()

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
            info['bread'] = get_bread()
            return render_template('Lfunction.html', **info)
        except (KeyError,ValueError,RuntimeError,NotImplementedError) as err:
            return render_lfunction_exception(err)
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
    if p[0]=='EllipticCurve':
        # create the sage elliptic curve then create Galois rep object
        ainvs = db.ec_curves.lucky({'lmfdb_label':p[2]+"."+p[3]+p[4]}, 'ainvs')
        E = EllipticCurve(ainvs)
        return GaloisRepresentation(E)

    elif (p[0]=='Character' and p[1]=='Dirichlet'):
        dirichletArgs = {'type':'Dirichlet', 'modulus':int(p[2]), 'number':int(p[3])}
        chi = WebDirichletCharacter(**dirichletArgs)
        return GaloisRepresentation(chi)
 
    elif (p[0]=='ModularForm'):
        level = int(p[4])
        weight = int(p[5])
        conrey_label = p[6] # this should be zero; TODO check this is the case
        hecke_orbit = p[7] # this is a, b, c, etc.; chooses the galois orbit
        embedding = p[8] # this is the embedding of that galois orbit
        label = convert_newformlabel_from_conrey(str(level)+"."+str(weight)+"."+str(conrey_label)+"."+hecke_orbit)
        form = WebNewform(label)
        return GaloisRepresentation([form, ZZ(embedding)])

    elif (p[0]=='ArtinRepresentation'):
        dim = p[1]
        conductor = p[2]
        index = p[3]
        rho = ArtinRepresentation(dim, conductor, index)
        return GaloisRepresentation(rho)
    else:
        return
