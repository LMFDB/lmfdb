# -*- coding: utf8 -*-
# ListCharacters.py

import re
from sage.all import lcm, factor, divisors
from lmfdb.WebCharacter import WebDirichlet, WebDirichletCharacter
from dirichlet_conrey import DirichletGroup_conrey
from flask import flash
from markupsafe import Markup

"""
do everything on conrey labels only?
"""

# utility functions #

def modn_exponent(n):
    """ given a nonzero integer n, returns the group exponent of (Z/nZ)* """
    return lcm( [ (p-1)*p**(e-1) for (p,e) in factor(n) ] ) // (1 if n%8 else 2)

def divisors_in_interval(n, a, b):
    """ given a nonzero integer n and an interval [a,b] returns a list of the divisors of n in [a,b] """
    return [d for d in divisors(n) if a <= d and d <= b]

def parse_interval(arg, name):
    """ parses a user specified interval of positive integers (or a single integer), flashes errors and raises exceptions """
    a,b = 0,0
    arg = arg.replace (' ','')
    if re.match('^[0-9]+$', arg):
        a,b =  (int(arg),int(arg))
    elif re.match('^[0-9]+-[0-9]+$', arg):
        s = arg.split('-')
        a,b = (int(s[0]), int(s[1]))
    elif re.match('^[0-9]+..[0-9]+$', arg):
        s = arg.split('..')
        a,b = (int(s[0]), int(s[1]))
    elif re.match('^\[[0-9]+..[0-9]+\]$', arg):
        s = arg[1:-1].split('..')
        a,b = (int(s[0]), int(s[1]))
    if a <= 0 or b < a:
        flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid value for %s. It should be a positive integer (e.g. 7) or a nonempty range of positive integers (e.g. 1-10 or 1..10)"%(arg,name)), "error")
        raise ValueError("invalid "+name)
    return a,b

def get_character_modulus(a, b, limit=7):
    """ this function which is also used by lfunctions/LfunctionPlot.py """
    headers = range(1, limit)
    headers.append("more")
    entries = {}
    rows = range(a, b + 1)
    for row in rows:
        G = DirichletGroup_conrey(row)
        for chi in G:
            multorder = chi.multiplicative_order()
            el = chi
            col = multorder
            col = col if col <= 6 else 'more'
            entry = entries.get((row, col), [])
            entry.append(el)
            entries[(row, col)] = entry

    entries2 = {}
    out = lambda chi: (chi.number(), chi.is_primitive(),
                       chi.multiplicative_order(), chi.is_even())
    for k, v in entries.iteritems():
        l = []
        v = sorted(v)
        while v:
            e1 = v.pop(0)
            inv = ~e1
            if e1 == inv:
                l.append((out(e1),))
            else:
                l.append((out(e1), out(inv)))
                v.remove(inv)
        if k[1] == "more":
            l = sorted(l, key=lambda e: e[0][2])
        entries2[k] = l
    cols = headers
    return headers, entries2, rows, cols


def get_character_conductor(a, b, limit=7):
    def line(N):
        l = []
        count = 0
        modulus = N
        while count < limit:
            if modulus % N == 0:
                G = DirichletGroup_conrey(modulus)
                for chi in G:
                    j = chi.number()
                    c = WebDirichletCharacter(modulus = chi.modulus(),number = chi.number())
                    if chi.conductor() == N:
                        l.append((modulus, j, chi.is_primitive(), chi.multiplicative_order(), c.symbol))
                        count += 1
                        if count == limit:
                            break
            modulus += N
        return l
    return [(_, line(_)) for _ in range(a, b)]

def get_character_order(a, b, limit=7):
    def line(n):
        l = []
        count = 0
        modulus = n+1 if n > 1 else n
        while count < limit:
            if modn_exponent(modulus) % n == 0:
                G = DirichletGroup_conrey(modulus)
                for chi in G:
                    j = chi.number()
                    c = WebDirichletCharacter(modulus = chi.modulus(),number = chi.number())
                    if chi.multiplicative_order() == n:
                        l.append((modulus, j, chi.is_primitive(), chi.multiplicative_order(), c.symbol))
                        count += 1
                        if count == limit:
                            break
            modulus += 1
        return l
    return [(_, line(_)) for _ in range(a, b)]

