from lmfdb.tests import LmfdbTest


class AbGpsHomeTest(LmfdbTest):
    # All tests should pass
    # TODO test link to random isogeny class

    # The pages themselves
    def test_index_page(self):
        r"""
        Check that the Groups/Abstract index page works
        """
        homepage = self.tc.get("/Groups/Abstract/").get_data(as_text=True)
        assert "from the database" in homepage

    # TODO test stats once we have them
    #  def test_stats_page(self):
    #  self.check_args("/Groups/Abstract/stats","Abstract groups: Statistics")

 
    def test_completeness_page(self):
        r"""
        Check that Groups/Abstract/Completeness works
        """
        page = self.tc.get("/Groups/Abstract/Completeness").get_data(as_text=True)
        assert "All groups of order up to" in page

    def test_further_completeness_page(self):
        r"""
        Check that Groups/Abstract/Source works
        """
        page = self.tc.get("/Groups/Abstract/Source").get_data(as_text=True)
        assert "as well as their attributes, subgroups, character tables" in page

    def test_labels_page(self):
        r"""
        Check that Groups/Abstract/Labels works
        """
        page = self.tc.get("/Groups/Abstract/Labels").get_data(as_text=True)
        assert "has the form" in page

    def test_lookup(self):
        r"""
        Check that Groups/Abstract/?jump works
        """
        self.check_args("/Groups/Abstract/?jump=10.1", "10.1")

    # test that abelian group redirect works
    def test_abelian_lookup(self):
        r"""
        Check that Groups/Abstract/ab/ works
        """
        self.check_args("/Groups/Abstract/ab/2.2.2.6", "48.52")        

        
    # Various searches
    # Many things are checked twice: Once from main index/browse page, and once from the refining search page

    def test_bad_label(self):
        r"""
        Check the error message for a bad label url
        """
        self.check_args("/Groups/Abstract/7.2", "No group with label")

    def test_search_order(self):
        r"""
        Check that we can search by order
        """
        # check that 8.1 and  8.3 show up 
        self.check_args("/Groups/Abstract/?order=8", "8.1")
        self.check_args("/Groups/Abstract/?order=8", "8.3")


    def test_search_exponent(self):
        r"""
        Check that we can search by exponent
        """
        # check that C2^4 and C2^6 show up for exponent 2
        self.check_args("/Groups/Abstract/?exponent=2", "16.14")
        self.check_args("/Groups/Abstract/?exponent=2", "64.267")

    def test_search_nilpotent(self):
        r"""
        Check that we can search by exponent
        """
        # check that 64.30 and 64.94 show up in first 50 results
        self.check_args("/Groups/Abstract/?nilpotency_class=3", "64.30")
        self.check_args("/Groups/Abstract/?nilpotency_class=3", "64.94")
        

    def test_search_autgroup(self):
        r"""
        Check that we can search by automorphism group
        """
        # check that 7.1  and 18.2 show up as having 6.2 as aut. group
        self.check_args("/Groups/Abstract/?aut_group=6.2", "7.1")
        self.check_args("/Groups/Abstract/?aut_group=6.2", "18.2")


    def test_search_autgroup_order(self):
        r"""
        Check that we can search by automorphism group order
        """
        # check that 36.12 and 72.2 show up as having aut. group of order 24
        self.check_args("/Groups/Abstract/?aut_order=24", "36.12")
        self.check_args("/Groups/Abstract/?aut_order=24", "72.2")

    def test_search_center(self):
        r"""
        Check that we can search by center
        """
        # check that 64.212 and 80.43 show up on first page with center 8.5
        self.check_args("/Groups/Abstract/?center_label=8.5", "64.212")
        self.check_args("/Groups/Abstract/?center_label=8.5", "80.43")

    def test_search_commutator(self):
        r"""
        Check that we can search by commutators
        """
        # check that 32.20 and 64.190 show up on first page with center 8.1
        self.check_args("/Groups/Abstract/?commutator_label=8.1", "32.20")
        self.check_args("/Groups/Abstract/?commutator_label=8.1", "64.190")


    def test_search_centralquot(self):
        r"""
        Check that we can search by central quotients
        """
        # check that 40.10 and 64.87 show up on first page
        # with central quotient 4.2
        self.check_args("/Groups/Abstract/?central_quotient=4.2", "40.10")
        self.check_args("/Groups/Abstract/?central_quotient=4.2", "64.87")


    def test_search_abelianization(self):
        r"""
        Check that we can search by abelianization
        """
        # check that 72.19 and 96.65 show up with abelianization 8.1
        self.check_args("/Groups/Abstract/?abelian_quotient=8.1", "72.19")
        self.check_args("/Groups/Abstract/?abelian_quotient=8.1", "96.65")

        
    def test_abelian_search(self):
        r"""
        Check that we can restrict to abelian or non-abelian groups only
        """
        self.check_args("/Groups/Abstract/?order=12&abelian=yes", "12.2")
        self.check_args("/Groups/Abstract/?order=12&abelian=no", "12.3")
        self.not_check_args("/Groups/Abstract/?order=12&abelian=no", "12.5")
        self.not_check_args("/Groups/Abstract/?order=12&abelian=yes", "12.4")


    def test_cyclic_search(self):
        r"""
        Check that we can restrict to cyclic or non-cyclic groups only
        """
        self.check_args("/Groups/Abstract/?order=24&cyclic=yes", "24.2")
        self.check_args("/Groups/Abstract/?order=24&cylic=no", "24.3")
        self.not_check_args("/Groups/Abstract/?order=24&cyclic=no", "24.2")
        self.not_check_args("/Groups/Abstract/?order=24&cyclic=yes", "24.4")


    def test_simple_search(self):
        r"""
        Check that we can restrict to simple or non-simple groups only
        """
        self.check_args("/Groups/Abstract/?simple=yes", "60.5")
        self.check_args("/Groups/Abstract/?simple=no", "16.8")
        self.not_check_args("/Groups/Abstract/?simple=no", "29.1")
        self.not_check_args("/Groups/Abstract/?simple=yes", "18.4")


     #when the test was first written 60.5 was only perfect and
     # only non-solvable group in db so next two are quite restrictive 
    def test_perfect_search(self):
        r"""
        Check that we can restrict to perfect or non-perfect groups only
        """
        self.check_args("/Groups/Abstract/?order=60&perfect=yes", "60.5")
        self.check_args("/Groups/Abstract/?order=60&perfect=no", "60.3")
        self.not_check_args("/Groups/Abstract/?order=60&perfect=no", "60.5")
        self.not_check_args("/Groups/Abstract/?order=60&perfect=yes", "60.12")
        
    def test_solvable_search(self):
        r"""
        Check that we can restrict to solvable or non-solvbable groups only
        """
        self.check_args("/Groups/Abstract/?order=60&solvable=no", "60.5")
        self.check_args("/Groups/Abstract/?order=60&solvable=yes", "60.3")
        self.not_check_args("/Groups/Abstract/?order=60&solvable=yes", "60.5")
        self.not_check_args("/Groups/Abstract/?order=60&solvable=no", "60.12")

        
    def test_nilpotent_search(self):
        r"""
        Check that we can restrict to nilpotent or non-nilpotent groups only
        """
        self.check_args("/Groups/Abstract/?order=18&nilpotent=no", "18.1")
        self.check_args("/Groups/Abstract/?order=18&nilpotent=yes", "18.5")
        self.not_check_args("/Groups/Abstract/?order=18&nilpotent=yes", "18.3")
        self.not_check_args("/Groups/Abstract/?order=18&nilpotent=no", "18.2")


        
    def test_direct_product_search(self):
        r"""
        Check that we can restrict to direct product or not only
        """
        self.check_args("/Groups/Abstract/?direct_product=no", "30.3")
        self.check_args("/Groups/Abstract/?direct_product=yes", "32.22")
        self.not_check_args("/Groups/Abstract/?direct_product=yes", "8.1")
        self.not_check_args("/Groups/Abstract/?direct_product=no", "8.2")



               
    def test_semidirect_product_search(self):
        r"""
        Check that we can restrict to semidirect product or not only
        """
        self.check_args("/Groups/Abstract/?semidirect_product=no", "31.1")
        self.check_args("/Groups/Abstract/?direct_product=no&semidirect_product=yes", "16.7")
        self.not_check_args("/Groups/Abstract/?semidirect_product=no", "10.1")
        self.not_check_args("/Groups/Abstract/?direct_product=no&semidirect_product=yes", "6.2")



    ## TO DO
    ## Test sbugroup pages and subgroup searches
    ## Test searches: order statistics, all the advanced searches
    ## Test diagram and character table displays?
