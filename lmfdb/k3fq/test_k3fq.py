import unittest

from lmfdb import db
from lmfdb.tests import LmfdbTest

# The table is not yet available in every copy of the database (e.g. devmirror)
HAS_TABLE = "k3_fq_isog" in db.tablenames

# P(T) = 2(1-T)^22, supersingular over F_2
SS_LABEL = "2.22.a"
# P(T) = 2(1-T)^21(1+T), supersingular with sign -1
SS_MINUS_LABEL = "2.22.b"


class K3FqLabelTest(unittest.TestCase):
    # These do not need the database
    def test_labels(self):
        from lmfdb.k3fq.web_k3fq import poly_to_label, label_to_poly, validate_label, lpoly_to_poly
        poly = [2, -44, 462, -3080, 14630, -52668, 149226, -341088, 639540, -994840, 1293292, -1410864,
                1293292, -994840, 639540, -341088, 149226, -52668, 14630, -3080, 462, -44, 2]
        assert poly_to_label(poly) == SS_LABEL
        assert label_to_poly(SS_LABEL) == poly
        lpoly = [1] + [2**(i - 1) * a for i, a in enumerate(poly) if i > 0]
        assert lpoly_to_poly(lpoly) == poly
        validate_label(SS_MINUS_LABEL)
        assert label_to_poly(SS_MINUS_LABEL)[-1] == -2
        # 2 + 2T^22 = 2 Phi_4 Phi_44 is also supersingular
        assert poly_to_label([2] + [0] * 21 + [2]) == "2.22.dilx"
        assert label_to_poly("2.22.dilx") == [2] + [0] * 21 + [2]
        # (1-T)^16 Phi_4 (4 + T + 6T^2 + T^3 + 4T^4) over F_4
        from sage.all import PolynomialRing, ZZ
        T = PolynomialRing(ZZ, "T").gen()
        P = ((1 - T)**16 * (1 + T**2) * (4 + T + 6*T**2 + T**3 + 4*T**4)).list()
        assert poly_to_label(P) == "4.18.e.ot"
        assert label_to_poly("4.18.e.ot") == P
        # b_2 = 17 needs two letters, so b_1 = -12 gets two as well
        P = ((1 - T)**18 * (2 - 3*T + 2*T**2)**2).list()
        assert poly_to_label(P) == "4.18.a.nboe"
        assert label_to_poly("4.18.a.nboe") == P
        from lmfdb.k3fq.web_k3fq import label_wbr
        assert label_wbr("4.18.a.nboe") == "4.18.a.nb<wbr>oe" and label_wbr("4.18.e.ot") == "4.18.e.ot"
        from lmfdb.k3fq.web_k3fq import cyclotomic_index, cyclotomic_orders, num_cyclotomic_parts
        assert [num_cyclotomic_parts(k) for k in (0, 2, 22)] == [1, 6, 60280]
        assert [cyclotomic_orders(2, i) for i in range(6)] == [[1, 1], [1, 2], [2, 2], [3], [4], [6]]
        for i in range(0, 60280, 997):
            assert cyclotomic_index(cyclotomic_orders(22, i)) == i
        from lmfdb.k3fq.main import in_ranges
        assert in_ranges(5, "2-") and in_ranges(5, "1,3-6") and in_ranges(5, "4..9")
        assert not in_ranges(5, "6-") and not in_ranges(5, "2,3")
        assert in_ranges(4, "2^2") and in_ranges(4, "2*2") and not in_ranges(5, "2^2")
        # negated singletons, ranges and unions
        assert not in_ranges(2, "~2") and in_ranges(3, "~2")
        assert not in_ranges(3, "~2-4") and in_ranges(5, "~2-4") and in_ranges(1, "~2-4")
        assert not in_ranges(4, "~2,4") and in_ranges(3, "~2,4")
        assert not in_ranges(4, "~2^2") and in_ranges(5, "~2^2")
        for bad in ["2.p.a_a", "2.p.abs_ru_aeom_vqs_aczxs_imtm_atkou_bkkbs_aceprc_cvpea_adchca",
                    "6.20.a.o", "02.20.a.o", "1.20.a.o", "2.21.a.o", "2.020.a.o", "2.24.a", "2.22",
                    "2.22.ab", "2.22.dmcd", "2.22.a.o", "2.20.a", "2.20.a.", "2.20.a.o_o", "2.18.a.ooo",
                    "2.18.a.nono", "2.20.a.no", "2.20.A.o", "4.18.e.b_g"]:
            self.assertRaises(ValueError, validate_label, bad)
        for good in ["2.20.a.m", "2.20.a.zz", "2.0.a.nnnnnnnnnnn", "3.18.osw.mo", "4.18.a.nboe"]:
            validate_label(good)


