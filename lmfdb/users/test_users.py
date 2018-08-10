# -*- coding: utf-8 -*-
# testing users blueprint
from lmfdb.base import LmfdbTest
from main import login_page
from lmfdb.users.main import userdb

class UsersTestCase(LmfdbTest):
    ### helpers
    def get_me(self, uid='$test_user'):
        return userdb.lookup(uid)

    ### test methods
    def test_login_page(self):
        self.assertTrue(login_page.name == "users")

    def test_user_db(self):
        me = self.get_me('cremona') # any valid user id will do!
        assert me is not None

    def test_user(self, id='cremona'):
        p = self.tc.get("/users/profile/%s" % id)
        assert id in p.data
