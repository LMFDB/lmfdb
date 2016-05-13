# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class HMFTest(LmfdbTest):
    def test_home(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/')
        assert 'Hilbert' in L.data
        assert 'cusp forms' in L.data
        assert 'modular' in L.data
        assert 'Browse' in L.data
        assert 'Search' in L.data
        assert 'Find' in L.data
        assert '\sqrt{2}' in L.data #552

    def test_random(self): #993
        L = self.tc.get('/ModularForm/GL2/TotallyReal/random')
        assert 'edirect' in L.data

    def test_EC(self): #778
        L = self.tc.get('ModularForm/GL2/TotallyReal/6.6.300125.1/holomorphic/6.6.300125.1-631.2-d')
        assert 'Elliptic curve not available' in L.data     #TODO remove or change url when
                                                            #the elliptic curve is in the database
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.89.1/holomorphic/2.2.89.1-2.1-a')
        assert 'Isogeny class' in L.data
        assert 'EllipticCurve/2.2.89.1/2.1/a' in L.data

    def test_typo(self): #771
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=2.2.5.1') 
        assert 'or change' in L.data

    def test_large(self): #616
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=4.4.2000.1&count=1200')
        assert '719.2-c' in L.data

    def test_range_search(self): #547
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?disc=1..100&count=100')
        assert '209.1-b' in L.data
        assert 'Next' in L.data #435

    def test_bad_input_search(self): #547
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=hello&count=100')
        assert 'not a valid input' in L.data

    def test_search(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?start=0&deg=2..5&disc=60-200&level_norm=40-90&dimension=3..5&count=100')
        assert '70.1-o' in L.data

    def test_hmf_page(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.73.1/holomorphic/2.2.73.1-48.4-b')
        assert 'no' in L.data
        assert '-6' in L.data
        assert '2w + 10' in L.data
        assert '1.1.1.1' in L.data
        assert '[2, 2]' in L.data

    def test_hmf_page_higherdim(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.60.1/holomorphic/2.2.60.1-44.1-c')
        assert '-2w - 4' in L.data
        assert '2e' in L.data
        assert 'defining polynomial' in L.data

    def test_by_field(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/?field_label=4.4.725.1')
        assert 'w - 4' in L.data

    def test_download_sage(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/4.4.725.1/holomorphic/4.4.725.1-31.1-a/download/sage')
        assert 'NN = ZF.ideal([31, 31, w^3 - 4*w + 1])' in L.data
        assert '[89, 89, 3*w^3 - 2*w^2 - 7*w],\\' in L.data
        assert 'hecke_eigenvalues_array = [4, -4,' in L.data

    def test_download_magma(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/4.4.725.1/holomorphic/4.4.725.1-31.1-a/download/magma')
        assert 'NN := ideal<ZF | {31, 31, w^3 - 4*w + 1}>;' in L.data
        assert '[89, 89, 3*w^3 - 2*w^2 - 7*w],' in L.data
        assert 'heckeEigenvaluesArray := [4, -4,' in L.data

    def test_Lfun_link(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a')
        assert         'L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a' in L.data

    def test_browse(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/browse/')
        assert 'by field degree' in L.data
        assert 'database contains' in L.data
        assert 'data is complete up to' in L.data

    def test_browse_by_degree(self):
        L = self.tc.get('/ModularForm/GL2/TotallyReal/browse/2/')
        assert 'Number of newforms' in L.data
