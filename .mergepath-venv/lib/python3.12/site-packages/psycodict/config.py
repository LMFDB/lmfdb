# -*- coding: utf-8 -*-
"""
Configuration handling for psycodict.

:class:`Configuration` merges a ``config.ini`` file with command-line
arguments (off by default; see ``readargs``) and hands the result to
:class:`~psycodict.database.PostgresDatabase`.  When no file is named
explicitly, :func:`find_config_file` discovers one: the
``PSYCODICT_CONFIG`` environment variable, then ``config.ini`` in the
current directory if it already exists, then ``~/.psycodict/config.ini``,
which is created on first use.  A ``secrets.ini`` next to the configuration
file overrides its values, so credentials can be kept out of it.
"""
import os
import argparse
from configparser import ConfigParser
from collections import defaultdict
from copy import deepcopy


def strbool(s):
    """
    A function for parsing boolean strings
    """
    if s.lower() in ["true", "t", "yes", "y"]:
        return True
    elif s.lower() in ["false", "f", "no", "n"]:
        return False
    else:
        raise ValueError(s)


def psycodict_home():
    """
    The directory used for psycodict's own files (the configuration file and
    the slow-query log) when no explicit location is given: ``~/.psycodict``.

    Raises ``RuntimeError`` when no home directory can be determined -- for
    example a container running with ``HOME`` unset and a uid that has no
    passwd entry, where ``expanduser`` returns the literal ``~``.  Refusing
    loudly beats quietly creating a directory named ``~`` in the working
    directory.
    """
    home = os.path.expanduser("~")
    if not os.path.isabs(home):
        raise RuntimeError(
            "Cannot determine a home directory for psycodict's configuration; "
            "set the PSYCODICT_CONFIG environment variable (or pass "
            "config_file) to choose a location for the configuration file"
        )
    return os.path.join(home, ".psycodict")


def find_config_file():
    """
    The path of the configuration file when none is specified explicitly.

    This is the first of:

    - the ``PSYCODICT_CONFIG`` environment variable;
    - ``config.ini`` in the current directory, if it exists;
    - ``config.ini`` in ``~/.psycodict``.

    A missing configuration file is created at the resolved location.  The
    current-directory candidate requires the file to already exist, so
    nothing is ever created in the working directory: a fresh setup gets its
    configuration under ``~/.psycodict`` (or wherever ``PSYCODICT_CONFIG``
    points).  When no home directory can be determined either, this raises
    ``RuntimeError`` (see :func:`psycodict_home`).
    """
    path = os.environ.get("PSYCODICT_CONFIG")
    if path:
        return os.path.abspath(os.path.expanduser(path))
    if os.path.exists("config.ini"):
        return os.path.abspath("config.ini")
    return os.path.join(psycodict_home(), "config.ini")


