# -*- coding: utf-8 -*-
from lmfdb.base import *
from flask import (Flask, session, g, render_template, url_for, request,
                   make_response, abort)
import flask

from sage.all import *
import tempfile
import os
import sqlite3
import numpy
import pymongo
from Lfunction import *
import LfunctionPlot as LfunctionPlot
from lmfdb.utils import to_dict
import bson
from Lfunctionutilities import (p2sage, lfuncDShtml, lfuncEPtex, lfuncFEtex,
                                truncatenumber, styleTheSign, specialValueString, specialValueTriple)
from lmfdb.WebCharacter import WebDirichlet
from lmfdb.lfunctions import l_function_page, logger
from lmfdb.elliptic_curves.web_ec import cremona_label_regex, lmfdb_label_regex
from LfunctionComp import isogenyclasstable
import LfunctionDatabase
from lmfdb import base
from pymongo import ASCENDING

################################################################################
#   Route functions, navigation pages
################################################################################

# Top page #####################################################################
@l_function_page.route("/")
def l_function_top_page():
    info = set_info_for_start_page()
    return render_template("LfunctionNavigate.html", **info)

@l_function_page.route("/history")
def l_function_history():
    from lmfdb.pages import _single_knowl
    t = "A brief history of L-functions"

    bc = [('L-functions', url_for('.l_function_top_page')),
          (t, url_for('.l_function_history'))]
    return render_template(_single_knowl, title=t, kid='lfunction.history', body_class='', bread=bc)




# Degree 1 L-functions browsing page ##############################################
@l_function_page.route("/degree1/")
def l_function_dirichlet_browse_page():
    info = {"bread": get_bread(1, [])}
    info["minModDefault"] = 1
    info["maxModDefault"] = 20
    info["maxOrder"] = 19
    info["contents"] = [LfunctionPlot.getOneGraphHtmlChar(info["minModDefault"], info[
                "maxModDefault"], 1, info["maxOrder"])]
    return render_template("Degree1.html", title='Degree 1 L-functions', **info)

# Degree 2 L-functions browsing page ##############################################
@l_function_page.route("/degree2/")
def l_function_degree2_browse_page():
    info = {"bread": get_bread(2, [])}
    return render_template("Degree2.html", title='Degree 2 L-functions', **info)

# Degree 3 L-functions browsing page ##############################################
@l_function_page.route("/degree3/")
def l_function_degree3_browse_page():
    info = {"bread": get_bread(3, [])}
    return render_template("Degree3.html", title='Degree 3 L-functions', **info)

# Degree 4 L-functions browsing page ##############################################
@l_function_page.route("/degree4/")
def l_function_degree4_browse_page():
    info = {"bread": get_bread(4, [])}
    return render_template("Degree4.html", title='Degree 4 L-functions', **info)


# Degree browsing page #########################################################
@l_function_page.route("/<degree>/")
def l_function_degree_page(degree):
    degree = int(degree[6:])
    info = {"degree": degree}
    info["key"] = 777
    info["bread"] = get_bread(degree, [])
    return render_template("DegreeNavigateL.html", title='Degree ' + str(degree) + ' L-functions', **info)


# L-function of holomorphic cusp form with trivial character browsing page ##############################################
@l_function_page.route("/degree2/CuspForm/")
def l_function_cuspform_browse_page():
    info = {"bread": get_bread(2, [("CuspForm", url_for('.l_function_cuspform_browse_page'))])}
    info["contents"] = [LfunctionPlot.getOneGraphHtmlHolo(1, 13, 2, 12)]
    return render_template("cuspformGL2.html", title='L-functions of Cusp Forms on \(\Gamma_0(N)\) with trivial character', **info)


# L-function of GL(2) maass forms browsing page ##############################################
@l_function_page.route("/degree2/MaassForm/")
def l_function_maass_browse_page():
    info = {"bread": get_bread(2, [("MaassForm", url_for('.l_function_maass_browse_page'))])}
    info["contents"] = [processMaassNavigation()]
    return render_template("MaassformGL2.html", title='L-functions of GL(2) Maass Forms of weight 0', **info)


# L-function of elliptic curves browsing page ##############################################
@l_function_page.route("/degree2/EllipticCurve/")
def l_function_ec_browse_page():
    info = {"bread": get_bread(2, [("Elliptic curve", url_for('.l_function_ec_browse_page'))])}
    info["representation"] = ''
    info["contents"] = [processEllipticCurveNavigation(11, 65)]
    return render_template("ellipticcurve.html", title='L-functions of Elliptic Curves', **info)


# L-function of GL(n) Maass forms browsing page ##############################################
@l_function_page.route("/<degree>/MaassForm/")
def l_function_maass_gln_browse_page(degree):
    degree = int(degree[6:])
    info = {"bread": get_bread(degree, [("MaassForm", url_for('.l_function_maass_gln_browse_page',
                                                              degree='degree' + str(degree)))])}
    info["contents"] = LfunctionPlot.getAllMaassGraphHtml(degree)
    return render_template("MaassformGLn.html",
                           title='L-functions of GL(%s) Maass Forms' % degree, **info)


# L-function of symmetric square of elliptic curves browsing page ##############
@l_function_page.route("/degree3/EllipticCurve/SymmetricSquare/")
def l_function_ec_sym2_browse_page():
    info = {"bread": get_bread(3, [("Symmetric square of Elliptic curve",
                                    url_for('.l_function_ec_sym2_browse_page'))])}
    info["representation"] = 'Symmetric square'
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 26, 2)]
    return render_template("ellipticcurve.html",
                           title='Symmetric square L-functions of Elliptic Curves', **info)


# L-function of symmetric cube of elliptic curves browsing page ################
@l_function_page.route("/degree4/EllipticCurve/SymmetricCube/")
def l_function_ec_sym3_browse_page():
    info = {"bread": get_bread(4, [("Symmetric cube of Elliptic curve", url_for('.l_function_ec_sym3_browse_page'))])}
    info["representation"] = 'Symmetric cube'
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 17, 3)]
    return render_template("ellipticcurve.html",
                           title='Symmetric cube L-functions of Elliptic Curves', **info)

