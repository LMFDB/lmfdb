# -*- coding: utf8 -*-
# testing users blueprint
from base import LmfdbTest
from main import login_page

class UsersTestCase(LmfdbTest):
  def test_1(self):
    self.assertTrue(True)

  def test_login_page(self):
    print "users.login_page test"
    self.assertTrue(login_page.name=="users")
