# -*- coding: utf8 -*-
# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2017 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

import unittest2

from lmfdb.base import DoctestExampleTest


class ExampleUnitTest(unittest2.TestCase):
    """
    This is an example unittest. For this example, we will test
    DoctestExampleTest, from lmfdb/base.py
    """

    # Note that the docstring to this function is printed during testing
    def test_DoctestExampleTest(self):
        r"""
        Testing DoctestExampleTest.
        """
        ex = DoctestExampleTest(2)
        self.assertEqual(ex.__str__(), "I am 2")
