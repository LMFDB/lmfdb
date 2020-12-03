from lmfdb.tests import LmfdbTest

class HomePageTest(LmfdbTest):
    # All tests should pass
    #
    # The page itself
    def test_page(self):
        r"""
        Check that the elliptic curve/Q search & browse page works.
        """
        homepage = self.tc.get("/EllipticCurve/Q/").get_data(as_text=True)
        assert 'Label or coefficients' in homepage

    #
    # Link to stats page
    def test_stats(self):
        r"""
        Check that the link to the stats page works.
        """
        homepage = self.tc.get("/EllipticCurve/Q/").get_data(as_text=True)
        self.check(homepage, "/EllipticCurve/Q/stats",
                   'Distribution of <a title="Rank of an elliptic curve over a number field [ec.rank]" knowl="ec.rank" kwargs="">rank</a>')

    #
    # Link to random curve
    def test_random(self):
        r"""
        Check that the link to a random curve works.
        """
        homepage = self.tc.get("/EllipticCurve/Q/").get_data(as_text=True)
        self.check(homepage, "/EllipticCurve/Q/random",
                   'Minimal Weierstrass equation')

    #
    # Browsing links
    def test_browse(self):
        r"""
        Check that the browsing links work.
        """
        homepage = self.tc.get("/EllipticCurve/Q/").get_data(as_text=True)
        t = "?conductor=100-999"
        assert t in homepage
        self.check_args("/EllipticCurve/Q/%s" % t,
                        '[1, 0, 0, 1, 1]')
        t = "?rank=4"
        assert t in homepage
        self.check_args("/EllipticCurve/Q/%s" % t,
                        '[1, -1, 0, -79, 289]')
        t = "?torsion=16"
        assert t in homepage
        self.check_args("/EllipticCurve/Q/%s" % t,
                        '266910.ck5')

    #
    # Jump to specfic curve or class
    def test_jump(self):
        r"""
        Check that the link to a specific curve works.
        """
        self.check_args("/EllipticCurve/Q/?jump=11.a2",
                        r'\(y^2+y=x^3-x^2-10x-20\)')
        self.check_args("/EllipticCurve/Q/?jump=389.a",
                        'Elliptic curves in class 389.a')
        self.check_args("/EllipticCurve/Q/?jump=%5B0%2C1%2C1%2C-2%2C0%5D", '\\(\\Z^2\\)')
        self.check_args("/EllipticCurve/Q/?jump=%5B-3024%2C+46224%5D+",
                        '\\(\\Z^2\\)')

    #
    # Various search combinations
    def test_search(self):
        r"""
        Check that various search combinations work.
        """
        self.check_args("/EllipticCurve/Q/?conductor=100-200&count=100",
                        '[0, -1, 1, -887, -10143]')
        self.check_args_with_timeout("/EllipticCurve/Q/?rank=0&torsion=2&sha=4&count=100",
                        '[0, -1, 0, -10560, -414180]')
        self.check_args("/EllipticCurve/Q/?conductor=&jinv=-4096%2F11&count=100",
                        '169136.i3')
        self.check_args("/EllipticCurve/Q/?torsion_structure=%5B2%2C4%5D&sha=&count=100",
                        '[0, 1, 0, -1664, -9804]')
        self.check_args_with_timeout("/EllipticCurve/Q/?&surj_primes=&surj_quantifier=include&nonsurj_primes=2%2C3&count=100",
                        '[1, -1, 1, -24575, 1488935]')
        self.check_args_with_timeout("/EllipticCurve/Q/?&surj_primes=&surj_quantifier=exactly&nonsurj_primes=5&optimal=on&count=100",
                        '[1, -1, 0, -1575, 751869]')
        self.check_args("EllipticCurve/Q/?conductor=990&surj_quantifier=include&optimal=on",
                        '990h3')
