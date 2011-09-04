import math
#from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
import re
import pymongo
import bson
from utils import parse_range
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
        G = DirichletGroup(self.modulus)
        self.zetaorder = G.zeta_order()
        chi = G[self.number]
        self.sagechar = str(chi)
        if chi.is_primitive():
            self.primitive = True
        else:
            self.primitive = False
        self.conductor = chi.conductor()
        self.order = chi.multiplicative_order()
        self.vals = chi.values()
        list  = [latex(_) for _ in chi.values()]
        self.valstex = list
        self.bound = 5*1024
        if chi.is_even():
            self.parity = 'Even'
        else:
            self.parity = 'Odd'
        self.primchar = chi.primitive_character()
        self.primcharmodulus = self.primchar.modulus()
        self.primcharconductor = self.primchar.conductor()
        F = DirichletGroup(self.primcharmodulus)
        for i in range(len(F)):
            if F[i] == self.primchar:
                self.primcharnumber = i
                break
        self.primchartex = "\(\\chi_{%s}\\!\\!\\pmod{%s}\)" %(self.primcharnumber,self.primcharmodulus)
        if self.primitive == 'True':
            self.primtf = True
        else:
            self.primtf = False
        if self.conductor%2 == 1:
            self.kronsymbol = "\\begin{equation} \n\\chi_{%s}(a) = " %(self.number)
            self.kronsymbol += "\\begin{cases}\\left(\\frac{a}{%s}\\right) \\qquad" %(self.conductor)
            self.kronsymbol += "&\\text{if gcd\((a,%s) = 1\)} \\cr\\cr\n" %(self.modulus)
            self.kronsymbol += "\\;\\;\\;\\;\\; 0 \\qquad &\\text{otherwise}. \\end{cases}"
            self.kronsymbol += "\n \\end{equation}"
        else:
            if chi.is_even():
                self.kronsymbol = "\\begin{equation} \n \\chi_{%s}(a) = " %(self.number)
                self.kronsymbol += "\\begin{cases} \\left(\\frac{a}{%s}\\right)\\qquad " %(self.conductor)
                self.kronsymbol += "&\\text{if gcd\((a,%s) = 1\)} \\cr\\cr\n" %(self.modulus)
                self.kronsymbol += "\\;\\;\\;\\;\\; 0 \\qquad &\\text{otherwise}. \\end{cases}"
                self.kronsymbol += "\n \\end{equation}"
            else:
                self.kronsymbol = "\\begin{equation} \n \\chi_{%s}(a) = " %(self.number)
                self.kronsymbol += "\\begin{cases} \\left(\\frac{a}{%s}\\right)\\cdot\\left(\\frac{-1}{a}\\right) \\qquad" %(self.conductor)
                self.kronsymbol += "&\\text{if gcd\((a,%s) = 1\)} \\cr\\cr\n" %(self.modulus)
                self.kronsymbol += "\\qquad \\;\\;\\;\\;\\;\\, 0 \\qquad &\\text{otherwise}. \\end{cases}"
                self.kronsymbol += "\n \\end{equation}"

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
        self.lth = len(self.vals)
        #chiv = []
    #determine if the character is real
        self.sign = True
        for v in chivals:
            if abs(imag_part(v)) > 0.0001:
                self.sign = False
        chizero = G[0]
        self.gauss_sum = chi.gauss_sum(1)
        if chi.gauss_sum(1) != 0:
            self.gauss_sum_numerical = chi.gauss_sum_numerical(20,1)
        self.jacobi_sum = chi.jacobi_sum(chizero)
        self.jacobi_sum_numerical = CC(self.jacobi_sum)
        self.kloosterman_sum = chi.kloosterman_sum(1,1)
        if chi.kloosterman_sum(1,1) != 0:
            self.kloosterman_sum_numerical = chi.kloosterman_sum_numerical(20,1,1)
        self.texname = "\(\\chi_{%s}\)" %(self.number)
        self.credit = 'Sage'
        self.title = "Dirichlet Character: \(\chi_{%s}\\!\\!\pmod{%s}\)" %(self.number,self.modulus)

#================
    def gauss_sum_tex(self):
        ans = "\(\\tau_a(\\chi_{%s}) \\;\) at \(\\; a = \)" %(self.number)
        #if self.gauss_sum != 0:
        #    ans += "\\begin{equation} \\tau_1(\\chi_{%s}) = %s = %s.\\end{equation} " %(self.number,latex(self.gauss_sum),latex(self.gauss_sum_numerical))
        #else:
        #    ans += "\\begin{equation} \\tau_1(\\chi_{%s}) = %s.\\end{equation} " %(self.number,latex(self.gauss_sum))
        #ans += "Compute Gauss sum \(\\tau_a(\\chi_{%s})\) at \(a = \)" %(self.number)
        return(ans)
#================

    def jacobi_sum_tex(self):
        ans = "\(J(\\chi_{%s},\\psi) \\;\) for \(\\; \\psi = \)" %(self.number)
        #ans = "\\begin{equation} J(\\chi_{%s},\\chi_{0}) = %s.\\end{equation}" %(self.number,latex(self.jacobi_sum))
        #ans += "Compute Jacobi sum \(J(\\chi_{%s},\\psi)\) at \(\\psi = \)" %(self.number)
        return(ans)

#================
    def kloosterman_sum_tex(self):
        ans = "\(K(a,b,\\chi_{%s}) \\;\) at \(\\; a,b = \)" %(self.number)
        #if self.kloosterman_sum != 0:
        #    ans = "\\begin{equation} K(1,1,\\chi_{%s}) = %s = %s.\\end{equation}" %(self.number,latex(self.kloosterman_sum),latex(self.kloosterman_sum_numerical))
        #else:
        #    ans = "\\begin{equation} K(1,1,\\chi_{%s}) = %s.\\end{equation}" %(s+ elf.number,latex(self.kloosterman_sum))
        #ans += "Compute Kloosterman sum \(K(a,b,\\chi_{%s})\) at \(a,b = \)" %(self.number)
        return(ans)

    def _set_properties(self):
        conductor = str(self.conductor)
        primitive = self.primitive
        if primitive:
            prim = 'Primitive'
        else:
            prim = 'Non-primitive'
        order = str(self.order)
        if self.sign:
            sign = 'Real'
        else: 
            sign = 'Complex'
        self.properties = ['<br><table><tr><td align=left><b>Conductor:</b>','<td align=left> %s</td>'%(conductor)]
        self.properties.extend(['<tr><td align=left><b>Order:</b>', '<td align=left>%s</td>'%(order)])
        self.properties.extend(['<tr><td align=left><b>Parity:</b>', '<td align=left>%s</td>'%(self.parity)])
        self.properties.extend(['<tr><td align=left>%s'%(sign), '</td>'])
        self.properties.extend(['<tr><td align=left>%s'%(prim), '</td></table>'])





