# L-function of genus 2 curves browsing page ##############################################
@l_function_page.route("/degree4/Genus2Curve/")
def l_function_genus2_browse_page():
    info = {"bread": get_bread(2, [("Genus 2 curve", url_for('.l_function_genus2_browse_page'))])}
    info["representation"] = ''
    info["contents"] = [processGenus2CurveNavigation(169, 700)]
    return render_template("genus2curve.html", title='L-functions of Genus 2 Curves', **info)


###########################################################################
#   Helper functions, navigation pages
###########################################################################
def set_info_for_start_page():
    ''' Sets the properties of the top L-function page.
    '''

    tt = [[{'title': 'Riemann zeta function', 'link': url_for('.l_function_riemann_page')},
           {'title': 'Dirichlet L-function', 'link': url_for('.l_function_dirichlet_browse_page')}],

          [{'title': 'Holomorphic cusp form with trivial character', 'link': url_for('.l_function_cuspform_browse_page')},
           {'title': 'GL2 Maass form', 'link': url_for('.l_function_maass_browse_page')},
           {'title': 'Elliptic curve', 'link': url_for('.l_function_ec_browse_page')}],

          [{'title': '', 'link': ''},
           {'title': 'GL3 Maass form', 'link': url_for('.l_function_maass_gln_browse_page',
                                                       degree='degree3')},
           {'title': 'Symmetric square L-function of Elliptic curve', 'link': url_for('.l_function_ec_sym2_browse_page')}],

          [{'title': 'GSp4 Maass form', 'link': url_for('.l_function_maass_gln_browse_page', degree='degree4') + '#GSp4_Q_Maass'},
           {'title': 'GL4 Maass form', 'link': url_for('.l_function_maass_gln_browse_page',
                                                       degree='degree4')},
           {'title': 'Symmetric cube L-function of Elliptic curve', 'link': url_for('.l_function_ec_sym3_browse_page')}]]

    info = {
        'degree_list': range(1, 5),
        'type_table': tt,
        'type_row_list': [0, 1, 2, 3]
        }

    info['title'] = 'L-functions'
    info['bread'] = [('L-functions', url_for('.l_function_top_page'))]

    info['learnmore'] = [('History of L-functions', url_for('.l_function_history'))]

    return info


def get_bread(degree, breads=[]):
    ''' Returns the two top levels of bread crumbs plus the ones supplied in breads.
    '''
    bc = [('L-functions', url_for('.l_function_top_page')),
          ('Degree ' + str(degree), url_for('.l_function_degree_page', degree='degree' + str(degree)))]
    for b in breads:
        bc.append(b)
    return bc


################################################################################
#   Route functions, individual L-function homepages
################################################################################
# Riemann zeta function ########################################################
@l_function_page.route("/Riemann/")
def l_function_riemann_page():
    args = {}
    return render_single_Lfunction(RiemannZeta, args, request)


@l_function_page.route("/Character/Dirichlet/1/1/")
@l_function_page.route("/NumberField/1.1.1.1/")
def l_function_riemann_redirect():
    return flask.redirect(url_for('.l_function_riemann_page'), code=301)


# L-function of Dirichlet character ############################################
@l_function_page.route("/Character/Dirichlet/<modulus>/<number>/")
def l_function_dirichlet_page(modulus, number):
    args = {'charactermodulus': modulus, 'characternumber': number}
    return render_single_Lfunction(Lfunction_Dirichlet, args, request)


# L-function of tensor product #################################################
@l_function_page.route("/TensorProduct/")
def l_function_tensor_product_page(galoisrep):
    args = {}
    return render_single_Lfunction(GaloisRepresentationLfunction, args, request)

# L-function of Elliptic curve #################################################
@l_function_page.route("/EllipticCurve/Q/<label>/")
def l_function_ec_page(label):
    logger.debug(label)

    m = lmfdb_label_regex.match(label)
    if m is not None:
        # Lmfdb label is given
        if m.groups()[2]:
            # strip off the curve number
            return flask.redirect(url_for('.l_function_ec_page', label=label[:-1]), 301)
        else:
            args = {'label': label}
            return render_single_Lfunction(Lfunction_EC_Q, args, request)

    m = cremona_label_regex.match(label)
    if m is not None:
        # Do a redirect if cremona label is given
        if m.groups()[2]:
            C = getDBConnection().elliptic_curves.curves.find_one({'label': label})
        else:
            C = getDBConnection().elliptic_curves.curves.find_one({'iso': label})
        return flask.redirect(url_for('.l_function_ec_page', label=(C['lmfdb_iso'])), 301)


# L-function of Cusp form ############################################
@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/<character>/<label>/<number>/")
def l_function_emf_page(level, weight, character, label, number):
    args = {'level': level, 'weight': weight, 'character': character,
            'label': label, 'number': number}
    return render_single_Lfunction(Lfunction_EMF, args, request)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/<character>/<label>/")
def l_function_emf_redirect_1(level, weight, character, label):
    logger.debug(level, weight, character, label)
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character=character, label=label, number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/<character>/")
def l_function_emf_redirect_2(level, weight, character):
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character=character, label='a', number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/")
def l_function_emf_redirect_3(level, weight):
    logger.debug(level, weight)
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character='0', label='a', number='0'), code=301)


# L-function of Hilbert modular form ###########################################
@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/<character>/<number>/")
def l_function_hmf_page(field, label, character, number):
    args = {'field': field, 'label': label, 'character': character,
            'number': number}
    return render_single_Lfunction(Lfunction_HMF, args, request)


@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/<character>/")
def l_function_hmf_redirect_1(field, label, character):
    logger.debug(field, label, character)
    return flask.redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character=character, number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/TotallyReal/<field>/holomorphic/<label>/")
def l_function_hmf_redirect_2(field, label):
    logger.debug(field, label)
    return flask.redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character='0', number='0'), code=301)


# L-function of GL(2) Maass form ###############################################
@l_function_page.route("/ModularForm/GL2/Q/Maass/<dbid>/")
def l_function_maass_page(dbid):
    try:
        args = {'dbid': bson.objectid.ObjectId(dbid), 'fromDB': False}
    except Exception as ex:
        args = {'dbid': dbid, 'fromDB': False}
    return render_single_Lfunction(Lfunction_Maass, args, request)


