# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class HigherGenusWithAutomorphismsTest(LmfdbTest):

    # All tests should pass
    #
    def test_url_label(self):
	L = self.tc.get('/HigherGenus/C/aut/2.24-8.0.2-4-6')
	assert '[ 0; 2, 4, 6 ]' in L.data


    def test_url_naturallabel(self):
	L = self.tc.get('/HigherGenus/C/aut/junk')
	assert 'No family with label junk was found in the database' in L.data
    



    def test_search_genus_group(self):
        L = self.tc.get('/HigherGenus/C/aut/?genus=2&group=%5B48%2C29%5D&signature=&dim=&hyperelliptic=include&count=20&Submit=Search')
        assert '2 matches' in L.data
