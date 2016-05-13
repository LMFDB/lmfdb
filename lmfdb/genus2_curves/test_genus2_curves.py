# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class Genus2Test(LmfdbTest):

    # All tests should pass

    def test_Cond_search(self):
        L = self.tc.get('/Genus2Curve/Q/?cond=100-200&count=100')
        assert '196.a.21952.1' in L.data

    def test_disc_search(self):
        L = self.tc.get('/Genus2Curve/Q/?start=0&count=50&cond=1988&abs_disc=&num_rat_wpts=&torsion=&torsion_order=&two_selmer_rank=&analytic_rank=&is_gl2_type=&st_group=&real_geom_end_alg=&aut_grp=&geom_aut_grp=&locally_solvable=&has_square_sha=')
        assert '1988.a.3976.1' in L.data

    def test_torsion(self):
        L = self.tc.get('/Genus2Curve/Q/976/a/999424/1')
        assert '\Z/{29}\Z' in L.data
        L = self.tc.get('/Genus2Curve/Q/118606.a.118606.1')
        assert 'trivial' in L.data

    def test_sha_loc_solv(self):
        L = self.tc.get('/Genus2Curve/Q/?start=0&count=50&has_square_sha=True')
        assert '169.a.169.1' in L.data
        L = self.tc.get('/Genus2Curve/Q/?start=0&count=50&cond=&abs_disc=&num_rat_wpts=&torsion=&torsion_order=&two_selmer_rank=&analytic_rank=&is_gl2_type=&st_group=&real_geom_end_alg=&aut_grp=&geom_aut_grp=&locally_solvable=True&has_square_sha=False')
        assert 'displaying all 0 matches' in L.data
        L = self.tc.get('/Genus2Curve/Q/?start=0&count=50&cond=&abs_disc=&num_rat_wpts=&torsion=&torsion_order=&two_selmer_rank=&analytic_rank=&is_gl2_type=&st_group=&real_geom_end_alg=&aut_grp=&geom_aut_grp=&locally_solvable=False')
        assert '336.a.172032.1' in L.data

    def test_by_double_iso_label(self):
        L = self.tc.get('/Genus2Curve/Q/336/a/')
        assert '336.a.172032.1' in L.data

    def test_by_full_label(self):
        # Two elliptic curve factors and decomposing endomorphism algebra:
        L = self.tc.get('/Genus2Curve/Q/1088/b/2176/1')
        assert '32.a1' in L.data and '34.a3' in L.data
        # RM case, should we ever want this:
        #L = self.tc.get('/Genus2Curve/Q/17689/e/866761/1')
        #assert '17689' in L.data
        # QM curve:
        L = self.tc.get('Genus2Curve/Q/262144/d/524288/1')
        assert 'quaternion algebra' in L.data
        L = self.tc.get('Genus2Curve/Q/4096/b/65536/1')
        # Square over a quadratic extension that is CM over one extension and
        # multiplication by a quaternion algebra ramifying at infinity over
        # another:
        assert 'square of an elliptic curve' in L.data and '2.2.8.1-64.1-a3'\
            in L.data and r'\mathbf{H}' in L.data and '(CM)' in L.data

    def test_by_g2c_label(self):
        # This curve also decomposes as a square, this time of a curve without
        # a label:
        L = self.tc.get('/Genus2Curve/Q/169.a.169.1')
        assert 'square of an elliptic curve' in L.data and '\Z/{19}\Z'\
            in L.data
