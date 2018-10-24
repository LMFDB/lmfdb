# -*- coding: utf-8 -*-
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
import sys
import os

class Configuration(object):

    def __init__(self, writeargstofile = False):
        default_config_file = "config.ini"
        root_lmfdb_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
        if root_lmfdb_path != os.path.abspath(os.getcwd()):
            default_config_file = os.path.relpath(os.path.join(root_lmfdb_path, default_config_file),os.getcwd())

        # 1: parsing command-line arguments
        parser  =  argparse.ArgumentParser(description = 'LMFDB - The L-functions and modular forms database')
        parser.add_argument('-c', '--config-file',
                dest = "config_file",
                metavar = "FILE",
                help = 'configuration file [default: %(default)s]',
                default = default_config_file)

        parser.add_argument(
            '-d', '--debug',
            action = "store_true",
            dest = 'core_debug',
            help = 'enable debug mode')
        parser.add_argument(
            '--color',
            dest = 'core_color',
            metavar = "COLOR",
            help = 'color template (see templates/color.css)',
            default = 0,
            type = int)

        parser.add_argument('-p','--port',
                dest = 'web_port',
                metavar = 'PORT',
                help = 'the LMFDB server will be running on PORT [default: %(default)d]',
                type = int,
                default = 37777)
        parser.add_argument('-b', '--bind_ip',
                dest = 'web_bindip',
                metavar ='HOST',
                help = 'the LMFDB server will be listening to HOST [default: %(default)s]',
                default = '127.0.0.1')

        logginggroup = parser.add_argument_group('Logging options:')
        logginggroup.add_argument('--logfile',
                help = 'logfile for flask [default: %(default)s]',
                dest = 'logging_logfile',
                metavar = 'FILE',
                default = 'flasklog')

        logginggroup.add_argument('--logfocus',
                help = 'name of a logger to focus on',
                default = argparse.SUPPRESS)

        # PostgresSQL options
        postgresqlgroup = parser.add_argument_group('PostgreSQL options')
        postgresqlgroup.add_argument('--postgresql-host',
                dest = 'postgresql_host',
                metavar = 'HOST',
                help = 'PostgreSQL server host or socket directory [default: %(default)s]',
                default = 'devmirror.lmfdb.xyz')
        postgresqlgroup.add_argument('--postgresql-port',
                dest = 'postgresql_port',
                metavar = 'PORT',
                type = int,
                help = 'PostgreSQL server port [default: %(default)d]',
                default = 5432)

        postgresqlgroup.add_argument('--postgresql-user',
                dest = 'postgresql_user',
                metavar = 'USER',
                help = 'PostgreSQL username [default: %(default)s]',
                default = "lmfdb")

        postgresqlgroup.add_argument('--postgresql-pass',
                dest = 'postgresql_password',
                metavar = 'PASS',
                help = 'PostgreSQL password [default: %(default)s]',
                default = "lmfdb")

        # undocumented options
        parser.add_argument('--enable-profiler',
                dest = 'profiler',
                help=argparse.SUPPRESS,
                action='store_true',
                default=argparse.SUPPRESS)

        # undocumented flask options
        parser.add_argument('--enable-reloader',
                dest='use_reloader',
                help=argparse.SUPPRESS,
                action='store_true',
                default=argparse.SUPPRESS)

        parser.add_argument('--disable-reloader',
                dest='use_reloader',
                help=argparse.SUPPRESS,
                action='store_false',
                default=argparse.SUPPRESS)

        parser.add_argument('--enable-debugger',
                dest='use_debugger',
                help=argparse.SUPPRESS,
                action = 'store_true',
                default=argparse.SUPPRESS)

        parser.add_argument('--disable-debugger',
                dest='use_debugger',
                help=argparse.SUPPRESS,
                action='store_false',
                default=argparse.SUPPRESS)
        if os.path.split(sys.argv[0])[-1] == "start-lmfdb.py" or writeargstofile:
            args = parser.parse_args()
        else:
            # only read config file
            args = parser.parse_args([])
        args_dict = vars(args)
        default_arguments_dict = vars(parser.parse_args([]))
        if writeargstofile:
            default_arguments_dict = dict(args_dict)

        del default_arguments_dict['config_file']

        self.default_args = {}
        for key, val in default_arguments_dict.iteritems():
            sec, opt = key.split('_', 1)
            if sec not in self.default_args:
                self.default_args[sec] = {}
            self.default_args[sec][opt] = str(val)



        from ConfigParser import ConfigParser

        # reading the config file, creating it if necessary
        # 2/1: does config file exist?
        if not os.path.exists(args.config_file):
            if not writeargstofile:
                print("Config file: %s not found, creating it with the default values" % args.config_file )
            else:
                print("Config file: %s not found, creating it with the passed values" % args.config_file )
            _cfgp  =  ConfigParser()

            # create sections
            _cfgp.add_section('core')
            _cfgp.add_section('web')
            _cfgp.add_section('postgresql')
            _cfgp.add_section('logging')


            for sec, options in self.default_args.iteritems():
                for opt, val in options.iteritems():
                    _cfgp.set(sec, opt, str(val))

            with open(args.config_file, 'wb') as configfile:
                _cfgp.write(configfile)

        # 2/2: reading the config file
        _cfgp  =  ConfigParser()
        _cfgp.read(args.config_file)


        # 3: override specific settings
        def all(sep = '_'):
            ret  =  {}
            for s in _cfgp.sections():
                for k, v in _cfgp.items(s):
                    ret['%s%s%s' % (s, sep, k)]  =  v
            return ret

        all_set = all()

        for key, val in default_arguments_dict.iteritems():
            # if a nondefault value was passed through command line arguments set it
            # or if a default value was not set in the config file
            if args_dict[key] != val or key not in all_set:
                sec, opt = key.split('_')
                _cfgp.set(sec, opt, str(args_dict[key]))


        # some generic functions
        def get(section, key):
            return _cfgp.get(section, key)

        def getint(section, key):
            return _cfgp.getint(section, key)

        def getboolean(section, key):
            return _cfgp.getboolean(section, key)



        self.flask_options = {
                "port": getint('web', 'port'),
                "host": get('web', 'bindip'),
                "debug": getboolean('core', 'debug')
                }
        for opt in ['use_debugger', 'use_reloader', 'profiler']:
            if opt in args_dict:
                self.flask_options[opt] = args_dict[opt]

        self.color = getint('core', 'color')

        self.postgresql_options = {
                "port": getint("postgresql", "port"),
                "host": get("postgresql", "host"),
                "dbname": "lmfdb"}

        # optional items
        for elt in ['user','password']:
            if _cfgp.has_option("postgresql", elt):
                self.postgresql_options[elt] = get("postgresql", elt)

        self.logging_options = {'logfile': get('logging', 'logfile')}
        if "logfocus" in args_dict:
            self.logging_options["logfocus"] = args_dict["logfocus"]
        if _cfgp.has_option("logging", "editor"):
            self.logging_options["editor"] = get("logging", "editor")

    def get_all(self):
        return { 'flask_options' : self.flask_options, 'postgresql_options' : self.postgresql_options, 'logging_options' : self.logging_options}

    def get_flask(self):
        return self.flask_options

    def get_color(self):
        return self.color

    def get_postgresql(self):
        return self.postgresql_options

    def get_postgresql_default(self):
        res = dict(self.default_args["postgresql"])
        res["port"] = int(res["port"])
        return res

    def get_logging(self):
        return self.logging_options


if __name__ == '__main__':
    Configuration(writeargstofile = True)
