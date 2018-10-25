# -*- coding: utf-8 -*-

from lmfdb.base import app
import re
import flask
from flask import render_template, url_for, request, redirect
from sage.all import gcd, randint
from lmfdb.utils import to_dict, flash_error
from lmfdb.characters.utils import url_character
from lmfdb.WebCharacter import (
        WebDirichletGroup,
        WebSmallDirichletGroup,
        WebDirichletCharacter,
        WebSmallDirichletCharacter,
        WebDBDirichletCharacter,
        WebDBDirichletGroup
)
from lmfdb.WebCharacter import WebHeckeExamples, WebHeckeFamily, WebHeckeGroup, WebHeckeCharacter
from lmfdb.WebNumberField import WebNumberField
from lmfdb.characters import characters_page
import ListCharacters

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
    return redirect(url_for(".render_Dirichletwebpage"), 301)

def render_DirichletNavigation():
    args = to_dict(request.args)

    info = {'args':args}
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
                      ('Dirichlet', url_for(".render_Dirichletwebpage")) ]

    info['learnmore'] = learn()

    if 'modbrowse' in args:
        arg = args['modbrowse']
        arg = arg.split('-')
        modulus_start = int(arg[0])
        modulus_end = int(arg[1])
        info['title'] = 'Dirichlet Characters of Modulus ' + str(modulus_start) + '-' + str(modulus_end)
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
        info['title'] = 'Dirichlet Characters of Conductor ' + str(conductor_start) + '-' + str(conductor_end)
        info['credit'] = "Sage"
        info['contents'] = ListCharacters.get_character_conductor(conductor_start, conductor_end + 1)
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

    elif 'label' in args:
        label = args['label'].replace(' ','')
        if re.match(r'^[1-9][0-9]*\.[1-9][0-9]*$', label):
            slabel = label.split('.')
            m,n = int(slabel[0]), int(slabel[1])
            if m==n==1 or n < m and gcd(m,n) == 1:
                return redirect(url_for(".render_Dirichletwebpage", modulus=slabel[0], number=slabel[1]))
        if re.match(r'^[1-9][0-9]*$', label):
            return redirect(url_for(".render_Dirichletwebpage", modulus=label), 301)

        flash_error("%s is not a valid label for a Dirichlet character.  It should be of the form <span style='color:black'>q.n</span>, where q and n are coprime positive integers with n < q, or q=n=1.", label)
        return render_template('CharacterNavigate.html', **info)
        #FIXME, delete line below?
        #return redirect(url_for(".render_Dirichletwebpage"), 301)

    if args:
        # if user clicked refine search, reset start to 0
        if args.get('refine'):
            args['start'] = '0'
        try:
            search = ListCharacters.CharacterSearch(args)
        except ValueError as err:
            info['err'] = str(err)
            return render_template("CharacterNavigate.html" if "search" in args else "character_search_results.html" , **info)
        info['info'] = search.results()
        info['title'] = 'Dirichlet Character Search Results'
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Dirichlet', url_for(".render_Dirichletwebpage")),
                         ('Search Results', '') ]
        info['credit'] = 'SageMath'
        return render_template("character_search_results.html", **info)
    else:
       info['title'] = 'Dirichlet Characters'
       return render_template('CharacterNavigate.html', **info)

@characters_page.route("/Labels")
def labels_page():
    info = {}
    info['title'] = 'Dirichlet Character Labels'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Labels', '') ]
    info['learnmore'] = learn('labels')
    return render_template("single.html", kid='character.dirichlet.conrey', **info)

@characters_page.route("/Source")
def how_computed_page():
    info = {}
    info['title'] = 'Source of Dirichlet Characters'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Source', '') ]
    info['learnmore'] = learn('source')
    return render_template("single.html", kid='dq.character.dirichlet.source', **info)

@characters_page.route("/Extent")
def extent_page():
    info = {}
    info['title'] = 'Extent of Dirichlet Characters Data'
    info['bread'] = [ ('Characters',url_for(".render_characterNavigation")),
    ('Dirichlet', url_for(".render_Dirichletwebpage")), ('Extent', '') ]
    info['learnmore'] = learn('extent')
    return render_template("single.html", kid='dq.character.dirichlet.extent',
                           **info)

