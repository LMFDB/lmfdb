import re
from unittest.mock import patch

from lmfdb.tests import LmfdbTest
from lmfdb.api.api import hidden_collection
from lmfdb.knowledge.knowl import knowldb
from lmfdb.utils.psycopg_compat import SQL


def table_links(page):
    r"""
    The (href, table name) pairs of the table links on an api index page
    """
    return re.findall(r'<td class="api-table-name"><a href="/api/([^"]+)/">([^<]+)</a>', page)


class DescriptionKnowlTest(LmfdbTest):
    r"""
    The api index displays the ``tables.<name>`` description knowls, so the
    lookups behind it have to return the current revision of each knowl.
    """

    def _edited(self, pattern, limit=3):
        r"""
        The ids of some description knowls matching ``pattern`` whose content
        has been edited, i.e. that have more than one visible revision
        """
        selecter = SQL("SELECT id FROM kwl_knowls WHERE id LIKE %s AND type = %s AND status >= %s GROUP BY id HAVING COUNT(DISTINCT content) > 1 ORDER BY id LIMIT %s")
        return [rec[0] for rec in knowldb._safe_execute(selecter, [pattern, 2, 0, limit])]

    def _current(self, kid):
        r"""
        The content of the newest revision of a knowl visible on this server
        """
        # get_edit_history sorts the revisions by increasing timestamp
        return knowldb.get_edit_history(kid)[-1]["content"]

    def test_table_descriptions_are_current(self):
        r"""
        Check that both the single and the bulk table description lookups
        return the newest revision of an edited knowl
        """
        edited = self._edited("tables.%")
        assert edited, "no edited table description knowl to test against"
        bulk = knowldb.get_table_descriptions()
        for kid in edited:
            table = kid.split(".", 1)[1]
            current = self._current(kid)
            assert bulk[table] == current, "stale description for %s" % table
            assert knowldb.get_table_description(table).content == current

    def test_column_descriptions_are_current(self):
        r"""
        Check that the column description lookup returns the newest revision
        of an edited knowl
        """
        edited = self._edited("columns.%", limit=1)
        assert edited, "no edited column description knowl to test against"
        kid = edited[0]
        _, table, col = kid.split(".")
        assert knowldb.get_column_descriptions(table)[col].content == self._current(kid)


class ApiTest(LmfdbTest):
    def test_api_home(self):
        r"""
        Check that the top-level api page works: tables grouped into datasets
        with row counts and descriptions, the collapsed usage docs, the filter
        box, and links to the stats and access options pages
        """
        data = self.tc.get("/api", follow_redirects=True).get_data(as_text=True)
        assert "entry point to the API" in data
        assert "Query syntax and examples" in data
        assert 'id="api-filter"' in data
        # datasets are explained
        assert "Higher genus curves with automorphisms" in data
        assert 'id="hgcwa"' in data
        # fq_fields holds finite fields, not function fields
        assert "fq &mdash; Finite fields" in data
        # links to the stats and access options pages
        assert '"/api/stats"' in data
        assert '"/api/options"' in data
        # hidden tables are not shown by default, but can be
        assert "test_table" not in data
        assert '"/api/all"' in data

    def test_api_home_links(self):
        r"""
        Check that /api/ lists exactly the tables that are not hidden, that
        /api/all lists all of them, and that the links work
        """
        hidden = {name for name in self.db.tablenames if hidden_collection(name)}
        data = self.tc.get("/api", follow_redirects=True).get_data(as_text=True)
        links = table_links(data)
        assert all(href == name for href, name in links)
        assert sorted(name for _, name in links) == sorted(set(self.db.tablenames) - hidden)

        data = self.tc.get("/api/all", follow_redirects=True).get_data(as_text=True)
        links = table_links(data)
        assert all(href == name for href, name in links)
        assert sorted(name for _, name in links) == sorted(self.db.tablenames)
        # the anchors in the jump strip match the dataset sections
        sections = set(re.findall(r'<div class="api-dataset" id="([^"]+)"', data))
        jumps = set(re.findall(r'<a href="#([^"]+)">', data)) - {"api-tables"}
        assert jumps == sections

    def test_api_home_hidden(self):
        r"""
        Check that tables following either test naming convention (``test_x``
        and ``x_test``) are hidden from /api/ and shown on /api/all
        """
        tests = {name for name in self.db.tablenames
                 if name.startswith("test") or name.endswith("_test")}
        assert "test_table" in tests, "no test_-prefixed table in the database"
        assert any(name.endswith("_test") for name in tests), "no _test-suffixed table in the database"
        assert tests <= {name for name in self.db.tablenames if hidden_collection(name)}

        shown = {name for _, name in table_links(self.tc.get("/api", follow_redirects=True).get_data(as_text=True))}
        assert not (tests & shown)
        shown = {name for _, name in table_links(self.tc.get("/api/all", follow_redirects=True).get_data(as_text=True))}
        assert tests <= shown

    def test_api_home_descriptions(self):
        r"""
        Check that the description of a table is shown in its row and is
        searchable by the filter box
        """
        description = "The table that the api tests use"
        with patch.object(knowldb, "get_table_descriptions", return_value={"test_table": description}):
            data = self.tc.get("/api/all", follow_redirects=True).get_data(as_text=True)
        assert '<td class="api-table-desc">%s</td>' % description in data
        assert 'data-desc="%s"' % description.lower() in data
        # the real descriptions are not all empty either
        data = self.tc.get("/api", follow_redirects=True).get_data(as_text=True)
        described = [desc for desc in re.findall(r'<td class="api-table-desc">([^<]*)</td>', data) if desc.strip()]
        assert len(described) > 20, "only %s tables have a description" % len(described)

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
