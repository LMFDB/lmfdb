from lmfdb.tests import LmfdbTest


class HGMTest(LmfdbTest):
    # TODO: create stats page
    # def test_stats(self):
    #     self.check_args("Hypergeometric/Q/stats", "Monodromy")

    # test pages

    # family pages

    def test_random_family(self):
        self.check_args("/Motive/Hypergeometric/Q/random_family", ["Hypergeometric motive family", "Defining parameters"])

    def test_by_family_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1", ["[4, 4]", "[1, 1, 1, 1]", "[-2, -2, -1, -1, -1, -1, 4, 4]"])  # As, Bs, gamma

    def test_type(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "Orthogonal")

    def test_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/A10.6.3.2_B14.1.1.1", "[1, 2, 3, 2, 1]")

    def test_bezout_det(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.4.3_B10.2.2.2.2.2.2", "-191102976")

    def test_p_part(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", ["[4, 4, 2, 2, 2, 2, 2]", "[8, 1, 1, 1, 1, 1]", "[9, 3]"])

    def test_monodromy(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.3.3_B6.4.4.4.1.1", "S_{9}")
        self.check_args("/Motive/Hypergeometric/Q/A12.6.6_B5.1.1.1.1", "operatorname{Sp}(8,3)")

    def test_good_euler(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.3_B12.2.2.2.1", "1 + 6 T - 45 p T^{2} - 2130 p^{2} T^{3} + 268 p^{4} T^{4} - 2130 p^{6} T^{5} - 45 p^{9} T^{6} + 6 p^{12} T^{7} + p^{16} T^{8}")

    # ## motive pages

    def test_random_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/random_motive", "Local information")
        self.not_check_args("/Motive/Hypergeometric/Q/random_motive", "Hypergeometric motive family")

    def test_by_motive_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8", ["[2, 2, 2]", "[4, 1]", "[-4, -1, -1, -1, -1, 2, 2, 2, 2]"])  # As, Bs, gamma

    def test_type_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1/t-8.1", "Symplectic")

    def test_signature(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B2.2.2.1/t4.1", "-2")

    def test_conductor(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t2.1", "8192")

    def test_local_information(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t1.9", ["3737281794192", "8013465013431125"])

    # ## searches

    # ## family searches

    def test_search_degree(self):
        self.check_args("/Motive/Hypergeometric/Q/?degree=4&search_type=Family", ["A5_B3.2.1", "A10_B4.2.1"])
        self.not_check_args("/Motive/Hypergeometric/Q/?degree=4&search_type=Family", "A2_B1")

    def test_search_weight(self):
        self.check_args("/Motive/Hypergeometric/Q/?weight=3&search_type=Family", "A5_B6.6")
        self.not_check_args("/Motive/Hypergeometric/Q/?weight=3&search_type=Family", "A3_B4")

    def test_search_family_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C1%2C1%2C1]&search_type=Family", "A5_B6.6")
        self.not_check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C1%2C1%2C1]&search_type=Family", "A15_B8.1.1.1.1")

    def test_search_A(self):
        self.check_args("/Motive/Hypergeometric/Q/?A=[3%2C2%2C2]&search_type=Family", "A3.2.2_B5")
        self.not_check_args("/Motive/Hypergeometric/Q/?A=[3%2C2%2C2]&search_type=Family", "A3.2_B1.1.1")

    def test_search_B(self):
        self.check_args("/Motive/Hypergeometric/Q/?B=[6%2C4]&search_type=Family", "A5_B6.4")
        self.not_check_args("/Motive/Hypergeometric/Q/?B=[6%2C4]&search_type=Family", "A3.2_B1.1.1")

    def test_search_Ap(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=3&Ap=[9]&search_type=Family", "A9_B5.2.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=3&Ap=[9]&search_type=Family", "A2_B1")

    def test_search_Bp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=3&Bp=[1%2C1%2C1%2C1%2C1%2C1]&search_type=Family", "A9_B5.2.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=3&Bp=[1%2C1%2C1%2C1%2C1%2C1]&search_type=Family", "A3_B1.1")

    def test_search_Ap_perp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=5&Apperp=[2%2C2%2C1%2C1]&search_type=Family", "A8_B2.2.1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=5&Apperp=[2%2C2%2C1%2C1]&search_type=Family", "A5_B1.1.1.1")

    def test_search_Bp_perp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=7&Bpperp=[4%2C2%2C1%2C1%2C1]&search_type=Family", "A9_B4.2.1.1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=7&Bpperp=[4%2C2%2C1%2C1%2C1]&search_type=Family", "A2.2.2.2.2.2_B14")

    # ## motive searches

    def test_search_conductor(self):
        self.check_args("/Motive/Hypergeometric/Q/?conductor=32&search_type=Motive", "A4_B2.1_t-8.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?conductor=32&search_type=Motive", "A2.2_B1.1_t-8.1")

    def test_search_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/?hodge=[1%2C1%2C1%2C1]&search_type=Motive", "A8_B1.1.1.1_t-1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?hodge=[1%2C1%2C1%2C1]&search_type=Motive", "A8_B4.1.1_t-1.1")

    def test_search_specialization(self):
        self.check_args("/Motive/Hypergeometric/Q/?t=3%2F2&search_type=Motive", "A4_B2.1_t3.2")
        self.not_check_args("/Motive/Hypergeometric/Q/?t=3%2F2&search_type=Motive", "A4_B2.1_t-8.1")

    def test_search_root_number(self):
        self.check_args("/Motive/Hypergeometric/Q/?sign=-1&search_type=Motive", "A4_B1.1_t-1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?sign=-1&search_type=Motive", "A4_B2.1_t-1.1")

    # ## downloads

    # ## friends

    # ## for families

    def test_friends_family(self):
        self.check_args("/Motive/Hypergeometric/Q/A12.6.6.6_B3.2.2.2.2.2.2.1.1", "Motives in the family")

    # ## for motives

    def test_friends_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1", "Motive family A2.2.2 B4.1")  # containing family
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1", "/L/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1")  # L-function
