import re
from ast import literal_eval

from lmfdb.tests import LmfdbTest

# The graphs that diagram_js_string builds for a group page, in order
DIAGRAM_MODES = [("subgroup", ""), ("subgroup", "aut"), ("normal", ""), ("normal", "aut"),
                 ("maximal", ""), ("maximal", "aut")]


def diagram_graphs(page, label):
    r"""
    The graphs passed to make_sdiagram on a group page or a fullpage diagram: one
    entry for each mode of DIAGRAM_MODES, empty when that diagram is not drawn.
    Returns None when the page contains no subgroup diagram at all.
    """
    m = re.search(r'make_sdiagram\("subdiagram", "%s", (.*)\);' % re.escape(label), page)
    if m is None:
        return None
    graphs, order_lookup, layers = literal_eval("(" + m.group(1) + ")")
    assert len(graphs) == len(DIAGRAM_MODES)
    return graphs


def graph_content(graph):
    r"""
    The short labels of the nodes and the edges of one graph from diagram_graphs
    """
    nodes, edges = graph
    return {node[1] for node in nodes}, {tuple(edge) for edge in edges}


def profile_content(page, cls):
    r"""
    The contents of one of the subgroup profile divs on a group page
    """
    return re.search(r'<div class="%s"[^>]*>(.*?)</div>' % cls, page, re.DOTALL).group(1)


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

    def test_subgroups(self):
        self.check_args("/Groups/Abstract/sub/78125.1385.15625.A","Group of order 31250000")
        self.check_args("/Groups/Abstract/sub/16384.mv.8._.BQX",'The ambient group is <a title="Abelian group [group.abelian]"')

    def test_maximal_subgroups(self):
        r"""
        Check the maximal subgroup mode of the subgroup diagram/profile
        """
        # S4 has maximal subgroups A4 (2.a1.a1), D4 (3.a1.a1) and S3 (4.a1.a1),
        # none of which are related by an automorphism; 1.a1.a1 is S4 itself,
        # which sits at the top of the maximal diagram
        page = self.tc.get("/Groups/Abstract/24.12").get_data(as_text=True)
        assert "maximal subgroups</button>" in page
        profile = profile_content(page, "maximal_profile")
        assert "Classes of maximal subgroups up to conjugation" in profile
        assert "A_4" in profile and "D_4" in profile and "S_3" in profile
        autprofile = profile_content(page, "maximal_autprofile")
        assert "Classes of maximal subgroups up to automorphism" in autprofile
        assert "A_4" in autprofile and "D_4" in autprofile and "S_3" in autprofile
        graphs = diagram_graphs(page, "24.12")
        for mode in [("maximal", ""), ("maximal", "aut")]:
            nodes, edges = graph_content(graphs[DIAGRAM_MODES.index(mode)])
            assert nodes == {"1.a1.a1", "2.a1.a1", "3.a1.a1", "4.a1.a1"}
            assert edges == {("2.a1.a1", "1.a1.a1"), ("3.a1.a1", "1.a1.a1"), ("4.a1.a1", "1.a1.a1")}

    def test_maximal_subgroups_layout(self):
        r"""
        Check that the classes of maximal subgroups are laid out side by side rather
        than stacked in one column, which would suggest that each is contained in the
        next one up
        """
        # D20 has four classes of maximal subgroups, three of order 20 and one of order
        # 8, while the three classes of S4 all have different orders (12, 8 and 6) and so
        # land on three different rows of the diagram; both have to fan out
        for label in ["40.6", "24.12"]:
            page = self.tc.get("/Groups/Abstract/%s" % label).get_data(as_text=True)
            graphs = diagram_graphs(page, label)
            for mode in [("maximal", ""), ("maximal", "aut")]:
                nodes = graphs[DIAGRAM_MODES.index(mode)][0]
                whole_group = max(nodes, key=lambda node: node[4])
                maxima = [node for node in nodes if node is not whole_group]
                assert len(maxima) > 1
                # x-coordinates for the two height modes: by number of prime divisors
                # of the order, and by the order itself
                for x in [6, 7]:
                    columns = sorted(node[x] for node in maxima)
                    assert len(set(columns)) == len(maxima), f"{label} {mode} shares a column"
                    # evenly spaced, with the whole group centered above them
                    gaps = [columns[i] - columns[i - 1] for i in range(1, len(columns))]
                    assert max(gaps) - min(gaps) <= 1, f"{label} {mode} spaced unevenly"
                    assert abs(whole_group[x] - (columns[0] + columns[-1]) / 2) <= 1

    def test_maximal_subgroups_diagram(self):
        r"""
        Check that the maximal subgroup diagram is a star with the whole group on
        top, even when the full subgroup diagram is too large to be displayed
        """
        from lmfdb.groups.abstract.web_groups import WebAbstractGroup
        # 32.45 has 118 classes of subgroups, too many to draw, but only 15 classes
        # of maximal subgroups, which fuse into 2 classes up to automorphism
        G = WebAbstractGroup("32.45")
        assert G.diagram_count("subgroup", "", limit=100) == 0
        assert G.diagram_count("maximal", "", limit=100) == 16
        assert G.diagram_count("maximal", "aut", limit=100) == 3
        nodes, edges = G.subgroup_lattice("maximal", "")
        top = [H for H in nodes if H.quotient_order == 1]
        maxima = [H for H in nodes if H.maximal]
        assert len(top) == 1
        assert len(maxima) == 15
        assert len(nodes) == len(maxima) + 1
        assert {tuple(edge) for edge in edges} == {(H.short_label, top[0].short_label) for H in maxima}
        # Up to automorphism there is exactly one node for each autjugacy class
        aut_nodes, aut_edges = G.subgroup_lattice("maximal", "aut")
        assert len(aut_nodes) == G.diagram_count("maximal", "aut")
        assert len({H.aut_label for H in aut_nodes}) == len(aut_nodes)
        assert {H.aut_label for H in aut_nodes} == {H.aut_label for H in nodes}
        aut_top = [H for H in aut_nodes if H.quotient_order == 1]
        assert len(aut_top) == 1
        assert len(aut_edges) == len(aut_nodes) - 1
        assert {target for source, target in aut_edges} == {aut_top[0].short_label}
        # Only the two maximal diagrams and the normal diagram up to automorphism
        # are small enough to be drawn on the group page
        page = self.tc.get("/Groups/Abstract/32.45").get_data(as_text=True)
        graphs = diagram_graphs(page, "32.45")
        assert [DIAGRAM_MODES[i] for i, graph in enumerate(graphs) if graph] == [
            ("normal", "aut"), ("maximal", ""), ("maximal", "aut")]
        assert graph_content(graphs[DIAGRAM_MODES.index(("maximal", ""))]) == (
            {H.short_label for H in nodes},
            {(H.short_label, top[0].short_label) for H in maxima})
        assert graph_content(graphs[DIAGRAM_MODES.index(("maximal", "aut"))]) == (
            {H.short_label for H in aut_nodes},
            {tuple(edge) for edge in aut_edges})
        profile = profile_content(page, "maximal_profile")
        assert "x 14" in profile  # 14 conjugate copies of C_2^2 x C_4

    def test_maximal_subgroups_fullpage(self):
        r"""
        Check that the fullpage maximal subgroup diagrams contain the right graph
        """
        from lmfdb.groups.abstract.web_groups import WebAbstractGroup
        for label, title, mode in [
                ("24.12", "Diagram of maximal subgroups up to conjugation", ("maximal", "")),
                ("24.12", "Diagram of maximal subgroups up to automorphism", ("maximal", "aut")),
                ("32.45", "Diagram of maximal subgroups up to conjugation", ("maximal", "")),
                ("32.45", "Diagram of maximal subgroups up to automorphism", ("maximal", "aut"))]:
            sub_all, sub_aut = mode
            G = WebAbstractGroup(label)
            shown = [H for H in G.subgroups.values() if H.maximal or H.quotient_order == 1]
            response = self.tc.get(f"/Groups/Abstract/{sub_all}_{sub_aut}diagram/{label}")
            assert response.status_code == 200
            page = response.get_data(as_text=True)
            assert title in page
            assert f'show_info("{sub_all}_{sub_aut}diagram")' in page
            graphs = diagram_graphs(page, label)
            assert graphs is not None, f"no diagram on the fullpage {sub_all} {sub_aut} diagram for {label}"
            # The fullpage version contains only the requested diagram
            assert [DIAGRAM_MODES[i] for i, graph in enumerate(graphs) if graph] == [mode]
            drawn, edges = graph_content(graphs[DIAGRAM_MODES.index(mode)])
            whole_group, = [H.short_label for H in shown if H.quotient_order == 1]
            assert edges == {(short_label, whole_group) for short_label in drawn - {whole_group}}
            if sub_aut:
                # one representative from each autjugacy class, so 3 nodes for 32.45
                assert drawn <= {H.short_label for H in shown}
                assert len(drawn) == G.diagram_count(sub_all, sub_aut)
                assert ({H.aut_label for H in shown if H.short_label in drawn}
                        == {H.aut_label for H in shown})
            else:
                assert drawn == {H.short_label for H in shown}

    def test_maximal_subgroups_without_inclusions(self):
        r"""
        Check that maximal subgroups are shown for a group whose subgroup
        inclusions were never computed
        """
        from lmfdb.groups.abstract.web_groups import WebAbstractGroup
        G = WebAbstractGroup("1024.dip")
        assert G.maximal_subgroups_known
        assert not G.subgroup_inclusions_known
        assert G.maximal_profile
        # No diagram can be drawn without the inclusions, but the profile is still shown
        assert G.diagram_count("maximal", "", limit=100) == 0
        page = self.tc.get("/Groups/Abstract/1024.dip").get_data(as_text=True)
        assert diagram_graphs(page, "1024.dip") is None
        profile = profile_content(page, "maximal_profile")
        assert "not computed" not in profile
        # 255 classes of maximal subgroups, all of order 512
        assert "Order 512:" in profile
        assert r"$C_2^6:D_4$</a> x 248" in profile
        assert r"$D_4\times C_2^6$</a> x 3" in profile
        assert r"$C_2^8.C_2$</a> x 3" in profile
        assert r"$C_2^9$</a>" in profile
