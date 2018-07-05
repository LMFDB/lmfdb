# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

class HigherGenusWithAutomorphismsTest(LmfdbTest):

    # All tests should pass
    #
    def test_url_label(self):
	L = self.tc.get('/HigherGenus/C/Aut/2.24-8.0.2-4-6')
	assert '[ 0; 2, 4, 6 ]' in L.data


    def test_passport_label(self):
        L = self.tc.get('/HigherGenus/C/Aut/3.14-2.0.2-7-14.1')
        assert '(1,8) (2,9) (3,10) (4,11) (5,12) (6,13) (7,14)'  in L.data
        
    def test_url_naturallabel(self):
	L = self.tc.get('/HigherGenus/C/Aut/junk',follow_redirects=True)
	assert 'No family with label' in L.data
    

    def test_search_genus_group(self):
        L = self.tc.get('/HigherGenus/C/Aut/?genus=2&group=%5B48%2C29%5D&signature=&dim=&hyperelliptic=include&count=20&Submit=Search')
        assert 'both matches' in L.data


    def test_random(self):
        L = self.tc.get('/HigherGenus/C/Aut/random',follow_redirects=True)
        assert 'Dimension of the corresponding' in L.data

    def test_magma_download(self):
        L = self.tc.get('/HigherGenus/C/Aut/5.32-27.0.2-2-2-4.1/download/magma')
        assert '// Here we add an action to data.' in L.data

    def test_full_auto_links(self):
        L = self.tc.get('/HigherGenus/C/Aut/4.9-1.0.9-9-9.1')
        assert 'Full automorphism 4.18-2.0.2-9-18' in L.data        
        
    def test_index_page(self):
        L = self.tc.get('/HigherGenus/C/Aut/')
        assert 'Find specific automorphisms of higher genus curves' in L.data

    def test_stats_page(self):
        L = self.tc.get('/HigherGenus/C/Aut/stats')
        assert 'unique groups' in L.data


    def test_unique_groups_pages(self):
        L = self.tc.get('/HigherGenus/C/Aut/stats/groups_per_genus/5')
        assert 'Distribution of groups in curves of genus 5' in L.data

        
