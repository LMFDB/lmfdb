from lmfdb.tests import LmfdbTest


class AVTest(LmfdbTest):
    # All tests should pass
    def test_polynomial(self):
        r"""
        Check that the formatted polynomial displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/9/aj_bl", "1 - 9 x + 37 x^{2} - 81 x^{3} + 81 x^{4}")

    def test_display_field(self):
        r"""
        Check that the base field gets displayed correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/25/ac_b", r"\F_{5^{2}}")

    def test_frob_angles(self):
        r"""
        Check that the Frobenius angles display correctly
        """
        self.check_args("/Variety/Abelian/Fq/3/4/ab_a_i", "0.206216850513")

    def test_is_simple(self):
        r"""
        Check that is_simple is computed correctly, and that the decomposition information displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/4/3/ab_d_ad_g", ">simple")
        self.check_args("/Variety/Abelian/Fq/3/4/e_q_bg", "1.4.a")
        self.check_args("/Variety/Abelian/Fq/3/4/e_q_bg", '<a title="Simple abelian variety [av.simple]" knowl="av.simple" kwargs="">not simple</a>')

    def test_is_ordinary(self):
        r"""
        Check that is_ordinary is computed correctly
        """
        self.check_args("/Variety/Abelian/Fq/3/3/ad_i_aq", ">ordinary")
        self.check_args("/Variety/Abelian/Fq/2/61/ah_a", ">not ordinary")

    def test_is_supersingular(self):
        r"""
        Check that is_supersingular is computed correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/7/a_a", ">supersingular")
        self.check_args("/Variety/Abelian/Fq/2/71/ah_a", ">not supersingular")

    def test_slopes(self):
        r"""
        Check that display_slopes works
        """
        self.check_args("/Variety/Abelian/Fq/2/71/ah_a", "[0, 1/2, 1/2, 1]")

    def test_counts(self):
        r"""
        Check that length_A_counts and length_C_counts work
        """
        self.check_args("/Variety/Abelian/Fq/2/79/az_lj", "9468043770876073552")
        self.check_args("/Variety/Abelian/Fq/2/79/az_lj", "9468276088941449902")

    def test_display_number_fld(self):
        r"""
        Check that display_number_field works
        """
        self.check_args("/Variety/Abelian/Fq/2/4/ac_e", "4.0.125.1")
        # self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The number field of this isogeny class is not in the database.')
        # self.not_check_args("/Variety/Abelian/Fq/2/7/g_v", 'The number field of this isogeny class is not in the database.')

    def test_display_gal_gp(self):
        r"""
        Check that display_galois_group works
        """
        self.check_args("/Variety/Abelian/Fq/2/19/g_bt", "n=4&t=3")
        # self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The Galois group of this isogeny class is not in the database.')
        # self.not_check_args("/Variety/Abelian/Fq/2/27/f_n",'The Galois group of this isogeny class is not in the database.')

    def test_is_primitive(self):
        r"""
        Check that is_primitive is computed correctly, and that the base change information displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/9/e_l", "primitive")
        self.check_args("/Variety/Abelian/Fq/3/9/ai_bc_acx", "3.3.ac_ac_j")

    def test_newton_polygon_plot(self):
        r"""
        Check that the plot of the Newton polygon is included and computed correctly
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").get_data(as_text=True)
        # The following is part of the base64 encoded image of the Newton
        # polygon for this isogeny class.
        assert r"data:image/png;base64,iVBORw0KGgo" in page

    def test_circle_plot(self):
        r"""
        Check that the plot showing the roots of the Weil polynomial displays correctly
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").get_data(as_text=True)
        # The following is part of the base64 encoded image of the circle plot
        # for this isogeny class.
        assert r"data:image/png;base64,iVBORw0KGgo" in page

    def test_property_box(self):
        r"""
        Check that the property box displays.
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").get_data(as_text=True).replace("\n", "").replace(" ", "")
        assert r'<divclass="properties-body"><table><tr><tdclass="label">Label</td><td>2.4.ad_g</td></tr><tr>' in page
        assert r'<tdclass="label">Basefield</td><td>$\F_{2^{2}}$</td></tr><tr><tdclass="label">Dimension</td><td>' in page
        self.check_args("/Variety/Abelian/Fq/2/79/ar_go", "Principally polarizable")

    def test_split_Frobenius_angles(self):
        r"""
        Check that the Frobenius angles are split into multiple math elements
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").get_data(as_text=True)
        assert r"$\pm0.150432950460$, $\pm0.544835058382$" in page

    def test_av_download(self):
        r"""
        Test downloading on search results page.
        """
        data = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=sage&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D").get_data(as_text=True)
        self.assertTrue("Each entry in the following data list" in data)
        self.assertTrue("[1, -10, 50, -160, 360, -592, 720, -640, 400, -160, 32]" in data)
        response = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=gp&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D")
        self.assertTrue("Each entry in the following data list" in response.get_data(as_text=True))
        self.assertTrue("[1, -10, 50, -160, 360, -592, 720, -640, 400, -160, 32]" in response.get_data(as_text=True))
        response = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=magma&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D")
        self.assertTrue("Each entry in the following data list" in response.get_data(as_text=True))
        self.assertTrue("[1, -10, 50, -160, 360, -592, 720, -640, 400, -160, 32]" in response.get_data(as_text=True))

    def test_download_all(self):
        r"""
        Test downloading all stored data to text
        """

        page = self.tc.get('Variety/Abelian/Fq/download_all/1.81.r', follow_redirects=True)
        assert '"abvar_counts": [99, 6435, 532224, 43043715,' in page.get_data(as_text=True)

        page = self.tc.get('Variety/Abelian/Fq/download_all/3.17.d_b_act', follow_redirects=True)
        assert '"curve_counts": [21, 283, 4719, 84395' in page.get_data(as_text=True)

        text = self.tc.get('Variety/Abelian/Fq/data/3.17.d_b_act', follow_redirects=True).get_data(as_text=True)
        assert 'dim4_factors' in text and 'multiplicity' in text and 'brauer_invariants' in text

    def test_download_curves(self):
        r"""
        Test downloading all stored data to text
        """

        page = self.tc.get('Variety/Abelian/Fq/2.19.ae_w', follow_redirects=True)
        assert 'Curves to text' in page.get_data(as_text=True)

        page = self.tc.get('Variety/Abelian/Fq/download_curves/2.19.ae_w', follow_redirects=True)
        assert 'y^2=3*x^6+18*x^5+15*x^4+12*x^3+x^2+5*x+18' in page.get_data(as_text=True)

        page = self.tc.get('Variety/Abelian/Fq/5/3/ac_e_ai_v_abl', follow_redirects=True)
        assert 'Curves to text' not in page.get_data(as_text=True)

        page = self.tc.get('Variety/Abelian/Fq/download_curves/5.3.ac_e_ai_v_abl', follow_redirects=True)
        assert 'No curves for abelian variety isogeny class 5.3.ac_e_ai_v_abl' in page.get_data(as_text=True)
