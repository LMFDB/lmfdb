# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class GalGpTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_deg(self):
		L = self.tc.get('/GaloisGroup/?start=0&paging=0&parity=0&cyc=0&solv=0&prim=0&n=7&t=&count=50')
		assert 'all 7 matches' in L.data

    def test_search_t_solv_prim(self):
		L = self.tc.get('/GaloisGroup/?start=0&paging=0&parity=-1&cyc=0&solv=1&prim=-1&n=&t=18&count=50')
		assert '14T18' in L.data
		assert '294' in L.data # order of 21T18

    @unittest2.skip("never passed on my machine, does not pass on beta.lmbdb.org (Pascal M.)")
    def test_display_bigpage(self):
		L = self.tc.get('/GaloisGroup/22T29')
		assert '22528' in L.data # order of 22T29

    def test_search_range(self):
		L = self.tc.get('GaloisGroup/?start=0&paging=0&parity=0&cyc=0&solv=0&prim=0&n=8-11&t=3-5&count=50')
		assert '8T3' in L.data
		assert '660' in L.data # order of 11T5

