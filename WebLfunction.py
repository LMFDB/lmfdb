import math
from Lfunctionutilities import pair2complex, splitcoeff, seriescoeff
from sage.all import *
import sage.libs.lcalc.lcalc_Lfunction as lc
import re
import pymongo
import bson
#import web_modforms
from classical_modular_forms.backend.web_modforms import *

class WebLfunction:
    """Class for presenting an L-function on a web page

    """
     
    def __init__(self, dict):
        self.type = dict['type']
        self.coefficient_period = 0
        self.poles = []
        self.residues = []
        self.kappa_fe = []
        self.lambda_fe =[]
        self.mu_fe = []
        self.nu_fe = []
        self.selfdual = False
        self.langlands = True
        self.texname = "L(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleteds = "\\Lambda(s)"  # default name.  will be set later, for most L-functions
        self.texnamecompleted1ms = "\\overline{\\Lambda(1-\\overline{s})}"  # default name.  will be set later, for most L-functions
        self.primitive = True # should be changed
        self.citation = ''
        self.credit = ''
        
        if self.type=='lcalcurl':
            import urllib
            self.url = dict['url']
            self.lcalcfile = urllib.urlopen(self.url).read()
            self.parseLcalcfile()

        elif self.type=='lcalcfile':
            self.lcalcfile = dict['filecontents']
            self.parseLcalcfile()

        elif self.type=='db':
            self.id = dict["id"]
            self.getFromDatabase()

        elif self.type=='sl4maass' or self.type=='sp4maass' or self.type=='sl3maass':
            self.source = dict["source"]
            self.id = dict["id"]
            self.getFromDatabase()

        elif self.type=='gl2holomorphic':
            self.weight = int(dict['weight'])
            self.level = int(dict['level'])
            self.character = int(dict['character'])
            self.label = dict['label']
            self.number = int(dict['number'])
            self.modularformL()
             
        elif self.type=='gl2maass':
            self.id = dict["id"]
	    self.maassL()
             
	elif self.type=='riemann':
	    if "numcoeff" in dict.keys():
	        self.numcoeff = int(dict['numcoeff'])
	    else:
		self.numcoeff = 20 # set default to 20 coefficients
	    self.riemannzeta()

	elif self.type=='ellipticcurve':
	    self.label = dict['label']
	    if "numcoeff" in dict.keys():
	        self.numcoeff = int(dict['numcoeff'])
	    else:
		self.numcoeff = 20 # set default to 20 coefficients
	    self.ellipticcurveL()

	elif self.type=='dirichlet':
	    self.charactermodulus = int(dict['charactermodulus'])
	    self.characternumber = int(dict['characternumber'])
	    if "numcoeff" in dict.keys():
	        self.numcoeff = int(dict['numcoeff'])
	    else:
		self.numcoeff = 20 # set default to 20 coefficients
	    self.dirichletL()

        else:
            raise KeyError 

        """
        self.coefficient_type: 1 = integer, 2 = double, 3 = complex
        self.coefficient_period:  0 = non-periodic
        """
        self._set_properties()

        self.sageLfunction = lc.Lfunction_C(self.title, self.coefficient_type,
                                            self.dirichlet_coefficients,
                                            self.coefficient_period,
                                            self.Q_fe, self.sign ,
                                            self.kappa_fe, self.lambda_fe ,
                                            self.poles, self.residues)


#===================  Set all the properties for different types of L-functions

    def modularformL(self):
        self.MF = WebNewForm(self.weight, self.level, self.character, self.label)

        self.automorphyexp = float(self.weight-1)/float(2)
        self.Q_fe = float(sqrt(self.level)/(2*math.pi))
        if self.level>1:
#            self.sign = self.MF.atkin_lehner_eigenvalues() * (-1)**(float(self.weight/2))
            self.sign = self.MF.atkin_lehner_eigenvalues()[self.level] * (-1)**(float(self.weight/2))
#FIX: extract eigenvalue corresponding to the level.  (atkin_lehner_eigenvalues is a dictionary
        else:
            self.sign = (-1)**(float(self.weight/2))
        self.kappa_fe = [1]
        self.lambda_fe = [self.automorphyexp]
        self.mu_fe = []
        self.nu_fe = [self.automorphyexp]
        self.selfdual = True
        self.langlands = True
        self.degree = 2
        self.poles = []
        self.residues = []
        self.numcoeff = 9 #just testing
        self.dirichlet_coefficients = []#self.MF.anlist(self.numcoeff)[1:] #remove a0
        for n in range(1,self.numcoeff):
            self.dirichlet_coefficients.append(self.MF._embeddings[n][self.number])
        for n in range(1,len(self.dirichlet_coefficients)-1):
            an = self.dirichlet_coefficients[n]
            self.dirichlet_coefficients[n]=float(an)/float(n**self.automorphyexp)
