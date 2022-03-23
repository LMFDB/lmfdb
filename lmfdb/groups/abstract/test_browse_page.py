from lmfdb.tests import LmfdbTest

## TODO
## Test diagram and character table displays and picture?

class AbGpsHomeTest(LmfdbTest):
    # All tests should pass

    # The pages themselves
    def test_index_page(self):
        r"""
        Check that the Groups/Abstract index page works
        """
        homepage = self.tc.get("/Groups/Abstract/").get_data(as_text=True)
        assert "database currently contains" in homepage

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
        self.check_args("/Groups/Abstract/?jump=10.1", "10.1") # by label
        self.check_args("/Groups/Abstract/?jump=SL(2,7)", "336.114") # by family name
        self.check_args("/Groups/Abstract/?jump=F5", "20.3") # by name

    # test that abelian group redirect works
    def test_abelian_lookup(self):
        r"""
        Check that Groups/Abstract/ab/ works
        """
        self.check_args("/Groups/Abstract/ab/2.2.2.6", "48.52")

    def test_random(self):
        r"""
        Check that the random link works
        """
        self.check_args("/Groups/Abstract/random", "Group information")
        self.check_args("/Groups/Abstract/random", "Order:")

    # Various searches

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
        self.check_args("/Groups/Abstract/?order=24&cyclic=no", "24.3")
        self.not_check_args("/Groups/Abstract/?order=24&cyclic=yes", "24.4")
        self.not_check_args("/Groups/Abstract/?order=24&cyclic=no", "24.2")


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
        self.not_check_args("/Groups/Abstract/?direct_product=no", "16.11")

    def test_semidirect_product_search(self):
        r"""
        Check that we can restrict to semidirect product or not only
        """
        self.check_args("/Groups/Abstract/?semidirect_product=no", "31.1")
        self.check_args("/Groups/Abstract/?direct_product=no&semidirect_product=yes", "16.7")
        self.not_check_args("/Groups/Abstract/?semidirect_product=no", "10.1")
        self.not_check_args("/Groups/Abstract/?direct_product=no&semidirect_product=yes", "16.9")

    def test_order_stats_search(self):
        r"""
        Check that we can search by order statistics
        """
        self.check_args("/Groups/Abstract/?order_stats=1^1%2C2^3%2C3^2&search_type=List", "6.1")
        self.not_check_args("/Groups/Abstract/?order_stats=1^1%2C2^3%2C3^2&search_type=List", "10.1")

    #################################################################
    ##################### advanced searches #########################
    #################################################################

    def test_outer_group_search(self):
        r"""
        Check that we can search by outer automorphism group
        """
        self.check_args("/Groups/Abstract/?outer_group=4.2&search_type=List", "8.1")
        self.not_check_args("/Groups/Abstract/?outer_group=4.2&search_type=List", "16.8")

    def test_outer_order_search(self):
        r"""
        Check that we can search by order of outer automorphism group
        """
        self.check_args("/Groups/Abstract/?outer_order=3&search_type=List", "14.1")
        self.not_check_args("/Groups/Abstract/?outer_order=3&search_type=List", "18.3")

    def test_metabelian_search(self):
        r"""
        Check that we can restrict to metabelian groups or not only
        """
        self.check_args("/Groups/Abstract/?metabelian=yes&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?metabelian=yes&search_type=List", "24.3")
        self.check_args("/Groups/Abstract/?metabelian=no&search_type=List", "24.3")
        self.not_check_args("/Groups/Abstract/?metabelian=no&search_type=List", "13.1")

    def test_metacyclic_search(self):
        r"""
        Check that we can restrict to metacyclic groups or not only
        """
        self.check_args("/Groups/Abstract/?metacyclic=yes&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?metacyclic=yes&search_type=List", "12.3")
        self.check_args("/Groups/Abstract/?metacyclic=no&search_type=List", "12.3")
        self.not_check_args("/Groups/Abstract/?metacyclic=no&search_type=List", "12.2")

    def test_almost_simple_search(self):
        r"""
        Check that we can restrict to almost simple groups or not only
        """
        self.check_args("/Groups/Abstract/?almost_simple=yes&search_type=List", "60.5")
        self.not_check_args("/Groups/Abstract/?almost_simple=yes&search_type=List", "8.3")
        self.check_args("/Groups/Abstract/?almost_simple=no&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?almost_simple=no&search_type=List", "60.5")

    def test_quasisimple_search(self):
        r"""
        Check that we can restrict to quasisimple groups or not only
        """
        self.check_args("/Groups/Abstract/?quasisimple=yes&search_type=List", "60.5")
        self.not_check_args("/Groups/Abstract/?quasisimple=yes&search_type=List", "7.1")
        self.check_args("/Groups/Abstract/?quasisimple=no&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?quasisimple=no&search_type=List", "60.5")

    def test_Agroup_search(self):
        r"""
        Check that we can restrict to A-group groups or not only
        """
        self.check_args("/Groups/Abstract/?Agroup=yes&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?Agroup=yes&search_type=List", "16.3")
        self.check_args("/Groups/Abstract/?Agroup=no&search_type=List", "8.3")
        self.not_check_args("/Groups/Abstract/?Agroup=no&search_type=List", "16.14")

    def test_Zgroup_search(self):
        r"""
        Check that we can restrict to Z-group groups or not only
        """
        self.check_args("/Groups/Abstract/?Zgroup=yes&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?Zgroup=yes&search_type=List", "12.3")
        self.check_args("/Groups/Abstract/?Zgroup=no&search_type=List", "4.2")
        self.not_check_args("/Groups/Abstract/?Zgroup=no&search_type=List", "12.2")

    def test_derived_length_search(self):
        r"""
        Check that we can search by derived length
        """
        self.check_args("/Groups/Abstract/?derived_length=3&search_type=List", "24.3")
        self.not_check_args("/Groups/Abstract/?derived_length=3&search_type=List", "16.13")

    def test_frattini_label_search(self):
        r"""
        Check that we can search by Frattini subgroup
        """
        self.check_args("/Groups/Abstract/?frattini_label=4.2&search_type=List", "16.2")
        self.not_check_args("/Groups/Abstract/?frattini_label=4.2&search_type=List", "5.1")

    def test_supersolvable_search(self):
        r"""
        Check that we can restrict to supersolvable groups or not only
        """
        self.check_args("/Groups/Abstract/?supersolvable=yes&search_type=List", "1.1")
        self.not_check_args("/Groups/Abstract/?supersolvable=yes&search_type=List", "12.3")
        self.check_args("/Groups/Abstract/?supersolvable=no&search_type=List", "12.3")
        self.not_check_args("/Groups/Abstract/?supersolvable=no&search_type=List", "12.4")

    def test_monomial_search(self):
        r"""
        Check that we can restrict to monomial groups or not only
        """
        self.check_args("/Groups/Abstract/?monomial=yes&search_type=List", "2.1")
        self.not_check_args("/Groups/Abstract/?monomial=yes&search_type=List", "24.3")
        self.check_args("/Groups/Abstract/?monomial=no&search_type=List", "24.3")
        self.not_check_args("/Groups/Abstract/?monomial=no&search_type=List", "16.10")

    def test_rational_search(self):
        r"""
        Check that we can restrict to rational groups or not only
        """
        self.check_args("/Groups/Abstract/?rational=yes&search_type=List", "2.1")
        self.not_check_args("/Groups/Abstract/?rational=yes&search_type=List", "7.1")
        self.check_args("/Groups/Abstract/?rational=no&search_type=List", "3.1")
        self.not_check_args("/Groups/Abstract/?rational=no&search_type=List", "12.4")

    def test_rank_search(self):
        r"""
        Check that we can search by rank
        """
        self.check_args("/Groups/Abstract/?rank=3&search_type=List", "8.5")
        self.not_check_args("/Groups/Abstract/?rank=3&search_type=List", "18.5")

    #################################################################
    ##################### subgroup searches #########################
    #################################################################

    def test_subgroups_search(self):
        r"""
        Check that subgroup search page is working
        """
        self.check_args("/Groups/Abstract/?search_type=Subgroups", "1.1.1.a1.a1")
        self.check_args("/Groups/Abstract/sub/7.1.1.a1.a1","Ambient group ($G$) information")

    def test_subgroup_label_search(self):
        r"""
        Check that subgroup search by label is working
        """
        self.check_args("/Groups/Abstract/?search_type=Subgroups&subgroup=168.42", "504.157.3.a1.a1")

    def test_subgroup_order_search(self):
        r"""
        Check that subgroup search by label is working
        """
        self.check_args("/Groups/Abstract/?search_type=Subgroups&subgroup_order=15", "45.2.3.a1.b1")

    def test_subgroup_cyclic_search(self):
        r"""
        Check that we can restrict to cyclic or non-cyclic subgroups only
        """
        self.check_args("/Groups/Abstract/?cyclic=yes&search_type=Subgroups", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?cyclic=yes&search_type=Subgroups", "4.2.1.a1.a1")
        self.check_args("/Groups/Abstract/?cyclic=no&search_type=Subgroups", "4.2.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?cyclic=no&search_type=Subgroups", "8.5.4.a1.b1")

    def test_subgroup_abelian_search(self):
        r"""
        Check that we can restrict to abelian or non-abelian subgroups only
        """
        self.check_args("/Groups/Abstract/?abelian=yes&search_type=Subgroups", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?abelian=yes&search_type=Subgroups", "6.1.1.a1.a1")
        self.check_args("/Groups/Abstract/?abelian=no&search_type=Subgroups", "6.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?abelian=no&search_type=Subgroups", "6.1.2.a1.a1")

    def test_subgroup_solvable_search(self):
        r"""
        Check that we can restrict to solvable or non-solvable subgroups only
        """
        self.check_args("/Groups/Abstract/?solvable=yes&search_type=Subgroups", "3.1.3.a1.a1")
        self.not_check_args("/Groups/Abstract/?solvable=yes&search_type=Subgroups", "60.5.1.a1.a1")
        self.check_args("/Groups/Abstract/?solvable=no&search_type=Subgroups", "60.5.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?solvable=no&search_type=Subgroups", "3.1.3.a1.a1")

    def test_subgroup_normal_search(self):
        r"""
        Check that we can restrict to normal or non-normal subgroups only
        """
        self.check_args("/Groups/Abstract/?normal=yes&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?normal=yes&search_type=Subgroups", "6.1.3.a1.a1")
        self.check_args("/Groups/Abstract/?normal=no&search_type=Subgroups", "6.1.3.a1.a1")
        self.not_check_args("/Groups/Abstract/?normal=no&search_type=Subgroups", "4.1.2.a1.a1")

    def test_subgroup_characteristic_search(self):
        r"""
        Check that we can restrict to characteristic or non-characteristic subgroups only
        """
        self.check_args("/Groups/Abstract/?characteristic=yes&search_type=Subgroups", "3.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?characteristic=yes&search_type=Subgroups", "4.2.2.a1.b1")
        self.check_args("/Groups/Abstract/?characteristic=no&search_type=Subgroups", "4.2.2.a1.b1")
        self.not_check_args("/Groups/Abstract/?characteristic=no&search_type=Subgroups", "3.1.1.a1.a1")

    def test_subgroup_perfect_search(self):
        r"""
        Check that we can restrict to perfect or non-perfect subgroups only
        """
        page = self.tc.get("/Groups/Abstract/?perfect=yes&proper=yes&search_type=Subgroups", follow_redirects=True).get_data(as_text=True)
        assert "180.19.3.a1.a1" in page, "Missing perfect group"
        assert "4.2.2.a1.a1" not in page, "Incorrect perfect group"
        page = self.tc.get("/Groups/Abstract/?perfect=no&proper=yes&search_type=Subgroups", follow_redirects=True).get_data(as_text=True)
        assert "4.2.2.a1.a1" in page, "Missing imperfect group"
        assert "180.19.3.a1.a1" not in page, "Incorrect imperfect group"

    def test_subgroup_maximal_search(self):
        r"""
        Check that we can restrict to maximal or non-maximal subgroups only
        """
        self.check_args("/Groups/Abstract/?maximal=yes&search_type=Subgroups", "2.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?maximal=yes&search_type=Subgroups", "8.2.4.b1.b1")
        self.check_args("/Groups/Abstract/?maximal=no&search_type=Subgroups", "8.2.4.b1.b1")
        self.not_check_args("/Groups/Abstract/?maximal=no&search_type=Subgroups", "2.1.2.a1.a1")

    def test_subgroup_central_search(self):
        r"""
        Check that we can restrict to central or non-central subgroups only
        """
        self.check_args("/Groups/Abstract/?central=yes&search_type=Subgroups", "3.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?central=yes&search_type=Subgroups", "6.1.2.a1.a1")
        self.check_args("/Groups/Abstract/?central=no&search_type=Subgroups", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?central=no&search_type=Subgroups", "3.1.1.a1.a1")

    def test_subgroup_proper_search(self):
        r"""
        Check that we can restrict to proper or non-proper subgroups only
        """
        self.check_args("/Groups/Abstract/?proper=yes&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?proper=yes&search_type=Subgroups", "2.1.1.a1.a1")
        self.check_args("/Groups/Abstract/?proper=no&search_type=Subgroups", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?proper=no&search_type=Subgroups", "4.1.2.a1.a1")

    def test_subgroup_ambient_label_search(self):
        r"""
        Check that we can search by ambient label
        """
        self.check_args("/Groups/Abstract/?ambient=128.207&search_type=Subgroups", "128.207.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?ambient=128.207&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_ambient_order_search(self):
        r"""
        Check that we can search by ambient order
        """
        self.check_args("/Groups/Abstract/?ambient_order=128&search_type=Subgroups", "128.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?ambient_order=128&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_direct_search(self):
        r"""
        Check that we can restrict to subgroups that are direct products
        """
        self.check_args("/Groups/Abstract/?direct=yes&search_type=Subgroups", "4.2.2.a1.c1")
        self.not_check_args("/Groups/Abstract/?direct=yes&search_type=Subgroups", "4.1.2.a1.a1")
        self.check_args("/Groups/Abstract/?direct=no&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?direct=no&search_type=Subgroups", "4.2.2.a1.c1")

    def test_subgroup_semidirect_search(self):
        r"""
        Check that we can restrict to subgroups that are semidirect products
        """
        self.check_args("/Groups/Abstract/?split=yes&search_type=Subgroups", "4.2.2.a1.c1")
        self.not_check_args("/Groups/Abstract/?split=yes&search_type=Subgroups", "4.1.2.a1.a1")
        self.check_args("/Groups/Abstract/?split=no&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?split=no&search_type=Subgroups", "4.2.2.a1.c1")

    def test_subgroup_hall_search(self):
        r"""
        Check that we can restrict to subgroups that are Hall subgroups
        """
        self.check_args("/Groups/Abstract/?hall=yes&search_type=Subgroups", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?hall=yes&search_type=Subgroups", "8.5.2.a1.b1")
        self.check_args("/Groups/Abstract/?hall=no&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?hall=no&search_type=Subgroups", "2.1.1.a1.a1")

    def test_subgroup_sylow_search(self):
        r"""
        Check that we can restrict to subgroups that are Sylow subgroups
        """
        self.check_args("/Groups/Abstract/?sylow=yes&search_type=Subgroups", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?sylow=yes&search_type=Subgroups", "8.5.2.a1.f1")
        self.check_args("/Groups/Abstract/?sylow=no&search_type=Subgroups", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?sylow=no&search_type=Subgroups", "8.5.1.a1.a1")

    def test_subgroup_quotient_label_search(self):
        r"""
        Check that we can search by quotient label
        """
        self.check_args("/Groups/Abstract/?quotient=16.5&search_type=Subgroups", "32.12.16.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient=16.5&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_index_search(self):
        r"""
        Check that we can search by subgroup index
        """
        self.check_args("/Groups/Abstract/?quotient_order=17&search_type=Subgroups", "34.1.17.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_order=17&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_cyclic_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with cyclic quotients
        """
        self.check_args("/Groups/Abstract/?quotient_cyclic=yes&search_type=Subgroups", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_cyclic=yes&search_type=Subgroups", "4.2.4.a1.a1")
        self.check_args("/Groups/Abstract/?quotient_cyclic=no&search_type=Subgroups", "4.2.4.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_cyclic=no&search_type=Subgroups", "6.1.2.a1.a1")

    def test_subgroup_abelian_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with abelian quotients
        """
        self.check_args("/Groups/Abstract/?quotient_abelian=yes&search_type=Subgroups", "1.1.1.a1.a1")
        self.check_args("/Groups/Abstract/?quotient_abelian=no&search_type=Subgroups", "10.1.10.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_abelian=yes&search_type=Subgroups", "10.1.10.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_abelian=no&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_solvable_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with solvable quotients
        """
        self.check_args("/Groups/Abstract/?quotient_solvable=yes&search_type=Subgroups", "1.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_solvable=yes&search_type=Subgroups", "60.5.60.a1.a1")
        self.check_args("/Groups/Abstract/?quotient_solvable=no&search_type=Subgroups", "60.5.60.a1.a1")
        self.not_check_args("/Groups/Abstract/?quotient_solvable=no&search_type=Subgroups", "1.1.1.a1.a1")

    def test_subgroup_maximal_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with maximal quotients
        """
        self.check_args("/Groups/Abstract/?minimal_normal=yes&search_type=Subgroups", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/?minimal_normal=yes&search_type=Subgroups", "4.2.4.a1.a1")
        self.check_args("/Groups/Abstract/?minimal_normal=no&search_type=Subgroups", "4.2.4.a1.a1")
        self.not_check_args("/Groups/Abstract/?minimal_normal=no&search_type=Subgroups", "2.1.1.a1.a1")
