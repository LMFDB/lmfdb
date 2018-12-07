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
        assert '?search_type=Dimensions&char_order=1' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=Dimensions",follow_redirects=True).data
        assert r'<a href="/ModularForm/GL2/Q/holomorphic/19/5/">69</a>' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=Dimensions&char_order=1", follow_redirects=True).data
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
        assert '0.954138' in page.data
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/')
        assert '0.792122' in page.data

    def test_level11(self):
        r"""
        Check that the weight 2 form of level 11 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/a/a/")
        assert '2q^{2}' in page.data
        assert '2q^{4}' in page.data
        assert r'0.707106' in page.data
        assert r'0.707106' in page.data
        assert r'0.957427' in page.data
        assert r'0.223606' in page.data
        assert r'0.974679' in page.data
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
        assert '0.866025' in page.data
        assert r'6q^{6}' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/4/b/a/")
        assert r'46q^{9}' in page.data
        assert r'\Q(\sqrt{-1})' in page.data
        assert r'10' in page.data

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
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=1-100&search_type=Dimensions", follow_redirects=True)
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
        assert r'0.707106' in page.data
        assert r'0.957427' in page.data
        assert r'0.223606' in page.data
        assert r'0.974679' in page.data
        assert r'0.288675' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7/3/b/a/')
        assert r'0.750000' in page.data
        assert r'0.661437' in page.data
        assert r'0.272727' in page.data
        assert r'0.962091' in page.data
        assert r'1' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7/3/b/a/?&format=satake_angle')
        assert '\(\pi\)' in page.data
        assert '\(0.769946\pi\)' in page.data
        assert '\(0.587925\pi\)' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/21/2/e/a/?format=satake')
        assert r'0.965925' in page.data
        assert r'0.258819' in page.data
        assert r'0.990337' in page.data
        assert r'0.550989' in page.data


        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/5/9/c/a/?n=2-10&m=1-6&prec=6&format=satake')
        assert '0.972877' in page.data
        assert '0.231319' in page.data


        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/31/2/c/a/?m=1-4&n=2-10&prec=6&format=satake')
        assert '0.998758' in page.data
        assert '0.0498090' in page.data
        assert '0.542515' in page.data
        assert '0.840045' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/31/2/c/a/?m=1-4&n=2-10&prec=6&format=satake_angle')
        assert '0.984138\pi' in page.data
        assert '0.317472\pi' in page.data


        #test large floats
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=embed')
        assert '213.765' in page.data
        assert '5.39613e49' in page.data
        assert '7.61561e49' in page.data
        assert '3412.76' in page.data
        assert '1.55372e49' in page.data
        assert '1.00032e49' in page.data
        assert '3626.53' in page.data
        assert '1.17539e49' in page.data
        assert '1.20000e50' in page.data

        # same numbers but normalized
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=analytic_embed')
        assert '0.993913' in page.data
        assert '1.36786' in page.data
        assert '0.286180' in page.data
        assert '0.179671' in page.data
        assert '0.216496' in page.data
        assert '2.15536' in page.data

        # test some exact values
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/25/2/e/a/?n=97&m=8&prec=6&format=satake_angle')
        assert '0.0890699' in page.data
        assert '0.689069' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/25/2/d/a/?m=4&n=97&prec=6&format=satake_angle')
        assert '0.237314' in page.data
        assert '0.637314' in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/210/2/a/a/')
        # alpha_11
        assert '0.603022' in page.data
        assert '0.797724' in page.data
        # alpha_13
        assert '0.277350' in page.data
        assert '0.960768' in page.data
        # alpha_17
        assert '0.727606' in page.data
        assert '0.685994' in page.data



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
        assert '[-1, 0, 0, 1, -1, 0, -1, 1, 1, 1, 0, 0]' in page.data
        assert '-2.2282699087' in page.data
        assert '[0, 12, -6, -6, -6, -3, 0, -6, 6, 0, -3, 3, 12, -6, 15, 9, 0, 9, 9, -3, -3, -12, 3, -12, -18, 3, -30' in page.data
        assert '-12.531852282' in page.data
        assert '0.406839418685' in page.data


    def test_random(self):
        r"""
        Test that we don't hit any error on a random newform
        """
        def check(page):
            assert 'Newspace' in page.data, page.url
            assert 'parameters' in page.data, page.url
            assert 'Properties' in page.data, page.url
            assert 'Newform' in page.data, page.url
            assert 'expansion' in page.data, page.url
            assert 'L-function' in page.data, page.url
            assert 'Satake parameters' in page.data or 'Embeddings' in page.data, page.url
        for i in range(100):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random', follow_redirects = True)
            check(page)

        for w in ('1', '2', '3', '4', '5', '6-10', '11-20', '21-40', '41-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight=%s&search_type=Random' % w, follow_redirects = True)
            check(page)

        for l in ('1', '2-100', '101-500', '501-1000', '1001-2000', '2001-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=%s&search_type=Random' % l, follow_redirects = True)
            check(page)


