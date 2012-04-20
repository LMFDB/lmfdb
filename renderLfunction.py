# -*- coding: utf-8 -*-
from base import *
from flask import Flask, session, g, render_template, url_for, request, make_response, abort
import flask

from sage.all import *
import tempfile, os
import pymongo
from Lfunction import *
import LfunctionComp
import LfunctionPlot
from utils import to_dict
import bson
from Lfunctionutilities import lfuncDStex, lfuncEPtex, lfuncFEtex, truncatenumber

#logger = make_logger("LF")

##import upload2Db.py


###########################################################################
#   Route functions
###########################################################################

#@app.route("/L/EllipticCurve/Q/<label>")
def return_ECLfunction(label):
    logger.debug(label)
    from elliptic_curve import cremona_label_regex, lmfdb_label_regex
    m = lmfdb_label_regex.match(label)
    if m is not None:
        if m.groups()[2]:
            # strip off the curve number
            return flask.redirect("/L/EllipticCurve/Q/%s"%label[:-1], 301)
        else:
            return render_webpage(request,'EllipticCurve','Q',label,None,None,None,None,None,None)
    m = cremona_label_regex.match(label)
    if m is not None:
        if m.groups()[2]:
            C = getDBConnection().elliptic_curves.curves.find_one({'label':label})
        else:
            C = getDBConnection().elliptic_curves.curves.find_one({'iso':label})
        return flask.redirect("/L/EllipticCurve/Q/%s"%(C['lmfdb_iso']), 301)

@app.route("/L/")
@app.route("/L/<arg1>/") # arg1 is EllipticCurve, ModularForm, Character, etc
@app.route("/L/<arg1>/<arg2>/") # arg2 is field
@app.route("/L/<arg1>/<arg2>/<arg3>/") #arg3 is label
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@app.route("/L/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def render_Lfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None, arg6 = None, arg7 = None, arg8 = None, arg9 = None):
    #logger.debug("in render_L with args:{0}".format((arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9)))
    if arg1 == 'EllipticCurve' and arg2 == 'Q':
        return return_ECLfunction(arg3)
    return render_webpage(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)

@app.route("/Lfunction/")
@app.route("/Lfunction/<arg1>/")
@app.route("/Lfunction/<arg1>/<arg2>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@app.route("/Lfunction/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
@app.route("/L-function/")
@app.route("/L-function/<arg1>/")
@app.route("/L-function/<arg1>/<arg2>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/")
@app.route("/L-function/<arg1>/<arg2>/<arg3>/<arg4>/<arg5>/<arg6>/<arg7>/<arg8>/<arg9>/")
def render_Lfunction_redirect(**args):
    args.update(request.args)
    return flask.redirect(url_for("render_Lfunction", **args), code=301)

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
def plotLfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None, arg6 = None, arg7 = None, arg8 = None, arg9 = None):
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
def zeroesLfunction(arg1 = None, arg2 = None, arg3 = None, arg4 = None, arg5 = None, arg6 = None, arg7 = None, arg8 = None, arg9 = None):
    return render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)

@app.route("/browseGraph/")
def browseGraph():
    return render_browseGraph(request.args)

@app.route("/browseGraphTMP/")
def browseGraphTMP():
    return render_browseGraphTMP(request.args)

@app.route("/browseGraphHolo/")
def browseGraphHolo():
    return render_browseGraphHolo(request.args)

@app.route("/browseGraphChar/")
def browseGraphChar():
    return render_browseGraphChar(request.args)


###########################################################################
#   Functions for rendering the L-function web pages including, both browsing
#   and individual home pages.
###########################################################################

