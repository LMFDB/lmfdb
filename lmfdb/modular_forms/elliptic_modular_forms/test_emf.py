
from lmfdb.base import LmfdbTest

from flask import request

from views.emf_main import *
emf_logger.setLevel(0)

class CmfTest(LmfdbTest):
    def test_browse_page(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/")
        assert '/ModularForm/GL2/Q/holomorphic/24/6/1/">3' in page.data

    def test_delta(self):
        r"""
        Check that the Delta function is ok....
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/1/")        
        assert '24q^{2}' in page.data
        assert '84480q^{8}' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/1/12/1/a/")                
        assert '24q^{2}' in page.data
        assert '84480q^{8}' in page.data
        assert '0.518518518' in page.data
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/1/12/1/a/0/')
        assert '0.79212283' in page.data 

    def test_level11(self):
        r"""
        Check that the weight 2 form of level 11 works.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/11/2/1/a/")                
        assert '2q^{2}' in page.data
        assert '2q^{4}' in page.data
        assert '2.3561944901' in page.data
        ## We also check that the L-function works
        page = self.tc.get('/L/ModularForm/GL2/Q/holomorphic/11/2/1/a/0/')
        assert '0.253841860' in page.data
        
        
    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/0/")
        assert '24936' in page.data

    def test_empty(self):
        page = self.tc("ModularForm/GL2/Q/holomorphic/2/12/1/")
        assert 'is empty' in page.data