@unittest.skipUnless(HAS_TABLE, "k3_fq_isog is not in this database")
class K3FqTest(LmfdbTest):
    def test_index(self):
        self.check_args("/Motive/K3/Fq/", ["Motives of K3 type over finite fields", "Browse", "Find"])

    def test_static_pages(self):
        for page in ["Source", "Completeness", "Reliability", "Labels"]:
            self.assertEqual(self.tc.get("/Motive/K3/Fq/" + page).status_code, 200)

    def test_supersingular(self):
        self.check_args("/Motive/K3/Fq/" + SS_LABEL, ["supersingular", r"\infty", r"( 1 - T )^{22}", "Transcendental part"])

    def test_census_class(self):
        # a class from the quartic census over F_2: contains a K3 surface, with a polarization of degree 4
        self.check_args("/Motive/K3/Fq/2.18.msv.nk", ["Polarization degrees", "$4$ (other degrees may occur)"])

    def test_sign_minus(self):
        self.check_args("/Motive/K3/Fq/" + SS_MINUS_LABEL, ["$-1$", r"\rho = 21"])

    def test_bad_label(self):
        self.check_args("/Motive/K3/Fq/2.p.a_a_a", "not a valid label")
        self.check_args("/Motive/K3/Fq/2.22.ab", "not a valid label")
        self.check_args("/Motive/K3/Fq/2.20.a.zz", "not in the database")

    def test_jump(self):
        self.check_args("/Motive/K3/Fq/?jump=2*(1-T)^22", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?jump=" + SS_LABEL, SS_LABEL)
        self.check_args("/Motive/K3/Fq/?jump=garbage", "is not valid input")

    def test_search(self):
        self.check_args("/Motive/K3/Fq/?q=2", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&height=inf&sign=-1", SS_MINUS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&initial_coefficients=[-44,462]", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&picard_rank=22&newton=supersingular", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?height=foo", "is not a valid input")
        # 2(1-T)^22 has 1 + 2^2 + 44 = 49 points as a K3 surface, so 1 + 2^2 + 2^4 + 2*49 = 119 as a cubic fourfold
        self.check_args("/Motive/K3/Fq/?q=2&point_count=49", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&point_count=119&point_count_type=cubic", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&point_count=123&point_count_type=gm", SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&point_count=5&point_count_type=bogus", "is not a valid input")

    def test_cyclotomic_search(self):
        base = "/Motive/K3/Fq/?q=2&height=inf&"
        self.check_args(base + "cyclotomic_factors=1^22&cyclotomic_mode=exactly", SS_LABEL)
        self.check_args(base + "cyclotomic_factors=1,2,1^20&cyclotomic_mode=exactly", SS_MINUS_LABEL)
        self.check_args(base + "cyclotomic_factors=2", SS_MINUS_LABEL)
        self.check_args(base + "cyclotomic_factors=1^21", SS_MINUS_LABEL)
        self.check_args(base + "cyclotomic_factors=1&cyclotomic_mode=supported", SS_LABEL)
        self.check_args(base + "cyclotomic_factors=1,2&cyclotomic_mode=supported", SS_MINUS_LABEL)
        self.check_args(base + "cyclotomic_factors=1,2&cyclotomic_mode=supported&sign=-1", SS_MINUS_LABEL)
        self.not_check_args(base + "cyclotomic_factors=1&cyclotomic_mode=supported", SS_MINUS_LABEL)
        self.not_check_args(base + "cyclotomic_factors=1^22&cyclotomic_mode=exactly", SS_MINUS_LABEL)
        self.not_check_args(base + "cyclotomic_factors=3", SS_LABEL)
        self.check_args(base + "cyclotomic_factors=~2&sign=1", SS_LABEL)
        for bad in ["67", "1^23", "23,23", "x", "1&cyclotomic_mode=bogus"]:
            self.check_args(base + "cyclotomic_factors=" + bad, "is not a valid input")

    def test_counts(self):
        self.check_args("/Motive/K3/Fq/?search_type=Counts&q=2-", "Picard rank")
        self.check_args("/Motive/K3/Fq/?search_type=Counts&picard_rank=10-", "Picard rank")
        self.check_args("/Motive/K3/Fq/?search_type=Counts&p=2-3", "Picard rank")
        self.check_args("/Motive/K3/Fq/?search_type=Counts&q=2^2", "Picard rank")
        self.check_args("/Motive/K3/Fq/?search_type=Counts&picard_rank=2*5&p=2^1", "Picard rank")

    def test_random(self):
        self.check_args("/Motive/K3/Fq/random", "Motive of K3 type")

    def test_stats(self):
        self.check_args("/Motive/K3/Fq/stats", "Distribution of")

    def test_downloads(self):
        self.check_args("/Motive/K3/Fq/download_all/" + SS_LABEL, '"label": "%s"' % SS_LABEL)
        self.check_args("/Motive/K3/Fq/?q=2&height=inf&Submit=sage&download=1&query=%7B%27q%27%3A+2%2C+%27height%27%3A+None%7D", SS_LABEL)
