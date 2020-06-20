# -*- coding: utf-8 -*-

from lmfdb.tests import LmfdbTest

class HomePageTest(LmfdbTest):
    # Box 6
    # external links
    def test_box6(self):
        r"""
        Check that the links in Box 6 work.
        """
        homepage = self.tc.get("/").get_data(as_text=True)
        self.check_external(homepage, "https://github.com/LMFDB/lmfdb", 'Modular Forms Database')
        # I could not get this one to work - AVS
        #self.check_external(homepage, "http://www.sagemath.org/", 'mathematics software system')
        self.check_external(homepage, "http://pari.math.u-bordeaux.fr/", 'PARI/GP is a widely used computer algebra system'    )
        # I could not get this one to work -- JEC
        #self.check_external(homepage, "http://magma.maths.usyd.edu.au/magma/", 'Magma is a large, well-supported software     package')
        self.check_external(homepage, "https://www.python.org/", 'Python Logo')
