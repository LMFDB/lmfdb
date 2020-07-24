# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class HomePageTest(LmfdbTest):
    # All tests should pass: these are all the links in the home page as specified in index_boxes.yaml
    #
    # Box 1
    def test_box1(self):
        r"""
        Check that the links in Box 1 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check(homepage, "/L/degree2/", '9.53369')
        self.check(homepage, "/EllipticCurve/Q/?conductor=1-99", '[1, 0, 1, -11, 12]')
        self.check(homepage, "/ModularForm/GL2/Q/Maass/",  '/BrowseGraph/1/10/0/10/')
        self.check(homepage, "/zeros", 'The zeros are accurate') # the interesting numbers are filled in dynamically
        self.check(homepage, "/NumberField/?degree=2", '"/NumberField/2.0.8.1">2.0.8.1')

    #
    # Box 2
    def test_box2(self):
        r"""
        Check that the links in Box 2 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check(homepage,"/L/Riemann/",  r'Pole at \(s=1\)')
        self.check(homepage,"/ModularForm/GL2/Q/holomorphic/1/12/a/a/", '4830')
        self.check(homepage,"/ModularForm/GL2/Q/holomorphic/1/12/a/a/", '113643')
        self.check(homepage,"/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/", '0.792122')
        self.check(homepage,"/EllipticCurve/Q/5077/a/1", r'y^2 + y = x^{3} - 7 x + 6')
        self.check(homepage,"/L/EllipticCurve/Q/5077.a/", '5077')

    # Box 3
    def test_box3(self):
        r"""
        Check that the links in Box 3 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check(homepage, "/L/", 'Dirichlet')
        self.check(homepage, "/L/", 'Symmetric square')
        self.check(homepage, "/L/", 'Genus 2 curve')
        self.check(homepage, "/ModularForm", 'Maass forms')
        self.check(homepage, "/EllipticCurve/Q/", 'by coefficients')
        self.check(homepage, "/NumberField/", 'x^7 - x^6 - 3 x^5 + x^4 + 4 x^3 - x^2 - x + 1')

    # Box 4
    def test_box4(self):
        r"""
        Check that the links in Box 4 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check(homepage, "/L/degree4/MaassForm/", 'data on L-functions associated to Maass cusp forms for GSp(4) of level 1')
        self.check(homepage, "/EllipticCurve/Q/102/c/", r'1 &amp; 2 &amp; 4 &amp; 4 &amp; 8 &amp; 8')

    # Box 5
    def test_box5(self):
        r"""
        Check that the links in Box 5 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check(homepage, "/universe", 'universe')
        # removed in PR #1167
        #self.check(homepage, "/knowledge/", 'Recently modified Knowls')
