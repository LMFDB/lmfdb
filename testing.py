# -*- coding: utf8 -*-
# this is the master test file, collecting and running all
# test suits
import os

try:
  import unittest2
  ts = unittest2.defaultTestLoader.discover(".", pattern="test_*.py")
  runner = unittest2.runner.TextTestRunner()
  runner.run(ts)
except:
  raise
  print "You need to have unittest2 installed (backport of 2.7 features to Python 2.6)"
  print "most likely run:"
  print "$ sage -sh"
  print "easy_install -U unittest2"
  print "<CTRL+d>"

