import math
#from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
import re
import pymongo
import bson
#import web_modforms
from classical_modular_forms.backend.web_modforms import *

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
        chi = DirichletGroup(self.modulus)[self.number]
        self.sagechar = str(chi)
# Warning: will give nonsense if character is not primitive
        self.primitive = chi.is_primitive()
#	self.primitive = chi.primitive_character()
        self.conductor = chi.conductor()
        #self.unit_generators = chi.unit_gens()
        self.order = chi.multiplicative_order()
        self.vals = chi.values()
        count = 0
        counter = 1
        self.valstex = "\\begin{align}\n[\\mathstrut&"
        for v in chi.values():
            sv = str(v).partition('^')[0]
            if (sv.startswith("zeta")) and (counter == 1):
                rootunity = int(sv[4:])
                counter += 1
            elif (sv.startswith("-zeta")) and (counter == 1):
                rootunity = int(sv[5:])
                counter += 1
            count += 1
            if(count == len(chi.values())):
                self.valstex += str(latex(v))
            else:
                if(count%20 == 0):
                    self.valstex += "\\cr\n"
                    self.valstex += "&"
                else:
                    self.valstex += str(latex(v)) + "\\,,\\,"
        self.valstex += "]\n\\end{align}"
        if(counter == 2):
            self.valstex += "where \(\\zeta_{%s}\) is a primitive \(%s\)th root of unity." %(rootunity,rootunity)
        #self.valstex = "\("+ str(latex(chi.values())) + "\)"
        self.bound = 5*1024
        if chi.is_even():
            self.parity = 'Even'
        else:
            self.parity = 'Odd'
        self.primchar = chi.primitive_character()
        self.primcharmodulus = self.primchar.modulus()
        self.primcharconductor = self.primchar.conductor()
        G = DirichletGroup(self.primcharmodulus)
        for i in range(0,len(G)):
            if G[i] == self.primchar:
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
        self.chivalues = chi.values_on_gens()
        self.chivaluestex = "\(" + str(latex(chi.values_on_gens())) + "\)"
        chivals = chi.values_on_gens()
        self.lth = len(self.vals)
        #chiv = []
    #determine if the character is real
        self.sign = True
        for v in chivals:
            if abs(imag_part(v)) > 0.0001:
                self.sign = False
            #t = str(v).split('+')
            #for j in t:
            #    if j.startswith("-zeta"):
            #        rest = j[5:]
            #        rootunity = '\(-\\zeta\)' 
            #    elif j.startswith("zeta"):
            #        rest = j[4:]
            #    else:
            #        rest = j
            #        j = "\(\\chi_{%s}\)" %(self.number)
            #        j += rest
            #    t.append(j)
            #    chiv.append(str("\(\\zeta\)"))
        #self.chival = chiv
        self.texname = "\(\\chi_{%s}\)" %(self.number)
        self.credit = 'Sage'
        self.title = "Dirichlet Character: \(\chi_{%s}\\!\\!\pmod{%s}\)" %(self.number,self.modulus)

#================
    def gauss_sum_tex(self):
        ans = "For \(a \\in \\mathbb{Z}\\;\)  and "
        ans += "\(\\;\\zeta = e^{2\\pi i/%s}\)" %(self.modulus)
        ans += " a primitive \(%s\)th root of unity, " %(self.modulus)
        ans += "the \(\\textbf{Gauss sum}\) associated to "
        ans += "\(\\chi_{%s}\) and \(a\) is given by" %(self.number)
        ans += "\\begin{equation} \n \\tau_{a}(\\chi_{%s}) = \\sum_{r \\,\\in\\, \\mathbb{Z}/%s\\mathbb{Z}} \\chi_{%s}(r) \\zeta^{ar}. \n \\end{equation} \n" %(self.number,self.modulus,self.number)
        return(ans)
#================

    def jacobi_sum_tex(self):
        ans = "For \(\\psi\) a Dirichlet character modulo \(%s\), " %(self.modulus)
        ans += "the \(\\textbf{Jacobi sum}\) associated to "
        ans += "\(\\chi_{%s}\) and \(\\psi\) is given by" %(self.number)
        ans += "\\begin{equation} \n J(\\chi_{%s},\\psi) = \\sum_{r \\,\\in\\,\\mathbb{Z}/%s\\mathbb{Z}} \\chi_{%s}(r) \\psi(1-r). \n \\end{equation} \n" %(self.number,self.modulus,self.number)
        return(ans)

#================

    def kloosterman_sum_tex(self):
        ans = "The \(\\textbf{Kloosterman sum}\) associated to "
        ans += "\(\\chi_{%s}\) and the integers \(a,b\) " %(self.number)
        ans += "\\begin{equation} \n K(a,b,\\chi_{%s}) = \\sum_{r \\,\\in\\,\\mathbb{Z}/%s\\mathbb{Z}} \\chi_{%s}(r) \\zeta^{ar+ br^{-1}}, \n \end{equation} \n" %(self.number,self.modulus,self.number)
        ans += "where \(\\zeta = e^{2 \\pi i/%s}\) is " %(self.modulus)
        ans += "a primitive \(%s\)th root of unity. " %(self.modulus)
        ans += "This reduces to the Gauss sum if \(b=0\)."
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
        self.properties.extend(['<tr><td align=left><b>Sign:</b>', '<td align=left>%s</td>'%(sign)])
        self.properties.extend(['<tr><td align=left><b>Primitivity:&nbsp;&nbsp;</b>', '<td align=left>%s</td></table>'%(prim)])





























