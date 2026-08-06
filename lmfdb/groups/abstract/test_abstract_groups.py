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

    def test_subgroups(self):
        self.check_args("/Groups/Abstract/sub/78125.1385.15625.A","Group of order 31250000")
        self.check_args("/Groups/Abstract/sub/16384.mv.8._.BQX",'The ambient group is <a title="Abelian group [group.abelian]"')

    def test_hash_display(self):
        # Letter-labeled orders carry a genuine Magma hash, shown with a search link.
        self.check_args("/Groups/Abstract/2016.a", [
            "374703223365377769",
            "/Groups/Abstract/hash/2016/374703223365377769"])
        # Identifiable/enumerated orders store hash == counter, so the row is suppressed.
        self.not_check_args("/Groups/Abstract/60.5", "all groups with this order and hash")
        self.not_check_args("/Groups/Abstract/512.11", "all groups with this order and hash")

    def test_hash_resolution(self):
        # The one place that says which groups have a given order and hash.
        from lmfdb.groups.abstract.hash_lookup import (
            hash_constraint, resolve_order_hash, structural_hash)
        # gps_groups.hash is the label counter at order 512; the hash itself is
        # in gps_smallhash, whose tables are complete.
        res = resolve_order_hash(512, 1584677793794603025)
        assert res.complete and res.source == "gps_smallhash"
        assert res.labels == ["512.11"] and res.unique_label() == "512.11"
        assert hash_constraint(512, [1584677793794603025]) == {"counter": {"$in": [11]}}
        # A complete collision cluster names groups with no LMFDB row too.
        res = resolve_order_hash(78125, 3521944227884464685)
        assert res.complete
        assert res.labels == ["78125.82", "78125.335", "78125.340"]
        assert res.in_lmfdb() == ["78125.335", "78125.340"]
        assert res.unique_label() is None
        # Everywhere else the stored gps_groups.hash is the hash.
        res = resolve_order_hash(2016, 374703223365377769)
        assert not res.complete and res.source == "gps_groups"
        assert res.labels == ["2016.a"]
        assert hash_constraint(2016, [374703223365377769]) == {"hash": 374703223365377769}
        # With no single order, the counter-storing orders are excluded from
        # the column match and resolved separately.
        constraint = hash_constraint(None, [1584677793794603025])
        assert constraint == {"$or": [
            {"hash": 1584677793794603025,
             "order": {"$nin": [512, 1152, 1536, 1920, 2187, 15625]}},
            {"order": 512, "counter": {"$in": [11]}}]}
        assert hash_constraint(None, [11]) == {"$or": [
            {"hash": 11, "order": {"$nin": [512, 1152, 1536, 1920, 2187, 15625]}}]}
        # A counter stored in the hash column is not a hash to display.
        assert structural_hash(11, 11) is None
        assert structural_hash(1, 374703223365377769) == 374703223365377769

    def test_hash_jump(self):
        # A unique match in a complete table determines the group.
        r = self.tc.get("/Groups/Abstract/?jump=512%231584677793794603025")
        assert r.status_code in (301, 302), "jump did not redirect"
        assert "/Groups/Abstract/512.11" in r.headers["Location"]
        # A collision cluster does not: it lands on the hash page, which lists
        # the whole cluster including the groups with no database row.
        page = self.tc.get("/Groups/Abstract/?jump=78125%233521944227884464685",
                           follow_redirects=True).get_data(as_text=True)
        for lab in ["78125.82", "78125.335", "78125.340"]:
            assert lab in page, "%s not on the hash page" % lab

    def test_hash_page(self):
        # The complete cluster, not just the part of it in gps_groups.
        page = self.tc.get("/Groups/Abstract/hash/78125/3521944227884464685",
                           follow_redirects=True).get_data(as_text=True)
        import re
        assert set(re.findall(r"78125\.\d+", page)) == {"78125.82", "78125.335", "78125.340"}
        assert "hash tables are complete" in page
        # 78125.82 has no database row; it says so, and links to the GAP page
        assert "not in the database" in page
        assert '/Groups/Abstract/78125.82"' in page
        # An order with a complete table and no group of this hash says so.
        self.check_args("/Groups/Abstract/hash/512/1", "no group of")
        # Orders without a complete table go on to the ordinary search page.
        r = self.tc.get("/Groups/Abstract/hash/2016/374703223365377769")
        assert r.status_code in (301, 302)
        assert "hash=2016%23374703223365377769" in r.headers["Location"]
        # A value too large to be a stored hash is refused, not queried.
        self.check_args("/Groups/Abstract/hash/512/99999999999999999999",
                        "No group has order")

    def test_hash_page_without_homepage(self):
        # A unique complete-table match with neither a database row nor a GAP
        # page is still displayed, rather than becoming an empty search.
        from lmfdb.groups.abstract import main as main_mod
        from lmfdb.groups.abstract.hash_lookup import HashResolution
        orig = main_mod.resolve_order_hash
        main_mod.resolve_order_hash = (
            lambda order, value: HashResolution(int(order), int(value), ["6561.999999"],
                                                True, "gps_smallhash"))
        try:
            page = self.tc.get("/Groups/Abstract/hash/6561/12345",
                               follow_redirects=True).get_data(as_text=True)
        finally:
            main_mod.resolve_order_hash = orig
        assert "6561.999999" in page and "not in the database" in page
        assert '/Groups/Abstract/6561.999999"' not in page, "linked a page that does not exist"

    def test_hash_search(self):
        # Complete-table orders search through gps_smallhash: the stored
        # gps_groups.hash of 512.11 is 11, not the hash being searched for.
        self.check_args(
            "/Groups/Abstract/?hash=512%231584677793794603025&search_type=List", "512.11")
        self.check_args("/Groups/Abstract/?order=512&hash=1584677793794603025&search_type=List",
                        "512.11")
        # Several hashes at one order resolve through the complete table too.
        self.check_args(
            "/Groups/Abstract/?order=512&hash=1584677793794603025%2C1718285292446712970"
            "&search_type=List", ["512.11", "512.10494213"])
        # Ordinary orders still search the gps_groups column; the optional hash
        # column renders the same value the links resolve.
        page = self.tc.get(
            "/Groups/Abstract/?hash=5120%234714647875464396655&search_type=List&showcol=hash",
            follow_redirects=True).get_data(as_text=True)
        for lab in ["5120.cs", "5120.cw", "5120.db", "5120.dc", "5120.df"]:
            assert lab in page, "%s not in hash search" % lab
        assert "4714647875464396655" in page

    def test_hash_search_false_positives(self):
        # A stored counter must not answer a search for a structural hash:
        # 512.11 has hash 1584677793794603025, and stores 11.
        self.not_check_args("/Groups/Abstract/?hash=11&search_type=List", "512.11")
        self.not_check_args("/Groups/Abstract/?order=500-600&hash=11&search_type=List", "512.11")
        # ... while a search for the real hash finds it, with no order given.
        self.check_args("/Groups/Abstract/?hash=1584677793794603025&search_type=List", "512.11")

    def test_hash_search_order_list(self):
        # A hash condition names orders of its own, so foiling it into an order
        # list would leave only one of the two conditions standing; the query
        # has to intersect them.
        from lmfdb import db
        from lmfdb.groups.abstract.main import group_parse
        query = {}
        group_parse({"order": "512,2016", "hash": "1584677793794603025"}, query)
        assert query == {"$and": [
            {"$or": [{"order": 512}, {"order": 2016}]},
            {"$or": [{"hash": 1584677793794603025,
                      "order": {"$nin": [512, 1152, 1536, 1920, 2187, 15625]}},
                     {"order": 512, "counter": {"$in": [11]}}]}]}
        # One order pins the search to the complete table, and a range still
        # constrains every branch without an intersection being needed.
        query = {}
        group_parse({"order": "512", "hash": "1584677793794603025"}, query)
        assert query == {"order": 512, "counter": {"$in": [11]}}
        query = {}
        group_parse({"order": "500-600", "hash": "11"}, query)
        assert query == {
            "order": {"$gte": 500, "$lte": 600},
            "$or": [{"hash": 11,
                     "order": {"$nin": [512, 1152, 1536, 1920, 2187, 15625]}}]}
        # The intersected query means what it says: the orders it names, and
        # the group whose structural hash was asked for.
        query = {}
        group_parse({"order": "512,2016", "hash": "1584677793794603025"}, query)
        assert list(db.gps_groups.search(query, "label", limit=20)) == ["512.11"]
        # 512.11 stores its counter 11 in the hash column, so a list of orders
        # that includes 512 must not answer a search for the hash 11 with it,
        # and a list that excludes 512 must not acquire an order-512 result
        # from the counters resolved for the hash it did ask for, ...
        self.not_check_args(
            "/Groups/Abstract/?order=512%2C2016&hash=11&search_type=List", "512.11")
        self.not_check_args(
            "/Groups/Abstract/?order=2016%2C5120&hash=1584677793794603025&search_type=List",
            "512.11")
        # ... while the list still finds the group whose hash was asked for.
        self.check_args(
            "/Groups/Abstract/?order=512%2C2016&hash=1584677793794603025&search_type=List",
            "512.11")

    def test_hash_search_order_conflict(self):
        # N#h names an order itself, and the hash page answers a search that
        # asks for one order and one hash: an order box that says something
        # else is the conflict parse_hashes rejects, not a search to redirect.
        for order in ["2016", "500-600"]:
            page = self.tc.get(
                "/Groups/Abstract/?order=%s&hash=512%%231584677793794603025"
                "&search_type=List" % order, follow_redirects=True).get_data(as_text=True)
            assert "512.11" not in page, "%s did not constrain the search" % order
            assert "You cannot specify order both in the" in page, \
                "%s and an embedded order gave no error" % order
        # A list of orders reaches the ordinary search rather than the hash
        # page, and there it means the orders it names.
        self.not_check_args(
            "/Groups/Abstract/?order=2016%2C5120&hash=512%231584677793794603025"
            "&search_type=List", "512.11")
        # The same order in both places is one order, and still redirects.
        r = self.tc.get("/Groups/Abstract/?order=512&hash=512%231584677793794603025"
                        "&search_type=List")
        assert r.status_code in (301, 302), "matching orders did not reach the hash page"
        assert "/hash/512/1584677793794603025" in r.headers["Location"]

    def test_hash_column(self):
        # The column shows the structural hash, never a label counter, and the
        # hash a search asked for when the row cannot supply it.
        from lmfdb.groups.abstract.main import group_columns
        col = [C for C in group_columns.columns if C.name == "hash"][0]
        assert col.display({"counter": 11, "hash": 11, "public_hash": None}) == ""
        assert col.display({"counter": 1, "hash": 374703223365377769,
                            "public_hash": None}) == "374703223365377769"
        assert col.display({"counter": 11, "hash": 11,
                            "public_hash": 1584677793794603025}) == "1584677793794603025"
        self.check_args("/Groups/Abstract/?order=2016&search_type=List&showcol=hash",
                        "374703223365377769")
        # An order and a hash on their own are answered by the hash page, so a
        # second condition is what keeps this one a table of results, where the
        # column supplies the hash that the order-512 row cannot.
        r = self.tc.get("/Groups/Abstract/?order=512&hash=1584677793794603025"
                        "&solvable=yes&search_type=List&showcol=hash")
        assert r.status_code == 200, "the search was answered by a redirect"
        page = r.get_data(as_text=True)
        assert "512.11" in page and "1584677793794603025" in page

    def test_hash_popup_links(self):
        # The subgroup and quotient popups link to the same complete cluster.
        import re
        from lmfdb.groups.abstract.main import group_data
        with self.app.test_request_context():
            sub = group_data("None", ambient="390625.a",
                             profiledata="78125.?$3521944227884464685$?")
            # a subgroup of order 78125 in an ambient of order 5^12: the
            # quotient has order 78125 too, so both links resolve the same set
            quo = group_data("None", ambient="6103515625.a",
                             profiledata="78125.?$None$?$None$3521944227884464685$?")
        for html in [sub, quo]:
            link = re.search(r'href="([^"]*/hash/78125/3521944227884464685)"', str(html))
            assert link, "popup did not link to the hash page: %s" % html
            page = self.tc.get(link.group(1), follow_redirects=True).get_data(as_text=True)
            assert set(re.findall(r"78125\.\d+", page)) == {"78125.82", "78125.335", "78125.340"}

    def test_identify_perm(self):
        # Permutation generators that GAP can identify redirect to the group homepage.
        r = self.tc.get("/Groups/Abstract/identify?description=(1,2,3),(1,2)")
        assert r.status_code in (301, 302) and "/Groups/Abstract/6.1" in r.headers["Location"]
        r = self.tc.get("/Groups/Abstract/identify?description=(1,2,3,4,5),(1,2)")
        assert r.status_code in (301, 302) and "/Groups/Abstract/120.34" in r.headers["Location"]
        # A non-identifiable order returns a candidate list (no redirect).
        r = self.tc.get("/Groups/Abstract/identify?description=2016PC3171906956164764984387211839562004878842403748156043542557808747")
        assert r.status_code == 200 and b"2016.i" in r.data

    def test_identify_complete_table(self):
        # GAP cannot identify order 512, but the complete hash table can: the
        # elementary abelian group of order 512 is the only one with its hash.
        perm = ",".join("(%s,%s)" % (2 * i + 1, 2 * i + 2) for i in range(9))
        r = self.tc.get("/Groups/Abstract/identify?description=" + perm)
        assert r.status_code in (301, 302), "identification did not redirect"
        assert "/Groups/Abstract/512.10494213" in r.headers["Location"]

    def test_identify_hash_link(self):
        # The "all groups with this order and hash" link resolves the same set
        # of groups that the identification listed.
        import re
        page = self.tc.get(
            "/Groups/Abstract/identify?description=2016PC317190695616476498438"
            "7211839562004878842403748156043542557808747",
            follow_redirects=True).get_data(as_text=True)
        listed = set(re.findall(r"2016\.[a-z]+", page))
        assert listed, "no candidates were listed"
        link = re.search(r'href="([^"]*/hash/2016/\d+)"', page)
        assert link, "no hash link on the identification page"
        results = self.tc.get(link.group(1).replace("&amp;", "&"),
                              follow_redirects=True).get_data(as_text=True)
        assert set(re.findall(r"2016\.[a-z]+", results)) == listed
        # At a complete-table order the link has to reach the whole cluster,
        # including the groups the identification listed as absent.
        from lmfdb.groups.abstract import main as main_mod
        cluster = [{"label": lab, "present": lab != "78125.82", "live": True}
                   for lab in ["78125.82", "78125.335", "78125.340"]]
        orig = main_mod.identify_group
        main_mod.identify_group = lambda desc: {
            "status": "list", "input": desc, "kind": "permutation", "order": 78125,
            "order_factored": "5^{7}", "hash": 3521944227884464685, "complete": True,
            "candidates": cluster, "caveat": "mocked complete cluster"}
        try:
            page = self.tc.get("/Groups/Abstract/identify?description=mock",
                               follow_redirects=True).get_data(as_text=True)
        finally:
            main_mod.identify_group = orig
        link = re.search(r'href="([^"]*/hash/78125/3521944227884464685)"', page)
        assert link, "no hash link on the identification page"
        results = self.tc.get(link.group(1), follow_redirects=True).get_data(as_text=True)
        assert set(re.findall(r"78125\.\d+", results)) == {c["label"] for c in cluster}

    def test_identify_missing_smallhash(self):
        # A hash computed from a group of a complete-table order has to be in
        # that table: an empty answer is a data problem, and says so.
        from lmfdb.groups.abstract import identify as identify_mod
        from lmfdb.groups.abstract.hash_lookup import HashResolution
        perm = ",".join("(%s,%s)" % (2 * i + 1, 2 * i + 2) for i in range(9))
        orig = identify_mod.resolve_order_hash
        identify_mod.resolve_order_hash = (
            lambda order, value: HashResolution(int(order), int(value), [], True, "gps_smallhash"))
        try:
            page = self.tc.get("/Groups/Abstract/identify?description=" + perm,
                               follow_redirects=True).get_data(as_text=True)
        finally:
            identify_mod.resolve_order_hash = orig
        assert "did not contain the computed hash" in page

    def test_identify_errors(self):
        # Garbage input returns a clean page (no 500) with an error message.
        r = self.tc.get("/Groups/Abstract/identify?description=garbage")
        assert r.status_code == 200 and b"Unrecognized description" in r.data
        # Oversized permutation degree is rejected before any GAP computation.
        self.check_args("/Groups/Abstract/identify?description=(513,1)",
                        "Permutation degree must be at most 512")

    def test_identify_guards(self):
        # Parsing, construction and the order computation are inside the alarm,
        # and the order cap is checked before anything scales with the order.
        from cysignals.alarm import AlarmInterrupt
        from sage.all import ZZ
        from lmfdb.groups.abstract import identify as identify_mod

        class FakeGroup():
            def __init__(self, order):
                self._order = order

            def Order(self):
                return self._order

        def raises(err):
            def parse(desc):
                raise err
            return parse

        cancels = []
        factored = []
        orig = (identify_mod._parse, identify_mod.latex, identify_mod.cancel_alarm)
        identify_mod.latex = lambda x: factored.append(x) or "spy"

        def spy_cancel():
            cancels.append(1)
            orig[2]()
        identify_mod.cancel_alarm = spy_cancel
        try:
            # over the cap: no factorization, and the alarm is cancelled
            identify_mod._parse = lambda desc: (FakeGroup(ZZ(10) ** 7), "permutation")
            res = identify_mod.identify_group("(1,2)")
            assert res["status"] == "error" and "exceeds the supported bound" in res["error"]
            assert not factored, "the order was factored before the cap was checked"
            assert len(cancels) == 1, "the alarm was not cancelled on the over-cap path"
            # a timeout while parsing is reported, not raised
            identify_mod._parse = raises(AlarmInterrupt())
            res = identify_mod.identify_group("(1,2)")
            assert res["status"] == "error" and "Timed out" in res["error"]
            assert len(cancels) == 2
            # so is a GAP or Sage failure inside a parser
            identify_mod._parse = raises(RuntimeError("gap fell over"))
            res = identify_mod.identify_group("(1,2)")
            assert res["status"] == "error" and "gap fell over" in res["error"]
            assert len(cancels) == 3
            # a bad description still short-circuits, with the alarm cancelled
            identify_mod._parse = orig[0]
            res = identify_mod.identify_group("garbage")
            assert res["status"] == "error" and "Unrecognized description" in res["error"]
            assert len(cancels) == 4
            # and the whole thing is a 200 page rather than a 500
            identify_mod._parse = raises(RuntimeError("gap fell over"))
            r = self.tc.get("/Groups/Abstract/identify?description=(1,2)")
            assert r.status_code == 200 and b"gap fell over" in r.data
            # the success path cancels both alarms
            del cancels[:]
            identify_mod._parse, identify_mod.latex = orig[0], orig[1]
            res = identify_mod.identify_group("(1,2,3),(1,2)")
            assert res["status"] == "redirect" and res["label"] == "6.1"
            assert len(cancels) == 2, "the success path left an alarm running"
        finally:
            identify_mod._parse, identify_mod.latex, identify_mod.cancel_alarm = orig

    def test_identify_matrix_entries(self):
        # Over GF(p^e) an entry is an integer code, not a prime-field element:
        # 2 is the generator of GF(4), so this is a nonzero 1x1 matrix.
        r = self.tc.get("/Groups/Abstract/identify?description=Mat(1,4):[[2]]")
        assert r.status_code in (301, 302), "Mat(1,4):[[2]] was not identified"
        assert "/Groups/Abstract/3.1" in r.headers["Location"]
        # the generator of GF(9) has multiplicative order 8
        r = self.tc.get("/Groups/Abstract/identify?description=Mat(1,9):[[3]]")
        assert "/Groups/Abstract/8.1" in r.headers["Location"]
        # prime fields and Z/n are unchanged
        r = self.tc.get("/Groups/Abstract/identify?description=Mat(2,3):[[1,1],[0,1]],[[0,1],[1,0]]")
        assert "/Groups/Abstract/48.29" in r.headers["Location"]
        r = self.tc.get("/Groups/Abstract/identify?description=Mat(1,6):[[5]]")
        assert "/Groups/Abstract/2.1" in r.headers["Location"]
        # out of range codes (including negative ones) are refused
        for desc in ["Mat(1,4):[[4]]", "Mat(1,4):[[-1]]"]:
            self.check_args("/Groups/Abstract/identify?description=" + desc,
                            "must be an integer code")

    def test_matrix_entry_codes(self):
        # The codes cover GF(q) and follow the FiniteGroups DecodeMat basis.
        from sage.libs.gap.libgap import libgap
        from lmfdb.groups.abstract.identify import entry_ring
        for q, p, k in [(4, 2, 2), (8, 2, 3), (9, 3, 2)]:
            R, decode = entry_ring(q)
            values = [decode(x) for x in range(q)]
            assert len(set(values)) == q, "codes over GF(%s) collapse" % q
            assert decode(p) != 0, "the field generator decoded to zero"
            basis = libgap.Basis(libgap.GF(q))
            zero = libgap.Zero(libgap.GF(q))
            for x in range(q):
                digits = [(x // p ** m) % p for m in range(k)]
                expected = sum((basis[m] * digits[m] for m in range(k)), zero)
                assert libgap(decode(x)) == expected, "code %s over GF(%s)" % (x, q)

    def test_magma_identifiable(self):
        # Lock the pipeline-era CanIdentifyGroup boundary (see identify.py docstring).
        from lmfdb.groups.abstract.identify import magma_identifiable
        expected = {512: False, 1024: False, 1152: False, 1536: False, 1920: False,
                    2005: True, 2016: False, 2028: False, 2044: True, 2662: True,
                    3125: True, 5050: True, 16807: False, 29282: False, 44100: False}
        for n, e in expected.items():
            assert magma_identifiable(n) == e, "magma_identifiable(%s) should be %s" % (n, e)
