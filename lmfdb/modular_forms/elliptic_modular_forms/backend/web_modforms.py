# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2014
#  Fredrik Strömberg <fredrik314@gmail.com>,
#  Stephan Ehlen <stephan.j.ehlen@gmail.com>
# 
#  Distributed under the terms of the GNU General Public License (GPL)
#
#    This code is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    General Public License for more details.
#
#  The full text of the GPL is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
r""" Class for newforms in format which can be presented on the web easily


AUTHORS:

 - Fredrik Stroemberg
 - Stephan Ehlen


NOTE: We are now working completely with the Conrey naming scheme.
 
TODO:
Fix complex characters. I.e. embedddings and galois conjugates in a consistent way.

"""
from sage.all import ZZ, QQ, DirichletGroup, CuspForms, Gamma0, ModularSymbols, Newforms, trivial_character, is_squarefree, divisors, RealField, ComplexField, prime_range, I, join, gcd, Cusp, Infinity, ceil, CyclotomicField, exp, pi, primes_first_n, euler_phi, RR, prime_divisors, Integer, matrix,NumberField,PowerSeriesRing
from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import Parent, SageObject, dimension_new_cusp_forms, vector, dimension_modular_forms, dimension_cusp_forms, EisensteinForms, Matrix, floor, denominator, latex, is_prime, prime_pi, next_prime, previous_prime,primes_first_n, previous_prime, factor, loads,save,dumps,deepcopy
import re
import yaml
from flask import url_for
from lmfdb.number_fields.number_field import poly_to_field_label

## DB modules
import pymongo
import gridfs
from pymongo.helpers import bson
from bson import BSON
# local imports
import lmfdb.base
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger,emf_version
from plot_dom import draw_fundamental_domain
from emf_core import html_table, len_as_printed

from sage.rings.number_field.number_field_base import NumberField as NumberField_class
from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db,get_files_from_gridfs
from web_character import WebChar

    
def WebNewForm(N=1, k=2, chi=1, label='', prec=10, bitprec=53, display_bprec=26, parent=None, data=None, compute=False, verbose=-1,get_from_db=True):
    r"""
    Constructor for WebNewForms with added 'nicer' error message.
    """
    ## First check
    if chi == 1:
        if k % 2 == 1:
            emf_logger.debug("Only zero function here with N,k,chi,label={0}.".format( (N,k,chi,label)))
            return 0
    if not data is None: emf_logger.debug("incoming data in construction : {0}".format(data.get('N'),data.get('k'),data.get('chi')))
    try: 
        F = WebNewForm_class(N=N, k=k, chi=chi, label=label, prec=prec, bitprec = bitprec, display_bprec=display_bprec, parent = parent, data = data, compute = compute, verbose = verbose, get_from_db = get_from_db)
    except ArithmeticError as e:#Exception as e:
        emf_logger.critical("Could not construct WebNewForm with N,k,chi,label={0}. Error: {1}".format( (N,k,chi,label),e))
        raise IndexError,"We are very sorry. The sought function could not be found in the database."
    return F


