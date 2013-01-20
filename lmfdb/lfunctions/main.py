# -*- coding: utf-8 -*-
from lmfdb.base import *
from flask import Flask, session, g, render_template, url_for, request, make_response, abort
import flask

from sage.all import *
import tempfile
import os
import pymongo
from Lfunction import *
import LfunctionComp as LfunctionCompo
import LfunctionPlot as LfunctionPlot
from lmfdb.utils import to_dict
import bson
from Lfunctionutilities import (lfuncDStex, lfuncEPtex, lfuncFEtex,
                                truncatenumber, styleTheSign, specialValueString)
from lmfdb.DirichletCharacter import getPrevNextNavig
from lmfdb.lfunctions import l_function_page, logger

# import upload2Db.py


################################################################################
#   Route functions, navigation pages
################################################################################

# Top page #####################################################################
@l_function_page.route("/")
def l_function_top_page():
    info = set_info_for_start_page()
    return render_template("LfunctionNavigate.html", **info)


# Degree browsing page #########################################################
@l_function_page.route("/<degree>/")
def l_function_degree_page(degree):
    degree = int(degree[6:])
    info = {"degree": degree}
    info["key"] = 777
    info["bread"] = get_bread(degree, [])
    return render_template("DegreeNavigateL.html", title='Degree ' + str(degree) + ' L-functions', **info)


# Dirichlet L-function browsing page ##############################################
@l_function_page.route("/degree1/Dirichlet/")
def l_function_dirichlet_browse_page():
    info = {"bread": get_bread(1, [("Dirichlet", url_for('.l_function_dirichlet_browse_page'))])}
    info["minModDefault"] = 1
    info["maxModDefault"] = 20
    info["maxOrder"] = 14
    info["contents"] = [LfunctionPlot.getOneGraphHtmlChar(info["minModDefault"], info[
                                                          "maxModDefault"], 1, info["maxOrder"])]
    return render_template("Dirichlet.html", title='Dirichlet L-functions', **info)


# L-function of GL(2) cusp forms browsing page ##############################################
@l_function_page.route("/degree2/CuspForm/")
def l_function_cuspform_browse_page():
    info = {"bread": get_bread(2, [("CuspForm", url_for('.l_function_cuspform_browse_page'))])}
    info["contents"] = [LfunctionPlot.getOneGraphHtmlHolo(1, 13, 2, 12)]
    return render_template("cuspformGL2.html", title='L-functions of GL(2) Cusp Forms', **info)


# L-function of GL(2) maass forms browsing page ##############################################
@l_function_page.route("/degree2/MaassForm/")
def l_function_maass_browse_page():
    info = {"bread": get_bread(2, [("MaassForm", url_for('.l_function_maass_browse_page'))])}
    info["contents"] = [processMaassNavigation()]
    return render_template("MaassformGL2.html", title='L-functions of GL(2) Maass Forms', **info)


# L-function of elliptic curves browsing page ##############################################
@l_function_page.route("/degree2/EllipticCurve/")
def l_function_ec_browse_page():
    info = {"bread": get_bread(2, [("EllipticCurve", url_for('.l_function_ec_browse_page'))])}
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
    info = {"bread": get_bread(3, [("EllipticCurve",
                                    url_for('.l_function_ec_sym2_browse_page'))])}
    info["representation"] = 'Symmetric square'
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 26, 2)]
    return render_template("ellipticcurve.html",
                           title='Symmetric square L-functions of Elliptic Curves', **info)


# L-function of symmetric cube of elliptic curves browsing page ################
@l_function_page.route("/degree4/EllipticCurve/SymmetricCube/")
def l_function_ec_sym3_browse_page():
    info = {"bread": get_bread(4, [("EllipticCurve", url_for('.l_function_ec_sym3_browse_page'))])}
    info["representation"] = 'Symmetric cube'
    info["contents"] = [processSymPowerEllipticCurveNavigation(11, 17, 3)]
    return render_template("ellipticcurve.html",
                           title='Symmetric cube L-functions of Elliptic Curves', **info)


