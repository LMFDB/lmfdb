
import inspect
import io
import json
import os
import re
import tempfile
from contextlib import redirect_stdout

from lmfdb.tests import LmfdbTest
from lmfdb.cmdline_search import main, parse_lmfdb_url, build_parser, section_lookup, SECTIONS


class CmdlineSearchTest(LmfdbTest):
    """Tests for the command-line search interface (lmfdb/cmdline_search.py,
    invoked on the command line via the ``lmfdb_search`` script)."""

    def run_cmd(self, argv):
        """Run the command-line interface, returning everything written to stdout."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            main(argv)
        return buf.getvalue()

    def raw_rows(self, out):
        """Parse the data rows out of ``raw`` format output (skipping the two
        header lines and the blank separator line)."""
        lines = out.split("\n")
        # header (columns), header (types), blank line, then data
        assert lines[2] == "", "Expected blank line after raw headers"
        return [line for line in lines[3:] if line]

    # ------------------------------------------------------------------
    # raw format
    # ------------------------------------------------------------------

    def test_raw_section_url_query(self):
        # URL-style query string against a section
        out = self.run_cmd(["NumberField", "degree=4", "--limit", "3"])
        header = out.split("\n")[0].split("|")
        self.assertIn("label", header)
        self.assertIn("degree", header)
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 3)
        # The degree column should be 4 for every row
        degree_idx = header.index("degree")
        for row in rows:
            self.assertEqual(row.split("|")[degree_idx], "4")

    def test_raw_table_json_query(self):
        # json query directly against a raw table
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--limit", "5"])
        self.assertEqual(out.split("\n")[0], "label|degree")
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertEqual(row.split("|")[1], "4")

    def test_raw_empty_query(self):
        # No query returns everything (subject to the limit)
        out = self.run_cmd(["nf_fields", "--cols", "label", "--limit", "4"])
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 4)

    # ------------------------------------------------------------------
    # json format
    # ------------------------------------------------------------------

    def test_json_table(self):
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--format", "json", "--limit", "3"])
        data = json.loads(out)
        self.assertEqual(len(data), 3)
        for rec in data:
            self.assertEqual(set(rec), {"label", "degree"})
            self.assertEqual(rec["degree"], 4)

    def test_json_section(self):
        # json output works for a section even though json is not a download language
        out = self.run_cmd(["NumberField", "degree=4", "--format", "json", "--limit", "2"])
        data = json.loads(out)
        self.assertEqual(len(data), 2)
        self.assertTrue(all("label" in rec for rec in data))

    # ------------------------------------------------------------------
    # csv / tsv format
    # ------------------------------------------------------------------

    def test_csv_table(self):
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--format", "csv", "--limit", "3"])
        lines = [line for line in out.splitlines() if line]
        self.assertEqual(lines[0], "label,degree")
        self.assertEqual(len(lines), 4)  # header + 3 rows

    def test_tsv_table(self):
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--format", "tsv", "--limit", "2"])
        lines = [line for line in out.splitlines() if line]
        self.assertEqual(lines[0], "label\tdegree")
        self.assertEqual(len(lines), 3)

    def test_csv_section_download(self):
        # csv for a section goes through the download machinery
        out = self.run_cmd(["NumberField", "degree=4", "--format", "csv", "--limit", "2"])
        self.assertTrue(out.strip())
        self.assertIn("4.0.", out)

    # ------------------------------------------------------------------
    # download-language formats
    # ------------------------------------------------------------------

    def test_sage_section(self):
        out = self.run_cmd(["NumberField", "degree=4", "--format", "sage", "--limit", "2"])
        self.assertIn("data", out)
        self.assertIn("4.0.", out)

    def test_pari_maps_to_gp(self):
        # The CLI format "pari" must map to the download language key "gp"
        out = self.run_cmd(["NumberField", "degree=4", "--format", "pari", "--limit", "2"])
        self.assertIn("data", out)
        self.assertIn("4.0.", out)

    def test_magma_section(self):
        out = self.run_cmd(["NumberField", "degree=4", "--format", "magma", "--limit", "2"])
        self.assertIn("4.0.", out)

    # ------------------------------------------------------------------
    # completeness
    # ------------------------------------------------------------------

    def test_completeness_text(self):
        out = self.run_cmd(["nf_fields", '{"degree":2,"r2":1,"class_number":17}', "--completeness", "--cols", "label", "--limit", "2"])
        self.assertIn("Complete", out)

    def test_completeness_json(self):
        out = self.run_cmd(["nf_fields", '{"degree":2,"r2":1,"class_number":17}', "--completeness", "--format", "json", "--cols", "label", "--limit", "2"])
        data = json.loads(out)
        self.assertIn("complete", data)
        self.assertIn("results", data)
        self.assertTrue(data["complete"])

    # ------------------------------------------------------------------
    # sort / oneper
    # ------------------------------------------------------------------

    def test_sort_descending(self):
        # A descending column starts with "-", so it must be passed with the
        # "=" form (argparse would otherwise treat "-disc_abs" as a flag).
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,disc_abs", "--sort=-disc_abs", "--limit", "5"])
        rows = self.raw_rows(out)
        discs = [int(row.split("|")[1]) for row in rows]
        self.assertEqual(discs, sorted(discs, reverse=True))

    def test_oneper(self):
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--oneper", "degree", "--limit", "10"])
        rows = self.raw_rows(out)
        # Only one result per distinct value of degree, and all have degree 4
        self.assertEqual(len(rows), 1)

    def test_oneper_csv(self):
        # one_per makes psycodict return extra grouping/sort columns; the csv
        # writer must ignore those rather than crash.
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,galt", "--oneper", "galt", "--format", "csv", "--limit", "10"])
        lines = [line for line in out.splitlines() if line]
        self.assertEqual(lines[0], "label,galt")
        # Every data row has exactly the two requested columns
        for line in lines[1:]:
            self.assertEqual(len(line.split(",")), 2)

    # ------------------------------------------------------------------
    # raw SQL
    # ------------------------------------------------------------------

    def test_sql_table(self):
        out = self.run_cmd(["nf_fields", "--sql", "degree = 4 AND class_number = 5",
                            "--cols", "label,degree,class_number", "--format", "json", "--limit", "3"])
        data = json.loads(out)
        self.assertEqual(len(data), 3)
        for rec in data:
            self.assertEqual(rec["degree"], 4)
            self.assertEqual(rec["class_number"], 5)

    def test_sql_raw_format(self):
        out = self.run_cmd(["nf_fields", "--sql", "degree = 2", "--cols", "label,degree", "--limit", "4"])
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row.split("|")[1], "2")

    # ------------------------------------------------------------------
    # random
    # ------------------------------------------------------------------

    def test_random_table(self):
        out = self.run_cmd(["nf_fields", '{"degree":4}', "--random", "--cols", "label,degree"])
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].split("|")[1], "4")

    def test_random_json_section(self):
        out = self.run_cmd(["NumberField", "degree=4", "--random", "--format", "json"])
        data = json.loads(out)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["degree"], 4)

    def test_random_no_match(self):
        # A query with no results returns nothing (just the raw headers)
        out = self.run_cmd(["nf_fields", '{"degree":-1}', "--random", "--cols", "label"])
        self.assertEqual(self.raw_rows(out), [])

    def test_random_with_sql_errors(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", "--sql", "degree = 4", "--random"])

    # ------------------------------------------------------------------
    # help
    # ------------------------------------------------------------------

    def test_help_table(self):
        out = self.run_cmd(["help", "nf_fields"])
        self.assertIn("nf_fields: Number fields", out)
        self.assertIn("Columns:", out)
        # A known column and (part of) its description appear
        self.assertIn("degree", out)
        self.assertIn("class number", out)

    def test_help_column(self):
        out = self.run_cmd(["help", "nf_fields", "degree"]).strip()
        self.assertEqual(out, "nf_fields.degree: degree of the field over *Q*")

    def test_help_section_column(self):
        out = self.run_cmd(["help", "NumberField", "class_number"]).strip()
        self.assertEqual(out, "nf_fields.class_number: class number")

    def test_help_invalid_column(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["help", "nf_fields", "not_a_column"])

    def test_help_too_many_args(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["help", "nf_fields", "degree", "extra"])

    # ------------------------------------------------------------------
    # output file
    # ------------------------------------------------------------------

    def test_output_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--format", "csv", "--limit", "2", "-o", path])
            with open(path) as F:
                content = F.read()
            self.assertEqual(content.splitlines()[0], "label,degree")

    def test_output_file_exists_no_force(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            with open(path, "w") as F:
                F.write("existing")
            with self.assertRaises(SystemExit):
                self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label", "--format", "csv", "-o", path])
            # The pre-existing file must be left untouched
            with open(path) as F:
                self.assertEqual(F.read(), "existing")

    def test_output_file_force(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            with open(path, "w") as F:
                F.write("existing")
            self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,degree", "--format", "csv", "--limit", "2", "-o", path, "--force"])
            with open(path) as F:
                self.assertEqual(F.read().splitlines()[0], "label,degree")

    # ------------------------------------------------------------------
    # error handling
    # ------------------------------------------------------------------

    def test_error_invalid_table(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["NotARealTable", "--limit", "1"])

    def test_error_invalid_cols(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"degree":4}', "--cols", "label,not_a_column", "--limit", "1"])

    def test_error_table_url_query(self):
        # url-style queries are not supported for raw tables (no search wrapper)
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", "degree=4", "--limit", "1"])

    def test_error_unsupported_format_for_table(self):
        # sage/gap/etc. are only available for sections with a download object
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"degree":4}', "--format", "sage", "--limit", "1"])

    def test_error_too_many_positional(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"degree":4}', "extra", "--limit", "1"])

    def test_error_invalid_sort_column(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"degree":4}', "--sort", "not_a_column", "--limit", "1"])

    # ------------------------------------------------------------------
    # rejecting unknown search criteria (review comment)
    # ------------------------------------------------------------------

    def test_unknown_section_param_errors(self):
        # A typo'd/unknown url parameter is an error, not silently ignored
        with self.assertRaises(SystemExit):
            self.run_cmd(["NumberField", "degree=4&nonsense=5", "--limit", "1"])

    def test_known_noncolumn_section_param_ok(self):
        # signature is a valid search box, even though it is not a db column
        out = self.run_cmd(["NumberField", "degree=4&signature=[0,2]", "--cols", "label", "--limit", "1"])
        self.assertEqual(len(self.raw_rows(out)), 1)

    def test_unknown_json_column_errors(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"degre":4}', "--cols", "label", "--limit", "1"])

    def test_unknown_json_column_nested_errors(self):
        # also caught inside $or
        with self.assertRaises(SystemExit):
            self.run_cmd(["nf_fields", '{"$or":[{"degree":4},{"notacol":1}]}', "--cols", "label", "--limit", "1"])

    def test_json_value_operator_ok(self):
        # $-operators at the value level are not mistaken for columns
        out = self.run_cmd(["nf_fields", '{"degree":{"$gte":4}}', "--cols", "label,degree", "--limit", "3"])
        self.assertEqual(len(self.raw_rows(out)), 3)

    # ------------------------------------------------------------------
    # pasting a full LMFDB url
    # ------------------------------------------------------------------

    def test_url_paste_search(self):
        out = self.run_cmd(["https://www.lmfdb.org/NumberField/?degree=4", "--cols", "label,degree", "--limit", "2"])
        rows = self.raw_rows(out)
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row.split("|")[1], "4")

    def test_url_paste_beta(self):
        out = self.run_cmd(["https://beta.lmfdb.org/NumberField/?degree=4", "--cols", "label", "--limit", "2"])
        self.assertEqual(len(self.raw_rows(out)), 2)

    def test_url_paste_download_format(self):
        # Submit=sage in the url selects the sage download format
        out = self.run_cmd(["https://www.lmfdb.org/NumberField/?degree=4&download=1&Submit=sage", "--limit", "2"])
        self.assertIn("data", out)
        self.assertIn("4.0.", out)

    def test_url_paste_format_override(self):
        # an explicit --format overrides the download format in the url
        out = self.run_cmd(["https://www.lmfdb.org/NumberField/?degree=4&Submit=sage", "--format", "json", "--limit", "1"])
        data = json.loads(out)
        self.assertEqual(len(data), 1)

    def test_url_paste_bad_host_errors(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["https://evil.example.com/NumberField/?degree=4"])

    def test_url_paste_object_page_errors(self):
        # an object home page is not a search-results url
        with self.assertRaises(SystemExit):
            self.run_cmd(["https://www.lmfdb.org/NumberField/4.0.117.1"])

    def test_url_paste_with_extra_query_errors(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(["https://www.lmfdb.org/NumberField/?degree=4", "degree=2"])

    # parse_lmfdb_url unit tests (no database access)

    def test_parse_url_basic(self):
        parser = build_parser()
        section, query, fmt = parse_lmfdb_url("https://www.lmfdb.org/NumberField/?degree=4&class_number=2", parser)
        self.assertEqual(section, "NumberField")
        self.assertEqual(query, "degree=4&class_number=2")
        self.assertIsNone(fmt)

    def test_parse_url_pari_mapping(self):
        # the website "gp" download language maps to the CLI "pari" format
        parser = build_parser()
        _, _, fmt = parse_lmfdb_url("https://www.lmfdb.org/NumberField/?degree=4&download=1&Submit=gp", parser)
        self.assertEqual(fmt, "pari")

    def test_parse_url_download_default_text(self):
        parser = build_parser()
        _, _, fmt = parse_lmfdb_url("https://www.lmfdb.org/NumberField/?download=1", parser)
        self.assertEqual(fmt, "text")

    def test_parse_url_trailing_slash_section(self):
        parser = build_parser()
        section, query, fmt = parse_lmfdb_url("https://www.lmfdb.org/Character/Dirichlet/?modulus=7", parser)
        self.assertEqual(section, "Character/Dirichlet/")
        self.assertEqual(query, "modulus=7")

    def test_sections_match_section_lookup(self):
        # SECTIONS must stay in sync with the section_lookup dispatch
        src = inspect.getsource(section_lookup)
        found = set(re.findall(r'section == "([^"]+)"', src))
        self.assertEqual(set(SECTIONS), found)
