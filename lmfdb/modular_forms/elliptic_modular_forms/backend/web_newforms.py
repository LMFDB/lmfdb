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

from flask import url_for

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import (
     WebObject,
     WebInt,
     WebBool,
     WebStr,
     WebFloat,
     WebDict,
     WebList,
     WebSageObject,
     WebNoStoreObject,
     WebPoly,
     WebProperty,
     WebProperties,
     WebNumberField,     
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_character import (
     WebChar,
     WebCharProperty
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_modform_space import (
     WebModFormSpaceProperty
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import newform_label, space_label

from lmfdb.modular_forms.elliptic_modular_forms import (
     emf_version,
     emf_logger
     )

from lmfdb.number_fields.number_field import poly_to_field_label, field_pretty
from lmfdb.utils import web_latex_split_on_re

from sage.rings.number_field.number_field_base import (
     NumberField
     )

from sage.rings.power_series_poly import PowerSeries_poly

from sage.all import (
     ZZ,
     Gamma0,
     Gamma1,
     RealField,
     ComplexField,
     prime_range,
     join,
     ceil,
     RR,
     Integer,
     matrix,
     PowerSeriesRing,
     Matrix,
     vector,
     latex,
     primes_first_n,
     loads,
     dumps
     )

from sage.matrix.matrix_integer_dense import Matrix_integer_dense
from sage.modules.vector_integer_dense import Vector_integer_dense

from sage.structure.unique_representation import CachedRepresentation

class WebqExp(WebPoly):

    def __init__(self, name, prec=10,
                 default_value=None):
        super(WebqExp, self).__init__(name, default_value=default_value)

    def latex(self, prec=None, name=None):
        if prec is None:
            qe = self.value()
        else:
            qe = self.value().truncate_powerseries(prec)
        wl = web_latex_split_on_re(qe)
        
        if name is not None:
            return wl.replace(str(self.value().base_ring().gen()), name)
        else:
            return wl

    def from_fs(self, f):
        if f is None:
            return None
        f=loads(f)
        try:
            f = f.truncate_powerseries(prec)
            return f
        except:
            return f

    def to_fs(self):
        if self.value() is None:
            return None
        return dumps(self.value().polynomial())


class WebEigenvalues(WebObject, CachedRepresentation):

    _key = ['hecke_orbit_label']
    _file_key = ['hecke_orbit_label', 'prec']
    _collection_name = 'ap_test'

    def __init__(self, hecke_orbit_label, prec=10, update_from_db=True):
        self._properties = WebProperties(
            WebSageObject('E', None, Matrix),
            WebSageObject('v', None, vector),
            WebStr('hecke_orbit_label', value=hecke_orbit_label),
            WebInt('prec', value=prec)
            )
        
        super(WebEigenvalues, self).__init__(
            use_gridfs=True,
            use_separate_db=False,
            update_from_db=update_from_db
            )

    def update_from_db(self, ignore_non_existent = True, \
                       add_to_fs_query=None, add_to_db_query=None):

        self._add_to_fs_query = {'prec': {'$gt': self.prec-1}}
        super(WebEigenvalues,self).update_from_db(ignore_non_existent, add_to_fs_query, add_to_db_query)

    def init_dynamic_properties(self):
        emf_logger.debug("E = {0}".format(self.E))
        if not self.E is None and not self.v is None:
            c = self.E*self.v
            lc = len(c)
            self._ap = {}
            for i in range(len(c)):
                p = primes_first_n(lc)[i]
                self._ap[p] = c[i]
        else:
            self._ap = {}

    def primes(self):
        return self._ap.keys()

    def has_eigenvalue(self, p):
        return self._ap.has_key(p)

    def __getitem__(self, p):
        return self._ap[p]

    def __setitem__(self, p, v):
        self._ap[p] = v

    def __iter__(self):
        return self._ap.itervalues()

    def __len__(self):
        return len(self._ap)

    def __contains__(self, a):
        return a in self._ap

    def __repr__(self):
        return "Collection of {0} eigenvalues.".format(len(self._ap))

    
class WebNewForm(WebObject, CachedRepresentation):

    _key = ['level', 'weight', 'character', 'label']
    _file_key = ['hecke_orbit_label']
    _collection_name = 'webnewforms_test'

    def __init__(self, level=1, weight=12, character=1, label='a', prec=10, bitprec=53, parent=None, update_from_db=True):
        if isinstance(character, WebChar):
            character_number = character.number
        else:
            character_number = character
            character = None if parent is None else parent.character
        
        self._properties = WebProperties(
            WebInt('level', value=level),
            WebInt('weight', value=weight),
            WebCharProperty('character', modulus=level,
                            number=character_number,
                            value = character,
                            include_in_update = True if parent is None
                            else False),
            WebStr('character_naming_scheme', default_value='Conrey'),
            WebStr('hecke_orbit_label', default_value=newform_label(level, weight, character, label)),
            WebStr('label', default_value=label),
            WebInt('dimension'),
            WebqExp('q_expansion', prec=prec),
            WebDict('_coefficients'),
            WebInt('prec', default_value=int(prec)), #precision of q-expansion
            WebNumberField('base_ring'),
            WebNumberField('coefficient_field'),
            WebList('twist_info'),
            WebBool('is_cm'),
            WebBool('is_cuspidal',default_value=True),
            WebDict('satake'),
            WebDict('_atkin_lehner_eigenvalues'),
            WebBool('is_rational'),
            WebPoly('absolute_polynomial'),
            WebInt('sturm_bound'),
            WebFloat('version', default_value=float(emf_version), save_to_fs=True),
            WebModFormSpaceProperty('parent', value=parent,
                                              level = level,
                                              weight = weight,
                                              character = character),
            )
        super(WebNewForm, self).__init__(
            update_from_db=update_from_db
            )

        # We're setting the WebEigenvalues property after calling __init__ of the base class
        # because it will set hecke_orbit_label from the db first
        self.eigenvalues = WebEigenvalues(self.hecke_orbit_label, prec = self.prec)

    def q_expansion_latex(self, prec=None, name=None):
        return self._properties['q_expansion'].latex(prec, name)

    def coefficient(self, n):
        r"""
          Return coefficient nr. n
        """
        #emf_logger.debug("In coefficient: n={0}".format(n))
        if n==0:
            if self.is_cuspidal:
                return self.coefficient_field(0)
        c = self._coefficients.get(n, None)
        if c is None:
            c = self.coefficients([n])[0] 
        return c

    def coefficients(self, nrange=range(1, 10), save_to_db=True):
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
            c = self._coefficients.get(n, None)
            #emf_logger.debug("c({0}) in self._coefficients={1}".format(n,c))            
            if c is None:
                if n == 0 and self.is_cuspidal:
                    c = self.coefficient_field(0)
                else:
                    recompute = True
                    c = self.coefficient_n_recursive(n)
                    self._coefficients[n] = c
            res.append(c)
        if recompute and save_to_db:
            self.save_to_db(update=True)
        return res
       
    def coefficient_n_recursive(self, n):
        r"""
          Reimplement the recursive algorithm in sage modular/hecke/module.py
          We do this because of a bug in sage with .eigenvalue()
        """
        from sage.rings import arith
        #emf_logger.debug("computing c({0}) using recursive algortithm".format(n))
        if n==1:
            return 1
        F = arith.factor(n)
        prod = None        
        ev = self.eigenvalues
        if ev.has_eigenvalue(2):
            K = ev[2].parent()
        else:
            raise StopIteration,"Newform does not have eigenvalue a(2)!"
        for p, r in F:
            (p, r) = (int(p), int(r))
            pr = p**r
            if not ev.has_eigenvalue(p):
                # Here the question is whether we start computing or only use from database...
                raise ValueError,"p={0} is outside the range of computed primes (primes up to {1})!".format(p,max(ev.primes()))
            if not ev.has_eigenvalue(pr):  # and ev[pow].has_key(name)):
                # TODO: Optimization -- do something much more
                # intelligent in case character is not defined.  For
                # example, compute it using the diamond operators <d>
                eps = K(self.parent.character_used_in_computation.value(p))
                # a_{p^r} := a_p * a_{p^{r-1}} - eps(p)p^{k-1} a_{p^{r-2}}
                apr1 = self.coefficient_n_recursive(pr//p)
                ap = self.coefficient_n_recursive(p)
                k = self.weight
                apr2 = self.coefficient_n_recursive(pr//(p*p))
                apow = ap*apr1 - eps*(p**(k-1)) * apr2
                ev[pr]=apow
                #if self._verbose>1:
                #    print "eps=",eps
                #    print "a[",pr//p,"]=",apr1
                #    print "a[",pr//(p*p),"]=",apr2                
                #    print "a[",pr,"]=",apow                
                #    print "a[",p,"]=",ap
                # _dict_set(ev, pow, name, apow)
            if prod is None:
                prod = ev[pr]
            else:
                prod *= ev[pr]
        return prod

    def max_cn(self):
        r"""
        The largest N for which we are sure that we can compute a(n) for all 1<=n<=N
        """
        if self.eigenvalues.primes()==[]:
            return 1
        return max(self.eigenvalues.primes()) + 1

    def atkin_lehner_eigenvalue(self, Q):
        r""" Return the Atkin-Lehner eigenvalues of self
        corresponding to Q|N
        """
        if not (self.character.is_trivial() or self.character.order == 2):
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
        if not (self.character.is_trivial() or self.character.order == 2):
            return None
        
        if(len(self._atkin_lehner_eigenvalues.keys()) > 0):
            return self._atkin_lehner_eigenvalues
    
    def url(self):
        return url_for('emf.render_elliptic_modular_forms', level=self.level, weight=self.weight, character=self.character.numer(), label=self.label)

    def coefficient_field_label(self, pretty = True):
        r"""
          Returns the LMFDB label of the (absolute) coefficient field.
        """
        p = self.absolute_polynomial
        l = poly_to_field_label(p)
        if pretty:
            return field_pretty(l)
        else:
            return l

    def coefficient_field_url(self):
        return url_for("number_fields.by_label", label=self.coefficient_field_label(pretty = False))

    def base_field_label(self, pretty = True):
        r"""
          Returns the LMFDB label of the base field.
        """
        F = self.base_ring
        if F.degree() == 1:
            p = 'x'
        else:
            p = F.polynomial()
        l = poly_to_field_label(p)
        if pretty:
            return field_pretty(l)
        else:
            return l

    def base_field_url(self):
        return url_for("number_fields.by_label", label=self.base_field_label(pretty = False))
