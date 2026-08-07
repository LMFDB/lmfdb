import csv
import io
import re

from lmfdb.tests import LmfdbTest

# A search for the subgroups of a single small group (D_4), used to test the download of
# grouped columns.  The query is the url encoding of {'ambient': '8.3'}.
SUBGROUP_DOWNLOAD = ("/Groups/Abstract/Subgroups?download=1"
                     "&query=%7B%27ambient%27%3A+%278.3%27%7D"
                     "&ambient=8.3&download_row_count=3&Submit=")


def list_entries(field):
    """
    The top level entries of a list in a download file, as strings.  Entries of nested
    lists are not broken out, so this gives the length of the list as downloaded.
    """
    assert field.startswith("[") and field.endswith("]"), field
    entries = ['']
    escaped = in_string = False
    depth = 0
    for c in field[1:-1]:
        if escaped:
            escaped = False
        elif in_string:
            escaped = c == "\\"
            in_string = c != '"'
        elif c == '"':
            in_string = True
        elif c in "[(":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            entries.append('')
            continue
        entries[-1] += c
    return [entry.strip() for entry in entries]


def grouped_schema(page):
    """
    The expansions of the grouped columns, as (title, [subcolumn titles]) pairs in order,
    taken from the header comment of a text download.
    """
    header = page.split("where the grouped columns are themselves lists:")[-1]
    header = header.split("For more details")[0]
    schema = []
    for line in header.split("\n"):
        match = re.match(r"^#\s+(.+) = \[(.+)\]$", line)
        if match:
            schema.append((match.group(1), match.group(2).split(", ")))
    return schema


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

    def test_subgroup_search_download_text(self):
        r"""
        The subgroup columns are grouped, and each group downloads as a list of its
        subcolumns' values, so the download must describe those subcolumns (#6477).
        """
        page = self.tc.get(SUBGROUP_DOWNLOAD + "text").get_data(as_text=True)

        # The top level shape of a row is unchanged
        self.assertIn("[Label, Subgroup, Ambient, Quotient]", page)

        # and each grouped column is expanded into its subcolumns, in order.  We check the
        # first and last subcolumn along with a few in between, so that an expansion that is
        # truncated or reordered fails even if a column is added later.
        schema = grouped_schema(page)
        self.assertEqual([title for title, subs in schema], ["Subgroup", "Ambient", "Quotient"])
        expansions = dict(schema)
        for title, expected in [
            ("Subgroup", ["Sub. name", "Sub. order", "Sub. normal", "Sub. central", "Sub. metacyclic"]),
            ("Ambient", ["Ambient name", "Ambient order"]),
            ("Quotient", ["Quo. name", "Quo. size", "Quo. abelian", "Quo. metabelian"]),
        ]:
            subs = expansions[title]
            self.assertEqual([sub for sub in subs if sub in expected], expected)
            self.assertEqual(subs[0], expected[0])
            self.assertEqual(subs[-1], expected[-1])

            # The definitions at the bottom introduce the group and describe its subcolumns
            self.assertIn(f" {title} is a grouped column, downloaded as a list of the following subcolumns:", page)
        for title, name in [("Sub. name", "sub_name"), ("Sub. order", "subgroup_order"),
                            ("Sub. metacyclic", "metacyclic"), ("Ambient name", "ambient_name"),
                            ("Ambient order", "ambient_order"), ("Quo. name", "quotient_name"),
                            ("Quo. metabelian", "quotient_metabelian")]:
            self.assertIn(f"{title} ({name}) --", page)

        # The name of a group downloads as a [label, TeX name] pair rather than a single name,
        # which is documented for the subgroup, the ambient group and the quotient
        for what in ["subgroup", "ambient group", "quotient"]:
            self.assertIn(f"A two-element list [label, name] for the {what} as an abstract group", page)

        # Finally, the downloaded rows have the documented shape
        rows = [line for line in page.split("\n") if line.startswith('"8.3.')]
        self.assertTrue(rows)
        for row in rows:
            fields = row.split("\t")
            self.assertEqual(len(fields), 4)
            for field, title in zip(fields[1:], ["Subgroup", "Ambient", "Quotient"]):
                entries = list_entries(field)
                self.assertEqual(len(entries), len(expansions[title]))
                # whose first entry is the [label, TeX name] pair
                self.assertEqual(len(list_entries(entries[0])), 2)

    def test_subgroup_search_download_csv(self):
        r"""
        CSV files have no comments, so the header row itself has to describe the contents of
        each grouped column (#6477).  We keep one field per column, so the shape is unchanged.
        """
        page = self.tc.get(SUBGROUP_DOWNLOAD + "csv").get_data(as_text=True)
        rows = [row for row in csv.reader(io.StringIO(page)) if row]
        header, data = rows[0], rows[1:]
        self.assertEqual(len(header), 4)

        # An ordinary column is still just its name, linked to its knowl
        self.assertTrue(header[0].startswith("=HYPERLINK("), header[0])
        self.assertTrue(header[0].endswith('"label")'), header[0])

        # while a grouped column also lists the contents of its nested list, in order
        for cell, name, expected in [
            (header[1], "subgroup_cols", ["sub_name", "subgroup_order", "normal", "metacyclic"]),
            (header[2], "ambient_cols", ["ambient_name", "ambient_order"]),
            (header[3], "quotient_cols", ["quotient_name", "quotient_order", "quotient_metabelian"]),
        ]:
            match = re.match(r"^(\w+) \[(.+)\]$", cell)
            self.assertTrue(match, cell)
            self.assertEqual(match.group(1), name)
            subcols = match.group(2).split(", ")
            self.assertEqual([sub for sub in subcols if sub in expected], expected)
            self.assertEqual(subcols[0], expected[0])
            self.assertEqual(subcols[-1], expected[-1])

        # Each row still has one field per top level column
        self.assertTrue(data)
        for row in data:
            self.assertEqual(len(row), len(header))

    def test_scalar_colgroup_download(self):
        r"""
        Column groups that set a download_col download as a single value rather than as a
        list over their subcolumns, so they must not be expanded into subcolumns (#6477).
        """
        from lmfdb.classical_modular_forms.main import newform_columns
        from lmfdb.groups.abstract.main import conjugacy_class_columns, subgroup_columns
        from lmfdb.utils.search_columns import ColGroup

        def get_col(columns, name):
            # Some names are shared with a spacer column, so we ask for the group by type
            return next(col for col in columns.columns
                        if col.name == name and isinstance(col, ColGroup))

        for columns, name, download_col in [
            (newform_columns, "traces", "trace_display"),
            (newform_columns, "atkin_lehner", "atkin_lehner_eigenvals"),
            (conjugacy_class_columns, "power_cols", "powers"),
        ]:
            col = get_col(columns, name)
            self.assertEqual(col.download_col, download_col)
            self.assertEqual(col.download_subcols({}), [])
            # and the value downloaded is the single stored column
            self.assertEqual(col.download({download_col: "unchanged"}), "unchanged")

        # By contrast the subgroup groups, which have no download_col, are expanded
        for name in ["subgroup_cols", "ambient_cols", "quotient_cols"]:
            col = get_col(subgroup_columns, name)
            self.assertIsNone(col.download_col)
            self.assertEqual(col.download_subcols({}), col.subcols)

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
