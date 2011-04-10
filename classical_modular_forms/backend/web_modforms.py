
r""" Class for newforms in format which can be presented on the web easily



AUTHORS:

 - Fredrik Stroemberg
 - Aurel Page


TODO:
Fix complex characters. I.e. embedddings and galois conjugates in a consistent way. 

"""
from sage.all import ZZ,QQ,DirichletGroup,CuspForms,Gamma0,ModularSymbols,Newforms,trivial_character,is_squarefree,divisors,RealField,ComplexField,prime_range,I,join,gcd,Cusp,Infinity,ceil,CyclotomicField,exp,pi,primes_first_n,euler_phi
from sage.all import Parent,SageObject,dimension_new_cusp_forms,vector,dimension_modular_forms,EisensteinForms,Matrix,floor,denominator,latex,is_prime,prime_pi,next_prime,primes_first_n,previous_prime
from plot_dom import draw_fundamental_domain
from cmf_core import html_table,len_as_printed
#from sage.monoids.all import AlphabeticStrings
from sage.all import factor
from flask import url_for
import re

import pymongo 
from utilities import pol_to_html 
dburl = 'localhost:27017'

from pymongo.helpers import bson     
from bson import BSON

class WebModFormSpace(Parent):
    r"""
    Space of cuspforms to be presented on the web.
        G  = NS.

    EXAMPLES::

    sage: WS=WebModFormSpace(2,39)
 

    """
    def get_from_db(db,k,N,chi,prec):
        r"""
        Try to see what is in the database. 
        """
        try: 
            connection = pymongo.Connection(db)
        except:
            raise "Check that a mongodb is running at %s !" % db
        
        

        
    def __init__(self,k,N=1,chi=0,prec=10,data=None,compute=None):
        r"""
        Init self.
        """
        #print "k=",k
        self._k = ZZ(k)
        self._N = ZZ(N)
        if chi=='trivial':
            self._chi=ZZ(0)
        else:
            self._chi = ZZ(chi)
        self._prec = ZZ(prec)
        self.prec = ZZ(prec)
        self._ap = list()
        # check what is in the database

        if isinstance(data,dict):
            if data.has_key('ap'):
                self._ap = data['ap']
            if data.has_key('group'):
                self._group = data['group']
            if data.has_key('character'):
                self._character = data['character']
            if data.has_key('fullspace'):
                self._fullspace = data['fullspace']
            if data.has_key('modular_symbols'):
                 self._modular_symbols = data['modular_symbols']
            if data.has_key('newspace'):
                self._newspace = data['newspace'] 
            if data.has_key('newforms'):
                 self._newforms = data['newforms']
            if data.has_key('new_modular_symbols'):
                self._new_modular_symbols = data['new_modular_symbols'] 
            if data.has_key('decomposition'):
                self._galois_decomposition= data['galois_decomposition']
            if data.has_key('galois_orbits_labels'):
                self._galois_orbits_labels= data['galois_orbits_labels']
            if data.has_key('oldspace_decomposition'):
                self._oldspace_decomposition=data['oldspace_decomposition']
        else:
            try:
                self._group=Gamma0(N)
                self._character=DirichletGroup(N)[self._chi]
                if(self._chi==0):
                    #self._fullspace=CuspForms(N,k)
                    self._modular_symbols=ModularSymbols(N,k,sign=1).cuspidal_submodule()
                else:
                    #self._fullspace=CuspForms(self._character,k)
                    self._modular_symbols=ModularSymbols(self._character,k,sign=1).cuspidal_submodule()
                if(N<>1):
                    #self._newspace=self._fullspace.new_submodule()
                    self._newspace=self._modular_symbols.new_submodule()
                else:
                    self._newspace=self._modular_symbols
                self._newform_eigenvalues=self._modular_symbols.ambient().compact_newform_eigenvalues(prime_range(prec),names='x')
                self._newforms = list()
                #self._fullspace.newforms(names='x')
                #self._new_modular_symbols=self._modular_symbols.new_submodule()
                self._galois_decomposition=[]
                self._oldspace_decomposition=[]
                self._galois_orbits_labels=[]
                self._newforms = self.galois_decomposition()
                if compute=='all':
                    i = 0
                    for i in range(len(self._newforms)):
                        f_data
                        f_data=dict()
                        f_data['parent']=self
                        f_data['f']=self._newforms[i]
                        if len(self._ap)<i:
                            f_data['ap']=self._ap[i]
                        #f_data['ap']=self._ap[i]
                        label = self._galois_orbits_labels[i]
                        self._newforms = WebNewForm(self._k,self._N,self._chi,label=label,fi=i,prec=prec,bitprec=bitprec,verbose=verbose,data=f_data,compute='all')
                        


                
            except RuntimeError:
            
                raise RuntimeError, "Could not construct space for (k=%s,N=%s,chi=%s)=" % (k,N,self._chi)
        self._verbose=0
        if(self.dimension()==self.dimension_newspace()):
            self._is_new=True
        else:
            self._is_new=False



    def __reduce__(self):
        r"""
        Used for pickling.
        """
        data = self.to_dict()
        #return(WebModFormSpace,(self._k,self._N,self._chi,self.prec,data))
	return(unpickle_wmfs_v1,(self._k,self._N,self._chi,self.prec,data))   

    def _save_to_file(self,file):
        r"""
        Save self to file.
        """
        self.save(file,compress=None)

    def to_dict(self):
        r"""
        Makes a dictionary of the relevant information.
        """
        data = dict()
        data['group'] = self._group 
        data['character'] = self._character 
        #data['fullspace'] = self._fullspace
        data['modular_symbols'] = self._modular_symbols
        #data['newspace'] = self._newspace
        data['newforms'] = self._newforms
        data['new_modular_symbols'] = self._new_modular_symbols
        data['galois_decomposition'] = self._galois_decomposition
        data['galois_orbits_labels'] = self._galois_orbits_labels
        data['oldspace_decomposition'] = self._oldspace_decomposition
        return data
    
    def _repr_(self):
        s = 'Space of Cusp forms on '+str(self.group())+' of weight'+str(self._k)
        s+=' and dimension'+str(self.dimension())
        #return str(self._fullspace)

    # internal methods to generate properties of self
    def galois_decomposition(self):
        r"""
        We compose the new subspace into galois orbits.
        """
	from sage.monoids.all import AlphabeticStrings
        if(len(self._galois_decomposition)<>0):
            return self._galois_decomposition
        L=self._modular_symbols.new_submodule().decomposition()
        self._galois_decomposition=L
        # we also label the compnents
        x=AlphabeticStrings().gens()
        for j in range(len(L)):
            if(j<26):
                label=str(x[j]).lower()
            else:
                j1= j % 26
                j2= floor( QQ(j) / QQ(26))
                label=str(x[j1]).lower()
                label=label+str(j2)
            self._galois_orbits_labels.append(label)
        return L

    def galois_orbit_label(self,j):
        if(len(self._galois_orbits_labels)==0):
            self.galois_decomposition()
        return self._galois_orbits_labels[j]

    # return specific properties of self
    def dimension_newspace(self):
        return self._newspace.dimension()

    def dimension_cuspforms(self):
        return self._modular_symbols.dimension()

    def dimension(self):
        return self._modular_symbols.dimension()

    def weight(self):
        return self._k

    def level(self):
        return self._N

    def character(self):
        return self._chi
    
    def character_order(self):
        if(self._character<>0):
            return self._character.order()
        else:
            return 1

    def character_conductor(self):
        if(self._character<>0):
            return self._character.conductor()
        else:
            return 1


    def group(self):
        return self._group
    
    def sturm_bound(self):
        r""" Return the Sturm bound of S_k(N,xi), i.e. the number of coefficients necessary to determine a form uniquely in the space.
        """
        return self._modular_symbols.sturm_bound()

    def labels(self):
        r"""

        """
        if(len(self._galois_orbits_labels)>0):
            return self._galois_orbits_labels
        else:
            self.galois_decomposition()
            return self._galois_orbits_labels

    def f(self,i):
        r"""
        Return function f in the set of newforms on self.
        """
        if(isinstance(i,int) or i in ZZ):
            F=WebNewForm(self._k,self._N,self._chi,fi=i)
        else:
            F=WebNewForm(self._k,self._N,self._chi,label=i)
        if(F.f<>None):
            return F
        else:
            return None
        
    def galois_orbit(self,orbit,prec=None):
        r"""
        Return the q_eigenform nr. orbit in self
        """
        if(prec==None):
            prec=self.prec
        return self.galois_decomposition()[orbit].q_eigenform(prec,'x')

    def oldspace_decomposition(self):
        r"""
        Get decomposition of the oldspace in self into submodules.
        
        """
        if(len(self._oldspace_decomposition)<>0):
            return self._oldspace_decomposition
        N=self._N; k=self._k
        M=self._modular_symbols
        L=list()
        L=[]
        check_dim=self.dimension_newspace()
        if(check_dim==self.dimension()):
            return L
        #print "check_dim=",check_dim
        for d in divisors(N):
            if(d==1):
                continue
            q = N.divide_knowing_divisible_by(d)
            if(self._verbose>1):
                print "d=",d
            # since there is a bug in the current version of sage
            # we have to try this...
            try:
                O=M.old_submodule(d)
            except AttributeError:
                O=M.zero_submodule()
            Od=O.dimension()
            if(self._verbose>1):
                print "O=",O
                print "Od=",Od
            if(d==N and k==2 or Od==0):
                continue
            if self._character.is_trivial():
                #S=ModularSymbols(ZZ(N/d),k,sign=1).cuspidal_submodule().new_submodule(); Sd=S.dimension()
                print "q=",q,type(q)
                print "k=",k,type(k)
                Sd = dimension_new_cusp_forms(q,k)
                if(self._verbose>1):
                    print "Sd=",Sd
                if Sd > 0:
                    mult=len(divisors(ZZ(d)))
                    check_dim=check_dim+mult*Sd
                    L.append((q,0,mult,Sd))
            else:
                xd = self._character.decomposition()
                for xx in xd:
                    if xx.modulus() == q:
                        Sd = dimension_new_cusp_forms(xx,k)
                        if Sd>0:
                            # identify this character for internal storage... should be optimized
                            x_k = DirichletGroup(q).list().index(xx)
                            mult=len(divisors(ZZ(d)))
                            check_dim=check_dim+mult*Sd
                            L.append((q,x_k,mult,Sd))
            if(self._verbose>1):
                print "mult,N/d,Sd=",mult,ZZ(N/d),Sd
                print "check_dim=",check_dim
        check_dim=check_dim-M.dimension()
        if(check_dim<>0):
            raise ArithmeticError, "Something wrong! check_dim=%s" % check_dim
        return L

    ### Printing functions
    def print_oldspace_decomposition(self):
        r""" Print the oldspace decomposition of self.
        """
        if(len(self._oldspace_decomposition)==0):
            self._oldspace_decomposition=self.oldspace_decomposition()
        
        O=self._oldspace_decomposition

        n=0; s=""
        if(self._chi<>0):
            s="\[S_{%s}^{old}(%s,\chi_{%s}) = " % (self._k,self._N,self._chi)
        else:
            s="\[S_{%s}^{old}(%s) = " % (self._k,self._N)
        if(len(O)==0):
            s=s+"\left\{ 0 \\right\}"
        for n in range(len(O)):
            (N,chi,m,d)=O[n]
            if(self._chi<>0):
                s=s+" %s\cdot S_{%s}^{new}(%s,\chi_{%s})" %(m,self._k,N,chi)
            else:
                s=s+" %s\cdot S_{%s}^{new}(%s)" %(m,self._k,N)
            if(n<len(O)-1 and len(O)>1):
                s=s+"\\oplus "
        s=s+"\]"
        return s

    def print_galois_orbits(self,prec=10,qexp_max_len=50):
        r"""
        Print the Galois orbits of self.

        """
	from sage.monoids.all import AlphabeticStrings
        L=self.galois_decomposition()
        if(len(L)==0):
            return ""
        x=AlphabeticStrings().gens()
        tbl=dict()
        tbl['headersh']=["dim.","defining poly.","discriminant","\(q\)-expansion of eigenform"]
        tbl['atts']="border=\"1\""
        tbl['headersv']=list()
        tbl['data']=list()
        tbl['corner_label']=""
        is_relative = False
        for j in range(len(self._galois_decomposition)):
            label=self._galois_orbits_labels[j]
            #url="?weight="+str(self.weight())+"&level="+str(self.level())+"&character="+str(self.character())+"&label="+label
            url=url_for('cmf.render_one_classical_modular_form',level=self.level(),weight=self.weight(),label=label,character=self.character())
            header="<a href=\""+url+"\">"+label+"</a>"
            tbl['headersv'].append(header)
            dim=self._galois_decomposition[j].dimension()
            orbit=self.galois_orbit(j,prec)
            # we might to truncate the power series
            # if it is too long
            cc = orbit.coefficients()
            
            slist = list()
            i = 1
            # try to split up the orbit if too long
            s = str(orbit)
            ss = "\("+my_latex_from_qexp(s)+"\)"
            ll=0
            if len(s)>qexp_max_len:
                print "LEN > MAX!"
                sl = ss.split('}')
                for i in range(len(sl)-1):
                    sss = ''
                    if i>0 and i<len(sl)-1:
                        sss = '\('
                    sss += sl[i]
                    if i < len(sl)-2:
                        sss += '}\)'
                    else:
                        sss += '})\)'
                    ll = ll+len(str(sl[i]))
                    if ll>qexp_max_len:
                        ll = 0
                        sss+="<br>"
                    slist.append(sss)
                    #print i,sss
            else:
                slist.append(ss)

            K=orbit.base_ring()
            if(K==QQ):
                poly=ZZ['x'].gen()
                disc='1'
            else:
                poly=K.defining_polynomial()
                if(K.is_relative()):
                    disc=factor(K.relative_discriminant().absolute_norm())
                    is_relative = True
                else:
                    disc=factor(K.discriminant())
            tbl['data'].append([dim,poly,disc,slist])
        # we already formatted the table
        tbl['data_format']={3:'html'}
        tbl['col_width']={3:'200'}
        tbl['atts']='width="200" border="1"'
        s=html_table(tbl)
        if(is_relative):
            s = s + "<br><small>For relative number fields we list the absolute norm of the discriminant)</small>"
        return s


    def print_geometric_data(self):
        r""" Print data about the underlying group.
        """

        return print_geometric_data_Gamma0N(self.level())
        #s="<div>"
        #s=s+"\("+latex(G)+"\)"+" : "
        #s=s+"\((\\textrm{index}; \\textrm{genus}, \\nu_2,\\nu_3)=("
        #s=s+str(G.index())+";"+str(G.genus())+","
        #s=s+str(G.nu2())+","+str(G.nu3())
        #s=s+")\)</div>"
        #return s

    def present(self):
        r"""
        Present self.
        """
        if(self._is_new):
            new="^{new}"
        else:
            new=""
        if(self._chi == 0 ):
            s="<h1>\(S"+new+"_{%s}(%s)\)</h1>" %(self._k,self._N)
        else:
            s="<h1>\(S"+new+"_{%s}(%s,\chi_{%s})\)</h1>" %(self._k,self._N,self._chi)
        s=s+"<h2>Geometric data</h2>"
        s=s+self.print_geometric_data()
        s=s+"<h2>Galois orbits</h2>"
        s=s+self.print_galois_orbits()
        if(not self._is_new):
            s=s+"<h2>Decomposition of the Oldspace</h2>"
            s=s+self.print_oldspace_decomposition()
        return s
        
