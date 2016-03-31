# -*- coding: utf8 -*-
# ListCharacters.py

import re

from flask import render_template, url_for, make_response
from sage.all import Integers, primes, valuation, xmrange, lcm, prod
import tempfile
import os
from lmfdb.WebCharacter import *

"""
do everything on conrey labels only?
"""

def get_character_modulus(a, b, limit=7):
    """
    keep this function which is still used
    by the lfunctions blueprint
    """
    from dirichlet_conrey import DirichletGroup_conrey
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
    # from utils import debug; debug()
    return headers, entries2, rows, cols

class CharacterSearch:

    from dirichlet_conrey import DirichletGroup_conrey
    def __init__(self, query):
        self.modulus = query.get('modulus', None)
        if self.modulus:
            self.mmin, self.mmax = self.modulus
            if self.mmin > self.mmax:
                raise Exception('Empty search')
        self.conductor = query.get('conductor', None)
        if self.conductor:
            self.cmin, self.cmax = self.conductor
            if self.cmin % 4 == 2:
                self.cmin += 1
            if self.cmax % 4 == 2:
                self.cmax -= 1
            if self.cmin > self.cmax:
                raise Exception('Empty search')
        self.order = query.get('order', None)
        if self.order:
            self.omin, self.omax = self.order
            if self.omin > self.omax:
                raise Exception('Empty search')
        self.limit = query.get('limit', 25)

    def charinfo(self, chi):
        return (chi.modulus(), chi.number(), chi.conductor(),
                chi.multiplicative_order(), chi.is_odd(), chi.is_primitive(),
                WebDirichlet.char2tex(chi.modulus(), chi.number()))

    def results(self):
        if self.conductor:
            print 'BY CONDUCTOR %s <= c <= %s'%self.conductor
            return self.return_valid( self.by_conductor(self.cmin, self.cmax) )
        elif self.order and self.omin == self.omax:
            print 'BY ORDER %s <= o <= %s'%self.order
            return self.return_valid( self.by_order(self.omin, self.omax) )
        elif self.modulus:
            print 'BY MODULUS %s <= m <= %s'%self.modulus
            return self.return_valid( self.by_modulus(self.mmin, self.mmax) )
        elif self.order:
            print 'BY ORDER %s <= o <= %s'%self.order
            return self.return_valid( self.by_order(self.omin, self.omax) )
        else:
            return self.return_valid( self.by_modulus(1, 30) )

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
            wc = self.charinfo(chi)
            (m,n,c,o) = wc[:4]
            if self.modulus and ( self.mmin > m or m > self.mmax ):
                continue
            if self.order and ( self.omin > o or o > self.omax ):
                continue
            if self.conductor and ( self.cmin > c or c > self.cmax ):
                continue
            yield wc

    def by_modulus(self, mmin, mmax):
        for N in range(mmin, mmax + 1):
            G = DirichletGroup_conrey(N)
            for chi in G:
                yield chi

    def by_conductor(self, cmin, cmax):
        m = 1
        if self.modulus:
            m = int(self.mmin / cmin)
        while True:
            for n in range(cmin, cmax +1):
                if n % 4 == 2:
                    continue
                N = m * n
                if self.modulus and ( N < self.mmin or N > self.mmax):
                    continue
                G = DirichletGroup_conrey(N)
                for chi in G:
                    if cmin <= chi.conductor() <= cmax:
                        yield chi
            m += 1
            if self.modulus and m * cmin > self.mmax:
                break

    def expo(self, n):
        return lcm( [ (p-1)*p**(e-1) for (p,e) in zip(factor(n)) if e ] )

    def inversegroupexpo(self, expo):
        P = [ p for p in primes(2, expo + 2) if expo % (p-1) == 0 ]
        R = [ 2 + valuation(expo/(p-1),p) for p in P ]
        print P
        print R
        for E in xmrange(R):
            phim = lcm( [ (p-1)*p**(e-1) for (p,e) in zip(P,E) if e ] )
            if phim == expo:
                m = prod( [ p**e for (p,e) in zip(P,E) if e ] )
                yield m
    
    def by_order(self, omin, omax):
        m = 1
        while True:
            for o in range(omin, omax + 1):
                mo = m * o
                if mo % 2:
                    continue
                if self.modulus and mo > self.mmax:
                    continue
                for N in self.inversegroupexpo(mo):
                    if self.modulus and (N < self.mmin or N > self.mmax):
                        continue
                    # group has exponent m * o
                    G = DirichletGroup_conrey(N)
                    for chi in G:
                        if omin <= chi.multiplicative_order() <= omax:
                            yield chi
            m += 1
            if self.modulus and m * omin > self.mmax:
		break
