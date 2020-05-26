# -*- coding: utf-8 -*-

from __future__ import print_function
import unittest2
from six.moves.urllib.request import Request, urlopen
from six.moves.urllib.error import URLError
import ssl
import errno
from lmfdb.app import app


class LmfdbTest(unittest2.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.app = app
        self.tc = app.test_client()
        import lmfdb.website

        assert lmfdb.website
        from lmfdb import db

        self.db = db

    def check(self, homepage, path, text):
        assert path in homepage, "%s not in the homepage" % path
        assert text in self.tc.get(path, follow_redirects=True).get_data(
            as_text=True
        ), "%s not in the %s" % (text, path)

    def check_args(self, path, text):
        assert text in self.tc.get(path, follow_redirects=True).get_data(
            as_text=True
        ), "%s not in the %s" % (text, path)

    def check_args_with_timeout(self, path, text):
        timeout_error = "The search query took longer than expected!"
        data = self.tc.get(path, follow_redirects=True).get_data(as_text=True)
        assert (text in data) or (timeout_error in data), "%s not in the %s" % (
            text,
            path,
        )

    def not_check_args(self, path, text):
        assert not (
            text in self.tc.get(path, follow_redirects=True).get_data(as_text=True)
        ), "%s in the %s" % (text, path)

    def check_external(self, homepage, path, text):
        headers = {"User-Agent": "Mozilla/5.0"}
        context = ssl._create_unverified_context()
        request = Request(path, headers=headers)
        assert path in homepage
        try:
            assert text in urlopen(request, context=context).read().decode("utf-8")
        except URLError as e:
            if e.errno in [errno.ETIMEDOUT, errno.ECONNREFUSED, errno.EHOSTDOWN]:
                pass
            elif "Connection refused" in str(e):  # not every error comes with a errno
                pass
            else:
                print(e)
                print(e.errno)
                raise
