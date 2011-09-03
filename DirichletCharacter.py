#DirichletCharacter.py

import re
import logging 

from base import app
from flask import Flask, session, g, render_template, url_for, make_response, request, redirect
from sage.all import *
import tempfile, os
from pymongo import ASCENDING
from WebCharacter import *
import Lfunction
import LfunctionNavigationProcessing
import LfunctionPageProcessing
import LfunctionComp
import LfunctionPlot
from utils import to_dict, parse_range
import ListCharacters

@app.route("/Character/Dirichlet")
def render_webpage(request,arg1,arg2):
    args = request.args
    temp_args = to_dict(args)
    if len(args) == 0: # no arguments set yet
        if arg1 == None: # this means we're at the start page
            info = set_info_for_start_page() # sets info for character navigate
            info['credit'] = 'Matthew Alderson'
            return render_template("dirichlet_characters/CharacterNavigate.html", info = info, title = 'Dirichlet Characters', credit = info['credit'],bread = info['bread'])
        
        elif arg1.startswith("modulus"):
            modulus = int(arg1.partition('.')[0][7:])
            info = {}
            info["modulus"] = modulus
            info["key"] = 777
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Modulus '+str(modulus), '/Character/Dirichlet/modulus'+str(modulus))]
            info["contents"] = ListCharacters.characterlist_modulus(modulus,'list')
            eulerphi = euler_phi(modulus)
            info['properties'] = ['<table><tr><td align=left>\(\\phi(%s)\) = '%(modulus),'<td align=left> %s</td>'%(eulerphi)] 
            info['credit'] = 'Matthew Alderson'
            #lra = "\(\\longrightarrow\)"
            #info["properties"] = "Color Scheme:<ul><li> Red " + str(lra) + " <font color=red> non-primitive</font> characters </br><li> Green " +  str(lra) + " <font color=green> primitive </font> characters </ul>"

            return render_template("dirichlet_characters/ModulusNavigate.html", info=info, title = 'Dirichlet Characters modulo ' + str(modulus), bread = info["bread"],credit=info['credit'])
        
        elif arg1.startswith("modbrowse"):
            modulus_start = int(arg1.partition('-')[0][10:])
            modulus_end = int(arg1.partition('-')[2])
            info = {}
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Moduli '+str(modulus_start) + '-' + str(modulus_end), '/Character/Dirichlet/modbrowse='+str(modulus_start)+'-'+str(modulus_end))]
            title = 'Moduli ' +str(modulus_start)+'-'+str(modulus_end)
            info['credit'] = 'Matthew Alderson'
            info['contents'] = ListCharacters.get_character_modulus(modulus_start,modulus_end)
            return render_template("dirichlet_characters/ModulusList.html", info=info,title=title,bread=info["bread"],credit=info['credit'])

        elif arg1.startswith("conductor"):
            conductor = int(arg1.partition('.')[0][9:])
            pagenumber = int(arg1.partition('.')[2])
            M = 200
            info = {}
            info["pgplusone"] = pagenumber+1
            info["conductor"] = conductor
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Conductor '+str(conductor), '/Character/Dirichlet/conductor'+str(conductor))]
            if(pagenumber == 1):
                title = 'Dirichlet Characters of conductor ' + str(conductor) +', up to modulus ' + str(M)
            else:
                title = 'Dirichlet Characters of conductor ' + str(conductor) + ', moduli from ' + str((pagenumber-1)*M) + ' to ' + str(pagenumber*M) 
            info["contents"] = ListCharacters.characterlist_conductor(conductor,pagenumber,'list')
            info['credit'] = 'Matthew Alderson'
            return render_template("dirichlet_characters/ConductorNavigate.html", info=info, title = title, bread = info["bread"], credit=info['credit'])

        elif arg1.startswith("condbrowse"):
            conductor_start = int(arg1.partition('-')[0][11:])
            conductor_end = int(arg1.partition('-')[2])
            info = {}
            info['conductor_start'] = conductor_start
            info['conductor_end'] = conductor_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Conductor '+str(conductor_start) + '-' + str(conductor_end), '/Character/Dirichlet/condsearch='+str(conductor_start)+'-'+str(conductor_end))]
            title = 'Conductors ' +str(conductor_start)+'-'+str(conductor_end)
            info['credit'] = 'Matthew Alderson'
            info['contents'] = ListCharacters.get_character_conductor(conductor_start,conductor_end+1)
            return render_template("dirichlet_characters/ConductorList.html", info=info,title=title,bread=info["bread"], credit=info['credit'])

        elif arg1.startswith("order"):
            order = int(arg1.partition('.')[0][5:])
            pagenumber = int(arg1.partition('.')[2])
            info = {}
            M = 100
            kronecker = 'False'
            info["pagenumber"] = pagenumber
            info["kronecker"] = kronecker
            info["order"] = order
            if order == 2:
                if(pagenumber==1):
                    title = 'Quadratic Characters, up to modulus ' + str(M)
                else:
                    title = 'Quadratic Characters, moduli from ' + str((pagenumber-1)*M) + ' to ' + str(pagenumber*M)
            elif order == 3:
                if(pagenumber==1):
                    title = 'Cubic Characters, up to modulus ' + str(M)
                else:
                    title = 'Cubic Characters,  moduli from ' + str((pagenumber-1)*M) + ' to ' + str(pagenumber*M)
            else:
                if(pagenumber==1):
                    title = 'Characters of order ' + str(order) + ', up to modulus ' + str(M)
                else:
                    title = 'Characters of order ' + str(order) + ', moduli from ' + str((pagenumber-1)*M) + ' to ' + str(pagenumber*M)

            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Order ' +str(order), '/Character/Dirichlet/order'+str(order))]
            info["contents"] = ListCharacters.characterlist_order(order,kronecker,pagenumber,'list')
            info['credit'] = 'Matthew Alderson'
            return render_template("dirichlet_characters/OrderNavigate.html", info=info, title = title , bread = info["bread"], credit=info['credit'])
       
        
        elif arg1.startswith("ordbrowse"):
            order_start = int(arg1.partition('-')[0][10:])
            order_end = int(arg1.partition('-')[2])
            info = {}
            info['order_start'] = order_start
            info['order_end'] = order_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Order '+str(order_start) + '-' + str(order_end), '/Character/Dirichlet/ordbrowse='+str(order_start)+'-'+str(order_end))]
            title = 'Order ' +str(order_start)+'-'+str(order_end)
            info['credit'] = 'Matthew Alderson'
            info['contents'] = ListCharacters.get_character_order(order_start, order_end+1)
            return render_template("dirichlet_characters/OrderList.html", info=info,title=title,bread=info["bread"],credit=info['credit'])

        elif arg1.startswith("kronecker"):
            order = 2
            #if(len(arg1.partition('.')[2]) == 0):
            #    pagenumber = 1
            #else:
            pagenumber = int(arg1.partition('.')[2])
            M = 100
            info = {}
            info["pagenumber"] = pagenumber
            kronecker = 'True'
            info["kronecker"] = kronecker
            info["order"] = order
            if(pagenumber == 1):
                title = 'Kronecker symbols, up to modulus ' + str(M)
            else:
                title = 'Kronecker symbols, moduli from ' + str((pagenumber-1)*M) + ' to ' + str(pagenumber*M)
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Kronecker symbols', '/Character/Dirichlet/kronecker')]
            info["contents"] = ListCharacters.characterlist_order(order,kronecker,pagenumber,'list')
            info['credit'] = 'Matthew Alderson'
            return render_template("dirichlet_characters/OrderNavigate.html", info=info, title = title, bread = info["bread"], credit=info['credit'])
        
        elif arg1 == 'custom':
            return "not yet implemented"
        
    else:
        return character_search(**args)
        
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

    return render_template('dirichlet_characters/DirichletCharacter.html', info = info, title = info['title'], bread = info['bread'], properties = info['properties'], citation = info['citation'], credit = info['credit'], support = info['support'])


