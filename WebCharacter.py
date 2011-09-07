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
        logger.debug( "Check" )
        G = DirichletGroup(self.modulus)
        self.zetaorder = G.zeta_order()
        chi = G[self.number]
        self.sagechar = str(chi)
        if chi.is_primitive():
            self.primitive = "True"
        else:
            self.primitive = "False"
        self.conductor = chi.conductor()
        self.order = chi.multiplicative_order()
        self.vals = chi.values()
        logger.debug(DirichletGroup(1)[0].values())
        list  = [latex(_) for _ in chi.values()]
        logger.debug( "Check2" )
        self.valstex = list
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
            F = DirichletGroup(self.inducedchar_modulus)
            logger.debug("primitive")
            if self.number == 0:
                self.inducedchar_number = 0
            else:
                for i in range(1,len(F)):
                    if F[i] == self.inducedchar:
                        self.inducedchar_number = i
                        break
            self.inducedchar_tex = "\(\\chi_{%s}\\!\\!\\pmod{%s}\)" %(self.inducedchar_number,self.inducedchar_modulus)
            logger.debug( "Check3" )
       
       # if self.primitive == 'True':
       #     self.primtf = True
       # else:
       #     self.primtf = False
        if self.order == 2:
            logger.debug( "CHECK" )
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

        self.level = self.modulus
        self.genvalues = chi.values_on_gens()
        if len(chi.values_on_gens()) == 1:
            self.genvaluestex = latex(chi.values_on_gens()[0])
        else:
            self.genvaluestex = latex(chi.values_on_gens())
        chivals = chi.values_on_gens()
        Gunits = G.unit_gens()
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
        if self.zetaorder >= 2:
            self.sign = "False"
        chizero = G[0]
        self.credit = "Sage"
        self.title = "Dirichlet Character: \(\chi_{%s}\\!\\!\pmod{%s}\)" %(self.number,self.modulus)

    def gauss_sum_tex(self):
        ans = "\(\\tau_a(\\chi_{%s}) \\;\) at \(\\; a = \)" %(self.number)
        return(ans)

    def jacobi_sum_tex(self):
        ans = "\(J(\\chi_{%s},\\psi) \\;\) for \(\\; \\psi = \)" %(self.number)
        return(ans)

    def kloosterman_sum_tex(self):
        ans = "\(K(a,b,\\chi_{%s}) \\;\) at \(\\; a,b = \)" %(self.number)
        return(ans)

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





