class WebNewForm(SageObject):

    r"""
    Class for representing a (cuspidal) newform on the web.
    """
    def __init__(self,k,N,chi=0,label='',fi=-1,prec=10,bitprec=53,verbose=-1,data=None,compute=None):
        r"""
        Init self as form number fi in S_k(N,chi)
        """
        if chi=='trivial':
            chi=ZZ(0)
        else:
            chi=ZZ(chi)
        t=False
        self._parent=None; self.f=None
        self.f=None
        if isinstance(data,dict):
            if data.has_key('parent'):
                self._parent=data['parent']
            if data.has_key('f'):
                self.f = data['f']
        if not self._parent:
            self._parent=WebModFormSpace(k,N,chi)
        self._verbose=verbose
        # try to split the label at letters and numbers
        #if re.sub("([a-zA-Z]*)(\d*)","\\1 \\2",label):
        #    l = label.split(" ")
        #    label = l[0]
        #    if len(l)>1:
        #        num = l[1]
        self._label = label
        self._parent.galois_decomposition()
        if label not in self._parent._galois_orbits_labels:
            label=''
        if fi>=0 and fi < len(self._parent._galois_orbits_labels):
            label = self._parent._galois_orbits_labels[fi]
        if self._parent._galois_orbits_labels.count(label):
            j = self._parent._galois_orbits_labels.index(label)
        elif(len(self._parent._galois_orbits_labels)==1):
            j=0
        elif len(self._parent._galois_orbits_labels)>0:
            raise ValueError,"The space has dimension > 1. Please specify a label!"
        else:
            j=-1 #raise ValueError,"The space is zero-dimensional!"
        if j < len(self._parent._newforms) and j>=0:
            self.f=self._parent._newforms[j]
        else:
            self.f = None
            return 
        ##
        #self._name = str(N)+str(label)+str(num) +" (weight %s)" % k
        # a name is e.g. 11a (weight 2)
        self._name = str(N)+str(label) +" (weight %s)" % k
        if self.f == None:
            if(self._verbose>=0):
                raise IndexError,"Requested function does not exist!"
            else:
                return 
        self._k=ZZ(k)
        self._N=ZZ(N)
        self._chi=ZZ(chi)
        if(self._chi<>0):
            self._character=self._parent._character
        else:
            self._character=trivial_character(N)
        #self.atkin_lehner_eigenvalues()
        self._base_ring = self.f.q_eigenform(prec,names='x').base_ring()
        self._prec=prec
        self._bitprec=bitprec
        self._label=''
        self._fi=None
        self._atkin_lehner_eigenvalues={}
        #print "f=",self.f
        if(label <> ''):
            self._label=label
        else:
            self._fi = fi
        self._data = dict() # stores a lot of stuff
        self._satake={}
        self._ap = list()    # List of Hecke eigenvalues (can be long)
        self._coefficients = dict() # list of Fourier coefficients (should not be long)
        if isinstance(data,dict):
            #self._data = data
            if data.has_key('atkin_lehner_eigenalues'):
                self._atkin_lehner_eigenvalues=data['atkin_lehner_eigenalues']
            if data.has_key('coefficients'):
                self._coefficients = data['coefficients']
            if data.has_key('ap'):
                self._an = data['ap']
            if data.has_key('ebeddings'):
                self._embeddings=data['embeddings']
            if data.has_key('as_poly'):
                self._as_polynomial_in_E4_and_E6=data['as_poly']
            if data.has_key('twist_info'):
                self._twist_info = data['twist_info']
            if data.has_key('is_CM'):
                self._is_CM = data['is_CM']
            if data.has_key('satke'):
                self._satake = data['satake']
            if data.has_key('dimension'):
                self._dimension = data['dimension']
        elif compute=='all':
            self.q_expansion_embeddings(prec,bitprec)
            #self._embeddings=[]            
            if self._N==1:
                self.as_polynomial_in_E4_and_E6()
            #self._as_polynomial_in_E4_and_E6=None
            self.twist_info(prec)
            #self._twist_info = []
            self.is_CM()
            #self._is_CM = []
            self.satake_parameters()
            #self._satake = {}
            self._dimension = self.f.dimension() #1 # None
            c = self.coefficients(self.prec())
        else:
            self._embeddings=[]            
            #self.q_expansion_embeddings(prec,bitprec)
            self._as_polynomial_in_E4_and_E6=None
            self._twist_info = []
            self._is_CM = []
            self._satake = {}
            self._dimension = 1 # None

        ## we shold figure out which complex embeddings preserve the character
        
    def __eq__(self,other):
        if not isinstance(other,type(self)):
            return False
        if self._k<>other._k:
            return False
        if self._level<>other._level:
            return False        
        if self._character <> other._character:
            return False
        return True

    def __repr__(self):
        r""" String representation f self.
        """
        if self.f <>None:
            return str(self.q_expansion())
        else:
            return ""



        
    def __reduce__(self):
        r"""
        Reduce self for pickling.
        """
        data=dict()
        data['atkin_lehner_eigenvalues']=self._atkin_lehner_eigenvalues
        data['f']=self.f
        data['embeddings']=self._embeddings
        data['as_poly'] = self._as_polynomial_in_E4_and_E6
        data['twist_info'] = self._twist_info 
        data['is_CM'] = self._is_CM 
        data['satake'] = self._satake 
        data['dimension'] = self._dimension
        return(unpickle_wnf_v1,(self._k,self._N,self._chi,self._label,self._fi,self._prec,self._bitprec,self._verbose,data))

    def _save_to_file(self,file):
        r"""
        Save self to file.
        """
        self.save(file,compress=None)
        
    def level(self):
        return self._N

    def group(self):
        if hasattr(self,'_parent'):
            return self._parent.group()

    def label(self):
        if(not self._label):
            self._label = self.parent().labels()[self._fi]
        return self._label

    def weight(self):
        if hasattr(self,'_k'):
            return self._k

    def character(self):
        if hasattr(self,'_character'):
            return self._character
        else:
            return trivial_character
        
    def character_order(self):
        return self.parent.character_order()

    def character_conductor(self):
        return self.parent.character_conductor()

    def chi(self):
        if hasattr(self,'_chi'):
            return self._chi

    def prec(self):
        if hasattr(self,'_prec'):
            return self._prec

    def parent(self):
        if hasattr(self,'_parent'):
            return self._parent
    
    def is_rational(self):
        if(self.base_ring()==QQ):
            return True
        else:
            return False

    def dimension(self):
        r"""
        The dimension of this galois orbit is not necessarily equal to the degree of the number field, when we have a character....
        We therefore need this routine to distinguish between the two cases...
        """
        if not hasattr(self,'_dimension') or self._dimension == None or self._dimension<=0:
            P = self.parent()
            if P.labels().count(self.label())>0:
                j = P.labels().index(self.label())
                self._dimension = self.parent().galois_decomposition()[j].dimension()
                return self._dimension
            else:
                return 0
        else:
            return self._dimension
        
    def q_expansion_embeddings(self,prec=10,bitprec=53):
        r""" Compute all embeddings of self into C which are in the same space as self.
        """
        if(len(self._embeddings)>prec):
            bp = self._embeddings[0][0].prec()
            if bp >= bitprec:
                res = list()
                # 
                for n in range(max(prec,len(self._embeddings))):
                    l = list()
                    for i in range(len(self._embeddings[n])):
                        l.append(self._embeddings[n][i].n(bitprec))
                    res.append(l)
                return res
        if(bitprec<=0):
            bitprec=self._bitprec
        if(prec<=0):
            prec=self._prec            
        if(self.base_ring() == QQ):
            self._embeddings = self.coefficients(range(prec))
        else:
            coeffs=list()
            #E,v = self.f.compact_system_of_eigenvalues(prec)
            cc = self.coefficients(range(prec))
            for n in range(ZZ(prec)):
                cn=cc[n]
                if(self.degree()>1):
                    if hasattr(cn,'complex_embeddings'):
                        coeffs.append(cn.complex_embeddings(bitprec))
                    else:
                        coeffs.append([cn])
                else:
                    coeffs.append([cn.n(bitprec)])
            self._embeddings=coeffs
        return self._embeddings
        
    def base_ring(self):
        if hasattr(self,'_base_ring'):
            return self._base_ring
        else:
            return None

    def degree(self):
        if hasattr(self,'_base_ring'):
            return _degree(self._base_ring)
        else:
            return None

    def coefficient(self,n):
        print "n=",n
        return self.coefficients([n,n+1])

    def coefficients(self,nrange=range(1,10)):
        r"""
        Gives the coefficients in a range.
        We assume that the self._ap containing Hecke eigenvalues
        are stored.

        """
        print "nrange=",nrange
        res = []
        if not isinstance(nrange,list):
            M = nrange
            nrange = range(0,M)
        for n in nrange:
            if n==1:
                res.append(1)
            elif n==0:
                res.append(0)
            elif is_prime(n):
                pi = prime_pi(n)-1
                if pi < len(self._ap): 
                    ap = self._ap[pi]
                else:
                    # fill up the ap vector
                    prims = primes_first_n(len(self._ap))
                    #print "ap=",self._ap
                    #print "len=",len(self._ap)
                    #print "prim=",primes_first_n(len(self._ap))
                    if len(prims)>0:
                        ps = next_prime(primes_first_n(len(self._ap))[-1])
                    else:
                        ps = ZZ(2)
                    #print "nprime=",ps
                    mn = max(nrange)
                    if is_prime(mn):
                        pe = mn
                    else:
                        pe = previous_prime(mn)
                    #print "ps,pe=",ps,pe
                    E,v = self.f.compact_system_of_eigenvalues(prime_range(ps,pe+1),names='x')
                    c = E*v
                    for app in c:
                        self._ap.append(app)
                ap = self._ap[pi]
                res.append(ap)
                # we store up to self.prec coefficients which are not prime
                if n <= self.prec():
                    self._coefficients[n]=ap
            else:
                if self._coefficients.has_key(n):
                    an = self._coefficients[n]
                else:
                    print "n=",n
                    an = self.f.eigenvalue(n,name='x')
                    self._coefficients[n]=an
                res.append(an)
        return res

    def q_expansion(self,prec=10):
        if hasattr(self.f,'q_expansion'):
            return self.f.q_expansion(ZZ(prec))
        if hasattr(self.f,'q_eigenform'):
            return self.f.q_eigenform(ZZ(prec),names='x')
    
    def atkin_lehner_eigenvalues(self):
        r""" Compute the Atkin-Lehner eigenvalues of self. 

           EXAMPLES::

           sage: get_atkin_lehner_eigenvalues(4,14,0)
           '{2: 1, 14: 1, 7: 1}'
           sage: get_atkin_lehner_eigenvalues(4,14,1)
           '{2: -1, 14: 1, 7: -1}'
           

        """
        if(len(self._atkin_lehner_eigenvalues.keys())>0):
            return self._atkin_lehner_eigenvalues
        if(self._chi<>0):
            return ""
        res=dict()
        for Q in divisors(self.level()):
            if(Q==1):
                continue
            if(gcd(Q,ZZ(self.level()/Q))==1):
                try:
                    M=self.f.atkin_lehner_operator(ZZ(Q)).matrix()
                    ev = M.eigenvalues()
                    if len(ev)>1:
                        if len(set(ev))>1:
                            raise ArithmeticError,"Should be one Atkin-Lehner eigenvalue. Got: %s " % ev
                    res[Q]=ev[0]
                    #res[Q]=self.f.atkin_lehner_eigenvalue(ZZ(Q))
                except:
                    pass
        self._atkin_lehner_eigenvalues=res
        #print "res=",res
        return res

    def atkin_lehner_eigenvalues_for_all_cusps(self):
        r"""
        Return Atkin-Lehner eigenvalue of A-L involution 
        which normalizes cusp if such an inolution exist.
        """
        res=dict()
        for c in self.parent().group().cusps():
            if c==Infinity:
                continue
            l=self.atkin_lehner_at_cusp(c)
            print "l=",c,l
            if(l):
                (Q,ep)=l
                res[c]=[Q,ep]
                #res[c]=ep
        return res
            
    def atkin_lehner_at_cusp(self,cusp):
        r"""
        Return Atkin-Lehner eigenvalue of A-L involution 
        which normalizes cusp if such an involution exist.
        """
        x= self.character()
        if( x <> 0 and not x.is_trivial()):
            return None
        if(cusp==Cusp(Infinity)):
            return (ZZ(0),1)
        elif(cusp==Cusp(0)):
            try: 
                return (self.level(),self.atkin_lehner_eigenvalues()[self.level()])
            except:
                return None
        cusp=QQ(cusp)
        N=self.level()
        q=cusp.denominator()
        p=cusp.numerator()
        d=ZZ(cusp*N)
        if(d.divides(N) and gcd(ZZ(N/d),ZZ(d))==1):
            M = self.f.atkin_lehner_operator(ZZ(d))
            ev = M.eigenvalues()
            if len(ev)>1:
                if len(set(ev))>1:
                    raise ArithmeticError,"Should be one Atkin-Lehner eigenvalue. Got: %s " % ev
            return (ZZ(d),ev[0])
            #return (ZZ(d),self.f.atkin_lehner_eigenvalue(ZZ(d)))