# L-function of GL(n) Maass form (n>2) #########################################
@l_function_page.route("/ModularForm/<group>/Q/Maass/<level>/<char>/<R>/<ap_id>/")
def l_function_maass_gln_page(group, level, char, R, ap_id):
    args = {'fromDB': True, 'group': group, 'level': level,
            'char': char, 'R': R, 'ap_id': ap_id}
    return render_single_Lfunction(Lfunction_Maass, args, request)

@l_function_page.route("/ModularForm/<group>/Q/Maass/<dbid>/")
def l_function_maass_gln_page_noDb(group, dbid):
    args = {'dbid': dbid, 'dbName': 'Lfunction',
            'dbColl': 'LemurellMaassHighDegree', 'fromDB': False}
    return render_single_Lfunction(Lfunction_Maass, args, request)


# L-function of Siegel modular form    #########################################
@l_function_page.route("/ModularForm/GSp/Q/Sp4Z/specimen/<weight>/<orbit>/<number>/")
def l_function_siegel_page(weight, orbit, number):
    args = {'weight': weight, 'orbit': orbit, 'number': number}
    return render_single_Lfunction(Lfunction_SMF2_scalar_valued, args, request)


# L-function of Number field    ################################################
@l_function_page.route("/NumberField/<label>/")
def l_function_nf_page(label):
    args = {'label': label}
    return render_single_Lfunction(DedekindZeta, args, request)


# L-function of Artin representation    ########################################
@l_function_page.route("/ArtinRepresentation/<label>/")
def l_function_artin_page(label):
    return render_single_Lfunction(ArtinLfunction, {'label': label}, request)

# L-function of hypergeometric motive   ########################################
@l_function_page.route("/Motive/Hypergeometric/Q/<label>/<t>")
def l_function_hgm_page(label,t):
    args = {'label': label+'_'+t}
    return render_single_Lfunction(HypergeometricMotiveLfunction, args, request)

# L-function of symmetric powers of Elliptic curve #############################
@l_function_page.route("/SymmetricPower/<power>/EllipticCurve/Q/<label>/")
def l_function_ec_sym_page(power, label):
    args = {'power': power, 'underlying_type': 'EllipticCurve', 'field': 'Q', 'label': label}
    return render_single_Lfunction(SymmetricPowerLfunction, args, request)

# L-function of genus 2 curve/Q ########################################
@l_function_page.route("/Genus2Curve/Q/<cond>/<x>/")
def l_function_genus2_page(cond,x):
    args = {'label': cond+'.'+x}
    return render_single_Lfunction(Lfunction_genus2_Q, args, request)

# L-function from lcalcfile with given url #####################################
@l_function_page.route("/Lcalcurl/")
def l_function_lcalc_page():
    args = {'Ltype': 'lcalcurl', 'url': request.args['url']}
    return render_single_Lfunction(Lfunction_lcalc, args, request)


################################################################################
#   Helper functions, individual L-function homepages
################################################################################
def render_single_Lfunction(Lclass, args, request):
    temp_args = to_dict(request.args)
    logger.debug(args)
    logger.debug(temp_args)

    L = Lclass(**args)
    try:
        pass
    except Exception as ex:
        from flask import current_app
        if not current_app.debug:
            info = {'content': 'Sorry, there has been a problem: %s.'%str(ex.args), 'title': 'Error'}
            return render_template('LfunctionSimple.html', info=info, **info), 500
        else:
            raise ex
    try:
        if temp_args['download'] == 'lcalcfile':
            return render_lcalcfile(L, request.url)
    except KeyError as ex:
        pass # Do nothing

    info = initLfunction(L, temp_args, request)
    return render_template('Lfunction.html', **info)


def render_lcalcfile(L, url):
    ''' Function for rendering the lcalc file of an L-function.
    '''
    try:  # First check if the Lcalc file is stored in the database
        response = make_response(L.lcalcfile)
    except:
        import LfunctionLcalc
        response = make_response(LfunctionLcalc.createLcalcfile_ver2(L, url))

    response.headers['Content-type'] = 'text/plain'
    return response


def initLfunction(L, args, request):
    ''' Sets the properties to show on the homepage of an L-function page.
    '''
    info = {'title': L.title}
#    if 'title_arithmetic' in L:
    if not hasattr(L, 'fromDB'):
        L.fromDB = False

    try:
        info['title_arithmetic'] = L.title_arithmetic
        info['title_analytic'] = L.title_analytic
    except AttributeError:
        pass
    try:
        info['citation'] = L.citation
    except AttributeError:
        info['citation'] = ""
    try:
        info['support'] = L.support
    except AttributeError:
        info['support'] = ""

    info['Ltype'] = L.Ltype()

    try:
        info['label'] = L.label
    except:
        info['label'] = ""

    info['knowltype'] = ""   # will be things like g2c.q, ec.q, ...
    if L.Ltype() == "genus2curveQ":
        info['knowltype'] = "g2c.q"
    elif L.Ltype() == "ellipticcurveQ":
        info['knowltype'] = "ec.q"
    elif L.Ltype() == "dirichlet":
        info['knowltype'] = "character.dirichlet"
        info['label'] = str(L.charactermodulus) + "." + str(L.characternumber)
    elif L.Ltype() == "ellipticmodularform":
        info['knowltype'] = "mf"
        info['label'] =  str(L.level) + '.' + str(L.weight) 
        info['label'] += '.' + str(L.character) + '.' + str(L.label) 
        info['label'] += '.' + request.url.split("/")[-2]  # the embedding
    elif L.Ltype() == "riemann":
        info['knowltype'] = "riemann"
        info['label'] = "zeta"
    elif L.Ltype() == "maass":
        info['knowltype'] = "degree" + str(L.degree)
        info['label'] = re.sub(".*/([^/]+)/$",r"\1",request.url)  # should have an id from somewhere?


#    if L.Ltype() in ["genus2curveQ", "ellipticcurveQ", "dirichlet"] and L.fromDB:
    if L.fromDB and L.algebraic:
        if L.motivic_weight % 2 == 0:
           arith_center = "\\frac{" + str(1 + L.motivic_weight) + "}{2}"
        else:
           arith_center = str(ZZ(1)/2 + L.motivic_weight/2)
        svt_crit = specialValueTriple(L, 0.5, '\\frac12',arith_center)
