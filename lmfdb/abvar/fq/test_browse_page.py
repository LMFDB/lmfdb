from lmfdb.base import LmfdbTest

class AbVarHomeTest(LmfdbTest):

    def check(self, homepage, path, text):
        assert path in homepage
        assert text in self.tc.get(path, follow_redirects=True).data

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).data
        
    # All tests should pass
    #
    # The page itself
    def test_page(self):
        r"""
        Check that the Variety/Abelian/Fq search & browse page works.
        """
        homepage = self.tc.get("/Variety/Abelian/Fq/").data
        assert 'The table below gives' in homepage
        
    #
    # Various search combinations
    def test_search(self):
        r"""
        Check that various search combinations work.
        """
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=7&g=1&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.7.af')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=9&g=2&simple_only=no&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'2.9.ag_w')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=121&g=1&simple_only=no&p_rank=&newton_polygon=%5B0%2C1%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.121.ad')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-13%5D&abvar_point_count=&curve_point_count=&decomposition=",'2.25.b_an')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=2&g=6&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=%5B-5%2C11%5D&abvar_point_count=&curve_point_count=&decomposition=",'6.2.af_l_am_ac_bg_ack')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B373%2C391277%5D&curve_point_count=&decomposition=",'2.25.an_dh')
        self.check_args("/Variety/Abelian/Fq/?start=50&count=50&q=3&g=4&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B4%2C15%5D&decomposition=",'4.3.ae_f_ad_e')
        #still to test: simple only, newton polygon and isogeny factors decomposition
