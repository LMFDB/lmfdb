# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class Genus2Test(LmfdbTest):

    # All tests should pass
    #
    def test_by_full_label(self):
        L = self.tc.get('/Genus2Curve/Q/277/a/277/1')
        assert '277' in L.data

    def test_by_double_iso_label(self):
        L = self.tc.get('/Genus2Curve/Q/336/a/')
        assert '336.a.172032.1' in L.data

    def test_by_g2c_label(self):
        L = self.tc.get('/Genus2Curve/Q/169.a.169.1')
        assert '13' in L.data

    def test_Cond_search(self):
        L = self.tc.get('/Genus2Curve/Q/?cond=100-200&count=100')
        assert '196.a.21952.1' in L.data

