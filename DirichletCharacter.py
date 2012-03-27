# -*- coding: utf-8 -*-
#DirichletCharacter.py

import re

from base import app, r
import flask
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import *
import tempfile, os
from pymongo import ASCENDING
from WebCharacter import *
from renderLfunction import render_Lfunction
from utils import to_dict, parse_range, make_logger
import ListCharacters

try:
  from dirichlet_conrey import *
except:
  logger.critical("dirichlet_conrey.pyx cython file is not available ...")


logger = make_logger("DC")

###############################################################################
#   Route functions
###############################################################################

@app.route("/Character/Dirichlet/")
@app.route("/Character/Dirichlet/<arg1>")
@app.route("/Character/Dirichlet/<arg1>/<arg2>")
def render_Character(arg1 = None, arg2 = None):
    return DirichletCharacter.render_webpage(request,arg1,arg2)

def render_webpage(request,arg1,arg2):
    args = request.args
    temp_args = to_dict(args)
    if len(args) == 0: # no arguments set yet
        if arg1 == None: # this means we're at the start page
            info = set_info_for_start_page() # sets info for character navigate
            info['credit'] = 'Sage'
            return render_template("dirichlet_characters/CharacterNavigate.html", **info)

        elif arg1.startswith("modbrowse"):
            modulus_start = int(arg1.partition('-')[0][10:])
            modulus_end = int(arg1.partition('-')[2])
            info = {}
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Moduli '+str(modulus_start) + '-' + str(modulus_end), '/Character/Dirichlet/modbrowse='+str(modulus_start)+'-'+str(modulus_end))]
            info['title'] = 'Moduli ' +str(modulus_start)+'-'+str(modulus_end)
            info['credit'] = 'Sage'
            h, c, rows, cols = ListCharacters.get_character_modulus(modulus_start,modulus_end)
            info['contents'] = c 
            info['headers']  = h
            info['rows'] = rows
            info['cols'] = cols
            return render_template("dirichlet_characters/ModulusList.html", **info)


        elif arg1.startswith("condbrowse"):
            conductor_start = int(arg1.partition('-')[0][11:])
            conductor_end = int(arg1.partition('-')[2])
            info = {}
            info['conductor_start'] = conductor_start
            info['conductor_end'] = conductor_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Conductor '+str(conductor_start) + '-' + str(conductor_end), '/Character/Dirichlet/condsearch='+str(conductor_start)+'-'+str(conductor_end))]
            info['title'] = 'Conductors ' +str(conductor_start)+'-'+str(conductor_end)
            info['credit'] = "Sage"
            info['contents'] = ListCharacters.get_character_conductor(conductor_start,conductor_end+1)
            return render_template("dirichlet_characters/ConductorList.html", **info)

        elif arg1.startswith("ordbrowse"):
            order_start = int(arg1.partition('-')[0][10:])
            order_end = int(arg1.partition('-')[2])
            info = {}
            info['order_start'] = order_start
            info['order_end'] = order_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Order '+str(order_start) + '-' + str(order_end), '/Character/Dirichlet/ordbrowse='+str(order_start)+'-'+str(order_end))]
            info['title'] = 'Order ' +str(order_start)+'-'+str(order_end)
            info['credit'] = 'Sage'
            info['contents'] = ListCharacters.get_character_order(order_start, order_end+1)
            return render_template("dirichlet_characters/OrderList.html", **info)


        elif arg1 == 'custom':
            return "not yet implemented"

        temp_args['type'] = 'dirichlet' # set type and input
        temp_args['modulus'] = arg1
        temp_args['number'] = arg2
            #elif arg1 == 'Hecke':
            #    temp_args['type'] = 'hecke'
    
        web_chi = WebCharacter(temp_args)
        #chi = web_chi.dirichletcharacter()

        #print chi

        try:
            print temp_args
        except:
            1

        info = initCharacterInfo(web_chi, temp_args, request) # sets the various properties of chi to be displayed in DirichletCharacter.htiml

        return render_template('dirichlet_characters/DirichletCharacter.html', **info)
    else:
        return character_search(**args)

