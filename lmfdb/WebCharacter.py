# -*- coding: utf-8 -*-
# Author: Pascal Molin, molin.maths@gmail.com
from sage.databases.cremona import cremona_letter_code
from sage.misc.cachefunc import cached_method
from sage.all import gcd, Rational, power_mod, Integers, gp, xsrange
from flask import url_for
from lmfdb.db_backend import db
from lmfdb.utils import make_logger, web_latex_split_on_pm
logger = make_logger("DC")
from lmfdb.nfutils.psort import ideal_label, ideal_from_label
from WebNumberField import WebNumberField
try:
    from dirichlet_conrey import DirichletGroup_conrey, DirichletCharacter_conrey
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")
from lmfdb.characters.HeckeCharacters import HeckeChar, RayClassGroup
from lmfdb.characters.TinyConrey import ConreyCharacter, kronecker_symbol, symbol_numerator
from lmfdb.characters.utils import url_character, complex2str, evalpolelt

"""
Any character object is obtained as a double inheritance of

1. a family (currently: Dirichlet/Z or Hecke/K)

2. an object type (list of groups, character group, character)

For Dirichlet characters of modulus up to 10000, the database holds data for
the character and several of its values. For these objects, there are the
"DB" classes that replace on-the-fly computation with database lookups.

The code thus defines, from the generic top class WebCharObject

1. the mathematical family classes

   - WebDirichlet

   - WebDBDirichlet

   - WebHecke

2. the mathematical objects classes

   - WebCharFamily

   - WebCharGroup

   - WebChar

and one obtains:

- WebDirichletFamily

- WebDirichletGroup

- WebDBDirichletGroup

- WebDBDirichletCharacter

- WebHeckeFamily

- WebHeckeGroup

- WebHeckeCharacter

plus the additional WebHeckeExamples which collects interesting examples
of Hecke characters but could be converted to a yaml file [TODO]

The design is the following:

- the family class ancestor (Dirichler/Hecke) triggers a _compute method
  which initialize some mathematical class or fetches data in
  the database

- the object classe ancestor triggers the __init__ method

"""

#############################################################################
###
###    Class for Web objects
###
#############################################################################

class WebCharObject:
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
            if d[k] == None:
                logger.debug('### key[%s] is None'%k)
        return d

    @staticmethod
    def texlogvalue(x, tag=False):
        if x == None:
            return 0
        if not isinstance(x, Rational):
            return '1'
        d = int(x.denom())
        n = int(x.numer())  % d # should be fixed in Dirichlet_conrey
        if d == 1:
            return '1'
        elif n == 1 and d == 2:
            s = "-1"
        elif n == 1 and d == 4:
            s = "i"
        elif n == 3 and d == 4:
            s = "-i"
        else:
            s = r"e\left(\frac{%s}{%s}\right)" % (n, d)
        if tag:
            return "\(%s\)" % s
        else:
            return s

    @staticmethod
    def textuple(l,tag=True):
        t = ','.join(l)
        if len(l) > 1: t='(%s)'%t
        if tag: t = '\(%s\)'%t
        return t

    @staticmethod
    def texbool(b):
        return ("No","Yes")[b]

    def charvalues(self, chi):
        return [ self.texlogvalue(chi.logvalue(x), tag=True) for x in self.Gelts() ]

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
            self.modulus = m = int(self.modlabel)
            self.H = DirichletGroup_conrey(m)
        self.credit = 'SageMath'
        self.codelangs = ('pari', 'sage')

    def _char_desc(self, c, mod=None, prim=None):
        """ usually num is the number, but can be a character """
        if isinstance(c, DirichletCharacter_conrey):
            if prim == None:
                prim = c.is_primitive()
            mod = c.modulus()
            num = c.number()
        elif mod == None:
            mod = self.modulus
            num = c
            if prim == None:
                prim = self.charisprimitive(mod,num)
        else:
            num = c
            if prim == None:
                prim = self.charisprimitive(mod, num)
        return (mod, num, self.char2tex(mod,num), prim)

    def charisprimitive(self,mod,num):
        if isinstance(self.H, DirichletGroup_conrey) and self.H.modulus()==mod:
            H = self.H
        else:
            H = DirichletGroup_conrey(mod)
        return H[num].is_primitive()

    @property
    def gens(self):
        return map(int, self.H.gens())

    @property
    def generators(self):
        #import pdb; pdb.set_trace()
        #assert self.H.gens() is not None
        return self.textuple(map(str, self.H.gens()))

    """ for Dirichlet over Z, everything is described using integers """
    @staticmethod
    def char2tex(modulus, number, val='\cdot', tag=True):
        c = r'\chi_{%s}(%s,%s)'%(modulus,number,val)
        if tag:
           return '\(%s\)'%c
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

    @property
    def groupelts(self):
        return map(self.group2tex, self.Gelts())

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

        return res

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
        if n > 2:
            Gm = DirichletGroup_conrey(m)
        while True:
            n -= 1
            if n <= 1:  # (m,1) is never primitive for m>1
                m, n = m - 1, m - 1
                Gm = DirichletGroup_conrey(m)
            if m <= 2:
                return 1, 1
            if gcd(m, n) != 1:
                continue
            # we have a character, test if it is primitive
            chi = Gm[n]
            if chi.is_primitive():
                return m, n

    @staticmethod
    def nextprimchar(m, n):
        if m < 3:
            return 3, 2
        if n < m - 1:
            Gm = DirichletGroup_conrey(m)
        while 1:
            n += 1
            if n >= m:
                m, n = m + 1, 2
                Gm = DirichletGroup_conrey(m)
            if gcd(m, n) != 1:
                continue
            # we have a character, test if it is primitive
            chi = Gm[n]
            if chi.is_primitive():
                return m, n


