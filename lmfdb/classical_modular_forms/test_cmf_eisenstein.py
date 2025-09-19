from lmfdb.tests import LmfdbTest
import unittest

from . import cmf_logger
cmf_logger.setLevel(100)

class CmfTest(LmfdbTest):
    def runTest(self):
        pass

    def test_expression_divides(self):
        # checks search of conductors dividing 1000
        self.check_args('/ModularForm/GL2/Q/holomorphic/?level_type=divides&level=1000', '40.2.E.f.a')

    def test_dynamic_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/dynamic_stats?char_order=2&col1=level&buckets1=1-1000%2C1001-10000&proportions=recurse&col2=weight&buckets2=1-8%2C9-316&search_type=DynStats")
        data = page.get_data(as_text=True)
        # The proportions are against the unconstrained number, which now includes the Eisenstein series.
        # Therefore, we update the percentages accordingly. 
        # Eventually should allow generation of statistics with respect to imposed constraints
        # for x in ["16576", "24174", "6172", "20.90%", "30.46%", "13.26%"]:
        for x in ["17228", "24174", "6208", "20.67%", "30.54%", "13.26%"]:
            assert x in data

    def test_sidebar(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Labels").get_data(as_text=True)
        assert 'Labels for classical modular forms' in data
        # Making sure that this is the version containing Eisenstein labels
        assert 'Eisenstein' in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Completeness").get_data(as_text=True)
        assert "Completeness of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Reliability").get_data(as_text=True)
        assert "Reliability of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/Source").get_data(as_text=True)
        assert "Source of classical modular form data" in data
        # Making sure that this is the version containing Eisenstein information
        assert "Eisenstein newforms" in data

    