# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest

class HGMTest(LmfdbTest):
    # TODO: create stats page
    #def test_stats(self):
        #self.check_args("Hypergeometric/Q/stats", "Monodromy")

def test_random_family(self):
    self.check_args("/Hypergeometric/Q/random_family", "Hypergeometric motive family")
    self.check_args("/Hypergeometric/Q/random_family", "Defining parameters")

def test_random_motive(self):
    self.check_args("/Hypergeometric/Q/random_motive", "Local information")
    self.not_check_args("/Hypergeometric/Q/random_motive", "Hypergeometric motive family")
