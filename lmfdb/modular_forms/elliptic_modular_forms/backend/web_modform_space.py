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

from sage.all import ZZ, Gamma0, Gamma1, RealField, ComplexField, prime_range, join, ceil, RR, Integer, matrix, NumberField, PowerSeriesRing, Parent, SageObject, loads, save, dumps, deepcopy
from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import Matrix, latex
import re
import yaml
from flask import url_for

from lmfdb.modular_forms.elliptic_modular_forms import emf_logger, emf_version
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_core import html_table, len_as_printed

from sage.rings.number_field.number_field_base import NumberField as NumberField_class
from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db,get_files_from_gridfs
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_character import WebChar

def WebModFormSpace(N=1, k=2, chi=1, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,**kwds):
    r"""
    Constructor for WebNewForms with added 'nicer' error message.
    """
    if cuspidal <> 1:
        raise IndexError,"We are very sorry. There are only cuspidal spaces currently in the database!"

    F = WebModFormSpace_class(N=N, k=k, chi=chi, cuspidal=cuspidal, prec=prec, bitprec=bitprec, data=data, verbose=verbose,**kwds)
    return F


class WebModFormSpace_class(object):
    r"""
    Space of cuspforms to be presented on the web.

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
        
        if data is None:
            data = {}
        emf_logger.debug("WebModFormSpace with k,N,chi={0}".format( (k,N,chi)))
        d = {
            '_N': int(N),
            '_k': int(k),
            '_chi': int(chi),
            '_character_orbit_rep': None,
            '_character_galois_orbit': [],
            '_character_galois_orbit_embeddings': {},
            '_character_used_in_computation': None,
            '_character': None,
            '_cuspidal' : int(cuspidal),
            '_prec' : int(prec),
            '_ap' : {},
            '_group' : None,
            '_sturm_bound' : None,
            '_newforms' : {},
            '_hecke_orbits_labels' : [],
            '_oldspace_decomposition' : [],
            '_verbose' : int(verbose),
            '_bitprec' : int(bitprec),
            '_dimension': None,
            '_dimension_newspace' : None,
            '_dimension_cusp_forms' : None,
            '_dimension_modular_forms' : None,
            '_dimension_new_cusp_forms' : None,
            '_name' : "{0}.{1}.{2}".format(N,k,chi),
            '_version': float(emf_version),
            '_galois_orbit_poly_info':{},
            '_web_character_used_in_computation':None
            }
        self.__dict__.update(d)

        emf_logger.debug("Incoming data:{0} ".format(data))
        if get_from_db:
           d = self.get_from_db()
           emf_logger.debug("Got data:{0} from db".format(d))
           if d == {}:
               raise ValueError,"The space is not in the database, params: N={0}, k={1}, chi={2}".format(N,k,chi)
        else:
           d = {}
        if data is None:
            data = {}
        data.update(d)
        self.__dict__.update(data)
        if get_all_newforms_from_db:
            self.get_all_newforms_from_db()

    def _check_if_all_stored(self):
        f = WebModFormSpace(k=self.weight(), N=self.level(), chi=self.chi())
        f._check_if_all_computed()

    def _check_if_all_computed(self):
        needed = {
            '_character_orbit_rep': None,
            '_character_galois_orbit': [],
            '_character_galois_orbit_embeddings': {},
            '_character_used_in_computation': None,
            '_cuspidal' : int(0),
            '_prec' : int(0),
            '_sturm_bound' : None,
            '_hecke_orbits_labels' : [],
            '_oldspace_decomposition' : [],
            '_bitprec' : int(0),
            '_dimension': None,
            '_dimension_newspace' : None,
            '_dimension_cusp_forms' : None,
            '_dimension_modular_forms' : None,
            '_dimension_new_cusp_forms' : None,
            '_version': float(0),
            '_galois_orbit_poly_info': {}
            }
        
        for p in needed.keys():
            assert hasattr(self, p), "Missing property {0}".format(p)
            assert self.__dict__[p] is not needed[p], "Did you store {0}? It has value {1}".format(p,needed[p])
            
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
            self._character = WebChar(self.level(), self.chi())
            if hasattr(self, '_character_galois_orbit_embeddings') and self._character_galois_orbit_embeddings is not None:
                self._character.set_embeddings(self._character_galois_orbit_embeddings)
        return self._character

    def character_galois_orbit(self):
        return self._character_galois_orbit

    def name(self):
        return self._name

    def galois_orbit_name(self):
        r"""
        Returns a canonical name for the galois orbit of self.
        """
        return "{0}.{1}.{2}".format(self.level(), self.weight(), self._character_orbit_rep)
    
    def group(self):
        r"""
        The group of self.
        """
        if self._group is None:
            if self.character().is_trivial():
                self._group = Gamma0(self.level())
            else:
                self._group = Gamma1(self.level())
        return self._group

    def aps(self,prec=-1):
        r"""
        Return a list of aps, that is, Hecke eigenvalues of prime indices, for self.
        """
        return self._ap

    def newforms(self):
        r"""
          Return a dictionary of the form label => WebNewForm containing
          representatives of the irredicible Hecke orbits in the WebModFormSpace ``self```.
        """
        return self._newforms

    def oldspace_decomposition(self):
        r"""
          Return the oldspace decomposition of ```self```.
        """
        return self._oldspace_decomposition
                            
    def character_orbit_rep(self,k=None):
        r"""
        Returns canonical representative of the Galois orbit nr. k acting on the ambient space of self.

        """
        return self._character_orbit_rep

    def web_character_used_in_computation(self):
        r"""
          Return a WebCharacter that corresponds to the character that was used during computation.
        """
        if self._web_character_used_in_computation is None:
            self._web_character_used_in_computation = WebChar(self.level(), self._character_used_in_computation)
        return self._web_character_used_in_computation

    def to_dict(self):
        r"""
        Makes a dictionary of the serializable properties of self.
        """
        problematic_keys = ['_newforms',
                            '_newspace',
                            '_modular_symbols',
                            '_new_modular_symbols',
                            '_oldspace_decomposition',
                            '_conrey_character',
                            '_character',
                            '_web_character_used_in_computation',
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
        db = connect_to_modularforms_db('webmodformspace.files')
        s = {'k': self._k, 'N': self._N, 'character_galois_orbit': {'$all': [int(self._chi)]}, 'version': float(emf_version)}
        emf_logger.debug("Looking in DB for rec={0}".format(s))
        f = db.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = get_files_from_gridfs('webmodformspace')
            f = fs.get(id)
            emf_logger.debug("Getting rec={0}".format(f))
            d = loads(f.read())
            return d
        return {}

    def get_all_newforms_from_db(self):
        from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import WebNewForm
        for l in self.labels():
            self._newforms[l] = WebNewForm(N=self._N, k=self._k,  chi=self._chi, parent=self, label=l)
            
    def __repr__(self):
        r"""
        Return string representation of self.
        """
        
        if self.character().is_trivial():
            s = 'Space of Cusp forms on Gamma0({0}) of weight {1}'.format(self.level(),self.weight())
        else:
            s = 'Space of Cusp forms on Gamma0({0}) of weight {1} and character no. {2}'.format(self.level(),self.weight(),self.chi())
        return s


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
            if self.dimension_cusp_forms() is not None and self.dimension_new_cusp_forms() is not None:
                return self.dimension_cusp_forms() - self.dimension_new_cusp_forms()
            else:
                return None
        if self.dimension_modular_forms() is None or self.dimension_newspace() is None:
            return None
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
        if self._dimension is None:
            if self.is_cuspidal():
                self._dimension = self.dimension_cusp_forms()
            else:
                self._dimension = self.dimension_modular_forms()
        return self._dimension
  
    def sturm_bound(self):
        r"""
          Return the Sturm bound of S_k(N,xi),
          i.e. the trivial upper bound number of coefficients necessary to determine a form uniquely in the space.
        """
        if self._sturm_bound is None:
            self._sturm_bound = self.group().sturm_bound()
        return self._sturm_bound

    def labels(self):
        r"""
          Return the labels.
        """
        return self._hecke_orbits_labels

    def f(self, i):
        r"""
          Return function f in the set of newforms on self. Here i is either a label, e.g. 'a' or an integer.
        """
        from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modforms import WebNewForm
        
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

    def insert_into_db(self,update=False):
        r"""
          Insert a dictionary of data for self into the collection WebModularforms.files
        """
        db = connect_to_modularforms_db('webmodformspace.files')
        fs = get_files_from_gridfs('webmodformspace')
        fname = "webmodformspace-{0:0>5}-{1:0>3}-{2:0>3}".format(self._N,self._k,self._chi)
        emf_logger.debug("Check if we insert this webmodform space into db! fname={0}".format(fname))
        s = {'filename':fname, 'version':emf_version}
        if fs.exists(s):
            emf_logger.debug("We already have this space in the database and we do not reinsert it!")
            if not update:
                return True
            fid = fs.find(s)['_id']
            fs.delete(fid)
            emf_logger.debug("Removing self from db with s={0} and id={1}".format(s,id))
            

        d = self.to_dict()
        d.pop('_ap',None) # Since the ap's are already in the database we don't need them here
        id = fs.put(dumps(d),filename=fname,N=int(self._N),k=int(self._k),chi=int(self._chi),\
                    galois_orbit_name=self.galois_orbit_name(),version=emf_version,\
                    character_galois_orbit=map(int,self.character_galois_orbit()))
        emf_logger.debug("inserted :{0}".format(id))
    
