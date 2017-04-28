# -*- coding: utf8 -*-
# testing users blueprint
from lmfdb.base import LmfdbTest
from main import login_page
import unittest2

class UsersTestCase(LmfdbTest):
    def setUp(self):
        LmfdbTest.setUp(self)
        self.users = self.C.userdb.users
        # With authentication we can no longer add a test user during the test
        # self.users.remove("$test_user")
        # self.test_user = new_user("$test_user", "testpw")

        # self.tc.post('/users/login', data=dict(
        #     name='$test_user',
        #     password='testpw'
        # ))

    def tearDown(self):
        pass # self.users.remove("$test_user")

    ### helpers
    def get_me(self, id='$test_user'):
        return self.users.find_one({'_id': id})

    ### test methods
    def test_1(self):
        self.assertTrue(True)

    def test_login_page(self):
        self.assertTrue(login_page.name == "users")

    def test_user_db(self):
        me = self.get_me('cremona') # any valid user id will do!
        assert me is not None

    @unittest2.skip("skipping since no longer possible to insert test user during test")
    def test_myself(self):
        p = self.tc.get("/users/myself")
        assert '$test_user' in p.data

    def test_user(self, id='cremona'):
        p = self.tc.get("/users/profile/%s" % id)
        assert id in p.data

    def test_info(self):
        return
        with self.tc as tc:
            tc.post('/users/info', data=dict(
                full_name="test_full_name",
                url="test_url",
                about="test_about")
            )
            me = self.get_me()
            print me
            self.app.logger.info(str(me))
            assert me['url'] == 'test_url'
            assert me['about'] == 'test_about'
            assert me['full_name'] == "full_name"