#FIX: These coefficients are wrong; too large and a1 is not 1
        self.coefficient_period = 0
        self.coefficient_type = 2
        self.quasidegree = 1
        self.checkselfdual()
        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.title = "L-function of a holomorphic cusp form: $L(s,f)$, "+ "where $f$ is a holomorphic cusp form with weight "+str(self.weight)+", level "+str(self.level)+", and character "+str(self.character)

#===================
                                               
    def maassL(self):
        import base
        connection = base.getDBConnection()
        db = connection.MaassWaveForm
        collection = db.HT
        data=collection.find_one({'_id':bson.objectid.ObjectId(self.id)})
        self.symmetry = data['Symmetry']
        self.eigenvalue = float(data['Eigenvalue'])
        self.norm = data['Norm']
        self.dirichlet_coefficients = data['Coefficient']
        if 'Level' in data.keys():
            self.level = int(data['Level'])
        else:
            self.level = 1
        self.charactermodulus = self.level
        if 'Weight' in data.keys():
            self.weight = int(data['Weight'])
        else:
            self.weight = 0
        if 'Character' in data.keys():
            self.characternumber = int(data['Character'])
        if self.level > 1:
            self.fricke = data['Fricke']  #no fricke for level 1
# end of database input

        self.coefficient_type = 2
        self.selfdual = True
        self.quasidegree = 2
        self.Q_fe = float(sqrt(self.level))/float(math.pi)
	if self.symmetry =="odd":
	    aa=1
	else:
	    aa=0
	if aa==0:
	    self.sign = 1
	else:
	    self.sign = -1
	if self.level > 1:
	    self.sign = self.fricke * self.sign
        self.kappa_fe = [0.5,0.5]
        self.lambda_fe = [0.5*aa + self.eigenvalue*I, 0,5*aa - self.eigenvalue*I]
        self.mu_fe = [aa + 2*self.eigenvalue*I, aa -2*self.eigenvalue*I]
        self.nu_fe = []
        self.langlands = True
        self.degree = 2
        self.poles = []
        self.residues = []
        self.coefficient_period = 0
# determine if the character is real (i.e., if the L-function is selfdual)
	self.checkselfdual()
        self.texname = "L(s,f)"
        self.texnamecompleteds = "\\Lambda(s,f)"
        if self.selfdual:
            self.texnamecompleted1ms = "\\Lambda(1-s,f)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{f})"
        self.title = "$L(s,f)$, where $f$ is a Maass cusp form with level "+str(self.level)+", and eigenvalue "+str(self.eigenvalue)

#===========================
                                               
    def ellipticcurveL(self):
	self.E = EllipticCurve(str(self.label))
        self.quasidegree = 1
        self.level = self.E.conductor()
        self.Q_fe = float(sqrt(self.level)/(2*math.pi))
        self.sign = self.E.lseries().dokchitser().eps
        self.kappa_fe = [1]
        self.lambda_fe = [0.5]
        self.mu_fe = []
        self.nu_fe = [0.5]
        self.langlands = True
        self.degree = 2
#okay up to here
        self.dirichlet_coefficients = self.E.anlist(self.numcoeff)[1:]  #remove a0
	for n in range(0,len(self.dirichlet_coefficients)-1):
	   an = self.dirichlet_coefficients[n]
	   self.dirichlet_coefficients[n]=float(an)/float(sqrt(n+1))
	   
        self.poles = []
        self.residues = []
        self.coefficient_period = 0
        self.selfdual = True
        self.coefficient_type = 2
        self.texname = "L(s,E)"
        self.texnamecompleteds = "\\Lambda(s,E)"
        self.texnamecompleted1ms = "\\Lambda(1-s,E)"
        self.title = "L-function $L(s,E)$ for the Elliptic Curve over Q with label "+ self.E.label()

        self.properties = ['Degree ','%s<br><br>' % self.degree]
        self.properties.extend(['Level ', '%s' % self.level])
        self.credit = 'Sage'
