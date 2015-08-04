
# -*- coding: utf-8 -*-
#*****************************************************************************
#  Copyright (C) 2010 Fredrik Strömberg <fredrik314@gmail.com>,
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


TODO:
Fix complex characters. I.e. embedddings and galois conjugates in a consistent way.

"""
from sage.all import ZZ, QQ, DirichletGroup, CuspForms, Gamma0, ModularSymbols, Newforms, trivial_character, is_squarefree, divisors, RealField, ComplexField, prime_range, I, gcd, Cusp, Infinity, ceil, CyclotomicField, exp, pi, primes_first_n, euler_phi, RR, prime_divisors, Integer, matrix,NumberField,PowerSeriesRing
from sage.rings.power_series_poly import PowerSeries_poly
from sage.all import Parent, SageObject, dimension_new_cusp_forms, vector, dimension_modular_forms, dimension_cusp_forms, EisensteinForms, Matrix, floor, denominator, latex, is_prime, prime_pi, next_prime, previous_prime,primes_first_n, previous_prime, factor, loads,save,dumps,deepcopy
import re
import yaml
from flask import url_for

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

try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

db_name = 'modularforms2'
def connect_to_modularforms_db():
    try:
        C = lmfdb.base.getDBConnection()
    except Exception as e:
        emf_logger.critical("Could not connect to Database! C={0}. Error: {1}".format(C,e.message))
    if db_name not in C.database_names():
        emf_logger.critical("Database {0} does not exist at connection {1}".format(db_name,C))
    return C[db_name]


def WebNewForm(N=1, k=2, chi=0, label='', prec=10, bitprec=53, display_bprec=26, parent=None, data=None, compute=False, verbose=-1,get_from_db=True):
    r"""
    Constructor for WebNewForms with added 'nicer' error message.
    """
    ## First check
    if chi == 0:
        if k % 2 == 1:
            emf_logger.debug("Only zero function here with N,k,chi,label={0}.".format( (N,k,chi,label)))
            return 0
    if not data is None:
        emf_logger.debug("incoming data in construction : {0}".format(data.get('N'),data.get('k'),data.get('chi')))
    else:
        emf_logger.debug("No incoming data!")
    try: 
        F = WebNewForm_class(N=N, k=k, chi=chi, label=label, prec=prec, bitprec = bitprec, display_bprec=display_bprec, parent = parent, data = data, compute = compute, verbose = verbose,get_from_db = get_from_db)
    except (ArithmeticError,ValueError) as e:#Exception as e:
        emf_logger.debug("Could not construct WebNewForm with N,k,chi,label={0}. Error: {1}".format( (N,k,chi,label),e))
        raise IndexError,"We are very sorry. The sought function could not be found in the database."
    return F


def WebModFormSpace(N=1, k=2, chi=0, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,**kwds):
    r"""
    Constructor for WebNewForms with added 'nicer' error message.
    """
    if cuspidal <> 1:
        raise IndexError,"We are very sorry. There are only cuspidal spaces currently in the database!"
    try: 
        F = WebModFormSpace_class(N=N, k=k, chi=chi, cuspidal=cuspidal, prec=prec, bitprec=bitprec, data=data, verbose=verbose,**kwds)
    except Exception as e:
        emf_logger.debug("Could not construct WebModFormSpace with N,k,chi = {0}. Error: {1}".format( (N,k,chi),e.message))
        raise IndexError,"We are very sorry. The sought space could not be found in the database."
    return F


class WebModFormSpace_class(object):
    r"""
    Space of cuspforms to be presented on the web.
        G  = NS.

    EXAMPLES::

    sage: WS=WebModFormSpace(2,39)


    """
    def __init__(self, N=1, k=2, chi=0, cuspidal=1, prec=10, bitprec=53, data=None, verbose=0,get_from_db=True):
        r"""
        Init self.

        INPUT:
        - 'k' -- weight
        - 'N' -- level
        - 'chi' -- character
        - 'cuspidal' -- 1 if space of cuspforms, 0 if all modforms
        """
        emf_logger.debug("WebModFormSpace with k,N,chi={0}".format( (k,N,chi)))
        if data is None:
            data = {}
        d = {
            '_N': int(N),
            '_k': int(k),
            '_chi':int(chi),
            '_cuspidal' : int(cuspidal),
            '_prec' : int(prec),
            '_ap' : {}, '_group' : None,
            '_character' : None,
            '_conrey_character' : None,
            '_sage_character_no' : int(chi),
            '_conrey_character_no' : None,
            '_conrey_character_name' : None,
            '_character_order' : None,
            '_character_conductor' : None,
            '_modular_symbols' : None,
            '_sturm_bound' : None,
            '_newspace' : None,
            '_newforms' : {},
            '_new_modular_symbols' : None,
            '_galois_decomposition' : [],
            '_galois_orbits_labels' : [],
            '_oldspace_decomposition' : [],
            '_verbose' : int(verbose),
            '_bitprec' : int(bitprec),
            '_dimension_newspace' : None,
            '_dimension_cusp_forms' : None,
            '_dimension_modular_forms' : None,
            '_dimension_new_cusp_forms' : None,
            '_dimension_new_modular_symbols' : None,
            '_galois_decomposition' : [],
            '_newspace' : None,
            '_character' : None,
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
        if data == None:
            data = {}
        data.update(d)        
        self.__dict__.update(data)
        
        try:
            if self._group == None:
                self._group = Gamma0(N)
            if self._modular_symbols == None:
                self._modular_symbols = self._get_modular_symbols()
            if self._modular_symbols == None:
                raise ValueError("The space (N,k,chi)={0} is not in the database!".format((self._k,self._N,self._chi)))
                self._dimension = 0
                return 
            if self._newspace == None:
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
        
    def insert_into_db(self):
        r"""
        Insert a dictionary of data for self into the collection WebModularforms.files
        """
        emf_logger.debug("inserting self into db! name={0}".format(self._name))
        C = lmfdb.base.getDBConnection()
        fs = gridfs.GridFS(C[db_name], 'WebModformspace')
        collection = C[db_name].WebModformspace.files
        s = {'name':self._name}
        rec = collection.find_one(s)
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
        C = lmfdb.base.getDBConnection()
        collection = C[db_name].WebModformspace.files
        s = {'name':self._name}
        emf_logger.debug("Looking in DB for rec={0}".format(s))
        f = C[db_name].WebModformspace.files.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = gridfs.GridFS(C[db_name],'WebModformspace')
            f = fs.get(id)
            emf_logger.debug("Getting rec={0}".format(f))
            d = loads(f.read())
            return d
        return {}
            
    def _get_character(self,k=None):
        r"""
        Returns canonical representative of the Galois orbit nr. k acting on the ambient space of self.

        """
        D = DirichletGroup(self.group().level())
        G = D.galois_orbits(reps_only=True)
        if k==None:
            k = self._sage_character_no
        try:
            emf_logger.debug("k={0},G[k]={1}".format(k, G[k]))
            return G[k]
        except IndexError:
            emf_logger.critical("Got character no. {0}, which are outside the scope of Galois orbits of the characters mod {1}!".format(k, self.group().level()))
            raise IndexError,"There is no Galois orbit of this index!"

    def _get_conrey_character(self):
        r"""
        Return the Dirichlet character of self as an element of DirichletGroup_conrey.
        """
        if self._conrey_character <> None:
            return self._conrey_character
        Dc = DirichletGroup_conrey(self._N)
        for c in Dc:
            if c.sage_character() == self.character():
                self._conrey_character = c
                break
        return self._conrey_character
        
    def db_collection(self,collection):
        r"""
        Return a handle to an existing collection from the database.

        """
        D = connect_to_modularforms_db()
        if collection not in D.collection_names():
            emf_logger.critical("Collection {0} is not in database {1} at connection {2}".format(collection,db_name,C))
        return D[collection]

    def gridfs_collection(self,collection):
        r"""
        Return a file handle to a gridfs collection.
        """
        if '.files' in collection:
            collection = collection.split(".")[0]
        D = connect_to_modularforms_db()
        return gridfs.GridFS(D, collection)
        
    def _get_aps(self, prec=-1):
        r"""
        Get aps from database if they exist.
        """
        ap_files = self.db_collection('ap.files')
        key = {'k': int(self._k), 'N': int(self._N), 'chi': int(self._chi)}
        key['prec'] = {"$gt": int(prec - 1)}
        ap_from_db  = ap_files.find(key).sort("prec")
        emf_logger.debug("finds={0}".format(ap_from_db))
        emf_logger.debug("finds.count()={0}".format(ap_from_db.count()))
        fs = self.gridfs_collection('ap')
        aplist = {}
        for i in range(len(self.labels())):
            aplist[self.labels()[i]]={}
        for rec in ap_from_db:
            emf_logger.debug("rec={0}".format(rec))
            ni = rec.get('newform')
            if ni == None:
                for a in self.labels():
                    aplist[a][prec]=None
                return aplist
            a = self.labels()[ni]
            cur_prec = rec['prec']
            if aplist.get(a,{}).get(cur_prec,None)==None:
                aplist[a][prec]=loads(fs.get(rec['_id']).read())
            if cur_prec > prec and prec>0: # We are happy with these coefficients.
                return aplist
        return aplist

    def aps(self,prec=-1):
        if self._ap == None or self._ap == {}:
            self._ap = self._get_aps(prec)
        return self._ap

    def _get_modular_symbols(self):
        r"""
        Get Modular Symbols from database they exist.
        """
        modular_symbols = self.db_collection('Modular_symbols.files')
        key = {'k': int(self._k), 'N': int(self._N), 'chi': int(self._chi)}
#        key = {'hecke_orbit_label':"{0}.{1}.{2}".format(self._N,self._k,self._chi)}
        modular_symbols_from_db  = modular_symbols.find_one(key)
        emf_logger.debug("found ms={0} for key:{1}".format(modular_symbols_from_db,key))
        if modular_symbols_from_db == None:
            ms = None
        else:
            id = modular_symbols_from_db['_id']
            fs = self.gridfs_collection('Modular_symbols')
            ms = loads(fs.get(id).read())
            self._id = id
        return ms

    def _get_newform_factors(self):
        r"""
        Get New form factors from database they exist.
        """
        factors = self.db_collection('Newform_factors.files')
        key = {'k': int(self._k), 'N': int(self._N), 'chi': int(self._chi),}
        factors_from_db  = factors.find(key)
        emf_logger.debug("found factors={0}".format(factors_from_db))
        if factors_from_db.count() == 0:
            facts = []
        else:
            facts = []
            fs = self.gridfs_collection('Newform_factors')
            for rec in factors_from_db:
                factor =  loads(fs.get(rec['_id']).read())
                if factor.__dict__.get('_ModularSymbolsSubspace__is_cuspidal',False):
                    facts.append(factor)
        return facts
    
    
    def __reduce__(self):
        r"""
        Used for pickling.
        """
        data = self.to_dict()
        return(unpickle_wmfs_v1, (self._k, self._N, self._chi, self._cuspidal, self._prec, self._bitprec, data))
            
            
    def __reduce__(self):
        r"""
        Used for pickling.
        """
        data = self.to_dict()
        return(unpickle_wmfs_v1, (self._k, self._N, self._chi, self._cuspidal, self._prec, self._bitprec, data))

    def _save_to_file(self, file):
        r"""
        Save self to file.
        """
        self.save(file, compress=None)

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

    def _repr_(self):
        s = 'Space of Cusp forms on ' + str(self.group()) + ' of weight ' + str(self._k)
        s += ' and dimension ' + str(self.dimension())
        return s
        # return str(self._fullspace)

    def _computation_too_hard(self,comp='decomp'):
        r"""
        See if the supplied parameters make computation too hard or if we should try to do it on the fly.
        TODO: Actually check times.
        """
        if comp=='decomp':
            if self._N > 50:
                return True
            if self._chi > 0 and self._N > 100:
                return True
            if self._k+self._N  > 100:
                return True
            return False
    # internal methods to generate properties of self
    def galois_decomposition(self):
        r"""
        We compose the new subspace into galois orbits.
        """
        from sage.monoids.all import AlphabeticStrings
        if(len(self._galois_decomposition) != 0):
            return self._galois_decomposition
        if '_HeckeModule_free_module__decomposition' in self._newspace.__dict__:
            L = self._newspace.decomposition()
        else:
            decomp = self._get_newform_factors()
            if len(decomp)>0:
                L = filter(lambda x: x.is_new() and x.is_cuspidal(), decomp)
                emf_logger.debug("computed L:{0}".format(L))
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
        if(len(self._galois_orbits_labels) == 0):
            self.galois_decomposition()
        return self._galois_orbits_labels[j]

    # return specific properties of self
    ## By old and newforms we check if self is cuspidal or not
    def dimension_newspace(self):
        if self._dimension_newspace is None:
            if self._cuspidal == 1:
                self._dimension_newspace = self.dimension_new_cusp_forms()
            else:
                self._dimension_newspace = self._newspace.dimension()
        return self._dimension_newspace

    def dimension_oldspace(self):
        if self._cuspidal == 1:
            return self.dimension_cusp_forms() - self.dimension_new_cusp_forms()
        return self.dimension_modular_forms() - self.dimension_newspace()

    def dimension_cusp_forms(self):
        if self._dimension_cusp_forms is None:
            if self._chi != 0:
                self._dimension_cusp_forms = int(dimension_cusp_forms(self.character(), self._k))
            else:
                self._dimension_cusp_forms = int(dimension_cusp_forms(self.level(), self._k))
            # self._modular_symbols.cuspidal_submodule().dimension()
        return self._dimension_cusp_forms

    def dimension_modular_forms(self):
        if self._dimension_modular_forms is None:
            if self._chi != 0:
                self._dimension_modular_forms = int(dimension_modular_forms(self.character(), self._k))
            else:
                self._dimension_modular_forms = int(dimension_modular_forms(self._N, self._k))
            # self._dimension_modular_forms=self._modular_symbols.dimension()
        return self._dimension_modular_forms

    def dimension_new_cusp_forms(self):
        if self._dimension_new_cusp_forms is None:
            if self._chi != 0:
                self._dimension_new_cusp_forms = int(dimension_new_cusp_forms(self.character(), self._k))
            else:
                self._dimension_new_cusp_forms = int(dimension_new_cusp_forms(self._N, self._k))
        return self._dimension_new_cusp_forms

    def dimension(self):
        r"""
        By default return old and newspace together
        """
        if self._cuspidal == 1:
            return self.dimension_cusp_forms()
        elif self._cuspidal == 0:
            return self.dimension_modular_forms()
        else:
            raise ValueError("Do not know the dimension of space of type {0}".format(self._cuspidal))

    def weight(self):
        return self._k

    def level(self):
        return self._N

    def character(self):
        if self._character == None:
            self._character = self._get_character()
        return self._character

    def conrey_character(self):
        if self._conrey_character == None:
            self._get_conrey_character()
        return self._conrey_character

    def conrey_character_number(self):
        if not (self._conrey_character_no >0):
          self._conrey_character_no = self.conrey_character().number()
        return self._conrey_character_no
    
    def conrey_character_name(self):
        if self._conrey_character_name == None:
            self._conrey_character_name = "\chi_{" + str(self._N) + "}(" + str(self.conrey_character_number()) + ",\cdot)"
        return self._conrey_character_name 

    def character_order(self):
        if self._character_order == None:
            self._character_order = self.character().order()
        return self._character_order
            
    def character_conductor(self):
        if self._character_conductor == None:
           self._character_conductor = self.character().conductor()
        return self._character_conductor

    def group(self):
        return self._group

    def sturm_bound(self):
        r""" Return the Sturm bound of S_k(N,xi), i.e. the number of coefficients necessary to determine a form uniquely in the space.
        """
        if self._sturm_bound == None:
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

    def galois_orbit(self, orbit, prec=None):
        r"""
        Return the q_eigenform nr. orbit in self
        """
        if(prec is None):
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
            q = ZZ(N).divide_knowing_divisible_by(d)
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
        if(self._chi != 0):
            s = "\[S_{%s}^{old}(%s,{%s}) = " % (self._k, self._N, self.conrey_character_name())
        else:
            s = "\[S_{%s}^{old}(%s) = " % (self._k, self._N)
        if(len(O) == 0):
            s = s + "\left\{ 0 \\right\}"
        for n in range(len(O)):
            (N, chi, m, d) = O[n]
            if(self._chi != 0):
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
            full_label = "{0}.{1}.{2}".format(self.level(), self.weight(),self.conrey_character_number())
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
        if(self._chi == 0):
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


class WebNewForm_class(object):
    r"""
    Class for representing a (cuspidal) newform on the web.
    TODO: Include the computed data in the original database so we won't have to compute here at all.
    """
    def __init__(self, N=1, k=2, chi=0, label='', prec=10, bitprec=53, display_bprec=26,parent=None, data=None, compute=False, verbose=-1,get_from_db=True):
        r"""
        Init self as form with given label in S_k(N,chi)
        """
        if data is None:
            data = {}
        emf_logger.debug("WebNewForm with N,k,chi,label={0}".format( (N,k,chi,label)))
        # Set defaults.
        emf_logger.debug("incoming data in construction : {0},{1},{2},{3}".format(data.get('N'),data.get('k'),data.get('chi'),data.get('label')))

        #emf_logger.debug("incoming data: {0}".format(data))
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
            '_embeddings' : [],
            '_embeddings_latex' : [],            
            '_base_ring': None,
            '_base_ring_as_dict' : {},
            '_coefficient_field': None,
            '_coefficient_field_as_dict': {},
            '_as_polynomial_in_E4_and_E6' : None,
            '_twist_info' : [],
            '_is_CM' : [],
            '_cm_values' : {},
            '_satake' : {},
            '_dimension' : -1,
            '_is_rational' : None,
            '_degree' : 0,
            '_absolute_degree' : 0,
            '_relative_degree' : 0,
            '_character' : None,
            '_conrey_character' : None,
            '_conrey_character_no' : -1,
            '_sage_character_no' : -1,
            '_name' : "{0}.{1}.{2}{3}".format(N,k,chi,label),
            '_version': float(emf_version)            
            }
        self.__dict__.update(d)
        emf_logger.debug("label = {0}".format(label))
        emf_logger.debug("label = {0}".format(self._label))
        if self._label<>'' and get_from_db:            
            d = self.get_from_db(self._N,self._k,self._chi,self._label)
            emf_logger.debug("Got data:{0} from db".format(d))
            data.update(d)
        #emf_logger.debug("data: {0}".format(data))
        self.__dict__.update(data)
        if not isinstance(self._parent,WebModFormSpace_class):
            if self._verbose > 0:
                emf_logger.debug("compute parent! label={0}".format(label))
            self._parent = WebModFormSpace(N, k,chi, data=self._parent)
            emf_logger.debug("finished computing parent")
        if self._parent.dimension_newspace()==0:
            self._dimension=0
            return 
        self._check_consistency_of_labels()
        emf_logger.debug("name={0}".format(self._name))
        if compute: ## Compute all data we want.
            emf_logger.debug("compute")
            self._update_aps(insert_in_db=False)
            emf_logger.debug("compute q-expansion")
            self.q_expansion_embeddings(prec, bitprec,insert_in_db=False)
            emf_logger.debug("as polynomial")
            if self._N == 1:
                self.as_polynomial_in_E4_and_E6(insert_in_db=False)
            emf_logger.debug("compute twist info")
            self.twist_info(prec,insert_in_db=False)
            emf_logger.debug("compute CM-values")
            self.cm_values(insert_in_db=False)
            emf_logger.debug("check  CM of self")
            self.is_CM(insert_in_db=False)
            emf_logger.debug("compute Satake parameters")
            self.satake_parameters(insert_in_db=False)
            self._dimension = self.as_factor().dimension()  # 1 # None
            #c = self.coefficients(self.prec(),insert_in_db=False)
        emf_logger.debug("before end of __init__ f={0}".format(self.as_factor()))
        emf_logger.debug("before end of __init__ type(f)={0}".format(type(self.as_factor())))
        emf_logger.debug("done __init__")
        self.insert_into_db()

    def _check_consistency_of_labels(self):
        if self._label not in self.parent().labels():
            raise ValueError,"There does not exist a newform orbit of the given label: {0}!".format(self._label)
        # emf_logger.debug(" labels= {0}".format(self._parent._galois_orbits_labels))
        # emf_logger.debug(" fi= {0}".format(self._fi))        
        # if self._parent == None:
        #     raise ValueError,"Need parent to check labels!"
        # try:
        #     if self._fi < 0:
        #         emf_logger.debug(" labels= {0}".format(self._parent._galois_orbits_labels))
        #         self._fi = self._parent._galois_orbits_labels.index(self._label)
        #         emf_logger.debug(" fi = {0}".format(self._fi))
        #     if self._label=='':
        #         self._label = self._parent._galois_orbits_labels[self._fi]
        #     if not self._label == self._parent._galois_orbits_labels[self._fi]:
        #         raise ValueError
        # except (ValueError,KeyError):
        #     raise ValueError,"There does not exist a newform orbit of the given label: {0} and number:{1}!".format(self._label,self._fi)
        return True

    def _set_character(self):
        r"""
        Initialize the character associated to self.
        """
        if self._parent == None:
            raise ValueError,"Need parent to check labels!"
        if self._conrey_character_no>0 and self._conrey_character==None:
            self._conrey_character =  DirichletCharacter_conrey(DirichletGroup_conrey(self._N),self._conrey_character_no)
        else:
            self._conrey_character = self._parent.conrey_character()
            self._conrey_character_no = self._parent.conrey_character_number()
        self._character = self.parent().character()

        if self._character == None or self._conrey_character==None:
            self._character = DirichletGroup(self._N).galois_orbits(reps_only=True)[self._chi]
            Dc = DirichletGroup_conrey(self._N)
            for c in Dc:
                if c.sage_character() == self._character:
                    self._conrey_character = c
                    break
            self._conrey_character_no  = self._conrey_character.number()
            self._sage_character_no  = self._chi
        
    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        return self._name == other._name


    def get_from_db(self,N,k,chi,label):
        C = lmfdb.base.getDBConnection()
        collection = C[db_name].WebNewforms.files
        s = {'N':int(N),'k':int(k),'chi':int(chi),'label':label,'version':float(emf_version)}
        emf_logger.debug("Looking in DB for rec={0}".format(s))
        f = C[db_name].WebNewforms.files.find_one(s)
        emf_logger.debug("Found rec={0}".format(f))
        if f<>None:
            id = f.get('_id')
            fs = gridfs.GridFS(C[db_name],'WebNewforms')
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
        C = lmfdb.base.getDBConnection()
        fs = gridfs.GridFS(C[db_name], 'WebNewforms')
        collection = C[db_name].WebNewforms.files
        s = {'name':self._name,'version':float(self._version)}
        rec = collection.find_one(s)
        if rec:
            id = rec.get('_id')
        else:
            id = None
        if id<>None:
            emf_logger.debug("Removing self from db with id={0}".format(id))
            fs.delete(id)
            
        fname = "webnewform-{0:0>5}-{1:0>3}-{2:0>3}-{3}".format(self._N,self._k,self._chi,self._label) 
#        try:
        d = self.to_dict()
        d.pop('_ap',None) ## This is already stored in this format in the database
        id = fs.put(dumps(d),filename=fname,N=int(self._N),k=int(self._k),chi=int(self._chi),label=self._label,name=self._name,version=float(self._version))
#        except Exception as e:
#            emf_logger.critical("DB insertion failed: {0}".format(e.message))
        emf_logger.debug("inserted :{0}".format(id))
    
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

    def to_yaml(self,for_yaml=False):
        d = self.to_dict()
        return yaml.dump(d)
    
    def from_yaml(self,s):        
        d = yaml.load(s)
        return yaml.load(d)    
    
    def to_dict(self):
        r"""
        Export self as a serializable dictionary.
        """
        if self._base_ring_as_dict=={}:
            self._base_ring_as_dict=number_field_to_dict(self.base_ring())
        if self._coefficient_field_as_dict=={}:
            self._coefficient_field_as_dict=number_field_to_dict(self.coefficient_field())
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

    def level(self):
        r"""
        The level of self (assuming it is on a congruence subgroup).
        """
        return self._N

    def ambient_space(self):
        r"""
        The group on which self is defined.
        """
        return self.parent().group()

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
    
    def fi(self):
        r"""
        The number of self in the Galois orbits of self.parent()
        """
        if self._fi == None:
            if self._label not in self.parent().labels():
                raise ValueError,"Self (with label {0}) is not in the set of Galois orbits of self.parent()!".format(self._label)
            self._fi = self.parent().labels().index(self._label)
        return self._fi
    
    
    def as_factor(self):
        r"""
        Return the simple factor of the ambient space corresponding to self. 
        """
        if self._f == None:
            self._f = self.parent().galois_decomposition()[self.fi()]
        return self._f

    def character(self):
        if self._character == None:
            self._set_character()
        return self._character

    def conrey_character(self):
        if self._conrey_character == None:
            self._conrey_character = self.parent().conrey_character()
        return self._conrey_character

    def conrey_character_name(self):
        return "\chi_{" + str(self._N) + "}(" + str(self.conrey_character().number()) + ",\cdot)"

    def character_order(self):
        return self._parent.character_order()

    def character_conductor(self):
        return self._parent.character_conductor()

    def character_value(self,x):

        if self.character().is_trivial():
            if (x % self._N) == 0 and self._N>1:
                return self.base_ring()(0)
            else:
                return self.base_ring()(1)        
        return self.character()(x)

    def chi(self):
        return self._chi

    def base_ring(self):
        r"""
        The base ring of self, that is, the field of values of the character of self. 
        """
        if isinstance(self._base_ring,NumberField_class):
            return self._base_ring
        if self._base_ring_as_dict<>{}:
            emf_logger.debug("base_ring={0}".format(self._base_ring_as_dict))
            self._base_ring = number_field_from_dict(self._base_ring_as_dict)
        if self._base_ring == None:
            self._base_ring = self.as_factor().base_ring()
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
        #self._coefficient_field = self.as_factor().q_eigenform(self._prec, names='x').base_ring()
        try:
            self._coefficient_field = self._ap[2].parent()
        except KeyError:
            self._coefficient_field = self.as_factor().q_eigenform(self._prec, names='x').base_ring()
        emf_logger.debug("coef_field={0}".format(self._coefficient_field))
        return self._coefficient_field
    
    def relative_degree(self):
        r"""
        Degree of the field of coefficient relative to its base ring.
        """
        if self._relative_degree <= 0:
            self._relative_degree = self.coefficient_field().absolute_degree()/self.base_ring().absolute_degree()
        return self._relative_degree

    def degree(self):
        return self.absolute_degree()
    
    def absolute_degree(self):
        r"""
        Degree of the field of coefficient relative to its base ring.
        """
        if self._absolute_degree <= 0:
            self._absolute_degree = self.coefficient_field().absolute_degree()
        return self._absolute_degree
        

        
    def prec(self):
        return self._prec

    def parent(self):
        if not isinstance(self._parent,WebModFormSpace_class):
            if self._verbose > 0:
                emf_logger.debug("compute parent! label={0}".format(label))
            self._parent = WebModFormSpace(self._N, sel.f_k,self._chi, data=self._parent)
        return self._parent

    def is_rational(self):
        if self._is_rational==None:
            if self.coefficient_field().degree()==1:
                self._is_rational  = True
            else:
                self._is_rational = False
        return self._is_rational

    def dimension(self):
        r"""
        The dimension of this galois orbit is not necessarily equal to the degree of the number field, when we have a character....
        We therefore need this routine to distinguish between the two cases...
        """
        if self._dimension >= 0:
            return self._dimension
        P = self.parent()
        if P.labels().count(self.label()) > 0:
            j = P.labels().index(self.label())
            self._dimension = self.parent().galois_decomposition()[j].dimension()
        else:
            self._dimension =  0
        return self._dimension


    def q_expansion_embeddings(self, prec=10, bitprec=53,format='numeric',display_bprec=26,insert_in_db=True):
        r""" Compute all embeddings of self into C which are in the same space as self.
        """
        emf_logger.debug("computing embeddings of q-expansions : has {0} embedded coeffs. Want : {1} with bitprec={2}".format(len(self._embeddings),prec,bitprec))
        if display_bprec > bitprec:
            display_bprec = bitprec
        width = 0
        CF = ComplexField(bitprec)
        if self._embeddings == None:
            self._embeddings = []
        if self._embeddings_latex == None:
            self._embeddings_latex = []            
        # If we need more coefficients or higher precision than we currently have then we need to compute more.
        #
        if len(self._embeddings)>0:
            self._bitprec = self._embeddings[0][0].prec()
        if bitprec > self._bitprec: # Then we recompute
            self._embeddings = []
        nstart = len(self._embeddings)
        emf_logger.debug("has embeddings{0}:".format(nstart))
        deg = self.absolute_degree()
        for n in range(nstart,prec):
            try:
                cn = self.coefficient(n)
            except IndexError:
                break
            if hasattr(cn, 'complex_embeddings'):
                cn_emb = cn.complex_embeddings(bitprec)
            else:
                cn_emb = [ CF(cn) for i in range(deg) ]
            self._embeddings.append(cn_emb)
        nstart = len(self._embeddings_latex)
        emf_logger.debug("has embeddings_latex:{0}".format(nstart))            
        for n in range(nstart,prec):
            try: 
                cn_emb=self._embeddings[n]
            except IndexError:
                if self._embeddings==[]:
                    break
                continue
            cn_emb_latex = []
            for x in cn_emb:
                t = my_complex_latex(x,display_bprec)
                cn_emb_latex.append(t)

            self._embeddings_latex.append(cn_emb_latex)                   
            if n<=6:
                for i in range(deg):
                    emf_logger.debug("embedding of C={0}".format(cn_emb_latex))
                    emf_logger.debug("embedding of C[{0}][{1}]={2}".format(n,i,self._embeddings[n][i].n(bitprec)))
        if insert_in_db:
            self.insert_into_db()
        if format=='latex':
            return self._embeddings_latex
        else:
            if bitprec < self._embeddings[0][0].prec():
                res = []
                for x in self._embeddings:
                    res.append([y.n(bitprec) for y in x])
                return res
            else:
                return self._embeddings

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
        if c == None:
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
            if c == None:
                if n == 0 and self.is_cuspidal():
                    c = self.coefficient_field()(0)
                else:
                    recompute = True
                    c = self.coefficient_n_recursive(n,insert_in_db)
                    self._coefficients[n]=c
            res.append(c)
            #maxn = max(nrange)
            #E, v = self.as_factor().compact_system_of_eigenvalues(range(1,maxn+1), names='a')
            #c = E * v
            #par = c[0].parent()
            #self._coefficients[0]=par(0)
            #for n in range(len(c)):
            #    self._coefficients[n+1]=c[n]
        #for n in nrange:
        #    res.append(self._coefficients[n])
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
        if self._ap == None or self._ap == {}:
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
                eps = K(self.character_value(p))
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
        """
        emf_logger.debug("before update self_ap={0}".format(self._ap))
        aps = self._ap
        ambient_aps = self.parent().aps().get(self.label(),{})
        if ambient_aps == {}:
            return
        if self._ap <> {} and max(ambient_aps.keys())<=max(self._ap.keys()):
            return
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

    
 
                      
    def coefficients_old(self, nrange=range(1, 10),insert_in_db=True):
        r"""
        Gives the coefficients in a range.
        We assume that the self._ap containing Hecke eigenvalues
        are stored.

        """
        res = []
        emf_logger.debug("computing coeffs in range {0}".format(nrange))
        if not isinstance(nrange, list):
            M = nrange
            nrange = range(0, M)
        for n in nrange:
            emf_logger.debug("n= {0}".format(n))
            if n == 1:
                res.append(1)
            elif n == 0:
                res.append(0)
            elif is_prime(n):
                pi = prime_pi(n) - 1
                if pi < len(self._ap):
                    ap = self._ap[pi]
                else:
                    # fill up the ap vector
                    prims = primes_first_n(len(self._ap))
                    if len(prims) > 0:
                        ps = next_prime(primes_first_n(len(self._ap))[-1])
                    else:
                        ps = ZZ(2)
                    mn = max(nrange)
                    if is_prime(mn):
                        pe = mn
                    else:
                        pe = previous_prime(mn)
                    if self.level() == 1:
                        E, v = my_compact_system_of_eigenvalues(self.as_factor(), prime_range(ps, pe + 1), names='x')
                    else:
                        E, v = self.as_factor().compact_system_of_eigenvalues(prime_range(ps, pe + 1), names='x')
                    c = E * v
                    # if self._verbose>0:
                    for app in c:
                        self._ap.append(app)
                ap = self._ap[pi]
                res.append(ap)
                # we store up to self.prec coefficients which are not prime
                if n <= self.prec():
                    self._coefficients[n] = ap
            else:
                if n in self._coefficients:
                    an = self._coefficients[n]
                else:
                    try:
                        an = self.as_factor().eigenvalue(n, 'x')
                    except (TypeError,IndexError):
                        if n % self._N == 0:
                            atmp = self.as_factor().eigenvalue(self._N,'x')
                            emf_logger.debug("n= {0},c(n)={1}".format(n,atmp))       
                        an = self.as_factor().eigenvalue(n, 'x')
                    # an = self._f.eigenvalue(QQ(n),'x')
                    self._coefficients[n] = an
                res.append(an)
        if insert_in_db:
            self.insert_into_db()
        return res


    
    def q_expansion(self, prec=None):
        r"""
        Return the q-expansion of self to precision prec.
        """
        if prec == None:
            prec = self._prec

        if not isinstance(self._q_expansion,PowerSeries_poly):
            q_expansion = ''
            if self._q_expansion_str<>'':
                R = PowerSeriesRing(self.coefficient_field(), 'q')
                q_expansion = R(self._q_expansion_str)
                if q_expansion.degree()>=self.prec()-1: 
                    q_expansion = q_expansion.add_bigoh(prec)
            if q_expansion == '' and hasattr(self.as_factor(), 'q_eigenform'):
                q_expansion = self.as_factor().q_eigenform(prec, names='x')
            if q_expansion == '':
                self._q_expansion_str = ''
            else:
                self._q_expansion_str = str(q_expansion.polynomial())   
            self._q_expansion = q_expansion
        if self._q_expansion.prec() == prec:
            return self._q_expansion
        elif self._q_expansion.prec() > prec:
            return self._q_expansion.truncate_powerseries(prec)
        else:
            if prec <= self.max_cn():
                R = PowerSeriesRing(self.coefficient_field(), 'q')                
                q = R.gen()
                ### Get q=expansion from coefficients.... 
                p = self._q_expansion.polynomial()
                for i in range(p.degree()+1,prec+1):
                    p+=self.coefficient(i)*q**i
                p.add_bigoh(prec+1)
                self._q_expansion = p
        return self._q_expansion

    def atkin_lehner_eigenvalue(self, Q):
        r""" Return the Atkin-Lehner eigenvalues of self
        corresponding to Q|N
        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return None
        
        l = self.atkin_lehner_eigenvalues()
        return l.get(Q)


    def _compute_atkin_lehner_matrix(self, f, Q):
        ALambient = f.ambient_hecke_module()._compute_atkin_lehner_matrix(ZZ(Q))
        B = f.free_module().echelonized_basis_matrix()
        P = B.pivots()
        M = B * ALambient.matrix_from_columns(P)
        return M

    def atkin_lehner_eigenvalues(self):
        r""" Compute the Atkin-Lehner eigenvalues of self.

           EXAMPLES::

           sage: get_atkin_lehner_eigenvalues(4,14,0)
           '{2: 1, 14: 1, 7: 1}'
           sage: get_atkin_lehner_eigenvalues(4,14,1)
           '{2: -1, 14: 1, 7: -1}'


        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return {}
        
        if(len(self._atkin_lehner_eigenvalues.keys()) > 0):
            return self._atkin_lehner_eigenvalues
        if(self._chi != 0):
            return {}
        res = dict()
        for Q in divisors(self.level()):
            if(Q == 1):
                continue
            if(gcd(Q, ZZ(self.level() / Q)) == 1):
                emf_logger.debug("Q={0}".format(Q))
                emf_logger.debug("self.as_factor={0}".format(self.as_factor()))
                # try:
                M = self._compute_atkin_lehner_matrix(self.as_factor(), ZZ(Q))
                    # M=self._f._compute_atkin_lehner_matrix(ZZ(Q))
                # except:
                #    emf_logger.critical("Error in computing Atkin Lehner Matrix. Bug is known and due to pickling.")
                # M=self._f.atkin_lehner_operator(ZZ(Q)).matrix()
                try:
                    ev = M.eigenvalues()
                except:
                    emf_logger.critical("Could not get Atkin-Lehner eigenvalues!")
                    self._atkin_lehner_eigenvalues = {}
                    return {}
                emf_logger.debug("eigenvalues={0}".format(ev))
                if len(ev) > 1:
                    if len(set(ev)) > 1:
                        emf_logger.critical("Should be one Atkin-Lehner eigenvalue. Got: {0}".format(ev))
                res[Q] = ev[0]
        self._atkin_lehner_eigenvalues = res
        return res

    def atkin_lehner_eigenvalues_for_all_cusps(self):
        r"""
        Return Atkin-Lehner eigenvalue of A-L involution
        which normalizes cusp if such an inolution exist.
        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return {}
        res = dict()            
        for c in self.parent().group().cusps():
            if c == Infinity:
                continue
            l = self.atkin_lehner_at_cusp(c)
            emf_logger.debug("l={0},{0}".format(c, l))
            if(l):
                (Q, ep) = l
                res[c] = [Q, ep]
                # res[c]=ep
        return res

    def atkin_lehner_at_cusp(self, cusp):
        r"""
        Return Atkin-Lehner eigenvalue of A-L involution
        which normalizes cusp if such an involution exist.
        """
        if not (self.character().is_trivial() or self.character().order() == 2):
            return None
        
        x = self.character()
        if(x != 0 and not x.is_trivial()):
            return None
        if(cusp == Cusp(Infinity)):
            return (ZZ(0), 1)
        elif(cusp == Cusp(0)):
            try:
                return (self.level(), self.atkin_lehner_eigenvalues()[self.level()])
            except:
                return None
        cusp = QQ(cusp)
        N = self.level()
        q = cusp.denominator()
        p = cusp.numerator()
        d = ZZ(cusp * N)
        if(d.divides(N) and gcd(ZZ(N / d), ZZ(d)) == 1):
            M = self._compute_atkin_lehner_matrix(self.as_factor(), ZZ(d))
            ev = M.eigenvalues()
            if len(ev) > 1:
                if len(set(ev)) > 1:
                    emf_logger.critical("Should be one Atkin-Lehner eigenvalue. Got: {0} ".format(ev))
            return (ZZ(d), ev[0])
        else:
            return None

    def is_minimal(self):
        r"""
        Returns True if self is a twist and otherwise False.
        """
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
        if(len(self._twist_info) > 0):
            return self._twist_info
        N = self.level()
        k = self.weight()
        if(is_squarefree(ZZ(N))):
            self._twist_info = [True, None ]
            return [True, None]

        # We need to check all square factors of N
        twist_candidates = list()
        KF = self.base_ring()
        # check how many Hecke eigenvalues we need to check
        max_nump = self._number_of_hecke_eigenvalues_to_check()
        maxp = max(primes_first_n(max_nump))
        for d in divisors(N):
            if(d == 1):
                continue
            # we look at all d such that d^2 divdes N
            if(not ZZ(d ** 2).divides(ZZ(N))):
                continue
            D = DirichletGroup(d)
            # check possible candidates to twist into f
            # g in S_k(M,chi) wit M=N/d^2
            M = ZZ(N / d ** 2)
            if(self._verbose > 0):
                emf_logger.debug("Checking level {0}".format(M))
            for xig in range(euler_phi(M)):
                (t, glist) = _get_newform(M,k, xig)
                if(not t):
                    return glist
                for g in glist:
                    if(self._verbose > 1):
                        emf_logger.debug("Comparing to function {0}".format(g))
                    KG = g.base_ring()
                    # we now see if twisting of g by xi in D gives us f
                    for xi in D:
                        try:
                            for p in primes_first_n(max_nump):
                                if(ZZ(p).divides(ZZ(N))):
                                    continue
                                bf = self.as_factor().q_eigenform(maxp + 1, names='x')[p]
                                bg = g.q_expansion(maxp + 1)[p]
                                if(bf == 0 and bg == 0):
                                    continue
                                elif(bf == 0 and bg != 0 or bg == 0 and bf != 0):
                                    raise StopIteration()
                                if(ZZ(p).divides(xi.conductor())):
                                    raise ArithmeticError("")
                                xip = xi(p)
                                # make a preliminary check that the base rings match with respect to being
                                # real or not
                                try:
                                    QQ(xip)
                                    XF = QQ
                                    if(KF != QQ or KG != QQ):
                                        raise StopIteration
                                except TypeError:
                                    # we have a  non-rational (i.e. complex) value of the character
                                    XF = xip.parent()
                                    if((KF.absolute_degree() == 1 or KF.is_totally_real()) and (KG.absolute_degre() == 1 or KG.is_totally_real())):
                                        raise StopIteration
                            ## it is diffcult to compare elements from diferent rings in general but we make some checcks
                            # is it possible to see if there is a larger ring which everything can be
                            # coerced into?
                                ok = False
                                try:
                                    a = KF(bg / xip)
                                    b = KF(bf)
                                    ok = True
                                    if(a != b):
                                        raise StopIteration()
                                except TypeError:
                                    pass
                                try:
                                    a = KG(bg)
                                    b = KG(xip * bf)
                                    ok = True
                                    if(a != b):
                                        raise StopIteration()
                                except TypeError:
                                    pass
                                if(not ok):  # we could coerce and the coefficients were equal
                                    return "Could not compare against possible candidates!"
                                # otherwise if we are here we are ok and found a candidate
                            twist_candidates.append([M, g.q_expansion(prec), xi])
                        except StopIteration:
                            # they are not equal
                            pass
        emf_logger.debug("Candidates=v{0}".format(twist_candidates))
        self._twist_info = (False, twist_candidates)
        if(len(twist_candidates) == 0):
            self._twist_info = [True, None]
        else:
            self._twist_info = [False, twist_candidates]
        if insert_in_db:
            self.insert_into_db()
        return self._twist_info

    def is_CM(self,insert_in_db=True):
        r"""
        Checks if f has complex multiplication and if it has then it returns the character.

        OUTPUT:

        -''[t,x]'' -- string saying whether f is CM or not and if it is, the corresponding character

        EXAMPLES::

        """
        if(len(self._is_CM) > 0):
            return self._is_CM
        max_nump = self._number_of_hecke_eigenvalues_to_check()
        # E,v = self._f.compact_system_of_eigenvalues(max_nump+1)
        try:
            coeffs = self.coefficients(range(max_nump + 1),insert_in_db=insert_in_db)
        except IndexError: 
           return None,None
        nz = coeffs.count(0)  # number of zero coefficients
        nnz = len(coeffs) - nz  # number of non-zero coefficients
        if(nz == 0):
            self._is_CM = [False, 0]
            return self._is_CM
        # probaly checking too many
        for D in range(3, ceil(QQ(max_nump) / QQ(2))):
            try:
                for x in DirichletGroup(D):
                    if(x.order() != 2):
                        continue
                    # we know that for CM we need x(p) = -1 => c(p)=0
                    # (for p not dividing N)
                    if(x.values().count(-1) > nz):
                        raise StopIteration()  # do not have CM with this char
                    for p in prime_range(max_nump + 1):
                        if(x(p) == -1 and coeffs[p] != 0):
                            raise StopIteration()  # do not have CM with this char
                    # if we are here we have CM with x.
                    self._is_CM = [True, x]
                    return self._is_CM
            except StopIteration:
                pass
        self._is_CM = [False, 0]
        if insert_in_db:
            self.insert_into_db()
        return self._is_CM

    def as_polynomial_in_E4_and_E6(self,insert_in_db=True):
        r"""
        If self is on the full modular group writes self as a polynomial in E_4 and E_6.
        OUTPUT:
        -''X'' -- vector (x_1,...,x_n)
        with f = Sum_{i=0}^{k/6} x_(n-i) E_6^i * E_4^{k/4-i}
        i.e. x_i is the coefficient of E_6^(k/6-i)*
        """
        if(self.level() != 1):
            raise NotImplementedError("Only implemented for SL(2,Z). Need more generators in general.")
        if(self._as_polynomial_in_E4_and_E6 is not None and self._as_polynomial_in_E4_and_E6 != ''):
            return self._as_polynomial_in_E4_and_E6
        d = self._parent.dimension_modular_forms()  # dimension of space of modular forms
        k = self.weight()
        K = self.base_ring()
        l = list()
        # for n in range(d+1):
        #    l.append(self._f.q_expansion(d+2)[n])
        # v=vector(l) # (self._f.coefficients(d+1))
        v = vector(self.coefficients(range(d),insert_in_db=insert_in_db))
        d = dimension_modular_forms(1, k)
        lv = len(v)
        if(lv < d):
            raise ArithmeticError("not enough Fourier coeffs")
        e4 = EisensteinForms(1, 4).basis()[0].q_expansion(lv + 2)
        e6 = EisensteinForms(1, 6).basis()[0].q_expansion(lv + 2)
        m = Matrix(K, lv, d)
        lima = floor(k / 6)  # lima=k\6;
        if((lima - (k / 2)) % 2 == 1):
            lima = lima - 1
        poldeg = lima
        col = 0
        monomials = dict()
        while(lima >= 0):
            deg6 = ZZ(lima)
            deg4 = (ZZ((ZZ(k / 2) - 3 * lima) / 2))
            e6p = (e6 ** deg6)
            e4p = (e4 ** deg4)
            monomials[col] = [deg4, deg6]
            eis = e6p * e4p
            for i in range(1, lv + 1):
                m[i - 1, col] = eis.coefficients()[i - 1]
            lima = lima - 2
            col = col + 1
        if (col != d):
            raise ArithmeticError("bug dimension")
        # return [m,v]
        if self._verbose > 0:
            emf_logger.debug("m={0}".format(m, type(m)))
            emf_logger.debug("v={0}".format(v, type(v)))
        try:
            X = m.solve_right(v)
        except:
            return ""
        self._as_polynomial_in_E4_and_E6 = [poldeg, monomials, X]
        if insert_in_db:
            self.insert_into_db()
        return [poldeg, monomials, X]

    def exact_cm_at_i_level_1(self, N=10,insert_in_db=True):
        r"""
        Use formula by Zagier (taken from pari implementation by H. Cohen) to compute the geodesic expansion of self at i
        and evaluate the constant term.

        INPUT:
        -''N'' -- integer, the length of the expansion to use.
        """
        try:
            [poldeg, monomials, X] = self.as_polynomial_in_E4_and_E6()
        except:
            return ""
        k = self.weight()
        tab = dict()
        QQ['x']
        tab[0] = 0 * x ** 0
        tab[1] = X[0] * x ** poldeg
        for ix in range(1, len(X)):
            tab[1] = tab[1] + QQ(X[ix]) * x ** monomials[ix][1]
        for n in range(1, N + 1):
            tmp = -QQ(k + 2 * n - 2) / QQ(12) * x * tab[n] + (x ** 2 - QQ(1)) / QQ(2) * ((tab[
                                                                                          n]).derivative())
            tab[n + 1] = tmp - QQ((n - 1) * (n + k - 2)) / QQ(144) * tab[n - 1]
        res = 0
        for n in range(1, N + 1):
            term = (tab[n](x=0)) * 12 ** (floor(QQ(n - 1) / QQ(2))) * x ** (n - 1) / factorial(n - 1)
            res = res + term
        
        return res
    #,O(x^(N+1))))
    # return (sum(n=1,N,subst(tab[n],x,0)*

    def as_homogeneous_polynomial(self):
        r"""
        Represent self as a homogenous polynomial in E6/E4^(3/2)
        """

    def print_as_polynomial_in_E4_and_E6(self):
        r"""

        """
        if(self.level() != 1):
            return ""
        try:
            [poldeg, monomials, X] = self.as_polynomial_in_E4_and_E6()
        except ValueError:
            return ""
        s = ""
        e4 = "E_{4}"
        e6 = "E_{6}"
        dens = map(denominator, X)
        g = gcd(dens)
        s = "\\frac{1}{" + str(g) + "}\left("
        for n in range(len(X)):
            c = X[n] * g
            if(c == -1):
                s = s + "-"
            elif(c != 1):
                s = s + str(c)
            if(n > 0 and c > 0):
                s = s + "+"
            d4 = monomials[n][0]
            d6 = monomials[n][1]
            if(d6 > 0):
                s = s + e6 + "^{" + str(d6) + "}"
            if(d4 > 0):
                s = s + e4 + "^{" + str(d4) + "}"
        s = s + "\\right)"
        return "\(" + s + "\)"

    def cm_values(self, digits=12,insert_in_db=True):
        r""" Computes and returns a list of values of f at a collection of CM points as complex floating point numbers.

        INPUT:

        -''digits'' -- we want this number of corrrect digits in the value

        OUTPUT:
        -''s'' string representation of a dictionary {I:f(I):rho:f(rho)}.

        TODO: Get explicit, algebraic values if possible!
        """
        if self._cm_values <> None:
            cm_vals = self._cm_values
        else:
            cm_vals = self.compute_cm_values_numeric(digits=digits,insert_in_db=insert_in_db)
        emf_logger.debug("in cm_values with digits={0}".format(digits))
        # bits=max(int(53),ceil(int(digits)*int(4)))
        rho = CyclotomicField(3).gen()
        zi = CyclotomicField(4).gen()        
        res = dict()
        res['embeddings'] = range(self.degree())
        res['tau_latex'] = dict()
        res['cm_vals_latex'] = dict()
        maxl = 0
        for tau in cm_vals:
            if tau == zi:
                res['tau_latex'][tau] = "\(" + latex(I) + "\)"
            else:
                res['tau_latex'][tau] = "\(" + latex(tau.n(self._display_bprec)) + "\)"
            res['cm_vals_latex'][tau] = dict()
            for h in cm_vals[tau].keys():
                res['cm_vals_latex'][tau][h] = "\(" + latex(cm_vals[tau][h].n(self._display_bprec)) + "\)"
                l = len_as_printed(res['cm_vals_latex'][tau][h], False)
                if l > maxl:
                    maxl = l
        res['tau'] = cm_vals.keys()
        res['cm_vals'] = cm_vals
        res['max_width'] = maxl
        return res


    def compute_cm_values_numeric(self,digits=12,insert_in_db=True):
        r"""
        Compute CM-values numerically.
        """
        if isinstance(self._cm_values,dict) and self._cm_values  <> {}:
            return self._cm_values
         # the points we want are i and rho. More can be added later...
        bits = ceil(int(digits) * int(4))
        CF = ComplexField(bits)
        RF = ComplexField(bits)
        eps = RF(10 ** - (digits + 1))
        if(self._verbose > 1):
            emf_logger.debug("eps={0}".format(eps))
        K = self.base_ring()
        # recall that
        degree = self.degree()
        cm_vals = dict()
        rho = CyclotomicField(3).gen()
        zi = CyclotomicField(4).gen()
        points = [rho, zi]
        maxprec = 1000  # max size of q-expansion
        minprec = 10  # max size of q-expansion
        for tau in points:
            q = CF(exp(2 * pi * I * tau))
            fexp = dict()
            cm_vals[tau] = dict()
            if(tau == I and self.level() == -1):
                # cv=    #"Exact(soon...)" #_cohen_exact_formula(k)
                for h in range(degree):
                    cm_vals[tau][h] = cv
                continue
            if K.absolute_degree()==1:
                v1 = CF(0)
                v2 = CF(1)
                try:
                    for prec in range(minprec, maxprec, 10):
                        if(self._verbose > 1):
                            emf_logger.debug("prec={0}".format(prec))
                        v2 = self.as_factor().q_eigenform(prec).truncate(prec)(q)
                        err = abs(v2 - v1)
                        if(self._verbose > 1):
                            emf_logger.debug("err={0}".format(err))
                        if(err < eps):
                            raise StopIteration()
                        v1 = v2
                    cm_vals[tau][0] = None
                except StopIteration:
                    cm_vals[tau][0] = v2
            else:
                v1 = dict()
                v2 = dict()
                err = dict()
                for h in range(degree):
                    v1[h] = 1
                    v2[h] = 0
                try:
                    for prec in range(minprec, maxprec, 10):
                        if(self._verbose > 1):
                            emf_logger.debug("prec={0}".format(prec))
                        c = self.coefficients(range(prec),insert_in_db=insert_in_db)
                        for h in range(degree):
                            fexp[h] = list()
                            v2[h] = 0
                            for n in range(prec):
                                cn = c[n]
                                if hasattr(cn, 'complex_embeddings'):
                                    cc = cn.complex_embeddings(CF.prec())[h]
                                else:
                                    cc = CF(cn)
                                v2[h] = v2[h] + cc * q ** n
                            err[h] = abs(v2[h] - v1[h])
                            if(self._verbose > 1):
                                emf_logger.debug("v1[{0}]={1}".format(h,v1[h]))
                                emf_logger.debug("v2[{0}]={1}".format(h,v2[h]))
                                emf_logger.debug("err[{0}]={2}".format(h,err[h]))
                            if(max(err.values()) < eps):
                                raise StopIteration()
                            v1[h] = v2[h]
                except StopIteration:
                    pass
                for h in range(degree):
                    if(err[h] < eps):
                        cm_vals[tau][h] = v2[h]
                    else:
                        cm_vals[tau][h] = None
        self._cm_values = cm_vals
        if insert_in_db:
            self.insert_into_db()
        return self._cm_values

    
    def satake_parameters(self, prec=10, bits=53,insert_in_db=True):
        r""" Compute the Satake parameters and return an html-table.

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
        K = self.coefficient_field()
        degree = self.degree()
        RF = RealField(bits)
        CF = ComplexField(bits)
        ps = prime_range(prec)

        self._satake['ps'] = []
        alphas = dict()
        thetas = dict()
        aps = list()
        tps = list()
        k = self.weight()

        for j in range(degree):
            alphas[j] = dict()
            thetas[j] = dict()
        for j in xrange(len(ps)):
            p = ps[j]
            try:
                ap = self.coefficient(p) 
            except IndexError:
                break
            # Remove bad primes
            if p.divides(self.level()):
                continue
            self._satake['ps'].append(p)
            chip = self.character_value(p)
            emf_logger.debug("p={0}".format(p))
            emf_logger.debug("chip={0} of type={1}".format(chip,type(chip)))
            if hasattr(chip,'complex_embeddings'):
                emf_logger.debug("embeddings(chip)={0}".format(chip.complex_embeddings()))
            emf_logger.debug("ap={0}".format(ap))
            emf_logger.debug("K={0}".format(K))                        
            
            # ap=self._f.coefficients(ZZ(prec))[p]
            if K.absolute_degree()==1:
                f1 = QQ(4 * chip * p ** (k - 1) - ap ** 2)
                alpha_p = (QQ(ap) + I * f1.sqrt()) / QQ(2)
                ab = RF(p ** ((k - 1) / 2))
                norm_alpha = alpha_p / ab
                t_p = CF(norm_alpha).argument()
                thetas[0][p] = t_p
                alphas[0][p] = (alpha_p / ab).n(bits)
            else:
                for jj in range(degree):
                    app = ap.complex_embeddings(bits)[jj]
                    emf_logger.debug("chip={0}".format(chip))
                    emf_logger.debug("app={0}".format(app))
                    emf_logger.debug("jj={0}".format(jj))            
                    if not hasattr(chip,'complex_embeddings'):
                        f1 = (4 * CF(chip) * p ** (k - 1) - app ** 2)
                    else:
                        f1 = (4 * chip.complex_embeddings(bits)[jj] * p ** (k - 1) - app ** 2)
                    alpha_p = (app + I * abs(f1).sqrt())
                    # ab=RF(/RF(2)))
                    # alpha_p=alpha_p/RealField(bits)(2)
                    emf_logger.debug("f1={0}".format(f1))
                    
                    alpha_p = alpha_p / RF(2)
                    emf_logger.debug("alpha_p={0}".format(alpha_p))                    
                    t_p = CF(alpha_p).argument()
                    # tps.append(t_p)
                    # aps.append(alpha_p)
                    alphas[jj][p] = alpha_p
                    thetas[jj][p] = t_p
        self._satake['alphas'] = alphas
        self._satake['thetas'] = thetas
        self._satake['alphas_latex'] = dict()
        self._satake['thetas_latex'] = dict()
        for j in self._satake['alphas'].keys():
            self._satake['alphas_latex'][j] = dict()
            for p in self._satake['alphas'][j].keys():
                s = latex(self._satake['alphas'][j][p])
                self._satake['alphas_latex'][j][p] = s
        for j in self._satake['thetas'].keys():
            self._satake['thetas_latex'][j] = dict()
            for p in self._satake['thetas'][j].keys():
                s = latex(self._satake['thetas'][j][p])
                self._satake['thetas_latex'][j][p] = s

        emf_logger.debug("satake=".format(self._satake))
        if insert_in_db:
            self.insert_into_db()
        return self._satake

    def print_satake_parameters(self, stype=['alphas', 'thetas'], prec=10, bprec=53):
        emf_logger.debug("print_satake={0},{1}".format(prec, bprec))
        if self.as_factor() is None:
            return ""
        if len(self.coefficients()) < prec:
            self.coefficients(prec)
        if prec <= self.level() and prime_pi(prec - 1) <= len(prime_divisors(self.level())):
            prec = next_prime(self.level()) + 1

        satake = self.satake_parameters(prec, bprec)
        emf_logger.debug("satake={0}".format(satake))
        tbl = dict()
        if not isinstance(stype, list):
            stype = [stype]
        emf_logger.debug("type={0}".format(stype))
        emf_logger.debug("sat[type]={0}".format(satake[stype[0]]))
        emf_logger.debug("sat[type]={0}".format(satake[stype[0]].keys()))
        tbl['headersh'] = satake[stype[0]][0].keys()
        tbl['atts'] = "border=\"1\""
        tbl['data'] = list()
        tbl['headersv'] = list()
        K = self.coefficient_field()
        degree = self.degree()
        if(self.dimension() > 1):
            tbl['corner_label'] = "\( Embedding \, \\backslash \, p\)"
        else:
            tbl['corner_label'] = "\( p\)"
        for type in stype:
            for j in range(degree):
                if(self.dimension() > 1):
                    tbl['headersv'].append(j)
                else:
                    if(type == 'alphas'):
                        tbl['headersv'].append('\(\\alpha_p\)')
                    else:
                        tbl['headersv'].append('\(\\theta_p\)')
                row = list()
                for p in satake[type][j].keys():
                    row.append(satake[type][j][p])
                tbl['data'].append(row)
        emf_logger.debug("tbl={0}".format(tbl))
        s = html_table(tbl)
        return s

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
        if prec == None:
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
            s = r"\[\begin{align} &" + "\cr &".join(sb) + r"\end{align}\]"
            
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
            if self._base_ring_as_dict=={}:
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

    def print_atkin_lehner_eigenvalues(self):
        r"""
        """
        l = self.atkin_lehner_eigenvalues()
        if len(l) == 0:
            return ""
        tbl = dict()
        tbl['headersh'] = list()
        tbl['atts'] = "border=\"1\""
        tbl['data'] = [0]
        tbl['data'][0] = list()
        tbl['corner_label'] = "\(Q\)"
        tbl['headersv'] = ["\(\epsilon_{Q}\)"]
        for Q in l.keys():
            if(Q == self.level()):
                tbl['headersh'].append('\(' + str(Q) + '{}^*{}\)')
            else:
                tbl['headersh'].append('\(' + str(Q) + '\)')
            tbl['data'][0].append(l[Q])
        s = html_table(tbl)
        return s

    def print_atkin_lehner_eigenvalues_for_all_cusps(self):
        l = self.atkin_lehner_eigenvalues_for_all_cusps()
        if l.keys().count(Cusp(Infinity)) == len(l.keys()):
            return ""
        if len(l) == 0:
            return ""
        tbl = dict()
        tbl['headersh'] = list()
        tbl['atts'] = "border=\"1\""
        tbl['data'] = [0]
        tbl['data'][0] = list()
        tbl['corner_label'] = "\( Q \)  \([cusp]\)"
        tbl['headersv'] = ["\(\epsilon_{Q}\)"]
        for c in l.keys():
            if(c != Cusp(Infinity)):
                Q = l[c][0]
                s = '\(' + str(Q) + "\; [" + str(c) + "]\)"
                if(c == 0):
                    tbl['headersh'].append(s + '\({}^{*}\)')
                else:
                    tbl['headersh'].append(s)
                tbl['data'][0].append(l[c][1])
        emf_logger.debug("{0}".format(tbl))
        s = html_table(tbl)
        # s=s+"<br><small>* ) The Fricke involution</small>"
        return s

    def print_twist_info(self, prec=10):
        r"""
        Prints info about twisting.

        OUTPUT:

        -''s'' -- string representing a tuple of a Bool and a list. The list contains all tuples of forms which twists to the given form.
        The actual minimal one is the first element of this list.

        EXAMPLES::
        """
        [t, l] = self.twist_info(prec)
        if(t):
            return "f is minimal."
        else:
            return "f is a twist of " + str(l[0])

    def print_is_CM(self):
        r"""
        """
        [t, x] = self.is_CM()
        if(t):
            ix = x.parent().list().index(x)
            m = x.parent().modulus()
            s = "f has CM with character nr. %s modulo %s of order %s " % (ix, m, x.order())
        else:
            s = ""
        return s

    def present(self):
        r"""
        Present self.
        """
        s = "<h1>f is a newform in </h2>"
        s = " \( f (q) = " + self.print_q_expansion() + "\)"
        s = s + ""
        s = s + "<h2>Atkin-Lehner eigenvalues</h2>"
        s = s + self.print_atkin_lehner_eigenvalues()
        s = s + "<h2>Atkin-Lehner eigenvalues for all cusps</h2>"
        s = s + self.print_atkin_lehner_eigenvalues_for_all_cusps()
        s = s + "<h2>Info on twisting</h2>"
        s = s + self.print_twist_info()
        if(self.is_CM()[0]):
            s = s + "<h2>Info on CM</h2>"
            s = s + self.print_is_CM()
        s = s + "<h2>Embeddings</h2>"
        s = s + self.print_q_expansion_embeddings()
        s = s + "<h2>Values at CM points</h2>\n"
        s = s + self.print_values_at_cm_points()
        s = s + "<h2>Satake Parameters \(\\alpha_p\)</h2>"
        s = s + self.print_satake_parameters(type='alphas')
        s = s + "<h2>Satake Angles \(\\theta_p\)</h2>\n"
        s = s + self.print_satake_parameters(type='thetas')
        if(self.level() == 1):
            s = s + "<h2>As polynomial in \(E_4\) and \(E_6\)</h2>\n"
            s = s + self.print_as_polynomial_in_E4_and_E6()

        return s

    def print_values_at_cm_points(self):
        r"""
        """
        cm_vals = self.cm_values()['cm_values']
        K = self.coefficient_field()
        degree = self.degree()
        if(self._verbose > 2):
            emf_logger.debug("vals={0}".format(cm_vals))
            emf_logger.debug("errs={0}".format(err))
        tbl = dict()
        tbl['corner_label'] = "\(\\tau\)"
        tbl['headersh'] = ['\(\\rho=\zeta_{3}\)', '\(i\)']
        # if(K==QQ):
        #    tbl['headersv']=['\(f(\\tau)\)']
        #    tbl['data']=[cm_vals.values()]
        # else:
        tbl['data'] = list()
        tbl['atts'] = "border=\"1\""
        tbl['headersv'] = list()
        # degree = self.dimension()
        for h in range(degree):
            if(degree == 1):
                tbl['headersv'].append("\( f(\\tau) \)")
            else:
                tbl['headersv'].append("\(v_{%s}(f(\\tau))\)" % h)

            row = list()
            for tau in cm_vals.keys():
                if h in cm_vals[tau]:
                    row.append(cm_vals[tau][h])
                else:
                    row.append("")
            tbl['data'].append(row)
        s = html_table(tbl)
        # s=html.table([cm_vals.keys(),cm_vals.values()])
        return s

    def twist_by(self, x):
        r"""
        twist self by a primitive Dirichlet character x
        """
        # xx = x.primitive()
        assert x.is_primitive()
        q = x.conductor()
        # what level will the twist live on?
        level = self.level()
        qq = self.character().conductor()
        new_level = lcm(self.level(), lcm(q * q, q * qq))
        D = DirichletGroup(new_level)
        new_x = D(self.character()) * D(x) * D(x)
        ix = D.list().index(new_x)
        #  the correct space
        NS = WebModFormSpace(self._k, new_level, ix, self._prec)
        # have to find whih form wee want
        NS.galois_decomposition()
        M = NS.sturm_bound() + len(divisors(new_level))
        C = self.coefficients(range(M))
        for label in NS._galois_orbits_labels:
            emf_logger.debug("label={0}".format(label))
            FT = NS.f(label)
            CT = FT.f.coefficients(M)
            emf_logger.debug("{0}".format(CT))
            K = FT.f.hecke_eigenvalue_field()
            try:
                for n in range(2, M):
                    if(new_level % n + 1 == 0):
                        continue
                    emf_logger.debug("n={0}".format(n))
                    ct = CT[n]
                    c = K(x(n)) * K(C[n])
                    emf_logger.debug("{0} {1}".format(ct, c))
                    if ct != c:
                        raise StopIteration()
            except StopIteration:
                pass
            else:
                emf_logger.debug("Twist of f={0}".format(FT))
        return FT

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
            stmp = "".join([stmp, sl[j]])
        else:
            res.append(stmp)
            stmp = sl[j]
        if j == len(sl) - 1:
            res.append(stmp)
    return res


