#DirichletCharacter.py

import re
import logging 

from base import app
import flask
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import *
import tempfile, os
from pymongo import ASCENDING
from WebCharacter import *
from utils import to_dict, parse_range
import ListCharacters

def render_webpage(request,arg1,arg2):
    args = request.args
    temp_args = to_dict(args)
    if len(args) == 0: # no arguments set yet
        if arg1 == None: # this means we're at the start page
            info = set_info_for_start_page() # sets info for character navigate
            info['credit'] = 'Sage'
            return render_template("dirichlet_characters/CharacterNavigate.html", **info)

        elif arg1.startswith("modbrowse"):
            print "Check2"
            modulus_start = int(arg1.partition('-')[0][10:])
            modulus_end = int(arg1.partition('-')[2])
            info = {}
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Moduli '+str(modulus_start) + '-' + str(modulus_end), '/Character/Dirichlet/modbrowse='+str(modulus_start)+'-'+str(modulus_end))]
            info['title'] = 'Moduli ' +str(modulus_start)+'-'+str(modulus_end)
            info['credit'] = 'Sage'
            info['contents'] = ListCharacters.get_character_modulus(modulus_start,modulus_end)
            return render_template("dirichlet_characters/ModulusList.html", **info)


        elif arg1.startswith("condbrowse"):
            conductor_start = int(arg1.partition('-')[0][11:])
            conductor_end = int(arg1.partition('-')[2])
            info = {}
            info['conductor_start'] = conductor_start
            info['conductor_end'] = conductor_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Conductor '+str(conductor_start) + '-' + str(conductor_end), '/Character/Dirichlet/condsearch='+str(conductor_start)+'-'+str(conductor_end))]
            info['title'] = 'Conductors ' +str(conductor_start)+'-'+str(conductor_end)
            info['credit'] = 'Sage'
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
    
        chi = WebCharacter(temp_args)

        print chi

        try:
            print temp_args
        except:
            1

        info = initCharacterInfo(chi, temp_args, request) # sets the various properties of chi to be displayed in DirichletCharacter.html

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
    info['learnmore'] = [('Dirichlet Characters', 'http://wiki.l-functions.org/L-function')]
    info['friends'] = [('Dirichlet L-functions', '/Lfunction/degree1#Dirichlet')]
    return info

def initCharacterInfo(chi,args, request):
    info = {'title': chi.title}
    info['citation'] = ''
    info['support'] = ''
    info['args'] = args

    info['credit'] = 'Sage'
    info['citation'] = chi.citation

    try:
        info['url'] = chi.url
    except:
        info['url'] =''

    info['bread'] = []
    info['properties'] = chi.properties

    if args['type'] == 'dirichlet':
        snum = str(chi.number)
        info['number'] = snum
        smod = str(chi.modulus)
        info['modulus'] = smod
        info['bread'] = [('Characters','/Characters'),('Dirichlet Characters','/Character/Dirichlet'),('Character '+snum+ ' modulo '+smod,'/Character/Dirichlet/'+smod+'/'+snum)]
        info['sagechar'] = str(chi.sagechar)
        info['conductor'] = int(chi.conductor)
        info['order'] = int(chi.order)
        info['eulerphi'] = euler_phi(chi.modulus)-1
        info['nextmodulus'] = chi.modulus+1
        info['primitive'] = chi.primitive
        info['zetaorder'] = chi.zetaorder
        info['genvals'] = str(chi.genvalues)
        info['genvalstex'] = str(chi.genvaluestex)
        info['parity'] = chi.parity
        info['sign'] = chi.sign
        info['vals'] = latex(chi.vals)
        info['valstex'] = chi.valstex
        info['unitgens'] = str(chi.unitgens)
        #print chi.unitgens
        info['bound'] = int(chi.bound)
        #print chi.bound
        info['lth'] = int(chi.lth)
        #print chi.lth
        info['primchar'] = chi.primchar
        info['primcharmodulus'] = chi.primcharmodulus
        info['primcharconductor'] = chi.primcharconductor
        info['primcharnumber'] = chi.primcharnumber
        info['primchartex'] = chi.primchartex
        info['primtf'] = chi.primtf
        info['nextnumber'] = chi.number+1
        info['kronsymbol'] = str(chi.kronsymbol)
        info['gauss_sum'] = chi.gauss_sum_tex()
        info['jacobi_sum'] = chi.jacobi_sum_tex()
        info['kloosterman_sum'] = chi.kloosterman_sum_tex()
        info['learnmore'] = [('Dirichlet Characters', 'http://wiki.l-functions.org/L-functions') ] 
        info['friends'] = [('Dirichlet L-function', '/L/Character/Dirichlet/'+smod+'/'+snum)]

    return info

