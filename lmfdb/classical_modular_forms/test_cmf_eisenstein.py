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

    def test_browse_page(self):
        r"""
        Check that browsing has the added option Is cuspidal
        """
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/").get_data(as_text=True)
        assert 'Is cuspidal' in data

    def test_dynamic_stats(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/dynamic_stats?char_order=2&col1=level&buckets1=1-1000%2C1001-10000&proportions=recurse&col2=weight&buckets2=1-8%2C9-316&search_type=DynStats")
        data = page.get_data(as_text=True)
        # The proportions are against the unconstrained number, which now includes the Eisenstein series.
        # Therefore, we update the percentages accordingly. 
        # Eventually should allow generation of statistics with respect to imposed constraints
        # for x in ["16576", "24174", "6172", "20.90%", "30.46%", "13.26%"]:
        for x in ["19943", "24174", "6448", "30.67%", "16.84%", "13.26%"]:
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
    
    def test_badp(self):
        data = self.tc.get("/ModularForm/GL2/Q/holomorphic/?level_primes=7&count=100").get_data(as_text=True)
        assert '7.2.E.a.a' in data
        assert '21.2.E.g.d' in data
    
    def test_level_bread(self):
        # At the moment testing data with Nk^2 <= 1000
        # update when loading more data
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/248/?is_cuspidal=no',
                           follow_redirects=True)
        assert '248.2.E.bc.d' in page.get_data(as_text=True)
        assert fr'\Q(\zeta_{{15}})' in page.get_data(as_text=True)
        assert '248.2.E.v.d' in page.get_data(as_text=True)
        assert fr'\Q(\zeta_{{10}})' in page.get_data(as_text=True)
        assert '248.2.E.q.d' in page.get_data(as_text=True)
        assert fr'\Q(\sqrt{{-3}})' in page.get_data(as_text=True)
        page = self.tc.get('/ModularForm/GL2/Q/holomorphic/248/?weight=10&level=9', follow_redirects=True)
        assert 'Results (7 matches)' in page.get_data(as_text=True)
        assert '9.10.E.c.b' in page.get_data(as_text=True)
        assert '1023' in page.get_data(as_text=True)