# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest

class LocalFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
		L = self.tc.get('/LocalNumberField/?start=0&paging=0&n=8&c=24&gal=8T5&p=2&e=8&count=20')
		assert '4 matches' in L.data

    def test_field_page(self):
		L = self.tc.get('/LocalNumberField/11.6.4.2')
		assert 't^{2} - t + 7' in L.data # bad (not robust) test, but it's the best i was able to find...
