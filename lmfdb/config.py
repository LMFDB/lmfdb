# LMFDB - L-function and Modular Forms Database web-site - www.lmfdb.org
# Copyright (C) 2010-2012 by the LMFDB authors
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

"""
This file must not depend on other files from this project.
It's purpose is to parse a config file (create a default one if none
is present) and replace values stored within it with those given
via optional command-line arguments.

The location of the configuration file, the secret key and the log
files is determined as follows.

- When lmfdb is used from a git checkout, the configuration file is
  ``config.ini`` at the root of the checkout (as it always was), the secret
  key is stored next to it, and log files go to ``logs/`` at the root of
  the checkout.

- When lmfdb is installed as a package (e.g. with ``sage -pip install .``),
  these files live in the LMFDB home directory, ``~/.lmfdb`` by default;
  a ``config.ini`` in the current directory takes precedence if present.

- The environment variables ``LMFDB_HOME`` (directory for all of these
  files) and ``LMFDB_CONFIG`` (path of the configuration file) override
  the above, as does the ``--config-file`` command-line option.
"""


import argparse
import getpass
import os
import random
import string
import __main__
import socket
from contextlib import closing
from logging import INFO

COCALC_port = 0

# The root of the git checkout containing this file, or None if lmfdb is
# being used as an installed package rather than from a checkout
root_lmfdb_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
)
if not os.path.exists(os.path.join(root_lmfdb_path, "start-lmfdb.py")):
    root_lmfdb_path = None

from psycodict.config import Configuration as _Configuration


def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def lmfdb_home():
    """
    The directory holding the LMFDB configuration file, secret key and logs.

    This is the first of:

    - the ``LMFDB_HOME`` environment variable;
    - the root of the git checkout, when lmfdb is used from a checkout;
    - ``~/.lmfdb``.
    """
    home = os.environ.get("LMFDB_HOME")
    if home:
        return os.path.abspath(os.path.expanduser(home))
    if root_lmfdb_path is not None:
        return root_lmfdb_path
    return os.path.join(os.path.expanduser("~"), ".lmfdb")


def lmfdb_log_dir():
    """
    The directory where log files (flasklog, slow_queries.log, verification
    logs) are placed by default.
    """
    return os.path.join(lmfdb_home(), "logs")


def find_config_file():
    """
    The path where the configuration file is located (or will be created if
    missing), in the absence of a --config-file command-line option.

    This is the first of:

    - the ``LMFDB_CONFIG`` environment variable;
    - ``config.ini`` in the current directory, if it exists and lmfdb is not
      being used from a git checkout (a checkout keeps its own config.ini at
      the root, as before);
    - ``config.ini`` in the directory given by :func:`lmfdb_home`.
    """
    path = os.environ.get("LMFDB_CONFIG")
    if path:
        return os.path.abspath(os.path.expanduser(path))
    if root_lmfdb_path is None and os.path.exists("config.ini"):
        return os.path.abspath("config.ini")
    return os.path.join(lmfdb_home(), "config.ini")


def get_secret_key():
    """
    Return the secret key used for flask sessions, creating it (in the same
    directory as the configuration file) if it does not yet exist.
    """
    secret_key_file = os.path.join(os.path.dirname(find_config_file()), "secret_key")
    # if secret_key_file doesn't exist, create it
    if not os.path.exists(secret_key_file):
        os.makedirs(os.path.dirname(secret_key_file), exist_ok=True)
        with open(secret_key_file, "w") as F:
            # generate a random ASCII string
            F.write(
                "".join(
                    [
                        random.choice(string.ascii_letters + string.digits)
                        for n in range(32)
                    ]
                )
            )
    return open(secret_key_file).read()


def _resolve_log_path(value, default_name):
    """
    Determine the location of a log file.

    The historical default values ("flasklog" and "slow_queries.log", which
    used to be created in the current directory) are placed in the directory
    given by :func:`lmfdb_log_dir` instead; any other value is respected as a
    path (relative to the current directory if not absolute).
    """
    if value == default_name:
        logdir = lmfdb_log_dir()
        os.makedirs(logdir, exist_ok=True)
        return os.path.join(logdir, default_name)
    return value