###########################################################################
#   Helper functions, navigation pages
###########################################################################
def set_info_for_start_page():
    ''' Sets the properties of the top L-function page.
    '''

    tt = [[{'title': 'Riemann zeta function', 'link': url_for('.l_function_riemann_page')},
           {'title': 'Dirichlet L-function', 'link': url_for('.l_function_dirichlet_browse_page')}],

          [{'title': 'GL2 Cusp form', 'link': url_for('.l_function_cuspform_browse_page')},
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


# L-function of Elliptic curve #################################################
@l_function_page.route("/EllipticCurve/Q/<label>/")
def l_function_ec_page(label):
    logger.debug(label)
    from elliptic_curve import cremona_label_regex, lmfdb_label_regex

    m = lmfdb_label_regex.match(label)
    if m is not None:
        # Lmfdb label is given
        if m.groups()[2]:
            # strip off the curve number
            return flask.redirect(url_for('.l_function_ec_page', label=label[:-1]), 301)
        else:
            args = {'label': label}
            return render_single_Lfunction(Lfunction_EC, args, request)

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
def l_function_emf_redirect(level, weight, character, label):
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character=character, label=label, number=0), code=301)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/<character>/")
def l_function_emf_redirect(level, weight, character):
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character=character, label='a', number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/Q/holomorphic/<level>/<weight>/")
def l_function_emf_redirect(level, weight):
    return flask.redirect(url_for('.l_function_emf_page', level=level, weight=weight,
                                  character='0', label='a', number='0'), code=301)


# L-function of Hilbert modular form ###########################################
@l_function_page.route("/ModularForm/GL2/<field>/holomorphic/<label>/<character>/<number>/")
def l_function_hmf_page(field, label, character, number):
    args = {'field': field, 'label': label, 'character': character,
            'number': number}
    return render_single_Lfunction(Lfunction_HMF, args, request)


@l_function_page.route("/ModularForm/GL2/<field>/holomorphic/<label>/<character>/")
def l_function_hmf_redirect(field, label, character):
    return flask.redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character=character, number='0'), code=301)


@l_function_page.route("/ModularForm/GL2/<field>/holomorphic/<label>/")
def l_function_hmf_redirect(field, label):
    return flask.redirect(url_for('.l_function_hmf_page', field=field, label=label,
                                  character='0', number='0'), code=301)


# L-function of GL(2) Maass form ###############################################
@l_function_page.route("/ModularForm/GL2/Q/Maass/<dbid>/")
def l_function_maass_page(dbid):
    args = {'dbid': bson.objectid.ObjectId(dbid)}
    return render_single_Lfunction(Lfunction_Maass, args, request)


# L-function of GL(n) Maass form (n>2) #########################################
@l_function_page.route("/ModularForm/<group>/Q/Maass/<dbid>/")
def l_function_maass_gln_page(group, dbid):
    args = {'dbid': dbid, 'dbName': 'Lfunction', 'dbColl': 'LemurellMaassHighDegree'}
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
@l_function_page.route("/ArtinRepresentation/<dimension>/<conductor>/<tim_index>/")
def l_function_artin_page(dimension, conductor, tim_index):
    args = {'dimension': dimension, 'conductor': conductor,
            'tim_index': tim_index}
    return render_single_Lfunction(ArtinLfunction, args, request)


# L-function of symmetric powers of Elliptic curve #############################
@l_function_page.route("/SymmetricPower/<power>/EllipticCurve/Q/<label>/")
def l_function_ec_sym_page(power, label):
    args = {'power': power, 'underlying_type': 'EllipticCurve', 'field': 'Q', 'label': label}
    return render_single_Lfunction(SymmetricPowerLfunction, args, request)


