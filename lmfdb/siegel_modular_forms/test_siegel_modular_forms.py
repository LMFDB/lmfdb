"""
Tests for the rewritten Siegel modular forms pages (smf_* tables).

The data on devmirror is provisional and only partially loaded, so tests
that depend on database content use runtime skip guards rather than
failing when a table or label has not been loaded yet.
"""

import re

from lmfdb.tests import LmfdbTest
from lmfdb import db


class SmfTest(LmfdbTest):
    def check(self, url, text):
        data = self.tc.get("/ModularForm/GSp/Q/" + url, follow_redirects=True).get_data(as_text=True)
        # Match against both the raw page (for links) and a tag-stripped
        # version (for text that is interrupted by knowl links or line breaks)
        html = re.sub(r"\s+", " ", data)
        stripped = re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", data))
        if not isinstance(text, list):
            text = [text]
        for t in text:
            t = re.sub(r"\s+", " ", t)
            assert t in html or t in stripped, (
                "expected string '%s' not found in page /ModularForm/GSp/Q/%s"
                % (t, url)
            )
        return data

    def need_forms(self, label=None):
        if not db.smf_newforms.count():
            self.skipTest("smf_newforms not yet loaded on devmirror")
        if label is not None and not db.smf_newforms.label_exists(label):
            self.skipTest("%s not in smf_newforms on devmirror" % label)

    def need_spaces(self, label=None):
        if not db.smf_newspaces.count():
            self.skipTest("smf_newspaces not yet loaded on devmirror")
        if label is not None and not db.smf_newspaces.label_exists(label):
            self.skipTest("%s not in smf_newspaces on devmirror" % label)

    def test_browse_page(self):
        r"""
        Check the top-level browse page for Siegel modular forms
        """
        self.need_forms()
        self.check("", [
            "Siegel modular forms",
            "The database currently contains",
            "Browse newforms",
            "Browse newspaces",
            "By weight",
            "By level",
            "Some interesting newforms",
            "random newform",
            "paramodular",
            "/ModularForm/GSp/Q/stats",
            "provisional",
        ])

    def test_random_page(self):
        """
        Test 3 random newform pages
        """
        self.need_forms()
        for _ in range(3):
            self.check("random/", ["Newform orbit", "Newspace parameters", "Automorphic type"])

    def test_random_space(self):
        """
        Test a random newspace page
        """
        self.need_spaces()
        self.check("random_space/", "Space of Siegel modular forms")

    def test_newform_pages(self):
        """
        Test some specific newform pages, including scalar and vector-valued
        weights, all three families, and dimension larger than 1
        """
        # Siegel family (Sp(4,Z)), scalar weight 12
        self.need_forms("2.S.1.12.0.a.a")
        self.check("2/S/1/12.0/a/a/", [
            "Newform orbit 2.S.1.12.0.a.a",
            "Newspace parameters",
            "Newform invariants",
            "(12, 0)",
        ])
        # principal family, vector-valued weight (2,12), Yoshida lift
        self.need_forms("2.P.2.2.12.a.a")
        self.check("2/P/2/2.12/a/a/", [
            "Newform orbit 2.P.2.2.12.a.a",
            "principal",
            "(2, 12)",
            "Automorphic type",
            "Dirichlet series",
            "53460",  # coefficient of 5^{-s} in the spin L-series
        ])
        # paramodular family
        self.need_forms("2.K.568.3.0.a.c")
        self.check("2/K/568/3.0/a/c/", [
            "Newform orbit 2.K.568.3.0.a.c",
            "paramodular",
            "568 = 2^{3} \\cdot 71",
            "General type (G)",
        ])
        # dimension 2 form
        self.need_forms("2.K.1.4.20.a.a")
        self.check("2/K/1/4.20/a/a/", ["Newform orbit 2.K.1.4.20.a.a", "Dimension"])
        # vector-valued Siegel family form
        self.need_forms("2.S.1.4.8.a.a")
        self.check("2/S/1/4.8/a/a/", "Newform orbit 2.S.1.4.8.a.a")

    def test_space_pages(self):
        """
        Test newspace pages, including the dimension and decomposition tables
        """
        self.need_spaces("2.K.568.3.0.a")
        self.check("2/K/568/3.0/a/", [
            "Space of Siegel modular forms of level 568 and weight (3, 0)",
            "Defining parameters",
            "Cusp forms",
            "Saito-Kurokawa lifts (P)",
            "General type (G)",
            "Atkin-Lehner",
            "newform subspaces",
            "2.K.568.3.0.a.a",
        ])
        self.need_spaces("2.S.1.12.0.a")
        self.check("2/S/1/12.0/a/", [
            "Space of Siegel modular forms of level 1 and weight (12, 0)",
            "M_{12,0}",
        ])

    def test_dimension_tables(self):
        """
        Test the dimension tables for newforms and for spaces
        """
        self.need_forms()
        self.need_spaces()
        self.check("?search_type=Dimensions&degree=2&family=K", [
            "Dimension search results",
            "The dimensions shown below are for the space of newforms",
            "n/a",
        ])
        self.check("?search_type=Dimensions&degree=2&family=K&weight=3&level=1-24", [
            "Dimension search results",
            "(3, 0)",
        ])
        self.check("?search_type=SpaceDimensions&degree=2&family=K", [
            "Dimension search results",
            "The dimensions shown are for spaces of modular forms",
            "All modular forms",
            "New cusp forms",
            "Old Eisenstein series",
        ])

    def test_newform_search(self):
        """
        Test the newform search results
        """
        self.need_forms("2.K.568.3.0.a.c")
        self.check("?search_type=List&family=K&weight=3&level=568", [
            "Siegel newform search results",
            "Results (",
            "2.K.568.3.0.a.c",
        ])
        self.check("2/", ["Siegel newform search results", "Results ("])
        self.check("2/K/", ["Siegel newform search results", "Results ("])

    def test_space_search(self):
        """
        Test the newspace search results
        """
        self.need_spaces()
        self.check("?search_type=Spaces&degree=2&family=K&level=1-100", [
            "Newspace search results",
            "Results (",
            "2.K.",
        ])

    def test_trace_search(self):
        """
        Test the trace search results
        """
        self.need_forms()
        self.check("?search_type=Traces&degree=2&family=K&level=1-20", [
            "search results",
            "Results (",
        ])

    def test_stats(self):
        """
        Test the statistics page
        """
        self.need_forms()
        self.check("stats", [
            "Siegel modular forms: Statistics",
            "Distribution of levels and absolute dimension",
            "newforms",
        ])

    def test_dynamic_stats(self):
        """
        Test the dynamic statistics page
        """
        self.need_forms()
        self.check(
            "dynamic_stats?col1=level&buckets1=1-100%2C101-999&proportions=recurse"
            "&col2=dim&buckets2=1-4%2C5-1000&search_type=DynStats",
            "Dynamic statistics",
        )

    def test_jump(self):
        """
        Test the jump box, including error messages
        """
        self.need_forms("2.S.1.12.0.a.a")
        self.check("?jump=2.S.1.12.0.a.a", "Newform orbit 2.S.1.12.0.a.a")
        self.check("?jump=2.K.568.3.0.a", "Space of Siegel modular forms of level 568")
        self.check("?jump=maria", "is not a valid newform or space label")

    def test_not_found(self):
        """
        Check that missing labels and invalid families give proper errors
        """
        self.check("?jump=2.K.9999.3.0.a.z", "Newform 2.K.9999.3.0.a.z not found")
        self.check("2/K/9999/3.0/a/", "Space 2.K.9999.3.0.a not found")
        page = self.tc.get("/ModularForm/GSp/Q/2/X/", follow_redirects=True)
        assert page.status_code == 404

    def test_downloads(self):
        """
        Test the download links that appear on newform and newspace pages
        """
        self.need_forms("2.P.2.2.12.a.a")
        self.check("download_traces/2.P.2.2.12.a.a", "[0, 1, 0, -600, -4, -53460")
        self.check("download_newform/2.P.2.2.12.a.a", [
            "Stored data for newform 2.P.2.2.12.a.a",
            '"analytic_rank_proved"',
        ])
        self.need_spaces("2.K.568.3.0.a")
        self.check("download_newspace/2.K.568.3.0.a", [
            "Stored data for newspace 2.K.568.3.0.a",
            '"ALdims"',
        ])

    def test_underlying_data(self):
        """
        Test the underlying data pages
        """
        self.need_forms("2.P.2.2.12.a.a")
        self.check("data/2.P.2.2.12.a.a", [
            "Newform data - 2.P.2.2.12.a.a",
            "smf_newforms",
            "smf_hecke_nf",
        ])
        self.need_spaces("2.K.568.3.0.a")
        self.check("data/2.K.568.3.0.a", [
            "Newspace data - 2.K.568.3.0.a",
            "smf_newspaces",
        ])

    def test_interesting(self):
        """
        Test the interesting newforms and newspaces pages
        """
        self.check("interesting_newforms", "Some interesting newforms")
        self.check("interesting_spaces", "Some interesting newspaces")

    def test_sidebar(self):
        """
        Test the learn-more pages
        """
        self.check("Completeness", "Completeness of Siegel modular form data")
        self.check("Source", "Source of Siegel modular form data")
        self.check("Reliability", "Reliability of Siegel modular form data")
        self.check("Labels", "Labels for Siegel modular forms")
