"""
The configuration of the LMFDB website: the database connection settings
of lmfdb-client (see ``packages/lmfdb-client/lmfdb_client/config.py``),
together with the website's own options (port, debug mode, logging, ...).

Values are read from the configuration file (which is created with the
default values if it does not exist), and can be overridden by command-line
options.  The locations of the configuration file, the secrets file, the
secret key and the log files are described in GettingStarted.md, under
"Locations of configuration and log files".

The database layer imports this module and must work without sage or
flask, so this module must not import anything else from the LMFDB.
"""

import argparse
import getpass
import os
import secrets
import string
import socket
import tempfile
from contextlib import closing
from logging import INFO
from pathlib import Path

from lmfdb_client.config import Configuration as _ClientConfiguration
from lmfdb_client.config import ConfigWrapper

assert ConfigWrapper  # re-exported for the database layer

COCALC_port = 0

# The directory of the lmfdb package; use this to locate files that are
# part of the package (templates, data files, etc.)
lmfdb_package_dir = Path(__file__).resolve().parent

# The root of the git checkout containing the package
root_lmfdb_path = str(lmfdb_package_dir.parent)


def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def abs_path_lmfdb(filename):
    """
    The path of a file at the root of the git checkout, relative to the
    current directory (a historical helper).
    """
    return os.path.relpath(os.path.join(root_lmfdb_path, filename), os.getcwd())


def lmfdb_home():
    """
    The directory holding the LMFDB configuration file, secret key and logs:
    the ``LMFDB_HOME`` environment variable if set, and otherwise the root
    of the git checkout.
    """
    home = os.environ.get("LMFDB_HOME")
    if home:
        return os.path.abspath(os.path.expanduser(home))
    return root_lmfdb_path


def lmfdb_log_dir():
    """
    The directory where log files (flasklog, slow_queries.log, verification
    logs) are placed by default.
    """
    return os.path.join(lmfdb_home(), "logs")


def find_config_file():
    """
    The path where the configuration file is located (or will be created if
    missing), in the absence of a --config-file command-line option: the
    ``LMFDB_CONFIG`` environment variable if set, and otherwise
    ``config.ini`` in the directory given by :func:`lmfdb_home`.
    """
    path = os.environ.get("LMFDB_CONFIG")
    if path:
        return os.path.abspath(os.path.expanduser(path))
    return os.path.join(lmfdb_home(), "config.ini")


def get_secret_key(config_file=None):
    """
    Return the secret key used for flask sessions, creating it (in the same
    directory as the configuration file) if it does not yet exist.

    INPUT:

    - ``config_file`` -- the path of the configuration file next to which
      the key is stored.  Defaults to :func:`find_config_file`; components
      with access to a :class:`Configuration` should use its
      ``get_secret_key`` method instead, so that a ``--config-file`` option
      is respected.
    """
    if config_file is None:
        config_file = find_config_file()
    directory = os.path.dirname(os.path.abspath(config_file))
    secret_key_file = os.path.join(directory, "secret_key")
    if not os.path.exists(secret_key_file):
        os.makedirs(directory, exist_ok=True)
        key = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        # Write the key to a temporary file (created readable only by the
        # owner) and link it into place once it is complete: under its
        # final name the file is therefore never empty or half-written, so
        # workers starting simultaneously either create the key or read a
        # complete one.  The link fails if the name already exists, which
        # is how the losers of the race learn to use the existing key.
        fd, tmp = tempfile.mkstemp(dir=directory)
        try:
            with os.fdopen(fd, "w") as F:
                F.write(key)
            try:
                os.link(tmp, secret_key_file)
            except FileExistsError:
                pass
        finally:
            os.unlink(tmp)
    with open(secret_key_file) as F:
        return F.read()


# The process-wide configuration, shared by logging, the flask app's secret
# key, the website and the database.  The lmfdb command (lmfdb.cli) installs
# the configuration it builds from the command line before importing
# anything else; otherwise a default Configuration is created on first use.
_current_configuration = None


def current_configuration():
    """
    The process-wide :class:`Configuration`, created on first use unless
    one has been installed with :func:`set_current_configuration`.
    """
    global _current_configuration
    if _current_configuration is None:
        _current_configuration = Configuration()
    return _current_configuration


def set_current_configuration(config):
    """
    Make ``config`` the process-wide configuration returned by
    :func:`current_configuration`.

    This must happen before anything uses the process-wide configuration
    (in particular before the database connects or the website is imported);
    replacing a configuration that is already in use raises a RuntimeError.
    """
    global _current_configuration
    if _current_configuration is not None and _current_configuration is not config:
        raise RuntimeError("The process-wide configuration is already in use and cannot be replaced")
    _current_configuration = config


class Configuration(_ClientConfiguration):
    description = "LMFDB - The L-functions and modular forms database"
    default_slowcutoff = 0.1

    def __init__(self, writeargstofile=False, readargs=False):
        _ClientConfiguration.__init__(self, writeargstofile=writeargstofile, readargs=readargs)

        opts = self.options
        extopts = self.extra_options

        opts["logging"]["logfile"] = self.resolve_log_path(opts["logging"]["logfile"], "flasklog")

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

        self.logging_options["logfile"] = opts["logging"]["logfile"]
        self.logging_options["loglevel"] = opts["logging"]["loglevel"]

    def default_config_file(self):
        return find_config_file()

    def log_dir(self):
        return lmfdb_log_dir()

    def add_general_arguments(self, parser):
        _ClientConfiguration.add_general_arguments(self, parser)
        # gunicorn uses '-c' to specify its config file
        # we don't want the config parser to get confused
        # when the app is ran via gunicorn
        parser.add_argument(
            "-c",
            help=argparse.SUPPRESS,
            dest="trash_becauseofgunicorn"
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
            help="color template (see packages/lmfdb-utils/lmfdb_utils/color.py)",
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

    def add_logging_arguments(self, group):
        group.add_argument(
            "--logfile",
            help="logfile for flask [default: %(default)s]",
            dest="logging_logfile",
            metavar="FILE",
            default="flasklog",
        )
        group.add_argument(
            "--loglevel",
            help="loglevel for flask [default: %(default)s]",
            dest="logging_loglevel",
            metavar="LEVEL",
            type=int,
            default=INFO,
        )
        _ClientConfiguration.add_logging_arguments(self, group)

    def add_arguments(self, parser):
        _ClientConfiguration.add_arguments(self, parser)

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

    def get_secret_key(self):
        """
        Return the secret key used for flask sessions, stored next to this
        configuration's file.
        """
        return get_secret_key(self.config_file)

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


if __name__ == "__main__":
    Configuration(writeargstofile=True, readargs=True)
