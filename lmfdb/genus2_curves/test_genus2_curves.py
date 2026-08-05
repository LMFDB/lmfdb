import re

from sage.all import PolynomialRing, QQ

from lmfdb.tests import LmfdbTest
from lmfdb.genus2_curves.web_g2c import (comp_poly, simplify_hyperelliptic,
                                         simplify_hyperelliptic_point,
                                         simplify_hyperelliptic_scale)


class Genus2Test(LmfdbTest):

    # All tests should pass
    def test_stats(self):
        L = self.tc.get("/Genus2Curve/Q/stats")
        assert "Sato-Tate groups" in L.get_data(
            as_text=True
        ) and "proportion" in L.get_data(as_text=True)

    def test_cond_range(self):
        L = self.tc.get("/Genus2Curve/Q/?cond=100000-1000000")
        assert "100000.a.200000.1" in L.get_data(as_text=True)

    def test_disc_range(self):
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=100000-1000000")
        assert "336.a.172032.1" in L.get_data(as_text=True)

    def test_by_curve_label(self):
        L = self.tc.get("/Genus2Curve/Q/169.a.169.1", follow_redirects=True)
        assert "square of" in L.get_data(as_text=True) and "E_6" in L.get_data(
            as_text=True
        )
        L = self.tc.get("/Genus2Curve/Q/1152.a.147456.1", follow_redirects=True)
        assert (
            "non-isogenous elliptic curve" in L.get_data(as_text=True)
            and "24.a" in L.get_data(as_text=True)
            and "48.a" in L.get_data(as_text=True)
        )
        L = self.tc.get("/Genus2Curve/Q/15360.f.983040.2", follow_redirects=True)
        assert (
            r"N(\mathrm{U}(1)\times\mathrm{SU}(2))" in L.get_data(as_text=True)
            and "480.b" in L.get_data(as_text=True)
            and "32.a" in L.get_data(as_text=True)
        )

    def test_isogeny_class_label(self):
        L = self.tc.get("/Genus2Curve/Q/1369/a/")
        assert (
            "1369.1" in L.get_data(as_text=True)
            and "50653.1" in L.get_data(as_text=True)
            and r"\mathrm{SU}(2)\times\mathrm{SU}(2)" in L.get_data(as_text=True)
        )

    def test_Lfunction_link(self):
        L = self.tc.get("/L/Genus2Curve/Q/1369/a", follow_redirects=True)
        assert "Motivic weight" in L.get_data(as_text=True)

    def test_twist_link(self):
        L = self.tc.get("/Genus2Curve/Q/?g22=1016576&g20=5071050752/9&g21=195344320/9")
        for label in [
            "576.b.147456.1",
            "1152.a.147456.1",
            "2304.b.147456.1",
            "4608.a.4608.1",
            "4608.b.4608.1",
        ]:
            assert label in L.get_data(as_text=True)

    def test_by_conductor(self):
        L = self.tc.get("/Genus2Curve/Q/15360/")
        for x in "abcdefghij":
            assert "15360." + x in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/15360/?abs_disc=169")
        assert "No matches" in L.get_data(as_text=True)

    def test_by_url_isogeny_class_label(self):
        L = self.tc.get("/Genus2Curve/Q/336/a/")
        assert "336.a.172032.1" in L.get_data(as_text=True)

    def test_by_url_curve_label(self):
        # Two elliptic curve factors and decomposing endomorphism algebra:
        L = self.tc.get("/Genus2Curve/Q/1088/b/2176/1")
        assert "32.a1" in L.get_data(as_text=True) and "34.a3" in L.get_data(
            as_text=True
        )
        # RM curve:
        L = self.tc.get("/Genus2Curve/Q/17689/e/866761/1")
        assert (
            "simple" in L.get_data(as_text=True) or "Simple" in L.get_data(as_text=True)
        ) and r"\mathrm{SU}(2)\times\mathrm{SU}(2)" in L.get_data(as_text=True)
        # QM curve:
        L = self.tc.get("Genus2Curve/Q/262144/d/524288/1")
        assert "quaternion algebra" in L.get_data(
            as_text=True
        ) and "J(E_2)" in L.get_data(as_text=True)
        L = self.tc.get("Genus2Curve/Q/4096/b/65536/1")
        # Square over a quadratic extension that is CM over one extension and
        # multiplication by a quaternion algebra ramifying at infinity over another
        assert (
            "square of" in L.get_data(as_text=True)
            and "2.2.8.1-64.1-a3" in L.get_data(as_text=True)
            and r"\H" in L.get_data(as_text=True)
            and "(CM)" in L.get_data(as_text=True)
        )

    def test_by_url_isogeny_class_discriminant(self):
        L = self.tc.get("/Genus2Curve/Q/15360/f/983040/")
        assert (
            "15360.f.983040.1" in L.get_data(as_text=True)
            and "15360.f.983040.2" in L.get_data(as_text=True)
            and "15360.d.983040.1" not in L.get_data(as_text=True)
        )

    def test_random(self):
        for _ in range(5):
            L = self.tc.get("/Genus2Curve/Q/random", follow_redirects=True)
            assert "Sato-Tate group" in L.get_data(as_text=True)

    def test_conductor_search(self):
        L = self.tc.get("/Genus2Curve/Q/?cond=1225")
        assert "1225.a.6125.1" in L.get_data(as_text=True)

    def test_disc_search(self):
        L = self.tc.get("/Genus2Curve/Q/?abs_disc=3976")
        assert "1988.a.3976.1" in L.get_data(as_text=True)

    def test_download(self):
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=gp")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=sage")
        self.tc.get("/Genus2Curve/Q/?query={'abs_disc':3976}&download=magma")

    def test_rational_weierstrass_points_search(self):
        L = self.tc.get("/Genus2Curve/Q/?num_rat_wpts=4")
        assert "360.a.6480.1" in L.get_data(as_text=True)

    def test_torsion_search(self):
        L = self.tc.get("/Genus2Curve/Q/?torsion=[2,2,2]")
        assert "1584.a.684288.1" in L.get_data(as_text=True)

    def test_torsion_order_search(self):
        L = self.tc.get("/Genus2Curve/Q/?torsion_order=39")
        assert "1116.a.214272.1" in L.get_data(as_text=True)

    def test_two_selmer_rank_search(self):
        L = self.tc.get("/Genus2Curve/Q/?two_selmer_rank=6")
        assert "65520.b.131040.1" in L.get_data(as_text=True)

    def test_analytic_rank_search(self):
        L = self.tc.get("/Genus2Curve/Q/?analytic_rank=4")
        assert "440509.a.440509.1" in L.get_data(as_text=True)

    def test_gl2_type_search(self):
        L = self.tc.get("/Genus2Curve/Q/?gl2_type=True")
        assert "169.a.169.1" in L.get_data(as_text=True)

    def test_st_group_search(self):
        L = self.tc.get("/Genus2Curve/Q/?st_group=J(E_6)")
        assert "6075.a.18225.1" in L.get_data(as_text=True)

    def test_st0_group_search(self):
        L = self.tc.get("/Genus2Curve/Q/?real_geom_end_alg=C x R")
        assert "448.a.448.1" in L.get_data(as_text=True)

    def test_automorphism_group_search(self):
        self.check_args('/Genus2Curve/Q/?aut_grp_label=12.4', '196.a.21952.1')
        self.check_args('/Genus2Curve/Q/?aut_grp_id=%5B2,1%5D', '295.a.295.2')

    def test_geometric_automorphism_group_search(self):
        self.check_args('/Genus2Curve/Q/?geom_aut_grp_label=48.29', '4096.b.65536.1')
        self.check_args('/Genus2Curve/Q/?geom_aut_grp_id=%5B2,1%5D', '363.a.43923.1')

    def test_locally_solvable_serach(self):
        L = self.tc.get("/Genus2Curve/Q/?locally_solvable=False")
        assert "336.a.172032.1" in L.get_data(as_text=True)

    def test_sha_search(self):
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
        L = self.tc.get("/Genus2Curve/Q/976/a/999424/1")
        assert "\\Z/{29}\\Z" in L.get_data(as_text=True)

    def test_mwgroup(self):
        L = self.tc.get("/Genus2Curve/Q/25913/a/25913/1")
        assert "\\Z \\oplus \\Z \\oplus \\Z" in L.get_data(as_text=True)
        assert "-x^3 - z^3" in L.get_data(as_text=True)
        assert "0.375585" in L.get_data(as_text=True)
        assert "\\infty" in L.get_data(as_text=True)
        assert "6.2.1658432.2" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/969306/a/969306/1")
        assert "\\Z \\oplus \\Z \\oplus \\Z \\oplus \\Z/{2}\\Z" in L.get_data(as_text=True)
        assert "16y" in L.get_data(as_text=True) and "2xz^2 + 11z^3" in L.get_data(as_text=True)
        assert "3.259671" in L.get_data(as_text=True)
        assert "\\infty" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/461/a/461/2")
        assert "trivial" in L.get_data(as_text=True)

    def test_bsd_invariants(self):
        L = self.tc.get("/Genus2Curve/Q/70450/c/704500/1")
        assert "upper bound" in L.get_data(as_text=True)
        assert "0.046457" in L.get_data(as_text=True)
        assert "16.52129" in L.get_data(as_text=True)
        assert "0.767540" in L.get_data(as_text=True)
        assert "rounded" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/1253/a/1253/1")
        assert "0.207463" in L.get_data(as_text=True)
        assert "0.414927" in L.get_data(as_text=True)
        assert "twice a square" in L.get_data(as_text=True)

    def test_local_invariants(self):
        L = self.tc.get("/Genus2Curve/Q/806069/a/806069/1")
        assert "1 + 5 T + 11 T^{2}" in L.get_data(as_text=True)
        assert "1 + 2 T + 127 T^{2}" in L.get_data(as_text=True)
        assert "1 + 22 T + 577 T^{2}" in L.get_data(as_text=True)

    def test_mfhilbert(self):
        L = self.tc.get("/Genus2Curve/Q/12500/a/12500/1")
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/12500/a/")
        assert "2.2.5.1-500.1-a" in L.get_data(as_text=True)

    def test_ratpts(self):
        L = self.tc.get("/Genus2Curve/Q/792079/a/792079/1")
        assert "(-15 : -6579 : 14)" in L.get_data(as_text=True)
        assert "(13 : -4732 : 20)" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/126746/a/126746/1")
        assert "everywhere" in L.get_data(as_text=True)
        assert "This curve has no" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/3319/a/3319/1")
        assert "Known points" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/14880/c/238080/2")
        assert "rational points are known" in L.get_data(as_text=True)
        assert "for this curve" in L.get_data(as_text=True)

    def test_simplified_model_points(self):
        # 400.a.409600.1 has h = 0 and content(4f+h^2) = 4, so y-coordinates are
        # divided by sqrt(4) = 2 and not by the content 4: the simplified equation
        # equals the minimal one here, and the points must come through unchanged.
        fh = [[1, 0, 4, 0, 4, 0, 1], []]
        assert simplify_hyperelliptic_scale(fh) == 2
        R = PolynomialRing(QQ, ['x', 'z'])
        x, z = R.gens()
        g = sum(c*x**i*z**(6-i) for i, c in enumerate(simplify_hyperelliptic(fh)))
        pts = [[1, -1, 0], [1, 1, 0], [0, -1, 1], [0, 1, 1]]
        for pt in pts:
            X, Y, Z = simplify_hyperelliptic_point(fh, pt)
            assert [X, Y, Z] == pt
            assert Y**2 == g(X, Z)
        L = self.tc.get("/Genus2Curve/Q/400/a/409600/1")
        page = L.get_data(as_text=True)
        # the simplified-model snippet builds its points on Csim, and they are the
        # points above rather than the halved ones the content used to produce
        for pt in pts:
            assert "Csim![%s,%s,%s]" % tuple(pt) in page
        assert "(0 : -1/2 : 1)" not in page
        # nor does the simplified Mordell-Weil table pick up a factor of 1/2
        assert "1/2z^3" not in page

    def test_simplified_model_mw_gens(self):
        # 336.a.172032.1 is y^2 + (x^3 + xz^2)y = -x^6 + 15x^4z^2 - 75x^2z^4 - 56z^6
        # with a generator recorded as 3x^2 - 32z^2 = 0, 6y = -35xz^2.  Since
        # 6y = yD clears a denominator, the simplified relation multiplies h by 6
        # too: 6Y = 2*(-35xz^2) + 6*(x^3 + xz^2) = 6x^3 - 64xz^2.
        fh = [[-56, 0, -75, 0, 15, 0, -1], [0, 1, 0, 1]]
        assert simplify_hyperelliptic_scale(fh) == 1
        R = PolynomialRing(QQ, ['x', 'z'])
        x, z = R.gens()
        yD = comp_poly(fh, 6)(x, -35*x*z**2, z)
        assert yD == 6*x**3 - 64*x*z**2
        assert yD != x**3 - 69*x*z**2  # only one copy of h, the old behavior
        # the generator is 2-torsion, so yD vanishes on 3x^2 - 32z^2 = 0
        assert yD == 2*x*(3*x**2 - 32*z**2)
        L = self.tc.get("/Genus2Curve/Q/336/a/172032/1")
        page = L.get_data(as_text=True)
        assert "-35xz^2" in page  # minimal model, unchanged
        assert "6x^3 - 64xz^2" in page
        assert "x^3 - 69xz^2" not in page

    def test_model_code_snippets(self):
        url = "/Genus2Curve/Q/169/a/169/1"
        page = self.tc.get(url).get_data(as_text=True)
        assert "Cmin := HyperellipticCurve(R![0, 0, 0, 0, 1, 1], R![1, 1, 0, 1])" in page
        assert "Csim, pi := SimplifiedModel(Cmin);" in page
        # every point is built on the model it belongs to, with no stale bare C
        assert "Cmin![" in page and "Csim![" in page
        assert not re.search(r"(?<![A-Za-z])C!\[", page)
        # the download defines each object before it is used
        magma = self.tc.get(url + "/download/magma").get_data(as_text=True)
        assert (magma.index("Cmin := HyperellipticCurve(f, h);")
                < magma.index("Csim := SimplifiedModel(Cmin);")
                < magma.index("J := Jacobian(Csim);"))

    def test_endo_search(self):
        # first result for every search
        for endo, text in [
            ("Q", "249.a.249.1"),
            ("RM", "529.a.529.1"),
            ("CM", "3125.a.3125.1"),
            ("QM", "20736.l.373248.1"),
            ("Q x Q", "294.a.294.1"),
            ("CM x Q", "448.a.448.2"),
            ("CM x CM", "No matches"),
            ("M_2(Q)", "169.a.169.1"),
            ("M_2(CM)", "2916.b.11664.1"),
        ]:
            L = self.tc.get("/Genus2Curve/Q/?geom_end_alg={}".format(endo))
            assert text in L.get_data(as_text=True)

    # tests for searching by geometric invariants
    def test_igusa_clebsch_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[456%2C11220%2C2199936%2C202612]"
        )
        assert "1369.a.50653.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[456%2C11220%2C2199936%2C202612]"
        )
        assert "1369.a.50653.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)

    def test_igusa_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[228%2C296%2C-98568%2C-5640280%2C50653]"
        )
        assert "1369.a.50653.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)

    def test_G2_search(self):
        L = self.tc.get(
            "/Genus2Curve/Q/?geometric_invariants=[616132666368%2F50653%2C94818816%2F1369%2C-3742848%2F37]"
        )
        assert "1369.a.50653.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)

    def test_badprimes_search(self):
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=exactly&bad_primes=2%2C3")
        assert "324.a.648.1" in L.get_data(as_text=True)
        assert "450.a.2700.1" not in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=exclude&bad_primes=2%2C3")
        assert "324.a.648.1" not in L.get_data(as_text=True)
        assert "450.a.2700.1" not in L.get_data(as_text=True)
        assert "169.a.169.1" in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_quantifier=include&bad_primes=2%2C3")
        assert "324.a.648.1" in L.get_data(as_text=True)
        assert "450.a.2700.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)
        L = self.tc.get("/Genus2Curve/Q/?bad_primes=2%2C3")
        assert "324.a.648.1" in L.get_data(as_text=True)
        assert "450.a.2700.1" in L.get_data(as_text=True)
        assert "169.a.169.1" not in L.get_data(as_text=True)

    def test_related_objects(self):
        for url, friends in [
            (
                "/Genus2Curve/Q/20736/i/373248/1",
                (
                    "L-function",
                    "Genus 2 curve 20736.i",
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
                "/Genus2Curve/Q/20736/i/",
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
                "/Genus2Curve/Q/576/a/",
                (
                    "L-function",
                    "Elliptic curve 2.2.8.1-9.1-a",
                    "Modular form 24.2.d.a",
                    "Hilbert modular form 2.2.8.1-9.1-a",
                ),
            ),
        ]:
            data = self.tc.get(url).get_data(as_text=True)
            for friend in friends:
                assert friend in data

    def test_underlying_data(self):
        data = self.tc.get("/Genus2Curve/Q/data/576.a.576.1").get_data(as_text=True)
        assert ('g2c_curves' in data and 'bad_lfactors' in data and
                'g2c_endomorphisms' in data and 'factorsQQ_base' in data
                and 'g2c_ratpts' in data and 'mw_gens_v' in data
                and 'g2c_galrep' in data and 'modell_image' in data
                and 'g2c_tamagawa' in data and 'tamagawa_number' in data
                and 'g2c_plots' in data and "data:image/png;base64" in data)

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
        # A generic example
        L = self.tc.get("/Genus2Curve/Q/976/a/999424/1")
        assert "2.6.1" in L.get_data(as_text=True)

        # A nongeneric example
        L = self.tc.get("/Genus2Curve/Q/961/a/961/1")
        assert "3.72.2" in L.get_data(as_text=True)
        assert "Galois representation data has not been computed for this curve" in L.get_data(as_text=True)