def _started_as_website():
    """
    Whether this process was launched by one of the website entry points
    (start-lmfdb.py, the lmfdb console script, or python -m lmfdb), in which
    case command-line arguments are read and recorded in the config file.
    """
    main_file = getattr(__main__, "__file__", None)
    if not main_file:
        return False
    if os.path.basename(main_file) in ("start-lmfdb.py", "lmfdb", "lmfdb.exe", "lmfdb-script.py"):
        return True
    return main_file.endswith(os.path.join("lmfdb", "__main__.py"))


class Configuration(_Configuration):
    def __init__(self, writeargstofile=False, readargs=False):
        default_config_file = find_config_file()

        # 1: parsing command-line arguments
        parser = argparse.ArgumentParser(
            description="LMFDB - The L-functions and modular forms database"
        )

        parser.add_argument(
            "--config-file",
            dest="config_file",
            metavar="FILE",
            help="configuration file [default: %(default)s]",
            default=default_config_file,
        )
        # gunicorn uses '-c' to specify its config file
        # we don't want the config parser to get confused
        # when the app is ran via gunicorn
        parser.add_argument(
            "-c",
            help=argparse.SUPPRESS,
            dest="trash_becauseofgunicorn"
        )
        parser.add_argument(
            "-s",
            "--secrets-file",
            dest="secrets_file",
            metavar="SECRETS",
            help="secrets file [default: %(default)s]",
            default="secrets.ini",
        )

        parser.add_argument(
            "-d",
            "--debug",
            action="store_true",
            dest="core_debug",
            help="enable debug mode",
        )

        parser.add_argument(
            "-r",
            "--restart",
            action="store_true",
            dest="core_restart",
            help="enable restart mode. CAUTION: can cause segfaults on pages using PARI",
        )

        parser.add_argument(
            "--color",
            dest="core_color",
            metavar="COLOR",
            help="color template (see lmfdb/utils/color.py)",
            default=19,
            type=int,
        )

        parser.add_argument(
            "-p",
            "--port",
            dest="web_port",
            metavar="PORT",
            help="the LMFDB server will be running on PORT [default: %(default)d]",
            type=int,
            default=37777,
        )
        parser.add_argument(
            "-b",
            "--bind_ip",
            dest="web_bindip",
            metavar="HOST",
            help="the LMFDB server will be listening to HOST [default: %(default)s]",
            default="127.0.0.1",
        )

        logginggroup = parser.add_argument_group("Logging options:")
        logginggroup.add_argument(
            "--logfile",
            help="logfile for flask [default: %(default)s]",
            dest="logging_logfile",
            metavar="FILE",
            default="flasklog",
        )

        logginggroup.add_argument(
            "--loglevel",
            help="loglevel for flask [default: %(default)s]",
            dest="logging_loglevel",
            metavar="LEVEL",
            type=int,
            default=INFO,
        )

        logginggroup.add_argument(
            "--slowcutoff",
            dest="logging_slowcutoff",
            metavar="SLOWCUTOFF",
            help="threshold to log slow queries [default: %(default)s]",
            default=0.1,
            type=float,
        )

        logginggroup.add_argument(
            "--slowlogfile",
            help="logfile for slow queries [default: %(default)s]",
            dest="logging_slowlogfile",
            metavar="FILE",
            default="slow_queries.log",
        )
        logginggroup.add_argument(
            "--editor",
            help="username for editor making data changes",
            dest="logging_editor",
            metavar="EDITOR",
            default="",
        )

        # PostgresSQL options
        postgresqlgroup = parser.add_argument_group("PostgreSQL options")
        postgresqlgroup.add_argument(
            "--postgresql-host",
            dest="postgresql_host",
            metavar="HOST",
            help="PostgreSQL server host or socket directory [default: %(default)s]",
            default="devmirror.lmfdb.xyz",
        )
        postgresqlgroup.add_argument(
            "--postgresql-port",
            dest="postgresql_port",
            metavar="PORT",
            type=int,
            help="PostgreSQL server port [default: %(default)d]",
            default=5432,
        )

        postgresqlgroup.add_argument(
            "--postgresql-user",
            dest="postgresql_user",
            metavar="USER",
            help="PostgreSQL username [default: %(default)s]",
            default="lmfdb",
        )

        postgresqlgroup.add_argument(
            "--postgresql-pass",
            dest="postgresql_password",
            metavar="PASS",
            help="PostgreSQL password [default: %(default)s]",
            default="lmfdb",
        )

        postgresqlgroup.add_argument(
            "--postgresql-dbname",
            dest="postgresql_dbname",
            metavar="DBNAME",
            help="PostgreSQL database name [default: %(default)s]",
            default="lmfdb",
        )

        # undocumented options
        parser.add_argument(
            "--enable-profiler",
            dest="profiler",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        # undocumented flask options
        parser.add_argument(
            "--enable-reloader",
            dest="use_reloader",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--disable-reloader",
            dest="use_reloader",
            help=argparse.SUPPRESS,
            action="store_false",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--enable-debugger",
            dest="use_debugger",
            help=argparse.SUPPRESS,
            action="store_true",
            default=argparse.SUPPRESS,
        )

        parser.add_argument(
            "--disable-debugger",
            dest="use_debugger",
            help=argparse.SUPPRESS,
            action="store_false",
            default=argparse.SUPPRESS,
        )
        # if the website was started (via start-lmfdb.py, the lmfdb script or python -m lmfdb)
        startlmfdbQ = _started_as_website()
        writeargstofile = writeargstofile or startlmfdbQ
        readargs = readargs or startlmfdbQ

        # the config file is created if it doesn't exist; make sure the
        # directory it lives in exists first
        known_args, _ = parser.parse_known_args([] if not readargs else None)
        config_dir = os.path.dirname(os.path.abspath(known_args.config_file))
        os.makedirs(config_dir, exist_ok=True)

        _Configuration.__init__(self, parser, writeargstofile=writeargstofile, readargs=readargs)

        # Enable TCP keepalives on the PostgreSQL connection.
        #
        # LMFDB usually talks to a *remote* database (the default host is
        # devmirror.lmfdb.xyz), so a connection can be silently dropped by the
        # server, a load balancer, or the network.  Without keepalives, libpq
        # only notices when it next uses the socket: a query issued on a dead
        # connection then blocks on the OS TCP timeout for several minutes
        # before raising "OperationalError: server closed the connection
        # unexpectedly".  This is a recurring source of spurious CI failures
        # that pass on a rerun.
        #
        # These libpq parameters live in options["postgresql"] and are passed
        # straight through to psycopg2.connect by psycodict, for both the
        # initial connection and every reset_connection().  They are ignored for
        # local unix-socket connections and never interrupt a long-running query
        # (keepalives are handled by the OS TCP stack), so they are safe
        # defaults; setdefault lets an explicit config.ini or command-line value
        # take precedence.
        pg_options = self.options["postgresql"]
        pg_options.setdefault("keepalives", 1)
        pg_options.setdefault("keepalives_idle", 30)
        pg_options.setdefault("keepalives_interval", 10)
        pg_options.setdefault("keepalives_count", 5)

        opts = self.options
        extopts = self.extra_options

        # The historical default log files used to be created in the current
        # directory; they now go to the log directory.  We update the options
        # dictionary itself since psycodict reads the slow query settings
        # from there.
        opts["logging"]["logfile"] = _resolve_log_path(opts["logging"]["logfile"], "flasklog")
        opts["logging"]["slowlogfile"] = _resolve_log_path(opts["logging"]["slowlogfile"], "slow_queries.log")

        self.flask_options = {
            "port": opts["web"]["port"],
            "host": opts["web"]["bindip"],
            "debug": opts["core"]["debug"],
            "use_reloader": opts["core"]["restart"],
        }
        for opt in ["use_debugger", "use_reloader", "profiler"]:
            if opt in extopts:
                self.flask_options[opt] = extopts[opt]

        self.cocalc_options = {}
        if "COCALC_PROJECT_ID" in os.environ:
            from requests import get
            # we must accept external connections
            self.flask_options["host"] = "0.0.0.0"
            self.cocalc_options["host"] = "cocalc.com"
            external_ip = get('https://api.ipify.org').content.decode('utf8')
            if external_ip == "18.18.21.21": # chatelet
                self.cocalc_options["host"] = "chatelet.mit.edu"
                global COCALC_port
                if COCALC_port:
                    self.flask_options["port"] = COCALC_port
                else:
                    # randomify port, we have only container
                    if self.flask_options["port"] == 37777: # default
                        username = getpass.getuser()
                        intusername = int(username, base=36)
                        self.flask_options["port"] = 10000 + (intusername % 55536)
                    while is_port_open(self.flask_options["host"], self.flask_options["port"]):
                        print(f'port {self.flask_options["port"]} already in use, trying the next one')
                        self.flask_options["port"] += 1
                        if self.flask_options["port"] > 65536:
                            self.flask_options["port"] = 10000
                    COCALC_port = self.flask_options["port"]
            self.cocalc_options["root"] = '/' + os.environ['COCALC_PROJECT_ID'] + "/server/" + str(self.flask_options['port'])
            self.cocalc_options["prefix"] = ("https://"
                                             + self.cocalc_options["host"]
                                             + self.cocalc_options["root"])
            stars = "\n" + "*" * 80
            self.cocalc_options["message"] = (stars +
             "\n\033[1mCocalc\033[0m environment detected!\n"
             + "Visit"
             + f"\n  \033[1m {self.cocalc_options['prefix']} \033[0m"
             + "\nto access this LMFDB instance"
             + stars)

        self.color = opts["core"]["color"]

        self.postgresql_options = {
            "port": opts["postgresql"]["port"],
            "host": opts["postgresql"]["host"],
            "dbname": opts["postgresql"]["dbname"],
        }

        # optional items
        for elt in ["user", "password"]:
            if elt in opts["postgresql"]:
                self.postgresql_options[elt] = opts["postgresql"][elt]

        self.logging_options = {
            "logfile": opts["logging"]["logfile"],
            "slowcutoff": opts["logging"]["slowcutoff"],
            "slowlogfile": opts["logging"]["slowlogfile"],
            "editor": opts["logging"]["editor"],
            "loglevel": opts["logging"]["loglevel"],
        }

    def get_all(self):
        return {
            "flask_options": self.flask_options,
            "postgresql_options": self.postgresql_options,
            "logging_options": self.logging_options,
        }

    def get_flask(self):
        return self.flask_options

    def get_cocalc(self):
        return self.cocalc_options

    def get_url_prefix(self):
        return self.cocalc_options.get('prefix', '')

    def get_color(self):
        return self.color

    def get_postgresql(self):
        return self.postgresql_options

    def get_logging(self):
        return self.logging_options


class ConfigWrapper:
    """
    A wrapper class that provides the same interface as Configuration
    but is initialized from a dictionary of options.
    """
    def __init__(self, config_dict):
        # Set default values and update with provided config
        self.postgresql_options = config_dict.get('postgresql_options', {})
        self.flask_options = config_dict.get('flask_options', {})
        self.logging_options = config_dict.get('logging_options', {'editor': ''})

    # Add the get methods that might be expected
    def get_postgresql(self):
        return self.postgresql_options

    def get_flask(self):
        return self.flask_options

    def get_logging(self):
        return self.logging_options


if __name__ == "__main__":
    Configuration(writeargstofile=True, readargs=True)
