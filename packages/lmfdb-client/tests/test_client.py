"""
Tests for lmfdb-client: the configuration, the lazy ``db`` object, and (in
TestDatabase) the connection to devmirror.lmfdb.xyz.

They run both in plain Python against the installed package (see
.github/workflows/packaging.yml) and in the LMFDB's test suite, under Sage.
"""
import os
import subprocess
import sys
import threading

import pytest

import lmfdb_client
from lmfdb_client import config as config_mod
from lmfdb_client import LazyDatabase


def run_py(code, cwd=None, **env_overrides):
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=cwd
    )


@pytest.fixture
def home(tmp_path, monkeypatch):
    # an isolated LMFDB home directory, with no configuration file in the
    # current directory
    monkeypatch.delenv("LMFDB_CONFIG", raising=False)
    monkeypatch.setenv("LMFDB_HOME", str(tmp_path / "home"))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config_mod, "_current_configuration", None)
    return tmp_path / "home"


class TestFileLocations:
    def test_lmfdb_config_env(self, tmp_path, monkeypatch):
        target = tmp_path / "custom" / "config.ini"
        monkeypatch.setenv("LMFDB_CONFIG", str(target))
        assert config_mod.find_config_file() == str(target)

    def test_home(self, home):
        assert config_mod.lmfdb_home() == str(home)
        assert config_mod.find_config_file() == str(home / "config.ini")

    def test_default_home(self, monkeypatch):
        monkeypatch.delenv("LMFDB_HOME", raising=False)
        assert config_mod.lmfdb_home() == os.path.join(os.path.expanduser("~"), ".lmfdb")

    def test_cwd_config(self, home, tmp_path):
        (tmp_path / "config.ini").write_text("")
        assert config_mod.find_config_file() == str(tmp_path / "config.ini")


class TestConfiguration:
    def test_defaults(self, home):
        conf = config_mod.Configuration()
        assert conf.config_file == str(home / "config.ini")
        assert conf.secrets_file == str(home / "secrets.ini")
        assert (home / "config.ini").exists()
        pg = conf.options["postgresql"]
        assert pg["host"] == "devmirror.lmfdb.xyz"
        assert pg["user"] == "lmfdb"
        # the TCP keepalives on the database connection survive the defaults
        assert int(pg["keepalives"]) == 1
        assert conf.get_postgresql()["host"] == "devmirror.lmfdb.xyz"
        # nothing is slow for interactive use, and the log is in the home directory
        assert conf.logging_options["slowcutoff"] == float("inf")
        assert conf.logging_options["slowlogfile"] == str(home / "logs" / "slow_queries.log")
        assert (home / "logs").is_dir()

    def test_file_is_read(self, home):
        home.mkdir()
        (home / "config.ini").write_text("[postgresql]\nhost = example.org\n[logging]\nslowcutoff = 0.5\n")
        conf = config_mod.Configuration()
        assert conf.postgresql_options["host"] == "example.org"
        assert conf.logging_options["slowcutoff"] == 0.5
        # options missing from the file get their default values
        assert conf.postgresql_options["dbname"] == "lmfdb"

    def test_website_sections_are_ignored(self, home):
        # the LMFDB website's configuration file has more sections, which
        # the client can read
        home.mkdir()
        (home / "config.ini").write_text("[web]\nport = 37777\n[core]\ndebug = False\n[postgresql]\nuser = webserver\n")
        conf = config_mod.Configuration()
        assert conf.postgresql_options["user"] == "webserver"

    def test_secrets_override(self, home):
        home.mkdir()
        (home / "config.ini").write_text("[postgresql]\nuser = lmfdb\npassword = lmfdb\n")
        (home / "secrets.ini").write_text("[postgresql]\nuser = editor\npassword = hunter2\n")
        conf = config_mod.Configuration()
        assert conf.postgresql_options["user"] == "editor"
        assert conf.postgresql_options["password"] == "hunter2"

    def test_command_line(self, home, tmp_path, monkeypatch):
        cfg = tmp_path / "elsewhere" / "config.ini"
        secrets = tmp_path / "secret" / "secrets.ini"
        monkeypatch.setattr(sys, "argv", [
            "script", "--config-file", str(cfg), "--secrets-file", str(secrets),
            "--postgresql-host", "localhost", "--slowcutoff", "2",
        ])
        conf = config_mod.Configuration(readargs=True)
        assert conf.config_file == str(cfg)
        assert conf.secrets_file == str(secrets)
        assert conf.postgresql_options["host"] == "localhost"
        assert conf.logging_options["slowcutoff"] == 2

    def test_command_line_ignored_by_default(self, home, monkeypatch):
        # a library must not parse the command line of the program using it
        monkeypatch.setattr(sys, "argv", ["script", "--unrelated-option"])
        conf = config_mod.Configuration()
        assert conf.postgresql_options["host"] == "devmirror.lmfdb.xyz"

    def test_current_configuration(self, home):
        # creating a Configuration does not change the process-wide one;
        # only set_current_configuration (or first use) does
        first = config_mod.Configuration()
        assert config_mod._current_configuration is None
        config_mod.set_current_configuration(first)
        config_mod.set_current_configuration(first)  # no-op
        assert config_mod.current_configuration() is first
        with pytest.raises(RuntimeError):
            config_mod.set_current_configuration(config_mod.Configuration())

    def test_default_current_configuration(self, home):
        conf = config_mod.current_configuration()
        assert isinstance(conf, config_mod.Configuration)
        assert config_mod.current_configuration() is conf

    def test_subclass_hooks(self, home, tmp_path):
        # how the LMFDB website adds its own options and file locations
        class WebsiteConfiguration(config_mod.Configuration):
            def default_config_file(self):
                return str(tmp_path / "site" / "config.ini")

            def log_dir(self):
                return str(tmp_path / "site" / "logs")

            def add_general_arguments(self, parser):
                super().add_general_arguments(parser)
                parser.add_argument("--port", dest="web_port", type=int, default=37777)

        conf = WebsiteConfiguration()
        assert conf.config_file == str(tmp_path / "site" / "config.ini")
        assert conf.options["web"]["port"] == 37777
        assert conf.logging_options["slowlogfile"] == str(tmp_path / "site" / "logs" / "slow_queries.log")
        assert not home.exists()


