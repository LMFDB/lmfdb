# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class EllCurveTest(LmfdbTest):
    # All tests should pass
    #
    def test_int_points(self):
        L = self.tc.get('/EllipticCurve/Q/234446/a/1')
        assert '4532, 302803' in L.get_data(as_text=True)

    def test_by_curve_label(self):
        L = self.tc.get('/EllipticCurve/Q/400/e/3')
        assert '15, 50' in L.get_data(as_text=True)

    def test_by_iso_label(self):
        L = self.tc.get('/EllipticCurve/Q/12350/s/')
        assert '[1, -1, 1, -3655, -83403]' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/12350/s')
        assert 'You should be redirected automatically to target URL:' in L.get_data(as_text=True)
        assert '/EllipticCurve/Q/12350/s/' in L.get_data(as_text=True)

    def test_Cremona_label_mal(self):
        L = self.tc.get('/EllipticCurve/Q/?jump=Cremona%3A12qx', follow_redirects=True)
        assert '12qx' in L.get_data(as_text=True) and 'not a valid label' in L.get_data(as_text=True)

    def test_missing_curve(self):
        L = self.tc.get('/EllipticCurve/Q/13.a1', follow_redirects=True)
        assert '13.a1' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/13a1', follow_redirects=True)
        assert '13a1' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/13/a/1', follow_redirects=True)
        assert '13.a1' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)

    def test_missing_class(self):
        L = self.tc.get('/EllipticCurve/Q/11.b', follow_redirects=True)
        assert '11.b' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/11b', follow_redirects=True)
        assert '11b' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/11/b', follow_redirects=True)
        assert '11.b' in L.get_data(as_text=True) and 'not in the database' in L.get_data(as_text=True)

    def test_invalid_class(self):
        L = self.tc.get('/EllipticCurve/Q/11/a1', follow_redirects=True)
        assert '11.a1' in L.get_data(as_text=True) and 'not a valid label for an isogeny class' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/11/a1banana', follow_redirects=True)
        assert '11.a1banana' in L.get_data(as_text=True) and 'not a valid label for an isogeny class' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/11/1', follow_redirects=True)
        assert '11.1' in L.get_data(as_text=True) and 'not a valid label for an isogeny class' in L.get_data(as_text=True)

    def test_Cond_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=1200&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '[0, 1, 0, -2133408, 1198675188]' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/210/')
        assert '[1, 0, 0, 729, -176985]' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/210')
        assert 'You should be redirected automatically to target URL:' in L.get_data(as_text=True)
        assert '/EllipticCurve/Q/210/' in L.get_data(as_text=True)

    def test_Weierstrass_search(self):
        L = self.tc.get('/EllipticCurve/Q/[1,2,3,4,5]')
        assert 'You should be redirected automatically to target URL:' in L.get_data(as_text=True)
        assert '/EllipticCurve/Q/%5B1%2C2%2C3%2C4%2C5%5D/' in L.get_data(as_text=True)

    def test_j_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=2000&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '41616.bi2' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/?jinv=0,1728')
        t = L.get_data(as_text=True)
        assert '27.a3' in t and '32.a3' in t and '11.a3' not in t
        L = self.tc.get('/EllipticCurve/Q/?jinv=~0,1728&count=100')
        assert '27.a3' not in t and '32.a3' not in t and '11.a3' in t

    def test_jbad_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=2.3&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert 'Error' in L.get_data(as_text=True)
        assert 'rational number' in L.get_data(as_text=True)

    def test_tors_search(self):
        L = self.tc.get('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=[7]&sha=&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '858.k1' in L.get_data(as_text=True)
        assert '[1, -1, 1, 9588, 2333199]' in L.get_data(as_text=True)

    def test_SurjPrimes_search(self):
        self.check_args_with_timeout('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=2&surj_quantifier=include&nonsurj_primes=&count=100', '[0, 0, 1, -270, -1708]');

    def test_NonSurjPrimes_search(self):
        self.check_args_with_timeout('/EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=&optimal=&surj_primes=&surj_quantifier=exactly&nonsurj_primes=37&count=100', '[0, 0, 0, -36705844875, 2706767485056250]');

    def test_BadPrimes_search(self):
        L = self.tc.get('/EllipticCurve/Q/?bad_quantifier=include&bad_primes=3%2C5')
        assert '15.a1' in L.get_data(as_text=True)
        assert '30.a1' in L.get_data(as_text=True)
        assert not('11.a1' in L.get_data(as_text=True))
        L = self.tc.get('/EllipticCurve/Q/?bad_quantifier=exclude&bad_primes=3%2C5')
        assert not('15.a1' in L.get_data(as_text=True))
        assert not('30.a1' in L.get_data(as_text=True))
        assert '11.a1' in L.get_data(as_text=True)
        L = self.tc.get('/EllipticCurve/Q/?bad_quantifier=exactly&bad_primes=3%2C5')
        assert '15.a1' in L.get_data(as_text=True)
        assert not('30.a1' in L.get_data(as_text=True))
        assert not('11.a1' in L.get_data(as_text=True))

    def test_num_int_pts_search(self):
        L = self.tc.get('/EllipticCurve/Q/?num_int_pts=1')
        assert '14.a2' in L.get_data(as_text=True)
        assert not('11.a1' in L.get_data(as_text=True))

    def test_cm_disc_search(self):
        self.check_args('EllipticCurve/Q/?cm_disc=-4', '32.a3')
        self.not_check_args('EllipticCurve/Q/?cm_disc=-4', '11.a1')

    def test_isogeny_class(self):
        L = self.tc.get('/EllipticCurve/Q/11/a/')
        assert '[0, -1, 1, 0, 0]' in L.get_data(as_text=True)

    def test_dl_qexp(self):
        L = self.tc.get('/EllipticCurve/Q/download_qexp/66.c3/100')
        assert '0,1,1,1,1,-4,1,-2,1,1,-4,1,1,4,-2,-4,1,-2,1,0,-4,-2,1,-6,1,11,4,1,-2,10,-4,-8,1,1,-2,8,1,-2,0,4,-4,2,-2,4,1,-4,-6,-2,1,-3,11,-2,4,4,1,-4,-2,0,10,0,-4,-8,-8,-2,1,-16,1,-12,-2,-6,8,2,1,-6,-2,11,0,-2,4,10,-4,1,2,4,-2,8,4,10,1,10,-4,-8,-6,-8,-2,0,1,-2,-3,1,11' in L.get_data(as_text=True)

    def test_dl_all(self):
        L = self.tc.get('/EllipticCurve/Q/download_all/26.b2')
        assert '[1, -1, 1, -3, 3]' in L.get_data(as_text=True)

    def test_sha(self):
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=2&torsion=&torsion_structure=&sha=2-&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '[0, 1, 0, -73824640, -244170894880]' in L.get_data(as_text=True)
        assert '226920.h1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=81&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert '101592.p1' in L.get_data(as_text=True)
        L = self.tc.get('EllipticCurve/Q/?start=0&conductor=&jinv=&rank=&torsion=&torsion_structure=&sha=8.999&optimal=&surj_primes=&surj_quantifier=include&nonsurj_primes=&count=100')
        assert 'Error' in L.get_data(as_text=True)

    def test_disc_factor(self):
        """
        Test for factorization of large discriminants
        """
        L = self.tc.get('/EllipticCurve/Q/26569/a/1')
        assert r'-1 \cdot 163^{9}' in L.get_data(as_text=True)

    def test_torsion_growth(self):
        """
        Test for torsion growth data
        """
        L = self.tc.get('/EllipticCurve/Q/392/c/1')
        assert ' is strictly larger than ' in L.get_data(as_text=True)
        assert '<a href=/EllipticCurve/3.3.49.1/512.1/e/3>3.3.49.1-512.1-e3</a>' in L.get_data(as_text=True)

    def test_990h(self):
        """
        Test the exceptional 990h/990.i optimal labelling.
        """
        # The isogeny class 990h (Cremona labelling) or 990.i (LMFDB labelling)
        # has a different Gamma-optimal curve in its labelling than all others.
        L = self.tc.get('/EllipticCurve/Q/990/i/')
        row = '\n'.join([
            '<td class="center"><a href="/EllipticCurve/Q/990h3/">990h3</a></td>',
            r'<td class="center">\([1, -1, 1, -1568, -4669]\)</td>',
            r'<td class="center">\(15781142246787/8722841600\)</td>',
            r'<td class="center">\(235516723200\)</td>',
            r'<td align="center">\([6]\)</td>',
            r'<td align="center">',
            r'\(1728\)</td>',
            r'<td align="center">',
            r'\(0.87260\)',
            r'</td>',
            r'<td>',
            r'  \(\Gamma_0(N)\)-optimal</td>'
        ])
        self.assertTrue(row in L.get_data(as_text=True),
                        "990.i appears to have the wrong optimal curve.")

        L = self.tc.get('EllipticCurve/Q/990h/')
        #print row
        #print L.get_data(as_text=True)
        self.assertTrue(row in L.get_data(as_text=True),
                        "990h appears to have the wrong optimal curve.")

    def test_completeness(self):
        """
        Test that the dynamic completeness knowl displays OK.
        """
        L = self.tc.get('/EllipticCurve/Q/Completeness')
        assert 'Currently, the database includes' in L.get_data(as_text=True)
