# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest

class BelyiTest(LmfdbTest):

    def check_args(self, path, text):
        L = self.tc.get(path, follow_redirects=True)
        assert text in L.data, "assert failed: %s not in : %s" % (text, L.data)

    # All tests should pass
    def test_stats(self):
        L = self.tc.get('/Belyi/stats')
        assert 'number of maps' in L.data and 'proportion' in L.data

    def test_random(self):
        self.check_args('/Belyi/random', 'Monodromy group')

    # def test_by_galmap_label(self):
    #     self.check_args('/Belyi/6T15-[5,4,4]-51-42-42-g1-b', 'A_6')

    # def test_passport_label(self):
    #     self.check_args('/Belyi/5T4-[5,3,3]-5-311-311-g0-a', '5T4-[5,3,3]-5-311-311-g0')

    # def test_passport(self):
    #     self.check_args('/Belyi/9T33-[10,15,2]-522-531-22221-g0-a', '3.1.14175.1')






    # def test_by_conductor(self):
    #     L = self.tc.get('/Genus2Curve/Q/15360/')
    #     for x in "abcdefghij":
    #         assert "15360."+x in L.data
    #     L = self.tc.get('/Genus2Curve/Q/15360/?abs_disc=169')
    #     assert '0 matches' in L.data

    # def test_by_url_isogeny_class_label(self):
    #     L = self.tc.get('/Genus2Curve/Q/336/a/')
    #     assert '336.a.172032.1' in L.data

    # def test_by_url_curve_label(self):
    #     # Two elliptic curve factors and decomposing endomorphism algebra:
    #     L = self.tc.get('/Genus2Curve/Q/1088/b/2176/1')
    #     assert '32.a1' in L.data and '34.a3' in L.data
    #     # RM curve:
    #     L = self.tc.get('/Genus2Curve/Q/17689/e/866761/1')
    #     assert ('simple' in L.data or 'Simple' in L.data) and 'G_{3,3}' in L.data
    #     # QM curve:
    #     L = self.tc.get('Genus2Curve/Q/262144/d/524288/1')
    #     assert 'quaternion algebra' in L.data and 'J(E_2)' in L.data
    #     L = self.tc.get('Genus2Curve/Q/4096/b/65536/1')
    #     # Square over a quadratic extension that is CM over one extension and
    #     # multiplication by a quaternion algebra ramifying at infinity over another
    #     assert 'square of' in L.data and '2.2.8.1-64.1-a3'\
    #         in L.data and r'\mathbf{H}' in L.data and '(CM)' in L.data

    # def test_by_url_isogeny_class_discriminant(self):
    #     L = self.tc.get('/Genus2Curve/Q/15360/f/983040/')
    #     assert '15360.f.983040.1' in L.data and '15360.f.983040.2' in L.data and not '15360.d.983040.1' in L.data

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

    def test_genus_search(self):
        self.check_args('/Belyi/?genus=2', '6T6-[6,6,3]-6-6-33-g2-a')

    def test_orbit_size_search(self):
        self.check_args('/Belyi/?orbit_size=20-', '7T7-[6,10,4]-61-52-421-g1-a')

    def test_geom_type_search(self):
        self.check_args('/Belyi/?geomtype=H', '6T8-[4,4,3]-411-411-33-g0-a')

    def test_count_search(self):
        self.check_args('/Belyi/?count=20', '5T1-[5,5,5]-5-5-5-g2-c')


    # def test_download(self):
    #     self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=gp")
    #     self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=sage")
    #     self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=magma")

    # def test_torsion(self):
    #     L = self.tc.get('/Genus2Curve/Q/976/a/999424/1')
    #     assert '\Z/{29}\Z' in L.data
    #     L = self.tc.get('/Genus2Curve/Q/118606/a/118606/1')
    #     assert 'trivial' in L.data

    # def test_mfhilbert(self):
    #     L = self.tc.get('/Genus2Curve/Q/12500/a/12500/1')
    #     assert '2.2.5.1-500.1-a' in L.data
    #     L = self.tc.get('/Genus2Curve/Q/12500/a/')
    #     assert '2.2.5.1-500.1-a' in L.data

    # def test_ratpts(self):
    #     L = self.tc.get('/Genus2Curve/Q/792079/a/792079/1')
    #     assert '(-15 : -6579 : 14)' in L.data
    #     assert '(13 : -4732 : 20)' in L.data
    #     L = self.tc.get('/Genus2Curve/Q/126746/a/126746/1')
    #     assert 'everywhere' in L.data
    #     assert 'no rational points' in L.data
