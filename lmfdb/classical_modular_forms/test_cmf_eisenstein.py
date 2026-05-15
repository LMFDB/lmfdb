from lmfdb.tests import LmfdbTest
import unittest

class CmfTest(LmfdbTest):
    def runTest(self):
        pass

    def test_expression_divides(self):
        # checks search of conductors dividing 1000
        self.check_args('/ModularForm/GL2/Q/holomorphic/?level_type=divides&level=1000', '40.2.E.f.a')

    def test_browse_page(self):
        r"""
        Check that browsing has the added option Is cuspidal
        """
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/").get_data(as_text=True)
        assert 'Is cuspidal' in data

    def test_dynamic_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/dynamic_stats?char_order=2&col1=level&buckets1=1-1000%2C1001-10000&proportions=recurse&col2=weight&buckets2=1-8%2C9-316&search_type=DynStats")
        data = page.get_data(as_text=True)
        # The proportions are against the unconstrained number, which now includes the Eisenstein series.
        # Therefore, we update the percentages accordingly. 
        # Eventually should allow generation of statistics with respect to imposed constraints
        # for x in ["16576", "24174", "6172", "20.90%", "30.46%", "13.26%"]:
        for x in ["19943", "24174", "6448", "30.67%", "16.84%", "13.26%"]:
            assert x in data

    def test_sidebar(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Labels").get_data(as_text=True)
        assert 'Labels for classical modular forms' in data
        # Making sure that this is the version containing Eisenstein labels
        assert 'Eisenstein' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Completeness").get_data(as_text=True)
        assert "Completeness of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Reliability").get_data(as_text=True)
        assert "Reliability of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Source").get_data(as_text=True)
        assert "Source of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data
    
    def test_badp(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level_primes=7&count=100").get_data(as_text=True)
        assert '7.2.E.a.a' in data
        assert '21.2.E.g.d' in data
    
    def test_level_bread(self):
        # At the moment testing data with Nk^2 <= 1000
        # update when loading more data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/248/?is_cuspidal=no',
                           follow_redirects=True)
        assert '248.2.E.bc.d' in page.get_data(as_text=True)
        assert r'\Q(\zeta_{15})' in page.get_data(as_text=True)
        assert '248.2.E.v.d' in page.get_data(as_text=True)
        assert r'\Q(\zeta_{10})' in page.get_data(as_text=True)
        assert '248.2.E.q.d' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{-3})' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/248/?weight=10&level=9', follow_redirects=True)
        assert 'Results (7 matches)' in page.get_data(as_text=True)
        assert '9.10.E.c.b' in page.get_data(as_text=True)
        assert '1023' in page.get_data(as_text=True)

    @unittest.skip("Long tests for many newform spaces, should be run & pass before any release")
    def test_many(self):
        from sage.all import ZZ
        for Nk2 in range(1, 2001):
            for N in ZZ(Nk2).divisors():
                k = (Nk2 // N).sqrt()
                if k in ZZ and k > 1:
                    print("testing (N, k) = (%s, %s)" % (N, k))
                    url = "/ModularForm/GL2/Q/holomorphic/{0}/{1}/E/".format(N, k)
                    rv = self.tc.get(url,follow_redirects=True)
                    self.assertTrue(rv.status_code == 200,"Request failed for {0}".format(url))
                    assert str(N) in rv.get_data(as_text=True)
                    assert str(k) in rv.get_data(as_text=True)
                    assert str(N)+'.'+str(k) in rv.get_data(as_text=True)

    # 2DO - Still working on this one, add more favorites
    def test_favorite(self):
        favorite_newform_eis_labels = [
            [('1.4.E.a.a','First Level 1 form'),
             ('1.6.E.a.a','First weight 6 form'),
             ('2.2.E.a.a','First weight 2 form'),
            ],
            [
            ]
        ]
        favorite_space_eis_labels = [
            [
            ]
        ]
        for l in favorite_newform_eis_labels:
            for elt, desc in l:
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
                assert ("Newform orbit %s" % elt) in page.get_data(as_text=True)
                # redirect to the same page
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
                assert ("Newform orbit %s" % elt) in page.get_data(as_text=True)
        for l in favorite_space_eis_labels:
            for elt, desc in l:
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % elt, follow_redirects=True)
                assert elt in page.get_data(as_text=True)
                # redirect to the same page
                assert "Space of modular forms of " in page.get_data(as_text=True)
                page = self.tc.get("/ModularForm/GL2/Q/holomorphic/%s" % elt, follow_redirects=True)
                assert elt in page.get_data(as_text=True)
                assert "Space of modular forms of " in page.get_data(as_text=True)

    @unittest.skip("Needs to check the hash on traces here - so far have not produced trace hashes for Eisenstein series")
    def test_tracehash(self):
        for t, l in [[-121597739728372579,'867.2.E.i.bb'],[-67108865, '1.4.E.a.a'],[0,'not found']]:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%%23%d" % t, follow_redirects=True)
            assert l in page.get_data(as_text=True)

    def test_jump(self):
        for j, l in [['13.2.E','13.2.E.c.a'], # testing Eisenstein labels vs dirichlet character labels - 'e' vs 'E'
                     ['13.2.e', '13.2.e.a'], 
                     ['2.2.E.1.a', '3.6.a.a'], # 3.6.a.a appears as the example for the jump box
                     ['55.3.E.d', '55.3.E.d'], 
                     # ['55.3.E.54', '55.3.E.d'], # This was done for cmf only for backward compatibility - so we do not support it for eisenstein
                     ['20.5.E', '20.5.E'], 
                     ['yes&is_cuspidal=no','2.2.E.a.a'], 
                     ['yes&weight=3&is_cuspidal=no','3.3.E.b.a'], 
                     ['yes&weight=-2&is_cuspidal=no', 'There are no newforms specified by the query']]:
            page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?jump=%s" % j, follow_redirects=True)
            assert l in page.get_data(as_text=True)

    def test_failure(self):
        r"""
        Check that bad inputs are handled correctly
        """
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/983/2000/E/c/a/', follow_redirects=True) 
        assert "Level and weight too large" in page.get_data(as_text=True)
        assert "for non trivial character." in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/1000/4000/E/a/a/', follow_redirects=True)
        assert "Level and weight too large" in page.get_data(as_text=True)
        assert " for trivial character." in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/100/2/E/a/a/', follow_redirects=True)
        assert "The newform 100.2.E.a.a is not in the database" in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1000&weight=3-&is_cuspidal=no', follow_redirects=True)
        assert "No matches" in page.get_data(as_text=True)

    def test_E4(self):
        r"""
        Check that E4 is ok....
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/4/E/")
        assert '1.4.E.a.a' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/4/E/a/")
        assert '1.4.E.a.a' in page.get_data(as_text=True)
        assert '240' in page.get_data(as_text=True)
        assert '344' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/4/E/a/a/")
        assert '1/240' in page.get_data(as_text=True)
        assert '9 q^{2}' in page.get_data(as_text=True)
        # !!! We still don't have embedding data for Eisenstein series
        # page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/4/E/a/a/?format=satake")
        # assert '0.299367' in page.get_data(as_text=True)
        # assert '0.954138' in page.get_data(as_text=True)
        # !!! We do not have L-functions for Eisenstein series yet
        # page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/a/a/', follow_redirects=True)
        # assert '0.792122' in page.get_data(as_text=True)

    def test_level2(self):
        r"""
        Check that the weight 2 form of level 2 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/2/E/a/a/")
        assert '24' in page.get_data(as_text=True)
        assert '4 q^{3}' in page.get_data(as_text=True)
        # We still don't have embedding data for Eisenstein series
        # page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/2/E/a/a/?format=satake")
        # assert r'0.707107' in page.get_data(as_text=True)
        # assert r'0.957427' in page.get_data(as_text=True)
        # assert r'0.223607' in page.get_data(as_text=True)
        # assert r'0.974679' in page.get_data(as_text=True)
        ## !!! We do not have L-functions for Eisenstein series yet
        # page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/2/2/E/a/a/', follow_redirects=True)
        # assert '0.253841' in page.get_data(as_text=True)

    def test_triv_character(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/9/4/E/a/a/")
        assert r'344 q^{7}' in page.get_data(as_text=True)
        assert r'288 q^{3}' not in page.get_data(as_text=True) # Verifying this is not the level 1 E4 form
        assert '1134' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/25/8/E/a/a/")
        assert '2113665 q^{8}' in page.get_data(as_text=True)
        assert '36130444' in page.get_data(as_text=True)

    def test_non_triv_character(self):
        r"""
        Check that non-trivial characters are also working.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/2/E/e/a/")
        assert r'\Q(\sqrt{-3})' in page.get_data(as_text=True)
        # !!! We do not have the embedding data for Eisenstein series yet
        # assert '0.866025' in page.get_data(as_text=True)
        assert r'7 q^{6}' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/25/4/E/b/a/")
        assert r'1514 q^{9}' in page.get_data(as_text=True)
        assert r'\Q(\sqrt{-1})' in page.get_data(as_text=True)
        assert r'25' in page.get_data(as_text=True)

    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/E/b/")
        assert '40353606' in page.get_data(as_text=True)
        assert '-40353606' in page.get_data(as_text=True)

    def test_empty(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/8/E/a/")
        assert 'The following table gives the dimensions of various' in page.get_data(as_text=True)
        assert 'subspaces' in page.get_data(as_text=True)
        assert r'\(M_{8}(\Gamma_0(2))\)' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/3/E/a/")
        assert 'weight is odd while the character is ' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/6/E/a/")
        page_text = page.get_data(as_text=True)
        for elt in ['Decomposition', r'E_{6}^{\mathrm{old}}(\Gamma_0(12))', 'lower level spaces']:
            assert elt in page_text
        # Sublevel 1 contributes the weight-6 Eisenstein series E_6 as a newform.
        assert r'E_{6}^{\mathrm{new}}(\Gamma_0(1))' in page_text

    def test_not_in_db(self):
        # The following redirects to "ModularForm/GL2/Q/holomorphic/12000/12/E/"
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/E/")
        assert 'Space not in database' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12000/12/E/a/")
        assert 'Space 12000.12.E.a not found' in page.get_data(as_text=True)

    def test_character_validation(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/E/e/")
        assert 'Space 12.10.E.e not found' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/10/E/c/")
        assert 'since the weight is even while the character is' in page.get_data(as_text=True)

    def test_decomposition(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/6/12/E/", follow_redirects=True)
        assert r'Decomposition</a> of \(E_{12}^{\mathrm{old}}(\Gamma_1(6))\)' in page.get_data(as_text=True)
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/38/9/E/')
        for elt in map(str,[378, 120, 258, 342, 120, 222, 36]):
            assert elt in page.get_data(as_text=True)
        for elt in ['Decomposition', r"E_{9}^{\mathrm{old}}(\Gamma_1(38))", "lower level spaces"]:
            assert elt in page.get_data(as_text=True)
        decomposition = r"""
<div class="center">
  \( E_{9}^{\mathrm{old}}(\Gamma_1(38)) \cong \) <a href=/ModularForm/GL2/Q/holomorphic/1/9/E/>\(E_{9}^{\mathrm{new}}(\Gamma_1(1))\)</a>\(^{\oplus 4}\)\(\oplus\)<a href=/ModularForm/GL2/Q/holomorphic/2/9/E/>\(E_{9}^{\mathrm{new}}(\Gamma_1(2))\)</a>\(^{\oplus 2}\)\(\oplus\)<a href=/ModularForm/GL2/Q/holomorphic/19/9/E/>\(E_{9}^{\mathrm{new}}(\Gamma_1(19))\)</a>\(^{\oplus 2}\)
</div>
"""
        assert decomposition in page.get_data(as_text=True)
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/19/6/E', follow_redirects=True)
        assert r'Decomposition</a> of \(E_{6}^{\mathrm{new}}(\Gamma_1(19))\)' in page.get_data(as_text=True)
        for elt in map(str,[84,82,2,66,0,18,16,2]):
            assert elt in page.get_data(as_text=True)
        for elt in ['19.6.E.a', '19.6.E.c', '19.6.E.e']:
            assert elt in page.get_data(as_text=True)
            if elt != '19.6.E.a':
                assert elt + '.a' in page.get_data(as_text=True)
                assert elt + '.b' in page.get_data(as_text=True)

    # is_maximal test awaits updating the column is_maximal in the table mf_newforms_eis

    def test_dim_table(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=23&search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '20' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?weight=12&level=1-100&search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '20' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '1-12' in page.get_data(as_text=True)
        assert '1-24' in page.get_data(as_text=True)
        assert '20' in page.get_data(as_text=True) # Level 23, Weight 12

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=1-100&weight=1-20&search_type=Dimensions&is_cuspidal=no', follow_redirects=True)
        assert '22' in page.get_data(as_text=True) # Level 23, Weight 13
        assert '20' in page.get_data(as_text=True) # Level 23, Weight 12
        assert 'Dimension search results' in page.get_data(as_text=True)

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=900-1100&weight=1-12&char_order=2-&search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert '1120' in page.get_data(as_text=True) # Level 999, Weight 1
        assert '512' in page.get_data(as_text=True) # Level 1000, Weight 1

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=900-1100&weight=1-12&char_order=1&search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert '0' in page.get_data(as_text=True)

        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level=1002&weight=1&char_order=2-&search_type=Dimensions&is_cuspidal=no", follow_redirects=True)
        assert 'Dimension search results' in page.get_data(as_text=True)
        assert 'n/a' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?level=7,10&weight_parity=odd&char_parity=odd&count=50&search_type=Dimensions&is_cuspidal=no')
        for elt in map(str,[0,1,3,5,7,9,11,6]):
            assert elt in page.get_data(as_text=True)
        assert 'Dimension search results' in page.get_data(as_text=True)

        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/?weight_parity=odd&level=1-1000&weight=1-100&search_type=Dimensions&is_cuspidal=no')
        assert 'Error: Table too large: must have at most 10000 entries' in page.get_data(as_text=True)

        #the other dim table
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/2/E/")
        assert '7' in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/12/2/E/")
        for elt in map(str,[9,4,5]):
            assert elt in page.get_data(as_text=True)
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/59/8/E/")
        for elt in map(str,[1044, 1042, 2, 986, 0, 58, 56]):
            assert elt in page.get_data(as_text=True)
        for elt in ['59.8.E.a', '59.8.E.c', '59.8.E.c.a', '59.8.E.c.b']:
            assert elt in page.get_data(as_text=True)
