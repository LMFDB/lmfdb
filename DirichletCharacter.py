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
#from renderLfunction import render_Lfunction
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
            info['title'] = 'Dirichlet Characters of Moduli ' +str(modulus_start)+'-'+str(modulus_end)
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
            info['title'] = 'Dirichlet Characters of Conductors ' +str(conductor_start)+'-'+str(conductor_end)
            info['credit'] = "Sage"
            info['contents']  = ListCharacters.get_character_conductor(conductor_start,conductor_end+1)
            #info['contents'] = c
            #info['header'] = h 
            #info['rows'] = rows
            #info['cols'] = cols
            return render_template("dirichlet_characters/ConductorList.html", **info)

        elif arg1.startswith("ordbrowse"):
            order_start = int(arg1.partition('-')[0][10:])
            order_end = int(arg1.partition('-')[2])
            info = {}
            info['order_start'] = order_start
            info['order_end'] = order_end
            info["bread"] = [('Dirichlet Characters', url_for("render_Character")), ('Order '+str(order_start) + '-' + str(order_end), '/Character/Dirichlet/ordbrowse='+str(order_start)+'-'+str(order_end))]
            info['title'] = 'Dirichlet Characters of Orders ' +str(order_start)+'-'+str(order_end)
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

        mod,num = Integer(str(arg1)), Integer(str(arg2))
        if mod<=0 or num <0 or mod<num or gcd(mod,num) != 1:
            info = {}
            info['message'] = """ modulus=%s,number=%s does not correspond to
            a valid Dirichlet character name.
            """ % (arg1,arg2)
            #See our <a href="%s">naming conventions</a>.
            return render_template("404.html",**info), 404
            #return 'invalid Dirichlet character name'
            
        web_chi = WebCharacter(temp_args)

        #try:
        #    print temp_args
        #except:
        #    1

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
    #info['learnmore'] = [('Dirichlet Characters', url_for("knowledge.show", ID="character.dirichlet.learn_more_about"))]
    info['friends'] = [('Dirichlet L-functions', url_for("render_Lfunction", arg1="degree1"))]
    return info

def initCharacterInfo(web_chi, args, request):
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
        snum = str(web_chi.number)
        info['number'] = snum
        smod = str(web_chi.modulus)
        info['modulus'] = smod
        G = DirichletGroup_conrey(web_chi.modulus)
        if web_chi.modulus > 1:
          G_prev = DirichletGroup_conrey(web_chi.modulus -1)
        else:
          G_prev = None
        chi = G[web_chi.number]
        chi_sage = chi.sage_character()
        indices = []
        info['bread'] = [('Dirichlet Characters','/Character/Dirichlet'),('Character '+snum+ ' modulo '+smod,'/Character/Dirichlet/'+smod+'/'+snum)]
        info['char'] = str(web_chi.char)
        info['chisage'] = str(web_chi.chi_sage)
        info['conductor'] = int(web_chi.conductor)
        info['order'] = int(web_chi.order)
        info['eulerphi'] = euler_phi(web_chi.modulus)-1
        info['nextmodulus'] = web_chi.modulus+1
        info['primitive'] = web_chi.primitive
        info['zetaorder'] = web_chi.zetaorder
        #info['genvals'] = str(web_chi.genvalues)
        info['genvalstex'] = str(web_chi.genvaluestex)
        info['parity'] = web_chi.parity
        #info['sign'] = web_chi.sign  ## removed by Pascal (syn parity)
        info['real'] = web_chi.real
        info['prim'] = web_chi.prim
        info['vals'] = web_chi.vals
        info['logvals'] = web_chi.logvals
        #info['galoisorbits'] = web_chi.galoisorbits
        #info['root_unity'] =  str(any(map(lambda x : r"\zeta" in x,  web_chi.vals)))
        #  Code works, but currently not run
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
        #info['learnmore'] = [('Dirichlet Characters', url_for("knowledge.show", ID="character.dirichlet.learn_more_about"))] 
        if web_chi.primitive=="False":
            info['friends'] = []
        else:
            info['friends'] = [('Dirichlet L-function', '/L/Character/Dirichlet/'+smod+'/'+snum)]
        if web_chi.nf_friend != '': # Don't add yet since this is currently always ''
            info['friends'].append(('Number Field', web_chi.nf_friend))

        info['navi'] = getPrevNextNavig(web_chi.modulus, web_chi.number, "character")
        
    return info

