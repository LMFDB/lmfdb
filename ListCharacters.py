#ListCharacters.py

import re

from flask import render_template, url_for, make_response
from sage.all import *
import tempfile, os
import pymongo
from WebCharacter import *
from utils import to_dict

def characterlist_modulus(N,type):
    from sage.modular.dirichlet import DirichletGroup
    G = DirichletGroup(N)
    primitive = []
    all = []
    tf = []
    for i in range(0,len(G)):
        if G[i].is_primitive():
            primitive.append(i)
            tf.append('True')
        else:
            all.append(G[i])
            tf.append('False')
    
    s = '<table align=left cellpadding="3">\n'
    #s += '<tr>\n<th scope="row"> Characters modulo ' + str(N) + '</th>\n</tr>\n'
    stop = 'False'
    align_count = 1
    for j in range(0,len(G)):
        if j == 0 or stop == 'True':
            s += '<tr>'
            stop = 'False'
        s += '<td><a align=left'
        s += 'style=\'display:inline\' '
        s += 'href="'
        s += str(N)
        s += '/'
        s += str(j)
        s += '">'
        if tf[j] == 'False':
            s += '<font color = "red">'
        s += '\(\chi_{' + str(j) + '}\)</a></td>'
        #s += '</tr>'
        if (align_count%20 == 0):
            s += '</tr>'
            stop = 'True'
        align_count += 1
    s += '</table>\n'

    if type == "primitive":
        return(primitive)
    elif type == "list":
        return s
    else:
        return(all)

def characterlist_conductor(N,pagenumber,type):
    #charlist = []
    modulus = []
    number = []
    tf = []
    #if N > 200:
    #    return "Conductor to large. FIX THIS!!!"
    M = 201
    #pglessone = pagenumber-1
    if(pagenumber == 1):
        a = N
        b = M
    else:
        a = (pagenumber-1)*M
        b = pagenumber*M
    for v in range(a,b):
        if v%N == 0:
            from sage.modular.dirichlet import DirichletGroup
            G = DirichletGroup(v)
            count = -1
            for chi in G:
                count += 1
                if chi.conductor() == N:
                    if chi.is_primitive():
                        tf.append('True')
                    else:                                                                             tf.append('False')
                    modulus.append(chi.modulus())
                    #charlist.append(chi)
                    number.append(count)
            
    s = '<table align=left cellpadding = "8">'
    #s += '<tr>\n<th scope="row"> Characters modulo ' + str(N) + '</th>\n</tr>\n'
    stop = 'False'
    align_count = 1 
    for j in range(0,len(number)):
        if j == 0 or stop == 'True':
            s += '<tr>'
            stop = 'False'
        s += '<td><a align=left'
        s += 'style=\'display:inline\' '
        s += 'href="'
        s += str(modulus[j])
        s += '/'
        s += str(number[j])
        s += '">'
        if tf[j] == 'False':
            s += '<font color = "red">'
        s += '\(\chi_{' + str(number[j]) + '}\\!\\!\pmod{'+ str(modulus[j]) + '}\)</a></td>'
        #s += '</tr>'
        if align_count%8 == 0:
            s += '</tr>'
            stop = 'True'
        align_count += 1
    s += '<tr><td colspan = "8" align="right"><a href="conductor'
    s += str(N)
    s += '.'
    s += str(pagenumber+1)
    s += '"><font color="blue">higher moduli &rarr;</font></a>'
    s += '</table>'

    if type == "primitive":
        return(primitive)
    elif type == "list":
        return s
    else: 
        return(all)

def characterlist_order(N,kronecker,pagenumber,type):
    modulus = []
    number = []
    tf = []
    charlist = []
    conductor = []
    M = 100
    #if N > 200:
    #    return "Order to large. FIX THIS!!!"
    if(pagenumber == 1):
        a = 2
        b = M
    else:
        a = (pagenumber-1)*M
        b = pagenumber*M
    for v in range(a,b):
        from sage.modular.dirichlet import DirichletGroup
        G = DirichletGroup(v)
        count = -1
        for chi in G:
            count += 1
            if chi.multiplicative_order() == N:
                if chi.is_primitive():
                    tf.append('True')
                else:
                    tf.append('False')
                conductor.append(chi.conductor())
                modulus.append(chi.modulus())
                charlist.append(chi)
                number.append(count)
    if kronecker == 'True':
        s = '<table align="left" cellpadding="20">'
    else:
        s = '<table align="left" cellpadding = "12">'
    #s += '<tr>\n<th scope="row"> Characters modulo ' + str(N) + '</th>\n</tr>\n'
    stop = 'False'
    align_count = 1
    for j in range(0,len(number)):
        if j == 0 or stop == 'True':
            s += '<tr>'
            stop = 'False'
        s += '<td><a align=left'
        s += 'style=\'display:inline\' '
        s += 'href="'
        s += str(modulus[j])
        s += '/'
        s += str(number[j])
        s += '">'
        if tf[j] == 'False':
            s += '<font color = "red">'
        if kronecker == 'True':
            if conductor[j]%2 == 1:
                s += '\(\\left(\\frac{\\bullet}{' + str(conductor[j]) + '}\\right)\\!\\!\\pmod{'+ str(modulus[j]) + '}\)'
            else:
                if charlist[j].is_even():
                    s += '\(\\left(\\frac{\\bullet}{' + str(conductor[j]) + '}\\right)\\!\\!\\pmod{'+ str(modulus[j]) + '}\)'
                else:
                    s += '\(\\left(\\frac{\\bullet}{' + str(conductor[j]) + '}\\right)\\cdot\\left(\\frac{-1}{\\bullet}\\right)\\!\\!\\pmod{'+ str(modulus[j]) + '}\)'
        else:
            s += '\(\\chi_{' + str(number[j]) + '}\\!\\!\\pmod{'+ str(modulus[j]) + '}\)'
        s += '</a></td>'
        if kronecker == 'False':
            if align_count%8 == 0:
                s += '</tr>'
                stop = 'True'
        else:
            if align_count%5 == 0:
                s += '</tr>'
                stop = 'True'
        align_count += 1
    if(kronecker == 'True'):
        s += '<tr><td colspan = "5" align="right"><a href="kronecker'
    else:
        s += '<tr><td colspan = "8" align="right"><a href="order'
        s += str(N)
    s += '.'
    s += str(pagenumber+1)
    s += '"><font color="blue">higher moduli &rarr;</font></a>'
    s += '</table>'

    if type == "primitive":
        return(primitive)
    elif type == "list":
        return s
    else:
        return(all)

def charactertable(Nmin, Nmax, type):
    ans = []
    print 'min max', Nmin, Nmax
    for i in range(Nmin, Nmax+1):
        ans.append([i, characterlist(i,type)])
    return(ans)

def processDirichletNavigation(args):
    from sage.rings.arith import euler_phi
    s = '<table>\n'
    s += '<tr>\n<th scope="col">Characters</th>\n</tr>\n'
    for i in range(0,len(G)):
        s += '<tr>\n<th scope="row">' + str(i) + '</th>\n'
        s += '<td>\n'
        j = i-N
        for k in range(len(chars[j][1])):
            s += '<a style=\'display:inline\' href="Character/Dirichlet/'
            s += str(i)
            s += '/'
            s += str(chars[j][1][k])
            s += '/&numcoeff='
            s += str(numcoeff)
            s += '">'
            s += '\(\chi_{' + str(chars[j][1][k]) + '}\)</a> '
        s += '</td>\n</tr>\n'
    s += '</table>\n'
    return s
