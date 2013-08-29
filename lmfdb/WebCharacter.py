# -*- coding: utf-8 -*-
import math
# from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
import re
import pymongo
import bson
from lmfdb.utils import parse_range, make_logger
logger = make_logger("DC")
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import *
from WebNumberField import WebNumberField
try:
    from dirichlet_conrey import *
except:
    logger.critical("dirichlet_conrey.pyx cython file is not available ...")
from HeckeCharacters import *

def lmfdb_ideal2label(ideal):
      """
      labeling convention for ideal f:
      use two elements representation f = (n,b)
      with n = f cap Z an integer
       and b an algebraic element sum b_i a^i
      label f as n.b1+b2*a^2+...bn*a^n
      (dot between n and b, a is the field generator, use '+' and )
      """
      a,b = ideal.gens_two()
      s = '+'.join( '%s*a**%i'%(b,i) for i,b in enumerate(b.polynomial().list())
                                    if b != 0 ) 
      return "%s.%s"%(a,b)

def lmfdb_label2ideal(k,label):
      if label.count('.'):
          n, b = label.split(".")
      else:
          n, b = label, '0'
      a = k.gen()
      n, b = eval(n), eval(b)
      n, b = k(n), k(b)
      return k.ideal( (n,b) )

def lmfdb_ideal2tex(ideal):
    a,b = ideal.gens_two()
    return "\langle %s, %s\\rangle"%(a._latex_(), b._latex_())

def lmfdb_hecke2label(chi):
    """
    label of Hecke character
    """
    return '.'.join(map(str,chi.exponents()))

def lmfdb_hecke2tex(chi):
    """
    label of Hecke character
    """
    return r'\(\chi_{%s}(\cdot)\)'%(','.join(map(str,chi.exponents())))

def lmfdb_label2hecke(label):
    """
    label of Hecke character
    """
    return map(int,label.split('.'))

def lmfdb_dirichlet2tex(mod,num):
    return r'\(\chi_{%s}(%s,\cdot)\)'%(mod,num)

def lmfdb_bool(b):
    return ("No","Yes")[b]

def latex_char_logvalue(x, tag=False):
    n = int(x.numer())
    d = int(x.denom())
    if d == 1:
        s = "1"
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

def latex_tuple(v):
    if len(v) == 1:
        return v[0]
    else:
        return "(%s)" % (', '.join(v))


def log_value(modulus, number):
    """
    return the list of values of a given Dirichlet character
    """
    from dirichlet_conrey import DirichletGroup
    G = DirichletGroup_conrey(modulus)
    chi = G[number]
    l = []
    for j in range(1, modulus + 1):
        if gcd(j, modulus) != 1:
            l.append('0')
        else:
            logvalue = chi.logvalue(j)
            l.append(latex_char_logvalue(logvalue, True))
    return l

#############################################################################
###
###    Class for Web objects
###
#############################################################################

class WebCharObject:
    """ class for all characters and character groups """
    def __init__(self, args):
        self._keys = [ 'title', 'credit', 'codelangs',
                 'nf', 'nflabel', 'nfpol', 'modulus', 'modlabel',
                 'number', 'numlabel', 'texname', 'codeinit', 'symbol',
                 'previous', 'prevmod', 'prevnum', 'next', 'nextmod',
                 'nextnum', 'structure', 'codestruct', 'conductor',
                 'condlabel', 'codecond', 'isprimitive', 'inducing',
                 'indlabel', 'codeind', 'order', 'codeorder', 'parity',
                 'isreal', 'generators', 'codegen', 'genvalues', 'logvalues',
                 'values', 'codeval', 'galoisorbit', 'codegalois',
                 'valuefield', 'vflabel', 'vfpol',
                 'kerfield', 'kflabel', 'kfpol', 'contents' ]   
        self.nflabel = args.get('number_field',None)
        self.modlabel = args.get('modulus',None)
        self.numlabel = args.get('number',None)

        self._compute()

    def _compute(self):
        pass

    def to_dict(self):
        d = {}
        for k in self._keys:
            d[k] = getattr(self,k,None)
            if d[k] == None:
                pass # should not
        return d

    @staticmethod
    def logvalue2tex(x, tag=False):
        n = int(x.numer())
        d = int(x.denom())
        if d == 1:
            s = "1"
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


#############################################################################
###  Dirichlet type

