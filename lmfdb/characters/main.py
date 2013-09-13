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
from lmfdb.utils import to_dict, parse_range, make_logger, url_character
from lmfdb.WebCharacter import *
from lmfdb.characters import characters_page, logger
import ListCharacters

try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")

###############################################################################
#   Route functions
#   Do not use url_for on these, use url_character defined in lmfdb.utils
###############################################################################

@characters_page.route("/")
def render_characterNavigation():
    """
    FIXME: replace query by ?browse=<key>&start=<int>&end=<int>
    """
    args = to_dict(request.args)
    info = {}
    info['bread'] = [ ('Characters','/Character') ]

    if 'modbrowse' in args:
        arg = args['modbrowse']
        arg = arg.split('-')
        modulus_start = int(arg[0])
        modulus_end = int(arg[1])
        info['title'] = 'Dirichlet Characters of Moduli ' + str(modulus_start) + '-' + str(modulus_end)
        info['credit'] = 'Sage'
        h, c, rows, cols = ListCharacters.get_character_modulus(modulus_start, modulus_end)
        info['contents'] = c
        info['headers'] = h
        info['rows'] = rows
        info['cols'] = cols
        return render_template("ModulusList.html", **info)

    elif 'condbrowse' in args:
        arg = args['condbrowse']
        arg = arg.split('-')
        conductor_start = int(arg[0])
        conductor_end = int(arg[1])
        info['conductor_start'] = conductor_start
        info['conductor_end'] = conductor_end
        info['title'] = 'Dirichlet Characters of Conductors ' + str(conductor_start) + \
            '-' + str(conductor_end)
        info['credit'] = "Sage"
        info['contents'] = ListCharacters.get_character_conductor(conductor_start, conductor_end + 1)
        # info['contents'] = c
        # info['header'] = h
        # info['rows'] = rows
        # info['cols'] = cols
        return render_template("ConductorList.html", **info)

    elif 'ordbrowse' in args:
        arg = args['ordbrowse']
        arg = arg.split('-')
        order_start = int(arg[0])
        order_end = int(arg[1])
        info['order_start'] = order_start
        info['order_end'] = order_end
        info['title'] = 'Dirichlet Characters of Orders ' + str(order_start) + '-' + str(order_end)
        info['credit'] = 'Sage'
        info['contents'] = ListCharacters.get_character_order(order_start, order_end + 1)
        return render_template("OrderList.html", **info)

    elif args != {}:
        return character_search(**args)

    else:
       return render_template('CharacterNavigate.html', **info)

@characters_page.route("/Dirichlet/")
@characters_page.route("/Dirichlet/<modulus>")
@characters_page.route("/Dirichlet/<modulus>/<number>")
def render_Dirichletwebpage(modulus=None, number=None):
    #args = request.args
    #temp_args = to_dict(args)

    args={}
    args['type'] = 'Dirichlet'
    args['modulus'] = modulus
    args['number'] = number

    if modulus == None:
        info = WebDirichletFamily(**args).to_dict()
        #logger.info(info)
        return render_template('CharFamily.html', **info)
    elif number == None:
        info = WebDirichletGroup(**args).to_dict()
        m = info['modlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Dirichlet','/Character/Dirichlet'),
                         ('Modulus %s'%m, '/Character/Dirichlet/%s'%m)]
        #logger.info(info)
        return render_template('CharGroup.html', **info)
    else:
        info = WebDirichletCharacter(**args).to_dict()
        info['navi'] = navi([info['previous'],info['next']])
        m,n = info['modlabel'], info['numlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Dirichlet','/Character/Dirichlet'),
                         ('Modulus %s'%m, '/Character/Dirichlet/%s'%m),
                         ('Character number %s'%n, '/Character/Dirichlet/%s/%s'%(m,n)) ]
        #logger.info(info)
        return render_template('Character.html', **info)

def navi(L):
    r = [ (l, url_character(**args)) for l, args in L if l ]
    return r
    