class WebNewForm_class(object):
    r"""
    Class for representing a (cuspidal) newform on the web.
    """
    
    def __init__(self, N=1, k=2, chi=1, label='', prec=10, bitprec=53, display_bprec=26,parent=None, data=None, compute=False, verbose=-1,get_from_db=True):
        r"""
        Init self as form with given label in S_k(N,chi)
        """
        from web_modform_space import WebModFormSpace_class, WebModFormSpace
        emf_logger.debug("WebNewForm with N,k,chi,label={0}".format( (N,k,chi,label)))
        if not data is None and isinstance(data, dict):
            emf_logger.debug("incoming data in construction : {0},{1},{2},{3}".format(data.get('N'),data.get('k'),data.get('chi'),data.get('label')))
            # Check if we add something which was not in the database
            self.__dict__.update(data)
            self.insert_into_db()
        else:
            data = {}

        # Set defaults.
        d  = {
            '_chi' : int(chi),'_k' : int(k),'_N' : int(N),
            '_label' : str(label), '_fi':None,
            '_prec' : int(prec), '_bitprec' : int(bitprec),
            '_display_bprec':int(display_bprec),
            '_verbose' : int(verbose),
            '_satake' : {},
            '_ap' : {},    # List of Hecke eigenvalues (can be long)
            '_coefficients' : dict(),  # list of Fourier coefficients (should not be long)
            '_atkin_lehner_eigenvalues' : {},
            '_parent' : parent,
            '_f' : None,
            '_q_expansion' : None,
            '_q_expansion_str' : '',
            '_embeddings' :
                {
                'prec':0,
                'bitprec':bitprec,
                'values':[],
                'latex':[]},
            '_base_ring': None,
            '_base_ring_as_dict' : {},
            '_coefficient_field': None,
            '_coefficient_field_as_dict': {},
            '_as_polynomial_in_E4_and_E6' : None,
            '_twist_info' : [],
            '_is_CM' : [],
            '_cm_values' : {},
            '_satake' : {},
            '_dimension' : None,
            '_is_rational' : None,
            '_degree' : None,
            '_absolute_degree' : None,
            '_relative_degree' : None,
            '_character' : None,
            '_character_naming_scheme' : 'Conrey', # To make it clear in case someone simply looks at a dictionary.
            '_name' : "{0}.{1}.{2}{3}".format(N,k,chi,label),
            '_sturm_bound' : None,
            '_newform_number':None
            '_version': float(emf_version)            
            }
        self.__dict__.update(d)
        emf_logger.debug("label = {0}".format(self._label))
        emf_logger.debug("d = {0}".format(d))

        # Fetch data
        if self._label<>'' and get_from_db:            
            d = self.get_from_db(self._N, self._k, self._chi, self._label)
            emf_logger.debug("Got data in WebNewForm: {0} from db".format(d))
            self.__dict__.update(d)

        if parent is not None:
            # we have to do that again
            # otherwise we run into an infinite loop
            # of fetching from the DB
            self._parent = parent
        if not isinstance(self._parent,WebModFormSpace_class):
            emf_logger.debug("getting parent! label={0}".format(label))
            self._parent = WebModFormSpace(N, k,chi, data=self._parent,get_from_db=get_from_db)
            emf_logger.debug("finished getting parent")                
            
        if self._parent.dimension_newspace()==0:
            self._dimension=0
            return
        # What?
        if get_from_db:
            self._check_consistency_of_labels()
        emf_logger.debug("name={0}".format(self._name))
        emf_logger.debug("done __init__")

### Get basic properties of self
    
    def level(self):
        r"""
        The level of self (assuming it is on a congruence subgroup).
        """
        return self._N

    
    def ambient_space(self):
        r"""
        The group on which self is defined.
        """
        return self.parent()

    
    def group(self):
        r"""
        The group on which self is defined.
        """
        return self.parent().group()

    
    def label(self):
        r"""
        The label of self.
        """
        return self._label

    
    def chi(self):
        r"""
        Return the number of the character of self (in the Conrey ordering/naming scheme)
        """
        return self._chi

    
    def weight(self):
        r"""
        The weight of self.
        """
        return self._k

    
    def name(self):
        r"""
        The name, or *complete* label, of self.
        """
        return self._name
    
    
    def character(self):
        r"""
        Return the character of self.
        """
        if self._character is None:
            self._character = WebChar(modulus=self.level(),number=self.chi())
        return self._character

    def newform_number(self):
        r"""
        The number of self in the Galois orbits of self.parent()
        """
        if self._newform_number is None:
            if self._label not in self.parent().labels():
                raise ValueError,"Self (with label {0}) is not in the set of Galois orbits of self.parent()!".format(self._label)
            self._newform_number = self.parent().labels().index(self._label)
        return self._newform_number

    def prec(self):
        r"""
        Return the precision of self.
        """
        return self._prec
                     