def _get_newform(N, k, chi, fi=None):
    r"""
    Get an element of the space of newforms, incuding some error handling.

    INPUT:

     - ''k'' -- positive integer : the weight
     - ''N'' -- positive integer (default 1) : level
     - ''chi'' -- non-neg. integer (default 0) use character nr. chi
     - ''fi'' -- integer (default 0) We want to use the element nr. fi f=Newforms(N,k)[fi]. fi=-1 returns the whole list
     - ''prec'' -- integer (the number of coefficients to get)

    OUTPUT:

    -''t'' -- bool, returning True if we succesfully created the space and picked the wanted f
    -''f'' -- equals f if t=True, otherwise contains an error message.

    EXAMPLES::


        sage: _get_newform(16,10,1)
        (False, 'Could not construct space $S^{new}_{16}(10)$')
        sage: _get_newform(10,16,1)
        (True, q - 68*q^3 + 1510*q^5 + O(q^6))
        sage: _get_newform(10,16,3)
        (True, q + 156*q^3 + 870*q^5 + O(q^6))
        sage: _get_newform(10,16,4)
        (False, '')

     """
    t = False
    try:
        if(chi == 0):
            emf_logger.debug("EXPLICITLY CALLING NEWFORMS!")
            S = Newforms(N, k, names='x')
        else:
            S = Newforms(DirichletGroup(N)[chi], k, names='x')
        if(fi >= 0 and fi < len(S)):
            f = S[fi]
            t = True
        elif(fi == -1 or fi is None):
            t = True
            return (t, S)
        else:
            f = ""
    except RuntimeError:
        if(chi == 0):
            f = "Could not construct space $S^{new}_{%s}(%s)$" % (k, N)
        else:
            f = "Could not construct space $S^{new}_{%s}(%s,\chi_{%s})$" % (k, N, chi)
    return (t, f)


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
    ## For some reason we have either a or a1 as variable in the polynomials....
    s = re.sub("a1","x",s)
    s = re.sub("a","x",s)
    s = re.sub("zetx","zeta",s)
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
    s = re.sub("a1","x",s)
    s = re.sub("a","x",s)
    s = re.sub("zetx","zeta",s)
    s = re.sub("zeta(\d+)", "\zeta_{\\1}", s)
    return s


