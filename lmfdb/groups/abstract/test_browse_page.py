from urllib.parse import parse_qs, urlsplit

from lmfdb import db
from lmfdb.tests import LmfdbTest
from lmfdb.groups.abstract.main import FAMILY_ALIASES, FAMILY_NAME_ALIASES

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

    def test_legacy_search_urls(self):
        r"""
        Check that old search URLs redirect to the new landing pages without
        dropping their filters.
        """
        cases = [
            ("/Groups/Abstract/?search_type=Subgroups&ambient=128.207",
             "/Groups/Abstract/Subgroups", {"ambient": ["128.207"]}),
            ("/Groups/Abstract/?search_type=RandomSubgroup&ambient=128.207",
             "/Groups/Abstract/Subgroups",
             {"ambient": ["128.207"], "search_type": ["RandomSubgroup"]}),
            ("/Groups/Abstract/?search_type=ComplexCharacters&dim=3",
             "/Groups/Abstract/ComplexCharacters", {"dim": ["3"]}),
            ("/Groups/Abstract/?search_type=RandomComplexCharacter&dim=3",
             "/Groups/Abstract/ComplexCharacters",
             {"dim": ["3"], "search_type": ["RandomComplexCharacter"]}),
            ("/Groups/Abstract/?search_type=ConjugacyClasses&group=12.4",
             "/Groups/Abstract/ConjugacyClasses", {"group": ["12.4"]}),
        ]
        for source, expected_path, expected_query in cases:
            response = self.tc.get(source)
            target = urlsplit(response.location)
            assert response.status_code == 307
            assert target.path == expected_path
            assert parse_qs(target.query) == expected_query

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

    def test_family_alias_lookup(self):
        r"""
        Check that Groups/Abstract/?jump finds the members of a family that are
        stored in gps_special_names under another family's name (issue #6654).

        One stored example for each entry of FAMILY_ALIASES; the final
        assertion keeps the two lists in sync.
        """
        cases = [
            # (alias key, jump argument, label of the stored group)
            (("Sp", 2), "Sp(2, 5)", "120.5"),            # Sp(2,q) = SL(2,q)
            (("PSp", 2), "PSp(2,5)", "60.5"),            # PSp(2,q) = PSL(2,q)
            (("GSp", 2), "GSp(2,7)", "2016.a"),          # GSp(2,q) = GL(2,q)
            (("ASp", 2), "ASp(2,2)", "24.12"),           # ASp(2,q) = ASL(2,q)
            (("PSigmaSp", 2), "PSigmaSp(2,5)", "60.5"),  # PSigmaSp(2,q) = PSigmaL(2,q)
            (("ASigmaSp", 2), "ASigmaSp(2,2)", "24.12"), # ASigmaSp(2,q) = ASigmaL(2,q)
            (("Spin", 3), "Spin(3,5)", "120.5"),         # Spin(3,q) = SL(2,q)
        ]
        for _, jump, label in cases:
            self.check_args("/Groups/Abstract/?jump=" + jump, label)
        assert set(alias for alias, _, _ in cases) == set(FAMILY_ALIASES), \
            "every entry of FAMILY_ALIASES needs a jump test"

    def check_jump(self, jump, label):
        r"""
        Check that the jump box redirects to a group's page.  This looks at the
        redirect target rather than the rendered page, because a short label
        such as 6.1 occurs as a substring on plenty of other pages.
        """
        r = self.tc.get("/Groups/Abstract/?jump=" + jump)
        assert r.status_code == 302, "%s did not redirect (%s)" % (jump, r.status_code)
        assert r.headers["Location"].endswith("/" + label), \
            "%s redirected to %s, not to %s" % (jump, r.headers["Location"], label)

    def test_family_name_alias_lookup(self):
        r"""
        Check that Groups/Abstract/?jump accepts the family name printed in a
        group page's "Groups of Lie type" row and the one printed in its Magma
        snippet, neither of which is always the name stored in gps_families
        (issue #6654).

        One stored example for each entry of FAMILY_NAME_ALIASES; the final
        assertion keeps the two lists in sync.  A + is percent-encoded, since a
        literal + in a query string means a space.
        """
        cases = [
            # (alias, jump argument, label of the stored group)
            # as printed in the "Groups of Lie type" row
            ("O", "O(3,2)", "6.1"),
            ("O+", "O%2B(4,2)", "72.40"),
            ("O-", "O-(4,2)", "120.34"),
            ("GO", "GO(3,2)", "6.1"),
            ("GO+", "GO%2B(2,2)", "2.1"),
            ("GO-", "GO-(2,2)", "6.1"),
            ("U", "U(2,2)", "18.3"),
            ("GU", "GU(2,2)", "18.3"),
            ("SO+", "SO%2B(4,2)", "72.40"),
            ("SO-", "SO-(4,2)", "120.34"),
            ("GSO+", "GSO%2B(2,2)", "2.1"),
            ("GSO-", "GSO-(2,2)", "6.1"),
            ("PSO+", "PSO%2B(4,2)", "72.40"),
            ("PSO-", "PSO-(4,2)", "120.34"),
            ("PO+", "PO%2B(4,2)", "72.40"),
            ("PO-", "PO-(4,2)", "120.34"),
            ("Omega+", "Omega%2B(4,2)", "36.10"),
            ("Omega-", "Omega-(4,2)", "60.5"),
            ("POmega+", "POmega%2B(4,2)", "36.10"),
            ("POmega-", "POmega-(4,2)", "60.5"),
            ("Spin+", "Spin%2B(4,2)", "36.10"),
            ("Spin-", "Spin-(4,2)", "60.5"),
            # as printed in the Magma snippet
            ("CO", "CO(3,2)", "6.1"),
            ("COPlus", "COPlus(2,2)", "2.1"),
            ("COMinus", "COMinus(2,2)", "6.1"),
            ("CSO", "CSO(3,2)", "6.1"),
            ("CSOPlus", "CSOPlus(2,2)", "2.1"),
            ("CSOMinus", "CSOMinus(2,2)", "6.1"),
            ("CSp", "CSp(4,2)", "720.763"),
            ("CSU", "CSU(2,2)", "6.1"),
            ("CU", "CU(2,2)", "18.3"),
            ("PGO", "PGO(3,2)", "6.1"),
            ("PGOPlus", "PGOPlus(4,2)", "72.40"),
            ("PGOMinus", "PGOMinus(4,2)", "120.34"),
            ("PGU", "PGU(2,2)", "6.1"),
        ]
        for _, jump, label in cases:
            self.check_jump(jump, label)
        assert set(alias for alias, _, _ in cases) == set(FAMILY_NAME_ALIASES), \
            "every entry of FAMILY_NAME_ALIASES needs a jump test"

        # the name Jen Paulhus reported, and the other reading of it
        self.check_jump("GO(5,3)", "103680.a")
        self.check_jump("O(5,3)", "103680.a")

    def test_family_name_aliases_are_unclaimed(self):
        r"""
        The alias rewrite runs before the gps_families regexes are tried, so an
        alias must not be a name that already means something else.  Magma's
        GO, GOPlus, GOMinus and GU are the names this rules out: we print those
        for the conformal groups Magma calls CO, COPlus, COMinus and CU.
        """
        families = set(db.gps_families.search({}, projection="family"))
        for alias, family in FAMILY_NAME_ALIASES.items():
            assert alias not in families, "%s is already a family name" % alias
            assert family in families, "%s is not a family name" % family
        # what Magma means by each of these; we must not read them that way
        magma_only = {"GO": "Orth", "GOPlus": "OrthPlus",
                      "GOMinus": "OrthMinus", "GU": "Unitary"}
        for name, magma_family in magma_only.items():
            assert FAMILY_NAME_ALIASES.get(name) != magma_family, \
                "%s is printed for a different group than Magma's %s" % (name, name)

    def test_absent_family_lookup(self):
        r"""
        Check that Groups/Abstract/?jump reports a group that exists but is not
        in the database as missing rather than as an invalid name.  This is the
        branch of group_jump that goes through valid_params, so it checks the
        family names used there against gps_families.
        """
        absent = "has not yet been added to the database"
        invalid = "is not a valid name for a group or subgroup"
        # even-dimensional families: GSp and ASp are newly accepted there, and
        # OrthPlus, POPlus, GSOPlus, GOrthPlus replace GOPlus, PGOPlus,
        # CSOPlus, COPlus
        for jump in ["GSp(100,5)", "ASp(100,5)", "OrthPlus(100,5)",
                     "POPlus(100,5)", "GSOPlus(100,5)", "GOrthPlus(100,5)"]:
            self.check_args("/Groups/Abstract/?jump=" + jump, absent)
        # odd-dimensional families: Orth, PO, GSO, GOrth replace GO, PGO, CSO, CO
        for jump in ["Orth(101,5)", "PO(101,5)", "GSO(101,5)", "GOrth(101,5)"]:
            self.check_args("/Groups/Abstract/?jump=" + jump, absent)
        # a dimension of the wrong parity is not a group at all
        self.check_args("/Groups/Abstract/?jump=GOrthPlus(101,5)", invalid)
        self.check_args("/Groups/Abstract/?jump=GOrth(100,5)", invalid)

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

    # when the test was first written 60.5 was only perfect and
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

    def test_famly_search(self):
        r"""
        Check that we can search by family
        """
        self.check_args("/Groups/Abstract/?family=A", ["12.3","60.5"])
        self.check_args("/Groups/Abstract/?family=C", ["6.2","27.1"])
        self.check_args("/Groups/Abstract/?family=D", ["30.3","48.7"])
        self.check_args("/Groups/Abstract/?family=GL", ["168.42","480.218"])
        self.check_args("/Groups/Abstract/?family=PSL", ["60.5","660.13"])
        self.check_args("/Groups/Abstract/?family=Q", ["4.1","64.54"])
        self.check_args("/Groups/Abstract/?family=S", ["1.1","120.34"])
        self.check_args("/Groups/Abstract/?family=SL", ["6.1","720.409"])
        self.check_args("/Groups/Abstract/?family=any", ["6.1", "18.1", "18.2", "24.3"])
        # not checks
        self.not_check_args("/Groups/Abstract/?family=A", "6.1")
        self.not_check_args("/Groups/Abstract/?family=C", "8.3")
        self.not_check_args("/Groups/Abstract/?family=D", "16.11")
        self.not_check_args("/Groups/Abstract/?family=GL", "16.11")
        self.not_check_args("/Groups/Abstract/?family=PSL", "16.11")
        self.not_check_args("/Groups/Abstract/?family=Q", "16.11")
        self.not_check_args("/Groups/Abstract/?family=S", "16.11")
        self.not_check_args("/Groups/Abstract/?family=SL", "16.11")
        self.not_check_args("/Groups/Abstract/?family=any", "D_4:C_2")

    def test_order_stats_search(self):
        r"""
        Check that we can search by order statistics
        """
        self.check_args("/Groups/Abstract/?order_stats=1^1%2C2^3%2C3^2", "6.1")
        self.not_check_args("/Groups/Abstract/?order_stats=1^1%2C2^3%2C3^2", "10.1")

    #################################################################
    ##################### advanced searches #########################
    #################################################################

    def test_outer_group_search(self):
        r"""
        Check that we can search by outer automorphism group
        """
        self.check_args("/Groups/Abstract/?outer_group=4.2", "8.1")
        self.not_check_args("/Groups/Abstract/?outer_group=4.2", "16.8")

    def test_outer_order_search(self):
        r"""
        Check that we can search by order of outer automorphism group
        """
        self.check_args("/Groups/Abstract/?outer_order=3", "14.1")
        self.not_check_args("/Groups/Abstract/?outer_order=3", "18.3")

    def test_metabelian_search(self):
        r"""
        Check that we can restrict to metabelian groups or not only
        """
        self.check_args("/Groups/Abstract/?metabelian=yes", "1.1")
        self.not_check_args("/Groups/Abstract/?metabelian=yes", "24.3")
        self.check_args("/Groups/Abstract/?metabelian=no", "24.3")
        self.not_check_args("/Groups/Abstract/?metabelian=no", "13.1")

    def test_metacyclic_search(self):
        r"""
        Check that we can restrict to metacyclic groups or not only
        """
        self.check_args("/Groups/Abstract/?metacyclic=yes", "1.1")
        self.not_check_args("/Groups/Abstract/?metacyclic=yes", "12.3")
        self.check_args("/Groups/Abstract/?metacyclic=no", "12.3")
        self.not_check_args("/Groups/Abstract/?metacyclic=no", "12.2")

    def test_almost_simple_search(self):
        r"""
        Check that we can restrict to almost simple groups or not only
        """
        self.check_args("/Groups/Abstract/?almost_simple=yes", "60.5")
        self.not_check_args("/Groups/Abstract/?almost_simple=yes", "8.3")
        self.check_args("/Groups/Abstract/?almost_simple=no", "1.1")
        self.not_check_args("/Groups/Abstract/?almost_simple=no", "60.5")

    def test_quasisimple_search(self):
        r"""
        Check that we can restrict to quasisimple groups or not only
        """
        self.check_args("/Groups/Abstract/?quasisimple=yes", "60.5")
        self.not_check_args("/Groups/Abstract/?quasisimple=yes", "7.1")
        self.check_args("/Groups/Abstract/?quasisimple=no", "1.1")
        self.not_check_args("/Groups/Abstract/?quasisimple=no", "60.5")

    def test_Agroup_search(self):
        r"""
        Check that we can restrict to A-group groups or not only
        """
        self.check_args("/Groups/Abstract/?Agroup=yes", "1.1")
        self.not_check_args("/Groups/Abstract/?Agroup=yes", "16.3")
        self.check_args("/Groups/Abstract/?Agroup=no", "8.3")
        self.not_check_args("/Groups/Abstract/?Agroup=no", "16.14")

    def test_Zgroup_search(self):
        r"""
        Check that we can restrict to Z-group groups or not only
        """
        self.check_args("/Groups/Abstract/?Zgroup=yes", "1.1")
        self.not_check_args("/Groups/Abstract/?Zgroup=yes", "12.3")
        self.check_args("/Groups/Abstract/?Zgroup=no", "4.2")
        self.not_check_args("/Groups/Abstract/?Zgroup=no", "12.2")

    def test_derived_length_search(self):
        r"""
        Check that we can search by derived length
        """
        self.check_args("/Groups/Abstract/?derived_length=3", "24.3")
        self.not_check_args("/Groups/Abstract/?derived_length=3", "16.13")

    def test_frattini_label_search(self):
        r"""
        Check that we can search by Frattini subgroup
        """
        self.check_args("/Groups/Abstract/?frattini_label=4.2", "16.2")
        self.not_check_args("/Groups/Abstract/?frattini_label=4.2", "5.1")

    def test_supersolvable_search(self):
        r"""
        Check that we can restrict to supersolvable groups or not only
        """
        self.check_args("/Groups/Abstract/?supersolvable=yes", "1.1")
        self.not_check_args("/Groups/Abstract/?supersolvable=yes", "12.3")
        self.check_args("/Groups/Abstract/?supersolvable=no", "12.3")
        self.not_check_args("/Groups/Abstract/?supersolvable=no", "12.4")

    def test_monomial_search(self):
        r"""
        Check that we can restrict to monomial groups or not only
        """
        self.check_args("/Groups/Abstract/?monomial=yes", "2.1")
        self.not_check_args("/Groups/Abstract/?monomial=yes", "24.3")
        self.check_args("/Groups/Abstract/?monomial=no", "24.3")
        self.not_check_args("/Groups/Abstract/?monomial=no", "16.10")

    def test_rational_search(self):
        r"""
        Check that we can restrict to rational groups or not only
        """
        self.check_args("/Groups/Abstract/?rational=yes", "2.1")
        self.not_check_args("/Groups/Abstract/?rational=yes", "7.1")
        self.check_args("/Groups/Abstract/?rational=no", "3.1")
        self.not_check_args("/Groups/Abstract/?rational=no", "12.4")

    def test_rank_search(self):
        r"""
        Check that we can search by rank
        """
        self.check_args("/Groups/Abstract/?rank=3", "8.5")
        self.not_check_args("/Groups/Abstract/?rank=3", "18.5")

    #################################################################
    ##################### subgroup searches #########################
    #################################################################

    def test_subgroups_search(self):
        r"""
        Check that subgroup search page is working
        """
        self.check_args("/Groups/Abstract/Subgroups", "ambient order")
        self.check_args("/Groups/Abstract/sub/7.1.1.a1.a1","Ambient group ($G$) information")

    def test_subgroup_label_search(self):
        r"""
        Check that subgroup search by label is working
        """
        self.check_args("/Groups/Abstract/Subgroups?subgroup=168.42", "504.157.3.a1.a1")

    def test_subgroup_order_search(self):
        r"""
        Check that subgroup search by label is working
        """
        self.check_args("/Groups/Abstract/Subgroups?subgroup_order=15", "45.2.3.a1.b1")

    def test_subgroup_cyclic_search(self):
        r"""
        Check that we can restrict to cyclic or non-cyclic subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?cyclic=yes", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?cyclic=yes", "4.2.1.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?cyclic=no", "4.2.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?cyclic=no", "8.5.4.a1.b1")

    def test_subgroup_abelian_search(self):
        r"""
        Check that we can restrict to abelian or non-abelian subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?abelian=yes", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?abelian=yes", "6.1.1.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?abelian=no", "6.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?abelian=no", "6.1.2.a1.a1")

    def test_subgroup_solvable_search(self):
        r"""
        Check that we can restrict to solvable or non-solvable subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?solvable=yes", "3.1.3.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?solvable=yes", "60.5.1.a1.a1")
        # Solvable = False requires a 30GB index to support, so we disable them for now
        #self.check_args("/Groups/Abstract/Subgroups?solvable=no", "60.5.1.a1.a1")
        #self.not_check_args("/Groups/Abstract/Subgroups?solvable=no", "3.1.3.a1.a1")

    def test_subgroup_normal_search(self):
        r"""
        Check that we can restrict to normal or non-normal subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?normal=yes", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?normal=yes", "6.1.3.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?normal=no", "6.1.3.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?normal=no", "4.1.2.a1.a1")

    def test_subgroup_characteristic_search(self):
        r"""
        Check that we can restrict to characteristic or non-characteristic subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?characteristic=yes", "3.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?characteristic=yes", "4.2.2.a1.b1")
        self.check_args("/Groups/Abstract/Subgroups?characteristic=no", "4.2.2.a1.b1")
        self.not_check_args("/Groups/Abstract/Subgroups?characteristic=no", "3.1.1.a1.a1")

    def test_subgroup_perfect_search(self):
        r"""
        Check that we can restrict to perfect or non-perfect subgroups only
        """
        return
        page = self.tc.get("/Groups/Abstract/Subgroups?perfect=yes&nontrivproper=yes", follow_redirects=True).get_data(as_text=True)
        assert "180.19.3.a1.a1" in page, "Missing perfect group"
        assert "4.2.2.a1.a1" not in page, "Incorrect perfect group"
        page = self.tc.get("/Groups/Abstract/Subgroups?perfect=no&nontrivproper=yes", follow_redirects=True).get_data(as_text=True)
        assert "4.2.2.a1.a1" in page, "Missing imperfect group"
        assert "180.19.3.a1.a1" not in page, "Incorrect imperfect group"

    def test_subgroup_maximal_search(self):
        r"""
        Check that we can restrict to maximal or non-maximal subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?maximal=yes", "2.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?maximal=yes", "8.2.4.b1.a1")
        self.check_args("/Groups/Abstract/Subgroups?maximal=no", "8.2.4.b1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?maximal=no", "2.1.2.a1.a1")

    def test_subgroup_central_search(self):
        r"""
        Check that we can restrict to central or non-central subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?central=yes", "3.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?central=yes", "6.1.2.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?central=no", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?central=no", "3.1.1.a1.a1")

    def test_subgroup_proper_search(self):
        r"""
        Check that we can restrict to proper or non-proper subgroups only
        """
        self.check_args("/Groups/Abstract/Subgroups?nontrivproper=yes", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?nontrivproper=yes", "2.1.1.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?nontrivproper=no", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?nontrivproper=no", "4.1.2.a1.a1")

    def test_subgroup_ambient_label_search(self):
        r"""
        Check that we can search by ambient label
        """
        self.check_args("/Groups/Abstract/Subgroups?ambient=128.207", "128.207.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?ambient=128.207", "1.1.1.a1.a1")

    def test_subgroup_ambient_order_search(self):
        r"""
        Check that we can search by ambient order
        """
        self.check_args("/Groups/Abstract/Subgroups?ambient_order=128", "128.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?ambient_order=128", "1.1.1.a1.a1")

    def test_subgroup_direct_search(self):
        r"""
        Check that we can restrict to subgroups that are direct products
        """
        self.check_args("/Groups/Abstract/Subgroups?direct=yes", "4.2.2.a1.c1")
        self.not_check_args("/Groups/Abstract/Subgroups?direct=yes", "4.1.2.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?direct=no", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?direct=no", "4.2.2.a1.c1")

    def test_subgroup_semidirect_search(self):
        r"""
        Check that we can restrict to subgroups that are semidirect products
        """
        self.check_args("/Groups/Abstract/Subgroups?split=yes", "4.2.2.a1.c1")
        self.not_check_args("/Groups/Abstract/Subgroups?split=yes", "4.1.2.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?split=no", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?split=no", "4.2.2.a1.c1")

    def test_subgroup_hall_search(self):
        r"""
        Check that we can restrict to subgroups that are Hall subgroups
        """
        self.check_args("/Groups/Abstract/Subgroups?hall=yes", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?hall=yes", "8.5.2.a1.b1")
        self.check_args("/Groups/Abstract/Subgroups?hall=no", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?hall=no", "2.1.1.a1.a1")

    def test_subgroup_sylow_search(self):
        r"""
        Check that we can restrict to subgroups that are Sylow subgroups
        """
        self.check_args("/Groups/Abstract/Subgroups?sylow=yes", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?sylow=yes", "8.5.2.a1.f1")
        self.check_args("/Groups/Abstract/Subgroups?sylow=no", "4.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?sylow=no", "8.5.1.a1.a1")

    def test_subgroup_quotient_label_search(self):
        r"""
        Check that we can search by quotient label
        """
        self.check_args("/Groups/Abstract/Subgroups?quotient=16.5", "32.12.16.b1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient=16.5", "1.1.1.a1.a1")

    def test_subgroup_index_search(self):
        r"""
        Check that we can search by subgroup index
        """
        self.check_args("/Groups/Abstract/Subgroups?quotient_order=17", "34.1.17.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_order=17", "1.1.1.a1.a1")

    def test_subgroup_cyclic_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with cyclic quotients
        """
        self.check_args("/Groups/Abstract/Subgroups?quotient_cyclic=yes", "6.1.2.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_cyclic=yes", "4.2.4.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?quotient_cyclic=no", "4.2.4.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_cyclic=no", "6.1.2.a1.a1")

    def test_subgroup_abelian_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with abelian quotients
        """
        self.check_args("/Groups/Abstract/Subgroups?quotient_abelian=yes", "1.1.1.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?quotient_abelian=no", "10.1.10.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_abelian=yes", "10.1.10.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_abelian=no", "1.1.1.a1.a1")

    def test_subgroup_solvable_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with solvable quotients
        """
        self.check_args("/Groups/Abstract/Subgroups?quotient_solvable=yes", "1.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?quotient_solvable=yes", "60.5.60.a1.a1")
        # The following searches require a 30GB index to support, so we disable them for now
        #self.check_args("/Groups/Abstract/Subgroups?quotient_solvable=no", "60.5.60.a1.a1")
        #self.not_check_args("/Groups/Abstract/Subgroups?quotient_solvable=no", "1.1.1.a1.a1")

    def test_subgroup_maximal_quotient_search(self):
        r"""
        Check that we can restrict to subgroups with maximal quotients
        """
        self.check_args("/Groups/Abstract/Subgroups?minimal_normal=yes", "2.1.1.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?minimal_normal=yes", "4.2.4.a1.a1")
        self.check_args("/Groups/Abstract/Subgroups?minimal_normal=no", "4.2.4.a1.a1")
        self.not_check_args("/Groups/Abstract/Subgroups?minimal_normal=no", "2.1.1.a1.a1")

    def test_character_search(self):
        r"""
        Check that complex character search works
        """
        self.check_args("/Groups/Abstract/ComplexCharacters?dim=3", [
            "21.1.3a2", # character of C7:C3
            "4.0.2197.1", # character values for several characters of 39.1
        ])
        self.check_args("/Groups/Abstract/ComplexCharacters?dim=12&faithful=yes", "384.592.12a1")
        self.check_args("/Groups/Abstract/ComplexCharacters?dim=13&cyclotomic_n=39", ["4563.a.13b18", "351.a1.a1"]) # character label, center
        self.check_args("/Groups/Abstract/ComplexCharacters?image_isoclass=12.4&kernel_order=6", "72.21.2d")
        self.check_args("/Groups/Abstract/ComplexCharacters?faithful=yes&center_order=144", "576.176.2c1")
        self.check_args("/Groups/Abstract/ComplexCharacters","Enter a group label or a character table label.")

    def test_highlighted_character(self):
        r"""
        Check that character links work
        """
        self.check_args("/Groups/Abstract/char_table/72.43?char_highlight=72.43.6a", "The row representing the character 72.43.6a is highlighted below.")
        self.check_args("/Groups/Abstract/Qchar_table/96.71?char_highlight=96.71.6a", "The row representing the character 96.71.6a is highlighted below.")

    def test_conj_class_search(self):
        r"""
        Check that conjugacy class search works
        """
        self.check_args("/Groups/Abstract/ConjugacyClasses","e.g. 3, or a range like 3..5")
        self.check_args("/Groups/Abstract/ConjugacyClasses?group=12.4", ["3.a1.a1", "6A"])
        self.check_args("/Groups/Abstract/ConjugacyClasses?group=128.15", r"\OD_{16}:C_8" #group name
                )

    def test_highlighted_conj_class(self):
        r"""
        Check that conjugacy class links work
        """
        self.check_args("/Groups/Abstract/char_table/24.7?cc_highlight=4B-1&cc_highlight_i=9", r"The column representing the conjugacy class 4B-1 is highlighted below.")

    def test_diagram_search(self):
        r"""
        Check that diagram search page loads correctly
        """
        L = self.tc.get('/Groups/Abstract/?order=1-100&search_type=Diagram&count=100')
        data = L.get_data(as_text=True)
        # Check that D3 diagram template elements are present
        assert 'my_dataviz' in data
        assert 'pointRadius' in data
