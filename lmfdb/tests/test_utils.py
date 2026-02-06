# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2017 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import unittest

from sage.all import var

from lmfdb.utils import (
    an_list,
    coeff_to_poly,
    display_multiset,
    pair2complex,
    round_to_half_int,
    splitcoeff,
    to_dict,
    comma,
    format_percentage,
    signtocolour,
    rgbtohex,
    web_latex,
    web_latex_split_on,
    web_latex_split_on_pm,
    web_latex_split_on_re,
    web_latex_ideal_fact,
    list_to_latex_matrix,
)

from lmfdb.utils.completeness import (
    results_complete,
    IntegerSet,
    top,
    bottom,
    infinity,
)

class UtilsTest(unittest.TestCase):
    """
    An example of unit tests that are not based on the website itself.
    """

    def test_an_list(self):
        r"""
        Checking utility: an_list
        """
        # (1 - 2^{-s})^{-1} (1 - 3^{-s})^{-1}
        def euler1(p): return [1, -1] if p <= 3 else [1,0]
        t1 = an_list(euler1, upperbound=20)
        expect1 = [1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0]
        self.assertEqual(t1, expect1)

        # (1 + 2^{-s})^{-1} (1 + 3^{-s})^{-1}
        def euler2(p): return [1, 1] if p <= 3 else [1,0]
        t2 = an_list(euler2, upperbound=20)
        expect2 = [1, -1, -1, 1, 0, 1, 0, -1, 1, 0, 0, -1, 0, 0, 0, 1, 0, -1, 0, 0]
        self.assertEqual(t2, expect2)

    def test_coeff_to_poly(self):
        r"""
        Checking utility: coeff_to_poly
        """
        x = var('x')
        self.assertEqual(coeff_to_poly("1 - 3x + x^2"), x**2 - 3*x + 1)

    def test_display_multiset(self):
        r"""
        Checking utility: display_multiset
        """
        self.assertEqual(display_multiset([["a", 3], [12, 2]]), 'a x3, 12 x2')
        self.assertEqual(display_multiset([[1, 4], [0, 0], ["cat", 2]]),
                                          '1 x4, 0, cat x2')

    def test_pair2complex(self):
        r"""
        Checking utility: pair2complex
        """
        self.assertEqual(pair2complex("1 2"), [1.0, 2.0])
        self.assertEqual(pair2complex("1.5"), [1.5, 0])
        self.assertEqual(pair2complex("  -1.3    4.1   "), [-1.3, 4.1])

    def test_round_to_half_int(self):
        r"""
        Checking utility: round_to_half_int
        """
        self.assertEqual(round_to_half_int(1.1), 1.0)
        self.assertEqual(round_to_half_int(-0.9), -1.0)

    def test_to_dict(self):
        r"""
        Checking utility: to_dict
        """
        self.assertEqual(to_dict({"not_list": 1, "is_list":[2,3,4]}),
                         {'is_list': 4, 'not_list': 1})

    def test_splitcoeff(self):
        r"""
        Checking utility: splitcoeff
        """
        self.assertEqual(splitcoeff("1 2"), [[1.0, 2.0]])
        self.assertEqual(splitcoeff("  0  -1.2  \n  3.14  1 "),
                         [[0.0, -1.2], [3.14, 1.0]])

    ################################################################################
    #  display and formatting utilities
    ################################################################################

    def test_comma(self):
        r"""
        Checking utility: comma
        """
        self.assertEqual(comma(123), "$123$")
        self.assertEqual(comma(123456789), "$123{,}456{,}789$")
        self.assertEqual(comma(123, mathmode=False), "123")
        self.assertEqual(comma(123456789, mathmode=False), "123,456,789")

    def test_format_percentage(self):
        r"""
        Checking utility: format_percentage
        """
        self.assertEqual(format_percentage(12,31), '     38.71')
        self.assertEqual(format_percentage(12,37), '     32.43')

    def test_signtocolour(self):
        r"""
        Checking utility: signtocolour
        """
        self.assertEqual(signtocolour(0), 'rgb(63,63,255)')
        self.assertEqual(signtocolour("1+2*I"), 'rgb(197,0,184)')

    def test_rgbtohex(self):
        r"""
        Checking utility: rgbtohex
        """
        self.assertEqual(rgbtohex('rgb(63,255,100)'), '#3fff64')
        self.assertEqual(rgbtohex('rbg(63,63,255)'), '#3f3fff')

    ################################################################################
    #  latex/math rendering utilities
    ################################################################################

    def test_web_latex(self):
        r"""
        Checking utility: web_latex
        """
        x = var('x')
        self.assertEqual(web_latex("test string"), "test string")
        self.assertEqual(web_latex(x**23 + 2*x + 1),
                         '\\( x^{23} + 2 \\, x + 1 \\)')
        self.assertEqual(web_latex(x**23 + 2*x + 1, enclose=False),
                         ' x^{23} + 2 \\, x + 1 ')

    def test_web_latex_ideal_fact(self):
        r"""
        Checking utility: web_latex_ideal_fact
        """
        from sage.all import NumberField
        x = var('x')
        K = NumberField(x**2 - 5, 'a')
        a = K.gen()
        I = K.ideal(2/(5+a)).factor()
        self.assertEqual(web_latex_ideal_fact(I),
                         '\\( \\left(-a\\right)^{-1} \\)')
        self.assertEqual(web_latex_ideal_fact(I, enclose=False),
                         ' \\left(-a\\right)^{-1} ')

    def test_web_latex_split_on(self):
        r"""
        Checking utility: web_latex_split_on
        """
        x = var('x')
        self.assertEqual(web_latex_split_on("test string"), "test string")
        self.assertEqual(web_latex_split_on(x**2 + 1),
                         '\\( x^{2} \\) + \\(  1 \\)')

    def test_web_latex_split_on_pm(self):
        r"""
        Checking utility: web_latex_split_on_pm
        """
        x = var('x')
        f = x**2 + 1
        expected = '\\(x^{2} \\) \\(\\mathstrut +\\mathstrut  1 \\)'
        self.assertEqual(web_latex_split_on_pm(f), expected)

    def test_web_latex_split_on_re(self):
        r"""
        Checking utility: web_latex_split_on_re
        """
        x = var('x')
        f = x**2 + 1
        expected = '\\(x^{2} \\) \\(\\mathstrut+  1 \\)'
        self.assertEqual(web_latex_split_on_re(f), expected)

    def test_list_to_latex_matrix(self):
        r"""
        Checking utility: list_to_latex_matrix
        """
        identity_list = [[1,0], [0,1]]
        identity_rep = '\\left(\\begin{array}{rr}1 & 0\\\\0 & 1\\end{array}\\right)'
        self.assertEqual(list_to_latex_matrix(identity_list), identity_rep)

        # malformed matrices should work
        malformed = [[1,0], [0]]
        malform_rep = '\\left(\\begin{array}{rr}1 & 0\\\\0\\end{array}\\right)'
        self.assertEqual(list_to_latex_matrix(malformed), malform_rep)

    def test_integer_set(self):
        A = IntegerSet([2, 4])
        B = IntegerSet([6, 9])
        C = IntegerSet([-11, 5])
        self.assertEqual(str(A + A), "[4, 8]")
        self.assertEqual(str(A - A), "[-2, 2]")
        self.assertEqual(str(A * A), "[4, 16]")
        self.assertEqual(str(A / A), "[1, 2]")
        self.assertEqual(str(-A), "[-4, -2]")
        self.assertEqual(str(~A), "[1/4, 1/2]")
        self.assertEqual(str(A + B), "[8, 13]")
        self.assertEqual(str(A - B), "[-7, -2]")
        self.assertEqual(str(A * B), "[12, 36]")
        self.assertEqual(str(A / B), "{}")
        self.assertEqual(str(A + C), "[-9, 9]")
        self.assertEqual(str(A - C), "[-3, 15]")
        self.assertEqual(str(A * C), "[-44, 20]")
        self.assertEqual(str(A / C), "[-4, -1] ∪ [1, 4]")
        self.assertEqual(str(B + A), "[8, 13]")
        self.assertEqual(str(B - A), "[2, 7]")
        self.assertEqual(str(B * A), "[12, 36]")
        self.assertEqual(str(B / A), "[2, 4]")
        self.assertEqual(str(B + B), "[12, 18]")
        self.assertEqual(str(B - B), "[-3, 3]")
        self.assertEqual(str(B * B), "[36, 81]")
        self.assertEqual(str(B / B), "{1}")
        self.assertEqual(str(-B), "[-9, -6]")
        self.assertEqual(str(~B), "[1/9, 1/6]")
        self.assertEqual(str(B + C), "[-5, 14]")
        self.assertEqual(str(B - C), "[1, 20]")
        self.assertEqual(str(B * C), "[-99, 45]")
        self.assertEqual(str(B / C), "[-9, -1] ∪ [2, 9]")
        self.assertEqual(str(C + A), "[-9, 9]")
        self.assertEqual(str(C - A), "[-15, 3]")
        self.assertEqual(str(C * A), "[-44, 20]")
        self.assertEqual(str(C / A), "[-5, 2]")
        self.assertEqual(str(C + B), "[-5, 14]")
        self.assertEqual(str(C - B), "[-20, -1]")
        self.assertEqual(str(C * B), "[-99, 45]")
        self.assertEqual(str(C / B), "[-1, 0]")
        self.assertEqual(str(C + C), "[-22, 10]")
        self.assertEqual(str(C - C), "[-16, 16]")
        self.assertEqual(str(C * C), "[-55, 121]")
        self.assertEqual(str(C / C), "[-11, 11]")
        self.assertEqual(str(-C), "[-5, 11]")
        self.assertEqual(str(~C), "(-oo, -1/11] ∪ [1/5, +oo)")
        self.assertEqual(str(abs(C)), "[0, 11]")

        self.assertEqual(str(B.pow_cap(A, 1.5)), "[6, 8]")
        self.assertEqual(str(A.union(B, C)), "[-11, 9]")
        self.assertEqual(str(C.intersection(A * A)), "[4, 5]")
        self.assertEqual(str(C.difference(-A,A)), "[-11, -5] ∪ [-1, 1] ∪ {5}")
        self.assertEqual(A.is_subset(C), True)
        self.assertEqual(B.is_subset(A + A), False)
        self.assertEqual(A <= B, True)
        self.assertEqual(A <= A + A, True)
        self.assertEqual(C <= A + A, False)
        self.assertEqual(A < B, True)
        self.assertEqual(A < A + A, False)
        self.assertEqual(A.bounded(5), True)
        self.assertEqual(A.bounded(4), True)
        self.assertEqual(A.bounded(3), False)
        self.assertEqual(A.bounded(2,4), True)
        self.assertEqual(A.restricted(), True)
        self.assertEqual(IntegerSet(None).restricted(), False)
        self.assertEqual(A.min(), 2)
        self.assertEqual(A.max(), 4)
        self.assertEqual(top(4).min(), -infinity)
        self.assertEqual(top(4).max(), 4)

        self.assertEqual(list(IntegerSet([5, 40]).stickelberger(2, [0])), [(5,), (2,), (2, 3), (13,), (17,), (3, 7), (2, 3), (2, 7), (29,), (3, 11), (37,), (2, 5)])
        self.assertEqual(list(IntegerSet([3, 40]).stickelberger(2, [1])), [(3,), (2,), (7,), (2,), (11,), (3, 5), (19,), (2, 5), (23,), (2, 3), (31,), (5, 7), (3, 13), (2, 5)])
        self.assertEqual(list(IntegerSet([200, 220]).stickelberger(3, [0])), [(2, 5), (3, 67), (2, 3, 17), (5, 41), (2, 13), (11, 19), (2, 53), (3, 71), (2, 3), (7, 31), (2, 5, 11)])

        self.assertEqual(A.is_finite(), True)
        self.assertEqual(IntegerSet(None).is_finite(), False)
        self.assertEqual(top(4).is_finite(), False)
        self.assertEqual(bottom(4).is_finite(), False)

        X = [
            (3, 150000), # 3
            (4, 100000), # 4
            ([5,14], 50000), # 7,8,11
            (15, 1000), # 15
            ([16,19], 15000), # 19
            (20, 1000), # 20
            ([21,23], 3000), # 23
            (24, 1000), # 24
            ([25,34], 5000), # 31
            ([35,40], 1000), # 35,39,40
            ([41,46], 15000), # 43
            ([47, 59], 1000), # 47,51,52,55,56,59
            ([60, 67], 10000), # 67
            ([68, 120], 1000),
            ([121, 159], 100),
            ([160, 163], 5000), # 163
            ([164, 702], 100), # 703 is the first missing
        ]
        self.assertEqual(A.bound_under(X), None)
        self.assertEqual((A + A).bound_under(X), 50000)
        self.assertEqual((A * B).bound_under(X), 1000)

    def test_mod_operator(self):
        """
        Test that $mod operator in queries is handled correctly
        
        Note: psycodict uses [remainder, divisor] format for $mod, so
        {'$mod': [0, 7]} means "values where value % 7 == 0" (multiples of 7)
        """
        from lmfdb.utils.completeness import to_rset, IntegerSet
        
        # Test that $mod creates an unbounded set (full real line)
        # {'$mod': [0, 7]} means multiples of 7 in psycodict format
        mod_query = {'$mod': [0, 7]}
        rset = to_rset(mod_query)
        self.assertEqual(str(rset), "(-oo, +oo)")
        
        # Test that IntegerSet can be created from $mod query without error
        iset = IntegerSet(mod_query)
        self.assertEqual(str(iset.rset), "(-oo, +oo)")
        
        # Test that unbounded set is not a subset of bounded set
        bounded = IntegerSet([1, 500000])
        self.assertEqual(iset.is_subset(bounded), False)
        self.assertEqual(bounded.is_subset(iset), True)

    def test_complete(self):
        from lmfdb import db
        for tup in [
                ("lfunc_search", {"rational": True, "degree": 1, "conductor": {"$lte": 100}}, 'L-functions with degree 1 and conductor at most 2800'),
                ("maass_rigor", {"level": 3, "spectral_parameter": {"$lte": 21}}, 'Maass forms with level 3 and spectral parameter at most 24.9526'),
                ("mf_newforms", {'level': {'$gte': 4, '$lte': 12}, 'weight': {'$gte': 3, '$lte': 6}}, "newforms with $Nk^2$ at most 4000"),
                ("mf_newforms", {'level': {'$gte': 24, '$lte': 100}, 'weight': {'$gte': 10, '$lte': 16}, 'char_orbit_index': 1}, "newforms with trivial character and $Nk^2$ at most 40000"),
                ("mf_newforms", {'level': {'$gte': 12, '$lte': 20}, 'weight': {'$gte': 20, '$lte': 40}}, "newforms with level $N$ at most 24 and $Nk^2$ at most 40000"),
                ("mf_newforms", {'level': {'$gte': 4, '$lte': 8}, 'weight': {'$gte': 60, '$lte': 100}}, "newforms with level $N$ at most 10 and $Nk^2$ at most 100000"),
                ("mf_newforms", {'level': {'$gte': 96, '$lte': 100}, 'weight': {'$gte': 8, '$lte': 12}}, "newforms with level at most 100 and weight at most 12"),
                ("mf_newforms", {'level': {'$gte': 37000, '$lte': 49000}, 'weight': 2, 'prim_orbit_index': 1}, "newforms with trivial character, weight 2, and level at most 50000"),
                ("mf_newforms", {'level': 900001, 'weight': 2, 'char_order': 1}, "newforms with trivial character, weight 2 and prime level at most a million"),
                ("hmf_forms", {'deg': 4, 'disc': {'$gte': 1, '$lte': 1200}, 'level_norm': {'$gte': 1, '$lte': 40}}, "Hilbert modular forms over 4.4.725.1, 4.4.1125.1 of level norm at most 991"),
                ("hmf_forms", {'field_label': '3.3.1929.1', 'level_norm': {'$gte': 1, '$lte': 50}}, "Hilbert modular forms over 3.3.1929.1 of level norm at most 53"),
                ("bmf_forms", {'field_disc': {'$gte': -12, '$lte': -3}, 'level_norm': {'$gte': 1, '$lte': 40000}}, "Bianchi modular forms with level norm at most 50000 over imaginary quadratic fields with absolute discriminant in [3, 12]"),
                ("ec_nfcurves", {'field_label': '3.3.1929.1', 'conductor_norm': {'$gte': 1, '$lte': 50}}, "elliptic curves with conductor norm at most 2059 over totally real cubic fields with discriminant 1957"),
                ("nf_fields", {'disc_abs': {'$gte': 1, '$lte': 10000}}, "number fields with absolute discriminant at most 1656109"),
                ("nf_fields", {'degree': 3, 'r2': 0, 'disc_abs': {'$gte': 1, '$lte': 2000000}}, "number fields with degree 3, signature [3,0], absolute discriminant at most 3375000"),
                ("nf_fields", {'degree': 1}, "number fields with degree 1"),
                ("nf_fields", {'degree': 14, 'r2': 1, 'disc_sign': 1}, "number fields with incompatible conditions: signature and discriminant"),
                ("nf_fields", {'degree': 2, 'r2': 1, 'class_number': 17}, "number fields with signature [0,1], class number at most 100 (except 98)"),
                ("nf_fields", {'degree': 2, 'r2': 1, 'class_group': [2, 2, 2, 2, 2, 2, 2]}, "number fields with signature [0,1], class group of exponent 2", "depends on GRH"),
                ("nf_fields", {'degree': 5, 'rd': {'$gte': 40, '$lte': 60}, 'grd': {'$gte': 20, '$lte': 30}}, "number fields with incompatible conditions: root discriminant and Galois root discriminant"),
                ("nf_fields", {'degree': 2, 'rd': {'$gte': 30, '$lte': 40}, 'disc_abs': {'$gte': 10000, '$lte': 20000}}, "number fields with absolute discriminant at most 1656109"),
                ("nf_fields", {'degree': 6, 'r2': 0, 'galois_label': '6T11', 'disc_abs': {'$gte': 1200000000, '$lte': 1800000000}}, "number fields with degree 6, signature [6,0], Galois group 6T11, absolute discriminant at most 1838265625"),
                ("nf_fields", {'degree': 9, 'r2': 0, 'gal_is_abelian': True, 'disc_abs': {'$gte': 1, '$lte': 1900000000000000}}, "number fields with degree 9, signature [9,0], Galois group 9T(1,2,6,7,17), absolute discriminant at most 1953125000000000"),
                ("nf_fields", {'degree': 6, 'disc_abs': 489631389843456}, "number fields with degree 6, unramified outside {2,3,7}"),
                ("nf_fields", {'degree': 5, 'disc_abs': 4130513738895632747}, "number fields with degree 5, unramified outside {107,131}"),
                ("nf_fields", {'degree': 5, 'disc_abs': 38602932139211521}, "number fields with degree 5, unramified outside {107,131}"),
                ("nf_fields", {'degree': 7, 'galois_label': '7T1', 'disc_abs': 446132784330195495457232}, "number fields with degree 7, Galois group 7T1, unramified outside {2,7,11,17,37,41}"),
                ("nf_fields", {'degree': 5, 'galois_label': '5T4', 'disc_abs': 920627786839041}, "number fields with degree 5, Galois group 5T(1,2,4), unramified outside {3,1201}"),
                ("nf_fields", {'degree': 5, 'galois_label': '5T4', 'gal_is_abelian': True, 'disc_abs': 920627786839041}, "number fields with incompatible conditions: Galois group"),
                ("nf_fields", {'degree': 5, 'galois_label': '5T4', 'disc_rad': 1254}, "number fields with degree 5, Galois group 5T(1,2,4), unramified outside {2,3,11,19}"),
                ("nf_fields", {'degree': 8, 'galois_label': '8T25', 'rd': {'$gte': 1, '$lte': 100}}, "number fields with degree 8, Galois group 8T(25,36), Galois root discriminant at most 200"),
                ("artin_reps", {'GaloisLabel': '6T6', 'Conductor': {'$gte': 1, '$lte': 20000}}, "Artin representations with group 6T6, and conductor at most 22497"),
                ("gps_groups", {'order': {'$gte': 300, '$lte': 500}}, "groups of order at most 2000 except orders larger than 500 that are multiples of 128"),
                ("gps_groups", {'perfect': True, 'order': {'$gte': 20000, '$lte': 40000}}, "perfect groups of order at most 50000"),
                ("gps_groups", {'simple': True, 'abelian': False, 'order': {'$gte': 1, '$lte': 10000000}}, "nonabelian simple groups of order less than 10162031880"),
                ("gps_groups", {'transitive_degree': {'$gte': 16, '$lte': 24}}, "groups with minimal transitive degree at most 47 (except 32)"),
                ("gps_groups", {'transitive_degree': 32, 'order': {'$gte': 40000000000, '$lte': 100000000000}}, "groups with minimal transitive degree 32 and order at least 40 billion"),
                ("gps_groups", {'permutation_degree': {'$gte': 10, '$lte': 14}}, "groups with minimal permutation degree at most 15"),
                ("gps_groups", {'linQ_dim': 5}, r"groups with linear $\Q$-degree at most 6"),
                ("ec_curvedata", {'conductor': {'$gte': 300, '$lte': 3000}}, "elliptic curves with conductor at most 500000"),
                ("ec_curvedata", {'conductor': 1000003}, "elliptic curves with prime conductor at most 300 million"),
                ("ec_curvedata", {'conductor': 76204800}, "elliptic curves with 7-smooth conductor"),
                ("ec_curvedata", {'absD': {'$gte': 50000, '$lte': 100000}}, "elliptic curves with minimal discriminant at most 500000"),
                ("hgcwa_passports", {'genus': 3}, "groups acting as automorphisms of curves of genus 2, 3 or 4"),
                ("hgcwa_passports", {'genus': 11, 'g0': 0}, "groups G acting as automorphisms of curves X with the genus of X at most 15 and the genus of X/G equal to 0"),
                ("av_fq_isog", {'g': 1, 'q': 729}, "isogeny classes of elliptic curves over fields of cardinality less than 500 or 512, 625, 729, 1024"),
                ("av_fq_isog", {'g': {'$gte': 2, '$lte': 4}, 'q': {'$gte': 2, '$lte': 4}}, "isogeny classes of abelian varieties of dimension at most 4 over fields of cardinality at most 5"),
                ("av_fq_isog", {'q': 3, 'p_rank': 2, 'p_rank_deficit': 2}, "isogeny classes of abelian varieties of dimension at most 4 over fields of cardinality at most 5"),
                ("belyi_galmaps", {'deg': {'$gte': 2, '$lte': 4}}, "Belyi maps of degree at most 6"),
                ("lf_fields", {'p': 2, 'n': 16}, "p-adic fields of degree at most 23 and residue characteristic at most 199"),
                ("lf_fields", {'p': 3, 'e': 9, 'f': 2}, "p-adic fields of degree at most 23 and residue characteristic at most 199"),
                ("lf_families", {'p': 2, 'e': 4, 'f0': {'$gte': 1, '$lte': 2}, 'e0': 2, 'f': 2}, "families of p-adic extensions with absolute degree at most 47, base degree at most 15 and residue characteristic at most 199"),
                ("char_dirichlet", {'modulus': {'$gte': 40, '$lte': 100}}, "Dirichlet characters with modulus at most a million"),
                ("hgm_families", {'degree': {'$gte': 4, '$lte': 6}}, "hypergeometric families with degree at most 7"),
                ("gps_transitive", {'n': 18, 'solv': 1}, "transitive groups of degree at most 47 (except 32)"),
                ("gps_transitive", {'n': 32, 'order': 384}, "transitive groups of degree 32 and order at most 511"),
                ("gps_transitive", {'n': 32, 'order': {'$gte': 40000000000, '$lte': 100000000000}}, "transitive groups of degree at most 47 and order at least 40 billion"),
                ("gps_st", {'rational': True, 'weight': 1, 'degree': {'$gte': 3, '$lte': 5}}, "rational Sato-Tate groups of weight at most 1 and degree at most 6"),
                ("gps_st", {'rational': True, 'weight': 0, 'degree': 1}, "rational Sato-Tate groups of weight 0 and degree 1"),
                ("gps_st", {'weight': 0, 'degree': 1, 'components': {'$gte': 40, '$lte': 50}}, "Sato-Tate groups of weight 0, degree 1 and at most 10000 components"),
        ]:
            if len(tup) == 3:
                tbl, query, reason = tup
                caveat = None
            else:
                tbl, query, reason, caveat = tup
            self.assertEqual(results_complete(tbl, query, db), (True, reason, caveat))

        for tbl, query in [
                ("maass_rigor", {"level": {"$gte":2, "$lte": 5}, "spectral_parameter": {"$lte": 21}}),
                ("mf_newforms", {'level': {'$gte': 100, '$lte': 200}, 'weight': {'$gte': 20, '$lte': 30}}),
                ("hmf_forms", {'deg': 7, 'disc': {'$gte': 1, '$lte': 1200}, 'level_norm': {'$gte': 1, '$lte': 40}}),
                ("bmf_forms", {'field_disc': {'$gte': -120, '$lte': -3}, 'level_norm': {'$gte': 1, '$lte': 4000}}),
                ("ec_nfcurves", {'field_label': '7.7.20134393.1', 'conductor_norm': {'$gte': 1, '$lte': 50}}),
                ("nf_fields", {'degree': 6, 'disc_abs': {'$gte': 1, '$lte': 20000000}}),
                ("artin_reps", {'GaloisLabel': '8T34', 'Conductor': {'$gte': 1, '$lte': 200}}),
                ("gps_groups", {'order': {'$gte': 300, '$lte': 600}}),
                ("ec_curvedata", {'rank': 6}),
                ("hgcwa_passports", {'genus': 6}),
                ("av_fq_isog", {'g': 6, 'q': 3}),
                ("belyi_galmaps", {'deg': 8}),
                ("lf_fields", {'p': 2, 'n': 24}),
                ("lf_families", {'p': 2, 'e': 4, 'f0': {'$gte': 1, '$lte': 4}, 'e0': 2, 'f': 2}),
                ("char_dirichlet", {'modulus': {'$gte': 400000, '$lte': 3000000}}),
                ("hgm_families", {'degree': 8}),
                ("gps_transitive", {'n': 32, 'solv': 1}),
                ("gps_st", {'rational': True, 'weight': 1, 'degree': 8}),
                # Test $mod operator (multiples of n) - should be incomplete
                # Note: psycodict format is [remainder, divisor], so [0, 7] means multiples of 7
                ("ec_curvedata", {'conductor': {'$mod': [0, 7]}}),
                ("mf_newforms", {'level': {'$mod': [0, 23]}}),
        ]:
            self.assertEqual(results_complete(tbl, query, db)[0], False)
