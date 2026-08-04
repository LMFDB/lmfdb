# -*- coding: utf-8 -*-

from urllib.parse import quote

from lmfdb.tests import LmfdbTest

# These are checked against the database in the tests below
STAR_NAME = "X^*(6;1)"  # canonical spelling of the starred curve name
STAR_LABEL = "6.1.1.1.0.a.1"
PLAIN_NAME = "X(6;1)"
PLAIN_LABEL = "6.1.1.4.0.a.1"


class ShimCrvTest(LmfdbTest):
    def jump(self, entry):
        return self.tc.get(
            "/ShimuraCurve/Q/?jump=%s" % quote(entry, safe=""),
            follow_redirects=True,
        )

    def test_home(self):
        L = self.tc.get('/ShimuraCurve/Q/')
        assert 'Shimura curves' in L.get_data(as_text=True)
        assert 'Browse' in L.get_data(as_text=True)
        assert 'Search' in L.get_data(as_text=True)
        assert 'Find' in L.get_data(as_text=True)
        assert 'X(D;N)' in L.get_data(as_text=True)

    def test_jump_label(self):
        # Jumping to an LMFDB label goes directly to the curve page
        rec = self.db.gps_shimura_test.lookup(STAR_LABEL, ["name", "label"])
        assert rec["name"] == STAR_NAME
        L = self.jump(STAR_LABEL)
        assert L.status_code == 200
        page = L.get_data(as_text=True)
        assert STAR_LABEL in page
        assert STAR_NAME in page

    def test_jump_plain_name(self):
        # An unstarred standard name, in both X(D;N) and X(D,N) spellings
        assert self.db.gps_shimura_test.lucky({"name": PLAIN_NAME}, "label") == PLAIN_LABEL
        for entry in [PLAIN_NAME, "X(6,1)"]:
            L = self.jump(entry)
            assert L.status_code == 200
            page = L.get_data(as_text=True)
            assert PLAIN_LABEL in page
            assert PLAIN_NAME in page

    def test_jump_starred_name(self):
        # Starred names contain an asterisk, which must not be treated as a
        # fiber product separator; both X*(D;N) and the canonical X^*(D;N)
        # spelling are accepted (as well as a lowercase x)
        assert self.db.gps_shimura_test.lucky({"name": STAR_NAME}, "label") == STAR_LABEL
        for entry in ["X*(6;1)", "X^*(6;1)", "x*(6;1)"]:
            L = self.jump(entry)
            assert L.status_code == 200
            page = L.get_data(as_text=True)
            assert STAR_LABEL in page, entry
            assert STAR_NAME in page, entry

    def test_jump_fiber_product(self):
        # X^*(6;1) has index 1 (its group is the full ambient group), so the
        # fiber product of X(6;1) with it is X(6;1) itself; this can be
        # entered with names (including starred ones) or labels
        for entry in [
                "X(6;1)*X^*(6;1)",
                "X*(6;1)*X(6;1)",
                "%s*%s" % (PLAIN_LABEL, STAR_LABEL),
        ]:
            L = self.jump(entry)
            assert L.status_code == 200
            page = L.get_data(as_text=True)
            assert PLAIN_LABEL in page, entry
            assert PLAIN_NAME in page, entry
        # A fiber product not isomorphic to any curve in the database
        # produces a clean error message
        assert self.db.gps_shimura_test.lucky({"name": "X(10;1)"}, "label") is not None
        L = self.jump("X(6;1)*X(10;1)")
        assert L.status_code == 200
        assert "There is no Shimura curve in the database isomorphic to the fiber product" in L.get_data(as_text=True)
        # Repeated factors are rejected with a clean error message
        L = self.jump("X(6;1)*X(6;1)")
        assert L.status_code == 200
        assert "Fiber product decompositions cannot contain repeated terms" in L.get_data(as_text=True)

    def test_jump_malformed(self):
        # Malformed input (including malformed starred names) should flash an
        # error, not produce a 500
        for entry in ["X*(6;", "X^*(6;", "X*(6;1", "banana", "X(6;1)*banana"]:
            L = self.jump(entry)
            assert L.status_code == 200, entry
            assert "There is no Shimura curve in the database" in L.get_data(as_text=True), entry
        # A syntactically valid starred name that is not in the database
        L = self.jump("X*(10;1)")
        assert L.status_code == 200
        assert "There is no Shimura curve in the database with name" in L.get_data(as_text=True)

    def test_search(self):
        # All discB = 6, level 1 curves should show up in a search
        expected = sorted(rec["label"] for rec in self.db.gps_shimura_test.search(
            {"discB": 6, "level": 1}, ["label"]))
        assert PLAIN_LABEL in expected and STAR_LABEL in expected
        L = self.tc.get("/ShimuraCurve/Q/?discB=6&level=1")
        assert L.status_code == 200
        page = L.get_data(as_text=True)
        for label in expected:
            assert label in page
        # names are displayed (in LaTeX form) in the search results
        assert STAR_NAME in page
        assert PLAIN_NAME in page

    def test_search_family(self):
        # Searching for the starred family X^*(D;N) should find the starred curve
        starred = sorted(rec["label"] for rec in self.db.gps_shimura_test.search(
            {"name": {"$like": "X^*(%"}}, ["label"]))
        assert STAR_LABEL in starred
        L = self.tc.get("/ShimuraCurve/Q/?family=XDNstar")
        assert L.status_code == 200
        page = L.get_data(as_text=True)
        for label in starred:
            assert label in page

    def test_curve_page(self):
        # Check content of individual curve pages against the database
        for label in [PLAIN_LABEL, STAR_LABEL]:
            rec = self.db.gps_shimura_test.lookup(
                label, ["name", "genus", "index", "discB", "level"])
            L = self.tc.get("/ShimuraCurve/Q/%s/" % label)
            assert L.status_code == 200
            page = L.get_data(as_text=True)
            assert "Shimura curve $%s$" % rec["name"] in page
            assert label in page
            # invariants from the database: genus (as displayed by show_genus),
            # index and discriminant
            assert "$ %s " % rec["genus"] in page
            assert "$%s$" % rec["index"] in page
            assert "Discriminant of $B$" in page
            assert "$%s$" % rec["discB"] in page