def set_info_for_start_page():
    tl = [{'title':'Dirichlet','link':'degree#1Dirichlet'},
            {'title':'Hecke','link':'Hecke'}] #make the degree 1 ones, should be url_fors

    tt = {}
    tt[1]=tl
    modulus_list_endpoints = [1,100,1000,5000] + range(10000,130001,10000)
    modulus_list = ["%s-%s" %(start,end-1) for start,end in zip(modulus_list_endpoints[:-1], modulus_list_endpoints[1:])]
    info = {'modulus_list': modulus_list, 'conductor_list': range(1,181), 'order_list': range(2,21), 'type_table': tt, 'l':[1]}
    credit = 'Matthew Alderson'
    info['bread'] = [('Dirichlet Characters', url_for("render_Character"))]
    info['learnmore'] = [('Dirichlet Characters', 'http://wiki.l-functions.org/L-function')]
    info['friends'] = [('Dirichlet L-functions', '/Lfunction/degree1#Dirichlet')]
    return info

def initCharacterInfo(chi,args, request):
    info = {'title': chi.title}
    info['citation'] = ''
    info['support'] = ''
    info['args'] = args

    info['credit'] = 'Matthew Alderson'
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
        info['primitive'] = str(chi.primitive)
        info['genvals'] = str(chi.genvalues)
        info['genvalstex'] = str(chi.genvaluestex)
        info['vals'] = str(chi.vals)
        info['valstex'] = str(chi.valstex)
        info['unitgens'] = str(chi.unitgens)
        #print chi.unitgens
        info['bound'] = int(chi.bound)
        #print chi.bound
        info['lth'] = int(chi.lth)
        #print chi.lth
        info['primchar'] = str(chi.primchar)
        info['primcharmodulus'] = str(chi.primcharmodulus)
        info['primcharconductor'] = str(chi.primcharconductor)
        info['primcharnumber'] = str(chi.primcharnumber)
        info['primchartex'] = str(chi.primchartex)
        info['primtf'] = str(chi.primtf)
        info['kronsymbol'] = str(chi.kronsymbol)
        info['gauss_sum'] = chi.gauss_sum_tex()
        info['jacobi_sum'] = chi.jacobi_sum_tex()
        info['kloosterman_sum'] = chi.kloosterman_sum_tex()
        info['learnmore'] = [('Dirichlet Characters', 'http://wiki.l-functions.org/L-functions') ] 
        info['friends'] = [('Dirichlet L-function', '/L/Character/Dirichlet/'+smod+'/'+snum)]

    return info

