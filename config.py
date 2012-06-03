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

# only make "config" variable visible
__all__ = ['config']

import collections
class LmfdbConfig(collections.Mapping):
  '''
  This is the LMFDB configuration. Its values are immutable!
  '''
  def __init__(self):
    self._dict = dict()

  def __iter__(self):
    return iter(self._dict)

  def __getitem__(self, key):
    return self._dict[key]

  def __getattr__(self, key):
    if not key in self._dict:
      raise AttributeError('there is no %s' % key)
    return self._dict[key]

  def __hash__(self):
    return hash(tuple(sorted(self._dict.iteritems())))

default_config_fn = 'config.ini'

# 1: parsing command-line arguments
from optparse import OptionParser
parser = OptionParser()
parser.add_option('-c', '--config-file', dest="config_file",
                  help='configuration file',
                  default=default_config_fn)

options, args = parser.parse_args()

import os
from ConfigParser import ConfigParser

# 2/1: does config file exist?
if not os.path.exists(options.config_file):
  cfgp = ConfigParser()
  # create them in the reverse order
  cfgp.add_section('lfunc') # demo
  cfgp.add_section('mf')    # demo
  cfgp.add_section('artin') # demo

  cfgp.add_section('db') # database config
  cfgp.set('db', 'port', '37010')
  cfgp.set('db', 'host', 'localhost')

  cfgp.add_section('web') # webserver 
  cfgp.set('web', 'port', '37777')

  cfgp.add_section('core') # core configuration
  cfgp.set('core', 'debug', 'false') # default: no debug mode

  with open(options.config_file, 'wb') as configfile:
    cfgp.write(configfile)

# 2/2: reading the config file
cfgp = ConfigParser()
cfgp.read(options.config_file)


