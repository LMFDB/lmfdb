# -*- coding: utf-8 -*-

from lmfdb.base import LmfdbTest
import unittest2

from . import cmf_logger
cmf_logger.setLevel(100)

class CmfTest(LmfdbTest):
    def runTest():
        pass

    def test_browse_page(self):
        r"""
        Check browsing for elliptic modular forms
        """
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/").data
        assert '?search_type=Dimensions' in data
        assert '?submit=Dimensions&char_order=1' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=Dimensions",follow_redirects=True).data
        assert r'<a href="/ModularForm/GL2/Q/holomorphic/19/5/">69</a>' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?submit=Dimensions&char_order=1", follow_redirects=True).data
        assert r'<a href="/ModularForm/GL2/Q/holomorphic/18/4/a/">13</a>' in data

    @unittest2.skip("Long tests for many newform spaces, should be run & pass before any release")
    def test_many(self):
        from sage.all import ZZ, sqrt
        for Nk2 in range(1,2001):
            for N in ZZ(Nk2).divisors():
                    k = sqrt(Nk2/N)
                    if k in ZZ and k > 1:
                        print("testing (N, k) = (%s, %s)" % (N, k))
                        url  = "/ModularForm/GL2/Q/holomorphic/{0}/{1}/".format(N, k)
                        rv = self.tc.get(url,follow_redirects=True)
                        self.assertTrue(rv.status_code==200,"Request failed for {0}".format(url))
                        assert str(N) in rv.data
                        assert str(k) in rv.data
                        assert str(N)+'.'+str(k) in rv.data

    def test_delta(self):
        r"""
        Check that the Delta function is ok....
        Recall that this version uses the old urls...
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/")
        assert '1.12.a.a' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/a/")
        assert '1.12.a.a' in page.data
        assert '16744' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/a/a/")
        assert '24q^{2}' in page.data
        assert '84480q^{8}' in page.data
        assert '0.299366' in page.data
        assert '0.954138 i' in page.data
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/')
        assert '0.792122' in page.data

    def test_level11(self):
        r"""
        Check that the weight 2 form of level 11 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/a/a/")
        assert '2q^{2}' in page.data
        assert '2q^{4}' in page.data
        assert r'\(-0.707106\)' in page.data
        assert r'\(0.707106 i\)' in page.data
        assert r'\(0.957427 i\)' in page.data
        assert r'\(0.223606\)' in page.data
        assert r'\(0.974679 i\)' in page.data
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/a/a/')
        assert '0.253841' in page.data

    def test_triv_character(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/8/a/a/")
        assert r'1016q^{7}' in page.data
        assert '0.375659' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/3/6/a/a/")
        assert '168q^{8}' in page.data
        assert '0.0536656' in page.data

    def test_non_triv_character(self):
        r"""
        Check that non-trivial characters are also working.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/2/e/a/")
        assert r'\Q(\zeta_{6})' in page.data
        assert r'x^{2}' in page.data
        assert '0.866025' in page.data
        assert r'6q^{6}' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/4/b/a/")
        assert r'46q^{9}' in page.data
        assert r'\Q(\sqrt{-1})' in page.data
        assert r'10 i' in page.data

    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/a/")
        assert '11241' in page.data
        assert '10099' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/1/",  follow_redirects=True)
        assert '11241' in page.data
        assert '10099' in page.data

    def test_empty(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/2/a/")
        assert 'The following table gives the dimensions of various   subspaces of \(M_{2}(\Gamma_0(2))\).' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/3/a/")
        assert 'weight is odd while the character is ' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/6/a/")
        assert 'Decomposition</a> of \(S_{6}^{\mathrm{old}}(\Gamma_0(12))\) into   lower level spaces' in page.data


    def test_not_in_db(self):
        # The following redirects to "ModularForm/GL2/Q/holomorphic/12000/12/"
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/")
        assert 'Space not in database' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/a/")
        assert 'Space 12000.12.a not found' in page.data

    def test_character_validation(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/e/")
        assert 'Space 12.10.e not found' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/c/")
        assert 'since the weight is even while the character is' in page.data

    def test_decomposition(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/6/12/", follow_redirects=True)
        assert r'Decomposition</a> of \(S_{12}^{\mathrm{new}}(\Gamma_1(6))\)' in page.data

    def test_dim_table(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=1-100&submit=Dimensions", follow_redirects=True)
        assert 'Dimension Search Results' in page.data

    def test_character_parity(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/c/")
        assert 'since the weight is even while the character is' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/3/a/")
        assert 'since the weight is odd while the character is' in page.data

    def test_coefficient_fields(self):
        r"""
        Test the display of coefficient fields.
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/9/8/a/')
        assert '\Q(\sqrt{10})' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/11/6/a/')
        assert '3.3.54492.1' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/27/2/e/a/')
        assert '12.0.1952986685049.1' in page.data

    def test_satake(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/11/2/a/a/')
        assert r'\(-0.707106\)' in page.data
        assert r'\(0.707106 i\)' in page.data
        assert r'\(0.957427 i\)' in page.data
        assert r'\(0.223606\)' in page.data
        assert r'\(0.974679 i\)' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7/3/b/a/')
        assert r'\(-0.750000\)' in page.data
        assert r'\(0.661437 i\)' in page.data
        assert r'\(-0.272727\)' in page.data
        assert r'\(1\)' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7/3/b/a/?&format=satake_angle')
        assert '\(\pi\)' in page.data
        assert '\(0.769946\pi\)' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/21/2/e/a/?format=satake')
        assert r'\(-0.965925\)' in page.data
        assert r'\(0.258819 i\)' in page.data
        assert r'\(0.990337 i\)' in page.data


    def test_download(self):
        r"""
        Test download function
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_qexp/27.2.e.a', follow_redirects=True)
        assert '[8,11,-17,-11,-4,3,0,-15,-1,-3,4,7]' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_traces/27.2.e.a', follow_redirects=True)
        assert '[0, 12, -6, -6, -6, -3, 0, -6, 6, 0, -3, 3, 12, -6, 15, 9, 0, 9, 9, -3, -3, -12, 3, -12, -18, 3, -30' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_cc_data/27.2.e.a', follow_redirects=True)
        assert '0.5, -2.2282699087' in page.data
        assert '-12.531852282' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_satake_angles/27.2.e.a', follow_redirects=True)
        assert '0.5, -2.2282699087' in page.data
        assert '0.406839418685' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/download_newform/27.2.e.a', follow_redirects=True)
        assert '[8, 11, -17, -11, -4, 3, 0, -15, -1, -3, 4, 7]' in page.data
        assert '-2.2282699087' in page.data
        assert '[0, 12, -6, -6, -6, -3, 0, -6, 6, 0, -3, 3, 12, -6, 15, 9, 0, 9, 9, -3, -3, -12, 3, -12, -18, 3, -30' in page.data
        assert '-12.531852282' in page.data
        assert '0.406839418685' in page.data


    def test_random(self):
        r"""
        Test that we don't hit any error on a random newform
        """
        for i in range(100):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random', follow_redirects = True)
            assert 'Newspace' in page.data
            assert 'parameters' in page.data
            assert 'Properties' in page.data
            assert 'Newform' in page.data
            assert 'expansion' in page.data
            assert 'L-function' in page.data
            assert 'Satake parameters' in page.data or 'Embeddings' in page.data


