from lmfdb.tests import LmfdbTest


class HomePageTest(LmfdbTest):
    # Test external Links on workshops page
    def test_workshoplinks(self):
        homepage = self.tc.get("/acknowledgment/activities").get_data(as_text=True)
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
        # Skip MSRI link - it redirects to SLMath which is now a JavaScript SPA
        # self.check_external(
        #     homepage, "http://www.msri.org/programs/262", "algebraic number fields"
        # )
        self.check_external(
            homepage,
            "http://aimath.org/pastworkshops/lfunctionsandmf.html",
            "L-functions and modular forms",
        )
