# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class HigherGenusWithAutomorphismsTest(LmfdbTest):

    # All tests should pass
    #
    def test_url_label(self):
		L = self.tc.get('/HigherGenus/C/aut/2.12T13.0.2-4-6')
		assert '[0;2,4,6]' in L.data


    def test_url_naturallabel(self):
		L = self.tc.get('/HigherGenus/C/aut/junk')
		assert 'was not found in the database' in L.data # error mesage



