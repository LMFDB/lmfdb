# -*- coding: utf8 -*-
# this is the master test file, collecting and running all
# test suits

from glob import glob
import unittest
import os

def load_all_tests():
  testfns = glob("*/test_*.py")
  modules = []
  for hit in testfns:
    path, fn = hit.split(r'/')
    name = os.path.splitext(fn)[0]
    module_name = "%s.%s" % (path, name)
    print " >> loading", module_name
    modules.append(__import__(module_name))
  
  print modules
  load = unittest.defaultTestLoader.loadTestsFromModule
  tests = map(load, modules)
  tests.append(load("__main__"))
  return unittest.TestSuite(tests)

# start basic setup
import website
import base
dbport = 37010

class RootTestCase(unittest.TestCase):

  def setUp(self):
    base.app.config['TESTING'] = True
    self.app = base.app.test_client()
    base._init(dbport)

  def test_root(self):
    root = self.app.get("/")
    assert "Index" in root.data

  def test_robots(self):
    r = self.app.get("/robots.txt")
    assert "Disallow: /" in r.data

if __name__=="__main__":
  unittest.main(defaultTest="load_all_tests")
