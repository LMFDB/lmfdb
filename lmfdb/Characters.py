# -*- coding: utf-8 -*-
# Characters.py

import re

from base import app, r
import flask
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import *
import tempfile
import os
from pymongo import ASCENDING
from utils import to_dict, parse_range, make_logger
from WebCharacter import *
import ListCharacters

try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")


logger = make_logger("HC")

###############################################################################
#   Route functions
###############################################################################

## generic

@app.route("/Character/")
@app.route("/Character/<type>")
@app.route("/Character/<type>/<arg1>")
@app.route("/Character/<type>/<arg1>/<arg2>")
@app.route("/Character/<type>/<arg1>/<arg2>/<arg3>")
def render_Character(type=None, arg1=None, arg2=None, arg3=None):
    render_charwebpage(request, type, arg1, arg2, arg3)

@app.route("/Character/<type>/<modulus>/<number>")
@app.route("/Character/<type>/<number_field>/<modulus>/<number>")
def render_charwebpage(request, type, number_field, modulus, number):
    if type=='Dirichlet':
        render_Dirichletwebpage(request, modulus, number)
    elif type=='Hecke':
        render_Heckewebpage(request, number_field, modulus, number)

@app.route("/Character/<type>/calc-<calc>/<modulus>/<number>")
@app.route("/Character/<type>/calc-<calc>/<number_field>/<modulus>/<number>")
def char_calc(request, type, calc, number_field, modulus, number):
    if type=='Dirichlet':
        dc_calc(request, calc, modulus, number)
    elif type=='Hecke':
        hc_calc(request, calc, number_field, modulus, number)

@app.route("/Character/Dirichlet/")
@app.route("/Character/Dirichlet/<arg1>")
@app.route("/Character/Dirichlet/<arg1>/<arg2>")
def render_DirichletCharacter(arg1=None, arg2=None):
    return render_Dirichletwebpage(request, arg1, arg2)

@app.route("/Character/Dirichlet/<modulus>/<number>")
def render_Dirichletwebpage(request, modulus, number):
    args = request.args
    temp_args = to_dict(args)

    temp_args['type'] = 'Dirichlet'
    temp_args['modulus'] = modulus
    temp_args['number'] = number

    if modulus == None:
        info = WebDirichlet(temp_args).to_dict()
        return render_template('dirichlet_characters/Dirichlet.html', **info)
    elif number == None:
        info = WebDirichletGroup(temp_args).to_dict()
        print info
        return render_template('dirichlet_characters/CharGroup.html', **info)
    else:
        info = WebDirichletCharacter(temp_args).to_dict()
        print info
        info['navi'] = dirichlet_navi(info)
        return render_template('dirichlet_characters/Character.html', **info)

@app.route("/Character/Dirichlet/calc-<calc>/<int:modulus>/<int:number>")
def dc_calc(calc, modulus, number):
    val = request.args.get("val", [])
    args = {'type':'Dirichlet', 'modulus':modulus, 'number':number}
    if not val:
        return flask.abort(404)
    try:
        if calc == 'value':
            return WebDirichletCharacter(args).value(val)
        if calc == 'gauss':
            return WebDirichletCharacter(args).gauss_sum(val)
        elif calc == 'jacobi':
            return WebDirichletCharacter(args).jacobi_sum(val)
        elif calc == 'kloosterman':
            return WebDirichletCharacter(args).kloosterman_sum(val)
        else:
            return flask.abort(404)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

def dirichlet_navi(info):
    prevurl =  url_for("render_DirichletCharacter", arg1=info['prevmod'], arg2=info['prevnum'])
    nexturl =  url_for("render_DirichletCharacter", arg1=info['nextmod'], arg2=info['nextnum'])
    return [ (info['previous'], prevurl), (info['next'], nexturl) ]

@app.route("/Character/Hecke/")
@app.route("/Character/Hecke/<arg1>")
@app.route("/Character/Hecke/<arg1>/<arg2>")
@app.route("/Character/Hecke/<arg1>/<arg2>/<arg3>")
def render_HeckeCharacter(arg1=None, arg2=None, arg3=None):
    return render_Heckewebpage(request, arg1, arg2, arg3)

@app.route("/Character/Hecke/<number_field>/<modulus>/<number>")
def render_Heckewebpage(request, number_field, modulus, number):
    args = request.args
    temp_args = to_dict(args)

    temp_args['type'] = 'Hecke'
    temp_args['number_field'] = number_field
    temp_args['modulus'] = modulus
    temp_args['number'] = number

    if number_field == None:
        return render_template('dirichlet_characters/Hecke_help.html')
    elif modulus == None:
        info = init_NFinfo(temp_args)
        print info
        return render_template('dirichlet_characters/HeckeChooseIdeal.html', **info)
    elif number == None:
        info = WebHeckeGroup(temp_args).to_dict()
        print info
        return render_template('dirichlet_characters/CharGroup.html', **info)
    else:
        info = WebHeckeCharacter(temp_args).to_dict()
        print info
        return render_template('dirichlet_characters/Character.html', **info)