@characters_page.route("/calc-<calc>/Dirichlet/<int:modulus>/<int:number>")
def dc_calc(calc, modulus, number):
    val = request.args.get("val", [])
    args = {'type':'Dirichlet', 'modulus':modulus, 'number':number}
    if not val:
        return flask.abort(404)
    try:
        if calc == 'value':
            return WebDirichletCharacter(**args).value(val)
        if calc == 'gauss':
            return WebDirichletCharacter(**args).gauss_sum(val)
        elif calc == 'jacobi':
            return WebDirichletCharacter(**args).jacobi_sum(val)
        elif calc == 'kloosterman':
            return WebDirichletCharacter(**args).kloosterman_sum(val)
        else:
            return flask.abort(404)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@characters_page.route("/Hecke/")
@characters_page.route("/Hecke/<number_field>")
@characters_page.route("/Hecke/<number_field>/<modulus>")
@characters_page.route("/Hecke/<number_field>/<modulus>/<number>")
def render_Heckewebpage(number_field=None, modulus=None, number=None):
    #args = request.args
    #temp_args = to_dict(args)

    args = {}
    args['type'] = 'Hecke'
    args['number_field'] = number_field
    args['modulus'] = modulus
    args['number'] = number

    if number_field == None:
        info = WebHeckeExamples(**args).to_dict()
        return render_template('Hecke.html', **info)
    elif modulus == None:
        info = WebHeckeFamily(**args).to_dict()
        #logger.info(info)
        return render_template('CharFamily.html', **info)
    elif number == None:
        info = WebHeckeGroup(**args).to_dict()
        m = info['modlabel']
        info['bread'] = [('Characters','/Character'),
                         ('Hecke','/Character/Hecke'),
                         ('Number Field %s'%number_field,'/Character/Hecke/%s'%number_field),
                         ('Modulus %s'%m, '/Character/Hecke/%s/%s'%(number_field,m))]
        #logger.info(info)
        return render_template('CharGroup.html', **info)
    else:
        info = WebHeckeCharacter(**args).to_dict()
        info['navi'] = navi([info['previous'],info['next']])
        m,n = info['modlabel'], info['number']
        info['bread'] = [('Characters','/Character'),
                         ('Hecke','/Character/Hecke'),
                         ('Number Field %s'%number_field,'/Character/Hecke/%s'%number_field),
                         ('Modulus %s'%m, '/Character/Hecke/%s/%s'%(number_field,m)),
                         ('Character number %s'%n, '/Character/Hecke/%s/%s/%s'%(number_field,m,n))]
        #logger.info(info)
        return render_template('Character.html', **info)

@characters_page.route("/calc-<calc>/Hecke/<number_field>/<modulus>/<number>")
def hc_calc(calc, number_field, modulus, number):
    val = request.args.get("val", [])
    args = {'type':'Hecke', 'number_field':number_field, 'modulus':modulus, 'number':number}
    if not val:
        return flask.abort(404)
    try:
        if calc == 'value':
            return WebHeckeCharacter(**args).value(val)
        else:
            return flask.abort(404)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

###############################################################################
##  TODO: refactor the following
###############################################################################

def character_search(**args):
    info = to_dict(args)
    for field in ['modulus', 'conductor', 'order']:
        info[field] = info.get(field, '')
    query = {}
    if 'natural' in args:
        label = info.get('natural', '')
        try:
            modulus = int(str(label).partition('.')[0])
            number = int(str(label).partition('.')[2])
        except ValueError:
            return "<span style='color:red;'>ERROR: bad query</span>"
        return redirect(url_character(type='Dirichlet',modulus=modulus, number=number))
    else:
        for field in ['modulus', 'conductor', 'order']:
            if info.get(field):
                query[field] = parse_range(info[field])
        info['bread'] = [('Characters','/Character'), ('search results', ' ') ]
        info['credit'] = 'Sage'
        if (len(query) != 0):
            from sage.modular.dirichlet import DirichletGroup
            info['contents'] = charactertable(query)
            info['title'] = 'Dirichlet Characters'
            return render_template("character_search.html", **info)
        else:
            return "<span style='color:red;'>ERROR: bad query</span>"


