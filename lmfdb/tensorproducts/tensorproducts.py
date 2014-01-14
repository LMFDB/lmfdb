r"""

AUTHORS: Chris Wuthrich, 2014

Example:

    sage: import lmfdb
    sage: from lmfdb.tensorproducts.tensorproducts import *
    sage: V = TensorProduct("11.a2", 37, 4)
    sage: V.conductor()
    15059
    sage: V.root_number()
    (-0.6332531838242617+0.7739447042111184j)
    sage: V.an_list(30)
    [0,
    (1+0j),
    (-1.3289260487773493-0.48368952529595044j),
    (0.5425317875662491-0.19746542181734933j),
    (0.766044443118978+0.6427876096865393j),
    (-0.07765782588644339+0.4404194161008241j),
    (-0.8164965809277261+9.999199243478976e-17j),
    (-0.1312656839217877+0.7444446867653208j),
    0j,
    (-0.5106962954126518+0.4285250731243597j),
    (0.3162277660168378-0.5477225575051661j),
    (-0.15075567228888195-0.2611164839335467j),
    (0.5425317875662492+0.1974654218173492j),
    (-0.8498500058306874-0.7131088264485382j),
    (0.534522483824848-0.9258200997725519j),
    (0.04483576668021919+0.25427626844214857j),
    (-0.17364817766693041-0.984807753012208j),
    (0.37158613563494186-0.3117977893618706j),
    (0.8859506991848998-0.3224596835306336j),
    0j,
    (-0.3425854897200011+0.2874633580707409j),
    (0.07578627794760465+0.42980534030074463j),
    (0.07404383174487171+0.4199234368295236j),
    (-0.10425720702853725+0.1805787796286539j),
    -0j,
    (0.7517540966287267+0.2736161146605349j),
    (0.7844645405527368+1.3587324409735146j),
    (-0.48112522432468796+0.8333333333333334j),
    (-0.5790751684902228+0.4859017603040675j),
    0j,
    (0.06340734931856157-0.3596009474205084j)]

"""

########################################################################
#       Copyright (C) Chris Wuthrich 2014
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################

import os
import weakref

import lmfdb.base


from sage.structure.sage_object import SageObject
from sage.misc.all import verbose

# import sage.rings.all
from sage.schemes.elliptic_curves.constructor import EllipticCurve
#from sage.rings.arith import binomial
#from sympowlmfdb import sympowlmfdb

from lmfdb.WebCharacter import *

class TensorProduct(SageObject):

    def __init__(self, Elabel, modulus, number):
        """
        tensor product of an elliptic curve E over Q and a
        Dirichlet character chi given by a modulus and a number.

        (more to come)
        """
        C = lmfdb.base.getDBConnection()
        Edata = C.elliptic_curves.curves.find_one({'lmfdb_label': Elabel})
        if Edata is None:
            raise ValueError
        ainvs = [int(a) for a in Edata['ainvs']]
        E = EllipticCurve(ainvs)
        cremona_label = Edata['label']
        lmfdb_label = Edata['lmfdb_label']

        args = {'type':'Dirichlet', 'modulus':modulus, 'number':number}
        chi = WebDirichletCharacter(**args)
        chi = chi.H[number]

        #chi_sage = chi.chi.sage_character().primitive_character()
        chi = chi.primitive_character()

        NE = E.conductor()
        Nchi = chi.conductor()
        # test hypothesis
        if not NE.gcd(Nchi ** 2).is_squarefree():
            raise ValueError

        self.E = E
        self.chi = chi
        self.NE = NE
        self.Nchi = Nchi
        self.N = self.conductor()
 #       self.root_number = self.root_number()

    def temp(self):
        # check if chi is the trivial character, in which case we return the
        # elliptic curve
        if self.chi.is_trivial():
            from lmfdb.elliptic_curve.elliptic_curve import render_curve_webpage_by_label
            return render_curve_webpage_by_label(label=Elabel)
        # check if chi is of order  two. in which case we return the quadratic
        # twist of the elliptic curve
        #if self.chi_sage.order() == 2:

    def conductor(self):
        """
        Conductor of the tensor product. Formula provided by Dokchitser bros.
        Wrong without the hypothesis
        """
        return self.NE * self.Nchi**2 // self.NE.gcd(self.Nchi ** 2)

    def root_number(self):
        """
        Root number of the tensor product. Formula provided by Dokchitser bros.
        Wrong without the hypothesis.
        """
        g = self.NE.gcd(self.Nchi)
        wE = self.E.root_number()
        if self.chi.is_odd():
            saa = -1
        else:
            saa = 1
        wchi_square = saa * self.Nchi / (self.chi.gauss_sum_numerical()) ** 2
        chin = self.chi( -self.NE// g )
        # this will fail if the hypothesis is not correct.
        b = prod( - self.E.ap(p) for p in g.prime_divisors() )
        assert b == 1 or b == -1
        return wE * wchi_square * chin * b

    def an_list(self, upper_bound=10000):
        """
        compute the new coefficients of the Dirichlet series of self
        by multiplying simply with chi(n).
        This will be wrong when the hyptothesis does not hold

        Note : this is still algebraically normalised s <-> 2-s
        """
        li = self.E.anlist(upper_bound)
        for n in range(1,len(li)):
            li[n] *= self.chi(n)
        return li


