# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
#  Stephan Ehlen <>
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
from flask import url_for
from sage.all import dumps,loads, euler_phi,gcd,trivial_character
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger,emf_version,use_cache
from sage.rings.number_field.number_field_base import NumberField as NumberField_class
from sage.all import copy

from sage.structure.unique_representation import CachedRepresentation
#from lmfdb.WebCharacter import url_character
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import WebObject, WebProperty, WebInt, WebProperties, WebStr, WebNoStoreObject, WebDict, WebFloat

from lmfdb.modular_forms.elliptic_modular_forms.backend import connect_to_modularforms_db,get_files_from_gridfs
try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

import logging
#emf_logger.setLevel(logging.DEBUG)
    
class WebChar(WebObject, CachedRepresentation):
    r"""
    Class which should/might be replaced with 
    WebDirichletCharcter once this is ok.
    
    """
    _key = ['modulus', 'number']
    _file_key = ['modulus', 'number']
    _collection_name = 'webchar'
    
    def __init__(self, modulus=1, number=1, update_from_db=True, compute=False):
        r"""
        Init self.

        """
        emf_logger.critical("In WebChar {0}".format((modulus,number,update_from_db,compute)))
        if not gcd(number,modulus)==1:
            raise ValueError,"Character number {0} of modulus {1} does not exist!".format(number,modulus)
        if number > modulus:
            number = number % modulus
        self._properties = WebProperties(
            WebInt('conductor'),
            WebInt('modulus', value=modulus),
            WebInt('number', value=number),
            WebInt('modulus_euler_phi'),
            WebInt('order'),
            WebStr('latex_name'),
            WebStr('label',value="{0}.{1}".format(modulus,number)),
            WebNoStoreObject('sage_character', type(trivial_character(1))),
            WebDict('_values_algebraic'),
            WebDict('_values_float'),
            WebDict('_embeddings'),            
            WebFloat('version', value=float(emf_version))
            )
        emf_logger.debug('Set properties in WebChar!')
        super(WebChar, self).__init__(
            update_from_db=update_from_db
            )
        if self._has_updated_from_db is False:
            self.init_dynamic_properties() # this was not done if we exited early
            compute = True
        if compute:
            self.compute(save=True)            
            
        #emf_logger.debug('In WebChar, self.__dict__ = {0}'.format(self.__dict__))
        emf_logger.debug('In WebChar, self.number = {0}'.format(self.number))

    def compute(self, save=True):
        emf_logger.debug('in compute for WebChar number {0} of modulus {1}'.format(self.number, self.modulus))
        c = self.character
        changed = False
        if self.conductor == 0:            
            self.conductor = c.conductor()
            changed = True
        if self.order == 0:
            self.order = c.multiplicative_order()
            changed = True
        if self.latex_name == '':
            self.latex_name = "\chi_{" + str(self.modulus) + "}(" + str(self.number) + ", \cdot)"
            changed = True
        if self._values_algebraic == {} or self._values_float == {}:
            changed = True
            for i in range(self.modulus):
                self.value(i,value_format='float')
                self.value(i,value_format='algebraic')
        if self.modulus_euler_phi == 0:
            changed = True
            self.modulus_euler_phi = euler_phi(self.modulus)
        if changed and save:
            self.save_to_db()
        else:            
            emf_logger.debug('Not saving.')

    def init_dynamic_properties(self):
        from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import dirichlet_character_conrey_galois_orbit_embeddings
        if self.number is not None:            
            emf_logger.debug('number: {0}'.format(self.number))
            self.character = DirichletCharacter_conrey(DirichletGroup_conrey(self.modulus),self.number)
            self.sage_character = self.character.sage_character()
            self.name = "Character nr. {0} of modulus {1}".format(self.number,self.modulus)
            emb = dirichlet_character_conrey_galois_orbit_embeddings(self.modulus,self.number)
            self.set_embeddings(emb)
            
    def is_trivial(self):
        r"""
        Check if self is trivial.
        """        
        return self.character.is_trivial()

    def embeddings(self):
        r"""
          Returns a dictionary that maps the Conrey numbers
          of the Dirichlet characters in the Galois orbit of ```self```
          to the powers of $\zeta_{\phi(N)}$ so that the corresponding
          embeddings map the labels.

          Let $\zeta_{\phi(N)}$ be the generator of the cyclotomic field
          of $N$-th roots of unity which is the base field
          for the coefficients of a modular form contained in the database.
          Considering the space $S_k(N,\chi)$, where $\chi = \chi_N(m, \cdot)$,
          if embeddings()[m] = n, then $\zeta_{\phi(N)}$ is mapped to
          $\mathrm{exp}(2\pi i n /\phi(N))$.
        """
        return self._embeddings

    def set_embeddings(self, d):
        self._embeddings = d

    def embedding(self):
        r"""
          Let $\zeta_{\phi(N)}$ be the generator of the cyclotomic field
          of $N$-th roots of unity which is the base field
          for the coefficients of a modular form contained in the database.
          If ```self``` is given as $\chi = \chi_N(m, \cdot)$ in the Conrey naming scheme,
          then we have to apply the map
          \[
            \zeta_{\phi(N)} \mapsto \mathrm{exp}(2\pi i n /\phi(N))
          \]
          to the coefficients of normalized newforms in $S_k(N,\chi)$
          as in the database in order to obtain the coefficients corresponding to ```self```
          (that is to elements in $S_k(N,\chi)$).
        """
        return self._embeddings[self.number]
            
    def __repr__(self):
        r"""
        Return the string representation of the character of self.
        """
        return self.name
            
    def value(self, x, value_format='algebraic'):
        r"""
        Return the value of self as an algebraic integer or float.
        """
        x = int(x)
        if value_format =='algebraic':
            if self._values_algebraic is None:
                self._values_algebraic = {}
            y = self._values_algebraic.get(x)
            if y is None:
                y = self._values_algebraic[x]=self.sage_character(x)
            else:
                self._values_algebraic[x]=y
            return self._values_algebraic[x]
        elif value_format=='float':  ## floating point
            if self._values_float is None:
                self._values_float = {}
            y = self._values_float.get(x)
            if y is None:
                y = self._values_float[x]=self.character(x)
            else:
                self._values_float[x]=y
            return self._values_float[x]
        else:
            raise ValueError,"Format {0} is not known!".format(value_format)
        
    def url(self):
        r"""
        Return the url of self.
        """
        if not hasattr(self, '_url') or self._url is None:
            self._url = url_for('characters.render_Dirichletwebpage',modulus=self.modulus, number=self.number)
        return self._url


