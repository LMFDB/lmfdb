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

import re

from flask import url_for

from lmfdb.modular_forms.elliptic_modular_forms.backend.web_object import (
     WebObject,
     WebDate,
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

from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import (
        newform_label, 
        space_label, 
        field_label,
        parse_newform_label)

from lmfdb.utils import web_latex_split_on_re, web_latex_split_on_pm

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

from sage.databases.cremona import cremona_letter_code

class WebqExp(WebPoly):

    def __init__(self, name,
                 default_value=None):
        super(WebqExp, self).__init__(name, default_value=default_value)

    def latex(self, prec=None, name=None, keepzeta=False):
        """
        Change the name of the variable in a polynomial.  If keepzeta, then don't change
        the name of zetaN in the defining polynomial of a cyclotomic field.
        (keepzeta not implemented yet)
        """
        if prec is None:
            qe = self.value()
        else:
            qe = self.value()
            if not qe is None:
                qe = qe.truncate_powerseries(prec)
        wl = web_latex_split_on_re(qe)
        if name is not None and self.value().base_ring().absolute_degree()>1:
            oldname = latex(self.value().base_ring().gen())
            subfrom = oldname.strip()
            subfrom = subfrom.replace("\\","\\\\")  
            subfrom = subfrom.replace("{","\\{")   # because x_{0} means something in a regular expression
            if subfrom[0].isalpha():
                subfrom = "\\b" + subfrom
            subto = name.replace("\\","\\\\") + " "
            if keepzeta and "zeta" in subfrom:
                pass  # keep the variable as-is
            else:
                wl = re.sub(subfrom, subto, wl)
            return wl

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

    def to_db(self):
        if not self.value() is None:
            if self.value().base_ring().absolute_degree() > 1:
                return ''
            f = self.value().truncate_powerseries(1001)
            s = str(f)
            n = 1001
            while len(s)>10000 or n==3:
                n = max(n-20,3)
                f = self.value().truncate_powerseries(n)
                s = str(f)
            return s
        else:
            return ''
            
        


class WebEigenvalues(WebObject, CachedRepresentation):

    _key = ['hecke_orbit_label','version']
    _file_key = ['hecke_orbit_label', 'prec','version']
    _collection_name = 'webeigenvalues'

    def __init__(self, hecke_orbit_label, prec=10, update_from_db=True, auto_update = True,init_dynamic_properties=True, **kwargs):
        self._properties = WebProperties(
            WebSageObject('E', None, Matrix),
            WebSageObject('v', None, vector),
            WebDict('meta',value={}),
            WebStr('hecke_orbit_label', value=hecke_orbit_label),
            WebInt('prec', value=prec),
            WebFloat('version', value=float(emf_version),
                     save_to_fs=True, save_to_db=True),
        )

        self.auto_update = True
        self._ap = {}        
        super(WebEigenvalues, self).__init__(
            use_gridfs=True,
            use_separate_db=False,
            update_from_db=update_from_db,
            init_dynamic_properties=init_dynamic_properties,
            **kwargs
            )

    def update_from_db(self, ignore_non_existent = True, \
                       add_to_fs_query=None, add_to_db_query=None):

        self._add_to_fs_query = {'prec': {'$gt': int(self.prec-1)}}
        super(WebEigenvalues,self).update_from_db(ignore_non_existent, add_to_fs_query, add_to_db_query)
        #print "_ap=",self._ap

    def init_dynamic_properties(self):
        emf_logger.debug("E = {0}".format(self.E))
        if not self.E is None and not self.v is None:
            c = multiply_mat_vec(self.E,self.v)
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
        prec_in_db = list(self._file_collection.find(self.key_dict(), ['prec']))
        if len(prec_in_db) == 0:
            return 0
        max_prec_in_db = max(r['prec'] for r in prec_in_db)
        return next_prime(max_prec_in_db)-1
        
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

    _key = ['level', 'weight', 'character', 'label','version']
    _file_key = ['hecke_orbit_label','version']
    if emf_version > 1.3:
        _collection_name = 'webnewforms2'
    else:
        _collection_name = 'webnewforms'

    def __init__(self, level=1, weight=12, character=1, label='a', prec=None, parent=None, update_from_db=True, **kwargs):
        emf_logger.debug("In WebNewForm {0}".format((level,weight,character,label,parent,update_from_db)))
        if isinstance(level,basestring):
            level,weight,character,label = parse_newform_label(level)
        self._reduction = (type(self),(level,weight,character,label),{'parent':parent,'update_from_db':update_from_db})
        if isinstance(character, WebChar):
            character_number = character.number
        else:
            character_number = character
            character = None if parent is None else parent.character
            if not isinstance(label,basestring):
                if isinstance(label,(int,Integer)):
                    label = cremona_letter_code(label)
                else:
                    raise ValueError,"Need label either string or integer! We got:{0}".format(label)

        emf_logger.debug("Before init properties 0")
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
            WebInt('is_cm', required = False),
            WebInt('cm_disc', required = False, default_value=0),
            WebDict('_cm_values',required=False),
            WebBool('is_cuspidal',default_value=True),
            WebDict('satake', required=False),
            WebDict('_atkin_lehner_eigenvalues', required=False),
            WebBool('is_rational'),
            WebPoly('absolute_polynomial'),
            WebFloat('version', value=float(emf_version), save_to_fs=True),
            WebDict('explicit_formulas',required=False),
            WebDate('creation_date',value=None),
            WebModFormSpaceProperty('parent', value=parent,
                                    level = level,
                                    weight = weight,
                                    character = character_number,
                                    update_hecke_orbits=False)
#                                    include_in_update = True if parent is None
#                                    else False),
            )
        emf_logger.debug("After init properties 1")
        super(WebNewForm, self).__init__(
            update_from_db=update_from_db,
            **kwargs
            )
        emf_logger.debug("After init properties 2 prec={0}".format(self.prec))
        # We're setting the WebEigenvalues property after calling __init__ of the base class
        # because it will set hecke_orbit_label from the db first

        ## 
        ## We don't init the eigenvalues (since E*v is slow)
        ## unless we (later) request a coefficient which is not
        ## in self._coefficients
        
        self.eigenvalues = WebEigenvalues(self.hecke_orbit_label, prec = self.prec,init_dynamic_properties=False)
        emf_logger.debug("After init properties 3")

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
        return self._properties['q_expansion'].latex(prec, name, keepzeta=True)
    
    def coefficient(self, n):
        r"""
          Return coefficient nr. n
        """
        #emf_logger.debug("In coefficient: n={0}".format(n))
        if n==0:
            if self.is_cuspidal:
                return 0
        c = self._coefficients.get(n, None)
        if c is None:
            c = self.coefficients([n])[0] 
        return c

    def coefficient_embedding(self,n,i):
        r"""
        Return the i-th complex embedding of coefficient C(n).
        Note that if it is not in the dictionary we compute the embedding (but not the coefficient).
        """
        if not 'values' in self._embeddings:
            self._embeddings['values'] = {}
        if not 'bitprec' in self._embeddings:
            self._embeddings['bitprec'] = {}
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
            raise ValueError,"Embedding nr. {0} does not exist of a number field of degree {1},embc={2}".format(i,self.coefficient_field_degree,embc)
        return embc[i]
        
        
    def coefficients(self, nrange=range(1, 10), save_to_db=False):
        r"""
         Gives the coefficients in a range.
         We assume that the self._ap containing Hecke eigenvalues
         are stored.
        """
        if len(nrange) == 0:
            return []
        if len(nrange) > 1:
            emf_logger.debug("computing coeffs in range {0}--{1}".format(nrange[0],nrange[1]))
        else:
            emf_logger.debug("computing coeffs in range {0}--{0}".format(nrange[0]))
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
                    c = 0
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
        from sage.arith.all import factor
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
        if K.absolute_degree()>1 and K.is_relative():
            KZ = K.base_field()
        else:
            KZ = K
        #emf_logger.debug("K= {0}".format(K))
        F = factor(n)
        for p, r in F:
            #emf_logger.debug("parent_char_val[{0}]={1}".format(p,self.parent.character_used_in_computation.value(p)))
            #emf_logger.debug("char_val[{0}]={1}".format(p,self.character.value(p)))
            (p, r) = (int(p), int(r))
            pr = p**r
            cp = self._coefficients.get(p)
            if cp is None:
                if ev.has_eigenvalue(p):
                    cp = ev[p]
                elif ev.max_coefficient_in_db() >= p:
                    ev.init_dynamic_properties()
                    cp = ev[p]
            #emf_logger.debug("c{0} = {1}, parent={2}".format(p,cp,cp.parent()))
            if cp is None:
                raise IndexError,"p={0} is outside the range of computed primes (primes up to {1})! for label:{2}".format(p,max(ev.primes()),self.label)
            if self._coefficients.get(pr) is None:
                if r == 1:
                    c = cp
                else:
                    # a_{p^r} := a_p * a_{p^{r-1}} - eps(p)p^{k-1} a_{p^{r-2}}
                    apr1 = self.coefficient_n_recursive(pr//p)
                    #ap = self.coefficient_n_recursive(p)
                    apr2 = self.coefficient_n_recursive(pr//(p*p))
                    val = self.parent.character_used_in_computation.value(p)
                    if val == 0:
                        c = cp*apr1
                    else:
                        eps = KZ(val)
                        c = cp*apr1 - eps*(p**(self.weight-1)) * apr2
                    #emf_logger.debug("c({0})={1}".format(pr,c))
                            #ev[pr]=c
                self._coefficients[pr]=c
            try:
                prod *= K(self._coefficients[pr])
            except:
                if hasattr(self._coefficients[pr],'vector'):
                    if len(self._coefficients[pr].vector()) == len(K.power_basis()):
                        prod *= K(self._coefficients[pr].vector())
                    else:
                        emf_logger.debug("vec={0}".format(self._coefficients[pr].vector()))
                        raise ArithmeticError,"Wrong size of vectors!"
                else:
                    raise ArithmeticError,"Can not compute product of coefficients!"
            
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

from lmfdb.utils import cache
from lmfdb.modular_forms.elliptic_modular_forms.backend.emf_utils import multiply_mat_vec
from lmfdb.modular_forms.elliptic_modular_forms import use_cache

def WebNewForm_cached(level,weight,character,label,parent=None, **kwds):
    if use_cache: 
        M = WebModFormSpace_cached(level, weight, character)
        return M.hecke_orbits[label]
    else:
        F = WebNewForm(level,weight,character,label,**kwds)
        emf_logger.debug("Computed F not using cache!")
    return F



