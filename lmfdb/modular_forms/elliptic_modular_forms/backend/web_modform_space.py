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
r"""
  Class for spaces of modular forms in a format
  which can be presented on the web easily


AUTHORS:

 - Fredrik Stroemberg
 - Stephan Ehlen
 
 """

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import \
     WebObject, WebInt, WebStr, WebFloat,\
     WebDict, WebList, WebSageObject, WebNoStoreObject, WebProperties
from lmfdb.modular_forms.elliptic_modular_forms.backend.web_character import WebChar, WebCharProperty
from lmfdb.modular_forms.elliptic_modular_forms import emf_version
        
class WebModFormSpace(WebObject):
    r"""
    Space of modular forms to be presented on the web.

    EXAMPLES::
    - We assume that we are starting from scratch.

    sage: M=WebModFormSpace(1,12)
    sage: M.galois_orbit_name
    ''
    sage: M.galois_orbit_name='1.12.1'
    sage: M.dimension=1
    sage: M.dimension_newspace=1
    sage: M.dimension_cusp_forms=1
    sage: M.newforms = {'a': delta_qexp(20)}
    sage: M.save_to_db()
    {'galois_orbit_name': '1.12.1', 'character': 1, 'weight': 12, 'level': 1}
    sage: M1=WebModFormSpace(1,12)
    sage: M1.galois_orbit_name
    ''
    sage: M1.newforms
    {}
    sage: M1.update_from_db()
    sage: M1.newforms
    {'a': q - 24*q^2 + 252*q^3 - 1472*q^4 + 4830*q^5 - 6048*q^6 - 16744*q^7 + 84480*q^8 - 113643*q^9 - \
    115920*q^10 + 534612*q^11 - 370944*q^12 - 577738*q^13 + 401856*q^14 + 1217160*q^15 + 987136*q^16 - \
    6905934*q^17 + 2727432*q^18 + 10661420*q^19 + O(q^20)}

    """

    def __init__(self, level=1, weight=12, character=1, prec=10, bitprec=53, update_from_db=True):
        self._properties = WebProperties(
            WebInt('level', default_value=level),
            WebInt('weight', default_value=weight),
            WebCharProperty('character', modulus=level, default_value=character),
            WebList('character_galois_orbit', default_value=[character]),
            WebDict('character_galois_orbit_embeddings', default_value={}),
            WebInt('character_orbit_rep'),
            WebInt('character_used_in_computation'),
            WebInt('dimension'),
            WebStr('galois_orbit_name'),
            WebStr('naming_scheme', default_value='Conrey'),
            WebNoStoreObject('web_character_used_in_computation', WebChar),
            WebInt('cuspidal', default_value=int(1)),
            WebInt('prec', default_value=int(prec)), #precision of q-expansion
            WebList('eigenvalues'), #aps
            WebSageObject('group'),
            WebInt('sturm_bound'),
            WebDict('newforms'),
            WebList('hecke_orbit_labels'),
            WebSageObject('oldspace_decomposition'),
            WebInt('bitprec', default_value=bitprec),
            WebInt('dimension'),
            WebInt('dimension_newspace'),
            WebInt('dimension_cusp_forms'),
            WebInt('dimension_modular_forms'),
            WebInt('dimension_new_cusp_forms'),
            WebFloat('version', default_value=float(emf_version))
                    )
        
        super(WebModFormSpace, self).__init__(
            params=['level', 'weight', 'character'],
            dbkey=['galois_orbit_name'],
            collection_name='webmodformspace_test',
            update_from_db=update_from_db)

    def init_dynamic_properties(self):
        pass

    def __repr__(self):
        return "Space of (Web) Modular Forms of level {N}, weight {k}, and character {chi}".format(
            k=self.weight, N=self.level, chi=self.character)
