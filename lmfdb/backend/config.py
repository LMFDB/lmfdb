# -*- coding: utf-8 -*-
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


class Configuration():
    """
    This configuration object merges input from the command line and a configuration file.

    If the configuration file does not exist, it can create it with values specified by the default command line arguments.  This allows a user to edit the configuration file to change the defaults.

    Because of this dual approach, the types of all configuration values must be recoverable from their string values.  Namely, each object x of type T must satisfy x == T(str(x)).  Strings, integers and floats all have this property.

    INPUT:

    - ``parser`` -- an argparse.ArgumentParser instance.  If not provided, a default will be created.
    - ``defaults`` -- a dictionary with default values for the created argument parser.  Only used if a parser is not specified.  The keys used are:
      - ``config_file`` -- the filename for the configuration file
      - ``logging_slowcutoff`` -- a float, giving the threshold above which a slow-query warning will be logged
      - ``logging_slowlogfile`` -- a filename where slow-query warnings are printed
      - ``postgresql_host`` -- the hostname for the database
      - ``postgresql_port`` -- an integer, the port to use when connecting to the database
      - ``postgresql_user`` -- the username when connecting to the database
      - ``postgresql_password`` -- the password for connecting to the database
      - ``writeargstofile`` - a boolean, if config file doesn't exist, it determines if command line arguments are written to the config file instead of the default arguments
      - ``readargs`` - a boolean, if determines if command line arguments are read
    """
    def __init__(self, parser=None, defaults={}, writeargstofile=False, readargs=None):
        if readargs is None:
            import __main__ as main
            # if a file was ran
            readargs = hasattr(main, '__file__')

        if parser is None:
            parser = argparse.ArgumentParser(description="Default psycodict parser")

            parser.add_argument(
                "-c",
                "--config-file",
                dest="config_file",
                metavar="FILE",
                help="configuration file [default: %(default)s]",
                default=defaults.get("config_file", "config.ini"),
            )
            parser.add_argument(
                "-s",
                "--secrets-file",
                dest="secrets_file",
                metavar="SECRETS",
                help="secrets file [default: %(default)s]",
                default=defaults.get("secrets_file", "secrets.ini"),
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
                default=defaults.get("postgres_password", ""),
            )

            postgresqlgroup.add_argument(
                "--postgresql-dbname",
                dest="postgresql_dbname",
                metavar="DBNAME",
                help="PostgreSQL database name [default: %(default)s]",
                default="lmfdb",
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
            full = section+"_"+key
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

    def get_postgresql_default(self):
        res = dict(self.default_args["postgresql"])
        res["port"] = int(res["port"])
        return res
