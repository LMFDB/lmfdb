# Tests for the state the knowl and user backends derive from the database
# session, which psycodict asks them to refresh when it replaces a connection.
#
# A real failover is not something a test suite can arrange, so these tests
# stand in for one: they change what the database reports about the session and
# call the hook psycodict would call, which is the part of the mechanism that
# lives in the LMFDB.

import unittest
from unittest.mock import patch

from lmfdb import db, lmfdb_database
from lmfdb.lmfdb_database import LMFDBDatabase
from lmfdb.knowledge.knowl import knowldb
from lmfdb.users.pwdmanager import userdb
from psycodict.database import PostgresDatabase


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


class StatementTimeoutTest(unittest.TestCase):
    """
    What LMFDBDatabase asks psycodict for when it builds a connection.

    These check the arguments rather than the resulting session, since the
    connection the test suite already has was made long before the test ran and
    a second one is not something a test should open.  Both psycodict APIs are
    covered by setting the flag by hand: the installed psycodict is only ever
    one of them, and CI installs the newer one.
    """

    TIMEOUT = {"statement_timeout": "25s"}

    def _captured_database_kwargs(self, config_user="webserver", supported=True, **kwargs):
        """
        The keyword arguments LMFDBDatabase would hand to psycodict for a
        configuration naming ``config_user``, on a psycodict whose constructor
        takes session settings iff ``supported``.
        """
        captured = {}

        def fake_init(_self, _config, **base_kwargs):
            captured.update(base_kwargs)

        config = {
            "postgresql_options": {"user": config_user},
            "logging_options": {"editor": ""},
        }
        with patch.object(PostgresDatabase, "__init__", fake_init), \
             patch.object(lmfdb_database, "_PSYCODICT_HAS_SESSION_SETTINGS", supported):
            LMFDBDatabase(config, **kwargs)
        return captured

    def test_older_psycodict_is_left_to_its_own_default(self):
        # It has no such argument and would pass this one to psycopg.connect,
        # which does not know it either; it applies the same timeout itself.
        captured = self._captured_database_kwargs(supported=False)
        assert "session_settings" not in captured, \
            "a psycodict without the argument was passed it anyway"

    def test_configured_webserver_gets_the_timeout(self):
        captured = self._captured_database_kwargs()
        assert captured["session_settings"] == self.TIMEOUT, \
            "the web workers did not ask for a statement timeout"

    def test_keyword_user_beats_the_configuration(self):
        captured = self._captured_database_kwargs(user="lmfdb")
        assert captured["user"] == "lmfdb"
        assert "session_settings" not in captured, \
            "a connection as another role was given the webserver timeout"

    def test_keyword_webserver_gets_the_timeout(self):
        captured = self._captured_database_kwargs(config_user="lmfdb", user="webserver")
        assert captured["session_settings"] == self.TIMEOUT, \
            "a connection as webserver did not ask for a statement timeout"

    def test_explicit_settings_are_kept(self):
        settings = {"statement_timeout": "5min", "work_mem": "64MB"}
        captured = self._captured_database_kwargs(session_settings=settings)
        assert captured["session_settings"] == settings, \
            "the caller's session settings were overwritten or merged into"

    def test_none_means_the_lmfdb_default(self):
        # To psycodict this asks for no settings of its own; the LMFDB's are
        # what should fill that in.
        captured = self._captured_database_kwargs(session_settings=None)
        assert captured["session_settings"] == self.TIMEOUT, \
            "an unset session_settings lost the web workers their timeout"

    def test_empty_settings_are_kept(self):
        captured = self._captured_database_kwargs(session_settings={})
        assert captured["session_settings"] == {}, \
            "a caller could not turn the timeout off"
