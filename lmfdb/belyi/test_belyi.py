from lmfdb.tests import LmfdbTest


class BelyiTest(LmfdbTest):
    def test_stats(self):
        L = self.tc.get("/Belyi/stats")
        assert "Galois orbits of Belyi maps" in L.get_data(as_text=True) and "proportion" in L.get_data(as_text=True)

    def test_random(self):
        self.check_args("/Belyi/random", "Monodromy group")

    def test_by_galmap_label(self):
        self.check_args("/Belyi/6T15-5.1_4.2_4.2-b", "A_6")

    def test_passport_label(self):
        self.check_args("/Belyi/5T4-5_3.1.1_3.1.1-a", "5T4-5_3.1.1_3.1.1")

    def test_passport(self):
        self.check_args("/Belyi/9T33-5.2.2_5.3.1_2.2.2.2.1-a", "3.1.14175.1")

    def test_smooth_equation(self):
        self.check_args("/Belyi/7T5-7_7_3.3.1-a", r"\frac{50000 x^{5} + 60000 x^{4} + \left(7000 \nu + 5000\right) x^{3} + 50000 x^{2} y + \left(7000 \nu - 11400\right) x^{2} + 40000 x y + \left(455 \nu - 1725\right) x + \left(500 \nu + 2500\right) y - 532 \nu + 284}{50000 x^{5} + 60000 x^{4} + \left(7000 \nu + 5000\right) x^{3} + \left(7000 \nu - 11400\right) x^{2} + \left(455 \nu - 1725\right) x - 532 \nu + 284}")
        self.check_args("/Belyi/7T5-7_7_3.3.1-a", r"y^{2} = x^{6} + \frac{4}{5} x^{5} + \left(\frac{13}{50} \nu - \frac{19}{50}\right) x^{4} + \left(\frac{21}{125} \nu - \frac{7}{25}\right) x^{3} + \left(-\frac{709}{10000} \nu + \frac{279}{10000}\right) x^{2} + \left(-\frac{153}{6250} \nu + \frac{67}{6250}\right) x + \frac{83}{15625} \nu + \frac{47}{15625}")

    def test_plane_equation(self):
        self.check_args("/Belyi/9T33-9_5.1.1.1.1_5.1.1.1.1-a", r"x^{9} t + \left(-126 x^{4} + 420 x^{3} - 540 x^{2} + 315 x - 70")

    # web pages

    def test_urls(self):
        # galmap
        self.check_args(
            "/Belyi/4T5-4_3.1_2.1.1-a", "Belyi map orbit 4T5-4_3.1_2.1.1-a"
        )
        # passport
        self.check_args(
            "/Belyi/4T5-4_3.1_2.1.1", "Passport 4T5-4_3.1_2.1.1"
        )

    # searches

    # for galmaps

    def test_deg_range(self):
        self.check_args("/Belyi/?deg=2-7", "5T3-4.1_4.1_2.2.1")
        self.not_check_args("/Belyi/?deg=2-7", "1T1-1_1_1")

    def test_group_search(self):
        self.check_args("/Belyi/?group=7T5", "7T5-7_7_3.3.1-a")
        self.not_check_args("/Belyi/?group=7T5", "1T1-1_1_1-a")

    def test_abc_search(self):
        self.check_args("/Belyi/?abc=2-4", "6T10-4.2_4.2_3.3-a")

    def test_abc_list_search(self):
        self.check_args("/Belyi/?abc_list=[7,6,6]", "7T7-7_3.2.1.1_3.2.1.1-a")
        self.not_check_args("/Belyi/?abc_list=[7,6,6]", "1T1-1_1_1-a")

    def test_genus_search(self):
        self.check_args("/Belyi/?g=2", "6T6-6_6_3.3-a")
        self.not_check_args("/Belyi/?g=2", "1T1-1_1_1-a")

    def test_orbit_size_search(self):
        self.check_args("/Belyi/?orbit_size=20-", "7T7-6.1_5.2_4.2.1-a")
        self.not_check_args("/Belyi/?orbit_size=20-", "1T1-1_1_1-a")

    def test_pass_size_search(self):
        self.check_args("/Belyi/?pass_size=6", "7T6-4.2.1_4.2.1_3.2.2-a")
        self.not_check_args("/Belyi/?pass_size=6", "1T1-1_1_1-a")

    def test_geom_type_search(self):
        self.check_args("/Belyi/?geomtype=H", "6T8-4.1.1_4.1.1_3.3-a")
        self.not_check_args("/Belyi/?pass_size=6", "1T1-1_1_1-a")

    def test_count_search(self):
        self.check_args("/Belyi/?count=20", "5T1-5_5_5-c")

    def test_field_search(self):
        self.check_args("Belyi/?field=Qsqrt-3", "6T15-4.2_4.2_4.2-a")
        self.not_check_args("Belyi/?field=Qsqrt-3", "1T1-1_1_1-a")

    def test_primitive_search(self):
        self.check_args("Belyi/?is_primitive=no", "4T1-4_4_1.1.1.1-a")
        self.not_check_args("Belyi/?is_primitive=no", "1T1-1_1_1-a")
        self.check_args("Belyi/?is_primitive=yes", "1T1-1_1_1-a")

    def test_primitivization_search(self):
        self.check_args("/Belyi/?primitivization=2T1-2_2_1.1-a", "4T1-4_4_1.1.1.1-a")
        self.not_check_args("/Belyi/?primitivization=2T1-2_2_1.1-a", "1T1-1_1_1-a")

    # for passports

    def test_deg_range_passports(self):
        self.check_args("/Belyi/?hst=Passports&deg=2-7", "5T3-4.1_4.1_2.2.1")
        self.not_check_args("/Belyi/?hst=Passports&deg=2-7", "1T1-1_1_1")

    def test_group_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&group=7T5", "7T5-7_7_3.3.1")
        self.not_check_args("/Belyi/?hst=Passports&group=7T5", "1T1-1_1_1")

    def test_abc_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&abc=2-4", "6T10-4.2_4.2_3.3")

    def test_abc_list_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&abc_list=[7,6,6]", "7T7-7_3.2.1.1_3.2.1.1")
        self.not_check_args("/Belyi/?abc_list=[7,6,6]", "1T1-1_1_1")

    def test_genus_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&g=2", "6T6-6_6_3.3")
        self.not_check_args("/Belyi/?hst=Passports&g=2", "1T1-1_1_1")

    def test_max_orbit_size_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&maxdegbf=10", "7T7-6.1_3.3.1_5.2")
        self.not_check_args("/Belyi/?hst=Passports&maxdegbf=10", "1T1-1_1_1")

    def test_pass_size_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&pass_size=6", "7T6-4.2.1_4.2.1_3.2.2")
        self.not_check_args("/Belyi/?hst=Passports&pass_size=6", "1T1-1_1_1")

    def test_geom_type_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&geomtype=H", "6T8-4.1.1_4.1.1_3.3")
        self.not_check_args("/Belyi/?hst=Passports&pass_size=6", "1T1-1_1_1")

    def test_count_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&count=20", "5T1-5_5_5")

    def test_primitive_search_passports(self):
        self.check_args("Belyi/?hst=Passports&is_primitive=no", "4T1-4_4_1.1.1.1")
        self.not_check_args("Belyi/?hst=Passports&is_primitive=no", "1T1-1_1_1")
        self.check_args("Belyi/?hst=Passports&is_primitive=yes", "1T1-1_1_1")

    def test_primitivization_search_passports(self):
        self.check_args("/Belyi/?hst=Passports&primitivization=2T1-2_2_1.1", "4T1-4_4_1.1.1.1")
        self.not_check_args("/Belyi/?hst=Passports&primitivization=2T1-2_2_1.1", "1T1-1_1_1")

    # downloads

    def test_download(self):
        r"""
        Test download function
        """
        # genus 0 example
        # in magma
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/7T6-7_2.2.1.1.1_3.2.2-a",
            follow_redirects=True,
        )
        assert (
            "phi := 1/2*(7*nu-15)*x^7/(x^7+1/10*(28*nu+7)*x^6+1/100*(-56*nu+511)*x^5+1/40*(-672*nu-1323)*x^4+1/20*(-42*nu-63)*x^3+1/40*(1701*nu+3024)*x^2+1/200*(-6237*nu-11178));"
            in page.get_data(as_text=True)
        )
        # in sage
        page = self.tc.get(
            "/Belyi/download_galmap_to_sage/7T6-7_2.2.1.1.1_3.2.2-a",
            follow_redirects=True,
        )
        assert (
            "phi = 1/2*(7*nu-15)*x^7/(x^7+1/10*(28*nu+7)*x^6+1/100*(-56*nu+511)*x^5+1/40*(-672*nu-1323)*x^4+1/20*(-42*nu-63)*x^3+1/40*(1701*nu+3024)*x^2+1/200*(-6237*nu-11178))"
            in page.get_data(as_text=True)
        )

        # genus 1 example
        # in magma
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/6T15-5.1_5.1_5.1-c",
            follow_redirects=True,
        )
        assert (
            "phi := (1/3125*(162*nu-81)*x^2+1/78125*(972*nu-486)*x+1/390625*(-1458*nu+729))/(x^6-9/25*x^5+27/125*x^4+1/3125*(-162*nu-54)*x^3+1/78125*(729*nu-486)*x^2+1/9765625*(-2187*nu+5832)*x+1/244140625*(-2187*nu-1458))*y+(1/3125*(-162*nu+81)*x^3+1/156250*(1458*nu-729)*x^2+1/9765625*(-2187*nu+10935)*x+1/488281250*(-4374*nu-76545))/(x^6-9/25*x^5+27/125*x^4+1/3125*(-162*nu-54)*x^3+1/78125*(729*nu-486)*x^2+1/9765625*(-2187*nu+5832)*x+1/244140625*(-2187*nu-1458));"
            in page.get_data(as_text=True)
        )
        # in sage
        page = self.tc.get(
            "/Belyi/download_galmap_to_sage/6T15-5.1_5.1_5.1-c",
            follow_redirects=True,
        )
        assert (
           "phi = (1/3125*(162*nu-81)*x^2+1/78125*(972*nu-486)*x+1/390625*(-1458*nu+729))/(x^6-9/25*x^5+27/125*x^4+1/3125*(-162*nu-54)*x^3+1/78125*(729*nu-486)*x^2+1/9765625*(-2187*nu+5832)*x+1/244140625*(-2187*nu-1458))*y+(1/3125*(-162*nu+81)*x^3+1/156250*(1458*nu-729)*x^2+1/9765625*(-2187*nu+10935)*x+1/488281250*(-4374*nu-76545))/(x^6-9/25*x^5+27/125*x^4+1/3125*(-162*nu-54)*x^3+1/78125*(729*nu-486)*x^2+1/9765625*(-2187*nu+5832)*x+1/244140625*(-2187*nu-1458))"
            in page.get_data(as_text=True)
        )
        # genus 2 example
        # in magma
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/7T5-7_7_3.3.1-a",
            follow_redirects=True,
        )
        assert (
            "phi := (1/2*x^2+2/5*x+1/200*(nu+5))/(x^5+6/5*x^4+1/50*(7*nu+5)*x^3+1/250*(35*nu-57)*x^2+1/10000*(91*nu-345)*x+1/12500*(-133*nu+71))*y+1/2;"
            in page.get_data(as_text=True)
        )
        # in sage
        page = self.tc.get(
            "/Belyi/download_galmap_to_sage/7T5-7_7_3.3.1-a",
            follow_redirects=True,
        )
        assert (
            "phi = (1/2*x^2+2/5*x+1/200*(nu+5))/(x^5+6/5*x^4+1/50*(7*nu+5)*x^3+1/250*(35*nu-57)*x^2+1/10000*(91*nu-345)*x+1/12500*(-133*nu+71))*y+1/2"
            in page.get_data(as_text=True)
        )

        # Underlying data link
        data = self.tc.get("/Belyi/data/7T5-7_7_3.3.1", follow_redirects=True).get_data(as_text=True)
        assert "maxdegbf" in data and "orbit_size" in data

        data = self.tc.get("/Belyi/data/7T5-7_7_3.3.1-a", follow_redirects=True).get_data(as_text=True)
        assert "friends" in data and "maxdegbf" in data and "portrait" in data

    # friends
    def test_friends(self):
        for url, friends in [
            ('/Belyi/4T5/4/4/3.1/a',
                ('Passport',
                    'Elliptic curve 48.a6',)
             ),
            ('/Belyi/5T3/5/4.1/4.1/a',
                ('Passport',
                    'Elliptic curve 2.0.4.1-1250.3-a3',)
             ),
            ('/Belyi/6T6/6/6/3.3/a',
                ('Passport',
                    'Genus 2 curve 1728.b.442368.1',)
             )
        ]:
            data = self.tc.get(url, follow_redirects=True).get_data(as_text=True)
            for friend in friends:
                assert friend in data
