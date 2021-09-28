from lmfdb.tests import LmfdbTest


class AbGpsTest(LmfdbTest):
    # All tests should pass

    def test_is_solvable(self):
        r"""
        Check that solvable is computed correctly
        """
        self.check_args("/Groups/Abstract/60.5", "nonsolvable")
        self.check_args("/Groups/Abstract/32.51", "solvable")


# To do:  Test a lot more data,  also more property box tests



        
    def test_property_box(self):
        r"""
        Check that the property box displays.
        """
        page = self.tc.get("/Groups/Abstract/256.14916").get_data(as_text=True).replace("\n", "").replace(" ", "")
        assert r'<divclass="properties-body"><table><tr><tdclass="label">Label</td><td>256.14916</td></tr><tr>' in page
 #       assert r'<tdclass="label">Order</td><td>${2^{8}}$</td></tr>' in page
       # self.check_args("/Variety/Abelian/Fq/2/79/ar_go", "Principally polarizable")



    def test_abstract_group_download(self):
#        r"""
#        Test downloading on search results page.
        response = self.tc.get("/Groups/Abstract/384.5458/download/gap")
        self.assertTrue("If the group is solvable" in response.get_data(as_text=True))
        self.assertTrue("encd:= 293961739841108398509157889" in response.get_data(as_text=True))
        response = self.tc.get("/Groups/Abstract/384.5458/download/magma")
        self.assertTrue("If the group is solvable" in response.get_data(as_text=True))
        self.assertTrue("encd:= 293961739841108398509157889" in response.get_data(as_text=True))


        
#    def test_download_all(self):
#        r"""
#        Test downloading all stored data to text
#        """

#        page = self.tc.get('Variety/Abelian/Fq/download_all/1.81.r', follow_redirects=True)
#        assert '"abvar_counts": [99, 6435, 532224, 43043715,' in page.get_data(as_text=True)

#        page = self.tc.get('Variety/Abelian/Fq/download_all/3.17.d_b_act', follow_redirects=True)
#        assert '"curve_counts": [21, 283, 4719, 84395' in page.get_data(as_text=True)


