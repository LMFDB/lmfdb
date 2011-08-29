# -*- coding: utf8 -*-
# testing users blueprint
from base import LmfdbTest
from main import login_page
from flask import url_for

from pwdmanager import LmfdbUser, LmfdbAnonymousUser, new_user

class UsersTestCase(LmfdbTest):
  def setUp(self):
    LmfdbTest.setUp(self)
    self.users = self.C.userdb.users
    self.users.remove("$test_user")
    self.test_user = new_user("$test_user", "testpw")

    self.app.post('/users/login', data = dict(
            name = '$test_user',
            password = 'testpw'
    ))

  def tearDown(self):
    self.users.remove("$test_user")

  ### helpers
  def get_me(self):
    return self.users.find_one({'_id' : '$test_user'})

  ### test methods
  def test_1(self):
    self.assertTrue(True)

  def test_login_page(self):
    self.assertTrue(login_page.name=="users")

  def test_user_db(self):
    me = self.get_me()
    assert me != None

  def test_myself(self):
    p = self.app.get("/users/myself")
    print p.data
    assert '$test_user' in p.data

  def test_info(self):
    return
    self.app.post('/users/info', data = dict(
          full_name = "test_full_name",
          url = "test_url",
          about = "test_about")
    )
    me = self.get_me()
    print me
    assert me['url'] == 'test_url'
    assert me['about'] == 'test_about'
    assert me['full_name'] == "full_name"