#>>>>>>> variant B
#            return (ZZ(d),self.f.atkin_lehner_eigenvalue(ZZ(d)))
####### Ancestor
#            return self.f.atkin_lehner_eigenvalue(ZZ(d))
#======= end
        else:
            return None

    def is_minimal(self):
        r"""
        Returns True if self is a twist and otherwise False.
        """
        [t,f]=self.twist_info()
        if(t):
            return True
        elif(t==False):
            return False
        else:
            return "Unknown"
            
    def twist_info(self,prec=10):
        r"""
        Try to find forms of lower level which get twisted into self.
        OUTPUT:
        
        -''[t,l]'' -- tuple of a Bool t and a list l. The list l contains all tuples of forms which twists to the given form.
        The actual minimal one is the first element of this list.
	     t is set to True if self is minimal and False otherwise


        EXAMPLES::



        """
        if(len(self._twist_info)>0):
            return self._twist_info
        N=self.level()
        k=self.weight()
        if(is_squarefree(ZZ(N))):
            self._twist_info =  [True,self.f]
            return [True,self.f]
        
        # We need to check all square factors of N
        twist_candidates=list()
        KF=self.base_ring()
        # check how many Hecke eigenvalues we need to check
        max_nump=self._number_of_hecke_eigenvalues_to_check()
        maxp=max(primes_first_n(max_nump))
        for d in divisors(N):
            if(d==1):
                continue
            # we look at all d such that d^2 divdes N
            if(not ZZ(d**2).divides(ZZ(N))):
                continue
            D=DirichletGroup(d)
            # check possible candidates to twist into f
            # g in S_k(M,chi) wit M=N/d^2
            M=ZZ(N/d**2)
            if(self._verbose>0):
                print "Checking level ",M
            for xig in range(euler_phi(M)):
                (t,glist) = _get_newform(k,M,xig)
                if(not t):
                    return glist
                for g in glist:
                    if(self._verbose>1):
                        print "Comparing to function ",g
                    KG=g.base_ring()
                    # we now see if twisting of g by xi in D gives us f
                    for xi in D:
                        try:
                            for p in primes_first_n(max_nump):
                                if(ZZ(p).divides(ZZ(N))):
                                    continue
                                bf=self.f.q_expansion(maxp+1)[p]
                                bg=g.q_expansion(maxp+1)[p]
                                if(bf == 0 and bg == 0):
                                    continue
                                elif(bf==0 and bg<>0 or bg==0 and bf<>0):
                                    raise StopIteration()
                                if(ZZ(p).divides(xi.conductor())):
                                    raise ArithmeticError,""
                                xip=xi(p)
                                # make a preliminary check that the base rings match with respect to being real or not
                                try:
                                    QQ(xip)
                                    XF=QQ
                                    if( KF<>QQ or KG<>QQ):
                                        raise StopIteration
                                except TypeError:
                                    # we have a  non-rational (i.e. complex) value of the character
                                    XF=xip.parent() 
                                    if( (KF == QQ or KF.is_totally_real()) and (KG == QQ or KG.is_totally_real())):
                                        raise StopIteration
                            ## it is diffcult to compare elements from diferent rings in general but we make some checcks
                            ## is it possible to see if there is a larger ring which everything can be coerced into?
                                ok=False
                                try:
                                    a=KF(bg/xip); b=KF(bf)
                                    ok=True
                                    if(a<>b):
                                        raise StopIteration()
                                except TypeError:
                                    pass
                                try:
                                    a=KG(bg); b=KG(xip*bf)
                                    ok=True
                                    if(a<>b):
                                        raise StopIteration()
                                except TypeError:
                                    pass
                                if(not ok): # we could coerce and the coefficients were equal
                                    return "Could not compare against possible candidates!"
                                # otherwise if we are here we are ok and found a candidate
                            twist_candidates.append([M,g.q_expansion(prec),xi])
                        except StopIteration:
                            # they are not equal
                            pass
        # print "Candidates=",twist_candidates
        self._twist_info =  (False,twist_candidates)
        if(len(twist_candidates)==0):
            self._twist_info =  [True,self.f]
        else:
            self._twist_info = [False,twist_candidates]
        return self._twist_info 



    def is_CM(self):
        r"""
        Checks if f has complex multiplication and if it has then it returns the character.
        
        OUTPUT:
        
        -''[t,x]'' -- string saying whether f is CM or not and if it is, the corresponding character
        
        EXAMPLES::

        """
        if(len(self._is_CM)>0):
            return self._is_CM
        max_nump=self._number_of_hecke_eigenvalues_to_check()
        #E,v = self.f.compact_system_of_eigenvalues(max_nump+1)
        coeffs=self.coefficients(range(max_nump+1))
        nz=coeffs.count(0) # number of zero coefficients
        nnz = len(coeffs) - nz # number of non-zero coefficients
        if(nz==0):
            self._is_CM=[False,0]
            return self._is_CM
        # probaly checking too many
        for D in range(3,ceil(QQ(max_nump)/QQ(2))):
            try:
                for x in DirichletGroup(D):
                    if(x.order()<>2):
                        continue
                    # we know that for CM we need x(p) = -1 => c(p)=0
                    # (for p not dividing N)
                    if(x.values().count(-1) > nz):
                        raise StopIteration() # do not have CM with this char           
                    for p in prime_range(max_nump+1):
                        if(x(p)==-1 and coeffs[p]<>0):
                            raise StopIteration() # do not have CM with this char
                    # if we are here we have CM with x. 
                    self._is_CM=[True,x]
                    return self._is_CM
            except StopIteration:
                pass
        self._is_CM=[False,0]
        return self._is_CM


    def as_polynomial_in_E4_and_E6(self):
        r"""
        If self is on the full modular group writes self as a polynomial in E_4 and E_6.
        OUTPUT:
        -''X'' -- vector (x_1,...,x_n)
        with f = Sum_{i=0}^{k/6} x_(n-i) E_6^i * E_4^{k/4-i}
        i.e. x_i is the coefficient of E_6^(k/6-i)*
        """
        if(self.level()<>1):
            raise NotImplementedError,"Only implemented for SL(2,Z). Need more generators in general."
        if(self._as_polynomial_in_E4_and_E6<>None):
            return self._as_polynomial_in_E4_and_E6
        d=self._parent.dimension()
        k=self.weight()
        K=self.base_ring()
        l=list()
        #for n in range(d+1):
        #    l.append(self.f.q_expansion(d+2)[n])
        #v=vector(l) # (self.f.coefficients(d+1))
        v = self.coefficients(range(d+1))
        d=dimension_modular_forms(1,k)
        lv=len(v)
        if(lv<d):
            raise ArithmeticError,"not enough Fourier coeffs"
        e4=EisensteinForms(1,4).basis()[0].q_expansion(lv+2)
        e6=EisensteinForms(1,6).basis()[0].q_expansion(lv+2)
        m=Matrix(K,lv,d)
        lima=floor(k/6)     #lima=k\6;
        if( (lima-(k/2)) % 2==1):
            lima=lima-1
        poldeg=lima; col=0
        monomials=dict()
        while(lima>=0):
            deg6=ZZ(lima)
            deg4=(ZZ((ZZ(k/2)-3*lima)/2))
            e6p=(e6**deg6)
            e4p=(e4**deg4)
            monomials[col]=[deg4,deg6]
            eis=e6p*e4p
            for i in range(1,lv+1):
                m[i-1,col]=eis.coefficients()[i-1]
            lima=lima-2
            col=col+1
        if (col<>d):
            raise ArithmeticError,"bug dimension"
        #return [m,v]
        try:
            X=m.solve_right(v)
        except:
            return ""
        self._as_polynomial_in_E4_and_E6=[poldeg,monomials,X]
        return [poldeg,monomials,X]

    def exact_cm_at_i_level_1(self,N=10):
        r"""
        Use formula by Zagier (taken from pari implementation by H. Cohen) to compute the geodesic expansion of self at i
        and evaluate the constant term.

        INPUT:
        -''N'' -- integer, the length of the expansion to use.
        """
        [poldeg,monomials,X]=self.as_polynomial_in_E4_and_E6()
        k=self.weight()
        tab=dict()
        QQ['x']
        tab[0]=0*x**0
        tab[1]=X[0]*x**poldeg
        #print "tab=",tab
        for ix in range(1,len(X)):
            #print "X[ix]=",X[ix]
            tab[1]=tab[1]+QQ(X[ix])*x**monomials[ix][1]
        for n in range(1,N+1):
            tmp=-QQ(k+2*n-2)/QQ(12)*x*tab[n]+(x**2-QQ(1))/QQ(2)*((tab[n]).derivative())
            tab[n+1]=tmp-QQ((n-1)*(n+k-2))/QQ(144)*tab[n-1]
        res=0
        #print "tab=",tab
        for n in range(1,N+1):
            term=(tab[n](x=0))*12**(floor(QQ(n-1)/QQ(2)))*x**(n-1)/factorial(n-1)
            res=res+term
            #print "term(",n,")=",term
            #print "res(",n,")=",res
        return res
    #,O(x^(N+1))))
    #return (sum(n=1,N,subst(tab[n],x,0)*
 
    def as_homogeneous_polynomial(self):
        r"""
        Represent self as a homogenous polynomial in E6/E4^(3/2)
        """

    def print_as_polynomial_in_E4_and_E6(self):
        r"""

        """
        if(self.level() <> 1):
            return ""
        [poldeg,monomials,X]=self.as_polynomial_in_E4_and_E6()
        s=""
        e4="E_{4}";e6="E_{6}"
        dens=map(denominator,X)
        g=gcd(dens)
        s="\\frac{1}{"+str(g)+"}\left("
        for n in range(len(X)):
            c=X[n]*g            
            if(c==-1):
                s=s+"-"
            elif(c<>1):
                s=s+str(c)
            if(n>0 and c>0):
                s=s+"+"
            d6=monomials[n][0]
            d4=monomials[n][1]
            if(d6>0):
                s=s+e6+"^{"+str(monomials[n][1])+"}"
            if(d4>0):
                s=s+e4+"^{"+str(monomials[n][0])+"}"
        s=s+"\right)"
        return "\("+s+"\)"
    
    def cm_values(self,digits=12):
        r""" Computes and returns a list of values of f at a collection of CM points as complex floating point numbers.

        INPUT:

        -''digits'' -- we want this number of corrrect digits in the value

        OUTPUT:
        -''s'' string representation of a dictionary {I:f(I):rho:f(rho)}.

        TODO: Get explicit, algebraic values if possible!
        """

        
        bits=max(53,ceil(digits*4))
        CF=ComplexField(bits)
        RF=ComplexField(bits)
        eps=RF(10**-(digits+1))
        if(self._verbose>1):
            print "eps=",eps
        K=self.base_ring()
        print "K=",K
        # recall that 
        degree = K.degree()
        cm_vals=dict()
        # the points we want are i and rho. More can be added later...
        rho=CyclotomicField(3).gen()
        zi=CyclotomicField(4).gen()
        points=[rho,zi]
        maxprec=1000 # max size of q-expansion
        minprec=10 # max size of q-expansion
        for tau in points:
            q=CF(exp(2*pi*I*tau))
            fexp=dict()
            cm_vals[tau]=dict()
            if(tau==I and self.level()==-1):
                #cv=    #"Exact(soon...)" #_cohen_exact_formula(k)
                for h in range(degree):
                    cm_vals[tau][h]=cv
                continue
            if(K==QQ):
                v1=CF(0); v2=CF(1)
                try:
                    for prec in range(minprec,maxprec,10):
                        if(self._verbose>1):
                            print "prec=",prec
                        v2=self.f.q_eigenform(prec)(q)
                        err=abs(v2-v1)
                        if(self._verbose>1):
                            print "err=",err
                        if(err< eps):
                            raise StopIteration()
                        v1=v2
                    cm_vals[tau][0]=None
                except StopIteration:
                    cm_vals[tau][0]=v2
            else:
                v1=dict()
                v2=dict()
                err=dict()
                for h in  range(degree):
                    v1[h]=1
                    v2[h]=0
                try:
                    for prec in range(minprec,maxprec,10):
                        if(self._verbose>1):
                            print "prec=",prec
                        c = self.coefficients(range(prec))
                        for h in range(degree):
                            fexp[h]=list()
                            v2[h]=0
                            for n in range(prec):
                                cn = c[n]
                                if hasattr(cn,'complex_embeddings'):
                                    cc=cn.complex_embeddings(CF.prec())[h]
                                else:
                                    cc=CF(cn)
                                v2[h]=v2[h]+cc*q**n
                            err[h]=abs(v2[h]-v1[h])
                            if(self._verbose>1):
                                print "v1[",h,"]=",v1[h]
                                print "v2[",h,"]=",v2[h]
                                print "err[",h,"]=",err[h]
                            if(max(err.values()) < eps):          
                                raise StopIteration()
                            v1[h]=v2[h]
                except StopIteration:
                    pass
                for h in range(degree):
                    if(err[h] < eps):
                        cm_vals[tau][h]=v2[h]
                    else:
                        cm_vals[tau][h]=None
        return cm_vals
    
    def satake_parameters(self,prec=10,bits=53):
        r""" Compute the Satake parameters and return an html-table.

        We only do satake parameters for primes p primitive to the level.
        By defintion the S. parameters are given as the roots of
         X^2 - c(p)X + chi(p)*p^(k-1)

        INPUT:
        -''prec'' -- compute parameters for p <=prec
        -''bits'' -- do real embedings intoi field of bits precision

        """
        if not hasattr(self,'_satake'):
            self._satake={}
        elif(self._satake<>{}):
            x = self._satake['thetas'].values()[0].values()[0]
            if x.prec() >= bits: # else recompute
                return self._satake
        K=self.base_ring()
        degree = _degree(K)
        RF=RealField(bits)
        CF=ComplexField(bits)
        ps=prime_range(prec)
        alphas=dict()
        thetas=dict()
        aps=list(); tps=list()
        k=self.weight()
        E,v = self.f.compact_system_of_eigenvalues(ps)
        ap_vec = E*v
        for j in range(degree):
            alphas[j]=dict(); thetas[j]=dict();
        for j in xrange(len(ps)):
            p = ps[j]
            ap = ap_vec[j]
            if p.divides(self.level()):
                continue
            chip = self.character()(p)
            #ap=self.f.coefficients(ZZ(prec))[p]
            if(K==QQ):
                f1=QQ(4*chip*p**(k-1)-ap**2)
                alpha_p=(QQ(ap)+I*f1.sqrt())/QQ(2)
                ab=RF(p**((k-1)/2))
                norm_alpha=alpha_p/ab
                t_p=CF(norm_alpha).argument()
                thetas[0][p]=t_p
                alphas[0][p]=alpha_p
            else:

                
                for jj in range(degree):
                    app=ap.complex_embeddings(bits)[jj]
                    f1=(4*CF(chip)*p**(k-1)-app**2)
                    alpha_p=(app+I*abs(f1).sqrt())
                    #ab=RF(/RF(2)))
                    #alpha_p=alpha_p/RealField(bits)(2)

                    alpha_p=alpha_p/RF(2)
                    t_p=CF(alpha_p).argument()
                    #tps.append(t_p)
                    #aps.append(alpha_p)
                    alphas[jj][p]=alpha_p
                    thetas[jj][p]=t_p
        self._satake['alphas']=alphas
        self._satake['thetas']=thetas
        return self._satake
    
    def print_satake_parameters(self,stype=['alphas','thetas'],prec=10,bprec=53):
        print "print_satake=",prec,bprec
        if self.f == None:
            return ""
        satake=self.satake_parameters(prec,bprec)
        tbl=dict()
        if not isinstance(stype,list):
            stype = [stype]
        tbl['headersh']=satake[stype[0]][0].keys()
        tbl['atts']="border=\"1\""
        tbl['data']=list()
        tbl['headersv']=list()
        K = self.base_ring()
        degree = _degree(K)
        if(self.dimension()>1):
            tbl['corner_label']="\( Embedding \, \\backslash \, p\)"
        else:
            tbl['corner_label']="\( p\)"
        for type in stype:
            for j in range(degree):
                if(self.dimension()>1):
                    tbl['headersv'].append(j)
                else:
                    if(type=='alphas'):
                        tbl['headersv'].append('\(\\alpha_p\)')
                    else:
                        tbl['headersv'].append('\(\\theta_p\)')
                row=list()
                for p in satake[type][j].keys():
                    row.append(satake[type][j][p])
                tbl['data'].append(row)
        #print tbl
        s=html_table(tbl)
        return s



    def _number_of_hecke_eigenvalues_to_check(self):
        r""" Compute the number of Hecke eigenvalues (at primes) we need to check to identify twists of our given form with characters of conductor dividing the level.
        """
        ## initial bound
        bd=self.f.sturm_bound()
        # we do not check primes dividing the level
        bd=bd+len(divisors(self.level()))
        return bd


    ## printing functions


    def print_q_expansion(self,prec=None,br=0):
        r"""
        Print the q-expansion of self.
        
        INPUT:
 
        OUTPUT:

        - ''s'' string giving the coefficients of f as polynomals in x
        
        EXAMPLES::


        """
        
        if(prec==None):
            prec=self._prec
        s = my_latex_from_qexp(str(self.q_expansion(prec)))
        sb = list()
        #brpt
        if br > 0:
            sb = break_line_at(s,br)
        if len(sb)==0:
            s = "\("+s+"\)"
        else:
            s = "\("+"\)<br>\(".join(sb)+"\)"
        print "print_q_exp: prec=",prec
        print "s=",s
        return s

    
    

    def print_q_expansion_embeddings(self,prec=10,bprec=53):
        r"""
        Print all embeddings of Fourier coefficients of the newform self.
    
        INPUT:
        - ''prec'' -- integer (the number of coefficients to get)
        - ''bprec'' -- integer (the number of bits we use for floating point precision)
        
        OUTPUT:
        
        - ''s'' string giving the coefficients of f as floating point numbers
        
        EXAMPLES::
        
        # a rational newform
        sage: get_fourier_coefficients_of_newform_embeddings(2,39,0)
        '[1, 1, -1, -1, 2, -1, -4, -3, 1, 2]'
        sage: get_fourier_coefficients_of_newform(2,39,0)
        [1, 1, -1, -1, 2, -1, -4, -        - ''prec'' -- integer (the number of coefficients to get), 1, 2]
        # a degree two newform
        sage: get_fourier_coefficients_of_newform(2,39,1,5)
        [1, x, 1, -2*x - 1, -2*x - 2]
        sage: get_fourier_coefficients_of_newform_embeddings(2,39,1,5)
        [[1.00000000000000, 1.00000000000000], [-2.41421356237309, 0.414213562373095], [1.00000000000000, 1.00000000000000], [3.82842712474619, -1.82842712474619], [2.82842712474619, -2.82842712474619]]
        

        """
        coeffs=self.q_expansion_embeddings(prec,bprec)
        if(isinstance(coeffs,str)):
            return coeffs  ### we probably failed to compute the form
        # make a table of the coefficients
        print "print_embeddings: prec=",prec,"bprec=",bprec
        tbl=dict()
        tbl['atts']="border=\"1\""
        tbl['headersh']=list()
        for n in range(len(coeffs)):
            tbl['headersh'].append("\("+str(n+1)+"\)")
        tbl['headersv']=list()
        tbl['data']=list()
        tbl['corner_label']="\( Embedding \, \\backslash \, n \)"
        for i in range(len(coeffs[0])):
            tbl['headersv'].append("\(v_{%s}(a(n)) \)" % i)
            row=list()
            for n in range(len(coeffs)):
                if i<len(coeffs[n]):
                    row.append(coeffs[n][i])
                else:
                    row.append("")
            tbl['data'].append(row)

        s=html_table(tbl)
        return s

    def polynomial(self,format='latex'):
        r"""
        Here we have to check whether f is defined over a base ring over Q or over a CyclotomicField...
        """
        K = self.base_ring()
        if K == None:
            return ""
        if(self.dimension()==1 and K==QQ):
            if(K == QQ):
                s = 'x'
            else:
                if format == 'latex':
                    s = latex(K.gen())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
        else:
            if(K.is_relative()):
                if format == 'latex':
                    s=latex(K.relative_polynomial())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
            else:
                if format == 'latex':
                    s=latex(self.base_ring().polynomial())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
        return s

    
        
    def print_atkin_lehner_eigenvalues(self):
        r"""
        """
        l=self.atkin_lehner_eigenvalues()
        if(len(l)==0):
            return ""
        tbl=dict()
        tbl['headersh']=list()
        tbl['atts']="border=\"1\""
        tbl['data']=[0]
        tbl['data'][0]=list()
        tbl['corner_label']="\(Q\)"
        tbl['headersv']=["\(\epsilon_{Q}\)"]
        for Q in l.keys():
            if(Q == self.level()):
                tbl['headersh'].append('\('+str(Q)+'{}^*{}\)')
            else:
                tbl['headersh'].append('\('+str(Q)+'\)')
            tbl['data'][0].append(l[Q])
        s=html_table(tbl)
        return s
        
    def print_atkin_lehner_eigenvalues_for_all_cusps(self):
        l=self.atkin_lehner_eigenvalues_for_all_cusps()
        if(l.keys().count(Cusp(Infinity))==len(l.keys())):
            return ""
        if(len(l)==0):
            return ""
        tbl=dict()
        tbl['headersh']=list()
        tbl['atts']="border=\"1\""
        tbl['data']=[0]
        tbl['data'][0]=list()
        tbl['corner_label']="\( Q \)  \([cusp]\)"
        tbl['headersv']=["\(\epsilon_{Q}\)"]
        for c in l.keys():
            #print "Q=",Q
            if(c<>Cusp(Infinity)):
                #print "hej"
                Q = l[c][0]
                s = '\('+str(Q)+"\; ["+str(c)+"]\)"
                if( c==0 ):
                    tbl['headersh'].append(s+'\({}^{*}\)')
                else:
                    tbl['headersh'].append(s)
                tbl['data'][0].append(l[c][1])
        print tbl
        s=html_table(tbl)
        #s=s+"<br><small>* ) The Fricke involution</small>"
        return s

    def print_twist_info(self,prec=10):
        r"""
        Prints info about twisting.
        
        OUTPUT:

        -''s'' -- string representing a tuple of a Bool and a list. The list contains all tuples of forms which twists to the given form.
        The actual minimal one is the first element of this list.

        EXAMPLES::
        """
        [t,l]=self.twist_info(prec)
        if(t):
            return "f is minimal."
        else:
            return "f is a twist of "+str(l[0])


    def print_is_CM(self):
        r"""
        """
        [t,x]=self.is_CM()
        if(t):
            ix=x.parent().list().index(x)
            m=x.parent().modulus()
            s="f has CM with character nr. %s modulo %s of order %s " % (ix,m,x.order())
        else:
            s=""
        return s

    def present(self):
        r"""
        Present self.
        """
        s="<h1>f is a newform in </h2>"
        s=" \( f (q) = "+self.print_q_expansion()+"\)"
        s=s+""
        s=s+"<h2>Atkin-Lehner eigenvalues</h2>"
        s=s+self.print_atkin_lehner_eigenvalues()
        s=s+"<h2>Atkin-Lehner eigenvalues for all cusps</h2>"
        s=s+self.print_atkin_lehner_eigenvalues_for_all_cusps()
        s=s+"<h2>Info on twisting</h2>"
        s=s+self.print_twist_info()
        if(self.is_CM()[0]):
            s=s+"<h2>Info on CM</h2>"
            s=s+self.print_is_CM()
        s=s+"<h2>Embeddings</h2>"            
        s=s+self.print_q_expansion_embeddings()
        s=s+"<h2>Values at CM points</h2>\n"            
        s=s+self.print_values_at_cm_points()
        s=s+"<h2>Satake Parameters \(\\alpha_p\)</h2>"            
        s=s+self.print_satake_parameters(type='alphas')
        s=s+"<h2>Satake Angles \(\\theta_p\)</h2>\n"            
        s=s+self.print_satake_parameters(type='thetas')
        if(self.level()==1):
            s=s+"<h2>As polynomial in \(E_4\) and \(E_6\)</h2>\n"
            s=s+self.print_as_polynomial_in_E4_and_E6()

        return s


    def print_values_at_cm_points(self):
        r"""
        """
        cm_vals=self.cm_values()
        K=self.base_ring()
        degree = _degree(K)
        if(self._verbose>2):
            print "vals=",cm_vals
            print "errs=",err
        tbl=dict()
        tbl['corner_label']="\(\\tau\)"
        tbl['headersh']=['\(\\rho=\zeta_{3}\)','\(i\)']
        #if(K==QQ):
        #    tbl['headersv']=['\(f(\\tau)\)']
        #    tbl['data']=[cm_vals.values()]
        #else:
        tbl['data']=list()
        tbl['atts']="border=\"1\""
        tbl['headersv']=list()
        #degree = self.dimension()
        for h in range(degree):
            if(degree==1):
                tbl['headersv'].append("\( f(\\tau) \)")
            else:
                tbl['headersv'].append("\(v_{%s}(f(\\tau))\)" % h)
                
            row=list()
            for tau in cm_vals.keys():
                if cm_vals[tau].has_key(h):
                    row.append(cm_vals[tau][h])            
                else:
                    row.append("")
            tbl['data'].append(row)
        #print tbl
        #print 
        s=html_table(tbl)
        # s=html.table([cm_vals.keys(),cm_vals.values()])
        return s




    def twist_by(self,x):
        r"""
        twist self by a primitive Dirichlet character x
        """
        #xx = x.primitive()
        assert x.is_primitive()
        q = x.conductor()
        # what level will the twist live on?
        level = self.level()
        qq =  self._character.conductor()
        new_level = lcm(self.level(),lcm(q*q,q*qq))
        D = DirichletGroup(new_level)
        new_x = D(self._character)*D(x)*D(x)
        ix = D.list().index(new_x)
        #  the correct space
        NS = WebModFormSpace(self._k,new_level,ix,self._prec)
        # have to find whih form wee want
        NS.galois_decomposition()
        M = NS.sturm_bound() + len(divisors(new_level))
        C = self.coefficients(range(M))
        for label in NS._galois_orbits_labels:
            print "label=",label
            FT = NS.f(label)
            CT = FT.f.coefficients(M)
            print CT
            K = FT.f.hecke_eigenvalue_field()
            try:
                for n in range(2,M):
                    if(new_level % n+1 ==0):
                        continue
                    print "n=",n
                    ct = CT[n]
                    c  = K(x(n))*K(C[n])
                    print ct,c
                    if ct <> c:
                        raise StopIteration()
            except StopIteration:
                pass
            else:
                print  "Twist of f=",FT
        return  FT
            