## Functions related to storing / fetching data from database
##  
    def to_dict(self):
        r"""
        Export self as a serializable dictionary.
        """
        if self._base_ring_as_dict == {} and self.base_ring() is not None:
            self._base_ring_as_dict = number_field_to_dict(self.base_ring())
        if self._coefficient_field_as_dict == {}:
            self._coefficient_field_as_dict = number_field_to_dict(self.coefficient_field())
        data = {}
        for k in self.__dict__:
            data[k]=self.__dict__[k]
        ## Get rid of non-serializable objects.
        for k in ['_f','_character','_base_ring','_coefficient_field','_conrey_character']:
            data.pop(k,None)
        data['_parent']=self._parent.to_dict()
        return data

    def _from_dict(self, data):
        self.__dict__.update(data)
        if isinstance(self._parent,dict):
            self._parent = WebModFormSpace(self._k,self._N,self._chi,1,self._prec,self._bitprec,data = self._parent)

    def to_yaml(self,for_yaml=False):
        r"""
        Export self in yaml format
        """
        d = self.to_dict()
        return yaml.dump(d)
    
    def from_yaml(self,s):        
        r"""
        Import data from a yaml formatted string
        """

        d = yaml.load(s)
        return yaml.load(d)    
    
    def get_from_db(self,N,k,chi,label):
        r"""
        Fetch dictionary from the database
        """
        C = connect_to_modularforms_db()
        s = {'name':self.name(),'version':float(emf_version)}
        emf_logger.debug("Looking in DB for rec={0}".format(s))
        f = C.WebNewforms.files.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = get_files_from_gridfs('WebNewforms')
            f = fs.get(id)
            emf_logger.debug("Getting rec={0}".format(f))
            d = loads(f.read())
            return d
        return {}
    
    def insert_into_db(self):
        r"""
        Insert a dictionary of data for self into the database collection
        WebNewforms.files
        """
        emf_logger.debug("inserting self into db! name={0}".format(self._name))
        C = connect_to_modularforms_db('WebNewForms.files')
        fs = get_files_from_gridfs('WebNewforms')
        s = {'name':self._name,'version':float(self._version)}
        rec = C.find_one(s)
        if rec:
            id = rec.get('_id')
        else:
            id = None
        if id<>None:
            emf_logger.debug("Removing self from db with id={0}".format(id))
            fs.delete(id)
            
        fname = "webnewform-{0:0>5}-{1:0>3}-{2:0>3}-{3}".format(self._N,self._k,self._chi,self._label) 
        d = self.to_dict()
        d.pop('_ap',None)
        ## The ap's are already stored in this format in the database
        ## so we don't store them here again.
        id = fs.put(dumps(d),filename=fname,N=int(self._N),k=int(self._k),chi=int(self._chi),label=self._label,name=self._name,version=float(self._version))
#        except Exception as e:
#            emf_logger.critical("DB insertion failed: {0}".format(e.message))
        emf_logger.debug("inserted :{0}".format(id))
    
    

            

