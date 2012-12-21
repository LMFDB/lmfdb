# -*- coding: utf-8 -*-
import math
#from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
import re
import pymongo
import bson
from utils import parse_range, make_logger
logger = make_logger("DC")
#import web_modforms
from modular_forms.elliptic_modular_forms.backend.web_modforms import *
from WebNumberField import WebNumberField
try:
  from dirichlet_conrey import *
except:
  logger.critical("dirichlet_conrey.pyx cython file is not available ...")

def latex_char_logvalue(x,tag=False):
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
        s = r"e\left(\frac{%s}{%s}\right)" % (n,d)
    if tag:
        return "\(%s\)" % s
    else:
        return s

def latex_tuple(v):
    if len(v) == 1:
      return v[0]
    else:
      return "(%s)" % (', '.join(v))

def log_value(modulus,number):
    """
    return the list of values of a given character
    """
    from dirichlet_conrey import DirichletGroup
    G = DirichletGroup_conrey(modulus)
    chi = G[number]
    l = []
    for j in range(1, modulus+1):
      if gcd(j,modulus) != 1:
        l.append('0')
      else:
        logvalue = chi.logvalue(j)
        l.append(latex_char_logvalue(logvalue,True))
    return l

class WebCharacter:
    """Class for presenting a Character on a web page

    """
    def __init__(self, dict):
        self.type = dict['type']
        # self.texname = "\\chi"  # default name.  will be set later, for most L-functions
        # self.primitive = True # should be changed
        self.citation = ''
        self.credit = ''
        if self.type=='dirichlet':
            self.modulus = int(dict['modulus'])
            self.number = int(dict['number'])
            self.dirichletcharacter()
            self._set_properties()

#===================  Set all the properties for different types of Characters


    def dirichletcharacter(self):

        #######################################################################################
        ##  Conrey's naming convention for Dirichlet Characters
        #######################################################################################

        G = DirichletGroup_conrey(self.modulus)
        G_sage = G.standard_dirichlet_group()
        self.level = self.modulus
        if self.modulus == 1 or self.number%self.modulus != 0:
            chi = G[self.number]
            chi_sage = chi.sage_character()
            self.chi_sage = chi_sage
            self.zetaorder = G_sage.zeta_order()
            ###if len(chi_sage.values_on_gens()) == 1:
            ###    self.genvaluestex = latex(chi_sage.values_on_gens()[0])
            ###else:
            ###    self.genvaluestex = latex(chi_sage.values_on_gens())
            ###chizero = G_sage[0]
            self.char = str(chi)
            if chi.is_primitive():
                self.primitive = "True"
            else:
                self.primitive = "False"
            self.conductor = chi.conductor()
            self.order = chi.multiplicative_order()
            self.vals = chi.values()
            self.logvals = log_value(self.modulus,self.number)
            #self.logvals = map(chi.logvalue, range(1,self.modulus+1))
            #self.logvals = [latex_char_logvalue(k,True) for k in self.logvals]
            Gunits = G_sage.unit_gens()
            if self.modulus == 2: Gunits = [1]
            self.unitgens = latex_tuple(map(str, Gunits))
            self.genvalues = chi_sage.values_on_gens() ## what is the use ?
            self.genlogvalues = [ chi.logvalue(k) for k in Gunits ]
            self.genvaluestex = latex_tuple(map(latex_char_logvalue,self.genlogvalues))
            self.bound = 5*1024
            if chi.is_even():
                self.parity = 'Even'
            else:
                self.parity = 'Odd'
            if self.primitive=="False":
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
                self.inducedchar_tex = r"\(\chi_{%s}(%s,\cdot)\)" %(self.inducedchar_modulus,self.inducedchar_number) 
       # if self.primitive == 'True':
       #     self.primtf = True
       # else:
       #     self.primtf = False
            # Set data for related number fields
            order2 = int(self.order)
            if order2 % 4 == 2: 
                order2 = order2/2
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
                pol=str(gp.galoissubcyclo(self.modulus,self.chi_sage.kernel()))
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
                if self.conductor%2 == 1:
                    self.kronsymbol = r"\begin{equation} \chi_{%s}(a) = " %(self.number)
                    self.kronsymbol += r"\left(\frac{a}{%s}\right)" %(self.conductor)
                    self.kronsymbol += r"\end{equation}"
                else:
                    if chi.is_even():
                        self.kronsymbol = r"\begin{equation}  \chi_{%s}(a) = " %(self.number)
                        self.kronsymbol += r"\left(\frac{a}{%s}\right)" %(self.conductor)
                        self.kronsymbol += r"\end{equation}"
                    else:
                        self.kronsymbol = r"\begin{equation}  \chi_{%s}(a) = " %(self.number)
                        self.kronsymbol += r"\left(\frac{a}{%s}\right)" %(self.conductor)
                        self.kronsymbol += r"\end{equation}"

        self.credit = "Sage"
        self.title = r"Dirichlet Character: \(\chi_{%s}(%s,\cdot)\)" %(self.modulus,self.number)
    
        return chi

    def _set_properties(self):
        conductor = str(self.conductor)
        primitive = self.primitive
        if primitive=="True":
            self.prim = "Yes"
        else:
            self.prim = "No"
        order = str(self.order)
        if self.order == 2:
            self.real = "Yes"
        else: 
            self.real = "No"
        self.properties = [("Conductor", [conductor]), ("Order", [order]), ("Parity", [self.parity]), ("Real", [self.real]), ("Primitive", [self.prim])]




























