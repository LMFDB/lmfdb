# testing users blueprint

from unittest.mock import patch

from lmfdb.tests import LmfdbTest
from .main import login_page
from lmfdb.users.main import userdb

class UsersTestCase(LmfdbTest):
    ### helpers
    def get_me(self, uid='$test_user'):
        return userdb.lookup(uid)

    ### test methods
    def test_login_page(self):
        self.assertTrue(login_page.name == "users")

    def test_login_greeting_escapes_full_name(self):
        full_name = '''O'Neil & <b>"Alice"</b>'''
        data = {"username": "flash_test", "full_name": full_name,
                "bcpassword": "unused"}
        with self.app.app_context(), \
                patch.object(userdb, "user_exists", return_value=True), \
                patch.object(userdb, "lookup", return_value=data), \
                patch.object(userdb, "authenticate", return_value=True):
            response = self.app.test_client().post(
                "/users/login",
                data={"name": "flash_test", "password": "unused", "next": ""},
                follow_redirects=True)
        page = response.get_data(as_text=True)
        assert response.status_code == 200
        assert "Hello O&#39;Neil &amp; &lt;b&gt;&#34;Alice&#34;&lt;/b&gt;, your login was successful!" in page
        assert full_name not in page

    def test_user_db(self):
        me = self.get_me('cremona') # any valid user id will do!
        assert me is not None

    def test_user(self, id='cremona'):
        p = self.tc.get("/users/profile/%s" % id)
        assert id in p.get_data(as_text=True)
