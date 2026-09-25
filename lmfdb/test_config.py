"""
Tests for lmfdb.config, the lazy ``lmfdb.db`` object, and the command-line
entry point.

These tests need neither sage, nor flask, nor a database connection, so
they run in the regular test suite from a checkout and are also exercised
against the installed package by the packaging workflow
(.github/workflows/packaging.yml).
"""
import os
import stat
import subprocess
import sys
import threading

import pytest

from lmfdb import config as config_mod
from lmfdb import _lazy_database as lazy_mod


def run_py(code, cwd=None, **env_overrides):
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=cwd
    )


class TestFileLocations:
    def test_lmfdb_config_env(self, tmp_path, monkeypatch):
        target = tmp_path / "custom" / "config.ini"
        monkeypatch.setenv("LMFDB_CONFIG", str(target))
        assert config_mod.find_config_file() == str(target)

    def test_home_fallback(self, tmp_path, monkeypatch):
        # in installed mode (no checkout), files go to the LMFDB home directory
        monkeypatch.delenv("LMFDB_CONFIG", raising=False)
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setattr(config_mod, "root_lmfdb_path", None)
        monkeypatch.chdir(tmp_path)  # a directory without a config.ini
        assert config_mod.lmfdb_home() == str(tmp_path)
        assert config_mod.lmfdb_log_dir() == str(tmp_path / "logs")
        assert config_mod.find_config_file() == str(tmp_path / "config.ini")

    def test_cwd_config_used_when_installed(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LMFDB_CONFIG", raising=False)
        monkeypatch.setattr(config_mod, "root_lmfdb_path", None)
        (tmp_path / "config.ini").write_text("")
        monkeypatch.chdir(tmp_path)
        assert config_mod.find_config_file() == str(tmp_path / "config.ini")

    def test_checkout_ignores_cwd_config(self, tmp_path, monkeypatch):
        # a checkout keeps its configuration at its root, wherever it is run from
        if config_mod.root_lmfdb_path is None:
            pytest.skip("only applies when running from a checkout")
        monkeypatch.delenv("LMFDB_CONFIG", raising=False)
        monkeypatch.delenv("LMFDB_HOME", raising=False)
        (tmp_path / "config.ini").write_text("")
        monkeypatch.chdir(tmp_path)
        assert config_mod.find_config_file() == os.path.join(
            config_mod.root_lmfdb_path, "config.ini"
        )


class TestSecretKey:
    def test_created_next_to_config_file(self, tmp_path):
        cfg = tmp_path / "config.ini"
        key = config_mod.get_secret_key(str(cfg))
        keyfile = tmp_path / "secret_key"
        assert keyfile.exists()
        assert len(key) == 32
        # a second read returns the stored key
        assert config_mod.get_secret_key(str(cfg)) == key
        # readable only by the owner
        mode = stat.S_IMODE(os.stat(keyfile).st_mode)
        assert mode == 0o600

    def test_concurrent_creation_yields_one_key(self, tmp_path):
        # Concurrent workers must all end up with the same complete key.
        # Repeated, because the window in which a reader could observe a
        # created-but-not-yet-written file is small.
        for i in range(20):
            directory = tmp_path / ("run%d" % i)
            directory.mkdir()
            cfg = str(directory / "config.ini")
            barrier = threading.Barrier(8)
            keys = []

            def worker():
                barrier.wait()
                keys.append(config_mod.get_secret_key(cfg))

            threads = [threading.Thread(target=worker) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert all(len(k) == 32 for k in keys), "a worker read an incomplete key: %r" % keys
            assert len(set(keys)) == 1, keys

    def test_concurrent_creation_across_processes(self, tmp_path):
        # the same race between separate processes, as when several
        # gunicorn workers start at once
        cfg = str(tmp_path / "config.ini")
        code = (
            "import sys\n"
            "from lmfdb.config import get_secret_key\n"
            "sys.stdout.write(get_secret_key(%r))\n" % cfg
        )
        procs = [
            subprocess.Popen(
                [sys.executable, "-c", code], stdout=subprocess.PIPE, text=True
            )
            for _ in range(6)
        ]
        keys = [p.communicate()[0] for p in procs]
        assert all(p.returncode == 0 for p in procs)
        assert all(len(k) == 32 for k in keys), "a process read an incomplete key: %r" % keys
        assert len(set(keys)) == 1, keys


class TestConfiguration:
    def test_records_config_and_secrets_files(self, tmp_path, monkeypatch):
        target = tmp_path / "config.ini"
        monkeypatch.setenv("LMFDB_CONFIG", str(target))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        conf = config_mod.Configuration()
        assert conf.config_file == str(target)
        assert conf.secrets_file == str(tmp_path / "secrets.ini")
        assert target.exists()
        conf.get_secret_key()
        assert (tmp_path / "secret_key").exists()
        # the TCP keepalives on the database connection survive the defaults
        assert int(conf.options["postgresql"]["keepalives"]) == 1

    def test_config_file_option_moves_everything(self, tmp_path, monkeypatch):
        # what lmfdb.cli does: parse the command line into a Configuration,
        # which becomes the process-wide one used for the flask secret key,
        # logging, and the database
        cfg = tmp_path / "elsewhere" / "config.ini"
        cfg.parent.mkdir()
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        monkeypatch.setattr(
            sys, "argv", ["lmfdb", "--config-file", str(cfg), "--debug"]
        )
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        conf = config_mod.Configuration(readargs=True)
        assert conf.config_file == str(cfg)
        assert conf.secrets_file == str(cfg.parent / "secrets.ini")
        assert config_mod.current_configuration() is conf
        conf.get_secret_key()
        assert (cfg.parent / "secret_key").exists()

    def test_first_configuration_becomes_current(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LMFDB_CONFIG", str(tmp_path / "config.ini"))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        first = config_mod.Configuration()
        second = config_mod.Configuration()
        assert config_mod.current_configuration() is first
        assert config_mod.current_configuration() is not second


class TestLazyDb:
    def test_import_lmfdb_is_light_and_creates_no_files(self, tmp_path):
        # run from an empty directory: importing and introspecting must not
        # import the database stack, connect, or create any file
        r = run_py(
            "import sys, os, lmfdb\n"
            "assert 'lmfdb.lmfdb_database' not in sys.modules\n"
            "assert 'psycodict' not in sys.modules\n"
            "assert 'flask' not in sys.modules\n"
            "assert not any(m == 'sage' or m.startswith('sage.') for m in sys.modules)\n"
            "from lmfdb import db\n"
            "repr(db); bool(db); dir(db)\n"
            "assert db.connected is False\n"
            "assert 'db' in dir(lmfdb)\n"
            "assert 'lmfdb.lmfdb_database' not in sys.modules\n"
            "assert 'psycodict' not in sys.modules\n"
            "assert not os.listdir('.')\n",
            cwd=str(tmp_path),
            LMFDB_HOME=str(tmp_path / "home"),
            LMFDB_CONFIG=str(tmp_path / "home" / "config.ini"),
        )
        assert r.returncode == 0, r.stderr
        assert not any(tmp_path.iterdir()), "files were created by import/introspection"

    def test_factory_called_exactly_once(self, monkeypatch):
        calls = []

        def fake_factory(config=None, **kwargs):
            calls.append((config, kwargs))
            return object()

        monkeypatch.setattr(lazy_mod, "_make_database", fake_factory)
        d = lazy_mod.LazyDatabase()
        assert not d.connected
        first = d.connect()
        second = d.connect()
        assert first is second
        assert len(calls) == 1
        assert d.connected

    def test_factory_called_once_concurrently(self, monkeypatch):
        barrier = threading.Barrier(8)
        calls = []

        def fake_factory(config=None, **kwargs):
            calls.append(1)
            return object()

        monkeypatch.setattr(lazy_mod, "_make_database", fake_factory)
        d = lazy_mod.LazyDatabase()
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

    def test_second_connect_with_config_raises(self, monkeypatch):
        monkeypatch.setattr(lazy_mod, "_make_database", lambda config=None, **k: object())
        d = lazy_mod.LazyDatabase()
        d.connect()
        with pytest.raises(RuntimeError):
            d.connect(config={"postgresql_options": {}})

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
            "import lmfdb\n"
            "import pydoc\n"
            "pydoc.render_doc(lmfdb)\n"
            "from lmfdb import db\n"
            "repr(db); bool(db); dir(db)\n"
            "assert not db.connected\n"
            "try:\n"
            "    db.tablenames\n"
            "except ModuleNotFoundError as e:\n"
            "    assert 'sage -pip install' in str(e), e\n"
            "else:\n"
            "    raise SystemExit('expected a ModuleNotFoundError')\n"
        )
        r = run_py(
            code,
            LMFDB_HOME=str(tmp_path),
            LMFDB_CONFIG=str(tmp_path / "config.ini"),
        )
        assert r.returncode == 0, r.stderr + r.stdout

    def test_unrelated_import_error_not_masked(self, tmp_path):
        # an import failure that is not a missing database dependency must
        # propagate untouched rather than being relabeled
        code = (
            "import sys\n"
            "class Blocker:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name == 'lmfdb.config':\n"
            "            raise ModuleNotFoundError('broken internal module', name='lmfdb.config')\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "from lmfdb import db\n"
            "try:\n"
            "    db.tablenames\n"
            "except ModuleNotFoundError as e:\n"
            "    assert 'sage -pip install' not in str(e), 'internal error was masked: %s' % e\n"
            "else:\n"
            "    raise SystemExit('expected a ModuleNotFoundError')\n"
        )
        r = run_py(code)
        assert r.returncode == 0, r.stderr + r.stdout


class TestCommandLine:
    def test_help_is_fast_and_clean(self, tmp_path):
        # --help is handled before the website (or sage) is imported, and
        # creates no files
        env = dict(os.environ)
        env["LMFDB_HOME"] = str(tmp_path / "home")
        env["LMFDB_CONFIG"] = str(tmp_path / "home" / "config.ini")
        r = subprocess.run(
            [sys.executable, "-m", "lmfdb", "--help"],
            capture_output=True, text=True, env=env, cwd=str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        assert "--config-file" in r.stdout
        assert "--postgresql-host" in r.stdout
        assert not any(tmp_path.iterdir()), "files were created by --help"


class TestUtilsConfigShim:
    def test_shim_reexports(self):
        # the historical module keeps working (it needs the full website
        # dependencies, so this is skipped in a bare environment)
        try:
            from lmfdb.utils import config as shim
        except ImportError as e:
            pytest.skip("lmfdb.utils is unavailable here (%s)" % e)
        assert shim.Configuration is config_mod.Configuration
        assert shim.ConfigWrapper is config_mod.ConfigWrapper
        assert shim.get_secret_key is config_mod.get_secret_key
        assert shim.abs_path_lmfdb is config_mod.abs_path_lmfdb
        assert shim.root_lmfdb_path == config_mod.root_lmfdb_path
        # COCALC_port is forwarded dynamically, so reads see the current value
        assert shim.COCALC_port == config_mod.COCALC_port
