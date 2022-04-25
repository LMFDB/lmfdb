# -*- coding: utf-8 -*-
# Author: Pascal Molin, molin.maths@gmail.com
"""
Any character object is obtained as a double inheritance of

1. a family (currently: Dirichlet/Z)

2. an object type (list of groups, character group, character)

For Dirichlet characters of modulus up to 10000, the database holds data for
the character and several of its values. For these objects, there are the
"DB" classes that replace on-the-fly computation with database lookups.

The code thus defines, from the generic top class WebCharObject

1. the mathematical family classes

   - WebDirichlet

   - WebDBDirichlet

2. the mathematical objects classes

   - WebCharGroup

   - WebChar

and one obtains:

- WebDirichletGroup

- WebDBDirichletGroup

- WebDBDirichletCharacter

The design is the following:

- the family class ancestor (Dirichlet) triggers a _compute method
  which initialize some mathematical class or fetches data in
  the database

- the object class ancestor triggers the __init__ method

"""

from flask import url_for
from collections import defaultdict
from sage.all import (gcd, ZZ, Rational, Integers, cached_method,
                      euler_phi, latex)
from sage.databases.cremona import cremona_letter_code
from sage.misc.lazy_attribute import lazy_attribute
from lmfdb import db
from lmfdb.utils import prop_int_pretty
from lmfdb.utils.utilities import num2letters
from lmfdb.logger import make_logger
from lmfdb.number_fields.web_number_field import WebNumberField, formatfield, nf_display_knowl
from lmfdb.characters.TinyConrey import (ConreyCharacter, kronecker_symbol,
                symbol_numerator, PariConreyGroup, get_sage_genvalues)
from lmfdb.characters.utils import url_character, complex2str
from lmfdb.groups.abstract.main import abstract_group_display_knowl
logger = make_logger("DC")

def parity_string(n):
    return "odd" if n == -1 else "even"

def bool_string(b):
    return "yes" if b else "no"

#############################################################################
###
###    Class for Web objects
###
#############################################################################

class WebCharObject():
    """ class for all characters and character groups """
    def __init__(self, **args):
        self.type = args.get('type',None)
        self.nflabel = args.get('number_field',None)
        self.modlabel = args.get('modulus',None)
        self.numlabel = args.get('number',None)
        self.args = args

        self._compute()

    def to_dict(self):
        d = {}
        for k in self._keys:
            d[k] = getattr(self,k,None)
            if d[k] is None:
                logger.debug('### key[%s] is None'%k)
        return d

    @staticmethod
    def texlogvalue(x, tag=False):
        if x is None:
            return 0
        if not isinstance(x, Rational):
            return '1'
        d = int(x.denom())
        n = int(x.numer())  % d
        if d == 1:
            s = '1'
        elif n == 1 and d == 2:
            s = "-1"
        elif n == 1 and d == 4:
            s = "i"
        elif n == 3 and d == 4:
            s = "-i"
        else:
            s = r"e\left(\frac{%s}{%s}\right)" % (n, d)
        if tag:
            return r"\(%s\)" % s
        else:
            return s

    @staticmethod
    def textuple(l, tag=True):
        t = ','.join(l)
        if len(l) > 1:
            t = '(%s)' % t
        if tag:
            t = r'\(%s\)' % t
        return t

    @staticmethod
    def texparity(n):
        parity_string(n)

    def charvalues(self, chi):
        return [ self.texlogvalue(chi.conreyangle(x), tag=True) for x in self.Gelts() ]

#############################################################################
###  Dirichlet type

