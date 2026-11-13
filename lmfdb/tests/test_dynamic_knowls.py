
from unittest.mock import patch
import re

from flask import render_template, render_template_string
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
        L = self.tc.get('/knowledge/render/nf.field.data?label=6.0.21296.1&number_field_data=x&url_for=x')
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


class KnowlRenderTest(LmfdbTest):
    """
    These tests check what the public knowl popup does with request data.
    """

    def test_request_data_is_not_template_code(self):
        code = "{{ 'zq' ~ 'xj' }}"
        for query in [{"content": code}, {"x": '") }}' + code}]:
            page = self.tc.get("/knowledge/render/nf.degree", query_string=query)
            assert "zqxj" not in page.get_data(as_text=True)
        page = self.tc.post("/knowledge/render/nf.degree", data={"content": code, "footer": "0"})
        assert page.status_code == 405

    def test_generated_title_is_escaped(self):
        page = self.tc.get("/knowledge/render/columns.nf_fields.x%3Csvg%20onload=alert(1)%3E")
        text = page.get_data(as_text=True)
        assert "<svg" not in text
        assert "&lt;svg" in text

    def test_invalid_timestamp_is_ignored(self):
        page = self.tc.get("/knowledge/render/nf.degree?timestamp=abc")
        assert page.status_code == 200
        assert 'class="knowl-content"' in page.get_data(as_text=True)

    def test_out_of_range_timestamp_is_ignored(self):
        for timestamp in ["1" + "0" * 20, "1" + "0" * 400]:
            with self.subTest(timestamp=timestamp):
                page = self.tc.get("/knowledge/render/nf.degree", query_string={"timestamp": timestamp})
                assert page.status_code == 200
                text = page.get_data(as_text=True)
                assert 'class="knowl-content"' in text
                assert "ERROR in the template" not in text

    def test_parameters_named_like_template_variables(self):
        names = ["k", "source", "knowl_permalink", "knowl_header_title"]
        page = self.tc.get("/knowledge/render/nf.degree", query_string={n: "1" for n in names})
        text = page.get_data(as_text=True)
        assert "ERROR in the template" not in text
        assert 'href="/knowledge/show/nf.degree?' in text

    def test_parameters_named_like_context_variables(self):
        for name in ["url_for", "knowl_title", "user_is_authenticated"]:
            with self.subTest(name=name):
                page = self.tc.get("/knowledge/render/nf.degree", query_string={name: "x"})
                text = page.get_data(as_text=True)
                assert "ERROR in the template" not in text
                assert 'class="knowl-content"' in text
                assert 'href="/knowledge/edit/nf.degree"' not in text


class KnowlEditorTest(LmfdbTest):
    def setUp(self):
        login = patch.dict(self.app.config, LOGIN_DISABLED=True)
        login.start()
        self.addCleanup(login.stop)
        self.tc = self.app.test_client()

    def test_preview_requires_session_token(self):
        with self.tc.session_transaction() as session:
            session["_csrf_token"] = "session-token"
        for token in [None, "wrong", "\u00e9"]:
            with self.subTest(token=token):
                data = {"content": "Preview text", "footer": "0"}
                if token is not None:
                    data["csrf_token"] = token
                with patch("lmfdb.knowledge.main.Knowl", side_effect=AssertionError("Preview read the database before checking the token")):
                    page = self.tc.post("/knowledge/preview/nf.degree", data=data)
                assert page.status_code == 400

    def test_save_requires_session_token(self):
        with self.tc.session_transaction() as session:
            session["_csrf_token"] = "session-token"
        for token in [None, "wrong"]:
            with self.subTest(token=token):
                data = {"id": "nf.degree", "title": "Degree", "content": "Preview text"}
                if token is not None:
                    data["csrf_token"] = token
                with patch("lmfdb.knowledge.main.Knowl", side_effect=AssertionError("Save read the database before checking the token")):
                    page = self.tc.post("/knowledge/save", data=data)
                assert page.status_code == 400

    def test_editor_token_allows_preview(self):
        with patch.object(knowldb, "set_locked"):
            page = self.tc.get("/knowledge/edit/nf.degree?lock=ignore")
        assert page.status_code == 200
        token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page.get_data(as_text=True)).group(1)
        page = self.tc.post("/knowledge/preview/nf.degree",
                            data={"csrf_token": token, "content": "Preview text", "footer": "0"})
        assert page.status_code == 200
        assert "Preview text" in page.get_data(as_text=True)


