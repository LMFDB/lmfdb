from lfunctions.Lfunction import *
from lfunctions.LfunctionPlot import *
from lfunctions.Lfunctionutilities import *
from lfunctions.LfunctionLcalc import createLcalcfile_ver1
from base import LmfdbTest
import math
import unittest2
from modular_forms.elliptic_modular_forms import emf_logger
emf_logger.setLevel(100)


class LfunctionTest(LmfdbTest):

    # All tests should pass

    #------------------------------------------------------
    # Testing one example of each type of L-function page
    #------------------------------------------------------

    def test_riemann(self):
        L = self.tc.get('/L/Riemann/')
        assert 'Graph' in L.data

    def test_LDirichlet(self):
        L = self.tc.get('/L/Character/Dirichlet/5/2/')
        assert 'Graph' in L.data

    def test_Lec(self):
        L = self.tc.get('/L/EllipticCurve/Q/56.a/')
        assert 'Graph' in L.data
        assert '/ModularForm/GL2/Q/holomorphic/56/2/1/a/' in L.data

    def test_Lemf(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/1/a/0/')
        assert 'Graph' in L.data

    def test_Lgl2maass(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert 'Graph' in L.data

    def test_Lhmf(self):
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-36.1-a/0/0/')
        assert 'Graph' in L.data

    def test_Lgl3maass(self):
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/GL3Maass_4_19.9942_2.27431/')
        assert 'Graph' in L.data

    def test_Lsym2EC(self):
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/11.a/')
        assert 'Graph' in L.data

    def test_Lsym3EC(self):
        L = self.tc.get('/L/SymmetricPower/3/EllipticCurve/Q/11.a/')
        assert 'Graph' in L.data

    def test_Lgl4maass(self):
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/GL4Maass_1_17.6101_7.81101_-6.0675/')
        assert 'Graph' in L.data

    def test_Ldedekind(self):
        L = self.tc.get('/L/NumberField/3.1.23.1/')
        assert 'Graph' in L.data

    def test_Ldedekindabelian(self):
        L = self.tc.get('/L/NumberField/3.3.81.1/')
        assert 'Graph' in L.data

    def test_Lartin(self):
        L = self.tc.get('/L/ArtinRepresentation/2.2e2_17.4t3.2c1/')
        assert 'Graph' in L.data

    def test_Llcalcfile(self):
        L = self.tc.get('/L/ArtinRepresentation/2.2e2_17.4t3.2c1/?download=lcalcfile')
        assert 'lcalc' in L.data

    def test_LlcalcfileEc(self):
        L = self.tc.get('/L/EllipticCurve/Q/56.a/?download=lcalcfile')
        assert 'lcalc' in L.data

    def test_Lmain(self):
        L = self.tc.get('/L/')
        assert 'Riemann' in L.data

    def test_Ldegree1(self):
        L = self.tc.get('/L/degree1/')
        assert 'Dirichlet' in L.data

    def test_Ldegree2(self):
        L = self.tc.get('/L/degree2/')
        assert 'Elliptic' in L.data

    def test_Ldegree3(self):
        L = self.tc.get('/L/degree3/')
        assert 'Maass' in L.data

    def test_Ldegree4(self):
        L = self.tc.get('/L/degree4/')
        assert 'Maass' in L.data

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
        L = self.tc.get('/L/degree3/MaassForm/')
        assert 'Maass' in L.data

    def test_Ldegree3EllipticCurve(self):
        L = self.tc.get('/L/degree3/EllipticCurve/SymmetricSquare/')
        assert 'Elliptic' in L.data

    def test_Ldegree4MaassForm(self):
        L = self.tc.get('/L/degree4/MaassForm/')
        assert 'Maass' in L.data

    def test_Ldegree4EllipticCurve(self):
        L = self.tc.get('/L/degree4/EllipticCurve/SymmetricCube/')
        assert 'Elliptic' in L.data

    def test_Lhgm(self):
        L = self.tc.get('/L/Motive/Hypergeometric/Q/A2_B1/t-2.3') # To be moved eventually
        assert 'Graph' in L.data

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
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/56.a/')
        assert '2.791838' in L.data

    def test_LemfPlot(self):
        #L = self.tc.get('/L/Plot/ModularForm/GL2/Q/holomorphic/10/3/1/a/0/')
        # The modular form above does not exist in current labelling
        L = self.tc.get('/L/Plot/ModularForm/GL2/Q/holomorphic/14/6/1/a/0/')
        print str(L)
        assert 'OK' in str(L)

    def test_LdedekindZeros(self):
        L = self.tc.get('/L/Zeros/NumberField/3.1.23.1/')
        assert '5.1156833288' in L.data

    def test_LartinPlot(self):
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.2e2_17.4t3.2c1/')
        assert 'OK' in str(L)

    def test_LecPlot(self):
        L = self.tc.get('/L/Plot/EllipticCurve/Q/56.a/')
        assert 'OK' in str(L)

    def test_LHGMZeros(self):
        L = self.tc.get('/L/Zeros/Motive/Hypergeometric/Q/A2.2.2.2_B1.1.1.1_t1.2/')
        assert '4.307350233' in L.data


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

    # To quote from the function number_of_coefficients_needed() in
    # lfunctions/Lfunctionutilities.py: "This doesn't work. Trouble
    # when computing t0. We completely mimic what lcalc does when it
    # decides whether to print a warning."

    # def test_number_of_coefficients_needed(self):
    #     nr = number_of_coefficients_needed(1 / sqrt(math.pi), [0.5], [0], 50)
    #     print nr
    #     assert nr > 10
