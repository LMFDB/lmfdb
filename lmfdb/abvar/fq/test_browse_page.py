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
        self.check_args("/Variety/Abelian/Fq/?table_field_range=4..7&table_dimension_range=2..4",'2944')
        # and that it deals with invalid input
        self.check_args("/Variety/Abelian/Fq/?table_field_range=2-27&table_dimension_range=1%2C3%2C5",'Error: You cannot use commas in the table ranges.')
        self.check_args("/Variety/Abelian/Fq/?table_field_range=2-27&table_dimension_range=x",'not a valid input')

    def test_search_dimension(self):
        r"""
        Check that we can search by dimension
        """
        # check that 2.2.a_a and  2.3.ac_g show up in the first 50 results 
        self.check_args("/Variety/Abelian/Fq/?g=2", '2.2.a_a')
        self.check_args("/Variety/Abelian/Fq/?g=2", '2.3.ac_g')
        #this last one is url only
        self.check_args("/Variety/Abelian/Fq/2/", '2.3.ac_e')

    def test_search_basefield(self):
        r"""
        Check that we can search by base field
        """
        self.check_args("/Variety/Abelian/Fq/?q=121",'1.121.al')

    def test_simple_search(self):
        r"""
        Check that we can restrict to simple or non-simple abelian varieties only
        """
        #search for simple
        self.check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=yes",'2.2.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=yes",'2.2.ae_i')
        self.check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=yes",'2.2.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=yes",'2.2.ae_i')
        #search for not simple
        self.check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=no",'2.2.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=no",'2.2.ad_f')
        self.check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=no",'2.2.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=2&g=2&simple=no",'2.2.ad_f')

    def test_primitive_search(self):
        r"""
        Check that we can restrict to primitive or non-primitive abelian varieties only
        """
        self.check_args("/Variety/Abelian/Fq/?q=4&primitive=no&g=2",'2.4.ad_f')
        self.check_args("/Variety/Abelian/Fq/?q=4&primitive=yes&g=2",'2.4.af_o')
        self.not_check_args("/Variety/Abelian/Fq/?q=4&primitive=yes&g=2",'2.4.ad_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=4&primitive=no&g=2",'2.4.ae_j')

    def test_search_prank(self):
        r"""
        Check that we can search by p-rank
        """
        self.check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2", '2.9.ah_ba')
        self.check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2", '2.9.af_o')
        self.not_check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2",'2.9.b_ad')
        self.not_check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2",'2.9.b_ad')

    def test_search_newton(self):
        r"""
        Check that we can search by newton polygon
        """
        # [0,1] from browse page
        self.check_args("/Variety/Abelian/Fq/?newton_polygon=%5B0%2C1%5D",'1.2.ab')
        # 1/3 from browse page, doesn't currently work
        self.check_args("/Variety/Abelian/Fq/?newton_polygon=1%2F3",'You cannot specify slopes on their own')
        # 1/5 from refine search, doesn't currently work
        self.check_args("/Variety/Abelian/Fq/?newton_polygon=1%2F5",'You cannot specify slopes on their own')
        # slope not a rational number
        self.check_args("/Variety/Abelian/Fq/?newton_polygon=t",'is not a valid input')
        # slopes are not increasing
        self.check_args("/Variety/Abelian/Fq/?start=&count=&newton_polygon=%5B1%2C1%2F2%2C0%5D",'Slopes must be increasing')

    def test_search_initcoeffs(self):
        r"""
        Check that we can search by initial coefficients of the polynomial
        """
        self.check_args("/Variety/Abelian/Fq/?initial_coefficients=%5B1%2C-1%2C3%2C9%5D",'4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?initial_coefficients=%5B1%2C-1%2C3%2C9%5D",'4.3.b_ab_d_j')
        # there should be only one match, if ranges were supported
        self.check_args("/Variety/Abelian/Fq/?angle_ranks=&initial_coefficients=%5B3%2C+9%2C+10%2C+87-100%5D", "Ranges not supported");

    def test_search_pointcountsav(self):
        r"""
        Check that we can search by the point counts of the abelian variety
        """
        self.check_args("/Variety/Abelian/Fq/?abvar_point_count=%5B75%2C7125%5D", '2.9.ab_d')
        self.check_args("/Variety/Abelian/Fq/?abvar_point_count=%5B75%2C7125%5D", '2.9.ab_d')

    def test_search_pointcountscurve(self):
        r"""
        Check that we can search by the point counts of the curve
        """
        self.check_args("/Variety/Abelian/Fq/?curve_point_count=%5B9%2C87%5D", '3.9.ab_d_abs')
        self.check_args("/Variety/Abelian/Fq/?curve_point_count=%5B9%2C87%5D", '3.9.ab_d_abs')

    def test_search_anglerank(self):
        r"""
        Check that we can search by angle rank
        """
        self.check_args("/Variety/Abelian/Fq/?q=3&g=4&ang_rank=2",'4.3.ag_p_au_y')
        self.check_args("/Variety/Abelian/Fq/?q=3&g=4&ang_rank=2",'4.3.ag_p_au_y')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=4&ang_rank=2",'4.3.am_co_aii_rr')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=4&ang_rank=2",'4.3.am_co_aii_rr')

    def test_search_isogfactor(self):
        r"""
        Check that we can search by decomposition into isogeny factors
        """
        #[3.5.ah_y_ach,*]
        self.check_args("/Variety/Abelian/Fq/?simple_quantifier=include&simple_factors=3.5.ah_y_ach",'4.5.ak_by_agk_qb')
        self.check_args("/Variety/Abelian/Fq/?p_rank=4&dim1_factors=2&dim2_factors=2&dim1_distinct=1&dim2_distinct=1",'6.2.ag_p_aw_bh_acu_ey')
        self.check_args("/Variety/Abelian/Fq/?dim1_factors=6&dim1_distinct=1",'all 5 matches')

    def test_search_numberfield(self):
        r"""
        Check that we can search by number field
        """
        #4.0.9726525.1
        self.check_args("/Variety/Abelian/Fq/?number_field=4.0.9726525.1",'2.193.ax_tn')
        self.check_args("/Variety/Abelian/Fq/?number_field=4.0.9726525.1",'2.193.ax_tn')

    def test_search_jacobian(self):
        r"""
        Check that we can restrict to Jacobians or non Jacobians
        """
        #Jacobians only
        self.check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=yes",'2.3.ae_i')
        self.check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=yes",'2.3.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=yes",'2.3.a_af')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=yes",'2.3.a_af')
        #non Jacobians only
        self.check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=no",'2.3.a_af')
        self.check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=no",'2.3.a_af')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=no",'2.3.ae_i')
        self.not_check_args("/Variety/Abelian/Fq/?q=3&g=2&jacobian=no",'2.3.ae_i')
        # unknowns
        self.check_args("/Variety/Abelian/Fq/?g=3&jacobian=not_yes&polarizable=yes",'No matches')
        self.check_args("/Variety/Abelian/Fq/?q=2&g=3&p_rank=0&jacobian=not_no",'3.2.c_c_c')

    def test_search_princpol(self):
        r"""
        Check that we can restrict to principally polarizable or not principally polarizable
        """
        #princ polarizable only
        self.check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=yes",'2.5.ab_f')
        self.check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=yes",'2.5.ab_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=yes",'2.5.ac_ab')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=yes",'2.5.ac_ab')
        #not princ polariable only
        self.check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=no",'2.5.ac_ab')
        self.check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=no",'2.5.ac_ab')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=no",'2.5.ab_f')
        self.not_check_args("/Variety/Abelian/Fq/?q=5&g=2&polarizable=no",'2.5.ab_f')
        # unknowns
        self.check_args("/Variety/Abelian/Fq/?q=17&g=2&jacobian=no&polarizable=not_yes",'2.17.ae_ab')
        self.check_args("/Variety/Abelian/Fq/?q=17&g=2&jacobian=no&polarizable=not_no",'2.17.aj_cc')
        self.check_args("/Variety/Abelian/Fq/?q=3&g=3&jacobian=no&polarizable=not_no",'3.3.ag_v_abs')
        self.check_args("/Variety/Abelian/Fq/?q=2&g=3&p_rank=0&jacobian=not_no&polarizable=not_no",'3.2.c_e_g')

    def test_search_galois(self):
        self.check_args("/Variety/Abelian/Fq/?galois_group=4T3",'2.4.ab_f')
        self.check_args("/Variety/Abelian/Fq/?q=9&galois_group=4T3",'2.9.af_u')
        self.check_args("/Variety/Abelian/Fq/?galois_group=8T12",'4.2.b_b_e_f')
        self.check_args("/Variety/Abelian/Fq/?p_rank=0&galois_group=C4",'2.64.i_cm')

    def test_search_maxnumdisplay(self):
        r"""
        Check that we can restrict how many classes get displayed
        """
        self.check_args("/Variety/Abelian/Fq/?q=5&g=2&count=19",'19')

    def test_search_combos(self):
        r"""
        Check that various search combinations work.
        """
        # dimension and base field, last one is from the table
        self.check_args("/Variety/Abelian/Fq/?q=7&g=1",'1.7.f')
        self.check_args("/Variety/Abelian/Fq/?q=7&g=1",'1.7.f')
        self.check_args("/Variety/Abelian/Fq/1/7/", '1.7.af')
        # dimension, base field and p-rank
        self.check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2",'2.9.ad_b')
        self.check_args("/Variety/Abelian/Fq/?q=9&g=2&p_rank=2",'2.9.af_o')
        # dimension, base field and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?q=25&g=2&initial_coefficients=%5B1%2C-13%5D",'2.25.b_an')
        self.check_args("/Variety/Abelian/Fq/?q=25&g=2&initial_coefficients=%5B1%2C-13%5D",'2.25.b_an')
        # dimension, base field and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?q=25&g=2&abvar_point_count=%5B373%2C391277%5D",'2.25.an_dh')
        self.check_args("/Variety/Abelian/Fq/?q=25&g=2&abvar_point_count=%5B373%2C391277%5D",'2.25.an_dh')
        # dimension, base field and point counts of the curve
        self.check_args("/Variety/Abelian/Fq/?q=3&g=4&curve_point_count=%5B0%2C4%2C15%5D",'4.3.ae_f_ad_e')
        # dimension, base field and maximum number to display
        self.check_args("/Variety/Abelian/Fq/?q=25&g=2&count=100", '2.25.an_do')
        # p-rank and initial coefficients
        self.check_args("/Variety/Abelian/Fq/?p_rank=2&initial_coefficients=%5B1%2C-1%2C3%2C9%5D", '4.3.b_ab_d_j')
        self.check_args("/Variety/Abelian/Fq/?p_rank=2&initial_coefficients=%5B1%2C-1%2C3%2C9%5D", '4.3.b_ab_d_j')
        # initial coefficients and point counts of the abelian variety
        self.check_args("/Variety/Abelian/Fq/?initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D", 'No matches')
        self.check_args("/Variety/Abelian/Fq/?initial_coefficients=%5B1%2C-1%2C3%2C9%5D&abvar_point_count=%5B75%2C7125%5D", 'No matches')
        # Combining unknown fields on Jacobian and Principal polarization.
        self.check_args("/Variety/Abelian/Fq/?g=3&jacobian=no&polarizable=not_no", '3.2.a_a_ae')
        self.check_args("/Variety/Abelian/Fq/?g=3&jacobian=no&polarizable=yes", 'No matches')