@characters_page.route("/Dirichlet")
@characters_page.route("/Dirichlet/")
@characters_page.route("/Dirichlet/<modulus>")
@characters_page.route("/Dirichlet/<modulus>/")
@characters_page.route("/Dirichlet/<modulus>/<number>")
def render_Dirichletwebpage(modulus=None, number=None):

    if modulus == None:
        return render_DirichletNavigation()
    modulus = modulus.replace(' ','')
    if number == None and re.match('^[1-9][0-9]*\.[1-9][0-9]*$', modulus):
        return redirect(url_for(".render_Dirichletwebpage", label=modulus), 301)

    args={}
    args['type'] = 'Dirichlet'
    args['modulus'] = modulus
    args['number'] = number
    try:
        modulus = int(modulus)
    except ValueError:
        modulus = 0
    if modulus <= 0:
        flash_error ("%s is not a valid modulus for a Dirichlet character.  It should be a positive integer.", args['modulus'])
        return redirect(url_for(".render_Dirichletwebpage"))
    if modulus > 10**20:
        flash_error ("specified modulus %s is too large, it should be less than $10^{20}$.", modulus)
        return redirect(url_for(".render_Dirichletwebpage"))



    if number == None:
        if modulus < 10000:
            info = WebDBDirichletGroup(**args).to_dict()
            info['show_orbit_label'] = True
        elif modulus < 100000:
            info = WebDirichletGroup(**args).to_dict()
        else:
            info = WebSmallDirichletGroup(**args).to_dict()
        info['title'] = 'Group of Dirichlet Characters of Modulus ' + str(modulus)
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Dirichlet', url_for(".render_Dirichletwebpage")),
                         ('%d'%modulus, url_for(".render_Dirichletwebpage", modulus=modulus))]
        info['learnmore'] = learn()
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        if 'gens' in info:
            info['generators'] = ', '.join([r'<a href="%s">$\chi_{%s}(%s,\cdot)$'%(url_for(".render_Dirichletwebpage",modulus=modulus,number=g),modulus,g) for g in info['gens']])
        return render_template('CharGroup.html', **info)

    try:
        number = int(number)
    except ValueError:
        number = 0;
    if number <= 0 or gcd(modulus,number) != 1 or number > modulus:
        flash_error("the value %s is invalid.  It should be a positive integer coprime to and no greater than the modulus %s.", args['number'],args['modulus'])
        return redirect(url_for(".render_Dirichletwebpage"))
    if modulus < 10000:
        webchar = WebDBDirichletCharacter(**args)
        info = webchar.to_dict()
    elif modulus < 100000:
        webchar = WebDirichletCharacter(**args)
        info = webchar.to_dict()
    else:
        info = WebSmallDirichletCharacter(**args).to_dict()
    info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                     ('Dirichlet', url_for(".render_Dirichletwebpage")),
                     ('%s'%modulus, url_for(".render_Dirichletwebpage", modulus=modulus)),
                     ('%s'%number, url_for(".render_Dirichletwebpage", modulus=modulus, number=number)) ]
    info['learnmore'] = learn()
    info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
    info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
    return render_template('Character.html', **info)

@characters_page.route('/Dirichlet/random')
def random_Dirichletwebpage():
    modulus = randint(1,9999)
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
    else:
        WNF = WebNumberField(number_field)
        if WNF.is_null():
            return flask.abort(404, "Number field %s not found."%number_field)

    if modulus == None:
        try:
            info = WebHeckeFamily(**args).to_dict()
        except (ValueError,KeyError,TypeError) as err:
            return flask.abort(404,err.args)
        return render_template('CharFamily.html', **info)
    elif number == None:
        try:
            info = WebHeckeGroup(**args).to_dict()
        except (ValueError,KeyError,TypeError) as err:
            # Typical failure case is a GP error inside bnrinit which we don't really want to display
            return flask.abort(404,'Unable to construct modulus %s for number field %s'%(modulus,number_field))
        m = info['modlabel']
        info['bread'] = [('Characters', url_for(".render_characterNavigation")),
                         ('Hecke', url_for(".render_Heckewebpage")),
                         ('Number Field %s'%number_field, url_for(".render_Heckewebpage", number_field=number_field)),
                         ('%s'%m,  url_for(".render_Heckewebpage", number_field=number_field, modulus=m))]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
        return render_template('CharGroup.html', **info)
    else:
        try:
            X = WebHeckeCharacter(**args)
        except (ValueError,KeyError,TypeError) as err:
            return flask.abort(404, 'Unable to construct Hecke character %s modulo %s in number field %s.'%(number,modulus,number_field))
        info = X.to_dict()
        info['bread'] = [('Characters',url_for(".render_characterNavigation")),
                         ('Hecke',  url_for(".render_Heckewebpage")),
                         ('Number Field %s'%number_field,url_for(".render_Heckewebpage", number_field=number_field)),
                         ('%s'%X.modulus, url_for(".render_Heckewebpage", number_field=number_field, modulus=X.modlabel)),
                         ('%s'%X.number2label(X.number), '')]
        info['code'] = dict([(k[4:],info[k]) for k in info if k[0:4] == "code"])
        info['code']['show'] = { lang:'' for lang in info['codelangs'] } # use default show names
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

@characters_page.route("/Dirichlet/table")
def dirichlet_table():
    args = to_dict(request.args)
    mod = args.get('modulus',1)
    return redirect(url_for('characters.render_Dirichletwebpage',modulus=mod))

# FIXME: these group table pages are used by number fields pages.
# should refactor this into WebDirichlet.py
@characters_page.route("/Dirichlet/grouptable")
def dirichlet_group_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
        info["modulus"] = modulus
    info['bread'] = [('Characters', url_for(".render_characterNavigation")), ('Dirichlet Table', ' ') ]
    info['credit'] = 'SageMath'
    char_number_list = request.args.get("char_number_list",None)
    if char_number_list is not None:
        info['char_number_list'] = char_number_list
        char_number_list = [int(a) for a in char_number_list.split(',')]
        info['poly'] = request.args.get("poly", '???')
    else:
        return flask.abort(404, 'grouptable needs char_number_list argument')
    h, c = get_group_table(modulus, char_number_list)
    info['headers'] = h
    info['contents'] = c
    info['title'] = 'Group of Dirichlet Characters'
    return render_template("CharacterGroupTable.html", **info)


def get_group_table(modulus, char_list):
    # Move 1 to the front of the list
    char_list.insert(0, char_list.pop(next(j for j in range(len(char_list)) if char_list[j]==1)))
    headers = [j for j in char_list]  # Just a copy
    if modulus == 1:
        rows = [[1]]
    else:
        rows = [[(j * k) % modulus for k in char_list] for j in char_list]
    return headers, rows
