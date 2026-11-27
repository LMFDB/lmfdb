"""
Tests for lmfdb-utils on its own, without the LMFDB website.

The LMFDB's test suite exercises the utilities through the website; these
tests check that they work without it.  Most modules require Sage; without
it (as in .github/workflows/packaging.yml) only the others are tested.
"""
import importlib.util
import os
import pkgutil
import subprocess
import sys

import pytest

import lmfdb_utils
from lmfdb_utils import site as site_mod

HAVE_SAGE = importlib.util.find_spec("sage") is not None
needs_sage = pytest.mark.skipif(not HAVE_SAGE, reason="requires Sage")

# The modules that work without Sage
SAGE_FREE = {"color", "common_regex", "csrf", "datetime_utils", "random_wrap", "site"}

MODULES = sorted(m.name for m in pkgutil.iter_modules(lmfdb_utils.__path__))


def run_py(code):
    # run in a directory unrelated to any checkout, so that the lmfdb
    # package of an LMFDB checkout cannot be imported by accident
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        cwd=os.path.dirname(os.path.abspath(lmfdb_utils.__file__)) + "/..",
    )


@pytest.mark.parametrize("module", MODULES)
def test_independent_of_the_lmfdb(module):
    # nothing in lmfdb-utils may import the LMFDB website: what it needs
    # from a website goes through lmfdb_utils.site
    if module not in SAGE_FREE and not HAVE_SAGE:
        pytest.skip("requires Sage")
    r = run_py(
        "import sys\n"
        "class Blocker:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'lmfdb' or name.startswith('lmfdb.'):\n"
        "            raise ImportError('lmfdb_utils imported ' + name)\n"
        "sys.meta_path.insert(0, Blocker())\n"
        "import lmfdb_utils." + module + "\n"
    )
    assert r.returncode == 0, r.stderr


def test_no_lmfdb_imports_anywhere():
    # the same, for imports inside functions, which only run when called
    import re
    pattern = re.compile(r"^\s*(from|import)\s+lmfdb(\.|\s|$)", re.M)
    package_dir = os.path.dirname(os.path.abspath(lmfdb_utils.__file__))
    for filename in os.listdir(package_dir):
        if filename.endswith(".py"):
            with open(os.path.join(package_dir, filename)) as F:
                assert not pattern.search(F.read()), "%s imports from lmfdb" % filename


def test_package_and_site_are_light():
    # the website installs its Site when it is imported, so lmfdb_utils.site
    # must not import flask or sage
    r = run_py(
        "import sys\n"
        "import lmfdb_utils.site\n"
        "assert 'flask' not in sys.modules\n"
        "assert not any(m == 'sage' or m.startswith('sage.') for m in sys.modules)\n"
    )
    assert r.returncode == 0, r.stderr


@pytest.fixture
def site():
    # restore the installed site afterward
    old = site_mod.current_site()
    yield
    site_mod.set_current_site(old)


def test_default_site(site):
    site_mod.set_current_site(site_mod.Site())
    s = site_mod.current_site()
    assert s.knowl_title("any.knowl") is None
    assert s.knowl_create_url("any.knowl") is None
    assert s.all_knowls() == {}
    assert s.results_complete("table", {}, None) == (None, None, None)
    assert "longer than expected" in s.query_timeout_message()


@pytest.fixture
def app():
    flask = pytest.importorskip("flask")
    app = flask.Flask(__name__)
    app.secret_key = "test"
    with app.test_request_context("/"):
        yield app


@needs_sage
def test_display_knowl(site, app):
    from lmfdb_utils.web_display import display_knowl

    class KnowlSite(site_mod.Site):
        def knowl_title(self, kid):
            return {"nf.degree": "degree"}.get(kid)

        def knowl_create_url(self, kid):
            return "/create/" + kid

    site_mod.set_current_site(site_mod.Site())
    assert display_knowl("nf.degree", "Degree") == "Degree"
    site_mod.set_current_site(KnowlSite())
    assert display_knowl("nf.degree", "Degree") == '<a title="degree [nf.degree]" knowl="nf.degree" kwargs="">Degree</a>'
    assert 'href="/create/nf.missing"' in display_knowl("nf.missing", "Missing")


@needs_sage
def test_code_snippet_knowl(site, app):
    from lmfdb_utils.utilities import code_snippet_knowl
    D = {"filename": "site/main.py", "code": ["x = 1"], "lines": [3]}
    site_mod.set_current_site(site_mod.Site())
    assert "on Github" not in code_snippet_knowl(D)

    class SourceSite(site_mod.Site):
        def source_url(self, filename):
            return "https://example.org/" + filename

    site_mod.set_current_site(SourceSite())
    assert "https://example.org/site/main.py#L3" in code_snippet_knowl(D)


@needs_sage
def test_search_parsing(app):
    from lmfdb_utils.search_parsing import parse_ints, parse_floats
    info = {"degree": "2-4", "regulator": "0.5-1"}
    query = {}
    parse_ints(info, query, "degree")
    parse_floats(info, query, "regulator")
    assert query["degree"] == {"$gte": 2, "$lte": 4}
    assert set(query["regulator"]) == {"$gte", "$lte"}


def test_csrf(app):
    from flask import session
    from lmfdb_utils.csrf import csrf_token
    token = csrf_token()
    assert token == session["_csrf_token"] == csrf_token()


def test_version():
    assert lmfdb_utils.__version__