class WebCharProperty(WebInt):
    
    def __init__(self, name, modulus=1, number=int(1), **kwargs):
        #self._default_value = WebChar(modulus, number, update_from_db=True, compute=True)
        self.modulus = modulus
        self.number = number
        c = None
        if not kwargs.has_key('value'):
            c = WebChar_cached(modulus, number, update_from_db=True, compute=True)
        elif kwargs['value'] is not None:
            c = kwargs.pop('value')
        else:
            self._default_value = WebChar_cached(modulus, number, update_from_db=True, compute=True)
        if c is None:
            super(WebCharProperty, self).__init__(name, **kwargs)
        else:
            super(WebCharProperty, self).__init__(name, value=c, **kwargs)

    def to_db(self):
        c = self._value
        if not isinstance(c, WebChar) \
               and not isinstance(c, DirichletCharacter_conrey):
            return int(c)
        if isinstance(c,WebChar):
            return int(c.number)
        else:
            return int(c.number())

    def from_db(self, n):
        emf_logger.debug('converting {0} from store in WebCharProperty {1}'.format(n, self.name))
        return WebChar(self.modulus, n, compute=True)

    def from_fs(self, n):
        return self.from_db(n)

    def to_fs(self):
        return self.to_db()
    
   
from lmfdb.utils import cache
def WebChar_cached(modulus,number,**kwds):
    if use_cache:
        label = "{0}.{1}".format(modulus,number)
        X= cache.get(label)
        emf_logger.critical("Looking for cached  char:{0}".format(label))
        if X is None:
            emf_logger.debug("X was not in cache!")
            X = WebChar(modulus,number,**kwds)
            cache.set(label, X, timeout=5 * 60)
        else:
            emf_logger.critical("X was in cache!")
    else:
        X = WebChar(modulus,number,**kwds)
    return X