def getPrevNextNavig(modulus,number,mode='character'):
    """
    Returns the contents for info['navi'] which is the
    navigation to the next and previous character or
    the corresponding L-function
    Mode is either "character" or "L"
    In case of L-function, restrict to primitive characters.
    """
    if mode == "character":
        name_pattern = r"\(\chi_{%s}(%s,&middot;)\)"
        onlyprimitive = False
    else:
        name_pattern = r"\(L(s,\chi_{%s}(%s,&middot;))\)"
        onlyprimitive = True

    next_mod, next_number = next_char(modulus,number,onlyprimitive)
    next_name = name_pattern % (next_mod,next_number)
    next_url = getUrl(next_mod, next_number, mode)

    if modulus == 1:
        # no previous character
        return [("", ""), (next_name, next_url)]

    prev_mod, prev_number = prev_char(modulus,number,onlyprimitive)
    prev_name = name_pattern % (prev_mod,prev_number)
    prev_url = getUrl(prev_mod, prev_number, mode)
    
    return [(prev_name, prev_url), (next_name, next_url)]
     
def next_char(m,n,onlyprimitive=False):
    """ we know that the characters
        chi_m(1,.) and chi_m(m-1,.)
        always exist for m>1.
        They are extremal for a given m.
    """
    if onlyprimitive: return next_primitive_char(m,n)
    if m == 1: return 2,1
    if n == m-1: return m+1,1
    for k in xrange(n+1,m):
        if gcd(m,k)==1: return m,k
    raise Exception("next_char")

def prev_char(m,n,onlyprimitive=False):
    """ Assume m>1 """
    if onlyprimitive: return prev_primitive_char(m,n)
    if n == 1: m,n = m-1,m
    if m <= 2: return m,1 # important : 2,2 is not a character
    for k in xrange(n-1,0,-1):
        if gcd(m,k)==1: return m,k
    raise Exception("next_char")

def prev_primitive_char(m,n):
    if m<=3: return 1,1
    if n>2: Gm = DirichletGroup_conrey(m)
    while True:
        n-=1
        if n==1: # (m,1) is never primitive for m>1
            m,n=m-1,m-1
            Gm = DirichletGroup_conrey(m)
        if m<=2: return 1,1
        if gcd(m,n) != 1: continue
        # we have a character, test if it is primitive
        chi = Gm[n]
        if chi.is_primitive(): return m,n

def next_primitive_char(m,n):
    if m<3: return 3,2
    if n < m-1: Gm = DirichletGroup_conrey(m)
    while 1:
        n+=1
        if n==m:
            m,n=m+1,2
            Gm = DirichletGroup_conrey(m)
        if gcd(m,n) != 1: continue
        # we have a character, test if it is primitive
        chi = Gm[n]
        if chi.is_primitive(): return m,n


def getUrl(modulus, number, mode):
    if mode == "character":
        return url_for("render_Character", arg1=modulus, arg2=number)
    else:
        return url_for("render_Lfunction", arg1 = 'Character', arg2 = 'Dirichlet',
                arg3=modulus, arg4=number)

@app.route("/Character/Dirichlet/<modulus>/<number>")
def render_webpage_label(modulus,number):
    return render_webpage(request,modulus,number)