class TestLazyDb:
    def test_import_is_light_and_creates_no_files(self, tmp_path):
        # run from an empty directory: importing and introspecting must not
        # import the database stack, connect, or create any file
        r = run_py(
            "import sys, os, lmfdb_client, lmf\n"
            "assert 'psycodict' not in sys.modules\n"
            "assert not any(m == 'sage' or m.startswith('sage.') for m in sys.modules)\n"
            "from lmfdb_client import db\n"
            "repr(db); bool(db); dir(db)\n"
            "assert db.connected is False\n"
            "assert lmf.db is db\n"
            "assert 'psycodict' not in sys.modules\n"
            "assert not os.listdir('.')\n",
            cwd=str(tmp_path),
            LMFDB_HOME=str(tmp_path / "home"),
            LMFDB_CONFIG="",
        )
        assert r.returncode == 0, r.stderr
        assert not any(tmp_path.iterdir()), "files were created by import/introspection"

    def test_factory_called_exactly_once(self):
        calls = []

        def factory(config=None, **kwargs):
            calls.append((config, kwargs))
            return object()

        d = LazyDatabase(factory)
        assert not d.connected
        first = d.connect()
        second = d.connect()
        assert first is second
        assert len(calls) == 1
        assert d.connected

    def test_factory_called_once_concurrently(self):
        barrier = threading.Barrier(8)
        calls = []

        def factory(config=None, **kwargs):
            calls.append(1)
            return object()

        d = LazyDatabase(factory)
        results = []

        def worker():
            barrier.wait()
            results.append(d.connect())

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(calls) == 1
        assert len(set(map(id, results))) == 1

    def test_config_reaches_factory(self):
        received = []

        def factory(config=None, **kwargs):
            received.append((config, kwargs))
            return object()

        d = LazyDatabase(factory)
        d.connect({"postgresql_options": {}}, dbname="other")
        assert received == [({"postgresql_options": {}}, {"dbname": "other"})]
        with pytest.raises(RuntimeError):
            d.connect(config={"postgresql_options": {}})

    def test_forwarding(self):
        class Fake:
            tablenames = ["nf_fields"]

            def __getitem__(self, name):
                return "table " + name

        d = LazyDatabase(lambda config=None: Fake())
        assert d.tablenames == ["nf_fields"]
        assert d["nf_fields"] == "table nf_fields"
        d.extra = 1
        assert d.connect().extra == 1
        assert "tablenames" in dir(d)

    def test_missing_dependency_message(self, tmp_path):
        # with psycodict missing, importing and introspecting still works;
        # the first real use gives a single error explaining what to do
        code = (
            "import sys\n"
            "class Blocker:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name.split('.')[0] == 'psycodict':\n"
            "            raise ModuleNotFoundError('psycodict blocked for testing', name='psycodict')\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "import lmfdb_client, pydoc\n"
            "pydoc.render_doc(lmfdb_client)\n"
            "from lmfdb_client import db\n"
            "repr(db); bool(db); dir(db)\n"
            "try:\n"
            "    db.tablenames\n"
            "except ModuleNotFoundError as e:\n"
            "    assert 'pip install lmfdb-client' in str(e), e\n"
            "else:\n"
            "    raise SystemExit('expected a ModuleNotFoundError')\n"
        )
        r = run_py(code, cwd=str(tmp_path), LMFDB_HOME=str(tmp_path), LMFDB_CONFIG="")
        assert r.returncode == 0, r.stderr + r.stdout

    def test_unrelated_import_error_not_masked(self):
        # an import failure that is not a missing database dependency must
        # propagate untouched rather than being relabeled
        def factory(config=None):
            raise ModuleNotFoundError("broken internal module", name="lmfdb_client.broken")

        d = LazyDatabase(factory)
        with pytest.raises(ModuleNotFoundError, match="broken internal module"):
            d.connect()
        assert not d.connected


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    # a connection to devmirror.lmfdb.xyz with the default settings, but
    # its files in a temporary directory
    home = tmp_path_factory.mktemp("home")
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("LMFDB_HOME", str(home))
        mp.delenv("LMFDB_CONFIG", raising=False)
        mp.chdir(home)
        conf = config_mod.Configuration()
    from lmfdb_client.database import LMFDBDatabase
    db = LMFDBDatabase(conf)
    yield db
    db.conn.close()


