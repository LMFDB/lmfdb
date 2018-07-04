# -*- coding: utf8 -*-
from lmfdb.base import LmfdbTest

class NumberFieldTest(LmfdbTest):

    # All tests should pass

    def test_Q(self):
        L = self.tc.get('/NumberField/Q', follow_redirects=True)
        assert '\chi_{1}' in L.data
        L = self.tc.get('/NumberField/1.1.1.1')
        assert '\chi_{1}' in L.data

    def test_hard_degree10(self):
        L = self.tc.get('/NumberField/10.10.1107649855354064.1')
        assert '10T36' in L.data
        L = self.tc.get('/NumberField/10.10.138420300533025695415730492558689.1')
        assert '10T38' in L.data

    def test_hard_degree16(self):
        L = self.tc.get('/NumberField/16.0.13307764731675384304522756096.1')
        assert '16T1535' in L.data

    def test_search_ramif_cl_deg(self):
        L = self.tc.get('/NumberField/?start=0&paging=0&degree=5&signature=&galois_group=&class_number=&class_group=[2%2C2]&ur_primes=7&discriminant=&ram_quantifier=some&ram_primes=2%2C3%2C5&count=20')
        assert '5.1.27000000000.8' in L.data

    def test_abelian_conductor(self):
        L = self.tc.get('/NumberField/5.5.5719140625.2', follow_redirects=True)
        assert '275' in L.data # conductor

    def test_stuff_not_computed(self):
        L = self.tc.get('/NumberField/23.23.931347256889446325436632107655346061164193665348344821578377438399536607931200329.1', follow_redirects=True)
        assert 'Not computed' in L.data

    def test_search_poly_mean2parser(self):
        L = self.tc.get('/NumberField/?natural=X**3-4x%2B2&search=Go', follow_redirects=True)
        assert '148' in L.data # discriminant

    def test_search_zeta(self):
        L = self.tc.get('/NumberField/?natural=Qzeta23&search=Go', follow_redirects=True)
        assert '[3]' in L.data # class group

    def test_search_sqrt(self):
        L = self.tc.get('/NumberField/?natural=Qsqrt-163&search=Go', follow_redirects=True)
        assert '41' in L.data # minpoly

    def test_search_disc(self):
        L = self.tc.get('/NumberField/?start=&paging=0&degree=&signature=&galois_group=&class_number=&class_group=&ur_primes=&discriminant=1988-2014&ram_quantifier=all&ram_primes=&count=')
        assert '401' in L.data # factor of one of the discriminants

    def test_url_label(self):
        L = self.tc.get('/NumberField/2.2.5.1')
        assert '0.481211825' in L.data # regulator

    def test_url_naturallabel(self):
        L = self.tc.get('/NumberField/Qsqrt5', follow_redirects=True)
        assert '0.481211825' in L.data # regulator

    def test_arith_equiv(self):
        L = self.tc.get('/NumberField/7.3.6431296.1', follow_redirects=True)
        assert '7.3.6431296.2' in L.data # arith equiv field

    def test_sextic_twin(self):
        L = self.tc.get('/NumberField/6.0.10816.1', follow_redirects=True)
        assert 'Twin sextic algebra' in L.data

    def test_how_computed(self):
        L = self.tc.get('/NumberField/HowComputed')
        assert 'Hunter searches' in L.data

    def test_galois_group_page(self):
        L = self.tc.get('/NumberField/GaloisGroups')
        assert 'abstract group may have' in L.data

    def test_imaginary_quadratic_page(self):
        L = self.tc.get('/NumberField/QuadraticImaginaryClassGroups')
        assert 'Mosunov' in L.data

    def test_discriminants_page(self):
        L = self.tc.get('/NumberField/Discriminants')
        assert 'Jones-Roberts' in L.data

    def test_field_labels_page(self):
        L = self.tc.get('/NumberField/FieldLabels')
        assert 'with the same signature and absolute value of the' in L.data

    def test_url_bad(self):
        L = self.tc.get('/NumberField/junk')
        assert 'Error' in L.data # error mesage

    def test_random_field(self):
        L = self.tc.get('/NumberField/random', follow_redirects=True)
        assert 'Discriminant' in L.data

    def test_statistics(self):
        L = self.tc.get('/NumberField/stats', follow_redirects=True)
        assert 'Class number' in L.data

    def test_signature_search(self):
        L = self.tc.get('/NumberField/?start=0&degree=6&signature=%5B0%2C3%5D&count=100', follow_redirects=True)
        assert '6.0.61131.1' in L.data

        L = self.tc.get('/NumberField/?start=0&degree=7&signature=%5B3%2C2%5D&count=100', follow_redirects=True)
        assert '7.3.1420409.1' in L.data
