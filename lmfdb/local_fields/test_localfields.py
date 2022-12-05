# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
        L = self.tc.get('/padicField/?n=8&c=24&gal=8T5&p=2&e=8&count=20')
        assert '4 matches' in L.get_data(as_text=True)

    def test_search_f(self):
        L = self.tc.get('/padicField/?n=6&p=2&f=3&search_type=List')
        dat = L.get_data(as_text=True)
        assert '2.6.4.1' not in dat
        assert '2.6.6.2' in dat

    def test_search_top_slope(self):
        L = self.tc.get('/padicField/?p=2&topslope=3.5')
        assert '81' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=3.4..3.55')
        assert '81' in L.get_data(as_text=True) # number of matches
        L = self.tc.get('/padicField/?p=2&topslope=7/2')
        assert '81' in L.get_data(as_text=True) # number of matches

    def test_field_page(self):
        L = self.tc.get('/padicField/11.6.4.2')
        assert 'x^{2} - x + 7' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...
        assert 'x^{3} - 11 t' in L.get_data(as_text=True) # bad (not robust) test, but it's the best i was able to find...

    def test_global_splitting_models(self):
        # The first one will have to change if we compute a GSM for it
        L = self.tc.get('/padicField/163.8.7.2')
        assert 'Not computed' in L.get_data(as_text=True)
        L = self.tc.get('/padicField/2.8.0.1')
        assert 'Does not exist' in L.get_data(as_text=True)

    def test_underlying_data(self):
        page = self.tc.get('/padicField/11.6.4.2').get_data(as_text=True)
        assert 'Underlying data' in page and 'data/11.6.4.2' in page
