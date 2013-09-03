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
        m = info['modlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Dirichlet','/Character/Dirichlet'),
                         ('Modulus %s'%m, '/Character/Dirichlet/%s'%m)]
        return render_template('dirichlet_characters/CharGroup.html', **info)
    else:
        info = WebDirichletCharacter(temp_args).to_dict()
        info['navi'] = navi([info['previous'],info['next']])
        m,n = info['modlabel'], info['numlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Dirichlet','/Character/Dirichlet'),
                         ('Modulus %s'%m, '/Character/Dirichlet/%s'%m),
                         ('Character number %s'%n, '/Character/Dirichlet/%s/%s'%(m,n)) ]
        print info
        return render_template('dirichlet_characters/Character.html', **info)

def navi(L):
    print L
    r = [ (l, url_for('render_charwebpage', **args)) for l, args in L if l ]
    return r
    


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
        m = info['modlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Hecke','/Character/Hecke'),
                         ('Number Field %s'%number_field,'/Character/Hecke/%s'%number_field),
                         ('Modulus %s'%m, '/Character/Hecke/%s/%s'%(number_field,m))]
        print info
        return render_template('dirichlet_characters/CharGroup.html', **info)
    else:
        info = WebHeckeCharacter(temp_args).to_dict()
        info['navi'] = navi([info['previous'],info['next']])
        m,n = info['modlabel'], info['number']
        info['bread'] = [('Characters','/Character'),
                         ('Hecke','/Character/Hecke'),
                         ('Number Field %s'%number_field,'/Character/Hecke/%s'%number_field),
                         ('Modulus %s'%m, '/Character/Hecke/%s/%s'%(number_field,m)),
                         ('Character number %s'%n, '/Character/Hecke/%s/%s/%s'%(number_field,m,n))]
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
