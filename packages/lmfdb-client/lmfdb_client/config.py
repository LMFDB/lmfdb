"""
The settings for connecting to the LMFDB's PostgreSQL database.

Values are read from a configuration file, which is created with the
default values (a read-only connection to devmirror.lmfdb.xyz, a public
mirror of the LMFDB) if it does not exist, and can be overridden by
command-line options.  A ``secrets.ini`` next to the configuration file
overrides its values, so that credentials can be kept out of it.

The configuration file is the first of:

- the ``LMFDB_CONFIG`` environment variable;
- ``config.ini`` in the current directory, if it exists;
- ``config.ini`` in the LMFDB home directory, which is ``LMFDB_HOME`` if
  set and ``~/.lmfdb`` otherwise.

The default slow-query log goes to ``logs/`` in the LMFDB home directory.

The LMFDB website extends :class:`Configuration` with its own options and
file locations (see ``lmfdb/config.py`` in the LMFDB repository).  This
module must stay importable without sage or flask.
"""

import argparse
import os

from psycodict.config import Configuration as _Configuration

# The default connection: read-only, to the LMFDB's public mirror, with TCP
# keepalives (see Configuration.add_postgresql_arguments)
POSTGRESQL_DEFAULTS = {
    "host": "devmirror.lmfdb.xyz",
    "port": 5432,
    "user": "lmfdb",
    "password": "lmfdb",
    "dbname": "lmfdb",
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def lmfdb_home():
    """
    The directory holding the configuration file and logs when no other
    location is given: ``LMFDB_HOME`` if set, otherwise ``~/.lmfdb``.
    """
    home = os.environ.get("LMFDB_HOME")
    if home:
        return os.path.abspath(os.path.expanduser(home))
    return os.path.join(os.path.expanduser("~"), ".lmfdb")


def find_config_file():
    """
    The path where the configuration file is located (or will be created if
    missing), in the absence of a --config-file command-line option.

    This is the first of:

    - the ``LMFDB_CONFIG`` environment variable;
    - ``config.ini`` in the current directory, if it exists;
    - ``config.ini`` in the directory given by :func:`lmfdb_home`.
    """
    path = os.environ.get("LMFDB_CONFIG")
    if path:
        return os.path.abspath(os.path.expanduser(path))
    if os.path.exists("config.ini"):
        return os.path.abspath("config.ini")
    return os.path.join(lmfdb_home(), "config.ini")


class Configuration(_Configuration):
    """
    The settings for connecting to the LMFDB database.

    INPUT:

    - ``writeargstofile`` -- if the configuration file does not exist, create
      it with the values given on the command line rather than the defaults
    - ``readargs`` -- whether to parse the command line (``sys.argv``).
      Leave this off in libraries and in programs with their own command
      line.

    Subclasses (like the LMFDB website's) add options by extending
    :meth:`add_general_arguments`, :meth:`add_logging_arguments` and
    :meth:`add_arguments`, and change where files are placed by overriding
    :meth:`default_config_file` and :meth:`log_dir`.
    """
    description = "Connection to the L-functions and modular forms database (LMFDB)"

    # Queries slower than this many seconds are logged.  Interactive use is
    # not a website serving requests, so by default nothing is logged; the
    # website sets its own threshold.
    default_slowcutoff = float("inf")

    def __init__(self, writeargstofile=False, readargs=False):
        parser = argparse.ArgumentParser(description=self.description)
        self.add_arguments(parser)
        _Configuration.__init__(self, parser, writeargstofile=writeargstofile, readargs=readargs)

        opts = self.options
        extopts = self.extra_options

        # The locations of the configuration and secrets files, as resolved
        # by psycodict (including the --config-file and --secrets-file
        # options when arguments are read), so that files that live next to
        # the configuration can follow it
        self.config_file = os.path.abspath(extopts["config_file"])
        self.secrets_file = os.path.abspath(extopts["secrets_file"])

        # We update the options dictionary itself, since psycodict reads the
        # slow query settings from there
        opts["logging"]["slowlogfile"] = self.resolve_log_path(opts["logging"]["slowlogfile"], "slow_queries.log")

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
            "slowcutoff": opts["logging"]["slowcutoff"],
            "slowlogfile": opts["logging"]["slowlogfile"],
            "editor": opts["logging"]["editor"],
        }

    def default_config_file(self):
        """
        The configuration file used when none is given on the command line.
        """
        return find_config_file()

    def log_dir(self):
        """
        The directory in which log files are placed by default.
        """
        return os.path.join(lmfdb_home(), "logs")

    def resolve_log_path(self, value, default_name):
        """
        Determine the location of a log file.

        The default value ``default_name`` is placed in the directory given
        by :meth:`log_dir`; any other value is respected as a path (relative
        to the current directory if not absolute).
        """
        if value == default_name:
            logdir = self.log_dir()
            os.makedirs(logdir, exist_ok=True)
            return os.path.join(logdir, default_name)
        return value

    def add_arguments(self, parser):
        """
        Add all options to the ``argparse`` parser ``parser``.

        Option destinations have the form ``section_option``, giving the
        section and option names in the configuration file.
        """
        self.add_general_arguments(parser)
        self.add_logging_arguments(parser.add_argument_group("Logging options:"))
        self.add_postgresql_arguments(parser.add_argument_group("PostgreSQL options"))

    def add_general_arguments(self, parser):
        parser.add_argument(
            "--config-file",
            dest="config_file",
            metavar="FILE",
            help="configuration file [default: %(default)s]",
            default=self.default_config_file(),
        )
        parser.add_argument(
            "-s",
            "--secrets-file",
            dest="secrets_file",
            metavar="SECRETS",
            help="secrets file [default: secrets.ini next to the configuration file]",
            default=None,
        )

    def add_logging_arguments(self, group):
        group.add_argument(
            "--slowcutoff",
            dest="logging_slowcutoff",
            metavar="SLOWCUTOFF",
            help="threshold (in seconds) to log slow queries [default: %(default)s]",
            default=self.default_slowcutoff,
            type=float,
        )
        group.add_argument(
            "--slowlogfile",
            help="logfile for slow queries [default: %(default)s]",
            dest="logging_slowlogfile",
            metavar="FILE",
            default="slow_queries.log",
        )
        group.add_argument(
            "--editor",
            help="username for editor making data changes",
            dest="logging_editor",
            metavar="EDITOR",
            default="",
        )

    def add_postgresql_arguments(self, group):
        group.add_argument(
            "--postgresql-host",
            dest="postgresql_host",
            metavar="HOST",
            help="PostgreSQL server host or socket directory [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["host"],
        )
        group.add_argument(
            "--postgresql-port",
            dest="postgresql_port",
            metavar="PORT",
            type=int,
            help="PostgreSQL server port [default: %(default)d]",
            default=POSTGRESQL_DEFAULTS["port"],
        )
        group.add_argument(
            "--postgresql-user",
            dest="postgresql_user",
            metavar="USER",
            help="PostgreSQL username [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["user"],
        )
        group.add_argument(
            "--postgresql-pass",
            dest="postgresql_password",
            metavar="PASS",
            help="PostgreSQL password [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["password"],
        )
        group.add_argument(
            "--postgresql-dbname",
            dest="postgresql_dbname",
            metavar="DBNAME",
            help="PostgreSQL database name [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["dbname"],
        )

        # TCP keepalives on the database connection.  LMFDB usually talks to a
        # remote database (see --postgresql-host), where a connection can be
        # silently dropped by the server, a load balancer, or the network.
        # Keepalives let libpq detect a dead connection within about a minute
        # (with the defaults below) instead of blocking on the OS TCP timeout
        # for several minutes; this is a recurring source of spurious CI
        # failures that pass on a rerun.  psycodict passes these parameters
        # straight through to psycopg.connect, for both the initial connection
        # and every reconnection.  They are ignored for local unix-socket
        # connections and never interrupt a running query.  Pass
        # --postgresql-keepalives 0 to fall back to the operating system
        # defaults.
        group.add_argument(
            "--postgresql-keepalives",
            dest="postgresql_keepalives",
            metavar="0|1",
            type=int,
            help="use TCP keepalives on the database connection, 0 to disable [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["keepalives"],
        )
        group.add_argument(
            "--postgresql-keepalives-idle",
            dest="postgresql_keepalives_idle",
            metavar="SECONDS",
            type=int,
            help="idle time before the first keepalive probe is sent [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["keepalives_idle"],
        )
        group.add_argument(
            "--postgresql-keepalives-interval",
            dest="postgresql_keepalives_interval",
            metavar="SECONDS",
            type=int,
            help="time between keepalive probes [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["keepalives_interval"],
        )
        group.add_argument(
            "--postgresql-keepalives-count",
            dest="postgresql_keepalives_count",
            metavar="N",
            type=int,
            help="unanswered keepalive probes before the connection is dropped [default: %(default)s]",
            default=POSTGRESQL_DEFAULTS["keepalives_count"],
        )

    def get_all(self):
        return {
            "postgresql_options": self.postgresql_options,
            "logging_options": self.logging_options,
        }

    def get_postgresql(self):
        return self.postgresql_options

    def get_logging(self):
        return self.logging_options