#        info['sv_critical'] = specialValueString(L, 0.5, '1/2')
#        info['sv_critical_arithmetic'] = specialValueString(L, 0.5, str(ZZ(1)/2 + L.motivic_weight/2),'arithmetic')
        info['sv_critical'] = svt_crit[0] + "\\ =\\ " + svt_crit[2]
        info['sv_critical_analytic'] = [svt_crit[0], svt_crit[2]]
        info['sv_critical_arithmetic'] = [svt_crit[1], svt_crit[2]]

        if L.motivic_weight % 2 == 1:
           arith_edge = "\\frac{" + str(2 + L.motivic_weight) + "}{2}"
        else:
           arith_edge = str(ZZ(1) + L.motivic_weight/2)

        svt_edge = specialValueTriple(L, 1, '1',arith_edge)
        info['sv_edge'] = svt_edge[0] + "\\ =\\ " + svt_edge[2]
        info['sv_edge_analytic'] = [svt_edge[0], svt_edge[2]]
        info['sv_edge_arithmetic'] = [svt_edge[1], svt_edge[2]]

        info['st_group'] = L.st_group
        info['rank'] = L.order_of_vanishing
        info['motivic_weight'] = L.motivic_weight


    elif L.Ltype() != "artin" or (L.Ltype() == "artin" and L.sign != 0):
        try:
            info['sv_edge'] = specialValueString(L, 1, '1')
            info['sv_critical'] = specialValueString(L, 0.5, '1/2')
        except:
            info['sv_critical'] = "L(1/2): not computed"
            info['sv_edge'] = "L(1): not computed"

    info['args'] = args

    info['credit'] = L.credit
    #try:
    #    info['citation'] = L.citation
    #except:
    #    pass

    try:
        info['factorization'] = L.factorization
    except:
        pass

    try:
        info['url'] = L.url
    except:
        info['url'] = ''

    info['degree'] = int(L.degree)

    info['zeroeslink'] = (request.url.replace('/L/', '/L/Zeros/').
                          replace('/Lfunction/', '/L/Zeros/').
                          replace('/L-function/', '/L/Zeros/'))  # url_for('zeroesLfunction',  **args)

    info['plotlink'] = (request.url.replace('/L/', '/L/Plot/').
                        replace('/Lfunction/', '/L/Plot/').
                        replace('/L-function/', '/L/Plot/'))  # info['plotlink'] = url_for('plotLfunction',  **args)
