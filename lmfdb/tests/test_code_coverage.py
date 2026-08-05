from lmfdb.tests import LmfdbTest


class CodeCoverageTest(LmfdbTest):

    def test_page_loads(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "Code snippet coverage" in page

    def test_table_header(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        for cas in ["SageMath", "Pari/GP", "Magma"]:
            assert cas in page, f"{cas} not in code coverage page"

    def test_modules_present(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "Elliptic curves" in page
        assert "Number fields" in page
        assert "Genus2 curves" in page

    def test_classical_modular_forms_variants(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "Classical modular forms (form)" in page
        assert "Classical modular forms (space)" in page

    def test_coverage_cells(self):
        """Check that coverage cells contain X/Y patterns"""
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        import re
        matches = re.findall(r'\d+/\d+', page)
        assert len(matches) > 10, "Expected many X/Y coverage cells"

    def test_total_row(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "<td style=\"text-align:left\">Total</td>" in page

    def test_color_classes(self):
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "cov-full" in page or "cov-partial" in page or "cov-low" in page

    def test_oscar_and_gap(self):
        """Oscar and Gap should appear since some yaml files define them"""
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "Oscar" in page
        assert "Gap" in page

    def test_dash_for_missing_cas(self):
        """Modules without a CAS should show a dash"""
        page = self.tc.get("/CodeCoverage").get_data(as_text=True)
        assert "cov-none" in page