class ConfigWrapper:
    """
    A configuration given by a dictionary rather than read from files.

    The dictionary can have the keys

    - ``postgresql_options`` -- the connection parameters (``host``,
      ``port``, ``user``, ``password``, ``dbname``, and any other parameter
      of ``psycopg.connect``); missing ones take the values in
      :data:`POSTGRESQL_DEFAULTS`
    - ``logging_options`` -- ``editor`` (the editor's LMFDB username),
      ``slowcutoff`` (in seconds; by default nothing is slow) and
      ``slowlogfile`` (by default slow queries are only printed)
    - ``flask_options`` -- used by the LMFDB website
    """
    def __init__(self, config_dict):
        self.postgresql_options = dict(POSTGRESQL_DEFAULTS)
        self.postgresql_options.update(config_dict.get('postgresql_options', {}))
        self.flask_options = config_dict.get('flask_options', {})
        self.logging_options = {"editor": "", "slowcutoff": float("inf"), "slowlogfile": os.devnull}
        self.logging_options.update(config_dict.get('logging_options', {}))
        # What psycodict reads, in the format of Configuration.options
        self.options = {"postgresql": self.postgresql_options, "logging": self.logging_options}
        self.extra_options = {}
        # No configuration file is involved
        self.config_file = None

    def get_postgresql_default(self):
        return dict(POSTGRESQL_DEFAULTS)

    # Add the get methods that might be expected
    def get_postgresql(self):
        return self.postgresql_options

    def get_flask(self):
        return self.flask_options

    def get_logging(self):
        return self.logging_options


# The process-wide configuration used by lmfdb_client.db: one installed
# with set_current_configuration, or else a default Configuration created
# on first use
_current_configuration = None


def current_configuration():
    """
    The process-wide :class:`Configuration` used by ``lmfdb_client.db``,
    created on first use unless one has been installed with
    :func:`set_current_configuration`.
    """
    global _current_configuration
    if _current_configuration is None:
        _current_configuration = Configuration()
    return _current_configuration


def set_current_configuration(config):
    """
    Make ``config`` the process-wide configuration returned by
    :func:`current_configuration`.

    This must happen before the database connects; replacing a
    configuration that is already in use raises a RuntimeError.
    """
    global _current_configuration
    if _current_configuration is not None and _current_configuration is not config:
        raise RuntimeError("The process-wide configuration is already in use and cannot be replaced")
    _current_configuration = config
