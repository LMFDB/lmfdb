

from base import LmfdbTest
class LfunctionTest(LmfdbTest):
  
  def test_riemann(self):
    L = self.tc.get('/L/Riemann')
    assert 'Functional' in L.data

  def test_LDirichlet(self):
    L = self.tc.get('/L/Character/Dirichlet/35/7')
    assert 'Functional' in L.data

  def test_Lec(self):
    L = self.tc.get('/L/EllipticCurve/Q/11a2')
    assert 'Functional' in L.data

  def test_Lemf(self):
    L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic?weight=12&level=1&character=0&label=a&number=0')
    assert 'Functional' in L.data

  def test_Lgl2maass(self):
    L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000001?db=HT')
    assert 'Functional' in L.data

  def test_Lgl3maass(self):
    L = self.tc.get('/L/ModularForm/GL3/Q/maass?id=GL3Maass_4_19.9942_2.27431')
    assert 'Functional' in L.data

  def test_Lgl4maass(self):
    L = self.tc.get('/L/ModularForm/GL4/Q/maass?id=GL4Maass_1_17.6101_7.81101_-6.0675')
    assert 'Functional' in L.data

  def test_Ldedekind(self):
    L = self.tc.get('/L/NumberField/3.1.23.1')
    assert 'Functional' in L.data

  def test_Lmain(self):
    L = self.tc.get('/L/')
    assert 'Riemann' in L.data

  def test_Ldegree1(self):
    L = self.tc.get('/L/degree1')
    assert 'Dirichlet' in L.data

  def test_Ldegree2(self):
    L = self.tc.get('/L/degree2')
    assert 'Elliptic' in L.data

  def test_Ldegree3(self):
    L = self.tc.get('/L/degree3')
    assert 'Maass' in L.data

  def test_Ldegree4(self):
    L = self.tc.get('/L/degree4')
    assert 'Maass' in L.data



