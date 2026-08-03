"""
Tests for lmfdb.config and the lazy ``lmfdb.db`` object.

These tests need neither sage, nor flask, nor a database connection, so
they run in the regular test suite from a checkout and are also exercised
against the installed package by the packaging workflow
(.github/workflows/packaging.yml).
"""
import os
import subprocess
import sys

import pytest

from lmfdb import config as config_mod


def run_py(code, **env_overrides):
    env = dict(os.environ)
    env.update(env_overrides)
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env
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
        assert (tmp_path / "secret_key").exists()
        assert len(key) == 32
        # a second read returns the stored key
        assert config_mod.get_secret_key(str(cfg)) == key

    def test_follows_config_file_option(self, tmp_path, monkeypatch):
        # --config-file moves the secret key together with the configuration
        cfg = tmp_path / "elsewhere" / "config.ini"
        cfg.parent.mkdir()
        monkeypatch.setattr(config_mod, "_started_as_website", lambda: True)
        monkeypatch.setattr(
            sys, "argv", ["lmfdb", "--config-file", str(cfg), "--debug"]
        )
        config_mod.get_secret_key()
        assert (cfg.parent / "secret_key").exists()

    def test_configuration_records_config_file(self, tmp_path, monkeypatch):
        target = tmp_path / "config.ini"
        monkeypatch.setenv("LMFDB_CONFIG", str(target))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        conf = config_mod.Configuration()
        assert conf.config_file == str(target)
        assert target.exists()
        conf.get_secret_key()
        assert (tmp_path / "secret_key").exists()
        # the TCP keepalives on the database connection survive the defaults
        assert int(conf.options["postgresql"]["keepalives"]) == 1


class TestLazyDb:
    def test_import_lmfdb_is_light(self):
        r = run_py(
            "import sys, lmfdb\n"
            "assert 'lmfdb.lmfdb_database' not in sys.modules\n"
            "assert 'psycodict' not in sys.modules\n"
            "assert 'flask' not in sys.modules\n"
            "assert not any(m == 'sage' or m.startswith('sage.') for m in sys.modules)\n"
        )
        assert r.returncode == 0, r.stderr

    def test_db_does_not_connect(self, tmp_path):
        # no flask, and no connection; sage is not asserted about, since
        # psycodict itself enables its sage mode where sage is available
        r = run_py(
            "import sys\n"
            "from lmfdb import db\n"
            "assert db.connected is False\n"
            "assert bool(db) is True\n"
            "assert 'not yet connected' in repr(db)\n"
            "import lmfdb\n"
            "assert 'db' in dir(lmfdb)\n"
            "assert lmfdb.db is db\n"
            "assert 'flask' not in sys.modules\n",
            LMFDB_HOME=str(tmp_path),
            LMFDB_CONFIG=str(tmp_path / "config.ini"),
        )
        assert r.returncode == 0, r.stderr

    def test_missing_dependency_message(self, tmp_path):
        # with a dependency missing, help(lmfdb) still works and lmfdb.db
        # gives a single error explaining what to do
        code = (
            "import sys\n"
            "class Blocker:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name.split('.')[0] == 'psycodict':\n"
            "            raise ImportError('psycodict blocked for testing')\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "import lmfdb\n"
            "import pydoc\n"
            "pydoc.render_doc(lmfdb)\n"
            "try:\n"
            "    lmfdb.db\n"
            "except AttributeError as e:\n"
            "    assert 'sage -pip install' in str(e), e\n"
            "else:\n"
            "    raise SystemExit('expected an AttributeError')\n"
        )
        r = run_py(
            code,
            LMFDB_HOME=str(tmp_path),
            LMFDB_CONFIG=str(tmp_path / "config.ini"),
        )
        assert r.returncode == 0, r.stderr + r.stdout


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
