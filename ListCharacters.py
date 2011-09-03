#ListCharacters.py

import re

from flask import render_template, url_for, make_response
from sage.all import *
import tempfile, os
import pymongo
from WebCharacter import *
from utils import to_dict

def get_character_modulus(a,b):
    from sage.modular.dirichlet import DirichletGroup
    def line(N):
        G = DirichletGroup(N)
        return [(_, G[_].is_primitive()) for _ in range(len(G))]
    return [(_,line(_)) for _ in range(a,b+1)]

def get_character_conductor(a,b):
    from sage.modular.dirichlet import DirichletGroup
    def line(N):
        l = []
        count = 0
        modulus = N
        while count < 24:
            if modulus%N == 0:
                G = DirichletGroup(modulus)
                chi_count = 0
                for j in range(len(G)):
                    if G[j].conductor() == N:
                        l.append((modulus,j,G[j].is_primitive()))
                        chi_count += 1
            count += chi_count
            modulus += N
            if count == 0:
                break
        return l 
    return [(_,line(_)) for _ in range(a,b)]

def get_character_order(a,b):
    from sage.modular.dirichlet import DirichletGroup
    def line(N):
        l = []
        count = 0
        for modulus in range(N,250):
            G = DirichletGroup(modulus)
            chi_count = 0
            for j in range(len(G)):
                if G[j].multiplicative_order() == N:
                    l.append((modulus,j,G[j].is_primitive()))
                    count += 1
                    if count >= 24:
                        break
            if count >= 24:
                break
        return l
    return [(_,line(_)) for _ in range(a,b)]

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
