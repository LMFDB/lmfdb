from lmfdb.base import LmfdbTest

class AVHomeTest(LmfdbTest):

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).data

    def not_check_args(self, path, text):
        assert not(text in self.tc.get(path, follow_redirects=True).data)

    # All tests should pass
    # TODO test link to random isogeny class

    # The pages themselves
    def test_index_page(self):
        r"""
        Check that the Variety/Abelian/Fq index page works
        """
        homepage = self.tc.get("/Variety/Abelian/Fq/").data
        assert 'The table below gives' in homepage

    def test_completeness_page(self):
        r"""
        Check that Variety/Abelian/Fq/Completeness works
        """
        page = self.tc.get("/Variety/Abelian/Fq/Completeness").data
        assert 'the collection of isogeny classes is complete' in page

    def test_further_completeness_page(self):
        r"""
        Check that Variety/Abelian/Fq/Source works
        """
        page = self.tc.get("/Variety/Abelian/Fq/Source").data
        assert 'characteristic polynomial' in page

    def test_labels_page(self):
        r"""
        Check that Variety/Abelian/Fq/Labels works
        """
        page = self.tc.get("/Variety/Abelian/Fq/Labels").data
        assert 'label format' in page

    # Various searches
    # Many things are checked twice: Once from main index/browse page, and once from the refining search page

    def test_bad_label(self):
        r"""
        Check the error message for a bad label url
        """
        self.check_args("/Variety/Abelian/Fq/2/9/ak_bl", 'is not in the database')

    def test_table_range(self):
        r"""
        Check that we can change the table range
        """
        self.check_args("/Variety/Abelian/Fq/?table_field_range=32-100&table_dimension_range=2-4",'6408')

    def test_search_dimension(self):
        r"""
        Check that we can search by dimension
        """
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=2&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=", '2.11.ae_f')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=2&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=", '2.11.ae_f')
        #this last one is url only
        self.check_args("/Variety/Abelian/Fq/2/", '2.11.ae_f')

    def test_search_basefield(self):
        r"""
        Check that we can search by base field
        """
        self.check_args("/Variety/Abelian/Fq/?q=121&simple=any&g=&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'1.121.al')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=121&g=&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.121.al')

    def test_simple_search(self):
        r"""
        Check that we can restrict to simple or non-simple abelian varieties only
        """
        #search for simple
        self.check_args("/Variety/Abelian/Fq/?q=2&primitive=any&g=2&simple=yes&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.2.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&primitive=any&g=2&simple=yes&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.2.ae_i')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=2&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=yes&primitive=any&jacobian=any&polarizable=any",'2.2.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=2&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=yes&primitive=any&jacobian=any&polarizable=any",'2.2.ae_i')
        #search for not simple
        self.check_args("/Variety/Abelian/Fq/?q=2&primitive=any&g=2&simple=no&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.2.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&primitive=any&g=2&simple=no&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.2.ad_f')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=2&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=no&primitive=any&jacobian=any&polarizable=any",'2.2.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=2&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=no&primitive=any&jacobian=any&polarizable=any",'2.2.ad_f')

    def test_primitive_search(self):
        r"""
        Check that we can restrict to primitive or non-primitive abelian varieties only
        """
        self.check_args("/Variety/Abelian/Fq/?q=4&primitive=no&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.4.ad_f')
        self.check_args("/Variety/Abelian/Fq/?q=4&primitive=yes&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.4.af_o')
        self.not_check_args("/Variety/Abelian/Fq/?q=4&primitive=yes&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.4.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=4&primitive=no&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.4.ae_j')

    def test_search_prank(self):
        r"""
        Check that we can search by p-rank
        """
        self.check_args("/Variety/Abelian/Fq/?q=9&primitive=any&g=2&simple=any&p_rank=2&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=", '2.9.ab_n')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=9&g=2&p_rank=2&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any", '2.9.ab_n')
        self.not_check_args("/Variety/Abelian/Fq/?q=9&primitive=any&g=2&simple=any&p_rank=2&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.9.b_ad')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=9&g=2&p_rank=2&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any",'2.9.b_ad')

    def test_search_newton(self):
        r"""
        Check that we can search by newton polygon
        """
        # [0,1] from browse page
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=%5B0%2C1%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'1.13.g')
        # 1/3 from browse page
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=1%2F3&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'3.2.ac_c_ac')
        # 1/5 from refine search
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=1%2F5&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'5.2.ae_i_ao_ba_abq')
        # slope not a rational number
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=t&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'is not a valid input')
        # slopes are not increasing
        self.check_args("/Variety/Abelian/Fq/?start=&count=&q=&g=&simple=any&p_rank=&newton_polygon=%5B1%2C1%2F2%2C0%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'Slopes must be increasing')
        # [(1,0),(3,1)]
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=%5B%281%2C0%29%2C%283%2C1%29%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'2.16.j_ca')
        # breaks don't give a convex hull
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=%5B%281%2C2%29%2C%283%2C1%29%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'Slopes specified by break points must be increasing')
        # break coordinates not integers
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=%5B%281%2F2%2C0%29%2C%283%2C1%29%5D&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=", 'unable to convert')

    def test_search_initcoeffs(self):
        r"""
        Check that we can search by initial coefficients of the polynomial
        """
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=&count=",'4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=",'4.3.b_ab_d_j')

    def test_search_pointcountsav(self):
        r"""
        Check that we can search by the point counts of the abelian variety
        """
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=&count=", '2.9.ab_d')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=", '2.9.ab_d')

    def test_search_pointcountscurve(self):
        r"""
        Check that we can search by the point counts of the curve
        """
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B9%2C87%5D&decomposition=&count=", '3.9.ab_d_abs')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B9%2C87%5D&decomposition=", '3.9.ab_d_abs')

    def test_search_anglerank(self):
        r"""
        Check that we can search by angle rank
        """
        self.check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=4&simple=any&p_rank=&jacobian=any&angle_ranks=2&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'4.3.ag_u_abw_dn')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=4&p_rank=&angle_ranks=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any",'4.3.ag_u_abw_dn')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=4&simple=any&p_rank=&jacobian=any&angle_ranks=2&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'4.3.a_ad_a_j')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=4&p_rank=&angle_ranks=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any",'4.3.a_ad_a_j')

    def test_search_isogfactor(self):
        r"""
        Check that we can search by decomposition into isogeny factors
        """
        #[3.5.ah_y_ach,*]
        self.check_args("/Variety/Abelian/Fq/?q=&primitive=any&g=&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=%5B3.5.ah_y_ach%2C*%5D&number_field=&count=",'4.5.ak_by_agk_qb')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=%5B3.5.ah_y_ach%2C*%5D&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any",'4.5.ak_by_agk_qb')

    def test_search_numberfield(self):
        r"""
        Check that we can search by number field
        """
        #4.0.9726525.1
        self.check_args("/Variety/Abelian/Fq/?q=&primitive=any&g=&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=4.0.9726525.1&count=",'2.193.ax_tn')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=4.0.9726525.1&simple=any&primitive=any&jacobian=any&polarizable=any",'2.193.ax_tn')

    def test_search_jacobian(self):
        r"""
        Check that we can restrict to Jacobians or non Jacobians
        """
        #Jacobians only
        self.check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=2&simple=any&p_rank=&jacobian=yes&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.3.ae_i')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=yes&polarizable=any",'2.3.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=2&simple=any&p_rank=&jacobian=yes&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.3.a_af')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=yes&polarizable=any",'2.3.a_af')
        #non Jacobians only
        self.check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=2&simple=any&p_rank=&jacobian=no&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.3.a_af')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=no&polarizable=any",'2.3.a_af')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&primitive=any&g=2&simple=any&p_rank=&jacobian=no&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.3.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=no&polarizable=any",'2.3.ae_i')

    def test_search_princpol(self):
        r"""
        Check that we can restrict to principally polarizable or not principally polarizable
        """
        #princ polarizable only
        self.check_args("/Variety/Abelian/Fq/?q=5&primitive=any&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=yes&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.5.ab_f')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=5&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=yes",'2.5.ab_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&primitive=any&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=yes&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.5.ac_ab')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=5&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=yes",'2.5.ac_ab')
        #not princ polariable only
        self.check_args("/Variety/Abelian/Fq/?q=5&primitive=any&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=no&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.5.ac_ab')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=5&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=no",'2.5.ac_ab')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&primitive=any&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=no&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=",'2.5.ab_f')
        self.not_check_args("/Variety/Abelian/Fq/?start=0&count=50&q=5&g=2&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=no",'2.5.ab_f')

    def test_search_maxnumdisplay(self):
        r"""
        Check that we can restrict how many classes get displayed
        """
        self.check_args("/Variety/Abelian/Fq/?q=5&primitive=any&g=2&simple=any&p_rank=&jacobian=any&angle_ranks=&polarizable=any&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&number_field=&count=19",'19')

    def test_search_combos(self):
        r"""
        Check that various search combinations work.
        """
        # dimension and base field, last one is from the table
        self.check_args("/Variety/Abelian/Fq/?q=7&simple=any&g=1&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'1.7.af')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=7&g=1&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'1.7.af')
        self.check_args("/Variety/Abelian/Fq/1/7/", '1.7.af')
        # dimension, base field and p-rank
        self.check_args("/Variety/Abelian/Fq/?q=9&simple=any&g=2&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=",'2.9.ag_w')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=9&g=2&simple=any&p_rank=2&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=",'2.9.ag_w')
        # dimension, base field and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?q=25&simple=any&g=2&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-13%5D&abvar_point_count=&curve_point_count=&decomposition=&count=",'2.25.b_an')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple=any&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-13%5D&abvar_point_count=&curve_point_count=&decomposition=",'2.25.b_an')
        # dimension, base field and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?q=25&simple=any&g=2&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B373%2C391277%5D&curve_point_count=&decomposition=&count=",'2.25.an_dh')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=25&g=2&simple=any&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=%5B373%2C391277%5D&curve_point_count=&decomposition=",'2.25.an_dh')
        # dimension, base field and point counts of the curve
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=3&g=4&p_rank=&angle_ranks=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=%5B0%2C4%2C15%5D&decomposition=&number_field=&simple=any&primitive=any&jacobian=any&polarizable=any",'4.3.ae_f_ad_e')
        # dimension, base field and maximum number to display
        self.check_args("/Variety/Abelian/Fq/?q=25&simple=any&g=2&p_rank=&newton_polygon=&initial_coefficients=&abvar_point_count=&curve_point_count=&decomposition=&count=100", '2.25.am_cw')
        # p-rank and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=2&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=&count=", '4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=2&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=&curve_point_count=&decomposition=", '4.3.b_ab_d_j')
        # initial coefficients and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?q=&simple=any&g=&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=&count=", 'no matches')
        self.check_args("/Variety/Abelian/Fq/?start=0&count=50&q=&g=&simple=any&p_rank=&newton_polygon=&initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D&curve_point_count=&decomposition=", 'no matches')