def set_info_for_start_page():
    tl = [{'title':'Dirichlet','link':'degree#1Dirichlet'},
            {'title':'Hecke','link':'Hecke'}] #make the degree 1 ones, should be url_fors

    tt = {}
    tt[1]=tl
    modulus_list_endpoints = [1,100,1000,5000] + range(10000,130001,10000)
    modulus_list = ["%s-%s" %(start,end-1) for start,end in zip(modulus_list_endpoints[:-1], modulus_list_endpoints[1:])]
    info = {'modulus_list': modulus_list, 'conductor_list': range(1,181), 'order_list': range(2,21), 'type_table': tt, 'l':[1]}
    info['credit'] = 'Sage'
    info['title'] = 'Dirichlet Characters'
    info['bread'] = [('Dirichlet Characters', url_for("render_Character"))]
    info['learnmore'] = [('Dirichlet Characters', url_for("knowledge.show", ID="character.dirichlet.learn_more_about"))]
    info['friends'] = [('Dirichlet L-functions', url_for("render_Lfunction", arg1="degree1"))]
    return info

def initCharacterInfo(web_chi,args, request):
    chi = web_chi.dirichletcharacter()
    info = {'title': web_chi.title}
    info['citation'] = ''
    info['support'] = ''
    info['args'] = args

    info['credit'] = 'Sage'
    info['citation'] = web_chi.citation

    try:
        info['url'] = web_chi.url
    except:
        info['url'] =''

    info['bread'] = []
    info['properties2'] = web_chi.properties

    if args['type'] == 'dirichlet':
        #from dirichlet_conrey import *
        chi_sage = chi.sage_character()
        snum = str(web_chi.number)
        info['number'] = snum
        smod = str(web_chi.modulus)
        info['modulus'] = smod
        #G = DirichletGroup(web_chi.modulus)
        info['bread'] = [('Dirichlet Characters','/Character/Dirichlet'),('Character '+snum+ ' modulo '+smod,'/Character/Dirichlet/'+smod+'/'+snum)]
        info['char'] = str(web_chi.char)
        info['conductor'] = int(web_chi.conductor)
        info['order'] = int(web_chi.order)
        info['euerphi'] = euler_phi(web_chi.modulus)-1
        info['nextmodulus'] = web_chi.modulus+1
        info['primitive'] = web_chi.primitive
        info['zetaorder'] = web_chi.zetaorder
        info['genvals'] = str(web_chi.genvalues)
        info['genvalstex'] = str(web_chi.genvaluestex)
        info['parity'] = web_chi.parity
        info['sign'] = web_chi.sign
        info['real'] = web_chi.real
        info['prim'] = web_chi.prim
        info['vals'] = web_chi.vals
        #info['valstex'] = web_chi.valstex
        #info['root_unity'] =  str(any(map(lambda x : r"\zeta" in x,  web_chi.vals)))
        info['unitgens'] = str(web_chi.unitgens)
        info['bound'] = int(web_chi.bound)
        if web_chi.order == 2:
            info['kronsymbol'] = "%s" %(kronecker_symbol(chi_sage))
        if web_chi.primitive=="False":
            info['inducedchar'] = web_chi.inducedchar
            info['inducedchar_modulus'] = web_chi.inducedchar_modulus
            info['inducedchar_conductor'] = web_chi.inducedchar_conductor
            info['inducedchar_number'] = web_chi.inducedchar_number
            info['inducedchar_tex'] = web_chi.inducedchar_tex
        info['nextnumber'] = web_chi.number+1
        info['learnmore'] = [('Dirichlet Characters', url_for("knowledge.show", ID="character.dirichlet.learn_more_about"))] 
        info['friends'] = [('Dirichlet L-function', '/L/Character/Dirichlet/'+smod+'/'+snum)]
        nmore = int(snum) + 1
        nless = int(snum) - 1
        mmore = int(smod) + 1
        mless = int(smod) - 1
        url_ch = url_for("render_Character", arg1=smod,arg2=str(nmore))
        if web_chi.modulus == 1:
             info['navi'] = [(r"\(\chi_{" + str(0) + r"} \left( \text{mod}\; " + str(2)+ r"\right) \)" ,url_for("render_Character", arg1=str(2),arg2=str(0))), ("", "")]
        elif web_chi.modulus == 2:
             info['navi'] = [(r"\(\chi_{" + str(0) + r"} \left( \text{mod}\; " + str(3)+ r"\right) \)" ,url_for("render_Character", arg1=str(3),arg2=str(0))), (r"\(\chi_{" + str(0) + r"} \left( \text{mod}\;" + str(1)+ r"\right) \)",url_for("render_Character", arg1=str(1),arg2=str(0)))]
        else:
            if web_chi.number == 0:
                info['navi'] = [(r"\(\chi_{" + str(nmore) + r"} \left( \text{mod}\; " + smod+ r"\right) \)" ,url_ch), (r"\(\chi_{" + str(euler_phi(web_chi.modulus -1)-1) + r"} \left( \text{mod}\;" + str(mless)+ r"\right) \)",url_for("render_Character", arg1=str(mless),arg2=str(euler_phi(web_chi.modulus -1)-1)))]
            elif web_chi.number == euler_phi(web_chi.modulus)-1:
                info['navi'] = [(r"\(\chi_{" + str(0) + r"} \left( \text{mod}\;" + str(mmore)+ r"\right) \)",url_for("render_Character", arg1=str(mmore),arg2=str(0))), (r"\(\chi_{" + str(nless) + r"} \left( \text{mod}\;" + smod+ r"\right) \)",url_for("render_Character", arg1=smod,arg2=str(nless)))]
            else:
                info['navi'] = [(r"\(\chi_{" + str(nmore) + r"} \left( \text{mod}\;" + smod+ r"\right) \)",url_for("render_Character", arg1=smod,arg2=str(nmore))), (r"\(\chi_{" + str(nless) + r"} \left( \text{mod}\; " + smod+ r"\right) \)",url_for("render_Character", arg1=smod,arg2=str(nless)))]

    return info

