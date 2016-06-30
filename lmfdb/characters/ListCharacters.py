# -*- coding: utf8 -*-
# ListCharacters.py

import re

from flask import render_template, url_for, make_response
from sage.all import Integers, primes, valuation, xmrange, lcm, prod, factor
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


def get_character_conductor(a, b, limit=7):
    def line(N):
        l = []
        count = 0
        modulus = N
        while count < 7:
            if modulus % N == 0:
                G = DirichletGroup_conrey(modulus)
                for chi in G:
                    j = chi.number()
                    c = WebDirichletCharacter(modulus = chi.modulus(),number = chi.number())
                    if count == 7:
                        break
                    elif chi.conductor() == N:
                        count += 1
                        l.append((modulus, j, chi.is_primitive(), chi.multiplicative_order(), c.symbol))
            modulus += N
            if count == 0:
                break
        return l
    return [(_, line(_)) for _ in range(a, b)]


class CharacterSearch:
    from dirichlet_conrey import DirichletGroup_conrey

    def __init__(self, query):
        self.mmin = 1
        self.mmax = 100000
        self.modulus = query.get('modulus', None)
        if self.modulus:
            self.mmin, self.mmax = self.parse_range(self.modulus)
            if self.mmin > self.mmax:
                raise Exception('Empty search')
            if self.mmax > 100000:
                # should give a comment
                self.mmax = 100000
        self.conductor = query.get('conductor', None)
        if self.conductor:
            self.cmin, self.cmax = self.parse_range(self.conductor)
            if self.cmin % 4 == 2:
                self.cmin += 1
            if self.cmax % 4 == 2:
                self.cmax -= 1
            if self.cmin > self.cmax:
                raise Exception('Empty search')
        self.order = query.get('order', None)
        if self.order:
            self.omin, self.omax = self.parse_range(self.order)
            if self.omin > self.omax:
                raise Exception('Empty search')
        self.limit = int(query.get('limit', 25))
        self.parity = query.get('parity', None)
        if self.parity == 'All':
            self.parity = None
        if self.parity == 'Odd' and self.order:
            if self.omin % 2:
                self.omin += 1
            if self.omax % 2:
                self.omax -= 1
            if self.omin > self.omax:
                raise Exception('Empty search')
        self.primitive = query.get('primitive', None)
        if self.primitive == 'All':
            self.primitive = None
        self.startm = int(query.get('startm', 0))
        """    
        self.startn = query.get('startn', None)
        print 'start at %s'%(self.startm, self.startn)
        """

    def parse_range(self, arg):
        s = arg.split('-')
        if len(s) == 1:
            s = int(s[0])
            return (s, s)
        else:
            return map(int, s[:2])

    def charinfo(self, chi):
        return (chi.modulus(), chi.number(), chi.conductor(),
                chi.multiplicative_order(), chi.is_odd(), chi.is_primitive(),
                WebDirichlet.char2tex(chi.modulus(), chi.number()))

    def results(self):
        info = {}
        L = self.list_valid()
        if len(L):
            #args['startm'], args['startn'] = L[0][:2]
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
        """
        OK, always search by modulus for the moment
        """
        if self.modulus:
            print 'BY MODULUS %s <= m <= %s'%self.modulus
            return self.return_valid( self.by_modulus(self.mmin, self.mmax) )
        else:
            print 'BY ALL MODULUS'
            return self.return_valid( self.by_modulus(1, 10000) )
        """
        if self.modulus and self.mmin == self.mmax:
            return self.return_valid( self.by_modulus(self.mmin, self.mmax) )
        elif self.conductor:
            print 'BY CONDUCTOR %s <= c <= %s'%self.conductor
            return self.return_valid( self.by_conductor(self.cmin, self.cmax) )
        elif self.modulus:
            print 'BY MODULUS %s <= m <= %s'%self.modulus
            return self.return_valid( self.by_modulus(self.mmin, self.mmax) )
        elif self.order:
            print 'BY ORDER %s <= o <= %s'%self.order
            return self.return_valid( self.by_order(self.omin, self.omax) )
        else:
            return self.return_valid( self.by_modulus(1, 30) )
        """

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

    def group_expo(self, n):
        x = lcm( [ (p-1)*p**(e-1) for (p,e) in factor(n) if e ] )
        if n % 8 == 0:
            return x / 2
        else:
            return x

    def has_div_in(self, x, a, b):
        if b - a < 20:
            for d in range(a, b+1):
                if x % d == 0:
                    return True
            return False
        else:
            return True
        """
        dmin = int(x/b) + 1
        dmax = int(x/a) + 1
        for d in range(dmin, dmax):
            if x % d == 0:
                return True
        return False
        """

    def valid_expo(self, N):
        e = self.group_expo(N)
        return self.has_div_in(e, self.omin, self.omax)

    def valid_cond(self, N):
        if self.cmax - self.cmin < 10:
            for c in range(self.cmin, self.cmax+1):
                if N % c == 0:
                    return True
            return False
        else:
            return True

    def by_modulus(self, mmin, mmax):
        if self.startm:
            mmin = self.startm
        for N in xrange(mmin, mmax + 1):
            """
            if self.conductor and not self.valid_cond(N):
                continue
            if self.order and not self.valid_expo(N):
                continue
            """
            G = DirichletGroup_conrey(N)
            for chi in G:
                yield chi
            """
            if False and self.startn:
                for chi in G[startm:]:
                    yield chi
                self.startn = None
            else:
                for chi in G:
                    yield chi
            """

    def by_conductor(self, cmin, cmax):
        m = 1
        lastN = 0
        if self.modulus:
            m = int(self.mmin / cmin)
        while True:
            if lastN:
                nmin = min(cmin, lastN/m)
            for n in xrange(nmin, cmax +1):
                if n % 4 == 2:
                    continue
                N = m * n
                if self.modulus and ( N < self.mmin or N > self.mmax):
                    continue
                if order and not self.valid_expo(N):
                    continue
                lastN = N
                G = DirichletGroup_conrey(N)
                for chi in G:
                    if cmin <= chi.conductor() <= cmax:
                        yield chi
            m += 1
            if self.modulus and m * cmin > self.mmax:
                break

    def inversegroupexpo(self, expo):
        """
        return all integers m s.t. (Z/mZ)* has exponent expo
        handle the case of 2 separately
        """
        P = [2] + [ p for p in primes(3, expo + 2) if expo % (p-1) == 0 ]
        R = [1] + [ 2 + valuation(expo/(p-1),p) for p in P ]
        e2 = valuation(expo, 2)
        for E in xmrange(R):
            phim = lcm( [ (p-1)*p**(e-1) for (p,e) in zip(P,E) if e ] )
            if phim == expo:
                m = prod( [ p**e for (p,e) in zip(P,E) if e ] )
                for e in range(0, e2 + 3):
                    yield m
                    m *= 2
            elif phim < expo:
                v = e2 - valuation(phim, 2)
                if v > 0 and expo == phim * 2 ** v:
                    m = prod( [ p**e for (p,e) in zip(P,E) if e ] )
                    if e2 == 1:
                        yield 4 * m
                        yield 8 * m
                    else:
                        yield 2**(e2+2) * m

    def by_order(self, omin, omax):
        """
        one can do better (sieve the reverse way)
        but I do not have time now
        """
        m = 1
        while True:
            for o in range(omin, omax + 1):
                mo = m * o
                if mo % 2:
                    continue
                if self.modulus and mo > self.mmax:
                    continue
                expomo = sorted(list(self.inversegroupexpo(mo)))
                print expomo
                for N in expomo:
                    if self.modulus and N > self.mmax:
                        break
                    if self.modulus and N < self.mmin:
                        continue
                    # group has exponent m * o
                    G = DirichletGroup_conrey(N)
                    for chi in G:
                        if omin <= chi.multiplicative_order() <= omax:
                            yield chi
            m += 1
            if self.modulus and m * omin > self.mmax:
		break
