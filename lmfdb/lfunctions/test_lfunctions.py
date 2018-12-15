from LfunctionPlot import paintSvgHolo, paintSvgChar, paintSvgFileAll
from lmfdb.base import LmfdbTest

class LfunctionTest(LmfdbTest):

    # All tests should pass

    #------------------------------------------------------
    # Testing at least one example of each type of L-function page
    #------------------------------------------------------

    def test_history(self):
        L = self.tc.get('/L/history')
        assert 'Anzahl der Primzahlen' in L.data

    def test_riemann(self):
        L = self.tc.get('/L/Riemann/')
        assert 'Riemann Zeta-function' in L.data

    def test_LDirichlet(self):
        L = self.tc.get('/L/Character/Dirichlet/19/9/')
        assert '0.4813597783' in L.data and 'mu(9)' in L.data
        assert '2.13818063440820276534' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/3/')
        assert '2.131285033' in L.data in L.data and 'mu(320)' in L.data
        assert '3.1381043104275982' in L.data
        L = self.tc.get('/L/Character/Dirichlet/17/16/')
        assert '1.01608483' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/2/')
        assert '2 is not coprime to the modulus 6400' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/6399/')
        assert 'is imprimitive' in L.data
        L = self.tc.get('L/Character/Dirichlet/1000000000/3/')
        assert 'No L-function data' in L.data and 'found in the database' in L.data
        L = self.tc.get('L/Character/Dirichlet/1000000000000000000000/3/')
        assert 'too large' in L.data

    def test_Lec(self):
        L = self.tc.get('/L/EllipticCurve/Q/11/a/')
        assert '0.253841' in L.data
        assert 'Isogeny class 11.a' in L.data
        assert 'Modular form 11.2.a.a' in L.data
        assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/Zeros/EllipticCurve/Q/11/a/')
        assert '6.362613894713' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/27/a/')
        assert '0.5888795834' in L.data
        assert 'Isogeny class 27.a'in L.data
        assert 'Modular form 27.2.a.a' in L.data
        assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/Zeros/EllipticCurve/Q/27/a/')
        assert '4.043044013797' in L.data

        L = self.tc.get('/L/EllipticCurve/Q/379998/d/')
        assert '9.364311197' in L.data and 'Isogeny class 379998.d' in L.data and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/379998/d/')
        assert '0.8292065891985' in L.data

        L = self.tc.get('/L/EllipticCurve/2.2.5.1/31.1/a/')
        assert '0.3599289594' in L.data
        assert 'Isogeny class 2.2.5.1-31.1-a' in L.data
        assert 'Isogeny class 2.2.5.1-31.2-a' in L.data
        assert 'Hilbert modular form 2.2.5.1-31.1-a' in L.data
        assert 'Hilbert modular form 2.2.5.1-31.2-a' in L.data
        assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/EllipticCurve/2.2.5.1/80.1/a/')
        assert '0.5945775518' in L.data
        assert 'Isogeny class 2.2.5.1-80.1-a' in L.data
        assert 'Isogeny class 20.a' in L.data
        assert 'Isogeny class 100.a' in L.data
        assert 'Hilbert modular form 2.2.5.1-80.1-a' in L.data
        assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/EllipticCurve/2.0.11.1/256.1/a/')
        assert 'Isogeny class 2.0.11.1-256.1-a' in L.data
        assert 'Isogeny class 2.0.11.1-256.1-b' in L.data
        assert 'Isogeny class 2.2.44.1-16.1-a' in L.data
        assert 'Isogeny class 2.2.44.1-16.1-c' in L.data
        assert 'Hilbert modular form 2.2.44.1-16.1-a' in L.data
        assert 'Hilbert modular form 2.2.44.1-16.1-c' in L.data
        assert 'Bianchi modular form 2.0.11.1-256.1-a' in L.data
        assert 'Bianchi modular form 2.0.11.1-256.1-b' in L.data
        assert '/SatoTateGroup/1.2.' in L.data


        L = self.tc.get('/L/EllipticCurve/2.0.1879.1/1.0.1/a/')
        assert '/SatoTateGroup/1.2.' in L.data
        assert 'Isogeny class 2.0.1879.1-1.0.1-a' in L.data
        assert "(Bianchi modular form 2.0.1879.1-1.0.1-a)" in L.data, L.data

        L = self.tc.get('/L/EllipticCurve/2.0.4.1/100.2/a/')
        assert '/SatoTateGroup/1.2.' in L.data
        assert '0.5352579714' in L.data
        assert 'Bianchi modular form 2.0.4.1-100.2-a' in L.data
        assert 'Isogeny class 2.0.4.1-100.2-a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 20.a' in L.data
        assert 'Isogeny class 80.b' in L.data
        assert 'Modular form 20.2.a.a' in L.data
        assert 'Modular form 80.2.a.b' in L.data
        # check the zeros accross factors
        assert '2.76929890617261215013507568311' in L.data
        assert '4.78130792717525308450176413839' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/20/2/a/a/')
        assert '4.78130792717525308450176413839' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/20/a/')
        assert '4.781307927175253' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/80/2/a/b/')
        assert '2.76929890617261215013507568311' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/80/b/')
        assert '2.769298906172612' in L.data



        L = self.tc.get('/L/EllipticCurve/2.0.3.1/75.1/a/')
        assert 'Bianchi modular form 2.0.3.1-75.1-a' in L.data
        assert 'Isogeny class 2.0.3.1-75.1-a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 15.a' in L.data
        assert 'Isogeny class 45.a' in L.data
        assert 'Modular form 15.2.a.a' in L.data
        assert 'Modular form 45.2.a.a' in L.data

        L = self.tc.get('/L/EllipticCurve/2.0.8.1/2592.3/c/')
        assert 'Bianchi modular form 2.0.8.1-2592.3-c' in L.data
        assert 'Hilbert modular form 2.2.8.1-2592.1-f' in L.data
        assert 'Isogeny class 2.0.8.1-2592.3-c' in L.data
        assert 'Isogeny class 2.2.8.1-2592.1-f' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 288.a' in L.data
        assert 'Isogeny class 576.i' in L.data
        assert 'Modular form 288.2.a.a' in L.data





    def test_Lcmf(self):
        # check the zeros agree across 3 instances
        L = self.tc.get('/L/Zeros/EllipticCurve/2.0.11.1/11.1/a/')
        assert '6.36261389471308870138602900888' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/11/2/a/a/')
        assert '6.36261389471308870138602900888' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/11/a/')
        assert '6.36261389471308' in L.data



        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/a/a/1/1/')
        assert '4.84e4' in L.data # a_7
        assert '71.7' in L.data # a_2
        assert '1.51472556377341264746894823521' in L.data # first zero

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/a/a/')
        assert '1.51472556377341264746894823521' in L.data # first zero
        assert 'Origins of factors' in L.data
        for i in range(1,6):
            assert 'Modular form 13.12.a.a.1.%d' % i  in L.data
        assert '371293' in L.data # L_3 root
        assert '1856465' in L.data # a_13


        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/7/3/b/a/')
        assert '0.332981' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/7/3/b/a/')
        assert '7.21458918128718444354242474222' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/18/a/a/')
        assert '1341682069728' in L.data # a26
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/1/18/a/a/')
        assert '18.17341115038590061946085869072' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/4/c/a/3/1/')
        assert '0.523757' in L.data and '0.530517' in L.data
        assert '(16 + 27.7<em>i</em>)' in L.data
        assert 'Dual L-function' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/13/4/c/a/3/1/')
        assert '5.68016097036963500634962429051' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/a/a/')
        assert '0.253841' in L.data
        assert 'Isogeny class 11.a' in L.data
        assert 'Modular form 11.2.a.a' in L.data
        #FIXME merge with EC to get sato-tate
        #assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/2/e/a/')
        assert 'Isogeny class 169.a' in L.data
        assert 'Modular form 13.2.e.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Modular form 13.2.e.a.4.1' in L.data
        assert 'Modular form 13.2.e.a.10.1' in L.data
        #FIXME merge with G2C to get sato-tate
        #assert '/SatoTateGroup/1.4.E_6' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/18/2/c/a/')
        assert 'Isogeny class 324.a' in L.data
        assert 'Modular form 18.2.c.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Modular form 18.2.c.a.7.1' in L.data
        assert 'Modular form 18.2.c.a.13.1' in L.data
        #FIXME merge with G2C to get sato-tate
        #assert '/SatoTateGroup/1.4.E_3' in L.data


        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/490/2/a/a/')
        assert 'Modular form 490.2.a.a' in L.data
        assert 'Isogeny class 490.a' in L.data
        assert '0.729971' in L.data
        assert '(2,\ 490,\ (\ :1/2),\ 1)' in L.data
        assert '0.940863335931152039286421559408' in L.data
        assert '1+7T+ p T^{2}' in L.data
        assert '\chi_{490} (1, \cdot )' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/490/a/')
        assert '0.9408633359311520' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/51/1/')
        assert 'Modular form 350.2.e.k.51.1' in L.data
        assert 'Dual L-function' in L.data
        assert '/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/151/1/'
        assert '\chi_{350} (51, \cdot )' in L.data
        assert '(2,\ 350,\ (\ :1/2),\ 0.991 + 0.126i)' in L.data
        assert '2.00692' in L.data
        assert '0.127359' in L.data
        assert '$1 + 6T + 29T^{2}$' in L.data
        assert '1.68486586956382681209348921118' in L.data
        assert '3.10207045712088492456262227600' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/151/1/')
        assert 'Modular form 350.2.e.k.151.1' in L.data
        assert 'Dual L-function' in L.data
        assert '/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/51/1/'
        assert '\chi_{350} (151, \cdot )' in L.data
        assert '(2,\ 350,\ (\ :1/2),\ 0.991 - 0.126i)' in L.data
        assert '2.00692' in L.data
        assert '0.127359' in L.data
        assert '$1 + 6T + 29T^{2}$' in L.data
        assert '1.68486586956382681209348921118' in L.data
        assert '3.10207045712088492456262227600' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/350/2/e/k/')
        assert 'Modular form 350.2.e.k.151.1' in L.data
        assert 'Modular form 350.2.e.k.51.1' in L.data
        assert 'Modular form 350.2.e.k' in L.data
        assert '(4,\ 122500,\ (\ :1/2, 1/2),\ 1)' in L.data
        assert '4.04397' in L.data
        assert '1.68486586956382681209348921118' in L.data
        assert '3.10207045712088492456262227600' in L.data
        assert '(1+T+ p T^{2})(1+7T+ p T^{2})' in L.data
        assert '(1-2T+ p T^{2})^{2}' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/129/2/a/d/')
        assert 'Modular form 129.2.a.d' in L.data
        for i in range(1,4):
            assert 'Modular form 129.2.a.d.1.%d' % i in L.data

        assert '1.04395' in L.data
        assert '(1+T)^{3}' in L.data
        assert '1.55341889806322957326786121161' in L.data
        assert r'S_4\times C_2' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/60/2/i/a/')
        assert 'Modular form 60.2.i.a' in L.data
        for c in [17, 53]:
            for i in range(1,3):
                assert 'Modular form 60.2.i.a.%d.%d' % (c,i) in L.data, 'Modular form 60.2.%d.a.%d' % (c,i)
        assert '0.676894' in L.data
        assert '2.15777231959226116393597609132' in L.data
        assert '$1-2T+2T^{2}-2 p T^{3}+ p^{2} T^{4}$' in L.data
        assert '(8,\ 12960000,\ (\ :1/2, 1/2, 1/2, 1/2),\ 1)' in L.data

        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/207/2/i/b/')
        for c in [55,64,73,82,100,118,127,154,163,190]:
            assert 'Modular form 207.2.i.b.%d.1' % c in L.data, 'Modular form 207.2.%d.d.1' % c
        assert '0.233961' in L.data
        assert '0.096070203083029088532433951629' in L.data
        assert '$1-T+T^{2}+21T^{3}-219T^{4}-1365T^{5}-219 p T^{6}+21 p^{2} T^{7}+ p^{3} T^{8}- p^{4} T^{9}+ p^{5} T^{10}$' in L.data
        assert 'Plot not available' in L.data






    def test_Lhmf(self):
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/')
        assert '0.3599289594' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/')
        assert '3.67899147579' in L.data
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-9.1-a/0/0/')
        assert '0.22396252' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-9.1-a/0/0/')
        assert '3.03882077536' in L.data
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.24.1/holomorphic/2.2.24.1-1.1-a/0/0/')
        assert '0.28781' in L.data

    def test_Lgl2maass(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '1 + 4.54845492142i' in L.data
        # FIXME
        # these zeros cannot be correct to this much precision
        # the eigenvalue was computed to lower precision
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '7.8729423429' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '5.09874190873i' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '11.614970337' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032/')
        assert '1 + 9.53369526135i' in L.data

    def test_Lgl3maass(self):
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/20.39039_14.06890/-0.0742719/')
        assert '0.0742' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL3/Q/Maass/1/1/20.39039_14.06890/-0.0742719/')
        assert '0.9615558824' in L.data

    def test_Lgl4maass(self):
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/')
        assert '0.556' in L.data
        assert 'Graph' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/')
        assert '16.18901597' in L.data

    def test_Lsym2EC(self):
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/11/a/')
        assert '0.8933960461' in L.data
        L = self.tc.get('/L/Zeros/SymmetricPower/2/EllipticCurve/Q/11/a/')
        assert '4.7345954' in L.data

    def test_Lsym3EC(self):
        L = self.tc.get('/L/SymmetricPower/3/EllipticCurve/Q/11/a/')
        assert '1.140230868' in L.data

    def test_Lsym4EC(self):
        L = self.tc.get('/L/SymmetricPower/4/EllipticCurve/Q/11/a/')
        assert '0.6058003920' in L.data

    def test_LsymHighEC(self):
        L = self.tc.get('/L/SymmetricPower/5/EllipticCurve/Q/11/a/')
        assert '161051' in L.data
        L = self.tc.get('/L/SymmetricPower/6/EllipticCurve/Q/11/a/')
        assert '1771561' in L.data
        L = self.tc.get('/L/SymmetricPower/11/EllipticCurve/Q/11/a/')
        assert '11^{11}' in L.data


    def test_Ldedekind(self):
        L = self.tc.get('/L/NumberField/3.1.23.1/')
        assert '0.2541547348' in L.data
        L = self.tc.get('/L/Zeros/NumberField/3.1.23.1/')
        assert '5.1156833288' in L.data
        L = self.tc.get('/L/NumberField/5.5.2337227518904161.1/')
        assert '3718837' in L.data
        L = self.tc.get('L/NumberField/14.14.28152039412241052225421312.1/')
        assert 'chi_{172}' in L.data and 'chi_{43}' in L.data

    def test_Ldedekindabelian(self):
        L = self.tc.get('/L/NumberField/3.3.81.1/')
        assert 'Graph' in L.data

    def test_Lartin(self):
        L = self.tc.get('/L/ArtinRepresentation/2.23.3t2.1c1/', follow_redirects=True)
        assert '0.1740363269' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.23.3t2.1c1/')
        assert '5.1156833288' in L.data
        L = self.tc.get('/L/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '0.0755586459' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '3.504643404484' in L.data

    def test_Lmain(self):
        L = self.tc.get('/L/')
        assert 'Riemann' in L.data and 'Signature' in L.data

    def test_Ldegree1(self):
        L = self.tc.get('/L/degree1/')
        assert 'Dirichlet L-function' in L.data and 'Conductor range' in L.data and 'Primitive Dirichlet character' in L.data

    def test_Ldegree2(self):
        L = self.tc.get('/L/degree2/')
        assert '1.73353' in L.data and '/EllipticCurve/Q/234446/a' in L.data
        assert '17.02494' in L.data and '/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032' in L.data

    def test_Ldegree3(self):
        L = self.tc.get('/L/degree3/')
        assert '6.42223' in L.data and '/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.4216864' in L.data

    def test_Ldegree4(self):
        L = self.tc.get('/L/degree4/')
        assert '5.06823' in L.data and '/Genus2Curve/Q/169/a/' in L.data
        assert '16.18901' in L.data and '2.272' in L.data and '/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019' in L.data

    def test_LdegreeLarge(self):
        L = self.tc.get('L/degree1234567689/')
        assert 'no L-function data available' in L.data

    def test_Ldegree2CuspForm(self):
        L = self.tc.get('/L/degree2/CuspForm/')
        assert 'trivial character' in L.data

    def test_Ldegree2MaassForm(self):
        L = self.tc.get('/L/degree2/MaassForm/')
        assert 'Maass' in L.data

    def test_Ldegree2EllipticCurve(self):
        L = self.tc.get('/L/degree2/EllipticCurve/')
        assert 'Elliptic' in L.data

    def test_Ldegree3MaassForm(self):
        L = self.tc.get('/L/degree3/r0r0r0/')
        assert 'equation' in L.data

    def test_Ldegree3EllipticCurve(self):
        L = self.tc.get('/L/degree3/EllipticCurve/SymmetricSquare/')
        assert 'Elliptic' in L.data

    def test_Ldegree4MaassForm(self):
        L = self.tc.get('/L/degree4/r0r0r0r0/')
        assert 'functional' in L.data

    def test_Ldegree4EllipticCurve(self):
        L = self.tc.get('/L/degree4/EllipticCurve/SymmetricCube/')
        assert 'Elliptic' in L.data

    def test_Lhgm(self):
        L = self.tc.get('/L/Motive/Hypergeometric/Q/A4_B2.1/t-1.1')
        assert 'Graph' in L.data

    def test_Lgenus2(self):
        L = self.tc.get('/L/Genus2Curve/Q/169/a/')
        assert '0.0904903908' in L.data and 'E_6' in L.data

        L = self.tc.get('/L/Zeros/Genus2Curve/Q/169/a/')
        assert '5.06823463541' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/15360/f/')
        assert 'Isogeny class 15360.f' in L.data

        L = self.tc.get('/L/Zeros/Genus2Curve/Q/15360/f/')
        assert '2.15654793578' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/2457/b/')
        assert 'Isogeny class 2.0.3.1-273.1-a' in L.data
        assert 'Isogeny class 2.0.3.1-273.4-a' in L.data
        assert 'Isogeny class 2457.b' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/363/a/')
        assert 'Isogeny class 363.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 11.a' in L.data
        assert 'Isogeny class 33.a' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/360/a/')
        assert 'Isogeny class 360.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 15.a' in L.data
        assert 'Isogeny class 24.a' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/336/a/')
        assert 'Isogeny class 336.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 14.a' in L.data
        assert 'Isogeny class 24.a' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/324/a/')
        assert 'Isogeny class 324.a' in L.data
        assert 'Modular form 18.2.c.a' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/294/a/')
        assert 'Isogeny class 294.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 14.a' in L.data
        assert 'Isogeny class 21.' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/256/a/')
        assert 'Isogeny class 256.a' in L.data
        assert 'Modular form 16.2.e.a' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/169/a/')
        assert 'Isogeny class 169.a' in L.data
        assert 'Modular form 13.2.e.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Modular form 13.2.e.a.4.1' in L.data
        assert 'Modular form 13.2.e.a.10.1' in L.data

        L = self.tc.get('/L/Genus2Curve/Q/196/a/')
        assert 'Isogeny class 196.a' in L.data
        assert 'Origins of factors' in L.data
        assert 'Isogeny class 14.a' in L.data
        assert 'Modular form 14.2.a.a' in L.data

    def test_Llhash(self):
        r"""
        Checking L/lhash/ pages
        """
        # The hash for /L/EllipticCurve/Q/324016/h
        L = self.tc.get('/L/lhash/1938322253992393114/')
        assert '324016' in L.data, "Missing data in /L/lhash/1938322253992393114/"
        assert 'Dual L-function' not in L.data
        assert '/L/EllipticCurve/Q/324016/h' in L.data

        L = self.tc.get('/L/lhash/dirichlet_L_6253.458/')
        assert '1.0612' in L.data, "Missing data in /L/lhash/dirichlet_L_6253.458/"
        assert """Dirichlet Character \(\chi_{%s} (%s, \cdot) \)""" % (6253,458) in L.data,\
                "Missing origin in /L/lhash/dirichlet_L_6253.458/"
        assert 'Dual L-function' in L.data
        assert '/L/Character/Dirichlet/6253/2635' in L.data
        assert '/L/Character/Dirichlet/6253/458' in L.data # self

        L = self.tc.get('/L/Lhash/7200459463482029776252499748763/')
        assert 'Dual L-function' in L.data
        assert 'Modular form 13.4.c.a.3.1' in L.data
        assert '/L/ModularForm/GL2/Q/holomorphic/13/4/c/a/3/1' in L.data

    def test_tracehash(self):
        L = self.tc.get('/L/tracehash/7200459463482029776252499748763/')
        assert 'trace_hash = 7200459463482029776252499748763 not in [0, 2^61]' in L.data
        L = self.tc.get('/L/tracehash/1938322253992393114/', follow_redirects = True)
        assert '324016' in L.data, "Missing data in /L/tracehash/1938322253992393114/"
        assert 'Dual L-function' not in L.data


        L = self.tc.get('/L/tracehash/1127515239490717889/', follow_redirects = True)
        assert 'Isogeny class 37.a' in L.data
        assert 'Dual L-function' not in L.data


    #------------------------------------------------------
    # Testing plots and zeros of L-functions
    #------------------------------------------------------

    def test_riemannPlot(self):
        L = self.tc.get('/L/Plot/Riemann/')
        assert 'OK' in str(L)

    def test_LDirichletZeros(self):
        L = self.tc.get('/L/Zeros/Character/Dirichlet/5/2/')
        assert '6.18357819' in L.data

    def test_LecZeros(self):
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/56/a/')
        assert '2.791838' in L.data

    def test_LcmfPlot(self):
        L = self.tc.get('/L/Plot/ModularForm/GL2/Q/holomorphic/14/6/a/a/')
        assert 'OK' in str(L)

    def test_LartinPlot(self):
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.2e2_17.4t3.2c1/')
        assert 'OK' in str(L)

    def test_LecPlot(self):
        L = self.tc.get('/L/Plot/EllipticCurve/Q/56/a/')
        assert 'OK' in str(L)

    def test_LHGMZeros(self):
        L = self.tc.get('/L/Zeros/Motive/Hypergeometric/Q/A2.2.2.2_B1.1.1.1/t-1.1/')
        assert '4.497732273' in L.data


    #------------------------------------------------------
    # Testing error messages
    #------------------------------------------------------

    def test_errorMessages(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/5/k/4/a/1/')
        assert 'The requested URL was not found on the server' in L.data
        L = self.tc.get('/L/Character/Dirichlet/9/10/')
        assert 'should not exceed the modulus ' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/11/b/')
        assert 'No L-function instance data for' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/5/6/d/c/')
        assert 'No L-function instance data for "ModularForm/GL2/Q/holomorphic/5/6/d/c" was found in the database.' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.421999/')
        assert 'No L-function instance data for' in L.data
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/2/0/')
        assert 'L-function of Hilbert form of non-trivial character not implemented yet' in L.data
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.5-a/0/0/')
        assert 'No Hilbert modular form with label' in L.data
        L = self.tc.get('/L/Genus2Curve/Q/247/a/')
        assert 'No L-function instance data for' in L.data
        L = self.tc.get('/L/NumberField/2.2.7.1/')
        assert 'No data for the number field' in L.data
        L = self.tc.get('/L/ArtinRepresentation/3.231.4t5.1c1/')
        assert 'Error constructing Artin representation' in L.data
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/37/d/')
        assert 'No elliptic curve with label ' in L.data
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/27/a/')
        assert 'This Elliptic curve has complex multiplication and the symmetric power of its L-function is then not primitive.' in L.data


    #------------------------------------------------------
    # Testing units not tested above
    #------------------------------------------------------

    def test_paintSVGall(self):
        svg = paintSvgFileAll([["GSp4", 1]])
        assert "12.4687" in svg

    #FIXME
    #def test_paintSVGholo(self):
    #    svg = paintSvgHolo(4,6,4,6)
    #    assert "L/ModularForm/GL2/Q/holomorphic/4/6/1/a/1/" in svg
    assert paintSvgHolo # pyflakes

    def test_paintSVGchar(self):
        svg = paintSvgChar(1,20,1,12)
        assert "/L/Character/Dirichlet/8/5" in svg
