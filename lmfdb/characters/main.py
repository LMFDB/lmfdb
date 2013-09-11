# -*- coding: utf-8 -*-
# Characters.py

import re

from lmfdb.base import app, r
import flask
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import *
import tempfile
import os
from pymongo import ASCENDING
from lmfdb.utils import to_dict, parse_range, make_logger
from lmfdb.WebCharacter import *
from lmfdb.characters import characters_page, logger
import ListCharacters

try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")

###############################################################################
#   Route functions
###############################################################################

## generic

def url_character(type=None,number_field=None,modulus=None,number=None):
    if type=='Dirichlet':
        render_Dirichletwebpage(request, modulus, number)
    elif type=='Hecke':
        render_Heckewebpage(request, number_field, modulus, number)
    else:
        render_template('CharacterNavigate.html')

@characters_page.route("/")
def render_characterNavigation():
    return render_template('templates/CharacterNavigate.html')

@characters_page.route("/Dirichlet/")
@characters_page.route("/Dirichlet/<modulus>")
@characters_page.route("/Dirichlet/<modulus>/<number>")
def render_Dirichletwebpage(request, modulus=None, number=None):
    args = request.args
    temp_args = to_dict(args)

    temp_args['type'] = 'Dirichlet'
    temp_args['modulus'] = modulus
    temp_args['number'] = number

    if modulus == None:
        info = WebDirichletFamily(temp_args).to_dict()
        print info
        return render_template('dirichlet_characters/CharFamily.html', **info)
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
    r = [ (l, url_for('.render_charwebpage', **args)) for l, args in L if l ]
    return r
    
@characters_page.route("/calc-<calc>/Dirichlet/<int:modulus>/<int:number>")
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

@characters_page.route("/Hecke/<number_field>/<modulus>/<number>")
def render_Heckewebpage(request, number_field=None, modulus=None, number=None):
    args = request.args
    temp_args = to_dict(args)

    temp_args['type'] = 'Hecke'
    temp_args['number_field'] = number_field
    temp_args['modulus'] = modulus
    temp_args['number'] = number

    if number_field == None:
        return render_template('dirichlet_characters/Hecke.html')
    elif modulus == None:
        info = WebHeckeFamily(temp_args).to_dict()
        print info
        return render_template('dirichlet_characters/CharFamily.html', **info)
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

@characters_page.route("/calc-<calc>/Hecke/<number_field>/<modulus>/<number>")
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
