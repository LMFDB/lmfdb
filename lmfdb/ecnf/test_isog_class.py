# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class EcnfIsogClassTest(LmfdbTest):

    # All tests should pass
    #
    def test_ecnf_isgclass_title(self):
        r"""
        Check rendering of title name of ECNF isogeny class.
        """
        L = self.tc.get('/EllipticCurve/2.0.7.1/%5B16%2C10%2C1%5D/CMa/').data
        assert 'Elliptic curves in class [16,10,1]-CMa' in L

    def test_ecnf_label_in_isgclass(self):
        r"""
        Check curve in ECNF isogeny class by label.
        """
        L = self.tc.get('/EllipticCurve/2.0.3.1/%5B2268%2C36%2C18%5D/a/').data
        assert '[2268,36,18]-a5' in L

    def test_ecnf_weiercoeffs_in_isgclass(self):
        r"""
        Check curve in ECNF isogeny class by Weierstrass coefficients.
        """
        L = self.tc.get('/EllipticCurve/2.2.497.1/4.1/c/').data
        assert '142456112775' in L

    def test_ecnf_isgmatrix_in_ecnf_isgclass(self):
        r"""
        Check isogeny matrix of ECNF isogeny class.
        """
        L = self.tc.get('/EllipticCurve/2.2.89.1/81.1/a/').data
        assert '267' in L
        assert '89' in L

    def test_ecnf_isclass_related_object(self):
        r"""
        Check related object (near Properties box) of an ECNF isogeny class.
        """
        L = self.tc.get('/EllipticCurve/2.2.5.1/31.1/a/').data
        assert 'Hilbert Modular Form 2.2.5.1-31.1-a' in L


