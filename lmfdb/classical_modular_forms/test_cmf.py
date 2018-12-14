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
        assert "/ModularForm/GL2/Q/holomorphic/stats" in data

    def test_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/stats")
        assert "Cuspidal Newforms: Statistics" in page.data
        assert "Distribution" in page.data
        assert "proportion" in page.data
        assert "count" in page.data
        assert "CM disc" in page.data
        assert "RM disc" in page.data
        assert "has inner twist" in page.data
        assert "projective image" in page.data
        assert "character order" in page.data

    def test_sidebar(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Labels/").data
        assert 'Labels for classical modular forms' in data

    def test_badp(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level_primes=7&count=50&search_type=List").data
        assert '343.1.d.a' in data
        assert '49.4.a.a' in data
        assert '7.7.d.a' in data
        assert '−686' in data


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

    def test_favorite(self):
        from lmfdb.classical_modular_forms.main import favorite_newform_labels, favorite_space_labels
        for elt in favorite_newform_labels:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
            assert ("Newform %s" % elt) in page.data
            # redirect to the same page
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
            assert ("Newform %s" % elt) in page.data
        for elt in favorite_space_labels:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
            assert elt in page.data
            # redirect to the same page
            assert "Space of Cuspidal Newforms of " in page.data
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
            assert elt in page.data
            assert "Space of Cuspidal Newforms of " in page.data


    def test_failure(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/983/2000/c/a/', follow_redirects=True)
        assert "Level and weight too large" in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/100/2/z/a/', follow_redirects=True)
        assert "Newform 100.2.z.a not found" in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1000&weight=100-&search_type=List', follow_redirects=True)
        assert "No matches" in page.data
        assert "Only for weight 1" in page.data
        

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
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/38/9/')
        for elt in map(str,[378, 120, 258, 342, 120, 222, 36]):
            assert elt in page.data
        for elt in ['38.9.b','38.9.d','38.9.f']:
            assert elt in page.data
            assert elt + '.a' in page.data
        for elt in ['Decomposition', r"S_{9}^{\mathrm{old}}(\Gamma_1(38))", "lower level spaces"]:
            assert elt in page.data

    def test_convert_conreylabels(self):
        for c in [27, 31]:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/38/9/%d/a/' % c,follow_redirects=True)
            assert "Newform 38.9.d.a" in page.data
            for e in range(1, 13):
                page = self.tc.get('/ModularForm/GL2/Q/holomorphic/38/9/d/a/%d/%d/' % (c, e),follow_redirects=True)
                assert "Newform 38.9.d.a" in page.data

    def test_dim_table(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=1-100&search_type=Dimensions", follow_redirects=True)
        assert 'Dimension Search Results' in page.data
        assert '227' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=1-20&search_type=Dimensions', follow_redirects=True)
        assert '456' in page.data
        assert 'Dimension Search Results' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=3900-4100&weight=1-12&char_order=2-&search_type=Dimensions", follow_redirects=True)
        assert '426' in page.data
        assert '128' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=3900-4100&weight=1-12&char_order=1&search_type=Dimensions", follow_redirects=True)
        assert '128' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=4002&weight=1&char_order=2-&search_type=Dimensions", follow_redirects=True)
        assert 'n/a' in page.data

        #the other dim table
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/2/")
        assert '7' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/2/")
        for elt in map(str,[9,4,5]):
            assert elt in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/59/8/")
        for elt in map(str,[1044, 1042, 2, 986, 0, 58, 56]):
            assert elt in page.data
        for etl in ['59.8.a', '59.8.a.a', '59.8.a.b', '59.8.c', '59.8.c.a']:
            assert elt in page.data

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

        # specifying embeddings
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/99/2/p/a/?n=2-10&m=2.1%2C+95.10&prec=6&format=embed')
        for elt in ['2.1','95.10','1.05074','0.946093', '2.90567', '0.305398']:
            assert elt in page.data

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/13/2/e/a/?m=1-2&n=2-10000&prec=6&format=embed')
        assert "Only" in page.data
        assert "up to 1000 are available" in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/13/2/e/a/?m=1-2&n=3.5&prec=6&format=embed')
        assert "must be an integer, range of integers or comma separated list of integers" in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/419/3/h/a/?n=2-10&m=1-20000&prec=6&format=embed')
        assert "Web interface only supports 1000 embeddings at a time. Use download link to get more (may take some time)." in page.data





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
        for i in range(100):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random', follow_redirects = True)
            check(page)

        for w in ('1', '2', '3', '4', '5', '6-10', '11-20', '21-40', '41-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight=%s&search_type=Random' % w, follow_redirects = True)
            check(page)
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random?weight=%s' % w, follow_redirects = True)
            check(page)

        for l in ('1', '2-100', '101-500', '501-1000', '1001-2000', '2001-'):
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=%s&search_type=Random' % l, follow_redirects = True)
            check(page)
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/random?level=%s' % l, follow_redirects = True)
            check(page)


    def test_dimension(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=10&weight=1-14&dim=1&search_type=List', follow_redirects = True)
        assert "displaying all 14 matches" in page.data
        assert 'A-L signs' in page.data
    def test_traces(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=244&weight=4&count=50&search_type=Traces', follow_redirects = True)
        assert "Results (displaying all 18 matches)" in page.data
        for elt in map(str,[-98,-347,739,0,147,-414,324,306,-144,0,24,-204,153,414,-344,-756,-24,164]):
            assert elt in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=244&weight=4&search_type=Traces&n=1-40&n_primality=prime_powers&an_constraints=a3%3D0%2Ca37%3D0', follow_redirects = True)
        assert "Results (displaying all 3 matches)" in page.data
        for elt in map(str,[-6,-68, 3224, 206, 4240, -408, -598, 1048]):
            assert elt in page.data


    def test_trivial_searches(self):
        from sage.all import Subsets
        for begin in [
                ('level=10&weight=1-20&dim=1',
                    ['Results (displaying all 21 matches)', '171901114', 'No', '4003.3', 'A-L signs']
                    ),
                ('level=10%2C13%2C17&weight=1-8&dim=1',
                    ['Results (displaying all 12 matches)', '1373', 'No', '1093.6']
                    )]:
            for s in Subsets(['has_self_twist=no', 'is_self_dual=yes', 'nf_label=1.1.1.1','char_order=1','has_inner_twist=no']):
                s = '&'.join(['/ModularForm/GL2/Q/holomorphic/?search_type=List', begin[0]] + list(s))
                page = self.tc.get(s,  follow_redirects=True)
                for elt in begin[1]:
                    assert elt in page.data, s

        for begin in [
                ('level=1-330&weight=1&projective_image=D2',
                    ['Results (displaying all 49 matches)',
                        '328.1.c.a', '413.6', r"\sqrt{-82}", r"\sqrt{-323}", r"\sqrt{109}"]
                    ),
                ('level=900-1000&weight=1-&projective_image=D2',
                    ['Results (displaying all 26 matches)', r"\sqrt{-1}", r"\sqrt{-995}", r"\sqrt{137}"]
                    )]:
            for s in Subsets(['has_self_twist=yes', 'has_self_twist=cm', 'has_self_twist=rm',  'projective_image_type=Dn','dim=1-4']):
                s = '&'.join(['/ModularForm/GL2/Q/holomorphic/?search_type=List', begin[0]] + list(s))
                page = self.tc.get(s,  follow_redirects=True)
                for elt in begin[1]:
                    assert elt in page.data, s


    def test_special_fields(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-500&weight=2&nf_label=16.0.1048576000000000000.1&prime_quantifier=subsets&search_type=List')
        assert '\zeta_{40}' in page.data
        assert "Results (displaying all 6 matches)" in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-4000&weight=1&nf_label=9.9.16983563041.1&prime_quantifier=subsets&projective_image=D19&search_type=List')
        assert r"Q(\zeta_{19})^+" in page.data
        assert "Results (displaying all 32 matches)"
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=2&dim=4&nf_label=4.0.576.2&prime_quantifier=subsets&search_type=List')
        assert 'Results (displaying all 7 matches)' in page.data
        assert '\Q(\sqrt{2}, \sqrt{-3})' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?dim=8&char_order=20&has_self_twist=no&search_type=List')
        assert "Results (displaying all 17 matches)" in page.data
        assert r"Q(\zeta_{20})" in page.data


    def test_AL_search(self):
        r"""
        Test that we display AL eigenvals/signs
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15&char_order=1&search_type=List', follow_redirects=True)
        assert 'A-L signs' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15&search_type=Spaces', follow_redirects=True)
        assert 'AL-dims.' in page.data
        assert '\(0\)+\(1\)+\(0\)+\(0\)' in page.data





    def test_Fricke_signs_search(self):
        r"""
        Test that we display Fricke sings
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=15%2C20&weight=2&dim=1&search_type=List',  follow_redirects=True)
        assert 'Fricke sign' in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?char_order=1&search_type=List',  follow_redirects=True)
        assert 'Fricke sign' in page.data


    def displaying_weight1_search(self):
        for typ in ['List', 'Traces', 'Dimensions']:
            for search in ['weight=1', 'rm_discs=5','has_self_twist=rm','cm_discs=-3%2C+-39']:
                page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?%s&search_type=%s' % (search, typ),  follow_redirects=True)
                assert 'Only for weight 1:' in page.data


    def test_is_self_dual(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?is_self_dual=yes&search_type=List' ,  follow_redirects=True)
        for elt in ['23.1.b.a', '31.1.b.a', '11.2.a.a']:
            assert elt in page.data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?is_self_dual=no&search_type=List',  follow_redirects=True)
        for elt in ['13.2.e.a', '52.1.j.a', '57.1.h.a']:
            assert elt in page.data
