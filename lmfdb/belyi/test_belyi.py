# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

class BelyiTest(LmfdbTest):

    def check_args(self, path, text):
        L = self.tc.get(path, follow_redirects=True)
        # assert text in L.data, "assert failed: %s not in : %s" % (text, L.data)
        assert text in L.data

    ######## all tests should pass

    def test_stats(self):
        L = self.tc.get('/Belyi/stats')
        assert 'Galois orbits of Belyi maps' in L.data and 'proportion' in L.data

    def test_random(self):
        self.check_args('/Belyi/random', 'Monodromy group')

    def test_by_galmap_label(self):
        self.check_args('/Belyi/6T15-[5,4,4]-51-42-42-g1-b', 'A_6')

    def test_passport_label(self):
        self.check_args('/Belyi/5T4-[5,3,3]-5-311-311-g0-a', '5T4-[5,3,3]-5-311-311-g0')

    def test_passport(self):
        self.check_args('/Belyi/9T33-[10,15,2]-522-531-22221-g0-a', '3.1.14175.1')

    ######## web pages

    def test_urls(self):
        self.check_args('/Belyi/4T5-[4,3,2]-4-31-211-g0-a', 'Belyi map 4T5-[4,3,2]-4-31-211-g0-a')
        self.check_args('/Belyi/4T5-[4,3,2]-4-31-211-g0-', 'Passport 4T5-[4,3,2]-4-31-211-g0')
        self.check_args('/Belyi/4T5-[4,3,2]-4-31-211-g0', 'Passport 4T5-[4,3,2]-4-31-211-g0')
        self.check_args('/Belyi/4T5-[4,3,2]-4-31-211-', 'Belyi maps with group 4T5 and orders [4,3,2]')
        self.check_args('/Belyi/4T5-[4,3,2]-4-31-', 'Belyi maps with group 4T5 and orders [4,3,2]')
        self.check_args('/Belyi/4T5-[4,3,2]', 'Belyi maps with group 4T5')

    ######## searches

    def test_deg_range(self):
        L = self.tc.get('/Belyi/?deg=2-7')
        assert '5T4-[5,3,3]-5-311-311-g0-a' in L.data

    def test_group_search(self):
        self.check_args('/Belyi/?group=7T5', '7T5-[7,7,3]-7-7-331-g2-a')

    def test_abc_search(self):
        self.check_args('/Belyi/?abc=2-4', '6T10-[4,4,3]-42-42-33-g1-a')

    def test_abc_list_search(self):
        self.check_args('/Belyi/?abc_list=[7,6,6]', '7T7-[7,6,6]-7-3211-3211-g0-a')

    def test_genus_search(self):
        self.check_args('/Belyi/?genus=2', '6T6-[6,6,3]-6-6-33-g2-a')

    def test_orbit_size_search(self):
        self.check_args('/Belyi/?orbit_size=20-', '7T7-[6,10,4]-61-52-421-g1-a')

    def test_geom_type_search(self):
        self.check_args('/Belyi/?geomtype=H', '6T8-[4,4,3]-411-411-33-g0-a')

    def test_count_search(self):
        self.check_args('/Belyi/?count=20', '5T1-[5,5,5]-5-5-5-g2-c')
