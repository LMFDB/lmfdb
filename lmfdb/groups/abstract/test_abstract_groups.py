from lmfdb.tests import LmfdbTest


class AbGpsTest(LmfdbTest):
    # All tests should pass

    def test_is_solvable(self):
        r"""
        Check that solvable is computed correctly
        """
        self.check_args("/Groups/Abstract/60.5", "nonsolvable")
        self.check_args("/Groups/Abstract/32.51", "solvable")


# To do:  Test a lot more data,  also test downloads and property box
# (sample code from abvar/fq below for property box and downloads)  


        
#    def test_property_box(self):
#        r"""
#        Check that the property box displays.
#        """
#        page = self.tc.get("/Variety/Abelian/Fq/2/4/ad_g").get_data(as_text=True).replace("\n", "").replace(" ", "")
#        assert r'<divclass="properties-body"><table><tr><tdclass="label">Label</td><td>2.4.ad_g</td></tr><tr>' in page
#        assert r'<tdclass="label">Basefield</td><td>$\F_{2^{2}}$</td></tr><tr><tdclass="label">Dimension</td><td>' in page
#        self.check_args("/Variety/Abelian/Fq/2/79/ar_go", "Principally polarizable")



#    def test_av_download(self):
#        r"""
#        Test downloading on search results page.
#        """
#        response = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=sage&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D")
#        self.assertTrue("Below is a list" in response.get_data(as_text=True))
#        self.assertTrue("32*x^10" in response.get_data(as_text=True))
#        response = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=gp&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D")
#        self.assertTrue("Below is a list" in response.get_data(as_text=True))
#        self.assertTrue("32*x^10" in response.get_data(as_text=True))
#        response = self.tc.get("Variety/Abelian/Fq/5/2/?Submit=magma&download=1&query=%7B%27q%27%3A+2%2C+%27g%27%3A+5%7D")
#        self.assertTrue("Below is a list" in response.get_data(as_text=True))
#        self.assertTrue("32*x^10" in response.get_data(as_text=True))

#    def test_download_all(self):
#        r"""
#        Test downloading all stored data to text
#        """

#        page = self.tc.get('Variety/Abelian/Fq/download_all/1.81.r', follow_redirects=True)
#        assert '"abvar_counts": [99, 6435, 532224, 43043715,' in page.get_data(as_text=True)

#        page = self.tc.get('Variety/Abelian/Fq/download_all/3.17.d_b_act', follow_redirects=True)
#        assert '"curve_counts": [21, 283, 4719, 84395' in page.get_data(as_text=True)


