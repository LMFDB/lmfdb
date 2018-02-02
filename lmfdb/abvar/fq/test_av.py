from lmfdb.base import LmfdbTest

class AVTest(LmfdbTest):

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).data

    def not_check_args(self, path, text):
        assert not(text in self.tc.get(path, follow_redirects=True).data)

    # All tests should pass
    def test_polynomial(self):
        r"""
        Check that the formatted polynomial displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/9/aj_bl",'1-9x+37x^{2}-81x^{3}+81x^{4}')

    def test_display_field(self):
        r"""
        Check that the base field gets displayed correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/25/ac_b",'\F_{5^2}')

    def test_frob_angles(self):
        r"""
        Check that the Frobenius angles display correctly
        """
        self.check_args("/Variety/Abelian/Fq/3/4/ab_a_i",'0.206216850513')

    def test_is_simple(self):
        r"""
        Check that is_simple is computed correctly, and that the decomposition information displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/4/3/ab_d_ad_g",'simple')
        self.check_args("/Variety/Abelian/Fq/3/4/e_q_bg",'1.4.a')
        self.not_check_args("/Variety/Abelian/Fq/3/4/e_q_bg",'simple')

    def test_is_ordinary(self):
        r"""
        Check that is_ordinary is computed correctly
        """
        self.check_args("/Variety/Abelian/Fq/3/3/ad_i_aq",'ordinary')
        self.not_check_args("/Variety/Abelian/Fq/2/61/ah_a",'ordinary')

    def test_is_supersingular(self):
        r"""
        Check that is_supersingular is computed correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/7/a_a", 'supersingular')
        self.not_check_args("/Variety/Abelian/Fq/2/71/ah_a", 'supersingular')

    def test_slopes(self):
        r"""
        Check that display_slopes works
        """
        self.check_args("/Variety/Abelian/Fq/2/71/ah_a",'[0, 1/2, 1/2, 1]')

    def test_counts(self):
        r"""
        Check that length_A_counts and length_C_counts work
        """
        self.check_args("/Variety/Abelian/Fq/2/79/az_lj",'89648252036631997180633484850766696704')
        self.check_args("/Variety/Abelian/Fq/2/79/az_lj",'9468276088941449902')

    def test_display_number_fld(self):
        r"""
        Check that display_number_field works
        """
        self.check_args("/Variety/Abelian/Fq/2/4/ac_e",'4.0.125.1')
        #self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The number field of this isogeny class is not in the database.')
        #self.not_check_args("/Variety/Abelian/Fq/2/7/g_v", 'The number field of this isogeny class is not in the database.')

    def test_display_gal_gp(self):
        r"""
        Check that display_galois_group works
        """
        self.check_args("/Variety/Abelian/Fq/2/19/g_bt", 'n=4&t=3')
        #self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The Galois group of this isogeny class is not in the database.')
        #self.not_check_args("/Variety/Abelian/Fq/2/27/f_n",'The Galois group of this isogeny class is not in the database.')

    def test_is_primitive(self):
        r"""
        Check that is_primitive is computed correctly, and that the base change information displays correctly
        """
        self.check_args("/Variety/Abelian/Fq/2/9/e_l",'primitive')
        self.check_args("/Variety/Abelian/Fq/3/9/ai_bc_acx",'3.3.ac_ac_j')

    def test_newton_polygon_plot(self):
        r"""
        Check that the plot of the Newton polygon is included and computed correctly
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").data
        # The following is part of the base64 encoded image of the Newton
        # polygon for this isogeny class.
        assert "4S8eKLeWaDFgkQAKBLwgPyECAAQFeEB%2BQlQACALggPKIMA" in page

    def test_circle_plot(self):
        r"""
        Check that the plot showing the roots of the Weil polynomial displays correctly
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").data
        # The following is part of the base64 encoded image of the circle plot
        # for this isogeny class.
        assert "gMA4O7CwsJ06NAhDqLDaVBAYEkcQAcA4EccRIezo" in page

    def test_property_box(self):
        r"""
        Check that the property box displays.
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").data.replace("\n","").replace(" ","")
        assert '<divclass="properties-body"><table><tr><tdclass="label">Label</td><td>2.4.ad_g</td></tr><tr><tdclass="label">BaseField</td><td>$\F_{2^2}$</td></tr><tr><tdclass="label">Dimension</td><td>' in page
        self.check_args("/Variety/Abelian/Fq/2/79/ar_go",'Principally polarizable')

    def test_split_Frobenius_angles(self):
        r"""
        Check that the Frobenius angles are split into multiple mathjax boxes
        """
        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").data
        assert r"$\pm0.15043295046$, $\pm0.544835058382$" in page

    def test_av_download(self):
        r"""
        Test downloading on search results page.
        """
        response = self.tc.get('Variety/Abelian/Fq/5/2/?Submit=sage&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D')
        self.assertTrue('Below is a list' in response.data)
        self.assertTrue('32*x^10' in response.data)
        response = self.tc.get('Variety/Abelian/Fq/5/2/?Submit=gp&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D')
        self.assertTrue('Below is a list' in response.data)
        self.assertTrue('32*x^10' in response.data)
        response = self.tc.get('Variety/Abelian/Fq/5/2/?Submit=magma&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D')
        self.assertTrue('Below is a list' in response.data)
        self.assertTrue('32*x^10' in response.data)
