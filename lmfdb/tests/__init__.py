# -*- coding: utf-8 -*-

import unittest2

from lmfdb.app import app

class LmfdbTest(unittest2.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app
        self.tc = app.test_client()
        import lmfdb.website
        assert lmfdb.website
        from lmfdb import db
        self.db = db
