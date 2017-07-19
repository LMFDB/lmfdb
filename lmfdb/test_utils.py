# -*- coding: utf8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2017 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import unittest2

from lmfdb.utils import truncatenumber

class UtilsTest(unittest2.TestCase):
    """
    An example of unit tests that are not based on the website itself.
    """

    def test_truncatenumber(self):
        r"""
        Testing utility: truncatenumber
        """
        self.assertEqual(truncatenumber(1.000001, 5), "1")
        self.assertEqual(truncatenumber(1.123456, 5), "1.123")
        self.assertEqual(truncatenumber(-1.123456, 5), "-1.123")
        self.assertEqual(truncatenumber(0.000002, 5), "0")
