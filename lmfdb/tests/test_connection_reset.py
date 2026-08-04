# Tests for the state the knowl and user backends derive from the database
# session, which psycodict asks them to refresh when it replaces a connection.
#
# A real failover is not something a test suite can arrange, so these tests
# stand in for one: they change what the database reports about the session and
# call the hook psycodict would call, which is the part of the mechanism that
# lives in the LMFDB.

import unittest

from lmfdb import db
from lmfdb.knowledge.knowl import knowldb
from lmfdb.users.pwdmanager import userdb


class ConnectionResetTest(unittest.TestCase):
    def _set_capability(self, attr, value):
        """
        Make the database report ``value`` for one of its capability flags,
        returning what it reported before.
        """
        old = getattr(db, attr)
        setattr(db, attr, value)
        return old

    def test_knowl_backend_follows_the_session(self):
        old = self._set_capability("_read_and_write_knowls", False)
        try:
            knowldb._connection_reset()
            assert not knowldb.can_read_write_knowls(), \
                "knowl editing stayed enabled after the session lost the privilege"

            self._set_capability("_read_and_write_knowls", True)
            knowldb._connection_reset()
            assert knowldb.can_read_write_knowls(), \
                "knowl editing stayed disabled after the session regained the privilege"
        finally:
            self._set_capability("_read_and_write_knowls", old)
            knowldb._connection_reset()

    def test_user_backend_follows_the_session(self):
        old = self._set_capability("_read_and_write_userdb", False)
        try:
            userdb._connection_reset()
            assert not userdb.can_read_write_userdb(), \
                "userdb stayed writable after the session lost the privilege"
            # Failing closed means the columns the session could not confirm
            # are not left behind either.
            assert userdb._cols == userdb._username_full_name

            self._set_capability("_read_and_write_userdb", True)
            userdb._connection_reset()
            assert userdb.can_read_write_userdb(), \
                "userdb stayed read-only after the session regained the privilege"
        finally:
            self._set_capability("_read_and_write_userdb", old)
            userdb._connection_reset()

    def test_grant_policy_is_the_lmfdb_one(self):
        # Only meaningful once psycodict has policies at all; before that it
        # grants these same privileges on its own.
        try:
            from psycodict.grants import LMFDBGrantPolicy
        except ImportError:
            self.skipTest("this psycodict has no grant policies")
        assert db.grant_policy == LMFDBGrantPolicy(), \
            "the database is not granting what the website needs on the tables it creates"
