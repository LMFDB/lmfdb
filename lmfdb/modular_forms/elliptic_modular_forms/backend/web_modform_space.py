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
r"""
  Class for spaces of modular forms in a format
  which can be presented on the web easily


AUTHORS:

 - Fredrik Stroemberg
 - Stephan Ehlen
 
 """

import os, yaml
from flask import url_for

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import (
     WebObject,
     WebDate,
     WebInt,
     WebStr,
     WebFloat,
     WebDict,
     WebList,
     WebBool,
     WebSageObject,
     WebNoStoreObject,
     WebProperty,
     WebProperties
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_character import (
     WebChar,
     WebCharProperty
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import newform_label, space_label

from lmfdb.modular_forms.elliptic_modular_forms import (
     emf_version,
     emf_logger
     )

from sage.rings.number_field.number_field_base import (
     NumberField
     )

from sage.all import (
     ZZ,
     Gamma0,
     Gamma1,
     RealField,
     ComplexField,
     prime_range,
     ceil,
     RR,
     Integer,
     matrix,
     PowerSeriesRing,
     Matrix,
     latex
     )
     
from sage.rings.power_series_poly import PowerSeries_poly

from sage.structure.unique_representation import CachedRepresentation


class WebHeckeOrbits(WebDict):
    r"""
    Collection of WebNewforms for easy access by name.
    """

    def __init__(self, name, level, weight, character, parent=None, prec=10, **kwds):
        emf_logger.debug("Get Hecke orbits! {0},{1},{2},{3},{4},kwds={5}".format(name,level,weight,character,type(parent),kwds))
        self.level = level
        self.weight = weight
        self.character = character
        self.parent = parent
        self.prec = prec
        super(WebHeckeOrbits, self).__init__(
            name, None, save_to_db=True, save_to_fs=False,**kwds
            )
        emf_logger.debug("Initiated Hecke orbits!")
        
    def to_db(self):
        return self.value().keys()

    def to_fs(self):
        return self.to_db()

    def from_db(self, l):
        emf_logger.debug("Get Hecke orbits for labels : {0}!".format(l))
        self._only_rational = True
        from lmfdb.modular_forms.elliptic_modular_forms.backend.web_newforms import WebNewForm_cached,WebNewForm
        res = {}
        for lbl in l:
            F = WebNewForm(self.level, self.weight, self.character, lbl, prec = self.prec, parent=self.parent)
            if F.coefficient_field.absolute_degree() > 1:
                self._only_rational = False
            #F = WebNewForm_cached(self.level, self.weight, self.character, lbl, parent=self.parent)
            emf_logger.debug("Got F for label {0} : {1}".format(lbl,F))
            res[lbl]=F
#            return {lbl : WebNewForm_cached(self.level, self.weight, self.character, lbl, parent=self.parent)
#                for lbl in l}
        emf_logger.debug("Got Hecke orbits!")

        return res


    def from_fs(self, l):
        return self.from_db(l)

    def only_rational(self):
        return self._only_rational
    

class WebModFormSpace(WebObject, CachedRepresentation):
    r"""
    Space of modular forms to be presented on the web.

    EXAMPLES::
    - We assume that we are starting from scratch.

    sage: M=WebModFormSpace(1,12)
    sage: M.space_label
    '1.12.1'
    sage: M.dimension
    0
    sage: M.dimension=1
    sage: M.dimension_new_cusp_forms=1
    sage: M.dimension_cusp_forms=1
    sage: M.dimension_modular_form=1
    sage: f = WebNewForm(1,12,1,'a')
    sage: f.q_expansion = delta_qexp(20)
    sage: f.save_to_db()
    sage: M.hecke_orbits = {'a': f}
    sage: M.save_to_db()
    sage: M._clear_cache_()
    sage: f._clear_cache()
    sage: del(M)
    sage: del(f)
    sage: M=WebModFormSpace(1,12, update_from_db=False)
    sage: M.hecke_orbits
    {}
    sage: M.update_from_db()
    sage: M.hecke_orbits
    {'a': WebNewform in S_12(1,chi_1) with label a}
    sage: M.hecke_orbits['a'].q_expansion
    q - 24*q^2 + 252*q^3 - 1472*q^4 + 4830*q^5 - 6048*q^6 - 16744*q^7 + 84480*q^8 - 113643*q^9 - 115920*q^10 + 534612*q^11 - 370944*q^12 - 577738*q^13 + 401856*q^14 + 1217160*q^15 + 987136*q^16 - 6905934*q^17 + 2727432*q^18 + O(q^19)
    """

    _key = ['level', 'weight', 'character','version']
    _file_key = ['space_label','version']
    if emf_version > 1.3:
        _collection_name = 'webmodformspace2'
        _dimension_table_name = 'dimension_table2'
    else:
        _collection_name = 'webmodformspace'
        _dimension_table_name = 'dimension_table'

    def __init__(self, level=1, weight=12, character=1,cuspidal=True, new=True, prec=0, bitprec=53, update_from_db=True, update_hecke_orbits=True, **kwargs):

        # I added this reduction since otherwise there is a problem with
        # caching the hecke orbits (since they have self as  parent)
        self._reduction = (type(self),(level,weight,character),
                           {'cuspidal':cuspidal, 'prec':prec, 'bitprec':bitprec, 'update_from_db':update_from_db,'update_hecke_orbits':update_hecke_orbits})
        if isinstance(character, WebChar):
            character_number = character.number
        else:
            character_number = character
        emf_logger.debug("level={0}".format(level))
        emf_logger.debug("character={0},type={1}".format(character,type(character)))         
        emf_logger.debug("character_number={0}".format(character_number))         
        self._properties = WebProperties(
            WebInt('level', value=level),
            WebInt('weight', value=weight),
            WebCharProperty('character', modulus=level, number=character_number),
            WebStr('character_naming_scheme', value='Conrey', save_to_fs=True),
            WebList('_character_galois_orbit', default_value=[character]),
            WebDict('_character_galois_orbit_embeddings', default_value={}),
            WebCharProperty('character_orbit_rep', modulus=level, save_to_fs=True),
            WebCharProperty('character_used_in_computation', modulus=level, save_to_fs=True),
            WebStr('space_label', default_value=space_label(level=level, weight=weight, character=character), save_to_fs=True),
            WebStr('space_orbit_label', value='', save_to_db=True),            
            #WebStr('galois_orbit_name', value='', save_to_fs=True),
            WebInt('dimension'),
            WebInt('dimension_cusp_forms'),
            WebInt('dimension_modular_forms'),
            WebInt('dimension_new_cusp_forms'),
            WebBool('cuspidal', value=cuspidal),
            WebBool('new', value=new),
            #WebInt('prec', value=int(prec)), #precision of q-expansions -- removed, does not make much sense for the space here
            WebSageObject('group'),
            WebInt('sturm_bound'),
            WebHeckeOrbits('hecke_orbits', level, weight,
                           character, self,  prec=prec, include_in_update=update_hecke_orbits),
            WebList('oldspace_decomposition', required=False),
            WebInt('bitprec', value=bitprec),
            WebFloat('version', value=float(emf_version), save_to_fs=True),
            WebList('zeta_orders',value=[],save_to_db=True),
            WebDate('creation_date',value=None,save_to_db=True)
                    )

        self.make_code_snippets()
            
        emf_logger.debug("Have set properties of space 1 !!")
        super(WebModFormSpace, self).__init__(update_from_db=update_from_db, **kwargs)
        emf_logger.debug("Have set properties of space 2 !!")
        emf_logger.debug("orbits={0}".format(self.hecke_orbits))                

    def init_dynamic_properties(self):
        if self.character.is_trivial():
            self.group = Gamma0(self.level)
        else:
            self.group = Gamma1(self.level)

    def only_rational(self):
        return self._properties['hecke_orbits'].only_rational()

    def data_from_dimension_db(self):
        res = self.connect_to_db()[self._dimension_table_name].find_one({'space_label':self.space_label})
        # make sure that the return value is always a dict.
        if res == None:
            return {}
        return res

    def make_code_snippets(self):
         # read in code.yaml from numberfields directory:
        _curdir = os.path.dirname(os.path.abspath(__file__))
        self.code = yaml.load(open(os.path.join(_curdir, "../code.yaml")))
        self.code['show'] = {'sage':'','magma':''}
        # Fill in placeholders for this specific space:
        for lang in ['sage', 'magma']:
            if self.character.order == 1:
                self.code['newforms-triv-char'][lang] = self.code['newforms-triv-char'][lang].format(
                    N=self.level, k=self.weight)
            else:
                self.code['newforms-nontriv-char'][lang] = self.code['newforms-nontriv-char'][lang].format(
                    N=self.level, k=self.weight, elt=list(self.character.sage_character.element()))

    def __repr__(self):
        if self.character.is_trivial():
            return "Space of (Web) Modular Forms of level {N}, weight {k}, and trivial character".format(
                k=self.weight, N=self.level)
        return "Space of (Web) Modular Forms of level {N}, weight {k}, and character number {chi}  modulo {N}".format(
            k=self.weight, N=self.level, chi=self.character.number)


class WebModFormSpaceProperty(WebProperty):

    def __init__(self, name, level=1, weight=12, character=1, value=None, update_from_db=True, \
                 update_hecke_orbits=False,include_in_update=False):
        self.level = level
        self.weight = weight
        self.character = character
        emf_logger.debug("CCCCharacter = {0}".format(self.character))
        if value is None:
            value = WebModFormSpace_cached(self.level, self.weight, self.character, update_from_db=update_from_db, update_hecke_orbits=update_hecke_orbits)
        emf_logger.debug("CCCCharacter = {0}".format(self.character))
        super(WebModFormSpaceProperty, self).__init__(name,
                                                      include_in_update=include_in_update,
                                                      save_to_db=True,
                                                      save_to_fs=False,
                                                      value = value)

    def to_fs(self):
        return self.value().space_label

    def to_db(self):
        return self.to_fs()


    
from lmfdb.utils import cache
from lmfdb.modular_forms.elliptic_modular_forms import use_cache
def WebModFormSpace_cached(level,weight,character,**kwds):
    if use_cache: 
        label = space_label(level=level, weight=weight, character=character, make_cache_label = True)
        M= cache.get(label)
        emf_logger.debug("Looking for cached space:{0}".format(label))
        if M is None:
            emf_logger.debug("M was not in cache!")
            M = WebModFormSpace(level,weight,character,**kwds)
            cache.set(label, M, timeout=5 * 60)
        else:
            emf_logger.debug("M was in cache!")
    else:
        M = WebModFormSpace(level,weight,character,**kwds)
    return M