class Configuration():
    """
    This configuration object merges input from the command line and a configuration file.

    If the configuration file does not exist, it can create it with values specified by the default command line arguments.  This allows a user to edit the configuration file to change the defaults.

    Because of this dual approach, the types of all configuration values must be recoverable from their string values.  Namely, each object x of type T must satisfy x == T(str(x)).  Strings, integers and floats all have this property.

    INPUT:

    - ``parser`` -- an argparse.ArgumentParser instance.  If not provided, a default will be created.
    - ``defaults`` -- a dictionary with default values for the created argument parser.  Only used if a parser is not specified.  The keys used are:

      - ``config_file`` -- the filename for the configuration file.  If not
        given, it is discovered: the ``PSYCODICT_CONFIG`` environment
        variable, then ``config.ini`` in the current directory if it exists,
        then ``~/.psycodict/config.ini`` (created on first use); see
        :func:`find_config_file`.
      - ``secrets_file`` -- the filename for the secrets file, whose values
        override the configuration file.  If not given, ``secrets.ini`` next
        to the configuration file.
      - ``logging_slowcutoff`` -- a float, giving the threshold above which a slow-query warning will be logged
      - ``logging_slowlogfile`` -- a filename where slow-query warnings are
        printed.  The default value ``slow_queries.log`` is placed in a
        ``logs`` directory next to the configuration file, falling back to
        ``~/.psycodict/logs`` when that location is not writable; any other
        value is used verbatim.
      - ``postgresql_host`` -- the hostname for the database
      - ``postgresql_port`` -- an integer, the port to use when connecting to the database
      - ``postgresql_user`` -- the username when connecting to the database
      - ``postgresql_password`` -- the password for connecting to the database
      - ``postgresql_dbname`` -- the name of the database to connect to

    - ``writeargstofile`` -- a boolean, if config file doesn't exist, it determines if command line arguments are written to the config file instead of the default arguments
    - ``readargs`` -- a boolean (default False), determining whether command
      line arguments are read.  Leave this off in libraries and applications
      with their own command line; pass True in a script whose command line
      psycodict should parse.
    """
    def __init__(self, parser=None, defaults={}, writeargstofile=False, readargs=False):
        builtin_parser = parser is None

        if parser is None:
            parser = argparse.ArgumentParser(description="Default psycodict parser")

            parser.add_argument(
                "-c",
                "--config-file",
                dest="config_file",
                metavar="FILE",
                help="configuration file [default: $PSYCODICT_CONFIG, "
                     "./config.ini if present, else ~/.psycodict/config.ini]",
                default=defaults.get("config_file"),
            )
            parser.add_argument(
                "-s",
                "--secrets-file",
                dest="secrets_file",
                metavar="SECRETS",
                help="secrets file [default: secrets.ini next to the configuration file]",
                default=defaults.get("secrets_file"),
            )

            logginggroup = parser.add_argument_group("Logging options:")
            logginggroup.add_argument(
                "--slowcutoff",
                dest="logging_slowcutoff",
                metavar="SLOWCUTOFF",
                help="threshold to log slow queries [default: %(default)s]",
                default=defaults.get("logging_slowcutoff", 0.1),
                type=float,
            )

            logginggroup.add_argument(
                "--slowlogfile",
                help="logfile for slow queries [default: %(default)s]",
                dest="logging_slowlogfile",
                metavar="FILE",
                default=defaults.get("logging_slowlogfile", "slow_queries.log"),
            )

            # PostgresSQL options
            postgresqlgroup = parser.add_argument_group("PostgreSQL options")
            postgresqlgroup.add_argument(
                "--postgresql-host",
                dest="postgresql_host",
                metavar="HOST",
                help="PostgreSQL server host or socket directory [default: %(default)s]",
                default=defaults.get("postgresql_host", "localhost"),
            )
            postgresqlgroup.add_argument(
                "--postgresql-port",
                dest="postgresql_port",
                metavar="PORT",
                type=int,
                help="PostgreSQL server port [default: %(default)d]",
                default=defaults.get("postgresql_port", 5432),
            )

            postgresqlgroup.add_argument(
                "--postgresql-user",
                dest="postgresql_user",
                metavar="USER",
                help="PostgreSQL username [default: %(default)s]",
                default=defaults.get("postgresql_user", "postgres"),
            )

            postgresqlgroup.add_argument(
                "--postgresql-pass",
                dest="postgresql_password",
                metavar="PASS",
                help="PostgreSQL password [default: %(default)s]",
                default=defaults.get("postgresql_password", ""),
            )

            postgresqlgroup.add_argument(
                "--postgresql-dbname",
                dest="postgresql_dbname",
                metavar="DBNAME",
                help="PostgreSQL database name [default: %(default)s]",
                default=defaults.get("postgresql_dbname", "lmfdb"),
            )

        def sec_opt(key):
            if "_" in key:
                sec, opt = key.split("_", 1)
            else:
                sec = "misc"
                opt = key
            return sec, opt

        # 1: parsing command-line arguments
        if readargs:
            args = parser.parse_args()
        else:
            # only read config file
            args = parser.parse_args([])

        # Resolve the file locations.  An explicit location (from the
        # defaults dictionary or the command line) is used verbatim; with the
        # builtin parser both default to None, triggering the discovery in
        # find_config_file -- so a missing configuration file is created
        # under ~/.psycodict (or $PSYCODICT_CONFIG), never in the working
        # directory.
        if args.config_file is None:
            args.config_file = find_config_file()
        if args.secrets_file is None:
            args.secrets_file = os.path.join(
                os.path.dirname(os.path.abspath(args.config_file)), "secrets.ini"
            )

        args_dict = vars(args)
        default_arguments_dict = vars(parser.parse_args([]))

        del default_arguments_dict["config_file"]
        del default_arguments_dict["secrets_file"]

        self.default_args = defaultdict(dict)
        for key, val in default_arguments_dict.items():
            sec, opt = sec_opt(key)
            self.default_args[sec][opt] = str(val)

        # reading the config file, creating it if necessary
        # 2/1: does config file exist?
        if not os.path.exists(args.config_file):
            write_args = deepcopy(self.default_args)
            if not writeargstofile:
                print(
                    "Config file: %s not found, creating it with the default values"
                    % args.config_file
                )
            else:
                print(
                    "Config file: %s not found, creating it with the passed values"
                    % args.config_file
                )
                # overwrite default arguments passed via command line args
                for key, val in args_dict.items():
                    if key in default_arguments_dict:
                        sec, opt = sec_opt(key)
                        write_args[sec][opt] = str(val)

            _cfgp = ConfigParser()
            # create sections
            for sec, options in write_args.items():
                _cfgp.add_section(sec)
                for opt, val in options.items():
                    _cfgp.set(sec, opt, str(val))

            # the resolved location may sit in a directory that does not
            # exist yet (a fresh ~/.psycodict in particular)
            confdir = os.path.dirname(args.config_file)
            if confdir:
                os.makedirs(confdir, exist_ok=True)
            with open(args.config_file, "w") as configfile:
                _cfgp.write(configfile)

        # 2/2: reading the config file
        _cfgp = ConfigParser()
        _cfgp.read(args.config_file)
        # 2/3: reading the secrets file, which can override the config
        if os.path.exists(args.secrets_file):
            _cfgp.read(args.secrets_file)

        # 3: override specific settings
        def file_to_args(sep="_"):
            ret = {}
            for s in _cfgp.sections():
                for k, v in _cfgp.items(s):
                    ret["%s%s%s" % (s, sep, k)] = v
            return ret

        args_file = file_to_args()

        for key, val in default_arguments_dict.items():
            # if a nondefault value was passed through command line arguments set it
            # or if a default value was not set in the config file
            if args_dict[key] != val or key not in args_file:
                sec, opt = sec_opt(key)
                if sec not in _cfgp.sections():
                    _cfgp.add_section(sec)
                _cfgp.set(sec, opt, str(args_dict[key]))

        # We can derive the types from the parser
        type_dict = {}
        for action in parser._actions:
            if isinstance(action, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
                type_dict[action.dest] = strbool
            else:
                type_dict[action.dest] = action.type

        def get(section, key):
            val = _cfgp.get(section, key)
            # reconstruct the argparse dest: keys without an underscore went
            # into the misc section with the bare key as dest
            full = section + "_" + key
            if full not in type_dict and section == "misc":
                full = key
            type_func = type_dict.get(full)
            if type_func is not None:
                val = type_func(val)
            return val

        self.options = defaultdict(dict)
        for sec, options in self.default_args.items():
            for opt in options:
                self.options[sec][opt] = get(sec, opt)

        self.extra_options = {} # not stored in the config file
        for key, val in args_dict.items():
            if key not in default_arguments_dict:
                self.extra_options[key] = val

        if builtin_parser:
            # The default value of slowlogfile used to be created in the
            # working directory; place it in a logs directory next to the
            # configuration file instead, falling back to ~/.psycodict/logs
            # when that location cannot be written (a system-managed
            # configuration in a read-only directory, say -- reading a
            # configuration must not require write access beside it).  Any
            # other value is used verbatim.  (Callers supplying their own
            # parser own their logging semantics; they are not touched.)
            logopts = self.options["logging"]
            if logopts.get("slowlogfile") == "slow_queries.log":
                logdir = self._default_log_dir(args.config_file)
                if logdir is not None:
                    logopts["slowlogfile"] = os.path.join(logdir, "slow_queries.log")

    @staticmethod
    def _default_log_dir(config_file):
        """
        The directory for the default slow-query log: the first of
        ``<config dir>/logs`` and ``~/.psycodict/logs`` that exists or can be
        created, and is writable.

        The directory must exist and be writable before PostgresDatabase
        attaches its FileHandler, so the candidates are probed by creating
        them.  Returns None when neither candidate is usable (the plain
        default name is then kept, preserving the historical behavior of
        writing in the working directory).
        """
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(config_file)), "logs")
        ]
        try:
            candidates.append(os.path.join(psycodict_home(), "logs"))
        except RuntimeError:
            pass
        for candidate in candidates:
            try:
                os.makedirs(candidate, exist_ok=True)
            except OSError:
                continue
            if os.access(candidate, os.W_OK | os.X_OK):
                return candidate
        return None

    def get_postgresql_default(self):
        """
        The built-in default connection options (host, port, user, ...), as
        a dictionary -- the values used before the configuration file and
        command line are consulted.
        """
        res = dict(self.default_args["postgresql"])
        res["port"] = int(res["port"])
        return res