#    # an inelegant way to remove the plot in certain cases
    if L.Ltype() == 'ellipticmodularform':
        if ( (L.number == 1 and (1 + L.level) * L.weight > 50) or 
               (L.number > 1 and L.level * L.weight > 50)):
            info['zeroeslink'] = ""
            info['plotlink'] = ""


    info['bread'] = []
    info['properties2'] = set_gaga_properties(L)

    # Create friendlink by removing 'L/' and ending '/'
    friendlink = request.url.replace('/L/', '/').replace('/L-function/', '/').replace('/Lfunction/', '/')
    splitlink = friendlink.rpartition('/')
    friendlink = splitlink[0] + splitlink[2]
    logger.debug(L.Ltype())

    if L.Ltype() == 'maass':
        if L.group == 'GL2':
            minNumberOfCoefficients = 100     # TODO: Fix this to take level into account

            if len(L.dirichlet_coefficients) < minNumberOfCoefficients:
                info['zeroeslink'] = ''
                info['plotlink'] = ''
            info['bread'] = get_bread(2, [('Maass Form',
                                           url_for('.l_function_maass_browse_page')),
                                          ('\(' + L.texname + '\)', request.url)])
            info['friends'] = [('Maass Form ', friendlink)]

            # Navigation to previous and next form
            next_form_id = L.mf.next_maassform_id()
            if next_form_id:
                next_data = ("next",r"$L(s,f_{\text next})$", '/L' +
                             url_for('mwf.render_one_maass_waveform',
                             maass_id = next_form_id) )
            else:
                next_data = ('','','')
            prev_form_id = L.mf.prev_maassform_id()
            if prev_form_id:
                prev_data = ("previous", r"$L(s,f_{\text prev}$)", '/L' +
                             url_for('mwf.render_one_maass_waveform',
                             maass_id = prev_form_id) )
            else:
                prev_data = ('','','')

            info['navi'] = ( prev_data, next_data )

        else:
            if L.fromDB and not L.selfdual:
                info['friends'] = [('Dual L-function', L.dual_link)]
                
            info['bread'] = get_bread(L.degree,
                                      [('Maass Form', url_for('.l_function_maass_gln_browse_page',
                                                              degree='degree' + str(L.degree))),
                                       (L.dbid, request.url)])

    elif L.Ltype() == 'riemann':
        info['bread'] = get_bread(1, [('Riemann Zeta', request.url)])
        info['friends'] = [('\(\mathbb Q\)', url_for('number_fields.by_label', label='1.1.1.1')), ('Dirichlet Character \(\\chi_{1}(1,\\cdot)\)',url_for('characters.render_Dirichletwebpage', modulus=1, number=1))]

    elif L.Ltype() == 'dirichlet':
        mod, num = L.charactermodulus, L.characternumber
        Lpattern = r"\(L(s,\chi_{%s}(%s,&middot;))\)"
        if mod > 1:
            pmod,pnum = WebDirichlet.prevprimchar(mod, num)
            Lprev = ("previous",Lpattern%(pmod,pnum),
                     url_for('.l_function_dirichlet_page',
                             modulus=pmod,number=pnum))
        else:
            Lprev = ('','','')
        nmod,nnum = WebDirichlet.nextprimchar(mod, num)
        Lnext = ("next",Lpattern%(nmod,nnum),
                 url_for('.l_function_dirichlet_page',
                         modulus=nmod,number=nnum))
        info['navi'] = (Lprev,Lnext)
        #print info['navi']
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        charname = WebDirichlet.char2tex(smod, snum)
        info['bread'] = get_bread(1, [(charname, request.url)])
        info['friends'] = [('Dirichlet Character ' + str(charname), friendlink)]
        if L.fromDB and not L.selfdual:
            info['friends'].append(('Dual L-function', L.dual_link))


    elif L.Ltype() == 'ellipticcurveQ':
        label = L.label
        while friendlink[len(friendlink) - 1].isdigit():  # Remove any number at the end to get isogeny class url
            friendlink = friendlink[0:len(friendlink) - 1]

        info['friends'] = [('Isogeny class ' + label, friendlink)]
        for i in range(1, L.nr_of_curves_in_class + 1):
            info['friends'].append(('Elliptic curve ' + label + str(i), friendlink + str(i)))
        if L.modform:
            info['friends'].append(('Modular form ' + label.replace('.', '.2'), url_for("emf.render_elliptic_modular_forms", level=L.modform['level'], weight=2, character=1, label=L.modform['iso'])))
            # We don't want the modular form's L-function to be a friend of the elliptic curve L-function since they are the same!
            # info['friends'].append(('L-function ' + label.replace('.', '.2'),
            #                         url_for('.l_function_emf_page', level=L.modform['level'],
            #                             weight=2, character=1, label=L.modform['iso'], number=0)))
        info['friends'].append(
            ('Symmetric square L-function', url_for(".l_function_ec_sym_page",
                                                    power='2', label=label)))
        info['friends'].append(
            ('Symmetric cube L-function', url_for(".l_function_ec_sym_page", power='3', label=label)))
        info['bread'] = get_bread(2, [('Elliptic curve', url_for('.l_function_ec_browse_page')),
                                      (label, url_for('.l_function_ec_page', label=label))])
    elif L.Ltype() == 'genus2curveQ':
        # should use url_for
        info['friends'] = [('Isogeny class ' + L.label, "/Genus2Curve/Q/" + L.label.replace(".","/"))]

    elif L.Ltype() == 'ellipticmodularform':
        friendlink = friendlink.rpartition('/')[0] # Strips off the embedding
        # number for the L-function
        if L.character:
            info['friends'] = [('Modular form ' + str(
                        L.level) + '.' + str(L.weight) + '.' + str(L.character) +
                                str(L.label), friendlink)]
        else:
            info['friends'] = [('Modular form ' + str(L.level) + '.' +
                                str(L.weight) + str(L.label), friendlink)]
        if L.ellipticcurve:
            info['friends'].append(
                ('EC isogeny class ' + L.ellipticcurve,
                 url_for("ec.by_ec_label", label=L.ellipticcurve)))
            info['friends'].append(('L-function ' + str(L.level) + '.' + str(L.label),
                                    url_for('.l_function_ec_page', label=L.ellipticcurve)))
            for i in range(1, L.nr_of_curves_in_class + 1):
                info['friends'].append(('Elliptic curve ' + L.ellipticcurve + str(i),
                                        url_for("ec.by_ec_label", label=L.ellipticcurve + str(i))))
            info['friends'].append(
                ('Symmetric square L-function',
                 url_for(".l_function_ec_sym_page", power='2',
                         label=L.ellipticcurve)))
            info['friends'].append(
                ('Symmetric cube L-function',
                 url_for(".l_function_ec_sym_page", power='3',
                         label=L.ellipticcurve)))

    elif L.Ltype() == 'hilbertmodularform':
        friendlink = '/'.join(friendlink.split('/')[:-1])
        info['friends'] = [('Hilbert modular form ' + L.label, friendlink.rpartition('/')[0])]

    elif L.Ltype() == 'dedekindzeta':
        info['friends'] = [('Number Field', friendlink)]

    elif L.Ltype() in ['lcalcurl', 'lcalcfile']:
        info['bread'] = [('L-functions', url_for('.l_function_top_page'))]

    elif L.Ltype() == 'SymmetricPower':
        def ordinal(n):
            if n == 2:
                return "Square"
            elif n == 3:
                return "Cube"
            elif 10 <= n % 100 < 20:
                return str(n) + "th Power"
            else:
                return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, "th") + " Power"

        if L.m == 2:
            info['bread'] = get_bread(3, [("Symmetric square of Elliptic curve",
                                           url_for('.l_function_ec_sym2_browse_page')),
                                          (L.label, url_for('.l_function_ec_sym_page',
                                                            label=L.label,power=L.m))])
        elif L.m == 3:
            info['bread'] = get_bread(4, [("Symmetric cube of Elliptic curve",
                                           url_for('.l_function_ec_sym3_browse_page')),
                                          (L.label, url_for('.l_function_ec_sym_page',
                                                            label=L.label,power=L.m))])
        else:
            info['bread'] = [('L-functions', url_for('.l_function_top_page')),
                             ('Symmetric %s of Elliptic curve ' % ordinal(L.m)
                              + str(L.label),
                              url_for('.l_function_ec_sym_page',
                                      label=L.label,power=L.m))]

        friendlink = request.url.replace('/L/SymmetricPower/%d/' % L.m, '/')
        splitlink = friendlink.rpartition('/')
        friendlink = splitlink[0] + splitlink[2]

        friendlink2 = request.url.replace('/L/SymmetricPower/%d/' % L.m, '/L/')
        splitlink = friendlink2.rpartition('/')
        friendlink2 = splitlink[0] + splitlink[2]

        info['friends'] = [('Isogeny class ' + L.label, friendlink), ('Symmetric 1st Power', friendlink2)]
        for j in range(2, L.m + 2):
            if j != L.m:
                friendlink3 = request.url.replace('/L/SymmetricPower/%d/' % L.m, '/L/SymmetricPower/%d/' % j)
                info['friends'].append(('Symmetric %s' % ordinal(j), friendlink3))

    elif L.Ltype() == 'siegelnonlift' or L.Ltype() == 'siegeleisenstein' or L.Ltype() == 'siegelklingeneisenstein' or L.Ltype() == 'siegelmaasslift':
        friendlink = friendlink.rpartition('/')[0] #strip off embedding number for L-function
        weight = str(L.weight)
        number = str(L.number)
        info['friends'] = [('Siegel Modular Form ' + weight + '_' + L.orbit, friendlink)]

    elif L.Ltype() == "artin":
        info['friends'] = [('Artin representation', L.artin.url_for())]
        if L.sign == 0:           # The root number is now unknown
            info['zeroeslink'] = ''
            info['plotlink'] = ''

    elif L.Ltype() == "hgmQ":
        # undo the splitting above
        newlink = friendlink.rpartition('t')
        friendlink = newlink[0]+'/t'+newlink[2]
        #info['friends'] = [('Hypergeometric motive ', friendlink.replace("t","/t"))]   # The /L/ trick breaks down for motives, because we have a scheme for the L-functions themselves
        info['friends'] = [('Hypergeometric motive ', friendlink)]   # The /L/ trick breaks down for motives, because we have a scheme for the L-functions themselves

    # the code below should be in Lfunction.py
    info['conductor'] = L.level
    if not is_prime(L.level):
        info['conductor_factored'] = latex(factor(int(L.level)))

    info['degree'] = L.degree
    info['sign'] = "$"+styleTheSign(L.sign)+"$"
    info['algebraic'] = L.algebraic
    if L.selfdual:
        info['selfdual'] = 'yes'
    else:
        info['selfdual'] = 'no'
    if L.primitive:
        info['primitive'] = 'yes'
    else:
        info['primitive'] = 'no'
    info['dirichlet'] = lfuncDShtml(L, "analytic")
    # Hack, fix this more general?
    info['dirichlet'] = info['dirichlet'].replace('*I','<em>i</em>')
    
    info['eulerproduct'] = lfuncEPtex(L, "abstract")
    info['functionalequation'] = lfuncFEtex(L, "analytic")
    info['functionalequationSelberg'] = lfuncFEtex(L, "selberg")
 #   if L.Ltype() in ["genus2curveQ", "ellipticcurveQ", "dirichlet"] and L.fromDB:
    if L.fromDB and L.algebraic:
        info['dirichlet_arithmetic'] = lfuncDShtml(L, "arithmetic")
        info['eulerproduct_arithmetic'] = lfuncEPtex(L, "arithmetic")
        info['functionalequation_arithmetic'] = lfuncFEtex(L, "arithmetic")

    if len(request.args) == 0:
        lcalcUrl = request.url + '?download=lcalcfile'
    else:
        lcalcUrl = request.url + '&download=lcalcfile'

    if L.Ltype() != 'dirichlet':
        info['downloads'] = [('Lcalcfile', lcalcUrl)]
    return info