class WebDirichlet(WebCharObject):

    def _char_desc(self, num, mod=None):
        if mod == None:
            mod = self.modulus
        return ( mod, num, self.char2tex(mod,num))

    @staticmethod
    def char2tex(modulus, number):
        return r'\(\chi_{%s}(%s,\cdot)\)'%(modulus,number)


#############################################################################
###  Hecke type

class WebHecke(WebCharObject):
    """ labeling conventions are put here """

    @staticmethod
    def char2tex(c):
        """ c is a Hecke character """
        number = c.exponents()
        return r'\(\chi_{%s}(\cdot)\)'%(','.join(map(str,number)))

    def _char_desc(self, c, modlabel=None):
        """ c is a Hecke character of modulus self.modulus
            unless modlabel is specified
        """
        if modlabel == None:
            modlabel = self.modlabel
        numlabel = self.number2label( c.exponents() )
        return (modlabel, numlabel, self.char2tex(c) ) 

    @staticmethod
    def group2tex(ideal):
        a,b = ideal.gens_two()
        return "\(\langle %s, %s\\rangle\)"%(a._latex_(), b._latex_())

    @staticmethod
    def modulus2tex(ideal):
        a,b = ideal.gens_two()
        return "\(\langle %s, %s\\rangle\)"%(a._latex_(), b._latex_())

    @staticmethod
    def modulus2label(ideal):
        """
        labeling convention for ideal f:
        use two elements representation f = (n,b)
        with n = f cap Z an integer
         and b an algebraic element sum b_i a^i
        label f as n.b1+b2*a^2+...bn*a^n
        (dot between n and b, a is the field generator, use '+' and )
        """
        a,b = ideal.gens_two()
        s = '+'.join( '%s*a**%i'%(b,i) for i,b in enumerate(b.polynomial().list())
                                      if b != 0 ) 
        return "%s.%s"%(a,b)

    @staticmethod
    def label2modulus(k,label):
        if label.count('.'):
            n, b = label.split(".")
        else:
            n, b = label, '0'
        a = k.gen()
        n, b = eval(n), eval(b)
        n, b = k(n), k(b)
        return k.ideal( (n,b) )

    @staticmethod
    ### not static and put self as argument ?
    def number2label(number):
        return '.'.join(map(str,number))

    @staticmethod
    def label2number(label):
        return map(int,label.split('.'))

#############################################################################
###  Family

class WebCharFamily(WebCharObject):
    """ compute first groups """
    def __init__(self, args):
        WebCharObject.__init__(self,args)
        self._keys = [ 'title', 'credit', 'codelangs', 'nf', 'nflabel',
            'nfpol', 'codeinit', 'headers', 'contents' ]   
        self.headers = [ 'label', 'order', 'structure' ]
        self._contents = []

    def add_row(self, G):
        self._contents.append(
                 (G.modlabel,
                  G.texname,
                  G.order,
                  G.structure) )

#############################################################################
###  Groups

class WebCharGroup(WebCharObject):
    """
    Class for presenting Character Groups on a web page
    """
    def __init__(self, args):
        WebCharObject.__init__(self,args)
        self._keys = [ 'title', 'credit', 'codelangs', 'nf', 'nflabel',
            'nfpol', 'modulus', 'modlabel', 'texname', 'codeinit', 'previous',
            'prevmod', 'next', 'nextmod', 'structure', 'codestruct', 'order',
            'codeorder', 'generators', 'codegen', 'valuefield', 'vflabel',
            'vfpol', 'headers', 'contents' ] 
        self.headers = [ 'label', 'order', 'structure' ]
        self.contents = []

    @property
    def structure(self):
        inv = self.G.invariants()
        return '\\times '.join(['C_{%s}'%d for d in inv])
    @property
    def codestruct(self):
        return [('sage',['G.invariants()']), ('pari',['G.cyc'])]

    @property
    def order(self):
        return self.G.order()
    @property
    def codeorder(self):
        return [('sage','G.order()'), ('pari','G.no')]

    @property
    def generators(self):
        return latex_tuple(map(self.group2tex, self.G.gens()))

    def add_row(self, chi):
        self.contents.append(
                 (chi.modlabel,
                  chi.numlabel,
                  chi.texname,
                  chi.order,
                  chi.isprimitive )
            )
     
    def _fill_contents(self):
        if self.H is not None:
            for c in self.H.list():
                self.add_row(c)

#############################################################################
###  Characters