@app.route("/Character/Dirichlet/<modulus>/<number>")
def render_webpage_label(modulus,number):
    return render_webpage(request,modulus,number)

@app.route("/Character/Dirichlet/calc_gauss/<int:modulus>/<int:number>")
def dc_calc_gauss(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    try:
        from sage.modular.dirichlet import DirichletGroup
        chi = DirichletGroup(modulus)[number]
        gauss_sum_numerical = chi.gauss_sum_numerical(100,int(arg))
        if int(arg) == 0:
            zeta = ""
        elif int(arg) == 1:
            zeta = "\zeta^{r}"
        else:
            zeta = "\zeta^{%s r}" %(int(arg))
        if modulus == 1:
            zeta_subscript = "1st"
        if modulus == 2:
            zeta_subscript = "2nd"
        elif modulus == 3:
            zeta_subscript = "3rd"
        else:
            zeta_subscript = str(modulus)+"th"
        return r"\begin{equation} \tau_{%s}(\chi_{%s}) = \sum_{r\in \mathbb{Z}/%s\mathbb{Z}} \chi_{%s}(r) %s = %s, \end{equation} where \(\zeta\) is a primitive %s root of unity." %(int(arg),number,modulus,number,zeta,latex(gauss_sum_numerical),zeta_subscript)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/calc_jacobi/<int:modulus>/<int:number>")
def dc_calc_jacobi(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    arg = map(int,arg.split('.'))
    try:
        num = arg[0]
        from sage.modular.dirichlet import DirichletGroup
        chi = DirichletGroup(modulus)[number]
        psi = DirichletGroup(modulus)[num]
        jacobi_sum = chi.jacobi_sum(psi)
        return r"\begin{equation} J(\chi_{%s},\chi_{%s}) = \sum_{r\in \mathbb{Z}/%s\mathbb{Z}} \chi_{%s}(r) \chi_{%s}(1-r) = %s,\end{equation} where <a href='/Character/Dirichlet/%s/%s'> \(\chi_{%s}\) </a> is character \(%s\) modulo \(%s\)." %(number,num,modulus,number,num,latex(jacobi_sum),modulus,num,num,num,modulus)  
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/calc_kloosterman/<int:modulus>/<int:number>")
def dc_calc_kloosterman(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    arg = map(int,arg.split(','))
    try:
        from sage.modular.dirichlet import DirichletGroup
        chi = DirichletGroup(modulus)[number]
        kloosterman_sum_numerical = chi.kloosterman_sum_numerical(100,arg[0],arg[1])
        if modulus == 1:
            zeta_subscript = "1st"
        if modulus == 2:
            zeta_subscript = "2nd"
        elif modulus == 3:
            zeta_subscript = "3rd"
        else:
            zeta_subscript = str(modulus)+"th"
        return r"\begin{equation} K(%s,%s,\chi_{%s}) = \sum_{r \in \mathbb{Z}/%s\mathbb{Z}} \chi_{%s}(r) \zeta^{%s r + %s r^{-1}} = %s, \end{equation} where \(\zeta\) is a primitive %s root of unity." %(int(arg[0]),int(arg[1]),number, modulus, number,int(arg[0]),int(arg[1]),latex(kloosterman_sum_numerical),zeta_subscript)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/<modulus>/<number>")
def redirect_character(modulus,number):
    return render_webpage(request,modulus,number)

def character_search(**args):
    #import base
    info = to_dict(args)
    query = {}
    print args
    if 'natural' in args:
        label = info.get('natural', '')
        modulus = int(str(label).partition('.')[0])
        number = int(str(label).partition('.')[2])
        return redirect(url_for("render_webpage_label", modulus=modulus,number=number))
    else:
        for field in ['modulus', 'conductor', 'order']:
            if info.get(field):
                query[field] = parse_range(info[field])
        info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('search results', ' ')]
        info['credit'] = 'Sage'
        if (len(query) != 0):
            from sage.modular.dirichlet import DirichletGroup
            info['contents'] = charactertable(query)
            info['title'] = 'Dirichlet Characters'
            return render_template("dirichlet_characters/character_search.html", **info)

def charactertable(query):
    return render_character_table(
            modulus=query.get('modulus',None),
            conductor=query.get('conductor',None),
            order=query.get('order',None))

def render_character_table(modulus=None,conductor=None,order=None):
    from dirichlet_conrey import DirichletGroup_conrey
    start = 1
    end = 201
    stepsize = 1
    if modulus:
        start = modulus
        end = modulus+1
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
            add &= not order     or chi.order() == order
            if add:
                if chi.order() == 2 and kronecker_symbol(chi) != None:
                    ret.append([(j, kronecker_symbol(chi), chi.modulus(), chi.conductor(), chi.order(), chi.is_primitive(), chi.is_even())])
                else:
                    ret.append([(j,chi, chi.modulus(), chi.conductor(), chi.order(), chi.is_primitive(), chi.is_even())])
        return ret
    return [row(_) for _ in range(start,end,stepsize)]


def kronecker_symbol(chi):
    m = chi.conductor()/4
    if chi.conductor()%2 == 1:
        if chi.conductor()%4 == 1:
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" %(chi.conductor())
        else:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" %(chi.conductor())  
    elif chi.conductor()%8 == 4:
        if m%4 == 1:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" %(chi.conductor())
        elif m%4 == 3:
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" %(chi.conductor())
    elif chi.conductor()%16 == 8:
        if chi.is_even():
            return r"\(\displaystyle\left(\frac{%s}{\bullet}\right)\)" %(chi.conductor())
        else:
            return r"\(\displaystyle\left(\frac{-%s}{\bullet}\right)\)" %(chi.conductor()) 
    else:
        return None
