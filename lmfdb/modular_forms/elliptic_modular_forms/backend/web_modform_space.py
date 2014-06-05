# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010
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


NOTE: Now NOTHING should be computed.
 """

from sage.all import ZZ, QQ, DirichletGroup, CuspForms, Gamma0, ModularSymbols, Newforms, trivial_character, is_squarefree, divisors, RealField, ComplexField, prime_range, I, join, gcd, Cusp, Infinity, ceil, CyclotomicField, exp, pi, primes_first_n, euler_phi, RR, prime_divisors, Integer, matrix,NumberField,PowerSeriesRing
from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import Parent, SageObject, dimension_new_cusp_forms, vector, dimension_modular_forms, dimension_cusp_forms, EisensteinForms, Matrix, floor, denominator, latex, is_prime, prime_pi, next_prime, previous_prime,primes_first_n, previous_prime, factor, loads,save,dumps,deepcopy
import re
import yaml
from flask import url_for

from lmfdb.modular_forms.elliptic_modular_forms import emf_logger,emf_version
from emf_core import html_table, len_as_printed

from sage.rings.number_field.number_field_base import NumberField as NumberField_class
from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db,get_files_from_gridfs
from web_character import WebChar

def WebModFormSpace(N=1, k=2, chi=1, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,**kwds):
    r"""
    Constructor for WebNewForms with added 'nicer' error message.
    """
    if cuspidal <> 1:
        raise IndexError,"We are very sorry. There are only cuspidal spaces currently in the database!"
    #try: 
    F = WebModFormSpace_class(N=N, k=k, chi=chi, cuspidal=cuspidal, prec=prec, bitprec=bitprec, data=data, verbose=verbose,**kwds)
    #except Exception as e:
    #    emf_logger.critical("Could not construct WebModFormSpace with N,k,chi = {0}. Error: {1}".format( (N,k,chi),e.message))
    #    #raise e
    #    #raise IndexError,"We are very sorry. The sought space could not be found in the database."
    return F


class WebModFormSpace_class(object):
    r"""
    Space of cuspforms to be presented on the web.
        G  = NS.

    EXAMPLES::

    sage: WS=WebModFormSpace(2,39)


    """
    def __init__(self, N=1, k=2, chi=1, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,
                 get_from_db=True, get_all_newforms_from_db = False):
        r"""
        Init the WebModFormSpace.

        INPUT:
        - 'k' -- weight
        - 'N' -- level
        - 'chi' -- character
        - 'cuspidal' -- 1 if space of cuspforms, 0 if all modforms
        """
        from web_modforms import WebNewForm
        
        if data is None: data = {}
        emf_logger.debug("WebModFormSpace with k,N,chi={0}".format( (k,N,chi)))
        d = {
            '_N': int(N),
            '_k': int(k),
            '_chi':int(chi),
            '_cuspidal' : int(cuspidal),
            '_prec' : int(prec),
            '_ap' : {}, '_group' : None,
            '_character' : None,
            '_character_orbit_rep' : None,
            '_modular_symbols' : None,
            '_sturm_bound' : None,
            '_newspace' : None,
            '_newforms' : {},
            '_new_modular_symbols' : None,
            '_galois_decomposition' : [],
            '_galois_orbits_labels' : [],
            '_oldspace_decomposition' : [],
            '_newform_factors' : None,
            '_verbose' : int(verbose),
            '_bitprec' : int(bitprec),
            '_dimension_newspace' : None,
            '_dimension_cusp_forms' : None,
            '_dimension_modular_forms' : None,
            '_dimension_new_cusp_forms' : None,
            '_dimension_new_modular_symbols' : None,
            '_newspace' : None,
            '_name' : "{0}.{1}.{2}".format(N,k,chi),
            '_got_ap_from_db' : False,
            '_version': float(emf_version),
            '_galois_orbit_poly_info':{}
            }
        self.__dict__.update(d)
        #data.update(d)
        emf_logger.debug("Incoming data:{0} ".format(data))
        if get_from_db:
           d = self.get_from_db()
           emf_logger.debug("Got data:{0} from db".format(d))
           if d == {}:
               raise ValueError,"The form is not in the database!"
        else:
           d = {}
        if data is None:
            data = {}
        data.update(d)        
        self.__dict__.update(data)
        if get_all_newforms_from_db:
            self._get_aps()
            for l in self.labels():
                self._newforms[l] = WebNewForm(N=self._N, k=self._k,  chi=self._chi, parent=self, label=l)

    ### Return elementary properties of self.
    def weight(self):
        r"""
        The weight of self.
        """
        return self._k

    def level(self):
        r"""
        The level of self.
        """
        return self._N

    def chi(self):
        r"""
        Return the character number (chi) of self.
        """
        return self._chi
    
    def character(self):
        r"""
        Return the character of self.
        """
        if self._character is None:
            self._character = WebChar(self.level(),self.chi())
        return self._character
    
    def group(self):
        r"""
        The group of self.
        """
        return self._group

    def aps(self,prec=-1):
        r"""
        Return a list of aps, that is, Hecke eigenvalues of prime indices, for self.
        """
        return self._ap

    def newform_factors(self):
        r"""
        Return newform factors of self.
        """
        return self._newform_factors

    def newforms(self):
        return self._newforms
                            
    def character_orbit_rep(self,k=None):
        r"""
        Returns canonical representative of the Galois orbit nr. k acting on the ambient space of self.

        """
        return self._character_orbit_rep

    def to_dict(self):
        r"""
        Makes a dictionary of the serializable properties of self.
        """
        problematic_keys = ['_galois_decomposition',
                            '_newforms','_newspace',
                            '_modular_symbols',
                            '_new_modular_symbols',
                            '_galois_decomposition',
                            '_oldspace_decomposition',
                            '_conrey_character',
                            '_character',
                            '_group']
        data = {}
        data.update(self.__dict__)
        for k in problematic_keys:
            data.pop(k,None)
        return data
    
    ## Database fetching functions.
            
    def get_from_db(self):
        r"""
        Fetch data from the database.
        """
        db = connect_to_modularforms_db('WebModformspace.files')
        s = {'name':self._name,'version':emf_version}
        emf_logger.debug("Looking in DB for rec={0}".format(s))
        f = db.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = get_files_from_gridfs('WebModformspace')
            f = fs.get(id)
            emf_logger.debug("Getting rec={0}".format(f))
            d = loads(f.read())
            return d
        return {}

    def _get_aps(self, prec=-1):
        r"""
        Get aps from database if they exist.
        """
        ap_files = connect_to_modularforms_db('ap.files')
        key = {'k': int(self._k), 'N': int(self._N), 'cchi': int(self._chi)}
        key['prec'] = {"$gt": int(prec - 1)}
        ap_from_db  = ap_files.find(key).sort("prec")
        emf_logger.debug("finds={0}".format(ap_from_db))
        emf_logger.debug("finds.count()={0}".format(ap_from_db.count()))
        fs = get_files_from_gridfs('ap')
        aplist = {}
        for i in range(len(self.labels())):
            aplist[self.labels()[i]]={}
        for rec in ap_from_db:
            emf_logger.debug("rec={0}".format(rec))
            ni = rec.get('newform')
            if ni is None:
                for a in self.labels():
                    aplist[a][prec]=None
                return aplist
            a = self.labels()[ni]
            cur_prec = rec['prec']
            if aplist.get(a,{}).get(cur_prec,None) is None:
                aplist[a][prec]=loads(fs.get(rec['_id']).read())
            if cur_prec > prec and prec>0: # We are happy with these coefficients.
                return aplist
        self._ap = aplist
        return aplist  
             
    def __repr__(self):
        r"""
        Return string representation of self.
        """
        
        if self.character().is_trivial():
            s = 'Space of Cusp forms on Gamma0({0}) of weight {1}'.format(self.level(),self.weight())
        else:
            s = 'Space of Cusp forms on Gamma0({0}) of weight {1} and character no. {2}'.format(self.level(),self.weight(),self.chi())
        
#        s += ' and dimension ' + str(self.dimension())
        return s


    def galois_orbit_label(self, j):
        r"""
        Return the label of the Galois orbit nr. j
        """
        return self._galois_orbits_labels[j]

    ###  Dimension formulas, calculates dimensions of subspaces of self.
    def is_cuspidal(self):
        return self._cuspidal == 1
    
    def dimension_newspace(self):
        r"""
        The dimension of the subspace of newforms in self.
        """
        return self._dimension_newspace

    def dimension_oldspace(self):
        r"""
        The dimension of the subspace of oldforms in self.
        """
        if self.is_cuspidal():
            return self.dimension_cusp_forms() - self.dimension_new_cusp_forms()
        return self.dimension_modular_forms() - self.dimension_newspace()

    def dimension_cusp_forms(self):
        r"""
        The dimension of the subspace of cuspforms in self.
        """
        return self._dimension_cusp_forms

    def dimension_modular_forms(self):
        r"""
        The dimension of the space of modular forms.
        """
        return self._dimension_modular_forms

    def dimension_new_cusp_forms(self):
        r"""
        The dimension of the subspace of new cusp forms.
        """
        return self._dimension_new_cusp_forms

    def dimension(self):
        r"""
        The dimension of the space of modular forms or cusp forms, depending of self is cuspidal or not.
        """
        if self._cuspidal == 1:
            return self.dimension_cusp_forms()
        elif self._cuspidal == 0:
            return self.dimension_modular_forms()
        else:
            raise ValueError("Do not know the dimension of space of type {0}".format(self._cuspidal))

  
    def sturm_bound(self):
        r"""
          Return the Sturm bound of S_k(N,xi),
          i.e. the trivial upper bound number of coefficients necessary to determine a form uniquely in the space.
        """
        return self._sturm_bound

    def labels(self):
        r"""

        """
        return self._galois_orbits_labels

    def f(self, i):
        r"""
          Return function f in the set of newforms on self. Here i is either a label, e.g. 'a' or an integer.
        """
        from web_modforms import WebNewForm
        
        if (isinstance(i, int) or i in ZZ):
            if i < len(self.labels()):
                i = self.labels()[i]
            else:
                raise IndexError,"Form nr. {i} does not exist!".format(i=i)
        #if not i in self._galois_orbits_labels:
        #    raise IndexError,"Form wih label: {i} does not exist!".format(i=i)
        if self._newforms.has_key(i) and self._newforms[i]<>None:
            F = self._newforms[i]
        else:
            F = WebNewForm(N=self._N,k=self._k,  chi=self._chi, parent=self, label=i)
            self._newforms[i] = F
        emf_logger.debug("returning F! :{0}".format(F))
        return F

    def to_web_dict(self):
        d = {}
        dd = self.__dict__
        for k, v in dd.items():
            d[k[1:]] = v
        d['dimension_oldspace'] = self.dimension_oldspace()
        d['character'] = self.character()
        d['weight'] = self.weight()
        d['dimension'] = self.dimension()
        # properties for the sidebar
        prop = []
        if self.is_cuspidal():
            prop = [('Dimension newforms', [d['dimension_newspace']])]
            prop.append(('Dimension oldforms', [d['dimension_oldspace']]))
        else:
            prop = [('Dimension modular forms', [d['dimension_mod_forms']])]
            prop.append(('Dimension cusp forms', [d['dimension_cusp_forms']]))
            prop.append(('Sturm bound', [self.sturm_bound()]))
        d['properties2'] = prop
        if isinstance(d['newforms'], dict) and self.dimension_new_cusp_forms() > 0:
            d['nontrivial_new'] = True
        if d['dimension_newspace'] == 0:
            d['nontrivial_new_info'] = " is empty!"
        return d
