import re

import pytest

from lmfdb.api.api import parse_api_value, parse_numeric
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

    def test_parse_numeric(self):
        r"""
        Check the range syntax used by the i and f prefixes
        """
        # exact values
        assert parse_numeric("11", int) == 11
        assert parse_numeric("2.5", float) == 2.5
        # ranges are inclusive on both ends
        assert parse_numeric("11..100", int) == {"$gte": 11, "$lte": 100}
        assert parse_numeric("389..", int) == {"$gte": 389}
        assert parse_numeric("..2.5", float) == {"$lte": 2.5}
        assert parse_numeric("-0.9..-0.7", float) == {"$gte": -0.9, "$lte": -0.7}
        # a range must have at least one endpoint
        with pytest.raises(ValueError):
            parse_numeric("..", int)

    def test_parse_api_value(self):
        r"""
        Check the decoding of query values from the type-prefix syntax
        """
        # None matches null entries; the literal string is available as sNone
        assert parse_api_value("None", ",") is None
        assert parse_api_value("sNone", ",") == "None"
        # the contains prefixes build $contains queries
        assert parse_api_value("cf1.25", ",") == {"$contains": [1.25]}
        assert parse_api_value("ci7", ",") == {"$contains": [7]}
        assert parse_api_value("cs11.a2", ",") == {"$contains": ["11.a2"]}
        assert parse_api_value("cpy[1,2]", ",") == {"$contains": [[1, 2]]}
        # scalars, lists and ranges
        assert parse_api_value("i11", ",") == 11
        assert parse_api_value("f2.5", ",") == 2.5
        assert parse_api_value("i11..100", ",") == {"$gte": 11, "$lte": 100}
        assert parse_api_value("f..2.5", ",") == {"$lte": 2.5}
        assert parse_api_value("lsa;b", ";") == ["a", "b"]
        assert parse_api_value("li2;2", ";") == [2, 2]
        assert parse_api_value("lf0.5,1.5", ",") == [0.5, 1.5]
        assert parse_api_value("py{'a': 1}", ",") == {"a": 1}
        # unprefixed and malformed typed values are kept as strings
        assert parse_api_value("11.a2", ",") == "11.a2"
        assert parse_api_value("i1.5", ",") == "i1.5"
        assert parse_api_value("i..", ",") == "i.."

    def test_api_range_query(self):
        r"""
        Check range queries using the i and f prefixes
        """
        data = self.tc.get('/api/ec_curvedata/?conductor=i11..100&_format=json&_fields=conductor', follow_redirects=True).get_json()
        assert data['data'] and all(11 <= rec['conductor'] <= 100 for rec in data['data'])
        # both endpoints are included: the three curves of conductor 11 are found
        data = self.tc.get('/api/ec_curvedata/?conductor=i11..11&_format=json&_fields=conductor', follow_redirects=True).get_json()
        assert len(data['data']) == 3 and all(rec['conductor'] == 11 for rec in data['data'])
        # one-sided ranges
        data = self.tc.get('/api/ec_curvedata/?conductor=i..20&_format=json&_fields=conductor', follow_redirects=True).get_json()
        assert data['data'] and all(rec['conductor'] <= 20 for rec in data['data'])
        data = self.tc.get('/api/ec_curvedata/?conductor=i389..&_format=json&_fields=conductor', follow_redirects=True).get_json()
        assert data['data'] and all(rec['conductor'] >= 389 for rec in data['data'])
        # float range (numeric columns are encoded as RealLiteral dicts)
        data = self.tc.get('/api/ec_curvedata/?faltings_height=f-0.9..-0.7&_format=json&_fields=faltings_height', follow_redirects=True).get_json()
        assert data['data'] and all(-0.9 <= float(rec['faltings_height']['data']) <= -0.7 for rec in data['data'])

    def test_api_list_of_strings_query(self):
        r"""
        Check the ls prefix, which splits the whole value into a list of strings
        """
        # the example on the API index page: curves with torsion structure [2,2], not [2]
        data = self.tc.get('/api/ec_curvedata/?torsion_structure=ls2;2&_delim=;&_format=json&_fields=torsion_structure', follow_redirects=True).get_json()
        assert data['data'] and all(rec['torsion_structure'] == [2, 2] for rec in data['data'])

    def test_api_contains_float_query(self):
        r"""
        Check the cf prefix, which searches a numeric array for a given value
        """
        # the defining polynomial of 6.0.177147.2 is x^6 + 3, so its coefficients contain 0 but not 0.5
        query = '/api/nf_fields/?label=6.0.177147.2&coeffs=cf%s&_format=json&_fields=label,coeffs'
        data = self.tc.get(query % '0.0', follow_redirects=True).get_json()
        assert [rec['label'] for rec in data['data']] == ['6.0.177147.2']
        data = self.tc.get(query % '0.5', follow_redirects=True).get_json()
        assert data['data'] == []

    def test_api_null_query(self):
        r"""
        Check searching for entries where a column is null
        """
        data = self.tc.get('/api/gps_gl2zhat_fine/?q_gonality=None&_format=json&_fields=q_gonality,label', follow_redirects=True).get_json()
        assert data['data'] and all(rec['q_gonality'] is None for rec in data['data'])

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