def set_gaga_properties(L):
    ''' Sets the properties in the properties box in the
    upper right corner
    '''
    ans = [('Degree', str(L.degree))]

    ans.append(('Conductor', str(L.level)))
    ans.append(('Sign', "$"+styleTheSign(L.sign)+"$"))

    if L.selfdual:
 #       sd = 'Self-dual'
        ans.append(('Self-dual', "yes"))
    else:
 #       sd = 'Not self-dual'
        ans.append(('Self-dual', "no"))
 #   ans.append((None, sd))

    if L.algebraic:
        ans.append(('Motivic weight', str(L.motivic_weight)))

    if L.primitive:
        prim = 'Primitive'
    else:
        prim = 'Not primitive'
#    ans.append((None,        prim))    Disabled until fixed

    return ans


################################################################################
#   Route functions, plotting L-function and displaying zeroes
################################################################################

# L-function of Elliptic curve #################################################
@l_function_page.route("/Plot/EllipticCurve/Q/<label>/")
def l_function_ec_plot(label):
    query = "label = '{0}'".format(label)
    try:
        return render_plotLfunction_from_db("ecplots", "ecplots", query)
    except KeyError:
        return render_plotLfunction(request, 'EllipticCurve', 'Q', label, None, None, None,
                                    None, None, None)

@l_function_page.route("/Plot/<arg1>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@l_function_page.route("/Plot/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def plotLfunction(arg1=None, arg2=None, arg3=None, arg4=None, arg5=None, arg6=None, arg7=None, arg8=None, arg9=None):
    return render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)


@l_function_page.route("/Zeros/<arg1>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@l_function_page.route("/Zeros/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def zeroesLfunction(arg1=None, arg2=None, arg3=None, arg4=None, arg5=None, arg6=None, arg7=None, arg8=None, arg9=None):
    return render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)


################################################################################
#   Render functions, plotting L-function and displaying zeroes
################################################################################
def render_plotLfunction_from_db(db, dbTable, condition):
    data_location = os.path.expanduser(
        "~/data/lfunction_plots/{0}.db".format(db))

    if not os.path.exists(data_location):
        # We want to raise some exception so that the calling
        # function can catch it and fall back to normal plotting
        # when the database does not exist or doesn't have the
        # plot. This seems like a reasonable exception to raise.
        raise KeyError

    try:
        db = sqlite3.connect(data_location)
        with db:
            cur = db.cursor()
            query = "SELECT start,end,points FROM {0} WHERE {1} LIMIT 1".format(dbTable,
                                                                                condition)
            cur.execute(query)
            row = cur.fetchone()

        db.close()

        start,end,values = row
        values = numpy.frombuffer(values)
        step = (end - start)/values.size

        pairs = [ (start + x * step, values[x] )
                  for x in range(0, values.size, 1)]
        p = plot(spline(pairs), -30, 30, thickness = 0.4)
        styleLfunctionPlot(p, 8)

    except (sqlite3.OperationalError, TypeError):
        # An OperationalError will happen when the database exists for some reason
        # but it doesn't have the table. A TypeError will happen when there are no
        # results returned, in which case row will be None and unpacking the tuple
        # will fail. We turn both of these in KeyErrors, which can be caught by
        # the calling function to fallback to normal plotting.

        raise KeyError

    fn = tempfile.mktemp(suffix=".png")
    p.save(filename=fn, dpi = 100)
    data = file(fn).read()
    os.remove(fn)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response


