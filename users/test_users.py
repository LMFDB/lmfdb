# -*- coding: utf8 -*-
# testing users blueprint
import unittest
from main import login_page

print "loaded test_users"

class UsersTestCase(unittest.TestCase):
  def test_1(self):
    self.assertTrue(True)

  def test_login_page(self):
    print "users.login_page test"
    self.assertTrue(login_page.name=="users")
