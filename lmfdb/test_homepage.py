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

    # All tests should pass: these are all the links in the home page as specified in index_boxes.yaml
    #
    # Box 1
    def test_box1(self):
        r"""
        Check that the links in Box 1 work.
        """
        homepage = self.tc.get("/").data
        self.check(homepage, "/L/degree2/", '9.53369')
        self.check(homepage, "/EllipticCurve/Q/?conductor=1-99", '[1, 0, 1, -14, -64]')
        self.check(homepage, "/ModularForm/GL2/Q/Maass/",  'The entire database consists of 16599 Maass forms.')
        self.check(homepage, "/zeros/first/", 'Riemann zeta function') # the interesting numbers are filled in dynamically
        self.check(homepage, "/NumberField/?degree=2", '"/NumberField/2.0.8.1">2.0.8.1')

    #
    # Box 2
    def test_box2(self):
        r"""
        Check that the links in Box 2 work.
        """
        homepage = self.tc.get("/").data
        self.check(homepage,"/L/Riemann/",  r'\[\zeta(1/2) \approx -1.4603545088\]')
        self.check(homepage,"/NumberField/3.1.23.1", r'Regulator:<td>&nbsp;&nbsp;<td>\( 0.281199574322962 \)')
        self.check(homepage,"/ModularForm/GL2/Q/holomorphic/1/12/1/a/", '0.2993668')
        self.check(homepage,"/L/ModularForm/GL2/Q/holomorphic/1/12/1/a/0/", 'approx 0.839345512')
        self.check(homepage,"/EllipticCurve/Q/234446/a/1", r'y^2 + x y = x^{3} -  x^{2} - 79 x + 289')
        self.check(homepage,"/L/EllipticCurve/Q/234446.a/", 'L-function $L(s,E)$ for the Elliptic Curve Isogeny Class 234446.a')

    # Box 3
    def test_box3(self):
        r"""
        Check that the links in Box 3 work.
        """
        homepage = self.tc.get("/").data
        self.check(homepage, "/L/", 'Holomorphic cusp form')
        self.check(homepage, "/ModularForm/", r'Maass Forms on \(\GL(2,\Q) \)')
        self.check(homepage, "/EllipticCurve/Q/", 'curve, label or isogeny class label')
        self.check(homepage, "/NumberField/", 'x^7 - x^6 - 3 x^5 + x^4 + 4 x^3 - x^2 - x + 1')

    # Box 4
    def test_box4(self):
        r"""
        Check that the links in Box 4 work.
        """
        homepage = self.tc.get("/").data
        self.check(homepage, "/L/degree4/MaassForm/", 'data on L-functions associated to Maass cusp forms for GSp(4) of level 1')
        self.check(homepage, "/EllipticCurve/Q/102/c/", r'1 &amp; 2 &amp; 4 &amp; 4 &amp; 8 &amp; 8')

    # Box 5
    def test_box5(self):
        r"""
        Check that the links in Box 5 work.
        """
        homepage = self.tc.get("/").data
        self.check(homepage, "/bigpicture", 'some varieties are modular')
        self.check(homepage, "/knowledge/", 'Recently modified Knowls')

    # Box 6
    def test_box6(self):
        r"""
        Check that the links in Box 6 work.
        """
        homepage = self.tc.get("/").data
        self.check_external(homepage, "https://github.com/LMFDB/lmfdb", 'Modular Forms Database')
        self.check_external(homepage, "http://sagemath.org/", 'mathematics software system')
        self.check_external(homepage, "http://pari.math.u-bordeaux.fr/", 'PARI/GP is a widely used computer algebra system')
        # I could not get this one to work -- JEC
        #self.check_external(homepage, "http://magma.maths.usyd.edu.au/magma/", 'Magma is a large, well-supported software package')
        self.check_external(homepage, "https://www.python.org/", 'Python Logo')
