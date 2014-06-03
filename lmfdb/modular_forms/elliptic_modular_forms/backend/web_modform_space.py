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
    if data is None: data = {}
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
    def __init__(self, N=1, k=2, chi=1, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,get_from_db=True):
        r"""
        Init self.

        INPUT:
        - 'k' -- weight
        - 'N' -- level
        - 'chi' -- character
        - 'cuspidal' -- 1 if space of cuspforms, 0 if all modforms
        """
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
            '_galois_decomposition' : [],
            '_newspace' : None,
            '_name' : "{0}.{1}.{2}".format(N,k,chi),
            '_got_ap_from_db' : False ,
            '_version': float(emf_version),
            '_galois_orbit_poly_info':{}
            }
        self.__dict__.update(d)
        #data.update(d)
        emf_logger.debug("Incoming data:{0} ".format(data))
        if get_from_db:            
            d = self.get_from_db()
            emf_logger.debug("Got data:{0} from db".format(d))
        if data is None:
            data = {}
        data.update(d)        
        self.__dict__.update(data)
        
        try:
            if self._group is None:
                self._group = Gamma0(N)
            if self._modular_symbols is None:
                self._modular_symbols = self._get_modular_symbols()
            if self._modular_symbols is None:
                raise ValueError("The space (N,k,chi)={0} is not in the database!".format((self._k,self._N,self._chi)))
                self._dimension = 0
                return 
            if self._newspace is None:
                self._newspace = self._modular_symbols.cuspidal_submodule().new_submodule()
            if self._newforms == {} and self._newspace.dimension()>0:
                for i in self.labels():
                    self._newforms[i]=None
            #if len(self._ap) == 0:
            #    self._ap = self._get_aps(prec=prec)                
        except RuntimeError:
            raise RuntimeError("Could not construct space for (k=%s,N=%s,chi=%s)=" % (k, N, self._chi))
        ### If we can we set these dimensions using formulas
        if(self.dimension() == self.dimension_newspace()):
            self._is_new = True
        else:
            self._is_new = False
        self.insert_into_db()


    ### Elementary properties of self.
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

    ## More complicated properties (might need computation or database calls)
    def modular_symbols(self):
        r"""
        Return the modular symbols of self.
        
        """
        if self._modular_symbols is None:
            self._modular_symbols = self._get_modular_symbols()
        return self._modular_symbols

    def aps(self,prec=-1):
        r"""
        Return a list of aps, that is, Hecke eigenvalues of prime indices, for self.
        """
        if self._ap is None or self._ap == {}:
            self._ap = self._get_aps(prec)
        return self._ap

    def newform_factors(self):
        r"""
        Return newform factors of self.
        """
        if self._newform_factors is None:
            self._newform_factors = self._get_newform_factors()
        return self._newform_factors
                            
    def character_orbit_rep(self,k=None):
        r"""
        Returns canonical representative of the Galois orbit nr. k acting on the ambient space of self.

        """
        if self._character_orbit_rep is None:
            x = self.character().character().galois_orbit()[0]
            self._character_orbit_rep = WebChar(x.modulus(),x.number())
        return self._character_orbit_rep            
    ## Database fetching functions.
            
    def insert_into_db(self):
        r"""
        Insert a dictionary of data for self into the collection WebModularforms.files
        """
        emf_logger.debug("inserting self into db! name={0}".format(self._name))
        db = connect_to_modularforms_db('WebModformspace.files')
        fs = get_files_from_gridfs('WebModformspace')
        s = {'name':self._name,'version':emf_version}
        rec = db.find_one(s)
        if rec:
            id = rec.get('_id')
        else:
            id = None
        if id<>None:
            emf_logger.debug("Removing self from db with id={0}".format(id))
            fs.delete(id)
            
        fname = "webmodformspace-{0:0>5}-{1:0>3}-{2:0>3}".format(self._N,self._k,self._chi) 
        d = self.to_dict()
        d.pop('_ap',None) # Since the ap's are already in the database we don't need them here
        id = fs.put(dumps(d),filename=fname,N=int(self._N),k=int(self._k),chi=int(self._chi),name=self._name)
        emf_logger.debug("inserted :{0}".format(id))
        
    def get_from_db(self):
        r"""
        Fetch dictionary data from the database.
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
        return aplist

    def _get_modular_symbols(self):
        r"""
        Get Modular Symbols from database they exist.
        """
        modular_symbols = connect_to_modularforms_db('Modular_symbols.files')
        key = {'k': int(self._k), 'N': int(self._N), 'cchi': int(self._chi)}
        modular_symbols_from_db  = modular_symbols.find_one(key)
        emf_logger.debug("found ms={0}".format(modular_symbols_from_db))
        if modular_symbols_from_db is None:
            ms = None
        else:
            id = modular_symbols_from_db['_id']
            fs = get_files_from_gridfs('Modular_symbols')
            ms = loads(fs.get(id).read())
            self._id = id
        return ms

  
            
    def _get_newform_factors(self):
        r"""
        Get New form factors from database they exist.
        """
        factors = connect_to_modularforms_db('Newform_factors.files')
        key = {'k': int(self._k), 'N': int(self._N), 'cchi': int(self._chi),}
        factors_from_db  = factors.find(key)
        emf_logger.debug("found factors={0}".format(factors_from_db))
        if factors_from_db.count() == 0:
            facts = []
        else:
            facts = []
            fs = get_files_from_gridfs('Newform_factors')
            for rec in factors_from_db:
                facts.append(loads(fs.get(rec['_id']).read()))
        return facts
    
 
    def __reduce__(self):
        r"""
        Used for pickling.
        """
        data = self.to_dict()
        return(unpickle_wmfs_v1, (self._k, self._N, self._chi, self._cuspidal, self._prec, self._bitprec, data))
            
    def to_dict(self):
        r"""
        Makes a dictionary of the serializable properties of self.
        """
        problematic_keys = ['_galois_decomposition',
                            '_newforms','_newspace',
                            '_modular_symbols',
                            '_new_modular_symbols',
                            '_newform_factors',
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

    def _repr_(self):
        r"""
        Return string representation of self.
        """
        s = 'Space of Cusp forms on ' + str(self.group()) + ' of weight ' + str(self._k)
        s += ' and dimension ' + str(self.dimension())
        return s


    def _computation_too_hard(self,comp='decomp'):
        r"""
        See if the supplied parameters make computation too hard or if we should try to do it on the fly.
        TODO: Actually check times.
        """
        if comp=='decomp':
            if self._N > 50:
                return True
            if self._chi > 1 and self._N > 100:
                return True
            if self._k+self._N  > 100:
                return True
            return False

    # internal methods to generate properties of self
    def galois_decomposition(self):
        r"""
        We compose the new subspace into galois orbits of new cusp forms.
        """
        from sage.monoids.all import AlphabeticStrings
        if(len(self._galois_decomposition) != 0):
            return self._galois_decomposition
        if '_HeckeModule_free_module__decomposition' in self._newspace.__dict__:
            L = self._newspace.decomposition()
        else:
            decomp = self.newform_factors()
            if len(decomp)>0:
                L = filter(lambda x: x.is_new() and x.is_cuspidal(), decomp)
                emf_logger.debug("found L:{0}".format(L))
            elif self._computation_too_hard():
                L = []
                raise IndexError,"No decomposition was found in the database!"
                emf_logger.debug("no decomp in database!")
            else: # compute
                L = self._newspace.decomposition()
                emf_logger.debug("newspace :".format(self._newspace))                                
                emf_logger.debug("computed L:".format(L))
        self._galois_decomposition = L
        # we also label the compnents
        x = AlphabeticStrings().gens()
        for j in range(len(L)):
            if(j < 26):
                label = str(x[j]).lower()
            else:
                j1 = j % 26
                j2 = floor(QQ(j) / QQ(26))
                label = str(x[j1]).lower()
                label = label + str(j2)
            if label not in self._galois_orbits_labels:
                self._galois_orbits_labels.append(label)
        return L

    def galois_orbit_label(self, j):
        r"""
        Return the label of the Galois orbit nr. j
        """
        if(len(self._galois_orbits_labels) == 0):
            self.galois_decomposition()
        return self._galois_orbits_labels[j]

    ###  Dimension formulas, calculates dimensions of subspaces of self.
    def dimension_newspace(self):
        r"""
        The dimension of the subspace of newforms in self.
        """
        if self._dimension_newspace is None:
            if self._cuspidal == 1:
                self._dimension_newspace = self.dimension_new_cusp_forms()
            else:
                self._dimension_newspace = self._newspace.dimension()
        return self._dimension_newspace

    def dimension_oldspace(self):
        r"""
        The dimension of the subspace of oldforms in self.
        """
        if self._cuspidal == 1:
            return self.dimension_cusp_forms() - self.dimension_new_cusp_forms()
        return self.dimension_modular_forms() - self.dimension_newspace()

    def dimension_cusp_forms(self):
        r"""
        The dimension of the subspace of cuspforms in self.
        """
        if self._dimension_cusp_forms is None:
            if self._chi != 1:
                self._dimension_cusp_forms = int(dimension_cusp_forms(self.character().sage_character(), self._k))
            else:
                self._dimension_cusp_forms = int(dimension_cusp_forms(self.level(), self._k))
            # self._modular_symbols.cuspidal_submodule().dimension()
        return self._dimension_cusp_forms

    def dimension_modular_forms(self):
        r"""
        The dimension of the space of modular forms.
        """
        if self._dimension_modular_forms is None:
            if self._chi != 1:
                self._dimension_modular_forms = int(dimension_modular_forms(self.character().sage_character(), self._k))
            else:
                self._dimension_modular_forms = int(dimension_modular_forms(self._N, self._k))
            # self._dimension_modular_forms=self._modular_symbols.dimension()
        return self._dimension_modular_forms

    def dimension_new_cusp_forms(self):
        r"""
        The dimension of the subspace of new cusp forms.
        """
        if self._dimension_new_cusp_forms is None:
            if self._chi != 1:
                self._dimension_new_cusp_forms = int(dimension_new_cusp_forms(self.character().sage_character(), self._k))
            else:
                self._dimension_new_cusp_forms = int(dimension_new_cusp_forms(self._N, self._k))
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
        r""" Return the Sturm bound of S_k(N,xi), i.e. the number of coefficients necessary to determine a form uniquely in the space.
        """
        if self._sturm_bound is None:
            self._sturm_bound = self._modular_symbols.sturm_bound()
        return self._sturm_bound

    def labels(self):
        r"""

        """
        if(len(self._galois_orbits_labels) > 0):
            return self._galois_orbits_labels
        else:
            self.galois_decomposition()
            return self._galois_orbits_labels

    def f(self, i):
        r"""
        Return function f in the set of newforms on self. Here i is either a label, e.g. 'a' or an integer.
        """
        if (isinstance(i, int) or i in ZZ):
            if i <len(self.labels()):
                i = self.labels()[i]
            else:
                raise IndexError,"Form nr. {i} does not exist!".format(i=i)
        if not i in self._galois_orbits_labels:
            raise IndexError,"Form wih label: {i} does not exist!".format(i=i)
        if self._newforms.has_key(i) and self._newforms[i]<>None:
            F = self._newforms[i]
        else:
            F = WebNewForm(N=self._N,k=self._k,  chi=self._chi, parent=self, label=i)
        emf_logger.debug("returning F! :{0}".format(F))
        return F

    def galois_orbit(self, orbit,prec=None):
        r"""
        Return the q_eigenform nr. orbit in self
        """
        if prec is None:
            prec = self._prec
        return self.galois_decomposition()[orbit].q_eigenform(prec, 'x')

    def oldspace_decomposition(self):
        r"""
        Get decomposition of the oldspace in self into submodules.

        """
        if(len(self._oldspace_decomposition) != 0):
            return self._oldspace_decomposition
        N = self._N
        k = self._k
        M = self._modular_symbols.cuspidal_submodule()
        L = list()
        L = []
        check_dim = self.dimension_newspace()
        if(check_dim == self.dimension()):
            return L
        if(self._verbose > 1):
            emf_logger.debug("check_dim:={0}".format(check_dim))
        for d in divisors(N):
            if(d == 1):
                continue
            q = N.divide_knowing_divisible_by(d)
            if(self._verbose > 1):
                emf_logger.debug("d={0}".format(d))
            # since there is a bug in the current version of sage
            # we have to try this...
            try:
                O = M.old_submodule(d)
            except AttributeError:
                O = M.zero_submodule()
            Od = O.dimension()
            if(self._verbose > 1):
                emf_logger.debug("O={0}".format(O))
                emf_logger.debug("Od={0}".format(Od))
            if(d == N and k == 2 or Od == 0):
                continue
            if self.character().is_trivial():
                # S=ModularSymbols(ZZ(N/d),k,sign=1).cuspidal_submodule().new_submodule(); Sd=S.dimension()
                emf_logger.debug("q={0},{1}".format(q, type(q)))
                emf_logger.debug("k={0},{1}".format(k, type(k)))
                Sd = dimension_new_cusp_forms(q, k)
                if(self._verbose > 1):
                    emf_logger.debug("Sd={0}".format(Sd))
                if Sd > 0:
                    mult = len(divisors(ZZ(d)))
                    check_dim = check_dim + mult * Sd
                    L.append((q, 0, mult, Sd))
            else:
                xd = self.character().decomposition()
                for xx in xd:
                    if xx.modulus() == q:
                        Sd = dimension_new_cusp_forms(xx, k)
                        if Sd > 0:
                            # identify this character for internal storage... should be optimized
                            x_k = self.conrey_character(xx).number()
                            mult = len(divisors(ZZ(d)))
                            check_dim = check_dim + mult * Sd
                            L.append((q, x_k, mult, Sd))
            if(self._verbose > 1):
                emf_logger.debug("mult={0},N/d={1},Sd={2}".format(mult, ZZ(N / d), Sd))
                emf_logger.debug("check_dim={0}".format(check_dim))
        check_dim = check_dim - M.dimension()
        if(check_dim != 0):
            raise ArithmeticError("Something wrong! check_dim=%s" % check_dim)
        return L

    ### Printing functions
    def print_oldspace_decomposition(self):
        r""" Print the oldspace decomposition of self.
        """
        if(len(self._oldspace_decomposition) == 0):
            self._oldspace_decomposition = self.oldspace_decomposition()

        O = self._oldspace_decomposition

        n = 0
        s = ""
        if(self._chi != 1):
            s = "\[S_{%s}^{old}(%s,{%s}) = " % (self._k, self._N, self.conrey_character_name())
        else:
            s = "\[S_{%s}^{old}(%s) = " % (self._k, self._N)
        if(len(O) == 0):
            s = s + "\left\{ 0 \\right\}"
        for n in range(len(O)):
            (N, chi, m, d) = O[n]
            if(self._chi != 1):
                s = s + " %s\cdot S_{%s}^{new}(%s,\chi_{%s}({%s}, \cdot))" % (m, self._k, N, N, chi)
            else:
                s = s + " %s\cdot S_{%s}^{new}(%s)" % (m, self._k, N)
            if(n < len(O) - 1 and len(O) > 1):
                s = s + "\\oplus "
        s = s + "\]"
        return s

    def get_all_galois_orbit_info(self, prec=10, qexp_max_len=50):
        r"""
        Set the info for all galois orbits (newforms) in list of  dictionaries.
        """
        emf_logger.debug('In get_all_galois_orbit_info')
        from sage.monoids.all import AlphabeticStrings
        L = self.galois_decomposition()
        emf_logger.debug('have Galois decomposition: L={0}'.format(L))
        if(len(L) == 0):
            self._orbit_info = []
        x = AlphabeticStrings().gens()
        res = []
        for j in range(len(self._galois_decomposition)):
            o = dict()
            label = self._galois_orbits_labels[j]
            o['label'] = label
            full_label = "{0}.{1}".format(self.level(), self.weight())
            if self._chi != 1:
                full_label = full_label + ".{0}".format(self._chi)
            full_label = full_label + label
            o['full_label'] = full_label
            o['url'] = url_for('emf.render_elliptic_modular_forms', level=self.level(
            ), weight=self.weight(), label=o['label'], character=self._chi)
            o['dim'] = self._galois_decomposition[j].dimension()
            emf_logger.debug('dim({0}={1})'.format(j, o['dim']))
            oi = self.galois_orbit_poly_info(j, prec)
            emf_logger.debug('orbit pol. info ={0}'.format(oi))            
            poly, disc, is_relative = oi
            o['poly'] = "\( {0} \)".format(latex(poly))
            o['disc'] = "\( {0} \)".format(latex(disc))
            o['is_relative'] = is_relative
            emf_logger.debug('before qexp!')
            o['qexp'] = self.qexp_orbit_as_string(j, prec, qexp_max_len)
            emf_logger.debug('qexp({0}={1})'.format(j, o['qexp']))
            res.append(o)
        return res

    def print_galois_orbits(self, prec=10, qexp_max_len=50):
        r"""
        Print the Galois orbits of self.

        """
        from sage.monoids.all import AlphabeticStrings
        L = self.galois_decomposition()
        emf_logger.debug("L=".format(L))
        if(len(L) == 0):
            return ""
        x = AlphabeticStrings().gens()
        tbl = dict()
        tbl['headersh'] = ["dim.", "defining poly.", "discriminant", "\(q\)-expansion of eigenform"]
        tbl['atts'] = "border=\"1\""
        tbl['headersv'] = list()
        tbl['data'] = list()
        tbl['corner_label'] = ""
        is_relative = False
        for j in range(len(self._galois_decomposition)):
            label = self._galois_orbits_labels[j]
            # url="?weight="+str(self.weight())+"&level="+str(self.level())+"&character="+str(self.character())+"&label="+label
            url = url_for('emf.render_elliptic_modular_forms', level=self.level(),
                          weight=self.weight(), label=label, character=self._chi)
            header = "<a href=\"" + url + "\">" + label + "</a>"
            tbl['headersv'].append(header)
            dim = self._galois_decomposition[j].dimension()
            orbit = self.galois_orbit(j, prec)
            # we might to truncate the power series
            # if it is too long
            cc = orbit.coefficients()

            slist = list()
            i = 1
            # try to split up the orbit if too long
            s = str(orbit)
            ss = "\(" + my_latex_from_qexp(s) + "\)"
            ll = 0
            if len(s) > qexp_max_len:
                emf_logger.debug("LEN > MAX!")
                sl = ss.split('}')
                for i in range(len(sl) - 1):
                    sss = ''
                    if i > 0 and i < len(sl) - 1:
                        sss = '\('
                    sss += sl[i]
                    if i < len(sl) - 2:
                        sss += '}\)'
                    else:
                        sss += '})\)'
                    ll = ll + len(str(sl[i]))
                    if ll > qexp_max_len:
                        ll = 0
                        sss += "<br>"
                    slist.append(sss)
            else:
                slist.append(ss)
            
            K = orbit.base_ring()
            if K.absolute_degree() == 1:
                poly = ZZ['x'].gen()
                disc = '1'
            else:
                poly,disc,is_relative = self.galois_orbit_poly_info(j)
                #poly = K.defining_polynomial()
                #if(K.is_relative()):
                #    disc = factor(K.relative_discriminant().absolute_norm())
                #    is_relative = True
                #else:
                #    disc = factor(K.discriminant())
            tbl['data'].append([dim, poly, disc, slist])
        # we already formatted the table
        tbl['data_format'] = {3: 'html'}
        tbl['col_width'] = {3: '200'}
        tbl['atts'] = 'width="200" border="1"'
        s = html_table(tbl)
        if(is_relative):
            s = s + "<br><small>For relative number fields we list the absolute norm of the discriminant)</small>"
        return s

    def qexp_orbit_as_string(self, orbitnr, prec=20, qexp_max_len=50):
        orbit = self.galois_orbit(orbitnr, prec)
        if not orbit:
            return ''
        # if it is too long
        cc = orbit.coefficients()
        slist = list()
        i = 1
        # try to split up the orbit if too long
        s = str(orbit)
        ss = "\(" + my_latex_from_qexp(s) + "\)"
        ll = 0
        if len(s) > qexp_max_len:
            emf_logger.debug("LEN > MAX!")
            sl = ss.split('}')
            for i in range(len(sl) - 1):
                sss = ''
                if i > 0 and i < len(sl) - 1:
                    sss = '\('
                sss += sl[i]
                if i < len(sl) - 2:
                    sss += '}\)'
                else:
                    sss += '})\)'
                ll = ll + len(str(sl[i]))
                if ll > qexp_max_len:
                    ll = 0
                    sss += "<br>"
                slist.append(sss)
        else:
            slist.append(ss)
        return ss

    def galois_orbit_poly_info(self, orbitnr, prec=10):
        r"""
        Set the information about the defining polynomial of a Galois orbit.
        """
        if self._galois_orbit_poly_info.get(orbitnr)<>None:
            return self._galois_orbit_poly_info[orbitnr]
        orbit = self.galois_orbit(orbitnr, prec)
        emf_logger.debug("in orbit_poly_info orbit:{0}".format(orbit))
        if not orbit:
            return '',0,False
        K = orbit.base_ring()
        is_relative = False
        disc = 1
        if K.absolute_degree() == 1:
            poly = ZZ['x'].gen()
            disc = '1'
        else:
            emf_logger.debug("before poly")                    
            poly = K.defining_polynomial()
            emf_logger.debug("after poly")                                
            if(K.is_relative()):
                disc = factor(K.relative_discriminant().absolute_norm())
                is_relative = True
            else:
                disc = factor(K.discriminant())
        emf_logger.debug("end orbit_poly_info")
        self._galois_orbit_poly_info[orbitnr] = poly, disc, is_relative
        self.insert_into_db()
        return self._galois_orbit_poly_info[orbitnr]

    def print_geometric_data(self):
        r""" Print data about the underlying group.
        """

        return print_geometric_data_Gamma0N(self.level())
        # s="<div>"
        # s=s+"\("+latex(G)+"\)"+" : "
        # s=s+"\((\\textrm{index}; \\textrm{genus}, \\nu_2,\\nu_3)=("
        # s=s+str(G.index())+";"+str(G.genus())+","
        # s=s+str(G.nu2())+","+str(G.nu3())
        # s=s+")\)</div>"
        # return s

    def present(self):
        r"""
        Present self.
        """
        if(self._is_new):
            new = "^{new}"
        else:
            new = ""
        if(self._chi == 1):
            s = "<h1>\(S" + new + "_{%s}(%s)\)</h1>" % (self._k, self._N)
        else:
            s = "<h1>\(S" + new + "_{%s}(%s,\chi_{%s})\)</h1>" % (self._k, self._N, self._chi)
        s = s + "<h2>Geometric data</h2>"
        s = s + self.print_geometric_data()
        s = s + "<h2>Galois orbits</h2>"
        s = s + self.print_galois_orbits()
        if(not self._is_new):
            s = s + "<h2>Decomposition of the Oldspace</h2>"
            s = s + self.print_oldspace_decomposition()
        return s
