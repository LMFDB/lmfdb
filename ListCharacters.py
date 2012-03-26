#ListCharacters.py

import re

from flask import render_template, url_for, make_response
from sage.all import *
import tempfile, os
import pymongo
from WebCharacter import *
from utils import to_dict
from sage.rings.arith import euler_phi
 
#from dirichlet_conrey import *

def get_character_modulus(a,b):
    from dirichlet_conrey import DirichletGroup_conrey
    #from DirichletCharacter import kronecker_symbol as k
    headers = range(1,7)
    headers.append("more")
    entries = {}
    rows = range(a, b+1)
    for row in rows:
        G = DirichletGroup_conrey(row)
        for chi in G:
            j = chi.number()
            multorder = chi.multiplicative_order()
            el = (j, chi.is_primitive(), multorder)
            col = multorder 
            entry = entries.get((row, col), [])
            entry.append(el)
            entries[(row, col)] = entry
    cols = headers
    return headers, entries, rows, cols

def get_character_conductor(a,b):
    from dirichlet_conrey import DirichletGroup_conrey
    from DirichletCharacter import kronecker_symbol as k
    def line(N):
        l = []
        count = 0
        modulus = N
        while count < 7:
            if modulus%N == 0:
                G = DirichletGroup_conrey(modulus)
                #chi_count = 0
                for j,chi in enumerate(G):
                        if count == 7:
                            break
                        elif chi.conductor() == N:
                            count += 1
                            l.append((modulus,j,chi.is_primitive(),chi.multiplicative_order(),k(chi)))
            modulus += N
            if count == 0:
                break
        print count
        return l 
    return [(_,line(_)) for _ in range(a,b)]

def get_character_order(a,b):
    from dirichlet_conrey import DirichletGroup_conrey
    from DirichletCharacter import kronecker_symbol as k
    def line(N):
        l = []
        count = 0
        for modulus in range(N,250):
            G = DirichletGroup_conrey(modulus)
            for j,chi in enumerate(G):
                    if count == 8:
                        break
                    elif chi.multiplicative_order() == N:
                        count += 1
                        l.append((modulus,j,chi.is_primitive(),chi.multiplicative_order(), k(chi)))
            if count == 8:
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
    s = '<table>\n'
    s += '<tr>\n<th scope="col">Characters</th>\n</tr>\n'
    for i in range(0,euler_phi(modulus)):
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
