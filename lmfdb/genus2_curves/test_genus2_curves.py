from lmfdb.tests import LmfdbTest
from lmfdb import db

# The g2c_curves_new dataset (6.2M curves) uses EC-style labels (e.g. 1225.a1)
# and some auxiliary tables are still being loaded on devmirror.  Tests that
# need data from an unloaded table skip at runtime (grep for "not yet loaded on
# devmirror" to reactivate them once the load completes).


def need_endo(test):
    if not db.g2c_endomorphisms_new.count():
        test.skipTest("g2c_endomorphisms_new not yet loaded on devmirror")


def need_tamagawa(test):
    if not db.g2c_tamagawa_new.count():
        test.skipTest("g2c_tamagawa_new not yet loaded on devmirror")


def need_galrep(test):
    if not db.g2c_galrep_new.count():
        test.skipTest("g2c_galrep_new not yet loaded on devmirror")


class Genus2Test(LmfdbTest):

    # All tests should pass
    def test_stats(self):
        L = self.tc.get("/Genus2Curve/Q/stats")
        assert "Sato-Tate groups" in L.get_data(
            as_text=True
        ) and "proportion" in L.get_data(as_text=True)

    def test_cond_range(self):
        L = self.tc.get("/Genus2Curve/Q/?cond=100000-1000000")
        assert "100000.a1" in L.get_data(as_text=True)

    def test_disc_range(self):
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=100000-1000000")
        assert "336.a1" in L.get_data(as_text=True)

    def test_by_curve_label(self):
        L = self.tc.get("/Genus2Curve/Q/169.a.169.1", follow_redirects=True)
        assert "E_6" in L.get_data(as_text=True) and "Sato-Tate" in L.get_data(
            as_text=True
        )
        need_endo(self)
        assert "square of" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/1152.a.147456.1", follow_redirects=True)
        assert "non-isogenous elliptic curve" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/15360.f.983040.2", follow_redirects=True)
        assert r"N(\mathrm{U}(1)\times\mathrm{SU}(2))" in L.get_data(as_text=True)

    def test_isogeny_class_label(self):
        L = self.tc.get("/Genus2Curve/Q/1369/a/")
        assert (
            "1369.a1" in L.get_data(as_text=True)
            and "Bad L-factors" in L.get_data(as_text=True)
            and "Sato-Tate group" in L.get_data(as_text=True)
        )

    def test_Lfunction_link(self):
        L = self.tc.get("/L/Genus2Curve/Q/1369/a", follow_redirects=True)
        assert "Motivic weight" in L.get_data(as_text=True)

    def test_twist_link(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?g22=1016576&g20=5071050752/9&g21=195344320/9"
        )
        for label in [
            "576.c1",
            "1152.a1",
            "1728.a1",
            "2304.c1",
            "4608.d1",
        ]:
            assert label in L.get_data(as_text=True)

    def test_by_conductor(self):
        L = self.tc.get("/Genus2Curve/Q/15360/")
        for x in "ad":
            assert "15360." + x in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/15360/?abs_disc=169")
        assert "No matches" in L.get_data(as_text=True)

    def test_by_url_isogeny_class_label(self):
        L = self.tc.get("/Genus2Curve/Q/336/a/")
        assert "336.a1" in L.get_data(as_text=True)

    def test_by_url_curve_label(self):
        need_endo(self)
        # Two elliptic curve factors and decomposing endomorphism algebra:
        L = self.tc.get("/Genus2Curve/Q/1088/b/2176/1", follow_redirects=True)
        assert "32.a1" in L.get_data(as_text=True) and "34.a3" in L.get_data(
            as_text=True
        )
        # RM curve:
        L = self.tc.get("/Genus2Curve/Q/17689/e/866761/1", follow_redirects=True)
        assert (
            "simple" in L.get_data(as_text=True) or "Simple" in L.get_data(as_text=True)
        ) and r"\mathrm{SU}(2)\times\mathrm{SU}(2)" in L.get_data(as_text=True)
        # QM curve:
        L = self.tc.get("Genus2Curve/Q/262144/d/524288/1", follow_redirects=True)
        assert "quaternion algebra" in L.get_data(
            as_text=True
        ) and "J(E_2)" in L.get_data(as_text=True)
        L = self.tc.get("Genus2Curve/Q/4096/b/65536/1", follow_redirects=True)
        # Square over a quadratic extension that is CM over one extension and
        # multiplication by a quaternion algebra ramifying at infinity over another
        assert (
            "square of" in L.get_data(as_text=True)
            and r"\H" in L.get_data(as_text=True)
            and "(CM)" in L.get_data(as_text=True)
        )

    def test_by_url_isogeny_class_discriminant(self):
        L = self.tc.get("/Genus2Curve/Q/15360/f/983040/", follow_redirects=True)
        assert "15360.f1" in L.get_data(as_text=True)

    def test_random(self):
        for _ in range(5):
            L = self.tc.get("/Genus2Curve/Q/random", follow_redirects=True)
            assert "Sato-Tate group" in L.get_data(as_text=True)

    def test_conductor_search(self):
        L = self.tc.get("/Genus2Curve/Q/?cond=1225")
        assert "1225.a1" in L.get_data(as_text=True)

    def test_disc_search(self):
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=3976")
        assert "1988.a1" in L.get_data(as_text=True)

    def test_download(self):
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=gp")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=sage")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=magma")

    def test_rational_weierstrass_points_search(self):
        L = self.tc.get("/Genus2Curve/Q/?num_rat_wpts=4")
        assert "225.a3" in L.get_data(as_text=True)

    def test_torsion_search(self):
        L = self.tc.get("/Genus2Curve/Q/?torsion=[2,2,2]")
        assert "315.a2" in L.get_data(as_text=True)

    def test_torsion_order_search(self):
        L = self.tc.get("/Genus2Curve/Q/?torsion_order=39")
        assert "1116.a1" in L.get_data(as_text=True)

    def test_two_selmer_rank_search(self):
        if not db.g2c_curves_new.count({"two_selmer_rank": {"$exists": True}}):
            self.skipTest("two_selmer_rank not yet loaded on devmirror")
        L = self.tc.get("/Genus2Curve/Q/?two_selmer_rank=6")
        assert "65520.b.131040.1" in L.get_data(as_text=True)

    def test_analytic_rank_search(self):
        L = self.tc.get("/Genus2Curve/Q/?analytic_rank=4")
        assert "440509.a1" in L.get_data(as_text=True)

    def test_gl2_type_search(self):
        L = self.tc.get("/Genus2Curve/Q/?gl2_type=True")
        assert "169.a1" in L.get_data(as_text=True)

    def test_st_group_search(self):
        L = self.tc.get("/Genus2Curve/Q/?st_group=J(E_6)")
        assert "3600.k1" in L.get_data(as_text=True)

    def test_st0_group_search(self):
        L = self.tc.get("/Genus2Curve/Q/?real_geom_end_alg=C x R")
        assert "378.a1" in L.get_data(as_text=True)

    def test_automorphism_group_search(self):
        self.check_args('/Genus2Curve/Q/?aut_grp=12.4', '196.a1')
        self.check_args('/Genus2Curve/Q/?aut_grp_label=12.4', '196.a1')
        self.check_args('/Genus2Curve/Q/?aut_grp_id=%5B2,1%5D', '295.a1')

    def test_geometric_automorphism_group_search(self):
        self.check_args('/Genus2Curve/Q/?geom_aut_grp=48.29', '576.a1')
        self.check_args('/Genus2Curve/Q/?geom_aut_grp_label=48.29', '576.a1')
        self.check_args('/Genus2Curve/Q/?geom_aut_grp_id=%5B2,1%5D', '363.a1')

    def test_locally_solvable_serach(self):
        L = self.tc.get("/Genus2Curve/Q/?locally_solvable=False")
        assert "196.a3" in L.get_data(as_text=True)

    def test_sha_search(self):
        if not db.g2c_curves_new.count({"analytic_sha": {"$exists": True}}):
            self.skipTest("analytic_sha not yet loaded on devmirror")
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=256")
        assert "114240.d.114240.1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=3")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?has_square_sha=False")
        assert "336.a.172032.1" in L.get_data(
            as_text=True
        ) and "169.a.169.1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?locally_solvable=True&has_square_sha=False")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=2&has_square_sha=True")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=2&has_square_sha=False")
        assert "336.a.172032.1" in L.get_data(as_text=True)

    def test_torsion(self):
        L = self.tc.get("/Genus2Curve/Q/976/a/999424/1", follow_redirects=True)
        assert "\\Z/{29}\\Z" in L.get_data(as_text=True)

    def test_mwgroup(self):
        L = self.tc.get("/Genus2Curve/Q/25913/a/25913/1", follow_redirects=True)
        assert "Mordell-Weil group" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/969306/a/969306/1", follow_redirects=True)
        assert "Mordell-Weil group" in L.get_data(as_text=True)

    def test_bsd_invariants(self):
        need_tamagawa(self)
        L = self.tc.get("/Genus2Curve/Q/70450/c/704500/1", follow_redirects=True)
        assert "upper bound" in L.get_data(as_text=True)
        assert "rounded" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/1253/a/1253/1", follow_redirects=True)
        assert "twice a square" in L.get_data(as_text=True)

    def test_local_invariants(self):
        need_tamagawa(self)
        L = self.tc.get("/Genus2Curve/Q/806069/a/806069/1", follow_redirects=True)
        assert "1 + 5 T + 11 T^{2}" in L.get_data(as_text=True)
        assert "1 + 2 T + 127 T^{2}" in L.get_data(as_text=True)
        assert "1 + 22 T + 577 T^{2}" in L.get_data(as_text=True)

    def test_mfhilbert(self):
        need_endo(self)
        L = self.tc.get("/Genus2Curve/Q/12500/a/12500/1", follow_redirects=True)
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/12500/a/", follow_redirects=True)
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)

    def test_ratpts(self):
        L = self.tc.get("/Genus2Curve/Q/792079/a/792079/1", follow_redirects=True)
        assert "(1 : 0 : 0)" in L.get_data(as_text=True)
        assert "(-2 : 7 : 1)" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/126746/a/126746/1", follow_redirects=True)
        assert "This curve has no" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/3319/a/3319/1", follow_redirects=True)
        assert "Known points" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/14880/c/238080/2", follow_redirects=True)
        assert "for this curve" in L.get_data(as_text=True)

    def test_endo_search(self):
        # first result for every search
        for endo, text in [
            ("Q", "249.a1"),
            ("RM", "529.a1"),
            ("CM", "3125.a1"),
            ("QM", "8100.o1"),
            ("Q x Q", "255.a1"),
            ("CM x Q", "378.a1"),
            ("CM x CM", "8192.d1"),
            ("M_2(Q)", "121.a1"),
            ("M_2(CM)", "576.a1"),
        ]:
            L = self.tc.get("/Genus2Curve/Q/?geom_end_alg={}".format(endo))
            assert text in L.get_data(as_text=True)

    # tests for searching by geometric invariants
    # (invariant values updated for the re-minimized models in g2c_curves_new)
    def test_igusa_clebsch_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[1135%2C37120%2C12877120%2C103737344]"
        )
        assert "1369.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_igusa_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[4540%2C462870%2C-16619660%2C-72425473325%2C849816322048]"
        )
        assert "1369.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_G2_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[1883559343459375%2F829898752%2C9145656770625%2F179437568%2C-3909762875%2F9699328]"
        )
        assert "1369.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_badprimes_search(self):
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=exactly&bad_primes=2%2C3")
        assert "324.a1" in L.get_data(as_text=True)
        assert "450.a1" not in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=exclude&bad_primes=2%2C3")
        assert "324.a1" not in L.get_data(as_text=True)
        assert "450.a1" not in L.get_data(as_text=True)
        assert "169.a1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=include&bad_primes=2%2C3")
        assert "324.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)
        # 450.a1 (bad primes 2,3,5) matches but is beyond the first page of results
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=include&bad_primes=2%2C3&cond=450")
        assert "450.a1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_primes=2%2C3")
        assert "324.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_primes=2%2C3&cond=450")
        assert "450.a1" in L.get_data(as_text=True)

    def test_related_objects(self):
        need_endo(self)
        for url, friends in [
            (
                "/Genus2Curve/Q/20736/i/373248/1",
                (
                    "L-function",
                    "Elliptic curve 576.f3",
                    "Elliptic curve 36.a4",
                    "Twists",
                ),
            ),
            (
                "/Genus2Curve/Q/576/a/",
                (
                    "L-function",
                    "Elliptic curve 2.2.8.1-9.1-a",
                    "Modular form 24.2.d.a",
                    "Hilbert modular form 2.2.8.1-9.1-a",
                ),
            ),
        ]:
            data = self.tc.get(url, follow_redirects=True).get_data(as_text=True)
            for friend in friends:
                assert friend in data

    def test_underlying_data(self):
        data = self.tc.get("/Genus2Curve/Q/data/576.a1").get_data(as_text=True)
        assert ('g2c_curves_new' in data and 'bad_lfactors' in data
                and 'g2c_endomorphisms_new' in data
                and 'g2c_ratpts_new' in data and 'mw_gens' in data
                and 'g2c_galrep_new' in data and 'modell_image' in data
                and 'g2c_tamagawa_new' in data)

    def test_jump(self):
        from sage.all import magma
        try:
            magma('1+1')
            # Check that giving defining polynomials for f,h works
            L = self.tc.get('/Genus2Curve/Q/?jump=x%5E5%2Bx%2B1%2Cx', follow_redirects=True)
            assert "y^2 + xy = x^5 + x + 1" in L.get_data(as_text=True)

            # Check that giving a Weierstrass equation works, even without explicit multiplication '*'
            L = self.tc.get("/Genus2Curve/Q/?jump=b%5E2%3Da%5E5-2a%5E2%2B1", follow_redirects=True)
            assert "$y^2 = x^5 - 2x^2 + 1$" in L.get_data(as_text=True)

            # Check that variables are only single characters
            L = self.tc.get("/Genus2Curve/Q/?jump=(banana)%5E2%3Dx%5E5%2B1", follow_redirects=True)
            assert "is not in two variables" in L.get_data(as_text=True)

            # Check that curves not of genus 2 fail
            L = self.tc.get("/Genus2Curve/Q/?jump=y^2+%3D+x^10+-+1", follow_redirects=True)
            assert "invalid genus 2 curve" in L.get_data(as_text=True)

            # Check that there are only two variables present
            L = self.tc.get("/Genus2Curve/Q/?jump=y%5E2+%3D+x+%2B+a", follow_redirects=True)
            assert "is not in two variables" in L.get_data(as_text=True)
        except (RuntimeError, TypeError) as the_error:
            if str(the_error).startswith("unable to start magma"):
                pass
            else:
                raise

    def test_galrep(self):
        # A nongeneric example: mod-l image data has not been loaded, so the
        # curve page reports that it has not been computed
        L = self.tc.get("/Genus2Curve/Q/961/a/961/1", follow_redirects=True)
        assert "Galois representation data has not been computed for this curve" in L.get_data(as_text=True)

        need_galrep(self)
        # A generic example
        L = self.tc.get("/Genus2Curve/Q/976/a/999424/1", follow_redirects=True)
        assert "2.6.1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/961/a/961/1", follow_redirects=True)
        assert "3.72.2" in L.get_data(as_text=True)