class WebDirichlet(WebCharObject):
    """
    For some applications (orbits, enumeration), Dirichlet characters may be
    represented by a couple (modulus, number) without computing the Dirichlet
    group.
    """

    def _compute(self):
        if self.modlabel:
            self.modulus = int(self.modlabel)
        self.codelangs = ('pari', 'sage')

    def _char_desc(self, c, mod=None, prim=None):
        """ num is the number """
        if mod is None:
            mod = self.modulus
            num = c
            if prim is None:
                prim = self.charisprimitive(mod,num)
        else:
            num = c
            if prim is None:
                prim = self.charisprimitive(mod, num)
        return (mod, num, self.char2tex(mod,num), prim)

    def charisprimitive(self,mod,num):
        return ConreyCharacter(mod, num).is_primitive()

    @lazy_attribute
    def gens(self):
        return [int(k) for k in self.H.gens()]

    @lazy_attribute
    def generators(self):
        return self.textuple([str(k) for k in self.H.gens()])

    """ for Dirichlet over Z, everything is described using integers """
    @staticmethod
    def char2tex(modulus, number, val=r'\cdot', tag=True):
        c = r'\chi_{%s}(%s,%s)'%(modulus,number,val)
        if tag:
            return r'\(%s\)' % c
        else:
            return c

    group2tex = int
    group2label = int
    label2group = int

    ideal2tex = int
    ideal2label = int
    label2ideal = int

    """ numbering characters """
    number2label = int
    label2number = int

    @lazy_attribute
    def groupelts(self):
        return [self.group2tex(x) for x in self.Gelts()]

    @cached_method
    def Gelts(self):
        res = []
        m,n,k = self.modulus, 1, 1
        while k < m and n <= self.maxcols:
            if gcd(k,m) == 1:
                res.append(k)
                n += 1
            k += 1
        if n > self.maxcols:
            self.coltruncate = True

        return [-1] + res

    @staticmethod
    def nextchar(m, n, onlyprimitive=False):
        """ we know that the characters
            chi_m(1,.) and chi_m(m-1,.)
            always exist for m>1.
            They are extremal for a given m.
        """
        if onlyprimitive:
            return WebDirichlet.nextprimchar(m, n)
        if m == 1:
            return 2, 1
        if n == m - 1:
            return m + 1, 1
        k = n+1
        while k < m:
            if gcd(m, k) == 1:
                return m, k
            k += 1
        raise Exception("nextchar")

    @staticmethod
    def prevchar(m, n, onlyprimitive=False):
        """ Assume m>1 """
        if onlyprimitive:
            return WebDirichlet.prevprimchar(m, n)
        if n == 1:
            m, n = m - 1, m
        if m <= 2:
            return m, 1  # important : 2,2 is not a character
        k = n-1
        while k > 0:
            if gcd(m, k) == 1:
                return m, k
            k -= 1
        raise Exception("prevchar")

    @staticmethod
    def prevprimchar(m, n):
        if m <= 3:
            return 1, 1
        while True:
            n -= 1
            if n <= 1:  # (m,1) is never primitive for m>1
                m, n = m - 1, m - 1
            if m <= 2:
                return 1, 1
            if gcd(m, n) != 1:
                continue
            # we have a character, test if it is primitive
            chi = ConreyCharacter(m,n)
            if chi.is_primitive():
                return m, n

    @staticmethod
    def nextprimchar(m, n):
        if m < 3:
            return 3, 2
        while 1:
            n += 1
            if n >= m:
                m, n = m + 1, 2
            if gcd(m, n) != 1:
                continue
            # we have a character, test if it is primitive
            chi = ConreyCharacter(m,n)
            if chi.is_primitive():
                return m, n

    # The parts responsible for allowing computation of Gauss sums, etc. on page

    @lazy_attribute
    def charsums(self):
        if self.modulus < 1000:
            return { 'gauss': self.gauss_sum(2),
                     'jacobi': self.jacobi_sum(1),
                     'kloosterman': self.kloosterman_sum('1,2') }
        else:
            return None

    def gauss_sum(self, val):
        val = int(val)
        mod, num = self.modulus, self.number
        g = self.chi.gauss_sum_numerical(val)
        g = complex2str(g)
        x = Rational('%s/%s' % (val, mod))
        n = x.numerator()
        n = str(n) + "r" if not n == 1 else "r"
        d = x.denominator()
        Gtex = r'\Z/%s\Z' % mod
        chitex = self.char2tex(mod, num, tag=False)
        chitexr = self.char2tex(mod, num, 'r', tag=False)
        deftex = r'\sum_{r\in %s} %s e\left(\frac{%s}{%s}\right)'%(Gtex,chitexr,n,d)
        return r"\(\displaystyle \tau_{%s}(%s) = %s = %s \)" % (val, chitex, deftex, g)

    @lazy_attribute
    def codegauss(self):
        return {
            'sage': ['chi.gauss_sum(a)'],
            'pari': 'znchargauss(g,chi,a)' }

    def jacobi_sum(self, val):

        mod, num = self.modulus, self.number

        try:
            val = int(val)
        except ValueError:
            raise Warning ("n must be a positive integer coprime to the modulus {} and no greater than it".format(mod))
        if gcd(mod, val) > 1:
            raise Warning ("n must be coprime to the modulus : %s"%mod)
        if val > mod:
            raise Warning ("n must be less than the modulus : %s"%mod)
        if val < 0:
            raise Warning ("n must be positive")

        chi_values_data = db.char_dir_values.lookup(
            "{}.{}".format(mod, num)
        )
        chi_valuepairs = chi_values_data['values_gens']
        chi_genvalues = [int(v) for g, v in chi_valuepairs]
        chi = self.chi.sage_character(self.order, chi_genvalues)

        psi = ConreyCharacter(self.modulus, val)
        psi_values_data = db.char_dir_values.lookup(
            "{}.{}".format(self.modulus, val)
        )
        psi_valuepairs = psi_values_data['values_gens']
        psi_genvalues = [int(v) for g, v in psi_valuepairs]
        psi = psi.sage_character(self.order, psi_genvalues)

        jacobi_sum = chi.jacobi_sum(psi)
        chitex = self.char2tex(mod, num, tag=False)
        psitex = self.char2tex(mod, val, tag=False)
        Gtex = r'\Z/%s\Z' % mod
        chitexr = self.char2tex(mod, num, 'r', tag=False)
        psitex1r = self.char2tex(mod, val, '1-r', tag=False)
        deftex = r'\sum_{r\in %s} %s %s'%(Gtex,chitexr,psitex1r)
        return r"\( \displaystyle J(%s,%s) = %s = %s \)" % (chitex, psitex, deftex, latex(jacobi_sum))

    @lazy_attribute
    def codejacobi(self):
        return { 'sage': ['chi.jacobi_sum(n)']
        }

    def kloosterman_sum(self, arg):
        a, b = map(int, arg.split(','))
        modulus, number = self.modulus, self.number
        if modulus == 1:
            # there is a bug in sage for modulus = 1
            return r"""
            \( \displaystyle K(%s,%s,\chi_{1}(1,&middot;))
            = \sum_{r \in \Z/\Z}
                 \chi_{1}(1,r) 1^{%s r + %s r^{-1}}
            = 1 \)
            """ % (a, b, a, b)

        chi_values_data = db.char_dir_values.lookup(
            "{}.{}".format(modulus, number)
        )
        chi_valuepairs = chi_values_data['values_gens']
        chi_genvalues = [int(v) for g, v in chi_valuepairs]
        chi = self.chi.sage_character(self.order, chi_genvalues)

        k = chi.kloosterman_sum_numerical(100, a, b)
        k = complex2str(k, 10)
        return r"""
        \( \displaystyle K(%s,%s,\chi_{%s}(%s,&middot;))
        = \sum_{r \in \Z/%s\Z}
             \chi_{%s}(%s,r) e\left(\frac{%s r + %s r^{-1}}{%s}\right)
        = %s \)""" % (a, b, modulus, number, modulus, modulus, number, a, b, modulus, k)

    @lazy_attribute
    def codekloosterman(self):
        return { 'sage': ['chi.kloosterman_sum(a,b)']}

    def value(self, val):
        val = int(val)
        chartex = self.char2tex(self.modulus, self.number, val=val, tag=False)
        if gcd(val, self.modulus) == 1:
            val = self.texlogvalue(self.chi.conreyangle(val))
        else:
            val = 0
        return r'\(%s=%s\)' % (chartex, val)

    @lazy_attribute
    def codevalue(self):
        return { 'sage': 'chi(x) # x integer',
                 'pari': 'chareval(g,chi,x) \\\\ x integer, value in Q/Z' }


