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
from sage.all import ZZ, QQ, DirichletGroup, CuspForms, Gamma0, ModularSymbols, Newforms, trivial_character, is_squarefree, divisors, RealField, ComplexField, prime_range, I, join, gcd, Cusp, Infinity, ceil, CyclotomicField, exp, pi, primes_first_n, euler_phi, RR, prime_divisors, Integer, matrix
from sage.all import Parent, SageObject, dimension_new_cusp_forms, vector, dimension_modular_forms, dimension_cusp_forms, EisensteinForms, Matrix, floor, denominator, latex, is_prime, prime_pi, next_prime, primes_first_n, previous_prime, factor, loads,save
import re

from flask import url_for

## DB modules
import pymongo
import gridfs
from pymongo.helpers import bson
from bson import BSON
# local imports
import lmfdb.base
from lmfdb.modular_forms.elliptic_modular_forms import emf_logger
from plot_dom import draw_fundamental_domain
from emf_core import html_table, len_as_printed
try:
    from dirichlet_conrey import *
except:
    emf_logger.critical("Could not import dirichlet_conrey!")

db_name = 'modularforms'
from lmfdb.website import dbport


class WebModFormSpace(Parent):
    r"""
    Space of cuspforms to be presented on the web.
        G  = NS.

    EXAMPLES::

    sage: WS=WebModFormSpace(2,39)


    """
    def __init__(self, k, N=1, chi=0, cuspidal=1, prec=10, bitprec=53, data=None, compute=None, use_db=True, verbose=0):
        r"""
        Init self.

        INPUT:
        - 'k' -- weight
        - 'N' -- level
        - 'chi' -- character
        - 'cuspidal' -- 1 if space of cuspforms, 0 if all modforms
        """
        self._cuspidal = cuspidal
        self._k = ZZ(k)
        self._N = ZZ(N)
        if chi == 'trivial':
            self._chi = ZZ(0)
        else:
            self._chi = ZZ(chi)
        self._prec = ZZ(prec)
        self.prec = ZZ(prec)
        self._ap = list()
        self._verbose = verbose
        self._bitprec = bitprec
        self._dimension_newspace = None
        self._dimension_cusp_forms = None
        self._dimension_modular_forms = None
        self._dimension_new_cusp_forms = None
        self._dimension_new_modular_symbols = None
        self._galois_decomposition = []
        self._newspace = None
        self._character = None
        self._got_ap_from_db = False
        # check what is in the database
        ## dO A SIMPLE TEST TO SEE IF WE EXIST OR NOT.
        if N < 0 or int(chi) > int(euler_phi(N)) or chi < 0:
            print "1:", N < 0
            print "2:", int(chi) > int(euler_phi(N))
            print "3:", chi < 0

            emf_logger.critical("Could not construct WMFS with: {0}.{1}.{2} and eulerphi-{3}".format(
                k, N, chi, euler_phi(N)))
            return None
        if isinstance(data, dict):
            if 'ap' in data:
                self._ap = data['ap']
            if 'group' in data:
                self._group = data['group']
            if 'character' in data:
                self._character = data['character']
                self._conrey_character = self._get_conrey_character(self._character)
            if 'modular_symbols' in data:
                self._modular_symbols = data['modular_symbols']
            if 'newspace' in data:
                self._newspace = data['newspace']
            if 'newforms' in data:
                self._newforms = data['newforms']
            if 'new_modular_symbols' in data:
                self._new_modular_symbols = data['new_modular_symbols']
            if 'decomposition' in data:
                self._galois_decomposition = data['galois_decomposition']
            if 'galois_orbits_labels' in data:
                self._galois_orbits_labels = data['galois_orbits_labels']
            if 'oldspace_decomposition' in data:
                self._oldspace_decomposition = data['oldspace_decomposition']
        else:
            try:
                self._group = Gamma0(N)
                self._character = self._get_character(self._chi)
                MS = self._get_objects(k, N, chi, use_db, 'Modular_symbols')
                self._modular_symbols = MS
                # self._modular_symbols_cuspidal_new_submodule=MS.cuspidal_submodule().new_submodule()
                self._newspace = self._modular_symbols.cuspidal_submodule().new_submodule()
                self._ap = self._get_objects(k, N, chi, use_db, 'ap', prec=prec)
                # self._fullspace.newforms(names='x')
                # self._new_modular_symbols=self._modular_symbols.new_submodule()
                self._galois_decomposition = []
                self._oldspace_decomposition = []
                self._galois_orbits_labels = []
                self._conrey_character = self._get_conrey_character(self._character)
                self._newforms = list()
                l = len(self.galois_decomposition())
                for i in range(l):
                    self._newforms.append(None)
                if compute != '':
                    self._compute_newforms(compute)
            except RuntimeError:
                raise RuntimeError("Could not construct space for (k=%s,N=%s,chi=%s)=" % (k, N, self._chi))
        emf_logger.debug("Setting conrey_character={0}".format(self._conrey_character))
        ### If we can we set these dimensions using formulas
        if(self.dimension() == self.dimension_newspace()):
            self._is_new = True
        else:
            self._is_new = False

    def _compute_newforms(self, compute='all'):
        r"""
        Populates self with newforms.
        """
        emf_logger.debug("Computing! : {0}".format(compute))
        l = len(self.galois_decomposition())
        for i in range(l):
            label = self._galois_orbits_labels[i]
            if compute == i or compute == 'all' or compute == label:
                f_data = dict()
                f_data['parent'] = self
                f_data['f'] = self.galois_decomposition()[i]
                emf_logger.debug("f_data={0}".format(f_data['f']))
                emf_logger.debug("self_ap={0}".format(self._ap))
                if self._ap is not None and len(self._ap) <= i:
                    f_data['ap'] = self._ap[i]
                emf_logger.debug("Actually getting F {0},{1}".format(label, i))
                F = WebNewForm(self._k, self._N, self._chi, label=label, fi=i, prec=self._prec, bitprec=self._bitprec, verbose=self._verbose, data=f_data, parent=self, compute=i)
                emf_logger.debug("F={0},type(F)={1}".format(F, type(F)))
                self._newforms[i] = F

    def _get_character(self, k):
        r"""
        Returns canonical representative of the Galois orbit nr. k acting on the ambient space of self.

        """
        D = DirichletGroup(self.group().level())
        G = D.galois_orbits(reps_only=True)
        try:
            emf_logger.debug("k={0},G[k]={1}".format(k, G[k]))
            return G[k]
        except IndexError:
            emf_logger.critical("Got character no. {0}, which are outside the scope of Galois orbits of the characters mod {1}!".format(k, self.group().level()))
            return trivial_character(self.group().level())

    def _get_conrey_character(self, chi):
        Dc = DirichletGroup_conrey(chi.modulus())
        for c in Dc:
            if c.sage_character() == chi:
                return c

    def _get_objects(self, k, N, chi, use_db=True, get_what='Modular_symbols', **kwds):
        r"""
        Getting the space of modular symbols from the database if it exists. Otherwise compute it and insert it into the database.
        """
        if not get_what in ['ap', 'Modular_symbols']:
            emf_logger.critical("Collection {0} is not implemented!".format(get_what))
        collection = get_what
        emf_logger.debug("collection={0}".format(collection))
        res = None
        if 'prec' in kwds:
            prec = kwds['prec']
        elif get_what == 'ap':
            prec = 10
        self._from_db = 0
        try:
            if use_db:
                emf_logger.debug("dbport={0}".format(dbport))
                C = lmfdb.base.getDBConnection()
                emf_logger.debug("C={0}".format(C))
                if not C:
                    emf_logger.critical("Could not connect to Database! C={0}".format(C))
                if not db_name in C.database_names():
                    emf_logger.critical("Incorrect database name {0}. \n Available databases are:{1}".format(
                        db_name, C.database_names()))
                if not collection + '.files' in C[db_name].collection_names():
                    emf_logger.critical("Incorrect collection {0} in database {1}. \n Available collections are:{2}".format(collection, db_name, C[db_name].collection_names()))
                files = C[db_name][collection].files
                if chi == 0:
                    key = {'k': int(k), 'N': int(N)}
                else:
                    key = {'k': int(k), 'N': int(N), 'chi': int(chi)}
                if get_what == 'ap':
                    key['prec'] = {"$gt": prec - 1}
                finds = files.find(key)
                if get_what == 'ap':
                    finds = finds.sort("prec")
                if self._verbose > 1:
                    emf_logger.debug("files={0}".format(files))
                    emf_logger.debug("key={0}".format(key))
                    emf_logger.debug("finds={0}".format(finds))
                    emf_logger.debug("finds.count()={0}".format(finds.count()))
                if finds and finds.count() > 0:
                    rec = finds[0]
                    emf_logger.debug("rec={0}".format(rec))
                    fid = rec['_id']
                    fs = gridfs.GridFS(C[db_name], collection)
                    f = fs.get(fid)
                    #print f.read()
                    #save(f.read(),"/home/purem/cvzx53/modym.sobj")
                    res = loads(f.read())
                    # TODO avoid pickling python objects for storing in the database
                    self._from_db = 1
                    self._id = rec['_id']
                self._got_ap_from_db = True
        except ArithmeticError:
            pass
            #Exception as e:
            #emf_logger.critical("Error: {0}".format(e))
            # pass
        if not res and not use_db:
            if get_what == 'Modular_symbols':
                if chi == 0:
                    res = ModularSymbols(N, k, sign=1)
                else:
                    emf_logger.debug("character: {0}".format(self._character))
                    emf_logger.debug("weight: {0}".format(k))
                    res = ModularSymbols(self._character, k, sign=1)
            elif get_what == 'ap':
                if self.level() == 1:
                    ## Get the Hecke eigenvalues for level 1.
                    ## Have to do this manually due to bug in Sage:
                    res = my_compact_newform_eigenvalues(
                        self._modular_symbols.ambient(), prime_range(prec), names='x')
                else:
                    res = self._modular_symbols.ambient(
                    ).compact_newform_eigenvalues(prime_range(prec), names='x')
        emf_logger.debug("res={0}".format(res))
        return res

    def __reduce__(self):
        r"""
        Used for pickling.
        """
        data = self.to_dict()
        # return(WebModFormSpace,(self._k,self._N,self._chi,self.prec,data))
        return(unpickle_wmfs_v1, (self._k, self._N, self._chi, self._cuspidal, self.prec, self._bitprec, data))

    def _save_to_file(self, file):
        r"""
        Save self to file.
        """
        self.save(file, compress=None)

    def to_dict(self):
        r"""
        Makes a dictionary of the relevant information.
        """
        data = dict()
        data['group'] = self._group
        data['character'] = self._character
        # data['fullspace'] = self._fullspace
        data['modular_symbols'] = self._modular_symbols
        data['newspace'] = self._newspace
        data['newforms'] = self._newforms
        if hasattr(self, "_new_modular_symbols"):
            data['new_modular_symbols'] = self._new_modular_symbols
        data['galois_decomposition'] = self._galois_decomposition
        data['galois_orbits_labels'] = self._galois_orbits_labels
        data['oldspace_decomposition'] = self._oldspace_decomposition
        return data

    def _repr_(self):
        s = 'Space of Cusp forms on ' + str(self.group()) + ' of weight ' + str(self._k)
        s += ' and dimension ' + str(self.dimension())
        return s
        # return str(self._fullspace)

    # internal methods to generate properties of self
    def galois_decomposition(self):
        r"""
        We compose the new subspace into galois orbits.
        """
        from sage.monoids.all import AlphabeticStrings
        if(len(self._galois_decomposition) != 0):
            return self._galois_decomposition
        L = self._newspace.decomposition()
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
                self._dimension_cusp_forms = dimension_cusp_forms(self._character, self._k)
            else:
                self._dimension_cusp_forms = dimension_cusp_forms(self._N, self._k)
            # self._modular_symbols.cuspidal_submodule().dimension()
        return self._dimension_cusp_forms

    def dimension_modular_forms(self):
        if self._dimension_modular_forms is None:
            if self._chi != 0:
                self._dimension_modular_forms = dimension_modular_forms(self._character, self._k)
            else:
                self._dimension_modular_forms = dimension_modular_forms(self._N, self._k)
            # self._dimension_modular_forms=self._modular_symbols.dimension()
        return self._dimension_modular_forms

    def dimension_new_cusp_forms(self):
        if self._dimension_new_cusp_forms is None:
            if self._chi != 0:
                self._dimension_new_cusp_forms = dimension_new_cusp_forms(self._character, self._k)
            else:
                self._dimension_new_cusp_forms = dimension_new_cusp_forms(self._N, self._k)
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
        return self._character

    def conrey_character(self):
        return self._conrey_character

    def conrey_character_name(self):
        return "\chi_{" + str(self._N) + "}(" + str(self._conrey_character.number()) + ",\cdot)"

    def character_order(self):
        if(self._character != 0):
            return self._character.order()
        else:
            return 1

    def character_conductor(self):
        if(self._character != 0):
            return self._character.conductor()
        else:
            return 1

    def group(self):
        return self._group

    def sturm_bound(self):
        r""" Return the Sturm bound of S_k(N,xi), i.e. the number of coefficients necessary to determine a form uniquely in the space.
        """
        return self._modular_symbols.sturm_bound()

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
        Return function f in the set of newforms on self.
        """
        F = None
        if len(self._newforms) == 0:
            if(isinstance(i, int) or i in ZZ):
                F = WebNewForm(self._k, self._N, self._chi, parent=self, fi=i)
            else:
                F = WebNewForm(self._k, self._N, self._chi, parent=self, label=i)
        else:
            if not (isinstance(i, int) or i in ZZ) and i in self._galois_orbits_labels:
                ii = self._galois_orbits_labels.index(i)
            else:
                ii = i
            emf_logger.debug("print ii={0}".format(ii))
            if ii >= 0 and ii <= len(self._newforms):
                # print "set F!"
                F = self._newforms[ii]
                if not F:  # then we have to compute something.
                    emf_logger.debug("compute F")
                    self._compute_newforms(compute=ii)
                    F = self._newforms[ii]
        emf_logger.debug("returning F! :{0}".format(F))
        return F

    def galois_orbit(self, orbit, prec=None):
        r"""
        Return the q_eigenform nr. orbit in self
        """
        if(prec is None):
            prec = self.prec
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
            if self._character.is_trivial():
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
                xd = self._character.decomposition()
                for xx in xd:
                    if xx.modulus() == q:
                        Sd = dimension_new_cusp_forms(xx, k)
                        if Sd > 0:
                            # identify this character for internal storage... should be optimized
                            x_k = self._get_conrey_character(xx).number()
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
            full_label = "{0}.{1}".format(self.level(), self.weight())
            if self._chi != 0:
                full_label = full_label + ".{0}".format(self._chi)
            full_label = full_label + label
            o['full_label'] = full_label
            o['url'] = url_for('emf.render_elliptic_modular_forms', level=self.level(
            ), weight=self.weight(), label=o['label'], character=self._chi)
            o['dim'] = self._galois_decomposition[j].dimension()
            emf_logger.debug('dim({0}={1})'.format(j, o['dim']))
            poly, disc, is_relative = self.galois_orbit_poly_info(j, prec)
            o['poly'] = "\( {0} \)".format(latex(poly))
            o['disc'] = "\( {0} \)".format(latex(disc))
            o['is_relative'] = is_relative
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
                    # print i,sss
            else:
                slist.append(ss)

            K = orbit.base_ring()
            if(K == QQ):
                poly = ZZ['x'].gen()
                disc = '1'
            else:
                poly = K.defining_polynomial()
                if(K.is_relative()):
                    disc = factor(K.relative_discriminant().absolute_norm())
                    is_relative = True
                else:
                    disc = factor(K.discriminant())
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
        orbit = self.galois_orbit(orbitnr, prec)
        if not orbit:
            return ''
        K = orbit.base_ring()
        is_relative = False
        disc = 1
        if(K == QQ):
            poly = ZZ['x'].gen()
            disc = '1'
        else:
            poly = K.defining_polynomial()
            if(K.is_relative()):
                disc = factor(K.relative_discriminant().absolute_norm())
                is_relative = True
            else:
                disc = factor(K.discriminant())
        return poly, disc, is_relative

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


class WebNewForm(SageObject):

    r"""
    Class for representing a (cuspidal) newform on the web.
    """
    def __init__(self, k, N, chi=0, label='', fi=-1, prec=10, bitprec=53, parent=None, data=None, compute=None, verbose=-1):
        r"""
        Init self as form number fi in S_k(N,chi)
        """
        if chi == 'trivial':
            chi = ZZ(0)
        else:
            chi = ZZ(chi)
        t = False
        self._chi = ZZ(chi)
        self._parent = parent
        self.f = None
        self._character = trivial_character(N)
        if self._chi != 0:
            if self._parent and self._parent._character:
                self._character = self._parent._character
                self._conrey_character = self._parent._conrey_character
            else:
                self._character = DirichletGroup(N).galois_orbits(reps_only=True)[chi]
                Dc = DirichletGroup_conrey(N)
                for c in Dc:
                    if c.sage_character() == self._character:
                        self._conrey_character = c
                        break
        self.f = None
        self._label = label
        self._fi = fi
        self._prec = prec
        self._bitprec = bitprec
        self._k = ZZ(k)
        self._N = ZZ(N)
        self._verbose = verbose
        self._data = dict()  # stores a lot of stuff
        self._satake = {}
        self._ap = list()    # List of Hecke eigenvalues (can be long)
        self._coefficients = dict()  # list of Fourier coefficients (should not be long)
        self._atkin_lehner_eigenvalues = {}
        if self._verbose > 0:
            emf_logger.debug("DATA={0}".format(data))
        if isinstance(data, dict) and len(data.keys()) > 0:
            self._from_dict(data)
        else:
            self._from_dict({})
        if self._verbose > 0:
            emf_logger.debug("self.fi={0}".format(self._fi))
        if self._parent is None:
            if self._verbose > 0:
                emf_logger.debug("compute parent!")
                emf_logger.debug("label={0}".format(label))
                emf_logger.debug("fi={0}".format(fi))
            if label != '':
                self._parent = WebModFormSpace(k, N, chi, compute=label)
            elif fi > 0:
                self._parent = WebModFormSpace(k, N, chi, compute=fi)
            else:
                self._parent = WebModFormSpace(k, N, chi, compute='all')
            if self._verbose > 0:
                emf_logger.debug("finished computing parent")
            j = self._get_index_of_self_in_parent()
            if self._verbose > 0:
                emf_logger.debug("j={0}".format(j))
            if len(self._parent._newforms) and j >= 0:
                new_data = self._parent.f(j)._to_dict()
                self._from_dict(new_data)
            else:
                return None
        if self._verbose > 0:
            emf_logger.debug("parent={0}".format(self._parent))
        j = self._get_index_of_self_in_parent()
        if self._verbose > 0:
            emf_logger.debug("j={0}".format(j))
            emf_logger.debug("newforms={0}".format(self._parent._newforms))
        if self._f is None:
            if j < len(self._parent._newforms) and j >= 0:
                self._f = self._parent._newforms[j]
            else:
                self._f = None
                return

        self._name = str(self._N) + "." + str(self._k) + str(self._label)
        if self._f is None:
            if(self._verbose >= 0):
                raise IndexError("Requested function does not exist!")
            else:
                return

        emf_logger.debug("name={0}".format(self._name))

        emf_logger.debug("data: {0}".format(data))
        if isinstance(data, dict) and len(data.keys()) > 0:
            self._from_dict(data)

        elif compute == 'all':
            emf_logger.debug("compute")
            self.q_expansion_embeddings(prec, bitprec)
            if self._N == 1:
                self.as_polynomial_in_E4_and_E6()
            # self._as_polynomial_in_E4_and_E6=None
            self.twist_info(prec)
            # self._twist_info = []
            self.is_CM()
            # self._is_CM = []
            self.satake_parameters()
            # self._satake = {}
            self._dimension = self._f.dimension()  # 1 # None
            c = self.coefficients(self.prec())
        else:
            self._embeddings = []
            # self.q_expansion_embeddings(prec,bitprec)
            self._as_polynomial_in_E4_and_E6 = None
            self._twist_info = []
            self._is_CM = []
            self._satake = {}
            self._dimension = 1  # None
        emf_logger.debug("before end of __init__ prec={0}".format(prec))
        emf_logger.debug("before end of __init__ f={0}".format(self._f))
        emf_logger.debug("before end of __init__ type(f)={0}".format(type(self._f)))
        self._base_ring = self._f.q_eigenform(prec, names='x').base_ring()
        emf_logger.debug("done __init__")

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if self._k != other._k:
            return False
        if self._level != other._level:
            return False
        if self._character != other._character:
            return False
        return True

    def __repr__(self):
        r""" String representation f self.
        """
        if self._f is not None:
            return str(self.q_expansion())
        else:
            return ""

    def __reduce__(self):
        r"""
        Reduce self for pickling.
        """
        data = self._to_dict()
        return(unpickle_wnf_v1, (self._k, self._N, self._chi, self._label,
                                 self._fi, self._prec, self._bitprec, data))

    def _to_dict(self):
        data = dict()
        data['atkin_lehner_eigenvalues'] = self._atkin_lehner_eigenvalues
        data['parent'] = self._parent
        data['coefficients'] = self._coefficients
        data['ap'] = self._ap
        data['embeddings'] = self._embeddings
        data['f'] = self._f
        data['embeddings'] = self._embeddings
        data['as_poly'] = self._as_polynomial_in_E4_and_E6
        data['twist_info'] = self._twist_info
        data['is_CM'] = self._is_CM
        data['satake'] = self._satake
        data['dimension'] = self._dimension
        return data

    def _from_dict(self, data):

        self._atkin_lehner_eigenvalues = data.get('atkin_lehner_eigenalues', {})
        # data['atkin_lehner_eigenalues']
        self._coefficients = data.get('coefficients', {})

        self._parent = data.get('parent', None)
        self._f = data.get('f', None)
        self._ap = data.get('ap', [])
        self._embeddings = data.get('embeddings', [])
        self._as_polynomial_in_E4_and_E6 = data.get('as_poly', '')
        self._twist_info = data.get('twist_info', '')
        self._is_CM = data.get('is_CM', '')
        self._satake = data.get('satake', {})
        self._dimension = data.get('dimension', 0)

    def _save_to_file(self, file):
        r"""
        Save self to file.
        """
        self.save(file, compress=None)

    def level(self):
        return self._N

    def group(self):
        if hasattr(self, '_parent'):
            return self._parent.group()

    def label(self):
        if(not self._label):
            self._label = self._parent().labels()[self._fi]
        return self._label

    def weight(self):
        if hasattr(self, '_k'):
            return self._k

    def character(self):
        if hasattr(self, '_character'):
            return self._character
        else:
            return trivial_character

    def conrey_character(self):
        return self._conrey_character

    def conrey_character_name(self):
        return "\chi_{" + str(self._N) + "}(" + str(self._conrey_character.number()) + ",\cdot)"

    def character_order(self):
        return self._parent.character_order()

    def character_conductor(self):
        return self._parent.character_conductor()

    def chi(self):
        if hasattr(self, '_chi'):
            return self._chi

    def prec(self):
        if hasattr(self, '_prec'):
            return self._prec

    def parent(self):
        if hasattr(self, '_parent'):
            return self._parent

    def is_rational(self):
        if(self.base_ring() == QQ):
            return True
        else:
            return False

    def _get_index_of_self_in_parent(self):
        # make sure we have a galois decomposition
        label = self._label
        fi = self._fi
        self._parent.galois_decomposition()
        if label not in self._parent._galois_orbits_labels:
            label = ''
        if fi >= 0 and fi < len(self._parent._galois_orbits_labels):
            label = self._parent._galois_orbits_labels[fi]
        if self._parent._galois_orbits_labels.count(label):
            j = self._parent._galois_orbits_labels.index(label)
        elif(len(self._parent._galois_orbits_labels) == 1):
            j = 0
        elif len(self._parent._galois_orbits_labels) > 0:
            raise ValueError("The space has dimension > 1. Please specify a label!")
        else:
            j = -1  # raise ValueError,"The space is zero-dimensional!"
        if self._verbose > 1:
            emf_logger.debug("J={0}".format(j))
        return j

    def dimension(self):
        r"""
        The dimension of this galois orbit is not necessarily equal to the degree of the number field, when we have a character....
        We therefore need this routine to distinguish between the two cases...
        """
        if not hasattr(self, '_dimension') or self._dimension is None or self._dimension <= 0:
            P = self.parent()
            if P.labels().count(self.label()) > 0:
                j = P.labels().index(self.label())
                self._dimension = self.parent().galois_decomposition()[j].dimension()
                return self._dimension
            else:
                return 0
        else:
            return self._dimension

    def q_expansion_embeddings(self, prec=10, bitprec=53):
        r""" Compute all embeddings of self into C which are in the same space as self.
        """
        if(len(self._embeddings) > prec):
            bp = self._embeddings[0][0].prec()
            if bp >= bitprec:
                res = list()
                #
                for n in range(max(prec, len(self._embeddings))):
                    l = list()
                    for i in range(len(self._embeddings[n])):
                        l.append(self._embeddings[n][i].n(bitprec))
                    res.append(l)
                return res
        if(bitprec <= 0):
            bitprec = self._bitprec
        if(prec <= 0):
            prec = self._prec
        if(self.base_ring() == QQ):
            self._embeddings = self.coefficients(range(prec))
        else:
            coeffs = list()
            # E,v = self._f.compact_system_of_eigenvalues(prec)
            cc = self.coefficients(range(prec))
            for n in range(ZZ(prec)):
                cn = cc[n]
                if(self.degree() > 1):
                    if hasattr(cn, 'complex_embeddings'):
                        coeffs.append(cn.complex_embeddings(bitprec))
                    else:  # real coefficients are repeated for consistency
                        ccn = []
                        for j in range(self.degree()):
                            ccn.append(cn)
                        coeffs.append(ccn)
                else:
                    coeffs.append([cn.n(bitprec)])
            self._embeddings = coeffs
        return self._embeddings

    def base_ring(self):
        if hasattr(self, '_base_ring'):
            return self._base_ring
        else:
            return None

    def degree(self):
        if hasattr(self, '_base_ring'):
            return _degree(self._base_ring)
        else:
            return None

    def coefficient(self, n):
        emf_logger.debug("In coefficient: n={0}".format(n))
        if not isinstance(n, [int, Integer]):
            return self.coefficients(n)
        return self.coefficients([n, n + 1])

    def coefficients(self, nrange=range(1, 10)):
        r"""
        Gives the coefficients in a range.
        We assume that the self._ap containing Hecke eigenvalues
        are stored.

        """
        res = []
        if not isinstance(nrange, list):
            M = nrange
            nrange = range(0, M)
        for n in nrange:
            if n == 1:
                res.append(1)
            elif n == 0:
                res.append(0)
            elif is_prime(n):
                pi = prime_pi(n) - 1
                # if self._verbose>0:
                #    print "pi=",pi
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
                        E, v = my_compact_system_of_eigenvalues(self._f, prime_range(ps, pe + 1), names='x')
                    else:
                        E, v = self._f.compact_system_of_eigenvalues(prime_range(ps, pe + 1), names='x')
                    c = E * v
                    # if self._verbose>0:
                    #    print "c="
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
                        an = self._f.eigenvalue(n, 'x')
                    except IndexError:
                        atmp = self._f.eigenvalue(next_prime(n), 'x')
                        an = self._f.eigenvalue(n, 'x')
                    # an = self._f.eigenvalue(QQ(n),'x')
                    self._coefficients[n] = an
                res.append(an)
        return res

    def q_expansion(self, prec=10):
        if hasattr(self._f, 'q_expansion'):
            return self._f.q_expansion(ZZ(prec))
        if hasattr(self._f, 'q_eigenform'):
            return self._f.q_eigenform(ZZ(prec), names='x')

    def atkin_lehner_eigenvalue(self, Q):
        r""" Return the Atkin-Lehner eigenvalues of self
        corresponding to Q|N
        """
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
                emf_logger.debug("self._f={0}".format(self._f))
                # try:
                M = self._compute_atkin_lehner_matrix(self._f, ZZ(Q))
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
            M = self._compute_atkin_lehner_matrix(self._f, ZZ(d))
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

    def twist_info(self, prec=10):
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
            self._twist_info = [True, self._f]
            return [True, self._f]

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
                (t, glist) = _get_newform(k, M, xig)
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
                                bf = self._f.q_eigenform(maxp + 1, names='x')[p]
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
                                    if((KF == QQ or KF.is_totally_real()) and (KG == QQ or KG.is_totally_real())):
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
            self._twist_info = [True, self._f]
        else:
            self._twist_info = [False, twist_candidates]
        return self._twist_info

    def is_CM(self):
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
        coeffs = self.coefficients(range(max_nump + 1))
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
        return self._is_CM

    def as_polynomial_in_E4_and_E6(self):
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
        v = vector(self.coefficients(range(d)))
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
        return [poldeg, monomials, X]

    def exact_cm_at_i_level_1(self, N=10):
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

    def cm_values(self, digits=12):
        r""" Computes and returns a list of values of f at a collection of CM points as complex floating point numbers.

        INPUT:

        -''digits'' -- we want this number of corrrect digits in the value

        OUTPUT:
        -''s'' string representation of a dictionary {I:f(I):rho:f(rho)}.

        TODO: Get explicit, algebraic values if possible!
        """

        emf_logger.debug("in cm_values with digits={0}".format(digits))
        # bits=max(int(53),ceil(int(digits)*int(4)))
        bits = ceil(int(digits) * int(4))
        CF = ComplexField(bits)
        RF = ComplexField(bits)
        eps = RF(10 ** -(digits + 1))
        if(self._verbose > 1):
            emf_logger.debug("eps={0}".format(eps))
        K = self.base_ring()
        print "K={0}".format(K)
        # recall that
        degree = K.absolute_degree()
        cm_vals = dict()
        # the points we want are i and rho. More can be added later...
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
            if(K == QQ):
                v1 = CF(0)
                v2 = CF(1)
                try:
                    for prec in range(minprec, maxprec, 10):
                        if(self._verbose > 1):
                            emf_logger.debug("prec={0}".format(prec))
                        print "q=",q
                        v2 = self._f.q_eigenform(prec).truncate(prec)(q)
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
                        c = self.coefficients(range(prec))
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
                                emf_logger.debug("v1[{0}".format(h, "]={0}".format(v1[h])))
                                emf_logger.debug("v2[{0}".format(h, "]={0}".format(v2[h])))
                                emf_logger.debug("err[{0}".format(h, "]={0}".format(err[h])))
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
        res = dict()
        res['embeddings'] = range(degree)
        res['tau_latex'] = dict()
        res['cm_vals_latex'] = dict()
        maxl = 0
        for tau in points:
            if tau == zi:
                res['tau_latex'][tau] = "\(" + latex(I) + "\)"
            else:
                res['tau_latex'][tau] = "\(" + latex(tau) + "\)"
            res['cm_vals_latex'][tau] = dict()
            for h in cm_vals[tau].keys():
                res['cm_vals_latex'][tau][h] = "\(" + latex(cm_vals[tau][h]) + "\)"
                l = len_as_printed(res['cm_vals_latex'][tau][h], False)
                if l > maxl:
                    maxl = l
        res['tau'] = points
        res['cm_vals'] = cm_vals
        res['max_width'] = maxl
        return res

    def satake_parameters(self, prec=10, bits=53):
        r""" Compute the Satake parameters and return an html-table.

        We only do satake parameters for primes p primitive to the level.
        By defintion the S. parameters are given as the roots of
         X^2 - c(p)X + chi(p)*p^(k-1)

        INPUT:
        -''prec'' -- compute parameters for p <=prec
        -''bits'' -- do real embedings intoi field of bits precision

        """
        if not hasattr(self, '_satake'):
            self._satake = {}
        elif(self._satake != {}):
            if len(self._satake.values()) < prime_pi(prec) or len(self._satake.values()[0].values()) == 0:
                self._satake = {}
            else:
                x = self._satake['thetas'].values()[0].values()[0]
                if x.prec() >= bits:  # else recompute
                    return self._satake
        K = self.base_ring()
        degree = _degree(K)
        RF = RealField(bits)
        CF = ComplexField(bits)
        ps = prime_range(prec)
        self._satake['ps'] = []
        alphas = dict()
        thetas = dict()
        aps = list()
        tps = list()
        k = self.weight()
        maxp = len(prime_range(prec))
        if len(self._ap) < maxp:
            E, v = my_compact_system_of_eigenvalues(self._f, ps)
            ap_vec = E * v
        else:
            ap_vec = self._ap
        emf_logger.debug("AP={0}".format(ap_vec))
        emf_logger.debug("K={0}".format(K))
        for j in range(degree):
            alphas[j] = dict()
            thetas[j] = dict()
        for j in xrange(len(ps)):
            p = ps[j]
            ap = ap_vec[j]
            if p.divides(self.level()):
                continue
            self._satake['ps'].append(p)
            chip = self.character()(p)
            # ap=self._f.coefficients(ZZ(prec))[p]
            if(K == QQ):
                f1 = QQ(4 * chip * p ** (k - 1) - ap ** 2)
                alpha_p = (QQ(ap) + I * f1.sqrt()) / QQ(2)
                ab = RF(p ** ((k - 1) / 2))
                norm_alpha = alpha_p / ab
                t_p = CF(norm_alpha).argument()
                thetas[0][p] = t_p
                alphas[0][p] = (alpha_p / ab).n(bits)
                # print "adding thetas=",thetas
            else:
                for jj in range(degree):
                    app = ap.complex_embeddings(bits)[jj]
                    f1 = (4 * CF(chip) * p ** (k - 1) - app ** 2)
                    alpha_p = (app + I * abs(f1).sqrt())
                    # ab=RF(/RF(2)))
                    # alpha_p=alpha_p/RealField(bits)(2)

                    alpha_p = alpha_p / RF(2)
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
        return self._satake

    def print_satake_parameters(self, stype=['alphas', 'thetas'], prec=10, bprec=53):
        emf_logger.debug("print_satake={0},{1}".format(prec, bprec))
        if self._f is None:
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
        K = self.base_ring()
        degree = _degree(K)
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
        bd = self._f.sturm_bound()
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
        if(prec is None):
            prec = self._prec
        s = my_latex_from_qexp(str(self.q_expansion(prec)))

        sb = list()
        if br > 0:
            sb = break_line_at(s, br)
            emf_logger.debug("print_q_exp: sb={0}".format(sb))
        if len(sb) <= 1:
            s = r"\(" + s + r"\)"
        else:
            s = r"\[\begin{align} &" + join(sb, "\cr &") + r"\end{align}\]"

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
                    emf_logger.debug("i={0} {1}".format(i, coeffs[n + 1][i]))
                    row.append(coeffs[n + 1][i])
                else:
                    row.append("")
            tbl['data'].append(row)

        s = html_table(tbl)
        return s

    def polynomial(self, format='latex'):
        r"""
        Here we have to check whether f is defined over a base ring over Q or over a CyclotomicField...
        """
        K = self.base_ring()
        if K is None:
            return ""
        if(self.dimension() == 1 and K == QQ):
            if(K == QQ):
                s = 'x'
            else:
                if format == 'latex':
                    s = latex(K.gen())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
        else:
            if(K.is_relative()):
                if format == 'latex':
                    s = latex(K.relative_polynomial())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
            else:
                if format == 'latex':
                    s = latex(self.base_ring().polynomial())
                elif format == 'html':
                    s = pol_to_html(K.relative_polynomial())
                else:
                    s = str(K.relative_polynomial())
        return s

    def print_atkin_lehner_eigenvalues(self):
        r"""
        """
        l = self.atkin_lehner_eigenvalues()
        if(len(l) == 0):
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
        if(l.keys().count(Cusp(Infinity)) == len(l.keys())):
            return ""
        if(len(l) == 0):
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
        K = self.base_ring()
        degree = _degree(K)
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
        qq = self._character.conductor()
        new_level = lcm(self.level(), lcm(q * q, q * qq))
        D = DirichletGroup(new_level)
        new_x = D(self._character) * D(x) * D(x)
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
    emf_logger.debug('Break at line, Input ={0}'.format(s))
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
        emf_logger.debug("l={0}".format(l))
        if l < brpt:
            stmp = join([stmp, sl[j]])
        else:
            res.append(stmp)
            stmp = sl[j]
        if j == len(sl) - 1:
            res.append(stmp)
    return res


def _get_newform(k, N, chi, fi=None):
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
    # print k,N,chi,fi
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
    if(K == QQ):
        return 1
    try:
        return K.absolute_degree()
        # if(K.is_relative()):
        #    return K.relative_degree()
        # return K.degree()
    except AttributeError:
        return -1  # exit silently


def unpickle_wnf_v1(k, N, chi, label, fi, prec, bitprec, data):
    F = WebNewForm(k=k, N=N, chi=chi, label=label, fi=fi, prec=prec, bitprec=bitprec, data=data)
    return F


def unpickle_wmfs_v1(k, N, chi, cuspidal, prec, bitprec, data):
    M = WebModFormSpace(k, N, chi, cuspidal, prec, bitprec, data)
    return M


def pol_to_html(p):
    r"""
    Convert polynomial p to html.
    """
    s = str(p)
    s = re.sub("\^(\d*)", "<sup>\\1</sup>", s)
    s = re.sub("\_(\d*)", "<sub>\\1</sub>", s)
    s = re.sub("\*", "", s)
    s = re.subst("x", "<i>x</i>", s)
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