#        self.title = self.title+", where $\\chi$ is the character modulo "+\
#str(self.charactermodulus) + ", number " + str(self.characternumber)
        self.specialvalues =  'test'#'L(1/2) = '+str(self.sageLfunction.value(.5))
        

#===========================

    def dirichletL(self):
	chi = DirichletGroup(self.charactermodulus)[self.characternumber]
# Warning: will give nonsense if character is not primitive
	aa = int((1-chi(-1))/2)   # usually denoted \frak a
#        self.coefficient_type = 0
        self.quasidegree = 1
        self.Q_fe = float(sqrt(self.charactermodulus)/sqrt(math.pi))
        self.sign = 1/(I**aa * float(sqrt(self.charactermodulus))/(chi.gauss_sum_numerical()))
        self.kappa_fe = [0.5]
        self.lambda_fe = [0.5*aa]
        self.mu_fe = [aa]
        self.nu_fe = []
        self.langlands = True
        self.degree = 1
        self.level = self.charactermodulus
        self.dirichlet_coefficients = []
        for n in range(1,self.numcoeff):
            self.dirichlet_coefficients.append(chi(n).n())
        self.poles = []
        self.residues = []
        self.coefficient_period = self.charactermodulus
        self.coefficient_period = 0
	chivals=chi.values_on_gens()
  # determine if the character is real (i.e., if the L-function is selfdual)
        self.selfdual = True
        for v in chivals:
            if abs(imag_part(v)) > 0.0001:
                self.selfdual = False
  #
	self.coefficient_type = 2
	if self.selfdual:
	    self.coefficient_type = 1

        self.texname = "L(s,\\chi)"
        self.texnamecompleteds = "\\Lambda(s,\\chi)"
	if self.selfdual:
	    self.texnamecompleted1ms = "\\Lambda(1-s,\\chi)"
        else:
            self.texnamecompleted1ms = "\\Lambda(1-s,\\overline{\\chi})"
        self.credit = 'Sage'
        self.title = "Dirichlet L-function: $L(s,\\chi)$"
	self.title = (self.title+", where $\\chi$ is the character modulo "+
                      str(self.charactermodulus) + ", number " +
                      str(self.characternumber))

#===========================
                                               
    def riemannzeta(self):
	self.coefficient_type = 1
	self.quasidegree = 1
	self.Q_fe = float(1/sqrt(math.pi))
	self.sign = 1
	self.kappa_fe = [0.5]
	self.lambda_fe = [0]
	self.mu_fe = [0]
	self.nu_fe = []
	self.langlands = True
	self.degree = 1
	self.level = 1
	self.dirichlet_coefficients = []
	for n in range(self.numcoeff):
	    self.dirichlet_coefficients.append(1)
	self.poles = [0,1]
	self.residues = [-1,1]
	self.coefficient_period = 0
	self.selfdual = True
        self.texname = "\\zeta(s)"
        self.texnamecompleteds = "\\xi(s)"
        self.texnamecompleted1ms = "\\xi(1-s)"
        self.credit = 'Sage'
	self.title = "Riemann Zeta-function: $\\zeta(s)$"

#===========================
                                               
    def getFromDatabase(self):
        import base
        connection = base.getDBConnection()
        dbName = 'Lfunction'
        dbColl = 'LemurellMaassHighDegree'  #Probably later a choice
        db = pymongo.database.Database(connection, dbName)
        collection = pymongo.collection.Collection(db,dbColl)
        self.dbEntry = collection.find_one({'_id': self.id}) 
        self.lcalcfile = self.dbEntry['lcalcfile']
        self.parseLcalcfile()

        self.family = self.dbEntry['family']
        self.group = self.dbEntry['group']
        self.field = self.dbEntry['field']
        self.objectName = self.dbEntry['objectName']

        self.texnamecompleted1ms = self.dbEntry['texnamecompleted1ms']
        self.texname = self.dbEntry['texname']
        self.texnamecompleteds = self.dbEntry['texnamecompleteds']
        self.title = self.dbEntry['title']
        self.citation = self.dbEntry['citation']
        self.credit = self.dbEntry['credit']