#############################################################################
###  Characters

class WebChar(WebCharObject):
    """
    Class for presenting a character on a web page
    """
    _keys = [ 'title', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman']

    def __init__(self, **args):
        self.maxcols = 10
        self.coltruncate = False
        WebCharObject.__init__(self, **args)

    @lazy_attribute
    def order(self):
        return self.chi.multiplicative_order()

    @lazy_attribute
    def codeorder(self):
        return { 'sage': 'chi.multiplicative_order()',
                 'pari': 'charorder(g,chi)' }

    @lazy_attribute
    def isprimitive(self):
        return bool_string( self.chi.is_primitive() )

    @lazy_attribute
    def isreal(self):
        return bool_string( self.order <= 2 )

    @lazy_attribute
    def values(self):
        return self.charvalues(self.chi)

    @lazy_attribute
    def conductor(self):
        return self.ideal2tex(self.chi.conductor())

    @lazy_attribute
    def modulus(self):
        return self.ideal2tex(self._modulus)

    @lazy_attribute
    def H(self):
        return PariConreyGroup(self.modulus)

    @lazy_attribute
    def genvalues(self):
        logvals = [self.chi.conreyangle(k) for k in self.H.gens()]
        return self.textuple([self.texlogvalue(v) for v in logvals])

    @lazy_attribute
    def texname(self):
        return self.char2tex(self.chi)

    @lazy_attribute
    def condlabel(self):
        return self.ideal2label(self.conductor)

    @lazy_attribute
    def inducing(self):
        return self.char2tex(self.conductor, self.indlabel)

    @lazy_attribute
    def label(self):
        return '%s.%s' % (self.modulus, self.number)

    @lazy_attribute
    def vflabel(self):
        order2 = self.order if self.order % 4 != 2 else self.order / 2
        nf = WebNumberField.from_cyclo(order2)
        if not nf.is_null():
            return nf.label
        else:
            return ''

    @lazy_attribute
    def valuefield(self):
        order2 = self.order if self.order % 4 != 2 else self.order / 2
        nf = WebNumberField.from_cyclo(order2)
        if not nf.is_null():
            return nf_display_knowl(nf.get_label(), nf.field_pretty())
        else:
            return r'$\Q(\zeta_{%d})$' % order2

    @lazy_attribute
    def kerfield(self):
        kerpoly = self.kernel_field_poly
        if kerpoly and self.order <= 100:
            return formatfield(kerpoly, missing_text="Number field defined by a degree %d polynomial" % self.order)
        else:
            return "Number field defined by a degree %d polynomial (not computed)" % self.order

    @lazy_attribute
    def properties(self):
        f = [("Label", [self.label])]
        f.extend([
            ("Modulus", [prop_int_pretty(self.modulus)]),
            ("Conductor", [prop_int_pretty(self.conductor)]),
            ("Order", [prop_int_pretty(self.order)]),
            ("Real", [self.isreal]),
            ("Primitive", [self.isprimitive])
        ])
        if self.isminimal:
            f.append(("Minimal", [self.isminimal]))
        if self.parity:
            f.append(("Parity", [self.parity]))
        return f

    @lazy_attribute
    def friends(self):
        from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url
        f = []
        cglink = url_character(type=self.type,number_field=self.nflabel,modulus=self.modlabel)
        f.append( ("Character group", cglink) )
        if self.nflabel:
            f.append( ('Number field', '/NumberField/' + self.nflabel) )
        if self.type == 'Dirichlet' and self.chi.is_primitive() and self.conductor < 10000:
            url = url_character(type=self.type, number_field=self.nflabel, modulus=self.modlabel, number=self.numlabel)
            if get_lfunction_by_url(url[1:]):
                f.append( ('L-function', '/L'+ url) )
            else:
                if self.conductor == 1:
                    f.append (('L-function', '/L/Riemann'))
        if self.type == 'Dirichlet':
            f.append( ('Sato-Tate group', '/SatoTateGroup/0.1.%d'%self.order) )
        if len(self.vflabel)>0:
            f.append( ("Value field", '/NumberField/' + self.vflabel) )
        return f

#############################################################################
###  Actual web objects used in lmfdb

class WebDBDirichlet(WebDirichlet):
    """
    A base class using data stored in the database. Currently this is all
    Dirichlet characters with modulus up to 10000.
    """
    def __init__(self, **kwargs):
        self.type = "Dirichlet"
        self.modulus = kwargs.get('modulus', None)
        if self.modulus:
            self.modulus = int(self.modulus)
        self.modlabel = self.modulus
        self.number = kwargs.get('number', None)
        if self.number:
            self.number = int(self.number)
        self.numlabel = self.number
        if self.modulus:
            # Needed for Gauss sums, etc
            self.H = PariConreyGroup(self.modulus)
            if self.number:
                self.chi = ConreyCharacter(self.modulus, self.number)
        self.maxcols = 30
        self.codelangs = ('pari', 'sage')
        self._compute()

    @lazy_attribute
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    def _compute(self):
        self._populate_from_db()

    def _populate_from_db(self):
        values_data = db.char_dir_values.lookup(
            "{}.{}".format(self.modulus, self.number)
        )

        self.orbit_index = int(values_data['orbit_label'].partition('.')[-1])
        # The -1 in the line below is because labels index at 1, while
        # the Cremona letter code indexes at 0
        self.orbit_label = cremona_letter_code(self.orbit_index - 1)
        self.order = int(values_data['order'])
        self.indlabel = int(values_data['prim_label'].partition('.')[-1])
        self._set_values_and_groupelts(values_data)
        self._set_generators_and_genvalues(values_data)

        orbit_data = db.char_dir_orbits.lucky(
            {'modulus': self.modulus, 'orbit_index': self.orbit_index}
        )

        self.conductor = int(orbit_data['conductor'])
        self._set_isprimitive(orbit_data)
        self._set_isminimal(orbit_data)
        self._set_parity(orbit_data)
        self._set_galoisorbit(orbit_data)
        self._set_kernel_field_poly(orbit_data)

    def _set_generators_and_genvalues(self, values_data):
        """
        The char_dir_values db collection contains `values_gens`, which
        contains the generators for the unit group U(modulus) and the values
        of the character on those generators.
        """
        valuepairs = values_data['values_gens']
        if self.modulus == 1:
            self.generators = r"\(1\)"
            self.genvalues = r"\(1\)"
        else:
            gens = [int(g) for g, v in valuepairs]
            vals = [int(v) for g, v in valuepairs]
            self._genvalues_for_code = get_sage_genvalues(self.modulus, self.order, vals, self.chi.sage_zeta_order(self.order))
            self.generators = self.textuple([str(g) for g in gens])
            self.genvalues = self.textuple([self._tex_value(v) for v in vals])

    def _set_values_and_groupelts(self, values_data):
        """
        The char_dir_values db collection contains `values`, which contains
        several group elements and the corresponding values.
        """
        valuepairs = values_data['values']
        if self.modulus == 1:
            self.groupelts = [1]
            self.values = [r"\(1\)"]
        else:
            self.groupelts = [int(g) for g, v in valuepairs]
            self.groupelts[0] = -1
            raw_values = [int(v) for g, v in valuepairs]
            self.values = [
                self._tex_value(v, self.order, texify=True) for v in raw_values
            ]

    def _tex_value(self, numer, denom=None, texify=False):
        r"""
        Formats the number e**(2 pi i * numer / denom), detecting if this
        simplifies to +- 1 or +- i.

        Surround the output i MathJax `\(..\)` tags if `texify` is True.
        `denom` defaults to self.order.
        """
        if not denom:
            denom = self.order

        g = gcd(numer, denom)
        if g > 1:
            numer = numer // g
            denom = denom // g

        # Reduce mod the denominator
        numer = (numer % denom)

        if denom == 1:
            ret = '1'
        elif (numer % denom) == 0:
            ret = '1'
        elif numer == 1 and denom == 2:
            ret = '-1'
        elif numer == 1 and denom == 4:
            ret = 'i'
        elif numer == 3 and denom == 4:
            ret = '-i'
        else:
            ret = r"e\left(\frac{%s}{%s}\right)" % (numer, denom)
        if texify:
            return r"\({}\)".format(ret)
        else:
            return ret

    def _set_isprimitive(self, orbit_data):
        self.isprimitive = bool_string(orbit_data['is_primitive'])

    def _set_isminimal(self, orbit_data):
        self.isminimal = bool_string(orbit_data['is_minimal'])

    def _set_parity(self, orbit_data):
        self.parity = parity_string(int(orbit_data['parity']))

    def _set_galoisorbit(self, orbit_data):
        if self.modulus == 1:
            self.galoisorbit = [self._char_desc(1, mod=1,prim=True)]
            return
        upper_limit = min(200, self.order + 1)
        orbit = orbit_data['galois_orbit'][:upper_limit]
        self.galoisorbit = list(
            self._char_desc(num, prim=self.isprimitive) for num in orbit
        )

    def _set_kernel_field_poly(self, orbit_data):
        if 'kernel_field_poly' in orbit_data.keys():
            self.kernel_field_poly = orbit_data['kernel_field_poly']
        else:
            self.kernel_field_poly = None


class WebCharGroup(WebCharObject):
    """
    Class for presenting character groups on a web page
    self.H is the character group
    self.G is the underlying group
    """
    headers = [ 'order', 'primitive']
    _keys = [ 'title', 'codelangs', 'type', 'nf', 'nflabel',
            'nfpol', 'modulus', 'modlabel', 'texname', 'codeinit', 'previous',
            'prevmod', 'next', 'nextmod', 'structure', 'structure_group_knowl', 'codestruct', 'order',
            'codeorder', 'gens', 'generators', 'codegen', 'valuefield', 'vflabel',
            'vfpol', 'headers', 'groupelts', 'contents',
            'properties', 'friends', 'rowtruncate', 'coltruncate']

    def __init__(self, **args):
        self._contents = None
        self.maxrows, self.maxcols = 35, 30
        self.rowtruncate, self.coltruncate = False, False
        WebCharObject.__init__(self, **args)

    @lazy_attribute
    def structure(self):
        inv = self.H.invariants()
        if inv:
            inv_list = list(inv)
            inv_list.sort()
            return r"\(%s\)" % ("\\times ".join("C_{%s}" % d for d in inv_list))
        else:
            return r"\(C_1\)"

    @lazy_attribute
    def structure_group_knowl(self):
        inv = self.H.invariants()
        label = ".".join(str(v) for v in inv)
        parts = defaultdict(list)
        if label:
            for piece in label.split("."):
                if "_" in piece:
                    base, exp = map(ZZ, piece.split("_"))
                else:
                    base = ZZ(piece)
                    exp = 1
                for p, e in base.factor():
                    parts[p].extend([p ** e] * exp)
        for v in parts.values():
            v.sort()
        primary = sum((parts[p] for p in sorted(parts)), [])
        dblabel = db.gps_groups.lucky({"abelian": True, "primary_abelian_invariants": primary}, "label")
        if dblabel is None:
            abgp_url = url_for('abstract.by_abelian_label', label=label)
            return f'<a href= %s >{self.structure}</a>' % abgp_url
        return abstract_group_display_knowl(dblabel, f"{self.structure}")

    @lazy_attribute
    def codestruct(self):
        return {'sage':'G.invariants()',
                'pari':'g.cyc'}

    @lazy_attribute
    def order(self):
        return euler_phi(self.modulus)

    @lazy_attribute
    def codeorder(self):
        return {'sage': 'G.order()',
                'pari': 'g.no' }

    @lazy_attribute
    def modulus(self):
        return self.ideal2tex(self._modulus)

    @cached_method
    def first_chars(self):
        if self.modulus == 1:
            return [1]
        r = []
        for i,c in enumerate(Integers(self.modulus).list_of_elements_of_multiplicative_group()):
            r.append(c)
            if i > self.maxrows:
                self.rowtruncate = True
                break
        return r

    def _fill_contents(self):
        for c in self.first_chars():
            self.add_row(c)

    @lazy_attribute
    def properties(self):
        return [("Modulus", [prop_int_pretty(self.modulus)]),
                ("Structure", [self.structure]),
                ("Order", [prop_int_pretty(self.order)]),
                ]

    @lazy_attribute
    def friends(self):
        if self.nflabel:
            return [ ("Number field", '/NumberField/' + self.nflabel), ]

    @lazy_attribute
    def contents(self):
        if self._contents is None:
            self._contents = []
            self._fill_contents()
        return self._contents


class WebDirichletGroup(WebCharGroup, WebDirichlet):
    """
    Heritage: WebCharGroup -> __init__()
              WebDirichlet -> _compute()
    """

    def _compute(self):
        """ WARNING: do not remove otherwise _compute
        is called once for each ancestor (I don't know why)
        """
        WebDirichlet._compute(self)
        logger.debug('######## WebDirichletGroup Computed')

    @lazy_attribute
    def codeinit(self):
        return {
                'sage': [
                    'H = DirichletGroup(%i)'%(self.modulus)
                    ],
                'pari': 'g = idealstar(,%i,2)'%(self.modulus)
                }

    @lazy_attribute
    def title(self):
        return r"Group of Dirichlet characters of modulus %s" % (self.modulus)

    @lazy_attribute
    def codegen(self):
        return {'sage': 'H.gens()',
                'pari': 'g.gen' }

    @lazy_attribute
    def codestruct(self):
        return {'sage': 'H.invariants()',
                'pari': 'g.cyc'}

    @lazy_attribute
    def order(self):
        return euler_phi(self.modulus)


class WebDBDirichletGroup(WebDirichletGroup, WebDBDirichlet):
    """
    A class using data stored in the database. Currently this is all Dirichlet
    characters with modulus up to 10000.
    """
    headers = ['Character', 'Orbit', 'Order', 'Primitive']

    def __init__(self, **kwargs):
        self._contents = None
        self.maxrows = 30
        self.maxcols = 30
        self.rowtruncate = False
        self.coltruncate = False
        WebDBDirichlet.__init__(self, **kwargs)
        self._set_groupelts()

    def add_row(self, c):
        """
        Add a row to _contents for display on the webpage.
        Each row of content takes the form
            character_name, (header..data), (several..values)
        where `header..data` is expected to be a tuple of length the same
        size as `len(headers)`, and given in the same order as in `headers`,
        and where `several..values` are the values of the character
        on self.groupelts, in order.
        """
        mod = self.modulus
        num = c
        prim, order, orbit_label, valuepairs = self.char_dbdata(mod, num)
        letter = cremona_letter_code(int(orbit_label.partition(".")[-1]) - 1)
        formatted_orbit_label = "{}.{}".format(mod, letter)
        self._contents.append((
            self._char_desc(num, mod=mod, prim=prim),
            (mod, letter, formatted_orbit_label),
            (order, bool_string(prim)),
            self._determine_values(valuepairs, order)
        ))

    def char_dbdata(self, mod, num):
        """
        Determine if the character is primitive by checking if its primitive
        inducing character is itself, according to the database. Also return
        the order of chi, the orbit_label of chi,  and the values within the
        database.
        Using only char_dir_values saves one database lookup, and combining
        these steps saves more database lookups.
        """
        db_data = db.char_dir_values.lookup(
            "{}.{}".format(mod, num)
        )
        is_prim = (db_data['label'] == db_data['prim_label'])
        order = db_data['order']
        valuepairs = db_data['values']
        orbit_label = db_data['orbit_label']
        return is_prim, order, orbit_label, valuepairs

    def _compute(self):
        WebDirichlet._compute(self)
        logger.debug("WebDBDirichletGroup Computed")

    def _set_groupelts(self):
        if self.modulus == 1:
            self.groupelts = [1]
        else:
            db_data = db.char_dir_values.lookup(
                "{}.{}".format(self.modulus, 1)
            )
            valuepairs = db_data['values']
            self.groupelts = [int(g) for g, v in valuepairs]
            self.groupelts[0] = -1

    def _char_desc(self, num, mod=None, prim=None):
        return (mod, num, self.char2tex(mod, num), prim)

    def _determine_values(self, valuepairs, order):
        """
        Translate the db's values into the actual values.
        """
        raw_values = [int(v) for g, v in valuepairs]
        values = [
            self._tex_value(v, order, texify=True) for v in raw_values
        ]
        return values


class WebDBDirichletCharacter(WebChar, WebDBDirichlet):
    """
    A class using data stored in the database. Currently, this is all Dirichlet
    characters with modulus up to 10000.
    """
    _keys = [ 'title', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman',
              'orbit_label', 'orbit_index', 'isminimal']

    def __init__(self, **kwargs):
        self.maxcols = 30
        self.coltruncate = False
        WebDBDirichlet.__init__(self, **kwargs)

    @lazy_attribute
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    @lazy_attribute
    def title(self):
        return r"Dirichlet character {}".format(self.texname)

    @lazy_attribute
    def symbol(self):
        return kronecker_symbol(self.symbol_numerator())

    @lazy_attribute
    def friends(self):
        from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url
        friendlist = []
        cglink = url_character(type=self.type, modulus=self.modulus)
        friendlist.append( ("Character group", cglink) )
        gal_orb_link = url_character(type=self.type, modulus=self.modulus, orbit_label = self.orbit_label)
        friendlist.append( ("Character orbit", gal_orb_link) )

        if self.type == "Dirichlet" and self.isprimitive == bool_string(True):
            url = url_character(
                type=self.type,
                number_field=None,
                modulus=self.modulus,
                number=self.number
            )
            if get_lfunction_by_url(url[1:]):
                friendlist.append( ('L-function', '/L'+ url) )
            else:
                if self.conductor == 1:
                    friendlist.append (('L-function', '/L/Riemann'))
            friendlist.append(
                ('Sato-Tate group', '/SatoTateGroup/0.1.%d' % self.order)
            )
        if len(self.vflabel) > 0:
            friendlist.append( ("Value field", '/NumberField/' + self.vflabel) )
        if self.symbol_numerator():
            if self.symbol_numerator() > 0:
                assoclabel = '2.2.%d.1' % self.symbol_numerator()
            else:
                assoclabel = '2.0.%d.1' % -self.symbol_numerator()
            friendlist.append(("Associated quadratic field", '/NumberField/' + assoclabel))

        label = "%s.%s"%(self.modulus, self.number)
        myrep = db.artin_reps.lucky({'Dets': {'$contains': label}})
        if myrep is not None:
            j=myrep['Dets'].index(label)
            artlabel = myrep['Baselabel']+'.'+num2letters(j+1)
            friendlist.append(('Artin representation '+artlabel,
                url_for('artin_representations.render_artin_representation_webpage', label=artlabel)))

        if self.type == "Dirichlet" and self.isprimitive == bool_string(False):
            friendlist.append(('Primitive character '+self.inducing,
                url_for('characters.render_Dirichletwebpage', modulus=self.conductor, number=self.indlabel)))

        return friendlist

    def symbol_numerator(self):
        """
        chi is equal to a kronecker symbol if and only if it is real
        """
        if self.order != 2:
            return None
        if self.parity == parity_string(-1):
            return symbol_numerator(self.conductor, True)
        return symbol_numerator(self.conductor, False)

    @lazy_attribute
    def previous(self):
        return None

    @lazy_attribute
    def next(self):
        return None

    @lazy_attribute
    def codeinit(self):
        return {
            'sage': [
                'from sage.modular.dirichlet import DirichletCharacter',
                'H = DirichletGroup({}, base_ring=CyclotomicField({}))'.format(self.modulus, self.chi.sage_zeta_order(self.order)),
                'M = H._module',
                'chi = DirichletCharacter(H, M([{}]))'.format(
                    ','.join(str(val) for val in self._genvalues_for_code)
                ),
            ],
            'pari': '[g,chi] = znchar(Mod(%i,%i))' % (self.number, self.modulus),
        }

    @lazy_attribute
    def codeisprimitive(self):
        return { 'sage': 'chi.is_primitive()',
                 'pari': '#znconreyconductor(g,chi)==1' }

    @lazy_attribute
    def codecond(self):
        return { 'sage': 'chi.conductor()',
                 'pari': 'znconreyconductor(g,chi)' }

    @lazy_attribute
    def codeparity(self):
        return { 'sage': 'chi.is_odd()',
                 'pari': 'zncharisodd(g,chi)' }

    @lazy_attribute
    def codesymbol(self):
        m = self.symbol_numerator()
        if m:
            return { 'sage': 'kronecker_character(%i)'%m,
                     'pari': 'znchartokronecker(g,chi)'
                     }
        return None

    @lazy_attribute
    def codegaloisorbit(self):
        return {
            'sage': ['chi.galois_orbit()'],
            'pari': [
                'order = charorder(g,chi)',
                '[ charpow(g,chi, k % order) | k <-[1..order-1], gcd(k,order)==1 ]'
            ]
        }


class WebDBDirichletOrbit(WebChar, WebDBDirichlet):
    """
    A class using data stored in the database. Currently, this is all Dirichlet
    characters with modulus up to 10000.
    """

    headers = ['Character']

    _keys = [ 'title', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol','headers',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing','rowtruncate','ind_orbit_label',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman',
              'orbit_label', 'orbit_index', 'isminimal', 'isorbit', 'degree']

    def __init__(self, **kwargs):
        self.type = "Dirichlet"
        self.isorbit = True
        self.modulus = kwargs.get('modulus', None)
        if self.modulus:
            self.modulus = int(self.modulus)
        self.modlabel = self.modulus
        self.number = kwargs.get('number', None)
        if self.number:
            self.number = int(self.number)
        self.numlabel = self.number
        if self.modulus:
            # Needed for Gauss sums, etc
            self.H = PariConreyGroup(self.modulus)
            if self.number:
                self.chi = ConreyCharacter(self.modulus, self.number)
        self.codelangs = ('pari', 'sage')
        self.orbit_label = kwargs.get('orbit_label', None)  # this is what the user inserted, so might be banana
        self.label = "{}.{}".format(self.modulus, self.orbit_label)
        self.orbit_data = self.get_orbit_data(self.orbit_label)  # this is the meat
        self.maxrows = 30
        self.rowtruncate = False
        self._set_galoisorbit(self.orbit_data)
        self.maxcols = 10
        self._contents = None
        self._set_groupelts()

    @lazy_attribute
    def title(self):
        return "Dirichlet character orbit {}.{}".format(self.modulus, self.orbit_label)

    def _set_galoisorbit(self, orbit_data):
        if self.modulus == 1:
            self.galoisorbit = [self._char_desc(1, mod=1,prim=True)]
            return

        upper_limit = min(self.maxrows + 1, self.degree + 1)

        if self.maxrows < self.degree + 1:
            self.rowtruncate = True
        self.galorbnums = orbit_data['galois_orbit'][:upper_limit]
        self.galoisorbit = list(
            self._char_desc(num, prim=orbit_data['is_primitive']) for num in self.galorbnums
        )

    def get_orbit_data(self, orbit_label):
        mod_and_label = "{}.{}".format(self.modulus, orbit_label)
        orbit_data =  db.char_dir_orbits.lucky(
            {'modulus': self.modulus, 'label': mod_and_label}
        )

        if orbit_data is None:
            raise ValueError

        # Since we've got this, might as well set a bunch of stuff

        self.conductor = orbit_data['conductor']
        self.order = orbit_data['order']
        self.degree = orbit_data['char_degree']
        self.isprimitive = bool_string(orbit_data['is_primitive'])
        self.isminimal = bool_string(orbit_data['is_minimal'])
        self.parity = parity_string(int(orbit_data['parity']))
        self._set_kernel_field_poly(orbit_data)
        self.ind_orbit_label = cremona_letter_code(int(orbit_data['prim_orbit_index']) - 1)
        self.inducing = "{}.{}".format(self.conductor, self.ind_orbit_label)
        return orbit_data

    def _set_kernel_field_poly(self, orbit_data):
        if 'kernel_field_poly' in orbit_data.keys():
            self.kernel_field_poly = orbit_data['kernel_field_poly']
        else:
            self.kernel_field_poly = None

    @lazy_attribute
    def friends(self):
        friendlist = []
        cglink = url_character(type=self.type, modulus=self.modulus)
        friendlist.append( ("Character group", cglink) )
        if self.type == "Dirichlet" and self.isprimitive == bool_string(True):
            friendlist.append(
                ('Sato-Tate group', '/SatoTateGroup/0.1.%d' % self.order)
            )
        if len(self.vflabel) > 0:
            friendlist.append( ("Value field", '/NumberField/' + self.vflabel) )
        if self.symbol_numerator():
            if self.symbol_numerator() > 0:
                assoclabel = '2.2.%d.1' % self.symbol_numerator()
            else:
                assoclabel = '2.0.%d.1' % -self.symbol_numerator()
            friendlist.append(("Associated quadratic field", '/NumberField/' + assoclabel))

        if self.type == "Dirichlet" and self.isprimitive == bool_string(False):
            friendlist.append(('Primitive orbit '+self.inducing,
                url_for('characters.render_Dirichletwebpage', modulus=self.conductor, orbit_label=self.ind_orbit_label)))

        return friendlist

    @lazy_attribute
    def contents(self):
        if self._contents is None:
            self._contents = []
            self._fill_contents()
        return self._contents

    def _fill_contents(self):
        for c in self.galorbnums:
            self.add_row(c)

    def add_row(self, c):
        """
        Add a row to _contents for display on the webpage.
        Each row of content takes the form
            character_name, (header..data), (several..values)
        where `header..data` is expected to be a tuple of length the same
        size as `len(headers)`, and given in the same order as in `headers`,
        and where `several..values` are the values of the character
        on self.groupelts, in order.
        """
        mod = self.modulus
        num = c
        valuepairs = db.char_dir_values.lookup(
            "{}.{}".format(mod, num),
            projection='values'
        )
        prim = self.isprimitive == bool_string(True)
        self._contents.append((
            self._char_desc(num, mod=mod, prim=prim),
            self._determine_values(valuepairs, self.order)
        ))

    def symbol_numerator(self):
        """
        chi is equal to a kronecker symbol if and only if it is real
        """
        if self.order != 2:
            return None
        if self.parity == parity_string(-1):
            return symbol_numerator(self.conductor, True)
        return symbol_numerator(self.conductor, False)

    @lazy_attribute
    def symbol(self):
        return kronecker_symbol(self.symbol_numerator())

    @lazy_attribute
    def codesymbol(self):
        m = self.symbol_numerator()
        if m:
            return { 'sage': 'kronecker_character(%i)'%m,
                     'pari': 'znchartokronecker(g,chi)'
                     }
        return None

    def _determine_values(self, valuepairs, order):
        """
        Translate the db's values into the actual values.
        """
        raw_values = [int(v) for g, v in valuepairs]
        values = [
            self._tex_value(v, order, texify=True) for v in raw_values
        ]
        return values

    def _set_groupelts(self):
        if self.modulus == 1:
            self.groupelts = [1]
        else:
            db_data = db.char_dir_values.lookup(
                "{}.{}".format(self.modulus, 1)
            )
            valuepairs = db_data['values']
            self.groupelts = [int(g) for g, v in valuepairs]
            self.groupelts[0] = -1

    @lazy_attribute
    def codeinit(self):
        self.exnum = self.galorbnums[0]
        self.exchi = ConreyCharacter(self.modulus, self.exnum)

        values_gens = db.char_dir_values.lookup(
            "{}.{}".format(self.modulus, self.exnum),
            projection='values_gens'
        )

        vals = [int(v) for g, v in values_gens]
        sage_zeta_order = self.exchi.sage_zeta_order(self.order)
        self._genvalues_for_code = get_sage_genvalues(self.modulus,
                                    self.order, vals, sage_zeta_order)

        return {
            'sage': [
                'from sage.modular.dirichlet import DirichletCharacter',
                'H = DirichletGroup({}, base_ring=CyclotomicField({}))'.format(
                    self.modulus, sage_zeta_order),
                'M = H._module',
                'chi = DirichletCharacter(H, M([{}]))'.format(
                    ','.join(str(val) for val in self._genvalues_for_code)
                ),
                'chi.galois_orbit()'
            ],
            'pari': [
                '[g,chi] = znchar(Mod(%i,%i))' % (self.exnum, self.modulus),
                'order = charorder(g,chi)',
                '[ charpow(g,chi, k % order) | k <-[1..order-1], gcd(k,order)==1 ]'
            ]
        }

    @lazy_attribute
    def codeisprimitive(self):
        return { 'sage': 'chi.is_primitive()',
                 'pari': '#znconreyconductor(g,chi)==1' }

    @lazy_attribute
    def codecond(self):
        return { 'sage': 'chi.conductor()',
                 'pari': 'znconreyconductor(g,chi)' }

    @lazy_attribute
    def codeparity(self):
        return { 'sage': 'chi.is_odd()',
                 'pari': 'zncharisodd(g,chi)' }


class WebSmallDirichletGroup(WebDirichletGroup):

    def _compute(self):
        if self.modlabel:
            self.modulus = m = int(self.modlabel)
            self.H = Integers(m).unit_group()
        self.codelangs = ('pari', 'sage')

    @lazy_attribute
    def contents(self):
        return None

    @lazy_attribute
    def gens(self):
        return self.H.gens_values()

    @lazy_attribute
    def generators(self):
        return self.textuple([str(v) for v in self.H.gens_values()])


class WebSmallDirichletCharacter(WebChar, WebDirichlet):
    """
    Heritage: WebChar -> __init__()
              WebDirichlet -> _compute()
    """

    def _compute(self):
        self.modulus = int(self.modlabel)
        self.number = int(self.numlabel)
        self.chi = ConreyCharacter(self.modulus, self.number)
        self.codelangs = ('pari', 'sage')

    @lazy_attribute
    def conductor(self):
        return self.chi.conductor()

    @lazy_attribute
    def indlabel(self):
        if self.chi.indlabel is not None:
            return self.chi.indlabel
        else:
            # Calling conductor computes the indlabel
            self.chi.conductor()
            return self.chi.indlabel

    @lazy_attribute
    def codeinit(self):
        return {
          'sage': [
                 'H = DirichletGroup(%i)'%(self.modulus),
                 'chi = H[%i]'%(self.number) ],
          'pari': '[g,chi] = znchar(Mod(%i,%i))'%(self.number,self.modulus),
          }

    @lazy_attribute
    def title(self):
        return r"Dirichlet character %s" % (self.texname)

    @lazy_attribute
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    @lazy_attribute
    def codeisprimitive(self):
        return { 'sage': 'chi.is_primitive()',
                 'pari': '#znconreyconductor(g,chi)==1 \\\\ if not primitive returns [cond,factorization]' }

    @lazy_attribute
    def codecond(self):
        return { 'sage': 'chi.conductor()',
                 'pari': 'znconreyconductor(g,chi)' }

    @lazy_attribute
    def parity(self):
        return (parity_string(-1),parity_string(1))[self.chi.is_even()]

    @lazy_attribute
    def codeparity(self):
        return { 'sage': 'chi.is_odd()',
                 'pari': 'zncharisodd(g,chi)' }

    def symbol_numerator(self):
        """ chi is equal to a kronecker symbol if and only if it is real """
        if self.order != 2:
            return None
        return symbol_numerator(self.conductor, self.chi.is_odd())

    @lazy_attribute
    def symbol(self):
        return kronecker_symbol(self.symbol_numerator())

    @lazy_attribute
    def codesymbol(self):
        m = self.symbol_numerator()
        if m:
            return { 'sage': 'kronecker_character(%i)'%m,
                     'pari': 'znchartokronecker(g,chi)'
                     }
        return None

    @lazy_attribute
    def codegaloisorbit(self):
        return { 'sage': ['chi.galois_orbit()'],
                 'pari': [ 'order = charorder(g,chi)',
                           '[ charpow(g,chi, k % order) | k <-[1..order-1], gcd(k,order)==1 ]' ]
                 }