class TestDatabase:
    """
    These tests connect to devmirror.lmfdb.xyz, the default database.
    """
    def test_types(self, db):
        # numeric columns give plain Python types in plain Python, and Sage
        # types in Sage; other columns (degree is a smallint) give Python
        # types either way
        from psycodict.encoding import SAGE_MODE
        rec = db.nf_fields.lookup("2.2.5.1", ["degree", "disc_abs", "regulator", "coeffs"])
        assert rec["degree"] == 2 and rec["disc_abs"] == 5
        assert rec["coeffs"] == [-1, -1, 1]
        assert abs(rec["regulator"] - 0.4812118250596) < 1e-10
        assert type(rec["degree"]) is int
        if SAGE_MODE:
            from sage.rings.integer import Integer
            from sage.rings.real_mpfr import RealNumber
            assert isinstance(rec["disc_abs"], Integer)
            assert isinstance(rec["regulator"], RealNumber)
            assert all(isinstance(c, Integer) for c in rec["coeffs"])
        else:
            assert type(rec["disc_abs"]) is int
            assert type(rec["regulator"]) is float

    def test_lmfdb_classes(self, db):
        from lmfdb_client.database import LMFDBSearchTable
        assert isinstance(db.nf_fields, LMFDBSearchTable)
        assert "nf_fields" in db.tablenames

    def test_descriptions(self, db):
        descriptions = db.nf_fields.column_description()
        assert "degree" in descriptions
        assert descriptions["degree"] == db.nf_fields.column_description("degree")
        assert isinstance(db.nf_fields.description(), str)
        with pytest.raises(NotImplementedError):
            db.nf_fields.description("New description")
        with pytest.raises(NotImplementedError):
            db.nf_fields.column_description("degree", "New description")

    def test_data_changes_need_editor(self, db):
        with pytest.raises(RuntimeError, match="editor"):
            db.nf_fields._check_locks("update")

    def test_independent_of_the_website(self, tmp_path):
        # the client must not need anything else from the LMFDB repository
        # (checked in a fresh process: in the LMFDB's test suite, other tests
        # may have imported the website already)
        r = run_py(
            "import sys\n"
            "from lmfdb_client import db\n"
            "db.nf_fields.lookup('2.2.5.1')\n"
            "db.nf_fields.column_description('degree')\n"
            "bad = [m for m in sys.modules if m.split('.')[0] in ('lmfdb', 'lmfdb_utils')]\n"
            "assert not bad, bad\n",
            cwd=str(tmp_path),
            LMFDB_HOME=str(tmp_path / "home"),
            LMFDB_CONFIG="",
        )
        assert r.returncode == 0, r.stderr


def test_version():
    assert lmfdb_client.__version__
