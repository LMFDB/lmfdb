from lmfdb.base import LmfdbTest
import math
import unittest2


class GalGpTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_deg(self):
		L = self.tc.get('/GaloisGroup/?start=0&paging=0&parity=0&cyc=0&solv=0&prim=0&n=7&t=&count=50')
		assert 'all 7 matches' in L.data
