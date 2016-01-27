# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class Genus2Test(LmfdbTest):

    # All tests should pass

    def test_Cond_search(self):
        L = self.tc.get('/Genus2Curve/Q/?cond=100-200&count=100')
        assert '196.a.21952.1' in L.data

    def test_by_double_iso_label(self):
        L = self.tc.get('/Genus2Curve/Q/336/a/')
        assert '336.a.172032.1' in L.data

    def test_by_full_label(self):
        # Two elliptic curve factors and decomposing endomorphism algebra:
        L = self.tc.get('/Genus2Curve/Q/1088/b/2176/1')
        assert '32.a1' in L.data and '34.a3' in L.data
        # QM curve:
        L = self.tc.get('Genus2Curve/Q/262144/d/524288/1')
        assert 'quaternion algebra' in L.data
        L = self.tc.get('Genus2Curve/Q/4096/b/65536/1')
        # Square over a quadratic extension that is CM over one extension and
        # multiplication by a quaternion algebra ramifying at infinity over
        # another:
        assert 'square of an elliptic curve' in L.data and '2.2.8.1-64.1-a3'\
            in L.data and r'\mathbf{H}' in L.data and '(CM)' in L.data

    def test_by_g2c_label(self):
        # This curve also decomposes as a square, this time of a curve without
        # a label:
        L = self.tc.get('/Genus2Curve/Q/169.a.169.1')
        assert 'square of an elliptic curve' in L.data and '\Z/{19}\Z'\
            in L.data
