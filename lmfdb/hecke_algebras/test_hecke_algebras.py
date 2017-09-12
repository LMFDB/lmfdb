# -*- coding: utf-8 -*-

from lmfdb.base import LmfdbTest

class HomePageTest(LmfdbTest):

    def check(self,homepage,path,text):
        assert path in homepage
        assert text in self.tc.get(path).data

    def check_external(self, homepage, path, text):
        import urllib2
        assert path in homepage
        assert text in urllib2.urlopen(path).read()

    # Hecke algebra browse page
    def test_hecke_algebra(self):
        homepage = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/").data
        assert 'Hecke Algebras' in homepage
        assert '139.2.1' in homepage or "not yet available" in homepage

    # Hecke algebra single page
    def test_hecke_algebra_one(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?label=139.2.1").data
        assert '2145245897' in L 
        assert 'T_{ 4} =\left' in L 

    # Hecke algebra l-adic  page
    def test_hecke_algebra_classnumber(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/139.2.1.2/2").data
        assert 'Gorenstein' in L
        assert 'x^3 + x + 1' in L

    # Search no orbit
    def test_hecke_algebra_search(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?start=0&level=&weight=2&num_orbits=2&orbit_label=&ell=&count=50").data
        assert '86' in L 

    def test_hecke_algebra_search_next(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?start=50&level=&weight=&num_orbits=5&orbit_label=&ell=&count=50").data
        assert '222.2.1' in L
        
            
    # Search with l
    def test_hecke_algebra_search_with_l(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?start=50&level=1-100&weight=&num_orbits=&orbit_label=&ell=2&count=50").data
        assert '17.4.1.1' in L 
            
    # Search orbit   
    def test_hecke_algebra_search_with_orbit(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?level=&weight=&num_orbits=&orbit_label=139.2.1.3&ell=").data
        assert 'Labels' in L 
        
    def test_hecke_algebra_search_with_orbit_and_l(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/?level=&weight=&num_orbits=&orbit_label=139.2.1.3&ell=2").data
        assert 'Number of $\Z_{ 2 }$ orbits' in L 
                     
                     
    # Download Hecke operators
    def test_download_hecke_op(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/9.16.1.5/download/magma/operators").data
        assert '10307091840' in L
            
    # Download idempotents
    def test_download_idempotent(self):
        L = self.tc.get("/ModularForm/GL2/Q/HeckeAlgebra/139.2.1.3/3/2/download/magma/idempotents").data
        assert '8504333379429738379' in L