@app.route("/Character/Hecke/calc-<calc>/<number_field>/<modulus>/<number>")
def hc_calc(calc, number_field, modulus, number):
    val = request.args.get("val", [])
    args = {'type':'Hecke', 'number_field':number_field, 'modulus':modulus, 'number':number}
    if not val:
        return flask.abort(404)
    try:
        if calc == 'value':
            return WebHeckeCharacter(args).value(val)
        else:
            return flask.abort(404)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

def init_HeckeGroup(args):

    G = WebHeckeGroup(args)

    info = {'title': G.title()}
    info['args'] = args

    info['credit'] = 'Sage, Pari'
    info['support'] = ''
    info['citation'] = ""


    info['nflabel'] = nf_label = G.nflabel
    info['nf_pol'] = G.nf_pol()
    info['generators'] = G.generators()
    info['modlabel'] = G.modlabel
    info['modulus'] = G.mod()
    info['order'] = G.order()
    info['structure'] = G.structure()
    info['contents'] = G.table_content()

    info['friends'] = [('Field of definition', '/NumberField/' + nf_label)]

    return info

def initCharacterInfo(web_chi, args, request):
    info = {'title': web_chi.title}
    info['citation'] = ''
    info['support'] = ''
    info['args'] = args

    info['credit'] = 'Sage, Pari'
    info['citation'] = web_chi.citation

    try:
        info['url'] = web_chi.url
    except:
        info['url'] = ''

    info['bread'] = []
    info['properties2'] = web_chi.properties

    if args['type'] == 'hecke':
        snum = str(web_chi.number)
        info['number'] = snum
        smod = str(web_chi.modulus)
        info['modulus'] = smod
        G_prev = None
        #chi = G[web_chi.number]
        chi = None
        chi_sage = None
        indices = []
        info['bread'] = [('Hecke Characters', '/Character/Hecke'), (
            'Character ' + snum + ' modulo ' + smod, '/Character/Hecke/' + smod + '/' + snum)]
        info['char'] = ''
        info['chisage'] = ''
        info['conductor'] = web_chi.conductor
        info['order'] = int(web_chi.order)
        info['eulerphi'] = euler_phi(web_chi.modulus) - 1
        info['nextmodulus'] = web_chi.modulus + 1
        info['primitive'] = web_chi.primitive
        info['zetaorder'] = web_chi.zetaorder
        info['genvals'] = '' #str(web_chi.genvalues)
        info['genvalstex'] = str(web_chi.genvaluestex)
        info['parity'] = web_chi.parity
        info['real'] = web_chi.real
        info['prim'] = web_chi.prim
        info['vals'] = '' #web_chi.vals
        info['logvals'] = '' #web_chi.logvals
        modulus = web_chi.modulus
        info['galoisorbit'] = web_chi.galoisorbit
        info['valuefield'] = web_chi.valuefield
        info['kername'] = '' #web_chi.kername
        #if web_chi.nf_pol:
        #    info['nf_pol'] = web_chi.nf_pol
        info['unitgens'] = str(web_chi.unitgens)
        info['bound'] = 0 #int(web_chi.bound)
        if False and web_chi.primitive == "False":
            info['inducedchar'] = web_chi.inducedchar
            info['inducedchar_modulus'] = web_chi.inducedchar_modulus
            info['inducedchar_conductor'] = web_chi.inducedchar_conductor
            info['inducedchar_number'] = web_chi.inducedchar_number
            info['inducedchar_tex'] = web_chi.inducedchar_tex
        info['nextnumber'] = 0 #web_chi.number + 1
        if web_chi.primitive == "False":
            info['friends'] = []
        else:
            info['friends'] = [('Dirichlet L-function', '/L/Character/Hecke/' + smod + '/' + snum)]
        if web_chi.valuefield_label != '':
            info['friends'].append(('Field of values', '/NumberField/' + str(web_chi.valuefield_label)))
        #if web_chi.nf_friend != '':
        #    info['friends'].append((info['kername'], web_chi.nf_friend))
        #    info['nf_label'] = web_chi.nf_label

        prev_name, prev_url, next_name, next_url = '', '', '', ''
        info['navi'] = [(prev_name, prev_url), (next_name, next_url)]

    return info


