# -*- coding: utf-8 -*-
import unittest2
from lmfdb.tests import LmfdbTest

class TensorProductTest(LmfdbTest):
    """
    These tests check whether we can still take tensor products of the things
    we're supposed to be able to take tensor products of.  If naming 
    conventions are changed for the objects we're forming tensor products of
    then these tests will fail.  The test is the assertion that the correct
    conductor is displayed somewhere on the page.
    """

    @unittest2.skip("Tests tensor product of elliptic curve and Dirchlet L-functions -- skipping all tensor product tests ")
    def test_ellcurve_dirichletchar(self):
        L = self.tc.get("/TensorProducts/show/?obj1=Character%2FDirichlet%2F13%2F2&obj2=EllipticCurve%2FQ%2F11.a2")
        assert '1859' in L.data

    @unittest2.skip("Tests tensor product of artin rep and modular form L-functions -- skipping all tensor product tests ")
    def test_modform_artinrep(self):
        L1 = self.tc.get("ModularForm/GL2/Q/holomorphic/1/12/1/a/")
        assert "6048q^{6}" in L1.data
        # the following lines need changing after Artin rep
        # relabelling.  Perhaps "ArtinRepresentation/2.31.3t2.1c1"
        L2 = self.tc.get("ArtinRepresentation/2/31/1/")
        assert "(1,2,3)" in L2.data
        L = self.tc.get("TensorProducts/show/?obj1=ModularForm%2FGL2%2FQ%2Fholomorphic%2F1%2F12%2F0%2Fa%2F0&obj2=ArtinRepresentation%2F2%2F31%2F1%2F")
        assert '961' in L.data