@app.route("/Character/Dirichlet/calc_gauss/<int:modulus>/<int:number>")
def dc_calc_gauss(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    try:
        if modulus == 1:
            # there is a bug in sage for modulus = 1
            return r"""\(\displaystyle \tau_{%s}(\chi_{1}(1,&middot;)) =
          \sum_{r\in \mathbb{Z}/\mathbb{Z}} \chi_{1}(1,r) 1^{%s}= 1. \)""" %(int(arg),int(arg))
        from dirichlet_conrey import DirichletGroup_conrey
        chi = DirichletGroup_conrey(modulus)[number]
        chi = chi.sage_character()
        g = chi.gauss_sum_numerical(100,int(arg))
        real = round(g.real(),10)
        imag = round(g.imag(),10)
        if imag == 0.:
            g = str(real)
        elif real == 0.:
            g = str(imag) + "i"
        else:
            g = latex(g)
        from sage.rings.rational import Rational
        x = Rational('%s/%s' %(int(arg),modulus))
        n = x.numerator() 
        n = str(n)+"r" if not n == 1 else "r"
        d = x.denominator()
        return r"\(\displaystyle \tau_{%s}(\chi_{%s}(%s,&middot;)) = \sum_{r\in \mathbb{Z}/%s\mathbb{Z}} \chi_{%s}(%s,r) e\left(\frac{%s}{%s}\right) = %s. \)" %(int(arg),modulus,number,modulus,modulus,number,n,d,g)
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
        from dirichlet_conrey import DirichletGroup_conrey
        chi = DirichletGroup_conrey(modulus)[number]
        psi = DirichletGroup_conrey(modulus)[num]
        chi = chi.sage_character()
        psi = psi.sage_character()
        jacobi_sum = chi.jacobi_sum(psi)
        return r"\( \displaystyle J(\chi_{%s}(%s,&middot;),\chi_{%s}(%s,&middot;)) = \sum_{r\in \mathbb{Z}/%s\mathbb{Z}} \chi_{%s}(%s,r) \chi_{%s}(%s,1-r) = %s.\)" %(modulus,number,modulus,num,modulus,modulus,number,modulus,num,latex(jacobi_sum))  
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/calc_kloosterman/<int:modulus>/<int:number>")
def dc_calc_kloosterman(modulus,number):
    arg = request.args.get("val", [])
    if not arg:
        return flask.abort(404)
    try:
        a,b = map(int,arg.split(','))
        if modulus == 1:
            # there is a bug in sage for modulus = 1
            return r"""
            \( \displaystyle K(%s,%s,\chi_{1}(1,&middot;))
            = \sum_{r \in \mathbb{Z}/\mathbb{Z}}
                 \chi_{1}(1,r) 1^{%s r + %s r^{-1}}
            = 1 \)
            """ % (a,b,a,b)
        from dirichlet_conrey import DirichletGroup_conrey
        chi = DirichletGroup_conrey(modulus)[number]
        chi = chi.sage_character()
        k = chi.kloosterman_sum_numerical(100,a,b)
        real = round(k.real(),5)
        imag = round(k.imag(),5)
        if imag == 0:
            k = str(real)
        elif real == 0:
            k = str(imag) + "i"
        else:
            k = latex(k)
        return r"""
        \( \displaystyle K(%s,%s,\chi_{%s}(%s,&middot;))
        = \sum_{r \in \mathbb{Z}/%s\mathbb{Z}}
             \chi_{%s}(%s,r) e\left(\frac{%s r + %s r^{-1}}{%s}\right)
        = %s. \)""" %(a,b,modulus,number, modulus, modulus,number,a,b,modulus,k)
    except Exception, e:
        return "<span style='color:red;'>ERROR: %s</span>" % e

@app.route("/Character/Dirichlet/<modulus>/<number>")
def redirect_character(modulus,number):
    return render_webpage(request,modulus,number)

def character_search(**args):
    info = to_dict(args)
    for field in ['modulus', 'conductor', 'order']:
        info[field] = info.get(field,'')
    query = {}
    print "args = ", args
    if 'natural' in args:
        label = info.get('natural', '')
        try:
            modulus = int(str(label).partition('.')[0])
            number = int(str(label).partition('.')[2])
        except ValueError:
            return "<span style='color:red;'>ERROR: bad query</span>"
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
        else:
            return "<span style='color:red;'>ERROR: bad query</span>"

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
            add &= not order     or chi.multiplicative_order() == order
            if add:
                if chi.multiplicative_order() == 2 and kronecker_symbol(chi) != None:
                    ret.append([(j, kronecker_symbol(chi), chi.modulus(), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
                else:
                    ret.append([(j,chi, chi.modulus(), chi.conductor(), chi.multiplicative_order(), chi.is_primitive(), chi.is_even())])
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

@app.route("/Character/Dirichlet/table")
def dirichlet_table(**args):
    modulus = request.args.get("modulus", 1, type=int)
    info = to_dict(args)
    if "modulus" not in info:
      info["modulus"] = modulus
    info["bread"] = [('Dirichlet Character Table', url_for("dirichlet_table")), ('result', ' ')]
    info['credit'] = 'Sage'
    char_number_list = request.args.get("char_number_list")
    if char_number_list is not None:
      info['char_number_list'] = char_number_list
      char_number_list = [int(a) for a in char_number_list.split(',')]
      info['poly'] = request.args.get("poly", '???')
    h, c, = get_entries(modulus, char_number_list)
    info['headers'] = h
    info['contents'] = c
    info['title'] = request.args.get("title", 'Dirichlet Characters')
    return render_template("/dirichlet_characters/CharacterTable.html",**info)

def get_entries(modulus, char_number_list=None):
    from dirichlet_conrey import DirichletGroup_conrey
    from sage.all import Integer
    from WebCharacter import log_value 
    G = DirichletGroup_conrey(modulus)
    headers = range(1,modulus+1)
    e = euler_phi(modulus)
    rows = []
    for chi in G:
        is_prim = chi.is_primitive()
        number = chi.number()
        if char_number_list is None or number in char_number_list:
            rows.append((number,is_prim, log_value(modulus,number)))
    return headers, rows

