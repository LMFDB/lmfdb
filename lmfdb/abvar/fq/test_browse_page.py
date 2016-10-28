from lmfdb.base import LmfdbTest

class AVHomeTest(LmfdbTest):

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
        
    # TODO link to stats page, etc.
        
    #
    # Various search combinations
    # Everything is checked twice: Once from main index/browse page, and once from the refining search page
    def test_search(self):
        r"""
        Check that various search combinations work.
        """
        # change the range of the table
        self.check_args("/Variety/Abelian/Fq/?table_field_range=32-100&table_dimension_range=2-4",'9442')
        # dimension and base field, last one is from the table
        self.check_args("/Variety/Abelian/Fq/?q=7&simple_only=no&g=1&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'1.7.af')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=7&g=1&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.7.af')
        self.check_args("/Variety/Abelian/Fq/1/7/", '1.7.af')
        
        # p-rank only
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=", '2.11.ag_bc')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=", '2.11.ag_bc')
        # dimension, base field and p-rank
        self.check_args("/Variety/Abelian/Fq/?q=9&simple_only=no&g=2&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'2.9.ag_w')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=9&g=2&simple_only=no&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'2.9.ag_w')
        # dimension, base field and newton polygon
        #self.check_args("/Variety/Abelian/Fq/?q=121&simple_only=no&g=1&p_rank=&newton_polygon=%5B0%2C1%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=,'1.121.ad') 
        #self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=121&g=1&simple_only=no&p_rank=&newton_polygon=%5B0%2C1%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.121.ad')
        # dimension, base field and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?q=25&simple_only=no&g=2&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-13%5D&abvar_point_count=&curve_point_count=&decomposition=&count=",'2.25.b_an')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-13%5D&abvar_point_count=&curve_point_count=&decomposition=",'2.25.b_an')
        # initial coefficients only
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=&count=",'4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=",'4.3.b_ab_d_j')
        # dimension, base field and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?q=25&simple_only=no&g=2&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B373%2C391277%5D&curve_point_count=&decomposition=&count=",'2.25.an_dh')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B373%2C391277%5D&curve_point_count=&decomposition=",'2.25.an_dh')
        # point counts of the abelian variety only
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=&count=", '2.9.ab_d')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=", '2.9.ab_d')
        # dimension, base field and point counts of the curve
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=4&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B4%2C15%5D&decomposition=",'4.3.ae_f_ad_e')
        self.check_args("/Variety/Abelian/Fq/?start=50&count=50&q=3&g=4&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B4%2C15%5D&decomposition=",'4.3.ae_f_ad_e')
        # point counts of the curve only
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B9%2C87%5D&decomposition=&count=", '3.9.ab_d_abs')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B9%2C87%5D&decomposition=", '3.9.ab_d_abs')
        # dimension, base field and maximum number to display
        self.check_args("/Variety/Abelian/Fq/?q=25&simple_only=no&g=2&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=100", '2.25.am_cw')
        # p-rank and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=2&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=&count=", '4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=2&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=", '4.3.b_ab_d_j')
        # initial coefficients and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?q=&simple_only=no&g=&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=&count=", 'no matches')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple_only=no&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=", 'no matches')
        #still to test: simple only, newton polygon and isogeny factors decomposition
