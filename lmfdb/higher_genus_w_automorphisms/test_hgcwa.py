from lmfdb.tests import LmfdbTest


class HigherGenusWithAutomorphismsTest(LmfdbTest):

    # All tests should pass
    #
    def test_url_label(self):
        L = self.tc.get('/HigherGenus/C/Aut/2.24-8.0.2-4-6')
        assert '[ 0; 2, 4, 6 ]' in L.get_data(as_text=True)

    def test_passport_label(self):
        L = self.tc.get('/HigherGenus/C/Aut/3.14-2.0.2-7-14.1')
        assert '(1,8) (2,9) (3,10) (4,11) (5,12) (6,13) (7,14)' in L.get_data(as_text=True)

    def test_url_naturallabel(self):
        L = self.tc.get('/HigherGenus/C/Aut/junk', follow_redirects=True)
        assert 'No family with label' in L.get_data(as_text=True)

    def test_url_topological_pages(self):
        """Test bad URLs for topological webpages"""

        L = self.tc.get('/HigherGenus/C/Aut/boaty/mcboatface', follow_redirects=True)
        assert 'Invalid family label' in L.get_data(as_text=True)

        L = self.tc.get('/HigherGenus/C/Aut/2.8-1.0.2-8-8/mcboatface', follow_redirects=True)
        assert 'Invalid topological action label' in L.get_data(as_text=True)

        # This URL referenced in LMFDB#4449
        L = self.tc.get('/HigherGenus/C/Aut/2.8-1.0.2-8-8/T.2.1',follow_redirects=True)
        assert 'No orbit in family with label' in L.get_data(as_text=True)

    def test_search_genus_group(self):
        L = self.tc.get('/HigherGenus/C/Aut/?genus=2&group=%5B48%2C29%5D&signature=&dim=&hyperelliptic=include&count=20&Submit=Search')
        assert 'both matches' in L.get_data(as_text=True)

    def test_magma_download(self):
        L = self.tc.get('/HigherGenus/C/Aut/5.32-27.0.2-2-2-4.1/download/magma')
        assert '// Here we add an action to data.' in L.get_data(as_text=True)

    def test_full_auto_links(self):
        L = self.tc.get('/HigherGenus/C/Aut/4.9-1.0.9-9-9.1')
        assert 'Full automorphism 4.18-2.0.2-9-18' in L.get_data(as_text=True)

    def test_index_page(self):
        L = self.tc.get('/HigherGenus/C/Aut/')
        assert 'Cyclic trigonal' in L.get_data(as_text=True)

    def test_stats_page(self):
        L = self.tc.get('/HigherGenus/C/Aut/stats')
        assert 'distinct families' in L.get_data(as_text=True)

    def test_unique_groups_pages(self):
        L = self.tc.get('/HigherGenus/C/Aut/stats/groups_per_genus/5')
        assert 'Distribution of groups in curves of genus 5' in L.get_data(as_text=True)

    def test_quo_genus_gt_0(self):
        L = self.tc.get('/HigherGenus/C/Aut/3.2-1.2.0.1')
        assert '[2;-]' in L.get_data(as_text=True)

    def test_quo_genus_search(self):
        L = self.tc.get('/HigherGenus/C/Aut/?genus=3&g0=1..3')
        assert '10 matches' in L.get_data(as_text=True)

    def idG_showing(self):
        L = self.tc.get('/HigherGenus/C/Aut/2.2-1.1.2-2.1')
        assert 'Id(G)' in L.get_data(as_text=True)

    def top_inequiv(self):
        L = self.tc.get('/HigherGenus/C/Aut/3.8-2.0.2-2-4-4')
        assert 'topologically inequivalent' in L.get_data(as_text=True)

    def braid_inequiv(self):
        L = self.tc.get('HigherGenus/C/Aut/3.8-3.0.2-2-4-4.1')
        assert 'braid inequivalent' in L.get_data(as_text=True)

    def braid_summary_pages(self):
        L = self.tc.get('/HigherGenus/C/Aut/3.8-3.0.2-2-4-4/T.1.1')
        assert 'braid inequivalent' in L.get_data(as_text=True)

    def underlying_data(self):
        page = self.tc.get('/HigherGenus/C/Aut/3.8-3.0.2-2-4-4.1').get_data(as_text=True)
        assert 'Underlying data' in page and 'api/hgcwa_passports/?passport_label=3.8-3.0.2-2-4-4.1' in page
        page = self.tc.get('/HigherGenus/C/Aut/3.8-3.0.2-2-4-4').get_data(as_text=True)
        assert 'Underlying data' in page and 'api/hgcwa_passports/?label=3.8-3.0.2-2-4-4' in page
