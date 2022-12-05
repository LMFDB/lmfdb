# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class HomePageTest(LmfdbTest):
    # All tests should pass
    #
    # The acknowledgments page
    def test_acknowledgments(self):
        homepage = self.tc.get("/acknowledgment").get_data(as_text=True)
        assert 'American Institute of Mathematics' in homepage

    #
    # Link to workshops page
    def test_workshops(self):
        homepage = self.tc.get("/acknowledgment/activities").get_data(as_text=True)
        assert "Computational Aspects of the Langlands Program" in homepage
