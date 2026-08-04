from lmfdb.tests import LmfdbTest
from lmfdb import db

# The g2c_curves_new dataset (6.2M curves) renumbered curves with EC-style
# labels (e.g. 1225.a1) and re-minimized the models.  Class letters and curve
# numbers were reassigned, so the old labels below were translated to the new
# label of the SAME curve by matching Lhash (isogeny class) and then the
# equation or the absolute Igusa invariants g2_inv (which are unchanged by
# re-minimization) within the class; e.g. 1369.a.50653.1 is now 1369.b2 and
# 65520.b.131040.1 is now 65520.fq1.
#
# g2c_endomorphisms_new, g2c_tamagawa_new and g2c_galrep_new are still being
# loaded on devmirror.  Tests needing them skip at runtime with the exact
# string "not yet loaded on devmirror" (grep for it to reactivate them); the
# original assertions are kept inside the guards.


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
        # 100000.s1 was 100000.a.200000.1
        L = self.tc.get("/Genus2Curve/Q/?cond=100000-1000000")
        assert "100000.s1" in L.get_data(as_text=True)

    def test_disc_range(self):
        # 336.a1 was 336.a.172032.1
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=100000-1000000")
        assert "336.a1" in L.get_data(as_text=True)

    def test_by_curve_label(self):
        # 169.a1 was 169.a.169.1: Jacobian is the square of an elliptic curve,
        # with Sato-Tate group E_6
        L = self.tc.get("/Genus2Curve/Q/169.a.169.1", follow_redirects=True)
        assert "E_6" in L.get_data(as_text=True) and "Sato-Tate" in L.get_data(
            as_text=True
        )
        # 15360.o2 was 15360.f.983040.2
        L3 = self.tc.get("/Genus2Curve/Q/15360/o/2", follow_redirects=True)
        assert r"N(\mathrm{U}(1)\times\mathrm{SU}(2))" in L3.get_data(as_text=True)
        need_endo(self)
        assert "square of" in L.get_data(as_text=True)
        # 1152.a1 was 1152.a.147456.1: product of the non-isogenous elliptic
        # curves 24.a and 48.a
        L2 = self.tc.get("/Genus2Curve/Q/1152/a/1", follow_redirects=True)
        assert "non-isogenous elliptic curve" in L2.get_data(as_text=True)
        assert "24.a" in L2.get_data(as_text=True)
        assert "48.a" in L2.get_data(as_text=True)
        assert "480.b" in L3.get_data(as_text=True)
        assert "32.a" in L3.get_data(as_text=True)

    def test_isogeny_class_label(self):
        # class 1369.b was 1369.a (curve 1369.b2 was 1369.a.50653.1),
        # with Sato-Tate group SU(2)xSU(2)
        L = self.tc.get("/Genus2Curve/Q/1369/b/")
        assert (
            "1369.b1" in L.get_data(as_text=True)
            and "1369.b2" in L.get_data(as_text=True)
            and r"\mathrm{SU}(2)\times\mathrm{SU}(2)" in L.get_data(as_text=True)
        )

    def test_Lfunction_link(self):
        # L-function instances still reference the old class letters in their
        # URLs, so this stays at 1369/a for now
        L = self.tc.get("/L/Genus2Curve/Q/1369/a", follow_redirects=True)
        assert "Motivic weight" in L.get_data(as_text=True)

    def test_twist_link(self):
        # the five twists below were 576.b.147456.1, 1152.a.147456.1,
        # 2304.b.147456.1, 4608.a.4608.1, 4608.b.4608.1; the recomputed
        # dataset has 280 curves with these G2 invariants, so show them all
        L = self.tc.get(
            "/Genus2Curve/Q/?g22=1016576&g20=5071050752/9&g21=195344320/9&count=300"
        )
        for label in [
            "576.c1",
            "1152.a1",
            "2304.c1",
            "4608.d1",
            "4608.j1",
        ]:
            assert label in L.get_data(as_text=True)

    def test_by_conductor(self):
        L = self.tc.get("/Genus2Curve/Q/15360/?count=200")
        for x in "abcdefghij":
            assert "15360." + x in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/15360/?abs_disc=169")
        assert "No matches" in L.get_data(as_text=True)

    def test_by_url_isogeny_class_label(self):
        L = self.tc.get("/Genus2Curve/Q/336/a/")
        assert "336.a1" in L.get_data(as_text=True)

    def test_by_url_curve_label(self):
        # ST groups come from the curve table and are always shown
        # 17689.b1 was 17689.e.866761.1 (RM curve)
        L2 = self.tc.get("/Genus2Curve/Q/17689/b/1", follow_redirects=True)
        assert (
            "simple" in L2.get_data(as_text=True) or "Simple" in L2.get_data(as_text=True)
        ) and r"\mathrm{SU}(2)\times\mathrm{SU}(2)" in L2.get_data(as_text=True)
        # 262144.g1 was 262144.d.524288.1 (QM curve)
        L3 = self.tc.get("Genus2Curve/Q/262144/g/1", follow_redirects=True)
        assert "J(E_2)" in L3.get_data(as_text=True)
        need_endo(self)
        # 1088.c2 was 1088.b.2176.1: two elliptic curve factors and
        # decomposing endomorphism algebra
        L = self.tc.get("/Genus2Curve/Q/1088/c/2", follow_redirects=True)
        assert "32.a1" in L.get_data(as_text=True) and "34.a3" in L.get_data(
            as_text=True
        )
        assert "quaternion algebra" in L3.get_data(as_text=True)
        # 4096.g1 was 4096.b.65536.1: square over a quadratic extension that
        # is CM over one extension and multiplication by a quaternion algebra
        # ramifying at infinity over another
        L4 = self.tc.get("Genus2Curve/Q/4096/g/1", follow_redirects=True)
        assert (
            "square of" in L4.get_data(as_text=True)
            and "2.2.8.1-64.1-a3" in L4.get_data(as_text=True)
            and r"\H" in L4.get_data(as_text=True)
            and "(CM)" in L4.get_data(as_text=True)
        )

    def test_by_url_isogeny_class_discriminant(self):
        # the old-format URL redirects by dropping the discriminant
        L = self.tc.get("/Genus2Curve/Q/15360/f/983040/", follow_redirects=True)
        assert "15360.f1" in L.get_data(as_text=True)
        # the curves of the class formerly labeled 15360.f (disc 983040) are
        # now 15360.o1 and 15360.o2
        L = self.tc.get("/Genus2Curve/Q/15360/o/")
        assert (
            "15360.o1" in L.get_data(as_text=True)
            and "15360.o2" in L.get_data(as_text=True)
        )

    def test_random(self):
        for _ in range(5):
            L = self.tc.get("/Genus2Curve/Q/random", follow_redirects=True)
            assert "Sato-Tate group" in L.get_data(as_text=True)

    def test_conductor_search(self):
        # 1225.a1 was 1225.a.6125.1
        L = self.tc.get("/Genus2Curve/Q/?cond=1225")
        assert "1225.a1" in L.get_data(as_text=True)

    def test_disc_search(self):
        # 1988.a1 was 1988.a.3976.1
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=3976")
        assert "1988.a1" in L.get_data(as_text=True)

    def test_download(self):
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=gp")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=sage")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=magma")

    def test_rational_weierstrass_points_search(self):
        # 360.a1 was 360.a.6480.1
        L = self.tc.get("/Genus2Curve/Q/?num_rat_wpts=4")
        assert "360.a1" in L.get_data(as_text=True)

    def test_torsion_search(self):
        # 1584.e1 was 1584.a.684288.1
        L = self.tc.get("/Genus2Curve/Q/?torsion=[2,2,2]")
        assert "1584.e1" in L.get_data(as_text=True)

    def test_torsion_order_search(self):
        # 1116.a1 was 1116.a.214272.1
        L = self.tc.get("/Genus2Curve/Q/?torsion_order=39")
        assert "1116.a1" in L.get_data(as_text=True)

    def test_two_selmer_rank_search(self):
        if not db.g2c_curves_new.count({"two_selmer_rank": {"$exists": True}}):
            self.skipTest("two_selmer_rank not yet loaded on devmirror")
        # 65520.fq1 was 65520.b.131040.1 (re-verify once loaded)
        L = self.tc.get("/Genus2Curve/Q/?two_selmer_rank=6")
        assert "65520.fq1" in L.get_data(as_text=True)

    def test_analytic_rank_search(self):
        # 440509.a1 was 440509.a.440509.1
        L = self.tc.get("/Genus2Curve/Q/?analytic_rank=4")
        assert "440509.a1" in L.get_data(as_text=True)

    def test_gl2_type_search(self):
        # 169.a1 was 169.a.169.1
        L = self.tc.get("/Genus2Curve/Q/?gl2_type=True")
        assert "169.a1" in L.get_data(as_text=True)

    def test_st_group_search(self):
        # 6075.b1 was 6075.a.18225.1
        L = self.tc.get("/Genus2Curve/Q/?st_group=J(E_6)")
        assert "6075.b1" in L.get_data(as_text=True)

    def test_st0_group_search(self):
        # 448.a1 was 448.a.448.1
        L = self.tc.get("/Genus2Curve/Q/?real_geom_end_alg=C x R")
        assert "448.a1" in L.get_data(as_text=True)

    def test_automorphism_group_search(self):
        # 196.a1 was 196.a.21952.1, 295.a1 was 295.a.295.2
        self.check_args("/Genus2Curve/Q/?aut_grp=12.4", "196.a1")
        self.check_args("/Genus2Curve/Q/?aut_grp_label=12.4", "196.a1")
        self.check_args("/Genus2Curve/Q/?aut_grp_id=%5B2,1%5D", "295.a1")

    def test_geometric_automorphism_group_search(self):
        # 4096.g1 was 4096.b.65536.1, 363.a2 was 363.a.43923.1
        self.check_args("/Genus2Curve/Q/?geom_aut_grp=48.29", "4096.g1")
        self.check_args("/Genus2Curve/Q/?geom_aut_grp_label=48.29", "4096.g1")
        self.check_args("/Genus2Curve/Q/?geom_aut_grp_id=%5B2,1%5D", "363.a2")

    def test_locally_solvable_serach(self):
        # In the recomputed data the locally non-solvable curves of conductor
        # 336 are 336.a3 and 336.a4 (the old data marked 336.a.172032.1 =
        # 336.a1 as non-solvable; the recomputation corrected this)
        L = self.tc.get("/Genus2Curve/Q/?locally_solvable=False&cond=336")
        assert "336.a3" in L.get_data(as_text=True)
        assert "336.a1" not in L.get_data(as_text=True)

    def test_sha_search(self):
        if not db.g2c_curves_new.count({"analytic_sha": {"$exists": True}}):
            self.skipTest("analytic_sha not yet loaded on devmirror")
        # labels translated from 114240.d.114240.1, 336.a.172032.1 and
        # 169.a.169.1; re-verify the sha values against the recomputed data
        # once analytic_sha is loaded
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=256")
        assert "114240.cg1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=3")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?has_square_sha=False")
        assert "336.a1" in L.get_data(
            as_text=True
        ) and "169.a1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?locally_solvable=True&has_square_sha=False")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=2&has_square_sha=True")
        assert "No matches" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?analytic_sha=2&has_square_sha=False")
        assert "336.a1" in L.get_data(as_text=True)

    def test_torsion(self):
        # 976.a1 was 976.a.999424.1
        L = self.tc.get("/Genus2Curve/Q/976/a/999424/1", follow_redirects=True)
        assert "\\Z/{29}\\Z" in L.get_data(as_text=True)

    def test_mwgroup(self):
        # 25913.b1 was 25913.a.25913.1: MW group Z x Z x Z; the generators
        # (and hence their heights) changed with the re-minimized model
        L = self.tc.get("/Genus2Curve/Q/25913/b/1", follow_redirects=True)
        assert "\\Z \\oplus \\Z \\oplus \\Z" in L.get_data(as_text=True)
        assert "0.359039" in L.get_data(as_text=True)
        assert "\\infty" in L.get_data(as_text=True)
        # 969306.bj1 was 969306.a.969306.1: MW group Z^3 x Z/2Z with a
        # generator of height 3.259671
        L = self.tc.get("/Genus2Curve/Q/969306/bj/1", follow_redirects=True)
        assert "\\Z \\oplus \\Z \\oplus \\Z \\oplus \\Z/{2}\\Z" in L.get_data(as_text=True)
        assert "3.259671" in L.get_data(as_text=True)
        assert "\\infty" in L.get_data(as_text=True)
        # 461.a1 was 461.a.461.2: trivial MW group
        L = self.tc.get("/Genus2Curve/Q/461/a/1", follow_redirects=True)
        assert "trivial" in L.get_data(as_text=True)

    def test_bsd_invariants(self):
        need_tamagawa(self)
        # 70450.b1 was 70450.c.704500.1; re-verify the displayed values
        # against the recomputed data once the tamagawa table is loaded
        L = self.tc.get("/Genus2Curve/Q/70450/b/1", follow_redirects=True)
        assert "upper bound" in L.get_data(as_text=True)
        assert "0.046457" in L.get_data(as_text=True)
        assert "16.52129" in L.get_data(as_text=True)
        assert "0.767540" in L.get_data(as_text=True)
        assert "rounded" in L.get_data(as_text=True)
        # 1253.a1 was 1253.a.1253.1
        L = self.tc.get("/Genus2Curve/Q/1253/a/1", follow_redirects=True)
        assert "0.207463" in L.get_data(as_text=True)
        assert "0.414927" in L.get_data(as_text=True)
        assert "twice a square" in L.get_data(as_text=True)

    def test_local_invariants(self):
        need_tamagawa(self)
        # 806069.b1 was 806069.a.806069.1
        L = self.tc.get("/Genus2Curve/Q/806069/b/1", follow_redirects=True)
        assert "1 + 5 T + 11 T^{2}" in L.get_data(as_text=True)
        assert "1 + 2 T + 127 T^{2}" in L.get_data(as_text=True)
        assert "1 + 22 T + 577 T^{2}" in L.get_data(as_text=True)

    def test_mfhilbert(self):
        # 12500.a1 was 12500.a.12500.1, with Hilbert modular form friend
        # 2.2.5.1-500.1-a
        L = self.tc.get("/Genus2Curve/Q/12500/a/1", follow_redirects=True)
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/12500/a/", follow_redirects=True)
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)

    def test_ratpts(self):
        # 792079.a1 was 792079.a.792079.1; the point coordinates changed with
        # the re-minimized model (verified against g2c_ratpts_new)
        L = self.tc.get("/Genus2Curve/Q/792079/a/1", follow_redirects=True)
        assert "(1 : 0 : 0)" in L.get_data(as_text=True)
        assert "(-2 : 7 : 1)" in L.get_data(as_text=True)
        # 126746.a1 was 126746.a.126746.1
        L = self.tc.get("/Genus2Curve/Q/126746/a/1", follow_redirects=True)
        assert "This curve has no" in L.get_data(as_text=True)
        # 3319.a1 was 3319.a.3319.1
        L = self.tc.get("/Genus2Curve/Q/3319/a/1", follow_redirects=True)
        assert "Known points" in L.get_data(as_text=True)
        # 14880.h2 was 14880.c.238080.2
        L = self.tc.get("/Genus2Curve/Q/14880/h/2", follow_redirects=True)
        assert "for this curve" in L.get_data(as_text=True)

    def test_endo_search(self):
        # first result for every search; translated from the old labels
        # (e.g. 249.a1 was 249.a.249.1).  CM x CM previously had no matches;
        # the recomputed dataset contains such curves (e.g. 8192.d1).
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

    # tests for searching by geometric invariants; the invariant values are
    # unchanged from the original tests (absolute invariants do not depend on
    # the model), and identify the curve formerly labeled 1369.a.50653.1,
    # now 1369.b2
    def test_igusa_clebsch_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[456%2C11220%2C2199936%2C202612]"
        )
        assert "1369.b2" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_igusa_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[228%2C296%2C-98568%2C-5640280%2C50653]"
        )
        assert "1369.b2" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_G2_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[616132666368%2F50653%2C94818816%2F1369%2C-3742848%2F37]"
        )
        assert "1369.b2" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)

    def test_badprimes_search(self):
        # 324.a1 was 324.a.648.1, 450.a1 was 450.a.2700.1, 169.a1 was
        # 169.a.169.1
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
        # 450.a1 (bad primes 2,3,5) matches but is beyond the first page
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=include&bad_primes=2%2C3&cond=450")
        assert "450.a1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_primes=2%2C3")
        assert "324.a1" in L.get_data(as_text=True)
        assert "169.a1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_primes=2%2C3&cond=450")
        assert "450.a1" in L.get_data(as_text=True)

    def test_related_objects(self):
        need_endo(self)
        # 20736.g1 was 20736.i.373248.1 and class 20736.g was 20736.i;
        # class 576.b was 576.a
        for url, friends in [
            (
                "/Genus2Curve/Q/20736/g/1",
                (
                    "L-function",
                    "Elliptic curve 576.f3",
                    "Elliptic curve 36.a4",
                    "Elliptic curve 2.0.8.1-324.3-a",
                    "Modular form 36.2.a.a",
                    "Modular form 576.2.a.f",
                    "Bianchi modular form 2.0.8.1-324.3-a",
                    "Hilbert modular form 2.2.24.1-36.1-a",
                    "Elliptic curve 2.2.24.1-36.1-a",
                    "Twists",
                ),
            ),
            (
                "/Genus2Curve/Q/20736/g/",
                (
                    "L-function",
                    "Elliptic curve 576.f",
                    "Elliptic curve 36.a",
                    "Modular form 36.2.a.a",
                    "Modular form 576.2.a.f",
                    "Bianchi modular form 2.0.8.1-324.3-a",
                    "Elliptic curve 2.0.8.1-324.3-a",
                    "Elliptic curve 2.2.24.1-36.1-a",
                    "Hilbert modular form 2.2.24.1-36.1-a",
                ),
            ),
            (
                "/Genus2Curve/Q/576/b/",
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
        # 576.b1 was 576.a.576.1
        data = self.tc.get("/Genus2Curve/Q/data/576.b1").get_data(as_text=True)
        assert ("g2c_curves_new" in data and "bad_lfactors" in data
                and "g2c_endomorphisms_new" in data
                and "g2c_ratpts_new" in data and "mw_gens" in data
                and "g2c_galrep_new" in data and "modell_image" in data
                and "g2c_tamagawa_new" in data)

    def test_jump(self):
        from sage.all import magma
        try:
            magma("1+1")
            # Check that giving defining polynomials for f,h works; the jump
            # lands on the curve isomorphic to y^2 + xy = x^5 + x + 1, which
            # is 49946.b1 with re-minimized model y^2 + x^2y = x^6 - x^5 - x
            L = self.tc.get("/Genus2Curve/Q/?jump=x%5E5%2Bx%2B1%2Cx", follow_redirects=True)
            assert "49946.b1" in L.get_data(as_text=True)
            assert "y^2 + x^2y = x^6 - x^5 - x" in L.get_data(as_text=True)

            # Check that giving a Weierstrass equation works, even without
            # explicit multiplication '*'; y^2 = x^5 - 2x^2 + 1 is 10592.a1
            # with re-minimized model y^2 = x^6 - 2x^4 - x
            L = self.tc.get("/Genus2Curve/Q/?jump=b%5E2%3Da%5E5-2a%5E2%2B1", follow_redirects=True)
            assert "10592.a1" in L.get_data(as_text=True)
            assert "y^2 = x^6 - 2x^4 - x" in L.get_data(as_text=True)

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
        # 961.a2 was 961.a.961.1: mod-l image data has not been loaded, so
        # the curve page reports that it has not been computed
        L = self.tc.get("/Genus2Curve/Q/961/a/2", follow_redirects=True)
        assert "Galois representation data has not been computed for this curve" in L.get_data(as_text=True)

        need_galrep(self)
        # A generic example: 976.a1 was 976.a.999424.1
        L = self.tc.get("/Genus2Curve/Q/976/a/1", follow_redirects=True)
        assert "2.6.1" in L.get_data(as_text=True)
        # A nongeneric example
        L = self.tc.get("/Genus2Curve/Q/961/a/2", follow_redirects=True)
        assert "3.72.2" in L.get_data(as_text=True)

    def test_mw_gens_table_partial_data(self):
        # the Mordell-Weil generator table must tolerate independently
        # incomplete auxiliary data (heights missing, None, or shorter than
        # the generator list) while the dataset is being recomputed; unknown
        # heights display as ?
        from lmfdb.genus2_curves.web_g2c import mw_gens_table
        r = db.g2c_ratpts_new.lucky({"label": "25913.b1"})
        if r is None or r.get("mw_gens") is None:
            self.skipTest("mw generator data for 25913.b1 not yet loaded on devmirror")
        invs, gens, hts, pts = r["mw_invs"], r["mw_gens"], r["mw_heights"], r["rat_pts"]
        # complete data renders the heights
        full = mw_gens_table(invs, gens, hts, pts)
        assert "0.359039" in full and "?" not in full
        # missing, empty, or short height lists must not raise
        assert "?" in mw_gens_table(invs, gens, None, pts)
        assert "?" in mw_gens_table(invs, gens, [], pts)
        short = mw_gens_table(invs, gens, hts[:1], pts)
        assert "0.359039" in short and "?" in short
