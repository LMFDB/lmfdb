# -*- coding: utf8 -*-
from base import LmfdbTest
from flask import url_for
import unittest2

class TensorProductTest(LmfdbTest):
    """
    These tests check whether we can still take tensor products of the things
    we're supposed to be able to take tensor products of.  If naming 
    conventions are changed for the objects we're forming tensor products of
    then these tests will fail.  The test is the assertion that the correct
    conductor is displayed somewhere on the page.
    """

    def test_ellcurve_dirichletchar(self):
        L = self.tc.get("/TensorProducts/show/?obj1=Character%2FDirichlet%2F13%2F2&obj2=EllipticCurve%2FQ%2F11.a2")
        assert '1859' in L.data

    @unittest2.skip("sage error to be fixed")
    def test_modform_artinrep(self):
        L = self.tc.get("TensorProducts/show/?obj1=ModularForm%2FGL2%2FQ%2Fholomorphic%2F1%2F12%2F0%2Fa%2F0&obj2=ArtinRepresentation%2F2%2F31%2F1%2F")
        assert '961' in L.data 