#############################################################################
###  Hecke type

class WebHecke(WebCharObject):
    """ FIXME design issue: should underlying group elements be represented
        by tuples or by representative ideals ?
        for computations tuples are much better, this is also more compact.
        """
    def _compute(self):
        self.k = self.label2nf(self.nflabel)
        self._modulus = self.label2ideal(self.k, self.modlabel)
        self.G = RayClassGroup(self.k, self._modulus)
        self.H = self.G.dual_group()
        #self.number = lmfdb_label2hecke(self.numlabel)
        # make this canonical
        self.modlabel = self.ideal2label(self._modulus)
        self.credit = "Pari, SageMath"
        self.codelangs = ('pari', 'sage')
        self.parity = None
        logger.debug('###### WebHeckeComputed')

    @property
    def generators(self):
        """ use representative ideals """
        return self.textuple( map(self.ideal2tex, self.G.gen_ideals() ), tag=False )

    """ labeling conventions are put here """

    @staticmethod
    def char2tex(c, val='\cdot',tag=True):
        """ c is a Hecke character """
        number = ','.join(map(str,c.exponents()))
        s = r'\chi_{%s}(%s)'%(number,val)
        if tag:
            return r'\(%s\)'%s
        else:
            return s

    def _char_desc(self, c, modlabel=None, prim=None):
        """ c is a Hecke character of modulus self.modulus
            unless modlabel is specified
        """
        if modlabel == None:
            modlabel = self.modlabel
        numlabel = self.number2label( c.exponents() )
        if prim == None:
            prim = c.is_primitive()
        return (modlabel, numlabel, self.char2tex(c), prim )

    @staticmethod
    def ideal2tex(ideal):
        a,b = ideal.gens_two()
        return "\(\langle %s, %s\\rangle\)"%(a._latex_(), b._latex_())

    @staticmethod
    def ideal2cas(ideal):
        return '%s,%s'%(ideal.gens_two())

    @staticmethod
    def ideal2label(ideal):
        return ideal_label(ideal)

    @staticmethod
    def label2ideal(k,label):
        return ideal_from_label(k, label)

    """
    underlying group contains ideal classes, but are represented
    as exponent tuples on cyclic components (not canonical, but
    more compact)
    """
    #group2tex = ideal2tex
    #group2label = ideal2label
    #label2group = label2ideal
    @staticmethod
    def group2tex(x, tag=True):
        if not isinstance(x, tuple):
            x = x.exponents()
        #s =  '\cdot '.join('g_{%i}^{%i}'%(i,e) for i,e in enumerate(x) if e>0)
        s = []
        for i,e in enumerate(x):
            if e > 0:
                if e==1:
                    s.append('g_{%i}'%i)
                else:
                    s.append('g_{%i}^{%i}'%(i,e))
        s =  '\cdot '.join(s)
        if s == '': s = '1'
        if tag: s = '\(%s\)'%s
        return s

    @staticmethod
    def group2label(self,x):
        return self.number2label(x.exponents())

    def label2group(self,x):
        """ x is either an element of k or a tuple of ints or an ideal """
        if x.count('.'):
            x = self.label2ideal(self.k,x)
        elif x.count('a'):
            a = self.k.gen()
            x = evalpolelt(x,a,'a')
        elif x.count(','):
            x = tuple(map(int,x.split(',')))
        return self.G(x)

    @staticmethod
    def number2label(number):
        return '.'.join(map(str,number))

    @staticmethod
    def label2number(label):
        return map(int,label.split('.'))

    @staticmethod
    def label2nf(label):
        return WebNumberField(label).K()

    @property
    def groupelts(self):
        return map(self.group2tex, self.Gelts())

    @cached_method
    def Gelts(self):
        res = []
        c = 1
        for x in self.G.iter_exponents():
            res.append(x)
            c += 1
            if c > self.maxcols:
                self.coltruncate = True
                break
        return res

#############################################################################
###  Family

