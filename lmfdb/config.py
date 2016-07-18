# -*- coding: utf8 -*-
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


class Configuration(object):

    def __init__(self):
        # 1: parsing command-line arguments
        from optparse import OptionParser
        _parser = OptionParser()
        _parser.add_option('-c', '--config-file', dest="config_file",
                           help='configuration file [default: %default]', default="config.ini")
        _parser.add_option(
            '-d', '--debug', action="store_true", dest='debug', help='debug mode [default: %default]', default=False)
        _parser.add_option(
            "-v", action="count", dest="verbosity", help="verbosity level: -v, -vv, or -vvv", default=0)

        _options, _args = _parser.parse_args()

        # print _options

        import os
        from ConfigParser import ConfigParser

        # 2/1: does config file exist?
        if not os.path.exists(_options.config_file):
            _cfgp = ConfigParser()
            # create them in the reverse order
            _cfgp.add_section('lfunc')  # demo
            _cfgp.add_section('mf')    # demo
            _cfgp.add_section('artin')  # demo

            _cfgp.add_section('db')  # database config
            _cfgp.set('db', 'port', '37010')
            _cfgp.set('db', 'host', 'localhost')

            _cfgp.add_section('web')  # webserver
            _cfgp.set('web', 'port', '37777')

            _cfgp.add_section('core')  # core configuration
            _cfgp.set('core', 'debug', 'false')  # default: no debug mode

            with open(_options.config_file, 'wb') as configfile:
                _cfgp.write(configfile)

        # 2/2: reading the config file
        _cfgp = ConfigParser()
        _cfgp.read(_options.config_file)

        # 3: override specific settings
        if _options.debug:
            _cfgp.set('core', 'debug', 'true')

        print _cfgp.get('core', 'debug')

        # some generic function

        def get_config(section, key):
            return _cfgp.get(section, key)

        def all(sep='::'):
            ret = {}
            for s in _cfgp.sections():
                for k, v in _cfgp.items(s):
                    ret['%s%s%s' % (s, sep, k)] = v
            return ret

        # specific data
        self.http_port = _cfgp.getint('web', 'port')
        self.db_port = _cfgp.getint('db', 'port')
        self.db_host = _cfgp.get('db', 'host')
        self.debug = _cfgp.getboolean('core', 'debug')
        self.verbosity = 40 - (10 * _options.verbosity)
