# -*- coding: utf-8 -*-
# Author: Pascal Molin, molin.maths@gmail.com
import math
# from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import re
from flask import url_for
from lmfdb.utils import parse_range, make_logger
logger = make_logger("DC")
from WebNumberField import WebNumberField
try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")
from HeckeCharacters import *

"""
Any character object is obtained as a double inheritance of

1. a family (currently: Dirichlet/Z or Hecke/K)

2. an object type (list of groups, character group, character)

The code thus defines, from the generic top class WebCharObject

1. the mathematical family classes

   - WebDirichlet

   - WebHecke

2. the mathematical objects classes

   - WebCharFamily

   - WebCharGroup

   - WebChar

and one obtains:

- WebDirichletFamily

- WebDirichletGroup

- WebDirichletCharacter

- WebHeckeFamily

- WebHeckeGroup

- WebHeckeCharacter

plus the additional WebHeckeExamples which collects interesting examples
of Hecke characters but could be converted to a yaml file [TODO]

"""

#############################################################################
###
###    small utilities to be removed one day
###
#############################################################################

def evalpolelt(label,gen,genlabel='a'):
    """ label is a compact polynomial expression in genlabel                    
        ( '*' and '**' are removed )                                            
    """                                                                         
    res = 0                                                                     
    import re                                                                   
    regexp = r'([+-]?)([+-]?\d*o?\d*)(%s\d*)?'%genlabel                         
    for m in re.finditer(regexp,label):                                         
        s,c,e = m.groups()                                                      
        if c == '' and e == None: break    
        if c == '':          
            c = 1                            
        else:                                
            """ c may be an int or a rational a/b """
            from sage.rings.rational import Rational
            c = str(c).replace('o','/')
            c = Rational(c)                                                      
        if s == '-': c = -c                                                     
        if e == None:                                                           
            e = 0                                                               
        elif e == genlabel:                                                     
            e = 1                                                               
        else:
            e = int(e[1:])                                                                   
        res += c*gen**e           
    return res              

def complex2str(g, digits=10):
    real = round(g.real(), digits)
    imag = round(g.imag(), digits)
    if imag == 0.:
        return str(real)
    elif real == 0.:
        return str(imag) + 'i'
    else:
        return str(real) + '+' + str(imag) + 'i'