#=========================== Extract the information from an Lcalcfile
#=========================== which is stored in self.lcalcfile
                                               
    def parseLcalcfile(self):
        lines = self.lcalcfile.split('\n',6)
        self.coefficient_type = int(lines[0])
        self.quasidegree = int(lines[4])
        lines = self.lcalcfile.split('\n',8+2*self.quasidegree)
        self.Q_fe = float(lines[5+2*self.quasidegree])
        self.sign = pair2complex(lines[6+2*self.quasidegree])

        for i in range(self.quasidegree):
            localdegree = float(lines[5+2*i])
            self.kappa_fe.append(localdegree)
            locallambda = pair2complex(lines[6+2*i])
            self.lambda_fe.append(locallambda)
            if math.fabs(localdegree-0.5)<0.00001:
                self.mu_fe.append(2*locallambda)
            elif math.fabs(localdegree-1)<0.00001:
                self.nu_fe.append(locallambda)
            else:
                self.nu_fe.append(locallambda)
                self.langlands = False

        """ Do poles here later
        """
        
        self.degree = int(round(2*sum(self.kappa_fe)))

        self.level = int(round(math.pi**float(self.degree) * 4**len(self.nu_fe) * self.Q_fe**2 ))
# note:  math.pi was not compatible with the sage type of degree

        self.dirichlet_coefficients = splitcoeff(lines[-1])
        
# check for selfdual
	self.checkselfdual()
#	
	if self.selfdual:
	    self.texnamecompleted1ms = "\\Lambda(1-s)"  # default name.  will be set later, for most L-functions

        try:
            self.originalfile = re.match(".*/([^/]+)$", self.url)
            self.originalfile = self.originalfile.group(1)
            self.title = "An L-function generated by an Lcalc file: "+self.originalfile
        except:
            self.originalfile = ''

        
#=========================== Returns the Lcalcfile 
#=========================== 
                                               
    def createLcalcfile(self):
        thefile="";
        if self.selfdual:
            thefile = thefile + "2\n"  # 2 means real coefficients
        else:
            thefile = thefile + "3\n"  # 3 means complex coefficients

        thefile = thefile + "0\n"  # 0 means unknown type

        thefile = thefile + str(len(self.dirichlet_coefficients)) + "\n"  

        thefile = thefile + "0\n"  # assume the coefficients are not periodic
        
        thefile = thefile + str(self.quasidegree) + "\n"  # number of actual Gamma functions

        for n in range(0,self.quasidegree):
            thefile = thefile + str(self.kappa_fe[n]) + "\n"
            thefile = thefile + str(real_part(self.lambda_fe[n])) + " " + str(imag_part(self.lambda_fe[n])) + "\n"
        
        thefile = thefile + str(real_part(self.Q_fe)) +  "\n"

        thefile = thefile + str(real_part(self.sign)) + " " + str(imag_part(self.sign)) + "\n"

        thefile = thefile + str(len(self.poles)) + "\n"  # counts number of poles

        for n in range(0,len(self.poles)):
            thefile = thefile + str(real_part(self.poles[n])) + " " + str(imag_part(self.poles[n])) + "\n" #pole location
            thefile = thefile + str(real_part(self.residues[n])) + " " + str(imag_part(self.residues[n])) + "\n" #residue at pole

        for n in range(0,len(self.dirichlet_coefficients)):
            thefile = thefile + str(real_part(self.dirichlet_coefficients[n]))   # add real part of Dirichlet coefficient
            if not self.selfdual:  # if not selfdual
                thefile = thefile + " " + str(imag_part(self.dirichlet_coefficients[n]))   # add imaginary part of Dirichlet coefficient
            thefile = thefile + "\n" 
        
        return(thefile)

#=============== Checks whether coefficients are real to determine
#=============== whether L-function is selfdual
                                               
    def checkselfdual(self):
	self.selfdual = True
        for n in range(1,min(8,len(self.dirichlet_coefficients))):
            if abs(imag_part(self.dirichlet_coefficients[n]/self.dirichlet_coefficients[0])) > 0.00001:
                self.selfdual = False

#=============== Sets the html of the properties to display in the upper right corner

    def _set_properties(self):
        deg = str(self.degree)
        if self.selfdual:
            sd = 'Self dual'
        else:
            sd = 'Not self dual'
        ll = str(self.level)
        sg = str(self.sign)
        if self.primitive:
            prim = 'Primitive'
        else:
            prim = 'Not primitive'
        self.properties = ['Degree: ',deg]
        self.properties.extend(['<br>', sd])
        self.properties.extend(['<br>Level: ', ll])
        self.properties.extend(['<br>Sign: ',sg])
        self.properties.extend(['<br>',prim])


