
from lmfdb.base import LmfdbTest

from flask import request
import unittest2

from views.emf_main import *
from . import emf_logger
emf_logger.setLevel(100)

class EmfTest(LmfdbTest):

    def runTest():
        pass
    def test_browse_page(self):
        r"""
        Check browsing for elliptic modular forms
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/")
        assert '"/ModularForm/GL2/Q/holomorphic/24/?group=0">24' in page.data
        assert '"/ModularForm/GL2/Q/holomorphic/23/12/1/?group=0">19' in page.data

    @unittest2.skip("Long tests for many newform spaces, should be run & pass before any release")
    def test_many(self):
        levels = range(1,41)
        weights = range(2,22,2)
        for N in levels:
            for k in weights:
                for g in range(2):
                    print("testing (N,k,g) = (%s,%s,%s)" % (N,k,g))
                    url  = "/ModularForm/GL2/Q/holomorphic/{0}/{1}/?group={2}".format(N,k,g)
                    rv = self.tc.get(url,follow_redirects=True)
                    self.assertTrue(rv.status_code==200,"Request failed for {0}".format(url))
                    self.assertFalse('Error:' in rv.data,"Error in the data for {0}".format(url))

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

    def test_triv_character(self):
        r"""
        Check that some forms from issue 815 work.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/2/8/1/a/")
        assert '1016q^{7}' in page.data
        assert '1.955904533356' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/3/6/1/a/")
        assert '168q^{8}' in page.data

    def test_non_triv_character(self):
        r"""
        Check that non-trivial characters are also working.
        """
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/2/4/a/")
        assert r'where \(\zeta_{6}=e^{\frac{2\pi i}{ 6 } }\) is a primitive 6-th root of unity.' in page.data
        assert r'\(\mathstrut+\) \(\bigl(2 \zeta_{6} \) \(\mathstrut-  2\bigr)q^{3} \)' in page.data
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/10/4/9/a/")
        assert r'where</div> \(\alpha ^{2} \) \(\mathstrut +\mathstrut  4\)\(\mathstrut=0\)' in page.data
        assert r'\(\mathstrut-\) \(\alpha  q^{3} \)' in page.data

    def test_get_args(self):
        page = self.tc.get("/ModularForm/GL2/Q/holomorphic/13/10/1/")
        assert '24936' in page.data

    def test_empty(self):
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/2/2/1/")
        assert 'no newforms' in page.data


    def test_not_in_db(self):
        # The following redirects to "ModularForm/GL2/Q/holomorphic/12000/12/"
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/0/", follow_redirects=True)
        assert 'The database does not currently contain' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/1/")
        assert 'do not have' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12000/12/0/a/", follow_redirects=True)
        assert 'The database does not currently contain' in page.data

    def test_character_validation(self):
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/120/12/x/")
        assert 'The character number should be an integer' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12/10/20/")
        assert 'The character number should be a positive integer less than or equal to and coprime to the level' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12/10/4/")
        assert 'The character number should be a positive integer less than or equal to and coprime to the level' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/12/10/5/")
        assert 'Newforms of weight 10' in page.data

    def test_restrict_range(self):
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/6/12/?group=0", follow_redirects=True)
        assert 'Decomposition of \( S_{12}^{\mathrm{new}}(6) \) into' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/6/12/?group=1", follow_redirects=True)
        assert 'The table below gives the dimensions of the spaces of' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/ranges/?level=6-8&weight=12&group=0", follow_redirects=True)
        assert 'The table below gives the dimensions of the space of' in page.data
        page = self.tc.get("ModularForm/GL2/Q/holomorphic/ranges/?level=6&weight=12-20&group=1", follow_redirects=True)
        assert 'The table below gives the dimensions of the space of' in page.data
        #page = self.tc.get("", follow_redirects=True)
        #assert '' in page.data
        
    def test_character_parity(self):
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/99/3/?group=1',
                           follow_redirects=True)
        self.assertFalse('n/a' in page.data)

    def test_hide(self):
        r"""
        Test that very large Fourier coefficients are not shown.
        """
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/25/36/1/')
        assert 'The Fourier coefficients of this newform are large.' in page.data

    def test_coefficient_fields(self):
        r"""
        Test the display of coefficient fields.
        """
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/9/8/1/')
        assert 'Minimal polynomial' in page.data
        assert '\Q(\sqrt{10})' in page.data
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/11/6/1/')
        assert '3.3.54492.1' in page.data
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/18/4/1/')
        assert 'Minimal polynomial' not in page.data

    def test_download(self):
        r"""
        Test download function
        """
        response = self.tc.post('ModularForm/GL2/Q/holomorphic/Download/',
                             content_type='multipart/form-data',
                                data={'level': 25, 'weight': 36, 'character': 1, 'label': 'f', 'number': 10, 'format': 'sage', 'download': 'coefficients'}, follow_redirects=True)
        assert "NumberField(x^16 - 380304819268*x^14" in response.data
        response = self.tc.post('ModularForm/GL2/Q/holomorphic/Download/',
                             content_type='multipart/form-data',
                                data={'level': 25, 'weight': 36, 'character': 1, 'label': 'f', 'number': 800, 'format': 'embeddings', 'download': 'coefficients'}, follow_redirects=True)
        assert "799	-5.0969" in response.data

    def test_galois_conjugate(self):
        r"""
        Testing that we link to Galois conjugate spaces
        And don't say anything stupid about the space
        """
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/32/2/29/')
        assert "This space is a Galois conjugate of" in page.data
        assert "/ModularForm/GL2/Q/holomorphic/32/2/5/" in page.data
        assert "There are no newforms" not in page.data
        assert "empty" not in page.data
        assert "Decomposition" not in page.data


    def test_nontriv_zero_space(self):
        r"""
        Test that a space that is nontrivially zero is clickable and the page tells us that the space has no newforms.
        """
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/5/4/')
        assert "ModularForm/GL2/Q/holomorphic/5/4/4" in page.data
        page = self.tc.get('ModularForm/GL2/Q/holomorphic/5/4/4/')
        assert "There are no newforms" in page.data