## Added routines to replace sage routines with bugs for level 1
##


def my_compact_system_of_eigenvalues(AA, v, names='alpha', nz=None):
    r"""
    Return a compact system of eigenvalues `a_n` for
    `n\in v`. This should only be called on simple factors of
    modular symbols spaces.

    INPUT:


    -  ``v`` - a list of positive integers

    -  ``nz`` - (default: None); if given specifies a
       column index such that the dual module has that column nonzero.


    OUTPUT:


    -  ``E`` - matrix such that E\*v is a vector with
       components the eigenvalues `a_n` for `n \in v`.

    -  ``v`` - a vector over a number field


    EXAMPLES::

        sage: M = ModularSymbols(43,2,1)[2]; M
        Modular Symbols subspace of dimension 2 of Modular Symbols space of dimension 4 for Gamma_0(43) of weight 2 with sign 1 over Rational Field
        sage: E, v = M.compact_system_of_eigenvalues(prime_range(10))
        sage: E
        [ 3 -2]
        [-3  2]
        [-1  2]
        [ 1 -2]
        sage: v
        (1, -1/2*alpha + 3/2)
        sage: E*v
        (alpha, -alpha, -alpha + 2, alpha - 2)
    """
    if nz is None:
        nz = AA._eigen_nonzero()
    M = AA.ambient()
    try:
        E = my_hecke_images(M, nz, v) * AA.dual_free_module().basis_matrix().transpose()
    except AttributeError:
        # TODO!!!
        raise NotImplementedError("ambient space must implement hecke_images but doesn't yet")
    v = AA.dual_eigenvector(names=names, lift=False, nz=nz)
    return E, v