##  Internal functions
##        
    def _check_consistency_of_labels(self):
        if self._label not in self.parent().labels():
            raise ValueError,"There does not exist a newform orbit of the given label: {0}!".format(self._label)
        return True

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self._name == other._name


    def __repr__(self):
        r""" String representation f self.
        """
        if self.dimension()==0:
            return "0"
        return str(self.q_expansion())

    def __reduce__(self):
        r"""
        Reduce self for pickling.
        """
        data = self.to_dict()
        return(unpickle_wnf_v1, (self._N, self._k, self._chi, self._label,
                                 self._prec, self._bitprec, self._display_bprec,self._parent,data))

    
    def base_ring(self):
        r"""
        The base ring of self, that is, the field of values of the character of self. 
        """
        if isinstance(self._base_ring,NumberField_class):
            return self._base_ring
        if self._base_ring_as_dict<>{}:
            emf_logger.debug("base_ring={0}".format(self._base_ring_as_dict))
            self._base_ring = number_field_from_dict(self._base_ring_as_dict)
        #if self._base_ring is None:
        #    self._base_ring = self.as_factor().base_ring()
        return self._base_ring

    
    def coefficient_field(self):
        r"""
        The coefficient field of self, that is, the field generated by the Fourier coefficients of self.
        """
        emf_logger.debug("coef_fld={0}".format(self._coefficient_field))
        if isinstance(self._coefficient_field,NumberField_class):
            return self._coefficient_field
        if self._coefficient_field_as_dict<>{}:
            emf_logger.debug("coef_fldas_d={0}".format(self._coefficient_field_as_dict))
            return number_field_from_dict(self._coefficient_field_as_dict)
        ## Get field from the ap's # Necessary because change in sage implementation
        self._update_aps()
        try:
            self._coefficient_field = self._ap[2].parent()
        except KeyError:
            emf_logger.debug("Cannot determine coefficient_field")
            self._coefficient_field = None
        emf_logger.debug("coef_field={0}".format(self._coefficient_field))
        return self._coefficient_field

    
    def coefficient_field_disc(self):
        if self._coefficient_field is not None:
            return self._coefficient_field.disc()

    
    def relative_degree(self):
        r"""
        Degree of the field of coefficient relative to its base ring.
        """
        if self._relative_degree is None:
            if self._coefficient_field() is not None:
                self._relative_degree = self.coefficient_field().absolute_degree()/self.base_ring().absolute_degree()
        return self._relative_degree

    
    def degree(self):
        return self.absolute_degree()

    
    def absolute_degree(self):
        r"""
        Degree of the field of coefficient relative to its base ring.
        """
        if self._absolute_degree is None:
            if not self.coefficient_field() is None:
                self._absolute_degree = self.coefficient_field().absolute_degree()
        return self._absolute_degree
        
    
    def parent(self):
        from web_modform_space import WebModFormSpace_class, WebModFormSpace
        if not isinstance(self._parent,WebModFormSpace_class):
            if self._verbose > 0:
                emf_logger.debug("compute parent! label={0}".format(label))
            self._parent = WebModFormSpace(self._N, sel.f_k,self._chi, data=self._parent)
        return self._parent

    
    def is_rational(self):
        if self._is_rational is None:
            if self.coefficient_field().degree()==1:
                self._is_rational  = True
            else:
                self._is_rational = False
        return self._is_rational

    
    def dimension(self):
        r"""
        Return the dimension of the intersection of the galois orbit corresponding to ```self```
        and the surrounding space.
        
        NOTE:
        The dimension returned is not necessarily equal to the degree of the number field
        when we have a character!
        """
        return self._dimension

    def q_expansion_embeddings(self, prec=10, bitprec=53,format='numeric',display_bprec=26,insert_in_db=True):
        if format=='latex':
            return self._embeddings['latex']
        else:
            return self._embeddings['values']
            
    def _q_expansion_embeddings(self, prec=10, bitprec=53,format='numeric',display_bprec=26,insert_in_db=True):
        r""" Compute all embeddings of self into C which are in the same space as self.
        Return 0 if we didn't compute anything new, otherwise return 1.
        """
        emf_logger.debug("computing embeddings of q-expansions : has {0} embedded coeffs. Want : {1} with bitprec={2}".format(len(self._embeddings),prec,bitprec))
        if display_bprec > bitprec:
            display_bprec = bitprec
        ## First check if we have sufficient data
        if self._embeddings['prec'] >= prec or self._embeddings['bitprec'] >= bitprec:
            return 0 ## We should already have sufficient data.
        ## Else we compute new embeddings.
        CF = ComplexField(bitprec)
        # First wee if we need higher precision, in which case we reset all coefficients:
        if self._embeddings['bitprec'] < bitprec:
            self._embeddings['values']=[]
            self._embeddings['latex']=[]
            self._embeddings['prec']=0
        # See if we have need of more coefficients
        nstart = len(self._embeddings)
        emf_logger.debug("Should have {0} embeddings".format(self._embeddings['prec']))
        emf_logger.debug("Computing new stuff !")
        for n in range(self._embeddings['prec'],prec):
            try:
                cn = self.coefficient(n)
            except IndexError:
                break
            if hasattr(cn, 'complex_embeddings'):
                cn_emb = cn.complex_embeddings(bitprec)
            else:
                cn_emb = [ CF(cn) for i in range(deg) ]
            self._embeddings['values'].append(cn_emb)
        self._embeddings['prec'] = len(self._embeddings['values'])
        # See if we also need to recompute the latex strings
        if display_bprec > self._embeddings['bitprec']:
            self._embeddings['latex'] = []  ## Have to redo these
        numc = len(self._embeddidngs['latex'])
        for n in range(numc,prec):
            cn_emb = []
            for x in self._embeddings['values'][n]:
                t = my_complex_latex(x,display_bprec)
            cn_emb_latex.append(t)
            self._embeddidngs['latex'].append(cn_emb)
        emf_logger.debug("has embeddings_latex:{0}".format(nstart))
        return 1

    
    def is_cuspidal(self):
        return 1

    def coefficient(self, n,insert_in_db=False):
        r"""
        Return coefficient nr. n
        """
        emf_logger.debug("In coefficient: n={0}".format(n))
        if n==0:
            if self.is_cuspidal():
                return self.coefficient_field()(0)
        c = self._coefficients.get(n,None)
        if c is None:
            c = self.coefficients([n],insert_in_db)[0] 
        return c


    def coefficients(self, nrange=range(1, 10),insert_in_db=True):
        r"""
        Gives the coefficients in a range.
        We assume that the self._ap containing Hecke eigenvalues
        are stored.

        """
        emf_logger.debug("computing coeffs in range {0}".format(nrange))
        if not isinstance(nrange, list):
            M = nrange
            nrange = range(0, M)
        res = []
        recompute = False
        for n in nrange:
            c = self._coefficients.get(n,None)
            emf_logger.debug("c({0}) in self._coefficients={1}".format(n,c))            
            if c is None:
                if n == 0 and self.is_cuspidal():
                    c = self.coefficient_field()(0)
                else:
                    recompute = True
                    c = self.coefficient_n_recursive(n,insert_in_db)
                    self._coefficients[n]=c
            res.append(c)
        if recompute and insert_in_db:
            self.insert_into_db()
        return res
       
    def coefficient_n_recursive(self,n,insert_in_db=False):
        r"""
        Reimplement the recursive algorithm in sage modular/hecke/module.py
        We do this because of a bug in sage with .eigenvalue()
        """
        from sage.rings import arith
        emf_logger.debug("computing c({0}) using recursive algortithm".format(n))
        if n==1:
            return 1
        F = arith.factor(n)
        prod = None
        if self._ap is None or self._ap == {}:
            self._update_aps()
            if self._ap == {}:
               raise IndexError,"Have no coefficients!"
        ev = self._ap
        K = self._ap[2].parent()
        for p, r in F:
            (p, r) = (int(p), int(r))
            pr = p**r
            if not ev.has_key(p):
                # Here the question is whether we start computing or only use from database...
                raise ValueError,"p={0} is outside the range of computed primes (primes up to {1})!".format(p,max(ev.keys()))
            if not ev.has_key(pr):  # and ev[pow].has_key(name)):
                # TODO: Optimization -- do something much more
                # intelligent in case character is not defined.  For
                # example, compute it using the diamond operators <d>
                eps = K(self.character().value(p))
                # a_{p^r} := a_p * a_{p^{r-1}} - eps(p)p^{k-1} a_{p^{r-2}}
                apr1 = self.coefficient_n_recursive(pr//p)
                ap = self.coefficient_n_recursive(p)
                k = self.weight()
                apr2 = self.coefficient_n_recursive(pr//(p*p))
                apow = ap*apr1 - eps*(p**(k-1)) * apr2
                ev[pr]=apow
                if self._verbose>1:
                    print "eps=",eps
                    print "a[",pr//p,"]=",apr1
                    print "a[",pr//(p*p),"]=",apr2                
                    print "a[",pr,"]=",apow                
                    print "a[",p,"]=",ap
                # _dict_set(ev, pow, name, apow)
            if prod is None:
                prod = ev[pr]
            else:
                prod *= ev[pr]
        if insert_in_db:
            self.insert_into_db()
        return prod

    
    def max_cn(self):
        r"""
        The largest N for which we are sure that we can compute a(n) for all 1<=n<=N
        """
        if self._ap.keys()==[]:
            return 1
        return max(self._ap.keys())+1
    
    def _update_aps(self,maxp_needed=None,insert_in_db=True):        
        r"""
        Update ap's from parent ambient.
        Return 1 if we have computed / fetched something, else 0
        """
        emf_logger.debug("before update self_ap={0}".format(self._ap))
        aps = self._ap
        ambient_aps = self.parent().aps().get(self.label(),{})
        if ambient_aps == {}:
            return 0 
        if self._ap <> {} and max(ambient_aps.keys())<=max(self._ap.keys()):
            return 0
        # Otherwise we can get something new. Let's take the appripriate file
        l=ambient_aps.keys(); l.sort()
        if maxp_needed <> None:
            for i in l:
                if i>=maxp_needed: # This set of coefficients should be ok.
                    break
        else:
            i = max(l)
        ambient_aps = ambient_aps[i]
        emf_logger.debug("i={0}".format(i))
        emf_logger.debug("ambient_aps={0}".format(ambient_aps))
        try:
            E, v = ambient_aps
            if len(aps) < E.rows(): # We have more to update with
                c = E*v
                lc = len(c)
                for i in range(len(c)):
                    p = primes_first_n(lc)[i]
                    aps[p] = c[i]
                emf_logger.debug("after update self_ap={0}".format(self._ap))
                if insert_in_db:
                    self.insert_into_db()
        except Exception as e:
            emf_logger.debug("Could not update ap's from {0}. Error: {1}".format(ambient_aps,e.message))
            pass
        return 1
 
                          
    def q_expansion(self, prec=None):
        r"""
        Return the q-expansion of self to precision prec.
        """
        if prec is None:
            prec = self._prec

        if not isinstance(self._q_expansion,PowerSeries_poly):
            q_expansion = ''
            if self._q_expansion_str<>'':
                R = PowerSeriesRing(self.coefficient_field(), 'q')
                q_expansion = R(self._q_expansion_str)
                if q_expansion.degree() >= self.prec() - 1: 
                    q_expansion = q_expansion.add_bigoh(prec)
            if q_expansion == '':
                self._q_expansion_str = ''
            else:
                self._q_expansion_str = str(q_expansion.polynomial())   
            self._q_expansion = q_expansion
        if not self._q_expansion == '':
            if self._q_expansion.prec() <= prec:
                return self._q_expansion
            elif self._q_expansion.prec() > prec:
                return self._q_expansion.truncate_powerseries(prec)
        return self._q_expansion

    def atkin_lehner_eigenvalue(self, Q):
        r""" Return the Atkin-Lehner eigenvalues of self
        corresponding to Q|N
        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return None
        
        l = self.atkin_lehner_eigenvalues()
        return l.get(Q)

    
    def atkin_lehner_eigenvalues(self):
        r""" Return the Atkin-Lehner eigenvalues of self.

           EXAMPLES::

           sage: get_atkin_lehner_eigenvalues(4,14,0)
           '{2: 1, 14: 1, 7: 1}'
           sage: get_atkin_lehner_eigenvalues(4,14,1)
           '{2: -1, 14: 1, 7: -1}'


        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return None
        
        if(len(self._atkin_lehner_eigenvalues.keys()) > 0):
            return self._atkin_lehner_eigenvalues

    
    def is_minimal(self):
        r"""
        Returns True if self is a twist and otherwise False.
        """
        if isinstance(self.twist_info(), list):
            if len(self.twist_info()) == 2:
                [t, f] = self.twist_info()
                if(t):
                    return True
                elif(t == False):
                    return False
        else:
            return "Unknown"

    def twist_info(self, prec=10,insert_in_db=True):
        r"""
        Try to find forms of lower level which get twisted into self.
        OUTPUT:

        -''[t,l]'' -- tuple of a Bool t and a list l. The list l contains all tuples of forms which twists to the given form.
        The actual minimal one is the first element of this list.
             t is set to True if self is minimal and False otherwise


        EXAMPLES::

        """
        return self._twist_info

    
    def is_CM(self):
        r"""
        Returns if f has complex multiplication and if it has then it returns the character.

        OUTPUT:

        -''[t,x]'' -- string saying whether f is CM or not and if it is, the corresponding character

        EXAMPLES::

        """
        return self._is_CM


    
    def exact_cm_at_i_level_1(self, N=10):
        r"""
        Use formula by Zagier (taken from pari implementation by H. Cohen) to compute the geodesic expansion of self at i
        and evaluate the constant term.

        INPUT:
        -''N'' -- integer, the length of the expansion to use.
        """
        raise NotImplementedError

    
    def cm_values(self):
        r""" Returns a list of values of f at a collection of CM points as complex floating point numbers.

        INPUT:

        -''digits'' -- we want this number of corrrect digits in the value

        OUTPUT:
        -''s'' string representation of a dictionary {I:f(I):rho:f(rho)}.

        TODO: Get explicit, algebraic values if possible!
        """
        return self._cm_values

    
    def satake_parameters(self):
        r""" Return an html-table containing the Satake parameters.

        We only do satake parameters for primes p primitive to the level.
        By defintion the S. parameters are given as the roots of
         X^2 - c(p)X + chi(p)*p^(k-1) if (p,N)=1

        INPUT:
        -''prec'' -- compute parameters for p <=prec
        -''bits'' -- do real embedings intoi field of bits precision

        """
        if self.character().order()>2:
            ## We only implement this for trival or quadratic characters.
            ## Otherwise there is difficulty to figure out what the embeddings mean... 
            return 
        return self._satake

    
    def as_polynomial_in_E4_and_E6(self):
        return self._as_polynomial_in_E4_and_E6

    
    def sturm_bound(self):
        return self._sturm_bound

    
    def url(self):
        return url_for('emf.render_elliptic_modular_forms', level=self.level(), weight=self.weight(), character=self.chi(), label=self.label())

    def _number_of_hecke_eigenvalues_to_check(self):
        r""" Compute the number of Hecke eigenvalues (at primes) we need to check to identify twists of our given form with characters of conductor dividing the level.
        """
        ## initial bound
        bd = self.as_factor().sturm_bound()
        # we do not check primes dividing the level
        bd = bd + len(divisors(self.level()))
        return bd

    ## printing functions
    def print_q_expansion(self, prec=None, br=0):
        r"""
        Print the q-expansion of self.

        INPUT:

        OUTPUT:

        - ''s'' string giving the coefficients of f as polynomals in x

        EXAMPLES::


        """
        if prec is None:
            prec = self._prec
        emf_logger.debug("PREC2: {0}".format(prec))
        s = my_latex_from_qexp(str(self.q_expansion(prec)))
        emf_logger.debug("q-exp-str: {0}".format(s))        
        sb = list()
        if br > 0:
            sb = break_line_at(s, br)
            emf_logger.debug("print_q_exp: sb={0}".format(sb))
        if len(sb) <= 1:
            s = r"\(" + s + r"\)"
        else:
            s = r"\[\begin{align} &" + join(sb, "\cr &") + r"\end{align}\]"
            
        emf_logger.debug("print_q_exp: prec=".format(prec))
        
        return s

    def print_q_expansion_embeddings(self, prec=10, bprec=53):
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
        coeffs = self.q_expansion_embeddings(prec, bprec)
        if isinstance(coeffs, str):
            return coeffs  # we probably failed to compute the form
        # make a table of the coefficients
        emf_logger.debug("print_embeddings: prec={0} bprec={1} coefs={0}".format(prec, bprec, coeffs))
        tbl = dict()
        tbl['atts'] = "border=\"1\""
        tbl['headersh'] = list()
        for n in range(len(coeffs) - 1):
            tbl['headersh'].append("\(" + str(n + 1) + "\)")
        tbl['headersv'] = list()
        tbl['data'] = list()
        tbl['corner_label'] = "\( Embedding \, \\backslash \, n \)"
        for i in range(len(coeffs[0])):
            tbl['headersv'].append("\(v_{%s}(a(n)) \)" % i)
            row = list()
            emf_logger.debug("len={0}".format(len(coeffs)))
            for n in range(len(coeffs) - 1):
                emf_logger.debug("n={0}".format(n))
                if i < len(coeffs[n]):
                    emf_logger.debug("i={0} {1}".format(i, coeffs[n + 1][i].n(self._display_bprec)))
                    row.append(coeffs[n + 1][i].n(self._display_bprec))
                else:
                    row.append("")
            tbl['data'].append(row)

        s = html_table(tbl)
        return s
    
    
    def polynomial(self, type='base_ring',format='latex'):
        r"""
        Return a formatted string representation of the defining polynomial of either the base ring or the coefficient ring of self.
        """
        if type == 'base_ring':
            if self.base_ring() is None:
                return None
            if self._base_ring_as_dict == {}:
                self._base_ring_as_dict  = number_field_to_dict(self.base_ring())
            p = self._base_ring_as_dict['relative polynomial']
        else:
            if self._coefficient_field_as_dict=={}:
                self._coefficient_field_as_dict  = number_field_to_dict(self.coefficient_field())
            p = self._coefficient_field_as_dict['relative polynomial']
        if format == 'latex':
            p = pol_to_latex(p)
        elif format == 'html':
            p = pol_to_html(p)
        return p

    def number_field_label(self, pretty = True):
        r"""
          Returns the LMFDB label of the oefficient field.
        """
        p = self.polynomial() 
        if p is None:
            l = poly_to_field_label('x')
        else:
            l = poly_to_field_label(p)
        if l == "1.1.1.1" and pretty:
            return "\( \Q \)"
        else:
            return l

    def number_field_url(self):
        return url_for("number_fields.by_label", label=self.number_field_label(pretty = False))

###
### Independent helper functions
###


def my_latex_from_qexp(s):
    r"""
    Make LaTeX from string. in particular from parts of q-expansions.
    """
    ss = ""
    ss += re.sub('x\d', 'x', s)
    ss = re.sub("\^(\d+)", "^{\\1}", ss)
    ss = re.sub('\*', '', ss)
    ss = re.sub('zeta(\d+)', 'zeta_{\\1}', ss)
    ss = re.sub('zeta', '\zeta', ss)
    ss += ""
    # emf_logger.debug("ss=",ss
    return ss


def break_line_at(s, brpt=20):
    r"""
    Breaks a line containing math 'smartly' at brpt characters.
    With smartly we mean that we break at + or - but keep brackets
    together
    """
    sl = list()
    stmp = ''
    left_par = 0
    #emf_logger.debug('Break at line, Input ={0}'.format(s))
    for i in range(len(s)):
        if s[i] == '(':  # go to the matching case
            left_par = 1
        elif s[i] == ')' and left_par == 1:
            left_par = 0
        if left_par == 0 and (s[i] == '+' or s[i] == '-'):
            sl.append(stmp)
            stmp = ''
        stmp = stmp + s[i]
        if i == len(s) - 1:
            sl.append(stmp)
    emf_logger.debug('sl={0}'.format(sl))

    # sl now contains a split  e.g. into terms in the q-expansion
    # we now have to join as many as fits on the line
    res = list()
    stmp = ''
    for j in range(len(sl)):
        l = len_as_printed(stmp) + len_as_printed(sl[j])
        #emf_logger.debug("l={0}".format(l))
        if l < brpt:
            stmp = join([stmp, sl[j]])
        else:
            res.append(stmp)
            stmp = sl[j]
        if j == len(sl) - 1:
            res.append(stmp)
    return res


def _degree(K):
    r"""
    Returns the degree of the number field K
    """
    return K.absolute_degree()


def unpickle_wnf_v1(N, k,chi, label, fi, prec, bitprec, display_bprec,parent,data):
    F = WebNewForm(N=N,k=k, chi=chi, label=label, fi=fi, prec=prec, bitprec=bitprec, display_bprec=display_bprec,parent=parent, data=data)
    return F


def unpickle_wmfs_v1(N, k,chi, cuspidal, prec, bitprec, data):
    M = WebModFormSpace(N=N, k=k, chi=chi, cuspidal=cuspidal, prec=prec, bitprec=bitprec, data=data)
    return M


def pol_to_html(p):
    r"""
    Convert polynomial p to html.
    """
    s = str(p)
    s = re.sub("\^(\d*)", "<sup>\\1</sup>", s)
    s = re.sub("\_(\d*)", "<sub>\\1</sub>", s)
    s = re.sub("\*", "", s)
    s = re.subst("x", "<i>x</i>", s)
    return s

def pol_to_latex(p):
    r"""
    Convert polynomial in string format to latex.
    """
    s = str(p)
    s = re.sub("\^(\d*)", "^{\\1}", s)
    s = re.sub("\_(\d*)", "_{\\1}", s)
    s = re.sub("\*", "", s)
    s = re.sub("zeta(\d+)", "\zeta_{\\1}", s)
    return s


## Added routines to replace sage routines with bugs for level 1
##
def my_hecke_images(AA, i, v):
    # Use slow generic algorithm
    x = AA.gen(i)
    X = [AA.hecke_operator(n).apply_sparse(x).element() for n in v]
    return matrix(AA.base_ring(), X)

def number_field_to_dict(F):

    r"""
    INPUT:
    - 'K' -- Number Field
    - 't' -- (p,gens) where p is a polynomial in the variable(s) xN with coefficients in K. (The 'x' is just a convention)

    OUTPUT:

    - 'F' -- Number field extending K with relative minimal polynomial p.
    """
    if F.base_ring().absolute_degree()==1:
        K = 'QQ'
    else:
        K = number_field_to_dict(F.base_ring())
    if F.absolute_degree() == 1:
        p = 'x'
        g = ('x',)
    else:
        p = F.relative_polynomial()
        g = str(F.gen())
        x = p.variables()[0]
        p = str(p).replace(str(x),str(g))
    return {'base':K,'relative polynomial':p,'gens':g}


def number_field_from_dict(d):
    r"""
    INPUT:

    - 'd' -- {'base':F,'p':p,'g':g } where p is a polynomial in the variable(s) xN with coefficients in K. (The 'x' is just a convention)

    OUTPUT:

    - 'F' -- Number field extending K with relative minimal polynomial p.
    """
    K = d['base']; p=d['relative polynomial']; g=d['gens']
    if K=='QQ':
        K = QQ
    elif isinstance(K,dict):
        K = number_field_from_dict(K)
    else:
        raise ValueError,"Could not construct number field!"
    F = NumberField(K[g](p),names=g)
    if F.absolute_degree()==1:
        F = QQ
    return F

def my_complex_latex(c,bitprec):
    x = c.real().n(bitprec)
    y = c.imag().n(bitprec)
    d = floor(bitprec/3.4)
    if x >= 0:
        prefx = "\\hphantom{-}"
    else:
        prefx = ""
    if y < 0:
        prefy = ""
    else:
        prefy = "+"
    xi,xf = str(x).split(".")
    xstr = "{0}.{1:0<{d}}".format(xi,xf,d=d)
    #print "xstr=",xstr
    yi,yf = str(y).split(".")
    ystr = "{0}.{1:0<{d}}".format(yi,yf,d=d)
    t = "{prefx}{x}{prefy}{y}i".format(prefx=prefx,x=xstr,prefy=prefy,y=ystr)
    return t
#     d = 
#     if y ==0:
#         return "{0:.df}
        
    