def render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    data = getLfunctionPlot(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
    if not data:
        # see note about missing "hardy_z_function" in plotLfunction()
        return flask.redirect(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response


def getLfunctionPlot(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    pythonL = generateLfunctionFromUrl(
        arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))

    plotrange = 30
    if hasattr(pythonL,"lfunc_data"):
        if pythonL.lfunc_data is None:
            return ""
        else:
            F = p2sage(pythonL.lfunc_data['plot'])
    else:
     # obsolete, because lfunc_data comes from DB?
      #  if pythonL.fromDB:
      #      return ""
        L = pythonL.sageLfunction
        # HSY: I got exceptions that "L.hardy_z_function" doesn't exist
        # SL: Reason, it's not in the distribution of Sage
        if not hasattr(L, "hardy_z_function"):
            return None
        # FIXME there could be a filename collission
        #F = [(i, L.hardy_z_function(CC(.5, i)).real()) for i in srange(-30, 30, .1)]
        plotStep = .1
    #    if pythonL._Ltype == "hilbertmodularform":
        if pythonL._Ltype not in ["riemann", "maass", "ellipticmodularform", "ellipticcurveQ"]:
            plotrange = 12
        F = [(i, L.hardy_z_function(i).real()) for i in srange(-1*plotrange, plotrange, plotStep)]
    interpolation = spline(F)
    F_interp = [(i, interpolation(i)) for i in srange(-1*plotrange, plotrange, 0.05)]
    p = line(F_interp)
#    p = line(F)    # temporary hack while the correct interpolation is being implemented
    
    styleLfunctionPlot(p, 10)
    fn = tempfile.mktemp(suffix=".png")
    p.save(filename=fn)
    data = file(fn).read()
    os.remove(fn)
    return data

def styleLfunctionPlot(p, fontsize):
    p.fontsize(fontsize)
    p.axes_color((0.5,0.5,0.5))
    p.tick_label_color((0.5,0.5,0.5))
    p.axes_width(0.2)




def render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    ''' Renders the first few zeroes of the L-function with the given arguments.
    '''
    L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))

    if hasattr(L,"lfunc_data"):
        if L.lfunc_data is None:
            return "<span>" + L.zeros + "</span>"
        else:
            website_zeros = L.lfunc_data['zeros']
    else:
        # This depends on mathematical information, all below is formatting
        # More semantic this way
        # Allow 10 seconds
        website_zeros = L.compute_web_zeros(time_allowed = 10)

    positiveZeros = []
    negativeZeros = []

    for zero in website_zeros:
        if abs(float(zero)) < 1e-10:
            zero = 0
        if float(zero) < 0:
            negativeZeros.append(str(zero))
        else:
            positiveZeros.append(str(zero))

    zero_truncation = 25   # show at most 25 positive and negative zeros
                           # later: implement "show more"
    negativeZeros = negativeZeros[-1*zero_truncation:]
    positiveZeros = positiveZeros[:zero_truncation]
    # Format the html string to render
#    positiveZeros = str(positiveZeros)
#    negativeZeros = str(negativeZeros)
    positiveZeros = ", ".join(positiveZeros)
    negativeZeros = ", ".join(negativeZeros)
    if len(positiveZeros) > 2 and len(negativeZeros) > 2:  # Add comma and empty space between negative and positive
       # negativeZeros = negativeZeros.replace("]", ", ]")
        negativeZeros = negativeZeros + ", "

    return "<span class='redhighlight'>{0}</span><span class='positivezero'>{1}</span>".format(
     #   negativeZeros[1:len(negativeZeros) - 1], positiveZeros[1:len(positiveZeros) - 1])
        negativeZeros.replace("-","&minus;"), positiveZeros)


def generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, temp_args):
    ''' Returns the L-function object corresponding to the supplied argumnents
    from the url. temp_args contains possible arguments after a question mark.
    '''
    if arg1 == 'Riemann':
        return RiemannZeta()

    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        return Lfunction_Dirichlet(charactermodulus=arg3, characternumber=arg4)

    elif arg1 == 'EllipticCurve' and arg2 == 'Q':
        return Lfunction_EC_Q(label=arg3)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic':  # this has args: one for weight and one for level
        # logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_EMF(level=arg5, weight=arg6, character=arg7, label=arg8, number=arg9)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'TotallyReal' and arg5 == 'holomorphic':  # Hilbert modular form
        # logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_HMF(field=arg4, label=arg6, character=arg7, number=arg8)

# next option is probably from an archaic HMF url
    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 != 'Q' and arg4 == 'holomorphic':  # Hilbert modular form
        # logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_HMF(field=arg3, label=arg5, character=arg6, number=arg7)

    elif arg1 == 'ModularForm' and arg2 == 'GL2'and arg3 == 'Q' and arg4 == 'Maass':
        # logger.debug(db)
        try:
            dbid = bson.objectid.ObjectId(arg5)
        except Exception as ex:
            dbid = arg5
        return Lfunction_Maass(dbid=dbid)

    elif arg1 == 'ModularForm' and (arg2 == 'GSp4' or arg2 == 'GL4' or arg2 == 'GL3') and arg3 == 'Q' and arg4 == 'Maass':
        # logger.debug(db)
        if arg6 == '':  # Not from database
            return Lfunction_Maass(dbid=arg5, dbName='Lfunction', dbColl='LemurellMaassHighDegree')
        else:
            return Lfunction_Maass(fromDB = True, group = arg2, level = arg5,
                char = arg6, R = arg7, ap_id = arg8)


    elif arg1 == 'ModularForm' and arg2 == 'GSp' and arg3 == 'Q' and arg4 == 'Sp4Z' and arg5 == 'specimen':  # this should be changed when we fix the SMF urls
        return Lfunction_SMF2_scalar_valued(weight=arg6, orbit=arg7, number=arg8)

    elif arg1 == 'NumberField':
        return DedekindZeta(label=str(arg2))

    elif arg1 == "ArtinRepresentation":
        return ArtinLfunction(label=str(arg2))

    elif arg1 == "SymmetricPower":
        return SymmetricPowerLfunction(power=arg2, underlying_type=arg3, field=arg4, label=arg5)

    elif arg1 == "Motive" and arg2 == "Hypergeometric" and arg3 == "Q":
        if arg5:
            return HypergeometricMotiveLfunction(family = arg4, t = arg5)
        else:
            return HypergeometricMotiveLfunction(label = arg4)

    elif arg1 == "Genus2Curve" and arg2 == "Q":
        return Lfunction_genus2_Q(label=str(arg3)+'.'+str(arg4))

    elif arg1 == 'Lcalcurl':
        return Lfunction_lcalc(Ltype='lcalcurl', url=temp_args['url'])

    else:
        return flask.redirect(403)