###
### Independent helper functions  
### 





def my_latex_from_qexp(s):
    r"""
    Make LaTeX from string. in particular from parts of q-expansions.
    """
    ss = ""
    ss+=re.sub('x\d','x',s)
    ss=re.sub("\^(\d+)","^{\\1}",ss)
    ss=re.sub('\*','',ss)
    ss=re.sub('zeta(\d+)','\zeta_{\\1}',ss)  
    ss += ""
    return ss


def break_line_at(s,brpt=20):
    r"""
    Breaks a line containing math 'smartly' at brpt characters.
    With smartly we mean that we break at + or - but keep brackets
    together
    """
    sl=list()
    stmp = ''
    left_par = 0
    for i in range(len(s)):
        if s[i] == '(': ## go to the matching case
            left_par = 1
        elif s[i] == ')' and left_par==1:
            left_par = 0
        if left_par == 0 and (s[i] == '+' or s[i]== '-'):
            sl.append(stmp)
            stmp=''
        stmp = join([stmp,s[i]])
        if i==len(s)-1:
            sl.append(stmp)

    # sl now contains a split  e.g. into terms in the q-expansion
    # we now have to join as many as fits on the line
    #print "sl=",sl
    res = list()
    stmp=''
    for j in range(len(sl)):
        l = len_as_printed(stmp)+len_as_printed(sl[j])
        print "l=",l
        #print join([stmp,sl[j]])
        #print "len(stmp)+len(sl[j])=",len(stmp)+len(sl[j])
        if l<brpt:
            stmp = join([stmp,sl[j]])
        else:
            res.append(stmp)
            stmp = sl[j]
        #print "stmp=",stmp
        if j == len(sl)-1:
            res.append(stmp)
    return res



