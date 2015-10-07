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
     WebModFormSpaceProperty,
     WebModFormSpace_cached
     )

from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import newform_label, space_label, field_label

from lmfdb.utils import web_latex_split_on_re

from lmfdb.modular_forms.elliptic_modular_forms import (
     emf_version,
     emf_logger
     )

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

    def __init__(self, name,
                 default_value=None):
        super(WebqExp, self).__init__(name, default_value=default_value)

    def latex(self, prec=None, name=None):
        if prec is None:
            qe = self.value()
        else:
            qe = self.value().truncate_powerseries(prec)
        wl = web_latex_split_on_re(qe)
        if name is not None and self.value().base_ring().degree()>1:
            return wl.replace(latex(self.value().base_ring().gen()), name)
        else:
            return wl

    def from_fs(self, f):
        if f is None:
            return None
        #print "f", f
        try:
            f = f.truncate_powerseries(f.degree())
            return f
        except:
            return f

    def to_fs(self):
        if self.value() is None:
            return None
        #print type(self.value()), self.value()
        return self.value()


class WebEigenvalues(WebObject, CachedRepresentation):

    _key = ['hecke_orbit_label']
    _file_key = ['hecke_orbit_label', 'prec']
    _collection_name = 'webeigenvalues'

    def __init__(self, hecke_orbit_label, prec=10, update_from_db=True, auto_update = True,init_dynamic_properties=True):
        self._properties = WebProperties(
            WebSageObject('E', None, Matrix),
            WebSageObject('v', None, vector),
            WebDict('meta',value={}),
            WebStr('hecke_orbit_label', value=hecke_orbit_label),
            WebInt('prec', value=prec)
            )

        self.auto_update = True
        self._ap = {}        
        super(WebEigenvalues, self).__init__(
            use_gridfs=True,
            use_separate_db=False,
            update_from_db=update_from_db,
            init_dynamic_properties=init_dynamic_properties
            )

    def update_from_db(self, ignore_non_existent = True, \
                       add_to_fs_query=None, add_to_db_query=None):

        self._add_to_fs_query = {'prec': {'$gt': int(self.prec-1)}}
        super(WebEigenvalues,self).update_from_db(ignore_non_existent, add_to_fs_query, add_to_db_query)
        #print "_ap=",self._ap

    def init_dynamic_properties(self):
        emf_logger.debug("E = {0}".format(self.E))
        if not self.E is None and not self.v is None:
            c = self.E*self.v
            lc = len(c)
            primes_to_lc = primes_first_n(lc)
            self._ap = {}
            for i in range(len(c)):
                p = primes_to_lc[i]
                self._ap[p] = c[i]
        else:
            self._ap = {}

    def primes(self):
        return self._ap.keys()

    def has_eigenvalue(self, p):
        return self._ap.has_key(p)

    def max_coefficient_in_db(self):
        r"""
        Check how many coefficients we can generate from the eigenvalues in the database.
        """
        from sage.all import next_prime
        rec = self.get_db_record()
        if rec is None:
            return 0
        prec_in_db = rec.get('prec')
        return next_prime(prec_in_db)-1
        
    def __getitem__(self, p):
        if self.auto_update and not self.has_eigenvalue(p):
            self.prec = p
            self.update_from_db()
            self.init_dynamic_properties()
        return self._ap.get(p)

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
    _collection_name = 'webnewforms'

    def __init__(self, level=1, weight=12, character=1, label='a', prec=None, parent=None, update_from_db=True):
        emf_logger.critical("In WebNewForm {0}".format((level,weight,character,label,parent,update_from_db)))
        self._reduction = (type(self),(level,weight,character,label),{'parent':parent,'update_from_db':update_from_db})
        if isinstance(character, WebChar):
            character_number = character.number
        else:
            character_number = character
            character = None if parent is None else parent.character
            if not isinstance(label,basestring):
                if isinstance(label,(int,Integer)):
                    label = orbit_label(label)
                else:
                    raise ValueError,"Need label either string or integer! We got:{0}".format(label)

        emf_logger.critical("Before init properties 0")
        self._properties = WebProperties(
            WebInt('level', value=level),
            WebInt('weight', value=weight),
            WebCharProperty('character', modulus=level,
                            number=character_number,
                            value = character,
                            include_in_update = True if character is None
                            else False),
            WebStr('character_naming_scheme', value='Conrey'),
            WebStr('hecke_orbit_label', default_value=newform_label(level, weight, character_number, label)),
            WebStr('label', default_value=label),
            WebInt('dimension'),
            WebqExp('q_expansion'),
            WebDict('_coefficients'),
            WebDict('_embeddings'),
            WebInt('prec',value=0), 
            WebNumberField('base_ring'),
            WebNumberField('coefficient_field'),
            WebInt('coefficient_field_degree'),
            WebList('twist_info', required = False),
            WebBool('is_cm', required = False),
            WebDict('_cm_values',required=False),
            WebBool('is_cuspidal',default_value=True),
            WebDict('satake', required=False),
            WebDict('_atkin_lehner_eigenvalues', required=False),
            WebBool('is_rational'),
            WebPoly('absolute_polynomial'),
            WebFloat('version', value=float(emf_version), save_to_fs=True),
            WebDict('explicit_formulas',required=False),
            WebModFormSpaceProperty('parent', value=parent,
                                    level = level,
                                    weight = weight,
                                    character = character_number,
                                    update_hecke_orbits=False)
#                                    include_in_update = True if parent is None
#                                    else False),
            )
        emf_logger.critical("After init properties 1")
        super(WebNewForm, self).__init__(
            update_from_db=update_from_db
            )
        emf_logger.critical("After init properties 2 prec={0}".format(self.prec))
        # We're setting the WebEigenvalues property after calling __init__ of the base class
        # because it will set hecke_orbit_label from the db first

        ## 
        ## We don't init the eigenvalues (since E*v is slow)
        ## unless we (later) request a coefficient which is not
        ## in self._coefficients
        
        self.eigenvalues = WebEigenvalues(self.hecke_orbit_label, prec = self.prec,init_dynamic_properties=False)
        emf_logger.critical("After init properties 3")

    def __repr__(self):
        if self.dimension == 0:
            s = "Zero "
        else:
            s = ""
        s = "WebNewform in S_{0}({1},chi_{2}) with label {3}".format(self.weight,self.level,self.character.number,self.label)
        return s

    def init_dynamic_properties(self):
        self._properties['q_expansion'].maxprec = self.prec
        
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

    def coefficient_embedding(self,n,i):
        r"""
        Return the i-th complex embedding of coefficient C(n).
        Note that if it is not in the dictionary we compute the embedding (but not the coefficient).
        """
        embc = self._embeddings['values'].get(n,None)
        bitprec = self._embeddings['bitprec']
        if embc is None:
            c = self.coefficient(n)
            if hasattr(c,"complex_embeddings"):
                embc = c.complex_embeddings(bitprec)
            else:
                embc = [ComplexField(bitprec)(c) for x in range(self.coefficient_field_degree)]
            self._embeddings['values'][n]=embc
        else:
            if len(embc) < self.coefficient_field_degree:
                embc = [embc[0] for x in range(self.coefficient_field_degree)]
                self._embeddings['values'][n]=embc
        if i > len(embc):
            raise ValueError,"Embedding nr. {0} does not exist of a number field of degree {1},embc={2}".format(i,self.coefficient_field.absolute_degree(),embc)
        return embc[i]
        
        
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
        ev = self.eigenvalues

        c2 = self._coefficients.get(2)
        if c2 is not None:
            K = c2.parent()
        else:
            if ev.max_coefficient_in_db() >= 2:
                ev.init_dynamic_properties()
            else:
                raise StopIteration,"Newform does not have eigenvalue a(2)!"
            self._coefficients[2]=ev[2]
            K = ev[2].parent()
        prod = K(1)
        #emf_logger.debug("K= {0}".format(K))        
        F = arith.factor(n)
        for p, r in F:
            (p, r) = (int(p), int(r))
            pr = p**r
            cp = self._coefficients.get(p)