def render_webpage(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    args = request.args
    temp_args = to_dict(args)

    if len(args) == 0:  #This ensures it's a navigation page 
        if not arg1: # this means we're at the start page
            info = set_info_for_start_page()
            return render_template("LfunctionNavigate.html", **info)

        elif arg1.startswith("degree"):
            degree = int(arg1[6:])
            if not arg2:
                info = { "degree" : degree }
                info["key"] = 777
                info["bread"] =  [('L-functions', url_for("render_Lfunction")),
                                  ('Degree '+str(degree), url_for('render_Lfunction', arg1='degree' + str(degree)))]
                    
                return render_template("lfunctions/DegreeNavigateL.html", title = 'Degree ' + str(degree)+ ' L-functions', **info)
            
            else:
                info = {}
                info["bread"] =  [('L-functions', url_for("render_Lfunction")),
                                  ('Degree '+str(degree), url_for('render_Lfunction',
                                                                  arg1='degree' + str(degree))),
                                  (arg2, url_for('render_Lfunction', arg1='degree' + str(degree), arg2=arg2, arg3=arg3))]
                if degree == 1:
                    if arg2 == 'Dirichlet':
                        info["minModDefault"] = 1
                        info["maxModDefault"] = 20
                        info["maxOrder"] = 14
                        info["contents"] = [LfunctionPlot.getOneGraphHtmlChar(info["minModDefault"],info["maxModDefault"],1,info["maxOrder"])]
                        return render_template("lfunctions/Dirichlet.html", title = 'Dirichlet L-functions', **info)
                elif degree == 2:
                    if arg2 == 'CuspForm':
                        info["contents"] = [LfunctionPlot.getOneGraphHtmlHolo(1, 6, 2, 14)]
                        return render_template("lfunctions/cuspformGL2.html", title = 'L-functions of GL(2) Cusp Forms', **info)
                    elif arg2 == 'MaassForm':
                        info["contents"] = [processMaassNavigation()]
                        return render_template("lfunctions/MaassformGL2.html", title = 'L-functions of GL(2) Maass Forms', **info)
                    elif arg2 == 'EllipticCurve':
                        info["representation"] = ''
                        info["contents"] = [processEllipticCurveNavigation(11,65)]
                        return render_template("lfunctions/ellipticcurve.html", title = 'L-functions of Elliptic Curves', **info)
                elif degree == 3:
                    if arg2 == 'MaassForm':
                        info["contents"] = LfunctionPlot.getAllMaassGraphHtml(3)
                        return render_template("lfunctions/MaassformGLn.html", title = 'L-functions of GL(3) Maass Forms', **info)
                    elif arg2 == 'EllipticCurve':
                        info["representation"] = 'Symmetric square'
                        info["contents"] = [processSymPowerEllipticCurveNavigation(11,65,2)]
                        return render_template("lfunctions/ellipticcurve.html", title = 'Symmetric square of L-functions of Elliptic Curves', **info)
                elif degree == 4:
                    if arg2 == 'MaassForm':
                        info["contents"] = LfunctionPlot.getAllMaassGraphHtml(4)
                        return render_template("lfunctions/MaassformGLn.html", title = 'L-functions of GL(4) Maass Forms', **info)
                    elif arg2 == 'EllipticCurve':
                        info["representation"] = 'Symmetric cube'
                        info["contents"] = [processSymPowerEllipticCurveNavigation(11,65,3)]
                        return render_template("lfunctions/ellipticcurve.html", title = 'Symmetric cube of L-functions of Elliptic Curves', **info)
                       
        elif arg1 == 'custom': # need a better name
            return "not yet implemented"

    try:
      L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, temp_args)
    except Exception as e:
      # throw exception if not UserError
      if len(e.args) > 1 and e.args[1] != 'UserError': raise
      info = { 'content': 'Sorry, there has been a problem: %s .         Please report it <a href="http://code.google.com/p/lmfdb/issues/list">here</a>.' % e.args[0], 'title': 'Error' }
      return render_template('LfunctionSimple.html', info=info, **info), 500

    try:
        #logger.debug(temp_args)
        if temp_args['download'] == 'lcalcfile':
            return render_lcalcfile(L, request.url)
    except:
        pass #Do nothing


    info = initLfunction(L, temp_args, request)

    return render_template('Lfunction.html', **info)


def generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, temp_args):
    ''' Returns the L-function object corresponding to the supplied argumnents
        from the url. temp_args contains possible arguments after a question mark.
    '''

    if (arg1 == 'Riemann' or (arg1 == 'Character' and arg2 == 'Dirichlet' and arg3 == '1' and arg4 == '0')
        or (arg1 == 'NumberField' and arg2 == '1.1.1.1')):
        return RiemannZeta()

    elif arg1 == 'Character' and arg2 == 'Dirichlet':
        return Lfunction_Dirichlet( charactermodulus = arg3, characternumber = arg4)

    elif arg1 == 'EllipticCurve' and arg2 == 'Q':
        return Lfunction_EC( label = arg3)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 == 'Q' and arg4 == 'holomorphic': # this has args: one for weight and one for level
        #logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_EMF( level = arg5, weight = arg6, character = arg7, label = arg8, number = arg9)

    elif arg1 == 'ModularForm' and arg2 == 'GL2' and arg3 <> 'Q' and arg4 == 'holomorphic': # Hilbert modular form
        #logger.debug(arg5+arg6+str(arg7)+str(arg8)+str(arg9))
        return Lfunction_HMF( field = arg3, label = arg5, character = arg6, number = arg7)

    elif arg1 == 'ModularForm' and arg2 == 'GL2'and arg3 == 'Q' and arg4 == 'Maass':
        #logger.debug(db)
        return Lfunction_Maass(dbid = bson.objectid.ObjectId(arg5))

    elif arg1 == 'ModularForm' and (arg2 == 'GSp4' or arg2 == 'GL4' or  arg2 == 'GL3') and arg3 == 'Q' and arg4 == 'maass':
        return Lfunction_Maass( dbid = arg5, dbName = 'Lfunction', dbColl = 'LemurellMaassHighDegree')

    elif arg1 == 'ModularForm' and arg2 == 'GSp' and arg3 == 'Q' and arg4 == 'Sp4Z' and arg5== 'specimen': #this should be changed when we fix the SMF urls
        return Lfunction_SMF2_scalar_valued( weight=arg6, orbit=arg7, number=arg8 )

    elif arg1 == 'NumberField':
        return DedekindZeta( label = str(arg2))

    elif arg1 == "ArtinRepresentation":
        return ArtinLfunction(dimension = arg2, conductor = arg3, tim_index = arg4)

    elif arg1 == "SymmetricPower":
        return SymmetricPowerLfunction(arg2, [arg3, arg4, arg5, arg6, arg7, arg8, arg9], temp_args)

    elif arg1 == 'Lcalcurl':
        return Lfunction( Ltype = arg1, url = arg2)

    else:
        return flask.redirect(403)


def set_info_for_start_page():
    ''' Sets the properties of the top L-function page.
    '''

    tt = [[{'title':'Riemann zeta function','link': url_for('render_Lfunction', arg1='Riemann')},
           {'title':'Dirichlet L-function','link': url_for('render_Lfunction', arg1='degree1', arg2='Dirichlet')}],

          [{'title':'GL2 Cusp form', 'link': url_for('render_Lfunction', arg1='degree2', arg2='CuspForm')},
           {'title':'GL2 Maass form','link': url_for('render_Lfunction', arg1='degree2', arg2='MaassForm')},
           {'title':'Elliptic curve','link': url_for('render_Lfunction', arg1='degree2', arg2='EllipticCurve')}],

          [ {'title':'', 'link': ''},
            {'title':'GL3 Maass form', 'link': url_for('render_Lfunction', arg1='degree3', arg2='MaassForm')},
            {'title':'Symmetric square L-function of Elliptic curve','link': url_for('render_Lfunction', arg1='degree3', arg2='EllipticCurve', arg3='Symmetric square')}],
          
          [{'title':'GSp4 Maass form', 'link': url_for('render_Lfunction', arg1='degree4', arg2='MaassForm') + '#GSp4_Q_Maass'},
           {'title':'GL4 Maass form', 'link': url_for('render_Lfunction', arg1='degree4', arg2='MaassForm')},
           {'title':'Symmetric cube L-function of Elliptic curve','link': url_for('render_Lfunction', arg1='degree4', arg2='EllipticCurve', arg3='Symmetric square')}]]
          


    info = {
        'degree_list': range(1,5),
        'type_table': tt,
        'type_row_list':[0,1,2,3]
    }

    info['title'] = 'L-functions'
    info['bread'] = [('L-functions', url_for("render_Lfunction"))]

    return info