def charactertable(query):
    return render_character_table(
        modulus=query.get('modulus', None),
        conductor=query.get('conductor', None),
        order=query.get('order', None))


def render_character_table(modulus=None, conductor=None, order=None):
    from dirichlet_conrey import DirichletGroup_conrey
    start = 1
    end = 201
    stepsize = 1
    if modulus:
        start = modulus
        end = modulus + 1
    elif conductor:
        start = conductor
        stepsize = conductor

    def row(N):
        ret = []
        G = DirichletGroup_conrey(N)
        for chi in G:
            j = chi.number()
            add = True
            add &= not conductor or chi.conductor() == conductor
            add &= not order or chi.multiplicative_order() == order
            if add:
                if chi.multiplicative_order() == 2 and kronecker_symbol(chi) is not None:
                    ret.append([(j, kronecker_symbol(chi), chi.modulus(
                    ), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
                else:
                    ret.append([(j, chi, chi.modulus(
                    ), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
        return ret
    return [row(_) for _ in range(start, end, stepsize)]


def kronecker_symbol(chi):
    m = chi.conductor() / 4
    if chi.conductor() % 2 == 1:
        if chi.conductor() % 4 == 1:
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" % (chi.conductor())
        else:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" % (chi.conductor())
    elif chi.conductor() % 8 == 4:
        if m % 4 == 1:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" % (chi.conductor())
        elif m % 4 == 3:
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" % (chi.conductor())
    elif chi.conductor() % 16 == 8:
        if chi.is_even():
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" % (chi.conductor())
        else:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" % (chi.conductor())
    else:
        return None


@characters_page.route("/Dirichlet/table")
def dirichlet_table():
    args = to_dict(request.args)
    mod = args.get('modulus',1)
    return redirect(url_character(type='Dirichlet',modulus=mod))

#    info = to_dict(args)
#    info['modulus'] = modulus
#    info["bread"] = [('Dirichlet Character Table', url_for("dirichlet_table")), ('result', ' ')]
#    info['credit'] = 'Sage'
#    h, c, = get_entries(modulus)
#    info['headers'] = h
#    info['contents'] = c
#    info['title'] = 'Dirichlet Characters'
#    return render_template("CharacterTable.html", **info)
#
#
#def get_entries(modulus):
#    from dirichlet_conrey import DirichletGroup_conrey
#    from sage.all import Integer
#    G = DirichletGroup_conrey(modulus)
#    headers = range(1, modulus + 1)
#    e = euler_phi(modulus)
#    rows = []
#    for chi in G:
#        is_prim = chi.is_primitive()
#        number = chi.number()
#        rows.append((number, is_prim, log_value(modulus, number)))
#    return headers, rows


# fixme: remove this
@characters_page.route("/Dirichlet/grouptable")
def dirichlet_group_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
        info["modulus"] = modulus
    info['bread'] = [('Characters','/Character'), ('Dirichlet table', ' ') ]
    info['credit'] = 'Sage'
    char_number_list = request.args.get("char_number_list")
    if char_number_list is not None:
        info['char_number_list'] = char_number_list
        char_number_list = [int(a) for a in char_number_list.split(',')]
        info['poly'] = request.args.get("poly", '???')
    h, c = get_group_table(modulus, char_number_list)
    info['headers'] = h
    info['contents'] = c
    info['title'] = 'Group of Dirichlet Characters'
    return render_template("CharacterGroupTable.html", **info)


def get_group_table(modulus, char_number_list):
    # Move 1 to the front of the list
    j = 0
    while char_number_list[j] != 1:
        j += 1
    char_number_list.insert(0, char_number_list.pop(j))
    headers = [j for j in char_number_list]  # Just a copy
    if modulus == 1:
        rows = [[1]]
    else:
        rows = [[(j * k) % modulus for k in char_number_list] for j in char_number_list]
    return headers, rows
