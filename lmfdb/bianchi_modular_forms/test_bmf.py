# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

base_url = '/ModularForm/GL2/ImaginaryQuadratic/'

class BMFTest(LmfdbTest):

    def check(self, homepage, path, text):
        assert path in homepage
        assert text in self.tc.get(path, follow_redirects=True).data

    def check_args(self, path, text):
        if text in self.tc.get(path, follow_redirects=True).data:
            assert True
        else:
            print(text)
            print(self.tc.get(path, follow_redirects=True).data)
            assert False

    # All tests should pass
    #
    def test_home_page(self):
        r"""
        Check that the home page loads
        """
        L = self.tc.get(base_url)
        assert 'Bianchi modular forms' in L.data

    # Link to random newform
    def test_random(self):
        r"""
        Check that the link to a random curve works.
        """
        homepage = self.tc.get(base_url).data
        self.check(homepage, base_url+"random", 'Hecke eigenvalues')

    # Browsing links
    def test_browse(self):
        r"""
        Check that the browsing links work.
        """
        homepage = self.tc.get(base_url).data
        t = "?field_label=2.0.3.1"
        assert t in homepage
        self.check_args(base_url+t, "/ModularForm/GL2/ImaginaryQuadratic/2.0.3.1/124.1/a/")
        t = "?field_label=2.0.4.1"
        assert t in homepage
        self.check_args(base_url+t, "/ModularForm/GL2/ImaginaryQuadratic/2.0.4.1/164.1")
        t = "gl2dims/2.0.4.1"
        assert t in homepage
        self.check_args(base_url+t,'show both the dimension $d$ of the space of cusp forms of weight')
        t = '2.0.4.1/100.2/a/'
        assert t in homepage
        self.check_args(base_url+t,'Base change')

    #
    # Jump to specfic newform
    def test_jump(self):
        r"""
        Check that jumping to a specific newform by label works.
        """
        self.check_args(base_url+"?label=2.0.4.1-65.2-a", 'Analytic rank')


    #
    # Various search combinations
    def test_search(self):
        r"""
        Check that various search combinations work.
        """
        self.check_args(base_url+"?field_label=2.0.7.1&level_norm=322&count=10", 'Results (displaying all 4 matches)')
        self.check_args(base_url+"?start=0&count=100&field_label=&level_norm=&dimension=&include_base_change=off&include_cm=only&count=100", '/ModularForm/GL2/ImaginaryQuadratic/2.0.7.1/16384.9')

    #
    # tests for newspace pages

    def test_newspace(self):
        r"""
        Check newspace pages
        """
        self.check_args(base_url+'2.0.3.1/77283.1', 'are 2 cuspidal newforms')
        self.check_args(base_url+'2.0.11.1/207.6', 'Dimension of new cuspidal subspace:')
        # I don't know why the follwing fails, as the text was copied from the page source:
        #self.check_args(base_url+'2.0.11.1/207.6', '\((2 a + 13) = (\left(a - 1\right))^{2} \cdot (\left(a - 5\right)) \)')

    #
    # tests for individual newform pages
    def test_newform(self):
        r"""
        Check newform pages
        """
        base_url = '/ModularForm/GL2/ImaginaryQuadratic/'
        self.check_args(base_url+'2.0.11.1/207.6/b', 'Base change')
        self.check_args(base_url+'2.0.11.1/207.6/b', '2.0.11.1-207.6-b')
        self.check_args(base_url+'2.0.3.1/44332.1/a/', 'Elliptic curve isogeny class 2.0.3.1-44332.1-a')
        self.check_args(base_url+'2.0.3.1/44332.1/a/', '-238 a + 76')
        self.check_args(base_url+'2.0.11.1/256.1/a/', 'no, but is a twist of the base-change of a form over');
        self.check_args(base_url+'2.0.11.1/256.1/a/', 'Elliptic curve isogeny class 2.0.11.1-256.1-a');
        # A dimension 2 example
        self.check_args(base_url+'2.0.4.1/377.1/a2', 'The Hecke eigenfield is \(\Q(z)\) where  $z$ is a root of the defining');
