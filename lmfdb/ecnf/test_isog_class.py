# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

class EcnfIsogClassTest(LmfdbTest):

    # All tests should pass
    #
    def test_ecnf_isgclass_title(self):
        r"""
        Check rendering of title name and base field of ECNF isogeny class.
        """
        L = self.tc.get('/EllipticCurve/2.0.7.1/16.1/CMa/').data
        assert 'Elliptic curves in class 16.1-CMa' in L
        assert 'minimal polynomial' in L

    def test_ecnf_label_in_isgclass(self):
        r"""
        Check curve in ECNF isogeny class by label.
        """
        L = self.tc.get('/EllipticCurve/2.0.3.1/2268.1/a/').data
        assert '2268.1-a5' in L

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