class WebChar(WebCharObject):
    """
    Class for presenting a Character on a web page
    """

    @property
    def order(self):
        return self.chi.order()

    @property
    def isprimitive(self):
        return lmfdb_bool( self.chi.is_primitive() )

    @property
    def isreal(self):
        return lmfdb_bool( self.order <= 2 )

    @property
    def valuefield(self):
        """ compute order """
        order2 = self.order
        if order2 % 4 == 2:
            order2 = order2 / 2
        if order2 == 1:
            vf = r'\(\mathbb{Q}\)'
        elif order2 == 4:
            vf = r'\(\mathbb{Q}(i)\)'
        else:
            vf = r'\(\mathbb{Q}(\zeta_{%d})\)' % order2
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

#############################################################################
###  Actual web objects used in lmfdb

class WebDirichletGroup(WebDirichlet, WebCharGroup):

    def _compute(self):
        self.modulus = m = int(self.modlabel)
        self.G = G = DirichletGroup_conrey(m)
        self.G_sage = G_sage = G.standard_dirichlet_group()
        self.credit = 'Sage'
        self.codelangs = ('pari', 'sage')
        
    @property
    def codeinit(self):
        kpol = self.nf.K().polynomial()
        return [('sage', ['G = DirichletGroup_conrey(m)']),
                ('pari', ['G = znstar(m)'])
                ]

    @property
    def title(self):
      return r"Dirichlet Group modulo %s" % (self.modulus)

    @property
    def generators(self):
        return latex_tuple(self.G.gens())


class WebDirichletCharacter(WebDirichlet, WebChar):

    def _compute(self):
        self.modulus = m = int(self.modlabel)
        self.G = G = DirichletGroup_conrey(m)
        self.G_sage = G_sage = G.standard_dirichlet_group()
        self._gens = G_sage.unit_gens()
        self.number = n = int(self.numlabel)

        assert gcd(m, n) == 1
        self.chi = chi = G[n]
        self.chi_sage = chi_sage = chi.sage_character()
        self.order = chi.multiplicative_order()
        self.credit = "Sage"
        self.codelangs = ('pari', 'sage')
        self.prevmod, self.prevnum = prev_dirichlet_char(m, n)
        self.nextmod, self.nextnum = next_dirichlet_char(m, n)

    @property
    def title(self):
        return r"Dirichlet Character %s" % (self.texname)

    @property
    def texname(self):
        return self.char2tex(self.modulus, self.number)

    @property
    def previous(self):
        return self.char2tex(self.prevmod, self.prevnum)

    @property
    def next(self):
        return self.char2tex(self.nextmod, self.nextnum)

    @property
    def conductor(self):
        return self.chi.conductor()

    @property
    def condlabel(self):
        return self.conductor

    @property
    def inducing(self):
        return self.char2tex(self.conductor, self.indlabel)

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
    def generators(self):
        return '\(%s\)'%(','.join( map(str, self._gens)) )

    @property
    def genvalues(self):
        logvals = [self.chi.logvalue(k) for k in self._gens]
        return '\(%s\)'%(','.join( map(self.logvalue2tex, logvals)) )

    @property
    def galoisorbit(self):
        order = self.order
        mod, num = self.modulus, self.number
        orbit = [ power_mod(num, k, mod) for k in xrange(1, order) if gcd(k,order) == 1 ]
        return [ self._char_desc(num) for num in orbit ]

    @property
    def symbol(self):
        """ chi is equal to a kronecker symbol if and only if it is real """
        if self.order != 2:
            return None
        cond = self.conductor
        if cond % 2 == 1:
            if cond % 4 == 1: m = cond
            else: m = -cond
        elif cond % 8 == 4:
            if cond % 16 == 4: m = cond
            elif cond % 16 == 12: m = -cond
        elif cond % 16 == 8:
            if self.chi.is_even(): m = cond
            else: m = -cond
        else:
            return None
        return r'\(\displaystyle\left(\frac{%s}{\bullet}\right)\)' % (m)

