# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest

class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
		L = self.tc.get('/LocalNumberField/?start=0&paging=0&n=8&c=24&gal=8T5&p=2&e=8&count=20')
		assert '4 matches' in L.data

    def test_search_top_slope(self):
		L = self.tc.get('/LocalNumberField/?p=2&topslope=3.5')
		assert '81' in L.data # number of matches
		L = self.tc.get('/LocalNumberField/?p=2&topslope=topslope=3.4..3.55')
		assert '81' in L.data # number of matches
		L = self.tc.get('/LocalNumberField/?p=2&topslope=topslope=7/2')
		assert '81' in L.data # number of matches

    def test_field_page(self):
		L = self.tc.get('/LocalNumberField/11.6.4.2')
		assert 'x^{2} - x + 7' in L.data # bad (not robust) test, but it's the best i was able to find...
		assert 'x^{3} - 11 t' in L.data # bad (not robust) test, but it's the best i was able to find...

    def test_global_splitting_models(self):
	# The first one will have to change if we compute a GSM for it
        L = self.tc.get('/LocalNumberField/163.8.7.2')
        assert 'Not computed' in L.data
        L = self.tc.get('/LocalNumberField/2.8.0.1')
        assert 'Does not exist' in L.data