def charinfo(chi):
    """ return data associated to the WebDirichletCharacter chi """
    return (chi.modulus(), chi.number(), chi.conductor(), chi.multiplicative_order(), chi.is_odd(), chi.is_primitive(), WebDirichlet.char2tex(chi.modulus(), chi.number()))

class CharacterSearch:

    def __init__(self, query):
        self.modulus = query.get('modulus')
        self.conductor = query.get('conductor')
        self.order = query.get('order')
        self.parity = None if query.get('parity', 'All') == 'All' else query.get('parity')
        self.primitive = None if query.get('primitive', 'All') == 'All' else query.get('primitive')
        self.limit = int(query.get('limit', 25))
        if self.parity and not self.parity in ['Odd','Even']:
            flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid value for parity.  It must be 'Odd', 'Even', or 'All'"),"error")
            raise ValueError('parity')
        if self.primitive and not self.primitive in ['Yes','No']:
            flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid value for primitive.  It must be 'Yes', 'No', or 'All'"),"error")
            raise ValueError('primitive')
        self.mmin, self.mmax = parse_interval(self.modulus,'modulus') if self.modulus else (1, 99999)
        if self.mmax > 99999:
            flash(Markup("Error: Searching is limited to charactors of modulus less than $10^5$"),"error")
            raise ValueError('modulus')
        self.cmin, self.cmax = parse_interval(self.conductor, 'conductor') if self.conductor else (1, self.mmax)
        self.omin, self.omax = parse_interval(self.order, 'order') if self.order else (1, self.cmax)
        self.cmax = min(self.cmax,self.mmax)
        self.omax = min(self.omax,self.cmax)
        if self.primitive:
            self.cmin = max([self.cmin,self.mmin])
        self.cmin += 1 if self.cmin%4 == 2 else 0
        self.cmax -= 1 if self.cmax%4 == 2 else 0
        if self.primitive:
            self.mmin = max([self.cmin,self.mmin])
            self.mmax = min([self.cmax,self.mmax])
            self.cmin,self.cmax = self.mmin,self.mmax
        if self.parity == "Odd":
            self.omin += 1 if self.omin%2 else 0
            self.omax -= 1 if self.omax%2 else 0
        self.mmin = max(self.mmin,self.cmin,self.omin)
        
    def results(self):
        info = {}
        L = self.list_valid()
        if len(L):
            info['lastm'], info['lastn'] = L[-1][:2]
            if len(L) == self.limit:
                info['report'] = 'first %i results'%(len(L))
                info['more'] = True
            else:
                info['report'] = 'all %i results'%(len(L))
                info['more'] = False
            # always false, just navigate previous page...
            info['start'] = 0
        info['number'] = len(L)
        info['chars'] = L
        info['title'] = 'Dirichlet Characters'
        if self.modulus:
            info['modulus'] = self.modulus
        if self.conductor:
            info['conductor'] = self.conductor
        if self.order:
            info['order'] = self.order
        if self.limit:
            info['limit'] = self.limit
        return info

    def list_valid(self):
        return self.return_valid( self.by_modulus(self.mmin, self.mmax) )

    def return_valid(self, gen):
        l, count = [], 0
        for c in self.yield_valid( gen ):
            l.append(c)
            count += 1
            if count == self.limit:
                return l
        return l

    def yield_valid(self, gen):
        for chi in gen:
            wc = charinfo(chi)
            (m,n,c,o,p) = wc[:5]
            if self.modulus and ( self.mmin > m or m > self.mmax ):
                continue
            if self.order and ( self.omin > o or o > self.omax ):
                continue
            if self.conductor and ( self.cmin > c or c > self.cmax ):
                continue
            if self.primitive:
                if (self.primitive == 'Yes' and m != c) or (self.primitive == 'No' and m == c):
                    continue
            if self.parity:
                if (self.parity == 'Even' and p) or (self.parity == 'Odd' and not p):
                    continue
            yield wc

    def by_modulus(self, mmin, mmax):
        if mmin > mmax or self.cmin > self.cmax or self.omin > self.omax:
            return
        step = self.cmin if self.conductor and self.cmin == self.cmax else 1
        for N in xrange(mmin, mmax + 1, step):
            if self.conductor and not divisors_in_interval(N, self.cmin, self.cmax):
                continue
            if self.order and not divisors_in_interval(modn_exponent(N), self.omin, self.omax):
                continue
            G = DirichletGroup_conrey(N)
            for chi in G:
                print "%d.%d"%(chi.modulus(),chi.number())
                yield chi