@app.route("/Character/Dirichlet/<modulus>/<number>")
def render_webpage_label(modulus,number):
    return render_webpage(request,modulus,number)

@app.route("/Character/Dirichlet/<modulus>/<conductor>/<number>")
def induced_character(modulus,conductor,number):
    return render_webpage(request,conductor,number)

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
        #print query['modulus'], len(query), query['modulus']['$gte']
        #print "Check 2 = " + str(
        info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('search results', ' ')]
        info['credit'] = 'Matthew Alderson'
        if (len(query) != 0):
            from sage.modular.dirichlet import DirichletGroup
            #if ('modulus' in query) and (len(query['modulus']) == 2):
            #    info['start'] = int(query['modulus']['$gte'])
            #    info['end'] = int(query['modulus']['$lte']
            #    info['list'] = 'True'
            t,texname,number,length  = charactertable(query)
            info['characters'] = t
            info['texname'] = texname
            info['number'] = number
            info['len'] = length
            #print t
            #print texname
            return render_template("dirichlet_characters/character_search.html", info=info, title = 'Dirichlet Characters', bread = info["bread"], credit = info['credit'])

def charactertable(query):
    if(len(query) == 1):
        if 'modulus' in query:
            #if (len(query['modulus']) == 2):
            #    chartable_modulus = []
            #    start = int(query['modulus']['$gte'])
                #info['start'] = start
            #    end = int(query['modulus']['$lte'])
                #info['end'] = end
            #    for modulus in range(start,end+1):
            #        return chartable_modulus.append(charactertable_modulus(modulus))
           # else:
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