# L-function from lcalcfile with given url #####################################
@l_function_page.route("/Lcalcurl/<Ltype>/<url>/")
def l_function_lcalc_page(Ltype, url):
    args = {Ltype: Ltype, url: url}
    return render_single_Lfunction(Lfunction, args, request)


################################################################################
#   Helper functions, individual L-function homepages
################################################################################
def render_single_Lfunction(Lclass, args, request):
    temp_args = to_dict(request.args)
    logger.debug(args)
    logger.debug(temp_args)

    try:
        L = Lclass(**args)
        try:
            if temp_args['download'] == 'lcalcfile':
                return render_lcalcfile(L, request.url)
        except Exception as ex:
            pass  # Do nothing

    except Exception as ex:
        info = {'content': 'Sorry, there has been a problem: %s.' % ex.args[0], 'title': 'Error'}
        return render_template('LfunctionSimple.html', info=info, **info), 500

    info = initLfunction(L, temp_args, request)
    return render_template('Lfunction.html', **info)


# def render_single_Lfunction(L, request):
##    ''' Renders the homepage of the L-function object L.
##        If the argument download = 'lcalcfile' then a plain text file with
##        the lcalcfile of L is rendered.
##        Request should be the request of the page.
##    '''
##    args = request.args
##    temp_args = to_dict(args)
##    try:
##        if temp_args['download'] == 'lcalcfile':
##            return render_lcalcfile(L, request.url)
##    except:
##        pass #Do nothing
##
##    info = initLfunction(L, temp_args, request)
##    return render_template('Lfunction.html', **info)


def render_lcalcfile(L, url):
    ''' Function for rendering the lcalc file of an L-function.
    '''
    try:  # First check if the Lcalc file is stored in the database
        response = make_response(L.lcalcfile)
    except:
        response = make_response(L.createLcalcfile_ver2(url))

    response.headers['Content-type'] = 'text/plain'
    return response


