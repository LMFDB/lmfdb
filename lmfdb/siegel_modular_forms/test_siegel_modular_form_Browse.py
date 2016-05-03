# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2


class HomePageTest(LmfdbTest):

    def check(self,homepage,path,text):
        assert path in homepage
        assert text in self.tc.get(path).data

    def check_external(self, homepage, path, text):
        import urllib2
        assert path in homepage
        assert text in urllib2.urlopen(path).read()

    # All tests should pass: these are all the links in the browse page 
    def Siegel_links_browse_page(self):
        homepage = self.tc.get("/ModularForm/GSp/Q/").data
        self.check(homepage, "/ModularForm/GSp/Q/Sp4Z_j/", '\Upsilon_{20}')
        self.check(homepage, "/ModularForm/GSp/Q/Kp/", 'in level 277, the')
        self.check(homepage, "/ModularForm/GSp/Q/Sp6Z/", '12_Miyawaki (1)')
        self.check(homepage, "/ModularForm/GSp/Q/Sp8Z/", '16_Other_II (2)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_2/", '\Gamma_0(2)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma1_2/", '\Gamma_1(2)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma_2/", '\Gamma(2)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_3/", '$M_k\left(\Gamma_0(3)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_3_psi_3/", 'T.Ibukiyama:')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_4/", '\Gamma_0(4)')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_4_psi_4/", 'psi_4')
        self.check(homepage, "/ModularForm/GSp/Q/Gamma0_4_half/", 'k-1/2')


