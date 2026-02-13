# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class ShimCrvTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ShimuraCurve/Q/')
        assert 'Shimura curves' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert 'X_0(N)' in L.get_data(as_text=True)