def my_compact_newform_eigenvalues(AA, v, names='alpha'):
    r"""
    """

    if AA.sign() == 0:
        raise ValueError("sign must be nonzero")
    v = list(v)

    # Get decomposition of this space
    D = AA.cuspidal_submodule().new_subspace().decomposition()
    for A in D:
        # since sign is zero and we're on the new cuspidal subspace
        # each factor is definitely simple.
        A._is_simple = True
        B = [A.dual_free_module().basis_matrix().transpose() for A in D]

        # Normalize the names strings.
        names = ['%s%s' % (names, i) for i in range(len(B))]

        # Find an integer i such that the i-th columns of the basis for the
        # dual modules corresponding to the factors in D are all nonzero.
        nz = None
        for i in range(AA.dimension()):
            # Decide if this i works, i.e., ith row of every element of B is nonzero.
            bad = False
            for C in B:
                if C.row(i) == 0:
                    # i is bad.
                    bad = True
                    continue
            if bad:
                continue
            # It turns out that i is not bad.
            nz = i
            break

        if nz is not None:
            R = my_hecke_images(AA, nz, v)
            return [(R * m, D[i].dual_eigenvector(names=names[i], lift=False, nz=nz)) for i, m in enumerate(B)]
        else:
            # No single i works, so we do something less uniform.
            ans = []
            cache = {}
            for i in range(len(D)):
                nz = D[i]._eigen_nonzero()
                if nz in cache:
                    R = cache[nz]
                else:
                    R = my_hecke_images(AA, nz, v)
                    cache[nz] = R
                ans.append((R * B[i], D[i].dual_eigenvector(names=names[i], lift=False, nz=nz)))
            return ans


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
        
    