@app.route("/Character/Dirichlet/<modulus>/<number>")
def character_next_modulus(modulus,number):
    return render_webpage(request,modulus,number)

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
        return "\(%s\)" %(latex(gauss_sum_numerical))
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/calc_jacobi/<int:modulus>/<int:number>")
def dc_calc_jacobi(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    arg = map(int,arg.split('.'))
    try:
        mod = arg[0]
        num = arg[1]
        from sage.modular.dirichlet import DirichletGroup
        chi = DirichletGroup(modulus)[number]
        psi = DirichletGroup(mod)[num]
        jacobi_sum = chi.jacobi_sum(psi)
        return "\(%s\)" %(latex(jacobi_sum))
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
        return "\(%s\)" %(latex(kloosterman_sum_numerical))
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
            t,texname,number,length  = charactertable(query)
            info['characters'] = t
            info['texname'] = texname
            info['number'] = number
            info['len'] = length
            info['title'] = 'Dirichlet Characters'
            return render_template("dirichlet_characters/character_search.html", **info)

def charactertable(query):
    if(len(query) == 1):
        if 'modulus' in query:
            modulus = query['modulus']
            return charactertable_modulus(modulus)
        elif 'conductor' in query:
            conductor = query['conductor'] 
            return charactertable_conductor(conductor)
        elif 'order' in query:
            order = query['order']
            return charactertable_order(order)
    elif (len(query) == 2):
        if ('modulus' in query) and ('conductor' in query):
            modulus = query['modulus']
            conductor = query['conductor']
            return charactertable_modcond(modulus,conductor)
        elif ('modulus' in query) and ('order' in query):
            modulus = query['modulus']
            order = query['order']
            return charactertable_modorder(modulus,order)
        else:
            conductor = query['conductor']
            order = query['order']
            return charactertable_condorder(conductor,order)
    elif (len(query) == 3):
        modulus = query['modulus']
        conductor = query['conductor']
        order = query['order']
        return charactertable_modcondorder(modulus,conductor,order)

def charactertable_modulus(N):
    G = DirichletGroup(N)
    texname = []
    chars = []
    number = []
    j = 0
    for v in G:
        number.append(j)
        s = "\(\\chi_{" + str(j) + "}\)"
        texname.append(s)
        chars.append(v)
        j += 1
    return chars,texname,number,len(G)

def charactertable_conductor(N):
    #print N
    texname = []
    chars = []
    number = []
    count = 0
    for a in range(N,201): #TODO FIX THIS TO TAKE INTERVALS
        if a%N == 0:
            G = DirichletGroup(a)
            j = 0
            for chi in G:
                if chi.conductor() == N:
                    count += 1
                    number.append(j)
                    s = "\(\\chi_{" + str(j) + "}\)"
                    texname.append(s)
                    chars.append(chi)
                j += 1
    return chars,texname,number,count

def charactertable_order(N):
    texname = []
    chars = []
    number = []
    count = 0
    for a in range(2,200):
        G = DirichletGroup(a)
        j=0
        for chi in G:
            if chi.multiplicative_order() == N:
                count += 1
                number.append(j)
                s = "\(\\chi_{" + str(j) + "}\)"
                texname.append(s)
                chars.append(chi)
            j += 1
    return chars,texname,number,count

def charactertable_modcond(N,M):
    G = DirichletGroup(N)
    texname = []
    chars = []
    number = []
    j = 0
    count = 0
    for chi in G:
        if chi.conductor() == M:
            count += 1
            number.append(j)
            s = "\(\\chi_{" + str(j) + "}\)"
            texname.append(s)
            chars.append(chi)
        j += 1
    return chars,texname,number,count

def charactertable_modorder(N,M):
    G = DirichletGroup(N)
    texname = []
    chars = []
    number = []
    j = 0
    count = 0
    for chi in G:
        if chi.multiplicative_order() == M:
            count += 1
            number.append(j)
            s = "\(\\chi_{" + str(j) + "}\)"
            texname.append(s)
            chars.append(chi)
        j += 1
    return chars,texname,number,count

def charactertable_condorder(N,M):
    texname = []
    chars = []
    number = []
    count = 0
    for a in range(N,201): #TODO FIX THIS TO TAKE INTERVALS
        if a%N == 0:
            G = DirichletGroup(a)
            j = 0
            for chi in G:
                if (chi.conductor() == N) and (chi.multiplicative_order() == M):
                    count += 1
                    number.append(j)
                    s = "\(\\chi_{" + str(j) + "}\)"
                    texname.append(s)
                    chars.append(chi)
                j += 1
    return chars,texname,number,count

def charactertable_modcondorder(N,M,O):
    G = DirichletGroup(N)
    texname = []
    chars = []
    number = []
    j = 0
    count = 0
    for chi in G:
        if (chi.conductor() == M) and (chi.multiplicative_order() == O):
            count += 1
            number.append(j)
            s = "\(\\chi_{" + str(j) + "}\)"
            texname.append(s)
            chars.append(chi)
        j += 1
    return chars,texname,number,count

