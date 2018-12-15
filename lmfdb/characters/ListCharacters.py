# -*- coding: utf-8 -*-
# ListCharacters.py

import re
from sage.all import lcm, factor, divisors
from sage.databases.cremona import cremona_letter_code
from lmfdb.db_backend import db
from lmfdb.WebCharacter import WebDirichlet, WebDirichletCharacter, logger
try:
    from dirichlet_conrey import DirichletGroup_conrey
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")
from flask import flash
from markupsafe import Markup

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

def parse_limit (arg):
    if not arg:
        return 25
    limit = -1
    arg = arg.replace  (' ','')
    if re.match('^[0-9]+$', arg):
        limit = int(arg)
    if limit > 100:
        flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid limit on the number of results to display.  It should be a positive integer no greater than 100."%arg), "error")
        raise ValueError("limit")
    return limit

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
        if N%4 == 2:
            return l
        count = 0
        q = N
        while count < limit:
            if q % N == 0:
                G = DirichletGroup_conrey(q)
                for chi in G:
                    j = chi.number()
                    c = WebDirichletCharacter(modulus = q, number = j)
                    if chi.conductor() == q:
                        l.append((q, j, chi.is_primitive(), chi.multiplicative_order(), c.symbol))
                        count += 1
                        if count == limit:
                            break
            q += N
        return l
    return [(_, line(_)) for _ in range(a, b)]

def get_character_order(a, b, limit=7):
    def line(n):
        l = []
        count = 0
        q = n
        while count < limit:
            if modn_exponent(q) % n == 0:
                G = DirichletGroup_conrey(q)
                for chi in G:
                    j = chi.number()
                    c = WebDirichletCharacter(modulus = q, number = j)
                    if chi.multiplicative_order() == n:
                        l.append((q, j, chi.is_primitive(), chi.multiplicative_order(), c.symbol))
                        count += 1
                        if count == limit:
                            break
            q += 1
        return l
    return [(_, line(_)) for _ in range(a, b)]


def info_from_db_orbit(orbit):
    mod = orbit['modulus']
    conductor = orbit['conductor']
    orbit_index = orbit['orbit_index']
    orbit_letter = cremona_letter_code(orbit_index - 1)
    orbit_label = "{}.{}".format(mod, orbit_letter)
    order = orbit['order']
    is_odd = 'Odd' if _is_odd(orbit['parity']) else 'Even'
    is_prim = _is_primitive(orbit['is_primitive'])
    results = []
    for num in orbit['galois_orbit']:
        results.append((
            mod,
            num,
            conductor,
            orbit_label,
            order,
            is_odd,
            is_prim,
            WebDirichlet.char2tex(mod, num)
        ))
    return results


def _is_primitive(db_primitive):
    """
    Translate db's primitive entry to boolean.
    """
    if str(db_primitive) == "True":
        return True
    return False


def _is_odd(db_parity):
    """
    Translate db's parity entry to boolean.
    """
    _parity = int(db_parity)
    if _parity == -1:
        return True
    return False


class CharacterSearch:

    def __init__(self, query):
        self.modulus = query.get('modulus')
        self.conductor = query.get('conductor')
        self.order = query.get('order')
        self.parity = None if query.get('parity', 'All') == 'All' else query.get('parity')
        self.primitive = None if query.get('primitive', 'All') == 'All' else query.get('primitive')
        self.limit = parse_limit(query.get('limit'))
        if self.parity and not self.parity in ['Odd','Even']:
            flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid value for parity.  It must be 'Odd', 'Even', or 'All'"),"error")
            raise ValueError('parity')
        if self.primitive and not self.primitive in ['Yes','No']:
            flash(Markup("Error:  <span style='color:black'>%s</span> is not a valid value for primitive.  It must be 'Yes', 'No', or 'All'"),"error")
            raise ValueError('primitive')
        self.mmin, self.mmax = parse_interval(self.modulus,'modulus') if self.modulus else (1, 9999)
        if self.mmax > 9999:
            flash(Markup("Error: Searching is limited to charactors of modulus less than $10^5$"),"error")
            raise ValueError('modulus')
        if self.order and self.mmin > 999:
            flash(Markup("Error: For order searching the minimum modulus needs to be less than $10^3$"),"error")
            raise ValueError('modulus')

        self.cmin, self.cmax = parse_interval(self.conductor, 'conductor') if self.conductor else (1, self.mmax)
        self.omin, self.omax = parse_interval(self.order, 'order') if self.order else (1, self.cmax)
        self.cmax = min(self.cmax,self.mmax)
        self.omax = min(self.omax,self.cmax)
        if self.primitive == 'Yes':
            self.cmin = max([self.cmin,self.mmin])
        self.cmin += 1 if self.cmin%4 == 2 else 0
        self.cmax -= 1 if self.cmax%4 == 2 else 0
        if self.primitive == 'Yes':
            self.mmin = max([self.cmin,self.mmin])
            self.mmax = min([self.cmax,self.mmax])
            self.cmin,self.cmax = self.mmin,self.mmax
        if self.parity == "Odd":
            self.omin += 1 if self.omin%2 else 0
            self.omax -= 1 if self.omax%2 else 0
        self.mmin = max(self.mmin,self.cmin,self.omin)

        if self.parity:
            self.is_odd = True if self.parity == 'Odd' else False
        if self.primitive:
            self.is_primitive = True if self.primitive == 'Yes' else False

        self.start = int(query.get('start', '0'))


    def results(self):
        info = {}
        L, complete = self.lookup_results(self.mmin, self.mmax, self.start, self.limit)
        info['more'] = not complete
        if len(L):
            if self.start == 0:
                info['report'] = 'all %i matches'%(len(L)) if complete else 'first %i matches'%(len(L))
            else:
                info['report'] = 'matches %i to %i'%(self.start+1, self.start+len(L))
            # always false, just navigate previous page...
        info['start'] = self.start
        info['count'] = len(L)
        info['chars'] = L
        info['title'] = 'Dirichlet Characters'
        return info

    def list_valid(self):
        return

    def _construct_search_query(self):
        query = {}
        query['modulus'] = {
            '$gte': self.mmin,
            '$lte': self.mmax
        }
        query['conductor'] = {
            '$gte': self.cmin,
            '$lte': self.cmax
        }
        query['order'] = {
            '$gte': self.omin,
            '$lte': self.omax
        }
        if self.parity:
            if self.is_odd:
                query['parity'] = -1
            else:
                query['parity'] = 1
        if self.primitive:
            if self.is_primitive:
                query['is_primitive'] = True
            else:
                query['is_primitive'] = False
        return query

    def lookup_results(self, mmin, mmax, start, limit):
        res = []
        if mmin > mmax or self.cmin > self.cmax or self.omin > self.omax:
            return res, True
        if self.omax == 1 and self.cmin > 1:
            return res, True
        query = self._construct_search_query()

        orbit_cursor = db.char_dir_orbits.search(query)
        for orbit in orbit_cursor:
            res += info_from_db_orbit(orbit)
            # This is a not great way to implement offsets.
            # This should be improved.
            if start > 0:
                num_omit = min(len(res), start)
                res = res[num_omit:]
                start = start - num_omit
            if len(res) >= limit:
                break

        if len(res) >= limit:
            res = res[:limit]
            complete = False
        else:
            complete = True

        return res, complete
