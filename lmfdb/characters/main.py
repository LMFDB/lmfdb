# -*- coding: utf-8 -*-

import re

from lmfdb.base import app, r
import flask
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import gcd, randint
import tempfile
import os
from lmfdb.base import getDBConnection
from lmfdb.utils import to_dict, make_logger
from lmfdb.search_parsing import parse_range
from lmfdb.WebCharacter import *
from lmfdb.characters import characters_page, logger
import ListCharacters

try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")

#### make url_character available from templates
@app.context_processor
def ctx_characters():
    chardata = {}
    chardata['url_character'] = url_character
    return chardata

def learn(current = None):
    r = []
    if current != 'source':
        r.append( ('Source of the data', url_for(".how_computed_page")) )
    if current != 'extent':
        r.append( ('Extent of the data', url_for(".extent_page")) )
    if current != 'labels':
        r.append( ('Labels for Dirichlet characters', url_for(".labels_page")) )
    return r

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
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")) ]

    info['learnmore'] = learn()

    if 'modbrowse' in args:
        arg = args['modbrowse']
        arg = arg.split('-')
        modulus_start = int(arg[0])
        modulus_end = int(arg[1])
        info['title'] = 'Dirichlet Characters of Moduli ' + str(modulus_start) + '-' + str(modulus_end)
        info['credit'] = 'SageMath'
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
        info['credit'] = "SageMath"
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
        info['credit'] = 'SageMath'
        info['contents'] = ListCharacters.get_character_order(order_start, order_end + 1)
        return render_template("OrderList.html", **info)

    elif args != {}:
        return character_search(**args)

    else:
       info['title'] = 'Dirichlet Characters'
       return render_template('CharacterNavigate.html', **info)

@characters_page.route("/Labels")
def labels_page():
    info = {}
    info['title'] = 'Dirichlet character labels'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Labels', '') ]
    info['learnmore'] = learn('labels')
    return render_template("single.html", kid='character.dirichlet.conrey',
                           **info)

@characters_page.route("/Source")
def how_computed_page():
    info = {}
    info['title'] = 'Source of Dirichlet characters'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Source', '') ]
    info['learnmore'] = learn('source')
    return render_template("single.html", kid='dq.character.dirichlet.source',
                           **info)

@characters_page.route("/Extent")
def extent_page():
    info = {}
    info['title'] = 'Extent of Dirichlet characters data'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Extent', '') ]
    info['learnmore'] = learn('extent')
    return render_template("single.html", kid='dq.character.dirichlet.extent',
                           **info)

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
        return render_characterNavigation() # waiting for new landing page
        info = WebDirichletFamily(**args).to_dict()
        info['learnmore'] = learn()

        return render_template('CharFamily.html', **info)
    else:
        modulus = int(modulus)
        if number == None:
            if modulus < 100000:
                info = WebDirichletGroup(**args).to_dict()
            else:
                info = WebSmallDirichletGroup(**args).to_dict()
            m = info['modlabel']
            info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                             ('Dirichlet', url_for(".render_Dirichletwebpage")),
                             ('Mod %s'%m, url_for(".render_Dirichletwebpage", modulus=m))]
            info['learnmore'] = learn()
            info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
            info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
            return render_template('CharGroup.html', **info)
        else:
            number = int(number)
            if gcd(modulus, number) != 1:
                return flask.abort(404)
            if modulus < 100000:
                webchar = WebDirichletCharacter(**args)
                info = webchar.to_dict()
            else:
                info = WebSmallDirichletCharacter(**args).to_dict()
            m,n = info['modlabel'], info['numlabel']
            info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                             ('Dirichlet', url_for(".render_Dirichletwebpage")),
                             ('Mod %s'%m, url_for(".render_Dirichletwebpage", modulus=m)),
                             ('%s'%n, url_for(".render_Dirichletwebpage", modulus=m, number=n)) ]
            info['learnmore'] = learn()
            info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
            info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
            return render_template('Character.html', **info)

@characters_page.route('/Dirichlet/random')
def random_Dirichletwebpage():
    modulus = randint(1,99999)
    number = randint(1,modulus-1)
    while gcd(modulus,number) > 1:
        number = randint(1,modulus-1)
    return redirect(url_for('.render_Dirichletwebpage', modulus=str(modulus), number=str(number)))

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
    except Warning, e:
        return "<span style='color:gray;'>%s</span>" % e
    except Exception:
        return "<span style='color:red;'>Error: bad input</span>"

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
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Hecke', url_for(".render_Heckewebpage")),
                         ('Number Field %s'%number_field, url_for(".render_Heckewebpage", number_field=number_field)),
                         ('Mod %s'%m,  url_for(".render_Heckewebpage", number_field=number_field, modulus=m))]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        #logger.info(info)
        return render_template('CharGroup.html', **info)
    else:
        X = WebHeckeCharacter(**args)
        info = X.to_dict()
        m,n = info['modlabel'], info['number']
        info['bread'] = [('Characters',url_for(".render_characterNavigation")),
                         ('Hecke',  url_for(".render_Heckewebpage")),
                         ('Number Field %s'%number_field,url_for(".render_Heckewebpage", number_field=number_field)),
                         ('Mod %s'%X.modulus, url_for(".render_Heckewebpage", number_field=number_field, modulus=m)),
                         ('#%s'%X.number, url_for(".render_Heckewebpage", number_field=number_field, modulus=m, number=n))]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
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
        return redirect(url_for('characters.render_Dirichletwebpage',modulus=modulus, number=number))
    else:
        for field in ['modulus', 'conductor', 'order']:
            if info.get(field):
                query[field] = parse_range(info[field])
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Dirichlet', url_for(".render_Dirichletwebpage")),
                         ('search results', ' ') ]
        info['credit'] = 'SageMath'
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
            c = WebDirichletCharacter(modulus = chi.modulus(), number = chi.number())
            add = True
            add &= not conductor or chi.conductor() == conductor
            add &= not order or chi.multiplicative_order() == order
            if add:
                if chi.multiplicative_order() == 2 and c.symbol is not None:
                    ret.append([(j, c.symbol, chi.modulus(), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
                else:
                    ret.append([(j, chi, chi.modulus(), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
        return ret
    return [row(_) for _ in range(start, end, stepsize)]




@characters_page.route("/Dirichlet/table")
def dirichlet_table():
    args = to_dict(request.args)
    mod = args.get('modulus',1)
    return redirect(url_for('characters.render_Dirichletwebpage',modulus=mod))

#    info = to_dict(args)
#    info['modulus'] = modulus
#    info["bread"] = [('Dirichlet Character Table', url_for("dirichlet_table")), ('result', ' ')]
#    info['credit'] = 'SageMath'
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


# fixme: these group tables are needed by number fields pages.
# should refactor this into WebDirichlet.py
@characters_page.route("/Dirichlet/grouptable")
def dirichlet_group_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
        info["modulus"] = modulus
    info['bread'] = [('Characters', url_for(".render_characterNavigation")), ('Dirichlet table', ' ') ]
    info['credit'] = 'SageMath'
    char_number_list = request.args.get("char_number_list",None)
    if char_number_list is not None:
        info['char_number_list'] = char_number_list
        char_number_list = [int(a) for a in char_number_list.split(',')]
        info['poly'] = request.args.get("poly", '???')
    else:
        return render_template("404.html", message='grouptable needs char_number_list argument')
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
