from lmfdb.base import LmfdbTest

class AVTest(LmfdbTest):

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).data
        
    def not_check_args(self, path, text):
        assert not(text in self.tc.get(path, follow_redirects=True).data)
        

    # All tests should pass
    #
    # We check everything that is computed on the fly or that uses Sage
    # TODO: test newton_plot, circle_plot, properties box
    # TODO: update test_is_primitive when primitive_models is fixed
    
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
        self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The number field of this isogeny class is not in the database.')
        self.not_check_args("/Variety/Abelian/Fq/2/7/g_v", 'The number field of this isogeny class is not in the database.')
        
    def test_display_gal_gp(self):
        r"""
        Check that display_galois_group works
        """
        self.check_args("/Variety/Abelian/Fq/2/19/g_bt", 'n=4&t=3')
        self.check_args("/Variety/Abelian/Fq/3/9/d_h_bb",'The Galois group of this isogeny class is not in the database.')
        self.not_check_args("/Variety/Abelian/Fq/2/27/f_n",'The Galois group of this isogeny class is not in the database.')
        
    def test_is_primitive(self):
        r"""
        Check that is_primitive is computed correctly, and that the base change information displays correctly
        """
        #TODO: this is broken in reality. Once it is fixed the test should be updated
        self.check_args("/Variety/Abelian/Fq/2/9/e_l",'primitive')
        self.check_args("/Variety/Abelian/Fq/3/13/ao_dz_ars",'3.13.ao_dz_ars')

        
    #def test_weil_nums(self):
    #    r"""
    #    Check that the Weil numbers display correctly
    #    """        


    