#            emf_logger.debug("c{0} = {1}".format(p,cp))
            if cp is None:
                if ev.has_eigenvalue(p):
                    cp = ev[p]
                elif ev.max_coefficient_in_db() >= p:
                    ev.init_dynamic_properties()
                    cp = ev[p]
            if cp is None:
                raise ValueError,"p={0} is outside the range of computed primes (primes up to {1})! for label:{2}".format(p,max(ev.primes(),self.label))
            if self._coefficients.get(pr) is None:
                if r == 1:
                    c = cp
                else:
                    eps = K(self.parent.character_used_in_computation.value(p))
                    # a_{p^r} := a_p * a_{p^{r-1}} - eps(p)p^{k-1} a_{p^{r-2}}
                    apr1 = self.coefficient_n_recursive(pr//p)
                    #ap = self.coefficient_n_recursive(p)
                    k = self.weight
                    apr2 = self.coefficient_n_recursive(pr//(p*p))
                    c = cp*apr1 - eps*(p**(k-1)) * apr2
                    #emf_logger.debug("c({0})={1}".format(pr,c))
                            #ev[pr]=c
                self._coefficients[pr]=c
            prod *= self._coefficients[pr]
        return prod

    def max_cn(self):
        r"""
        The largest N for which we are sure that we can compute a(n) for all 1<=n<=N
        """
        return self.eigenvalues.max_coefficient_in_db()

        #if self.eigenvalues.primes()==[]:
        #    return 1
        #return max(self.eigenvalues.primes()) + 1

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

    def atkin_lehner_eigenvalues_for_all_cusps(self):
        r"""
        """
        self._atkin_lehner_eigenvalues_at_cusps = {}
        G =Gamma0(self.level)
        for c in Gamma0(self.level).cusps():
            aev = self.atkin_lehner_eigenvalues()
            if aev is None:
                self._atkin_lehner_eigenvalues_at_cusps = None
            else:
                for Q,ev in aev.items():
                    if G.are_equivalent(c,Q/self.level):
                        self._atkin_lehner_eigenvalues_at_cusps[c] = Q,ev
        return self._atkin_lehner_eigenvalues_at_cusps
        
    def url(self):
        return url_for('emf.render_elliptic_modular_forms', level=self.level, weight=self.weight, character=self.character.number, label=self.label)

    def coefficient_field_label(self, pretty = True, check=False):
        r"""
          Returns the LMFDB label of the (absolute) coefficient field (if it exists).
        """
        F = self.coefficient_field
        return field_label(F, pretty, check)

    def coefficient_field_url(self):
        if self.coefficient_field_label(check=True):
            return url_for("number_fields.by_label", label=self.coefficient_field_label(pretty = False))
        else:
            return ''

    def base_field_label(self, pretty = True, check=False):
        r"""
          Returns the LMFDB label of the base field.
        """
        F = self.base_ring
        return field_label(F, pretty, check)

    def base_field_url(self):
        if self.base_field_label(check=True):
            return url_for("number_fields.by_label", label=self.base_field_label(pretty = False))
        else:
            return ''


from sage.all import cached_function,AlphabeticStrings
       
@cached_function
def orbit_label(j):
    x = AlphabeticStrings().gens()
    j1 = j % 26
    label = str(x[j1]).lower()
    j  = (j - j1) / 26 -1
    while j >= 0:
        j1 = j % 26
        label = str(x[j1]).lower() + label
        j = (j - j1) / 26 - 1
    return label



from lmfdb.utils import cache
from lmfdb.modular_forms.elliptic_modular_forms import use_cache

def WebNewForm_cached(level,weight,character,label,parent=None, **kwds):
    if use_cache: 
        M = WebModFormSpace_cached(level, weight, character)
        return M.hecke_orbits[label]
    else:
        F = WebNewForm(level,weight,character,label,**kwds)
        emf_logger.critical("Computed F not using cache!")
    return F