class WebCharFamily(WebCharObject):
    """ compute first groups """
    _keys = [ 'title', 'credit', 'codelangs', 'type', 'nf', 'nflabel',
            'nfpol', 'code', 'headers', 'contents' ]
    headers = [ 'modulus', 'order', 'structure', 'first characters' ]

    def __init__(self, **args):
        self._contents = None
        self.maxrows, self.rowtruncate = 25, False
        WebCharObject.__init__(self, **args)

    def structure(self, G):
        return self.struct2tex(G.invariants())

    def struct2tex(self, inv):
        if not inv: inv = (1,)
        return '\(%s\)'%('\\times '.join(['C_{%s}'%d for d in inv]))

    def add_row(self, modulus):
        G = self.chargroup(modulus)
        order = G.order
        struct = G.structure
        firstchars = [ self._char_desc(c) for c in G.first_chars() ]
        self._contents.append( (self.ideal2label(modulus), order, struct, firstchars) )

    @property
    def contents(self):
        if self._contents is None:
            self._contents = []
            self._fill_contents()
        return self._contents

    def _fill_contents(self):
        r = 0
        for mod in self.first_moduli():
            self.add_row(mod)
            r += 1
            if r > self.maxrows:
                self.rowtruncate = True
                break

#############################################################################
###  Groups

class WebCharGroup(WebCharObject):
    """
    Class for presenting Character Groups on a web page
    self.H is the character group
    self.G is the underlying group
    """
    headers = [ 'order', 'primitive']
    _keys = [ 'title', 'credit', 'codelangs', 'type', 'nf', 'nflabel',
            'nfpol', 'modulus', 'modlabel', 'texname', 'codeinit', 'previous',
            'prevmod', 'next', 'nextmod', 'structure', 'codestruct', 'order',
            'codeorder', 'gens', 'generators', 'codegen', 'valuefield', 'vflabel',
            'vfpol', 'headers', 'groupelts', 'contents',
            'properties2', 'friends', 'rowtruncate', 'coltruncate']

    def __init__(self, **args):
        self._contents = None
        self.maxrows, self.maxcols = 35, 30
        self.rowtruncate, self.coltruncate = False, False
        WebCharObject.__init__(self, **args)

    @property
    def structure(self):
        inv = self.H.invariants()
        return '\(%s\)'%('\\times '.join(['C_{%s}'%d for d in inv]))

    @property
    def codestruct(self):
        return {'sage':'G.invariants()',
                'pari':'g.cyc'}

    @property
    def order(self):
        return self.H.order()

    @property
    def codeorder(self):
        return {'sage': 'G.order()',
                'pari': 'g.no' }

    @property
    def modulus(self):
        return self.ideal2tex(self._modulus)

    def add_row(self, chi):
        prim = chi.is_primitive()
        self._contents.append(
                 ( self._char_desc(chi, prim=prim),
                   ( chi.multiplicative_order(),
                     self.texbool(prim) ),
                     self.charvalues(chi) ) )

    @cached_method
    def first_chars(self):
        r = []
        for i,c in enumerate(self.H):
            r.append(c)
            if i > self.maxrows:
                self.rowtruncate = True
                break
        return r

    def _fill_contents(self):
        for c in self.first_chars():
            self.add_row(c)

    @property
    def properties2(self):
        return [("Modulus", [self.modulus]),
                ("Structure", [self.structure]),
                ("Order", [self.order]),
                ]

    @property
    def friends(self):
        if self.nflabel:
            return [ ("Number Field", '/NumberField/' + self.nflabel), ]

    @property
    def contents(self):
        if self._contents == None:
            self._contents = []
            self._fill_contents()
        return self._contents

#############################################################################
###  Characters

