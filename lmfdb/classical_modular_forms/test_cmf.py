
from lmfdb.tests import LmfdbTest
import unittest

from . import cmf_logger
cmf_logger.setLevel(100)


class CmfTest(LmfdbTest):
    def runTest(self):
        pass

    def test_expression_divides(self):
        # checks search of conductors dividing 1000
        self.check_args('/ModularForm/GL2/Q/holomorphic/?level_type=divides&level=1000', '40.2.k.a')

    def test_browse_page(self):
        r"""
        Check browsing for elliptic modular forms
        """
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/").get_data(as_text=True)
        assert '?search_type=Dimensions&dim=1' in data
        assert '?search_type=SpaceDimensions&char_order=1' in data
        assert "/stats" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=SpaceDimensions",follow_redirects=True).get_data(as_text=True)
        assert r'<a href="/ModularForm/GL2/Q/holomorphic/23/12/">229</a>' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=SpaceDimensions&char_order=1", follow_redirects=True).get_data(as_text=True)
        assert r'<a href="/ModularForm/GL2/Q/holomorphic/18/4/a/">1</a>' in data

    def test_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/stats")
        assert "Classical modular forms: Statistics" in page.get_data(as_text=True)
        assert "Distribution" in page.get_data(as_text=True)
        assert "proportion" in page.get_data(as_text=True)
        assert "count" in page.get_data(as_text=True)
        assert "CM disc" in page.get_data(as_text=True)
        assert "RM disc" in page.get_data(as_text=True)
        assert "inner twists" in page.get_data(as_text=True)
        assert "projective image" in page.get_data(as_text=True)
        assert "character order" in page.get_data(as_text=True)

    def test_dynamic_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/dynamic_stats?char_order=2&col1=level&buckets1=1-1000%2C1001-10000&proportions=recurse&col2=weight&buckets2=1-8%2C9-316&search_type=DynStats")
        data = page.get_data(as_text=True)
        for x in ["16576", "24174", "6172", "20.90%", "30.46%", "13.26%"]:
            assert x in data

    def test_sidebar(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Labels").get_data(as_text=True)
        assert 'Labels for classical modular forms' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Completeness").get_data(as_text=True)
        assert "Completeness of classical modular form data" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Reliability").get_data(as_text=True)
        assert "Reliability of classical modular form data" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Source").get_data(as_text=True)
        assert "Source of classical modular form data" in data

    def test_badp(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level_primes=7&count=100").get_data(as_text=True)
        assert '273.1.o.a' in data
        assert '56.1.h.a' in data
        assert '14.2.a.a' in data
        assert '168' in data

    def test_level_bread(self):
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1124/',
                           follow_redirects=True)
        assert '1124.1.d.a' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{-281})' in page.get_data(as_text=True)
        assert '1124.1.d.d' in page.get_data(as_text=True)
        assert r'\Q(\zeta_{20})^+' in page.get_data(as_text=True)
        assert '1124.1.ba.a' in page.get_data(as_text=True)
        assert r'\Q(\zeta_{35})' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1124/?weight=10&level=10', follow_redirects=True)
        assert 'Results (4 matches)' in page.get_data(as_text=True)
        assert '10.10.b.a' in page.get_data(as_text=True)
        assert '2580' in page.get_data(as_text=True)

    @unittest.skip("Long tests for many newform spaces, should be run & pass before any release")
    def test_many(self):
        from sage.all import ZZ
        for Nk2 in range(1, 2001):
            for N in ZZ(Nk2).divisors():
                k = (Nk2 // N).sqrt()
                if k in ZZ and k > 1:
                    print("testing (N, k) = (%s, %s)" % (N, k))
                    url = "/ModularForm/GL2/Q/holomorphic/{0}/{1}/".format(N, k)
                    rv = self.tc.get(url,follow_redirects=True)
                    self.assertTrue(rv.status_code == 200,"Request failed for {0}".format(url))
                    assert str(N) in rv.get_data(as_text=True)
                    assert str(k) in rv.get_data(as_text=True)
                    assert str(N)+'.'+str(k) in rv.get_data(as_text=True)

    def test_favorite(self):
        favorite_newform_labels = [
            [('23.1.b.a','Smallest analytic conductor'),
             ('11.2.a.a','First weight 2 form'),
             ('39.1.d.a','First D2 form'),
             ('7.3.b.a','First CM-form with weight at least 2'),
             ('23.2.a.a','First trivial-character non-rational form'),
             ('1.12.a.a','Delta'),
             ('124.1.i.a','First non-dihedral weight 1 form'),
             ('148.1.f.a','First S4 form'),
            ],
            [
                ('633.1.m.b','First A5 form'),
                ('163.3.b.a','Best q-expansion'),
                ('8.14.b.a','Large weight, non-self dual, analytic rank 1'),
                ('8.21.d.b','Large coefficient ring index'),
                ('3600.1.e.a','Many zeros in q-expansion'),
                ('983.2.c.a','Large dimension'),
                ('3997.1.cz.a','Largest projective image'),
                ('7524.2.l.b', 'CM-form by Q(-627) and many inner twists'),
            ]
        ]
        favorite_space_labels = [
            [('1161.1.i', 'Has A5, S4, D3 forms'),
             ('23.10', 'Mile high 11s'),
             ('3311.1.h', 'Most weight 1 forms'),
             ('1200.2.a', 'All forms rational'),
             ('9450.2.a','Most newforms'),
             ('4000.1.bf', 'Two large A5 forms'),
            ]
        ]
        for l in favorite_newform_labels:
            for elt, desc in l:
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
                assert ("Newform orbit %s" % elt) in page.get_data(as_text=True)
                # redirect to the same page
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
                assert ("Newform orbit %s" % elt) in page.get_data(as_text=True)
        for l in favorite_space_labels:
            for elt, desc in l:
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
                assert elt in page.get_data(as_text=True)
                # redirect to the same page
                assert "Space of modular forms of " in page.get_data(as_text=True)
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
                assert elt in page.get_data(as_text=True)
                assert "Space of modular forms of " in page.get_data(as_text=True)

    def test_tracehash(self):
        for t, l in [[1329751273693490116,'7.3.b.a'],[1294334189658968734, '4.5.b.a'],[0,'not found']]:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%%23%d" % t, follow_redirects=True)
            assert l in page.get_data(as_text=True)

    def test_jump(self):
        for j, l in [['10','10.3.c.a'], ['3.6.1.a', '3.6.a.a'], ['55.3.d', '55.3.d'], ['55.3.54', '55.3.d'], ['20.5', '20.5'], ['yes','23.1.b.a'], ['yes&weight=2','11.2.a.a'], ['yes&weight=-2', 'There are no newforms specified by the query']]:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % j, follow_redirects=True)
            assert l in page.get_data(as_text=True)

    def test_failure(self):
        r"""
        Check that bad inputs are handled correctly
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/983/2000/c/a/', follow_redirects=True)
        assert "Level and weight too large" in page.get_data(as_text=True)
        assert "for non trivial character." in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1000/4000/a/a/', follow_redirects=True)
        assert "Level and weight too large" in page.get_data(as_text=True)
        assert " for trivial character." in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/100/2/z/a/', follow_redirects=True)
        assert "The newform 100.2.z.a is not in the database" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1000&weight=100-', follow_redirects=True)
        assert "No matches" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/maria/', follow_redirects=True)
        assert 'maria' in page.get_data(as_text=True) and "is not a valid newform" in page.get_data(as_text=True)

    def test_delta(self):
        r"""
        Check that the Delta function is ok....
        Recall that this version uses the old urls...
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/")
        assert '1.12.a.a' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/a/")
        assert '1.12.a.a' in page.get_data(as_text=True)
        assert '16744' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/a/a/")
        assert '24 q^{2}' in page.get_data(as_text=True)
        assert '84480 q^{8}' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/a/a/?format=satake")
        assert '0.299367' in page.get_data(as_text=True)
        assert '0.954138' in page.get_data(as_text=True)
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/', follow_redirects=True)
        assert '0.792122' in page.get_data(as_text=True)

    def test_level11(self):
        r"""
        Check that the weight 2 form of level 11 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/a/a/")
        assert '2 q^{2}' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/a/a/?format=satake")
        assert r'0.707107' in page.get_data(as_text=True)
        assert r'0.957427' in page.get_data(as_text=True)
        assert r'0.223607' in page.get_data(as_text=True)
        assert r'0.974679' in page.get_data(as_text=True)
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/a/a/', follow_redirects=True)
        assert '0.253841' in page.get_data(as_text=True)

    def test_triv_character(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/8/a/a/")
        assert r'1016 q^{7}' in page.get_data(as_text=True)
        assert '1680' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/3/6/a/a/")
        assert '168 q^{8}' in page.get_data(as_text=True)
        assert '36' in page.get_data(as_text=True)

    def test_non_triv_character(self):
        r"""
        Check that non-trivial characters are also working.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/2/e/a/")
        assert r'\Q(\sqrt{-3})' in page.get_data(as_text=True)
        assert '0.866025' in page.get_data(as_text=True)
        assert r'6 q^{6}' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/4/b/a/")
        assert r'46 q^{9}' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{-1})' in page.get_data(as_text=True)
        assert r'10' in page.get_data(as_text=True)

    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/a/")
        assert '11241' in page.get_data(as_text=True)
        assert '10099' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/1/", follow_redirects=True)
        assert '11241' in page.get_data(as_text=True)
        assert '10099' in page.get_data(as_text=True)

    def test_empty(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/2/a/")
        assert 'The following table gives the dimensions of various' in page.get_data(as_text=True)
        assert 'subspaces' in page.get_data(as_text=True)
        assert r'\(M_{2}(\Gamma_0(2))\)' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/3/a/")
        assert 'weight is odd while the character is ' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/6/a/")
        for elt in ['Decomposition', r'S_{6}^{\mathrm{old}}(\Gamma_0(12))', 'lower level spaces']:
            assert elt in page.get_data(as_text=True)

    def test_not_in_db(self):
        # The following redirects to "ModularForm/GL2/Q/holomorphic/12000/12/"
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/")
        assert 'Space not in database' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/a/")
        assert 'Space 12000.12.a not found' in page.get_data(as_text=True)

    def test_character_validation(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/e/")
        assert 'Space 12.10.e not found' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/c/")
        assert 'since the weight is even while the character is' in page.get_data(as_text=True)

    def test_decomposition(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/6/12/", follow_redirects=True)
        assert r'Decomposition</a> of \(S_{12}^{\mathrm{new}}(\Gamma_1(6))\)' in page.get_data(as_text=True)
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/38/9/')
        for elt in map(str,[378, 120, 258, 342, 120, 222, 36]):
            assert elt in page.get_data(as_text=True)
        for elt in ['38.9.b','38.9.d','38.9.f']:
            assert elt in page.get_data(as_text=True)
            assert elt + '.a' in page.get_data(as_text=True)
        for elt in ['Decomposition', r"S_{9}^{\mathrm{old}}(\Gamma_1(38))", "lower level spaces"]:
            assert elt in page.get_data(as_text=True)
        decomposition = r"""
<div class="center">
  \( S_{9}^{\mathrm{old}}(\Gamma_1(38)) \cong \) <a href=/ModularForm/GL2/Q/holomorphic/1/9/>\(S_{9}^{\mathrm{new}}(\Gamma_1(1))\)</a>\(^{\oplus 4}\)\(\oplus\)<a href=/ModularForm/GL2/Q/holomorphic/2/9/>\(S_{9}^{\mathrm{new}}(\Gamma_1(2))\)</a>\(^{\oplus 2}\)\(\oplus\)<a href=/ModularForm/GL2/Q/holomorphic/19/9/>\(S_{9}^{\mathrm{new}}(\Gamma_1(19))\)</a>\(^{\oplus 2}\)
</div>
"""
        assert decomposition in page.get_data(as_text=True)

    def test_convert_conreylabels(self):
        for c in [27, 31]:
            page = self.tc.get('/ModularForm/GL2/Q/holomorphic/38/9/%d/a/' % c,follow_redirects=True)
            assert "Newform orbit 38.9.d.a" in page.get_data(as_text=True)
            for e in range(1, 13):
                page = self.tc.get('/ModularForm/GL2/Q/holomorphic/38/9/d/a/%d/%d/' % (c, e),follow_redirects=True)
                assert "Newform orbit 38.9.d.a" in page.get_data(as_text=True)

    def test_maximal(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=1234&weight=2")
        assert '15 matches' in page.get_data(as_text=True)
        assert '1234.2.a.h' in page.get_data(as_text=True)
        assert '1234.2.a.i' in page.get_data(as_text=True)
        assert '1234.2.b.c' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=1234&weight=2&is_maximal_largest=maximal")
        assert 'unique match' in page.get_data(as_text=True)
        assert '1234.2.a.h' not in page.get_data(as_text=True)
        assert '1234.2.a.i' in page.get_data(as_text=True)
        assert '1234.2.b.c' not in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=1234&weight=2&is_maximal_largest=largest")
        assert '5 matches' in page.get_data(as_text=True)
        assert '1234.2.a.h' in page.get_data(as_text=True)
        assert '1234.2.a.i' in page.get_data(as_text=True)
        assert '1234.2.b.c' not in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=1234&weight=2&is_maximal_largest=notlargest")
        assert '10 matches' in page.get_data(as_text=True)
        assert '1234.2.a.h' not in page.get_data(as_text=True)
        assert '1234.2.a.i' not in page.get_data(as_text=True)
        assert '1234.2.b.c' in page.get_data(as_text=True)

    def test_dim_table(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=23&search_type=Dimensions", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '229' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=1-100&search_type=Dimensions", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '229' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=Dimensions", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '1-12' in page.get_data(as_text=True)
        assert '1-24' in page.get_data(as_text=True)
        assert '229' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=1-20&search_type=Dimensions', follow_redirects=True)
        assert '253' in page.get_data(as_text=True) # Level 23, Weight 13
        assert '229' in page.get_data(as_text=True) # Level 23, Weight 12
        assert 'Dimension search results' in page.get_data(as_text=True)

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=3900-4100&weight=1-12&char_order=2-&search_type=Dimensions", follow_redirects=True)
        assert '426' in page.get_data(as_text=True) # Level 3999, Weight 1
        assert '128' in page.get_data(as_text=True) # Level 4000, Weight 1

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=3900-4100&weight=1-12&char_order=1&search_type=Dimensions", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '0' in page.get_data(as_text=True)

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=4002&weight=1&char_order=2-&search_type=Dimensions", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert 'n/a' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=7,10&weight_parity=odd&char_parity=odd&count=50&search_type=Dimensions')
        for elt in map(str,[0,1,2,5,4,9,6,13,8,17,10]):
            assert elt in page.get_data(as_text=True)
        assert 'Dimension search results' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=odd&level=1-1000&weight=1-100&search_type=Dimensions')
        assert 'Error: Table too large: must have at most 10000 entries' in page.get_data(as_text=True)

        #the other dim table
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/2/")
        assert '7' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/2/")
        for elt in map(str,[9,4,5]):
            assert elt in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/59/8/")
        for elt in map(str,[1044, 1042, 2, 986, 0, 58, 56]):
            assert elt in page.get_data(as_text=True)
        for etl in ['59.8.a', '59.8.a.a', '59.8.a.b', '59.8.c', '59.8.c.a']:
            assert elt in page.get_data(as_text=True)

    def test_character_parity(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/c/")
        assert 'since the weight is even while the character is' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/3/a/")
        assert 'since the weight is odd while the character is' in page.get_data(as_text=True)

    def test_dual(self):
        urls_set = [
                [('/ModularForm/GL2/Q/holomorphic/5/9/c/a/', 'Newform orbit 5.9.c.a'),
                ('/ModularForm/GL2/Q/holomorphic/5/9/c/a/2/1/', 'Dual form 5.9.c.a.2.1'),
                ('/ModularForm/GL2/Q/holomorphic/5/9/c/a/3/1/', 'Dual form 5.9.c.a.3.1'),
                ],
                [('/ModularForm/GL2/Q/holomorphic/5/9/c/a/', 'Newform orbit 5.9.c.a'),
                ('/ModularForm/GL2/Q/holomorphic/5/9/c/a/2/3/', 'Dual form 5.9.c.a.2.3'),
                ('/ModularForm/GL2/Q/holomorphic/5/9/c/a/3/3/', 'Dual form 5.9.c.a.3.3'),
                ],
                [
                ('/ModularForm/GL2/Q/holomorphic/13/2/e/a/', 'Newform orbit 13.2.e.a'),
                ('/ModularForm/GL2/Q/holomorphic/13/2/e/a/4/1/', 'Dual form 13.2.e.a.4.1'),
                ('/ModularForm/GL2/Q/holomorphic/13/2/e/a/10/1/', 'Dual form 13.2.e.a.10.1'),
                ]
                ]
        for urls in urls_set:
            for i, (url, _) in enumerate(urls):
                page = self.tc.get(url)
                for j, (other, name) in enumerate(urls):
                    if i != j:
                        assert other in page.get_data(as_text=True)
                        if i > 0:
                            assert name in page.get_data(as_text=True)

                if i > 0:
                    assert 'Embedding label' in page.get_data(as_text=True)
                    assert 'Root' in page.get_data(as_text=True)

    def test_embedded_invariants(self):
        for url in ['/ModularForm/GL2/Q/holomorphic/13/2/e/a/4/1/',
                    '/ModularForm/GL2/Q/holomorphic/13/2/e/a/10/1/']:

            page = self.tc.get(url)
            # root
            assert 'Root' in page.get_data(as_text=True)
            assert '0.500000' in page.get_data(as_text=True)
            assert '0.866025' in page.get_data(as_text=True)
            # p = 13
            for n in ['2.50000', '2.59808', '0.693375', '0.720577']:
                assert n in page.get_data(as_text=True)

            # p = 47
            for n in ['3.46410', '0.505291', '0.967559', '0.252646', '0.918699']:
                assert n in page.get_data(as_text=True)

            assert 'Newspace 13.2.e' in page.get_data(as_text=True)
            assert 'Newform orbit 13.2.e.a' in page.get_data(as_text=True)
            assert 'Dual form 13.2.e.a.' in page.get_data(as_text=True)
            assert 'L-function 13.2.e.a.' in page.get_data(as_text=True)

            assert '0.103805522628' in page.get_data(as_text=True)

            assert '13.2.e.a.4.1' in page.get_data(as_text=True)
            assert '13.2.e.a.10.1' in page.get_data(as_text=True)

    def test_satake(self):
        for url in ['/ModularForm/GL2/Q/holomorphic/11/2/a/a/?format=satake',
                '/ModularForm/GL2/Q/holomorphic/11/2/a/a/1/1/']:
            page = self.tc.get(url)
            assert r'0.707107' in page.get_data(as_text=True)
            assert r'0.957427' in page.get_data(as_text=True)
            assert r'0.223607' in page.get_data(as_text=True)
            assert r'0.974679' in page.get_data(as_text=True)
            assert r'0.288675' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/7/3/b/a/?&format=satake',
                '/ModularForm/GL2/Q/holomorphic/7/3/b/a/6/1/']:
            page = self.tc.get(url)
            assert r'0.750000' in page.get_data(as_text=True)
            assert r'0.661438' in page.get_data(as_text=True)
            assert r'0.272727' in page.get_data(as_text=True)
            assert r'0.962091' in page.get_data(as_text=True)
        assert r'1.00000' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/7/3/b/a/?&format=satake_angle',
                '/ModularForm/GL2/Q/holomorphic/7/3/b/a/6/1/']:
            page = self.tc.get(url)
            assert r'\(\pi\)' in page.get_data(as_text=True)
            assert r'\(0.769947\pi\)' in page.get_data(as_text=True)
            assert r'\(0.587926\pi\)' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/21/2/e/a/?format=satake',
                '/ModularForm/GL2/Q/holomorphic/21/2/e/a/4/1/',
                '/ModularForm/GL2/Q/holomorphic/21/2/e/a/16/1/',
                ]:
            page = self.tc.get(url)
            assert r'0.965926' in page.get_data(as_text=True)
            assert r'0.258819' in page.get_data(as_text=True)
            assert r'0.990338' in page.get_data(as_text=True)
            assert r'0.550990' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/5/9/c/a/?n=2-10&m=1-6&prec=6&format=satake',
                '/ModularForm/GL2/Q/holomorphic/5/9/c/a/2/1/',
                '/ModularForm/GL2/Q/holomorphic/5/9/c/a/3/1/',
                ]:
            page = self.tc.get(url)
            assert '0.972878' in page.get_data(as_text=True)
            assert '0.231320' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/5/9/c/a/?n=2-10&m=1-6&prec=6&format=satake',
                '/ModularForm/GL2/Q/holomorphic/5/9/c/a/2/3/',
                '/ModularForm/GL2/Q/holomorphic/5/9/c/a/3/3/',
                ]:
            page = self.tc.get(url)
            assert '0.00593626' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/31/2/c/a/?m=1-4&n=2-10&prec=6&format=satake',
                '/ModularForm/GL2/Q/holomorphic/31/2/c/a/5/1/',
                '/ModularForm/GL2/Q/holomorphic/31/2/c/a/25/1/',
                ]:
            page = self.tc.get(url)
            assert '0.998759' in page.get_data(as_text=True)
            assert '0.0498090' in page.get_data(as_text=True)
            assert '0.542515' in page.get_data(as_text=True)
            assert '0.840046' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/31/2/c/a/?m=1-4&n=2-10&prec=6&format=satake_angle',
                '/ModularForm/GL2/Q/holomorphic/31/2/c/a/5/1/',
                '/ModularForm/GL2/Q/holomorphic/31/2/c/a/25/1/',
                ]:
            page = self.tc.get(url)
            assert r'0.984139\pi' in page.get_data(as_text=True)
            assert r'0.317472\pi' in page.get_data(as_text=True)

        #test large floats
        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/1/']:
            page = self.tc.get(url)
            assert '213.765' in page.get_data(as_text=True)
            assert '5.39613e49' in page.get_data(as_text=True)
            assert '7.61562e49' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/2/']:
            page = self.tc.get(url)
            assert '3412.77' in page.get_data(as_text=True)
            assert '1.55372e49' in page.get_data(as_text=True)
            assert '1.00032e49' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/3/']:
            page = self.tc.get(url)
            assert '3626.53' in page.get_data(as_text=True)
            assert '1.17540e49' in page.get_data(as_text=True)
            assert '1.20001e50' in page.get_data(as_text=True)

        # same numbers but normalized
        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=analytic_embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/1/']:
            page = self.tc.get(url)
            assert '0.993913' in page.get_data(as_text=True)
            assert '1.36787' in page.get_data(as_text=True)

        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=analytic_embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/2/']:
            page = self.tc.get(url)
            assert '0.286180' in page.get_data(as_text=True)
            assert '0.179671' in page.get_data(as_text=True)
        for url in ['/ModularForm/GL2/Q/holomorphic/1/36/a/a/?m=1-3&n=695-696&prec=6&format=analytic_embed',
                    '/ModularForm/GL2/Q/holomorphic/1/36/a/a/1/3/']:
            page = self.tc.get(url)
            assert '0.216496' in page.get_data(as_text=True)
            assert '2.15537' in page.get_data(as_text=True)

        # test some exact values
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/25/2/e/a/?n=97&m=8&prec=6&format=satake_angle')
        assert '0.0890699' in page.get_data(as_text=True)
        assert '0.689070' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/25/2/d/a/?m=4&n=97&prec=6&format=satake_angle')
        assert '0.237314' in page.get_data(as_text=True)
        assert '0.637314' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/210/2/a/a/?format=satake&n=2-20')
        # alpha_11
        assert '0.603023' in page.get_data(as_text=True)
        assert '0.797724' in page.get_data(as_text=True)
        # alpha_13
        assert '0.277350' in page.get_data(as_text=True)
        assert '0.960769' in page.get_data(as_text=True)
        # alpha_17
        assert '0.727607' in page.get_data(as_text=True)
        assert '0.685994' in page.get_data(as_text=True)

        # specifying embeddings
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/99/2/p/a/?n=2-10&m=2.1%2C+95.10&prec=6&format=embed')
        for elt in ['2.1','95.10','1.05074','0.946093', '2.90568', '0.305399']:
            assert elt in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/13/2/e/a/?m=1-2&n=2-10000&prec=6&format=embed')
        assert "Only" in page.get_data(as_text=True)
        assert "up to 1000 are available" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7524/2/l/b/?n=5000&m=&prec=&format=embed')
        assert "Only" in page.get_data(as_text=True)
        assert "up to 3000 are available" in page.get_data(as_text=True)
        assert "in specified range; resetting to default" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/7524/2/l/b/?n=1500-4000&m=&prec=&format=embed')
        assert "Only" in page.get_data(as_text=True)
        assert "up to 3000 are available" in page.get_data(as_text=True)
        assert "limiting to" in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/13/2/e/a/?m=1-2&n=3.5&prec=6&format=embed')
        assert "must be an integer, range of integers or comma separated list of integers" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/419/3/h/a/?n=2-10&m=1-20000&prec=6&format=embed', follow_redirects=True)
        assert "Web interface only supports 1000 embeddings at a time.  Use download link to get more (may take some time)." in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/419/3/h/a/?n=3.14&format=embed', follow_redirects=True)
        assert "must be an integer, range of integers or comma separated list of integers" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/99/2/p/a/?n=2-10&m=1-20&prec=16&format=embed')
        assert 'must be a positive integer, at most 15 (for higher precision, use the download button)' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/99/2/p/a/?n=999-1001&m=1-20&prec=6&format=embed')
        assert 'Only' in page.get_data(as_text=True)
        assert 'up to 1000 are available' in page.get_data(as_text=True)
        assert 'a_{1000}' in page.get_data(as_text=True)

    def test_underlying_data(self):
        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/data/13.2').get_data(as_text=True)
        assert ('mf_gamma1' in data and 'newspace_dims' in data
                and 'mf_gamma1_portraits' in data and "data:image/png;base64" in data)

        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/data/13.2.e').get_data(as_text=True)
        assert ('mf_newspaces' in data and 'num_forms' in data
                and 'mf_newspace_portraits' in data and "data:image/png;base64" in data)

        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/data/13.2.e.a').get_data(as_text=True)
        assert ('mf_newforms' in data and 'field_disc_factorization' in data and
                'mf_hecke_nf' in data and 'hecke_ring_character_values' in data
                and 'mf_newspaces' in data and 'num_forms' in data
                and 'mf_twists_nf' in data and 'twisting_char_label' in data
                and 'mf_hecke_charpolys' in data and 'charpoly_factorization' in data
                and 'mf_newform_portraits' in data and "data:image/png;base64" in data
                and 'mf_hecke_traces' in data and 'trace_an' in data)

        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/data/13.2.e.a.4.1').get_data(as_text=True)
        assert ('mf_newforms' in data and 'field_disc_factorization' in data and
                'mf_hecke_cc' in data and 'an_normalized' in data
                and 'mf_newspaces' in data and 'num_forms' in data
                and 'mf_twists_cc' in data and 'twisting_conrey_index' in data
                and 'mf_hecke_charpolys' in data and 'charpoly_factorization' in data
                and 'mf_newform_portraits' in data and "data:image/png;base64" in data
                and 'mf_hecke_traces' in data and 'trace_an' in data)

    def test_character_values(self):
        # A newform orbit of dimension 1
        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/12/3/c/a/').get_data(as_text=True)
        character_values_table = r"""
<table class="ntdata">
  <tbody>
        <tr>
      <td class="dark border-right border-bottom">\(n\)</td>
      <td class="light border-bottom">\(5\)</td>
      <td class="dark border-bottom">\(7\)</td>    </tr>
    <tr>
      <td class="dark border-right">\(\chi(n)\)</td>
      <td class="light">\(-1\)</td>
      <td class="dark">\(1\)</td>    </tr>
  </tbody>
</table>
"""
        assert (character_values_table in data)

        # A newform orbit of dimension 2
        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/119/1/d/a/').get_data(as_text=True)
        character_values_table = r"""
<table class="ntdata">
  <tbody>
        <tr>
      <td class="dark border-right border-bottom">\(n\)</td>
      <td class="light border-bottom">\(52\)</td>
      <td class="dark border-bottom">\(71\)</td>    </tr>
    <tr>
      <td class="dark border-right">\(\chi(n)\)</td>
      <td class="light">\(-1\)</td>
      <td class="dark">\(-1\)</td>    </tr>
  </tbody>
</table>
"""
        assert (character_values_table in data)

        # An embedded newform
        data = self.tc.get('/ModularForm/GL2/Q/holomorphic/119/1/d/a/118/1/').get_data(as_text=True)
        character_values_table = r"""
<table class="ntdata">
  <tbody>
        <tr>
      <td class="dark border-right border-bottom">\(n\)</td>
      <td class="light border-bottom">\(52\)</td>
      <td class="dark border-bottom">\(71\)</td>    </tr>
    <tr>
      <td class="dark border-right">\(\chi(n)\)</td>
      <td class="light">\(-1\)</td>
      <td class="dark">\(-1\)</td>    </tr>
  </tbody>
</table>
"""
        assert (character_values_table in data)