def initLfunction(L, args, request):
    ''' Sets the properties to show on the homepage of an L-function page.
    '''

    info = {'title': L.title}
    try:
        info['citation'] = L.citation
    except AttributeError:
        info['citation'] = ""
    try:
        info['support'] = L.support
    except AttributeError:
        info['support'] = ""

    info['Ltype'] = L.Ltype()

    # Here we should decide which values are indeed special values
    # According to Brian, odd degree has special value at 1, and even
    # degree has special value at 1/2.
    # (however, I'm not sure this is true if L is not primitive -- GT)

    # Now we usually display both
    if L.Ltype() != "artin" or (L.Ltype() == "artin" and L.sign != 0):
    #    if is_even(L.degree) :
    #        info['sv12'] = specialValueString(L, 0.5, '1/2')
    #    if is_odd(L.degree):
    #        info['sv1'] = specialValueString(L, 1, '1')
        info['sv1'] = specialValueString(L, 1, '1')
        info['sv12'] = specialValueString(L, 0.5, '1/2')

    info['args'] = args

    info['credit'] = L.credit
    # info['citation'] = L.citation

    try:
        info['factorization'] = L.factorization
    except:
        pass

    try:
        info['url'] = L.url
    except:
        info['url'] = ''

    info['degree'] = int(L.degree)

    info['zeroeslink'] = (request.url.replace('/L/', '/zeroesLfunction/').
                          replace('/Lfunction/', '/zeroesLfunction/').
                          replace('/L-function/', '/zeroesLfunction/'))  # url_for('zeroesLfunction',  **args)

    info['plotlink'] = (request.url.replace('/L/', '/plotLfunction/').
                        replace('/Lfunction/', '/plotLfunction/').
                        replace('/L-function/', '/plotLfunction/'))  # info['plotlink'] = url_for('plotLfunction',  **args)

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
        else:
            info['bread'] = get_bread(L.degree,
                                      [('Maass Form', url_for('.l_function_maass_gln_browse_page',
                                        degree='degree' + str(L.degree))),
                                     (L.dbid, request.url)])

    elif L.Ltype() == 'riemann':
        info['bread'] = get_bread(1, [('Riemann Zeta', request.url)])
        info['friends'] = [('\(\mathbb Q\)', url_for('number_fields.by_label', label='1.1.1.1')), ('Dirichlet Character \(\\chi_{1}(1,\\cdot)\)',
                           url_for('render_Character', arg1=1, arg2=1))]

    elif L.Ltype() == 'dirichlet':
        info['navi'] = getPrevNextNavig(L.charactermodulus, L.characternumber, "L")
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        charname = '\(\\chi_{%s}({%s},\\cdot)\)' % (smod, snum)
        info['bread'] = get_bread(1, [(charname, request.url)])
        info['friends'] = [('Dirichlet Character ' + str(charname), friendlink)]

    elif L.Ltype() == 'ellipticcurve':
        label = L.label
        while friendlink[len(friendlink) - 1].isdigit():  # Remove any number at the end to get isogeny class url
            friendlink = friendlink[0:len(friendlink) - 1]

        info['friends'] = [('Isogeny class ' + label, friendlink)]
        for i in range(1, L.nr_of_curves_in_class + 1):
            info['friends'].append(('Elliptic curve ' + label + str(i), friendlink + str(i)))
        if L.modform:
            info['friends'].append(('Modular form ' + label.replace('.', '.2'), url_for("emf.render_elliptic_modular_forms",
                                                                                        level=L.modform['level'], weight=2, character=0, label=L.modform['iso'])))
            info['friends'].append(('L-function ' + label.replace('.', '.2'),
                                    url_for('.l_function_emf_page', level=L.modform['level'],
                                            weight=2, character=0, label=L.modform['iso'], number=0)))
        info['friends'].append(
            ('Symmetric square L-function', url_for(".l_function_ec_sym_page", power='2', label=label)))
        info['friends'].append(
            ('Symmetric cube L-function', url_for(".l_function_ec_sym_page", power='3', label=label)))
        info['bread'] = get_bread(2, [('Elliptic curve', url_for('.l_function_ec_browse_page')),
                                 (label, url_for('.l_function_ec_page', label=label))])

    elif L.Ltype() == 'ellipticmodularform':
        friendlink = friendlink + L.addToLink        # Strips off the embedding
        friendlink = friendlink.rpartition('/')[0]   # number for the L-function
        if L.character:
            info['friends'] = [('Modular form ' + str(
                L.level) + '.' + str(L.weight) + '.' + str(L.character) + str(L.label), friendlink)]
        else:
            info['friends'] = [('Modular form ' + str(L.level) + '.' + str(L.weight) + str(
                L.label), friendlink)]
        if L.ellipticcurve:
            info['friends'].append(
                ('EC isogeny class ' + L.ellipticcurve, url_for("by_ec_label", label=L.ellipticcurve)))
            info['friends'].append(('L-function ' + str(L.level) + '.' + str(L.label),
                                    url_for('.l_function_ec_page', label=L.ellipticcurve)))
            for i in range(1, L.nr_of_curves_in_class + 1):
                info['friends'].append(('Elliptic curve ' + L.ellipticcurve + str(i),
                                       url_for("by_ec_label", label=L.ellipticcurve + str(i))))
            info['friends'].append(
                ('Symmetric square L-function', url_for(".l_function_ec_sym_page", power='2', label=label)))
            info['friends'].append(
                ('Symmetric cube L-function', url_for(".l_function_ec_sym_page", power='3', label=label)))

    elif L.Ltype() == 'hilbertmodularform':
        friendlink = '/'.join(friendlink.split('/')[:-1])
        info['friends'] = [('Hilbert Modular Form', friendlink.rpartition('/')[0])]

    elif L.Ltype() == 'dedekindzeta':
        info['friends'] = [('Number Field', friendlink)]

    elif L.Ltype() in ['lcalcurl', 'lcalcfile']:
        info['bread'] = [('L-function', url_for('.l_function_top_page'))]

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
        weight = str(L.weight)
        number = str(L.number)
        info['friends'] = [('Siegel Modular Form', friendlink)]

    elif L.Ltype() == "artin":
        # info['zeroeslink'] = ''
        # info['plotlink'] = ''
        info['friends'] = [('Artin representation', L.artin.url_for())]
        if L.sign == 0:           # The root number is now unknown
            info['zeroeslink'] = ''
            info['plotlink'] = ''

    info['dirichlet'] = lfuncDStex(L, "analytic")
    info['eulerproduct'] = lfuncEPtex(L, "abstract")
    info['functionalequation'] = lfuncFEtex(L, "analytic")
    info['functionalequationSelberg'] = lfuncFEtex(L, "selberg")

    if len(request.args) == 0:
        lcalcUrl = request.url + '?download=lcalcfile'
    else:
        lcalcUrl = request.url + '&download=lcalcfile'

    info['downloads'] = [('Lcalcfile', lcalcUrl)]

    return info