class WebChar(WebCharObject):
    """
    Class for presenting a Character on a web page
    """
    _keys = [ 'title', 'credit', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing', 'codeinducing',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties2', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman']

    def __init__(self, **args):
        self.maxcols = 30
        self.coltruncate = False
        WebCharObject.__init__(self, **args)

    @property
    def order(self):
        return self.chi.multiplicative_order()

    @property
    def codeorder(self):
        return { 'sage': 'chi.multiplicative_order()',
                 'pari': 'charorder(g,chi)' }

    @property
    def isprimitive(self):
        return self.texbool( self.chi.is_primitive() )

    @property
    def isreal(self):
        return self.texbool( self.order <= 2 )

    @property
    def values(self):
        return self.charvalues(self.chi)

    @property
    def conductor(self):
        return self.ideal2tex(self.chi.conductor())

    @property
    def modulus(self):
        return self.ideal2tex(self._modulus)

    @property
    def texname(self):
        return self.char2tex(self.chi)

    @property
    def condlabel(self):
        return self.ideal2label(self.conductor)

    @property
    def inducing(self):
        return self.char2tex(self.conductor, self.indlabel)

    @property
    def valuefield(self):
        """ compute order """
        order2 = self.order
        if order2 % 4 == 2:
            order2 = order2 / 2
        if order2 == 1:
            vf = r'\(\Q\)'
        elif order2 == 4:
            vf = r'\(\Q(i)\)'
        else:
            vf = r'\(\Q(\zeta_{%d})\)' % order2
        return vf

    @property
    def vflabel(self):
      order2 = self.order if self.order % 4 != 2 else self.order / 2
      if order2 == 1:
          return '1.1.1.1'
      elif order2 == 4:
          return '2.0.4.1'
      valuewnf =  WebNumberField.from_cyclo(order2)
      if not valuewnf.is_null():
          return valuewnf.label
      else:
          return ''

    @property
    def properties2(self):
        f = [("Conductor", [self.conductor]),
                ("Order", [self.order]),
                ("Real", [self.isreal]),
                ("Primitive", [self.isprimitive])]
        if self.parity:
            f.append(("Parity", [self.parity]))
        try:
            if self.orbit_label:
                formatted_orbit_label = "{}.{}".format(self.modulus, self.orbit_label)
                f.append(("Orbit Label", [formatted_orbit_label]))
        except KeyError:
            pass
        return f

    @property
    def friends(self):
        from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url

        f = []
        cglink = url_character(type=self.type,number_field=self.nflabel,modulus=self.modlabel)
        f.append( ("Character Group", cglink) )
        if self.nflabel:
            f.append( ('Number Field', '/NumberField/' + self.nflabel) )
        if self.type == 'Dirichlet' and self.chi.is_primitive() and self.conductor < 10000:
            url = url_character(type=self.type, number_field=self.nflabel, modulus=self.modlabel, number=self.numlabel)
            if get_lfunction_by_url(url[1:]):
                f.append( ('L-function', '/L'+ url) )
        if self.type == 'Dirichlet':
            f.append( ('Sato-Tate group', '/SatoTateGroup/0.1.%d'%self.order) )
        if len(self.vflabel)>0:
            f.append( ("Value Field", '/NumberField/' + self.vflabel) )
        return f

#############################################################################
###  Actual web objects used in lmfdb
class WebDirichletFamily(WebCharFamily, WebDirichlet):

    def _compute(self):
        WebDirichlet._compute(self)
        del self.args['modulus']
        logger.debug('######## WebDirichletFamily Computed')

    def first_moduli(self):
        """ restrict to conductors """
        return ( m for m in xrange(2, self.maxrows) if m%4!=2 )

    def chargroup(self, mod):
        return WebDirichletGroup(modulus=mod,**self.args)

    #def structure(self, G):
    #    inv = G.standard_dirichlet_group().generator_orders()
    #    return self.struct2tex(sorted(inv))

    @property
    def title(self):
        return "Dirichlet characters"

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

    @property
    def codeinit(self):
        return {
                'sage': [
                    'from dirichlet_conrey import DirichletGroup_conrey # requires nonstandard Sage package to be installed',
                    'H = DirichletGroup_conrey(%i)'%(self.modulus)
                    ],
                'pari': 'g = idealstar(,%i,2)'%(self.modulus)
                }

    @property
    def title(self):
      return r"Group of Dirichlet Characters of modulus %s" % (self.modulus)

    @property
    def codegen(self):
        return {'sage': 'H.gens()',
                'pari': 'g.gen' }

    @property
    def codestruct(self):
        return {'sage': 'H.invariants()',
                'pari': 'g.cyc'}

    @property
    def order(self):
        return self.H.order()


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
        self.maxcols = 30
        self.credit = ''
        self.codelangs = ('pari', 'sage')
        self._compute()

    @property
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
        self._set_parity(orbit_data)
        self._set_galoisorbit(orbit_data)

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
            self.generators = self.textuple( map(str, gens) )
            self.genvalues = self.textuple( map(self._tex_value, vals) )

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
        """
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
            return "\({}\)".format(ret)
        else:
            return ret

    def _set_isprimitive(self, orbit_data):
        if str(orbit_data['is_primitive']) == "True":
            self.isprimitive = "Yes"
        else:
            self.isprimitive = "No"

    def _set_parity(self, orbit_data):
        _parity = int(orbit_data['parity'])
        if _parity == -1:
            self.parity = 'Odd'
        else:
            self.parity = 'Even'

    def _set_galoisorbit(self, orbit_data):
        if self.modulus == 1:
            self.galoisorbit = [self._char_desc(1, mod=1,prim=True)]
            return
        upper_limit = min(200, self.order + 1)
        orbit = orbit_data['galois_orbit'][:upper_limit]
        self.galoisorbit = list(
            self._char_desc(num, prim=self.isprimitive) for num in orbit
        )


class WebDBDirichletGroup(WebDirichletGroup, WebDBDirichlet):
    """
    A class using data stored in the database. Currently this is all Dirichlet
    characters with modulus up to 10000.
    """
    headers = ['orbit label', 'order', 'primitive']

    def __init__(self, **kwargs):
        self._contents = None
        self.maxrows = 30
        self.maxcols = 30
        self.rowtruncate = False
        self.coltruncate = False
        WebDBDirichlet.__init__(self, **kwargs)
        self._set_groupelts()

    def add_row(self, chi):
        """
        Add a row to _contents for display on the webpage.

        Each row of content takes the form

            character_name, (header..data), (several..values)

        where `header..data` is expected to be a tuple of length the same
        size as `len(headers)`, and given in the same order as in `headers`,
        and where `several..values` are the values of the character
        on self.groupelts, in order.
        """
        mod = chi.modulus()
        num = chi.number()
        prim, order, orbit_label, valuepairs = self.char_dbdata(mod, num)
        formatted_orbit_label = "{}.{}".format(
            mod, cremona_letter_code(int(orbit_label.partition(".")[-1]) - 1)
        )
        self._contents.append((
            self._char_desc(num, mod=mod, prim=prim),
            (formatted_orbit_label, order, self.texbool(prim)),
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
    _keys = [ 'title', 'credit', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing', 'codeinducing',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties2', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman',
              'orbit_label']

    def __init__(self, **kwargs):
        self.maxcols = 30
        self.coltruncate = False
        WebDBDirichlet.__init__(self, **kwargs)

    @property
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    @property
    def title(self):
        return r"Dirichlet Character {}".format(self.texname)

    @property
    def symbol(self):
        return kronecker_symbol(self.symbol_numerator())

    @property
    def friends(self):
        from lmfdb.lfunctions.LfunctionDatabase import get_lfunction_by_url

        friendlist = []
        cglink = url_character(type=self.type, modulus=self.modulus)
        friendlist.append( ("Character Group", cglink) )
        if self.type == "Dirichlet" and self.isprimitive == "Yes":
            url = url_character(
                type=self.type,
                number_field=None,
                modulus=self.modulus,
                number=self.number
            )
            if get_lfunction_by_url(url[1:]):
                friendlist.append( ('L-function', '/L'+ url) )
            friendlist.append(
                ('Sato-Tate group', '/SatoTateGroup/0.1.%d' % self.order)
            )
        if len(self.vflabel) > 0:
            friendlist.append( ("Value Field", '/NumberField/' + self.vflabel) )
        return friendlist

    def symbol_numerator(self):
        """
        chi is equal to a kronecker symbol if and only if it is real
        """
        if self.order != 2:
            return None
        if self.parity == "Odd":
            return symbol_numerator(self.conductor, True)
        return symbol_numerator(self.conductor, False)

#######################
# The parts responsible for allowing computation of Gauss sums, etc. on page
    @property
    def charsums(self, *args):
        return False

    def gauss_sum(self, *args):
        return None

    def jacobi_sum(self, *args):
        return None

    def kloosterman_sum(self, *args):
        return None

    def value(self, *args):
        return None
########################

    @property
    def previous(self):
        return None

    @property
    def next(self):
        return None

    @property
    def codeinit(self):
        return {
          'sage': [ 'from dirichlet_conrey import DirichletGroup_conrey # requires nonstandard Sage package to be installed',
                 'H = DirichletGroup_conrey(%i)'%(self.modulus),
                 'chi = H[%i]'%(self.number) ],
          'pari': '[g,chi] = znchar(Mod(%i,%i))'%(self.number,self.modulus),
          }

    @property
    def codeisprimitive(self):
        return { 'sage': 'chi.is_primitive()',
                 'pari': '#znconreyconductor(g,chi)==1 \\\\ if not primitive returns [cond,factorization]' }

    @property
    def codecond(self):
        return { 'sage': 'chi.conductor()',
                 'pari': 'znconreyconductor(g,chi)' }

    @property
    def codeparity(self):
        return { 'sage': 'chi.is_odd()',
                 'pari': 'zncharisodd(g,chi)' }

    @property
    def codesymbol(self):
        m = self.symbol_numerator()
        if m:
            return { 'sage': 'kronecker_character(%i)'%m }
        return None

    @property
    def codegaloisorbit(self):
        return { 'sage': 'chi.sage_character().galois_orbit()',
                 'pari': [ 'order = charorder(g,chi)',
                           '[ charpow(g,chi, k % order) | k <-[1..order-1], gcd(k,order)==1 ]' ]
                 }


class WebSmallDirichletGroup(WebDirichletGroup):

    def _compute(self):
        if self.modlabel:
            self.modulus = m = int(self.modlabel)
            self.H = Integers(m).unit_group()
        self.credit = 'SageMath'
        self.codelangs = ('pari', 'sage')

    @property
    def contents(self):
        return None

    @property
    def gens(self):
        return self.H.gens_values()

    @property
    def generators(self):
        return self.textuple(map(str, self.H.gens_values()))


class WebSmallDirichletCharacter(WebChar, WebDirichlet):
    """
    Heritage: WebChar -> __init__()
              WebDirichlet -> _compute()
    """

    def _compute(self):
        self.modulus = int(self.modlabel)
        self.number = int(self.numlabel)
        self.chi = ConreyCharacter(self.modulus, self.number)
        self.credit = ''
        self.codelangs = ('pari', 'sage')

    @property
    def conductor(self):
        return self.chi.conductor()

    @property
    def previous(self):   return None
    @property
    def next(self):       return None
    @property
    def genvalues(self):  return None
    @property
    def indlabel(self):  return None
    def value(self, *args): return None

    @property
    def charsums(self, *args):
        return False

    def gauss_sum(self, *args): return None
    def jacobi_sum(self, *args): return None
    def kloosterman_sum(self, *args): return None


    @property
    def codeinit(self):
        return {
          'sage': [ 'from dirichlet_conrey import DirichletGroup_conrey # requires nonstandard Sage package to be installed',
                 'H = DirichletGroup_conrey(%i)'%(self.modulus),
                 'chi = H[%i]'%(self.number) ],
          'pari': '[g,chi] = znchar(Mod(%i,%i))'%(self.number,self.modulus),
          }

    @property
    def title(self):
        return r"Dirichlet Character %s" % (self.texname)

    @property
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    @property
    def codeisprimitive(self):
        return { 'sage': 'chi.is_primitive()',
                 'pari': '#znconreyconductor(g,chi)==1 \\\\ if not primitive returns [cond,factorization]' }

    @property
    def codecond(self):
        return { 'sage': 'chi.conductor()',
                 'pari': 'znconreyconductor(g,chi)' }

    @property
    def parity(self):
        return ('Odd', 'Even')[self.chi.is_even()]

    @property
    def codeparity(self):
        return { 'sage': 'chi.is_odd()',
                 'pari': 'zncharisodd(g,chi)' }

    @property
    def galoisorbit(self):
        order = self.order
        mod, num = self.modulus, self.number
        prim = self.isprimitive
        #beware this **must** be a generator
        upper_limit = min(200, order + 1)
        orbit = ( power_mod(num, k, mod) for k in xsrange(1, upper_limit)
                  if gcd(k, order) == 1) # use xsrange not xrange
        ret = list(self._char_desc(num, prim=prim) for num in orbit)
        return ret

    @property
    def orbit_label(self):
        if self.modulus > 10000:
            return
        logger.warning("Orbit label code was called. This shouldn't happen.")
        # Shortcut the trivial character, which behaves differently
        if self.conductor == 1:
            return 'a'
        orbit_dict = {}
        ordered_orbits = self.H._galois_orbits()
        for n, orbit in enumerate(ordered_orbits, 1):  # index at 1
            for character_number in orbit:
                orbit_dict[character_number] = n
        # The -1 in the line below is because labels index at 1, while the
        # cremona_letter_code indexes at 0
        return cremona_letter_code(orbit_dict[self.number] - 1)

    def symbol_numerator(self):
        """ chi is equal to a kronecker symbol if and only if it is real """
        if self.order != 2:
            return None
        return symbol_numerator(self.conductor, self.chi.is_odd())

    @property
    def symbol(self):
        return kronecker_symbol(self.symbol_numerator())

    @property
    def codesymbol(self):
        m = self.symbol_numerator()
        if m:
            return { 'sage': 'kronecker_character(%i)'%m }
        return None

    @property
    def codegaloisorbit(self):
        return { 'sage': 'chi.sage_character().galois_orbit()',
                 'pari': [ 'order = charorder(g,chi)',
                           '[ charpow(g,chi, k % order) | k <-[1..order-1], gcd(k,order)==1 ]' ]
                 }



class WebDirichletCharacter(WebSmallDirichletCharacter):
    """
    remove all computations for large moduli
    """
    _keys = [ 'title', 'credit', 'codelangs', 'type',
              'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
              'number', 'numlabel', 'texname', 'codeinit',
              'symbol', 'codesymbol',
              'previous', 'next', 'conductor',
              'condlabel', 'codecond',
              'isprimitive', 'codeisprimitive',
              'inducing', 'codeinducing',
              'indlabel', 'codeind', 'order', 'codeorder', 'parity', 'codeparity',
              'isreal', 'generators', 'codegenvalues', 'genvalues', 'logvalues',
              'groupelts', 'values', 'codeval', 'galoisorbit', 'codegaloisorbit',
              'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
              'kfpol', 'contents', 'properties2', 'friends', 'coltruncate',
              'charsums', 'codegauss', 'codejacobi', 'codekloosterman',
              'orbit_label']

    def _compute(self):
        WebDirichlet._compute(self)
        m = self.modulus
        self.number = n = int(self.numlabel)
        assert gcd(m, n) == 1
        self.chi = self.H[n]

    @property
    def previous(self):
        if self.modulus == 1:
            return ('',{})
        mod, num = self.prevchar(self.modulus, self.number, onlyprimitive=True)
        return (self.char2tex(mod, num), {'type':'Dirichlet', 'modulus':mod,'number':num})

    @property
    def next(self):
        mod, num = self.nextchar(self.modulus, self.number, onlyprimitive=True)
        return (self.char2tex(mod, num), {'type':'Dirichlet', 'modulus':mod,'number':num})

    @property
    def indlabel(self):
        """ Conrey scheme makes this trivial ? except at two..."""
        indlabel =  self.chi.primitive_character().number()
        if indlabel == 0:
            return 1
        return indlabel

    @property
    def codeinducing(self):
        return { 'sage': 'chi.primitive_character()',
                 'pari': ['znconreyconductor(g,chi,&chi0)','chi0'] }

    @property
    def genvalues(self):
        logvals = [self.chi.logvalue(k) for k in self.H.gens()]
        return self.textuple( map(self.texlogvalue, logvals) )

    @property
    def codegenvalues(self):
        return { 'sage': 'chi(k) for k in H.gens()',
                 'pari': '[ chareval(g,chi,x) | x <- g.gen ] \\\\ value in Q/Z' }

    def value(self, val):
        val = int(val)
        chartex = self.char2tex(self.modulus,self.number,val=val,tag=False)
        # FIXME: bug in dirichlet_conrey logvalue
        if gcd(val, self.modulus) == 1:
            val = self.texlogvalue(self.chi.logvalue(val))
        else:
            val = 0
        return '\(%s=%s\)'%(chartex,val)

    @property
    def codevalue(self):
        return { 'sage': 'chi(x) # x integer',
                 'pari': 'chareval(g,chi,x) \\\\ x integer, value in Q/Z' }

    @property
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
        chi = self.chi.sage_character()
        g = chi.gauss_sum_numerical(100, val)
        g = complex2str(g)
        from sage.rings.rational import Rational
        x = Rational('%s/%s' % (val, mod))
        n = x.numerator()
        n = str(n) + "r" if not n == 1 else "r"
        d = x.denominator()
        Gtex = '\Z/%s\Z' % mod
        chitex = self.char2tex(mod, num, tag=False)
        chitexr = self.char2tex(mod, num, 'r', tag=False)
        deftex = r'\sum_{r\in %s} %s e\left(\frac{%s}{%s}\right)'%(Gtex,chitexr,n,d)
        return r"\(\displaystyle \tau_{%s}(%s) = %s = %s \)" % (val, chitex, deftex, g)

    @property
    def codegauss(self):
        return { 'sage': 'chi.sage_character().gauss_sum(a)',
                 'pari': 'znchargauss(g,chi,a)' }

    def jacobi_sum(self, val):
        mod, num = self.modulus, self.number
        val = int(val)
        if gcd(mod, val) > 1:
            raise Warning ("n must be coprime to the modulus : %s"%mod)
        psi = self.H[val]
        chi = self.chi.sage_character()
        psi = psi.sage_character()
        jacobi_sum = chi.jacobi_sum(psi)
        chitex = self.char2tex(mod, num, tag=False)
        psitex = self.char2tex(mod, val, tag=False)
        Gtex = '\Z/%s\Z' % mod
        chitexr = self.char2tex(mod, num, 'r', tag=False)
        psitex1r = self.char2tex(mod, val, '1-r', tag=False)
        deftex = r'\sum_{r\in %s} %s %s'%(Gtex,chitexr,psitex1r)
        from sage.all import latex
        return r"\( \displaystyle J(%s,%s) = %s = %s \)" % (chitex, psitex, deftex, latex(jacobi_sum))

    @property
    def codejacobi(self):
        return { 'sage': 'chi.sage_character().jacobi_sum(n)' }

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
        chi = self.chi.sage_character()
        k = chi.kloosterman_sum_numerical(100, a, b)
        k = complex2str(k, 10)
        return r"""
        \( \displaystyle K(%s,%s,\chi_{%s}(%s,&middot;))
        = \sum_{r \in \Z/%s\Z}
             \chi_{%s}(%s,r) e\left(\frac{%s r + %s r^{-1}}{%s}\right)
        = %s \)""" % (a, b, modulus, number, modulus, modulus, number, a, b, modulus, k)

    @property
    def codekloosterman(self):
        return { 'sage': 'chi.sage_character().kloosterman_sum(a,b)' }


class WebHeckeExamples(WebHecke):
    """ this class only collects some interesting number fields """

    _keys = [ 'title', 'credit', 'headers', 'contents' ]
    headers = ['label','signature', 'polynomial' ]

    def __init__(self, **args):
        self._contents = None
        self.maxrows, self.rowtruncate = 25, False
        WebCharObject.__init__(self, **args)

    def _compute(self):
        self.nflabels = ['2.2.8.1',
                     '2.0.4.1',
                     '3.3.81.1',
                     '3.1.44.1',
                     #'4.4.2403.1',
                     #'4.2.283.1',
                     ]
        self.credit = "Pari, SageMath"
        self.codelangs = ('pari', 'sage')

    @property
    def title(self):
        return "Finite order Hecke characters"

    @property
    def contents(self):
        if self._contents is None:
            self._contents = []
            self._fill_contents()
        return self._contents

    def _fill_contents(self):
        for nflabel in self.nflabels:
            self.add_row(nflabel)

    def add_row(self, nflabel):
        nf = WebNumberField(nflabel)
        #nflink = (nflabel, url_for('number_fields.by_label',label=nflabel))
        nflink = (nflabel, url_for('characters.render_Heckewebpage',number_field=nflabel))
        #F = WebHeckeFamily(number_field=nflabel)
        self._contents.append( (nflink, nf.signature(), nf.web_poly() ) )


class WebHeckeFamily(WebCharFamily, WebHecke):

    def _compute(self):
        self.k = self.label2nf(self.nflabel)
        self.credit = 'Pari, SageMath'
        self.codelangs = ('pari', 'sage')

    def first_moduli(self, bound=200):
        """ first ideals which are conductors """
        bnf = self.k.pari_bnf()
        oldbound = 0
        while True:
            L = bnf.ideallist(bound)[oldbound:]
            for l in L:
                if l == []: next
                for ideal in l:
                    if gp.bnrisconductor(bnf,ideal):
                        yield self.k.ideal(ideal)
            """ double the range if one needs more ideal """
            oldbound = bound
            bound *=2

    """ for Hecke, I don't want to init WebHeckeGroup classes
        (recomputing number field and modulus is stupid)
        rewrite some things
    """
    def chargroup(self, mod):
        return RayClassGroup(self.k,mod).dual_group()

    #def structure(self, H):
    #    return self.struct2tex(H.invariants())

    #def struct2tex(self, inv):
    #    if not inv: inv = (1,)
    #    return '\(%s\)'%('\\times '.join(['C_{%s}'%d for d in inv]))

    def first_chars(self, H):
        r = []
        for i,c in enumerate(H.group().iter_exponents()):
            r.append(H(c))
            if i > self.maxrows:
                self.rowtruncate = True
                break
        return r

    def add_row(self, modulus):
        H = self.chargroup(modulus)
        order = H.order()
        struct = self.structure(H)
        firstchars = [ self._char_desc(c) for c in self.first_chars(H) ]
        self._contents.append( (self.ideal2label(modulus), order, struct, firstchars) )


    @property
    def title(self):
        return "Hecke characters"

class WebHeckeCharacter(WebChar, WebHecke):

    def _compute(self):
        WebHecke._compute(self)
        self.number = self.label2number(self.numlabel)
        assert len(self.number) == self.G.ngens()
        self.chi = HeckeChar(self.H, self.number)

        self.zetaorder = 0 # FIXME H.zeta_order()

    @property
    def codeinit(self):
        kpol = self.k.polynomial()
        mod = self.ideal2cas(self._modulus)
        return {
                'sage':  [
                          'k.<a> = NumberField(%s)'%kpol,
                          'm = k.ideal(%s)'%mod,
                          'from HeckeCharacters import RayClassGroup # use package in the lmfdb',
                          'G = RayClassGroup(k,m)',
                          'H = G.dual_group()',
                          'chi = H(%s)'%self.number
                          ],
                'pari':  [
                           'k=bnfinit(%s)'%str(kpol).replace('x','a'),
                           'm=idealhnf(k,%s)'%mod,
                           'g=bnrinit(k,m,1)',
                           'chi = %s'%self.number
                           ]
                }

    @property
    def title(self):
      return r"Hecke Character: %s modulo %s" % (self.texname, self.modulus)

    @property
    def codecond(self):
        return {
                'sage': 'chi.conductor()',
                'pari': 'bnrconductorofchar(g,chi)'
                }

    @property
    def inducing(self):
        #return lmfdb_hecke2tex(self.conductor(),self.indlabel())
        return None

    @property
    def indlabel(self):
        #return chi.primitive_character().number()
        return None

    @property
    def genvalues(self):
        logvals = self.chi.logvalues_on_gens()
        return self.textuple( map(self.texlogvalue, logvals))

    @property
    def galoisorbit(self):
        prim = self.isprimitive
        return  [ self._char_desc(c, prim=prim) for c in self.chi.galois_orbit() ]

    def value(self, val):
        chartex = self.char2tex(self.chi,val=val,tag=False)
        val = self.label2group(val)
        val = self.texlogvalue(self.chi.logvalue(val))
        return '\(%s=%s\)'%(chartex,val)

    def char4url(self, chi):
        # FIXME: call url_character and only return (label, url)
        if chi is None:
            return ('', {})
        label = self.char2tex(chi)
        args = {'type': 'Hecke',
                'number_field': self.nflabel,
                'modulus': self.ideal2label(chi.modulus()),
                'number': self.number2label(chi.exponents())}
        return (label, args)

    @property
    def previous(self):
        psi = self.chi.prev_character()
        return self.char4url(psi)

    @property
    def next(self):
        psi = self.chi.next_character()
        return self.char4url(psi)

class WebHeckeGroup(WebCharGroup, WebHecke):

    @property
    def codeinit(self):
        kpol = self.k.polynomial()
        mod = self.ideal2cas(self._modulus)
        return {
                'sage':  [
                          'k.<a> = NumberField(%s)'%kpol,
                          'm = k.ideal(%s)'%mod,
                          'from HeckeCharacters import RayClassGroup # use package in the lmfdb',
                          'G = RayClassGroup(k,m)',
                          'H = G.dual_group()',
                          ],
                'pari':  [
                           'k=bnfinit(%s)'%str(kpol).replace('x','a'),
                           'm=idealhnf(k,%s)'%mod,
                           'g=bnrinit(k,m,1)',
                           ]
                }


    @property
    def title(self):
        return "Group of Hecke characters modulo %s"%(self.modulus)

    @property
    def nfpol(self):
        #return self.nf.web_poly()
        return web_latex_split_on_pm(self.k.polynomial())

    @property
    def codegen(self):
        return {
                'sage': 'G.gen_ideals()',
                'pari': 'g.gen'
                }
