r"""

AUTHORS: Chris Wuthrich, 2014

Example:


"""

########################################################################
#       Copyright (C) Chris Wuthrich 2014
#
#  Distributed under the terms of the GNU General Public License (GPL)
#
#                  http://www.gnu.org/licenses/
########################################################################

#import os
#import weakref

#import lmfdb.base
from lmfdb.WebCharacter import *

from sage.structure.sage_object import SageObject
#from sage.schemes.elliptic_curves.constructor import EllipticCurve
#from sage.rings.rational import Rational
from sage.rings.integer_ring import ZZ

class GaloisRepresentation(SageObject):

    def __init__(self, thingy):
        """
        Class representing a L-function coming from a Galois representation.
        Typically, dirichlet characters, artin reps, elliptic curves,...
        can give rise to such a class.

        It can be used for tensor two such together (mul below) and a
        L-function class can be extracted from it.
        """
        self.sign = 0 # not yet set

        if isinstance(thingy, sage.schemes.elliptic_curves.ell_rational_field.EllipticCurve_rational_field):
            self.init_elliptic_curve(thingy)

## Various ways to construct such a class

    def init_elliptic_curve(self, E):
        """
        Returns the Galois rep of an elliptic curve over Q
        """
        # needed ?
        # Remove the ending number (if given) in the label to only get isogeny
        # class
        #while self.label[len(self.label) - 1].isdigit():
            #self.label = self.label[0:len(self.label) - 1]
        ## Create the elliptic curve in the database
        #Edata = LfunctionDatabase.getEllipticCurveData(self.label + '1')
        #if Edata is None:
            #raise KeyError('No elliptic curve with label %s exists in the database' % self.label)
        #self.db_object = Edata

        self.original_object = [E]
        self.object_type = "ellipticcurve"
        self.dim = 2
        self.degree = self.dim
        self.weight = 2
        self.motivic_weight = 1
        self.conductor = E.conductor()
        self.sign = E.root_number()
        self.mu = []
        self.nu = [ZZ(1)/ZZ(2)]
        self.gammaV = [0, 1]
        self.langlands = True
        self.selfdual = True
        self.primitive = True
        self.set_dokchitser_Lfunction()
        self.set_number_of_coefficients()
        self.dirichlet_coefficients = E.anlist(self.numcoeff)[1:]
        self.coefficient_type = 2
        self.coefficient_period = 0


## These are used when creating the classes with the above

    def set_dokchitser_Lfunction(self):
        """
        The L-function calling Dokchitser's code
        """
        if self.sign != 0:
            self.ld = Dokchitser(conductor = self.conductor,
                                gammaV = self.gammaV,
                                weight = self.motivic_weight,
                                eps = self.sign,
                                poles = [],
                                residues = [])
        else:
            # find the sign from the functional equation
            self.sign = 0


    def set_number_of_coefficients(self):
        """
        Determines the number of coefficients needed using Dokchitser's
        """
        self.numcoeff = 1000

## A function that gives back a L-function class as used later

    def Lfunction(self):
        """
        The L-function object associated to this class
        """
        from lmfdb.lfunctions.Lfunction import Lfunction_TensorProduct
        return Lfunction_GaloisRep(self)

## various direct accessible functions


    def root_number(self):
        """
        Root number
        """
        return self.sign

    def dimension(self):
        """
        Dimension = Degree
        """
        return self.dim

    def weight(self):
        """
        Motivic weight
        """
        return self.motivic_weight



