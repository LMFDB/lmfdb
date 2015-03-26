# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest
import math
import unittest2

class EllCurveTest(LmfdbTest):

    # All tests should pass
    #
    def test_int_points(self):
        L = self.tc.get('/EllipticCurve/Q/234446/a/1')
        assert '4532, 302803' in L.data

    def test_by_curve_label(self):
        L = self.tc.get('/EllipticCurve/Q/400/e/3')
        assert '15, 50' in L.data

    def test_by_iso_label(self):
        L = self.tc.get('/EllipticCurve/Q/12350/s/')
        assert '[1, -1, 1, -3655, -83403]' in L.data
        L = self.tc.get('/EllipticCurve/Q/12350/s')
        assert 'You should be redirected automatically to target URL: <a href="http://localhost/EllipticCurve/Q/12350/s/">http://localhost/EllipticCurve/Q/12350/s/</a>' in L.data

    def test_Cremona_label_mal(self):
        L = self.tc.get('/EllipticCurve/Q/?label=Cremona%3A12qx&jump=label+or+isogeny+class')
        assert '12qx does not define a recognised elliptic curve' in L.data

    def test_Cond_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=1200&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '[0, 1, 0, -2133408, 1198675188]' in L.data
        L = self.tc.get('/EllipticCurve/Q/210/')
        assert '[1, 0, 0, 729, -176985]' in L.data
        L = self.tc.get('/EllipticCurve/Q/210')
        assert 'You should be redirected automatically to target URL: <a href="http://localhost/EllipticCurve/Q/210/">http://localhost/EllipticCurve/Q/210/</a>' in L.data

    def test_Weierstrass_search(self):
        L = self.tc.get('/EllipticCurve/Q/[1,2,3,4,5]')
        assert 'You should be redirected automatically to target URL: <a href="/EllipticCurve/Q/10351.b1">/EllipticCurve/Q/10351.b1</a>' in L.data

    def test_j_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=2000&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '41616.bi2' in L.data

    def test_jbad_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=2.3&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert 'Error' in L.data
        assert 'rational number' in L.data

    def test_tors_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=[7]&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '858.k1' in L.data
        assert '[1, -1, 1, 9588, 2333199]' in L.data

    def test_SurjPrimes_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=2&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '[0, 0, 1, -270, -1708]' in L.data

    def test_NonSurjPrimes_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=exactly&nonsurj_primes=37&count=100')
        assert '[0, 0, 0, -36705844875, 2706767485056250]' in L.data

    def test_isogeny_class(self):
        L = self.tc.get('/EllipticCurve/Q/11/a/')
        assert '[0, -1, 1, 0, 0]' in L.data

    def test_dl_qexp(self):
        L = self.tc.get('/EllipticCurve/Q/download_qexp/66.c3/100')
        assert '0,1,1,1,1,-4,1,-2,1,1,-4,1,1,4,-2,-4,1,-2,1,0,-4,-2,1,-6,1,11,4,1,-2,10,-4,-8,1,1,-2,8,1,-2,0,4,-4,2,-2,4,1,-4,-6,-2,1,-3,11,-2,4,4,1,-4,-2,0,10,0,-4,-8,-8,-2,1,-16,1,-12,-2,-6,8,2,1,-6,-2,11,0,-2,4,10,-4,1,2,4,-2,8,4,10,1,10,-4,-8,-6,-8,-2,0,1,-2,-3,1,11' in L.data

    def test_dl_all(self):
        L = self.tc.get('/EllipticCurve/Q/download_all/26.b2')
        assert '[1, -1, 1, -3, 3]' in L.data

    def test_sha(self):
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=2&torsion=&torsion_structure=&sha=2-&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '[0, 1, 0, -73824640, -244170894880]' in L.data
        assert '226920.h1' in L.data
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=81&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '101592.p1' in L.data
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=8.999&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert 'Error' in L.data

    def test_disc_factor(self):
        """
        Test for factorization of large discriminants
        """
        L = self.tc.get('/EllipticCurve/Q/26569/a/1')
        assert '\(-1 \cdot 163^{9} \)' in L.data

