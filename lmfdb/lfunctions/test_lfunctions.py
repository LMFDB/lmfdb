from Lfunction import RiemannZeta
from LfunctionLcalc import createLcalcfile_ver1
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
        assert '0.4813597784' in L.data and 'mu(9)' in L.data
        assert '2.13818063440820276534' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/3/')
        assert '2.1312850332' in L.data in L.data and 'mu(320)' in L.data
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

    def test_LcalcDirichlet(self):
        L = self.tc.get('L/Character/Dirichlet/19/9/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('L/Character/Dirichlet/6400/3/?download=lcalcfile')
        assert 'lcalc file' in L.data

    def test_Lec(self):
        L = self.tc.get('/L/EllipticCurve/Q/11/a/')
        assert '0.2538418609' in L.data
        assert 'Isogeny class 11.a' in L.data
        assert 'Modular form 11.2a' in L.data
        assert '/SatoTateGroup/1.2.' in L.data

        L = self.tc.get('/L/Zeros/EllipticCurve/Q/11/a/')
        assert '6.362613894713' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/27/a/')
        assert '0.5888795834' in L.data and 'Isogeny class 27.a' in L.data and 'Modular form 27.2a' in L.data and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/27/a/')
        assert '4.043044013797' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/379998/d/')
        assert '9.3643111977' in L.data and 'Isogeny class 379998.d' in L.data and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/379998/d/')
        assert '0.8292065891985' in L.data

        L = self.tc.get('/L/EllipticCurve/2.2.5.1/31.1/a/')
        assert '0.3599289595' in L.data
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
        assert r"Bianchi modular form 2.0.1879.1-1.0.1-a&nbsp;  n/a" in L.data, L.data




    def test_Lemf(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/1/a/0/')
        assert '0.3055149662' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/13/12/1/a/0/')
        assert '1.51472556377' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/7/3/6/a/0/')
        assert '0.3329817715' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/7/3/6/a/0/')
        assert '7.214589181287' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/18/1/a/0/')
        assert '0.27971563' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/1/18/1/a/0/')
        assert '18.17341115038' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/4/3/a/0/')
        assert '0.52375796' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/13/4/3/a/0/')
        assert '2.1369513202' in L.data

    def test_Lhmf(self):
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/')
        assert '0.3599289595' in L.data
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
        assert '1.1402308684' in L.data

    def test_Lsym4EC(self):
        L = self.tc.get('/L/SymmetricPower/4/EllipticCurve/Q/11/a/')
        assert '0.6058003921' in L.data

    def test_LsymHighEC(self):
        L = self.tc.get('/L/SymmetricPower/5/EllipticCurve/Q/11/a/')
        assert '161051' in L.data
        L = self.tc.get('/L/SymmetricPower/6/EllipticCurve/Q/11/a/')
        assert '1771561' in L.data
        L = self.tc.get('/L/SymmetricPower/11/EllipticCurve/Q/11/a/')
        assert '285311670611' in L.data


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
        assert '0.174036327' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.23.3t2.1c1/')
        assert '5.1156833288' in L.data
        L = self.tc.get('/L/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '0.0755586459' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '3.504643404484' in L.data

    def test_Llcalcfile(self):
        L = self.tc.get('/L/ArtinRepresentation/2.2e2_17.4t3.2c1/?download=lcalcfile')
        assert 'lcalc' in L.data

    def test_LlcalcfileEc(self):
        L = self.tc.get('/L/EllipticCurve/Q/56/a/?download=lcalcfile')
        assert 'lcalc' in L.data

    def test_LcalcfileMaass(self):
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.4216864/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/4/1/9.632444_1.374060/0.15012282/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/4/1/8.954662_2.936591/0.36025530/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/-16.4031_-0.17112/-0.4216864/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/4/1/-9.63244_-1.37406/0.15012282/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/4/1/-8.95466_-2.93659/0.36025530/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/1/1/-16.8997_-2.27258_6.035835/0.55659019/?download=lcalcfile')
        assert 'lcalc file' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.4216864/?download=lcalcfile')
        assert 'lcalc file' in L.data

    def test_Lmain(self):
        L = self.tc.get('/L/')
        assert 'Riemann' in L.data and 'Signature' in L.data

    def test_Ldegree1(self):
        L = self.tc.get('/L/degree1/')
        assert 'Dirichlet L-function' in L.data and 'Conductor range' in L.data and 'Primitive Dirichlet character' in L.data

    def test_Ldegree2(self):
        L = self.tc.get('/L/degree2/')
        assert '1.73353' in L.data and '/EllipticCurve/Q/234446.a' in L.data
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

    def test_Llhash(self):
        r"""
        Checking L/lhash/ pages
        """
        # The hash for /L/EllipticCurve/Q/324016/h
        L = self.tc.get('/L/lhash/1938322253992393114/')
        self.assertTrue('324016' in L.data,
                "Missing data in /L/lhash/1938322253992393114/")
        L = self.tc.get('/L/lhash/dirichlet_L_6253.458/')
        self.assertTrue('1.0612' in L.data,
                "Missing data in /L/lhash/dirichlet_L_6253.458/")


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

    def test_LemfPlot(self):
        L = self.tc.get('/L/Plot/ModularForm/GL2/Q/holomorphic/14/6/1/a/0/')
        print str(L)
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
        assert 'Unable to convert parameter' in L.data
        L = self.tc.get('/L/Character/Dirichlet/9/10/')
        assert 'should not exceed the modulus ' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/11/b/')
        assert 'No L-function instance data for' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/5/6/4/c/1/')
        assert 'The specified modular form does not appear to be in the database' in L.data
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

    def test_lcalcfile_ver1(self):
        L = RiemannZeta()
        assert "1" in createLcalcfile_ver1(L)

    def test_paintSVGall(self):
        svg = paintSvgFileAll([["GSp4", 1]])
        assert "12.4687" in svg

    def test_paintSVGholo(self):
        svg = paintSvgHolo(4,6,4,6)
        assert "/L/ModularForm/GL2/Q/holomorphic/4/6/1/a/0" in svg

    def test_paintSVGchar(self):
        svg = paintSvgChar(1,20,1,12)
        assert "/L/Character/Dirichlet/8/5" in svg
