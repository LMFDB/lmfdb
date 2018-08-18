# -*- coding: utf-8 -*-
from lmfdb.base import LmfdbTest

class Genus2Test(LmfdbTest):

    # All tests should pass
    def test_stats(self):
        L = self.tc.get('/Genus2Curve/Q/stats')
        assert 'Sato-Tate groups' in L.data and 'proportion' in L.data
        
    def test_cond_range(self):
        L = self.tc.get('/Genus2Curve/Q/?cond=100000-1000000')
        assert '100000.a.200000.1' in L.data

    def test_disc_range(self):
        L = self.tc.get('/Genus2Curve/Q/?abs_disc=100000-1000000')
        assert '336.a.172032.1' in L.data

    def test_by_curve_label(self):
        L = self.tc.get('/Genus2Curve/Q/169.a.169.1',follow_redirects=True)
        assert 'square of' in L.data and 'E_6' in L.data
        L = self.tc.get('/Genus2Curve/Q/1152.a.147456.1',follow_redirects=True)
        assert 'non-isogenous elliptic curves' in L.data and '24.a5' in L.data and '48.a5' in L.data
        L = self.tc.get('/Genus2Curve/Q/15360.f.983040.2',follow_redirects=True)
        assert 'N(G_{1,3})' in L.data and '480.b3' in L.data and '32.a3' in L.data

    def test_isogeny_class_label(self):
        L = self.tc.get('/Genus2Curve/Q/1369/a/')
        assert '1369.1' in L.data and '50653.1' in L.data and 'G_{3,3}' in L.data
        
    def test_Lfunction_link(self):
        L = self.tc.get('/L/Genus2Curve/Q/1369/a',follow_redirects=True)
        assert 'G_{3,3}' in L.data and 'Motivic weight' in L.data
        
    def test_twist_link(self):
        L = self.tc.get('/Genus2Curve/Q/?g22=1016576&g20=5071050752/9&g21=195344320/9')
        for label in ['576.b.147456.1', '1152.a.147456.1', '2304.b.147456.1', '4608.a.4608.1','4608.b.4608.1']:
            assert label in L.data
            
    def test_by_conductor(self):
        L = self.tc.get('/Genus2Curve/Q/15360/')
        for x in "abcdefghij":
            assert "15360."+x in L.data
        L = self.tc.get('/Genus2Curve/Q/15360/?abs_disc=169')
        assert 'No matches' in L.data
            
    def test_by_url_isogeny_class_label(self):
        L = self.tc.get('/Genus2Curve/Q/336/a/')
        assert '336.a.172032.1' in L.data

    def test_by_url_curve_label(self):
        # Two elliptic curve factors and decomposing endomorphism algebra:
        L = self.tc.get('/Genus2Curve/Q/1088/b/2176/1')
        assert '32.a1' in L.data and '34.a3' in L.data
        # RM curve:
        L = self.tc.get('/Genus2Curve/Q/17689/e/866761/1')
        assert ('simple' in L.data or 'Simple' in L.data) and 'G_{3,3}' in L.data
        # QM curve:
        L = self.tc.get('Genus2Curve/Q/262144/d/524288/1')
        assert 'quaternion algebra' in L.data and 'J(E_2)' in L.data
        L = self.tc.get('Genus2Curve/Q/4096/b/65536/1')
        # Square over a quadratic extension that is CM over one extension and
        # multiplication by a quaternion algebra ramifying at infinity over another
        assert 'square of' in L.data and '2.2.8.1-64.1-a3'\
            in L.data and r'\mathbf{H}' in L.data and '(CM)' in L.data

    def test_by_url_isogeny_class_discriminant(self):
        L = self.tc.get('/Genus2Curve/Q/15360/f/983040/')
        assert '15360.f.983040.1' in L.data and '15360.f.983040.2' in L.data and not '15360.d.983040.1' in L.data

    def test_random(self):
        L = self.tc.get('/Genus2Curve/Q/random',follow_redirects=True)
        assert 'geometric invariants' in L.data

    def test_conductor_search(self):
        L = self.tc.get('/Genus2Curve/Q/?cond=1225')
        assert '1225.a.6125.1' in L.data

    def test_disc_search(self):
        L = self.tc.get('/Genus2Curve/Q/?abs_disc=3976')
        assert '1988.a.3976.1' in L.data

    def test_download(self):
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=gp")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=sage")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=magma")

    def test_rational_weierstrass_points_search(self):
        L = self.tc.get('/Genus2Curve/Q/?num_rat_wpts=4')
        assert '360.a.6480.1' in L.data

    def test_torsion_search(self):
        L = self.tc.get('/Genus2Curve/Q/?torsion=[2,2,2]')
        assert '1584.a.684288.1' in L.data

    def test_torsion_order_search(self):
        L = self.tc.get('/Genus2Curve/Q/?torsion_order=39')
        assert '1116.a.214272.1' in L.data

    def test_two_selmer_rank_search(self):
        L = self.tc.get('/Genus2Curve/Q/?two_selmer_rank=6')
        assert '65520.b.131040.1' in L.data

    def test_analytic_rank_search(self):
        L = self.tc.get('/Genus2Curve/Q/?analytic_rank=4')
        assert '440509.a.440509.1' in L.data

    def test_gl2_type_search(self):
        L = self.tc.get('/Genus2Curve/Q/?gl2_type=True')
        assert '169.a.169.1' in L.data

    def test_st_group_search(self):
        L = self.tc.get('/Genus2Curve/Q/?st_group=J(E_6)')
        assert '6075.a.18225.1' in L.data

    def test_st0_group_search(self):
        L = self.tc.get('/Genus2Curve/Q/?real_geom_end_alg=C x R')
        assert '448.a.448.1' in L.data

    def test_automorphism_group_search(self):
        L = self.tc.get('/Genus2Curve/Q/?aut_grp_id=[12,4]')
        assert '196.a.21952.1' in L.data

    def test_geometric_automorphism_group_search(self):
        L = self.tc.get('/Genus2Curve/Q/?geom_aut_grp_id=[48,29]')
        assert '4096.b.65536.1' in L.data

    def test_locally_solvable_serach(self):
        L = self.tc.get('/Genus2Curve/Q/?locally_solvable=False')
        assert '336.a.172032.1' in L.data
        
    def test_sha_search(self):
        L = self.tc.get('/Genus2Curve/Q/?has_square_sha=False')
        assert  '336.a.172032.1' in L.data and not '169.a.169.1' in L.data
        L = self.tc.get('/Genus2Curve/Q/?locally_solvable=True&has_square_sha=False')
        assert 'No matches' in L.data

    def test_torsion(self):
        L = self.tc.get('/Genus2Curve/Q/976/a/999424/1')
        assert '\Z/{29}\Z' in L.data
        L = self.tc.get('/Genus2Curve/Q/118606/a/118606/1')
        assert 'trivial' in L.data
        
    def test_mfhilbert(self):
        L = self.tc.get('/Genus2Curve/Q/12500/a/12500/1')
        assert '2.2.5.1-500.1-a' in L.data
        L = self.tc.get('/Genus2Curve/Q/12500/a/')
        assert '2.2.5.1-500.1-a' in L.data
        
    def test_ratpts(self):
        L = self.tc.get('/Genus2Curve/Q/792079/a/792079/1')
        assert '(-15 : -6579 : 14)' in L.data
        assert '(13 : -4732 : 20)' in L.data
        L = self.tc.get('/Genus2Curve/Q/126746/a/126746/1')
        assert 'everywhere' in L.data
        assert 'no rational points' in L.data
        