class WebHeckeCharacter(WebChar):

    def _compute(self):
        self._nf = WebNumberField(self.nflabel)
        k = self.nf.K()
        self._modulus = lmfdb_label2ideal(k, self.modlabel)
        self.G = G = RayClassGroup(k, self.modulus)
        self.H = H = self.G.dual_group()
        #self.number = lmfdb_label2hecke(self.numlabel)
        self.modlabel = lmfdb_ideal2label(self._modulus)
 
        assert len(self.number) == G.ngens()
        self.chi = chi = HeckeChar(self.H, self.number)

        self.order = chi.order()
        self.zetaorder = 0 # FIXME H.zeta_order()
        self.parity = 'None'
        self.credit = "Pari, Sage"
        self.codelangs = ('pari', 'sage')

    @property
    def title(self):
      return r"Hecke Character: %s modulo \(%s\)" % (self.texname, self.modulus)
    
    @property
    def inducing(self):
        #return lmfdb_hecke2tex(self.conductor(),self.indlabel())
        return None

    @property
    def indlabel(self):
        #return chi.primitive_character().number()
        return None

    @property
    def generators(self):
        return '\(%s\)'%(','.join( map(lmfdb_ideal2tex, self.G.gen_ideals() )) )

    @property
    def genvalues(self):
        logvals = self.chi.logvalues_on_gens()
        return '\(%s\)'%(','.join( map(self.logvalue2tex, logvals)) )

    @property
    def galoisorbit(self):
        return  [ self._char_desc(c) for c in chi.galois_orbit() ]

    @property
    def texname(self):
        return lmfdb_hecke2tex(chi)

    @property
    def conductor(self):
        return lmfdb_ideal2tex(chi.conductor())

    @property
    def modulus(self):
        return self.modulus2tex(self._modulus)

def next_dirichlet_char(m, n, onlyprimitive=False):
    """ we know that the characters
        chi_m(1,.) and chi_m(m-1,.)
        always exist for m>1.
        They are extremal for a given m.
    """
    if onlyprimitive:
        return next_primitive_char(m, n)
    if m == 1:
        return 2, 1
    if n == m - 1:
        return m + 1, 1
    for k in xrange(n + 1, m):
        if gcd(m, k) == 1:
            return m, k
    raise Exception("next_char")

def prev_dirichlet_char(m, n, onlyprimitive=False):
    """ Assume m>1 """
    if onlyprimitive:
        return prev_primitive_char(m, n)
    if n == 1:
        m, n = m - 1, m
    if m <= 2:
        return m, 1  # important : 2,2 is not a character
    for k in xrange(n - 1, 0, -1):
        if gcd(m, k) == 1:
            return m, k
    raise Exception("next_char")

def prev_dirichlet_primitive_char(m, n):
    if m <= 3:
        return 1, 1
    if n > 2:
        Gm = DirichletGroup_conrey(m)
    while True:
        n -= 1
        if n == 1:  # (m,1) is never primitive for m>1
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

def next_dirichlet_primitive_char(m, n):
    if m < 3:
        return 3, 2
    if n < m - 1:
        Gm = DirichletGroup_conrey(m)
    while 1:
        n += 1
        if n == m:
            m, n = m + 1, 2
            Gm = DirichletGroup_conrey(m)
        if gcd(m, n) != 1:
            continue
        # we have a character, test if it is primitive
        chi = Gm[n]
        if chi.is_primitive():
            return m, n

class WebHeckeGroup(WebCharGroup):

    def _compute(self):
        self.nf = WebNumberField(self.nflabel)
        k = self.nf.K()
        self.modulus = lmfdb_label2ideal(k, self.modlabel)
        self.G = RayClassGroup(k, self.modulus)
        self.H = self.G.dual_group()
        self.order = self.G.order()
        self._fill_contents()
        self.credit = 'Pari, Sage'
        self.codelangs = ('pari', 'sage')
 
    @property
    def codeinit(self):
        kpol = self.nf.K().polynomial()
        return [('sage', ['k.<a> = NumberField(%s)'%kpol,
                          'm = k.ideal(%s)'%self.modulus,
                          'G = RayClassGroup(k,m)',
                          'H = G.dual_group()' ]),
                ('pari',  ['k=bnfinit(%s)'%kpol,
                           'G=bnrinit(k,m,1)'] )
                ]

    @property
    def nf_pol(self):
        return self.nf.web_poly()

    @property
    def generators(self):
        return latex_tuple(map(self.ideal2tex, self.G.gen_ideals()))
    @property
    def codegen(self):
        return [('sage','G.gen_ideals()'), ('pari','G.gen')]

    def _char_table_row(self, c):
        return ( self.modlabel,
                 lmfdb_hecke2label(c),
                 lmfdb_hecke2tex(c),
                 str(c.order()),
                 lmfdb_bool(c.is_primitive()),
                 )

    @cached_method
    def table_content(self):
        """ build list: (tex, link, order, primitive) """
        return [ self._char_table_row(c) for c in self.H.list() ]

    def title(self):
        return "Group of Hecke characters modulo %s"%(self.mod())

