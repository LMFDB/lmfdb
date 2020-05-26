# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class HomePageTest(LmfdbTest):
    # All tests should pass
    #
    # The acknowledgments page
    def test_acknowledgements(self):
        homepage = self.tc.get("/acknowledgment").get_data(as_text=True)
        assert 'American Institute of Mathematics' in homepage

    #
    # Link to workshops page
    def test_workshops(self):
        homepage = self.tc.get("/acknowledgment/activities").get_data(as_text=True)
        assert "Computational Aspects of the Langlands Program" in homepage

    #
    # External Links on workshops page
    def test_workshoplinks(self):
        homepage = self.tc.get("/acknowledgment/activities").get_data(as_text=True)
        self.check_external(
            homepage,
            "http://people.oregonstate.edu/~swisherh/CRTNTconference/index.html",
            "Galois",
        )
        self.check_external(
            homepage,
            "http://www2.warwick.ac.uk/fac/sci/maths/research/events/2013-2014/nonsymp/lmfdb/",
            "elliptic curves over number fields",
        )
        self.check_external(
            homepage, "https://hobbes.la.asu.edu/lmfdb-14/", "Arizona State University"
        )

        self.check_external(
            homepage,
            "http://www.maths.bris.ac.uk/~maarb/public/lmfdb2013.html",
            "Development of algorithms",
        )
        self.check_external(
            homepage,
            # "http://icms.org.uk/workshops/onlinedatabases"
            "https://aimath.org/pastworkshops/onlinedata.html",
            "development of new software tools",
        )
        self.check_external(
            homepage, "http://www.msri.org/programs/262", "algebraic number fields"
        )
        self.check_external(
            homepage,
            "http://aimath.org/pastworkshops/lfunctionsandmf.html",
            "L-functions and modular forms",
        )
