import datetime
import unittest
from unittest.mock import patch

from lmfdb.lmfdb_database import LMFDBDatabase


class LMFDBDatabaseTest(unittest.TestCase):
    def test_log_db_change_uses_python310_compatible_utc_timestamp(self):
        db = object.__new__(LMFDBDatabase)
        calls = []

        def execute(query, values):
            calls.append((query, values))

        db.login = lambda: "tester"
        db._execute = execute
        with patch("lmfdb.lmfdb_database.socket.gethostname", return_value="devhost"):
            db._log_db_change("rewrite", tablename="nf_fields", logid=17, count=3)

        self.assertEqual(len(calls), 2)
        self.assertIs(LMFDBDatabase.log_db_change, LMFDBDatabase._log_db_change)
        dbrecord_values = calls[0][1]
        ongoing_values = calls[1][1]
        self.assertIsInstance(dbrecord_values[1], datetime.datetime)
        self.assertIsNone(dbrecord_values[1].tzinfo)
        self.assertIsInstance(ongoing_values[2], datetime.datetime)
        self.assertIsNone(ongoing_values[2].tzinfo)
