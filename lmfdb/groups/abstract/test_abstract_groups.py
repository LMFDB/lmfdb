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
        # assert r'<tdclass="label">Order</td><td>${2^{8}}$</td></tr>' in page
        # self.check_args("/Variety/Abelian/Fq/2/79/ar_go", "Principally polarizable")

    def test_abstract_group_download(self):
        r"""
        Test downloading on search results page.
        """
        response = self.tc.get("/Groups/Abstract/384.5458/download/gap")
        self.assertTrue("Various presentations of this group are stored" in response.get_data(as_text=True))
        self.assertTrue("PcGroupCode(293961739841108398509157889,384);" in response.get_data(as_text=True))
        self.assertTrue("perfect := false," in response.get_data(as_text=True))
        self.assertTrue("chartbl_384_5458.NrConjugacyClasses:= 240;" in response.get_data(as_text=True))
        response = self.tc.get("/Groups/Abstract/384.5458/download/magma")
        self.assertTrue("GPerm := PermutationGroup< 23 | (1,2,4,7,5,8,11,14,3,6,9,12,10,13,15,16)(18,20), (1,3)(2,6)(4,9)(5,10)(7,12)(8,13)(11,15)(14,16)(17,18)(19,20), (1,2,4,7,5,8,11,14,3,6,9,12,10,13,15,16), (21,23,22), (17,19)(18,20), (1,4,5,11,3,9,10,15)(2,7,8,14,6,12,13,16), (1,5,3,10)(2,8,6,13)(4,11,9,15)(7,14,12,16), (1,3)(2,6)(4,9)(5,10)(7,12)(8,13)(11,15)(14,16) >;" in response.get_data(as_text=True))
        self.assertTrue("monomial := true," in response.get_data(as_text=True))
        self.assertTrue("CR := CharacterRing(G);" in response.get_data(as_text=True))

    def test_conj_decode(self):
        from lmfdb.groups.abstract.web_groups import WebAbstractGroup
        G = WebAbstractGroup("18.2")
        self.assertTrue(all(G.decode_as_pcgs(i, True) == f"a^{{{i}}}" for i in range(2,18)))

    def character_counts(self):
        # There was a bug in showing all dimensions of irreducible characters when we don't store the complex character table
        page = self.tc.get("/Groups/Abstract/1800.328").get_data(as_text=True).replace(" ","").replace("\n","")
        self.assertTrue("<td>30</td><td>30</td><td>30</td>" in page)

    def test_live_pages(self):
        self.check_args("/Groups/Abstract/1920.240463", [
            "nonsolvable",
            "10 subgroups in one conjugacy class",
            "240.190", # socle
            "960.5735", # max sub
            "960.5692", # max quo
            "rgb(20,82,204)", # color in image
        ])
        self.check_args("/Groups/Abstract/1536.123", [
            r"C_3 \times ((C_2\times C_8) . (C_4\times C_8))", # latex
            "216", # number of 2-dimensional complex characters
            "j^{3}", # presentation
            "metabelian", # boolean quantities
        ])
        self.check_args("/Groups/Abstract/ab/2.2.3.4.5.6.7.8.9.10", [
            "7257600", # order
            "2520", # exponent
            r"C_{2}^{3} \times C_{6} \times C_{60} \times C_{2520}", # latex
            r"2^{40} \cdot 3^{10} \cdot 5^{2} \cdot 7", # order of automorphism group
            "1990656", # number of elements of order 2520
            r"C_2\times C_{12}", # Frattini
        ])
        self.check_args("/Groups/Abstract/ab/2_50", [ # large elementary abelian 2-group
            "4432676798593", # factor of aut_order
        ])
        self.check_args("/Groups/Abstract/ab/3000", [ # large cyclic group
            r"C_2^3\times C_{100}", # automorphism group structure
        ])

    def test_underlying_data(self):
        self.check_args("/Groups/Abstract/data/2520.a", [
            "gps_groups", "number_normal_subgroups",
            "gps_conj_classes", "representative",
            "gps_qchar", "cdim",
            "gps_char", "indicator",
            "gps_subgroup_search", "mobius_sub"])
        self.check_args("/Groups/Abstract/sdata/16.8.2.b1.a1", [
            "gps_subgroup_search", "16.8.2.b1.a1",
            "gps_groups", "[28776, 16577, 5167]", # perm_gens
            "[[1, 1, 1]]"]) # faithful_reps