def _get_newform(k,N,chi,fi=None):
    r"""
    Get an element of the space of newforms, incuding some error handling.
    
    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''chi'' -- non-neg. integer (default 0) use character nr. chi
     - ''fi'' -- integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]. fi=-1 returns the whole list
     - ''prec'' -- integer (the number of coefficients to get)
     
    OUTPUT:
    
    -''t'' -- bool, returning True if we succesfully created the space and picked the wanted f
    -''f'' -- equals f if t=True, otherwise contains an error message.
     
    EXAMPLES::

    
        sage: _get_newform(16,10,1)
        (False, 'Could not construct space $S^{new}_{16}(10)$')
        sage: _get_newform(10,16,1)
        (True, q - 68*q^3 + 1510*q^5 + O(q^6))
        sage: _get_newform(10,16,3)
        (True, q + 156*q^3 + 870*q^5 + O(q^6))
        sage: _get_newform(10,16,4)
        (False, '')

     """
    t=False
    #print k,N,chi,fi
    try:
        if(chi==0):
            S=Newforms(N,k,names='x')
        else:
            S=Newforms(DirichletGroup(N)[chi],k,names='x')
        if(fi>=0 and fi <len(S)):
            f=S[fi]
            t=True
        elif(fi==-1 or fi==None):
            t=True
            return (t,S)
        else:
            f=""
    except RuntimeError: 
        if(chi==0):
            f="Could not construct space $S^{new}_{%s}(%s)$" %(k,N)
        else:
            f="Could not construct space $S^{new}_{%s}(%s,\chi_{%s})$" %(k,N,chi)
    return (t,f)






def _degree(K):
    r"""
    Returns the degree of the number field K
    """
    if(K==QQ):
        return 1
    try:
        if(K.is_relative()):
            return K.relative_degree()
        return K.degree()
    except AttributeError:
        return  -1 ##  exit silently
        

def unpickle_wnf_v1(k,N,chi,label,fi,prec,bitprec,verbose,data):
    F = WebNewForm(k,N,chi,label,fi,prec,bitprec,verbose,data)
    return F

def unpickle_wmfs_v1(k,N,chi,prec,data):
    M = WebModFormSpace(k,N,chi,prec,data)
    return M

