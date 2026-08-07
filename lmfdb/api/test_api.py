import re

from lmfdb.tests import LmfdbTest

class ApiTest(LmfdbTest):
    def test_api_home(self):
        r"""
        Check that the top-level api page works
        """
        data = self.tc.get("/api", follow_redirects=True).get_data(as_text=True)
        assert "API for accessing the LMFDB Database" in data

    def test_api_databases(self):
        r"""
        Check that one collection from each database works
        """
        dbs = ['lat_lattices', 'lfunc_lfunctions', 'av_fqisog',
               'artin_reps', 'bmf_forms', 'hgcwa_passports',
               'ec_curvedata', 'g2c_curves', 'halfmf_forms',
               'hgm_motives', 'hmf_forms', 'lf_fields',
               'modlmf_forms', 'modlgal_reps', 'nf_fields',
               'gps_st', 'smf_dims', 'gps_transitive',
               'fq_fields', 'hecke_algebras', 'belyi_passports']
        for tbl in dbs:
            data = self.tc.get("/api/{}".format(tbl), follow_redirects=True).get_data(as_text=True)
            assert "JSON" in data

    def test_api_examples_html(self):
        r"""
        Check that the sample queries on the top page all work (html output)
        """

        queries = [
                'nf_fields/?r2=i5&degree=i12',
                'ec_curvedata/?rank=i2&torsion=i5',
                'ec_curvedata/?ainvs=li0;1;1;-840;39800&_delim=;',
                'ec_curvedata/?_delim=%3B&torsion_structure=ls2%3B2',
                ]
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).get_data(as_text=True)
            assert 'Query: <code><a href="/api/' in data
            assert "Error:" not in data

    def test_api_examples_yaml(self):
        r"""
        Check that the sample queries on the top page all work (yaml output)
        """
        queries = ['ec_curvedata/?ainvs=li0;1;1;-840;39800&_format=yaml&_delim=;',
                ]
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).get_data(as_text=True)
            assert ("jinv:\n  - -65626385453056\n  - 656000554923" in data) or ("'jinv': !!python/unicode '-65626385453056/656000554923'" in data)
            assert "Error:" not in data

    def test_api_examples_json(self):
        r"""
        Check that the sample queries on the top page all work (json output)
        """
        query = 'nf_fields/?degree=i12&r2=i5&_format=json'
        data = self.tc.get("/api/{}".format(query), follow_redirects=True).get_data(as_text=True)
        assert '"label": "12.2.167630295667.1",' in data

    def test_api_usage(self):
        r"""
        Check that the queries used by ODK demo all work
        """
        queries = ['gps_transitive?_format=json&label=1T1',
                   'gps_transitive?_format=json&label=8T3',
                   'ec_curvedata?_format=json&label=11a1']
        for query in queries:
            data = self.tc.get("/api/{}".format(query), follow_redirects=True).get_data(as_text=True)
            if '1T1' in query:
                assert '"name": "Trivial group"' in data
            if '8T3' in query:
                assert '"name": "E(8)=2[x]2[x]2"' in data
            if '11a1' in query:
                assert '"lmfdb_label": "11.a2"' in data
                assert '"jinv": [\n        -122023936,\n        161051\n      ]' in data

    def test_api_schema_display(self):
        r"""
        Check the schema display on table pages: an Example column filled
        from a random row, and the table description no longer in the title
        """
        for tbl in ['mf_hecke_traces', 'nf_fields']:  # one small, one big table
            data = self.tc.get("/api/{}".format(tbl), follow_redirects=True).get_data(as_text=True)
            assert "<th>Example</th>" in data
            assert 'class="schema-example"' in data
            assert 'class="schema-holder {}-schema-holder"'.format(tbl) in data
            # the table description is displayed as a knowl, not in the title
            assert "Database - {} (".format(tbl) not in data
        # The random row must be sampled with a projection that includes the
        # search columns, otherwise the Example cells for search columns render
        # blank.  degree is a search column of nf_fields that is never null, so
        # its Example cell must carry an actual value, not an empty string.
        data = self.tc.get("/api/nf_fields", follow_redirects=True).get_data(as_text=True)
        m = re.search(r'columns\.nf_fields\.degree\b.*?'
                      r'<td class="schema-example">(.*?)</td>', data, re.S)
        assert m is not None, "degree row not found in nf_fields schema table"
        assert m.group(1).strip() != "", "Example cell for search column 'degree' is blank"

    def test_api_table_description(self):
        r"""
        Check that the tables.<table> knowl is shown with its own title as a
        heading above the schema, rather than folded into the page title
        """
        from markupsafe import escape
        from lmfdb.knowledge.knowl import Knowl
        from lmfdb.knowledge.main import md, md_preprocess

        tbl = 'nf_fields'
        # The title and content live in the knowl database, so we ask for them
        # rather than hard coding them here.
        with self.app.test_request_context():
            self.app.preprocess_request()
            knowl = Knowl('tables.{}'.format(tbl))
            assert knowl.exists(), "no tables.{} knowl to test against".format(tbl)
            heading = "<h2>{}</h2>".format(escape(knowl.title))
            content = md.convert(md_preprocess(knowl.content))

        data = self.tc.get("/api/{}".format(tbl), follow_redirects=True).get_data(as_text=True)
        assert heading in data, "table description heading missing"
        assert content in data, "table description content missing"
        # the heading introduces the description, and both precede the schema
        assert data.index(heading) < data.index(content) < data.index("{}-schema-shower".format(tbl))

    def test_api_schema_on_datapage(self):
        r"""
        Check that the schema display on underlying data pages still works
        (with no Example column there)
        """
        data = self.tc.get("/EllipticCurve/Q/data/11.a1", follow_redirects=True).get_data(as_text=True)
        assert 'class="schema-holder ec_curvedata-schema-holder"' in data
        assert "<th>Example</th>" not in data