# 
#===============

    def lfuncDStex(self,fmt):
        numperline = 4
        numcoeffs=min(10,len(self.dirichlet_coefficients))
	if self.selfdual:
	    numperline = 9
            numcoeffs=min(20,len(self.dirichlet_coefficients))
        ans=""
        if fmt=="analytic" or fmt=="langlands":
	    ans="\\begin{align}\n"
	    ans=ans+self.texname+"="+seriescoeff(self.dirichlet_coefficients[0],0,"literal","",-6,5)+"\\mathstrut&"
	    for n in range(1,numcoeffs):
	        ans=ans+seriescoeff(self.dirichlet_coefficients[n],n+1,"series","dirichlet",-6,5)
	        if(n % numperline ==0):
		    ans=ans+"\\cr\n"
		    ans=ans+"&"
	    ans=ans+"+ \\ \\cdots\n\\end{align}"

	elif fmt=="abstract":
	   if self.type=="riemann":
		ans="\\begin{equation} \n \\zeta(s) = \\sum_{n=1}^{\\infty} n^{-s} \n \\end{equation} \n"

	   elif self.type=="dirichlet":
		ans="\\begin{equation} \n L(s,\\chi) = \\sum_{n=1}^{\\infty} \\chi(n) n^{-s} \n \\end{equation}"
		ans = ans+"where $\\chi$ is the character modulo "+ str(self.charactermodulus)
		ans = ans+", number "+str(self.characternumber)+"." 

	   else:
		ans="\\begin{equation} \n "+self.texname+" = \\sum_{n=1}^{\\infty} a(n) n^{-s} \n \\end{equation}"
        return(ans)
	

#---------

    def lfuncEPtex(self,fmt):
        ans=""
        if fmt=="abstract":
	   ans="\\begin{equation} \n "+self.texname+" = "
           if self.type=="riemann":
                ans= ans+"\\prod_p (1 - p^{-s})^{-1}"
           elif self.type=="dirichlet":
                ans= ans+"\\prod_p (1- \\chi(p) p^{-s})^{-1}"

	   elif self.type=="gl2maass":
                ans= ans+"\\prod_p (1- a(p) p^{-s} + p^{-2s})^{-1}"

	   elif self.type=="gl3maass":
                ans= ans+"\\prod_p (1- a(p) p^{-s} + \\overline{a(p)} p^{-2s} - p^{-3s})^{-1}"

           elif self.langlands:
                ans= ans+"\\prod_p \\ \\prod_{j=1}^{"+str(self.degree)+"} (1 - \\alpha_{j,p}\\,  p^{-s})^{-1}"
           
           else:
		return("No information is available about the Euler product.")
	   ans=ans+" \n \\end{equation}"
           return(ans)
        else:
           return("No information is available about the Euler product.")


#---------

        
#===========================

    def lfuncFEtex(self,fmt):
        """ lfuncFEtex(fmt) is the functional equation in the chosen format:
    analytic, selberg, 
"""
        ans=""
        if fmt=="analytic":
            ans="\\begin{align}\n"+self.texnamecompleteds+"=\\mathstrut &"
	    if self.level>1:
               ans=ans+latex(self.level)+"^{\\frac{s}{2}}"
            for mu in self.mu_fe:
               ans=ans+"\Gamma_R(s"+seriescoeff(mu,0,"signed","",-6,5)+")"
            for nu in self.nu_fe:
               ans=ans+"\Gamma_C(s"+seriescoeff(nu,0,"signed","",-6,5)+")"
            ans=ans+"\\cdot "+self.texname+"\\cr\n"
            ans=ans+"=\\mathstrut & "+seriescoeff(self.sign,0,"factor","",-6,5)+\
self.texnamecompleted1ms+"\n\\end{align}\n"
	elif fmt=="selberg":
	    ans=ans+"("+str(int(self.degree))+","
	    ans=ans+str(int(self.level))+","
	    ans=ans+"("
	    if self.mu_fe != []:
	        for mu in range(len(self.mu_fe)-1):
		    ans=ans+seriescoeff(self.mu_fe[mu],0,"literal","",-6,5)+", "
	        ans=ans+seriescoeff(self.mu_fe[-1],0,"literal","",-6,5)
	    ans = ans+":"
	    if self.nu_fe != []:
	        for nu in range(len(self.nu_fe)-1):
		    ans=ans+str(self.mu_fe[nu])+", "
	        ans=ans+str(self.nu_fe[-1])
	    ans = ans+"), "
	    ans = ans+seriescoeff(self.sign, 0, "literal","", -6,5)
	    ans = ans+")"
	return(ans)
                           
#++++++++++++++++++++++++++++++