#############################################################################
###
###    OLD MATERIAL
###
#############################################################################

class WebCharacter:
    """
    Class for presenting a Character on a web page
    """
    def __init__(self, dict):
        self.type = dict['type']
        # self.texname = "\\chi"  # default name.  will be set later, for most L-functions
        self.citation = ''
        self.credit = ''
        if self.type == 'dirichlet':
            self.modulus = int(dict['modulus'])
            self.number = int(dict['number'])
            self.dirichletcharacter()
            self._set_properties()
        elif self.type == 'hecke':
            # need Sage number field... easier way ?
            k = WebNumberField(dict['number_field']).K()
            self.number_field = k
            self.modulus = lmfdb_label2ideal(k, dict['modulus'])
            self.number = lmfdb_label2hecke(dict['number'])
            self.heckecharacter()
            self._set_properties()

    def _set_properties(self):
        conductor = self.conductor
        primitive = self.primitive
        if primitive == "True":
            self.prim = "Yes"
        else:
            self.prim = "No"
        if self.order <= 2:
            self.real = "Yes"
        else:
            self.real = "No"
        order = str(self.order)
        self.properties = [("Conductor", [conductor]),
                           ( "Order", [order]),
                           ("Parity", [self.parity]),
                           ("Real", [self.real]),
                           ("Primitive", [self.prim])]
        
    def dirichletcharacter(self):

        #######################################################################################
        ##  Conrey's naming convention for Dirichlet Characters
        #######################################################################################

        G = DirichletGroup_conrey(self.modulus)
        G_sage = G.standard_dirichlet_group()
        self.level = self.modulus
        if self.modulus == 1 or self.number % self.modulus != 0:
            chi = G[self.number]
            chi_sage = chi.sage_character()
            self.chi_sage = chi_sage
            self.zetaorder = G_sage.zeta_order()
            # if len(chi_sage.values_on_gens()) == 1:
            ###    self.genvaluestex = latex(chi_sage.values_on_gens()[0])
            # else:
            ###    self.genvaluestex = latex(chi_sage.values_on_gens())
            # chizero = G_sage[0]
            self.char = str(chi)
            if chi.is_primitive():
                self.primitive = "True"
            else:
                self.primitive = "False"
            self.conductor = chi.conductor()
            self.order = chi.multiplicative_order()
            self.galoisorbit = [ power_mod(self.number, k, self.modulus) for k in xrange(1, self.order) if gcd(k, self.order) == 1 ]
            self.vals = chi.values()
            self.logvals = log_value(self.modulus, self.number)
            # self.logvals = map(chi.logvalue, range(1,self.modulus+1))
            # self.logvals = [latex_char_logvalue(k,True) for k in self.logvals]
            Gunits = G_sage.unit_gens()
            if self.modulus == 2:
                Gunits = [1]
            self.unitgens = latex_tuple(map(str, Gunits))
            self.genvalues = chi_sage.values_on_gens()  # what is the use ?
            self.genlogvalues = [chi.logvalue(k) for k in Gunits]
            self.genvaluestex = latex_tuple(map(latex_char_logvalue, self.genlogvalues))
            self.bound = 5 * 1024
            if chi.is_even():
                self.parity = 'Even'
            else:
                self.parity = 'Odd'
            if self.primitive == "False":
                self.inducedchar = chi.primitive_character()
                self.inducedchar_isprim = self.inducedchar.is_primitive()
                self.inducedchar_modulus = self.inducedchar.modulus()
                self.inducedchar_conductor = self.inducedchar.conductor()
                F = DirichletGroup_conrey(self.inducedchar_modulus)
                if self.number == 1:
                    self.inducedchar_number = 1
                else:
                    for chi in F:
                        j = chi.number()
                        if chi == self.inducedchar:
                            self.inducedchar_number = j
                            break
                self.inducedchar_tex = r"\(\chi_{%s}(%s,\cdot)\)" % (
                    self.inducedchar_modulus, self.inducedchar_number)
       # if self.primitive == 'True':
       #     self.primtf = True
       # else:
       #     self.primtf = False
            # Set data for related number fields
            order2 = int(self.order)
            if order2 % 4 == 2:
                order2 = order2 / 2
            self.valuefield = r'\(\mathbb{Q}(\zeta_{%d})\)' % order2
            if order2 == 1:
                self.valuefield = r'\(\mathbb{Q}\)'
            if order2 == 4:
                self.valuefield = r'\(\mathbb{Q}(i)\)'
            valuewnf = WebNumberField.from_cyclo(order2)
            if not valuewnf.is_null():
                self.valuefield_label = valuewnf.label
            else:
                self.valuefield_label = ''
            self.texname = r'\chi_{%d}(%d, \cdot)' % (self.modulus, self.number)
            self.kername = r'\(\mathbb{Q}(\zeta_{%d})^{\ker %s}\)' % (self.modulus, self.texname)

            if self.order < 16:
                pol = str(gp.galoissubcyclo(self.modulus, self.chi_sage.kernel()))
                sagepol = PolynomialRing(QQ, 'x')(pol)
                R = sagepol.parent()
                nf_pol = R(pari(sagepol).polredabs())
                self.nf_pol = "\( %s \)" % latex(nf_pol)
                wnf = WebNumberField.from_coeffs([int(c) for c in nf_pol.coeffs()])
                if wnf.is_null():
                    self.nf_friend = ''
                else:
                    self.nf_friend = '/NumberField/' + str(wnf.label)
                    self.nf_label = wnf.label
            else:
                self.nf_pol = ''
                self.nf_friend = ''

            if self.order == 2:
                if self.conductor % 2 == 1:
                    self.kronsymbol = r"\begin{equation} \chi_{%s}(a) = " % (self.number)
                    self.kronsymbol += r"\left(\frac{a}{%s}\right)" % (self.conductor)
                    self.kronsymbol += r"\end{equation}"
                else:
                    if chi.is_even():
                        self.kronsymbol = r"\begin{equation}  \chi_{%s}(a) = " % (self.number)
                        self.kronsymbol += r"\left(\frac{a}{%s}\right)" % (self.conductor)
                        self.kronsymbol += r"\end{equation}"
                    else:
                        self.kronsymbol = r"\begin{equation}  \chi_{%s}(a) = " % (self.number)
                        self.kronsymbol += r"\left(\frac{a}{%s}\right)" % (self.conductor)
                        self.kronsymbol += r"\end{equation}"

        self.credit = "Sage"
        self.title = r"Dirichlet Character: \(\chi_{%s}(%s,\cdot)\)" % (self.modulus, self.number)

        return chi

    def heckecharacter(self):

        G = RayClassGroup(self.number_field, self.modulus)
        H = G.dual_group()
        assert len(self.number) == G.ngens()
        chi = HeckeChar(H,self.number)

        self.order = chi.order()
        self.zetaorder = 0 # FIXME H.zeta_order()

        self.unitgens = latex_tuple(map(lmfdb_ideal2tex, G.gen_ideals()))
        self.genvaluestex = latex_tuple(map(latex_char_logvalue, chi.logvalues_on_gens()))


        # not relevant over ideals
        #self.parity = ('Odd', 'Even')[chi.is_even()]
        self.parity = 'None'

        self.conductor = lmfdb_ideal2tex(chi.conductor())

        self.primitive = str(chi.is_primitive())

        self.texname = lmfdb_hecke2tex(chi)
        
        order2 = int(self.order)
        if order2 % 4 == 2:
            order2 = order2 / 2
        self.valuefield = r'\(\mathbb{Q}(\zeta_{%d})\)' % order2
        if order2 == 1:
            self.valuefield = r'\(\mathbb{Q}\)'
        if order2 == 4:
            self.valuefield = r'\(\mathbb{Q}(i)\)'
        valuewnf = WebNumberField.from_cyclo(order2)
        if not valuewnf.is_null():
            self.valuefield_label = valuewnf.label
        else:
            self.valuefield_label = ''
        
        mod_tex = lmfdb_ideal2tex(self.modulus)
        mod_label = lmfdb_ideal2label(self.modulus)
        self.galoisorbit = [ ( mod_label, lmfdb_hecke2label(c), lmfdb_hecke2tex(c) ) for c in chi.galois_orbit() ]

        self.credit = "Pari, Sage"
        self.title = r"Hecke Character: %s modulo \(%s\)" % (self.texname, mod_tex)

        return chi

