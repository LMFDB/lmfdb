# Tests for the knowledge (knowl) blueprint.

from lmfdb.tests import LmfdbTest
from lmfdb.knowledge import main as knowl_main


class KnowlUIVisibilityTest(LmfdbTest):
    """
    Issue #3721: knowls whose id starts with ``ui.`` are user-interface helper
    texts (search-box help, sort-order and statistics-extent explanations, ...)
    rather than context-free definitions.  They must be hidden from the public
    (logged-out) knowl browse/search index, together with their ``ui`` category.
    """

    # Stand-in for a knowldb.search() response: one ui. helper and one ordinary
    # (context-free) math-definition knowl.
    _fake_knowls = [
        {"id": "ui.demo_helper", "title": "Demo UI helper"},
        {"id": "ec.q.conductor", "title": "Conductor of an elliptic curve"},
    ]

    def _get_index(self):
        """Render /knowledge/ with knowldb.search patched to return _fake_knowls."""
        knowl_main.knowldb.search = lambda *args, **kwargs: [dict(k) for k in self._fake_knowls]
        try:
            return self.tc.get("/knowledge/", follow_redirects=True).get_data(as_text=True)
        finally:
            # Remove the instance override, restoring the real bound method.
            del knowl_main.knowldb.search

    def test_index_page_loads(self):
        # Regression: the public knowl index still renders.
        page = self.tc.get("/knowledge/", follow_redirects=True).get_data(as_text=True)
        assert "Knowledge database" in page

    def test_ui_knowl_hidden_when_logged_out(self):
        page = self._get_index()
        # The ui. helper and its "ui" category are hidden from a logged-out user ...
        assert "ui.demo_helper" not in page
        assert "ui(1)" not in page
        # ... while ordinary knowls and their categories remain visible.
        assert "ec.q.conductor" in page
        assert "ec(1)" in page

    def test_ui_category_query_hidden_when_logged_out(self):
        # Explicitly requesting ?category=ui must not surface an empty "ui" category.
        knowl_main.knowldb.search = lambda *args, **kwargs: [dict(k) for k in self._fake_knowls]
        try:
            page = self.tc.get("/knowledge/?category=ui", follow_redirects=True).get_data(as_text=True)
        finally:
            del knowl_main.knowldb.search
        assert "ui.demo_helper" not in page
        assert "ui(0)" not in page
        assert "ui(1)" not in page

    def test_ui_knowl_visible_when_logged_in(self):
        # When authenticated, the filter is skipped and ui. knowls are listed.
        class _FakeUser:
            is_authenticated = True

            def is_admin(self):
                return False

        orig_user = knowl_main.current_user
        knowl_main.current_user = _FakeUser()
        knowl_main.knowldb.search = lambda *args, **kwargs: [dict(k) for k in self._fake_knowls]
        try:
            page = self.tc.get("/knowledge/", follow_redirects=True).get_data(as_text=True)
        finally:
            knowl_main.current_user = orig_user
            del knowl_main.knowldb.search
        assert "ui.demo_helper" in page
        assert "ec.q.conductor" in page
