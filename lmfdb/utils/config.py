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
"""


import argparse
import getpass
import os
import random
import string
import __main__
from requests import get
import socket
from contextlib import closing
from logging import INFO

COCALC_port = 0
root_lmfdb_path = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

from psycodict.config import Configuration as _Configuration


def is_port_open(host, port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        return sock.connect_ex((host, port)) == 0


def abs_path_lmfdb(filename):
    return os.path.relpath(os.path.join(root_lmfdb_path, filename), os.getcwd())


def get_secret_key():
    secret_key_file = abs_path_lmfdb("secret_key")
    # if secret_key_file doesn't exist, create it
    if not os.path.exists(secret_key_file):
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


class Configuration(_Configuration):
    def __init__(self, writeargstofile=False, readargs=False):
        default_config_file = abs_path_lmfdb("config.ini")

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
            "--logfocus", help="name of a logger to focus on", default=argparse.SUPPRESS
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
        # if start-lmfdb.py was executed
        startlmfdbQ = getattr(__main__, '__file__').endswith("start-lmfdb.py") if hasattr(__main__, '__file__') else False
        writeargstofile = writeargstofile or startlmfdbQ
        readargs = readargs or startlmfdbQ
        _Configuration.__init__(self, parser, writeargstofile=writeargstofile, readargs=readargs)

        opts = self.options
        extopts = self.extra_options
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
        if "logfocus" in extopts:
            self.logging_options["logfocus"] = extopts["logfocus"]

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
