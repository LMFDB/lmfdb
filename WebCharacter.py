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
try:
  from dirichlet_conrey import *
except:
  logger.critical("dirichlet_conrey.pyx cython file is not available ...")

def log_value(modulus,number):
    from dirichlet_conrey import DirichletGroup
    G = DirichletGroup_conrey(modulus)
    chi = G[number]
    l = []
    for j in range(1, modulus+1):
        logvalue = chi.logvalue(j)
        n = int(logvalue.numer())
        d = int(logvalue.denom())
        from sage.all import Integer
        if Integer(j).gcd(modulus) == 1:
            if n == 0:
                s = "\(1\)"
            else:
                s = r"\(e\left(\frac{%s}{%s}\right)\)" %(n,d)
                if n == 1 and d == 2:
                    s = "\(-1\)"
                if n == 1 and d == 4:
                    s = "\(i\)"
                if n == 3 and d == 4:
                    s = "\(-i\)"
        else:
            s="0"
        l.append(s)
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
            self.genvalues = chi_sage.values_on_gens()
            if len(chi_sage.values_on_gens()) == 1:
                self.genvaluestex = latex(chi_sage.values_on_gens()[0])
            else:
                self.genvaluestex = latex(chi_sage.values_on_gens())
            chivals = chi_sage.values_on_gens()
            Gunits = G_sage.unit_gens()
            if len(Gunits) != 1:
                self.unitgens = "("
            else:
                self.unitgens = ""
            count = 0
            for g in Gunits:
                if count != len(Gunits)-1:
                    self.unitgens += latex(g) + ","
                else:
                    self.unitgens += latex(g)
                count += 1
            if len(Gunits) != 1:
                self.unitgens += ")"
            self.sign = "True"
            if self.zetaorder > 2:
                self.sign = "False"
            chizero = G_sage[0]
            self.char = str(chi)
            if chi.is_primitive():
                self.primitive = "True"
            else:
                self.primitive = "False"
            self.conductor = chi.conductor()
            self.order = chi.multiplicative_order()
            self.vals = chi.values()
            self.logvals = log_value(self.modulus,self.number)
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
        if self.sign=="True":
            self.real = "Yes"
        else: 
            self.real = "No"
        self.properties = [("Conductor", [conductor]), ("Order", [order]), ("Parity", [self.parity]), ("Real", [self.real]), ("Primitive", [self.prim])]




