def initLfunction(L,args, request):
    ''' Sets the properties to show on the homepage of an L-function page.
    '''

    info = {'title': L.title}
    info['citation'] = ''
    info['support'] = ''
    # Here we should decide which values are indeed special values
    # According to Brian, odd degree has special value at 1, and even
    # degree has special value at 1/2.
    # (however, I'm not sure this is true if L is not primitive -- GT)
    if is_even(L.degree):
        info['sv12'] = specialValueString(L, 0.5, '1/2')
    if is_odd(L.degree):
        info['sv1'] = specialValueString(L, 1, '1')
    info['args'] = args
    info['Ltype'] = L.Ltype()


    info['credit'] = L.credit
    #info['citation'] = L.citation

    try:
        info['url'] = L.url
    except:
        info['url'] =''

    info['degree'] = int(L.degree)

    info['zeroeslink'] = (request.url.replace('/L/', '/zeroesLfunction/').
                          replace('/Lfunction/', '/zeroesLfunction/').
                          replace('/L-function/', '/zeroesLfunction/') ) #url_for('zeroesLfunction',  **args)

    info['plotlink'] = (request.url.replace('/L/', '/plotLfunction/').
                          replace('/Lfunction/', '/plotLfunction/').
                          replace('/L-function/', '/plotLfunction/') ) #info['plotlink'] = url_for('plotLfunction',  **args)

    info['bread'] = []
    info['properties2'] = set_gaga_properties(L)


    # Create friendlink by removing 'L/' and ending '/'
    friendlink = request.url.replace('/L/','/').replace('/L-function/','/').replace('/Lfunction/','/')
    splitlink = friendlink.rpartition('/')
    friendlink = splitlink[0] + splitlink[2]
    logger.debug(L.Ltype())

    if L.Ltype() == 'maass':
        if L.group == 'GL2':
            minNumberOfCoefficients = 100     # TODO: Fix this to take level into account
                            
            if len(L.dirichlet_coefficients)< minNumberOfCoefficients:
                info['zeroeslink'] = ''
                info['plotlink'] = ''
            info['bread'] = [('L-function','/L') ,('Degree 2',
                              url_for('render_Lfunction', arg1='degree2')),
                             ('\('+L.texname+'\)', request.url )]
            info['friends'] = [('Maass Form ', friendlink)]
        else:
            info['bread'] = [('L-function','/L') ,('Degree ' + str(L.degree),
                             url_for('render_Lfunction', arg1= str(L.degree))), (L.dbid, request.url)]

    elif L.Ltype()  == 'riemann':
        info['bread'] = [('L-function','/L'),('Riemann Zeta',request.url)]
        info['friends'] = [('\(\mathbb Q\)', url_for('number_fields.by_label', label='1.1.1.1')),  ('Dirichlet Character \(\\chi_{1}(0,\\cdot)\)',
                                                                       url_for('render_Character', arg1=1, arg2=0))]

    elif L.Ltype()  == 'dirichlet':
        snum = str(L.characternumber)
        smod = str(L.charactermodulus)
        charname = '\(\\chi_{%s}({%s},\\cdot)\)' %(smod, snum)
        info['bread'] = [('L-function','/L'),('Dirichlet Characters',url_for('render_Lfunction', arg1='degree1') +'Dirichlet'),
                         (charname, request.url)]
        info['friends'] = [('Dirichlet Character '+str(charname), friendlink)]


    elif L.Ltype()  == 'ellipticcurve':
        label = L.label
        while friendlink[len(friendlink)-1].isdigit():  #Remove any number at the end to get isogeny class url
            friendlink = friendlink[0:len(friendlink)-1]

        info['friends'] = [('Isogeny class ' + label, friendlink )]
        for i in range(1, L.nr_of_curves_in_class + 1):
            info['friends'].append(('Elliptic curve ' + label + str(i), friendlink + str(i)))
        if L.modform:
            info['friends'].append(('Modular form ' + label.replace('.','.2'), url_for("emf.render_elliptic_modular_forms",
                                                            level=L.modform['level'],weight=2,character=0,label=L.modform['iso'])))
            info['friends'].append(('L-function ' + label.replace('.','.2'), url_for("render_Lfunction", arg1='ModularForm', arg2='GL2', arg3='Q', arg4='holomorphic', arg5=L.modform['level'], arg6='2', arg7='0', arg8=L.modform['iso'])))
        info['friends'].append(('Symmetric square L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='2',arg3='EllipticCurve', arg4='Q', arg5=label)))
        info['friends'].append(('Symmetric 4th power L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='4',arg3='EllipticCurve', arg4='Q', arg5=label)))
        info['bread'] = [('L-function','/L'),('Elliptic curve',url_for('render_Lfunction', arg1='/L/degree2#EllipticCurve_Q')),
                         (label,url_for('render_Lfunction',arg1='EllipticCurve',arg2='Q',arg3= label))]

    elif L.Ltype() == 'ellipticmodularform':
        friendlink = friendlink + L.addToLink        # Strips off the embedding
        friendlink = friendlink.rpartition('/')[0]   # number for the L-function
        if L.character:
            info['friends'] = [('Modular form ' + str(L.level) + '.' + str(L.weight) + '.' + str(L.character) + str(L.label), friendlink)]
        else:
            info['friends'] = [('Modular form ' + str(L.level) + '.' + str(L.weight) + str(L.label), friendlink)]
        if L.ellipticcurve:
            info['friends'].append(('EC isogeny class ' + L.ellipticcurve, url_for("by_ec_label",label=L.ellipticcurve)))
            info['friends'].append(('L-function ' + str(L.level) + '.' + str(L.label), url_for("render_Lfunction", arg1='EllipticCurve', arg2='Q', arg3=L.ellipticcurve)))
            for i in range(1, L.nr_of_curves_in_class + 1):
                info['friends'].append(('Elliptic curve ' + L.ellipticcurve + str(i), url_for("by_ec_label",label=L.ellipticcurve + str(i))))
            info['friends'].append(('Symmetric square L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='2',arg3='EllipticCurve', arg4='Q', arg5=L.ellipticcurve)))
            info['friends'].append(('Symmetric 4th power L-function', url_for("render_Lfunction", arg1='SymmetricPower', arg2='4',arg3='EllipticCurve', arg4='Q', arg5=L.ellipticcurve)))

    elif L.Ltype() == 'hilbertmodularform':
        friendlink = '/'.join(friendlink.split('/')[:-1])
        info['friends'] = [('Hilbert Modular Form', friendlink.rpartition('/')[0])] 

    elif L.Ltype() == 'dedekindzeta':
        info['friends'] = [('Number Field', friendlink)]

    elif L.Ltype() in ['lcalcurl', 'lcalcfile']:
        info['bread'] = [('L-function',url_for('render_Lfunction'))]
        
    elif L.Ltype() == 'SymmetricPower':
        def ordinal(n):
            if n == 2:
                return "Square"
            elif n == 3:
                return "Cube"
            elif 10 <= n % 100 < 20:
                return str(n) + "th Power"
            else:
                return  str(n) + {1 : 'st', 2 : 'nd', 3 : 'rd'}.get(n % 10, "th") + " Power"
        friendlink =request.url.replace('/L/SymmetricPower/%d/'%L.m,'/')
        splitlink=friendlink.rpartition('/')
        friendlink = splitlink[0]+splitlink[2]

        friendlink2 =request.url.replace('/L/SymmetricPower/%d/'%L.m,'/L/')
        splitlink=friendlink2.rpartition('/')
        friendlink2 = splitlink[0]+splitlink[2]

        mplusone = L.m +1
        friendlink3 =request.url.replace('/L/SymmetricPower/%d/'%L.m,'/L/SymmetricPower/%d/'%mplusone)

        info['friends'] = [('Isogeny class '+L.label, friendlink), ('Symmetric 1st Power', friendlink2), ('Symmetric %s'%ordinal(mplusone) , friendlink3)]

    elif L.Ltype() == 'siegelnonlift' or L.Ltype() == 'siegeleisenstein' or L.Ltype() == 'siegelklingeneisenstein' or L.Ltype() == 'siegelmaasslift':
        weight = str(L.weight)
        number = str(L.number)
        info['friends'] = [('Siegel Modular Form', friendlink)]




    info['dirichlet'] = lfuncDStex(L, "analytic")
    info['eulerproduct'] = lfuncEPtex(L, "abstract")
    info['functionalequation'] = lfuncFEtex(L, "analytic")
    info['functionalequationSelberg'] = lfuncFEtex(L, "selberg")

    info['learnmore'] = [('L-functions', 'http://wiki.l-functions.org/L-functions') ]
    
    if len(request.args)==0:
        lcalcUrl = request.url + '?download=lcalcfile'
    else:
        lcalcUrl = request.url + '&download=lcalcfile'
        
    info['downloads'] = [('Lcalcfile', lcalcUrl) ]
    
    return info


def set_gaga_properties(L):
    ''' Sets the properties in the properties box in the
        upper right corner
    '''
    ans = [ ('Degree',    str(L.degree))]

    ans.append(('Level',     str(L.level)))
    ans.append(('Sign',      styleTheSign(L.sign)))

    if L.selfdual:
        sd = 'Self-dual'
    else:
        sd = 'Not self-dual'
    ans.append((None,        sd))

    if L.primitive:
        prim = 'Primitive'
    else:
        prim = 'Not primitive'
#    ans.append((None,        prim))    Disabled until fixed
#    ans.append((None,        prim))    Disabled until fixed

    return ans

def styleTheSign(sign):
    ''' Returns the string to display as sign
    '''
    try:
        logger.debug(1-sign)
        if abs(1-sign) < 1e-10:
            return '1'
        elif abs(1+sign) < 1e-10:
            return '-1'
        elif abs(1-sign.imag()) < 1e-10:
            return 'i'
        elif abs(1+sign.imag()) < 1e-10:
            return '-i'
        elif sign.imag > 0:
            return "${0} + {1}i$".format(truncatenumber(sign.real(), 5),truncatenumber(sign.imag(), 5))
        else:
            return "${0} {1}i$".format(truncatenumber(sign.real(), 5),truncatenumber(sign.imag(), 5))
    except:
        logger.debug("no styling of sign")
        return str(sign)


def specialValueString(L, s, sLatex):
    ''' Returns the LaTex to dislpay for L(s) 
    '''
    
    number_of_decimals = 10
    val = L.sageLfunction.value(s)
    lfunction_value_tex = L.texname.replace('(s', '(' + sLatex)
    # We must test for NaN first, since it would show as zero otherwise
    # Try "RR(NaN) < float(1e-10)" in sage -- GT
    if val.real().is_NaN():
        return "\\[{0}=\\infty\\]".format(lfunction_value_tex)
    elif val.abs() < 1e-10:
        return "\\[{0}=0\\]".format(lfunction_value_tex)
    else:
        return "\\[{0} \\approx {1}\\]".format(lfunction_value_tex,
            latex( round(val.real(), number_of_decimals)
                 + round(val.imag(), number_of_decimals)*I ))


###########################################################################
#   Functions for rendering the plot of an L-function.
###########################################################################

def plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    pythonL = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))
    L = pythonL.sageLfunction
    # HSY: I got exceptions that "L.hardy_z_function" doesn't exist
    # SL: Reason, it's not in the distribution of Sage
    if not hasattr(L, "hardy_z_function"):
      return None
    #FIXME there could be a filename collission
    fn = tempfile.mktemp(suffix=".png")
    F=[(i,L.hardy_z_function(CC(.5,i)).real()) for i in srange(-30,30,.1)]
    p = line(F)
    p.save(filename = fn)
    data = file(fn).read()
    os.remove(fn)
    return data

def render_plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    data = plotLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9)
    if not data:
        # see note about missing "hardy_z_function" in plotLfunction()
        return flask.redirect(404)
    response = make_response(data)
    response.headers['Content-type'] = 'image/png'
    return response

###########################################################################
#   Functions for rendering a few of the zeros of an L-function.
###########################################################################
def render_zeroesLfunction(request, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9):
    L = generateLfunctionFromUrl(arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, to_dict(request.args))

    # Compute the first few zeros
    if L.degree > 2 or L.Ltype()=="maass":  # Too slow to be rigorous here  ( or L.Ltype()=="ellipticmodularform")
        search_step = 0.02
        if L.selfdual:
            allZeros = L.sageLfunction.find_zeros(-search_step/2 , 20 ,search_step)
        else:
            allZeros = L.sageLfunction.find_zeros(-15,15,search_step)

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
        if zero.abs()< 1e-10:
            zero = 0
        if zero < 0:
            negativeZeros.append(zero)
        else:
            positiveZeros.append(zero)

    #Format the html string to render 
    positiveZeros = str(positiveZeros)
    negativeZeros = str(negativeZeros)
    if len(positiveZeros) > 2 and len(negativeZeros) > 2:  # Add comma and empty space between negative and positive
        negativeZeros = negativeZeros.replace("]", ", ]")
    
    return "<span class='redhighlight'>{0}</span><span class='bluehighlight'>{1}</span>".format(
        negativeZeros[1:len(negativeZeros)-1], positiveZeros[1:len(positiveZeros)-1])


###########################################################################
#   Functions for rendering graphs for browsing L-functions.
###########################################################################
def render_browseGraph(args):
    #logger.debug(args)
    if 'sign' in args:
      data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level']), args['sign']]])
    else:
      data = LfunctionPlot.paintSvgFileAll([[args['group'], int(args['level'])]])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

def render_browseGraphHolo(args):
    #logger.debug(args)
    data = LfunctionPlot.paintSvgHolo(args['Nmin'], args['Nmax'], args['kmin'], args['kmax'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

def render_browseGraphTMP(args):
    #logger.debug(args)
    data = LfunctionPlot.paintSvgHoloGeneral(args['Nmin'], args['Nmax'], args['kmin'], args['kmax'],args['imagewidth'], args['imageheight'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

def render_browseGraphChar(args):
    #logger.debug(args)
    data = LfunctionPlot.paintSvgChar(args['min_cond'], args['max_cond'], args['min_order'], args['max_order'])
    response = make_response(data)
    response.headers['Content-type'] = 'image/svg+xml'
    return response

###########################################################################
#   Function for rendering the lcalc file of an L-function.
###########################################################################
def render_lcalcfile(L, url):
    try:  #First check if the Lcalc file is stored in the database
        response = make_response(L.lcalcfile)
    except:
        response = make_response(L.createLcalcfile_ver2(url))

    response.headers['Content-type'] = 'text/plain'
    return response


###########################################################################
#   A demo for showing metadata of the collections in the database.
###########################################################################
def render_showcollections_demo():
    connection = pymongo.Connection()
    dbNames = connection.database_names()
    dbList = []
    for dbName in dbNames:
        db = pymongo.database.Database(connection, dbName)
        dbMeta = connection.Metadata
        collectionNames = db.collection_names()
        collList = []
        for collName in collectionNames:
            if not collName == 'system.indexes': 
                collMeta = pymongo.collection.Collection(dbMeta,'collection_data')
                infoMeta = collMeta.find_one({'db': dbName, 'collection': collName})
                try:
                    info = infoMeta['description']
                except:
                    info = ''
                collList.append( (collName, info) )
        dbList.append( (str(db.name), collList) )
    info = {'collections' : dbList}
    return render_template("ShowCollectionDemo.html", info = info)



###########################################################################
#   Functions for displaying examples of degree 2 L-functions on the
#   degree browsing page.
###########################################################################
def processEllipticCurveNavigation(startCond, endCond):
    try:
        N = startCond
        if N < 11:
            N=11
        elif N > 100:
            N=100
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
        if counter==0:
            s += '<tr>'
            
        counter += 1
        s += '<td><a href="' + url_for('render_Lfunction', arg1='EllipticCurve', arg2='Q', arg3=label)+ '">%s</a></td>\n' % label
            
        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter>0:
        s += '</tr>\n'
        
    s += '</table>\n'
    return s

## Old version. I added the version below with tests for existence 
def processMaassNavigation_old():
    s = '<h5>Examples of L-functions attached to Maass forms on Hecke congruence groups $\Gamma_0(N)$</h5>'
    s += '<table>\n'

    s += '<tr>\n'
    s += '<td><bold>N=3:</bold></td>\n'
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00002a')+ '">4.38805356322</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00002b')+ '">5.09874190873</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00002c')+ '">6.12057553309</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00002d')+ '">6.75741527775</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00002e')+ '">7.75813319502</a></td>\n' 
    s += '</tr>\n'
    
    s += '<tr>\n'
    s += '<td><bold>N=5:</bold></td>\n'
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c000036')+ '">3.02837629307</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c000039')+ '">4.89723501573</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00003b')+ '">5.70582652719</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00003c')+ '">6.05402838077</a></td>\n' 
    s += '<td><a href="' + url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q',
                                   arg4='Maass', arg5='4cb8502658bca9141c00003d')+ '">6.45847643848</a></td>\n' 
    s += '</tr>\n'
    
    s += '</table>\n'

    return s


def processMaassNavigation(numrecs=10):
    r"""
    Produces a table of numrecs Maassforms with Fourier coefficients in the database
    """
    host  = base.getDBConnection().host
    port  = base.getDBConnection().port
    DB=MaassDB(host=host,port=port)
    s = '<h5>Examples of L-functions attached to Maass forms on Hecke congruence groups $\Gamma_0(N)$</h5>'
    s += '<table>\n'
    i=0
    maxinlevel=5
    for level in [3,5,7,10]:
        j=0
        s += '<tr>\n'
        s += '<td><bold>N={0}:</bold></td>\n'.format(level)
        finds= DB.get_Maass_forms({'Level':int(level),'Character':int(0)})
        for f in finds:
            nc = f.get('Numc',0)
            if nc<=0:
                continue
            R = f.get('Eigenvalue',0)
            if R==0:
                continue
            Rst=str(R)[0:min(12,len(str(R)))]
            idd = f.get('_id',None)
            if idd==None:
                continue
            idd=str(idd)
            url =  url_for('render_Lfunction', arg1='ModularForm', arg2='GL2', arg3='Q', arg4='Maass', arg5=idd)
            s += '<td><a href="{0}">{1}</a>'.format(url,Rst)
            i+=1;j+=1
            if i>=numrecs or j>=maxinlevel:
                break
        s += '</tr>\n'
        if i>numrecs:
            break        
    s += '</table>\n'

    return s

def processSymPowerEllipticCurveNavigation(startCond, endCond,power):
    try:
        N = startCond
        if N < 11:
            N=11
        elif N > 100:
            N=100
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
                
    s = '<h5>Examples of symmetric ' + powerName + ' L-functions attached to isogeny classes of elliptic curves</h5>'
    s += '<table>'
    
    logger.debug(iso_list)

    counter = 0
    nr_of_columns = 10
    for label in iso_list:
        if counter==0:
            s += '<tr>'
            
        counter += 1
        s += '<td><a href="' + url_for('render_Lfunction', arg1 = 'SymmetricPower', arg2='%d'%power, arg3='EllipticCurve', arg4='Q', arg5=label)+ '">%s</a></td>\n' % label
            
        if counter == nr_of_columns:
            s += '</tr>\n'
            counter = 0

    if counter>0:
        s += '</tr>\n'
        
    s += '</table>\n'
    return s

