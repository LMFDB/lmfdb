# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class NumberFieldTest(LmfdbTest):

    # All tests should pass
    #
    def test_search_ramif_cl_deg(self):
		L = self.tc.get('/NumberField/?start=0&paging=0&degree=5&signature=&galois_group=&class_number=&class_group=[2%2C2]&ur_primes=7&discriminant=&ram_quantifier=some&ram_primes=2%2C3%2C5&count=20')
		assert '5.1.27000000000.8' in L.data

    def test_search_poly_mean2parser(self):
		L = self.tc.get('/NumberField/?natural=X**3-4x%2B2&search=Go')
		assert '148' in L.data # discriminant

    def test_search_zeta(self):
		L = self.tc.get('/NumberField/?natural=Qzeta23&search=Go', follow_redirects=True)
		assert '[3]' in L.data # class group

    def test_search_sqrt(self):
		L = self.tc.get('/NumberField/?natural=Qsqrt-163&search=Go', follow_redirects=True)
		assert '41' in L.data # minpoly

    def test_search_disc(self):
		L = self.tc.get('/NumberField/?start=&paging=0&degree=&signature=&galois_group=&class_number=&class_group=&ur_primes=&discriminant=1988-2014&ram_quantifier=all&ram_primes=&count=')
		assert '401' in L.data # factor of one of the discriminants

    def test_url_label(self):
		L = self.tc.get('/NumberField/2.2.5.1')
		assert '0.481211825059603' in L.data # regulator

    def test_url_naturallabel(self):
		L = self.tc.get('/NumberField/Qsqrt5')
		assert '0.481211825059603' in L.data # regulator

    def test_url_naturallabel(self):
		L = self.tc.get('/NumberField/junk')
		assert 'Error' in L.data # error mesage



