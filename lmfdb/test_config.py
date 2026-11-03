"""
Tests for lmfdb.config, the lazy ``lmfdb.db`` object, and the command-line
entry point.

These tests need neither sage, nor flask, nor a database connection.  The
configuration and the lazy database object are built on lmfdb-client, which
has its own tests in packages/lmfdb-client/tests.
"""
import importlib.util
import os
import stat
import subprocess
import sys
import threading

import pytest

import lmfdb_client.config
from lmfdb import config as config_mod


def subprocess_env(**env_overrides):
    # the checkout is importable from any directory
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [config_mod.root_lmfdb_path] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    )
    env.update(env_overrides)
    return env


def run_py(code, cwd=None, **env_overrides):
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env=subprocess_env(**env_overrides), cwd=cwd,
    )


class TestFileLocations:
    def test_lmfdb_config_env(self, tmp_path, monkeypatch):
        target = tmp_path / "custom" / "config.ini"
        monkeypatch.setenv("LMFDB_CONFIG", str(target))
        assert config_mod.find_config_file() == str(target)

    def test_lmfdb_home_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LMFDB_CONFIG", raising=False)
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        assert config_mod.lmfdb_home() == str(tmp_path)
        assert config_mod.lmfdb_log_dir() == str(tmp_path / "logs")
        assert config_mod.find_config_file() == str(tmp_path / "config.ini")

    def test_checkout_ignores_cwd_config(self, tmp_path, monkeypatch):
        # the website keeps its configuration at the root of the checkout,
        # wherever it is run from
        monkeypatch.delenv("LMFDB_CONFIG", raising=False)
        monkeypatch.delenv("LMFDB_HOME", raising=False)
        (tmp_path / "config.ini").write_text("")
        monkeypatch.chdir(tmp_path)
        assert config_mod.lmfdb_home() == config_mod.root_lmfdb_path
        assert config_mod.find_config_file() == os.path.join(
            config_mod.root_lmfdb_path, "config.ini"
        )
        assert os.path.exists(os.path.join(config_mod.root_lmfdb_path, "start-lmfdb.py"))


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

    def test_extends_client_configuration(self, tmp_path, monkeypatch):
        # the website's configuration is lmfdb-client's, with the website's
        # options and defaults added
        monkeypatch.setenv("LMFDB_CONFIG", str(tmp_path / "config.ini"))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        conf = config_mod.Configuration()
        assert isinstance(conf, lmfdb_client.config.Configuration)
        assert conf.postgresql_options["host"] == "devmirror.lmfdb.xyz"
        assert conf.get_flask()["port"] == 37777
        logging = conf.get_logging()
        assert logging["slowcutoff"] == 0.1
        assert logging["logfile"] == str(tmp_path / "logs" / "flasklog")
        assert logging["slowlogfile"] == str(tmp_path / "logs" / "slow_queries.log")
        assert conf.config_file == str(tmp_path / "config.ini")
        # and lmfdb-client can read the website's configuration file
        client = lmfdb_client.config.Configuration()
        assert client.config_file == conf.config_file
        assert client.postgresql_options == conf.postgresql_options

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
        config_mod.set_current_configuration(conf)
        assert conf.config_file == str(cfg)
        assert conf.secrets_file == str(cfg.parent / "secrets.ini")
        assert config_mod.current_configuration() is conf
        conf.get_secret_key()
        assert (cfg.parent / "secret_key").exists()

    def test_secrets_file_option(self, tmp_path, monkeypatch):
        cfg = tmp_path / "config.ini"
        secrets = tmp_path / "elsewhere" / "secrets.ini"
        monkeypatch.setattr(
            sys, "argv", ["lmfdb", "--config-file", str(cfg), "--secrets-file", str(secrets)]
        )
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        conf = config_mod.Configuration(readargs=True)
        assert conf.config_file == str(cfg)
        assert conf.secrets_file == str(secrets)

    def test_explicit_current_configuration(self, tmp_path, monkeypatch):
        # creating a Configuration does not change the process-wide one;
        # only set_current_configuration (or first use) does
        monkeypatch.setenv("LMFDB_CONFIG", str(tmp_path / "config.ini"))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        first = config_mod.Configuration()
        assert config_mod._current_configuration is None
        config_mod.set_current_configuration(first)
        config_mod.set_current_configuration(first)  # no-op
        assert config_mod.current_configuration() is first
        second = config_mod.Configuration()
        assert config_mod.current_configuration() is first
        with pytest.raises(RuntimeError):
            config_mod.set_current_configuration(second)

    def test_default_current_configuration(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LMFDB_CONFIG", str(tmp_path / "config.ini"))
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        conf = config_mod.current_configuration()
        assert isinstance(conf, config_mod.Configuration)
        assert config_mod.current_configuration() is conf

    def test_command_line_overrides_existing_config_file(self, tmp_path, monkeypatch):
        # Options given on the command line apply even when the
        # configuration file already exists (on first startup they are
        # written into the new file, which would hide a failure to apply
        # them), and reach every consumer of the process-wide configuration
        cfg = tmp_path / "config.ini"
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setenv("LMFDB_CONFIG", str(cfg))
        config_mod.Configuration()
        assert cfg.exists()
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        monkeypatch.setattr(sys, "argv", ["lmfdb", "--port", "39999"])
        conf = config_mod.Configuration(writeargstofile=True, readargs=True)
        config_mod.set_current_configuration(conf)
        assert config_mod.current_configuration().get_flask()["port"] == 39999
        try:
            from lmfdb.utils.cocalcwrap import CocalcWrap
        except ImportError as e:
            pytest.skip("lmfdb.utils is unavailable here (%s)" % e)
        monkeypatch.setenv("COCALC_PROJECT_ID", "example-project")
        assert CocalcWrap(None).app_root == "/example-project/server/39999"


class TestLogging:
    def test_logging_does_not_alter_configuration(self, tmp_path):
        # logging redacts the database password in the configuration it
        # prints, but must leave the shared configuration (which the
        # database also uses) intact
        if importlib.util.find_spec("sage") is None:
            pytest.skip("logging requires sage")
        code = (
            "from lmfdb import config\n"
            "conf = config.Configuration()\n"
            "config.set_current_configuration(conf)\n"
            "password = conf.postgresql_options['password']\n"
            "assert password != '****'\n"
            "import lmfdb.logger\n"
            "assert conf.postgresql_options['password'] == password\n"
            "assert conf.get_all()['postgresql_options']['password'] == password\n"
            "assert conf.options['postgresql']['password'] == password\n"
        )
        r = run_py(
            code,
            cwd=str(tmp_path),
            LMFDB_HOME=str(tmp_path),
            LMFDB_CONFIG=str(tmp_path / "config.ini"),
        )
        assert r.returncode == 0, r.stderr + r.stdout
        assert "'password': '****'" in r.stderr + r.stdout


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

    def test_db_objects(self):
        # lmfdb.db is lmfdb-client's lazy proxy, with the website's database
        # class (whose configuration is the website's), and the historical
        # lmfdb.lmfdb_database.db is the same object
        import lmfdb
        from lmfdb_client import LazyDatabase
        assert isinstance(lmfdb.db, LazyDatabase)
        assert lmfdb.db is not lmfdb_client.db
        r = run_py(
            "import lmfdb, lmfdb.lmfdb_database as d, lmfdb_client.database as c\n"
            "assert d.db is lmfdb.db\n"
            "assert issubclass(d.LMFDBDatabase, c.LMFDBDatabase)\n"
            "assert issubclass(d.LMFDBSearchTable, c.LMFDBSearchTable)\n"
            "assert d.LMFDBDatabase._search_table_class_ is d.LMFDBSearchTable\n"
            "from lmfdb.config import Configuration\n"
            "assert type(d.LMFDBDatabase.default_configuration()) is Configuration\n"
        )
        assert r.returncode == 0, r.stderr

    def test_site_installed(self):
        # importing lmfdb describes the LMFDB to lmfdb-utils
        import lmfdb
        from lmfdb.site import LMFDBSite
        from lmfdb_utils.site import current_site
        assert lmfdb
        assert isinstance(current_site(), LMFDBSite)


class TestCommandLine:
    def test_help_is_fast_and_clean(self, tmp_path):
        # --help is handled before the website (or sage) is imported, and
        # creates no files
        env = subprocess_env(
            LMFDB_HOME=str(tmp_path / "home"),
            LMFDB_CONFIG=str(tmp_path / "home" / "config.ini"),
        )
        r = subprocess.run(
            [sys.executable, "-m", "lmfdb", "--help"],
            capture_output=True, text=True, env=env, cwd=str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        assert "--config-file" in r.stdout
        assert "--postgresql-host" in r.stdout
        assert not any(tmp_path.iterdir()), "files were created by --help"

    def test_cli_installs_configuration(self, tmp_path, monkeypatch):
        # the configuration built from the command line is the one the
        # website is started with, and the process-wide one
        import types
        import lmfdb
        from lmfdb import cli
        started = []
        fake_website = types.ModuleType("lmfdb.website")
        fake_website.main = started.append
        monkeypatch.setitem(sys.modules, "lmfdb.website", fake_website)
        monkeypatch.setattr(lmfdb, "website", fake_website, raising=False)
        monkeypatch.setattr(config_mod, "_current_configuration", None)
        monkeypatch.setenv("LMFDB_HOME", str(tmp_path))
        monkeypatch.setenv("LMFDB_CONFIG", str(tmp_path / "config.ini"))
        monkeypatch.setattr(sys, "argv", ["lmfdb", "--port", "39999"])
        cli.main()
        assert len(started) == 1
        assert started[0] is config_mod.current_configuration()
        assert started[0].get_flask()["port"] == 39999

    def test_missing_sage_message(self, tmp_path):
        # starting the website without sage exits with an explanation
        # rather than a traceback
        code = (
            "import sys\n"
            "class Blocker:\n"
            "    def find_spec(self, name, path=None, target=None):\n"
            "        if name == 'sage' or name.startswith('sage.'):\n"
            "            raise ModuleNotFoundError('No module named %r' % name, name=name)\n"
            "sys.meta_path.insert(0, Blocker())\n"
            "sys.argv = ['lmfdb']\n"
            "from lmfdb.cli import main\n"
            "main()\n"
        )
        r = run_py(
            code,
            cwd=str(tmp_path),
            LMFDB_HOME=str(tmp_path),
            LMFDB_CONFIG=str(tmp_path / "config.ini"),
        )
        assert r.returncode == 1, r.stderr + r.stdout
        assert "requires SageMath" in r.stderr
        assert "Traceback" not in r.stderr


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