class AIWrittenKnowlTest(LmfdbTest):
    """
    AI-written knowls are only shown to logged-in users, and become normal
    knowls when someone saves them in the editor.
    """
    ai_data = {"title": "AI-written title", "content": "AI-written content", "status": 0, "type": 3}

    def test_type_codes(self):
        for ID, code, typ in [("test.ai", 3, 0), ("nf.6.0.21296.1.top", 4, 1), ("nf.6.0.21296.1.bottom", 5, -1)]:
            k = Knowl(ID, data={"title": "", "content": "", "type": code, "source": None})
            assert (k.type, k.ai_written) == (typ, True)
            assert k.copy().ai_written
        k = Knowl("test.ai", data={"title": "", "content": "", "type": 0})
        assert (k.type, k.ai_written) == (0, False)

    def _saved_type(self, ID, ai_written):
        saved = []
        k = Knowl(ID, data={"title": "Title", "content": "Content", "status": 0})
        k.ai_written = ai_written
        with patch.object(knowldb, "_execute", side_effect=lambda query, values: saved.append(values)), \
             patch.object(knowldb, "cached_titles", {}), patch.object(knowldb, "cached_ai_titles", {}):
            knowldb.save(k, "tester", most_recent={})
            assert ID in (knowldb.cached_ai_titles if ai_written else knowldb.cached_titles)
        # the type comes after id, authors, cat, content, last_author, timestamp, title and status
        return saved[0][8]

    def test_save_stores_ai_type(self):
        assert self._saved_type("test.ai", True) == 3
        assert self._saved_type("nf.6.0.21296.1.top", True) == 4
        assert self._saved_type("nf.6.0.21296.1.bottom", True) == 5
        assert self._saved_type("nf.6.0.21296.1.bottom", False) == -1
        with self.assertRaises(ValueError):
            self._saved_type("columns.nf_fields.degree", True)

    def test_show_ai_knowls(self):
        from lmfdb.knowledge.knowl import show_ai_knowls, public_knowls
        # code run outside a request, such as module imports, does not see them by default
        assert not show_ai_knowls()

        @public_knowls()
        def decorated():
            return show_ai_knowls()

        with self.app.test_request_context("/"):
            assert not show_ai_knowls()
            with patch("lmfdb.knowledge.knowl.userdb.can_read_write_userdb", return_value=True), \
                 patch("lmfdb.knowledge.knowl.current_user") as user:
                user.is_authenticated = True
                assert show_ai_knowls()
                with public_knowls():
                    assert not show_ai_knowls()
                assert show_ai_knowls()
                assert not decorated()
                user.is_authenticated = False
                assert not show_ai_knowls()

    def _logged_in(self):
        """
        Patches making the current request look as if it came from a logged-in user.
        """
        user = patch("lmfdb.knowledge.knowl.current_user")
        rw = patch("lmfdb.knowledge.knowl.userdb.can_read_write_userdb", return_value=True)
        return user, rw

    def test_shared_objects_hide_ai(self):
        # Objects kept for the life of the process are built from public knowls only
        from lmfdb.knowledge.knowl import show_ai_knowls
        from lmfdb.utils import StatsDisplay, SearchArray

        class StatsProbe(StatsDisplay):
            def __init__(self):
                self.seen = show_ai_knowls()

        class SearchProbe(SearchArray):
            def __init__(self):
                self.seen = show_ai_knowls()

        user, rw = self._logged_in()
        with self.app.test_request_context("/"), user as current_user, rw:
            current_user.is_authenticated = True
            assert show_ai_knowls()
            assert not StatsProbe().seen
            assert not SearchProbe().seen
            with patch.object(StatsProbe, "_prep", lambda self, attr: show_ai_knowls()):
                assert StatsProbe().prep({}) is False

    def test_display_knowl_outside_request(self):
        # At import time an AI-only knowl looks missing, and there is no current user
        from lmfdb.utils import display_knowl
        assert display_knowl("test.no_such_knowl", "Title") == "Title"

    def test_announcements_box_hides_ai(self):
        from lmfdb.homepage.boxes import Box
        self.real_get_knowl = knowldb.get_knowl

        def get_knowl(ID, fields=None, beta=None, allow_deleted=False, timestamp=None, ai=None):
            assert ID == "content.announcements"
            item = "* AI-written item" if not knowldb._hide_ai(ai) else "* Human item"
            return {"content": item}

        user, rw = self._logged_in()
        with self.app.test_request_context("/"), user as current_user, rw, \
             patch.object(knowldb, "get_knowl", side_effect=get_knowl):
            current_user.is_authenticated = True
            box = Box({"title": "Announcements", "image": "announcements"})
        assert "Human item" in box.content
        assert "AI-written item" not in box.content

    def test_backup_annotation_is_labelled(self):
        self.real_get_knowl = knowldb.get_knowl
        with self.app.test_request_context("/"), \
             patch.object(knowldb, "get_knowl", side_effect=self._get_knowl), \
             patch("lmfdb.knowledge.knowl.show_ai_knowls", return_value=True):
            self.app.preprocess_request()
            html = render_template_string(
                "{% from 'knowl-defs.html' import KNOWL_INC with context %}"
                "{{ KNOWL_INC('test.no_such_knowl.top', title='', backupid='test.ai_written') }}",
                user_is_authenticated=True)
        assert "AI-written content" in html
        assert "AI-written, so only shown to logged-in users" in html

    def test_queries_run_with_and_without_ai(self):
        # The knowl database used for tests has no AI-written knowls, so this
        # checks that the queries are valid either way.
        for ai in [True, False]:
            assert knowldb.get_knowl("nf.degree", beta=True, ai=ai)["id"] == "nf.degree"
            assert knowldb.get_knowl("nf.degree", beta=False, ai=ai)["id"] == "nf.degree"
            timestamp = knowldb.get_knowl("nf.degree", beta=True, ai=ai)["timestamp"]
            assert knowldb.get_knowl("nf.degree", timestamp=timestamp, ai=ai)["id"] == "nf.degree"
            assert knowldb.get_edit_history("nf.degree", ai=ai)
            assert "nf.degree" in [k["id"] for k in knowldb.search(types=["normal", "ai"], keywords="degree", ai=ai)]
            assert "nf.degree" in [k["id"] for k in knowldb.get_all_knowls(["id"], ids=["nf.degree"], ai=ai)]
            assert len(knowldb.get_history(5, ai=ai)) == 5
            for beta in [True, False]:
                assert knowldb.ids_referencing("nf.degree", beta=beta, ai=ai)
            assert knowldb.ids_referencing("nf.degree", old=True, ai=ai)
        # this one is slow
        knowldb.broken_links_knowls(ai=False)
        with self.app.test_request_context("/"):
            self.app.preprocess_request()
            knowldb.stale_knowls()
            knowldb.needs_review(1)

    def _get_knowl(self, ID, fields=None, beta=None, allow_deleted=False, timestamp=None, ai=None):
        """
        A get_knowl in which test.ai_written is an AI-written knowl, and the
        last author of nf.degree wrote it.
        """
        if ID != "test.ai_written":
            return self.real_get_knowl(ID, fields=fields, beta=beta, allow_deleted=allow_deleted, timestamp=timestamp, ai=ai)
        if knowldb._hide_ai(ai):
            return None
        author = self.real_get_knowl("nf.degree", beta=True)["last_author"]
        data = dict(self.ai_data, id=ID, authors=[author], last_author=author, timestamp=utc_now_naive())
        return {f: data.get(f) for f in (fields or data)}

    def _page(self, url, logged_in):
        self.real_get_knowl = knowldb.get_knowl
        with patch.object(knowldb, "get_knowl", side_effect=self._get_knowl), \
             patch("lmfdb.knowledge.knowl.show_ai_knowls", return_value=logged_in), \
             patch("lmfdb.knowledge.main.show_ai_knowls", return_value=logged_in):
            return self.tc.get(url)

    def test_shown_only_when_logged_in(self):
        assert self._page("/knowledge/show/test.ai_written", False).status_code == 404
        for url in ["/knowledge/render/test.ai_written", "/knowledge/content/test.ai_written"]:
            page = self._page(url, False)
            assert "AI-written" not in page.get_data(as_text=True)
            assert "public" in page.headers["Cache-Control"]
        page = self._page("/knowledge/show/test.ai_written", True)
        assert page.status_code == 200
        text = page.get_data(as_text=True)
        assert "AI-written content" in text
        assert "AI-written title (AI-written)" in text
        assert "only shown to logged-in users" in text
        for url in ["/knowledge/render/test.ai_written", "/knowledge/content/test.ai_written"]:
            page = self._page(url, True)
            assert "AI-written content" in page.get_data(as_text=True)
            assert "private" in page.headers["Cache-Control"]

    def _save_form(self, form, ai_written=True):
        r"""
        Post the editor's form for a knowl with title "Title" and content
        "Content", and return what it would have saved.
        """
        saved = []

        class FakeKnowl:
            def __init__(self, ID, **kwds):
                self.id, self.title, self.content, self.type = ID, "Title", "Content", 0
                self.ai_written = ai_written

            def exists(self, allow_deleted=False):
                return True

            def save(self, who):
                saved.append((self.title, self.content, self.ai_written))

        tc = self.app.test_client()
        with tc.session_transaction() as session:
            session["_csrf_token"] = "token"
        data = dict({"id": "test.ai_written", "title": "Title", "content": "Content", "csrf_token": "token"}, **form)
        with patch.dict(self.app.config, LOGIN_DISABLED=True), patch("lmfdb.knowledge.main.Knowl", FakeKnowl):
            assert tc.post("/knowledge/save", data=data).status_code == 302
        return saved

    def test_saving_makes_normal_knowl(self):
        assert self._save_form({}) == [("Title", "Content", False)]
        assert self._save_form({"content": "Changed"}) == [("Title", "Changed", False)]

    def test_saving_can_keep_ai(self):
        assert self._save_form({"keep_ai": "on"}) == []
        assert self._save_form({"content": "Changed", "keep_ai": "on"}) == [("Title", "Changed", True)]
        # the box cannot mark a human-written knowl as AI-written
        assert self._save_form({"content": "Changed", "keep_ai": "on"}, ai_written=False) == [("Title", "Changed", False)]

    def test_edit_page_offers_to_keep_ai(self):
        checkbox = '<input type="checkbox" name="keep_ai" id="keep_ai" value="on" />'
        with patch.dict(self.app.config, LOGIN_DISABLED=True), patch.object(knowldb, "set_locked"):
            assert checkbox in self._page("/knowledge/edit/test.ai_written?lock=ignore", True).get_data(as_text=True)
            assert "keep_ai" not in self._page("/knowledge/edit/nf.degree?lock=ignore", True).get_data(as_text=True)

    def test_type_options(self):
        assert 'name="ai"' not in self._page("/knowledge/", False).get_data(as_text=True)
        text = self._page("/knowledge/", True).get_data(as_text=True)
        assert 'name="ai"' in text
        assert "AI-written top" in text

    def _yaml_import(self, existing, records, **kwds):
        r"""
        Run knowldb.yaml_import on ``records`` with the database mocked out:
        ``existing`` are the current versions.  Returns the knowls it would
        have saved and its output.
        """
        import io
        import os
        import tempfile
        import contextlib
        import yaml
        saved = []

        def fake_save(knowl, who, most_recent=None, minor=False):
            saved.append(knowl)

        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "knowls.yaml")
            with open(filename, "w") as F:
                yaml.safe_dump([{"written": utc_now_naive()}] + records, F)
            out = io.StringIO()
            with patch.object(knowldb, "get_all_knowls", return_value=existing), \
                 patch.object(knowldb, "save", side_effect=fake_save), \
                 contextlib.redirect_stdout(out):
                knowldb.yaml_import(filename, "tester", **kwds)
        return {k.id: k for k in saved}, out.getvalue()

    def test_yaml_import(self):
        old = utc_now_naive().replace(year=2000)
        existing = [dict(self.ai_data, id="test.ai_written", timestamp=old),
                    dict(self.ai_data, id="test.human_written", type=0, status=1, timestamp=old)]
        records = [{"id": "test.ai_written", "title": "AI-written title", "content": "Changed"},
                   {"id": "test.human_written", "title": "AI-written title", "content": "Changed"},
                   {"id": "test.new", "title": "New", "content": "New"},
                   {"id": "columns.nf_fields.degree", "title": "", "content": "Changed"}]
        saved, out = self._yaml_import(existing, records, ai=True, straight_to_production=True)
        assert sorted(saved) == ["test.ai_written", "test.human_written", "test.new"]
        assert all(k.ai_written and k.status == 0 for k in saved.values())
        assert "Cannot mark columns.nf_fields.degree as AI-written" in out
        # without ai, AI-written knowls stay AI-written and new knowls are not
        saved, out = self._yaml_import(existing, records)
        assert saved["test.ai_written"].ai_written
        assert not saved["test.human_written"].ai_written
        assert not saved["test.new"].ai_written
        assert "columns.nf_fields.degree" in saved
