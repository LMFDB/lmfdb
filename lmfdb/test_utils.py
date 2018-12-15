# -*- coding: utf-8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2017 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import unittest2

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
    pol_to_html,
    web_latex,
    web_latex_split_on,
    web_latex_split_on_pm,
    web_latex_split_on_re,
    web_latex_ideal_fact,
    list_to_latex_matrix
)


class UtilsTest(unittest2.TestCase):
    """
    An example of unit tests that are not based on the website itself.
    """

    def test_an_list(self):
        r"""
        Checking utility: an_list
        """
        # (1 - 2^{-s})^{-1} (1 - 3^{-s})^{-1}
        euler1 = lambda p: [1, -1] if p <= 3 else [1,0]
        t1 = an_list(euler1, upperbound=20)
        expect1 = [1, 1, 1, 1, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 0, 0]
        self.assertEqual(t1, expect1)

        # (1 + 2^{-s})^{-1} (1 + 3^{-s})^{-1}
        euler2 = lambda p: [1, 1] if p <= 3 else [1,0]
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
        self.assertEqual(comma(123), "123")
        self.assertEqual(comma(123456789), "123,456,789")

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
        self.assertEqual(signtocolour(1+2j), 'rgb(197,0,184)')

    def test_rgbtohex(self):
        r"""
        Checking utility: rgbtohex
        """
        self.assertEqual(rgbtohex('rgb(63,255,100)'), '#3fff64')
        self.assertEqual(rgbtohex('rbg(63,63,255)'), '#3f3fff')

    def test_pol_to_html(self):
        r"""
        Checking utility: pol_to_html
        """
        x = var('x')
        f1 = x**2 + 2*x + 1
        self.assertEqual(pol_to_html(f1),
                         '<i>x</i><sup>2</sup> + 2<i>x</i> + 1')
        f2 = 'x^3 + 1'
        self.assertEqual(pol_to_html(f2),
                         '<i>x</i><sup>3</sup> + 1')

    ################################################################################
    #  latex/mathjax utilities
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
        identity_rep = '\\left(\\begin{array}{*{2}{r}}1 & 0\\\\0 & 1\\end{array}\\right)'
        self.assertEqual(list_to_latex_matrix(identity_list), identity_rep)

        # malformed matrices should work
        malformed = [[1,0], [0]]
        malform_rep = '\\left(\\begin{array}{*{2}{r}}1 & 0\\\\0\\end{array}\\right)'
        self.assertEqual(list_to_latex_matrix(malformed), malform_rep)