###############################################################################
## url_for modified for characters
def url_character(**kwargs):
    if 'type' not in kwargs:
        return url_for('characters.render_characterNavigation')
    elif kwargs['type'] == 'Dirichlet':
        del kwargs['type']
        if kwargs.get('calc',None):
            return url_for('characters.dc_calc',**kwargs)
        else:
            return url_for('characters.render_Dirichletwebpage',**kwargs)
    elif kwargs['type'] == 'Hecke':
        del kwargs['type']
        if kwargs.get('calc',None):
            return url_for('characters.hc_calc',**kwargs)
        else:
            return url_for('characters.render_Heckewebpage',**kwargs)

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

        logger.debug('### class WebCharObject calls _compute')
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
        n = int(x.numer())
        d = int(x.denom())
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
            self.H = H = DirichletGroup_conrey(m)
        self.credit = 'Sage'
        self.codelangs = ('pari', 'sage')
        logger.debug('###### WebDirichletComputed')

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
        return ( mod, num, self.char2tex(mod,num), prim)

    def charisprimitive(self,mod,num):
        if isinstance(self.H, DirichletGroup_conrey) and self.H.modulus()==mod:
            H = self.H
        else:
            H = DirichletGroup_conrey(mod)
        return H[num].is_primitive()

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
        m,n = self.modulus, 1
        for k in xrange(1,m):
            if gcd(k,m) == 1:
                res.append(k)
                n += 1
                if n > self.maxcols:
                  self.coltruncate = True
                  break

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
        for k in xrange(n + 1, m):
            if gcd(m, k) == 1:
                return m, k
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
        for k in xrange(n - 1, 0, -1):
            if gcd(m, k) == 1:
                return m, k
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
        self.G = G = RayClassGroup(self.k, self._modulus)
        self.H = H = self.G.dual_group()
        #self.number = lmfdb_label2hecke(self.numlabel)
        # make this canonical
        self.modlabel = self.ideal2label(self._modulus)
        self.credit = "Pari, Sage"
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
    def ideal2label(ideal):
        """
        labeling convention for ideal f:
        use two elements representation f = (n,b)
        with n = f cap Z an integer
         and b an algebraic element sum b_i a^i
        label f as n.b1+b2*a^2+...bn*a^n
        (dot between n and b, a is the field generator, use '+' and )
        """
        a,b = ideal.gens_two()
        s = '+'.join( '%sa%i'%(b,i) for i,b in enumerate(b.polynomial().list())
                                      if b != 0 ) 
        return "%s.%s"%(a,s.replace('+-','-').replace('/','o'))

    @staticmethod
    def label2ideal(k,label):
        """ k = underlying number field """
        if label.count('.'):
            n, b = label.split(".")
        else:
            n, b = label, '0'
        a = k.gen()
        # FIXME: dangerous
        n, b = evalpolelt(n,a,'a'), evalpolelt(b,a,'a')
        n, b = k(n), k(b)
        return k.ideal( (n,b) )

           
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
    def group2label(x):
        return number2label(x.exponents())

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
        # FIXME: replace by calls to WebNF
        #x = var('x')
        #pol = evalpolelt(label,x,'x')
        #return NumberField(pol,'a')
 
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
    def __init__(self, **args):
        self._keys = [ 'title', 'credit', 'codelangs', 'type', 'nf', 'nflabel',
            'nfpol', 'codeinit', 'headers', 'contents' ]   
        self.headers = [ 'modulus', 'order', 'structure', 'first characters' ]
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
    def __init__(self, **args):
        self.headers = [ 'order', 'primitive']
        self._contents = None
        self.maxrows, self.maxcols = 25, 20
        self.rowtruncate, self.coltruncate = False, False
        self._keys = [ 'title', 'credit', 'codelangs', 'type', 'nf', 'nflabel',
            'nfpol', 'modulus', 'modlabel', 'texname', 'codeinit', 'previous',
            'prevmod', 'next', 'nextmod', 'structure', 'codestruct', 'order',
            'codeorder', 'generators', 'codegen', 'valuefield', 'vflabel',
            'vfpol', 'headers', 'groupelts', 'contents',
            'properties2', 'friends', 'rowtruncate', 'coltruncate'] 
        WebCharObject.__init__(self, **args)

    @property
    def structure(self):
        inv = self.H.invariants()
        return '\(%s\)'%('\\times '.join(['C_{%s}'%d for d in inv]))

    @property
    def codestruct(self):
        return [('sage','G.invariants()'), ('pari','G.cyc')]

    @property
    def order(self):
        return self.H.order()

    @property
    def codeorder(self):
        return [('sage','G.order()'), ('pari','G.no')]

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
        return [("Structure", [self.structure]),
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
    def __init__(self, **args):
        self.maxcols = 20
        self.coltruncate = False
        self._keys = [ 'title', 'credit', 'codelangs', 'type',
                 'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
                 'number', 'numlabel', 'texname', 'codeinit', 'symbol',
                 'previous', 'next', 'conductor',
                 'condlabel', 'codecond', 'isprimitive', 'inducing',
                 'indlabel', 'codeind', 'order', 'codeorder', 'parity',
                 'isreal', 'generators', 'codegen', 'genvalues', 'logvalues',
                 'groupelts', 'values', 'codeval', 'galoisorbit', 'codegalois',
                 'valuefield', 'vflabel', 'vfpol', 'kerfield', 'kflabel',
                 'kfpol', 'contents', 'properties2', 'friends', 'coltruncate']   
        WebCharObject.__init__(self, **args)

    @property
    def order(self):
        return self.chi.multiplicative_order()
    @property
    def codeorder(self):
        return [('sage', 'chi.multiplicative_order()'),]

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
        self._order2 = order2
        return vf

    @property
    def vflabel(self):
      _ = self.valuefield # make sure valuefield was computed
      order2 = self._order2
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
        return f

    @property
    def friends(self):
        f = []
        cglink = url_character(type=self.type,number_field=self.nflabel,modulus=self.modlabel)
        f.append( ("Character group", cglink) )
        if self.nflabel:
            f.append( ('Number Field', '/NumberField/' + self.nflabel) )
        if self.type == 'Dirichlet' and self.chi.is_primitive():
            f.append( ('L function', '/L'+ url_character(type=self.type,
                                    number_field=self.nflabel,
                                    modulus=self.modlabel,
                                    number=self.numlabel) ) )
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
        return [('sage', 'H = DirichletGroup_conrey(%i)\n'%(self.modulus)),
                ('pari', 'G = znstar(%i)'%(self.modulus) ) ]

    @property
    def title(self):
      return r"Dirichlet Group modulo %s" % (self.modulus)

    @property
    def codegen(self):
        return [('sage', 'H.gens()'),
                ('pari', 'G.gen') ]

    @property
    def codestruct(self):
        return [('sage', 'H.invariants()'),
                ('pari', 'G.cyc') ]
      
    @property
    def order(self):
        return self.H.order()

class WebDirichletCharacter(WebChar, WebDirichlet):
    """
    Heritage: WebCharacter -> __init__()
              WebDirichlet -> _compute()
    """           

    def _compute(self):
        WebDirichlet._compute(self)
        m = self.modulus
        self.number = n = int(self.numlabel)
        assert gcd(m, n) == 1
        self.chi = chi = self.H[n]

    @property
    def codeinit(self):
        return [('sage', 'H = DirichletGroup_conrey(%i)\n'%(self.modulus)
                       + 'chi = H[%i]'%(self.number)),
                ]
        
    @property
    def title(self):
        return r"Dirichlet Character %s" % (self.texname)

    @property
    def texname(self):
        return self.char2tex(self.modulus, self.number)

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
        #return self.number % self.conductor
        indlabel =  self.chi.primitive_character().number()
        if indlabel == 0:
            return 1
        return indlabel
    
    @property
    def parity(self):
        return ('Odd', 'Even')[self.chi.is_even()]

    @property
    def genvalues(self):
        logvals = [self.chi.logvalue(k) for k in self.H.gens()]
        return self.textuple( map(self.texlogvalue, logvals) )

    @property
    def galoisorbit(self):
        order = self.order
        mod, num = self.modulus, self.number
        prim = self.isprimitive
        orbit = ( power_mod(num, k, mod) for k in xrange(1, order) if gcd(k, order) == 1)
        return ( self._char_desc(num, prim=prim) for num in orbit )

    @property
    def symbol(self):
        return self.symbol_numerator() 

    def value(self, val):
        val = int(val)
        chartex = self.char2tex(self.modulus,self.number,val=val,tag=False)
        # FIXME: bug in dirichlet_conrey logvalue
        if gcd(val, self.modulus) == 1:
            val = self.texlogvalue(self.chi.logvalue(val))
        else:
            val = 0
        return '\(%s=%s\)'%(chartex,val)

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
        return r"\(\displaystyle \tau_{%s}(%s) = %s = %s. \)" % (val, chitex, deftex, g)

    def jacobi_sum(self, val):
        mod, num = self.modulus, self.number
        val = int(val[0])
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
        return r"\( \displaystyle J(%s,%s) = %s = %s.\)" % (chitex, psitex, deftex, latex(jacobi_sum))

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
        = %s. \)""" % (a, b, modulus, number, modulus, modulus, number, a, b, modulus, k)


    def symbol_numerator(self): 
#Reference: Sect. 9.3, Montgomery, Hugh L; Vaughan, Robert C. (2007). Multiplicative number theory. I. Classical theory. Cambridge Studies in Advanced Mathematics 97 
# Let F = Q(\sqrt(d)) with d a non zero squarefree integer then a real Dirichlet character \chi(n) can be represented as a Kronecker symbol (m / n) where { m  = d if # d = 1 mod 4 else m = 4d if d = 2,3 (mod) 4 }  and m is the discriminant of F. The conductor of \chi is |m|. 
# symbol_numerator returns the appropriate Kronecker symbol depending on the conductor of \chi. 
        """ chi is equal to a kronecker symbol if and only if it is real """
        if self.order != 2:
            return None
        cond = self.conductor
        if cond % 2 == 1:
            if cond % 4 == 1: m = cond
            else: m = -cond
        elif cond % 8 == 4:
	    # Fixed cond % 16 == 4 and cond % 16 == 12 were switched in the previous version of the code. 
            # Let d be a non zero squarefree integer. If d  = 2,3 (mod) 4 and if cond = 4d = 4 ( 4n + 2) or 4 (4n + 3) = 16 n + 8 or 16n + 12 then we set m = cond. 
            # On the other hand if d = 1 (mod) 4 and cond = 4d = 4 (4n +1) = 16n + 4 then we set m = -cond. 
            if cond % 16 == 4: m = -cond
            elif cond % 16 == 12: m = cond
        elif cond % 16 == 8:
            if self.chi.is_even(): m = cond
            else: m = -cond
        else:
            return None
        return r'\(\displaystyle\left(\frac{%s}{\bullet}\right)\)' % (m)



class WebHeckeExamples(WebHecke):
    """ this class only collects some interesting number fields """

    def __init__(self, **args):
        self._keys = [ 'title', 'credit', 'headers', 'contents' ]   
        self.headers = ['label','signature', 'polynomial' ]
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
        self.credit = "Pari, Sage"
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
        F = WebHeckeFamily(number_field=nflabel)
        self._contents.append( (nflink, nf.signature(), nf.web_poly() ) )


class WebHeckeFamily(WebCharFamily, WebHecke):

    def _compute(self):
        self.k = self.label2nf(self.nflabel)
        self.credit = 'Pari, Sage'
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
        self.chi = chi = HeckeChar(self.H, self.number)

        self.zetaorder = 0 # FIXME H.zeta_order()

    @property
    def codeinit(self):
        kpol = self.k.polynomial()
        return [('sage', '\n'.join(['k.<a> = NumberField(%s)'%kpol,
                          'm = k.ideal(%s)'%self.modulus,
                          'G = RayClassGroup(k,m)',
                          'H = G.dual_group()',
                          'chi = H(%s)'%self.number])),
                ('pari',  '\n'.join(['k=bnfinit(%s)'%kpol,
                           'G=bnrinit(k,m,1)',
                           'chi = %s'%self.number] )) ]

    @property
    def title(self):
      return r"Hecke Character: %s modulo %s" % (self.texname, self.modulus)
    
    @property
    def codecond(self):
        return [('sage', 'chi.conductor()'),
                ('pari', 'bnrconductorofchar(G,chi)')]

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
        return [('sage', '\n'.join(['k.<a> = NumberField(%s)'%kpol,
                          'm = k.ideal(%s)'%self.modulus,
                          'G = RayClassGroup(k,m)',
                          'H = G.dual_group()' ])),
                ('pari',  '\n'.join(['k=bnfinit(%s)'%kpol,
                           'G=bnrinit(k,m,1)']) )
                ]

    @property
    def title(self):
        return "Group of Hecke characters modulo %s"%(self.modulus)

    @property
    def nf_pol(self):
        #return self.nf.web_poly()
        return self.k.polynomial()._latex_()

    @property
    def codegen(self):
        return [('sage','G.gen_ideals()'), ('pari','G.gen')]

