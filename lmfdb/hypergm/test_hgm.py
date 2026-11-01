import re
from html import unescape
from urllib.parse import unquote

from lmfdb.tests import LmfdbTest

# The Hodge polygon heading followed by its plot.  Both pages carry other base64
# plots, so the two have to be matched together rather than separately.
HODGE_POLYGON_RE = re.compile(r'Hodge polygon\s*(?:</a>)?\s*</h2>\s*<img src="data:image/png;base64,')
# The Download link rendered by templates/download_search_results.html
DOWNLOAD_LINK_RE = re.compile(r'href="([^"]*download=1[^"]*)"')
# The "search families instead" link flashed by hgm_postprocess
FAMILY_HINT_RE = re.compile(r'no motives in the database match this search.*?href="([^"]*)"', re.S)


class HGMTest(LmfdbTest):
    # TODO: create stats page
    # def test_stats(self):
    #     self.check_args("Hypergeometric/Q/stats", "Monodromy")

    # test pages

    # family pages

    def test_random_family(self):
        self.check_args("/Motive/Hypergeometric/Q/random_family", ["Hypergeometric motive family", "Defining parameters"])

    def test_by_family_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1", ["[4, 4]", "[1, 1, 1, 1]", "[-2, -2, -1, -1, -1, -1, 4, 4]"]) # As, Bs, gamma

    def test_type(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", "Orthogonal")

    def test_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/A10.6.3.2_B14.1.1.1", "[1, 2, 3, 2, 1]")

    def test_bezout_det(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.4.3_B10.2.2.2.2.2.2", "-191102976")

    def test_p_part(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.12_B8.3.2.1.1.1", ["[4, 4, 2, 2, 2, 2, 2]", "[8, 1, 1, 1, 1, 1]", "[9, 3]"])

    def test_monodromy(self):
        self.check_args("/Motive/Hypergeometric/Q/A18.3.3_B6.4.4.4.1.1", "S_{9}")
        self.check_args("/Motive/Hypergeometric/Q/A12.6.6_B5.1.1.1.1", "operatorname{Sp}(8,3)")

    def test_good_euler(self):
        self.check_args("/Motive/Hypergeometric/Q/A6.4.4.3_B12.2.2.2.1", "1 + 6 T - 45 p T^{2} - 2130 p^{2} T^{3} + 268 p^{4} T^{4} - 2130 p^{6} T^{5} - 45 p^{9} T^{6} + 6 p^{12} T^{7} + p^{16} T^{8}")

    ### motive pages

    def test_random_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/random_motive", "Local information")
        self.not_check_args("/Motive/Hypergeometric/Q/random_motive", "Hypergeometric motive family")

    def test_by_motive_label(self):
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8", ["[2, 2, 2]", "[4, 1]", "[-4, -1, -1, -1, -1, 2, 2, 2, 2]"]) # As, Bs, gamma

    def test_type_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B1.1.1.1/t-8.1", "Symplectic")

    def test_signature(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.4_B2.2.2.1/t4.1", "-2")

    def test_conductor(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t2.1", "8192")

    def test_local_information(self):
        self.check_args("/Motive/Hypergeometric/Q/A4.2.2_B1.1.1.1/t1.9", ["3737281794192", "8013465013431125"])

    ### searches

    ### family searches

    def test_search_degree(self):
        self.check_args("/Motive/Hypergeometric/Q/?degree=4&search_type=Family", ["A5_B3.2.1","A10_B4.2.1"])
        self.not_check_args("/Motive/Hypergeometric/Q/?degree=4&search_type=Family", "A2_B1")

    def test_search_weight(self):
        self.check_args("/Motive/Hypergeometric/Q/?weight=3&search_type=Family", "A5_B6.6")
        self.not_check_args("/Motive/Hypergeometric/Q/?weight=3&search_type=Family", "A3_B4")

    def test_search_family_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C1%2C1%2C1]&search_type=Family", "A5_B6.6")
        self.not_check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C1%2C1%2C1]&search_type=Family", "A15_B8.1.1.1.1")

    def test_search_famhodge_bare(self):
        # issue #3406: the family Hodge vector is a family-level invariant, so a
        # bare famhodge query (no search_type) should return matching families
        # rather than zero motives.
        self.check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]", "A7.2_B5.3.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]", "search families instead")

    def test_search_famhodge_bare_download(self):
        # The Download link on the bare famhodge results page must return the same
        # family dataset the page displays.  SearchWrapper dispatches the download
        # shortcut before hgm_search runs, so the search type has to be settled at
        # the route entry point; otherwise the download runs the family query
        # against hgm_motives and comes back empty.
        page = self.tc.get("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]").get_data(as_text=True)
        link = DOWNLOAD_LINK_RE.search(page)
        assert link is not None, "no download link on the search results page"
        response = self.tc.get(unescape(link.group(1)))
        self.assertEqual(response.status_code, 200)
        text = response.get_data(as_text=True)
        self.assertIn("A7.2_B5.3.1", text)
        self.assertNotIn("returned 0", text)
        # family labels, not motive labels
        assert re.search(r"A[\d.]+_B[\d.]+_t", text) is None, "motive labels in a family download"

    def test_search_famhodge_motive_hint(self):
        # An explicit motive search on a family Hodge vector with no matching
        # motives points the user at the family search instead.
        self.check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]&search_type=Motive",
                        ["search families instead", "matching famil"])

    def test_search_famhodge_hint_incompatible(self):
        # The count and the link cover every family-compatible constraint, so a
        # search that no family satisfies gets no hint at all.
        self.not_check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]&degree=999&search_type=Motive",
                            "search families instead")

    def test_search_famhodge_hint_keeps_constraints(self):
        # The family link is the same search with only the object type changed.
        page = self.tc.get("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]&A=[7%2C2]&search_type=Motive").get_data(as_text=True)
        hint = FAMILY_HINT_RE.search(page)
        assert hint is not None, "no family hint on a motive search with matching families"
        link = unescape(hint.group(1))
        self.assertIn("search_type=Family", link)
        self.assertIn("A=[7,2]", unquote(link))
        families = self.tc.get(link, follow_redirects=True).get_data(as_text=True)
        self.assertIn("A7.2_B5.3.1", families)
        # not broadened back to every family with this Hodge vector
        self.assertNotIn("A10.3.2_B7.1", families)

    def test_search_famhodge_hint_singular(self):
        self.check_args("/Motive/Hypergeometric/Q/?famhodge=[1%2C5%2C1]&A=[7%2C2]&B=[5%2C3%2C1]&search_type=Motive",
                        "1 matching family exists")

    def test_search_A(self):
        self.check_args("/Motive/Hypergeometric/Q/?A=[3%2C2%2C2]&search_type=Family", "A3.2.2_B5")
        self.not_check_args("/Motive/Hypergeometric/Q/?A=[3%2C2%2C2]&search_type=Family", "A3.2_B1.1.1")

    def test_search_B(self):
        self.check_args("/Motive/Hypergeometric/Q/?B=[6%2C4]&search_type=Family", "A5_B6.4")
        self.not_check_args("/Motive/Hypergeometric/Q/?B=[6%2C4]&search_type=Family", "A3.2_B1.1.1")

    def test_search_Ap(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=3&Ap=[9]&search_type=Family", "A9_B5.2.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=3&Ap=[9]&search_type=Family", "A2_B1")

    def test_search_Bp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=3&Bp=[1%2C1%2C1%2C1%2C1%2C1]&search_type=Family", "A9_B5.2.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=3&Bp=[1%2C1%2C1%2C1%2C1%2C1]&search_type=Family", "A3_B1.1")

    def test_search_Ap_perp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=5&Apperp=[2%2C2%2C1%2C1]&search_type=Family", "A8_B2.2.1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=5&Apperp=[2%2C2%2C1%2C1]&search_type=Family", "A5_B1.1.1.1")

    def test_search_Bp_perp(self):
        self.check_args("/Motive/Hypergeometric/Q/?p=7&Bpperp=[4%2C2%2C1%2C1%2C1]&search_type=Family", "A9_B4.2.1.1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?p=7&Bpperp=[4%2C2%2C1%2C1%2C1]&search_type=Family", "A2.2.2.2.2.2_B14")

    ### motive searches

    def test_search_conductor(self):
        self.check_args("/Motive/Hypergeometric/Q/?conductor=32&search_type=Motive", "A4_B2.1_t-8.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?conductor=32&search_type=Motive", "A2.2_B1.1_t-8.1")

    def test_search_hodge_vector(self):
        self.check_args("/Motive/Hypergeometric/Q/?hodge=[1%2C1%2C1%2C1]&search_type=Motive", "A8_B1.1.1.1_t-1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?hodge=[1%2C1%2C1%2C1]&search_type=Motive", "A8_B4.1.1_t-1.1")

    def test_search_specialization(self):
        self.check_args("/Motive/Hypergeometric/Q/?t=3%2F2&search_type=Motive", "A4_B2.1_t3.2")
        self.not_check_args("/Motive/Hypergeometric/Q/?t=3%2F2&search_type=Motive", "A4_B2.1_t-8.1")

    def test_search_root_number(self):
        self.check_args("/Motive/Hypergeometric/Q/?sign=-1&search_type=Motive", "A4_B1.1_t-1.1")
        self.not_check_args("/Motive/Hypergeometric/Q/?sign=-1&search_type=Motive", "A4_B2.1_t-1.1")

    ### downloads

    ### friends

    ### for families

    def test_friends_family(self):
        self.check_args("/Motive/Hypergeometric/Q/A12.6.6.6_B3.2.2.2.2.2.2.1.1", "Motives in the family")

    ### for motives

    def test_friends_motive(self):
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1", "Motive family A2.2.2 B4.1") # containing family
        self.check_args("/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1", "/L/Motive/Hypergeometric/Q/A2.2.2_B4.1/t2.1") # L-function

    ### Hodge polygon (issue #3406)

    def test_hodge_polygon(self):
        # The Hodge polygon plot is shown on family and motive pages of positive weight.
        for path in ["/Motive/Hypergeometric/Q/A10.6.3.2_B14.1.1.1",
                     "/Motive/Hypergeometric/Q/A2.2.2_B4.1/t9.8"]:
            page = self.tc.get(path, follow_redirects=True).get_data(as_text=True)
            assert HODGE_POLYGON_RE.search(page) is not None, "no Hodge polygon plot on %s" % path

    def test_no_hodge_polygon_weight_zero(self):
        # The polygon of a weight 0 object is flat, so it is deliberately omitted.
        self.not_check_args("/Motive/Hypergeometric/Q/A10.2_B5.1", "Hodge polygon")
        self.not_check_args("/Motive/Hypergeometric/Q/A4_B2.1/t-8.1", "Hodge polygon")

    ### malformed labels (issue #3406)

    def test_bad_labels(self):
        # Malformed labels should return a clean 404, not a 500 or a redirect-with-flash.
        self.assertEqual(self.tc.get("/Motive/Hypergeometric/Q/banana").status_code, 404)
        self.assertEqual(self.tc.get("/Motive/Hypergeometric/Q/A2.2_B1.1/tbanana").status_code, 404)
        self.assertEqual(self.tc.get("/Motive/Hypergeometric/Q/data/banana").status_code, 404)
        for kind in ["circle", "linear", "constant"]:
            self.assertEqual(self.tc.get("/Motive/Hypergeometric/Q/plot/%s/banana" % kind).status_code, 404)

    def test_full_label_redirect(self):
        # A full motive label pasted as a single path segment redirects to the motive page.
        self.assertEqual(self.tc.get("/Motive/Hypergeometric/Q/A2.2_B1.1_t1.2").status_code, 301)
        self.check_args("/Motive/Hypergeometric/Q/A2.2_B1.1_t1.2", "Hypergeometric motive")

    def test_jump_malformed(self):
        # A malformed jump input flashes an error rather than raising.
        self.check_args("/Motive/Hypergeometric/Q/?jump=A2_B1_t1x2", "not a valid")
