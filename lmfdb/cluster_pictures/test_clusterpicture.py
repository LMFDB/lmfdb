""" Still todo
# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest

class NumberFieldTest(LmfdbTest):
    # All tests should pass
    def test_Q(self):
        self.check_args('/NumberField/Q', r'\chi_{1}')
        self.check_args('/NumberField/1.1.1.1', r'\chi_{1}')

    def test_hard_degree10(self):
        self.check_args('/NumberField/10.10.1107649855354064.1', '10T36')
        self.check_args('/NumberField/10.10.138420300533025695415730492558689.1', '10T38')

    def test_hard_degree16(self):
        self.check_args('/NumberField/16.0.13307764731675384304522756096.1', '16T1535')

    def test_search_ramif_cl_deg(self):
        self.check_args('/NumberField/?degree=5&class_group=[2%2C2]&ur_primes=7&discriminant=&ram_quantifier=exactly&ram_primes=2%2C3%2C5', '5.1.27000000000.8')

    def test_abelian_conductor(self):
        self.check_args('/NumberField/5.5.5719140625.2', '275') # conductor

    def test_stuff_not_computed(self):
        self.check_args('/NumberField/23.23.931347256889446325436632107655346061164193665348344821578377438399536607931200329.1', 'Not computed')

    def test_search_poly_mean2parser(self):
        self.check_args('/NumberField/?jump=X**3-4x%2B2&search=Go', '148') # discriminant

    def test_search_zeta(self):
        self.check_args('/NumberField/?jump=Qzeta23&search=Go', '[3]') # class group

    def test_search_sqrt(self):
        self.check_args('/NumberField/?jump=Qsqrt-163&search=Go', '41') # minpoly

    def test_search_disc(self):
        self.check_args('/NumberField/?discriminant=1988-2014', '401') # factor of one of the discriminants

    def test_url_label(self):
        self.check_args('/NumberField/2.2.5.1', '0.481211825') # regulator

    def test_url_naturallabel(self):
        self.check_args('/NumberField/Qsqrt5', '0.481211825') # regulator

    def test_arith_equiv(self):
        self.check_args('/NumberField/7.3.6431296.1', '7.3.6431296.2') # arith equiv field

    def test_sextic_twin(self):
        self.check_args('/NumberField/6.0.10816.1', 'Twin sextic algebra')

    def test_how_computed(self):
        self.check_args('/NumberField/Source', 'Hunter searches')

    def test_galois_group_page(self):
        self.check_args('/NumberField/GaloisGroups', 'abstract group may have')

    def test_imaginary_quadratic_page(self):
        self.check_args('/NumberField/QuadraticImaginaryClassGroups', 'Mosunov')

    def test_discriminants_page(self):
        self.check_args('/NumberField/Source', 'Jones-David Roberts')

    def test_field_labels_page(self):
        self.check_args('/NumberField/FieldLabels', 'with the same signature and absolute value of the')

    def test_url_bad(self):
        self.check_args('/NumberField/junk', 'Error') # error mesage

    def test_random_field(self):
        self.check_args('/NumberField/random', 'Discriminant')

    def test_statistics(self):
        self.check_args('/NumberField/stats', 'Class number')

    def test_signature_search(self):
        self.check_args('/NumberField/?start=0&degree=6&signature=%5B0%2C3%5D&count=100', '6.0.61131.1')
        self.check_args('/NumberField/?start=0&degree=7&signature=%5B3%2C2%5D&count=100', '7.3.1420409.1')

    def test_fundamental_units(self):
        self.check_args('NumberField/2.2.10069.1', '43388173')
        self.check_args('NumberField/3.3.10004569.1', '22153437467081345')

    def test_split_ors(self):
        self.check_args('/NumberField/?signature=%5B0%2C3%5D&galois_group=S3', '6.0.177147.2')
        self.check_args('/NumberField/?signature=%5B3%2C0%5D&galois_group=S3', '3.3.229.1')
        self.check_args('/NumberField/?signature=[4%2C0]&galois_group=C2xC2&class_number=3%2C6','4.4.1311025.1')
        self.check_args('/NumberField/?signature=[4%2C0]&galois_group=C2xC2&class_number=6%2C3','4.4.1311025.1')
        self.check_args('/NumberField/?signature=[4%2C0]&galois_group=C2xC2&class_number=5-6%2C3','4.4.485809.1')"""
