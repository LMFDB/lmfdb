# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest

class LfunctionTest(LmfdbTest):

    def test_main(self):
        L = self.tc.get('/L/')
        assert 'Browse' in L.data and 'Dirichlet L-function' in L.data and 'GL4 Maass form' in L.data  and 'Holomorphic cusp form' in L.data
        
    def test_degree(self):
        L = self.tc.get('/L/degree1/')
        assert 'Dirichlet L-function' in L.data and 'Conductor range' in L.data and 'Primitive Dirichlet character' in L.data
        L = self.tc.get('/L/degree2/')
        assert '1.73353' in L.data and '/EllipticCurve/Q/234446.a' in L.data
        assert '17.02494' in L.data and '/ModularForm/GL2/Q/Maass/4cb8503a58bca91458000032' in L.data
        L = self.tc.get('/L/degree3/')
        assert '6.42223' in L.data and '/ModularForm/GL3/Q/Maass/1/1/16.40312_0.171121/-0.4216864' in L.data
        L = self.tc.get('/L/degree4/')
        assert '5.06823' in L.data and '/Genus2Curve/Q/169/a/' in L.data
        assert '16.18901' in L.data and '2.272' in L.data and '/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019' in L.data
        L = self.tc.get('L/degree1234567689/')
        assert 'no L-function data available' in L.data
    
    def test_dirichlet(self):
        L = self.tc.get('/L/Character/Dirichlet/19/9/')
        assert '0.4813597784' in L.data and 'mu(9)' in L.data
        L = self.tc.get('/L/Zeros/Character/Dirichlet/19/9/')
        assert '2.13818063440820276534' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/3/')
        assert '2.1312850332' in L.data in L.data and 'mu(320)' in L.data
        L = self.tc.get('/L/Zeros/Character/Dirichlet/6400/3/')
        assert '3.1381043104275982' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/2/')
        assert '2 is not coprime to the modulus 6400' in L.data
        L = self.tc.get('/L/Character/Dirichlet/6400/6399/')
        assert 'is imprimitive' in L.data
        L = self.tc.get('L/Character/Dirichlet/1000000000/3/')
        assert 'No L-function data' in L.data and 'found in the database' in L.data
        L = self.tc.get('L/Character/Dirichlet/1000000000000000000000/3/')
        assert 'too large' in L.data

    def test_ec(self):
        L = self.tc.get('/L/EllipticCurve/Q/11.a/')
        assert '0.2538418609' in L.data and 'Isogeny class 11.a' in L.data and 'Modular form 11.2a' in L.data and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/11.a/')
        assert '6.362613894713' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/27.a/')
        assert '0.5888795834' in L.data and 'Isogeny class 27.a' in L.data and 'Modular form 27.2a' in L.data and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/27.a/')
        assert '4.043044013797' in L.data
        L = self.tc.get('/L/EllipticCurve/Q/379998.d/')
        assert '9.3643111977' in L.data in L.data and 'Isogeny class 379998.d' and '/SatoTateGroup/1.2.' in L.data
        L = self.tc.get('/L/Zeros/EllipticCurve/Q/379998.d/')
        assert '0.8292065891985' in L.data

    def test_classical_mf(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/13/12/1/a/0/')
        assert '0.3055149662' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/13/12/1/a/0/')
        assert '1.51472556377' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/7/3/6/a/0/')
        assert '0.3329817715' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/holomorphic/7/3/6/a/0/')
        assert '7.214589181287' in L.data
        
        
    def test_maass(self):
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '4.548454921423' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f5695df88aece2afe000021/')
        assert '7.872942342977' in L.data
        L = self.tc.get('/L/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '5.0987419087' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/Q/Maass/4f55571b88aece241f000013/')
        assert '11.6149703378' in L.data
        L = self.tc.get('/L/ModularForm/GL3/Q/Maass/1/1/20.39039_14.06890/-0.0742719/')
        assert '0.07427197998156' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL3/Q/Maass/1/1/20.39039_14.06890/-0.0742719/')
        assert '0.9615558824' in L.data
        L = self.tc.get('/L/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/')
        assert '0.55659019311' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL4/Q/Maass/1/1/16.89972_2.272587_-6.03583/0.55659019/')        
        assert '16.18901597' in L.data
        
    def test_dedekind_zeta(self):
        L = self.tc.get('/L/NumberField/3.1.23.1/')
        assert '0.2541547348' in L.data
        L = self.tc.get('/L/Zeros/NumberField/3.1.23.1/')
        assert '5.1156833288' in L.data
        L = self.tc.get('/L/NumberField/5.5.2337227518904161.1/')
        assert '3718837' in L.data
        L = self.tc.get('L/NumberField/14.14.28152039412241052225421312.1/')
        assert 'chi_{172}' in L.data and 'chi_{43}' in L.data

    def test_artin(self):
        L = self.tc.get('/L/ArtinRepresentation/2.23.3t2.1c1/', follow_redirects=True)
        assert '0.174036327' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/2.23.3t2.1c1/')
        assert '5.1156833288' in L.data
        L = self.tc.get('/L/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '0.0755586459' in L.data
        L = self.tc.get('/L/Zeros/ArtinRepresentation/4.1609.5t5.1c1/')
        assert '3.504643404484' in L.data
        
        
    def test_sym_powers(self):
        L = self.tc.get('/L/SymmetricPower/2/EllipticCurve/Q/11.a/')
        assert '0.8933960461' in L.data
        L = self.tc.get('/L/SymmetricPower/3/EllipticCurve/Q/11.a/')
        assert '1.1402308684' in L.data
        L = self.tc.get('/L/SymmetricPower/4/EllipticCurve/Q/11.a/')
        assert '0.6058003921' in L.data
        L = self.tc.get('/L/SymmetricPower/5/EllipticCurve/Q/11.a/')
        assert '1.1434943586' in L.data
        L = self.tc.get('/L/SymmetricPower/6/EllipticCurve/Q/11.a/')
        assert '1.1814669745' in L.data

    def test_hmf(self):
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/')
        assert '0.3599289595' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/TotallyReal/2.2.5.1/holomorphic/2.2.5.1-31.1-a/0/0/')
        assert '3.67899147579' in L.data
        L = self.tc.get('/L/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-9.1-a/0/0/')
        assert '0.22396252' in L.data
        L = self.tc.get('/L/Zeros/ModularForm/GL2/TotallyReal/2.2.8.1/holomorphic/2.2.8.1-9.1-a/0/0/')
        assert '3.03882077536' in L.data
        

    def test_genus2(self):
        L = self.tc.get('/L/Genus2Curve/Q/169/a/')
        assert '0.0904903908' in L.data and 'E_6' in L.data
        L = self.tc.get('/L/Zeros/Genus2Curve/Q/169/a/')
        assert '5.06823463541' in L.data
        L = self.tc.get('/L/Genus2Curve/Q/15360/f/')
        assert 'Isogeny class 15360.f' in L.data
        L = self.tc.get('/L/Zeros/Genus2Curve/Q/15360/f/')
        assert '2.15654793578' in L.data
    