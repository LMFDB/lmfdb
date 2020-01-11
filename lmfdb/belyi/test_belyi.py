# -*- coding: utf-8 -*-
from lmfdb.tests import LmfdbTest


class BelyiTest(LmfdbTest):
    def check_args(self, path, text):
        L = self.tc.get(path, follow_redirects=True)
        assert text in L.get_data(as_text=True)

    def test_stats(self):
        L = self.tc.get("/Belyi/stats")
        assert "Galois orbits of Belyi maps" in L.get_data(as_text=True) and "proportion" in L.get_data(as_text=True)

    def test_random(self):
        self.check_args("/Belyi/random", "Monodromy group")

    def test_by_galmap_label(self):
        self.check_args("/Belyi/6T15-[5,4,4]-51-42-42-g1-b", "A_6")

    def test_passport_label(self):
        self.check_args("/Belyi/5T4-[5,3,3]-5-311-311-g0-a", "5T4-[5,3,3]-5-311-311-g0")

    def test_passport(self):
        self.check_args("/Belyi/9T33-[10,15,2]-522-531-22221-g0-a", "3.1.14175.1")

    # web pages

    def test_urls(self):
        self.check_args(
            "/Belyi/4T5-[4,3,2]-4-31-211-g0-a", "Belyi map 4T5-[4,3,2]-4-31-211-g0-a"
        )
        self.check_args(
            "/Belyi/4T5-[4,3,2]-4-31-211-g0-", "Passport 4T5-[4,3,2]-4-31-211-g0"
        )
        self.check_args(
            "/Belyi/4T5-[4,3,2]-4-31-211-g0", "Passport 4T5-[4,3,2]-4-31-211-g0"
        )
        self.check_args(
            "/Belyi/4T5-[4,3,2]-4-31-211-",
            "Belyi maps with group 4T5 and orders [4,3,2]",
        )
        self.check_args(
            "/Belyi/4T5-[4,3,2]-4-31-", "Belyi maps with group 4T5 and orders [4,3,2]"
        )
        self.check_args("/Belyi/4T5-[4,3,2]", "Belyi maps with group 4T5")

    # searches

    def test_deg_range(self):
        L = self.tc.get("/Belyi/?deg=2-7")
        assert "5T4-[5,3,3]-5-311-311-g0-a" in L.get_data(as_text=True)

    def test_group_search(self):
        self.check_args("/Belyi/?group=7T5", "7T5-[7,7,3]-7-7-331-g2-a")

    def test_abc_search(self):
        self.check_args("/Belyi/?abc=2-4", "6T10-[4,4,3]-42-42-33-g1-a")

    def test_abc_list_search(self):
        self.check_args("/Belyi/?abc_list=[7,6,6]", "7T7-[7,6,6]-7-3211-3211-g0-a")

    def test_genus_search(self):
        self.check_args("/Belyi/?genus=2", "6T6-[6,6,3]-6-6-33-g2-a")

    def test_orbit_size_search(self):
        self.check_args("/Belyi/?orbit_size=20-", "7T7-[6,10,4]-61-52-421-g1-a")

    def test_geom_type_search(self):
        self.check_args("/Belyi/?geomtype=H", "6T8-[4,4,3]-411-411-33-g0-a")

    def test_count_search(self):
        self.check_args("/Belyi/?count=20", "5T1-[5,5,5]-5-5-5-g2-c")

    # downloads

    def test_download(self):
        r"""
        Test download function
        """
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/7T6-%5B7%2C2%2C6%5D-7-22111-322-g0-a",
            follow_redirects=True,
        )
        assert (
            "phi := 1/2*(7*nu - 15)*x^7/(x^7 + 1/10*(28*nu + 7)*x^6 + 1/100*(-56*nu + 511)*x^5 + 1/40*(-672*nu - 1323)*x^4 + 1/20*(-42*nu - 63)*x^3 + 1/40*(1701*nu + 3024)*x^2 + 1/200*(-6237*nu - 11178));"
            in page.get_data(as_text=True)
        )
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/6T15-%5B5%2C5%2C5%5D-51-51-51-g1-c",
            follow_redirects=True,
        )
        assert (
            "phi := (1/3125*(162*nu - 81)*x^2 + 1/78125*(972*nu - 486)*x + 1/390625*(-1458*nu + 729))/(x^6 - 9/25*x^5 + 27/125*x^4 + 1/3125*(-162*nu - 54)*x^3 + 1/78125*(729*nu - 486)*x^2 + 1/9765625*(-2187*nu + 5832)*x + 1/244140625*(-2187*nu - 1458))*y + (1/3125*(-162*nu + 81)*x^3 + 1/156250*(1458*nu - 729)*x^2 + 1/9765625*(-2187*nu + 10935)*x + 1/488281250*(-4374*nu - 76545))/(x^6 - 9/25*x^5 + 27/125*x^4 + 1/3125*(-162*nu - 54)*x^3 + 1/78125*(729*nu - 486)*x^2 + 1/9765625*(-2187*nu + 5832)*x + 1/244140625*(-2187*nu - 1458));"
            in page.get_data(as_text=True)
        )
        page = self.tc.get(
            "/Belyi/download_galmap_to_magma/7T5-%5B7%2C7%2C3%5D-7-7-331-g2-a",
            follow_redirects=True,
        )
        assert (
            "phi := (1/2*x^2 + 2/5*x + 1/200*(nu + 5))/(x^5 + 6/5*x^4 + 1/50*(7*nu + 5)*x^3 + 1/250*(35*nu - 57)*x^2 + 1/10000*(91*nu - 345)*x + 1/12500*(-133*nu + 71))*y + 1/2;"
            in page.get_data(as_text=True)
        )