################################################################################
#   Route functions, graphs for browsing L-functions
################################################################################
@l_function_page.route("/browseGraph/")
def browseGraph():
    return render_browseGraph(request.args)


@l_function_page.route("/browseGraphTMP/")
def browseGraphTMP():
    return render_browseGraphTMP(request.args)


@l_function_page.route("/browseGraphHolo/")
def browseGraphHolo():
    return render_browseGraphHolo(request.args)


@l_function_page.route("/browseGraphChar/")
def browseGraphChar():
    return render_browseGraphChar(request.args)


###########################################################################
#   Functions for rendering graphs for browsing L-functions.
###########################################################################
def render_browseGraph(args):
    # logger.debug(args)
    if 'sign' in args:
        data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level']), args['sign']]])
    else:
        data = LfunctionPlot.paintSvgFileAllNEW([[args['group'], int(args['level'])]])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


def render_browseGraphHolo(args):
    # logger.debug(args)
    data = LfunctionPlot.paintSvgHolo(args['Nmin'], args['Nmax'], args['kmin'], args['kmax'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


def render_browseGraphTMP(args):
    # logger.debug(args)
    data = LfunctionPlot.paintSvgHoloGeneral(
        args['Nmin'], args['Nmax'], args['kmin'], args['kmax'], args['imagewidth'], args['imageheight'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


def render_browseGraphChar(args):
    # logger.debug(args)
    data = LfunctionPlot.paintSvgChar(
        args['min_cond'], args['max_cond'], args['min_order'], args['max_order'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response


###########################################################################
#   Functions for displaying examples of degree 2 L-functions on the
#   degree browsing page.
###########################################################################
def processEllipticCurveNavigation(startCond, endCond):
    """
    Produces a table of all L-functions of elliptic curves with conductors
    from startCond to endCond
    """
    try:
        N = startCond
        if N < 11:
            N = 11
        elif N > 100:
            N = 100
    except:
        N = 11

    try:
        if endCond > 500:
            end = 500
        else:
            end = endCond

    except:
        end = 100

    iso_list = isogenyclasstable(N, end)
    s = '<h5>Examples of L-functions attached to isogeny classes of elliptic curves</h5>'
    s += '<table>'

    logger.debug(iso_list)

    counter = 0
    nr_of_columns = 10
    for label in iso_list:
        if counter == 0:
            s += '<tr>'

        counter += 1
        s += '<td><a href="' + url_for('.l_function_ec_page', label=label) + '">%s</a></td>\n' % label

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s


def processMaassNavigation(numrecs=35):
    """
    Produces a table of numrecs Maassforms with Fourier coefficients in the database
    """
    DB = LfunctionDatabase.getMaassDb()
    s = '<h5>The L-functions attached to the first 4 weight 0 Maass newforms with trivial character on Hecke congruence groups $\Gamma_0(N)$</h5>'
    s += '<table>\n'
    i = 0
    maxinlevel = 4
    for level in [1, 2, 3, 4, 5, 6, 7, 9]:
        j = 0
        s += '<tr>\n'
        s += '<td><bold>N={0}:</bold></td>\n'.format(level)
        finds = DB.get_Maass_forms({'Level': int(level),
                                    'char': 1,
                                    'Newform' : None})
        for f in finds:
            nc = f.get('Numc', 0)
            if nc <= 0:
                continue
            R = f.get('Eigenvalue', 0)
            if R == 0:
                continue
            if f.get('Symmetry',0) == 1:
                T = 'o'
            else:
                T = 'e'
            _until = min(12, len(str(R)))
            Rst = str(R)[:_until]
            idd = f.get('_id', None)
            if idd is None:
                continue
            idd = str(idd)
            url = url_for('.l_function_maass_page', dbid=idd)
            s += '<td><a href="{0}">{1}</a>{2}'.format(url, Rst, T)
            i += 1
            j += 1
            if i >= numrecs or j >= maxinlevel:
                break
        s += '</tr>\n'
        if i > numrecs:
            break
    s += '</table>\n'

    return s


def processSymPowerEllipticCurveNavigation(startCond, endCond, power):
    """
    Produces a table of all symmetric power L-functions of elliptic curves
    with conductors from startCond to endCond
    """
    try:
        N = startCond
        if N < 11:
            N = 11
        elif N > 100:
            N = 100
    except:
        N = 11

    try:
        if endCond > 500:
            end = 500
        else:
            end = endCond

    except:
        end = 100

    iso_list = isogenyclasstable(N, end)
    if power == 2:
        powerName = 'square'
    elif power == 3:
        powerName = 'cube'
    else:
        powerName = str(power) + '-th power'

    s = '<h5>Examples of symmetric ' + powerName + \
        ' L-functions attached to isogeny classes of elliptic curves</h5>'
    s += '<table>'

    logger.debug(iso_list)

    counter = 0
    nr_of_columns = 10
    for label in iso_list:
        if counter == 0:
            s += '<tr>'

        counter += 1
        s += '<td><a href="' + url_for('.l_function_ec_sym_page', power=str(power),
                                       label=label) + '">%s</a></td>\n' % label

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s

def processGenus2CurveNavigation(startCond, endCond):
    """
    Produces a table of all L-functions of genus 2 curves with conductors
    from startCond to endCond
    """
    Nmin = startCond
    if Nmin < 169:
        Nmin = 169

    Nmax = endCond
    if Nmax > 10000:
        Nmax = 10000

    query = {'cond': {'$lte': Nmax, '$gte': Nmin}}

    # Get all the isogeny classes and sort them according to conductor
    cursor = base.getDBConnection().genus2_curves.isogeny_classes.find(query)
    iso_list = cursor.sort([('cond', ASCENDING), ('label', ASCENDING)])

    s = '<h5>Examples of L-functions attached to isogeny classes of genus 2 curves</h5>'
    s += '<table>'

    logger.debug(iso_list)

    counter = 0
    nr_of_columns = 10
    for iso in iso_list:
        if counter == 0:
            s += '<tr>'

        counter += 1
        condx = iso['label'].split('.')
        s += '<td><a href="' + url_for('.l_function_genus2_page',cond=condx[0], x=condx[1]) + '">%s</a></td>\n' % iso['label']

        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter > 0:
        s += '</tr>\n'

    s += '</table>\n'
    return s
