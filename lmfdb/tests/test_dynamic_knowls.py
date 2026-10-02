
from unittest.mock import patch

from flask import render_template
from markupsafe import escape

from lmfdb.tests import LmfdbTest
from lmfdb.knowledge.knowl import Knowl, knowldb
from lmfdb.utils.datetime_utils import utc_now_naive

class DynamicKnowlTest(LmfdbTest):
    """
    These tests check the functioning of some dynamic knowls.
    """

    def test_Galois_group_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.data?n=5&t=5', follow_redirects=True)
        assert 'Prime degree' in L.get_data(as_text=True)

    def test_conjugacy_classes_knowl(self):
        L = self.tc.get('/knowledge/show/gg.conjugacy_classes.data?n=5&t=5', follow_redirects=True)
        assert '1,3,4,5' in L.get_data(as_text=True)

    def test_character_table_knowl(self):
        L = self.tc.get('/knowledge/show/gg.character_table.data?n=5&t=5', follow_redirects=True)
        # character values now complicated text in mathml, so look for labels
        assert '120.34.5a' in L.get_data(as_text=True)
        assert '5A' in L.get_data(as_text=True)

    def test_abstract_group_knowl(self):
        L = self.tc.get('/knowledge/show/lmfdb.object_information?func=group_data&args=16.5', follow_redirects=True)
        assert '11 subgroups' in L.get_data(as_text=True)

    def test_number_field_knowl(self):
        L = self.tc.get('/knowledge/show/nf.field.data?label=6.0.21296.1', follow_redirects=True)
        assert '-21296' in L.get_data(as_text=True)

    def test_local_field_knowl(self):
        L = self.tc.get('/knowledge/show/lf.field.data?label=2.2.3.4', follow_redirects=True)
        assert 'Residue field degree' in L.get_data(as_text=True)

    def test_galois_module_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.gmodule?ind=3&n=6&t=2', follow_redirects=True)
        assert 'Action' in L.get_data(as_text=True)

    def test_galois_alias_knowl(self):
        L = self.tc.get('/knowledge/show/nf.galois_group.name', follow_redirects=True)
        assert '11T6' in L.get_data(as_text=True)

    def test_prod_knowl_sync(self):
        # This test checks that the script at https://github.com/edgarcosta/lmfdb-gce/blob/master/server_scripts/update_knowls_and_userdb.sh is successully syncing the knowl databases on beta.lmfdb.org and www.lmfdb.org
        # It will be run as part of the CI for PRs against dev or prod.

        from lmfdb import db
        if db.config.postgresql_options["host"] == "proddb.lmfdb.xyz":
            # Create a different connection to devmirror to compare timestamps
            from lmfdb.utils.config import Configuration
            from lmfdb.utils.psycopg_compat import SQL
            from datetime import timedelta
            dev_config = Configuration()
            # Modify configuration to connect to devmirror
            for D in [dev_config.default_args["postgresql"], dev_config.postgresql_options, dev_config.options["postgresql"]]:
                D["host"] = "devmirror.lmfdb.xyz"
                D["port"] = 5432
                D["dbname"] = "lmfdb"
                D["user"] = "lmfdb"
                D["password"] = "lmfdb"
            from psycodict.database import PostgresDatabase
            dev_db = PostgresDatabase(dev_config)

            # Updates happen every 20 minutes, so we only compare knowls older than that (plus a buffer).
            cutoff = utc_now_naive() - timedelta(minutes=30)

            t_query = SQL("SELECT timestamp FROM kwl_knowls WHERE timestamp < %s LIMIT 1")
            dev_t = dev_db._execute(t_query, [cutoff]).fetchone()[0]
            prod_t = db._execute(t_query, [cutoff]).fetchone()[0]

            cnt_query = SQL("SELECT COUNT(*) FROM kwl_knowls WHERE timestamp < %s")
            dev_cnt = dev_db._execute(cnt_query, [cutoff]).fetchone()[0]
            prod_cnt = db._execute(cnt_query, [cutoff]).fetchone()[0]

            # The timestamps and counts should be the same
            assert dev_cnt == prod_cnt and dev_t == prod_t


class DescriptionKnowlTest(LmfdbTest):
    """
    These tests check that a table description knowl has a title that editors
    can set, while a column description knowl keeps its generated title.
    """

    def test_table_title_is_kept(self):
        k = Knowl("tables.nf_fields",
                  data={"title": "Number field data", "content": "", "status": 0})
        assert k.title == "Number field data"

    def test_table_title_is_generated_when_absent(self):
        k = Knowl("tables.nf_fields", data={"title": "", "content": "", "status": 0})
        assert k.title == "Table nf_fields"

    def test_defunct_table_is_marked_once(self):
        k = Knowl("tables.not_a_table",
                  data={"title": "Number field data", "content": "", "status": 0})
        assert k.title == "Number field data (DEFUNCT)"
        # a title saved while the table was defunct already carries the marker
        again = Knowl("tables.not_a_table",
                      data={"title": k.title, "content": "", "status": 0})
        assert again.title == "Number field data (DEFUNCT)"

    def test_column_title_is_generated(self):
        k = Knowl("columns.nf_fields.degree",
                  data={"title": "Number field data", "content": "", "status": 0})
        assert k.title == "Column degree of table nf_fields"
        assert k.coltype == self.db.nf_fields.col_type["degree"]

    def test_editor_title_row(self):
        r"""
        The editor offers a table description an editable title and a column
        description a read-only one; only a column has a Postgres column type.
        """
        def edit_page(ID):
            # the template uses endpoints relative to the knowledge blueprint,
            # so it has to be rendered from the edit page's own request context
            with self.app.test_request_context("/knowledge/edit/" + ID):
                self.app.preprocess_request()
                k = Knowl(ID, editing=True)
                return k, render_template("knowl-edit.html", k=k, title="", bread=[])

        table_knowl, table = edit_page("tables.nf_fields")
        column_knowl, column = edit_page("columns.nf_fields.degree")

        assert '<td>Title</td>' in table
        assert '<input size="40" name="title" id="ktitle" value="{}" />'.format(
            escape(table_knowl.title)) in table
        assert "Postgres column type" not in table

        assert '<input name="title" id="ktitle" value="{}" type="hidden" />'.format(
            escape(column_knowl.title)) in column
        assert "Postgres column type" in column

    def _set_table_description(self, table, description, old):
        r"""
        Run knowldb.set_table_description with the database write mocked out,
        and return the knowl it would have saved.
        """
        saved = []

        def fake_save(knowl, who, most_recent=None, minor=False):
            saved.append(knowl)

        with patch.object(knowldb, "get_knowl", return_value=old), \
             patch.object(knowldb, "save", side_effect=fake_save), \
             patch.object(self.db, "login", return_value="tester"):
            knowldb.set_table_description(table, description)

        assert len(saved) == 1
        return saved[0]

    def test_content_update_keeps_table_title(self):
        r"""
        db.<table>.description(...) updates the content, so it must carry the
        title over rather than saving the generated fallback in its place.
        """
        old = {"authors": ["editor"], "title": "Number field data",
               "content": "Number fields", "status": 0}
        kwl = self._set_table_description("nf_fields", "Fields of finite degree", old)
        assert kwl.title == "Number field data"
        assert kwl.content == "Fields of finite degree"

    def test_content_update_generates_missing_table_title(self):
        # a table description that does not exist yet still gets the fallback
        kwl = self._set_table_description("nf_fields", "Number fields", None)
        assert kwl.title == "Table nf_fields"
