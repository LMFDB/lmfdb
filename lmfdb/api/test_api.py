import json
import re
from decimal import Decimal

from psycodict.encoding import numeric_converter

from lmfdb.api.api import raw_json_dumps
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

    def test_raw_json_dumps(self):
        r"""
        Check the raw serializer (LMFDB#1010) on the decimals that are awkward
        to look for in the database: one that is exactly zero, which psycodict
        hands back as an exact integer wrapper rather than as a real number,
        and which still carries the scale, and the sign, that Postgres sent.
        The exact strings are what matters, since numeric equality catches
        neither a lost scale nor a lost sign.
        """
        for text in ('0.000', '-0.000', '1.250', '-0.30800984111840306468901426146'):
            out = raw_json_dumps(numeric_converter(text))
            assert out == text
            json.loads(out)  # and every one of them is valid JSON
        # zeros nested in an array or an object keep their literal too
        out = raw_json_dumps([numeric_converter('1.250'), numeric_converter('0.000')])
        assert out == '[1.250, 0.000]'
        assert json.loads(out, parse_float=Decimal) == [Decimal('1.250'), Decimal('0.000')]
        out = raw_json_dumps({'a': numeric_converter('-0.000')})
        assert out == '{"a": -0.000}'
        assert json.loads(out, parse_float=Decimal) == {'a': Decimal('-0.000')}

    def test_api_raw(self):
        r"""
        Check the raw output format (LMFDB#1010): newline-delimited JSON with
        no response envelope and no implicit id.  With one requested field each
        line is that field's JSON value, and with several fields each line is a
        JSON array of those values, so a record parses back unambiguously with
        json.loads even when a value contains the delimiter.  Integers and
        nested arrays of integers are also valid GP syntax, hence readable with
        PARI/GP readvec, but other JSON values are not.
        """
        # single field: one JSON value per line
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=ainvs').get_data(as_text=True)
        assert data == "[0, -1, 1, -10, -20]\n"
        assert json.loads(data) == [0, -1, 1, -10, -20]
        # an exact PostgreSQL numeric is a JSON number carrying every stored
        # digit, not the __RealLiteral__ object that records the Sage type
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=faltings_height').get_data(as_text=True)
        assert data == '-0.30800984111840306468901426146\n'
        assert json.loads(data, parse_float=Decimal) == Decimal('-0.30800984111840306468901426146')
        assert '__RealLiteral__' not in data
        # booleans show that the wire syntax is JSON, not a universal GP syntax
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=semistable').get_data(as_text=True)
        assert data == 'true\n'
        assert json.loads(data) is True
        # a NULL is a JSON null, whether alone or beside a value (psycodict
        # leaves NULL columns out of the record; squarefree_disc is unfilled)
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=squarefree_disc').get_data(as_text=True)
        assert data == 'null\n'
        assert json.loads(data) is None
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=squarefree_disc,conductor').get_data(as_text=True)
        assert data == '[null, 11]\n'
        assert json.loads(data) == [None, 11]
        # several fields: one JSON array per line, parseable by json.loads
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=ainvs,conductor').get_data(as_text=True)
        assert data == "[[0, -1, 1, -10, -20], 11]\n"
        assert json.loads(data) == [[0, -1, 1, -10, -20], 11]
        # values keep their exact rendering inside a multi-field record too
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw&_fields=lmfdb_label,faltings_height').get_data(as_text=True)
        assert data == '["11.a2", -0.30800984111840306468901426146]\n'
        assert json.loads(data, parse_float=Decimal) == ['11.a2', Decimal('-0.30800984111840306468901426146')]
        # the _delim only splits _fields; the record itself is still a JSON array
        data = self.tc.get('/api/ec_curvedata/?ainvs=li0;1;1;-840;39800&_delim=;&_format=raw&_fields=ainvs;jinv').get_data(as_text=True)
        assert data == "[[0, 1, 1, -840, 39800], [-65626385453056, 656000554923]]\n"
        assert json.loads(data) == [[0, 1, 1, -840, 39800], [-65626385453056, 656000554923]]
        # a value that itself contains the delimiter still round-trips, because
        # multi-field records are JSON arrays rather than delimiter-joined text
        # (here the delimiter is '.', which occurs inside the label "11.a2";
        # note Cremona 11a1 is LMFDB 11.a2, cf. test_api_usage below)
        data = self.tc.get('/api/ec_curvedata/?label=11a1&_delim=.&_format=raw&_fields=lmfdb_label.conductor').get_data(as_text=True)
        assert data == '["11.a2", 11]\n'
        assert json.loads(data) == ["11.a2", 11]
        # one line per record; each line is independently valid JSON, and a
        # single string field is JSON-quoted and escaped
        data = self.tc.get('/api/ec_curvedata/?conductor=i11&_format=raw&_fields=lmfdb_label&_sort=lmfdb_label').get_data(as_text=True)
        assert data == '"11.a1"\n"11.a2"\n"11.a3"\n'
        assert [json.loads(line) for line in data.splitlines()] == ["11.a1", "11.a2", "11.a3"]
        # raw format requires _fields
        response = self.tc.get('/api/ec_curvedata/?label=11a1&_format=raw')
        assert response.status_code == 400

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
