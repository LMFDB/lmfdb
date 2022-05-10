
from .LfunctionPlot import paintSvgFileAll
from lmfdb.tests import LmfdbTest

class LfunctionTest(LmfdbTest):

    # All tests should pass

    #------------------------------------------------------
    # Testing at least one example of each type of L-function page
    #------------------------------------------------------



    def test_LDirichlet(self):
        L = self.tc.get('/L/Character/Dirichlet/19/9/', follow_redirects = True)
        assert '0.4813597783' in L.get_data(as_text=True)
        #assert 'SatoTate' in L.get_data(as_text=True)
        #assert 'mu(9)' in L.get_data(as_text=True)
        assert '2.13818063440820276534' in L.get_data(as_text=True)
        assert '1-19-19.9-r0-0-0' in L.get_data(as_text=True)

        L = self.tc.get('/L/Character/Dirichlet/6400/3/', follow_redirects = True)
        assert '2.131285033' in L.get_data(as_text=True) in L.get_data(as_text=True)
        #assert 'SatoTate' in L.get_data(as_text=True)
        #assert 'mu(320)' in L.get_data(as_text=True)
        assert '3.1381043104275982' in L.get_data(as_text=True)
        assert '1-80e2-6400.3-r0-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Character/Dirichlet/17/16/', follow_redirects = True)
        assert '1.01608483' in L.get_data(as_text=True)
        assert '1-17-17.16-r0-0-0' in L.get_data(as_text=True)

        # errors
        for url in ['/L/Character/Dirichlet/6400/2/',
                    '/L/Character/Dirichlet/6400/6399/',
                    'L/Character/Dirichlet/1000000000/3/',
                    'L/Character/Dirichlet/1000000000000000000000/3/']:
            L = self.tc.get(url, follow_redirects = True)
            assert 'not found' in L.get_data(as_text=True)

    def test_Lec(self):
        L = self.tc.get('/L/EllipticCurve/Q/11/a/', follow_redirects=True)
        assert '0.253841' in L.get_data(as_text=True)
        assert 'Elliptic curve 11.a' in L.get_data(as_text=True)
        assert 'Modular form 11.2.a.a' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '2-11-1.1-c1-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/11/1.1/c1/0/0/')
        assert '6.362613894713' in L.get_data(as_text=True)


        L = self.tc.get('/L/EllipticCurve/Q/27/a/', follow_redirects=True)
        assert '0.5888795834' in L.get_data(as_text=True)
        assert 'Elliptic curve 27.a'in L.get_data(as_text=True)
        assert 'Modular form 27.2.a.a' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '2-3e3-1.1-c1-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/3e3/1.1/c1/0/0/')
        assert '4.043044013797' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/Q/379998/d/', follow_redirects=True)
        assert '9.364311197' in L.get_data(as_text=True)
        assert 'Elliptic curve 379998.d' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '2-379998-1.1-c1-0-2' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/379998/1.1/c1/0/2/')
        assert '0.8292065891985' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/2.2.5.1/31.1/a/', follow_redirects=True)
        assert '0.3599289594' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.5.1-31.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.5.1-31.2-a' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.5.1-31.1-a' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.5.1-31.2-a' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '4-775-1.1-c1e2-0-0' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/2.2.5.1/80.1/a/', follow_redirects=True)
        assert '0.5945775518' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.5.1-80.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 20.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 100.a' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.5.1-80.1-a' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '4-2000-1.1-c1e2-0-0' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/2.0.11.1/256.1/a/', follow_redirects=True)
        assert 'Elliptic curve 2.0.11.1-256.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.11.1-256.1-b' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.44.1-16.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.44.1-16.1-c' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.44.1-16.1-a' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.44.1-16.1-c' in L.get_data(as_text=True)
        assert 'Bianchi modular form 2.0.11.1-256.1-a' in L.get_data(as_text=True)
        assert 'Bianchi modular form 2.0.11.1-256.1-b' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '4-176e2-1.1-c1e2-0-4' in L.get_data(as_text=True)


        L = self.tc.get('/L/EllipticCurve/2.0.1879.1/1.0.1/a/', follow_redirects=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.1879.1-1.0.1-a' in L.get_data(as_text=True)
        assert '4-1879e2-1.1-c1e2-0-0' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/2.0.4.1/100.2/a/', follow_redirects=True)
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)
        assert '0.5352579714' in L.get_data(as_text=True)
        assert 'Bianchi modular form 2.0.4.1-100.2-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.4.1-100.2-a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 20.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 80.b' in L.get_data(as_text=True)
        assert 'Modular form 20.2.a.a' in L.get_data(as_text=True)
        assert 'Modular form 80.2.a.b' in L.get_data(as_text=True)
        assert '4-40e2-1.1-c1e2-0-1' in L.get_data(as_text=True)
        # check the zeros across factors
        assert '2.76929890617261215013507568311' in L.get_data(as_text=True)
        assert '4.78130792717525308450176413839' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/20/2/a/a/', follow_redirects=True)
        assert '4.78130792717525308450176413839' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/Q/20/a/', follow_redirects=True)
        assert '4.781307927175253' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/80/2/a/b/', follow_redirects=True)
        assert '2.76929890617261215013507568311' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/Q/80/b/', follow_redirects=True)
        assert '2.769298906172612' in L.get_data(as_text=True)



        L = self.tc.get('/L/EllipticCurve/2.0.3.1/75.1/a/', follow_redirects=True)
        assert 'Bianchi modular form 2.0.3.1-75.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.3.1-75.1-a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 15.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 45.a' in L.get_data(as_text=True)
        assert 'Modular form 15.2.a.a' in L.get_data(as_text=True)
        assert 'Modular form 45.2.a.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/2.0.8.1/2592.3/c/', follow_redirects=True)
        assert 'Bianchi modular form 2.0.8.1-2592.3-c' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.8.1-2592.1-f' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.8.1-2592.3-c' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.8.1-2592.1-f' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 288.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 576.i' in L.get_data(as_text=True)
        assert 'Modular form 288.2.a.a' in L.get_data(as_text=True)


        # check we get same L-fcn across 2 instances
        for url in ['EllipticCurve/2.0.11.1/11.1/a/', 'ModularForm/GL2/ImaginaryQuadratic/2.0.11.1/11.1/a/']:
            L = self.tc.get('/L/' + url, follow_redirects=True)
            assert '4-11e3-1.1-c1e2-0-0' in L.get_data(as_text=True)





    def test_Lcmf(self):
        # test old links
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/1/a/0/', follow_redirects=True)
        assert "Modular form 11.2.a.a.1.1" in L.get_data(as_text=True)



        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/a/a/1/1/', follow_redirects=True)
        assert '4.84e4' in L.get_data(as_text=True) # a_7
        assert '71.7' in L.get_data(as_text=True) # a_2
        assert '1.51472556377341264746894823521' in L.get_data(as_text=True) # first zero

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/a/a/', follow_redirects=True)
        assert '1.51472556377341264746894823521' in L.get_data(as_text=True) # first zero
        assert 'Origins of factors' in L.get_data(as_text=True)
        for i in range(1,6):
            assert 'Modular form 13.12.a.a.1.%d' % i in L.get_data(as_text=True)
        assert '371293' in L.get_data(as_text=True) # L_3 root
        assert '2.54e3' in L.get_data(as_text=True) # a_13


        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/7/3/b/a/', follow_redirects=True)
        assert '0.332981' in L.get_data(as_text=True)
        assert '2-7-7.6-c2-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/7/7.6/c2/0/0/')
        assert '7.21458918128718444354242474222' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/18/a/a/', follow_redirects=True)
        assert '1.34e12' in L.get_data(as_text=True) # a26
        assert '2-1-1.1-c17-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/1/1.1/c17/0/0/')
        assert '18.17341115038590061946085869072' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/4/c/a/3/1/', follow_redirects=True)
        assert '0.523757' in L.get_data(as_text=True) and '0.530517' in L.get_data(as_text=True)
        assert '(16 + 27.7<em>i</em>)' in L.get_data(as_text=True)
        assert 'Dual L-function' in L.get_data(as_text=True)
        assert '2-13-13.3-c3-0-2' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/2/13/13.3/c3/0/2/')
        assert '5.68016097036963500634962429051' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/a/a/', follow_redirects=True)
        assert '0.253841' in L.get_data(as_text=True)
        assert 'Elliptic curve 11.a' in L.get_data(as_text=True)
        assert 'Modular form 11.2.a.a' in L.get_data(as_text=True)
        #FIXME fill ST info in origins = CMFs
        #assert '/SatoTateGroup/1.2.' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/2/e/a/', follow_redirects=True)
        assert 'Genus 2 curve 169.a' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a.4.1' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a.10.1' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.4.E_6' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/18/2/c/a/', follow_redirects=True)
        assert 'Genus 2 curve 324.a' in L.get_data(as_text=True)
        assert 'Modular form 18.2.c.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Modular form 18.2.c.a.7.1' in L.get_data(as_text=True)
        assert 'Modular form 18.2.c.a.13.1' in L.get_data(as_text=True)
        #assert '/SatoTateGroup/1.4.E_3' in L.get_data(as_text=True)


        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/490/2/a/a/', follow_redirects=True)
        assert 'Modular form 490.2.a.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 490.a' in L.get_data(as_text=True)
        assert '0.729971' in L.get_data(as_text=True)
        assert r'(2,\ 490,\ (\ :1/2),\ 1)' in L.get_data(as_text=True)
        assert '0.940863335931152039286421559408' in L.get_data(as_text=True)
        assert '1 + 7 T + p T^{2}' in L.get_data(as_text=True)
        assert r'\chi_{490} (1, \cdot )' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/Q/490/a/', follow_redirects=True)
        assert '0.9408633359311520' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/51/1/', follow_redirects=True)
        assert 'Modular form 350.2.e.k.51.1' in L.get_data(as_text=True)
        assert 'Dual L-function' in L.get_data(as_text=True)
        assert r'\chi_{350} (51, \cdot )' in L.get_data(as_text=True)
        assert r'(2,\ 350,\ (\ :1/2),\ 0.991 + 0.126i)' in L.get_data(as_text=True)
        assert '2.00692' in L.get_data(as_text=True)
        assert '0.127359' in L.get_data(as_text=True)
        assert '1 + 6T + 29T^{2}' in L.get_data(as_text=True)
        assert '1.68486586956382681209348921118' in L.get_data(as_text=True)
        assert '3.10207045712088492456262227600' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/151/1/', follow_redirects=True)
        assert 'Modular form 350.2.e.k.151.1' in L.get_data(as_text=True)
        assert 'Dual L-function' in L.get_data(as_text=True)
        assert r'\chi_{350} (151, \cdot )' in L.get_data(as_text=True)
        assert r'(2,\ 350,\ (\ :1/2),\ 0.991 - 0.126i)' in L.get_data(as_text=True)
        assert '2.00692' in L.get_data(as_text=True)
        assert '0.127359' in L.get_data(as_text=True)
        assert '1 + 6T + 29T^{2}' in L.get_data(as_text=True)
        assert '1.68486586956382681209348921118' in L.get_data(as_text=True)
        assert '3.10207045712088492456262227600' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/', follow_redirects=True)
        assert 'Modular form 350.2.e.k.151.1' in L.get_data(as_text=True)
        assert 'Modular form 350.2.e.k.51.1' in L.get_data(as_text=True)
        assert 'Modular form 350.2.e.k' in L.get_data(as_text=True)
        assert r'(4,\ 122500,\ (\ :1/2, 1/2),\ 1)' in L.get_data(as_text=True)
        assert '4.04397' in L.get_data(as_text=True)
        assert '1.68486586956382681209348921118' in L.get_data(as_text=True)
        assert '3.10207045712088492456262227600' in L.get_data(as_text=True)
        assert '( 1 + T + p T^{2} )( 1 + 7 T + p T^{2} )' in L.get_data(as_text=True)
        assert '( 1 - 2 T + p T^{2} )^{2}' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/129/2/a/d/', follow_redirects=True)
        assert 'Modular form 129.2.a.d' in L.get_data(as_text=True)
        for i in range(1,4):
            assert 'Modular form 129.2.a.d.1.%d' % i in L.get_data(as_text=True)

        assert '1.04395' in L.get_data(as_text=True)
        assert '( 1 + T )^{3}' in L.get_data(as_text=True)
        assert '1.55341889806322957326786121161' in L.get_data(as_text=True)
        assert r'S_4\times C_2' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/60/2/i/a/', follow_redirects=True)
        assert 'Modular form 60.2.i.a' in L.get_data(as_text=True)
        for c in [17, 53]:
            for i in range(1,3):
                assert 'Modular form 60.2.i.a.%d.%d' % (c,i) in L.get_data(as_text=True), 'Modular form 60.2.%d.a.%d' % (c,i)
        assert '0.676894' in L.get_data(as_text=True)
        assert '2.15777231959226116393597609132' in L.get_data(as_text=True)
        assert '1 - 2 T + 2 T^{2} - 2 p T^{3} + p^{2} T^{4}' in L.get_data(as_text=True)
        assert r'(8,\ 12960000,\ (\ :1/2, 1/2, 1/2, 1/2),\ 1)' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/207/2/i/b/', follow_redirects=True)
        for c in [55,64,73,82,100,118,127,154,163,190]:
            assert 'Modular form 207.2.i.b.%d.1' % c in L.get_data(as_text=True), 'Modular form 207.2.%d.d.1' % c
        assert '0.233961' in L.get_data(as_text=True)
        assert '0.096070203083029088532433951629' in L.get_data(as_text=True)
        assert 'T + T^{2} + 21 T^{3} - 219 T^{4} - 1365 T^{5} - 219 p T^{6} + 21 p^{2} T^{7} + p^{3} T^{8}' in L.get_data(as_text=True)
        assert 'Plot not available' in L.get_data(as_text=True)






    def test_Lhmf(self):
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/', follow_redirects=True)
        assert '0.3599289594' in L.get_data(as_text=True)
        assert '4-775-1.1-c1e2-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/4/775/1.1/c1e2/0/0/', follow_redirects=True)
        assert '3.67899147579' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-9.1-a/0/0/', follow_redirects=True)
        assert '0.22396252' in L.get_data(as_text=True)
        assert '4-24e2-1.1-c1e2-0-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/4/24e2/1.1/c1e2/0/0/', follow_redirects=True)
        assert '3.03882077536' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.24.1/holomorphic/2.2.24.1-1.1-a/0/0/', follow_redirects=True)
        assert '0.28781' in L.get_data(as_text=True)
        assert '4-24e2-1.1-c1e2-0-1' in L.get_data(as_text=True)

    def test_Lgl2maass(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '1 + 4.54845492142i' in L.get_data(as_text=True)
        # FIXME
        # these zeros cannot be correct to this much precision
        # the eigenvalue was computed to lower precision
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '7.8729423429' in L.get_data(as_text=True)
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '5.09874190873i' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '11.614970337' in L.get_data(as_text=True)
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032/')
        assert '1 + 9.53369526135i' in L.get_data(as_text=True)

    def test_Lgl3maass(self):
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/20.39039_14.06890/-0.0742719/', follow_redirects=True)
        assert '0.0742' in L.get_data(as_text=True)
        assert '3-1-1.1-r0e3-p14.07p20.39m34.46-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/3/1/1.1/r0e3/p14.07p20.39m34.46/0/', follow_redirects=True)
        assert '0.9615558824' in L.get_data(as_text=True)

    def test_Lgl4maass(self):
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/', follow_redirects=True)
        assert '4-1-1.1-r0e4-p2.27m6.04m13.14p16.90-0' in L.get_data(as_text=True)
        assert '0.556' in L.get_data(as_text=True)
        assert 'Graph' in L.get_data(as_text=True)
        assert '16.89972715592' in L.get_data(as_text=True)
        assert '4-1-1.1-r0e4-p2.27m6.04m13.14p16.90-0' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/4/1/1.1/r0e4/p2.27m6.04m13.14p16.90/0/')
        assert '16.18901597' in L.get_data(as_text=True)

    def test_Lsym2EC(self):
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/11/a/')
        assert '0.8933960461' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/SymmetricPower/2/EllipticCurve/Q/11/a/')
        assert '4.7345954' in L.get_data(as_text=True)

    def test_Lsym3EC(self):
        L = self.tc.get('/L/SymmetricPower/3/EllipticCurve/Q/11/a/')
        assert '1.140230868' in L.get_data(as_text=True)

    def test_Lsym4EC(self):
        L = self.tc.get('/L/SymmetricPower/4/EllipticCurve/Q/11/a/')
        assert '0.6058003920' in L.get_data(as_text=True)

    def test_LsymHighEC(self):
        L = self.tc.get('/L/SymmetricPower/5/EllipticCurve/Q/11/a/')
        assert '161051' in L.get_data(as_text=True)
        L = self.tc.get('/L/SymmetricPower/6/EllipticCurve/Q/11/a/')
        assert '1771561' in L.get_data(as_text=True)
        L = self.tc.get('/L/SymmetricPower/11/EllipticCurve/Q/11/a/')
        assert '11^{11}' in L.get_data(as_text=True)


    def test_Ldedekind(self):
        L = self.tc.get('/L/NumberField/3.1.23.1/')
        assert '0.2541547348' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/NumberField/3.1.23.1/')
        assert '5.1156833288' in L.get_data(as_text=True)
        L = self.tc.get('/L/NumberField/5.5.2337227518904161.1/')
        assert '3718837' in L.get_data(as_text=True)
        L = self.tc.get('L/NumberField/14.14.28152039412241052225421312.1/')
        assert 'chi_{172}' in L.get_data(as_text=True) and 'chi_{43}' in L.get_data(as_text=True)

    def test_Ldedekindabelian(self):
        L = self.tc.get('/L/NumberField/3.3.81.1/')
        assert 'Graph' in L.get_data(as_text=True)

    def test_Lartin(self):
        L = self.tc.get('/L/ArtinRepresentation/2.23.3t2.1c1/', follow_redirects=True)
        assert '0.1740363269' in L.get_data(as_text=True)
        # same in new labels
        L = self.tc.get('/L/ArtinRepresentation/2.23.3t2.b.a/', follow_redirects=True)
        assert '0.1740363269' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.23.3t2.b.a/', follow_redirects=True)
        assert '5.1156833288' in L.get_data(as_text=True)
        L = self.tc.get('/L/ArtinRepresentation/4.1609.5t5.a.a/', follow_redirects=True)
        assert '0.0755586459' in L.get_data(as_text=True)
        L = self.tc.get('/L/Zeros/ArtinRepresentation/4.1609.5t5.1c1/', follow_redirects=True)
        assert '3.50464340448' in L.get_data(as_text=True)


    def test_Lhgm(self):
        L = self.tc.get('/L/Motive/Hypergeometric/Q/A4_B2.1/t-1.1')
        assert 'Graph' in L.get_data(as_text=True)

    def test_Lgenus2(self):
        L = self.tc.get('/L/Genus2Curve/Q/169/a/', follow_redirects=True)
        assert '0.0904903908' in L.get_data(as_text=True)
        assert '4-13e2-1.1-c1e2-0-0' in L.get_data(as_text=True)
        #assert 'SatoTate' in L.get_data(as_text=True)
        #assert 'E_6' in L.get_data(as_text=True)

        L = self.tc.get('/L/Zeros/4/13e2/1.1/c1e2/0/0/')
        assert '5.0682346354' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/15360/f/', follow_redirects=True)
        assert 'Genus 2 curve 15360.f' in L.get_data(as_text=True)
        assert '4-15360-1.1-c1e2-0-5' in L.get_data(as_text=True)


        L = self.tc.get('/L/Zeros/4/15360/1.1/c1e2/0/5/', follow_redirects=True)
        assert '2.15654793578' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/2457/b/', follow_redirects=True)
        assert 'Elliptic curve 2.0.3.1-273.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.3.1-273.4-a' in L.get_data(as_text=True)
        assert 'Genus 2 curve 2457.b' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/363/a/', follow_redirects=True)
        assert 'Genus 2 curve 363.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 11.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 33.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/360/a/', follow_redirects=True)
        assert 'Genus 2 curve 360.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 15.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 24.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/336/a/', follow_redirects=True)
        assert 'Genus 2 curve 336.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 14.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 24.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/324/a/', follow_redirects=True)
        assert 'Genus 2 curve 324.a' in L.get_data(as_text=True)
        assert 'Modular form 18.2.c.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/294/a/', follow_redirects=True)
        assert 'Genus 2 curve 294.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 14.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 21.' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/256/a/', follow_redirects=True)
        assert 'Genus 2 curve 256.a' in L.get_data(as_text=True)
        assert 'Modular form 16.2.e.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/169/a/', follow_redirects=True)
        assert 'Genus 2 curve 169.a' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a.4.1' in L.get_data(as_text=True)
        assert 'Modular form 13.2.e.a.10.1' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/196/a/', follow_redirects=True)
        assert 'Genus 2 curve 196.a' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 14.a' in L.get_data(as_text=True)
        assert 'Modular form 14.2.a.a' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/576/a/', follow_redirects=True)
        assert 'Hilbert modular form 2.2.8.1-9.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.8.1-9.1-a' in L.get_data(as_text=True)
        assert 'Genus 2 curve 576.a' in L.get_data(as_text=True)
        assert 'Modular form 24.2.d.a' in L.get_data(as_text=True)
        assert 'Modular form 24.2.d.a.13.1' in L.get_data(as_text=True)
        assert 'Modular form 24.2.d.a.13.2' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/20736/i/', follow_redirects=True)
        assert 'Bianchi modular form 2.0.8.1-324.3-a' in L.get_data(as_text=True)
        assert 'Hilbert modular form 2.2.24.1-36.1-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.0.8.1-324.3-a' in L.get_data(as_text=True)
        assert 'Elliptic curve 2.2.24.1-36.1-a' in L.get_data(as_text=True)
        assert 'Genus 2 curve 20736.i' in L.get_data(as_text=True)
        assert 'Origins of factors' in L.get_data(as_text=True)
        assert 'Elliptic curve 36.a' in L.get_data(as_text=True)
        assert 'Elliptic curve 576.f' in L.get_data(as_text=True)
        assert 'Modular form 36.2.a.a' in L.get_data(as_text=True)
        assert 'Modular form 36.2.a.a.1.1' in L.get_data(as_text=True)
        assert 'Modular form 576.2.a.f' in L.get_data(as_text=True)
        assert 'Modular form 576.2.a.f.1.1' in L.get_data(as_text=True)


    def test_Llhash(self):
        r"""
        Checking L/lhash/ pages
        """
        # The hash for /L/EllipticCurve/Q/324016/h
        L = self.tc.get('/L/lhash/1938322253992393114/', follow_redirects=True)
        assert '324016' in L.get_data(as_text=True), "Missing data in /L/lhash/1938322253992393114/"
        assert 'Dual L-function' not in L.get_data(as_text=True)
        assert '2-324016-1.1-c1-0-6' in L.get_data(as_text=True)
        assert 'Elliptic curve 324016.h' in L.get_data(as_text=True)

        L = self.tc.get('/L/lhash/dirichlet_L_6253.458/', follow_redirects=True)
        assert '1.0612' in L.get_data(as_text=True), "Missing data in /L/lhash/dirichlet_L_6253.458/"
        assert '1-6253-6253.458-r1-0-0' in L.get_data(as_text=True)
        assert 'Dual L-function' in L.get_data(as_text=True)
        assert 'Character/Dirichlet/6253/458' in L.get_data(as_text=True)

        L = self.tc.get('/L/Lhash/7200459463482029776252499748763/', follow_redirects=True)
        assert 'Dual L-function' in L.get_data(as_text=True)
        assert 'Modular form 13.4.c.a.3.1' in L.get_data(as_text=True)
        assert 'ModularForm/GL2/Q/holomorphic/13/4/c/a/3/1' in L.get_data(as_text=True)

    def test_tracehash(self):
        L = self.tc.get('/L/tracehash/7200459463482029776252499748763/', follow_redirects=True)
        assert 'trace_hash = 7200459463482029776252499748763 not in [0, 2^61]' in L.get_data(as_text=True)
        L = self.tc.get('/L/tracehash/1938322253992393114/', follow_redirects = True)
        assert '324016' in L.get_data(as_text=True), "Missing data in /L/tracehash/1938322253992393114/"
        assert 'Dual L-function' not in L.get_data(as_text=True)
        assert '2-324016-1.1-c1-0-6' in L.get_data(as_text=True)
        assert 'Elliptic curve 324016.h' in L.get_data(as_text=True)


        L = self.tc.get('/L/tracehash/1127515239490717889/', follow_redirects=True)
        assert 'Elliptic curve 37.a' in L.get_data(as_text=True)
        assert 'Dual L-function' not in L.get_data(as_text=True)

    def test_jump(self):
        self.check_args('/L/?jump=4-167040-1.1-c1e2-0-7', 'Functional equation')
        self.check_args('/L/?jump=3-1-1.1-r0e3-m9.92m29.99p39.92-0', 'Functional equation')
        self.check_args('/L/?jump=2-1.2.1-r0e2-0-4', 'Malformed L-function label')
        self.check_args('/L/?jump=2-1-2.1-r0e2-0-4', 'not found')

    #------------------------------------------------------
    # Testing plots and zeros of L-functions
    #------------------------------------------------------

    def test_LDirichletZeros(self):
        L = self.tc.get('/L/Character/Dirichlet/5/2/', follow_redirects=True)
        assert '6.18357819' in L.get_data(as_text=True)

    def test_LecZeros(self):
        # EC 56.a or MF 56.2.a.a
        L = self.tc.get('/L/Zeros/2/56/1.1/c1/0/0/')
        assert '2.791838' in L.get_data(as_text=True)

    def test_LecPlot(self):
        L = self.tc.get('/L/Plot/2/56/1.1/c1/0/0/')
        assert 'OK' in str(L)

    def test_LcmfPlot(self):
        # ModularForm/GL2/Q/holomorphic/14/6/a/a/
        L = self.tc.get('/L/Plot/2/14/1.1/c5/0/0/')
        assert 'OK' in str(L)

    def test_LartinPlot(self):
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.68.4t3.b.a/')
        assert 'OK' in str(L)

    def test_LHGMZeros(self):
        L = self.tc.get('/L/Zeros/Motive/Hypergeometric/Q/A2.2.2.2_B1.1.1.1/t-1.1/')
        assert '4.497732273' in L.get_data(as_text=True)


    #------------------------------------------------------
    # Testing error messages
    #------------------------------------------------------

    def test_errorMessages(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/5/k/4/a/1/')
        assert 'The requested URL was not found on the server' in L.get_data(as_text=True)

        L = self.tc.get('/L/Character/Dirichlet/9/10/')
        assert 'L-function for dirichlet character with label 9.10 not found' in L.get_data(as_text=True)

        L = self.tc.get('/L/EllipticCurve/Q/11/b/')
        assert 'L-function for elliptic curve isogeny class with label 11.b not found' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/5/6/d/c/')
        assert 'L-function for classical modular form with label 5.6.d.c not found' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.421999/')
        assert 'L-function for modular form ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.421999/ not found' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/2/0/')
        assert 'L-function of Hilbert form of non-trivial character not implemented yet' in L.get_data(as_text=True)

        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.5-a/0/0/')
        assert 'No Hilbert modular form with label' in L.get_data(as_text=True)

        L = self.tc.get('/L/Genus2Curve/Q/247/a/')
        assert 'L-function for genus 2 curve with label 247.a not found' in L.get_data(as_text=True)

        L = self.tc.get('/L/NumberField/2.2.7.1/')
        assert 'No data for the number field' in L.get_data(as_text=True)

        L = self.tc.get('/L/ArtinRepresentation/3.231.4t5.a.a/')
        assert 'Error constructing Artin representation' in L.get_data(as_text=True)

        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/37/d/')
        assert 'No elliptic curve with label ' in L.get_data(as_text=True)

        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/27/a/')
        assert 'This Elliptic curve has complex multiplication and the symmetric power of its L-function is then not primitive.' in L.get_data(as_text=True)


    #------------------------------------------------------
    # Testing units not tested above
    #------------------------------------------------------

    def test_paintSVGall(self):
        svg = paintSvgFileAll([["GSp4", 1]])
        assert "12.4687" in svg

    def test_underlying_data(self):
        data = self.tc.get("/L/data/2-289379-1.1-c1-0-0").get_data(as_text=True)
        assert ("lfunc_lfunctions" in data and "st_group" in data and
                "lfunc_search" in data and "euler19" in data and
                "lfunc_instances" in data and "Lhash_array" in data)