def set_gaga_properties(L):
    ''' Sets the properties in the properties box in the
        upper right corner
    '''
    ans = [('Degree', str(L.degree))]

    ans.append(('Level', str(L.level)))
    ans.append(('Sign', styleTheSign(L.sign)))

    if L.selfdual:
        sd = 'Self-dual'
    else:
        sd = 'Not self-dual'
    ans.append((None, sd))

    if L.primitive:
        prim = 'Primitive'
    else:
        prim = 'Not primitive'
#    ans.append((None,        prim))    Disabled until fixed
#    ans.append((None,        prim))    Disabled until fixed

    return ans


################################################################################
#   Route functions, plotting L-function and displaying zeroes
################################################################################
@app.route("/plotLfunction/")
@app.route("/plotLfunction/<arg1>/")
@app.route("/plotLfunction/<arg1>/<arg2>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@app.route("/plotLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def plotLfunction(arg1=None, arg2=None, arg3=None, arg4=None, arg5=None, arg6=None, arg7=None, arg8=None, arg9=None):
    return render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)


@app.route("/zeroesLfunction/")
@app.route("/zeroesLfunction/<arg1>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@app.route("/zeroesLfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def zeroesLfunction(arg1=None, arg2=None, arg3=None, arg4=None, arg5=None, arg6=None, arg7=None, arg8=None, arg9=None):
    return render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)


################################################################################
#   Render functions, plotting L-function and displaying zeroes
################################################################################
def render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    data = plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
    if not data:
        # see note about missing "hardy_z_function" in plotLfunction()
        return flask.redirect(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response


def plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    pythonL = generateLfunctionFromUrl(
        arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))
    L = pythonL.sageLfunction
    # HSY: I got exceptions that "L.hardy_z_function" doesn't exist
    # SL: Reason, it's not in the distribution of Sage
    if not hasattr(L, "hardy_z_function"):
        return None
    # FIXME there could be a filename collission
    fn = tempfile.mktemp(suffix=".png")
    F = [(i, L.hardy_z_function(CC(.5, i)).real()) for i in srange(-30, 30, .1)]
    p = line(F)
    p.save(filename=fn)
    data = file(fn).read()
    os.remove(fn)
    return data


def render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    ''' Renders the first few zeroes of the L-function with the given arguments.
    '''
    L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))

    # Compute the first few zeros
    if L.degree > 2 or L.Ltype() == "maass":  # Too slow to be rigorous here  ( or L.Ltype()=="ellipticmodularform")
        search_step = 0.02
        if L.selfdual:
            allZeros = L.sageLfunction.find_zeros(-search_step / 2, 20, search_step)
        else:
            allZeros = L.sageLfunction.find_zeros(-15, 15, search_step)

    else:
        if L.selfdual:
            number_of_zeros = 6
        else:
            number_of_zeros = 8
        allZeros = L.sageLfunction.find_zeros_via_N(number_of_zeros, not L.selfdual)

    # Sort the zeros and divide them into negative and positive ones
    allZeros.sort()
    positiveZeros = []
    negativeZeros = []

    for zero in allZeros:
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


def generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, temp_args):
    ''' Returns the L-function object corresponding to the supplied argumnents
        from the url. temp_args contains possible arguments after a question mark.
    '''
    if arg1 == 'Riemann':
        return RiemannZeta()

    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        return Lfunction_Dirichlet(charactermodulus=arg3, characternumber=arg4)

    elif arg1 == 'EllipticCurve' and arg2 == 'Q':
        return Lfunction_EC(label=arg3)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic':  # this has args: one for weight and one for level
        # logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_EMF(level=arg5, weight=arg6, character=arg7, label=arg8, number=arg9)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 != 'Q' and arg4 == 'holomorphic':  # Hilbert modular form
        # logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_HMF(field=arg3, label=arg5, character=arg6, number=arg7)

    elif arg1 == 'ModularForm' and arg2 == 'GL2'and arg3 == 'Q' and arg4 == 'Maass':
        # logger.debug(db)
        return Lfunction_Maass(dbid=bson.objectid.ObjectId(arg5))

    elif arg1 == 'ModularForm' and (arg2 == 'GSp4' or arg2 == 'GL4' or arg2 == 'GL3') and arg3 == 'Q' and arg4 == 'Maass':
        # logger.debug(db)
        return Lfunction_Maass(dbid=arg5, dbName='Lfunction', dbColl='LemurellMaassHighDegree')

    elif arg1 == 'ModularForm' and arg2 == 'GSp' and arg3 == 'Q' and arg4 == 'Sp4Z' and arg5 == 'specimen':  # this should be changed when we fix the SMF urls
        return Lfunction_SMF2_scalar_valued(weight=arg6, orbit=arg7, number=arg8)

    elif arg1 == 'NumberField':
        return DedekindZeta(label=str(arg2))

    elif arg1 == "ArtinRepresentation":
        return ArtinLfunction(dimension=arg2, conductor=arg3, tim_index=arg4)

    elif arg1 == "SymmetricPower":
        return SymmetricPowerLfunction(power=arg2, underlying_type=arg3, field=arg4, label=arg5)

    elif arg1 == 'Lcalcurl':
        return Lfunction(Ltype=arg1, url=arg2)

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
        data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level'])]])
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

    iso_list = LfunctionComp.isogenyclasstable(N, end)
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


def processMaassNavigation(numrecs=10):
    """
    Produces a table of numrecs Maassforms with Fourier coefficients in the database
    """
    host = base.getDBConnection().host
    port = base.getDBConnection().port
    DB = MaassDB(host=host, port=port)
    s = '<h5>Examples of L-functions attached to Maass forms on Hecke congruence groups $\Gamma_0(N)$</h5>'
    s += '<table>\n'
    i = 0
    maxinlevel = 5
    for level in [3, 5, 7, 10]:
        j = 0
        s += '<tr>\n'
        s += '<td><bold>N={0}:</bold></td>\n'.format(level)
        finds = DB.get_Maass_forms({'Level': int(level), 'Character': int(0)})
        for f in finds:
            nc = f.get('Numc', 0)
            if nc <= 0:
                continue
            R = f.get('Eigenvalue', 0)
            if R == 0:
                continue
            Rst = str(R)[0:min(12, len(str(R)))]
            idd = f.get('_id', None)
            if idd is None:
                continue
            idd = str(idd)
            url = url_for('.l_function_maass_page', dbid=idd)
            s += '<td><a href="{0}">{1}</a>'.format(url, Rst)
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

    iso_list = LfunctionComp.isogenyclasstable(N, end)
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
