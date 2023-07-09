# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class ModCrvTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ModularCurve/Q/')
        assert 'Modular curves' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert 'X_0(N)' in L.get_data(as_text=True)
