# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest

class HGMTest(LmfdbTest):
    # TODO: create stats page
    #def test_stats(self):
        #self.check_args("Hypergeometric/Q/stats", "Monodromy")

    ### family tests

    def test_random_family(self):
        self.check_args("/Motive/Hypergeometric/Q/random_family", "Hypergeometric motive family")
        self.check_args("/Hypergeometric/Q/random_family", "Defining parameters")

    def test_by_family_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1", "[4, 4]")
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1", "[1, 1, 1, 1]")
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1", "[-2, -2, -1, -1, -1, -1, 4, 4]") # gamma vector

    def test_type(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "Orthogonal")

    def test_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/A10.6.3.2_B14.1.1.1", "[1, 2, 3, 2, 1]")

    def test_bezout_det(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.4.3_B10.2.2.2.2.2.2", "-191102976")

    def test_p_part(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "[4, 4, 2, 2, 2, 2, 2]")
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "[8, 1, 1, 1, 1, 1]")
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "[9, 3]")

    def test_monodromy(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.3.3_B6.4.4.4.1.1", "S_{9}")
        self.check_args("/Motive/Hypergeometric/Q/A12.6.6_B5.1.1.1.1", "\operatorname{Sp}(8,3)")

    def test_good_euler(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.3_B12.2.2.2.1", "1 + 6 T - 45 p T^{2} - 2130 p^{2} T^{3} + 268 p^{4} T^{4} - 2130 p^{6} T^{5} - 45 p^{9} T^{6} + 6 p^{12} T^{7} + p^{16} T^{8}")

    ### motive tests

    def test_random_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/random_motive", "Local information")
        self.not_check_args("/Motive/Hypergeometric/Q/random_motive", "Hypergeometric motive family")

    def test_by_motive_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8", "[2, 2, 2]")
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8", "[4, 1]")
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8", "[-4, -1, -1, -1, -1, 2, 2, 2, 2]") # gamma vector

    def test_type_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1/t-8.1", "Symplectic")

    def test_signature(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B2.2.2.1/t4.1", "-2")

    def test_conductor(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t2.1", "8192")

    def test_local_information(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t1.9", "3737281794192")
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t1.9", "8013465013431125")

    ### searches

    ### downloads

    ### friends 
