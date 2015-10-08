
from lmfdb.base import LmfdbTest

from flask import request

from views.emf_main import *

class EmfTest(LmfdbTest):

    def runTest():
        pass
    def test_browse_page(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/")
        assert '"/ModularForm/GL2/Q/holomorphic/24/?character=1">24' in page.data
        assert '"/ModularForm/GL2/Q/holomorphic/23/12/1/">19' in page.data

    def test_delta(self):
        r"""
        Check that the Delta function is ok....
        Recall that this version uses the old urls...
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/1/")
        assert '24q^{2}' in page.data
        assert '84480q^{8}' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/1/a/")
        assert '24q^{2}' in page.data
        assert '84480q^{8}' in page.data
        assert '0.2993668' in page.data
        # The following is wrong!
        #assert '0.5185' in page.data
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/1/a/0/')
        assert '0.7921' in page.data 

    def test_level11(self):
        r"""
        Check that the weight 2 form of level 11 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/1/a/")
        assert '2q^{2}' in page.data
        assert '2q^{4}' in page.data
        assert '2.3561' in page.data
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/1/a/0/')
        assert '0.2538' in page.data

    def test_non_triv_character(self):
        r"""
        Check that non-trivial characters are also working.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/2/4/a/")
        assert r'\(  \left( {}\right.\)\( {}- a \)\( {}-  1\left.\right)q^{2} \)' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/4/9/a/")
        assert r'\( {}-\) \(  aq^{3} \)' in page.data

    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/1/")
        assert '24936' in page.data

    def test_empty(self):
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/2/2/1/")
        assert 'is empty' in page.data


    def test_not_in_db(self):
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/0/")
        assert 'n/a' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/1/")
        #assert 'not available yet' in page.data
        assert 'This space is empty' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/0/a/")
        assert 'n/a' in page.data
