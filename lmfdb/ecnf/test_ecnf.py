# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest

class EllCurveTest(LmfdbTest):

    # All tests should pass
    #
    def test_minimal_eqn(self):
        r"""
        Check that the elliptic curve/#field tells about (non)existence of a global minimal model
        """
        L = self.tc.get('/EllipticCurve/2.2.89.1/81.1/a/1')
        assert 'This is a <a title="Global minimal model' in L.data
        L = self.tc.get('/EllipticCurve/2.2.229.1/9.3/a/2')
        assert 'This is not a <a title="Global minimal model' in L.data
        assert 'at all primes except' in L.data

    def test_base_field(self):
        r"""
        Check that the elliptic curve/#field tells about its base field
        """
        L = self.tc.get('/EllipticCurve/3.1.23.1/89.1/A/1')
        assert '3.1.23.1' in L.data
        L = self.tc.get('/EllipticCurve/2.2.5.1/49.1/a/2')
        assert '\phi' in L.data

    def test_bad_red(self):
        r"""
        Check that the elliptic curve/#field tells about its bad reduction primes
        """
        L = self.tc.get('/EllipticCurve/2.2.5.1/31.2/a/3')
        assert 'Non-split multiplicative' in L.data
        L = self.tc.get('/EllipticCurve/2.2.5.1/64.1/a/1')
        assert 'Additive' in L.data

    def test_weierstrass(self):
        r"""
        Check that the elliptic curve/#field tells about its Weirstrass eqn
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/225.2/a/2')
        assert '396' in L.data
        assert '2982' in L.data

    def test_conductor(self):
        r"""
        Check that the elliptic curve/#field tells about its conductor and disciminant
        """
        L = self.tc.get('/EllipticCurve/2.0.7.1/10000.5/a/1')
        assert '10000' in L.data
        assert '15625000000000000' in L.data
        assert '87890625' in L.data
        assert '25^{9}' in L.data
        assert '12' in L.data

    def test_j(self):
        r"""
        Check that the elliptic curve/#field tells about its j invariant
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert '226834389543384' in L.data
        assert '1490902050625' in L.data
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1') # Test factorisation
        assert '8798344145175011328000' in L.data

    def test_download(self):
        r"""
        Check that the code download links work
        """
        L = self.tc.get('/EllipticCurve/2.0.4.1/5525.5/b/9')
        assert 'Code to Magma' in L.data
        assert 'Code to SageMath' in L.data
        assert 'Code to GP' in L.data
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/magma')
        assert 'Magma code for working with elliptic curve 2.2.89.1-81.1-a1' in L.data
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/sage')
        assert 'SageMath code for working with elliptic curve 2.2.89.1-81.1-a1' in L.data
        L = self.tc.get('EllipticCurve/2.2.89.1/81.1/a/1/download/gp')
        assert 'Pari/GP code for working with elliptic curve 2.2.89.1-81.1-a1' in L.data

    def test_search(self):
        r"""
        Check ecnf search results
        """
        # Conductor 1
        L = self.tc.get('/EllipticCurve/?start=0&count=50&conductor_norm=1&include_isogenous=on&include_base_change=on')
        assert '2115 a - 13286543' in L.data
        # 4*4 torsion
        L = self.tc.get('/EllipticCurve/?start=0&count=50&include_isogenous=on&include_base_change=on&torsion=&torsion_structure=[4%2C4]')
        assert '/EllipticCurve/2.0.4.1/5525.5/b/9' in L.data
        # 13 torsion
        L = self.tc.get('/EllipticCurve/?torsion=13')
        assert '2745' in L.data
        assert '3.3.49.1' in L.data
        #field (see what I did here?)
        L = self.tc.get('/EllipticCurve/?field=Qsqrt-11&include_base_change=on&conductor_norm=&include_isogenous=on&torsion=&torsion_structure=&count=')
        assert '2.0.11.1' in L.data
        assert '1681' in L.data


    def test_related_objects(self):
        for url, text in [('/EllipticCurve/2.0.8.1/324.3/a/1',
                ['Isogeny class 324.3-a',
                 'Twists',
                 'Base-change of 36.a4',
                 'Base-change of 576.f3',
                 'Bianchi modular form 2.0.8.1-324.3-a',
                 'Hilbert modular form 2.2.24.1-36.1-a',
                 'Isogeny class 2.2.24.1-36.1-a',
                 'Isogeny class 20736.i',
                 'L-function']),
                ('/EllipticCurve/2.0.11.1/256.1/b/1',
                    ['Isogeny class 256.1-b',
                     'Twists',
                     'Bianchi modular form 2.0.11.1-256.1-a',
                     'Bianchi modular form 2.0.11.1-256.1-b',
                     'Hilbert modular form 2.2.44.1-16.1-a',
                     'Hilbert modular form 2.2.44.1-16.1-c',
                     'Isogeny class 2.0.11.1-256.1-a',
                     'Isogeny class 2.2.44.1-16.1-a',
                     'Isogeny class 2.2.44.1-16.1-c',
                     'L-function'])]:
            L = self.tc.get(url).data
            for t in text:
                assert t in L

